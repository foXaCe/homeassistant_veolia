# Veolia Eau

Intégration Home Assistant pour Veolia Eau (portail https://www.eau.veolia.fr).

## Fonctionnalités

- Consommation d'eau journalière et mensuelle
- Index de consommation d'eau
- Configuration des seuils d'alertes de consommation (journalière, mensuelle, logement vide)
- État des alertes de consommation
- Date de la dernière relève
- Intégration native au dashboard Énergie de Home Assistant

> Les données sont mises à jour toutes les 6 h par défaut (intervalle configurable de 1 à 24 h
> dans les options). Veolia publie la consommation avec un délai minimum de 24 h. L'historique
> long terme est publié sous forme de statistiques externes datées `veolia:*` (voir le README
> pour la configuration du dashboard Énergie).

## Configuration

Paramètres → Appareils et services → Ajouter une intégration → « Veolia », puis renseignez
les identifiants de votre compte client Veolia.
