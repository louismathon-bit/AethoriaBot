import os
import discord
from discord.ext import commands
from dotenv import load_dotenv

# Chargement du token d'environnement
load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")

# Configuration des permissions du bot
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

# --- CONFIGURATION DU JEU HISTOIRE INFINIE ---
CHANNEL_JEU_ID = 1541006278191747182  # ID de ton salon dédié
LIMITE_MOTS = 30

histoire = []
dernier_joueur_id = None


@bot.event
async def on_ready():
    print(f"✅ Bot connecté sous le nom de : {bot.user.name}")


@bot.event
async def on_message(message):
    global dernier_joueur_id, histoire

    # Ignorer si c'est un message du bot
    if message.author.bot:
        return

    # Gestion du jeu du mot à mot dans le salon spécifique
    if message.channel.id == CHANNEL_JEU_ID:
        mots = message.content.strip().split()

        # 1. Empêcher d'écrire plus d'un mot
        if len(mots) != 1:
            await message.delete()
            await message.channel.send(
                f"{message.author.mention}, un seul mot à la fois !",
                delete_after=3,
            )
            return

        # 2. Empêcher un joueur de rejouer d'affilée
        if message.author.id == dernier_joueur_id:
            await message.delete()
            await message.channel.send(
                f"{message.author.mention}, attends qu'un autre joueur écrive un mot !",
                delete_after=3,
            )
            return

        # Ajout du mot et validation
        mot = mots[0]
        histoire.append(mot)
        dernier_joueur_id = message.author.id
        await message.add_reaction("✅")

        # 3. Fin de l'histoire (limite de 30 mots)
        if len(histoire) >= LIMITE_MOTS:
            texte_final = " ".join(histoire)

            embed = discord.Embed(
                title="📜 Fin de l'histoire !",
                description=f"**{texte_final}**",
                color=0x00FF00,
            )
            embed.set_footer(
                text="Une nouvelle histoire commence... Propose le premier mot !"
            )

            await message.channel.send(embed=embed)

            # Réinitialisation
            histoire = []
            dernier_joueur_id = None

        return

    # Exécution des autres commandes si le message est hors du salon de jeu
    await bot.process_commands(message)


# Lancement du bot
if __name__ == "__main__":
    bot.run(TOKEN)
