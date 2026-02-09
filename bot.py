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

@tree.command(name="farm", description="💸 Rentabilité Gold vs Enclumes (Podium)")
async def farm_command(interaction: discord.Interaction):
    embed = discord.Embed(
        title="🏆 Rentabilité Farming Enclumes", 
        description="Comparatif sur **8 heures** de farm (Full Stamina)",
        color=0x00dbde
    )
    
    # 1. LE VAINQUEUR (BdG Half)
    embed.add_field(
        name="👑 N°1 : BdG (Half-Stam)", 
        value=(
            "**0,054** Enclume/Stam\n"
            "📈 **915 Enclumes** / 8h\n"
            "✨ *Le ROI absolu. 3x plus rentable.*"
        ), 
        inline=False
    )
    
    # 2. LE DEUXIÈME (BdG Normal)
    embed.add_field(
        name="🥈 N°2 : BdG (70 Stam)", 
        value=(
            "**0,027** Enclume/Stam\n"
            "📉 **~460 Enclumes** / 8h\n"
            "⚠️ *Coûteux en potions.*"
        ), 
        inline=True
    )
    
    # 3. LE PERDANT (Donjon Or)
    embed.add_field(
        name="🥉 N°3 : Donjon Or", 
        value=(
            "**0,020** Enclume/Stam\n"
            "⛔ **240 Enclumes** / 8h\n"
            "❌ *À éviter pour les enclumes.*"
        ), 
        inline=True
    )
    
    # Footer technique
    embed.set_footer(text="Base : 1 Tirage = 0,66 Enclume • 1 Tirage = 200k Gold")
    
    # Bouton vers le site (le Podium visuel)
    view = View()
    # ATTENTION : Remplace l'URL ci-dessous par la VRAIE URL de ton bot Render
    btn = Button(label="Voir le Graphique 📊", style=discord.ButtonStyle.link, url="https://sevends-stuff.onrender.com/farming")
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

# --- PAGE 4 : FARMING (PODIUM EDITION) ---
@app.route('/farming')
def farming():
    content = '''
        <h1 class="liquid-text" style="text-align: center; margin-bottom: 40px;">Rentabilité Enclumes - Merci à Wazdakka pour les data</h1>
        
        <!-- RESUME RAPIDE -->
        <div style="text-align: center; margin-bottom: 50px;">
            <p style="color: #ccc; font-size: 1.1em;">Comparatif sur <strong>8 heures de farm</strong> avec potions.</p>
        </div>

        <!-- LE PODIUM -->
        <div class="podium-container">
            
            <!-- 2ème Place : BDG NORMAL -->
            <div class="podium-step step-2">
                <div class="medal silver">2</div>
                <h3>BdG (70 Stam)</h3>
                <div class="stat-box">
                    <span class="value">0,027</span>
                    <span class="label">Enclume/Stam</span>
                </div>
                <p class="gain">~460 Enclumes</p>
            </div>

            <!-- 1ère Place : BDG HALF STAMINA -->
            <div class="podium-step step-1">
                <div class="crown">👑</div>
                <div class="medal gold">1</div>
                <h3>BdG (Half-Stam)</h3>
                <div class="badge-winner">MEILLEUR RATIO</div>
                <div class="stat-box winner-box">
                    <span class="value">0,054</span>
                    <span class="label">Enclume/Stam</span>
                </div>
                <p class="gain gain-winner">915 Enclumes</p>
                <p class="sub-gain">Le plus rentable !</p>
            </div>

            <!-- 3ème Place : DONJON OR -->
            <div class="podium-step step-3">
                <div class="medal bronze">3</div>
                <h3>Donjon Or</h3>
                <div class="stat-box">
                    <span class="value">0,020</span>
                    <span class="label">Enclume/Stam</span>
                </div>
                <p class="gain">240 Enclumes</p>
            </div>

        </div>

        <!-- VISUALISATION DE L'ECART -->
        <div class="glass-card" style="margin-top: 60px;">
            <h3>📉 L'écart est important !</h3>
            <p style="color: #aaa; margin-bottom: 20px;">Ce que vous perdez en farmant le Donjon Or au lieu d'attendre la Demi-Stamina.</p>
            
            <!-- Barres comparatives -->
            <div class="chart-row">
                <span class="chart-label">Donjon Or</span>
                <div class="chart-bar" style="width: 26%; background: #e74c3c;">240</div>
            </div>
            <div class="chart-row">
                <span class="chart-label">BDG (70 Stam)</span>
                <div class="chart-bar" style="width: 50%; background: #f39c12;">460</div>
            </div>
            <div class="chart-row">
                <span class="chart-label" style="color: #00dbde; font-weight: bold;">BDG (Half)</span>
                <div class="chart-bar" style="width: 100%; background: linear-gradient(90deg, #00dbde, #fc00ff); box-shadow: 0 0 15px #fc00ff;">915</div>
            </div>
        </div>

        <!-- STYLE CSS SPECIFIQUE AU PODIUM (Intégré ici pour simplicité) -->
        <style>
            .podium-container {
                display: flex;
                align-items: flex-end;
                justify-content: center;
                gap: 20px;
                margin-top: 20px;
                height: 400px;
            }

            .podium-step {
                background: rgba(255, 255, 255, 0.05);
                backdrop-filter: blur(10px);
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 15px 15px 0 0;
                text-align: center;
                padding: 20px;
                position: relative;
                transition: transform 0.3s ease;
            }

            .podium-step:hover { transform: translateY(-5px); }

            /* HAUTEURS */
            .step-1 { height: 100%; width: 35%; border-top: 2px solid #00dbde; background: linear-gradient(to bottom, rgba(0, 219, 222, 0.1), rgba(255,255,255,0.02)); z-index: 2; box-shadow: 0 0 30px rgba(0, 219, 222, 0.15); }
            .step-2 { height: 75%; width: 30%; border-top: 2px solid #f39c12; }
            .step-3 { height: 60%; width: 30%; border-top: 2px solid #e74c3c; }

            /* MEDAILLES */
            .medal {
                width: 40px; height: 40px; line-height: 40px; border-radius: 50%;
                font-weight: bold; font-size: 1.2em; margin: 0 auto 10px auto;
                box-shadow: 0 4px 10px rgba(0,0,0,0.3);
            }
            .gold { background: linear-gradient(45deg, #ffd700, #fdb931); color: #000; }
            .silver { background: linear-gradient(45deg, #e0e0e0, #bdbdbd); color: #000; }
            .bronze { background: linear-gradient(45deg, #cd7f32, #a0522d); color: #fff; }

            .crown { font-size: 2em; margin-bottom: -10px; animation: float 3s infinite ease-in-out; }

            /* TEXTES */
            h3 { font-size: 1.1em; margin: 10px 0; color: #fff; }
            .stat-box { background: rgba(0,0,0,0.3); padding: 10px; border-radius: 8px; margin: 15px 0; }
            .winner-box { background: rgba(0, 219, 222, 0.1); border: 1px solid rgba(0, 219, 222, 0.3); }
            
            .value { display: block; font-size: 1.8em; font-weight: bold; }
            .step-1 .value { color: #00dbde; }
            .step-2 .value { color: #f39c12; }
            .step-3 .value { color: #e74c3c; }
            
            .label { font-size: 0.7em; text-transform: uppercase; letter-spacing: 1px; color: #aaa; }

            .badge-winner {
                background: linear-gradient(90deg, #00dbde, #fc00ff);
                color: #000; font-weight: bold; font-size: 0.8em;
                padding: 5px 10px; border-radius: 20px; display: inline-block; margin-bottom: 10px;
            }

            .gain { font-size: 1.2em; font-weight: bold; color: #fff; }
            .gain-winner { font-size: 1.5em; text-shadow: 0 0 10px rgba(255,255,255,0.5); }
            .sub-gain { font-size: 0.8em; color: #00dbde; }

            /* GRAPHIQUE BARRES */
            .chart-row { display: flex; align-items: center; margin-bottom: 15px; }
            .chart-label { width: 100px; font-size: 0.9em; color: #ccc; }
            .chart-bar { 
                height: 30px; line-height: 30px; 
                border-radius: 0 15px 15px 0; padding-left: 10px; 
                color: #fff; font-weight: bold; font-size: 0.9em; text-shadow: 1px 1px 2px rgba(0,0,0,0.5);
                transition: width 1s ease-out;
            }
        </style>
    '''
    return render_template_string(get_layout(content, "Lampa - Farming", "/farming"))


def run_web():
    app.run(host='0.0.0.0', port=8080)


if __name__ == "__main__":
    web_thread = Thread(target=run_web)
    web_thread.daemon = True
    web_thread.start()
    client.run(TOKEN)





