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
# Le package principal de TikTok (utile pour forcer l'arrêt)
TIKTOK_PACKAGE = "com.zhiliaoapp.musically"
TERMUX_PACKAGE = "com.termux/com.termux.app.TermuxActivity"

# 📍 TES COORDONNÉES EXACTES
APP_PICKER_SLOTS = {
    1: "145 2015",  # Position du clone 1 dans le menu "Ouvrir avec"
    2: "340 2015",  # Position du clone 2
    3: "535 2015"   # Position du clone 3
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
            if not devices: 
                print(f"{R}❌ Aucun appareil détecté.{RESET}")
                return False
            self.device_id = devices[0]
            self.adb_prefix = f"adb -s {self.device_id} shell"
            print(f"{G}✅ Appareil connecté : {C}{self.device_id}{RESET}")
            return True
        except: return False

    async def run_adb_interaction(self, account_idx, link, action):
        if not self.device_id and not self.detect_device(): return False

        # Vérification si on a les coordonnées pour ce compte
        picker_coord = APP_PICKER_SLOTS.get(account_idx)
        if not picker_coord:
            print(f"{R}❌ Erreur: Pas de coordonnées définies pour le compte {account_idx} (Max 3){RESET}")
            return False

        try:
            # 1. Nettoyage préalable
            os.system(f"{self.adb_prefix} am force-stop {TIKTOK_PACKAGE}")
            await asyncio.sleep(0.5)

            # 2. Lancer le lien directement (Intent)
            print(f"{Y}🚀 Lancement du lien via Android Intent...{RESET}")
            # Cette commande ouvre le lien et déclenche le menu "Choisir une app"
            cmd = f'{self.adb_prefix} am start -a android.intent.action.VIEW -d "{link}" > /dev/null 2>&1'
            os.system(cmd)

            # 3. Attente du menu "Ouvrir avec"
            print(f"{C}⏱️ Attente du menu de sélection (3s)...{RESET}")
            await asyncio.sleep(3)

            # 4. Sélection du Clone
            print(f"{B}point👉 Clic sur le Clone {account_idx} ({picker_coord}){RESET}")
            os.system(f"{self.adb_prefix} input tap {picker_coord}")

            # 5. Attente chargement APP (40 secondes demandées)
            print(f"{M}⏳ Chargement du TikTok (40s)...{RESET}")
            await asyncio.sleep(40)

            # 6. Exécution de l'action
            print(f"{G}⚡ Exécution de l'action...{RESET}")
            if "Like" in action:
                os.system(f"{self.adb_prefix} input tap {ACTIONS_COORDS['LIKE']}")
                print(f"{Y}❤️ Like envoyé à {ACTIONS_COORDS['LIKE']}{RESET}")
            else:
                # Follow ou autre
                os.system(f"{self.adb_prefix} input tap {ACTIONS_COORDS['FOLLOW']}")
                print(f"{Y}👤 Follow envoyé à {ACTIONS_COORDS['FOLLOW']}{RESET}")
            
            # Petit délai pour valider l'action
            await asyncio.sleep(3)

            # 7. Fermeture propre
            print(f"{R}🏁 Fermeture de l'application...{RESET}")
            os.system(f"{self.adb_prefix} am force-stop {TIKTOK_PACKAGE}")
            
            # Retour premier plan Termux (Optionnel, mais propre)
            os.system(f"{self.adb_prefix} am start -n {TERMUX_PACKAGE} > /dev/null 2>&1")
            
            return True

        except Exception as e:
            print(f"{R}❌ Erreur critique : {e}{RESET}")
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
        # Gestion des boutons si on clique manuellement
        buttons = event.message.buttons

        if "Link :" in text and "Action :" in text:
            link_match = re.search(r"Link\s*:\s*(https?://[^\s\n]+)", text)
            action_match = re.search(r"Action\s*:\s*([^\n]+)", text)
            reward_match = re.search(r"Reward\s*:\s*\n?(\d+\.?\d*)", text, re.IGNORECASE)

            if link_match and action_match:
                url = link_match.group(1)
                action = action_match.group(1)
                reward_val = float(reward_match.group(1)) if reward_match else 0.0
                
                # On détermine quel compte utiliser (1, 2 ou 3)
                acc_idx = (self.current_account_index % 3) + 1 
                acc_name = self.accounts[self.current_account_index] if self.accounts else f"Compte {acc_idx}"

                print(f"\n{B}💎 Tâche reçue pour {W}{acc_name}{B} (Slot {acc_idx}){RESET}")
                print(f"{C}🔗 {url}{RESET}")
                
                success = await self.run_adb_interaction(acc_idx, url, action)

                if success and buttons:
                    # Recherche du bouton "Completed"
                    for i, row in enumerate(buttons):
                        for j, btn in enumerate(row):
                            if any(x in btn.text for x in ["Completed", "✅"]):
                                await asyncio.sleep(2)
                                await event.message.click(i, j)
                                self.stats["total_earned"] += reward_val
                                self.save_stats_now()
                                print(f"{G}💰 Gain validé (+{reward_val}) ! Total: {self.stats['total_earned']:.2f}{RESET}")
                                return

        elif "Sorry" in text:
            print(f"{Y}💤 Pas de tâche. Changement de compte...{RESET}")
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
        print(f"║ {G}Solde : {W}{bot.stats['total_earned']:.4f} USD{M}             ║")
        print(f"║ {B}Comptes chargés : {W}{len(bot.accounts)}{M}                 ║")
        print(f"╠════════════════════════════════════════════╣")
        print(f"║ {Y}[1]{W} Lancer le Bot                         {M}║")
        print(f"║ {Y}[2]{W} Ajouter Compte (Nom)                  {M}║")
        print(f"║ {Y}[3]{W} Tester ADB                            {M}║")
        print(f"║ {R}[4]{W} Quitter                               {M}║")
        print(f"╚════════════════════════════════════════════╝{RESET}")
        
        choice = input(f"{C}➤ Choix : {RESET}")
        if choice == '1': 
            if not bot.accounts:
                print(f"{R}⚠️ Ajoute au moins un compte (Option 2){RESET}")
                await asyncio.sleep(2)
            else:
                await bot.start_telegram()
        elif choice == '2':
            name = input("Nom du compte : ")
            if name: 
                bot.accounts.append(name)
                with open('accounts.json', 'w') as f: json.dump(bot.accounts, f)
        elif choice == '3':
            bot.detect_device()
            await asyncio.sleep(3)
        elif choice == '4': break

if __name__ == '__main__':
    asyncio.run(main_menu())
