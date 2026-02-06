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

MAX_SUBSTAT = 15

# === FONCTIONS DE CALCUL ===
def calculate_pivot_old(gear_key, base_stat):
    """Ancien calcul pivot (SSR vs R)"""
    data = GEAR_DATA[gear_key]
    if base_stat == 0:
        return 0
    delta = data["ssr"] - data["r"]
    pivot = MAX_SUBSTAT - (delta / float(base_stat) * 100)
    return round(pivot, 2)

def calculate_pivot_7ds(gear_key, pct_stat_ssr, base_stat):
    """Calcule le % de substats nécessaire pour qu'une pièce SSR batte une R 15% maxée"""
    gear_info = GEAR_DATA[gear_key]
    ssr_max = gear_info['ssr']
    r_stat = gear_info['r']
    
    r_total = base_stat + r_stat + (base_stat * MAX_SUBSTAT / 100)
    ssr_piece_stat = ssr_max * (pct_stat_ssr / 100)
    pivot = ((r_total - base_stat - ssr_piece_stat) / base_stat) * 100
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
        return f"⚠️ **Roll élevé nécessaire**\n\nPour **{gear_name}**, une pièce **SSR avec >{pivot}%** de substats doit être équipée pour gagner plus de CC qu'une **R 15% maxée**."
    elif pivot < 10:
        return f"✅ **Roll faible**\n\nPour **{gear_name}**, une pièce **SSR avec >{pivot}%** de substats doit être équipée pour gagner plus de CC qu'une **R 15% maxée**."
    else:
        return f"⚖️ **Roll Moyen**\n\nPour **{gear_name}**, une pièce **SSR avec >{pivot}%** de substats doit être équipée pour gagner plus de CC qu'une **R 15% maxée**."

# === MODALS ===
class StatModal(Modal):
    def __init__(self, gear_key, original_message):
        super().__init__(title=f"Calcul {gear_key.capitalize()}")
        self.gear_key = gear_key
        self.gear_info = GEAR_DATA[gear_key]
        self.original_message = original_message
        
        self.stat_noire_input = TextInput(
            label=f"{self.gear_info['type']} affiché (noir)",
            placeholder="Ex: 207152 (stats noires affichées dans le jeu)",
            min_length=2,
            max_length=8,
            required=True
        )
        self.add_item(self.stat_noire_input)
        
        self.stat_verte_input = TextInput(
            label=f"{self.gear_info['type']} bonus (vert)",
            placeholder="Ex: 90182 (stats vertes = bonus équipement)",
            min_length=1,
            max_length=8,
            required=True
        )
        self.add_item(self.stat_verte_input)

    async def on_submit(self, interaction: discord.Interaction):
        try:
            stat_noire = int(self.stat_noire_input.value)
            stat_verte = int(self.stat_verte_input.value)
            base_stat = stat_noire - stat_verte
            
            if base_stat <= 0:
                await interaction.response.send_message(
                    "❌ **Erreur** : Les stats noires doivent être supérieures aux stats vertes",
                    ephemeral=True
                )
                return
            
            pivot = calculate_pivot_old(self.gear_key, base_stat)
            verdict = get_verdict_message(pivot, self.gear_key.capitalize())
            
            color = 0xe74c3c if pivot > 13.5 else 0x2ecc71 if pivot < 10 else 0xf1c40f
            
            embed = discord.Embed(
                title=f"📊 {self.gear_key.capitalize()} - Pivot {pivot}%",
                description=verdict,
                color=color
            )
            embed.add_field(name="Stats noires", value=f"{stat_noire:,}", inline=True)
            embed.add_field(name="Stats vertes", value=f"{stat_verte:,}", inline=True)
            embed.add_field(name="Base calculée", value=f"{base_stat:,}", inline=True)
            embed.set_footer(text="Lampa Calculator • Consultez les dms de Lampouille pour plus d'infos")

            await interaction.response.send_message(embed=embed)
            
            # Supprimer le message original avec les boutons
            try:
                await self.original_message.delete()
            except:
                pass
            
        except ValueError:
            await interaction.response.send_message(
                "❌ **Erreur** : Nombres entiers requis",
                ephemeral=True
            )
        except Exception as e:
            print(f"[ERREUR MODAL] {e}", flush=True)
            traceback.print_exc()
            await interaction.response.send_message(
                f"❌ Erreur : {e}",
                ephemeral=True
            )

class CompareModal(Modal):
    def __init__(self, gear_key, original_message):
        super().__init__(title=f"Combien il te manque - {gear_key.capitalize()}")
        self.gear_key = gear_key
        self.gear_info = GEAR_DATA[gear_key]
        self.original_message = original_message
        
        self.stat_noire_input = TextInput(
            label=f"{self.gear_info['type']} affiché (noir)",
            placeholder="Ex: 207152 (stats noires = totales affichées)",
            min_length=2,
            max_length=8,
            required=True
        )
        self.add_item(self.stat_noire_input)
        
        self.stat_verte_input = TextInput(
            label=f"{self.gear_info['type']} bonus (vert)",
            placeholder="Ex: 90182 (stats vertes = bonus équipement)",
            min_length=1,
            max_length=8,
            required=True
        )
        self.add_item(self.stat_verte_input)

        self.piece_stat_pct_input = TextInput(
            label=f"% de la stat de base de ta pièce SSR",
            placeholder="Ex : 85.22",
            min_length=1,
            max_length=6,
            required=True
        )
        self.add_item(self.piece_stat_pct_input)

        self.current_substat_roll_input = TextInput(
            label=f"% de substats actuel",
            placeholder="Ex: 3",
            min_length=1,
            max_length=5,
            required=True
        )
        self.add_item(self.current_substat_roll_input)

    async def on_submit(self, interaction: discord.Interaction):
        try:
            stat_noire = int(self.stat_noire_input.value)
            stat_verte = int(self.stat_verte_input.value)
            base_stat = stat_noire - stat_verte
            piece_stat_pct = float(self.piece_stat_pct_input.value.replace(",", "."))
            current_substat_roll = float(self.current_substat_roll_input.value.replace(",", "."))

            if base_stat <= 0:
                await interaction.response.send_message(
                    "❌ **Erreur** : Les stats noires doivent être supérieures aux stats vertes",
                    ephemeral=True
                )
                return

            if not 0 <= piece_stat_pct <= 100:
                await interaction.response.send_message(
                    "❌ Le % de la stat doit être entre 0 et 100%",
                    ephemeral=True
                )
                return

            if not 0 <= current_substat_roll <= MAX_SUBSTAT:
                await interaction.response.send_message(
                    f"❌ Les substats doivent être entre 0 et {MAX_SUBSTAT}% ",
                    ephemeral=True
                )
                return

            pivot_result = calculate_pivot_7ds(
                gear_key=self.gear_key,
                pct_stat_ssr=piece_stat_pct,
                base_stat=base_stat
            )
            
            pivot = pivot_result['pivot']
            ssr_piece_stat = round(pivot_result['ssr_piece_stat'])
            r_total = round(pivot_result['r_total'])
            
            ssr_current_substat_value = base_stat * current_substat_roll / 100
            ssr_current_total = base_stat + ssr_piece_stat + ssr_current_substat_value
            
            if current_substat_roll >= pivot:
                surplus = round(current_substat_roll - pivot, 2)
                total_surplus = round(ssr_current_total - r_total)
                message = (
                    f"✅ **  Ta pièce bat déjà la R 15% ! <:gotosleep:871036926549975112> **\n\n"
                    f"Marge : **+{surplus}%** soit **+{total_surplus:,}** {self.gear_info['type']}"
                )
                color = 0x2ecc71
            else:
                missing = round(pivot - current_substat_roll, 2)
                stat_manquante = round(r_total - ssr_current_total)
                message = (
                    f"🎯 **Objectif : {pivot}% de substats TOTAL**\n\n"
                    f"Actuellement : **{current_substat_roll}%**\n"
                    f"Reste à roller : **+{missing}%**\n"
                    f"Manque : **{stat_manquante:,}** {self.gear_info['type']}"
                )
                color = 0xe74c3c

            embed = discord.Embed(
                title=f"⚖️ {self.gear_key.capitalize()} - SSR vs R 15%",
                description=message,
                color=color
            )
            
            embed.add_field(name="Stats noires", value=f"{stat_noire:,}", inline=True)
            embed.add_field(name="Stats vertes", value=f"{stat_verte:,}", inline=True)
            embed.add_field(name="Base calculée", value=f"{base_stat:,}", inline=True)

            if not pivot_result['rentable']:
                embed.add_field(
                    name="⚠️ Attention",
                    value=f"Le pivot ({pivot}%) dépasse {MAX_SUBSTAT}% : Pièce trop faible  <:dogkek:923909141523734528>   ",
                    inline=False
                )

            embed.set_footer(text="Lampa Calculator • Consultez les dms de Lampouille pour plus d'infos")

            await interaction.response.send_message(embed=embed)
            
            # Supprimer le message original avec les boutons
            try:
                await self.original_message.delete()
            except:
                pass

        except ValueError:
            await interaction.response.send_message(
                "❌ **Erreur** : Formats invalides",
                ephemeral=True
            )
        except Exception as e:
            print(f"[ERREUR COMPARE] {e}", flush=True)
            traceback.print_exc()
            await interaction.response.send_message(
                f"❌ Erreur : {e}",
                ephemeral=True
            )

# === VUES ===
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
                    await interaction.response.send_modal(modal_class(key, interaction.message))
                
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
        .shape1 { width: 400px; height: 400px; background: #ff6b6b; top: -100px; left: -100px; }
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
        @keyframes pulse { 0%, 100% { transform: scale(1); } 50% { transform: scale(1.05); } }
        .status-dot {
            width: 12px;
            height: 12px;
            background: #4caf50;
            border-radius: 50%;
            box-shadow: 0 0 15px #4caf50;
            animation: blink 1.5s infinite;
        }
        @keyframes blink { 0%, 100% { opacity: 1; } 50% { opacity: 0.3; } }
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
        title="🧮 Gear Roll Calculator",
        description="Sélectionnez le type d'équipement à analyser :",
        color=0x3498db
    )
    embed.set_footer(text="Cliquez sur un bouton pour commencer")
    await interaction.response.send_message(embed=embed, view=PivotView())

@tree.command(name="comparer", description="⚖️ Estimer le roll à viser pour battre du R maxé")
async def comparer(interaction: discord.Interaction):
    embed = discord.Embed(
        title="<:cash:936291615679598672>  Calculateur de roll SSR  <:cash:936291615679598672> ",
        description="Choisissez le type d'équipement à comparer :",
        color=0x9b59b6
    )
    embed.set_footer(text="Cliquez sur un bouton pour commencer")
    await interaction.response.send_message(embed=embed, view=CompareView())

# === DÉMARRAGE ===
if __name__ == "__main__":
    keep_alive()
    bot.run(TOKEN)




