import discord
from discord import app_commands
from discord.ui import Button, View, Modal, TextInput
import traceback
import os
from dotenv import load_dotenv
from flask import Flask
from threading import Thread

# === WEB SERVER (KEEP ALIVE) ===
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

bot = discord.Client(intents=intents)
tree = app_commands.CommandTree(bot)

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
    """Calcule le pivot à partir de la stat de base"""
    data = GEAR_DATA[gear_key]
    delta = data["flat_ssr"] - data["flat_r"]
    if base_stat == 0:
        return 0
    pivot = 15 - (delta / float(base_stat) * 100)
    return round(pivot, 2)

def get_verdict_message(pivot, gear_name):
    """Génère le message détaillé basé sur le pivot"""
    if pivot > 13.5:
        return (
            f"⚠️ **Cas DIFFICILE**\n\n"
            f"Pour ce personnage sur **{gear_name}**, vous devez avoir :\n"
            f"• Une pièce **SSR avec >{pivot}%** (quasi parfaite)\n"
            f"• **OU** une pièce **R 15% maxée** (qui sera meilleure)\n\n"
            f"💡 *Recommandation : Gardez votre R 15% si vous n'avez pas un SSR excellent.*"
        )
    elif pivot < 10:
        return (
            f"✅ **Cas FACILE**\n\n"
            f"Pour ce personnage sur **{gear_name}**, vous devez avoir :\n"
            f"• Une pièce **SSR avec >{pivot}%** (très accessible)\n"
            f"• La pièce **R 15% maxée** sera toujours inférieure\n\n"
            f"💡 *Recommandation : Mettez du SSR sans hésiter, même moyen.*"
        )
    else:
        return (
            f"⚖️ **Cas MOYEN**\n\n"
            f"Pour ce personnage sur **{gear_name}**, vous devez avoir :\n"
            f"• Une pièce **SSR avec >{pivot}%** (correct)\n"
            f"• **OU** une pièce **R 15% maxée** (si vous n'avez pas mieux)\n\n"
            f"💡 *Recommandation : Un SSR à 12-13% fera l'affaire.*"
        )

# === MODAL (POP-UP) ===
class StatModal(Modal):
    def __init__(self, gear_key):
        super().__init__(title=f"Calcul {gear_key.capitalize()}")
        self.gear_key = gear_key
        self.gear_info = GEAR_DATA[gear_key]
        
        self.stat_input = TextInput(
            label=f"Base {self.gear_info['type']} (Sans Stuff)",
            placeholder="Ex: 126000",
            min_length=2,
            max_length=8,
            required=True
        )
        self.add_item(self.stat_input)

    async def on_submit(self, interaction: discord.Interaction):
        try:
            valeur = int(self.stat_input.value)
            pivot = calculate_pivot(self.gear_key, valeur)
            verdict = get_verdict_message(pivot, self.gear_key.capitalize())
            
            # Choix de la couleur
            if pivot > 13.5:
                color = 0xe74c3c  # Rouge
            elif pivot < 10:
                color = 0x2ecc71  # Vert
            else:
                color = 0xf1c40f  # Jaune
            
            # Création de l'embed
            embed = discord.Embed(
                title="📊 Résultat de l'Analyse",
                description=verdict,
                color=color
            )
            embed.add_field(name="Équipement analysé", value=self.gear_key.capitalize(), inline=True)
            embed.add_field(name="Stat de base", value=f"{valeur:,}", inline=True)
            embed.add_field(name="🎯 Pivot calculé", value=f"**{pivot}%**", inline=True)
            embed.set_footer(text="Lampa Calculator • 7DS Gear Optimizer")

            await interaction.response.send_message(embed=embed)
            
        except ValueError:
            await interaction.response.send_message(
                "❌ **Erreur de saisie**\nVeuillez entrer un nombre entier valide (ex: 126000).",
                ephemeral=True
            )
        except Exception as e:
            print(f"[ERREUR MODAL] {e}")
            traceback.print_exc()
            await interaction.response.send_message(
                f"❌ Une erreur interne s'est produite : {e}",
                ephemeral=True
            )

# === VIEW (BOUTONS) ===
class PivotView(View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Ceinture (HP)", style=discord.ButtonStyle.primary, emoji="🥋", row=0)
    async def ceinture_btn(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_modal(StatModal("ceinture"))

    @discord.ui.button(label="Orbe (HP)", style=discord.ButtonStyle.primary, emoji="🔮", row=0)
    async def orbe_btn(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_modal(StatModal("orbe"))

    @discord.ui.button(label="Bracelet (ATK)", style=discord.ButtonStyle.danger, emoji="🥊", row=1)
    async def bracelet_btn(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_modal(StatModal("bracelet"))

    @discord.ui.button(label="Bague (ATK)", style=discord.ButtonStyle.danger, emoji="💍", row=1)
    async def bague_btn(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_modal(StatModal("bague"))

    @discord.ui.button(label="Collier (DEF)", style=discord.ButtonStyle.success, emoji="📿", row=2)
    async def collier_btn(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_modal(StatModal("collier"))

    @discord.ui.button(label="Boucles (DEF)", style=discord.ButtonStyle.success, emoji="👂", row=2)
    async def boucles_btn(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_modal(StatModal("boucles"))

# === ÉVÉNEMENTS ===
@bot.event
async def on_ready():
    await tree.sync()
    print(f"✅ Bot connecté : {bot.user}")
    print(f"📚 Discord.py version : {discord.__version__}")
    print(f"🔄 Commandes synchronisées !")

# === COMMANDE SLASH ===
@tree.command(name="calcul", description="🧮 Ouvre le calculateur d'optimisation Gear 7DS")
async def calcul(interaction: discord.Interaction):
    embed = discord.Embed(
        title="🧮 Calculateur d'Optimisation Gear",
        description="Sélectionnez la pièce d'équipement que vous souhaitez analyser :",
        color=0x3498db
    )
    embed.set_footer(text="Cliquez sur un bouton pour commencer")
    await interaction.response.send_message(embed=embed, view=PivotView())

# === DÉMARRAGE ===
keep_alive()
bot.run(TOKEN)
