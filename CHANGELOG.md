# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

Ce fichier est maintenu automatiquement par
[release-please](https://github.com/googleapis/release-please) à partir des
conventional commits.

## [2.3.0](https://github.com/foXaCe/homeassistant_veolia/compare/v2.2.0...v2.3.0) (2026-07-09)


### Added

* add balance, monthly payment and next direct debit sensors ([cf14113](https://github.com/foXaCe/homeassistant_veolia/commit/cf14113e373151d834a9fdd390cb0124f572ac56))


### Documentation

* dedupe CHANGELOG 2.2.0 section ([c9a3d90](https://github.com/foXaCe/homeassistant_veolia/commit/c9a3d90fa663c95357a6607222d409084ab68b7c))

## [Unreleased]

### Fixed

- Le coordinator distingue désormais les erreurs d'authentification (déclenchent la
  ré-authentification) des erreurs transitoires réseau/API (nouvelle tentative au cycle
  suivant) — une coupure passagère ne casse plus l'intégration.
- `device_info` du switch d'alerte SMS journalière aligné sur les autres entités
  (même nom d'appareil).

### Added

- **Flux de ré-authentification** : en cas de mot de passe invalidé, HA propose de
  ressaisir le mot de passe au lieu de rester en erreur.
- **Config entry unique** (`unique_id` sur le numéro d'abonnement) : impossible d'ajouter
  deux fois le même compte.
- Nouveau capteur **index de facturation** (relevé officiel Veolia), avec les
  informations de contrat en attributs (n° compteur, mode de relevé/paiement, contrat,
  adresse de branchement, emplacement, statut, n° client, titulaire, marque).

### Changed

- Migration vers `ConfigEntry.runtime_data` (suppression de `hass.data[DOMAIN]` et du
  code mort `VeoliaData`).
- Les switches d'alerte **SMS sont désactivés par défaut** (à activer si vous configurez
  des seuils d'alerte).
- Le capteur **prochain prélèvement** affiche la date au format FR (`JJ/MM/AAAA`) ;
  la date ISO et le montant restent disponibles en attributs (`date`, `amount`).
- Le capteur **conso journalière** affiche désormais la dernière journée disponible
  (Veolia publie avec ~1 jour de retard) au lieu de rester vide ; la date du relevé est
  dans l'attribut `reading_date` et la valeur du jour courant dans l'attribut `today`.

### Added

- Nouveaux capteurs de facturation : **solde du compte** (`sensor` €),
  **mensualité** (`sensor` €) et **prochain prélèvement** (`sensor` date, avec le
  montant en attribut), issus des endpoints facturation et mensualisation.

### Security

- Le client vendoré masque désormais l'en-tête `Authorization` (token Bearer) dans
  les logs de debug (le token n'apparaît plus en clair dans `home-assistant.log`).

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
