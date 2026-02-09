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

@tree.command(name="farm", description="💸 Rentabilité Gold vs Enclumes")
async def farm_command(interaction: discord.Interaction):
    embed = discord.Embed(title="💸 Rentabilité Farming Enclumes", color=0xf1c40f)
    
    embed.add_field(
        name="🥇 Le ROI : BdG (Half-Stam)", 
        value="**0,054** Enclume/Stam\n`915 Enclumes en 8h`\nC'est le moment de claquer toutes tes potions !", 
        inline=False
    )
    
    embed.add_field(
        name="🥈 BdG (Normal)", 
        value="**0,027** Enclume/Stam\n`Moins rentable, mais OK si pressé.`", 
        inline=True
    )
    
    embed.add_field(
        name="🥉 Donjon Or", 
        value="**0,020** Enclume/Stam\n`240 Enclumes en 8h`\nAucun intérêt pour les enclumes.", 
        inline=True
    )
    
    embed.set_footer(text="Basé sur 200k gold/tirage et 0,66 enclume/tirage.")
    
    # Ajoute un bouton vers le site pour voir les détails
    view = View()
    btn = Button(label="Voir Graphiques", style=discord.ButtonStyle.link, url="https://ton-url-render.com/farming")
    view.add_item(btn)
    
    await interaction.response.send_message(embed=embed, view=view)


@tree.command(name="help", description="❓ Comment utiliser le bot")
async def help_command(interaction: discord.Interaction):
    log_usage(interaction, "help")
    
    embed = discord.Embed(title="📖 Guide du Lampa Calculator", color=0x3498db)
    
    embed.add_field(
        name="📊 /pivot", 
        value=(
            "Calcule le % de substats qu'il te faut sur une SSR pour battre une R 15%.\n"
            "• **Noir** : La stat totale affichée à l'écran.\n"
            "• **Vert** : La stat bonus (+xxxx) affichée en vert.\n"
            "*(Le bot fait la soustraction tout seul !)*"
        ), 
        inline=False
    )
    
    embed.add_field(
        name="🎲 /roll", 
        value=(
            "Vérifie si ta pièce actuelle est bonne ou poubelle.\n"
            "• Choisis le type de pièce (Ceinture, Bracelet...).\n"
            "• Rentre les stats Noir/Vert.\n"
            "• Rentre le % de la pièce (ex: 95%) et tes rolls actuels (ex: 12.5%)."
        ), 
        inline=False
    )
    
    embed.set_footer(text="Dev by Lampa • Version 2.0")
    await interaction.response.send_message(embed=embed)


@client.event
async def on_ready():
    await tree.sync()
    print(f'✅ Bot connecté : {client.user}')

# === WEB SERVER PREMIUM DESIGN ===
app = Flask(__name__)

# --- LAYOUT GÉNÉRAL (CSS & SQUELETTE) ---
def get_layout(content, title="Lampa Calculator", active_page="/"):
    nav_items = {
        "/": "🏠 Accueil",
        "/guide": "📖 Commandes & Guide",
        "/farming": "💸 Farming",
        "/stats": "📊 Statistiques"
    }
    
    nav_html = ""
    for link, name in nav_items.items():
        active_class = 'active' if link == active_page else ''
        nav_html += f'<a href="{link}" class="nav-item {active_class}">{name}</a>'

    return f'''
    <!DOCTYPE html>
    <html lang="fr">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>{title}</title>
        <style>
            :root {{
                --glass-bg: rgba(255, 255, 255, 0.05);
                --glass-border: rgba(255, 255, 255, 0.1);
                --text-glow: 0 0 10px rgba(118, 75, 162, 0.5);
                --primary-gradient: linear-gradient(45deg, #00dbde, #fc00ff);
            }}

            body {{
                margin: 0;
                padding: 0;
                font-family: 'Inter', 'Segoe UI', sans-serif;
                background: #0f0c29;  /* fallback */
                background: linear-gradient(to bottom right, #24243e, #302b63, #0f0c29);
                color: white;
                min-height: 100vh;
                overflow-x: hidden;
            }}

            /* BACKGROUND ANIMÉ */
            body::before {{
                content: '';
                position: fixed;
                top: -50%;
                left: -50%;
                width: 200%;
                height: 200%;
                background: radial-gradient(circle, rgba(118,75,162,0.15) 0%, transparent 60%),
                            radial-gradient(circle, rgba(0,219,222,0.1) 0%, transparent 50%);
                z-index: -1;
                animation: float 20s infinite linear;
            }}
            
            @keyframes float {{ 0% {{ transform: rotate(0deg); }} 100% {{ transform: rotate(360deg); }} }}

            /* NAVBAR */
            .navbar {{
                display: flex;
                justify-content: center;
                padding: 20px;
                backdrop-filter: blur(10px);
                position: sticky;
                top: 0;
                z-index: 100;
                border-bottom: 1px solid var(--glass-border);
                background: rgba(15, 12, 41, 0.7);
            }}

            .nav-item {{
                color: rgba(255,255,255,0.6);
                text-decoration: none;
                margin: 0 20px;
                font-weight: 500;
                transition: 0.3s;
                position: relative;
                padding: 5px 0;
            }}

            .nav-item:hover, .nav-item.active {{
                color: white;
                text-shadow: var(--text-glow);
            }}
            
            .nav-item.active::after {{
                content: '';
                position: absolute;
                bottom: -5px;
                left: 0;
                width: 100%;
                height: 2px;
                background: var(--primary-gradient);
                box-shadow: 0 0 10px #fc00ff;
            }}

            /* CONTENEUR */
            .container {{
                max-width: 1000px;
                margin: 40px auto;
                padding: 20px;
            }}

            /* EFFET GLASS (La Vitre) */
            .glass-card {{
                background: var(--glass-bg);
                backdrop-filter: blur(12px);
                -webkit-backdrop-filter: blur(12px);
                border: 1px solid var(--glass-border);
                border-radius: 20px;
                padding: 30px;
                box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.37);
                margin-bottom: 30px;
                transition: transform 0.3s ease;
            }}
            
            .glass-card:hover {{
                border-color: rgba(255,255,255,0.2);
            }}

            /* TEXTE LIQUIDE */
            .liquid-text {{
                background: var(--primary-gradient);
                background-size: 200% auto;
                color: #000;
                -webkit-background-clip: text;
                -webkit-text-fill-color: transparent;
                animation: shine 3s linear infinite;
                font-weight: 800;
            }}

            @keyframes shine {{ to {{ background-position: 200% center; }} }}

            /* BOUTON STATUS PULSE */
            .status-badge {{
                display: inline-flex;
                align-items: center;
                padding: 8px 16px;
                background: rgba(46, 204, 113, 0.1);
                border: 1px solid #2ecc71;
                border-radius: 50px;
                color: #2ecc71;
                font-weight: bold;
                box-shadow: 0 0 15px rgba(46, 204, 113, 0.2);
            }}

            .dot {{
                width: 10px;
                height: 10px;
                background: #2ecc71;
                border-radius: 50%;
                margin-right: 10px;
                animation: pulse 2s infinite;
            }}

            @keyframes pulse {{
                0% {{ box-shadow: 0 0 0 0 rgba(46, 204, 113, 0.7); }}
                70% {{ box-shadow: 0 0 0 10px rgba(46, 204, 113, 0); }}
                100% {{ box-shadow: 0 0 0 0 rgba(46, 204, 113, 0); }}
            }}

            /* TABLES */
            table {{ width: 100%; border-collapse: collapse; margin-top: 10px; }}
            th {{ text-align: left; color: #a0a0a0; padding: 10px; border-bottom: 1px solid var(--glass-border); }}
            td {{ padding: 15px 10px; border-bottom: 1px solid rgba(255,255,255,0.05); }}
            
            /* GRID ACCUEIL */
            .grid-3 {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 20px; }}
            .feature-icon {{ font-size: 2em; margin-bottom: 10px; display: block; }}

        </style>
    </head>
    <body>
        <nav class="navbar">
            {nav_html}
        </nav>
        <div class="container">
            {content}
        </div>
    </body>
    </html>
    '''

# --- PAGE 1 : VITRINE (ACCUEIL) ---
@app.route('/')
def home():
    content = f'''
        <div style="text-align: center; margin-bottom: 60px;">
            <h1 style="font-size: 3.5em; margin-bottom: 10px;" class="liquid-text">LAMPA CALCULATOR</h1>
            <p style="font-size: 1.2em; color: #ccc; margin-bottom: 30px;">Optimisez vos équipements 7DS avec précision mathématique.</p>
            
            <div class="status-badge">
                <div class="dot"></div>
                SYSTEM ONLINE
            </div>
        </div>

        <div class="grid-3">
            <div class="glass-card" style="text-align: center;">
                <span class="feature-icon">📐</span>
                <h3>Précision Chirurgicale</h3>
                <p style="color: #aaa; font-size: 0.9em;">Ne gaspillez plus de ressources. Calculez le point de bascule exact entre stuff R et SSR.</p>
            </div>
            <div class="glass-card" style="text-align: center;">
                <span class="feature-icon">🚀</span>
                <h3>Optimisation Box</h3>
                <p style="color: #aaa; font-size: 0.9em;">Analysez vos rolls instantanément et sachez quelles pièces graver en UR.</p>
            </div>
            <div class="glass-card" style="text-align: center;">
                <span class="feature-icon">⚡</span>
                <h3>Rapide & Facile</h3>
                <p style="color: #aaa; font-size: 0.9em;">Des commandes simples, des résultats visuels clairs directement dans Discord.</p>
            </div>
        </div>
        
        <div class="glass-card" style="margin-top: 40px; text-align: center;">
            <h3 style="margin-bottom: 5px;">Rejoindre l'aventure</h3>
            <p style="color: #aaa;">Utilisez les commandes slash <code>/</code> sur votre serveur.</p>
        </div>
    '''
    return render_template_string(get_layout(content, "Lampa - Accueil", "/"))

# --- PAGE 2 : GUIDE & COMMANDES ---
@app.route('/guide')
def guide():
    content = '''
        <h1 class="liquid-text">Commandes & Guide</h1>
        
        <div class="glass-card">
            <h2 style="color: #00dbde;">📊 /pivot</h2>
            <p><strong>C'est quoi ?</strong> La commande essentielle pour savoir si vous devez passer au SSR.</p>
            <p>Elle calcule le pourcentage de substats minimum qu'une pièce SSR doit avoir pour battre une pièce R avec 15% de rolls.</p>
            <br>
            <code>Utilisation : Entrez simplement vos Stats Noires (Total) et Vertes (Bonus).</code>
        </div>

        <div class="glass-card">
            <h2 style="color: #fc00ff;">🎲 /roll</h2>
            <p><strong>C'est quoi ?</strong> Le juge de paix pour vos équipements actuels.</p>
            <p>Vous avez drop une pièce SSR ? Vous avez fait quelques rolls ? Vérifiez si elle est "Rentable" ou "Poubelle".</p>
            <br>
            <code>Utilisation : Sélectionnez la pièce, entrez les stats et le % actuel.</code>
        </div>
        
        <div class="glass-card">
            <h3>💡 Astuce Pro</h3>
            <p style="color: #aaa;">Pour les pièces HP (Ceinture/Orbe), le pivot est souvent plus bas (facile à atteindre). Pour les pièces ATK, c'est plus exigeant !</p>
        </div>
    '''
    return render_template_string(get_layout(content, "Lampa - Guide", "/guide"))

# --- PAGE 3 : STATISTIQUES ---
@app.route('/stats')
def stats():
    top_users = sorted(USAGE_STATS["users"].values(), key=lambda x: x['count'], reverse=True)[:10]
    
    # Génération HTML des tableaux
    rows_users = "".join([f"<tr><td>{u['name']}</td><td><strong>{u['count']}</strong></td></tr>" for u in top_users])
    rows_history = "".join([f"<tr><td>{i['user']}</td><td><span style='color:#00dbde'>/{i['command']}</span></td><td style='color:#aaa'>{i['time']}</td></tr>" for i in USAGE_STATS["history"]])

    content = f'''
        <h1 class="liquid-text">Statistiques en Temps Réel</h1>
        
        <div class="grid-3">
            <div class="glass-card">
                <div style="font-size: 3em; font-weight: bold; color: #fff;">{USAGE_STATS["total_commands"]}</div>
                <div style="color: #aaa;">Commandes Totales</div>
            </div>
            <div class="glass-card">
                <div style="font-size: 3em; font-weight: bold; color: #fff;">{len(USAGE_STATS["users"])}</div>
                <div style="color: #aaa;">Utilisateurs Uniques</div>
            </div>
        </div>

        <div class="glass-card">
            <h3>🏆 Top Utilisateurs</h3>
            <table>
                <tr><th>Pseudo</th><th>Commandes</th></tr>
                {rows_users}
            </table>
        </div>

        <div class="glass-card">
            <h3>⏱️ Historique Récent</h3>
            <table>
                <tr><th>Utilisateur</th><th>Action</th><th>Heure</th></tr>
                {rows_history}
            </table>
        </div>
    '''
    return render_template_string(get_layout(content, "Lampa - Stats", "/stats"))

@app.route('/farming')
def farming():
    content = '''
        <h1 class="liquid-text">Rentabilité du Farming</h1>
        
        <div class="glass-card">
            <h2 style="color: #f1c40f;">💰 Or & Enclumes</h2>
            <p>Analyse de la rentabilité pour obtenir des enclumes via le tirage d'équipement (Gacha).</p>
            
            <div style="display: flex; justify-content: space-between; margin-top: 20px;">
                <div style="text-align: center;">
                    <span style="font-size: 2em; display: block;">200 000</span>
                    <span style="color: #aaa; font-size: 0.9em;">Gold par Tirage</span>
                </div>
                <div style="text-align: center;">
                    <span style="font-size: 2em; display: block; color: #e74c3c;">0,66</span>
                    <span style="color: #aaa; font-size: 0.9em;">Enclumes / Tirage</span>
                </div>
                <div style="text-align: center;">
                    <span style="font-size: 2em; display: block; color: #2ecc71;">5,4 M</span>
                    <span style="color: #aaa; font-size: 0.9em;">Gold Revente (Inv. Full)</span>
                </div>
            </div>
        </div>

        <div class="grid-3">
            <!-- CARTE 1 : DONJON OR -->
            <div class="glass-card" style="border-top: 4px solid #f1c40f;">
                <h3>🏰 Donjon Or (Dimanche)</h3>
                <p style="color: #aaa; margin-bottom: 20px;">Le classique pour farm les golds bruts.</p>
                
                <div style="margin-bottom: 15px;">
                    <div style="display: flex; justify-content: space-between; margin-bottom: 5px;">
                        <span>Enclumes / Stamina</span>
                        <strong>0,020</strong>
                    </div>
                    <div style="background: rgba(255,255,255,0.1); height: 8px; border-radius: 4px;">
                        <div style="background: #f1c40f; width: 37%; height: 100%; border-radius: 4px;"></div>
                    </div>
                </div>

                <ul style="list-style: none; padding: 0; color: #ccc; font-size: 0.9em;">
                    <li>⚡ <strong>30</strong> Stamina / Run</li>
                    <li>💰 <strong>64M</strong> Gold / 8h</li>
                    <li>🔨 <strong>240</strong> Enclumes (via tirage)</li>
                </ul>
            </div>

            <!-- CARTE 2 : BDG 70 (EXTRÊME) -->
            <div class="glass-card" style="border-top: 4px solid #e67e22;">
                <h3>🔥 BdG Infernale (70 Stam)</h3>
                <p style="color: #aaa; margin-bottom: 20px;">Farm rapide mais coûteux en stamina.</p>
                
                <div style="margin-bottom: 15px;">
                    <div style="display: flex; justify-content: space-between; margin-bottom: 5px;">
                        <span>Enclumes / Stamina</span>
                        <strong>0,027</strong>
                    </div>
                    <div style="background: rgba(255,255,255,0.1); height: 8px; border-radius: 4px;">
                        <div style="background: #e67e22; width: 50%; height: 100%; border-radius: 4px;"></div>
                    </div>
                </div>
            </div>

            <!-- CARTE 3 : BDG 35 (HALF STAM) -->
            <div class="glass-card" style="border-top: 4px solid #9b59b6; background: rgba(155, 89, 182, 0.1);">
                <h3>👑 BdG (Half Stamina)</h3>
                <p style="color: #aaa; margin-bottom: 20px;">Le ROI du farm d'enclumes.</p>
                
                <div style="margin-bottom: 15px;">
                    <div style="display: flex; justify-content: space-between; margin-bottom: 5px;">
                        <span style="color: #fff;">Enclumes / Stamina</span>
                        <strong style="color: #00dbde;">0,054</strong>
                    </div>
                    <div style="background: rgba(255,255,255,0.1); height: 8px; border-radius: 4px;">
                        <div style="background: linear-gradient(90deg, #00dbde, #fc00ff); width: 100%; height: 100%; border-radius: 4px; box-shadow: 0 0 10px #fc00ff;"></div>
                    </div>
                </div>

                <ul style="list-style: none; padding: 0; color: #ccc; font-size: 0.9em;">
                    <li>⚡ <strong>35</strong> Stamina / Run</li>
                    <li>🔨 <strong>915</strong> Enclumes / 8h</li>
                    <li>🏆 <strong>2x plus rentable</strong> que tout le reste</li>
                </ul>
            </div>
        </div>

        <div class="glass-card">
            <h3>📝 Conclusion</h3>
            <p>Si vous cherchez des <strong>Enclumes</strong>, attendez absolument la <strong>Demi-Stamina (Half-Stam)</strong> sur les Boss de Guilde (BdG) ou les Boss de Combat.</p>
            <p>Le <strong>Donjon Or</strong> sert uniquement à monter vos persos/équipements, mais c'est le pire moyen d'obtenir des enclumes via le recyclage.</p>
        </div>
    '''
    return render_template_string(get_layout(content, "Lampa - Farming", "/farming"))

def run_web():
    app.run(host='0.0.0.0', port=8080)


if __name__ == "__main__":
    web_thread = Thread(target=run_web)
    web_thread.daemon = True
    web_thread.start()
    client.run(TOKEN)


