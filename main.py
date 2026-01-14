import os
import json
import asyncio
import re
import subprocess
from dotenv import load_dotenv
from telethon import TelegramClient, events

# --- SYSTÈME DE COULEURS ---
R, G, Y, B, M, C, W = "\033[1;91m", "\033[1;92m", "\033[1;93m", "\033[1;94m", "\033[1;95m", "\033[1;96m", "\033[1;97m"
RESET = "\033[0m"
BOLD = "\033[1m"

# --- CONFIGURATION ---
TIKTOK_PACKAGE = "com.zhiliaoapp.musically"
TERMUX_PACKAGE = "com.termux/com.termux.app.TermuxActivity"

# 📍 TES NOUVELLES COORDONNÉES
# On définit les positions des clones dans le menu "Ouvrir avec"
CLONE_PICKER = {
    1: "145 2015",
    2: "340 2015",
    3: "535 2015"
}

# Coordonnées des actions à l'intérieur de TikTok
COORDINATES = {
    "LIKE_BUTTON": "990 1200",
    "FOLLOW_BUTTON": "350 840",
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
            if os.path.exists('accounts.json'):
                with open('accounts.json', 'r') as f: return json.load(f)
            return []
        except: return []

    def load_stats(self):
        try:
            if os.path.exists('stats.json'):
                with open('stats.json', 'r') as f: return json.load(f)
            return {"total_earned": 0.0, "tasks_completed": 0}
        except: return {"total_earned": 0.0, "tasks_completed": 0}

    def save_stats_now(self):
        with open('stats.json', 'w') as f:
            json.dump(self.stats, f, indent=4)

    def detect_device(self):
        try:
            output = subprocess.check_output(["adb", "devices"]).decode("utf-8")
            lines = output.strip().split('\n')[1:]
            authorized_devices = [line.split('\t')[0] for line in lines if "\tdevice" in line]
            
            if not authorized_devices:
                print(f"{R}❌ Aucun appareil ADB trouvé.{RESET}")
                return False
            
            self.device_id = authorized_devices[0]
            self.adb_prefix = f"adb -s {self.device_id} shell"
            print(f"{G}✅ Appareil détecté : {C}{self.device_id}{RESET}")
            return True
        except Exception as e:
            print(f"{R}❌ Erreur ADB : {e}{RESET}")
            return False

    async def run_adb_interaction(self, account_idx, link, action):
        if not self.device_id and not self.detect_device(): return False

        # Déterminer quel clone utiliser (Rotation entre 1, 2 et 3)
        slot = ((account_idx - 1) % 3) + 1
        picker_pos = CLONE_PICKER[slot]

        try:
            # 1. Fermer TikTok avant de commencer
            os.system(f"{self.adb_prefix} am force-stop {TIKTOK_PACKAGE}")
            await asyncio.sleep(1)

            # 2. Ouvrir le lien via Intent (Déclenche le menu "Choose an app")
            print(f"{Y}🚀 Envoi du lien vers le sélecteur...{RESET}")
            os.system(f'{self.adb_prefix} am start -a android.intent.action.VIEW -d "{link}"')
            
            # 3. Attendre l'apparition du menu et cliquer sur le bon clone
            await asyncio.sleep(4) 
            print(f"{C}👆 Sélection du TikTok Clone {slot} ({picker_pos})...{RESET}")
            os.system(f"{self.adb_prefix} input tap {picker_pos}")

            # 4. Attente de chargement (40 secondes comme demandé)
            print(f"{B}⏳ Chargement du clone (40s)...{RESET}")
            await asyncio.sleep(40)

            # 5. Effectuer l'action
            if "Like" in action:
                print(f"{M}❤️ Like en cours...{RESET}")
                os.system(f"{self.adb_prefix} input tap {COORDINATES['LIKE_BUTTON']}")
            else:
                print(f"{M}👤 Follow en cours...{RESET}")
                os.system(f"{self.adb_prefix} input tap {COORDINATES['FOLLOW_BUTTON']}")
            
            await asyncio.sleep(5)

            # 6. Fermeture et retour
            print(f"{Y}🧹 Fermeture et retour à Termux...{RESET}")
            os.system(f"{self.adb_prefix} am force-stop {TIKTOK_PACKAGE}")
            os.system(f"{self.adb_prefix} am start -n {TERMUX_PACKAGE} > /dev/null 2>&1")
            
            return True

        except Exception as e:
            print(f"{R}❌ Erreur interaction : {e}{RESET}")
            return False

    async def start_telegram(self):
        if not self.detect_device(): return
        print(f"\n{M}┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓")
        print(f"┃      {W}BOT ACTIF : MODE SELECTEUR      {M}┃")
        print(f"┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛{RESET}")
        try:
            await self.client.start()
            self.client.add_event_handler(self.message_handler, events.NewMessage(chats=TARGET_BOT))
            self.working = True
            await self.client.send_message(TARGET_BOT, 'TikTok')
            await self.client.run_until_disconnected()
        except Exception as e:
            print(f"{R}❌ Erreur Telegram : {e}{RESET}")

    async def message_handler(self, event):
        if not self.working: return
        text = event.message.message or ""
        buttons = event.message.buttons

        if "Link :" in text and "Action :" in text:
            link_match = re.search(r"Link\s*:\s*(https?://[^\s\n]+)", text)
            action_match = re.search(r"Action\s*:\s*([^\n]+)", text)
            reward_match = re.search(r"Reward\s*:\s*\n?(\d+\.?\d*)", text, re.IGNORECASE)

            if link_match and action_match:
                url, action = link_match.group(1), action_match.group(1)
                reward_val = float(reward_match.group(1)) if reward_match else 0.0
                
                account_num = self.current_account_index + 1
                current_acc_name = self.accounts[self.current_account_index]

                print(f"\n{B}⚡ Tâche : {W}{action} {B}| Compte : {C}{current_acc_name}{RESET}")
                success = await self.run_adb_interaction(account_num, url, action)

                if success and buttons:
                    for i, row in enumerate(buttons):
                        for j, btn in enumerate(row):
                            if any(x in btn.text for x in ["Completed", "✅"]):
                                await asyncio.sleep(2)
                                await event.message.click(i, j)
                                self.stats["total_earned"] += reward_val
                                self.save_stats_now()
                                print(f"{G}💰 Gain: +{reward_val} | Total: {self.stats['total_earned']:.2f}{RESET}")
                                return

        elif "Sorry" in text:
            print(f"{Y}😴 Pas de tâche sur {self.accounts[self.current_account_index]}. Switch...{RESET}")
            self.current_account_index = (self.current_account_index + 1) % len(self.accounts)
            await asyncio.sleep(5)
            await self.client.send_message(TARGET_BOT, 'TikTok')

async def main_menu():
    bot = TaskBot()
    while True:
        os.system('clear')
        print(f"{M}╔════════════════════════════════════════════╗{RESET}")
        print(f"{M}║{W} {BOLD}     SMM KINGDOM BOT v6 - SELECTOR        {RESET}{M} ║{RESET}")
        print(f"{M}╠════════════════════════════════════════════╣{RESET}")
        print(f"{M}║{RESET}  {G}💰 SOLDE : {W}{bot.stats['total_earned']:.2f} USD{RESET}             {M}║{RESET}")
        print(f"{M}║{RESET}  {B}👤 COMPTES : {W}{len(bot.accounts)}{RESET}                       {M}║{RESET}")
        print(f"{M}╠════════════════════════════════════════════╣{RESET}")
        print(f"{M}║{RESET}  {Y}[1]{RESET} Lancer le Bot                         {M}║{RESET}")
        print(f"{M}║{RESET}  {Y}[2]{RESET} Ajouter un compte                     {M}║{RESET}")
        print(f"{M}║{RESET}  {R}[4]{RESET} Quitter                               {M}║{RESET}")
        print(f"{M}╚════════════════════════════════════════════╝{RESET}")
        
        choice = input(f"\n{C}➤ Choix : {RESET}")
        if choice == '1':
            if not bot.accounts: print(f"{R}❌ Ajoutez un compte !{RESET}"); await asyncio.sleep(2); continue
            await bot.start_telegram()
        elif choice == '2':
            name = input(f"{W}Nom : {RESET}")
            if name: 
                bot.accounts.append(name)
                with open('accounts.json', 'w') as f: json.dump(bot.accounts, f)
        elif choice == '4': break

if __name__ == '__main__':
    asyncio.run(main_menu())
