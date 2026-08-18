import threading
from http.server import HTTPServer, BaseHTTPRequestHandler

import discord
from discord import app_commands
from discord.ext import tasks

import json
import aiohttp
import os
import asyncio

from datetime import datetime, timedelta, time
from dotenv import load_dotenv


load_dotenv()


# ============================================================
# SERVEUR WEB — RENDER
# ============================================================

class HealthHandler(BaseHTTPRequestHandler):

    def do_GET(self):

        self.send_response(200)

        self.send_header(
            "Content-Type",
            "text/plain; charset=utf-8"
        )

        self.end_headers()

        self.wfile.write(
            b"Aethoria Bot is online!"
        )

    def log_message(self, format, *args):
        pass


def start_web_server():

    port = int(
        os.environ.get(
            "PORT",
            10000
        )
    )

    server = HTTPServer(
        ("0.0.0.0", port),
        HealthHandler
    )

    print(
        f"🌐 Serveur web lancé sur le port {port}"
    )

    server.serve_forever()


threading.Thread(
    target=start_web_server,
    daemon=True
).start()


# ============================================================
# CONFIGURATION
# ============================================================

TOKEN = os.getenv(
    "DISCORD_TOKEN"
)

FICHIER_TOURNOI = "invites.json"

DUREE_VALIDATION = 24 * 60 * 60

CATEGORIE_ROYAUME = "「 🏰・ROYAUME 」"

TABLEAU_DE_BORD = "📊・tableau-de-bord"

SALON_STATISTIQUES = "📈・statistiques"


# ============================================================
# SERVEURS MINECRAFT
# ============================================================

SERVEUR_MINECRAFT = "aethoria.omgcraft.fr"

SERVEUR_BEDROCK = "Aethoria.aternos.me"

PORT_BEDROCK = 27496


# ============================================================
# INTENTS
# ============================================================

intents = discord.Intents.default()

intents.members = True

bot = discord.Client(
    intents=intents
)

tree = app_commands.CommandTree(bot)


# ============================================================
# DONNÉES PAR DÉFAUT
# ============================================================

def donnees_par_defaut():

    return {

        "actif": False,

        "invites": {},

        "en_attente": {},

        "snapshots": {},

        "royaumes": {},

        "statistiques": {

            "record_discord": 0,

            "record_java": 0,

            "record_bedrock": 0,

            "record_total": 0,

            "historique": {},

            "membres_rejoint": {},

            "membres_partis": {}
        }
    }


# ============================================================
# CHARGEMENT DES DONNÉES
# ============================================================

def charger_donnees():

    if not os.path.exists(
        FICHIER_TOURNOI
    ):

        return donnees_par_defaut()

    try:

        with open(
            FICHIER_TOURNOI,
            "r",
            encoding="utf-8"
        ) as fichier:

            donnees_chargees = json.load(
                fichier
            )

        donnees_chargees.setdefault(
            "actif",
            False
        )

        donnees_chargees.setdefault(
            "invites",
            {}
        )

        donnees_chargees.setdefault(
            "en_attente",
            {}
        )

        donnees_chargees.setdefault(
            "snapshots",
            {}
        )

        donnees_chargees.setdefault(
            "royaumes",
            {}
        )

        donnees_chargees.setdefault(
            "statistiques",
            {}
        )

        statistiques = donnees_chargees[
            "statistiques"
        ]

        statistiques.setdefault(
            "record_discord",
            0
        )

        statistiques.setdefault(
            "record_java",
            0
        )

        statistiques.setdefault(
            "record_bedrock",
            0
        )

        statistiques.setdefault(
            "record_total",
            0
        )

        statistiques.setdefault(
            "historique",
            {}
        )

        statistiques.setdefault(
            "membres_rejoint",
            {}
        )

        statistiques.setdefault(
            "membres_partis",
            {}
        )

        return donnees_chargees

    except Exception as erreur:

        print(
            f"⚠️ Erreur chargement données : {erreur}"
        )

        return donnees_par_defaut()


donnees = charger_donnees()


# ============================================================
# SAUVEGARDE
# ============================================================

def sauvegarder():

    try:

        fichier_temp = (
            FICHIER_TOURNOI + ".tmp"
        )

        with open(
            fichier_temp,
            "w",
            encoding="utf-8"
        ) as fichier:

            json.dump(
                donnees,
                fichier,
                indent=4,
                ensure_ascii=False
            )

        os.replace(
            fichier_temp,
            FICHIER_TOURNOI
        )

    except Exception as erreur:

        print(
            f"❌ Erreur sauvegarde : {erreur}"
        )


# ============================================================
# OUTILS DATES
# ============================================================

def date_aujourdhui():

    return datetime.now().strftime(
        "%Y-%m-%d"
    )


# ============================================================
# STATISTIQUES MEMBRES
# ============================================================

def enregistrer_evenement_membre(
    guild_id,
    type_evenement
):

    aujourd_hui = date_aujourdhui()

    statistiques = donnees[
        "statistiques"
    ]

    cle = (
        f"{guild_id}:{aujourd_hui}"
    )

    statistiques[
        type_evenement
    ].setdefault(
        cle,
        0
    )

    statistiques[
        type_evenement
    ][cle] += 1

    sauvegarder()


def compter_evenements(
    guild_id,
    type_evenement,
    jours
):

    statistiques = donnees[
        "statistiques"
    ]

    resultat = 0

    for i in range(jours):

        jour = (
            datetime.now()
            - timedelta(days=i)
        ).strftime(
            "%Y-%m-%d"
        )

        cle = (
            f"{guild_id}:{jour}"
        )

        resultat += statistiques[
            type_evenement
        ].get(
            cle,
            0
        )

    return resultat


# ============================================================
# HISTORIQUE
# ============================================================

def enregistrer_historique(
    guild,
    membres,
    java_joueurs,
    bedrock_joueurs
):

    aujourd_hui = date_aujourdhui()

    guild_id = str(
        guild.id
    )

    historique = donnees[
        "statistiques"
    ][
        "historique"
    ]

    historique.setdefault(
        guild_id,
        {}
    )

    if aujourd_hui not in historique[
        guild_id
    ]:

        historique[
            guild_id
        ][aujourd_hui] = {

            "discord": membres,

            "java_max": java_joueurs,

            "bedrock_max": bedrock_joueurs,

            "total_max": (
                java_joueurs
                + bedrock_joueurs
            )
        }

    else:

        jour = historique[
            guild_id
        ][aujourd_hui]

        jour[
            "discord"
        ] = membres

        jour[
            "java_max"
        ] = max(
            jour.get(
                "java_max",
                0
            ),
            java_joueurs
        )

        jour[
            "bedrock_max"
        ] = max(
            jour.get(
                "bedrock_max",
                0
            ),
            bedrock_joueurs
        )

        jour[
            "total_max"
        ] = max(
            jour.get(
                "total_max",
                0
            ),
            java_joueurs
            + bedrock_joueurs
        )

    dates = sorted(
        historique[
            guild_id
        ].keys()
    )

    while len(dates) > 30:

        ancienne_date = dates.pop(0)

        del historique[
            guild_id
        ][ancienne_date]

    sauvegarder()


# ============================================================
# SNAPSHOT INVITATIONS
# ============================================================

async def prendre_snapshot(
    guild
):

    try:

        invitations = await guild.invites()

        snapshot = {}

        for invitation in invitations:

            snapshot[
                invitation.code
            ] = (
                invitation.uses
                or 0
            )

        donnees[
            "snapshots"
        ][
            str(guild.id)
        ] = snapshot

        sauvegarder()

        print(
            f"📸 Snapshot invitations : "
            f"{guild.name} "
            f"({len(snapshot)} invitations)"
        )

        return snapshot

    except discord.Forbidden:

        print(
            f"❌ Impossible de récupérer "
            f"les invitations : {guild.name}"
        )

        return None

    except Exception as erreur:

        print(
            f"❌ Erreur snapshot : {erreur}"
        )

        return None


# ============================================================
# DÉTECTER L'INVITATION UTILISÉE
# ============================================================

async def trouver_inviteur(
    guild
):

    try:

        invitations = await guild.invites()

        snapshot = donnees[
            "snapshots"
        ].get(
            str(guild.id),
            {}
        )

        invitation_trouvee = None

        plus_grande_difference = 0

        nouveau_snapshot = {}

        for invitation in invitations:

            anciennes_utilisations = (
                snapshot.get(
                    invitation.code,
                    0
                )
            )

            nouvelles_utilisations = (
                invitation.uses
                or 0
            )

            difference = (
                nouvelles_utilisations
                - anciennes_utilisations
            )

            if (
                difference
                > plus_grande_difference
            ):

                plus_grande_difference = (
                    difference
                )

                invitation_trouvee = (
                    invitation
                )

            nouveau_snapshot[
                invitation.code
            ] = nouvelles_utilisations

        donnees[
            "snapshots"
        ][
            str(guild.id)
        ] = nouveau_snapshot

        sauvegarder()

        if invitation_trouvee:

            return invitation_trouvee.inviter

    except discord.Forbidden:

        print(
            f"❌ Impossible de lire "
            f"les invitations de {guild.name}"
        )

    except Exception as erreur:

        print(
            f"❌ Erreur invitations : {erreur}"
        )

    return None


# ============================================================
# TÂCHES VALIDATION
# ============================================================

taches_validation = {}


def supprimer_tache_validation(
    membre_id
):

    tache = taches_validation.pop(
        str(membre_id),
        None
    )

    if tache:

        tache.cancel()


# ============================================================
# VALIDATION INVITATION
# ============================================================

async def valider_invitation(
    member_id,
    guild_id,
    secondes_attente
):

    try:

        if secondes_attente > 0:

            await asyncio.sleep(
                secondes_attente
            )

        membre_id = str(
            member_id
        )

        invitation = donnees[
            "en_attente"
        ].get(
            membre_id
        )

        if not invitation:

            return

        guild = bot.get_guild(
            guild_id
        )

        if not guild:

            return

        membre = guild.get_member(
            member_id
        )

        if not membre:

            del donnees[
                "en_attente"
            ][membre_id]

            sauvegarder()

            print(
                f"❌ Invitation annulée : "
                f"{member_id} a quitté."
            )

            return

        inviter_id = str(
            invitation[
                "inviteur"
            ]
        )

        donnees[
            "invites"
        ].setdefault(
            inviter_id,
            0
        )

        donnees[
            "invites"
        ][inviter_id] += 1

        del donnees[
            "en_attente"
        ][membre_id]

        sauvegarder()

        print(
            "======================================"
        )

        print(
            "🏆 INVITATION VALIDÉE"
        )

        print(
            f"Inviteur : {inviter_id}"
        )

        print(
            "Point gagné : +1"
        )

        print(
            "======================================"
        )

    except asyncio.CancelledError:

        return

    finally:

        taches_validation.pop(
            str(member_id),
            None
        )


# ============================================================
# RESTAURATION VALIDATIONS
# ============================================================

def restaurer_validations():

    if not donnees[
        "actif"
    ]:

        return

    maintenant = datetime.utcnow()

    for membre_id, invitation in list(
        donnees[
            "en_attente"
        ].items()
    ):

        try:

            date_validation = (
                datetime.fromisoformat(
                    invitation[
                        "validation"
                    ]
                )
            )

            secondes = (
                date_validation
                - maintenant
            ).total_seconds()

            if secondes <= 0:

                secondes = 0

            tache = asyncio.create_task(
                valider_invitation(
                    int(membre_id),
                    int(
                        invitation[
                            "guild"
                        ]
                    ),
                    secondes
                )
            )

            taches_validation[
                membre_id
            ] = tache

        except Exception as erreur:

            print(
                f"❌ Erreur restauration "
                f"{membre_id} : {erreur}"
            )


# ============================================================
# MEMBRE REJOINT
# ============================================================

@bot.event
async def on_member_join(
    member
):

    print(
        f"👤 Nouveau membre : {member}"
    )

    if member.bot:

        return

    enregistrer_evenement_membre(
        member.guild.id,
        "membres_rejoint"
    )

    asyncio.create_task(
        mise_a_jour_complete(
            member.guild
        )
    )

    if not donnees[
        "actif"
    ]:

        return

    inviter = await trouver_inviteur(
        member.guild
    )

    if not inviter:

        return

    membre_id = str(
        member.id
    )

    validation = (
        datetime.utcnow()
        + timedelta(
            seconds=DUREE_VALIDATION
        )
    )

    donnees[
        "en_attente"
    ][membre_id] = {

        "inviteur": inviter.id,

        "guild": member.guild.id,

        "validation": validation.isoformat()
    }

    sauvegarder()

    print(
        "📨 NOUVELLE INVITATION"
    )

    print(
        f"Membre : {member}"
    )

    print(
        f"Inviteur : {inviter}"
    )

    print(
        "⏳ Validation dans 24 heures"
    )

    tache = asyncio.create_task(
        valider_invitation(
            member.id,
            member.guild.id,
            DUREE_VALIDATION
        )
    )

    taches_validation[
        membre_id
    ] = tache


# ============================================================
# MEMBRE QUITTE
# ============================================================

@bot.event
async def on_member_remove(
    member
):

    print(
        f"👋 Membre parti : {member}"
    )

    if member.bot:

        return

    enregistrer_evenement_membre(
        member.guild.id,
        "membres_partis"
    )

    asyncio.create_task(
        mise_a_jour_complete(
            member.guild
        )
    )

    membre_id = str(
        member.id
    )

    if membre_id in donnees[
        "en_attente"
    ]:

        supprimer_tache_validation(
            membre_id
        )

        del donnees[
            "en_attente"
        ][membre_id]

        sauvegarder()


# ============================================================
# PERMISSIONS STAFF
# ============================================================

def peut_gerer(
    interaction: discord.Interaction
):

    return (
        interaction.user.guild_permissions.manage_channels
        or interaction.user.guild_permissions.administrator
    )


# ============================================================
# NETTOYAGE NOM ROYAUME
# ============================================================

def nettoyer_nom_royaume(
    nom
):

    nom = nom.lower().strip()

    nom = nom.replace(
        " ",
        "-"
    )

    caracteres_interdits = [
        "@",
        "#",
        ":",
        "`",
        "*",
        "_"
    ]

    for caractere in caracteres_interdits:

        nom = nom.replace(
            caractere,
            ""
        )

    nom = nom[:80]

    return nom


# ============================================================
# TROUVER LE ROYAUME
# ============================================================

def obtenir_royaume_par_salon(
    salon
):

    if not salon:

        return None

    if not salon.name.startswith(
        "🔒・"
    ):

        return None

    return donnees[
        "royaumes"
    ].get(
        str(salon.id)
    )


# ============================================================
# VÉRIFIER PROPRIÉTAIRE OU STAFF
# Le propriétaire ET le staff ayant « Gérer les salons »
# peuvent gérer le royaume.
# ============================================================

def est_proprietaire_ou_staff(
    interaction,
    royaume
):

    if not royaume:

        return False

    if peut_gerer(
        interaction
    ):

        return True

    return (
        str(
            interaction.user.id
        )
        == str(
            royaume[
                "proprietaire"
            ]
        )
    )


# ============================================================
# PERMISSIONS ROYAUME
# ============================================================

def permissions_royaume(
    guild,
    createur
):

    overwrites = {

        guild.default_role:
            discord.PermissionOverwrite(
                view_channel=False
            ),

        createur:
            discord.PermissionOverwrite(
                view_channel=True,
                send_messages=True,
                read_message_history=True,
                connect=True,
                speak=True
            )
    }

    if guild.me:

        overwrites[
            guild.me
        ] = discord.PermissionOverwrite(

            view_channel=True,

            send_messages=True,

            read_message_history=True,

            connect=True,

            speak=True,

            manage_channels=True,

            manage_permissions=True
        )

    return overwrites


# ============================================================
# /SALON
# ============================================================

@tree.command(
    name="salon",
    description="Gérer ton salon de royaume"
)
@app_commands.describe(
    action="Action à effectuer",
    salon="Salon textuel du royaume",
    nom="Nom du royaume",
    membre="Membre concerné"
)
@app_commands.choices(
    action=[

        app_commands.Choice(
            name="Créer",
            value="creer"
        ),

        app_commands.Choice(
            name="Supprimer",
            value="supprimer"
        ),

        app_commands.Choice(
            name="Renommer",
            value="renommer"
        ),

        app_commands.Choice(
            name="Ajouter",
            value="ajouter"
        ),

        app_commands.Choice(
            name="Retirer",
            value="retirer"
        )
    ]
)
async def salon(
    interaction: discord.Interaction,
    action: app_commands.Choice[str],
    salon: discord.TextChannel | None = None,
    nom: str | None = None,
    membre: discord.Member | None = None
):

    if interaction.guild is None:

        await interaction.response.send_message(
            "❌ Cette commande doit être utilisée sur un serveur Discord.",
            ephemeral=True
        )

        return

    # ========================================================
    # CRÉER
    # ACCESSIBLE À TOUT LE MONDE
    # ========================================================

    if action.value == "creer":

        if not nom:

            await interaction.response.send_message(
                "❌ Indique le nom de ton royaume.",
                ephemeral=True
            )

            return

        nom = nettoyer_nom_royaume(
            nom
        )

        if not nom:

            await interaction.response.send_message(
                "❌ Le nom du royaume est invalide.",
                ephemeral=True
            )

            return

        categorie = discord.utils.get(
            interaction.guild.categories,
            name=CATEGORIE_ROYAUME
        )

        if not categorie:

            await interaction.response.send_message(
                f"❌ La catégorie "
                f"`{CATEGORIE_ROYAUME}` "
                "n'existe pas.\n\n"
                "Demande au staff de la créer.",
                ephemeral=True
            )

            return

        nom_textuel = (
            f"🔒・{nom}"
        )

        nom_vocal = (
            f"🔊・{nom}"
        )

        textuel_existant = discord.utils.get(
            interaction.guild.text_channels,
            name=nom_textuel
        )

        vocal_existant = discord.utils.get(
            interaction.guild.voice_channels,
            name=nom_vocal
        )

        if (
            textuel_existant
            or vocal_existant
        ):

            await interaction.response.send_message(
                f"❌ Le royaume "
                f"**{nom}** existe déjà.",
                ephemeral=True
            )

            return

        permissions = permissions_royaume(
            interaction.guild,
            interaction.user
        )

        try:

            salon_textuel = (
                await interaction.guild.create_text_channel(
                    name=nom_textuel,
                    category=categorie,
                    overwrites=permissions,
                    reason=(
                        f"Création du royaume "
                        f"{nom} par "
                        f"{interaction.user}"
                    )
                )
            )

            try:

                salon_vocal = (
                    await interaction.guild.create_voice_channel(
                        name=nom_vocal,
                        category=categorie,
                        overwrites=permissions,
                        reason=(
                            f"Création du royaume "
                            f"{nom} par "
                            f"{interaction.user}"
                        )
                    )
                )

            except Exception:

                await salon_textuel.delete()

                raise

        except discord.Forbidden:

            await interaction.response.send_message(
                "❌ Le bot n'a pas les permissions "
                "nécessaires pour créer le royaume.",
                ephemeral=True
            )

            return

        except discord.HTTPException as erreur:

            print(
                f"❌ Erreur création royaume : {erreur}"
            )

            await interaction.response.send_message(
                "❌ Une erreur Discord est survenue "
                "pendant la création.",
                ephemeral=True
            )

            return

        # ====================================================
        # ENREGISTREMENT DU PROPRIÉTAIRE
        # ====================================================

        donnees[
            "royaumes"
        ][
            str(salon_textuel.id)
        ] = {

            "proprietaire": interaction.user.id,

            "nom": nom,

            "salon_textuel": salon_textuel.id,

            "salon_vocal": salon_vocal.id,

            "guild": interaction.guild.id,

            "membres": [
                interaction.user.id
            ]
        }

        sauvegarder()

        await interaction.response.send_message(

            "🏰 **ROYAUME CRÉÉ !**\n\n"

            f"👑 Propriétaire : "
            f"{interaction.user.mention}\n\n"

            f"💬 Salon : "
            f"{salon_textuel.mention}\n\n"

            f"🔊 Vocal : "
            f"**{salon_vocal.name}**\n\n"

            "🔒 Ton royaume est privé.\n"
            "➕ Tu peux ajouter des membres avec "
            "`/salon ajouter`.\n"
            "➖ Tu peux les retirer avec "
            "`/salon retirer`.\n"
            "🗑️ Tu peux supprimer ton royaume avec "
            "`/salon supprimer`."
        )

        return

    # ========================================================
    # LES AUTRES ACTIONS NÉCESSITENT UN SALON
    # ========================================================

    if not salon:

        await interaction.response.send_message(
            "❌ Sélectionne le salon textuel "
            "de ton royaume.",
            ephemeral=True
        )

        return

    if not salon.name.startswith(
        "🔒・"
    ):

        await interaction.response.send_message(
            "❌ Ce salon n'est pas un salon "
            "de royaume.",
            ephemeral=True
        )

        return

    royaume = obtenir_royaume_par_salon(
        salon
    )

    # ========================================================
    # COMPATIBILITÉ ANCIENS ROYAUMES
    # ========================================================

    if royaume is None:

        await interaction.response.send_message(
            "❌ Ce royaume n'est pas enregistré "
            "dans les données du bot.\n\n"
            "Il a probablement été créé avant "
            "l'installation de ce système.",
            ephemeral=True
        )

        return

    # ========================================================
    # PERMISSION PROPRIÉTAIRE / STAFF
    # ========================================================

    if not est_proprietaire_ou_staff(
        interaction,
        royaume
    ):

        await interaction.response.send_message(
            "❌ **Accès refusé.**\n\n"
            "Seul le propriétaire de ce royaume "
            "ou un membre du staff ayant "
            "**Gérer les salons** peut effectuer "
            "cette action.",
            ephemeral=True
        )

        return

    nom_royaume = royaume[
        "nom"
    ]

    vocal = interaction.guild.get_channel(
        royaume[
            "salon_vocal"
        ]
    )

    # ========================================================
    # SUPPRIMER
    # ========================================================

    if action.value == "supprimer":

        try:

            if vocal:

                await vocal.delete(
                    reason=(
                        f"Suppression du royaume "
                        f"{nom_royaume} par "
                        f"{interaction.user}"
                    )
                )

            await salon.delete(
                reason=(
                    f"Suppression du royaume "
                    f"{nom_royaume} par "
                    f"{interaction.user}"
                )
            )

        except discord.Forbidden:

            await interaction.response.send_message(
                "❌ Le bot ne possède pas les "
                "permissions nécessaires.",
                ephemeral=True
            )

            return

        except discord.HTTPException as erreur:

            print(
                f"❌ Erreur suppression : {erreur}"
            )

            await interaction.response.send_message(
                "❌ Une erreur Discord est survenue.",
                ephemeral=True
            )

            return

        donnees[
            "royaumes"
        ].pop(
            str(salon.id),
            None
        )

        sauvegarder()

        await interaction.response.send_message(
            f"🗑️ Le royaume "
            f"**{nom_royaume}** "
            "a été supprimé."
        )

        return

    # ========================================================
    # RENOMMER
    # ========================================================

    if action.value == "renommer":

        if not nom:

            await interaction.response.send_message(
                "❌ Indique le nouveau nom "
                "du royaume.",
                ephemeral=True
            )

            return

        nouveau_nom = nettoyer_nom_royaume(
            nom
        )

        if not nouveau_nom:

            await interaction.response.send_message(
                "❌ Le nouveau nom est invalide.",
                ephemeral=True
            )

            return

        nouveau_textuel = (
            f"🔒・{nouveau_nom}"
        )

        nouveau_vocal = (
            f"🔊・{nouveau_nom}"
        )

        if discord.utils.get(
            interaction.guild.text_channels,
            name=nouveau_textuel
        ):

            await interaction.response.send_message(
                "❌ Ce nom est déjà utilisé.",
                ephemeral=True
            )

            return

        try:

            await salon.edit(
                name=nouveau_textuel,
                reason=(
                    f"Renommage du royaume "
                    f"par {interaction.user}"
                )
            )

            if vocal:

                await vocal.edit(
                    name=nouveau_vocal,
                    reason=(
                        f"Renommage du royaume "
                        f"par {interaction.user}"
                    )
                )

        except discord.Forbidden:

            await interaction.response.send_message(
                "❌ Le bot ne peut pas renommer "
                "ce royaume.",
                ephemeral=True
            )

            return

        except discord.HTTPException:

            await interaction.response.send_message(
                "❌ Une erreur Discord est survenue.",
                ephemeral=True
            )

            return

        royaume[
            "nom"
        ] = nouveau_nom

        royaume[
            "salon_textuel"
        ] = salon.id

        if vocal:

            royaume[
                "salon_vocal"
            ] = vocal.id

        # La clé du dictionnaire reste l'ID du salon,
        # mais celui-ci ne change pas lors d'un renommage.

        sauvegarder()

        await interaction.response.send_message(
            f"✏️ Royaume renommé en "
            f"**{nouveau_nom}**."
        )

        return

    # ========================================================
    # AJOUTER UN MEMBRE
    # ========================================================

    if action.value == "ajouter":

        if not membre:

            await interaction.response.send_message(
                "❌ Indique le membre à ajouter.",
                ephemeral=True
            )

            return

        if membre.bot:

            await interaction.response.send_message(
                "❌ Tu ne peux pas ajouter un bot "
                "à ton royaume.",
                ephemeral=True
            )

            return

        permissions_membre = (
            discord.PermissionOverwrite(
                view_channel=True,
                send_messages=True,
                read_message_history=True,
                connect=True,
                speak=True
            )
        )

        try:

            await salon.set_permissions(
                membre,
                overwrite=permissions_membre,
                reason=(
                    f"Ajout de {membre} au royaume "
                    f"{nom_royaume} par "
                    f"{interaction.user}"
                )
            )

            if vocal:

                await vocal.set_permissions(
                    membre,
                    overwrite=permissions_membre,
                    reason=(
                        f"Ajout de {membre} au royaume "
                        f"{nom_royaume} par "
                        f"{interaction.user}"
                    )
                )

        except discord.Forbidden:

            await interaction.response.send_message(
                "❌ Le bot ne peut pas modifier "
                "les permissions de ce royaume.",
                ephemeral=True
            )

            return

        except discord.HTTPException:

            await interaction.response.send_message(
                "❌ Une erreur Discord est survenue.",
                ephemeral=True
            )

            return

        membres_royaume = royaume.setdefault(
            "membres",
            []
        )

        if membre.id not in membres_royaume:

            membres_royaume.append(
                membre.id
            )

        sauvegarder()

        await interaction.response.send_message(
            f"➕ {membre.mention} a été ajouté "
            f"au royaume **{nom_royaume}**."
        )

        return

    # ========================================================
    # RETIRER UN MEMBRE
    # ========================================================

    if action.value == "retirer":

        if not membre:

            await interaction.response.send_message(
                "❌ Indique le membre à retirer.",
                ephemeral=True
            )

            return

        if membre.id == int(
            royaume[
                "proprietaire"
            ]
        ):

            await interaction.response.send_message(
                "❌ Tu ne peux pas retirer "
                "le propriétaire du royaume.",
                ephemeral=True
            )

            return

        try:

            await salon.set_permissions(
                membre,
                overwrite=None,
                reason=(
                    f"Retrait de {membre} du royaume "
                    f"{nom_royaume} par "
                    f"{interaction.user}"
                )
            )

            if vocal:

                await vocal.set_permissions(
                    membre,
                    overwrite=None,
                    reason=(
                        f"Retrait de {membre} du royaume "
                        f"{nom_royaume} par "
                        f"{interaction.user}"
                    )
                )

        except discord.Forbidden:

            await interaction.response.send_message(
                "❌ Le bot ne peut pas modifier "
                "les permissions de ce royaume.",
                ephemeral=True
            )

            return

        except discord.HTTPException:

            await interaction.response.send_message(
                "❌ Une erreur Discord est survenue.",
                ephemeral=True
            )

            return

        membres_royaume = royaume.setdefault(
            "membres",
            []
        )

        if membre.id in membres_royaume:

            membres_royaume.remove(
                membre.id
            )

        sauvegarder()

        await interaction.response.send_message(
            f"➖ {membre.mention} a été retiré "
            f"du royaume **{nom_royaume}**."
        )

        return


# ============================================================
# MCSTATUS — SESSION HTTP
# ============================================================

session_http = None


async def obtenir_session_http():

    global session_http

    if (
        session_http is None
        or session_http.closed
    ):

        timeout = aiohttp.ClientTimeout(
            total=6
        )

        session_http = (
            aiohttp.ClientSession(
                timeout=timeout
            )
        )

    return session_http


# ============================================================
# STATUT JAVA
# ============================================================

async def obtenir_statut_minecraft():

    minecraft_en_ligne = False

    minecraft_joueurs = 0

    minecraft_max = 0

    try:

        session = (
            await obtenir_session_http()
        )

        url = (
            "https://api.mcstatus.io/v2/status/java/"
            f"{SERVEUR_MINECRAFT}"
        )

        async with session.get(
            url
        ) as response:

            if response.status == 200:

                minecraft = (
                    await response.json()
                )

                minecraft_en_ligne = (
                    minecraft.get(
                        "online",
                        False
                    )
                )

                if minecraft_en_ligne:

                    joueurs = (
                        minecraft.get(
                            "players",
                            {}
                        )
                    )

                    minecraft_joueurs = (
                        joueurs.get(
                            "online",
                            0
                        )
                    )

                    minecraft_max = (
                        joueurs.get(
                            "max",
                            0
                        )
                    )

    except Exception as erreur:

        print(
            f"⚠️ Erreur statut Java : {erreur}"
        )

    return (
        minecraft_en_ligne,
        minecraft_joueurs,
        minecraft_max
    )


# ============================================================
# STATUT BEDROCK
# ============================================================

async def obtenir_statut_bedrock():

    bedrock_en_ligne = False

    bedrock_joueurs = 0

    bedrock_max = 0

    try:

        session = (
            await obtenir_session_http()
        )

        url = (
            "https://api.mcstatus.io/v2/status/bedrock/"
            f"{SERVEUR_BEDROCK}:{PORT_BEDROCK}"
        )

        async with session.get(
            url
        ) as response:

            if response.status == 200:

                bedrock = (
                    await response.json()
                )

                bedrock_en_ligne = (
                    bedrock.get(
                        "online",
                        False
                    )
                )

                if bedrock_en_ligne:

                    joueurs = (
                        bedrock.get(
                            "players",
                            {}
                        )
                    )

                    bedrock_joueurs = (
                        joueurs.get(
                            "online",
                            0
                        )
                    )

                    bedrock_max = (
                        joueurs.get(
                            "max",
                            0
                        )
                    )

    except Exception as erreur:

        print(
            f"⚠️ Erreur statut Bedrock : {erreur}"
        )

    return (
        bedrock_en_ligne,
        bedrock_joueurs,
        bedrock_max
    )


# ============================================================
# STATISTIQUES
# ============================================================

async def mettre_a_jour_statistiques(
    guild
):

    if guild is None:

        return

    membres = sum(
        1
        for membre in guild.members
        if not membre.bot
    )

    (
        java_en_ligne,
        java_joueurs,
        java_max
    ) = await obtenir_statut_minecraft()

    (
        bedrock_en_ligne,
        bedrock_joueurs,
        bedrock_max
    ) = await obtenir_statut_bedrock()

    statistiques = donnees[
        "statistiques"
    ]

    if membres > statistiques[
        "record_discord"
    ]:

        statistiques[
            "record_discord"
        ] = membres

    if java_joueurs > statistiques[
        "record_java"
    ]:

        statistiques[
            "record_java"
        ] = java_joueurs

    if bedrock_joueurs > statistiques[
        "record_bedrock"
    ]:

        statistiques[
            "record_bedrock"
        ] = bedrock_joueurs

    total_joueurs = (
        java_joueurs
        + bedrock_joueurs
    )

    if total_joueurs > statistiques[
        "record_total"
    ]:

        statistiques[
            "record_total"
        ] = total_joueurs

    enregistrer_historique(
        guild,
        membres,
        java_joueurs,
        bedrock_joueurs
    )

    sauvegarder()

    return (
        membres,
        java_en_ligne,
        java_joueurs,
        java_max,
        bedrock_en_ligne,
        bedrock_joueurs,
        bedrock_max
    )


# ============================================================
# TABLEAU DE BORD
# ============================================================

async def mettre_a_jour_tableau_de_bord(
    guild_cible=None
):

    guilds = (
        [guild_cible]
        if guild_cible
        else bot.guilds
    )

    for guild in guilds:

        if guild is None:

            continue

        salon_dashboard = discord.utils.get(
            guild.text_channels,
            name=TABLEAU_DE_BORD
        )

        if salon_dashboard is None:

            continue

        resultats = (
            await mettre_a_jour_statistiques(
                guild
            )
        )

        if resultats is None:

            continue

        (
            membres,
            minecraft_en_ligne,
            minecraft_joueurs,
            minecraft_max,
            bedrock_en_ligne,
            bedrock_joueurs,
            bedrock_max
        ) = resultats

        if minecraft_en_ligne:

            minecraft_status = (
                "🟢 **En ligne**\n"
                f"👤 Joueurs : **"
                f"{minecraft_joueurs}/"
                f"{minecraft_max}**"
            )

        else:

            minecraft_status = (
                "🔴 **Hors ligne**"
            )

        if bedrock_en_ligne:

            bedrock_status = (
                "🟢 **En ligne**\n"
                f"👤 Joueurs : **"
                f"{bedrock_joueurs}/"
                f"{bedrock_max}**"
            )

        else:

            bedrock_status = (
                "🔴 **Hors ligne**"
            )

        if donnees[
            "actif"
        ]:

            total_invites = sum(
                donnees[
                    "invites"
                ].values()
            )

            tournoi_status = (
                "🟢 **EN COURS**\n"
                f"🎟️ Invitations validées : "
                f"**{total_invites}**"
            )

        else:

            tournoi_status = (
                "🔴 **AUCUN TOURNOI**"
            )

        contenu = (

            "🏰 **AETHORIA**\n"
            "━━━━━━━━━━━━━━━━━━\n\n"

            f"👥 **Membres Discord :** "
            f"**{membres}**\n\n"

            "⛏️ **AETHORIA JAVA**\n"
            f"{minecraft_status}\n\n"

            "📱 **AETHORIA BEDROCK**\n"
            f"{bedrock_status}\n\n"

            "🏆 **TOURNOI**\n"
            f"{tournoi_status}\n\n"

            "━━━━━━━━━━━━━━━━━━"
        )

        message_trouve = None

        try:

            async for message in (
                salon_dashboard.history(
                    limit=20
                )
            ):

                if (
                    message.author == bot.user
                    and message.content.startswith(
                        "🏰 **AETHORIA**"
                    )
                ):

                    message_trouve = message

                    break

            if message_trouve:

                await message_trouve.edit(
                    content=contenu
                )

            else:

                await salon_dashboard.send(
                    content=contenu
                )

        except discord.Forbidden:

            print(
                f"❌ Impossible de modifier "
                f"le dashboard de {guild.name}"
            )


# ============================================================
# SALON STATISTIQUES
# ============================================================

async def mettre_a_jour_salon_statistiques(
    guild_cible=None
):

    guilds = (
        [guild_cible]
        if guild_cible
        else bot.guilds
    )

    for guild in guilds:

        if guild is None:

            continue

        salon_stats = discord.utils.get(
            guild.text_channels,
            name=SALON_STATISTIQUES
        )

        if salon_stats is None:

            continue

        resultats = (
            await mettre_a_jour_statistiques(
                guild
            )
        )

        if resultats is None:

            continue

        (
            membres,
            java_en_ligne,
            java_joueurs,
            java_max,
            bedrock_en_ligne,
            bedrock_joueurs,
            bedrock_max
        ) = resultats

        statistiques = donnees[
            "statistiques"
        ]

        rejoints_aujourd_hui = (
            compter_evenements(
                guild.id,
                "membres_rejoint",
                1
            )
        )

        partis_aujourd_hui = (
            compter_evenements(
                guild.id,
                "membres_partis",
                1
            )
        )

        rejoints_semaine = (
            compter_evenements(
                guild.id,
                "membres_rejoint",
                7
            )
        )

        partis_semaine = (
            compter_evenements(
                guild.id,
                "membres_partis",
                7
            )
        )

        historique = statistiques[
            "historique"
        ].get(
            str(guild.id),
            {}
        )

        dates = sorted(
            historique.keys()
        )[-7:]

        evolution = []

        for date_jour in dates:

            valeur = historique[
                date_jour
            ].get(
                "discord",
                0
            )

            evolution.append(
                f"`{date_jour[5:]}` : "
                f"**{valeur}**"
            )

        if evolution:

            evolution_texte = (
                "\n".join(
                    evolution
                )
            )

        else:

            evolution_texte = (
                "Pas encore assez de données."
            )

        total_invites = sum(
            donnees[
                "invites"
            ].values()
        )

        attente_invites = len(
            donnees[
                "en_attente"
            ]
        )

        meilleur_inviteur = "Aucun"

        if donnees[
            "invites"
        ]:

            meilleur_id, meilleur_score = max(
                donnees[
                    "invites"
                ].items(),
                key=lambda element: element[1]
            )

            membre_meilleur = (
                guild.get_member(
                    int(meilleur_id)
                )
            )

            if membre_meilleur:

                meilleur_inviteur = (
                    f"{membre_meilleur.mention} "
                    f"— **{meilleur_score}**"
                )

            else:

                meilleur_inviteur = (
                    f"<@{meilleur_id}> "
                    f"— **{meilleur_score}**"
                )

        contenu = (

            "📈 **STATISTIQUES AETHORIA**\n"
            "━━━━━━━━━━━━━━━━━━━━\n\n"

            "👥 **DISCORD**\n"

            f"• Membres actuels : "
            f"**{membres}**\n"

            f"• Aujourd'hui : "
            f"**+{rejoints_aujourd_hui} / "
            f"-{partis_aujourd_hui}**\n"

            f"• Cette semaine : "
            f"**+{rejoints_semaine} / "
            f"-{partis_semaine}**\n"

            f"• Record de membres : "
            f"**{statistiques['record_discord']}**\n\n"

            "⛏️ **MINECRAFT**\n"

            f"• Java : "
            f"**{java_joueurs}/{java_max}** "
            f"{'🟢' if java_en_ligne else '🔴'}\n"

            f"• Bedrock : "
            f"**{bedrock_joueurs}/{bedrock_max}** "
            f"{'🟢' if bedrock_en_ligne else '🔴'}\n"

            f"• Record Java : "
            f"**{statistiques['record_java']}**\n"

            f"• Record Bedrock : "
            f"**{statistiques['record_bedrock']}**\n"

            f"• Record total : "
            f"**{statistiques['record_total']}**\n\n"

            "🏆 **TOURNOI D'INVITATIONS**\n"

            f"• Invitations validées : "
            f"**{total_invites}**\n"

            f"• En attente : "
            f"**{attente_invites}**\n"

            f"• Meilleur inviteur : "
            f"{meilleur_inviteur}\n\n"

            "📊 **ÉVOLUTION DES MEMBRES — "
            "7 JOURS**\n"

            f"{evolution_texte}\n\n"

            "━━━━━━━━━━━━━━━━━━━━\n"

            "`Mise à jour automatique "
            "toutes les minutes`"
        )

        message_trouve = None

        try:

            async for message in (
                salon_stats.history(
                    limit=20
                )
            ):

                if (
                    message.author == bot.user
                    and message.content.startswith(
                        "📈 **STATISTIQUES AETHORIA**"
                    )
                ):

                    message_trouve = message

                    break

            if message_trouve:

                await message_trouve.edit(
                    content=contenu
                )

            else:

                await salon_stats.send(
                    content=contenu
                )

        except discord.Forbidden:

            print(
                f"❌ Impossible de modifier "
                f"les statistiques de {guild.name}"
            )


# ============================================================
# MISE À JOUR COMPLÈTE
# ============================================================

async def mise_a_jour_complete(
    guild_cible=None
):

    guilds = (
        [guild_cible]
        if guild_cible
        else bot.guilds
    )

    for guild in guilds:

        if guild is None:

            continue

        await mettre_a_jour_tableau_de_bord(
            guild
        )

        await mettre_a_jour_salon_statistiques(
            guild
        )


# ============================================================
# BOUCLE — CHAQUE MINUTE
# ============================================================

@tasks.loop(
    minutes=1
)
async def actualiser_tableaux():

    try:

        await mise_a_jour_complete()

    except Exception as erreur:

        print(
            f"❌ Erreur actualisation tableaux : "
            f"{erreur}"
        )


# ============================================================
# BOUCLE — 00H00 / 12H00
# ============================================================

@tasks.loop(
    time=[
        time(
            hour=0,
            minute=0
        ),
        time(
            hour=12,
            minute=0
        )
    ]
)
async def actualiser_midi_minuit():

    print(
        "🕐 Mise à jour programmée 00h00 / 12h00"
    )

    try:

        await mise_a_jour_complete()

    except Exception as erreur:

        print(
            f"❌ Erreur mise à jour "
            f"00h00/12h00 : {erreur}"
        )


# ============================================================
# ERREURS BOUCLES
# ============================================================

@actualiser_tableaux.error
async def erreur_tableaux(
    erreur
):

    print(
        f"❌ Erreur boucle tableaux : "
        f"{erreur}"
    )


@actualiser_midi_minuit.error
async def erreur_midi_minuit(
    erreur
):

    print(
        f"❌ Erreur boucle 00h00/12h00 : "
        f"{erreur}"
    )


# ============================================================
# /TOURNOI
# ============================================================

def peut_gerer_tournoi(
    interaction
):

    return (
        interaction.user.guild_permissions.manage_guild
        or interaction.user.guild_permissions.administrator
    )


@tree.command(
    name="tournoi",
    description="Gérer le tournoi d'invitations"
)
@app_commands.describe(
    action="Action du tournoi"
)
@app_commands.choices(
    action=[

        app_commands.Choice(
            name="Démarrer",
            value="demarrer"
        ),

        app_commands.Choice(
            name="Arrêter",
            value="arreter"
        ),

        app_commands.Choice(
            name="Statut",
            value="statut"
        ),

        app_commands.Choice(
            name="Reset",
            value="reset"
        )
    ]
)
async def tournoi(
    interaction: discord.Interaction,
    action: app_commands.Choice[str]
):

    if not peut_gerer_tournoi(
        interaction
    ):

        await interaction.response.send_message(
            "❌ Tu dois avoir la permission "
            "**Gérer le serveur**.",
            ephemeral=True
        )

        return

    if action.value == "demarrer":

        await interaction.response.defer()

        donnees[
            "actif"
        ] = False

        donnees[
            "invites"
        ] = {}

        donnees[
            "en_attente"
        ] = {}

        for tache in (
            taches_validation.values()
        ):

            tache.cancel()

        taches_validation.clear()

        snapshot = await prendre_snapshot(
            interaction.guild
        )

        if snapshot is None:

            await interaction.followup.send(
                "❌ Impossible de récupérer "
                "les invitations.\n\n"
                "Vérifie que le bot possède "
                "**Gérer le serveur**."
            )

            return

        donnees[
            "actif"
        ] = True

        sauvegarder()

        total_utilisations = sum(
            snapshot.values()
        )

        await interaction.followup.send(
            "🏆 **TOURNOI D'INVITATIONS DÉMARRÉ !**\n\n"
            "📸 Le compteur commence **maintenant**.\n\n"
            f"📨 Invitations existantes ignorées : "
            f"**{total_utilisations} utilisations**\n\n"
            "👤 Seuls les nouveaux membres invités "
            "après maintenant pourront rapporter des points.\n\n"
            "⏳ Le membre doit rester **24 heures** "
            "pour valider le point."
        )

    elif action.value == "arreter":

        donnees[
            "actif"
        ] = False

        for tache in (
            taches_validation.values()
        ):

            tache.cancel()

        taches_validation.clear()

        sauvegarder()

        await interaction.response.send_message(
            "🛑 **Tournoi arrêté.**\n\n"
            "Les nouvelles invitations ne rapporteront "
            "plus de points."
        )

    elif action.value == "statut":

        statut = (
            "🟢 **ACTIF**"
            if donnees[
                "actif"
            ]
            else
            "🔴 **INACTIF**"
        )

        total = sum(
            donnees[
                "invites"
            ].values()
        )

        attente = len(
            donnees[
                "en_attente"
            ]
        )

        await interaction.response.send_message(
            "🏆 **TOURNOI D'INVITATIONS**\n\n"
            f"Statut : {statut}\n"
            f"🏆 Points validés : **{total}**\n"
            f"⏳ En attente : **{attente}**"
        )

    elif action.value == "reset":

        donnees[
            "actif"
        ] = False

        donnees[
            "invites"
        ] = {}

        donnees[
            "en_attente"
        ] = {}

        donnees[
            "snapshots"
        ] = {}

        for tache in (
            taches_validation.values()
        ):

            tache.cancel()

        taches_validation.clear()

        sauvegarder()

        await interaction.response.send_message(
            "🔄 **Tournoi réinitialisé !**\n\n"
            "Toutes les statistiques du tournoi "
            "ont été remises à zéro."
        )


# ============================================================
# /INVITES
# ============================================================

@tree.command(
    name="invites",
    description="Voir les invitations d'un membre"
)
@app_commands.describe(
    membre="Membre à consulter"
)
async def invites(
    interaction: discord.Interaction,
    membre: discord.Member | None = None
):

    membre = (
        membre
        or interaction.user
    )

    membre_id = str(
        membre.id
    )

    points = donnees[
        "invites"
    ].get(
        membre_id,
        0
    )

    attente = sum(

        1

        for invitation in donnees[
            "en_attente"
        ].values()

        if invitation[
            "inviteur"
        ] == membre.id
    )

    await interaction.response.send_message(
        f"📨 **Invitations de "
        f"{membre.display_name}**\n\n"
        f"🏆 Validées : **{points}**\n"
        f"⏳ En attente : **{attente}**"
    )


# ============================================================
# /CLASSEMENT
# ============================================================

@tree.command(
    name="classement",
    description="Voir le classement des invitations"
)
async def classement(
    interaction: discord.Interaction
):

    classement_data = sorted(
        donnees[
            "invites"
        ].items(),
        key=lambda element: element[1],
        reverse=True
    )

    if not classement_data:

        await interaction.response.send_message(
            "🏆 **Classement vide**\n\n"
            "Aucune invitation validée pour le moment."
        )

        return

    texte = (
        "🏆 **CLASSEMENT DES INVITATIONS**\n\n"
    )

    medailles = [
        "🥇",
        "🥈",
        "🥉"
    ]

    for position, (
        user_id,
        points
    ) in enumerate(
        classement_data[:10],
        start=1
    ):

        membre = (
            interaction.guild.get_member(
                int(user_id)
            )
        )

        if membre:

            nom = membre.mention

        else:

            nom = (
                f"<@{user_id}>"
            )

        if position <= 3:

            prefixe = medailles[
                position - 1
            ]

        else:

            prefixe = (
                f"**{position}.**"
            )

        texte += (
            f"{prefixe} {nom} — "
            f"**{points}** invitations\n"
        )

    await interaction.response.send_message(
        texte
    )


# ============================================================
# READY
# ============================================================

@bot.event
async def on_ready():

    print("")
    print(
        "======================================"
    )

    print(
        "🏰 AETHORIA BOT CONNECTÉ"
    )

    print(
        "======================================"
    )

    print(
        f"Bot : {bot.user}"
    )

    print(
        f"Serveurs : {len(bot.guilds)}"
    )

    print("")

    for guild in bot.guilds:

        permissions = (
            guild.me.guild_permissions
        )

        print(
            "===== PERMISSIONS DU BOT ====="
        )

        print(
            f"Serveur : {guild.name}"
        )

        print(
            f"Gérer les salons : "
            f"{permissions.manage_channels}"
        )

        print(
            f"Créer des invitations : "
            f"{permissions.create_instant_invite}"
        )

        print(
            f"Gérer le serveur : "
            f"{permissions.manage_guild}"
        )

        print(
            f"Administrateur : "
            f"{permissions.administrator}"
        )

        print(
            f"Voir les salons : "
            f"{permissions.view_channel}"
        )

        print(
            f"Envoyer des messages : "
            f"{permissions.send_messages}"
        )

        print(
            f"Lire l'historique : "
            f"{permissions.read_message_history}"
        )

        print(
            "==============================="
        )

    # ========================================================
    # SYNCHRONISATION COMMANDES
    # ========================================================

    try:

        await tree.sync()

        print(
            "✅ Commandes slash synchronisées."
        )

    except Exception as erreur:

        print(
            f"❌ Erreur synchronisation : "
            f"{erreur}"
        )

    # ========================================================
    # RESTAURATION VALIDATIONS
    # ========================================================

    restaurer_validations()

    # ========================================================
    # BOUCLES
    # ========================================================

    if not actualiser_tableaux.is_running():

        actualiser_tableaux.start()

    if not actualiser_midi_minuit.is_running():

        actualiser_midi_minuit.start()

    # ========================================================
    # PREMIÈRE MISE À JOUR
    # ========================================================

    try:

        await mise_a_jour_complete()

        print(
            "✅ Tableaux mis à jour."
        )

    except Exception as erreur:

        print(
            f"❌ Erreur première mise à jour : "
            f"{erreur}"
        )

    print(
        "✅ Boucles automatiques activées."
    )

    print(
        "======================================"
    )


# ============================================================
# DÉCONNEXION
# ============================================================

@bot.event
async def on_disconnect():

    print(
        "⚠️ Bot déconnecté de Discord."
    )


# ============================================================
# LANCEMENT
# ============================================================

if not TOKEN:

    print(
        "❌ ERREUR : DISCORD_TOKEN "
        "est introuvable."
    )

else:

    bot.run(
        TOKEN
    )