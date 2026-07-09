# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

Ce fichier est maintenu automatiquement par
[release-please](https://github.com/googleapis/release-please) à partir des
conventional commits.

## [2.4.0](https://github.com/foXaCe/homeassistant_veolia/compare/v2.3.0...v2.4.0) (2026-07-09)


### Added

* add billing index sensor with contract details, FR date for next payment ([a09dbb7](https://github.com/foXaCe/homeassistant_veolia/commit/a09dbb71d26f3f231a66481fd820641357e18fe0))
* daily consumption shows last available day instead of empty today ([f2214d8](https://github.com/foXaCe/homeassistant_veolia/commit/f2214d8e2991d82dd9ee59bfb285c0947128a919))


### Fixed

* coordinator error handling, reauth flow, runtime_data, unique config entry ([b0125c3](https://github.com/foXaCe/homeassistant_veolia/commit/b0125c3b897ac3287a64ae8bd8fab25443b6a699))

## [2.3.0](https://github.com/foXaCe/homeassistant_veolia/compare/v2.2.0...v2.3.0) (2026-07-09)


### Added

* add balance, monthly payment and next direct debit sensors ([cf14113](https://github.com/foXaCe/homeassistant_veolia/commit/cf14113e373151d834a9fdd390cb0124f572ac56))


### Documentation

* dedupe CHANGELOG 2.2.0 section ([c9a3d90](https://github.com/foXaCe/homeassistant_veolia/commit/c9a3d90fa663c95357a6607222d409084ab68b7c))

## [2.2.0](https://github.com/foXaCe/homeassistant_veolia/compare/v2.1.0...v2.2.0) (2026-07-09)

### Added

- Prise en charge du portail **Eau de Perpignan Méditerranée Métropole** (`www.ea-pm.fr`)
  ([202bccc](https://github.com/foXaCe/homeassistant_veolia/commit/202bcccb68d89853bb84618dfaaad69915e33930)).

### Changed

- Client `veolia_api` vendoré sous `custom_components/veolia/veolia_api/` (fork
  [foXaCe/veolia-api](https://github.com/foXaCe/veolia-api) v2.2.0) : il résout le
  `client_id` **et** le backend de données par portail (au lieu d'un backend codé en
  dur), permettant les portails à backend dédié comme `www.ea-pm.fr`. Vendoré car
  hassfest n'accepte que des dépendances PyPI. Seule dépendance ajoutée : `tenacity`
  ([8c7da12](https://github.com/foXaCe/homeassistant_veolia/commit/8c7da12cacee3d367b3fbbc23999be6967e74ee2)).
- Bootstrap complet du dépôt : CI, release-please, Renovate, sécurité, documentation.

## [2.1.0] - 2026-07-09

Version courante au moment du bootstrap du dépôt (voir
[l'historique amont](https://github.com/foXaCe/homeassistant_veolia/commits/main)
pour le détail des versions antérieures).
