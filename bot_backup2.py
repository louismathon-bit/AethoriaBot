import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
import discord
from discord import app_commands
import json
import aiohttp
import os
import asyncio
from datetime import datetime, timedelta


class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Aethoria Bot is online!")

    def log_message(self, format, *args):
        pass


def start_web_server():
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(("0.0.0.0", port), HealthHandler)
    server.serve_forever()


threading.Thread(target=start_web_server, daemon=True).start()

# ============================================================
# CONFIGURATION
# ============================================================

TOKEN = os.getenv("DISCORD_TOKEN")

CATEGORIE_ROYAUME = "「 🏰・ROYAUME 」"
DUREE_VALIDATION = 24 * 60 * 60

FICHIER_TOURNOI = "invites.json"


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
# DONNÉES DU TOURNOI
# ============================================================

def donnees_par_defaut():

    return {
        "actif": False,
        "invites": {},
        "en_attente": {},
        "snapshots": {}
    }


def charger_donnees():

    if not os.path.exists(FICHIER_TOURNOI):

        return donnees_par_defaut()

    try:

        with open(
            FICHIER_TOURNOI,
            "r",
            encoding="utf-8"
        ) as fichier:

            donnees = json.load(fichier)

        donnees.setdefault("actif", False)
        donnees.setdefault("invites", {})
        donnees.setdefault("en_attente", {})
        donnees.setdefault("snapshots", {})

        return donnees

    except Exception:

        return donnees_par_defaut()


donnees = charger_donnees()


def sauvegarder():

    with open(
        FICHIER_TOURNOI,
        "w",
        encoding="utf-8"
    ) as fichier:

        json.dump(
            donnees,
            fichier,
            indent=4,
            ensure_ascii=False
        )


# ============================================================
# SNAPSHOT DES INVITATIONS
# ============================================================

async def prendre_snapshot(guild):

    try:

        invitations = await guild.invites()

        snapshot = {}

        for invitation in invitations:

            snapshot[invitation.code] = (
                invitation.uses or 0
            )

        donnees["snapshots"][str(guild.id)] = snapshot

        sauvegarder()

        print("")
        print("📸 SNAPSHOT DES INVITATIONS")
        print(f"🏰 Serveur : {guild.name}")
        print(
            f"📨 Invitations trouvées : "
            f"{len(snapshot)}"
        )
        print("")

        return snapshot

    except discord.Forbidden:

        print(
            f"❌ Impossible de récupérer les "
            f"invitations de : {guild.name}"
        )

        return None

    except Exception as erreur:

        print(
            f"❌ Erreur lors du snapshot : {erreur}"
        )

        return None


# ============================================================
# DÉTECTER L'INVITATION UTILISÉE
# ============================================================

async def trouver_inviteur(guild):

    try:

        invitations = await guild.invites()

        snapshot = donnees["snapshots"].get(
            str(guild.id),
            {}
        )

        invitation_trouvee = None

        plus_grande_difference = 0

        for invitation in invitations:

            anciennes_utilisations = snapshot.get(
                invitation.code,
                0
            )

            nouvelles_utilisations = (
                invitation.uses or 0
            )

            difference = (
                nouvelles_utilisations
                - anciennes_utilisations
            )

            if difference > plus_grande_difference:

                plus_grande_difference = difference

                invitation_trouvee = invitation

        # Mise à jour du snapshot
        nouveau_snapshot = {}

        for invitation in invitations:

            nouveau_snapshot[invitation.code] = (
                invitation.uses or 0
            )

        donnees["snapshots"][str(guild.id)] = (
            nouveau_snapshot
        )

        sauvegarder()

        if invitation_trouvee:

            return invitation_trouvee.inviter

    except discord.Forbidden:

        print(
            f"❌ Impossible de récupérer les "
            f"invitations de : {guild.name}"
        )

    except Exception as erreur:

        print(
            f"❌ Erreur invitations : {erreur}"
        )

    return None


# ============================================================
# MEMBRE QUI REJOINT
# ============================================================

@bot.event
async def on_member_join(member):

    print(
        f"👤 Nouveau membre : {member}"
    )

    # Les bots ne participent pas
    if member.bot:

        print(
            "🤖 Membre ignoré : c'est un bot."
        )

        return

    # Tournoi inactif
    if not donnees["actif"]:

        print(
            "ℹ️ Tournoi inactif : aucun point."
        )

        return

    inviter = await trouver_inviteur(
        member.guild
    )

    if not inviter:

        print(
            f"⚠️ Impossible de déterminer "
            f"l'inviteur de {member}."
        )

        return

    # Empêcher une donnée précédente
    # d'écraser la nouvelle
    membre_id = str(member.id)

    validation = (
        datetime.utcnow()
        + timedelta(seconds=DUREE_VALIDATION)
    )

    donnees["en_attente"][membre_id] = {

        "inviteur": inviter.id,

        "guild": member.guild.id,

        "validation": validation.isoformat()
    }

    sauvegarder()

    print("")
    print("======================================")
    print("📨 NOUVELLE INVITATION")
    print("======================================")
    print(f"👤 Membre : {member}")
    print(f"👑 Inviteur : {inviter}")
    print("⏳ Validation dans 24 heures")
    print("======================================")
    print("")

    asyncio.create_task(
        valider_invitation(
            member.id,
            member.guild.id
        )
    )


# ============================================================
# VALIDATION APRÈS 24 HEURES
# ============================================================

async def valider_invitation(
    member_id,
    guild_id
):

    await asyncio.sleep(
        DUREE_VALIDATION
    )

    membre_id = str(member_id)

    invitation = donnees["en_attente"].get(
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

    # Le membre a quitté
    if not membre:

        del donnees["en_attente"][
            membre_id
        ]

        sauvegarder()

        print(
            f"❌ Invitation annulée : "
            f"{member_id} a quitté."
        )

        return

    inviter_id = str(
        invitation["inviteur"]
    )

    if inviter_id not in donnees["invites"]:

        donnees["invites"][inviter_id] = 0

    donnees["invites"][inviter_id] += 1

    del donnees["en_attente"][
        membre_id
    ]

    sauvegarder()

    print("")
    print("======================================")
    print("🏆 INVITATION VALIDÉE")
    print("======================================")
    print(
        f"👑 Inviteur : <@{inviter_id}>"
    )
    print("➕ Point gagné : +1")
    print("======================================")
    print("")


# ============================================================
# MEMBRE QUI QUITTE
# ============================================================

@bot.event
async def on_member_remove(member):

    membre_id = str(
        member.id
    )

    if membre_id in donnees["en_attente"]:

        del donnees["en_attente"][
            membre_id
        ]

        sauvegarder()

        print(
            f"❌ {member} a quitté avant "
            f"la validation des 24h."
        )


# ============================================================
# /TOURNOI
# ============================================================

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

    # Permission administrateur du serveur
    if not interaction.user.guild_permissions.manage_guild:

        await interaction.response.send_message(
            "❌ Tu dois avoir la permission "
            "**Gérer le serveur**.",
            ephemeral=True
        )

        return


    # ========================================================
    # DÉMARRER
    # ========================================================

    if action.value == "demarrer":

        await interaction.response.defer()

        # Nouveau tournoi
        donnees["actif"] = False

        donnees["invites"] = {}

        donnees["en_attente"] = {}

        # IMPORTANT :
        # On prend le snapshot exactement maintenant
        snapshot = await prendre_snapshot(
            interaction.guild
        )

        if snapshot is None:

            await interaction.followup.send(
                "❌ Impossible de récupérer les "
                "invitations.\n\n"
                "Le bot doit avoir les permissions "
                "nécessaires pour lire les invitations."
            )

            return

        donnees["actif"] = True

        sauvegarder()

        total_utilisations = sum(
            snapshot.values()
        )

        await interaction.followup.send(

            "🏆 **TOURNOI D'INVITATIONS DÉMARRÉ !**\n\n"

            "📸 Le compteur commence "
            "**maintenant**.\n\n"

            f"📨 Invitations existantes ignorées : "
            f"**{total_utilisations} utilisations**\n\n"

            "👤 Seuls les nouveaux membres "
            "invités après maintenant pourront "
            "rapporter des points.\n\n"

            "⏳ Le membre doit rester "
            "**24 heures** pour valider le point."
        )

        print("")
        print("======================================")
        print("🏆 TOURNOI DÉMARRÉ")
        print("======================================")
        print(
            f"📨 Utilisations initiales : "
            f"{total_utilisations}"
        )
        print("======================================")
        print("")


    # ========================================================
    # ARRÊTER
    # ========================================================

    elif action.value == "arreter":

        donnees["actif"] = False

        sauvegarder()

        await interaction.response.send_message(

            "🛑 **Tournoi arrêté.**\n\n"

            "Les nouvelles invitations ne "
            "rapporteront plus de points."
        )


    # ========================================================
    # STATUT
    # ========================================================

    elif action.value == "statut":

        statut = (
            "🟢 **ACTIF**"
            if donnees["actif"]
            else
            "🔴 **INACTIF**"
        )

        total = sum(
            donnees["invites"].values()
        )

        attente = len(
            donnees["en_attente"]
        )

        await interaction.response.send_message(

            f"🏆 **TOURNOI D'INVITATIONS**\n\n"

            f"Statut : {statut}\n"

            f"🏆 Points validés : **{total}**\n"

            f"⏳ En attente : **{attente}**"
        )


    # ========================================================
    # RESET
    # ========================================================

    elif action.value == "reset":

        donnees["actif"] = False

        donnees["invites"] = {}

        donnees["en_attente"] = {}

        donnees["snapshots"] = {}

        sauvegarder()

        await interaction.response.send_message(

            "🔄 **Tournoi réinitialisé !**\n\n"

            "Toutes les statistiques ont été "
            "remises à zéro."
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

    membre = membre or interaction.user

    membre_id = str(
        membre.id
    )

    points = donnees["invites"].get(
        membre_id,
        0
    )

    attente = sum(

        1

        for invitation
        in donnees["en_attente"].values()

        if invitation["inviteur"] == membre.id
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

        donnees["invites"].items(),

        key=lambda element: element[1],

        reverse=True
    )

    if not classement_data:

        await interaction.response.send_message(

            "🏆 **Classement vide**\n\n"
            "Aucune invitation validée pour "
            "le moment."
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

    for position, (user_id, points) in enumerate(

        classement_data[:10],

        start=1
    ):

        membre = interaction.guild.get_member(
            int(user_id)
        )

        if membre:

            nom = membre.mention

        else:

            nom = f"<@{user_id}>"

        if position <= 3:

            prefixe = medailles[
                position - 1
            ]

        else:

            prefixe = f"**{position}.**"

        texte += (
            f"{prefixe} {nom} — "
            f"**{points}** invitations\n"
        )

    await interaction.response.send_message(
        texte
    )


# ============================================================
# SYSTÈME DES ROYAUMES
# ============================================================

def peut_gerer(interaction):

    return (
        interaction.user.guild_permissions.manage_channels
    )


def permissions_royaume(
    guild,
    createur
):

    return {

        guild.default_role:
            discord.PermissionOverwrite(
                view_channel=False
            ),

        guild.me:
            discord.PermissionOverwrite(
                view_channel=True,
                send_messages=True,
                read_message_history=True,
                connect=True,
                speak=True,
                manage_channels=True
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


# ============================================================
# /SALON
# ============================================================

@tree.command(
    name="salon",
    description="Gérer les salons des royaumes"
)
@app_commands.describe(
    action="Action à effectuer",
    salon="Salon textuel concerné",
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

    if not peut_gerer(interaction):

        await interaction.response.send_message(
            "❌ Tu dois avoir la permission "
            "**Gérer les salons**.",
            ephemeral=True
        )

        return


    # ========================================================
    # CRÉER
    # ========================================================

    if action.value == "creer":

        if not nom:

            await interaction.response.send_message(
                "❌ Indique le nom du royaume.",
                ephemeral=True
            )

            return

        nom = nom.lower().replace(
            " ",
            "-"
        )

        categorie = discord.utils.get(

            interaction.guild.categories,

            name=CATEGORIE_ROYAUME
        )

        if not categorie:

            await interaction.response.send_message(

                f"❌ La catégorie "
                f"`{CATEGORIE_ROYAUME}` "
                f"est introuvable.",

                ephemeral=True
            )

            return

        nom_textuel = f"🔒・{nom}"

        nom_vocal = f"🔊・{nom}"

        textuel_existant = discord.utils.get(

            interaction.guild.text_channels,

            name=nom_textuel
        )

        vocal_existant = discord.utils.get(

            interaction.guild.voice_channels,

            name=nom_vocal
        )

        if textuel_existant or vocal_existant:

            await interaction.response.send_message(

                f"❌ Le royaume **{nom}** "
                f"existe déjà.",

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

                    overwrites=permissions
                )
            )

            salon_vocal = (
                await interaction.guild.create_voice_channel(

                    name=nom_vocal,

                    category=categorie,

                    overwrites=permissions
                )
            )

        except discord.Forbidden:

            await interaction.response.send_message(

                "❌ Le bot n'a pas les permissions "
                "nécessaires pour créer les salons.",

                ephemeral=True
            )

            return

        await interaction.response.send_message(

            "🏰 **Royaume créé !**\n\n"

            f"💬 {salon_textuel.mention}\n"

            f"🔊 **{salon_vocal.name}**"
        )


    # ========================================================
    # SUPPRIMER
    # ========================================================

    elif action.value == "supprimer":

        if not salon:

            await interaction.response.send_message(

                "❌ Sélectionne le salon textuel "
                "du royaume.",

                ephemeral=True
            )

            return

        if not salon.name.startswith("🔒・"):

            await interaction.response.send_message(

                "❌ Ce n'est pas un salon de royaume.",

                ephemeral=True
            )

            return

        nom_royaume = salon.name.replace(
            "🔒・",
            "",
            1
        )

        vocal = discord.utils.get(

            interaction.guild.voice_channels,

            name=f"🔊・{nom_royaume}"
        )

        try:

            await salon.delete()

            if vocal:

                await vocal.delete()

        except discord.Forbidden:

            await interaction.response.send_message(

                "❌ Le bot ne peut pas supprimer "
                "ce salon.",

                ephemeral=True
            )

            return

        await interaction.response.send_message(

            f"🗑️ Royaume **{nom_royaume}** supprimé."
        )


    # ========================================================
    # RENOMMER
    # ========================================================

    elif action.value == "renommer":

        if not salon or not nom:

            await interaction.response.send_message(

                "❌ Sélectionne le salon et "
                "indique le nouveau nom.",

                ephemeral=True
            )

            return

        if not salon.name.startswith("🔒・"):

            await interaction.response.send_message(

                "❌ Ce n'est pas un salon de royaume.",

                ephemeral=True
            )

            return

        ancien_nom = salon.name.replace(
            "🔒・",
            "",
            1
        )

        nouveau_nom = nom.lower().replace(
            " ",
            "-"
        )

        vocal = discord.utils.get(

            interaction.guild.voice_channels,

            name=f"🔊・{ancien_nom}"
        )

        try:

            await salon.edit(
                name=f"🔒・{nouveau_nom}"
            )

            if vocal:

                await vocal.edit(
                    name=f"🔊・{nouveau_nom}"
                )

        except discord.Forbidden:

            await interaction.response.send_message(

                "❌ Le bot ne peut pas renommer "
                "ce royaume.",

                ephemeral=True
            )

            return

        await interaction.response.send_message(

            f"✏️ Royaume renommé en "
            f"**{nouveau_nom}**."
        )


    # ========================================================
    # AJOUTER
    # ========================================================

    elif action.value == "ajouter":

        if not salon or not membre:

            await interaction.response.send_message(

                "❌ Sélectionne le salon et "
                "le membre.",

                ephemeral=True
            )

            return

        if not salon.name.startswith("🔒・"):

            await interaction.response.send_message(

                "❌ Ce n'est pas un salon de royaume.",

                ephemeral=True
            )

            return

        nom_royaume = salon.name.replace(
            "🔒・",
            "",
            1
        )

        vocal = discord.utils.get(

            interaction.guild.voice_channels,

            name=f"🔊・{nom_royaume}"
        )

        permissions = discord.PermissionOverwrite(

            view_channel=True,

            send_messages=True,

            read_message_history=True,

            connect=True,

            speak=True
        )

        try:

            await salon.set_permissions(

                membre,

                overwrite=permissions
            )

            if vocal:

                await vocal.set_permissions(

                    membre,

                    overwrite=permissions
                )

        except discord.Forbidden:

            await interaction.response.send_message(

                "❌ Le bot ne peut pas modifier "
                "les permissions de ce royaume.",

                ephemeral=True
            )

            return

        await interaction.response.send_message(

            f"➕ {membre.mention} a été ajouté "
            f"au royaume **{nom_royaume}**."
        )


    # ========================================================
    # RETIRER
    # ========================================================

    elif action.value == "retirer":

        if not salon or not membre:

            await interaction.response.send_message(

                "❌ Sélectionne le salon et "
                "le membre.",

                ephemeral=True
            )

            return

        if not salon.name.startswith("🔒・"):

            await interaction.response.send_message(

                "❌ Ce n'est pas un salon de royaume.",

                ephemeral=True
            )

            return

        nom_royaume = salon.name.replace(
            "🔒・",
            "",
            1
        )

        vocal = discord.utils.get(

            interaction.guild.voice_channels,

            name=f"🔊・{nom_royaume}"
        )

        try:

            await salon.set_permissions(

                membre,

                overwrite=None
            )

            if vocal:

                await vocal.set_permissions(

                    membre,

                    overwrite=None
                )

        except discord.Forbidden:

            await interaction.response.send_message(

                "❌ Le bot ne peut pas modifier "
                "les permissions de ce royaume.",

                ephemeral=True
            )

            return

        await interaction.response.send_message(

            f"➖ {membre.mention} a été retiré "
            f"du royaume **{nom_royaume}**."
        )

# ============================================================
# TABLEAU DE BORD
# ============================================================

TABLEAU_DE_BORD = "📊・tableau-de-bord"


async def mettre_a_jour_tableau_de_bord():

    for guild in bot.guilds:

        salon = discord.utils.get(
            guild.text_channels,
            name=TABLEAU_DE_BORD
        )

        if salon is None:
            continue

        membres = guild.member_count or 0

        if donnees["actif"]:

            total_invites = sum(
                donnees["invites"].values()
            )

            contenu = (
                "🏰 **AETHORIA**\n"
                "━━━━━━━━━━━━━━━━━━\n\n"
                f"👥 **Membres :** {membres}\n\n"
                "🏆 **Tournoi :** 🟢 EN COURS\n"
                f"🎟️ **Invitations gagnées :** +{total_invites}\n\n"
                "━━━━━━━━━━━━━━━━━━"
            )

        else:

            contenu = (
                "🏰 **AETHORIA**\n"
                "━━━━━━━━━━━━━━━━━━\n\n"
                f"👥 **Membres :** {membres}\n\n"
                "🏆 **Tournoi :** 🔴 AUCUN TOURNOI\n\n"
                "━━━━━━━━━━━━━━━━━━"
            )

        # Cherche un message existant du bot
        message_trouve = None

        async for message in salon.history(limit=20):

            if (
                message.author == bot.user
                and message.content.startswith("🏰 **AETHORIA**")
            ):
                message_trouve = message
                break

        if message_trouve:

            await message_trouve.edit(
                content=contenu
            )

        else:

            await salon.send(
                contenu
            )
# ============================================================
# DÉMARRAGE DU BOT
# ============================================================

@bot.event
async def on_ready():

    await tree.sync()
    await mettre_a_jour_tableau_de_bord()
    print("")
    print("======================================")
    print("🤖 AETHORIA BOT CONNECTÉ")
    print("======================================")
    print(
        f"👤 Bot : {bot.user}"
    )
    print(
        f"🌍 Serveurs : {len(bot.guilds)}"
    )
    print("")

    for guild in bot.guilds:

        permissions = guild.me.guild_permissions

        print(
            "===== PERMISSIONS DU BOT ====="
        )

        print(
            f"🏰 Serveur : {guild.name}"
        )

        print(
            f"⚙️ Gérer les salons : "
            f"{permissions.manage_channels}"
        )

        print(
            f"📨 Créer des invitations : "
            f"{permissions.create_instant_invite}"
        )

        print(
            f"👑 Administrateur : "
            f"{permissions.administrator}"
        )

        print(
            f"👁️ Voir les salons : "
            f"{permissions.view_channel}"
        )

        print(
            f"💬 Envoyer des messages : "
            f"{permissions.send_messages}"
        )

        print(
            f"📖 Lire l'historique : "
            f"{permissions.read_message_history}"
        )

        print(
            "==============================="
        )

        print("")


# ============================================================
# LANCEMENT
# ============================================================

bot.run(TOKEN)