# Fiabilité de session cloud et récupération automatique

## Retour d'expérience terrain

Le propriétaire teste actuellement l'intégration de référence
`Guillaume0385/ha-hoben-community`. Il observe une perte de mise à jour des
informations ; un rechargement manuel de l'intégration rétablit temporairement
les données.

Ce symptôme est un retour utilisateur, pas encore un diagnostic de sa cause.
Il doit être traité comme un risque prioritaire du jalon J1, avant toute
exposition de commandes.

## Hypothèses à départager

- Fermeture ou expiration de la socket TLS par le serveur, le réseau ou un
  équipement intermédiaire.
- Perte de la session applicative MyHOBEN sans fermeture TCP visible.
- Exception de lecture/décodage qui interrompt définitivement la boucle.
- Ping/Pong ou notification serveur non traités, ou framing incomplet.
- Tâche asyncio terminée, annulée ou bloquée sans supervision.
- Coordinateur Home Assistant qui ne déclenche plus de refresh après une erreur.
- Réassociation / DeviceGuid mal géré lors d'une reconnexion.

Le fait qu'un rechargement HA rétablisse les données ne permet pas à lui seul
de choisir entre ces hypothèses.

## Exigences de conception

1. **Cycle de vie supervisé** : une seule tâche de session par entrée HA ; sa
   fin inattendue doit être détectée et remonter un état indisponible.
2. **Timeouts explicites** : connexion TLS, ouverture, lecture et attente de
   réponse doivent être bornées. Une attente infinie ne doit jamais bloquer le
   coordinateur.
3. **Reconnect contrôlé** : sur EOF, timeout, erreur TLS ou erreur protocolaire,
   fermer proprement les ressources puis recréer une session complète. Ne pas
   réutiliser un writer/socket déclaré fermé.
4. **Backoff avec jitter** : délais progressifs bornés (par exemple 5, 10, 20,
   40 puis 60 s maximum), avec léger jitter ; remise à zéro après une session
   stable. Pas de boucle de reconnexion rapide.
5. **Ping/Pong** : répondre au Ping selon le protocole documenté et surveiller
   la progression de la session. Ne pas inventer de heartbeat non documenté.
6. **Framing strict** : aucune recherche arbitraire d'un octet de resynchronisation.
   Message incomplet, inconnu ou ambigu => fermer et reprendre une session
   propre ; ne jamais décoder des octets partiels comme des mesures.
7. **Erreurs isolées** : une erreur transitoire ne doit pas tuer silencieusement
   le polling futur. Les erreurs permanentes (identifiant invalide, profil
   inconnu, association requise) doivent être distinguées et signalées sans
   retry agressif.
8. **Données périmées visibles** : conserver la dernière valeur connue si utile,
   mais exposer la disponibilité et l'âge de la dernière lecture réussie.
   Marquer l'appareil indisponible lorsque les données dépassent le seuil de
   fraîcheur choisi ; ne jamais présenter une valeur périmée comme fraîche.
9. **Un seul propriétaire de session** : coordinateur et client doivent éviter
   les refresh concurrents et les connexions simultanées pour une même entrée.
10. **Arrêt propre** : au unload/reload HA, annuler la tâche, fermer le writer,
    attendre sa fermeture et éviter toute reconnexion après unload.
11. **Secrets** : ne jamais logger UserGuid, DeviceGuid, code d'association,
    trame brute ou données personnelles.
12. **Commandes** : les retries de lecture peuvent être contrôlés ; une commande
    d'écriture au résultat incertain ne doit jamais être renvoyée automatiquement.

## Télémétrie de diagnostic non sensible

Journaliser uniquement des événements structurés et expurgés :
- phase (connect, open, associate, read, decode, reconnect, unload) ;
- classe d'erreur (timeout, eof, tls, protocol, auth, unsupported_profile) ;
- nombre de reconnexions consécutives ;
- durée depuis la dernière lecture réussie ;
- profil pris en charge ou non, sans identifiant d'appareil ;
- durée de session.

Éviter les logs à chaque cycle nominal ; limiter les répétitions et utiliser
des niveaux adaptés. Aucun dump de socket ou de trame.

## Tests de non-régression requis

- fermeture distante propre (EOF) puis reconnexion ;
- timeout de lecture puis reconnexion ;
- reset TLS / erreur réseau puis reconnexion ;
- réponse fragmentée sur plusieurs lectures ;
- Ping reçu et Pong émis ;
- message inconnu ou framing invalide => fermeture, sans resynchronisation hasardeuse ;
- erreur de décodage ponctuelle : la tâche de supervision reste vivante ;
- backoff progressif et borné, sans tempête de reconnexion ;
- reset du backoff après lecture réussie stable ;
- unload pendant une attente : socket fermée, tâche terminée, aucune reconnexion ;
- plusieurs refresh simultanés : une seule lecture réseau ;
- disponibilité et timestamp de dernière donnée cohérents ;
- identifiants et données brutes absents des logs.

## Observation demandée pendant le test de l'intégration de référence

Lors de la prochaine perte de données, avant de recharger l'intégration, relever
si possible :
- heure approximative du début de la panne ;
- état de l'intégration dans Paramètres > Appareils et services ;
- messages de journal liés à `hoben` autour de cette heure ;
- si l'interface affiche une valeur figée ou « indisponible » ;
- si MyHOBEN sur téléphone continue à actualiser les mêmes informations.

Ne pas publier de GUID, code d'association, QR code, adresse MAC ou trame brute.
