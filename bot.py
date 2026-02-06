import discord
from discord import app_commands
from discord.ui import Button, View, Modal, TextInput
import traceback
import os
from dotenv import load_dotenv
from flask import Flask, render_template_string
from threading import Thread

# === CONFIGURATION ===
load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")

# === DONNÉES 7DS ===
GEAR_DATA = {
    "ceinture": {"ssr": 12400, "r": 5400, "type": "HP", "emoji": "🥋", "style": discord.ButtonStyle.primary},
    "orbe":     {"ssr": 5800,  "r": 2900, "type": "HP", "emoji": "🔮", "style": discord.ButtonStyle.primary},
    "bracelet": {"ssr": 1240,  "r": 540,  "type": "ATK", "emoji": "🥊", "style": discord.ButtonStyle.danger},
    "bague":    {"ssr": 640,   "r": 290,  "type": "ATK", "emoji": "💍", "style": discord.ButtonStyle.danger},
    "collier":  {"ssr": 560,   "r": 300,  "type": "DEF", "emoji": "📿", "style": discord.ButtonStyle.success},
    "boucles":  {"ssr": 320,   "r": 160,  "type": "DEF", "emoji": "👂", "style": discord.ButtonStyle.success}
}

MAX_SUBSTAT = 15  # % maximum de substats

# === FONCTIONS DE CALCUL ===
def calculate_pivot_old(gear_key, base_stat):
    """Ancien calcul pivot (SSR vs R) - DEPRECATED"""
    data = GEAR_DATA[gear_key]
    if base_stat == 0:
        return 0
    delta = data["ssr"] - data["r"]
    pivot = MAX_SUBSTAT - (delta / float(base_stat) * 100)
    return round(pivot, 2)

def calculate_pivot_7ds(gear_key, pct_stat_ssr, base_stat):
    """
    Calcule le % de substats nécessaire pour qu'une pièce SSR batte une R 15% maxée.
    
    Système 7DS :
    - Stat totale = Base + Stat_pièce + (Base × Substats%)
    - Les substats % s'appliquent sur la BASE du personnage
    
    Returns:
        dict: {
            'pivot': % de substats requis,
            'ssr_piece_stat': stat apportée par la pièce SSR,
            'r_total': stat totale de la R maxée,
            'ssr_total_au_pivot': stat totale de la SSR au pivot,
            'rentable': True si pivot <= 15%
        }
    """
    gear_info = GEAR_DATA[gear_key]
    ssr_max = gear_info['ssr']
    r_stat = gear_info['r']
    
    # Stat totale de la R 15% maxée
    r_total = base_stat + r_stat + (base_stat * MAX_SUBSTAT / 100)
    
    # Stat de la pièce SSR à X%
    ssr_piece_stat = ssr_max * (pct_stat_ssr / 100)
    
    # Calcul du pivot : base + ssr_piece + (base × pivot/100) = r_total
    pivot = ((r_total - base_stat - ssr_piece_stat) / base_stat) * 100
    
    # Stat totale de la SSR au pivot
    ssr_total_au_pivot = base_stat + ssr_piece_stat + (base_stat * pivot / 100)
    
    return {
        'pivot': round(pivot, 2),
        'ssr_piece_stat': ssr_piece_stat,
        'r_total': r_total,
        'ssr_total_au_pivot': ssr_total_au_pivot,
        'rentable': pivot <= MAX_SUBSTAT
    }

def get_verdict_message(pivot, gear_name):
    """Génère le message de verdict selon le pivot"""
    if pivot > 13.5:
        return (
            f"⚠️ **Roll élevé nécessaire - Va farm gold**\n\n"
            f"Pour **{gear_name}** :\n"
            f"Une pièce **SSR avec >{pivot}%** doit être équipée\n"
            f"pour gagner plus de CC qu'une pièce **R 15% maxée**\n\n"
            f"💡 *Recommandation : Gardez votre R 15% si vous n'avez pas un SSR >{pivot}%.*"
        )
    elif pivot < 10:
        return (
            f"✅ **Roll faible - Va farm enclumes**\n\n"
            f"Pour **{gear_name}** :\n"
            f"Une pièce **SSR avec >{pivot}%** doit être équipée\n"
            f"pour gagner plus de CC qu'une pièce **R 15% maxée**\n\n"
            f"💡 *Recommandation : Mettez du SSR sans hésiter, roll à {pivot}%.*"
        )
    else:
        return (
            f"⚖️ **Roll Moyen - SSR ou R selon vos ressources**\n\n"
            f"Pour **{gear_name}** :\n"
            f"Une pièce **SSR avec >{pivot}%** doit être équipée\n"
            f"pour gagner plus de CC qu'une pièce **R 15% maxée**\n\n"
            f"💡 *Recommandation : Gardez votre R 15% si vous n'avez pas un SSR >{pivot}%.*"
        )

# === MODALS ===
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
            pivot = calculate_pivot_old(self.gear_key, valeur)
            verdict = get_verdict_message(pivot, self.gear_key.capitalize())
            
            color = 0xe74c3c if pivot > 13.5 else 0x2ecc71 if pivot < 10 else 0xf1c40f
            
            embed = discord.Embed(
                title="📊 Résultat de l'Analyse",
                description=verdict,
                color=color
            )
            embed.add_field(name="Gear", value=self.gear_key.capitalize(), inline=True)
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
            await interaction.response.send_message(
                f"❌ Une erreur interne s'est produite : {e}",
                ephemeral=True
            )

class CompareModal(Modal):
    def __init__(self, gear_key):
        super().__init__(title=f"Combien il te manque - {gear_key.capitalize()}")
        self.gear_key = gear_key
        self.gear_info = GEAR_DATA[gear_key]
        
        self.base_input = TextInput(
            label=f"Base {self.gear_info['type']} (Sans Stuff)",
            placeholder="Stat de base du perso (ex: 150000)",
            min_length=2,
            max_length=8,
            required=True
        )
        self.add_item(self.base_input)

        self.piece_stat_pct_input = TextInput(
            label=f"% de la stat de base de ta pièce SSR",
            placeholder="Ex: 50 (si ta pièce = 6200 HP et max = 12400)",
            min_length=1,
            max_length=6,
            required=True
        )
        self.add_item(self.piece_stat_pct_input)

        self.current_substat_roll_input = TextInput(
            label=f"% de roll substats actuel",
            placeholder="Ex: 3 (substats actuels sur ta pièce)",
            min_length=1,
            max_length=5,
            required=True
        )
        self.add_item(self.current_substat_roll_input)

    async def on_submit(self, interaction: discord.Interaction):
        try:
            base_stat = int(self.base_input.value)
            piece_stat_pct = float(self.piece_stat_pct_input.value.replace(",", "."))
            current_substat_roll = float(self.current_substat_roll_input.value.replace(",", "."))

            # Validations
            if not 0 <= piece_stat_pct <= 100:
                await interaction.response.send_message(
                    "❌ Le % de la stat de la pièce doit être entre 0 et 100%.",
                    ephemeral=True
                )
                return

            if not 0 <= current_substat_roll <= MAX_SUBSTAT:
                await interaction.response.send_message(
                    f"❌ Le % de roll substat doit être entre 0 et {MAX_SUBSTAT}%.",
                    ephemeral=True
                )
                return

            # Calcul du pivot avec la nouvelle fonction
            pivot_result = calculate_pivot_7ds(
                gear_key=self.gear_key,
                pct_stat_ssr=piece_stat_pct,
                base_stat=base_stat
            )
            
            pivot = pivot_result['pivot']
            ssr_piece_stat = round(pivot_result['ssr_piece_stat'])
            r_total = round(pivot_result['r_total'])
            
            # Stats actuelles
            ssr_current_substat_value = base_stat * current_substat_roll / 100
            ssr_current_total = base_stat + ssr_piece_stat + ssr_current_substat_value
            
            # Verdict
            if current_substat_roll >= pivot:
                surplus = round(current_substat_roll - pivot, 2)
                total_surplus = round(ssr_current_total - r_total)
                message = (
                    f"✅ **Ta pièce SSR bat déjà une R 15% maxée !**\n\n"
                    f"Tu as **+{surplus}%** de marge en substats.\n"
                    f"Soit **+{total_surplus:,}** {self.gear_info['type']} de surplus."
                )
                color = 0x2ecc71
                missing = 0
            else:
                missing = round(pivot - current_substat_roll, 2)
                stat_manquante = round(r_total - ssr_current_total)
                message = (
                    f"🎯 **Il te faut {missing}% de roll substats supplémentaires**\n\n"
                    f"pour battre une R 15% maxée.\n"
                    f"Il te manque **{stat_manquante:,}** {self.gear_info['type']}."
                )
                color = 0xe74c3c

            embed = discord.Embed(
                title="⚖️ Comparaison SSR vs R 15%",
                description=message,
                color=color
            )

            # Stats actuelles
            embed.add_field(
                name="📊 Stats actuelles",
                value=(
                    f"```\n"
                    f"Base : {base_stat:,}\n"
                    f"Pièce SSR : +{ssr_piece_stat:,} ({piece_stat_pct}%)\n"
                    f"Substats : +{round(ssr_current_substat_value):,} ({current_substat_roll}%)\n"
                    f"{'─' * 20}\n"
                    f"Total : {round(ssr_current_total):,}\n"
                    f"```"
                ),
                inline=False
            )

            # Objectif
            embed.add_field(
                name="🎯 Objectif (R 15% maxée)",
                value=(
                    f"```\n"
                    f"Total R : {r_total:,}\n"
                    f"Pivot SSR : {pivot}% substats\n"
                    f"À roller : {missing}%\n"
                    f"```"
                ),
                inline=False
            )

            # Avertissement si non rentable
            if not pivot_result['rentable']:
                embed.add_field(
                    name="⚠️ Attention",
                    value=(
                        f"Le pivot ({pivot}%) dépasse {MAX_SUBSTAT}%.\n"
                        f"Ta pièce est trop faible pour battre une R 15% maxée."
                    ),
                    inline=False
                )

            embed.set_footer(text="Lampa Calculator • Les substats s'appliquent sur la BASE du perso")

            await interaction.response.send_message(embed=embed)

        except ValueError:
            await interaction.response.send_message(
                "❌ **Erreur de saisie**\nVérifie les formats (base = entier, % = nombres).",
                ephemeral=True
            )
        except Exception as e:
            print(f"[ERREUR COMPARE] {e}", flush=True)
            traceback.print_exc()
            await interaction.response.send_message(
                f"❌ Une erreur interne s'est produite : {e}",
                ephemeral=True
            )

# === VUES OPTIMISÉES ===
def create_gear_view(modal_class):
    """Factory pour créer des views avec tous les boutons gear"""
    class GearView(View):
        def __init__(self):
            super().__init__(timeout=None)
            for row_idx, (gear_key, gear_data) in enumerate(GEAR_DATA.items()):
                button = Button(
                    label=f"{gear_key.capitalize()} ({gear_data['type']})",
                    style=gear_data['style'],
                    emoji=gear_data['emoji'],
                    custom_id=f"{modal_class.__name__}_{gear_key}",
                    row=row_idx // 2
                )
                
                async def callback(interaction: discord.Interaction, key=gear_key):
                    await interaction.response.send_modal(modal_class(key))
                
                button.callback = callback
                self.add_item(button)
    
    return GearView

PivotView = create_gear_view(StatModal)
CompareView = create_gear_view(CompareModal)

# === WEB SERVER ===
app = Flask('')

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
        * { margin: 0; padding: 0; box-sizing: border-box; }
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
        .bg-shapes { position: absolute; width: 100%; height: 100%; overflow: hidden; z-index: 0; }
        .shape { position: absolute; border-radius: 50%; filter: blur(80px); opacity: 0.4; animation: float 20s infinite ease-in-out; }
        .shape1 { width: 400px; height: 400px; background: #ff6b6b; top: -100px; left: -100px; animation-delay: 0s; }
        .shape2 { width: 350px; height: 350px; background: #4ecdc4; bottom: -100px; right: -100px; animation-delay: 5s; }
        .shape3 { width: 300px; height: 300px; background: #ffe66d; top: 50%; left: 50%; animation-delay: 10s; }
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
        .status-text { color: #fff; font-weight: 600; font-size: 14px; text-transform: uppercase; letter-spacing: 1px; }
        h1 { color: #fff; font-size: 48px; font-weight: 700; margin-bottom: 10px; text-shadow: 0 4px 20px rgba(0, 0, 0, 0.3); }
        .subtitle { color: rgba(255, 255, 255, 0.8); font-size: 18px; margin-bottom: 30px; font-weight: 300; }
        .features { display: flex; flex-direction: column; gap: 15px; margin: 30px 0; }
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
        .feature:hover { background: rgba(255, 255, 255, 0.1); transform: translateX(5px); }
        .feature-icon { font-size: 24px; }
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
        .footer { margin-top: 30px; color: rgba(255, 255, 255, 0.6); font-size: 14px; }
        @media (max-width: 600px) {
            .container { padding: 40px 30px; margin: 20px; }
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
            <div class="feature"><span class="feature-icon">⚡</span><span>Calculs de pivot en temps réel</span></div>
            <div class="feature"><span class="feature-icon">🎯</span><span>6 types d'équipements analysables</span></div>
            <div class="feature"><span class="feature-icon">📊</span><span>Comparateur de pièces SSR</span></div>
            <div class="feature"><span class="feature-icon">🔒</span><span>100% gratuit et sécurisé</span></div>
        </div>
        <p style="color: rgba(255,255,255,0.8); margin-top: 30px; font-size: 14px;">Commandes disponibles :</p>
        <div class="command">/calcul • /comparer</div>
        <div class="footer">Made with love for The Last Dance<br>Version 2.0 • Lampouille</div>
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
    Thread(target=run, daemon=True).start()

# === BOT DISCORD ===
intents = discord.Intents.default()
intents.message_content = True

bot = discord.Client(intents=intents)
tree = app_commands.CommandTree(bot)

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

@tree.command(name="calcul", description="🧮 Calculer le pivot optimal pour une pièce d'équipement")
async def calcul(interaction: discord.Interaction):
    embed = discord.Embed(
        title="% Gear Roll Calculator <:LOVE:871036790021169213>",
        description="Sélectionnez le type de pièce d'équipement que vous souhaitez analyser :",
        color=0x3498db
    )
    embed.set_footer(text="Cliquez sur un bouton pour commencer")
    await interaction.response.send_message(embed=embed, view=PivotView())

@tree.command(name="comparer", description="⚖️ Estimer le roll à viser pour battre du R maxé")
async def comparer(interaction: discord.Interaction):
    embed = discord.Embed(
        title="⚖️ Calculateur de roll SSR",
        description=(
            "Choisis le type d'équipement.\n"
            "Le bot te dira à quel **% de roll** une nouvelle pièce SSR doit monter\n"
            "pour être plus forte qu'une R 15% maxée."
        ),
        color=0x9b59b6
    )
    embed.set_footer(text="Cliquez sur un bouton pour commencer")
    await interaction.response.send_message(embed=embed, view=CompareView())

# === DÉMARRAGE ===
if __name__ == "__main__":
    keep_alive()
    bot.run(TOKEN)
