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

# === MODAL POUR /pivot ===
class PivotModal(Modal):
    def __init__(self):
        super().__init__(title="📊 Calcul des Pivots")
        
        self.stat_noire_hp = TextInput(
            label="HP affiché (noir)",
            placeholder="Ex: 207152",
            min_length=2,
            max_length=8,
            required=True
        )
        self.add_item(self.stat_noire_hp)
        
        self.stat_verte_hp = TextInput(
            label="HP bonus (vert)",
            placeholder="Ex: 90182",
            min_length=1,
            max_length=8,
            required=True
        )
        self.add_item(self.stat_verte_hp)
        
        self.stat_noire_atk = TextInput(
            label="ATK affiché (noir)",
            placeholder="Ex: 13836",
            min_length=2,
            max_length=8,
            required=True
        )
        self.add_item(self.stat_noire_atk)
        
        self.stat_verte_atk = TextInput(
            label="ATK bonus (vert)",
            placeholder="Ex: 5581",
            min_length=1,
            max_length=8,
            required=True
        )
        self.add_item(self.stat_verte_atk)

    async def on_submit(self, interaction: discord.Interaction):
        try:
            # Calcul bases
            stat_noire_hp = int(self.stat_noire_hp.value)
            stat_verte_hp = int(self.stat_verte_hp.value)
            base_hp = stat_noire_hp - stat_verte_hp
            
            stat_noire_atk = int(self.stat_noire_atk.value)
            stat_verte_atk = int(self.stat_verte_atk.value)
            base_atk = stat_noire_atk - stat_verte_atk
            
            # Validation
            if base_hp <= 0 or base_atk <= 0:
                await interaction.response.send_message(
                    "❌ **Erreur** : Les stats noires doivent être supérieures aux stats vertes",
                    ephemeral=True
                )
                return
            
            # Embed principal
            embed = discord.Embed(
                title="📊 Pivots SSR 100% vs R 15%",
                description=(
                    "**Rolls minimum sur pièces SSR 100% pour battre R 15% maxée**\n\n"
                    f"📈 **Stats de Base :**\n"
                    f"🔵 HP : `{base_hp:,}`\n"
                    f"🔴 ATK : `{base_atk:,}`"
                ),
                color=0xf39c12
            )
            
            # Grouper par type
            hp_pieces = []
            atk_pieces = []
            
            for gear_key, gear_data in GEAR_DATA.items():
                stat_type = gear_data['type']
                
                # Skip DEF car pas de stats DEF demandées
                if stat_type == "DEF":
                    continue
                
                base_stat = base_hp if stat_type == "HP" else base_atk
                pivot = calculate_pivot_old(gear_key, base_stat)
                emoji = gear_data['emoji']
                
                # Interprétation
                if pivot > 13.5:
                    verdict = "⚠️ Dur"
                elif pivot < 10:
                    verdict = "✅ Facile"
                else:
                    verdict = "⚖️ Moyen"
                
                piece_info = f"{emoji} **{gear_key.capitalize()}** : `{pivot}%` {verdict}"
                
                if stat_type == "HP":
                    hp_pieces.append(piece_info)
                else:
                    atk_pieces.append(piece_info)
            
            # Ajouter les pièces HP
            if hp_pieces:
                embed.add_field(
                    name="🔵 Pièces HP",
                    value="\n".join(hp_pieces),
                    inline=False
                )
            
            # Ajouter les pièces ATK
            if atk_pieces:
                embed.add_field(
                    name="🔴 Pièces ATK",
                    value="\n".join(atk_pieces),
                    inline=False
                )
            
            embed.add_field(
                name="💡 Rappel",
                value=(
                    "Plus le pivot est **bas**, plus c'est facile à atteindre.\n"
                    "Ces % sont pour des pièces **SSR 100%** (stat de base maximale)."
                ),
                inline=False
            )
            
            embed.set_footer(text="Lampa Calculator • /help pour plus d'infos")
            
            # Bouton pour aller plus loin
            view = PivotActionView()
            
            await interaction.response.send_message(embed=embed, view=view)
            
        except ValueError:
            await interaction.response.send_message(
                "❌ **Erreur** : Nombres entiers requis",
                ephemeral=True
            )
        except Exception as e:
            print(f"[ERREUR PIVOT] {e}", flush=True)
            traceback.print_exc()
            await interaction.response.send_message(
                f"❌ Erreur : {e}",
                ephemeral=True
            )

# === VIEW AVEC BOUTON ACTION ===
class PivotActionView(View):
    def __init__(self):
        super().__init__(timeout=300)
        
        button = Button(
            label="Calculer mes rolls actuels",
            style=discord.ButtonStyle.primary,
            emoji="🎲",
            custom_id="goto_roll"
        )
        button.callback = self.goto_roll
        self.add_item(button)
    
    async def goto_roll(self, interaction: discord.Interaction):
        await interaction.response.send_message(
            "💡 Utilisez la commande `/roll` pour vérifier où vous en êtes avec vos pièces actuelles !",
            ephemeral=True
        )

# === MODAL POUR /roll ===
class RollModal(Modal):
    def __init__(self, gear_key, original_message):
        super().__init__(title=f"🎲 Mes Rolls - {gear_key.capitalize()}")
        self.gear_key = gear_key
        self.gear_info = GEAR_DATA[gear_key]
        self.original_message = original_message
        
        self.stat_noire_input = TextInput(
            label=f"{self.gear_info['type']} affiché (noir)",
            placeholder="Ex: 207152",
            min_length=2,
            max_length=8,
            required=True
        )
        self.add_item(self.stat_noire_input)
        
        self.stat_verte_input = TextInput(
            label=f"{self.gear_info['type']} bonus (vert)",
            placeholder="Ex: 90182",
            min_length=1,
            max_length=8,
            required=True
        )
        self.add_item(self.stat_verte_input)

        self.piece_stat_pct_input = TextInput(
            label=f"% de la stat de base de ta pièce SSR",
            placeholder="Ex: 50 (si pièce = 6200/12400)",
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
                    f"❌ Les substats doivent être entre 0 et {MAX_SUBSTAT}%",
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
                    f"✅ **Ta pièce bat déjà la R 15% !**\n\n"
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
                color = self.gear_info['color']

            embed = discord.Embed(
                title=f"{self.gear_info['emoji']} {self.gear_key.capitalize()} - SSR vs R 15%",
                description=message,
                color=color
            )
            
            embed.add_field(name="Stats noires", value=f"`{stat_noire:,}`", inline=True)
            embed.add_field(name="Stats vertes", value=f"`{stat_verte:,}`", inline=True)
            embed.add_field(name="Base calculée", value=f"`{base_stat:,}`", inline=True)

            if not pivot_result['rentable']:
                embed.add_field(
                    name="⚠️ Attention",
                    value=f"Le pivot ({pivot}%) dépasse {MAX_SUBSTAT}% : pièce trop faible",
                    inline=False
                )

            # Ajouter l'image de la pièce
            image_filename = self.gear_info['image']
            file = discord.File(f"./images/{image_filename}", filename=image_filename)
            embed.set_thumbnail(url=f"attachment://{image_filename}")
            
            embed.set_footer(text="Lampa Calculator • /help pour plus d'infos")

            await interaction.response.send_message(embed=embed, file=file)
            
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
            print(f"[ERREUR ROLL] {e}", flush=True)
            traceback.print_exc()
            await interaction.response.send_message(
                f"❌ Erreur : {e}",
                ephemeral=True
            )

# === VIEW POUR /roll ===
def create_roll_view():
    class RollView(View):
        def __init__(self):
            super().__init__(timeout=None)
            for row_idx, (gear_key, gear_data) in enumerate(GEAR_DATA.items()):
                button = Button(
                    label=f"{gear_key.capitalize()}",
                    style=discord.ButtonStyle.primary if gear_data['type'] == 'HP' 
                          else discord.ButtonStyle.danger if gear_data['type'] == 'ATK'
                          else discord.ButtonStyle.success,
                    emoji=gear_data['emoji'],
                    custom_id=f"roll_{gear_key}",
                    row=row_idx // 2
                )
                
                async def callback(interaction: discord.Interaction, key=gear_key):
                    await interaction.response.send_modal(RollModal(key, interaction.message))
                
                button.callback = callback
                self.add_item(button)
    
    return RollView

# === COMMANDES SLASH ===
@tree.command(name="pivot", description="📊 Calcule les pivots pour battre R 15% avec SSR 100%")
async def pivot_command(interaction: discord.Interaction):
    """Calcule les pivots SSR 100% vs R 15% pour tous les équipements"""
    await interaction.response.send_modal(PivotModal())

@tree.command(name="roll", description="🎲 Vérifie tes rolls : combien il te manque ?")
async def roll_command(interaction: discord.Interaction):
    """Compare ta pièce SSR actuelle avec R 15%"""
    embed = discord.Embed(
        title="🎲 Vérifier mes rolls",
        description="Sélectionne le type d'équipement à analyser :",
        color=0x9b59b6
    )
    embed.set_footer(text="Lampa Calculator • /help pour plus d'infos")
    
    view = create_roll_view()()
    await interaction.response.send_message(embed=embed, view=view)

@tree.command(name="help", description="❓ Guide d'utilisation du bot")
async def help_command(interaction: discord.Interaction):
    """Affiche l'aide et les explications"""
    embed = discord.Embed(
        title="📖 Lampa Calculator - Guide",
        description="Bot d'optimisation d'équipement pour The Seven Deadly Sins: Grand Cross",
        color=0x3498db
    )
    
    # Commande /pivot
    embed.add_field(
        name="📊 `/pivot` - Calculer les pivots",
        value=(
            "**À quoi ça sert ?**\n"
            "Calcule le % de substats minimum qu'une pièce **SSR 100%** doit avoir "
            "pour battre une **R 15% maxée**.\n\n"
            "**Comment l'utiliser ?**\n"
            "1. Entre tes stats HP et ATK (noires et vertes)\n"
            "2. Le bot calcule automatiquement les pivots pour TOUTES les pièces\n"
            "3. Plus le pivot est bas, plus c'est facile à atteindre !\n\n"
            "**Interprétation :**\n"
            "✅ **< 10%** : Facile, équipe du SSR sans hésiter\n"
            "⚖️ **10-13.5%** : Moyen, faisable\n"
            "⚠️ **> 13.5%** : Dur, garde ta R 15% si SSR mal rollé"
        ),
        inline=False
    )
    
    # Commande /roll
    embed.add_field(
        name="🎲 `/roll` - Vérifier mes rolls",
        value=(
            "**À quoi ça sert ?**\n"
            "Compare ta pièce SSR actuelle avec une R 15% maxée "
            "et te dit combien de % il te reste à roller.\n\n"
            "**Comment l'utiliser ?**\n"
            "1. Choisis le type d'équipement (Ceinture, Orbe, etc.)\n"
            "2. Entre tes stats (noires et vertes)\n"
            "3. Indique le % de ta pièce SSR et tes substats actuels\n"
            "4. Le bot te dit si tu bats déjà la R ou combien il te manque\n\n"
            "**Exemple de résultat :**\n"
            "🎯 Objectif : 14.47% substats TOTAL\n"
            "Actuellement : 3%\n"
            "Reste à roller : +11.47%"
        ),
        inline=False
    )
    
    # Explications
    embed.add_field(
        name="🧮 Comment ça marche ?",
        value=(
            "**Formule CC :**\n"
            "`CC = HP × 0.2 + ATK × 1.0 + DEF × 0.8`\n\n"
            "**Substats :**\n"
            "Les substats s'appliquent sur ta **BASE** (stats noires - vertes), "
            "pas sur la pièce !\n\n"
            "**Exemple :**\n"
            "Base HP : 150,000\n"
            "Substats 3% = 150,000 × 3% = **4,500 HP**\n"
            "(pas 6,200 × 3% = 186)"
        ),
        inline=False
    )
    
    # Tips
    embed.add_field(
        name="💡 Conseils Pro",
        value=(
            "• **R 15% d'abord** : Beaucoup moins cher que SSR\n"
            "• **Ceintures en priorité** : Meilleur ratio CC/Gold\n"
            "• **Roll 12-13%** : Plus rentable que viser 15% parfait\n"
            "• **Type par type** : Meilleur pour Box CC que perso par perso"
        ),
        inline=False
    )
    
    embed.set_footer(text="Développé par Lampouille • Version 2.0")
    
    await interaction.response.send_message(embed=embed)

# === ÉVÉNEMENTS ===
@client.event
async def on_ready():
    await tree.sync()
    print(f'✅ Bot connecté : {client.user}')
    print(f'📊 Commandes disponibles : /pivot, /roll, /help')

# === WEB SERVER (KEEP-ALIVE) ===
app = Flask(__name__)

@app.route('/')
def home():
    return render_template_string('''
    <!DOCTYPE html>
    <html>
    <head>
        <title>Lampa Calculator</title>
        <style>
            body { 
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                text-align: center; 
                padding: 50px; 
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                margin: 0;
            }
            .container {
                background: rgba(255, 255, 255, 0.1);
                border-radius: 20px;
                padding: 40px;
                max-width: 600px;
                margin: 0 auto;
                backdrop-filter: blur(10px);
                box-shadow: 0 8px 32px 0 rgba(31, 38, 135, 0.37);
            }
            h1 { 
                color: #fff;
                font-size: 3em;
                margin-bottom: 10px;
            }
            .status {
                display: inline-block;
                padding: 8px 20px;
                background: #2ecc71;
                border-radius: 20px;
                font-weight: bold;
                margin: 20px 0;
            }
            ul {
                list-style: none;
                padding: 0;
            }
            li {
                background: rgba(255, 255, 255, 0.2);
                margin: 10px 0;
                padding: 15px;
                border-radius: 10px;
                font-size: 1.1em;
            }
            .emoji {
                font-size: 1.5em;
                margin-right: 10px;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🤖 Lampa Calculator</h1>
            <p style="font-size: 1.2em;">Bot Discord pour 7DS Grand Cross</p>
            <div class="status">✅ Online</div>
            <hr style="border: 1px solid rgba(255,255,255,0.3); margin: 30px 0;">
            <h3>Commandes disponibles :</h3>
            <ul>
                <li><span class="emoji">📊</span> /pivot - Calculer les pivots</li>
                <li><span class="emoji">🎲</span> /roll - Vérifier mes rolls</li>
                <li><span class="emoji">❓</span> /help - Guide d'utilisation</li>
            </ul>
        </div>
    </body>
    </html>
    ''')

def run_web():
    app.run(host='0.0.0.0', port=8080)

# === DÉMARRAGE ===
if __name__ == "__main__":
    web_thread = Thread(target=run_web)
    web_thread.daemon = True
    web_thread.start()
    
    client.run(TOKEN)
