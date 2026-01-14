import os
import json
import asyncio
import re
import subprocess
from dotenv import load_dotenv
from telethon import TelegramClient, events

# --- CONFIGURATION COULEURS ---
R, G, Y, B, M, C, W = "\033[1;91m", "\033[1;92m", "\033[1;93m", "\033[1;94m", "\033[1;95m", "\033[1;96m", "\033[1;97m"
RESET = "\033[0m"

# --- CONFIGURATION ---
TIKTOK_PACKAGE = "com.zhiliaoapp.musically"
TERMUX_PACKAGE = "com.termux/com.termux.app.TermuxActivity"

# 📍 NOUVELLES COORDONNÉES (Sélecteur d'app & Actions)
# Logique : Quand le menu "Ouvrir avec" apparait
APP_CLONES_COORDS = {
    1: "145 2015",  # Clone 1
    2: "340 2015",  # Clone 2
    3: "535 2015"   # Clone 3
}

ACTIONS_COORDS = {
    "LIKE": "990 1200",   # Bouton J'aime
    "FOLLOW": "350 840"   # Bouton Suivre
}

load_dotenv()
API_ID = os.getenv('API_ID')
API_HASH = os.getenv('API_HASH')
TARGET_BOT = '@SmmKingdomTasksBot'

class TaskBot:
    def __init__(self):
        self.accounts = self.load_accounts()
        self.stats = self.load_stats()
        self.current_account_index = 0
        self.client = TelegramClient('session_telebot', int(API_ID), API_HASH)
        self.working = False
        self.device_id = None
        self.adb_prefix = "adb shell"

    def load_accounts(self):
        try:
            with open('accounts.json', 'r') as f: return json.load(f)
        except: return []

    def load_stats(self):
        try:
            with open('stats.json', 'r') as f: return json.load(f)
        except: return {"total_earned": 0.0, "tasks_completed": 0}

    def save_stats_now(self):
        with open('stats.json', 'w') as f: json.dump(self.stats, f, indent=4)

    def detect_device(self):
        try:
            output = subprocess.check_output(["adb", "devices"]).decode("utf-8")
            lines = output.strip().split('\n')[1:]
            devices = [line.split('\t')[0] for line in lines if "\tdevice" in line]
            if not devices: return False
            self.device_id = devices[0]
            self.adb_prefix = f"adb -s {self.device_id} shell"
            return True
        except: return False

    async def run_adb_interaction(self, account_idx, link, action):
        if not self.device_id and not self.detect_device(): return False

        # On s'assure que l'index du compte correspond à un slot (1, 2 ou 3)
        # Si tu as plus de 3 comptes, ça boucle (Compte 4 -> Slot 1, etc.)
        slot_number = ((account_idx - 1) % 3) + 1
        
        # Récupération des coordonnées du slot
        clone_coord = APP_CLONES_COORDS.get(slot_number)
        
        if not clone_coord:
            print(f"{R}❌ Erreur coordonnée slot {slot_number}{RESET}")
            return False

        try:
            # 1. Nettoyage (Fermer l'ancien TikTok pour éviter les conflits)
            os.system(f"{self.adb_prefix} am force-stop {TIKTOK_PACKAGE}")
            await asyncio.sleep(1)

            # 2. OUVERTURE DIRECTE DU LIEN (Déclenche le menu "Choisir une app")
            print(f"{Y}🚀 Ouverture du lien (Intent)...{RESET}")
            # Cette commande force l'ouverture de l'URL, Android demandera "Avec quelle app ?"
            cmd = f'{self.adb_prefix} am start -a android.intent.action.VIEW -d "{link}" > /dev/null 2>&1'
            os.system(cmd)

            # 3. Attente affichage du menu "Ouvrir avec"
            await asyncio.sleep(3)

            # 4. Sélection du Clone TikTok (1, 2 ou 3)
            print(f"{B}point👉 Clic sur Clone {slot_number} (Coords: {clone_coord}){RESET}")
            os.system(f"{self.adb_prefix} input tap {clone_coord}")

            # 5. ATTENTE CHARGEMENT (40 secondes)
            print(f"{C}⏳ Chargement de l'app (40s)...{RESET}")
            await asyncio.sleep(40)

            # 6. ACTION (LIKE ou FOLLOW)
            if "Like" in action:
                print(f"{M}❤️ Click J'aime ({ACTIONS_COORDS['LIKE']}){RESET}")
                os.system(f"{self.adb_prefix} input tap {ACTIONS_COORDS['LIKE']}")
            else:
                print(f"{M}👤 Click Suivre ({ACTIONS_COORDS['FOLLOW']}){RESET}")
                os.system(f"{self.adb_prefix} input tap {ACTIONS_COORDS['FOLLOW']}")
            
            await asyncio.sleep(3)
            
            # 7. Fermeture et Retour Termux
            print(f"{Y}🏁 Fermeture...{RESET}")
            os.system(f"{self.adb_prefix} am force-stop {TIKTOK_PACKAGE}")
            os.system(f"{self.adb_prefix} am start -n {TERMUX_PACKAGE} > /dev/null 2>&1")
            return True

        except Exception as e:
            print(f"{R}❌ Erreur Interaction : {e}{RESET}")
            return False

    async def start_telegram(self):
        if not self.detect_device(): return
        print(f"\n{M}┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓")
        print(f"┃      {W}BOT EN ATTENTE DE TÂCHES{M}        ┃")
        print(f"┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛{RESET}")
        try:
            await self.client.start()
            self.client.add_event_handler(self.message_handler, events.NewMessage(chats=TARGET_BOT))
            self.working = True
            await self.client.send_message(TARGET_BOT, 'TikTok')
            await self.client.run_until_disconnected()
        except Exception as e: print(f"{R}❌ Erreur Telegram : {e}{RESET}")

    async def message_handler(self, event):
        if not self.working: return
        text = event.message.message or ""
        # Gestion des boutons
        buttons = event.message.buttons

        if "Link :" in text and "Action :" in text:
            link_match = re.search(r"Link\s*:\s*(https?://[^\s\n]+)", text)
            action_match = re.search(r"Action\s*:\s*([^\n]+)", text)
            
            if link_match and action_match:
                url, action = link_match.group(1), action_match.group(1)
                
                # Index du compte actuel (1, 2, 3...)
                acc_idx = self.current_account_index + 1
                
                success = await self.run_adb_interaction(acc_idx, url, action)
                
                if success and buttons:
                    # Clic automatique sur "Completed"
                    for i, row in enumerate(buttons):
                        for j, btn in enumerate(row):
                            if any(x in btn.text for x in ["Completed", "✅"]):
                                await asyncio.sleep(2)
                                await event.message.click(i, j)
                                print(f"{G}💰 Tâche validée !{RESET}")
                                return

        elif "Sorry" in text:
            print(f"{Y}💤 Pas de tâche. Changement de compte...{RESET}")
            # Passage au compte suivant
            self.current_account_index = (self.current_account_index + 1) % len(self.accounts) if self.accounts else 0
            await asyncio.sleep(5)
            await self.client.send_message(TARGET_BOT, 'TikTok')

async def main_menu():
    bot = TaskBot()
    while True:
        os.system('clear')
        print(f"{M}╔════════════════════════════════════════════╗")
        print(f"║{W}   SMM KINGDOM BOT v7 - DIRECT LINK        {M}║")
        print(f"╠════════════════════════════════════════════╣")
        print(f"║ {G}Solde : {W}{bot.stats['total_earned']:.2f} USD{M}              ║")
        print(f"║ {Y}[1]{W} Lancer le Bot                         {M}║")
        print(f"║ {Y}[2]{W} Ajouter Compte                        {M}║")
        print(f"║ {R}[4]{W} Quitter                               {M}║")
        print(f"╚════════════════════════════════════════════╝{RESET}")
        choice = input(f"{C}➤ Choix : {RESET}")
        if choice == '1': 
            if not bot.accounts:
                print("Ajoutez d'abord des comptes !")
                await asyncio.sleep(2)
            else:
                await bot.start_telegram()
        elif choice == '2':
            name = input("Nom : ")
            if name: 
                bot.accounts.append(name)
                with open('accounts.json', 'w') as f: json.dump(bot.accounts, f)
        elif choice == '4': break

if __name__ == '__main__':
    asyncio.run(main_menu())
