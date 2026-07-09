# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

Ce fichier est maintenu automatiquement par
[release-please](https://github.com/googleapis/release-please) à partir des
conventional commits.

## [Unreleased]

### Added

- Prise en charge du portail **Eau de Perpignan Méditerranée Métropole** (`www.ea-pm.fr`).

### Changed

- Le client `veolia_api` pointe désormais sur le fork
  [foXaCe/veolia-api](https://github.com/foXaCe/veolia-api) (v2.2.0), qui résout le
  `client_id` **et** le backend de données par portail (au lieu d'un backend codé en
  dur), permettant les portails à backend dédié comme `www.ea-pm.fr`.
- Bootstrap complet du dépôt : CI, release-please, Renovate, sécurité, documentation.

## [2.1.0] - 2026-07-09

Version courante au moment du bootstrap du dépôt (voir
[l'historique amont](https://github.com/foXaCe/homeassistant_veolia/commits/main)
pour le détail des versions antérieures).
