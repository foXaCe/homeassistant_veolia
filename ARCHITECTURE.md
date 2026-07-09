# Architecture

Vue d'ensemble du fonctionnement interne de l'intégration `veolia`.

## Flux de données

```text
Portail Veolia (cloud)
        │  HTTPS
        ▼
veolia_api (client Python externe, PyPI)
        │
        ▼
VeoliaDataUpdateCoordinator (coordinator.py, polling toutes les 6 h)
        │  entry.runtime_data (VeoliaData)
        ▼
Entités : sensor / binary_sensor / switch / text
```

## Modules

| Fichier            | Rôle                                                                     |
| ------------------ | ------------------------------------------------------------------------ |
| `__init__.py`      | `async_setup_entry` : instancie le client + coordinator, forward setup vers les plateformes |
| `config_flow.py`   | Flow UI en 3 étapes : commune → sélection du portail → identifiants      |
| `coordinator.py`   | `VeoliaDataUpdateCoordinator` (DataUpdateCoordinator, `update_interval=6h`), gestion `ConfigEntryAuthFailed` |
| `data.py`          | `VeoliaConfigEntry = ConfigEntry[VeoliaData]` — typage du `runtime_data` (client, coordinator, integration) |
| `model.py`         | Modèle de données consommation (journalière, mensuelle, index, alertes)  |
| `entity.py`        | Classe de base des entités (device info, rattachement coordinator)       |
| `sensor.py`        | Capteurs de consommation, index, dernière relève                         |
| `binary_sensor.py` | États des alertes de consommation                                        |
| `switch.py`        | Activation/désactivation des notifications SMS d'alerte                  |
| `text.py`          | Saisie des seuils d'alertes (journalier, mensuel, logement vide)         |
| `const.py`         | Constantes (`DOMAIN`, `CONF_PORTAL_URL`, logger)                         |
| `translations/`    | `en.json`, `fr.json`                                                     |

## Points notables

- **Dépendance `recorder`** : l'intégration injecte l'historique de consommation du mois
  en cours dans les statistiques Home Assistant (dashboard Énergie) — les données Veolia
  arrivent avec au minimum 24 h de retard.
- **Client API externe** : toute la logique d'authentification/portails vit dans
  [veolia-api](https://github.com/Jezza34000/veolia-api) (`veolia_api` sur PyPI), épinglé
  dans `manifest.json` et `requirements.txt`.
- **Portails multiples** : le config flow résout la commune via l'API de référence des
  communes, puis choisit le portail (`CONF_PORTAL_URL`).

## Release & CI

- **release-please** maintient une Release PR ; au merge : tag `vX.Y.Z`, CHANGELOG,
  bump de `manifest.json`/`pyproject.toml`, upload de `veolia.zip` sur la release.
- **CI** : prek (ruff, codespell, gitleaks, renovate-config-validator), hassfest,
  validation HACS, CodeQL, audit sécurité quotidien (pip-audit, OSV-Scanner, gitleaks).
