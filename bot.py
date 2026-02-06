import discord
from discord import app_commands
from discord.ui import Button, View, Modal, TextInput
import traceback
import os
from dotenv import load_dotenv
from flask import Flask, render_template_string
from threading import Thread

# === WEB SERVER STYLÉ ===
app = Flask('')

# Template HTML avec Glassmorphism 7DS
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Lampa Calculator - 7DS Bot</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;600;700&display=swap" rel="stylesheet">
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: 'Poppins', sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 50%, #f093fb 100%);
            min-height: 100vh;
            display: flex;
            justify-content: center;
            align-items: center;
            overflow: hidden;
            position: relative;
        }

        .bg-shapes {
            position: absolute;
            width: 100%;
            height: 100%;
            overflow: hidden;
            z-index: 0;
        }

        .shape {
            position: absolute;
            border-radius: 50%;
            filter: blur(80px);
            opacity: 0.4;
            animation: float 20s infinite ease-in-out;
        }

        .shape1 {
            width: 400px;
            height: 400px;
            background: #ff6b6b;
            top: -100px;
            left: -100px;
            animation-delay: 0s;
        }

        .shape2 {
            width: 350px;
            height: 350px;
            background: #4ecdc4;
            bottom: -100px;
            right: -100px;
            animation-delay: 5s;
        }

        .shape3 {
            width: 300px;
            height: 300px;
            background: #ffe66d;
            top: 50%;
            left: 50%;
            animation-delay: 10s;
        }

        @keyframes float {
            0%, 100% { transform: translate(0, 0) scale(1); }
            33% { transform: translate(50px, -50px) scale(1.1); }
            66% { transform: translate(-50px, 50px) scale(0.9); }
        }

        .container {
            position: relative;
            z-index: 1;
            background: rgba(255, 255, 255, 0.1);
            backdrop-filter: blur(20px) saturate(180%);
            -webkit-backdrop-filter: blur(20px) saturate(180%);
            border-radius: 30px;
            border: 1px solid rgba(255, 255, 255, 0.2);
            box-shadow: 0 8px 32px 0 rgba(31, 38, 135, 0.37);
            padding: 60px 50px;
            text-align: center;
            max-width: 500px;
            animation: slideIn 0.8s ease-out;
        }

        @keyframes slideIn {
            from { opacity: 0; transform: translateY(-50px); }
            to { opacity: 1; transform: translateY(0); }
        }

        .status-badge {
            display: inline-flex;
            align-items: center;
            gap: 10px;
            background: rgba(76, 175, 80, 0.2);
            border: 1px solid rgba(76, 175, 80, 0.4);
            padding: 8px 20px;
            border-radius: 50px;
            margin-bottom: 20px;
            animation: pulse 2s infinite;
        }

        @keyframes pulse {
            0%, 100% { transform: scale(1); }
            50% { transform: scale(1.05); }
        }

        .status-dot {
            width: 12px;
            height: 12px;
            background: #4caf50;
            border-radius: 50%;
            box-shadow: 0 0 15px #4caf50;
            animation: blink 1.5s infinite;
        }

        @keyframes blink {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.3; }
        }

        .status-text {
            color: #fff;
            font-weight: 600;
            font-size: 14px;
            text-transform: uppercase;
            letter-spacing: 1px;
        }

        h1 {
            color: #fff;
            font-size: 48px;
            font-weight: 700;
            margin-bottom: 10px;
            text-shadow: 0 4px 20px rgba(0, 0, 0, 0.3);
        }

        .subtitle {
            color: rgba(255, 255, 255, 0.8);
            font-size: 18px;
            margin-bottom: 30px;
            font-weight: 300;
        }

        .features {
            display: flex;
            flex-direction: column;
            gap: 15px;
            margin: 30px 0;
        }

        .feature {
            background: rgba(255, 255, 255, 0.05);
            border: 1px solid rgba(255, 255, 255, 0.1);
            padding: 15px 20px;
            border-radius: 15px;
            color: #fff;
            font-size: 16px;
            display: flex;
            align-items: center;
            gap: 15px;
            transition: all 0.3s ease;
        }

        .feature:hover {
            background: rgba(255, 255, 255, 0.1);
            transform: translateX(5px);
        }

        .feature-icon {
            font-size: 24px;
        }

        .command {
            background: rgba(0, 0, 0, 0.2);
            border: 1px solid rgba(255, 255, 255, 0.2);
            padding: 12px 20px;
            border-radius: 10px;
            color: #fff;
            font-family: 'Courier New', monospace;
            font-size: 16px;
            margin-top: 20px;
            display: inline-block;
        }

        .footer {
            margin-top: 30px;
            color: rgba(255, 255, 255, 0.6);
            font-size: 14px;
        }

        @media (max-width: 600px) {
            .container {
                padding: 40px 30px;
                margin: 20px;
            }
            h1 { font-size: 36px; }
            .subtitle { font-size: 16px; }
        }
    </style>
</head>
<body>
    <div class="bg-shapes">
        <div class="shape shape1"></div>
        <div class="shape shape2"></div>
        <div class="shape shape3"></div>
    </div>

    <div class="container">
        <div class="status-badge">
            <div class="status-dot"></div>
            <span class="status-text">Bot en ligne</span>
        </div>

        <h1>🧮 Lampa Calculator</h1>
        <p class="subtitle">Calculateur d'optimisation Gear pour 7DS</p>

        <div class="features">
            <div class="feature">
                <span class="feature-icon">⚡</span>
                <span>Calculs de pivot en temps réel</span>
            </div>
            <div class="feature">
                <span class="feature-icon">🎯</span>
                <span>6 types d'équipements analysables</span>
            </div>
            <div class="feature">
                <span class="feature-icon">📊</span>
                <span>Comparateur de pièces SSR</span>
            </div>
            <div class="feature">
                <span class="feature-icon">🔒</span>
                <span>100% gratuit et sécurisé</span>
            </div>
        </div>

        <p style="color: rgba(255,255,255,0.8); margin-top: 30px; font-size: 14px;">
            Commandes disponibles :
        </p>
        <div class="command">/calcul • /comparer</div>

        <div class="footer">
            Made with love for The Last Dance<br>
            Version 2.0 • Lampouille
        </div>
    </div>
</body>
</html>
"""

@app.route('/')
def home():
    return render_template_string(HTML_TEMPLATE)

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
    data = GEAR_DATA[gear_key]
    delta = data["flat_ssr"] - data["flat_r"]
    if base_stat == 0:
        return 0
    pivot = 15 - (delta / float(base_stat) * 100)
    return round(pivot, 2)

def get_verdict_message(pivot, gear_name):
    if pivot > 13.5:
        return (
            f"⚠️ **Roll élevé nécéssaire - Va farm gold**\n\n"
            f"Pour : **{gear_name}**, :\n"
            f"Une pièce **SSR avec >{pivot}%** doit être équipée\n"
            f"pour gagner plus de CC qu'une pièce **R 15% maxée**\n\n"
            f"💡 *Recommandation : Gardez votre R 15% si vous n'avez pas un SSR>{pivot}%.*\n\n"
        )
    elif pivot < 10:
        return (
            f"✅ **Roll faible - Va farm enclumes**\n\n"
            f"Pour : **{gear_name}**, :\n"
            f"Une pièce **SSR avec >{pivot}%** doit être équipée\n"
            f"pour gagner plus de CC qu'une pièce **R 15% maxée**\n\n"
            f"💡 *Recommandation : Mettez du SSR sans hésiter, roll à {pivot}%.*"
        )
    else:
        return (
            f"⚖️ **Roll Moyen - SSR ou R selon vos ressources**\n\n"
            f"Pour : **{gear_name}**, :\n"
            f"Une pièce **SSR avec >{pivot}%** doit être équipée\n"
            f"pour gagner plus de CC qu'une pièce **R 15% maxée**\n\n"
            f"💡 *Recommandation : Gardez votre R 15% si vous n'avez pas un SSR>{pivot}%.*\n\n"
        )

# --- Comparateur : calcule le % cible pour battre la SSR actuelle ---
def required_percent_to_beat_current(gear_key, base_stat, current_gear_stat):
    """
    base_stat = stat du perso sans stuff
    current_gear_stat = stat du perso avec la pièce SSR actuelle équipée
    On en déduit le % actuel, puis on donne le % minimum pour qu'une nouvelle SSR soit plus forte.
    """
    data = GEAR_DATA[gear_key]
    max_ssr = data["flat_ssr"]

    gain_actuel = current_gear_stat - base_stat
    if gain_actuel <= 0:
        return 0.0, 0.0  # cas degueu

    percent_actuel = gain_actuel / max_ssr * 100
    # On veut strictement mieux que la pièce actuelle → +0.1%
    percent_cible = round(percent_actuel + 0.1, 2)

    return round(percent_actuel, 2), percent_cible

# === MODAL PIVOT ===
class StatModal(Modal):
    def __init__(self, gear_key):
        super().__init__(title=f"Calcul {gear_key.capitalize()}")
        self.gear_key = gear_key
        self.gear_info = GEAR_DATA[gear_key]
        
        self.stat_input = TextInput(
            label=f"Base {self.gear_info['type']} (Sans Stuff)",
            placeholder="Renseigner la stat noire du perso - la verte",
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
            
            if pivot > 13.5:
                color = 0xe74c3c
            elif pivot < 10:
                color = 0x2ecc71
            else:
                color = 0xf1c40f
            
            embed = discord.Embed(
                title="📊 Résultat de l'Analyse",
                description=verdict,
                color=color
            )
            embed.add_field(name="Gear :", value=self.gear_key.capitalize(), inline=True)
            embed.add_field(name="Stat de base", value=f"{valeur:,}", inline=True)
            embed.add_field(name="🎯 % Pivot", value=f"**{pivot}%**", inline=True)
            embed.set_footer(text="Lampa Calculator • 7DS Gear Optimizer")

            await interaction.response.send_message(embed=embed)
            
        except ValueError:
            await interaction.response.send_message(
                "❌ **Erreur de saisie**\nVeuillez entrer un nombre entier valide (ex: 126000).",
                ephemeral=True
            )
        except Exception as e:
            print(f"[ERREUR MODAL] {e}", flush=True)
            traceback.print_exc()
            try:
                await interaction.response.send_message(
                    f"❌ Une erreur interne s'est produite : {e}",
                    ephemeral=True
                )
            except:
                pass

# === MODAL COMPARE (base + stat gear actuelle) ===
class CompareModal(Modal):
    def __init__(self, gear_key):
        super().__init__(title=f"Comparer à ta SSR actuelle - {gear_key.capitalize()}")
        self.gear_key = gear_key
        self.gear_info = GEAR_DATA[gear_key]
        
        self.base_input = TextInput(
            label=f"Base {self.gear_info['type']} (Sans Stuff)",
            placeholder="Renseigner la stat noire du perso - la verte",
            min_length=2,
            max_length=8,
            required=True
        )
        self.add_item(self.base_input)

        self.current_input = TextInput(
            label=f"{self.gear_info['type']} avec la pièce SSR actuelle",
            placeholder="Stat affichée avec la pièce équipée",
            min_length=2,
            max_length=8,
            required=True
        )
        self.add_item(self.current_input)

    async def on_submit(self, interaction: discord.Interaction):
        try:
            base_stat = int(self.base_input.value)
            current_stat = int(self.current_input.value)

            current_pct, target_pct = required_percent_to_beat_current(
                self.gear_key, base_stat, current_stat
            )

            data = GEAR_DATA[self.gear_key]
            type_stat = data["type"]

            embed = discord.Embed(
                title="⚖️ Comparateur de nouvelle pièce SSR",
                color=0x9b59b6
            )

            embed.add_field(
                name="Gear :",
                value=self.gear_key.capitalize(),
                inline=True
            )
            embed.add_field(
                name="Stat de base",
                value=f"{base_stat:,}",
                inline=True
            )
            embed.add_field(
                name=f"{type_stat} avec ta SSR actuelle",
                value=f"{current_stat:,}",
                inline=True
            )

            embed.add_field(
                name="Roll actuel estimé",
                value=f"≈ **{current_pct}%**",
                inline=True
            )
            embed.add_field(
                name="Roll cible pour être meilleure",
                value=f"**>{target_pct}%**",
                inline=True
            )

            embed.set_footer(
                text="Conseil : ne roll une nouvelle SSR que si tu peux viser plus haut que ta pièce actuelle."
            )

            await interaction.response.send_message(embed=embed)

        except ValueError:
            await interaction.response.send_message(
                "❌ **Erreur de saisie**\nVérifie que tu as bien mis des nombres entiers.",
                ephemeral=True
            )
        except Exception as e:
            print(f"[ERREUR COMPARE] {e}", flush=True)
            traceback.print_exc()
            try:
                await interaction.response.send_message(
                    f"❌ Une erreur interne s'est produite : {e}",
                    ephemeral=True
                )
            except:
                pass

# === VUES ===
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

class CompareView(View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Ceinture (HP)", style=discord.ButtonStyle.primary, emoji="🥋", row=0)
    async def ceinture_btn(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_modal(CompareModal("ceinture"))

    @discord.ui.button(label="Orbe (HP)", style=discord.ButtonStyle.primary, emoji="🔮", row=0)
    async def orbe_btn(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_modal(CompareModal("orbe"))

    @discord.ui.button(label="Bracelet (ATK)", style=discord.ButtonStyle.danger, emoji="🥊", row=1)
    async def bracelet_btn(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_modal(CompareModal("bracelet"))

    @discord.ui.button(label="Bague (ATK)", style=discord.ButtonStyle.danger, emoji="💍", row=1)
    async def bague_btn(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_modal(CompareModal("bague"))

    @discord.ui.button(label="Collier (DEF)", style=discord.ButtonStyle.success, emoji="📿", row=2)
    async def collier_btn(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_modal(CompareModal("collier"))

    @discord.ui.button(label="Boucles (DEF)", style=discord.ButtonStyle.success, emoji="👂", row=2)
    async def boucles_btn(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_modal(CompareModal("boucles"))

# === ÉVÉNEMENTS ===
@bot.event
async def on_ready():
    print("=" * 60, flush=True)
    print(f"✅ Bot connecté : {bot.user}", flush=True)
    print(f"📚 Discord.py version : {discord.__version__}", flush=True)
    print("=" * 60, flush=True)
    try:
        synced = await tree.sync()
        print(f"🔄 Commandes synchronisées : {len(synced)}", flush=True)
        for cmd in synced:
            print(f"   ➜ /{cmd.name}", flush=True)
    except Exception as e:
        print(f"❌ Erreur de synchronisation : {e}", flush=True)
        traceback.print_exc()

# === COMMANDES SLASH ===
@tree.command(name="calcul", description="🧮 Calculer le pivot optimal pour une pièce d'équipement")
async def calcul(interaction: discord.Interaction):
    try:
        embed = discord.Embed(
            title="% Gear Roll Calculator <:LOVE:871036790021169213> ",
            description="Sélectionnez le type de pièce d'équipement que vous souhaitez analyser :",
            color=0x3498db
        )
        embed.set_footer(text="Cliquez sur un bouton pour commencer")
        await interaction.response.send_message(embed=embed, view=PivotView())
    except Exception as e:
        print(f"[ERREUR COMMANDE CALCUL] {e}", flush=True)
        traceback.print_exc()

@tree.command(name="comparer", description="⚖️ Estimer le roll à viser pour battre du R maxé")
async def comparer(interaction: discord.Interaction):
    embed = discord.Embed(
        title="⚖️ Calculateur de roll SSR",
        description=(
            "Choisis le type d'équipement.\n"
            "Le bot te dira à quel **% de roll** une nouvelle pièce SSR doit monter\n"
            "pour être plus forte que celle que tu utilises déjà."
        ),
        color=0x9b59b6
    )
    embed.set_footer(text="Cliquez sur un bouton pour commencer")
    await interaction.response.send_message(embed=embed, view=CompareView())

# === DÉMARRAGE ===
keep_alive()
bot.run(TOKEN)

