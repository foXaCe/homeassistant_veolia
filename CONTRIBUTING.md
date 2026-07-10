# Contribuer

Merci de votre intérêt pour l'intégration Veolia Eau !

## Rapports de bug

Utilisez le [modèle de rapport de bug](https://github.com/foXaCe/homeassistant_veolia/issues/new?template=bug_report.yml).

## Demandes de fonctionnalité

Utilisez le [modèle de demande de fonctionnalité](https://github.com/foXaCe/homeassistant_veolia/issues/new?template=feature_request.yml).

## Ajouter un portail

L'authentification et l'accès aux données passent par le paquet PyPI
[`veolia-api-foxace`](https://pypi.org/project/veolia-api-foxace/) (module
`veolia_api`), publié depuis le fork
[foXaCe/veolia-api](https://github.com/foXaCe/veolia-api). Chaque portail y est
décrit par son `client_id` Cognito **et** son backend de données
(dict `VEOLIA_PORTALS` dans `veolia_api/portals.py` de ce fork).

Si votre portail Veolia (champ `type_commune` = `REDIRIGE` avec un hostname
inconnu, voir le [README](README.md#vérifier-léligibilité-de-votre-commune))
n'est pas encore supporté :

1. Ouvrez une issue en précisant le hostname exact du portail (celui de la barre
   d'adresse une fois connecté à votre compte client).
2. Si vous êtes développeur, proposez une PR sur le fork
   [foXaCe/veolia-api](https://github.com/foXaCe/veolia-api) ajoutant l'entrée à
   `VEOLIA_PORTALS` : le `client_id` se trouve dans le bundle JavaScript du
   portail (`ClientId:"..."`), le `backend_url` dans les appels réseau vers
   `*.istefr.fr` (à ne préciser que s'il diffère du backend par défaut).
3. Après publication d'une nouvelle version sur PyPI, la version épinglée dans
   `manifest.json` (`requirements`) est bumpée ici (Renovate ouvre la PR
   automatiquement).

## Pull requests

1. Forkez le dépôt
2. Créez une branche dédiée : `git checkout -b feat/ma-fonctionnalite`
3. Installez les hooks : voir [Setup local](#setup-local)
4. Vérifiez le lint : `./scripts/lint` (identique au job CI)
5. Commitez en suivant les [conventional commits](https://www.conventionalcommits.org/fr/) : `feat: …`, `fix: …`, `docs: …`
6. Poussez et ouvrez une PR vers `main`

Les titres de commits conditionnent le changelog généré automatiquement par release-please :
`feat:` = version mineure, `fix:` = correctif, `feat!:` ou `BREAKING CHANGE:` = version majeure.

## Setup local

```bash
pipx install prek   # ou : brew install j178/prek/prek
prek install
pip install -r requirements_dev.txt
```

> prek est un remplaçant drop-in (Rust) de pre-commit, nettement plus rapide.
> Si vous préférez la version Python : `pipx install pre-commit && pre-commit install`.

Pour lancer tous les hooks manuellement :

```bash
prek run --all-files
```

## Gestion des dépendances

Ce dépôt utilise **Renovate** (et non Dependabot). Les PR de mise à jour sont ouvertes
par le bot `@renovate[bot]`. Voir le [dashboard Renovate](../../issues?q=is%3Aissue+author%3Aapp%2Frenovate).
