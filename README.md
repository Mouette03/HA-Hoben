# HA-Hoben

Intégration communautaire non officielle Home Assistant destinée aux poêles Hoben 230 V utilisant MyHOBEN.

## État du projet

Projet en préparation. Aucune intégration installable et aucune commande de pilotage ne sont encore disponibles dans ce dépôt. La compatibilité avec tous les modèles constitue un objectif, pas une validation acquise.

## Périmètre

- Cibler tous les Hoben 230 V utilisant le même système MyHOBEN, sans verrouillage sur un modèle commercial.
- Détecter le profil protocolaire lors de la connexion.
- Séparer les variantes de protocole lorsque nécessaire.
- Prévoir la lecture des températures et de l'état, puis le marche/arrêt, la consigne et la ventilation après vérification des commandes.
- Refuser les écritures sur un profil inconnu.
- Distinguer modèles ciblés, profils compatibles et appareils effectivement testés.
- Les modèles 24 V/HB Zen restent hors du périmètre initial tant que leur protocole n'est pas vérifié.

## Premier appareil de validation prévu

Hoben H7 Standard du propriétaire. Informations relevées sur sa photo :

- Logiciel : Hoben rv2.8.4 - BSP 1.5.
- Matériel : ESvs2.90 - vh4.80.
- Configuration : DH7v280.01 - TBH7v252.

Ces informations ne déterminent pas à elles seules le profil MyHOBEN. Aucun test sur cet appareil n'a encore été réalisé par le projet.

## Base d'étude

https://github.com/Guillaume0385/ha-hoben-community

Étudier le code et la documentation du protocole. Respecter la licence et conserver les mentions requises pour toute reprise de code. Ne pas supposer qu'une commande documentée a été validée sur tous les modèles.

## Principes

- Lecture seule par défaut pendant la validation.
- Configuration depuis l'interface Home Assistant et installation HACS comme objectifs.
- Tests hors ligne avant tout essai réel explicitement autorisé.
- Ne pas inventer de commandes, registres ou plages de valeurs.
- Distinguer consigne permanente et dérogation temporaire.
- Pas de répétition automatique d'une commande dont le résultat est incertain.
- Aucun accès aux paramètres installateur ou de combustion.
- Ne pas publier d'identifiants Hoben, de codes d'association, de QR codes ou d'adresses MAC.
- Conserver la régulation et les sécurités natives du poêle.

Projet non affilié à Hoben, Inovalp, Home Assistant ou HACS.
