import os
import json
import asyncio
import re
import subprocess
import requests
from dotenv import load_dotenv
from telethon import TelegramClient, events
from telethon.tl.types import MessageEntityTextUrl

# ================== COULEURS & STYLES (DESIGN) ==================
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
    7: "340 2015",
    8: "530 2015",
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
        self.skip_next_balance = False # Pour gérer le non-comptage des commentaires

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

            # NOTE: La partie commentaire ici ne sera plus appelée car filtrée dans on_message
            if "comment" in action_lower:
                # Code legacy gardé au cas où, mais non utilisé
                pass 
            
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
                
                # --- DESIGN LOG ---
                print(f"\n{DIM}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{RESET}", flush=True)
                print(f"{WHITE}🔗 Task: {BOLD}{action}{RESET} | {YELLOW}Reward: {self.current_reward} CC{RESET}", flush=True)
                
                # ============================================================
                # 🛑 GESTION COMMENTAIRES (IGNORE ADB + PAS DE COMPTAGE)
                # ============================================================
                if "comment" in action.lower():
                    self.skip_next_balance = True # On active le flag pour ne pas compter l'argent
                    print(f"{MAGENTA}💬 Commentaire détecté : {RED}ADB SKIPPED{RESET}", flush=True)
                    print(f"{DIM}   (Fonctionnalité en dev - Validation auto sans reward){RESET}", flush=True)
                    
                    # Simulation délai humain rapide
                    await asyncio.sleep(2)
                    
                    # Clic immédiat
                    if buttons:
                        for i, row in enumerate(buttons):
                            for j, btn in enumerate(row):
                                if "Completed" in btn.text or "✅" in btn.text:
                                    await event.message.click(i, j)
                                    return
                    return # On sort de la fonction ici

                # ============================================================
                # ▶️ GESTION NORMALE (LIKE / FOLLOW)
                # ============================================================
                else:
                    self.skip_next_balance = False # On compte l'argent normalement
                    print(f"{YELLOW}⏳ Exécution en cours sur le téléphone...{RESET}", flush=True)
                    
                    success = await self.do_task(self.index + 1, full_link, action, None)
                    
                    if success:
                        # --- AFFICHAGE COMPLET AVANT LE CLICK ---
                        action_name = "👤 FOLLOW" if "FOLLOW" in self.last_action_type else "❤️ LIKE"
                        print(f"{GREEN}✅ {action_name} EFFECTUÉ AVEC SUCCÈS{RESET}", flush=True)
                        print(f"{CYAN}➡️  Envoi de la validation au bot...{RESET}", flush=True)
                        
                        if buttons:
                            for i, row in enumerate(buttons):
                                for j, btn in enumerate(row):
                                    if "Completed" in btn.text or "✅" in btn.text:
                                        await event.message.click(i, j)
                                        return

        # --- 2. VALIDATION & LOGS ---
        elif "added" in text.lower() or "credited" in text.lower():
            # SI C'ETAIT UN COMMENTAIRE, ON IGNORE LE COMPTAGE
            if self.skip_next_balance:
                print(f"{DIM}🚫 Gain ignoré (Commentaire skipped).{RESET}", flush=True)
                self.skip_next_balance = False # Reset du flag
            
            else:
                # COMPTAGE NORMAL
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

                    print(f"{MAGENTA}💰 SOLDE: {old_balance:.1f} + {gain} = {BOLD}{new_balance:.1f} CC{RESET}", flush=True)
            
            # --- SUITE RAPIDE ---
            await asyncio.sleep(2)
            await self.client.send_message(TARGET_BOT, "TikTok")

        # --- 3. PAS DE TASK ---
        elif "Sorry" in text or "No more" in text:
            print(f"{RED}🚫 Pas de task sur ce compte.{RESET}", flush=True)
            
            self.index = (self.index + 1) % len(self.accounts)
            next_acc = self.accounts[self.index]
            
            await asyncio.sleep(2)
            print(f"\n{WHITE}🔍 Switch vers : {CYAN}{next_acc}{RESET}", flush=True)
            await self.client.send_message(TARGET_BOT, "TikTok")

        # --- 4. GESTION BOUTONS COMPTE ---
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

            # LOGO MICH STYLE
            print(f"""
{BLUE}███╗   ███╗██╗ ██████╗██╗  ██╗
████╗ ████║██║██╔════╝██║  ██║
██╔████╔██║██║██║     ███████║
██║╚██╔╝██║██║██║     ██╔══██║
██║ ╚═╝ ██║██║╚██████╗██║  ██║
╚═╝     ╚═╝╚═╝ ╚═════╝╚═╝  ╚═╝{RESET}
{DIM}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{RESET}
{WHITE}🤖 BOT AUTOMATION V3.1.2 {DIM}|{RESET} {CYAN}BY MICH{RESET}
{DIM}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{RESET}
 📱 Status ADB    : {adb_status}
 👥 Comptes       : {WHITE}{acc_count}{RESET}
 💰 Total Gagné   : {YELLOW}{total_earned:.2f} CashCoins{RESET}
{DIM}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{RESET}
 {WHITE}[1]{RESET} ▶️  LANCER LE FARMING
 {WHITE}[2]{RESET} ➕  AJOUTER UN COMPTE
 {WHITE}[3]{RESET} 📋  GÉRER LES COMPTES
 {WHITE}[4]{RESET} 🔄  RE-SCAN ADB
 {WHITE}[5]{RESET} ☁️  MISE À JOUR
 {WHITE}[6]{RESET} ❌  QUITTER
{DIM}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{RESET}
""", flush=True)
            choice = input(f"{BOLD}{BLUE}➜ CHOIX : {RESET}")

            if choice == "1":
                if self.accounts: 
                    await self.start_telegram()
                else:
                    input(f"{RED}Ajoute au moins un compte d'abord ! [Entrée]{RESET}")

            elif choice == "2":
                while True:
                    clear_screen()
                    print(f"{CYAN}=== ➕ AJOUT DE COMPTE ==={RESET}", flush=True)
                    print(f"{DIM}Entrée vide pour retour.{RESET}\n", flush=True)
                    
                    name = input(f"Nom du compte n°{len(self.accounts)+1} : ")
                    
                    if not name.strip(): break
                    
                    if name in self.accounts:
                        print(f"{RED}Ce compte existe déjà !{RESET}", flush=True)
                        await asyncio.sleep(1)
                    else:
                        self.accounts.append(name)
                        self.save_json("accounts.json", self.accounts)
                        print(f"{GREEN}✅ Compte ajouté.{RESET}", flush=True)
                        await asyncio.sleep(0.5)

            elif choice == "3":
                clear_screen()
                print(f"{CYAN}=== 📋 LISTE COMPTES ==={RESET}", flush=True)
                for i, acc in enumerate(self.accounts, 1):
                    print(f"{CYAN}{i}.{RESET} {acc}", flush=True)
                
                print(f"\n{RED}[S]{RESET} Supprimer | {WHITE}[Entrée]{RESET} Retour", flush=True)
                if input("➜ ").lower() == 's':
                    try:
                        idx = int(input("Numéro : ")) - 1
                        if 0 <= idx < len(self.accounts):
                            self.accounts.pop(idx)
                            self.save_json("accounts.json", self.accounts)
                    except: pass

            elif choice == "4":
                self.detect_device()
            elif choice == "5":
                self.update_script()
            elif choice == "6":
                print(f"{CYAN}Bye !{RESET}", flush=True)
                break

if __name__ == "__main__":
    bot = TikTokTaskBot()
    try:
        asyncio.run(bot.menu())
    except KeyboardInterrupt:
        print("\nArrêt forcé.", flush=True)
