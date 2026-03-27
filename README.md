# Bot Discord NovaForge

Bot Discord en Python pour :

- afficher un panel ticket avec menu déroulant
- créer un ticket privé selon la catégorie choisie
- fermer un ticket avec un bouton ou une commande
- claim un ticket côté staff
- envoyer un transcript lors de la fermeture
- envoyer des logs dans un salon dédié
- ajouter, retirer ou renommer un ticket via commandes
- donner automatiquement un rôle à l'arrivée sur le serveur
- publier des avis clients avec note étoilée
- poser un formulaire différent selon chaque catégorie de ticket
- gérer blacklist, avertissements et ban staff
- envoyer le règlement dans le salon prévu
- répondre automatiquement dans les tickets avec une IA optionnelle

## IDs déjà configurés

- Salon du panel ticket : `1484300903010799777`
- Catégorie ticket Acheter un site : `1484300828847247410`
- Catégorie ticket Commande via internet : `1484300832911528077`
- Catégorie ticket Autre / aide : `1484300830919098581`
- Salon règlement : `1484300877316755626`
- Rôle automatique à l'arrivée : `1484300777366225056`
- Salon des avis : `1484300896052707529`

## Fichiers

- `main.py` : le bot complet
- `.env.example` : modèle de configuration
- `requirements.txt` : dépendances Python

## Installation

1. Ouvre le dossier dans VS Code.
2. Crée un fichier `.env` à partir de `.env.example`.
3. Remplis au minimum `DISCORD_TOKEN`.
4. Optionnel :
   - `GUILD_ID` pour synchroniser plus vite les commandes slash.
   - `SUPPORT_ROLE_ID` pour donner accès aux tickets au rôle support.
   - `RULE_ACCEPT_ROLE_ID` pour donner un rôle après acceptation du règlement.
   - `LOG_CHANNEL_ID` pour recevoir les logs et transcripts des tickets.
   - `ENABLE_TICKET_AI=true` pour activer les réponses IA dans les tickets.
   - `OPENAI_API_KEY` pour brancher l'assistant IA.
   - `OPENAI_MODEL` si tu veux changer de modèle.
5. Dans le terminal VS Code :

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python3 main.py
```

## Permissions du bot

Le bot doit avoir au minimum :

- Voir les salons
- Gérer les salons
- Envoyer des messages
- Gérer les messages
- Lire l’historique des messages
- Lire le contenu des messages si tu actives l'IA ticket
- Intégrer des liens
- Joindre des fichiers
- Gérer les rôles si tu utilises `RULE_ACCEPT_ROLE_ID`
- et accès au salon logs si tu configures `LOG_CHANNEL_ID`

Si tu utilises l'IA ticket, active aussi l'intent **Message Content** dans le portail développeur Discord du bot.

## Utilisation

1. Lance le bot.
2. Dans ton serveur Discord, utilise la commande `/setup`.
3. Le bot va envoyer ou mettre à jour :
   - le panel ticket dans le salon prévu
   - le règlement dans le salon prévu
4. Si `LOG_CHANNEL_ID` est rempli :
   - chaque ouverture, claim et fermeture sera loggé
   - le transcript texte sera envoyé à la fermeture

## Fonctionnement du panel

Le menu affiche :

- Acheter un site
- Commande via internet
- Autre (aide)

Quand un membre choisit une option :

- un formulaire dédié à la catégorie s'ouvre d'abord
- un ticket privé est créé dans la catégorie correspondante
- le membre reçoit un message privé dans le salon
- un bouton `Claim` est disponible pour le staff
- un bouton `Fermer` est disponible
- le ticket reçoit un numéro propre comme `achat-001`
- les réponses du formulaire sont postées dans le ticket sous forme de brief

Formulaires actuels :

- `Acheter un site` : type de site, nom du site, domaine, budget, détails
- `Commande via internet` : service demandé, lien/référence, paiement, délai, détails
- `Autre (aide)` : sujet, plateforme, urgence, détails

Assistant IA ticket :

- si `OPENAI_API_KEY` est configuré, le bot peut répondre dans les tickets
- l'IA répond seulement au créateur du ticket
- elle se déclenche quand le client pose une vraie question, mentionne le bot ou répond au bot
- elle aide à clarifier la demande mais ne remplace pas une validation ou un devis du staff

## Commandes disponibles

- `/setup` : envoie ou met à jour le panel et le règlement
- `/close` : ferme le ticket courant
- `/claim` : claim ou libère le ticket courant
- `/add @membre` : ajoute un membre au ticket
- `/remove @membre` : retire un membre du ticket
- `/rename nom` : renomme le ticket courant
- `/avis` : publie un avis client avec note de 1 à 5
- `/blacklist @membre raison` : empêche un membre d’ouvrir des tickets
- `/unblacklist @membre` : retire la blacklist ticket
- `/warn @membre raison` : ajoute un avertissement
- `/warnings @membre` : affiche les avertissements
- `/clearwarnings @membre` : efface les avertissements
- `/ban @membre raison` : ban du serveur
- `/unban user_id raison` : unban du serveur

## Notes

- Sans `SUPPORT_ROLE_ID`, seuls le client, le bot et les admins du serveur verront facilement le ticket.
- Un seul salon logs suffit largement. Mets simplement son ID dans `LOG_CHANNEL_ID`.
- La commande `/setup` republie maintenant le panel et le règlement proprement pour éviter de garder une ancienne version active.
- Si tu veux aller encore plus loin ensuite, je peux te faire une version avec base de données, blacklist, fermeture confirmée et interface encore plus premium.
