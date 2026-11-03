# Premier lot : protocole en lecture seule

Ce lot a été écrit directement par l'assistant, sans délégation à Copilot.
Il ne constitue pas encore une intégration Home Assistant installable.
Aucun client réseau ni aucune commande de chauffage n'est inclus.

## Sources et attribution

Les formats et la cartographie proviennent de :
https://github.com/Guillaume0385/ha-hoben-community

Fichiers examinés : protocol.md (partie accessible), myhoben.py, modbus.py,
profiles.py, v4_state.py et docs/fonctionnalites-futures.md.
Les codecs ont été réécrits ici ; les mentions MIT du projet source sont conservées.

## Implémenté et vérifié hors ligne

- Normalisation de l'identifiant Hoben, encodage OpenClient et code d'association.
- Décodage du préfixe connu OpenedClient de 48 octets.
- Sélection V4 uniquement pour product_type == 5, sans nom commercial imposé.
- Requête 04, transaction FFFF, unité 1, adresse 1024, quantité 20.
- Corrélation de la réponse : transaction, unité, fonction, longueur et quantité.
- Décodage des températures, puissance, modes et indicateurs de dérogation.
- Valeurs inconnues conservées comme inconnues ; aucun mode arbitraire substitué.
- Framing incrémental après ouverture pour Ping et DataResponseClient uniquement.
- Tests synthétiques des fragmentations, erreurs et confidentialité.

## Blocages avant connexion réelle

Les 48 octets constituent un préfixe connu, pas une longueur totale prouvée.
ResponseBuffer ne doit pas servir à deviner la fin d'OpenedClient.
Une future couche réseau doit traiter explicitement cette incertitude avant
la lecture ; une frontière ne peut pas être déduite d'une lecture socket.
Les notifications 07/1B, les fermetures et l'association réseau ne sont pas
implémentées dans ce lot. Aucun test ne contacte myhoben.fr.

## Pilotage

La roadmap source mentionne notamment le registre 1280 pour le marche/arrêt,
mais cette mention ne suffit pas à établir toute la trame et sa sémantique.
Aucune adresse d'écriture n'est déduite d'une adresse de lecture.
Marche/arrêt, température et ventilation restent à implémenter après examen
complet des écritures. Aucun bouton fictif ni contrôle silencieusement inopérant.
La commande OFF devra demander l'arrêt normal du contrôleur, jamais couper le secteur.

## Compatibilité

Objectif : tous les Hoben 230 V utilisant MyHOBEN.
Ce lot reconnaît seulement le profil V4 ; tout autre profil est refusé.
Aucun modèle réel, y compris le H7 Standard du propriétaire, n'a été testé.
La couverture des autres profils reste nécessaire pour atteindre l'objectif.

## Tests

Depuis la racine, avec Python 3.10 ou supérieur :

    python -m unittest discover -s tests -v

Aucune dépendance externe n'est nécessaire pour ce lot.
Les tests Home Assistant, Hassfest et HACS ne sont pas encore disponibles.
