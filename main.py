import os
import json
import asyncio
import re
import subprocess
from dotenv import load_dotenv
from telethon import TelegramClient, events

# --- COULEURS ---
RED = "\033[91m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
RESET = "\033[0m"
BLUE = "\033[94m"

# --- CONFIGURATION ---
MULTI_APP_PACKAGE = "com.waxmoon.ma.gp/com.waxmoon.mobile.module.home.MainActivity"
TIKTOK_PACKAGE = "com.zhiliaoapp.musically"
TERMUX_PACKAGE = "com.termux/com.termux.app.TermuxActivity"

# ⚠️ NOUVELLES COORDONNÉES À VÉRIFIER ⚠️
COORDINATES = {
    "LIKE_BUTTON": "950 1100",
    "FOLLOW_BUTTON": "950 850",
    
    # Bouton Loupe/Recherche en haut à droite dans TikTok
    "SEARCH_ICON": "980 130", 
    
    # Premier résultat qui s'affiche après la recherche (cliquer au milieu de la première vidéo/profil)
    "FIRST_RESULT": "300 600",
    
    "APP_SLOTS": {
        1: "540 400",
        2: "540 700",
        3: "540 1000",
    }
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

    # --- DÉTECTION APPAREIL ---
    def detect_device(self):
        try:
            output = subprocess.check_output(["adb", "devices"]).decode("utf-8")
            lines = output.strip().split('\n')[1:]
            authorized_devices = []
            for line in lines:
                if "\tdevice" in line:
                    authorized_devices.append(line.split('\t')[0])
            
            if not authorized_devices:
                print(f"{RED}❌ Aucun appareil autorisé trouvé.{RESET}")
                return False
            
            self.device_id = authorized_devices[0]
            self.adb_prefix = f"adb -s {self.device_id} shell"
            print(f"{GREEN}✅ Appareil détecté : {self.device_id}{RESET}")
            return True
        except Exception as e:
            print(f"{RED}❌ Erreur détection ADB : {e}{RESET}")
            return False

    # --- FONCTION POUR TAPER LE LIEN PROPREMENT ---
    def adb_type_text(self, text):
        """Écrit du texte via ADB en gérant les caractères spéciaux"""
        # On remplace les caractères problématiques pour le shell Android
        # ADB input text n'aime pas trop les &, ?, =. 
        # Astuce : On échappe les caractères spéciaux
        escaped_text = text.replace("&", "\&").replace("?", "\?").replace("=", "\=")
        os.system(f"{self.adb_prefix} input text \"{escaped_text}\"")

    # --- SÉQUENCE D'AUTOMATISATION ---
    async def run_adb_interaction(self, account_idx, link, action):
        if not self.device_id:
            if not self.detect_device(): return False

        try:
            # 0. Nettoyage préalable
            os.system(f"{self.adb_prefix} am force-stop {TIKTOK_PACKAGE}")
            await asyncio.sleep(1)

            print(f"{YELLOW}⏳ Ouverture Multi-App...{RESET}")
            
            # 1. Ouvrir Multi App
            os.system(f"{self.adb_prefix} am start -n {MULTI_APP_PACKAGE} > /dev/null 2>&1")
            await asyncio.sleep(6) 

            # 2. Cliquer sur le profil (Slot correspondant)
            pos = COORDINATES["APP_SLOTS"].get(account_idx, "540 400")
            print(f"{BLUE}👉 Sélection du profil n°{account_idx}{RESET}")
            os.system(f"{self.adb_prefix} input tap {pos}")
            
            # Attente importante : le clone doit charger
            await asyncio.sleep(10) 

            # 3. NAVIGATION INTERNE (Remplacement de l'ouverture du lien externe)
            print(f"{YELLOW}🔍 Recherche du contenu dans le clone...{RESET}")
            
            # A. Clic sur la Loupe (Recherche)
            os.system(f"{self.adb_prefix} input tap {COORDINATES['SEARCH_ICON']}")
            await asyncio.sleep(2)

            # B. Écriture du lien (Tape le lien comme un clavier)
            print(f"{BLUE}⌨️ Écriture du lien...{RESET}")
            self.adb_type_text(link)
            await asyncio.sleep(2)

            # C. Appuyer sur ENTRÉE (Keycode 66)
            os.system(f"{self.adb_prefix} input keyevent 66")
            await asyncio.sleep(5) # Attente des résultats de recherche

            # D. Cliquer sur le premier résultat
            print(f"{BLUE}👆 Clic sur le résultat...{RESET}")
            os.system(f"{self.adb_prefix} input tap {COORDINATES['FIRST_RESULT']}")
            await asyncio.sleep(6) # Attente chargement vidéo

            print(f"{GREEN}✅ Vidéo/Profil ouvert !{RESET}")

            # 4. Action
            if "Like" in action:
                os.system(f"{self.adb_prefix} input tap {COORDINATES['LIKE_BUTTON']}")
                print(f"{GREEN}❤️ J'aime effectué{RESET}")
            elif "Follow" in action or "profile" in action:
                os.system(f"{self.adb_prefix} input tap {COORDINATES['FOLLOW_BUTTON']}")
                print(f"{GREEN}👤 Follow effectué{RESET}")
            
            await asyncio.sleep(3)

            # 5. Fermeture propre
            print(f"{BLUE}🔄 Retour Termux...{RESET}")
            os.system(f"{self.adb_prefix} am force-stop {TIKTOK_PACKAGE}")
            await asyncio.sleep(1)
            os.system(f"{self.adb_prefix} am start -n {TERMUX_PACKAGE} > /dev/null 2>&1")
            
            return True

        except Exception as e:
            print(f"{RED}❌ Erreur séquence : {e}{RESET}")
            return False

    async def start_telegram(self):
        if not self.detect_device(): return

        print(f"\n{BLUE}--- Connexion à Telegram ---{RESET}")
        try:
            await self.client.start()
            self.client.add_event_handler(self.message_handler, events.NewMessage(chats=TARGET_BOT))
            self.working = True
            await self.client.send_message(TARGET_BOT, 'TikTok')
            await self.client.run_until_disconnected()
        except Exception as e:
            print(f"{RED}❌ Erreur Telegram : {e}{RESET}")

    async def message_handler(self, event):
        if not self.working: return
        text = event.message.message or ""
        buttons = event.message.buttons

        if "Link :" in text and "Action :" in text:
            link_match = re.search(r"Link\s*:\s*(https?://[^\s\n]+)", text)
            action_match = re.search(r"Action\s*:\s*([^\n]+)", text)
            reward_match = re.search(r"Reward\s*:\s*\n?(\d+\.?\d*)", text, re.IGNORECASE)

            if link_match and action_match:
                url = link_match.group(1)
                action = action_match.group(1)
                reward_val = float(reward_match.group(1)) if reward_match else 0.0
                
                account_num = self.current_account_index + 1
                current_acc_name = self.accounts[self.current_account_index]

                print(f"\n{BLUE}⚡ Tâche détectée pour {current_acc_name} (Session {account_num}){RESET}")
                
                success = await self.run_adb_interaction(account_num, url, action)

                if success and buttons:
                    for i, row in enumerate(buttons):
                        for j, btn in enumerate(row):
                            if any(x in btn.text for x in ["Completed", "✅"]):
                                await asyncio.sleep(2)
                                await event.message.click(i, j)
                                self.stats["total_earned"] += reward_val
                                self.save_stats_now()
                                print(f"{GREEN}💰 Tâche validée ! Gain: +{reward_val}{RESET}")
                                print(f"{BLUE}---------------------------------------------------{RESET}")
                                return

        elif "Sorry" in text:
            print(f"{YELLOW}😴 Pas de tâche sur : {self.accounts[self.current_account_index]}{RESET}")
            self.current_account_index = (self.current_account_index + 1) % len(self.accounts)
            print(f"{BLUE}🔄 Recherche sur le compte suivant...{RESET}")
            await asyncio.sleep(5)
            await self.client.send_message(TARGET_BOT, 'TikTok')

        elif buttons:
            current_target = self.accounts[self.current_account_index]
            for i, row in enumerate(buttons):
                for j, btn in enumerate(row):
                    if btn.text == current_target:
                        await event.message.click(i, j)
                        return

async def main_menu():
    bot = TaskBot()
    while True:
        print(f"\n{BLUE}--- MENU BOT v3 (Solde: {bot.stats['total_earned']:.2f}) ---{RESET}")
        print("[1] Lancer le bot")
        print("[2] Ajouter un compte")
        print("[3] Redétecter ADB")
        print("[4] Quitter")
        
        choice = input(f"{YELLOW}Choix : {RESET}")
        if choice == '1':
            if not bot.accounts: print(f"{RED}❌ Liste vide !{RESET}"); continue
            await bot.start_telegram()
        elif choice == '2':
            name = input("Nom du compte : ")
            if name: 
                bot.accounts.append(name)
                with open('accounts.json', 'w') as f: json.dump(bot.accounts, f)
        elif choice == '3':
            bot.detect_device()
        elif choice == '4': break

if __name__ == '__main__':
    asyncio.run(main_menu())
