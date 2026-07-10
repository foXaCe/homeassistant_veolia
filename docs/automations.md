# Exemples d'automatisations

Quelques automatisations prêtes à adapter. Les `entity_id` contiennent votre
identifiant d'abonnement Veolia : remplacez `123456` par le vôtre (visible dans
**Paramètres → Appareils et services → Veolia**).

## Être notifié d'une surconsommation journalière

Le capteur binaire d'alerte journalière passe à `on` lorsque Veolia détecte un
dépassement du seuil que vous avez configuré (entité
`text.veolia_123456_seuil_alerte_journaliere_en_l`).

```yaml
automation:
  - alias: "Eau — alerte surconsommation journalière"
    triggers:
      - trigger: state
        entity_id: binary_sensor.veolia_123456_alerte_conso_journaliere
        to: "on"
    actions:
      - action: notify.mobile_app_votre_telephone
        data:
          title: "💧 Surconsommation d'eau"
          message: >
            Consommation d'hier :
            {{ states('sensor.veolia_123456_conso_journaliere') }} L
            — vérifiez qu'aucun robinet ne fuit.
```

## Activer l'alerte « logement vide » pendant les vacances

L'interrupteur `switch.veolia_123456_alerte_logement_vide` demande à Veolia de
vous prévenir de **toute** consommation — utile pour détecter une fuite en
votre absence.

```yaml
automation:
  - alias: "Eau — mode logement vide au départ"
    triggers:
      - trigger: state
        entity_id: group.famille
        to: "not_home"
        for: "24:00:00"
    actions:
      - action: switch.turn_on
        target:
          entity_id: switch.veolia_123456_alerte_logement_vide

  - alias: "Eau — mode logement vide au retour"
    triggers:
      - trigger: state
        entity_id: group.famille
        to: "home"
    actions:
      - action: switch.turn_off
        target:
          entity_id: switch.veolia_123456_alerte_logement_vide
```

## Ajuster le seuil d'alerte selon la saison

Un arrosage estival justifie un seuil plus haut ; resserrez-le en hiver.

```yaml
automation:
  - alias: "Eau — seuil journalier saisonnier"
    triggers:
      - trigger: calendar
        entity_id: calendar.saisons
        event: start
    actions:
      - action: text.set_value
        target:
          entity_id: text.veolia_123456_seuil_alerte_journaliere_en_l
        data:
          value: >
            {{ '600' if 'été' in trigger.calendar_event.summary | lower
               else '350' }}
```

## Être prévenu avant le prochain prélèvement

```yaml
automation:
  - alias: "Eau — rappel de prélèvement à venir"
    triggers:
      - trigger: time
        at: "09:00:00"
    conditions:
      - condition: template
        value_template: >
          {{ state_attr('sensor.veolia_123456_prochain_prelevement', 'date')
             == (now().date() + timedelta(days=2)) | string }}
    actions:
      - action: notify.mobile_app_votre_telephone
        data:
          message: >
            Prélèvement Veolia de
            {{ state_attr('sensor.veolia_123456_prochain_prelevement', 'amount') }} €
            dans 2 jours.
```

## Suivi long terme (dashboard Énergie)

La consommation est aussi publiée sous forme de **statistiques externes**
(`veolia:123456_daily_consumption`, `veolia:123456_monthly_consumption`,
`veolia:123456_index`), directement sélectionnables dans le dashboard Énergie,
section Eau — voir le [README](../README.md#1-ajout-au-dashboard-énergie-de-home-assistant).
