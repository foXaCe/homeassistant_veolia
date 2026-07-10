# FAQ

## À quelle fréquence les données sont-elles mises à jour ?

Le coordinator interroge l'API Veolia toutes les 6 h. Veolia publie ses données de
consommation avec un délai minimum de 24 h.

## Quels portails sont compatibles ?

Voir [Portails Veolia supportés](../README.md#portails-veolia-supportés). Les portails
`service.eau.veolia.fr` et `espace-client.vedif.eau.veolia.fr` ne sont **pas** compatibles.

## Puis-je ajouter la consommation au dashboard Énergie ?

Oui : sélectionnez la **statistique externe** `Veolia daily consumption xxx`
(identifiant `veolia:xxx_daily_consumption`) — voir le
[README](../README.md#1-ajout-au-dashboard-énergie-de-home-assistant).
Ces statistiques sont datées du **jour de relevé réel** (Veolia publie avec
~2 jours de retard), contrairement aux capteurs qui ne changent qu'au moment
de l'actualisation. Les capteurs `sensor.veolia_*` restent utiles pour le
« live » mais ne produisent plus de statistiques long-terme.

## Les jours « estimés » par Veolia sont-ils comptés ?

Oui — les jours dont l'index est estimé sont importés tels quels (aucun trou
artificiel). La valeur du dernier jour importé est ré-importée à chaque
actualisation, elle converge donc automatiquement vers la valeur définitive.

## Les alertes envoient-elles des notifications dans Home Assistant ?

Non — les notifications d'alerte (email, SMS) sont envoyées par Veolia directement aux
coordonnées de votre compte client. L'intégration expose l'état des alertes via des
`binary_sensor` que vous pouvez utiliser dans vos automatisations.

## Comment sont gérées les mises à jour du dépôt ?

Les dépendances sont maintenues par Renovate, les releases par release-please
(voir [CONTRIBUTING.md](../CONTRIBUTING.md)).
