# Dépannage

## La consommation du jour reste à 0

Ce n'est **pas un bug** : Veolia publie les données avec un délai minimum de 24 h
(parfois plus selon la fréquence de collecte de votre zone). L'intégration ne peut
exposer que ce que l'API Veolia a publié.

## Erreur d'authentification

1. Vérifiez vos identifiants sur le portail web Veolia directement.
2. Vérifiez que votre portail est supporté : voir
   [Portails Veolia supportés](../README.md#portails-veolia-supportés).
3. Si le problème persiste, reconfigurez l'intégration (Paramètres → Appareils et
   services → Veolia → Reconfigurer).

## Ma commune n'est pas éligible

Interrogez l'API de référence des communes (voir
[Vérifier l'éligibilité](../README.md#vérifier-léligibilité-de-votre-commune)).
Si `type_commune` = `REDIRIGE` vers un hostname inconnu, ouvrez une issue avec ce
hostname : voir [CONTRIBUTING.md](../CONTRIBUTING.md#ajouter-un-portail).

## Activer les journaux de débogage

```yaml
logger:
  default: warning
  logs:
    custom_components.veolia: debug
    veolia_api: debug
```

Ou via l'UI : Paramètres → Appareils et services → Veolia → Activer le journal de débogage.

## Ouvrir un rapport de bug

Utilisez le [modèle de bug](https://github.com/foXaCe/homeassistant_veolia/issues/new?template=bug_report.yml)
en joignant les journaux de débogage et les détails de la santé du système.
