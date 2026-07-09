<a href=""><img src="images/veolialogo.png"></a>

[![GitHub Release][releases-shield]][releases]
[![hacs][hacsbadge]][hacs]
[![CI][ci-shield]][ci]
[![Hassfest][hassfest-shield]][hassfest]
[![License][license-shield]](LICENSE)
[![Project Maintenance][maintainer-shield]][maintainer]

_Intégration Home Assistant pour Veolia Eau (compatible avec https://www.eau.veolia.fr)._

> ### Portails compatibles : voir [Portails Veolia supportés](#portails-veolia-supportés)
>
> ### N'est PAS compatible avec : https://service.eau.veolia.fr & https://espace-client.vedif.eau.veolia.fr

---

## Informations disponibles

**Cette intégration configurera les plateformes suivantes.**

| Plateforme      | Description                                         |
| --------------- | --------------------------------------------------- |
| `sensor`        | Affiche les informations de l'API Veolia            |
| `switch`        | Switch d'activation/désactivation des alertes conso |
| `text`          | Saisie des valeurs de réglages des alertes          |
| `binary_sensor` | Affiche l'état des alertes conso                    |

### Données disponibles

- Consommation d'eau (journalière, mensuelle)
- Index de consommation d'eau
- Seuils d'alertes de consommation d'eau
- État des alertes de consommation d'eau
- Date de la dernière relève de consommation d'eau

> #### **Note :** Les données de l'intégration sont mises à jour toutes les 12h.

### Capteurs

<a href=""><img src="images/capteurs.png" alt="Capteurs Veolia dans Home Assistant"></a>

### Contrôles

<a href=""><img src="images/controles.png" alt="Contrôles des alertes Veolia"></a>

### Configuration des alertes

L'intégration Veolia permet de configurer des alertes de consommation d'eau pour surveiller votre utilisation
quotidienne et mensuelle, et même pour détecter une fuite si vous n'êtes pas chez vous.

Les alertes sont activées ou désactivées en renseignant les champs seuils d'alertes (0 = désactivé, >0 = activé).

Il existe 3 types d'alertes :

- Alerte journalière
  - L'alerte journalière se déclenche si votre consommation d'eau quotidienne dépasse un certain seuil **cette valeur est en litres, le minimum est de 100 litres.**
- Alerte mensuelle
  - L'alerte mensuelle se déclenche si votre consommation d'eau mensuelle dépasse un certain seuil **cette valeur est en mètres cubes, le minimum est de 1 m³**.
- Alerte logement « vide »
  - L'alerte logement vide se déclenche si une consommation d'eau est détectée alors que vous n'êtes pas chez vous.

Informations supplémentaires :

> Les notifications d'alerte sont envoyées par Veolia directement par email et par SMS (aux coordonnées de contact renseignées dans votre compte Veolia).

> Il n'est pas possible de désactiver les notifications d'alerte par email, mais vous pouvez choisir d'activer ou non les notifications par SMS, uniquement si un seuil est renseigné.

### Visualisation des données de consommation

L'intégration Veolia permet de visualiser les données de consommation d'eau en natif dans Home Assistant. Elle re-télécharge l'historique du mois en cours depuis Veolia et met à jour la base de données Home Assistant.

> Pour visualiser les informations à la bonne date, il est nécessaire d'utiliser le sensor de consommation journalière (l'utilisation du sensor index compteur générera un décalage dans les dates).

#### 1. Ajout au dashboard énergie de Home Assistant

<a href=""><img src="images/dashboard_eau.png" alt="Dashboard énergie eau"></a>

Pour ajouter la consommation d'eau au dashboard énergie de Home Assistant, allez dans `Énergie` -> crayon en haut à droite -> `Eau` -> `Ajouter une consommation d'eau` -> Dans le champ `Consommation d'eau` choisissez `sensor.veolia_xxx_conso_journaliere`

<a href=""><img src="images/consommation.png" alt="Consommation d'eau"></a>

#### 2. Ajout d'une carte de consommation d'eau journalière

> [!WARNING]
>
> Pourquoi le sensor `veolia_xxx_conso_journaliere` reste à 0 ? Je n'arrive pas à avoir ma consommation du jour ?
>
> C'est une contrainte technique de Veolia, PAS UN BUG !
>
> Veolia traite et publie les données de consommation avec un délai de minimum 24 h, parfois beaucoup plus en fonction de la fréquence de collecte de la zone.
> L'intégration ne peut retourner que ce que l'API Veolia expose, elle ne peut pas récupérer des données que Veolia n'a pas encore publiées...
>
> Le seul usage de ce sensor est l'usage avec une carte graphique comme décrit ci-dessous :

<a href=""><img src="images/historique.png" alt="Historique de consommation"></a>

Pour ajouter la carte de consommation d'eau journalière, sur votre dashboard, cliquez sur `Ajouter une carte` puis sélectionnez `Graphique des statistiques` et choisissez l'entité `sensor.veolia_xxx_conso_journaliere`, configurez la carte comme l'exemple ci-dessous :

<a href=""><img src="images/config_carte.png" alt="Configuration de la carte"></a>

> #### **Note :** La carte Graphique des statistiques ne fonctionnera qu'avec le sensor `sensor.veolia_xxx_conso_journaliere`

## Vérifier l'éligibilité de votre commune

Avant d'installer l'intégration, vous pouvez vérifier si votre commune est prise en charge en interrogeant l'API Veolia depuis votre navigateur ou avec `curl` :

```text
https://prd-ael-sirius-refcommunes.istefr.fr/communes-nationales?q=VOTRE_CODE_POSTAL
```

Dans le résultat JSON, cherchez votre commune et examinez le champ `type_commune` :

| Valeur `type_commune`         | Éligibilité                                  |
| ----------------------------- | -------------------------------------------- |
| `NON_REDIRIGE`                | ✅ Compatible — portail `eau.veolia.fr`      |
| `REDIRIGE` (hostname connu)   | ✅ Compatible — portail alternatif supporté  |
| `REDIRIGE` (hostname inconnu) | ❌ Non supporté — portail non encore intégré |
| `NON_DESSERVIE`               | ❌ Veolia ne dessert pas cette commune       |

## Portails Veolia supportés

| Hostname                          | Description               |
| --------------------------------- | ------------------------- |
| `eau.veolia.fr`                   | Veolia France (national)  |
| `eaudetm.monespace.eau.veolia.fr` | Eau de Toulouse Métropole |

Votre portail n'est pas géré ? Voir [CONTRIBUTING.md](CONTRIBUTING.md#ajouter-un-portail)

## Installation

### Via [HACS](https://hacs.xyz/) (recommandé)

**Cliquez ici :**

[![Open your Home Assistant instance and open the repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg?style=flat-square)](https://my.home-assistant.io/redirect/hacs_repository/?owner=foXaCe&repository=homeassistant_veolia&category=integration)

**ou suivez ces étapes :**

1. Ouvrez HACS (Home Assistant Community Store)
2. Cliquez sur les trois points en haut à droite
3. Cliquez sur `Dépôts personnalisés`
4. Dans le champ `Dépôt` entrez https://github.com/foXaCe/homeassistant_veolia/
5. Dans le champ `Type` sélectionnez `Intégration`
6. Cliquez sur `Ajouter`
7. Recherchez `Veolia` dans la liste des intégrations
8. Installez l'intégration
9. Redémarrez Home Assistant
10. Ouvrez Paramètres -> Intégrations -> Ajouter une intégration -> recherchez `Veolia`
11. Suivez les instructions pour configurer l'intégration

### Manuellement

1. Copiez le dossier `custom_components/veolia` dans le dossier `custom_components` de votre configuration Home Assistant.
2. Redémarrez Home Assistant
3. Ouvrez Paramètres -> Intégrations -> Ajouter une intégration -> recherchez `Veolia`
4. Suivez les instructions pour configurer l'intégration

## Bug et demande de fonctionnalités

- [Ouvrir une issue](https://github.com/foXaCe/homeassistant_veolia/issues)

## API Veolia

Cette intégration utilise le client API Python [veolia-api](https://github.com/Jezza34000/veolia-api).

## Contribuer

Voir [CONTRIBUTING.md](CONTRIBUTING.md).

## Credits

- [@Jezza34000](https://github.com/Jezza34000) — auteur original de cette intégration et du client [veolia-api](https://github.com/Jezza34000/veolia-api).
- [@Ludeeus](https://github.com/ludeeus) — le modèle de code de cette intégration a principalement été tiré de son blueprint.

## License

[MIT](LICENSE)

<!-- Badges links -->

[releases-shield]: https://img.shields.io/github/v/release/foXaCe/homeassistant_veolia.svg?style=for-the-badge
[releases]: https://github.com/foXaCe/homeassistant_veolia/releases
[hacsbadge]: https://img.shields.io/badge/HACS-Custom-orange.svg?style=for-the-badge
[hacs]: https://hacs.xyz
[ci-shield]: https://img.shields.io/github/actions/workflow/status/foXaCe/homeassistant_veolia/ci.yml?branch=main&style=for-the-badge&label=CI
[ci]: https://github.com/foXaCe/homeassistant_veolia/actions/workflows/ci.yml
[hassfest-shield]: https://img.shields.io/github/actions/workflow/status/foXaCe/homeassistant_veolia/hassfest.yml?branch=main&style=for-the-badge&label=hassfest
[hassfest]: https://github.com/foXaCe/homeassistant_veolia/actions/workflows/hassfest.yml
[license-shield]: https://img.shields.io/github/license/foXaCe/homeassistant_veolia.svg?style=for-the-badge
[maintainer-shield]: https://img.shields.io/badge/maintainer-%40foXaCe-blue.svg?style=for-the-badge
[maintainer]: https://github.com/foXaCe
