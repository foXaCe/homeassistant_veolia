# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

Ce fichier est maintenu automatiquement par
[release-please](https://github.com/googleapis/release-please) à partir des
conventional commits.

## [4.0.1](https://github.com/foXaCe/homeassistant_veolia/compare/v4.0.0...v4.0.1) (2026-07-12)


### Fixed

* bump veolia-api-foxace to 2.4.3 ([#25](https://github.com/foXaCe/homeassistant_veolia/issues/25)) ([66241bb](https://github.com/foXaCe/homeassistant_veolia/commit/66241bb75a1422ba7896a3ad77058b10b61a7a30))

## [4.0.0](https://github.com/foXaCe/homeassistant_veolia/compare/v3.0.2...v4.0.0) (2026-07-10)


### ⚠ BREAKING CHANGES

* remove personal identifiers from billing_index sensor attributes ([#22](https://github.com/foXaCe/homeassistant_veolia/issues/22))

### Added

* add cost external statistic with configurable price per m³ ([#21](https://github.com/foXaCe/homeassistant_veolia/issues/21)) ([5f2ba73](https://github.com/foXaCe/homeassistant_veolia/commit/5f2ba735f655889a7e70ebf16cd47a89d407cf61))


### Fixed

* dedicated maintenance error in the commune flow and info.md resync ([#24](https://github.com/foXaCe/homeassistant_veolia/issues/24)) ([e942421](https://github.com/foXaCe/homeassistant_veolia/commit/e942421e38142eac03227ea1b74c949f0d3fb284))
* guard the statistics rewind against a vanished anchor row ([#19](https://github.com/foXaCe/homeassistant_veolia/issues/19)) ([dd7b7e2](https://github.com/foXaCe/homeassistant_veolia/commit/dd7b7e2df4267d3918d1b3cdc9443f17c350a840))
* remove personal identifiers from billing_index sensor attributes ([#22](https://github.com/foXaCe/homeassistant_veolia/issues/22)) ([ddbb1fd](https://github.com/foXaCe/homeassistant_veolia/commit/ddbb1fd0a922eee71af897a6189100f07c3e0fb1))
* serialize concurrent alert-settings writes with a lock ([#23](https://github.com/foXaCe/homeassistant_veolia/issues/23)) ([f67a5f7](https://github.com/foXaCe/homeassistant_veolia/commit/f67a5f72bcf393b2c165c40553656bb64a228eff))

## [3.0.2](https://github.com/foXaCe/homeassistant_veolia/compare/v3.0.1...v3.0.2) (2026-07-10)


### Fixed

* translate coordinator errors and use French statistic names ([#17](https://github.com/foXaCe/homeassistant_veolia/issues/17)) ([3c7505a](https://github.com/foXaCe/homeassistant_veolia/commit/3c7505a406a879bf65e06b5f390784f82ab03da5))

## [3.0.1](https://github.com/foXaCe/homeassistant_veolia/compare/v3.0.0...v3.0.1) (2026-07-10)


### Fixed

* **deps:** bump veolia-api-foxace to 2.4.1 ([#15](https://github.com/foXaCe/homeassistant_veolia/issues/15)) ([0094dd8](https://github.com/foXaCe/homeassistant_veolia/commit/0094dd85f8abd54c40215efafc7ff82e9e315c20))

## [3.0.0](https://github.com/foXaCe/homeassistant_veolia/compare/v2.4.0...v3.0.0) (2026-07-10)


### ⚠ BREAKING CHANGES

* anchored external statistics, config flow hardening and repair issues ([#13](https://github.com/foXaCe/homeassistant_veolia/issues/13))

### Added

* anchored external statistics, config flow hardening and repair issues ([#13](https://github.com/foXaCe/homeassistant_veolia/issues/13)) ([cc880a0](https://github.com/foXaCe/homeassistant_veolia/commit/cc880a0bae754dc22280d13eb2feb950887124d8))
* complete integration overhaul (coordinator, entities, unique_id migration, tests 98%) ([62c0742](https://github.com/foXaCe/homeassistant_veolia/commit/62c0742a5a34f9c4775c47b5b06da037c7a99d6c))
* config entry diagnostics with sensitive-data redaction ([62c0742](https://github.com/foXaCe/homeassistant_veolia/commit/62c0742a5a34f9c4775c47b5b06da037c7a99d6c))
* configurable update interval via an options flow (1-24h) ([62c0742](https://github.com/foXaCe/homeassistant_veolia/commit/62c0742a5a34f9c4775c47b5b06da037c7a99d6c))
* integration overhaul — system health, platinum quality scale, upstreamed API tests ([#14](https://github.com/foXaCe/homeassistant_veolia/issues/14)) ([3d79287](https://github.com/foXaCe/homeassistant_veolia/commit/3d79287b548d0ed419c8eddcb79dbf8a8415fb71))
* reconfigure flow to update credentials from the UI ([62c0742](https://github.com/foXaCe/homeassistant_veolia/commit/62c0742a5a34f9c4775c47b5b06da037c7a99d6c))
* unique_ids migrated to the Veolia subscription id (automatic v1→v2 migration, entity_ids preserved) ([62c0742](https://github.com/foXaCe/homeassistant_veolia/commit/62c0742a5a34f9c4775c47b5b06da037c7a99d6c))


### Fixed

* binary_sensor/switch/text entities were polled instead of coordinator-driven and ignored API failures in their availability ([62c0742](https://github.com/foXaCe/homeassistant_veolia/commit/62c0742a5a34f9c4775c47b5b06da037c7a99d6c))
* daily/monthly alert threshold was sent as a string instead of an int ([62c0742](https://github.com/foXaCe/homeassistant_veolia/commit/62c0742a5a34f9c4775c47b5b06da037c7a99d6c))
* meter-index recorder statistics were never imported (# NOT WORKING hook re-enabled) ([62c0742](https://github.com/foXaCe/homeassistant_veolia/commit/62c0742a5a34f9c4775c47b5b06da037c7a99d6c))
* **security:** redact password from request-body debug logs ([7443b09](https://github.com/foXaCe/homeassistant_veolia/commit/7443b0903a87157b299e1594b5a4a7af8e57474c))
* vendored client robustness (raw-int timeout ValueError, 401 handling, token expiry margin, typed AlertSettings defaults) ([62c0742](https://github.com/foXaCe/homeassistant_veolia/commit/62c0742a5a34f9c4775c47b5b06da037c7a99d6c))


### Changed

* EntityDescription pattern on all platforms, modular pure-function model, strict typing (mypy --strict) incl. the vendored client ([62c0742](https://github.com/foXaCe/homeassistant_veolia/commit/62c0742a5a34f9c4775c47b5b06da037c7a99d6c))
* replace vendored client with the veolia-api-foxace PyPI package ([#12](https://github.com/foXaCe/homeassistant_veolia/issues/12)) ([7a5a32b](https://github.com/foXaCe/homeassistant_veolia/commit/7a5a32bca16c8d300822d314ad01ebd416f64360))


### Documentation

* remove duplicated unreleased changelog section (release-please owns it) ([fa711e5](https://github.com/foXaCe/homeassistant_veolia/commit/fa711e531dcc78c24b1fb9a1e9c9c0903f221a57))

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
