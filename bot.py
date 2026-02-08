import discord
from discord import app_commands
from discord.ui import Button, View, Modal, TextInput
import traceback
import os
import datetime
from dotenv import load_dotenv
from flask import Flask, render_template_string
from threading import Thread

# === CONFIGURATION ===
load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")

# === CHEMINS ===
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
IMAGES_DIR = os.path.join(BASE_DIR, "images")

# === ANALYTICS (Mémoire simple) ===
USAGE_STATS = {
    "total_commands": 0,
    "users": {},  # {user_id: {"name": str, "count": int}}
    "history": [] # [{"user": str, "command": str, "time": str}]
}

def log_usage(interaction: discord.Interaction, command_name: str):
    """Enregistre l'utilisation d'une commande"""
    user = interaction.user
    user_name = f"{user.name}#{user.discriminator}" if user.discriminator != "0" else user.name
    
    USAGE_STATS["total_commands"] += 1
    
    # Update user stats
    if user.id not in USAGE_STATS["users"]:
        USAGE_STATS["users"][user.id] = {"name": user_name, "count": 0}
    USAGE_STATS["users"][user.id]["count"] += 1
    
    # Add to history (garder les 50 derniers)
    USAGE_STATS["history"].insert(0, {
        "user": user_name,
        "command": command_name,
        "time": datetime.datetime.now().strftime("%d/%m %H:%M")
    })
    USAGE_STATS["history"] = USAGE_STATS["history"][:50]
    
    print(f"📊 [LOG] {user_name} used /{command_name}")

# === DONNÉES 7DS ===
GEAR_DATA = {
    "ceinture": {"ssr": 12400, "r": 5400, "type": "HP", "emoji": "🛡️", "color": 0x3498db, "image": "icon_weapon_2_belt.jpg"},
    "orbe": {"ssr": 5800, "r": 2900, "type": "HP", "emoji": "🔮", "color": 0x3498db, "image": "icon_weapon_2_rune.jpg"},
    "bracelet": {"ssr": 1240, "r": 540, "type": "ATK", "emoji": "⚔️", "color": 0xe74c3c, "image": "icon_weapon_2_bracelet.jpg"},
    "bague": {"ssr": 640, "r": 290, "type": "ATK", "emoji": "💍", "color": 0xe74c3c, "image": "icon_weapon_2_ring-1.jpg"},
    "collier": {"ssr": 560, "r": 300, "type": "DEF", "emoji": "📿", "color": 0x2ecc71, "image": "icon_weapon_7_amulet.jpg"},
    "boucles": {"ssr": 320, "r": 160, "type": "DEF", "emoji": "💎", "color": 0x2ecc71, "image": "icon_weapon_7_earring.jpg"}
}
MAX_SUBSTAT = 15

# === BOT SETUP ===
intents = discord.Intents.default()
client = discord.Client(intents=intents)
tree = app_commands.CommandTree(client)

# === FONCTIONS CALCUL ===
def calculate_pivot_old(gear_key, base_stat):
    data = GEAR_DATA[gear_key]
    if base_stat == 0: return 0
    delta = data["ssr"] - data["r"]
    pivot = MAX_SUBSTAT - (delta / float(base_stat) * 100)
    return round(pivot, 2)

def calculate_pivot_7ds(gear_key, pct_stat_ssr, base_stat):
    gear_info = GEAR_DATA[gear_key]
    r_total = base_stat + gear_info['r'] + (base_stat * MAX_SUBSTAT / 100)
    ssr_piece_stat = gear_info['ssr'] * (pct_stat_ssr / 100)
    pivot = ((r_total - base_stat - ssr_piece_stat) / base_stat) * 100
    return {'pivot': round(pivot, 2), 'rentable': pivot <= MAX_SUBSTAT}

# === MODAL /PIVOT (Retour aux stats Noir/Vert) ===
class PivotModal(Modal):
    def __init__(self):
        super().__init__(title="📊 Calcul des Pivots")
        
        self.hp_noir = TextInput(label="HP Total (Noir)", placeholder="Ex: 207152", required=True)
        self.add_item(self.hp_noir)
        
        self.hp_vert = TextInput(label="HP Bonus (Vert)", placeholder="Ex: 90182", required=True)
        self.add_item(self.hp_vert)
        
        self.atk_noir = TextInput(label="ATK Total (Noir)", placeholder="Ex: 13836", required=True)
        self.add_item(self.atk_noir)
        
        self.atk_vert = TextInput(label="ATK Bonus (Vert)", placeholder="Ex: 5581", required=True)
        self.add_item(self.atk_vert)

    async def on_submit(self, interaction: discord.Interaction):
        try:
            log_usage(interaction, "pivot")
            
            # Calcul BASE
            base_hp = int(self.hp_noir.value.replace(" ", "")) - int(self.hp_vert.value.replace(" ", ""))
            base_atk = int(self.atk_noir.value.replace(" ", "")) - int(self.atk_vert.value.replace(" ", ""))
            
            if base_hp <= 0 or base_atk <= 0:
                return await interaction.response.send_message("❌ Erreur : Stats invalides (Noir doit être > Vert)", ephemeral=True)

            embed = discord.Embed(title="📊 Pivots SSR 100% vs R 15%", color=0xf39c12)
            embed.add_field(name="📈 Bases calculées", value=f"HP: `{base_hp:,}` • ATK: `{base_atk:,}`", inline=False)
            
            # HP
            hp_txt = ""
            for k in ["ceinture", "orbe"]:
                p = calculate_pivot_old(k, base_hp)
                e = GEAR_DATA[k]['emoji']
                v = "✅ Facile" if p < 10 else "⚖️ Moyen" if p < 13.5 else "⚠️ Dur"
                hp_txt += f"{e} **{k.capitalize()}** : `{p}%` {v}\n"
            embed.add_field(name="🔵 Pièces HP", value=hp_txt, inline=False)
            
            # ATK
            atk_txt = ""
            for k in ["bracelet", "bague"]:
                p = calculate_pivot_old(k, base_atk)
                e = GEAR_DATA[k]['emoji']
                v = "✅ Facile" if p < 10 else "⚖️ Moyen" if p < 13.5 else "⚠️ Dur"
                atk_txt += f"{e} **{k.capitalize()}** : `{p}%` {v}\n"
            embed.add_field(name="🔴 Pièces ATK", value=atk_txt, inline=False)
            
            view = PivotActionView()
            await interaction.response.send_message(embed=embed, view=view)
            
        except ValueError:
            await interaction.response.send_message("❌ Erreur : Chiffres uniquement", ephemeral=True)

class PivotActionView(View):
    def __init__(self):
        super().__init__(timeout=300)
        button = Button(label="Calculer mes rolls", style=discord.ButtonStyle.primary, emoji="🎲", custom_id="goto_roll")
        button.callback = self.goto_roll
        self.add_item(button)
    
    async def goto_roll(self, interaction: discord.Interaction):
        await interaction.response.send_message("💡 Utilisez `/roll` !", ephemeral=True)

# === MODAL /ROLL ===
class RollModal(Modal):
    def __init__(self, gear_key, original_message):
        super().__init__(title=f"🎲 Mes Rolls - {gear_key.capitalize()}")
        self.gear_key = gear_key
        self.gear_info = GEAR_DATA[gear_key]
        self.original_message = original_message
        
        self.stat_noire = TextInput(label=f"{self.gear_info['type']} Noir", placeholder="Ex: 207152", required=True)
        self.add_item(self.stat_noire)
        
        self.stat_verte = TextInput(label=f"{self.gear_info['type']} Vert", placeholder="Ex: 90182", required=True)
        self.add_item(self.stat_verte)

        self.piece_pct = TextInput(label=f"% stat pièce SSR (100 = max)", placeholder="Ex: 100", required=True)
        self.add_item(self.piece_pct)

        self.substat = TextInput(label=f"% substats actuel", placeholder="Ex: 3", required=True)
        self.add_item(self.substat)

    async def on_submit(self, interaction: discord.Interaction):
        try:
            log_usage(interaction, f"roll_{self.gear_key}")
            
            base = int(self.stat_noire.value.replace(" ", "")) - int(self.stat_verte.value.replace(" ", ""))
            piece_pct = float(self.piece_pct.value.replace(",", "."))
            curr_sub = float(self.substat.value.replace(",", "."))

            if base <= 0: return await interaction.response.send_message("❌ Erreur stats", ephemeral=True)

            res = calculate_pivot_7ds(self.gear_key, piece_pct, base)
            pivot = res['pivot']
            
            if curr_sub >= pivot:
                msg = f"✅ **Ta pièce bat déjà la R 15% !**\nMarge : **+{round(curr_sub - pivot, 2)}%**"
                color = 0x2ecc71
            else:
                msg = f"🎯 **Objectif : {pivot}%**\nActuellement : **{curr_sub}%**\nReste : **+{round(pivot - curr_sub, 2)}%**"
                color = self.gear_info['color']

            embed = discord.Embed(title=f"{self.gear_info['emoji']} {self.gear_key.capitalize()}", description=msg, color=color)
            embed.add_field(name="Base calculée", value=f"`{base:,}`", inline=True)

            # Image
            img_path = os.path.join(IMAGES_DIR, self.gear_info['image'])
            if os.path.exists(img_path):
                file = discord.File(img_path, filename=self.gear_info['image'])
                embed.set_thumbnail(url=f"attachment://{self.gear_info['image']}")
                await interaction.response.send_message(embed=embed, file=file)
            else:
                await interaction.response.send_message(embed=embed)
            
            try: await self.original_message.delete()
            except: pass

        except ValueError:
            await interaction.response.send_message("❌ Erreur format", ephemeral=True)

def create_roll_view():
    class RollView(View):
        def __init__(self):
            super().__init__(timeout=None)
            for i, (k, d) in enumerate(GEAR_DATA.items()):
                b = Button(label=k.capitalize(), style=discord.ButtonStyle.primary if d['type']=='HP' else discord.ButtonStyle.danger, emoji=d['emoji'], row=i//2)
                async def cb(intr, key=k): await intr.response.send_modal(RollModal(key, intr.message))
                b.callback = cb
                self.add_item(b)
    return RollView

@tree.command(name="pivot", description="📊 Calcule pivots (Noir/Vert)")
async def pivot_command(interaction: discord.Interaction):
    await interaction.response.send_modal(PivotModal())

@tree.command(name="roll", description="🎲 Vérifie rolls")
async def roll_command(interaction: discord.Interaction):
    view = create_roll_view()()
    await interaction.response.send_message(embed=discord.Embed(title="Choisis une pièce", color=0x9b59b6), view=view)

@tree.command(name="help", description="❓ Guide")
async def help_command(interaction: discord.Interaction):
    log_usage(interaction, "help")
    await interaction.response.send_message("📖 Guide disponible !")

@client.event
async def on_ready():
    await tree.sync()
    print(f'✅ Bot connecté : {client.user}')

# === WEB SERVER AVEC ANALYTICS ===
app = Flask(__name__)

@app.route('/')
def home():
    # Trier les top utilisateurs
    top_users = sorted(USAGE_STATS["users"].values(), key=lambda x: x['count'], reverse=True)[:10]
    
    html = '''
    <!DOCTYPE html>
    <html lang="fr">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Lampa Stats</title>
        <style>
            body { font-family: 'Segoe UI', sans-serif; background: #1a1a2e; color: white; padding: 20px; }
            .container { max-width: 800px; margin: 0 auto; }
            h1 { text-align: center; color: #667eea; margin-bottom: 40px; }
            .stats-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; margin-bottom: 40px; }
            .card { background: rgba(255,255,255,0.05); padding: 20px; border-radius: 15px; text-align: center; }
            .number { font-size: 2.5em; font-weight: bold; color: #f093fb; }
            .label { color: #a0a0a0; }
            table { width: 100%; border-collapse: collapse; background: rgba(255,255,255,0.05); border-radius: 10px; overflow: hidden; margin-bottom: 40px; }
            th, td { padding: 15px; text-align: left; border-bottom: 1px solid rgba(255,255,255,0.1); }
            th { background: rgba(0,0,0,0.3); color: #667eea; }
            tr:hover { background: rgba(255,255,255,0.05); }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>📊 Lampa Analytics</h1>
            
            <div class="stats-grid">
                <div class="card">
                    <div class="number">{{ total }}</div>
                    <div class="label">Commandes Totales</div>
                </div>
                <div class="card">
                    <div class="number">{{ users_count }}</div>
                    <div class="label">Utilisateurs Uniques</div>
                </div>
            </div>

            <h2>🏆 Top Utilisateurs</h2>
            <table>
                <tr><th>Utilisateur</th><th>Commandes</th></tr>
                {% for user in top_users %}
                <tr>
                    <td>{{ user.name }}</td>
                    <td>{{ user.count }}</td>
                </tr>
                {% endfor %}
            </table>

            <h2>🕒 Dernières Activités</h2>
            <table>
                <tr><th>Utilisateur</th><th>Commande</th><th>Heure</th></tr>
                {% for item in history %}
                <tr>
                    <td>{{ item.user }}</td>
                    <td>/{{ item.command }}</td>
                    <td>{{ item.time }}</td>
                </tr>
                {% endfor %}
            </table>
        </div>
    </body>
    </html>
    '''
    return render_template_string(html, 
                                total=USAGE_STATS["total_commands"],
                                users_count=len(USAGE_STATS["users"]),
                                top_users=top_users,
                                history=USAGE_STATS["history"])

def run_web():
    app.run(host='0.0.0.0', port=8080)

if __name__ == "__main__":
    web_thread = Thread(target=run_web)
    web_thread.daemon = True
    web_thread.start()
    client.run(TOKEN)
