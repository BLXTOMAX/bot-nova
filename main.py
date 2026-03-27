import asyncio
import io
import json
import logging
import os
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

import discord
from discord import app_commands
from discord.ext import commands
from dotenv import load_dotenv


load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger("novaforge-ticket-bot")


BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
STATE_FILE = DATA_DIR / "messages.json"
ASSETS_DIR = BASE_DIR / "assets"
TICKET_LOGO_PATH = ASSETS_DIR / "ticket-logo.png"
TICKET_BANNER_PATH = ASSETS_DIR / "ticket-banner.png"

PANEL_CHANNEL_ID = 1484300903010799777
RULES_CHANNEL_ID = 1484300877316755626
AUTO_ROLE_ID = 1484300777366225056
REVIEW_CHANNEL_ID = 1484300896052707529

COMPONENT_PREFIX = "novaforge_v3"
PANEL_SELECT_ID = f"{COMPONENT_PREFIX}_ticket_select"
RULES_ACCEPT_ID = f"{COMPONENT_PREFIX}_rules_accept"
TICKET_CLAIM_ID = f"{COMPONENT_PREFIX}_ticket_claim"
TICKET_CLOSE_ID = f"{COMPONENT_PREFIX}_ticket_close"

AI_TRIGGER_PREFIXES = (
    "ia ",
    "bot ",
    "question ",
    "j'ai une question",
    "jai une question",
)
AI_GREETING_PREFIXES = (
    "bonjour",
    "salut",
    "bonsoir",
    "hello",
    "cc",
)
MAX_AI_HISTORY_MESSAGES = 12

DEFAULT_COUNTERS = {
    "acheter_site": 0,
    "commande_internet": 0,
    "autre_aide": 0,
}

DEFAULT_BLACKLIST: Dict[str, Dict[str, str]] = {}
DEFAULT_WARNINGS: Dict[str, List[Dict[str, str]]] = {}
DEFAULT_TICKET_BRIEFS: Dict[str, Dict[str, object]] = {}

TICKET_CATEGORIES = {
    "acheter_site": {
        "label": "Acheter un site",
        "emoji": "\U0001f6d2",
        "category_id": 1484300828847247410,
        "description": "Tu veux acheter un site ou discuter d'une offre.",
        "prefix": "achat",
        "brief_title": "Brief site web",
        "ai_focus": (
            "Aide le client a clarifier son besoin de site web, son domaine, ses pages, ses options "
            "et les informations utiles avant intervention humaine."
        ),
        "form": {
            "title": "Achat de site",
            "fields": [
                {
                    "label": "Quel type de site veux-tu ?",
                    "brief_label": "Type de site",
                    "placeholder": "Vitrine, e-commerce, portfolio...",
                    "max_length": 100,
                    "required": True,
                },
                {
                    "label": "Nom du site ou de la marque",
                    "brief_label": "Nom du site",
                    "placeholder": "Nom du projet ou de l'entreprise",
                    "max_length": 100,
                    "required": False,
                },
                {
                    "label": "Nom de domaine souhaite",
                    "brief_label": "Nom de domaine",
                    "placeholder": "monsite.fr, pas encore choisi...",
                    "max_length": 100,
                    "required": False,
                },
                {
                    "label": "Budget estime",
                    "brief_label": "Budget",
                    "placeholder": "150EUR, 500EUR, a discuter...",
                    "max_length": 100,
                    "required": False,
                },
                {
                    "label": "Details du projet",
                    "brief_label": "Details",
                    "placeholder": "Pages, style, fonctions, delai, exemples...",
                    "style": discord.TextStyle.paragraph,
                    "max_length": 1000,
                    "required": True,
                },
            ],
        },
    },
    "commande_internet": {
        "label": "Commande via internet",
        "emoji": "\U0001f310",
        "category_id": 1484300832911528077,
        "description": "Tu as une commande en ligne, une preuve de paiement ou un suivi.",
        "prefix": "commande",
        "brief_title": "Brief commande",
        "ai_focus": (
            "Aide le client a preciser sa commande, le lien concerne, l'etat du paiement, le delai "
            "et les preuves utiles."
        ),
        "form": {
            "title": "Commande internet",
            "fields": [
                {
                    "label": "Quel service veux-tu commander ?",
                    "brief_label": "Service demande",
                    "placeholder": "Site, design, automatisation, autre...",
                    "max_length": 100,
                    "required": True,
                },
                {
                    "label": "Lien ou reference utile",
                    "brief_label": "Lien / reference",
                    "placeholder": "Produit, site, inspiration, panier...",
                    "max_length": 200,
                    "required": False,
                },
                {
                    "label": "Paiement deja effectue ?",
                    "brief_label": "Paiement",
                    "placeholder": "Oui, non, en attente, preuve dispo...",
                    "max_length": 100,
                    "required": False,
                },
                {
                    "label": "Delai souhaite",
                    "brief_label": "Delai",
                    "placeholder": "Aujourd'hui, cette semaine, pas urgent...",
                    "max_length": 100,
                    "required": False,
                },
                {
                    "label": "Explique ta demande",
                    "brief_label": "Details",
                    "placeholder": "Quantite, besoin, probleme, precision utile...",
                    "style": discord.TextStyle.paragraph,
                    "max_length": 1000,
                    "required": True,
                },
            ],
        },
    },
    "autre_aide": {
        "label": "Autre (aide)",
        "emoji": "\u2753",
        "category_id": 1484300830919098581,
        "description": "Tu as besoin d'aide ou tu veux poser une autre question.",
        "prefix": "aide",
        "brief_title": "Brief assistance",
        "ai_focus": (
            "Aide le client a formuler son probleme, son contexte, son urgence et les infos qui "
            "permettront au staff de repondre rapidement."
        ),
        "form": {
            "title": "Demande d'aide",
            "fields": [
                {
                    "label": "Sujet principal",
                    "brief_label": "Sujet",
                    "placeholder": "Bug, conseil, question, SAV...",
                    "max_length": 100,
                    "required": True,
                },
                {
                    "label": "Service ou plateforme concerne",
                    "brief_label": "Plateforme",
                    "placeholder": "Discord, site, commande, compte...",
                    "max_length": 100,
                    "required": False,
                },
                {
                    "label": "Niveau d'urgence",
                    "brief_label": "Urgence",
                    "placeholder": "Urgent, aujourd'hui, cette semaine...",
                    "max_length": 100,
                    "required": False,
                },
                {
                    "label": "Decris exactement le besoin",
                    "brief_label": "Details",
                    "placeholder": "Contexte, erreurs, captures, attente...",
                    "style": discord.TextStyle.paragraph,
                    "max_length": 1000,
                    "required": True,
                },
            ],
        },
    },
}

RULES_TEXT = """# Règlement NovaForge
Merci de lire et respecter ce règlement avant d’accéder au serveur.

**Respect**
• Aucun manque de respect, harcèlement, insulte ou toxicité.
• Pas de spam, flood, pub ou troll inutile.

**Commandes & paiements**
• Toute commande se fait uniquement via le site officiel ou un ticket.
• N’effectue aucun paiement sur un autre compte que celui communiqué officiellement.

**Scam & sécurité**
• Toute tentative d’arnaque, usurpation, fausse preuve de paiement ou manipulation = sanction immédiate.
• Les transactions hors cadre officiel ne sont pas garanties.

**Revente & contenu**
• Interdiction de revendre, leak ou redistribuer nos créations sans autorisation.

**Litiges**
• Tout litige passe uniquement par ticket.
• Le staff garde le dernier mot en cas d’abus ou de comportement suspect.

En cliquant sur **J’accepte le règlement**, tu confirmes accepter ces règles.
"""


def ensure_data_dir() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)


def load_state() -> Dict[str, object]:
    ensure_data_dir()
    if not STATE_FILE.exists():
        return {
            "counters": DEFAULT_COUNTERS.copy(),
            "ticket_blacklist": DEFAULT_BLACKLIST.copy(),
            "warnings": DEFAULT_WARNINGS.copy(),
            "ticket_briefs": DEFAULT_TICKET_BRIEFS.copy(),
        }

    try:
        state = json.loads(STATE_FILE.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        logger.warning("Le fichier d'état est invalide, réinitialisation.")
        state = {}

    counters = state.get("counters", {})
    for key, value in DEFAULT_COUNTERS.items():
        counters.setdefault(key, value)
    state["counters"] = counters
    state.setdefault("ticket_blacklist", DEFAULT_BLACKLIST.copy())
    state.setdefault("warnings", DEFAULT_WARNINGS.copy())
    state.setdefault("ticket_briefs", DEFAULT_TICKET_BRIEFS.copy())
    return state


def save_state(state: Dict[str, object]) -> None:
    ensure_data_dir()
    STATE_FILE.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")


def get_required_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"La variable d'environnement {name} est obligatoire.")
    return value


def get_optional_int(name: str) -> Optional[int]:
    value = os.getenv(name)
    if not value:
        return None
    try:
        return int(value)
    except ValueError as exc:
        raise RuntimeError(f"La variable {name} doit être un nombre entier.") from exc


def get_optional_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None or value.strip() == "":
        return default
    return value.strip().lower() in {"1", "true", "yes", "on", "oui"}


def sanitize_channel_name(value: str) -> str:
    allowed = "abcdefghijklmnopqrstuvwxyz0123456789-"
    cleaned = value.lower().replace(" ", "-")
    cleaned = "".join(char for char in cleaned if char in allowed)
    cleaned = cleaned.strip("-")
    return cleaned or "client"


def clean_form_value(value: str) -> str:
    cleaned = " ".join(value.strip().split())
    return cleaned or "Non renseigne"


def truncate_text(value: str, limit: int = 1200) -> str:
    value = value.strip()
    if len(value) <= limit:
        return value
    return f"{value[: limit - 3].rstrip()}..."


def get_ticket_color(ticket_type: str) -> discord.Color:
    color_map = {
        "acheter_site": discord.Color.from_rgb(120, 89, 255),
        "commande_internet": discord.Color.from_rgb(80, 140, 255),
        "autre_aide": discord.Color.from_rgb(173, 92, 255),
    }
    return color_map.get(ticket_type, discord.Color.blurple())


def has_valid_openai_api_key() -> bool:
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not api_key:
        return False

    lowered = api_key.lower()
    placeholder_markers = (
        "ta_cle_openai",
        "colle_ici",
        "your_openai",
        "your-api-key",
        "example",
    )
    return not any(marker in lowered for marker in placeholder_markers)


def build_ticket_files() -> List[discord.File]:
    files: List[discord.File] = []
    if TICKET_LOGO_PATH.exists():
        files.append(discord.File(TICKET_LOGO_PATH, filename="ticket-logo.png"))
    if TICKET_BANNER_PATH.exists():
        files.append(discord.File(TICKET_BANNER_PATH, filename="ticket-banner.png"))
    return files


def apply_ticket_branding(embed: discord.Embed) -> discord.Embed:
    if TICKET_LOGO_PATH.exists():
        embed.set_author(name="NovaForge Services", icon_url="attachment://ticket-logo.png")
        embed.set_thumbnail(url="attachment://ticket-logo.png")
    else:
        embed.set_author(name="NovaForge Services")

    if TICKET_BANNER_PATH.exists():
        embed.set_image(url="attachment://ticket-banner.png")
    return embed


def parse_ticket_topic(topic: Optional[str]) -> Dict[str, str]:
    if not topic:
        return {}

    result: Dict[str, str] = {}
    for chunk in topic.split(";"):
        if ":" not in chunk:
            continue
        key, value = chunk.split(":", maxsplit=1)
        result[key] = value
    return result


def build_ticket_topic(data: Dict[str, object]) -> str:
    ordered_keys = ["ticket_owner", "ticket_type", "ticket_number", "claimed_by"]
    return ";".join(
        f"{key}:{data[key]}"
        for key in ordered_keys
        if data.get(key) not in (None, "", "none")
    )


def is_ticket_channel(channel: Optional[discord.abc.GuildChannel]) -> bool:
    return isinstance(channel, discord.TextChannel) and "ticket_owner" in parse_ticket_topic(channel.topic)


def get_ticket_data(channel: discord.TextChannel) -> Dict[str, str]:
    return parse_ticket_topic(channel.topic)


def get_ticket_owner_id(channel: discord.TextChannel) -> Optional[int]:
    value = get_ticket_data(channel).get("ticket_owner")
    if value is None:
        return None
    try:
        return int(value)
    except ValueError:
        return None


def get_ticket_type(channel: discord.TextChannel) -> Optional[str]:
    ticket_type = get_ticket_data(channel).get("ticket_type")
    if ticket_type in TICKET_CATEGORIES:
        return ticket_type
    return None


def get_ticket_number(channel: discord.TextChannel) -> str:
    return get_ticket_data(channel).get("ticket_number", "ticket")


def get_claimed_by_id(channel: discord.TextChannel) -> Optional[int]:
    value = get_ticket_data(channel).get("claimed_by")
    if value is None:
        return None
    try:
        return int(value)
    except ValueError:
        return None


def format_ticket_number(ticket_type: str, number: int) -> str:
    prefix = TICKET_CATEGORIES[ticket_type]["prefix"]
    return f"{prefix}-{number:03d}"


def is_support_member(member: discord.Member) -> bool:
    support_role_id = get_optional_int("SUPPORT_ROLE_ID")
    if not support_role_id:
        return False
    return any(role.id == support_role_id for role in member.roles)


def can_manage_ticket(member: discord.Member, channel: discord.TextChannel) -> bool:
    owner_id = get_ticket_owner_id(channel)
    if owner_id == member.id:
        return True
    if member.guild_permissions.administrator or member.guild_permissions.manage_channels:
        return True
    return is_support_member(member)


def can_claim_ticket(member: discord.Member) -> bool:
    return member.guild_permissions.administrator or member.guild_permissions.manage_channels or is_support_member(member)


def find_existing_ticket(guild: discord.Guild, user_id: int, ticket_key: str) -> Optional[discord.TextChannel]:
    for channel in guild.text_channels:
        if not is_ticket_channel(channel):
            continue
        data = get_ticket_data(channel)
        if data.get("ticket_owner") == str(user_id) and data.get("ticket_type") == ticket_key:
            return channel
    return None


def build_panel_embed() -> discord.Embed:
    embed = discord.Embed(
        title="Support NovaForge",
        description=(
            "Choisis le type de ticket qui correspond a ta demande.\n"
            "Un seul ticket par categorie peut etre ouvert a la fois."
        ),
        color=discord.Color.blurple(),
        timestamp=datetime.now(timezone.utc),
    )
    for config in TICKET_CATEGORIES.values():
        embed.add_field(
            name=f"{config['emoji']} {config['label']}",
            value=config["description"],
            inline=False,
        )
    embed.add_field(
        name="Conseil",
        value="Un formulaire adapte a la categorie choisie sera affiche avant l'ouverture du ticket.",
        inline=False,
    )
    embed.set_footer(text="NovaForge • Panel Tickets V3")
    return embed


def build_rules_embed() -> discord.Embed:
    embed = discord.Embed(
        title="Reglement NovaForge",
        description=RULES_TEXT,
        color=discord.Color.orange(),
        timestamp=datetime.now(timezone.utc),
    )
    embed.set_footer(text="Clique sur le bouton si tu acceptes le reglement")
    return embed


def build_ticket_embed(
    guild: discord.Guild,
    owner: discord.Member,
    ticket_type: str,
    ticket_number: str,
    claimed_by_id: Optional[int] = None,
    brief_title: Optional[str] = None,
    brief_fields: Optional[List[tuple[str, str]]] = None,
) -> discord.Embed:
    config = TICKET_CATEGORIES[ticket_type]
    claimed_text = "Non attribue"
    if claimed_by_id:
        claimed_member = guild.get_member(claimed_by_id)
        claimed_text = claimed_member.mention if claimed_member else f"<@{claimed_by_id}>"

    embed = discord.Embed(
        title=f"{config['emoji']} Ticket {ticket_number}",
        description=(
            f"{owner.mention}, ton ticket **{config['label']}** est bien cree.\n"
            "Le brief envoye avant l'ouverture est resume juste en dessous pour que le staff ait tout tout de suite."
        ),
        color=get_ticket_color(ticket_type),
        timestamp=datetime.now(timezone.utc),
    )
    embed.add_field(name="Client", value=owner.mention, inline=True)
    embed.add_field(name="Categorie", value=config["label"], inline=True)
    embed.add_field(name="Assigne a", value=claimed_text, inline=True)
    embed.add_field(
        name="Suivi",
        value="Le staff peut claim ce ticket. Tu peux aussi ajouter des precisions directement dans le salon.",
        inline=False,
    )

    if brief_fields:
        embed.add_field(
            name=brief_title or "Brief du client",
            value="Informations remplies avant la creation du ticket.",
            inline=False,
        )
        for name, value in brief_fields:
            embed.add_field(name=f"✦ {name}", value=value[:1024] or "Non renseigne", inline=False)
    else:
        embed.add_field(
            name="Brief",
            value="Aucun brief n'a ete enregistre pour ce ticket.",
            inline=False,
        )

    embed.set_footer(text="NovaForge • Ticket Premium")
    return apply_ticket_branding(embed)


def build_log_embed(title: str, description: str, color: discord.Color) -> discord.Embed:
    embed = discord.Embed(
        title=title,
        description=description,
        color=color,
        timestamp=datetime.now(timezone.utc),
    )
    embed.set_footer(text="NovaForge • Ticket Logs")
    return embed


def build_review_embed(member: discord.Member, rating: int, review_text: str) -> discord.Embed:
    stars = "★" * rating + "☆" * (5 - rating)
    embed = discord.Embed(
        title="Nouvel avis client",
        description=review_text,
        color=discord.Color.gold(),
        timestamp=datetime.now(timezone.utc),
    )
    embed.add_field(name="Client", value=member.mention, inline=True)
    embed.add_field(name="Note", value=f"{stars} ({rating}/5)", inline=True)
    embed.set_thumbnail(url=member.display_avatar.url)
    embed.set_footer(text="Merci pour ton avis")
    return embed


def build_server_stats_embed(guild: discord.Guild) -> discord.Embed:
    members = guild.members
    total_members = guild.member_count or len(members)
    human_members = sum(1 for member in members if not member.bot)
    bot_members = sum(1 for member in members if member.bot)
    online_members = sum(1 for member in members if member.status != discord.Status.offline)
    voice_members = sum(1 for member in members if member.voice and member.voice.channel)

    embed = discord.Embed(
        title=f"Statistiques de {guild.name}",
        color=discord.Color.blurple(),
        timestamp=datetime.now(timezone.utc),
    )
    if guild.icon:
        embed.set_thumbnail(url=guild.icon.url)

    embed.add_field(name="Membres", value=str(total_members), inline=True)
    embed.add_field(name="Humains", value=str(human_members), inline=True)
    embed.add_field(name="Bots", value=str(bot_members), inline=True)
    embed.add_field(name="En ligne", value=str(online_members), inline=True)
    embed.add_field(name="En vocal", value=str(voice_members), inline=True)
    embed.add_field(name="Boosts", value=str(guild.premium_subscription_count or 0), inline=True)
    embed.add_field(name="Salons texte", value=str(len(guild.text_channels)), inline=True)
    embed.add_field(name="Salons vocaux", value=str(len(guild.voice_channels)), inline=True)
    embed.add_field(name="Roles", value=str(len(guild.roles)), inline=True)
    embed.add_field(
        name="Creation",
        value=discord.utils.format_dt(guild.created_at, style="F"),
        inline=False,
    )
    embed.set_footer(text=f"ID serveur: {guild.id}")
    return embed


def build_online_embed(guild: discord.Guild) -> discord.Embed:
    members = guild.members
    online_members = [member for member in members if not member.bot and member.status != discord.Status.offline]
    staff_online = [
        member
        for member in online_members
        if member.guild_permissions.administrator
        or member.guild_permissions.manage_guild
        or member.guild_permissions.manage_channels
    ]

    status_counts = {
        "En ligne": sum(1 for member in members if member.status == discord.Status.online),
        "Inactif": sum(1 for member in members if member.status == discord.Status.idle),
        "Ne pas deranger": sum(1 for member in members if member.status == discord.Status.dnd),
        "Hors ligne": sum(1 for member in members if member.status == discord.Status.offline),
    }

    embed = discord.Embed(
        title=f"Membres connectes - {guild.name}",
        color=discord.Color.green(),
        timestamp=datetime.now(timezone.utc),
    )

    embed.add_field(name="Humains connectes", value=str(len(online_members)), inline=True)
    embed.add_field(name="Staff connecte", value=str(len(staff_online)), inline=True)
    embed.add_field(
        name="Repartition",
        value="\n".join(f"{label}: {count}" for label, count in status_counts.items()),
        inline=False,
    )

    if staff_online:
        preview = ", ".join(member.mention for member in staff_online[:10])
        if len(staff_online) > 10:
            preview += f" ... (+{len(staff_online) - 10})"
        embed.add_field(name="Staff actuellement la", value=preview, inline=False)
    else:
        embed.add_field(name="Staff actuellement la", value="Aucun staff connecte pour le moment.", inline=False)

    return embed


def build_user_info_embed(member: discord.Member) -> discord.Embed:
    roles = [role.mention for role in reversed(member.roles) if role != member.guild.default_role]
    role_text = ", ".join(roles[:12]) if roles else "Aucun role"
    if len(roles) > 12:
        role_text += f" ... (+{len(roles) - 12})"

    embed = discord.Embed(
        title=f"Infos membre - {member.display_name}",
        color=member.color if member.color != discord.Color.default() else discord.Color.blurple(),
        timestamp=datetime.now(timezone.utc),
    )
    embed.set_thumbnail(url=member.display_avatar.url)
    embed.add_field(name="Utilisateur", value=f"{member.mention}\n`{member}`", inline=False)
    embed.add_field(name="ID", value=str(member.id), inline=True)
    embed.add_field(name="Statut", value=str(member.status).replace("_", " "), inline=True)
    embed.add_field(name="Bot", value="Oui" if member.bot else "Non", inline=True)
    embed.add_field(name="Compte cree", value=discord.utils.format_dt(member.created_at, style="F"), inline=False)
    embed.add_field(name="Arrivee serveur", value=discord.utils.format_dt(member.joined_at, style="F") if member.joined_at else "Inconnue", inline=False)
    embed.add_field(name="Roles", value=role_text[:1024], inline=False)
    embed.set_footer(text=f"Demande pour {member.guild.name}")
    return embed


def build_brief_embed(title: str, fields: List[tuple[str, str]]) -> discord.Embed:
    embed = discord.Embed(
        title=title,
        color=discord.Color.green(),
        timestamp=datetime.now(timezone.utc),
    )
    for name, value in fields:
        embed.add_field(name=name, value=value[:1024] or "Non renseigne", inline=False)
    embed.set_footer(text="NovaForge • Brief Client")
    return embed


def get_ticket_brief_entry(channel_id: int) -> Optional[Dict[str, object]]:
    entry = bot.state.get("ticket_briefs", {}).get(str(channel_id))
    if isinstance(entry, dict):
        return entry
    return None


def get_ticket_brief(channel_id: int) -> Tuple[Optional[str], List[Tuple[str, str]]]:
    entry = get_ticket_brief_entry(channel_id)
    if not entry:
        return None, []

    title = entry.get("title")
    raw_fields = entry.get("fields", [])
    if not isinstance(raw_fields, list):
        return str(title) if title else None, []

    fields: List[Tuple[str, str]] = []
    for raw_field in raw_fields:
        if not isinstance(raw_field, dict):
            continue
        name = str(raw_field.get("name", "")).strip()
        value = str(raw_field.get("value", "")).strip()
        if name:
            fields.append((name, value or "Non renseigne"))

    return (str(title) if title else None, fields)


def store_ticket_brief(channel_id: int, title: Optional[str], fields: List[Tuple[str, str]]) -> None:
    ticket_briefs = bot.state.setdefault("ticket_briefs", DEFAULT_TICKET_BRIEFS.copy())
    ticket_briefs[str(channel_id)] = {
        "title": title or "Brief du client",
        "fields": [{"name": name, "value": value} for name, value in fields],
    }
    save_state(bot.state)


def remove_ticket_brief(channel_id: int) -> None:
    ticket_briefs = bot.state.setdefault("ticket_briefs", DEFAULT_TICKET_BRIEFS.copy())
    if ticket_briefs.pop(str(channel_id), None) is not None:
        save_state(bot.state)


def get_ticket_form_config(ticket_key: str) -> Dict[str, Any]:
    return TICKET_CATEGORIES[ticket_key].get("form", {})


def ticket_has_form(ticket_key: str) -> bool:
    return bool(get_ticket_form_config(ticket_key).get("fields"))


def is_ticket_ai_enabled() -> bool:
    return get_optional_bool("ENABLE_TICKET_AI", default=True) and has_valid_openai_api_key()


def is_ai_trigger_message(content: str) -> bool:
    lowered = content.lower().strip()
    if "?" in lowered:
        return True
    if any(lowered.startswith(prefix) for prefix in AI_TRIGGER_PREFIXES):
        return True
    return any(lowered == prefix or lowered.startswith(f"{prefix} ") for prefix in AI_GREETING_PREFIXES)


def should_answer_with_ai(message: discord.Message) -> bool:
    if not is_ticket_ai_enabled():
        return False
    if message.author.bot or not message.content.strip():
        return False
    if not isinstance(message.channel, discord.TextChannel):
        return False
    if not is_ticket_channel(message.channel):
        return False
    owner_id = get_ticket_owner_id(message.channel)
    if owner_id != message.author.id:
        return False
    if bot.user and bot.user.mentioned_in(message):
        return True
    if message.reference and isinstance(message.reference.resolved, discord.Message):
        if bot.user and message.reference.resolved.author.id == bot.user.id:
            return True
    return is_ai_trigger_message(message.content)


def describe_ticket_speaker(channel: discord.TextChannel, author: discord.abc.User) -> str:
    owner_id = get_ticket_owner_id(channel)
    if author.id == owner_id:
        return "Client"
    if isinstance(author, discord.Member) and can_claim_ticket(author):
        return "Staff"
    return "Participant"


def extract_message_context(channel: discord.TextChannel, message: discord.Message) -> Optional[Tuple[str, str]]:
    content_parts: List[str] = []
    if message.content.strip():
        content_parts.append(message.content.strip())

    for embed in message.embeds:
        embed_lines: List[str] = []
        if embed.title and "brief" in embed.title.lower():
            embed_lines.append(embed.title)
            for field in embed.fields:
                embed_lines.append(f"{field.name}: {field.value}")
        if embed_lines:
            content_parts.append("\n".join(embed_lines))

    combined = "\n".join(part for part in content_parts if part).strip()
    if not combined:
        return None

    if bot.user and message.author.id == bot.user.id:
        return ("assistant", truncate_text(combined))

    speaker = describe_ticket_speaker(channel, message.author)
    author_name = getattr(message.author, "display_name", message.author.name)
    return ("user", truncate_text(f"{speaker} {author_name}: {combined}"))


async def build_ticket_ai_messages(channel: discord.TextChannel) -> List[Dict[str, str]]:
    ticket_type = get_ticket_type(channel)
    config = TICKET_CATEGORIES.get(ticket_type or "", {})
    category_label = config.get("label", "Ticket")
    ai_focus = config.get("ai_focus", "Aide le client et pose des questions utiles.")

    messages: List[Dict[str, str]] = [
        {
            "role": "system",
            "content": (
                "Tu es l'assistant automatique de NovaForge dans un ticket Discord. "
                f"Categorie: {category_label}. {ai_focus} "
                "Reponds en francais, de facon concise, utile et professionnelle. "
                "Si une information manque, pose 1 ou 2 questions claires. "
                "Ne promets jamais un prix final, un delai final ou une action garantie au nom du staff. "
                "Si la demande depasse ce que tu sais, dis que le staff prendra le relai."
            ),
        }
    ]

    brief_title, brief_fields = get_ticket_brief(channel.id)
    if brief_fields:
        brief_lines = [brief_title or "Brief du client"]
        brief_lines.extend(f"{name}: {value}" for name, value in brief_fields)
        messages.append(
            {
                "role": "system",
                "content": "Brief du client au moment de l'ouverture:\n" + "\n".join(brief_lines),
            }
        )

    history_entries: List[Dict[str, str]] = []
    async for history_message in channel.history(limit=MAX_AI_HISTORY_MESSAGES, oldest_first=True):
        extracted = extract_message_context(channel, history_message)
        if extracted is None:
            continue
        role, content = extracted
        history_entries.append({"role": role, "content": content})

    messages.extend(history_entries[-MAX_AI_HISTORY_MESSAGES:])
    return messages


def parse_openai_error_message(raw_error_body: str, default: str) -> str:
    try:
        error_data = json.loads(raw_error_body)
    except json.JSONDecodeError:
        return default

    error = error_data.get("error")
    if isinstance(error, dict):
        message = error.get("message")
        if isinstance(message, str) and message.strip():
            return message.strip()
    return default


def request_openai_chat_completion(messages: List[Dict[str, str]]) -> Tuple[Optional[str], Optional[str]]:
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not has_valid_openai_api_key():
        return None, "La cle OpenAI n'est pas configuree correctement."

    model = os.getenv("OPENAI_MODEL", "gpt-4.1-mini")
    payload = {
        "model": model,
        "messages": messages,
        "temperature": 0.7,
        "max_tokens": 350,
    }
    request = urllib.request.Request(
        "https://api.openai.com/v1/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            raw_data = response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        error_body = exc.read().decode("utf-8", errors="ignore")
        error_message = parse_openai_error_message(error_body, f"Erreur OpenAI HTTP {exc.code}.")
        logger.warning("Erreur HTTP OpenAI (%s): %s | %s", exc.code, exc.reason, error_body[:400])
        return None, error_message
    except urllib.error.URLError as exc:
        logger.warning("Erreur reseau OpenAI: %s", exc.reason)
        return None, "Impossible de contacter OpenAI pour le moment."
    except Exception:
        logger.exception("Erreur inattendue pendant l'appel OpenAI ticket.")
        return None, "Une erreur inattendue est survenue pendant la reponse IA."

    data = json.loads(raw_data)
    choice = (data.get("choices") or [{}])[0]
    message = choice.get("message") or {}
    content = message.get("content")
    if isinstance(content, str):
        final_content = content.strip()
        return (final_content or None), None
    if isinstance(content, list):
        text_parts = [part.get("text", "") for part in content if isinstance(part, dict)]
        final_content = "\n".join(part for part in text_parts if part).strip()
        return (final_content or None), None
    return None, "OpenAI n'a renvoye aucun texte exploitable."


async def generate_ticket_ai_reply(channel: discord.TextChannel) -> Tuple[Optional[str], Optional[str]]:
    messages = await build_ticket_ai_messages(channel)
    try:
        return await asyncio.to_thread(request_openai_chat_completion, messages)
    except Exception:
        logger.exception("Erreur inattendue pendant la reponse IA ticket.")
    return None, "La reponse IA a echoue avant l'envoi."


def get_blacklist_entry(user_id: int) -> Optional[Dict[str, str]]:
    entry = bot.state.get("ticket_blacklist", {}).get(str(user_id))
    if isinstance(entry, dict):
        return entry
    return None


def is_ticket_blacklisted(user_id: int) -> bool:
    return get_blacklist_entry(user_id) is not None


def get_warning_entries(user_id: int) -> List[Dict[str, str]]:
    warnings = bot.state.get("warnings", {}).get(str(user_id), [])
    if isinstance(warnings, list):
        return warnings
    return []


async def safe_defer(interaction: discord.Interaction, *, ephemeral: bool = True) -> bool:
    try:
        if not interaction.response.is_done():
            await interaction.response.defer(ephemeral=ephemeral, thinking=False)
        return True
    except discord.NotFound:
        logger.warning("Interaction expirée ignorée.")
        return False


async def safe_followup(interaction: discord.Interaction, content: str, *, ephemeral: bool = True) -> None:
    try:
        await interaction.followup.send(content, ephemeral=ephemeral)
    except discord.NotFound:
        logger.warning("Impossible d'envoyer la reponse de suivi, interaction expirée.")


async def get_log_channel(guild: discord.Guild) -> Optional[discord.TextChannel]:
    log_channel_id = get_optional_int("LOG_CHANNEL_ID")
    if not log_channel_id:
        return None
    channel = guild.get_channel(log_channel_id)
    if isinstance(channel, discord.TextChannel):
        return channel
    return None


async def send_log_message(
    guild: discord.Guild,
    *,
    title: str,
    description: str,
    color: discord.Color,
    file: Optional[discord.File] = None,
) -> None:
    log_channel = await get_log_channel(guild)
    if log_channel is None:
        return
    try:
        await log_channel.send(embed=build_log_embed(title, description, color), file=file)
    except discord.Forbidden:
        logger.warning("Impossible d'envoyer un log dans le salon configure.")


async def cleanup_previous_messages(channel: discord.TextChannel, *, limit: int = 100) -> None:
    bot_user = bot.user
    if bot_user is None:
        return

    async for message in channel.history(limit=limit):
        if message.author.id != bot_user.id:
            continue
        component_ids = [child.custom_id for row in message.components for child in row.children]
        if any(custom_id and custom_id.startswith("novaforge_") for custom_id in component_ids):
            try:
                await message.delete()
            except discord.Forbidden:
                logger.warning("Impossible de supprimer un ancien message dans %s", channel.id)


async def get_bot_member(guild: discord.Guild) -> Optional[discord.Member]:
    bot_user = bot.user
    if bot_user is None:
        return None
    member = guild.me or guild.get_member(bot_user.id)
    if member is not None:
        return member
    try:
        return await guild.fetch_member(bot_user.id)
    except discord.NotFound:
        return None


async def update_ticket_message(channel: discord.TextChannel) -> None:
    bot_member = await get_bot_member(channel.guild)
    if bot_member is None:
        return

    owner_id = get_ticket_owner_id(channel)
    ticket_type = get_ticket_type(channel)
    if owner_id is None or ticket_type is None:
        return

    owner = channel.guild.get_member(owner_id)
    if owner is None:
        try:
            owner = await channel.guild.fetch_member(owner_id)
        except discord.NotFound:
            return

    claimed_by_id = get_claimed_by_id(channel)
    ticket_number = get_ticket_number(channel)
    brief_title, brief_fields = get_ticket_brief(channel.id)
    legacy_brief_message: Optional[discord.Message] = None

    if not brief_fields:
        legacy_brief_message, legacy_title, legacy_fields = await find_legacy_brief_message(channel)
        if legacy_fields:
            brief_title = legacy_title
            brief_fields = legacy_fields
            store_ticket_brief(channel.id, brief_title, brief_fields)

    async for message in channel.history(limit=20, oldest_first=True):
        if message.author.id != bot_member.id:
            continue
        if not message.embeds:
            continue
        if not message.components:
            continue
        await message.edit(
            content=None,
            embed=build_ticket_embed(
                channel.guild,
                owner,
                ticket_type,
                ticket_number,
                claimed_by_id,
                brief_title=brief_title,
                brief_fields=brief_fields,
            ),
            attachments=build_ticket_files(),
            view=TicketActionView(),
        )

        if legacy_brief_message and legacy_brief_message.id != message.id:
            try:
                await legacy_brief_message.delete()
            except discord.Forbidden:
                logger.warning("Impossible de supprimer l'ancien brief dans %s", channel.id)
        return


async def find_legacy_brief_message(
    channel: discord.TextChannel,
) -> Tuple[Optional[discord.Message], Optional[str], List[Tuple[str, str]]]:
    bot_user = bot.user
    if bot_user is None:
        return None, None, []

    async for message in channel.history(limit=20, oldest_first=True):
        if message.author.id != bot_user.id:
            continue
        for embed in message.embeds:
            if not embed.title or "brief" not in embed.title.lower():
                continue
            fields = [(field.name, str(field.value)) for field in embed.fields if field.name]
            if fields:
                return message, embed.title, fields
    return None, None, []


async def create_transcript_file(channel: discord.TextChannel) -> discord.File:
    lines: List[str] = [
        f"Transcript du ticket {channel.name}",
        f"Serveur: {channel.guild.name}",
        f"Salon: {channel.name}",
        "-" * 60,
    ]

    async for message in channel.history(limit=None, oldest_first=True):
        created_at = message.created_at.strftime("%Y-%m-%d %H:%M:%S")
        lines.append(f"[{created_at}] {message.author} ({message.author.id})")
        lines.append(message.content or "[aucun texte]")
        for attachment in message.attachments:
            lines.append(f"Attachment: {attachment.url}")
        if message.embeds:
            lines.append(f"Embeds: {len(message.embeds)}")
        lines.append("")

    buffer = io.BytesIO("\n".join(lines).encode("utf-8"))
    return discord.File(buffer, filename=f"{channel.name}-transcript.txt")


async def close_ticket_channel(channel: discord.TextChannel, closed_by: discord.Member) -> None:
    owner_id = get_ticket_owner_id(channel)
    ticket_type = get_ticket_type(channel)
    ticket_number = get_ticket_number(channel)
    category_label = TICKET_CATEGORIES.get(ticket_type or "", {}).get("label", "Inconnu")

    transcript = await create_transcript_file(channel)
    await send_log_message(
        channel.guild,
        title="Ticket ferme",
        description=(
            f"Ticket: **{ticket_number}**\n"
            f"Client: <@{owner_id}>\n"
            f"Categorie: **{category_label}**\n"
            f"Ferme par: {closed_by.mention}"
        ),
        color=discord.Color.red(),
        file=transcript,
    )
    remove_ticket_brief(channel.id)
    await channel.delete(reason=f"Ticket ferme par {closed_by}")


async def create_ticket_for_member(
    interaction: discord.Interaction,
    ticket_key: str,
    *,
    brief_fields: Optional[List[tuple[str, str]]] = None,
    brief_title: Optional[str] = None,
) -> None:
    assert interaction.guild is not None
    assert isinstance(interaction.user, discord.Member)

    if is_ticket_blacklisted(interaction.user.id):
        entry = get_blacklist_entry(interaction.user.id) or {}
        reason = entry.get("reason", "Aucune raison precisee")
        await safe_followup(
            interaction,
            f"Tu es blacklist du systeme de tickets. Raison : {reason}",
        )
        return

    existing_channel = find_existing_ticket(interaction.guild, interaction.user.id, ticket_key)
    if existing_channel is not None:
        await safe_followup(interaction, f"Tu as deja un ticket ouvert ici : {existing_channel.mention}")
        return

    config = TICKET_CATEGORIES[ticket_key]
    category = interaction.guild.get_channel(config["category_id"])
    if not isinstance(category, discord.CategoryChannel):
        await safe_followup(interaction, "La categorie de ticket est introuvable. Verifie les IDs.")
        return

    bot_member = await get_bot_member(interaction.guild)
    if bot_member is None:
        await safe_followup(interaction, "Je n'arrive pas a recuperer mon profil serveur.")
        return

    support_role_id = get_optional_int("SUPPORT_ROLE_ID")
    support_role = interaction.guild.get_role(support_role_id) if support_role_id else None

    overwrites = {
        interaction.guild.default_role: discord.PermissionOverwrite(view_channel=False),
        interaction.user: discord.PermissionOverwrite(
            view_channel=True,
            send_messages=True,
            read_message_history=True,
            attach_files=True,
            embed_links=True,
        ),
        bot_member: discord.PermissionOverwrite(
            view_channel=True,
            send_messages=True,
            manage_channels=True,
            manage_messages=True,
            read_message_history=True,
        ),
    }
    if support_role is not None:
        overwrites[support_role] = discord.PermissionOverwrite(
            view_channel=True,
            send_messages=True,
            read_message_history=True,
            attach_files=True,
            embed_links=True,
        )

    counters = bot.state.setdefault("counters", DEFAULT_COUNTERS.copy())
    counters[ticket_key] = int(counters.get(ticket_key, 0)) + 1
    save_state(bot.state)

    ticket_number = format_ticket_number(ticket_key, counters[ticket_key])
    channel_name = f"{ticket_number}-{sanitize_channel_name(interaction.user.display_name)}"[:100]
    topic = build_ticket_topic(
        {
            "ticket_owner": interaction.user.id,
            "ticket_type": ticket_key,
            "ticket_number": ticket_number,
        }
    )

    try:
        created_channel = await interaction.guild.create_text_channel(
            name=channel_name,
            category=category,
            overwrites=overwrites,
            topic=topic,
            reason=f"Ticket {config['label']} cree par {interaction.user}",
        )
    except discord.Forbidden:
        await safe_followup(interaction, "Je n'ai pas les permissions pour creer le ticket.")
        return

    mention_line = interaction.user.mention
    if support_role is not None:
        mention_line = f"{interaction.user.mention} {support_role.mention}"

    if brief_fields:
        store_ticket_brief(created_channel.id, brief_title or config.get("brief_title"), brief_fields)

    ticket_message = await created_channel.send(
        content=mention_line,
        embed=build_ticket_embed(
            interaction.guild,
            interaction.user,
            ticket_key,
            ticket_number,
            brief_title=brief_title or config.get("brief_title"),
            brief_fields=brief_fields,
        ),
        view=TicketActionView(),
        files=build_ticket_files(),
    )

    if mention_line:
        try:
            await ticket_message.edit(content=None)
        except discord.HTTPException:
            logger.warning("Impossible de nettoyer la ligne de ping dans %s", created_channel.id)

    log_description = (
        f"Ticket: **{ticket_number}**\n"
        f"Client: {interaction.user.mention}\n"
        f"Categorie: **{config['label']}**\n"
        f"Salon: {created_channel.mention}"
    )
    if brief_fields:
        preview = " | ".join(f"{name}: {value}" for name, value in brief_fields[:3])
        log_description += f"\nResume: {preview[:400]}"

    await send_log_message(
        interaction.guild,
        title="Ticket ouvert",
        description=log_description,
        color=discord.Color.green(),
    )
    await safe_followup(interaction, f"Ton ticket a ete cree : {created_channel.mention}")


class TicketBriefModal(discord.ui.Modal):
    def __init__(self, ticket_key: str) -> None:
        self.ticket_key = ticket_key
        self.ticket_config = TICKET_CATEGORIES[ticket_key]
        self.form_config = get_ticket_form_config(ticket_key)
        self.form_inputs: List[Tuple[Dict[str, Any], discord.ui.TextInput]] = []

        super().__init__(title=self.form_config.get("title", self.ticket_config["label"])[:45])

        for field_config in self.form_config.get("fields", []):
            text_input = discord.ui.TextInput(
                label=field_config["label"][:45],
                placeholder=field_config.get("placeholder", "")[:100],
                style=field_config.get("style", discord.TextStyle.short),
                max_length=field_config.get("max_length", 100),
                required=field_config.get("required", True),
            )
            self.form_inputs.append((field_config, text_input))
            self.add_item(text_input)

    async def on_submit(self, interaction: discord.Interaction) -> None:
        if not await safe_defer(interaction):
            return

        if not interaction.guild or not isinstance(interaction.user, discord.Member):
            await safe_followup(interaction, "Cette action doit etre utilisee dans le serveur.")
            return

        lock_key = f"{interaction.guild.id}:{interaction.user.id}:{self.ticket_key}"
        if lock_key in bot.ticket_creation_in_progress:
            await safe_followup(interaction, "La creation de ton ticket est deja en cours.")
            return

        bot.ticket_creation_in_progress.add(lock_key)
        try:
            brief_fields = [
                (field_config.get("brief_label", field_config["label"]), clean_form_value(str(text_input)))
                for field_config, text_input in self.form_inputs
            ]
            await create_ticket_for_member(
                interaction,
                self.ticket_key,
                brief_fields=brief_fields,
                brief_title=self.ticket_config.get("brief_title"),
            )
        finally:
            bot.ticket_creation_in_progress.discard(lock_key)


class RulesView(discord.ui.View):
    def __init__(self) -> None:
        super().__init__(timeout=None)

    @discord.ui.button(
        label="J'accepte le reglement",
        style=discord.ButtonStyle.success,
        custom_id=RULES_ACCEPT_ID,
    )
    async def accept_rules(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ) -> None:
        del button
        if not await safe_defer(interaction):
            return

        if not interaction.guild or not isinstance(interaction.user, discord.Member):
            await safe_followup(interaction, "Cette action doit etre utilisee dans le serveur.")
            return

        role_id = get_optional_int("RULE_ACCEPT_ROLE_ID")
        role = interaction.guild.get_role(role_id) if role_id else None
        if role is None:
            await safe_followup(interaction, "Reglement accepte. Aucun role automatique n'est configure.")
            return

        try:
            await interaction.user.add_roles(role, reason="Reglement NovaForge accepte")
        except discord.Forbidden:
            await safe_followup(interaction, "Je ne peux pas donner le role de reglement.")
            return

        await safe_followup(interaction, f"Merci, tu as recu le role {role.mention}.")


class TicketActionView(discord.ui.View):
    def __init__(self) -> None:
        super().__init__(timeout=None)

    @discord.ui.button(
        label="Claim",
        style=discord.ButtonStyle.secondary,
        emoji="\U0001f9f7",
        custom_id=TICKET_CLAIM_ID,
    )
    async def claim_ticket(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ) -> None:
        del button
        if not await safe_defer(interaction):
            return

        channel = interaction.channel
        if not interaction.guild or not isinstance(interaction.user, discord.Member) or not isinstance(channel, discord.TextChannel):
            await safe_followup(interaction, "Ce bouton fonctionne uniquement dans un ticket.")
            return

        if not is_ticket_channel(channel):
            await safe_followup(interaction, "Ce salon n'est pas un ticket gere par le bot.")
            return

        if not can_claim_ticket(interaction.user):
            await safe_followup(interaction, "Seul le support ou un administrateur peut claim un ticket.")
            return

        ticket_data = get_ticket_data(channel)
        current_claim = get_claimed_by_id(channel)
        ticket_number = get_ticket_number(channel)

        if current_claim == interaction.user.id:
            ticket_data.pop("claimed_by", None)
            await channel.edit(topic=build_ticket_topic(ticket_data))
            await update_ticket_message(channel)
            await send_log_message(
                interaction.guild,
                title="Ticket libere",
                description=f"{interaction.user.mention} a libere le ticket **{ticket_number}**.",
                color=discord.Color.gold(),
            )
            await safe_followup(interaction, "Tu as libere ce ticket.")
            return

        ticket_data["claimed_by"] = interaction.user.id
        await channel.edit(topic=build_ticket_topic(ticket_data))
        await update_ticket_message(channel)
        await send_log_message(
            interaction.guild,
            title="Ticket claim",
            description=f"{interaction.user.mention} a claim le ticket **{ticket_number}**.",
            color=discord.Color.blue(),
        )
        await safe_followup(interaction, "Ticket claim avec succes.")

    @discord.ui.button(
        label="Fermer",
        style=discord.ButtonStyle.danger,
        emoji="\U0001f512",
        custom_id=TICKET_CLOSE_ID,
    )
    async def close_ticket(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ) -> None:
        del button
        if not await safe_defer(interaction):
            return

        channel = interaction.channel
        if not interaction.guild or not isinstance(interaction.user, discord.Member) or not isinstance(channel, discord.TextChannel):
            await safe_followup(interaction, "Ce bouton fonctionne uniquement dans un ticket.")
            return

        if not is_ticket_channel(channel):
            await safe_followup(interaction, "Ce salon n'est pas un ticket gere par le bot.")
            return

        if not can_manage_ticket(interaction.user, channel):
            await safe_followup(interaction, "Seul le createur du ticket, le support ou un admin peut le fermer.")
            return

        await close_ticket_channel(channel, interaction.user)


class TicketSelect(discord.ui.Select):
    def __init__(self) -> None:
        options = [
            discord.SelectOption(
                label=config["label"],
                value=key,
                emoji=config["emoji"],
                description=config["description"][:100],
            )
            for key, config in TICKET_CATEGORIES.items()
        ]
        super().__init__(
            placeholder="Choisis le type de ticket a ouvrir",
            min_values=1,
            max_values=1,
            options=options,
            custom_id=PANEL_SELECT_ID,
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        if not interaction.guild or not isinstance(interaction.user, discord.Member):
            await interaction.response.send_message(
                "Ce menu doit etre utilise dans un serveur Discord.",
                ephemeral=True,
            )
            return

        ticket_key = self.values[0]
        if is_ticket_blacklisted(interaction.user.id):
            entry = get_blacklist_entry(interaction.user.id) or {}
            reason = entry.get("reason", "Aucune raison precisee")
            await interaction.response.send_message(
                f"Tu es blacklist du systeme de tickets. Raison : {reason}",
                ephemeral=True,
            )
            return

        if ticket_has_form(ticket_key):
            await interaction.response.send_modal(TicketBriefModal(ticket_key))
            return

        if not await safe_defer(interaction):
            return

        lock_key = f"{interaction.guild.id}:{interaction.user.id}:{ticket_key}"
        if lock_key in bot.ticket_creation_in_progress:
            await safe_followup(interaction, "La creation de ton ticket est deja en cours.")
            return

        bot.ticket_creation_in_progress.add(lock_key)
        try:
            await create_ticket_for_member(interaction, ticket_key)
        finally:
            bot.ticket_creation_in_progress.discard(lock_key)


class TicketPanelView(discord.ui.View):
    def __init__(self) -> None:
        super().__init__(timeout=None)
        self.add_item(TicketSelect())


class NovaForgeBot(commands.Bot):
    def __init__(self) -> None:
        intents = discord.Intents.default()
        intents.guilds = True
        intents.members = True
        intents.message_content = True
        super().__init__(command_prefix="!", intents=intents)
        self.state: Dict[str, object] = load_state()
        self.ticket_creation_in_progress: Set[str] = set()
        self.ai_response_in_progress: Set[int] = set()

    async def setup_hook(self) -> None:
        self.add_view(TicketPanelView())
        self.add_view(TicketActionView())
        self.add_view(RulesView())

        guild_id = get_optional_int("GUILD_ID")
        if guild_id:
            guild_obj = discord.Object(id=guild_id)
            self.tree.copy_global_to(guild=guild_obj)
            await self.tree.sync(guild=guild_obj)
            logger.info("Commandes synchronisees sur le serveur %s", guild_id)
        else:
            await self.tree.sync()
            logger.info("Commandes globales synchronisees.")

    async def on_ready(self) -> None:
        logger.info("Connecte en tant que %s (%s)", self.user, self.user.id)
        if get_optional_bool("ENABLE_TICKET_AI", default=True):
            if has_valid_openai_api_key():
                logger.info("Assistant IA tickets actif.")
            else:
                logger.warning("Assistant IA tickets desactive: OPENAI_API_KEY manquante ou encore exemple.")

        for guild in self.guilds:
            for channel in guild.text_channels:
                if not is_ticket_channel(channel):
                    continue
                try:
                    await update_ticket_message(channel)
                except discord.HTTPException:
                    logger.warning("Impossible de rafraichir le ticket %s au demarrage.", channel.id)

    async def on_member_join(self, member: discord.Member) -> None:
        role = member.guild.get_role(AUTO_ROLE_ID)
        if role is None:
            logger.warning("Le role automatique %s est introuvable.", AUTO_ROLE_ID)
            return
        try:
            await member.add_roles(role, reason="Role automatique NovaForge")
        except discord.Forbidden:
            logger.warning("Impossible d'ajouter le role automatique a %s", member.id)

    async def on_message(self, message: discord.Message) -> None:
        await self.process_commands(message)

        if not should_answer_with_ai(message):
            return
        if not isinstance(message.channel, discord.TextChannel):
            return
        if message.channel.id in self.ai_response_in_progress:
            return

        self.ai_response_in_progress.add(message.channel.id)
        try:
            async with message.channel.typing():
                ai_reply, ai_error = await generate_ticket_ai_reply(message.channel)

            if not ai_reply:
                if ai_error:
                    await message.channel.send(
                        f"{message.author.mention} Je n'ai pas pu repondre automatiquement pour le moment.\n"
                        f"Raison: {truncate_text(ai_error, 300)}"
                    )
                return

            await message.channel.send(
                f"{message.author.mention} **Assistant NovaForge**\n{truncate_text(ai_reply, 1800)}"
            )
        finally:
            self.ai_response_in_progress.discard(message.channel.id)


bot = NovaForgeBot()


@bot.tree.command(name="setup", description="Republie le panel ticket et le reglement")
@app_commands.default_permissions(manage_guild=True)
async def setup(interaction: discord.Interaction) -> None:
    if not await safe_defer(interaction):
        return

    if not interaction.guild:
        await safe_followup(interaction, "Cette commande doit etre utilisee dans ton serveur.")
        return

    panel_channel = interaction.guild.get_channel(PANEL_CHANNEL_ID)
    rules_channel = interaction.guild.get_channel(RULES_CHANNEL_ID)
    if not isinstance(panel_channel, discord.TextChannel):
        await safe_followup(interaction, f"Le salon panel `{PANEL_CHANNEL_ID}` est introuvable.")
        return
    if not isinstance(rules_channel, discord.TextChannel):
        await safe_followup(interaction, f"Le salon reglement `{RULES_CHANNEL_ID}` est introuvable.")
        return

    await cleanup_previous_messages(panel_channel)
    await cleanup_previous_messages(rules_channel)

    panel_message = await panel_channel.send(embed=build_panel_embed(), view=TicketPanelView())
    rules_message = await rules_channel.send(embed=build_rules_embed(), view=RulesView())
    bot.state["panel_message_id"] = panel_message.id
    bot.state["rules_message_id"] = rules_message.id
    save_state(bot.state)

    log_channel = await get_log_channel(interaction.guild)
    log_text = log_channel.mention if log_channel else "non configure"
    await safe_followup(
        interaction,
        (
            "Configuration terminee.\n"
            f"Panel: {panel_message.jump_url}\n"
            f"Reglement: {rules_message.jump_url}\n"
            f"Logs: {log_text}"
        ),
    )


@bot.tree.command(name="close", description="Ferme le ticket courant")
async def close(interaction: discord.Interaction) -> None:
    if not await safe_defer(interaction):
        return

    channel = interaction.channel
    if not interaction.guild or not isinstance(interaction.user, discord.Member) or not isinstance(channel, discord.TextChannel):
        await safe_followup(interaction, "Cette commande doit etre utilisee dans un ticket.")
        return
    if not is_ticket_channel(channel):
        await safe_followup(interaction, "Cette commande doit etre utilisee dans un ticket.")
        return
    if not can_manage_ticket(interaction.user, channel):
        await safe_followup(interaction, "Seul le createur du ticket, le support ou un admin peut le fermer.")
        return

    await close_ticket_channel(channel, interaction.user)


@bot.tree.command(name="claim", description="Claim ou libere le ticket courant")
async def claim(interaction: discord.Interaction) -> None:
    if not await safe_defer(interaction):
        return

    channel = interaction.channel
    if not interaction.guild or not isinstance(interaction.user, discord.Member) or not isinstance(channel, discord.TextChannel):
        await safe_followup(interaction, "Cette commande doit etre utilisee dans un ticket.")
        return
    if not is_ticket_channel(channel):
        await safe_followup(interaction, "Cette commande doit etre utilisee dans un ticket.")
        return
    if not can_claim_ticket(interaction.user):
        await safe_followup(interaction, "Seul le support ou un administrateur peut claim un ticket.")
        return

    ticket_data = get_ticket_data(channel)
    current_claim = get_claimed_by_id(channel)
    ticket_number = get_ticket_number(channel)

    if current_claim == interaction.user.id:
        ticket_data.pop("claimed_by", None)
        await channel.edit(topic=build_ticket_topic(ticket_data))
        await update_ticket_message(channel)
        await send_log_message(
            interaction.guild,
            title="Ticket libere",
            description=f"{interaction.user.mention} a libere le ticket **{ticket_number}**.",
            color=discord.Color.gold(),
        )
        await safe_followup(interaction, "Tu as libere ce ticket.")
        return

    ticket_data["claimed_by"] = interaction.user.id
    await channel.edit(topic=build_ticket_topic(ticket_data))
    await update_ticket_message(channel)
    await send_log_message(
        interaction.guild,
        title="Ticket claim",
        description=f"{interaction.user.mention} a claim le ticket **{ticket_number}**.",
        color=discord.Color.blue(),
    )
    await safe_followup(interaction, "Ticket claim avec succes.")


@bot.tree.command(name="add", description="Ajoute un membre au ticket")
@app_commands.describe(member="Le membre a ajouter")
async def add_member(interaction: discord.Interaction, member: discord.Member) -> None:
    if not await safe_defer(interaction):
        return

    channel = interaction.channel
    if not interaction.guild or not isinstance(interaction.user, discord.Member) or not isinstance(channel, discord.TextChannel):
        await safe_followup(interaction, "Cette commande doit etre utilisee dans un ticket.")
        return
    if not is_ticket_channel(channel):
        await safe_followup(interaction, "Cette commande doit etre utilisee dans un ticket.")
        return
    if not can_manage_ticket(interaction.user, channel):
        await safe_followup(interaction, "Tu ne peux pas ajouter quelqu'un a ce ticket.")
        return

    await channel.set_permissions(
        member,
        view_channel=True,
        send_messages=True,
        read_message_history=True,
        attach_files=True,
        embed_links=True,
        reason=f"Ajout au ticket par {interaction.user}",
    )
    await send_log_message(
        interaction.guild,
        title="Membre ajoute",
        description=f"{interaction.user.mention} a ajoute {member.mention} au ticket **{get_ticket_number(channel)}**.",
        color=discord.Color.blurple(),
    )
    await safe_followup(interaction, f"{member.mention} a ete ajoute au ticket.")


@bot.tree.command(name="remove", description="Retire un membre du ticket")
@app_commands.describe(member="Le membre a retirer")
async def remove_member(interaction: discord.Interaction, member: discord.Member) -> None:
    if not await safe_defer(interaction):
        return

    channel = interaction.channel
    if not interaction.guild or not isinstance(interaction.user, discord.Member) or not isinstance(channel, discord.TextChannel):
        await safe_followup(interaction, "Cette commande doit etre utilisee dans un ticket.")
        return
    if not is_ticket_channel(channel):
        await safe_followup(interaction, "Cette commande doit etre utilisee dans un ticket.")
        return
    if not can_manage_ticket(interaction.user, channel):
        await safe_followup(interaction, "Tu ne peux pas retirer quelqu'un de ce ticket.")
        return
    if get_ticket_owner_id(channel) == member.id:
        await safe_followup(interaction, "Tu ne peux pas retirer le createur du ticket.")
        return

    await channel.set_permissions(member, overwrite=None, reason=f"Retrait du ticket par {interaction.user}")
    await send_log_message(
        interaction.guild,
        title="Membre retire",
        description=f"{interaction.user.mention} a retire {member.mention} du ticket **{get_ticket_number(channel)}**.",
        color=discord.Color.orange(),
    )
    await safe_followup(interaction, f"{member.mention} a ete retire du ticket.")


@bot.tree.command(name="rename", description="Renomme le ticket courant")
@app_commands.describe(name="Le nouveau nom visible")
async def rename_ticket(interaction: discord.Interaction, name: str) -> None:
    if not await safe_defer(interaction):
        return

    channel = interaction.channel
    if not interaction.guild or not isinstance(interaction.user, discord.Member) or not isinstance(channel, discord.TextChannel):
        await safe_followup(interaction, "Cette commande doit etre utilisee dans un ticket.")
        return
    if not is_ticket_channel(channel):
        await safe_followup(interaction, "Cette commande doit etre utilisee dans un ticket.")
        return
    if not can_manage_ticket(interaction.user, channel):
        await safe_followup(interaction, "Tu ne peux pas renommer ce ticket.")
        return

    final_name = f"{get_ticket_number(channel)}-{sanitize_channel_name(name)}"[:100]
    await channel.edit(name=final_name, reason=f"Ticket renomme par {interaction.user}")
    await send_log_message(
        interaction.guild,
        title="Ticket renomme",
        description=f"{interaction.user.mention} a renomme le ticket en `{final_name}`.",
        color=discord.Color.dark_teal(),
    )
    await safe_followup(interaction, f"Le ticket a ete renomme en `{final_name}`.")


@bot.tree.command(name="avis", description="Publie un avis client")
@app_commands.describe(
    note="Ta note entre 1 et 5",
    ressenti="Ton ressenti sur ta commande et ton experience",
)
@app_commands.choices(
    note=[
        app_commands.Choice(name="1 etoile", value=1),
        app_commands.Choice(name="2 etoiles", value=2),
        app_commands.Choice(name="3 etoiles", value=3),
        app_commands.Choice(name="4 etoiles", value=4),
        app_commands.Choice(name="5 etoiles", value=5),
    ]
)
async def avis(
    interaction: discord.Interaction,
    note: app_commands.Choice[int],
    ressenti: str,
) -> None:
    if not await safe_defer(interaction):
        return

    if not interaction.guild or not isinstance(interaction.user, discord.Member):
        await safe_followup(interaction, "Cette commande doit etre utilisee dans le serveur.")
        return

    review_channel = interaction.guild.get_channel(REVIEW_CHANNEL_ID)
    if not isinstance(review_channel, discord.TextChannel):
        await safe_followup(interaction, "Le salon d'avis est introuvable.")
        return

    try:
        await review_channel.send(embed=build_review_embed(interaction.user, note.value, ressenti[:1024]))
    except discord.Forbidden:
        await safe_followup(interaction, "Je n'ai pas la permission d'envoyer un avis dans ce salon.")
        return

    await safe_followup(interaction, f"Merci, ton avis a ete publie dans {review_channel.mention}.")


@bot.tree.command(name="server", description="Affiche les statistiques principales du serveur")
async def server_stats(interaction: discord.Interaction) -> None:
    if not await safe_defer(interaction):
        return

    if not interaction.guild:
        await safe_followup(interaction, "Cette commande doit etre utilisee dans le serveur.")
        return

    await safe_followup(interaction, embed=build_server_stats_embed(interaction.guild))


@bot.tree.command(name="online", description="Affiche combien de membres sont connectes")
async def online_stats(interaction: discord.Interaction) -> None:
    if not await safe_defer(interaction):
        return

    if not interaction.guild:
        await safe_followup(interaction, "Cette commande doit etre utilisee dans le serveur.")
        return

    await safe_followup(interaction, embed=build_online_embed(interaction.guild))


@bot.tree.command(name="userinfo", description="Affiche les informations d'un membre")
@app_commands.describe(member="Le membre a inspecter")
async def user_info(interaction: discord.Interaction, member: Optional[discord.Member] = None) -> None:
    if not await safe_defer(interaction):
        return

    if not interaction.guild or not isinstance(interaction.user, discord.Member):
        await safe_followup(interaction, "Cette commande doit etre utilisee dans le serveur.")
        return

    target = member or interaction.user
    await safe_followup(interaction, embed=build_user_info_embed(target))


@bot.tree.command(name="ping", description="Affiche la latence du bot")
async def ping_bot(interaction: discord.Interaction) -> None:
    if not await safe_defer(interaction):
        return

    latency_ms = round(bot.latency * 1000)
    embed = discord.Embed(
        title="Ping du bot",
        description=f"Latence actuelle: **{latency_ms} ms**",
        color=discord.Color.green() if latency_ms < 200 else discord.Color.orange(),
        timestamp=datetime.now(timezone.utc),
    )
    await safe_followup(interaction, embed=embed)


@bot.tree.command(name="blacklist", description="Blacklist un membre du systeme de tickets")
@app_commands.default_permissions(manage_guild=True)
@app_commands.describe(member="Le membre a blacklist", reason="La raison de la blacklist")
async def blacklist_member(interaction: discord.Interaction, member: discord.Member, reason: str) -> None:
    if not await safe_defer(interaction):
        return

    blacklist = bot.state.setdefault("ticket_blacklist", DEFAULT_BLACKLIST.copy())
    blacklist[str(member.id)] = {
        "reason": reason[:300],
        "by": str(interaction.user.id),
        "at": datetime.now(timezone.utc).isoformat(),
    }
    save_state(bot.state)
    await safe_followup(interaction, f"{member.mention} a ete blacklist du systeme de tickets.")


@bot.tree.command(name="unblacklist", description="Retire un membre de la blacklist tickets")
@app_commands.default_permissions(manage_guild=True)
@app_commands.describe(member="Le membre a retirer de la blacklist")
async def unblacklist_member(interaction: discord.Interaction, member: discord.Member) -> None:
    if not await safe_defer(interaction):
        return

    blacklist = bot.state.setdefault("ticket_blacklist", DEFAULT_BLACKLIST.copy())
    removed = blacklist.pop(str(member.id), None)
    save_state(bot.state)
    if removed is None:
        await safe_followup(interaction, f"{member.mention} n'etait pas blacklist.")
        return
    await safe_followup(interaction, f"{member.mention} a ete retire de la blacklist.")


@bot.tree.command(name="warn", description="Ajoute un avertissement a un membre")
@app_commands.default_permissions(moderate_members=True)
@app_commands.describe(member="Le membre a avertir", reason="La raison de l'avertissement")
async def warn_member(interaction: discord.Interaction, member: discord.Member, reason: str) -> None:
    if not await safe_defer(interaction):
        return

    warnings_map = bot.state.setdefault("warnings", DEFAULT_WARNINGS.copy())
    entries = warnings_map.setdefault(str(member.id), [])
    entries.append(
        {
            "reason": reason[:500],
            "by": str(interaction.user.id),
            "at": datetime.now(timezone.utc).isoformat(),
        }
    )
    save_state(bot.state)
    await safe_followup(interaction, f"{member.mention} a recu un avertissement. Total: {len(entries)}.")


@bot.tree.command(name="warnings", description="Affiche les avertissements d'un membre")
@app_commands.default_permissions(moderate_members=True)
@app_commands.describe(member="Le membre dont tu veux voir les avertissements")
async def warnings_member(interaction: discord.Interaction, member: discord.Member) -> None:
    if not await safe_defer(interaction):
        return

    entries = get_warning_entries(member.id)
    if not entries:
        await safe_followup(interaction, f"{member.mention} n'a aucun avertissement.")
        return

    lines = [f"Avertissements de {member.mention} : {len(entries)} total"]
    for index, entry in enumerate(entries[-5:], start=max(1, len(entries) - 4)):
        reason = entry.get("reason", "Aucune raison")
        lines.append(f"{index}. {reason}")
    await safe_followup(interaction, "\n".join(lines))


@bot.tree.command(name="clearwarnings", description="Efface tous les avertissements d'un membre")
@app_commands.default_permissions(moderate_members=True)
@app_commands.describe(member="Le membre dont tu veux effacer les avertissements")
async def clearwarnings_member(interaction: discord.Interaction, member: discord.Member) -> None:
    if not await safe_defer(interaction):
        return

    warnings_map = bot.state.setdefault("warnings", DEFAULT_WARNINGS.copy())
    removed = warnings_map.pop(str(member.id), None)
    save_state(bot.state)
    if removed is None:
        await safe_followup(interaction, f"{member.mention} n'avait aucun avertissement.")
        return
    await safe_followup(interaction, f"Les avertissements de {member.mention} ont ete effaces.")


@bot.tree.command(name="ban", description="Bannit un membre du serveur")
@app_commands.default_permissions(ban_members=True)
@app_commands.describe(member="Le membre a bannir", reason="La raison du ban")
async def ban_member(
    interaction: discord.Interaction,
    member: discord.Member,
    reason: str = "Aucune raison precisee",
) -> None:
    if not await safe_defer(interaction):
        return

    if not interaction.guild or not isinstance(interaction.user, discord.Member):
        await safe_followup(interaction, "Cette commande doit etre utilisee dans le serveur.")
        return
    if member.id == interaction.user.id:
        await safe_followup(interaction, "Tu ne peux pas te bannir toi-meme.")
        return

    try:
        await interaction.guild.ban(member, reason=f"{reason} | par {interaction.user}")
    except discord.Forbidden:
        await safe_followup(interaction, "Je n'ai pas la permission de bannir ce membre.")
        return

    await safe_followup(interaction, f"{member} a ete banni.")


@bot.tree.command(name="unban", description="Debannit un membre du serveur")
@app_commands.default_permissions(ban_members=True)
@app_commands.describe(user_id="L'ID du membre a debannir", reason="La raison du deban")
async def unban_member(
    interaction: discord.Interaction,
    user_id: str,
    reason: str = "Aucune raison precisee",
) -> None:
    if not await safe_defer(interaction):
        return

    if not interaction.guild:
        await safe_followup(interaction, "Cette commande doit etre utilisee dans le serveur.")
        return

    try:
        target_id = int(user_id)
    except ValueError:
        await safe_followup(interaction, "L'ID fourni n'est pas valide.")
        return

    try:
        await interaction.guild.unban(discord.Object(id=target_id), reason=f"{reason} | par {interaction.user}")
    except discord.NotFound:
        await safe_followup(interaction, "Aucun ban trouve pour cet ID.")
        return
    except discord.Forbidden:
        await safe_followup(interaction, "Je n'ai pas la permission de debannir cet utilisateur.")
        return

    await safe_followup(interaction, f"L'utilisateur `{target_id}` a ete debanni.")


def main() -> None:
    token = get_required_env("DISCORD_TOKEN")
    bot.run(token, log_handler=None)


if __name__ == "__main__":
    main()
