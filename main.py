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
ADB_KEYBOARD_PACKAGE = "com.android.adbkeyboard/.AdbIME"

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
try:
    API_ID = int(os.getenv("API_ID"))
    API_HASH = os.getenv("API_HASH")
except:
    print(f"{RED}Erreur: API_ID ou API_HASH manquant dans le fichier .env{RESET}", flush=True)
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
        self.last_action_type = "" 

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
        print(f"{CYAN}🌐 Vérification mise à jour...{RESET}", flush=True)
        url = "https://raw.githubusercontent.com/MichelPrincy/telebot/main/main.py"
        try:
            response = requests.get(url)
            if response.status_code == 200:
                with open("main.py", "w") as f:
                    f.write(response.text)
                print(f"{GREEN}✅ Mise à jour installée.{RESET}", flush=True)
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
                    # Initialisation du clavier ADB
                    self.enable_adb_keyboard()
                    return True
            return False
        except: return False

    def enable_adb_keyboard(self):
        """Force l'activation du clavier ADBKeyBoard pour éviter les erreurs"""
        try:
            os.system(f"{self.adb} ime set {ADB_KEYBOARD_PACKAGE} > /dev/null 2>&1")
        except: pass

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
            await asyncio.sleep(23) # Attente chargement vidéo

            # 2. Réouverture (Refresh)
            os.system(f'{self.adb} am start -a android.intent.action.VIEW -d "{link}" > /dev/null 2>&1')
            await asyncio.sleep(3)
            os.system(f"{self.adb} input tap {coord_clone}")
            
            # --- STRICT : ATTENTE 10S AVANT INTERACTION ---
            print(f"{YELLOW}⏳ Attente stricte 10s...{RESET}", flush=True)
            await asyncio.sleep(10)

            # ACTION
            action_lower = action.lower()

            if "comment" in action_lower:
                self.last_action_type = "COMMENTAIRE"
                if comment_text:
                    # A. METTRE EN PAUSE
                    os.system(f"{self.adb} input tap {PAUSE_VIDEO}")
                    await asyncio.sleep(5)

                    print(f"{CYAN}   ✍️ Écriture via ADBKeyBoard...{RESET}", flush=True)
                    
                    # B. OUVRIR COMMENTAIRES
                    os.system(f"{self.adb} input tap {COMMENT_ICON}")
                    await asyncio.sleep(2)
                    
                    # C. CLIQUER INPUT (Pour donner le focus au clavier ADB)
                    os.system(f"{self.adb} input tap {COMMENT_INPUT_FIELD}")
                    await asyncio.sleep(2)
                    
                    # D. ENVOYER LE TEXTE VIA SUBPROCESS (CORRECTION DU BUG EMOJI)
                    # L'utilisation d'une liste [] empêche le shell d'interpréter les emojis comme des commandes
                    cmd = [
                        "adb", "-s", self.device_id, "shell", "am", "broadcast",
                        "-a", "ADB_INPUT_TEXT",
                        "--es", "msg", comment_text
                    ]
                    
                    try:
                        subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    except Exception as e:
                        print(f"{RED}Erreur envoi texte: {e}{RESET}")
                        # Fallback simple
                        os.system(f'{self.adb} am broadcast -a ADB_INPUT_TEXT --es msg "Wow"')

                    await asyncio.sleep(2)
                    
                    # E. ENVOYER LE MESSAGE (Bouton Send de l'appli)
                    os.system(f"{self.adb} input tap {COMMENT_SEND_BUTTON}")
                else:
                    print(f"{RED}   ❌ ERREUR: Pas de texte de commentaire reçu.{RESET}", flush=True)
                    return False
            
            elif "follow" in action_lower or "profile" in action_lower:
                self.last_action_type = "FOLLOW"
                print(f"{CYAN}   👤 Ajout en ami (Follow)...{RESET}", flush=True)
                os.system(f"{self.adb} input swipe {SWIPE_REFRESH}")
                await asyncio.sleep(4)
                os.system(f"{self.adb} input tap {FOLLOW_BUTTON}")
            
            else:
                self.last_action_type = "LIKE"
                print(f"{CYAN}   ❤️ Like de la vidéo...{RESET}", flush=True)
                os.system(f"{self.adb} input tap {PAUSE_VIDEO}")
                await asyncio.sleep(1)
                os.system(f"{self.adb} input tap {LIKE_BUTTON}")

            await asyncio.sleep(3)
            os.system(f"{self.adb} am force-stop {CLONE_CONTAINER_PACKAGE}")
            self.focus_termux()
            return True

        except Exception as e:
            print(f"Erreur ADB: {e}", flush=True)
            return False

    # ---------- TELEGRAM ----------
    async def start_telegram(self):
        if not self.detect_device():
            print(f"{RED}❌ ADB non détecté. Vérifie ta connexion USB/Wifi.{RESET}", flush=True)
            input("Appuie sur Entrée pour revenir au menu...")
            return
        
        await self.client.start()
        self.client.remove_event_handler(self.on_message)
        self.client.add_event_handler(self.on_message, events.NewMessage(chats=TARGET_BOT))
        
        if not self.accounts:
            print(f"{RED}⚠️ Aucun compte configuré !{RESET}", flush=True)
            return

        current_acc = self.accounts[self.index]
        print(f"\n{BOLD}{WHITE}🚀 Démarrage sur le compte : {CYAN}{current_acc}{RESET}", flush=True)
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
                
                print(f"\n{DIM}---------------task detecting leka--------------{RESET}", flush=True)
                print(f"{WHITE}🔗 Link: {DIM}{full_link[:30]}...{RESET}", flush=True)
                print(f"{WHITE}⚡ Action: {BOLD}{action}{RESET}", flush=True)
                
                comment_content = None
                if "comment" in action.lower():
                    await asyncio.sleep(1) 
                    history = await self.client.get_messages(TARGET_BOT, limit=1)
                    if history:
                        last_msg = history[0]
                        if last_msg.id != event.message.id:
                            comment_content = last_msg.text
                
                print(f"{YELLOW}⏳ Exécution en cours...{RESET}", flush=True)
                
                success = await self.do_task(self.index + 1, full_link, action, comment_content)
                
                if success:
                    if buttons:
                        for i, row in enumerate(buttons):
                            for j, btn in enumerate(row):
                                if "Completed" in btn.text or "✅" in btn.text:
                                    await event.message.click(i, j)
                                    return

        # --- 2. VALIDATION & LOGS PERSONNALISÉS ---
        elif "added" in text.lower() or "credited" in text.lower():
            # Essai de capture du montant dans le message de confirmation
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

                # --- AFFICHAGE STRICT DEMANDÉ ---
                action_name = "❤️ like" if "LIKE" in self.last_action_type else "💬 commentaire"
                if "FOLLOW" in self.last_action_type: action_name = "👤 follow"

                print(f"{BOLD}{CYAN}{action_name} du video{RESET}", flush=True)
                print(f"{GREEN}Video {action_name.split()[-1]}r avec success{RESET}", flush=True) 
                print(f"{MAGENTA}{old_balance:.1f} + {gain} cashcoint = {new_balance:.1f} cashcoint{RESET}", flush=True)
            
            # --- SUITE RAPIDE ---
            await asyncio.sleep(2)
            await self.client.send_message(TARGET_BOT, "TikTok")

        # --- 3. PAS DE TASK ---
        elif "Sorry" in text or "No more" in text:
            print(f"{RED}🚫 Pas de task sur ce compte.{RESET}", flush=True)
            
            self.index = (self.index + 1) % len(self.accounts)
            next_acc = self.accounts[self.index]
            
            await asyncio.sleep(2)
            print(f"\n{WHITE}🔍 Recherche sur : {CYAN}{next_acc}{RESET}", flush=True)
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
            if not clicked and "Select account" in text:
                 print(f"{RED}Compte {target} introuvable dans le menu bot.{RESET}", flush=True)

    # ---------- MENU PRINCIPAL ----------
    async def menu(self):
        while True:
            clear_screen()
            adb_status = f"{GREEN}CONNECTÉ{RESET}" if self.detect_device() else f"{RED}DÉCONNECTÉ{RESET}"
            acc_count = len(self.accounts)
            total_earned = self.stats.get("earned", 0.0)

            print(f"""
{CYAN}╔═══════════════════════════════════════════════╗
║             {BOLD}🤖 TIKTOK AUTOMATION BOT V3.1.1{RESET}{CYAN}             ║
╠═══════════════════════════════════════════════╣
║ 📱 État Appareil : {adb_status}{CYAN}                 ║
║ 👥 Comptes Chargés : {WHITE}{acc_count}{CYAN}                         ║
║ 💰 Total Gagné : {YELLOW}{total_earned:.2f} CashCoins{CYAN}                ║
╠═══════════════════════════════════════════════╣
║ {WHITE}1️⃣    ▶️  LANCER LE BOT{CYAN}                           ║
║ {WHITE}2️⃣    ➕  AJOUTER DES COMPTES (Boucle){CYAN}         ║
║ {WHITE}3️⃣    📋  LISTE DES COMPTES{CYAN}                       ║
║ {WHITE}4️⃣    🔄  REDÉTECTER ADB{CYAN}                          ║
║ {WHITE}5️⃣    ☁️  MISE À JOUR (GITHUB){CYAN}                    ║
║ {WHITE}6️⃣    ❌  QUITTER{CYAN}                                 ║
╚═══════════════════════════════════════════════╝{RESET}
""", flush=True)
            choice = input(f"{BOLD}➜ Ton choix : {RESET}")

            if choice == "1":
                if self.accounts: 
                    await self.start_telegram()
                else:
                    input(f"{RED}Ajoute au moins un compte d'abord ! [Entrée]{RESET}")

            elif choice == "2":
                while True:
                    clear_screen()
                    print(f"{CYAN}=== ➕ AJOUT DE COMPTE ==={RESET}", flush=True)
                    print(f"{DIM}Appuie sur ENTRÉE sans rien écrire pour retourner au menu.{RESET}\n", flush=True)
                    
                    name = input(f"Nom du compte n°{len(self.accounts)+1} : ")
                    
                    if not name.strip():
                        break
                    
                    if name in self.accounts:
                        print(f"{RED}Ce compte existe déjà !{RESET}", flush=True)
                        await asyncio.sleep(1)
                    else:
                        self.accounts.append(name)
                        self.save_json("accounts.json", self.accounts)
                        print(f"{GREEN}✅ Compte '{name}' ajouté avec succès !{RESET}", flush=True)
                        await asyncio.sleep(0.5)

            elif choice == "3":
                clear_screen()
                print(f"{CYAN}=== 📋 COMPTES CONFIGURÉS ==={RESET}", flush=True)
                if not self.accounts:
                    print("Aucun compte.", flush=True)
                for i, acc in enumerate(self.accounts, 1):
                    print(f"{CYAN}{i}.{RESET} {acc}", flush=True)
                
                print(f"\n{RED}[S]{RESET} Supprimer un compte  |  {WHITE}[Entrée]{RESET} Retour", flush=True)
                sub = input("➜ ").lower()
                if sub == 's':
                    try:
                        idx = int(input("Numéro du compte à supprimer : ")) - 1
                        if 0 <= idx < len(self.accounts):
                            removed = self.accounts.pop(idx)
                            self.save_json("accounts.json", self.accounts)
                            print(f"{RED}Compte '{removed}' supprimé.{RESET}", flush=True)
                            await asyncio.sleep(1)
                    except: pass

            elif choice == "4":
                self.detect_device()
            elif choice == "5":
                self.update_script()
            elif choice == "6":
                print(f"{CYAN}À bientôt ! 👋{RESET}", flush=True)
                break

if __name__ == "__main__":
    bot = TikTokTaskBot()
    try:
        asyncio.run(bot.menu())
    except KeyboardInterrupt:
        print("\nArrêt forcé.", flush=True)
