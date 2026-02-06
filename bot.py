import discord
from discord.ext import commands
from discord.ui import Button, View, Modal, TextInput

import os
from dotenv import load_dotenv

from flask import Flask
from threading import Thread

# === WEB SERVER (POUR GARDER LE BOT EN LIGNE) ===
app = Flask('')

@app.route('/')
def home():
    return "Bot is running!"

def run():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = Thread(target=run)
    t.start()

# === CONFIGURATION DU BOT ===
load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")

# Permissions
intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="/", intents=intents)

# === DONNÉES DU JEU ===
GEAR_DATA = {
    "ceinture": {"flat_r": 5400, "flat_ssr": 12400, "type": "HP"},
    "orbe":     {"flat_r": 2900, "flat_ssr": 5800,  "type": "HP"},
    "bracelet": {"flat_r": 540,  "flat_ssr": 1240,  "type": "ATK"},
    "bague":    {"flat_r": 290,  "flat_ssr": 640,   "type": "ATK"},
    "collier":  {"flat_r": 300,  "flat_ssr": 560,   "type": "DEF"},
    "boucles":  {"flat_r": 160,  "flat_ssr": 320,   "type": "DEF"}
}

def calculate_pivot(gear_key, base_stat):
    data = GEAR_DATA[gear_key]
    delta = data["flat_ssr"] - data["flat_r"]
    pivot = 15 - (delta / float(base_stat) * 100)
    return round(pivot, 2)

# === LE FORMULAIRE (MODAL) ===
class StatModal(Modal):
    def __init__(self, gear_key):
        super().__init__(title=f"Calcul {gear_key.capitalize()}")
        self.gear_key = gear_key
        self.gear_info = GEAR_DATA[gear_key]
        
        self.stat_input = TextInput(
            label=f"Base {self.gear_info['type']} (Sans Stuff)",
            placeholder="Exemple: 120000",
            min_length=2,
            max_length=8,
            required=True
        )
        self.add_item(self.stat_input)

    async def on_submit(self, interaction: discord.Interaction):
        # 1. ON DIT A DISCORD D'ATTENDRE (C'est ça qui corrige l'erreur de timeout !)
        await interaction.response.defer()

        try:
            # 2. ON FAIT LE CALCUL
            valeur = int(self.stat_input.value)
            pivot = calculate_pivot(self.gear_key, valeur)
            
            # 3. ON PREPARE LA REPONSE
            embed = discord.Embed(title="📊 Résultat de l'Analyse", color=0x2ecc71)
            embed.add_field(name="Équipement", value=self.gear_key.capitalize(), inline=True)
            embed.add_field(name="Stat de base", value=f"{valeur}", inline=True)
            
            if pivot > 13.5:
                verdict = "⚠️ **HARD** : Le R 15% est très fort. Il faut un SSR quasi parfait."
                color = 0xe74c3c # Rouge
            elif pivot < 10:
                verdict = "✅ **EASY** : Mettez toujours du SSR."
                color = 0x2ecc71 # Vert
            else:
                verdict = "⚖️ **MOYEN** : Un SSR correct (12-13%) suffit."
                color = 0xf1c40f # Jaune
                
            embed.color = color
            embed.add_field(name="🎯 PIVOT À VISER", value=f"**> {pivot}%**", inline=False)
            embed.set_footer(text=verdict)

            # 4. ON ENVOIE LA REPONSE VIA FOLLOWUP (Car on a utilisé defer avant)
            await interaction.followup.send(embed=embed)
            
        except ValueError:
            await interaction.followup.send("❌ Erreur : Tu dois entrer un nombre entier (pas de lettres, pas de virgules).", ephemeral=True)
        except Exception as e:
            await interaction.followup.send(f"❌ Erreur critique : {e}", ephemeral=True)

# === LES BOUTONS ===
class PivotView(View):
    def __init__(self):
        super().__init__(timeout=None) # Les boutons ne meurent jamais

    @discord.ui.button(label="Orbe (HP)", style=discord.ButtonStyle.primary, emoji="🔮")
    async def orbe_btn(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_modal(StatModal("orbe"))

    @discord.ui.button(label="Bague (ATK)", style=discord.ButtonStyle.danger, emoji="💍")
    async def bague_btn(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_modal(StatModal("bague"))

    @discord.ui.button(label="Boucles (DEF)", style=discord.ButtonStyle.success, emoji="👂")
    async def boucles_btn(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_modal(StatModal("boucles"))

# === DEMARRAGE ===
@bot.event
async def on_ready():
    print(f"✅ Bot connecté : {bot.user.name}")

@bot.command()
async def calcul(ctx):
    # Petit check pour éviter le spam si jamais le doublon persiste
    if ctx.author.bot:
        return
        
    embed = discord.Embed(title="Salut <:pepegojo:901403926186840094> ", description="Tu veux analyser quoi <:whatcry:871036640250978304> <:whatcry:871036640250978304> :")
    await ctx.send(embed=embed, view=PivotView())

keep_alive()
bot.run(TOKEN)
