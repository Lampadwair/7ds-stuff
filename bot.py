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

# === CHEMINS ===
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
IMAGES_DIR = os.path.join(BASE_DIR, "images")

# === DONNÉES 7DS ===
GEAR_DATA = {
    "ceinture": {
        "ssr": 12400, 
        "r": 5400, 
        "type": "HP", 
        "emoji": "🛡️", 
        "color": 0x3498db,
        "image": "icon_weapon_2_belt.jpg"
    },
    "orbe": {
        "ssr": 5800, 
        "r": 2900, 
        "type": "HP", 
        "emoji": "🔮", 
        "color": 0x3498db,
        "image": "icon_weapon_2_rune.jpg"
    },
    "bracelet": {
        "ssr": 1240, 
        "r": 540, 
        "type": "ATK", 
        "emoji": "⚔️", 
        "color": 0xe74c3c,
        "image": "icon_weapon_2_bracelet.jpg"
    },
    "bague": {
        "ssr": 640, 
        "r": 290, 
        "type": "ATK", 
        "emoji": "💍", 
        "color": 0xe74c3c,
        "image": "icon_weapon_2_ring-1.jpg"
    },
    "collier": {
        "ssr": 560, 
        "r": 300, 
        "type": "DEF", 
        "emoji": "📿", 
        "color": 0x2ecc71,
        "image": "icon_weapon_7_amulet.jpg"
    },
    "boucles": {
        "ssr": 320, 
        "r": 160, 
        "type": "DEF", 
        "emoji": "💎", 
        "color": 0x2ecc71,
        "image": "icon_weapon_7_earring.jpg"
    }
}

MAX_SUBSTAT = 15

# === BOT SETUP ===
intents = discord.Intents.default()
client = discord.Client(intents=intents)
tree = app_commands.CommandTree(client)

# === FONCTIONS DE CALCUL ===
def calculate_pivot_old(gear_key, base_stat):
    """Calcul pivot SSR 100% vs R 15%"""
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

# === MODAL POUR /pivot (SIMPLIFIÉ) ===
class PivotModal(Modal):
    def __init__(self):
        super().__init__(title="📊 Calcul des Pivots")
        
        self.base_hp = TextInput(
            label="BASE HP (Stat du perso NU)",
            placeholder="Ex: 150000 (Noir - Vert)",
            min_length=4,
            max_length=8,
            required=True
        )
        self.add_item(self.base_hp)
        
        self.base_atk = TextInput(
            label="BASE ATK (Stat du perso NU)",
            placeholder="Ex: 12000 (Noir - Vert)",
            min_length=3,
            max_length=8,
            required=True
        )
        self.add_item(self.base_atk)

    async def on_submit(self, interaction: discord.Interaction):
        try:
            base_hp = int(self.base_hp.value.replace(" ", ""))
            base_atk = int(self.base_atk.value.replace(" ", ""))
            
            # Embed principal
            embed = discord.Embed(
                title="📊 Pivots SSR 100% vs R 15%",
                description=f"Objectifs pour battre une R 15% avec vos stats.",
                color=0xf39c12
            )
            
            embed.add_field(
                name="📈 Bases utilisées",
                value=f"HP: `{base_hp:,}` • ATK: `{base_atk:,}`",
                inline=False
            )
            
            # Calcul HP (Ceinture / Orbe)
            hp_content = ""
            for gear in ["ceinture", "orbe"]:
                pivot = calculate_pivot_old(gear, base_hp)
                emoji = GEAR_DATA[gear]['emoji']
                verdict = "✅ Facile" if pivot < 10 else "⚖️ Moyen" if pivot < 13.5 else "⚠️ Dur"
                hp_content += f"{emoji} **{gear.capitalize()}** : `{pivot}%` {verdict}\n"
                
            embed.add_field(name="🔵 Pièces HP", value=hp_content, inline=False)
            
            # Calcul ATK (Bracelet / Bague)
            atk_content = ""
            for gear in ["bracelet", "bague"]:
                pivot = calculate_pivot_old(gear, base_atk)
                emoji = GEAR_DATA[gear]['emoji']
                verdict = "✅ Facile" if pivot < 10 else "⚖️ Moyen" if pivot < 13.5 else "⚠️ Dur"
                atk_content += f"{emoji} **{gear.capitalize()}** : `{pivot}%` {verdict}\n"
                
            embed.add_field(name="🔴 Pièces ATK", value=atk_content, inline=False)
            
            embed.set_footer(text="Conseil : Vise 12-13% pour être tranquille !")
            
            view = PivotActionView()
            await interaction.response.send_message(embed=embed, view=view)
            
        except ValueError:
            await interaction.response.send_message("❌ Erreur : Entre juste des chiffres (ex: 150000)", ephemeral=True)
        except Exception as e:
            traceback.print_exc()
            await interaction.response.send_message(f"❌ Erreur : {e}", ephemeral=True)

class PivotActionView(View):
    def __init__(self):
        super().__init__(timeout=300)
        button = Button(label="Calculer mes rolls actuels", style=discord.ButtonStyle.primary, emoji="🎲", custom_id="goto_roll")
        button.callback = self.goto_roll
        self.add_item(button)
    
    async def goto_roll(self, interaction: discord.Interaction):
        await interaction.response.send_message("💡 Utilisez `/roll` pour vérifier vos pièces !", ephemeral=True)

# === MODAL POUR /roll ===
class RollModal(Modal):
    def __init__(self, gear_key, original_message):
        super().__init__(title=f"🎲 Mes Rolls - {gear_key.capitalize()}")
        self.gear_key = gear_key
        self.gear_info = GEAR_DATA[gear_key]
        self.original_message = original_message
        
        self.stat_noire_input = TextInput(label=f"{self.gear_info['type']} affiché (noir)", placeholder="Ex: 207152", required=True)
        self.add_item(self.stat_noire_input)
        
        self.stat_verte_input = TextInput(label=f"{self.gear_info['type']} bonus (vert)", placeholder="Ex: 90182", required=True)
        self.add_item(self.stat_verte_input)

        self.piece_stat_pct_input = TextInput(label=f"% stat de ta pièce SSR (100 = max)", placeholder="Ex: 100", required=True)
        self.add_item(self.piece_stat_pct_input)

        self.current_substat_roll_input = TextInput(label=f"% de substats actuel", placeholder="Ex: 3", required=True)
        self.add_item(self.current_substat_roll_input)

    async def on_submit(self, interaction: discord.Interaction):
        try:
            stat_noire = int(self.stat_noire_input.value.replace(" ", ""))
            stat_verte = int(self.stat_verte_input.value.replace(" ", ""))
            base_stat = stat_noire - stat_verte
            piece_stat_pct = float(self.piece_stat_pct_input.value.replace(",", "."))
            current_substat_roll = float(self.current_substat_roll_input.value.replace(",", "."))

            if base_stat <= 0: return await interaction.response.send_message("❌ Erreur stats", ephemeral=True)

            pivot_result = calculate_pivot_7ds(self.gear_key, piece_stat_pct, base_stat)
            pivot = pivot_result['pivot']
            
            # Message de résultat
            if current_substat_roll >= pivot:
                surplus = round(current_substat_roll - pivot, 2)
                msg = f"✅ **Ta pièce bat déjà la R 15% !**\nMarge : **+{surplus}%**"
                color = 0x2ecc71
            else:
                missing = round(pivot - current_substat_roll, 2)
                msg = f"🎯 **Objectif : {pivot}%**\nActuellement : **{current_substat_roll}%**\nReste à roller : **+{missing}%**"
                color = self.gear_info['color']

            embed = discord.Embed(
                title=f"{self.gear_info['emoji']} {self.gear_key.capitalize()} - SSR vs R 15%",
                description=msg,
                color=color
            )
            embed.add_field(name="Base calculée", value=f"`{base_stat:,}`", inline=True)

            # IMAGE HANDLING (CORRIGÉ)
            image_filename = self.gear_info['image']
            image_path = os.path.join(IMAGES_DIR, image_filename)
            
            if os.path.exists(image_path):
                file = discord.File(image_path, filename=image_filename)
                embed.set_thumbnail(url=f"attachment://{image_filename}")
                await interaction.response.send_message(embed=embed, file=file)
            else:
                print(f"⚠️ Image introuvable : {image_path}")
                await interaction.response.send_message(embed=embed)
            
            try: await self.original_message.delete()
            except: pass

        except ValueError:
            await interaction.response.send_message("❌ Erreur format", ephemeral=True)
        except Exception as e:
            traceback.print_exc()
            await interaction.response.send_message(f"❌ Erreur : {e}", ephemeral=True)

def create_roll_view():
    class RollView(View):
        def __init__(self):
            super().__init__(timeout=None)
            for i, (k, d) in enumerate(GEAR_DATA.items()):
                b = Button(label=k.capitalize(), style=discord.ButtonStyle.primary if d['type']=='HP' else discord.ButtonStyle.danger if d['type']=='ATK' else discord.ButtonStyle.success, emoji=d['emoji'], row=i//2)
                async def cb(intr, key=k): await intr.response.send_modal(RollModal(key, intr.message))
                b.callback = cb
                self.add_item(b)
    return RollView

@tree.command(name="pivot", description="📊 Calcule les pivots SSR 100% vs R 15%")
async def pivot_command(interaction: discord.Interaction):
    await interaction.response.send_modal(PivotModal())

@tree.command(name="roll", description="🎲 Vérifie tes rolls actuels")
async def roll_command(interaction: discord.Interaction):
    embed = discord.Embed(title="🎲 Vérifier mes rolls", description="Choisis une pièce :", color=0x9b59b6)
    view = create_roll_view()()
    await interaction.response.send_message(embed=embed, view=view)

@tree.command(name="help", description="❓ Guide rapide")
async def help_command(interaction: discord.Interaction):
    embed = discord.Embed(title="📖 Aide Lampa Calculator", color=0x3498db)
    embed.add_field(name="📊 /pivot", value="Entre ta BASE HP/ATK pour savoir quel % viser.", inline=False)
    embed.add_field(name="🎲 /roll", value="Compare ta SSR actuelle avec une R 15%.", inline=False)
    await interaction.response.send_message(embed=embed)

@client.event
async def on_ready():
    await tree.sync()
    print(f'✅ Bot connecté : {client.user}')

# === WEB SERVER ===
app = Flask(__name__)
@app.route('/')
def home():
    return render_template_string('''
    <!DOCTYPE html>
    <html lang="fr">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Lampa Calculator - 7DS Bot</title>
        <style>
            body { font-family: 'Segoe UI', sans-serif; background: #1a1a2e; color: white; display: flex; justify-content: center; align-items: center; height: 100vh; margin: 0; }
            .container { text-align: center; padding: 40px; background: rgba(255,255,255,0.05); border-radius: 20px; box-shadow: 0 10px 30px rgba(0,0,0,0.5); }
            h1 { background: linear-gradient(45deg, #667eea, #764ba2); -webkit-background-clip: text; -webkit-text-fill-color: transparent; font-size: 2.5em; }
            .status { color: #2ecc71; font-weight: bold; border: 1px solid #2ecc71; padding: 5px 15px; border-radius: 20px; display: inline-block; margin: 20px 0; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>Lampa Calculator</h1>
            <div class="status">✅ Online</div>
            <p>Le bot est actif sur Discord !</p>
        </div>
    </body>
    </html>
    ''')

def run_web():
    app.run(host='0.0.0.0', port=8080)

if __name__ == "__main__":
    web_thread = Thread(target=run_web)
    web_thread.daemon = True
    web_thread.start()
    client.run(TOKEN)
