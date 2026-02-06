import discord
from discord.ext import commands
from discord.ui import Button, View, Modal, TextInput

import os
from dotenv import load_dotenv

from flask import Flask
from threading import Thread

# === WEB SERVER ===
app = Flask('')

@app.route('/')
def home():
    return "Bot en ligne !"

def run():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = Thread(target=run)
    t.start()

# === CONFIGURATION ===
load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="/", intents=intents)

# === DONNÉES 7DS ===
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

# === MODAL ===
class StatModal(Modal):
    def __init__(self, gear_key):
        super().__init__(title=f"Calcul {gear_key.capitalize()}")
        self.gear_key = gear_key
        self.gear_info = GEAR_DATA[gear_key]
        
        self.stat_input = TextInput(
            label=f"Base {self.gear_info['type']} (Sans Stuff)",
            placeholder="Ex: 120000",
            min_length=2,
            max_length=8,
            required=True
        )
        self.add_item(self.stat_input)

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer()

        try:
            valeur = int(self.stat_input.value)
            pivot = calculate_pivot(self.gear_key, valeur)
            
            embed = discord.Embed(title="📊 Résultat de l'Analyse", color=0x2ecc71)
            embed.add_field(name="Équipement", value=self.gear_key.capitalize(), inline=True)
            embed.add_field(name="Base Stat", value=f"{valeur}", inline=True)
            
            if pivot > 13.5:
                verdict = "⚠️ **HARD** : Le R 15% est très fort. SSR Perfect requis."
                color = 0xe74c3c # Rouge
            elif pivot < 10:
                verdict = "✅ **EASY** : Mettez toujours du SSR."
                color = 0x2ecc71 # Vert
            else:
                verdict = "⚖️ **MID** : Un SSR correct (12-13%) suffit."
                color = 0xf1c40f # Jaune
                
            embed.color = color
            embed.add_field(name="🎯 PIVOT À VISER", value=f"**> {pivot}%**", inline=False)
            embed.set_footer(text=verdict)

            await interaction.followup.send(embed=embed)
            
        except ValueError:
            await interaction.followup.send("❌ Erreur : Entrez un nombre entier valide.", ephemeral=True)
        except Exception as e:
            await interaction.followup.send(f"❌ Erreur : {e}", ephemeral=True)

# === VUE AVEC LES 6 BOUTONS ===
class PivotView(View):
    def __init__(self):
        super().__init__(timeout=None)

    # --- LIGNE 1 : HP (Bleu) ---
    @discord.ui.button(label="Ceinture (HP)", style=discord.ButtonStyle.primary, emoji="🥋", row=0)
    async def ceinture_btn(self, button: Button, interaction: discord.Interaction):
        await interaction.response.send_modal(StatModal("ceinture"))

    @discord.ui.button(label="Orbe (HP)", style=discord.ButtonStyle.primary, emoji="🔮", row=0)
    async def orbe_btn(self, button: Button, interaction: discord.Interaction):
        await interaction.response.send_modal(StatModal("orbe"))

    # --- LIGNE 2 : ATK (Rouge) ---
    @discord.ui.button(label="Bracelet (ATK)", style=discord.ButtonStyle.danger, emoji="🥊", row=1)
    async def bracelet_btn(self, button: Button, interaction: discord.Interaction):
        await interaction.response.send_modal(StatModal("bracelet"))

    @discord.ui.button(label="Bague (ATK)", style=discord.ButtonStyle.danger, emoji="💍", row=1)
    async def bague_btn(self, button: Button, interaction: discord.Interaction):
        await interaction.response.send_modal(StatModal("bague"))

    # --- LIGNE 3 : DEF (Vert) ---
    @discord.ui.button(label="Collier (DEF)", style=discord.ButtonStyle.success, emoji="📿", row=2)
    async def collier_btn(self, button: Button, interaction: discord.Interaction):
        await interaction.response.send_modal(StatModal("collier"))

    @discord.ui.button(label="Boucles (DEF)", style=discord.ButtonStyle.success, emoji="👂", row=2)
    async def boucles_btn(self, button: Button, interaction: discord.Interaction):
        await interaction.response.send_modal(StatModal("boucles"))

# === START ===
@bot.event
async def on_ready():
    print(f"✅ Bot prêt : {bot.user}")

@bot.command()
async def calcul(ctx):
    # J'ai nettoyé cette partie pour éviter l'IndentationError
    if ctx.author.bot:
        return
        
    embed = discord.Embedembed = discord.Embed(title="Salut <:darius_chokbar:1406639439689814146>  ", description="Tu veux analyser quoi <:darius_chokbar:1406639439689814146> <:darius_chokbar:1406639439689814146>  :")
    await ctx.send(embed=embed, view=PivotView())

keep_alive()
bot.run(TOKEN)
