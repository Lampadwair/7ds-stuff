import discord
from discord.ext import commands
from discord.ui import Button, View

import os
from dotenv import load_dotenv

from flask import Flask
from threading import Thread

# === WEB SERVER ===
app = Flask('')

@app.route('/')
def home():
    return "I am alive"

def run():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = Thread(target=run)
    t.start()

# === BOT SETUP ===
load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")

if not TOKEN:
    print("Error: Token not found")
    exit()

# On demande juste les permissions par défaut + lire les messages
intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="/", intents=intents)

# === DATA ===
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

# === VIEW ===
class PivotView(View):
    
    # CORRECTION CRITIQUE ICI : (self, button, interaction)
    @discord.ui.button(label="Orbe (HP)", style=discord.ButtonStyle.primary, emoji="🔮")
    async def orbe_btn(self, button: Button, interaction: discord.Interaction):
        await ask_stat(interaction, "orbe")

    @discord.ui.button(label="Bague (ATK)", style=discord.ButtonStyle.danger, emoji="💍")
    async def bague_btn(self, button: Button, interaction: discord.Interaction):
        await ask_stat(interaction, "bague")
        
    @discord.ui.button(label="Boucles (DEF)", style=discord.ButtonStyle.success, emoji="👂")
    async def boucles_btn(self, button: Button, interaction: discord.Interaction):
        await ask_stat(interaction, "boucles")

async def ask_stat(interaction, gear_key):
    await interaction.response.send_modal(StatModal(gear_key))

# === MODAL ===
class StatModal(discord.ui.Modal):
    def __init__(self, gear_key):
        self.gear_key = gear_key
        gear_info = GEAR_DATA[gear_key]
        super().__init__(title=f"Calcul Pivot {gear_key.capitalize()}")
        
        self.stat_input = discord.ui.TextInput(
            label=f"Base {gear_info['type']} (Sans Stuff)",
            placeholder="Ex: 112000",
            min_length=3,
            max_length=7
        )
        self.add_item(self.stat_input)

    async def on_submit(self, interaction: discord.Interaction):
        # Pour éviter le timeout "Echec de l'interaction"
        # On ne peut pas defer avant un Modal, mais on peut répondre après
        
        try:
            valeur = int(self.stat_input.value)
            pivot = calculate_pivot(self.gear_key, valeur)
            
            embed = discord.Embed(title="📊 Résultat", color=0x00ff00)
            embed.add_field(name="Gear", value=self.gear_key.capitalize(), inline=True)
            embed.add_field(name="Base Stat", value=f"{valeur}", inline=True)
            
            if pivot > 13.5:
                verdict = "⚠️ **HARD** : R 15% > SSR Moyen"
                color = 0xff0000
            elif pivot < 10:
                verdict = "✅ **EASY** : SSR > R"
                color = 0x00ff00
            else:
                verdict = "⚖️ **MID** : Visez SSR > 12%"
                color = 0xffff00
                
            embed.color = color
            embed.add_field(name="🎯 PIVOT", value=f"**> {pivot}%**", inline=False)
            embed.set_footer(text=verdict)

            await interaction.response.send_message(embed=embed)
            
        except ValueError:
            await interaction.response.send_message("❌ Erreur : Nombre invalide.", ephemeral=True)

# === START ===
@bot.event
async def on_ready():
    print(f"✅ Bot Ready: {bot.user}")

@bot.command()
async def calcul(ctx):
    embed = discord.Embed(title="Salut <:pepegojo:901403926186840094> ", description="Tu veux analyser quoi <:whatcry:871036640250978304> <:whatcry:871036640250978304> :")
    await ctx.send(embed=embed, view=PivotView())

keep_alive()
bot.run(TOKEN)

