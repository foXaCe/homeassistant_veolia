# FAQ

## À quelle fréquence les données sont-elles mises à jour ?

Le coordinator interroge l'API Veolia toutes les 6 h. Veolia publie ses données de
consommation avec un délai minimum de 24 h.

## Quels portails sont compatibles ?

Voir [Portails Veolia supportés](../README.md#portails-veolia-supportés). Les portails
`service.eau.veolia.fr` et `espace-client.vedif.eau.veolia.fr` ne sont **pas** compatibles.

## Puis-je ajouter la consommation au dashboard Énergie ?

Oui : utilisez le sensor `sensor.veolia_xxx_conso_journaliere` (voir le
[README](../README.md#1-ajout-au-dashboard-énergie-de-home-assistant)).
N'utilisez pas le sensor d'index compteur (décalage de dates).

## Les alertes envoient-elles des notifications dans Home Assistant ?

Non — les notifications d'alerte (email, SMS) sont envoyées par Veolia directement aux
coordonnées de votre compte client. L'intégration expose l'état des alertes via des
`binary_sensor` que vous pouvez utiliser dans vos automatisations.

## Comment sont gérées les mises à jour du dépôt ?

Les dépendances sont maintenues par Renovate, les releases par release-please
(voir [CONTRIBUTING.md](../CONTRIBUTING.md)).
