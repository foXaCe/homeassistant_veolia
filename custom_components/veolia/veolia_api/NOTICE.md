# Client Veolia vendoré

Ce dossier est une copie intégrée du client Python **veolia-api**.

- Source : https://github.com/foXaCe/veolia-api (tag `v2.2.1`)
- Fork amont : https://github.com/Jezza34000/veolia-api
- Licence : MIT

## Pourquoi vendoré ?

Home Assistant (validation `hassfest`) n'accepte que des dépendances **PyPI**
dans `manifest.json`. Le fork corrigé — qui résout le `client_id` Cognito **et**
le backend de données **par portail** (au lieu d'un backend codé en dur),
permettant les portails à backend dédié comme `www.ea-pm.fr` — n'est pas publié
sur PyPI. Il est donc embarqué ici.

Seule dépendance tierce non fournie par Home Assistant : `tenacity`
(déclarée dans `manifest.json`). `aiohttp` est fourni par Home Assistant.

## Mise à jour

Reportez les correctifs sur le fork, puis resynchronisez ce dossier depuis
`veolia_api/` du fork (en corrigeant l'import `from veolia_api.exceptions`
en `from .exceptions`).

## Licence MIT

```
Copyright (c) 2025 Jezza34000

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```
