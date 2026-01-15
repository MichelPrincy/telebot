import os
import json
import asyncio
import re
import subprocess
import requests
from dotenv import load_dotenv
from telethon import TelegramClient, events
from telethon.tl.types import MessageEntityTextUrl

# ================== COULEURS & STYLES ==================
RED = "\033[91m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
CYAN = "\033[96m"
MAGENTA = "\033[95m"
WHITE = "\033[97m"
BOLD = "\033[1m"
DIM = "\033[2m"
RESET = "\033[0m"

# ================== PACKAGES ==================
CLONE_CONTAINER_PACKAGE = "com.waxmoon.ma.gp"
TERMUX_PACKAGE = "com.termux/com.termux.app.TermuxActivity"

# ================== COORDONNÉES ==================
APP_CHOOSER = {
    1: "150 1800",
    2: "350 1800",
    3: "530 1800",
    4: "740 1800",
    5: "930 1800",
    6: "150 2015",
}

PAUSE_VIDEO = "530 1030"
LIKE_BUTTON = "990 1200"
FOLLOW_BUTTON = "350 840"
SWIPE_REFRESH = "900 450 900 980 500"

# --- COORDONNÉES COMMENTAIRE ---
COMMENT_ICON = "990 1382"
COMMENT_INPUT_FIELD = "400 2088"
COMMENT_SEND_BUTTON = "980 1130"

# ================== TELEGRAM ==================
load_dotenv()
# Vérifie que les variables existent, sinon valeurs par défaut pour éviter le crash immédiat
try:
    API_ID = int(os.getenv("API_ID"))
    API_HASH = os.getenv("API_HASH")
except:
    print(f"{RED}Erreur: API_ID ou API_HASH manquant dans le fichier .env{RESET}")
    exit()

TARGET_BOT = "@SmmKingdomTasksBot"

# ================== UTILS ==================
def clear_screen():
    os.system("clear")

class TikTokTaskBot:
    def __init__(self):
        self.accounts = self.load_json("accounts.json", [])
        self.stats = self.load_json("stats.json", {"earned": 0.0, "tasks": 0})
        self.index = 0
        self.device_id = None
        self.adb = "adb shell"
        self.client = TelegramClient("session_bot", API_ID, API_HASH)
        
        self.current_reward = 0.0 

    def log(self, msg, color=RESET):
        print(f"{color}{msg}{RESET}")

    def load_json(self, file, default):
        if os.path.exists(file):
            try:
                with open(file, "r") as f:
                    return json.load(f)
            except: return default
        return default

    def save_json(self, file, data):
        with open(file, "w") as f:
            json.dump(data, f, indent=4)

    # ---------- MISE À JOUR ----------
    def update_script(self):
        self.log("🌐 Vérification mise à jour...", CYAN)
        url = "https://raw.githubusercontent.com/MichelPrincy/telebot/main/main.py"
        try:
            response = requests.get(url)
            if response.status_code == 200:
                with open("main.py", "w") as f:
                    f.write(response.text)
                self.log("✅ Mise à jour installée.", GREEN)
                exit()
        except Exception: pass

    # ---------- ADB & GESTION APPS ----------
    def detect_device(self):
        try:
            out = subprocess.check_output(["adb", "devices"]).decode()
            for line in out.splitlines():
                if "\tdevice" in line:
                    self.device_id = line.split("\t")[0]
                    self.adb = f"adb -s {self.device_id} shell"
                    return True
            return False
        except: return False

    def cleanup_apps(self):
        os.system(f"{self.adb} am force-stop {CLONE_CONTAINER_PACKAGE} > /dev/null 2>&1")
        os.system(f"{self.adb} am kill-all > /dev/null 2>&1")

    def focus_termux(self):
        os.system(f"{self.adb} am start --activity-brought-to-front {TERMUX_PACKAGE} > /dev/null 2>&1")

    # ---------- ACTIONS TIKTOK ----------
    async def do_task(self, account_idx, link, action, comment_text=None):
        try:
            self.cleanup_apps()
            coord_clone = APP_CHOOSER.get(account_idx, "150 1800")
            
            # 1. Ouverture & Attente
            os.system(f'{self.adb} am start -a android.intent.action.VIEW -d "{link}" > /dev/null 2>&1')
            await asyncio.sleep(4)
            os.system(f"{self.adb} input tap {coord_clone}")
            await asyncio.sleep(25) # Attente chargement vidéo

            # 2. Réouverture (Refresh pour éviter les bugs de chargement)
            os.system(f'{self.adb} am start -a android.intent.action.VIEW -d "{link}" > /dev/null 2>&1')
            await asyncio.sleep(3)
            os.system(f"{self.adb} input tap {coord_clone}")
            await asyncio.sleep(8)

            # ACTION
            action_lower = action.lower()

            if "comment" in action_lower:
                if comment_text:
                    self.log(f"   ✍️ Écriture du commentaire...", CYAN)
                    os.system(f"{self.adb} input tap {COMMENT_ICON}")
                    await asyncio.sleep(3)
                    os.system(f"{self.adb} input tap {COMMENT_INPUT_FIELD}")
                    await asyncio.sleep(2)
                    # Remplacement des espaces pour ADB
                    safe_text = comment_text.replace(" ", "%s")
                    os.system(f'{self.adb} input text "{safe_text}"')
                    await asyncio.sleep(2)
                    os.system(f"{self.adb} input tap {COMMENT_SEND_BUTTON}")
                else:
                    self.log(f"   ❌ ERREUR: Pas de texte de commentaire reçu.", RED)
                    return False
            
            elif "follow" in action_lower or "profile" in action_lower:
                self.log(f"   👤 Ajout en ami (Follow)...", CYAN)
                os.system(f"{self.adb} input swipe {SWIPE_REFRESH}")
                await asyncio.sleep(4)
                os.system(f"{self.adb} input tap {FOLLOW_BUTTON}")
            
            else:
                self.log(f"   ❤️ Like de la vidéo...", CYAN)
                os.system(f"{self.adb} input tap {PAUSE_VIDEO}")
                await asyncio.sleep(1)
                os.system(f"{self.adb} input tap {LIKE_BUTTON}")

            await asyncio.sleep(3)
            os.system(f"{self.adb} am force-stop {CLONE_CONTAINER_PACKAGE}")
            self.focus_termux()
            return True

        except Exception as e:
            print(f"Erreur ADB: {e}")
            return False

    # ---------- TELEGRAM ----------
    async def start_telegram(self):
        if not self.detect_device():
            self.log("❌ ADB non détecté. Vérifie ta connexion USB/Wifi.", RED)
            input("Appuie sur Entrée pour revenir au menu...")
            return
        
        await self.client.start()
        # On vide les handlers précédents pour éviter les doublons si redémarrage
        self.client.remove_event_handler(self.on_message)
        self.client.add_event_handler(self.on_message, events.NewMessage(chats=TARGET_BOT))
        
        if not self.accounts:
            self.log("⚠️ Aucun compte configuré !", RED)
            return

        current_acc = self.accounts[self.index]
        print(f"\n{BOLD}{WHITE}🚀 Démarrage sur le compte : {CYAN}{current_acc}{RESET}")
        await self.client.send_message(TARGET_BOT, "TikTok")
        await self.client.run_until_disconnected()

    async def on_message(self, event):
        text = event.message.message or ""
        buttons = event.message.buttons

        # --- 1. DETECTION DE TÂCHE ---
        if "Link :" in text and "Action :" in text:
            full_link = None
            if event.message.entities:
                for entity in event.message.entities:
                    if isinstance(entity, MessageEntityTextUrl):
                        full_link = entity.url
                        break
            if not full_link:
                match = re.search(r"Link\s*:\s*(https?://\S+)", text)
                if match: full_link = match.group(1)

            if full_link:
                action = re.search(r"Action\s*:\s*(.+)", text).group(1)
                
                # Extraction Récompense
                reward_match = re.search(r"Reward\s*:\s*([\d\.]+)", text)
                self.current_reward = float(reward_match.group(1)) if reward_match else 0.0
                
                # --- AFFICHAGE ETAPE PAR ETAPE ---
                print(f"\n{DIM}----------------------------------------{RESET}")
                print(f"{GREEN}🎯 Tâche trouvée !{RESET}")
                
                clean_action = "❤️ LIKE"
                comment_content = None

                if "Follow" in action: clean_action = "👤 FOLLOW"
                
                # GESTION SPÉCIALE COMMENTAIRE
                if "comment" in action.lower():
                    clean_action = "💬 COMMENTAIRE"
                    print(f"⚡ Type : {clean_action}")
                    print(f"{CYAN}🔍 Récupération du commentaire...{RESET}")
                    
                    # On attend que le bot envoie le DEUXIEME message (le texte)
                    await asyncio.sleep(1) 
                    
                    # On récupère le dernier message de l'historique
                    history = await self.client.get_messages(TARGET_BOT, limit=1)
                    if history:
                        last_msg = history[0]
                        # On vérifie que ce n'est pas le message du lien lui-même
                        if last_msg.id != event.message.id:
                            comment_content = last_msg.text
                            print(f"{WHITE}📝 Commentaire : {BOLD}{comment_content}{RESET}")
                        else:
                            print(f"{RED}⚠️ Impossible de récupérer le texte (Message unique ?){RESET}")
                    else:
                        print(f"{RED}⚠️ Erreur historique vide.{RESET}")

                else:
                     print(f"⚡ Type : {clean_action}")

                print(f"💰 Récompense prévue : {YELLOW}{self.current_reward} CC{RESET}")
                print(f"{YELLOW}⏳ Exécution en cours...{RESET}")
                
                success = await self.do_task(self.index + 1, full_link, action, comment_content)
                
                if success:
                    # Cliquer sur Completed
                    if buttons:
                        for i, row in enumerate(buttons):
                            for j, btn in enumerate(row):
                                if "Completed" in btn.text or "✅" in btn.text:
                                    await event.message.click(i, j)
                                    return

        # --- 2. VALIDATION & COMPTAGE ARGENT ---
        elif "added" in text.lower() or "credited" in text.lower():
            # Regex stricte pour capturer le montant (ex: "1.1 CC added" ou "+0.5 CC")
            gain_match = re.search(r"\+?\s*([\d\.]+)\s*CC", text)
            
            if gain_match:
                 gain = float(gain_match.group(1))
            elif self.current_reward > 0:
                gain = self.current_reward
            else:
                gain = 0.0
            
            if gain > 0:
                old_balance = self.stats["earned"]
                new_balance = old_balance + gain
                
                self.stats["earned"] = new_balance
                self.stats["tasks"] += 1
                self.save_json("stats.json", self.stats)

                # AFFICHAGE DU SOLDE EN BAS DE LA TACHE
                print(f"{BOLD}{GREEN}✅ Tâche validée !{RESET}")
                print(f"{BOLD}{MAGENTA}💵 Balance : {old_balance:.2f} + {gain} = {new_balance:.2f} CC{RESET}")
                print(f"{DIM}----------------------------------------{RESET}")
            
            # Demander la tâche suivante
            await asyncio.sleep(2)
            current_acc = self.accounts[self.index]
            print(f"\n{WHITE}👉 Tâche suivante pour : {CYAN}{current_acc}{RESET}")
            await self.client.send_message(TARGET_BOT, "TikTok")

        # --- 3. PAS DE TASK ---
        elif "Sorry" in text or "No more" in text:
            print(f"{RED}🚫 Plus de tâches sur ce compte.{RESET}")
            print(f"{DIM}   Passage au compte suivant...{RESET}")
            
            self.index = (self.index + 1) % len(self.accounts)
            next_acc = self.accounts[self.index]
            
            await asyncio.sleep(2)
            print(f"\n{WHITE}🔍 Recherche sur : {CYAN}{next_acc}{RESET}")
            await self.client.send_message(TARGET_BOT, "TikTok")

        # --- 4. GESTION BOUTONS COMPTE (SELECTION) ---
        elif buttons and "Link" not in text:
            target = self.accounts[self.index]
            clicked = False
            for i, row in enumerate(buttons):
                for j, btn in enumerate(row):
                    if btn.text == target:
                        await event.message.click(i, j)
                        clicked = True
                        return
            # Si on n'a pas trouvé le compte dans les boutons, on passe au suivant
            if not clicked and "Select account" in text:
                 print(f"{RED}Compte {target} introuvable dans le menu bot.{RESET}")

    # ---------- MENU PRINCIPAL ----------
    async def menu(self):
        while True:
            clear_screen()
            # Vérification état
            adb_status = f"{GREEN}CONNECTÉ{RESET}" if self.detect_device() else f"{RED}DÉCONNECTÉ{RESET}"
            acc_count = len(self.accounts)
            total_earned = self.stats.get("earned", 0.0)

            print(f"""
{CYAN}╔═══════════════════════════════════════════════╗
║           {BOLD}🤖 TIKTOK AUTOMATION BOT V3{RESET}{CYAN}          ║
╠═══════════════════════════════════════════════╣
║ 📱 État Appareil : {adb_status}{CYAN}                 ║
║ 👥 Comptes Chargés : {WHITE}{acc_count}{CYAN}                       ║
║ 💰 Total Gagné : {YELLOW}{total_earned:.2f} CashCoins{CYAN}            ║
╠═══════════════════════════════════════════════╣
║ {WHITE}1️⃣   ▶️  LANCER LE BOT{CYAN}                        ║
║ {WHITE}2️⃣   ➕  AJOUTER DES COMPTES (Boucle){CYAN}         ║
║ {WHITE}3️⃣   📋  LISTE DES COMPTES{CYAN}                    ║
║ {WHITE}4️⃣   🔄  REDÉTECTER ADB{CYAN}                        ║
║ {WHITE}5️⃣   ☁️  MISE À JOUR (GITHUB){CYAN}                  ║
║ {WHITE}6️⃣   ❌  QUITTER{CYAN}                              ║
╚═══════════════════════════════════════════════╝{RESET}
""")
            choice = input(f"{BOLD}➜ Ton choix : {RESET}")

            if choice == "1":
                if self.accounts: 
                    await self.start_telegram()
                else:
                    input(f"{RED}Ajoute au moins un compte d'abord ! [Entrée]{RESET}")

            # --- MISE A JOUR : BOUCLE D'AJOUT ---
            elif choice == "2":
                while True:
                    clear_screen()
                    print(f"{CYAN}=== ➕ AJOUT DE COMPTE ==={RESET}")
                    print(f"{DIM}Appuie sur ENTRÉE sans rien écrire pour retourner au menu.{RESET}\n")
                    
                    name = input(f"Nom du compte n°{len(self.accounts)+1} : ")
                    
                    if not name.strip(): # Si vide, on sort
                        break
                    
                    if name in self.accounts:
                        print(f"{RED}Ce compte existe déjà !{RESET}")
                        await asyncio.sleep(1)
                    else:
                        self.accounts.append(name)
                        self.save_json("accounts.json", self.accounts)
                        print(f"{GREEN}✅ Compte '{name}' ajouté avec succès !{RESET}")
                        await asyncio.sleep(0.5)

            elif choice == "3":
                clear_screen()
                print(f"{CYAN}=== 📋 COMPTES CONFIGURÉS ==={RESET}")
                if not self.accounts:
                    print("Aucun compte.")
                for i, acc in enumerate(self.accounts, 1):
                    print(f"{CYAN}{i}.{RESET} {acc}")
                
                print(f"\n{RED}[S]{RESET} Supprimer un compte  |  {WHITE}[Entrée]{RESET} Retour")
                sub = input("➜ ").lower()
                if sub == 's':
                    try:
                        idx = int(input("Numéro du compte à supprimer : ")) - 1
                        if 0 <= idx < len(self.accounts):
                            removed = self.accounts.pop(idx)
                            self.save_json("accounts.json", self.accounts)
                            print(f"{RED}Compte '{removed}' supprimé.{RESET}")
                            await asyncio.sleep(1)
                    except: pass

            elif choice == "4":
                self.detect_device()
            elif choice == "5":
                self.update_script()
            elif choice == "6":
                print(f"{CYAN}À bientôt ! 👋{RESET}")
                break

if __name__ == "__main__":
    bot = TikTokTaskBot()
    try:
        asyncio.run(bot.menu())
    except KeyboardInterrupt:
        print("\nArrêt forcé.")
