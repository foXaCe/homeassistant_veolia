# Configuration

L'intégration se configure entièrement via l'interface (config flow), aucun YAML n'est requis.

## Ajout de l'intégration

1. Paramètres → Appareils et services → Ajouter une intégration → « Veolia »
2. **Commune** : renseignez votre commune / code postal — l'intégration détermine le portail Veolia à utiliser
3. **Portail** : confirmez le portail détecté
4. **Identifiants** : email et mot de passe de votre compte client Veolia

## Entités créées

| Plateforme      | Entités                                                        |
| --------------- | -------------------------------------------------------------- |
| `sensor`        | Consommation journalière/mensuelle, index, date de relève      |
| `binary_sensor` | État des alertes de consommation                               |
| `switch`        | Notifications SMS des alertes                                  |
| `text`          | Seuils d'alertes (journalier, mensuel, logement vide)          |

## Configuration des alertes

Voir le [README](../README.md#configuration-des-alertes) pour le détail des trois types
d'alertes (journalière, mensuelle, logement vide) et de leurs unités.

## Dashboard Énergie

Voir le [README](../README.md#visualisation-des-données-de-consommation).
