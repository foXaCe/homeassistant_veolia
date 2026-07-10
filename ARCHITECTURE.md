# Architecture

Vue d'ensemble du fonctionnement interne de l'intégration `veolia`.

## Flux de données

```text
Portail Veolia (cloud)
        │  HTTPS (session partagée Home Assistant, timeout 15 s, retry tenacity)
        ▼
veolia_api/ (client vendoré : Cognito, portails, consommation, alertes)
        │
        ▼
VeoliaDataUpdateCoordinator (coordinator.py, intervalle configurable, défaut 6 h)
        │  entry.runtime_data (VeoliaConfigEntry = ConfigEntry[VeoliaDataUpdateCoordinator])
        │  coordinator.data = VeoliaModel (raw + computed)
        ▼
VeoliaBaseEntity (entity.py, CoordinatorEntity commune, DeviceInfo)
        ▼
Entités : sensor (9) / binary_sensor (3) / switch (3) / text (2)
        │
        └─ statistics.py → recorder (dashboard Énergie : index, conso jour/mois)
```

## Modules

| Fichier            | Rôle                                                                     |
| ------------------ | ------------------------------------------------------------------------ |
| `__init__.py`      | `async_setup_entry`/`async_unload_entry` + `async_migrate_entry` (v1→v2 : unique_id `{entry_id}_…` → `{account_id}_…`) |
| `config_flow.py`   | Flow UI (code postal → commune → identifiants) + reauth + reconfigure + options (`scan_interval`, `OptionsFlowWithReload`) |
| `coordinator.py`   | `VeoliaDataUpdateCoordinator(DataUpdateCoordinator[VeoliaModel])` ; fetch initial 1 an puis fenêtre glissante 2 mois ; écritures centralisées `async_set_alert_settings()` |
| `data.py`          | `type VeoliaConfigEntry = ConfigEntry[VeoliaDataUpdateCoordinator]` — typage du `runtime_data` |
| `model.py`         | Fonctions **pures** (aucun import HA) : calculs index/conso/statistiques/facturation, `VeoliaModel`/`VeoliaComputed`, `StatisticsRow` |
| `entity.py`        | `VeoliaBaseEntity` : base `CoordinatorEntity` commune à toutes les plateformes (unique_id `{account_id}_{key}`, `DeviceInfo` complet) |
| `statistics.py`    | Import des statistiques cumulées dans le recorder (réimporté à chaque refresh) |
| `helpers.py`       | Fonctions pures partagées (`is_unoccupied_mode`)                          |
| `sensor.py`        | 9 capteurs via `VeoliaSensorEntityDescription` (`value_fn`/`attributes_fn`/`statistics_fn`) |
| `binary_sensor.py` | 3 états d'alertes via descriptions (`is_on_fn`/`available_fn`), catégorie diagnostic |
| `switch.py`        | 3 interrupteurs d'alertes via descriptions (`turn_on/off_settings`), catégorie configuration |
| `text.py`          | 2 seuils d'alerte via descriptions (0 = désactivation), catégorie configuration |
| `diagnostics.py`   | Diagnostics de config entry avec redaction des données sensibles          |
| `const.py`         | Toutes les constantes (`Final`), zéro string magique ailleurs             |
| `icons.json`       | Icônes (y compris icônes par état on/off)                                 |
| `strings.json`     | Source de vérité des traductions ; `translations/en.json` en est la copie |
| `veolia_api/`      | Client Veolia vendoré (fork corrigé) : `veolia_api.py`, `portals.py` (registre `hostname → client_id + backend`), `constants.py`, `model.py`, `exceptions.py` — voir `NOTICE.md` |

## Ajouter une entité

1. Ajouter une description dans le tuple `SENSORS`/`BINARY_SENSORS`/`SWITCHES`/`TEXTS`
   de la plateforme concernée (`key` = suffixe stable du unique_id, `translation_key`).
2. Ajouter les traductions dans `strings.json`, recopier dans `translations/en.json`,
   traduire dans `translations/fr.json` (vouvoiement), et l'icône dans `icons.json`.
3. Si la valeur vient d'un nouveau calcul : l'ajouter dans `model.py` (fonction pure +
   champ `VeoliaComputed`) avec ses tests dans `tests/test_model.py`.

## Ajouter une plateforme

1. Créer `<platform>.py` sur le modèle des existants : description dataclass frozen,
   tuple de descriptions, `async_setup_entry` (uniquement l'instanciation),
   classe `Veolia<Platform>(VeoliaBaseEntity, <Platform>Entity)`, `PARALLEL_UPDATES = 0`.
2. Ajouter la `Platform` à `PLATFORMS` dans `__init__.py`.
3. Créer `tests/test_<platform>.py`.

## Points notables

- **unique_id** : format `{account_id}_{key}` (id d'abonnement Veolia). La migration
  v1→v2 (`async_migrate_entry`) remappe automatiquement l'ancien format
  `{entry_id}_{key}` — ne JAMAIS changer un `key` de description sans nouvelle migration.
- **Dépendance `recorder`** : l'intégration injecte l'historique de consommation dans
  les statistiques Home Assistant (dashboard Énergie) — les données Veolia arrivent
  avec au minimum 24 h de retard. Les statistiques sont réimportées à chaque refresh
  du coordinator.
- **Client API vendoré** : la logique d'authentification/portails vit dans le client
  [veolia-api](https://github.com/foXaCe/veolia-api) (fork), **embarqué** sous
  `custom_components/veolia/veolia_api/` (voir son `NOTICE.md`). Il est vendoré car
  hassfest n'accepte que des dépendances PyPI dans `manifest.json` et le fork corrigé
  n'est pas publié sur PyPI. Seule dépendance tierce : `tenacity` (dans `manifest.json`).
  Le vendored est soumis au même niveau d'exigence que le reste (ruff + mypy --strict) ;
  reporter les correctifs sur le fork upstream.
- **Portails multiples** : le config flow résout la commune via l'API de référence des
  communes, puis choisit le portail (`CONF_PORTAL_URL`). Chaque portail a son propre
  `client_id` Cognito **et** son backend de données ; le client vendoré résout les deux
  par portail (`VEOLIA_PORTALS`). C'est ce qui permet les portails à backend dédié comme
  `www.ea-pm.fr` (Perpignan Méditerranée Métropole → `prd-ael-sirius-pmm-backend`).
- **Erreurs** : `VeoliaAPIInvalidCredentialsError` → `ConfigEntryAuthFailed` (reauth),
  toute autre `VeoliaAPIError` → `UpdateFailed` (retry au cycle suivant) ; les écritures
  lèvent `HomeAssistantError` avec clés de traduction (`exceptions` dans strings.json).

## Tests

- `tests/` : pytest + `pytest-homeassistant-custom-component` (épinglé sur la version
  HA cible), coverage ≥ 90 % exigé en CI (`--cov-fail-under=90`).
- Environnement local : `uv venv .venv --python 3.14` puis
  `uv pip install -r requirements_dev.txt` ; lancer `.venv/bin/pytest tests/`.

## Release & CI

- **release-please** maintient une Release PR ; au merge : tag `vX.Y.Z`, CHANGELOG,
  bump de `manifest.json`/`pyproject.toml`, upload de `veolia.zip` sur la release.
- **CI** : prek (ruff, codespell, gitleaks, renovate-config-validator), pytest+coverage,
  mypy --strict, hassfest, validation HACS, CodeQL, audit sécurité quotidien
  (pip-audit, OSV-Scanner, gitleaks).
