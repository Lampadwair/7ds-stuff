import discord
from discord.ext import commands
from discord.ui import Button, View

import os
from dotenv import load_dotenv

from flask import Flask
from threading import Thread

app = Flask('')

@app.route('/')
def home():
    return "Je suis vivant !"

def run():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = Thread(target=run)
    t.start()


load_dotenv() # Charge les variables si tu testes en local avec un fichier .env
TOKEN = os.getenv("DISCORD_TOKEN") # Récupère la variable d'environnement du serveur

if not TOKEN:
    print("Erreur: Le token n'est pas trouvé !")
    exit()


bot = commands.Bot(command_prefix="/", intents=discord.Intents.all())

# === DONNÉES STATS (Ta base de données) ===
GEAR_DATA = {
    "ceinture": {"flat_r": 5400, "flat_ssr": 12400, "type": "HP", "emoji": "🛡️"},
    "orbe":     {"flat_r": 2900, "flat_ssr": 5800,  "type": "HP", "emoji": "💍"},
    "bracelet": {"flat_r": 540,  "flat_ssr": 1240,  "type": "ATK", "emoji": "⚔️"},
    "bague":    {"flat_r": 290,  "flat_ssr": 640,   "type": "ATK", "emoji": "💍"},
    "collier":  {"flat_r": 300,  "flat_ssr": 560,   "type": "DEF", "emoji": "🛡️"},
    "boucles":  {"flat_r": 160,  "flat_ssr": 320,   "type": "DEF", "emoji": "💍"}
}

# === FORMULE DE CALCUL ===
def calculate_pivot(gear_key, base_stat):
    data = GEAR_DATA[gear_key]
    # Pivot = 15 - ((Flat_SSR - Flat_R) / Base * 100)
    delta = data["flat_ssr"] - data["flat_r"]
    pivot = 15 - (delta / float(base_stat) * 100)
    return round(pivot, 2)

# === VUE INTERACTIVE (BOUTONS) ===
class PivotView(View):
    @discord.ui.button(label="Orbe (HP)", style=discord.ButtonStyle.primary, emoji="🔮")
    async def orbe_btn(self, interaction: discord.Interaction, button: Button):
        await ask_stat(interaction, "orbe")

    @discord.ui.button(label="Bague (ATK)", style=discord.ButtonStyle.danger, emoji="💍")
    async def bague_btn(self, interaction: discord.Interaction, button: Button):
        await ask_stat(interaction, "bague")
        
    @discord.ui.button(label="Boucles (DEF)", style=discord.ButtonStyle.success, emoji="👂")
    async def boucles_btn(self, interaction: discord.Interaction, button: Button):
        await ask_stat(interaction, "boucles")

async def ask_stat(interaction, gear_key):
    # Demande la stat à l'utilisateur
    await interaction.response.send_modal(StatModal(gear_key))

# === MODAL (POP-UP DE SAISIE) ===
class StatModal(discord.ui.Modal):
    def __init__(self, gear_key):
        self.gear_key = gear_key
        gear_info = GEAR_DATA[gear_key]
        super().__init__(title=f"Calcul Pivot {gear_key.capitalize()}")
        
        self.stat_input = discord.ui.TextInput(
            label=f"Entrez la Base {gear_info['type']} du perso",
            placeholder="Ex: 112000"
        )
        self.add_item(self.stat_input)

    async def on_submit(self, interaction: discord.Interaction):
        try:
            valeur = int(self.stat_input.value)
            pivot = calculate_pivot(self.gear_key, valeur)
            
            # Création de l'Embed Réponse
            embed = discord.Embed(title="📊 Résultat du Calcul", color=0x00ff00)
            embed.add_field(name="Équipement", value=self.gear_key.capitalize(), inline=True)
            embed.add_field(name="Base Stat", value=f"{valeur}", inline=True)
            
            # Message dynamique selon le résultat
            verdict = ""
            if pivot > 13.5:
                verdict = "⚠️ **DIFFICILE** : Le R 15% est très fort ici. Il faut un SSR quasi parfait."
                color = 0xff0000 # Rouge
            elif pivot < 10:
                verdict = "✅ **FACILE** : Mettez toujours du SSR."
                color = 0x00ff00 # Vert
            else:
                verdict = "⚖️ **MOYEN** : Un SSR correct (12-13%) suffit."
                color = 0xffff00 # Jaune
                
            embed.color = color
            embed.add_field(name="🎯 PIVOT À VISER", value=f"**> {pivot}%**", inline=False)
            embed.set_footer(text=verdict)

            await interaction.response.send_message(embed=embed)
            
        except ValueError:
            await interaction.response.send_message("❌ Erreur : Veuillez entrer un nombre entier valide.", ephemeral=True)

# === COMMANDE DE DÉPART ===
@bot.command()
async def calcul(ctx):
    embed = discord.Embed(title="🧮 Calculateur d'Optimisation Gear", description="Choisissez la pièce d'équipement à analyser :")
    await ctx.send(embed=embed, view=PivotView())

bot.run(TOKEN)
