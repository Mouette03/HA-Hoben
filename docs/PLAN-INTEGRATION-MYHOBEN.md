# Plan d'intégration MyHOBEN — H7 Standard de référence

## Décision de périmètre

Le premier appareil de validation est le Hoben H7 Standard décrit dans le README du dépôt HA-Hoben :

- Logiciel : Hoben rv2.8.4 — BSP 1.5
- Matériel : ESvs2.90 — vh4.80
- Configuration : DH7v280.01 — TBH7v252

L'intégration cible le service cloud MyHOBEN. Elle ne communique pas directement avec le réseau local du poêle.

Le H7 est un appareil de référence pour les essais, pas une preuve que son protocole est V4. Le profil doit être détecté à partir de la réponse OpenedClient. Aucun modèle commercial ne doit être utilisé seul pour sélectionner le décodeur.

## État des dépôts au démarrage

Le dépôt HA-Hoben contient actuellement son README de cadrage, mais pas encore le paquet `custom_components/hoben/`, les tests ou les métadonnées HACS. La branche de travail est donc une base de développement, pas une intégration installable.

Le dépôt communautaire `Guillaume0385/ha-hoben-community` apporte une implémentation de référence documentée :

- client MyHOBEN TLS vers `myhoben.fr:465`, avec validation TLS normale ;
- ouverture de session via l'Identifiant HOBEN (UserGuid), puis attribution et persistance du DeviceGuid ;
- gestion explicite de la demande d'autorisation ;
- sélection dynamique du profil et refus des profils non pris en charge ;
- lecture V4 des 20 registres à partir de l'adresse 1024 ;
- décodeur V4 indépendant et entités Home Assistant en lecture seule ;
- tests hors ligne et diagnostics expurgés.

La documentation amont rapporte des validations réelles sur un Hoben Osmose de référence. Ces validations ne prouvent pas la compatibilité du H7 Standard. Les fichiers et changements repris devront conserver les mentions de copyright et la licence MIT du projet d'origine, conformément à ses conditions.

## Architecture visée

1. Config flow Home Assistant demandant l'Identifiant HOBEN.
2. Client cloud MyHOBEN asynchrone, sans secret dans les logs.
3. Gestion du DeviceGuid attribué par le serveur dans les données privées de l'entrée HA.
4. Détection dynamique du profil ; V4 uniquement tant qu'un autre profil n'a pas de spécification et de tests.
5. Coordinateur HA pour les lectures et la disponibilité des entités.
6. Plateformes sensor/binary_sensor/select/climate/switch/number uniquement lorsque chaque capacité est justifiée.
7. Tests unitaires simulant TLS, réponses serveur, erreurs, annulation et déchargement HA.

## Jalons

### J1 — Portage sûr de la lecture seule

- Reprendre le client, les codecs, les exceptions et le décodeur nécessaires depuis le projet communautaire.
- Respecter la licence MIT et documenter la provenance des fichiers repris.
- Ajouter manifest, config flow, coordinator, plateformes et traductions.
- Garder une cadence de lecture prudente et un cycle de vie réseau borné.
- Ne publier aucune identité, trame brute ou valeur privée dans les diagnostics.
- Refuser les profils inconnus et les réponses ambiguës.

### J2 — Validation sur le H7 Standard

Avant toute activation du contrôle :
- effectuer une association MyHOBEN explicite avec l'accord du propriétaire ;
- confirmer le profil réellement annoncé par le serveur ;
- comparer en privé les valeurs HA et MyHOBEN au même instant ;
- vérifier les températures, consigne lue, puissance, mode, ventilation et état ;
- consigner uniquement des métadonnées expurgées et le résultat des tests.

Si le H7 n'annonce pas V4, ne pas forcer le décodeur V4 : suspendre l'exposition des mesures non prises en charge et documenter le profil à étudier.

### J3 — Étude du contrôle, séparée de la lecture

Le contrôle n'est pas implémenté dans le projet de départ et ne doit pas être déduit de la seule présence de registres lisibles. Avant d'exposer une commande, il faudra établir séparément :

- le type de message et la séquence d'autorisation du contrôle distant ;
- les commandes et paramètres effectivement utilisés par MyHOBEN ;
- les plages, unités, états d'acquittement et erreurs ;
- les conséquences d'un timeout où le résultat de commande est incertain ;
- les différences éventuelles entre profils et versions.

Aucune écriture Modbus, commande de combustion, paramètre installateur ou réglage de sécurité ne sera ajoutée par supposition. Une commande ne sera exposée qu'après preuve documentaire et validation contrôlée sur l'appareil de référence, sans contourner les sécurités natives.

## Sécurité et critères de refus

- TLS et validation du certificat/nom d'hôte obligatoires.
- Aucun repli en clair.
- UserGuid, DeviceGuid et code d'autorisation considérés comme secrets.
- Aucun identifiant, QR code, trame ou valeur de mesure dans les logs publics.
- Pas de retry automatique d'une commande dont l'exécution est incertaine.
- Lecture seule par défaut jusqu'à validation explicite du jalon J3.
- Pas d'accès aux réglages installateur ou de combustion.
- Le serveur MyHOBEN et les protections natives du poêle restent maîtres de la communication et de la sécurité.

## Critère de première version

La première version installable vise une intégration cloud MyHOBEN en lecture seule, testée sur le H7 Standard si le profil est pris en charge. Le pilotage viendra dans une version distincte après validation du protocole de commande.