import discord
from discord.ext import commands
from discord.ui import Button, View

import os
from dotenv import load_dotenv

from flask import Flask
from threading import Thread

# === PARTIE WEB (POUR UPTIMEROBOT) ===
app = Flask('')

@app.route('/')
def home():
    return "Je suis vivant !"

def run():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = Thread(target=run)
    t.start()

# === CONFIGURATION DU BOT ===
load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")

if not TOKEN:
    print("Erreur: Le token n'est pas trouvé !")
    exit()

bot = commands.Bot(command_prefix="/", intents=discord.Intents.all())

# === BASE DE DONNÉES (GEAR) ===
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

# === VUE INTERACTIVE (BOUTONS) ===
class PivotView(View):
    
    # BOUTON 1 : ORBE (HP)
    # Pour mettre une image custom, remplace emoji="🔮" par emoji="<:ton_emoji:123456>"
    @discord.ui.button(label="Orbe (HP)", style=discord.ButtonStyle.primary, emoji="🔮")
    async def orbe_btn(self, interaction: discord.Interaction, button: Button):
        # On ouvre direct le modal, pas besoin de defer ici car le modal est instantané
        await ask_stat(interaction, "orbe")

    # BOUTON 2 : BAGUE (ATK)
    @discord.ui.button(label="Bague (ATK)", style=discord.ButtonStyle.danger, emoji="💍")
    async def bague_btn(self, interaction: discord.Interaction, button: Button):
        await ask_stat(interaction, "bague")
        
    # BOUTON 3 : BOUCLES (DEF)
    @discord.ui.button(label="Boucles (DEF)", style=discord.ButtonStyle.success, emoji="👂")
    async def boucles_btn(self, interaction: discord.Interaction, button: Button):
        await ask_stat(interaction, "boucles")

async def ask_stat(interaction, gear_key):
    await interaction.response.send_modal(StatModal(gear_key))

# === POP-UP (MODAL) ===
class StatModal(discord.ui.Modal):
    def __init__(self, gear_key):
        self.gear_key = gear_key
        gear_info = GEAR_DATA[gear_key]
        super().__init__(title=f"Calcul Pivot {gear_key.capitalize()}")
        
        self.stat_input = discord.ui.TextInput(
            label=f"Base {gear_info['type']} du perso (Sans Stuff)",
            placeholder="Exemple : 112000",
            min_length=3,
            max_length=7
        )
        self.add_item(self.stat_input)

    async def on_submit(self, interaction: discord.Interaction):
        # ICI on met le DEFER pour éviter le timeout pendant le calcul
        await interaction.response.defer() 
        
        try:
            valeur = int(self.stat_input.value)
            pivot = calculate_pivot(self.gear_key, valeur)
            
            embed = discord.Embed(title="📊 Résultat du Calcul", color=0x00ff00)
            embed.add_field(name="Équipement", value=self.gear_key.capitalize(), inline=True)
            embed.add_field(name="Base Stat", value=f"{valeur}", inline=True)
            
            if pivot > 13.5:
                verdict = "⚠️ **DIFFICILE** : Le R 15% est très fort ici. SSR Perfect requis."
                color = 0xff0000
            elif pivot < 10:
                verdict = "✅ **FACILE** : Mettez toujours du SSR."
                color = 0x00ff00
            else:
                verdict = "⚖️ **MOYEN** : Un SSR correct (12-13%) suffit."
                color = 0xffff00
                
            embed.color = color
            embed.add_field(name="🎯 PIVOT À VISER", value=f"**> {pivot}%**", inline=False)
            embed.set_footer(text=verdict)

            # On utilise followup.send car on a déjà defer l'interaction
            await interaction.followup.send(embed=embed)
            
        except ValueError:
            await interaction.followup.send("❌ Erreur : Entrez un nombre entier valide (ex: 112000).", ephemeral=True)

# === DÉMARRAGE ===
@bot.event
async def on_ready():
    print(f"✅ Bot connecté en tant que {bot.user}")

@bot.command()
async def calcul(ctx):
    embed = discord.Embed(title="Salut <:pepegojo:901403926186840094> ", description="Tu veux analyser quoi <:whatcry:871036640250978304> <:whatcry:871036640250978304> :")
    # Tu peux ajouter une image/bannière à l'embed ici :
    # embed.set_image(url="https://ton-lien-image.com/banner.png")
    await ctx.send(embed=embed, view=PivotView())

keep_alive()
bot.run(TOKEN)
