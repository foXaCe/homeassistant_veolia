# CLAUDE.md

Intégration Home Assistant custom `veolia` (Veolia Eau, portails français).
Lire `ARCHITECTURE.md` avant toute modification structurelle.

## Commandes

- Tests : `.venv/bin/python -m pytest tests/ -q` (coverage ≥ 90 % exigé en CI)
- Typing : `.venv/bin/python -m mypy custom_components/veolia/` (strict, 0 erreur)
- Lint : `./scripts/lint` (prek : ruff, ruff-format, codespell, gitleaks — identique CI)
- Environnement : `uv venv .venv --python 3.14 && uv pip install -r requirements_dev.txt`

## Invariants durs

- **unique_id** : format `{account_id}_{key}`. Ne JAMAIS changer le `key` d'une
  description d'entité sans écrire une migration (`async_migrate_entry`,
  voir la v1→v2 dans `custom_components/veolia/__init__.py`).
- **Traductions** : `strings.json` est la source de vérité →
  recopier dans `translations/en.json`, traduire dans `translations/fr.json`
  (vouvoiement), icône dans `icons.json`. Les quatre fichiers bougent ensemble.
- **model.py** : fonctions pures uniquement — aucun import Home Assistant, aucune I/O.
- **Client API** : toute logique d'authentification/portail va dans le fork
  [foXaCe/veolia-api](https://github.com/foXaCe/veolia-api) (PyPI
  `veolia-api-foxace`), jamais dans ce dépôt. Bump du pin dans `manifest.json`.

## Conventions

- Conventional commits (release-please génère le changelog) : `feat:`, `fix:`, `docs:`…
- Git : ne jamais commiter/pusher de sa propre initiative — l'utilisateur décide.
- Recettes « Ajouter une entité / une plateforme » : voir `ARCHITECTURE.md`.
