import os
import json
import asyncio
import re
import subprocess
import numpy as np
from PIL import Image
from dotenv import load_dotenv
from telethon import TelegramClient, events

# --- CONFIGURATION COULEURS ---
R, G, Y, B, M, C, W = "\033[1;91m", "\033[1;92m", "\033[1;93m", "\033[1;94m", "\033[1;95m", "\033[1;96m", "\033[1;97m"
RESET = "\033[0m"

# --- CONFIGURATION ---
MULTI_APP_PACKAGE = "com.waxmoon.ma.gp/com.waxmoon.mobile.module.home.MainActivity"
TIKTOK_PACKAGE = "com.zhiliaoapp.musically"
TERMUX_PACKAGE = "com.termux/com.termux.app.TermuxActivity"

# Ajuste ces coordonnées selon ton écran (Testés pour écran 1080p type standard)
COORDINATES = {
    "SEARCH_ICON": "980 130",      # Loupe en haut à droite
    "SEARCH_BAR_INPUT": "500 130", # Là où on tape le texte après avoir cliqué sur la loupe
    "FIRST_RESULT_USER": "450 350",# Premier utilisateur dans la liste
    "FIRST_RESULT_VIDEO": "300 600",# Première vidéo dans les résultats
    "LIKE_BUTTON": "950 1100",     # Cœur à droite
    "FOLLOW_BUTTON": "950 850",    # Bouton + ou Suivre
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

    def adb_type_text(self, text):
        # On utilise une méthode plus propre pour le texte spécial (URLs)
        text = text.replace(" ", "%s")
        os.system(f"{self.adb_prefix} input text {text}")

    def find_image_and_click(self, target_image_path):
        """Vision via Pillow pour trouver le clone de l'app"""
        try:
            os.system(f"adb -s {self.device_id} shell screencap -p /sdcard/screen.png")
            os.system(f"adb -s {self.device_id} pull /sdcard/screen.png screen.png > /dev/null 2>&1")
            img_screen = Image.open('screen.png').convert('L')
            img_target = Image.open(target_image_path).convert('L')
            s_arr, t_arr = np.array(img_screen), np.array(img_target)
            sw, sh = s_arr.shape[::-1]
            tw, th = t_arr.shape[::-1]
            
            best_val, best_loc = -1, (0,0)
            for y in range(0, sh - th, 15):
                for x in range(0, sw - tw, 15):
                    region = s_arr[y:y+th, x:x+tw]
                    diff = np.mean(np.abs(region - t_arr))
                    if best_val == -1 or diff < best_val:
                        best_val, best_loc = diff, (x, y)
            
            if best_val < 35:
                os.system(f"{self.adb_prefix} input tap {best_loc[0]+50} {best_loc[1]+50}")
                return True
            return False
        except: return False

    async def run_adb_interaction(self, account_idx, link, action):
        if not self.device_id and not self.detect_device(): return False

        try:
            # 1. Reset Apps
            print(f"{Y}🧹 Nettoyage des apps...{RESET}")
            os.system(f"{self.adb_prefix} am force-stop {TIKTOK_PACKAGE}")
            await asyncio.sleep(1)

            # 2. Ouvrir Multi-App
            print(f"{Y}🚀 Ouverture Multi-App...{RESET}")
            os.system(f"{self.adb_prefix} am start -n {MULTI_APP_PACKAGE}")
            await asyncio.sleep(6)

            # 3. Trouver et ouvrir le clone (via image ou position)
            target_image = f"{account_idx}.png"
            if os.path.exists(target_image):
                if not self.find_image_and_click(target_image):
                    os.system(f"{self.adb_prefix} input tap 540 400")
            else:
                os.system(f"{self.adb_prefix} input tap 540 400")

            # 4. ATTENTE DE CHARGEMENT (Crucial)
            print(f"{C}⏳ Attente chargement TikTok Clone (20s)...{RESET}")
            await asyncio.sleep(20)

            # 5. DÉFIS : AFFICHER LA VIDÉO / LE PROFIL
            print(f"{B}🔍 Recherche du lien : {W}{link}{RESET}")
            
            # Clic sur l'icône recherche (loupe)
            os.system(f"{self.adb_prefix} input tap {COORDINATES['SEARCH_ICON']}")
            await asyncio.sleep(3)
            
            # Clic sur la barre de saisie pour activer le clavier
            os.system(f"{self.adb_prefix} input tap {COORDINATES['SEARCH_BAR_INPUT']}")
            await asyncio.sleep(2)

            # Écrire le lien
            self.adb_type_text(link)
            await asyncio.sleep(2)
            
            # Presser "Entrée" du clavier pour lancer la recherche
            os.system(f"{self.adb_prefix} input keyevent 66")
            print(f"{Y}⏳ Recherche en cours...{RESET}")
            await asyncio.sleep(7) # Temps que TikTok cherche le lien

            # Clic sur le résultat
            # Si le lien contient 'video', on clique sur la zone vidéo, sinon zone utilisateur
            if "video" in link or "/v/" in link:
                print(f"{C}👆 Sélection de la vidéo...{RESET}")
                os.system(f"{self.adb_prefix} input tap {COORDINATES['FIRST_RESULT_VIDEO']}")
            else:
                print(f"{C}👆 Sélection du profil...{RESET}")
                os.system(f"{self.adb_prefix} input tap {COORDINATES['FIRST_RESULT_USER']}")
            
            await asyncio.sleep(6) # Attente ouverture finale

            # 6. ACTION FINALE
            if "Like" in action:
                os.system(f"{self.adb_prefix} input tap {COORDINATES['LIKE_BUTTON']}")
                print(f"{G}❤️ J'aime envoyé !{RESET}")
            else:
                os.system(f"{self.adb_prefix} input tap {COORDINATES['FOLLOW_BUTTON']}")
                print(f"{G}👤 Follow envoyé !{RESET}")
            
            await asyncio.sleep(4)
            
            # Retour à Termux
            os.system(f"{self.adb_prefix} am force-stop {TIKTOK_PACKAGE}")
            os.system(f"{self.adb_prefix} am start -n {TERMUX_PACKAGE}")
            return True

        except Exception as e:
            print(f"{R}❌ Erreur : {e}{RESET}")
            return False

    # ... (Le reste du code start_telegram et message_handler reste identique)
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
        except Exception as e: print(f"{R}❌ Erreur : {e}{RESET}")

    async def message_handler(self, event):
        if not self.working: return
        text = event.message.message or ""
        if "Link :" in text and "Action :" in text:
            link_match = re.search(r"Link\s*:\s*(https?://[^\s\n]+)", text)
            action_match = re.search(r"Action\s*:\s*([^\n]+)", text)
            if link_match and action_match:
                url, action = link_match.group(1), action_match.group(1)
                acc_idx = self.current_account_index + 1
                success = await self.run_adb_interaction(acc_idx, url, action)
                if success:
                    await asyncio.sleep(2)
                    await event.message.click(text="Completed") # Ou l'index du bouton
                    print(f"{G}💰 Tâche validée !{RESET}")

async def main_menu():
    bot = TaskBot()
    while True:
        os.system('clear')
        print(f"{M}╔════════════════════════════════════════════╗")
        print(f"║{W}   SMM KINGDOM BOT v6 - SMART DISPLAY      {M}║")
        print(f"╠════════════════════════════════════════════╣")
        print(f"║ {G}Solde : {W}{bot.stats['total_earned']:.2f} USD{M}              ║")
        print(f"║ {Y}[1]{W} Lancer le Bot                         {M}║")
        print(f"║ {Y}[2]{W} Ajouter Compte                        {M}║")
        print(f"║ {R}[4]{W} Quitter                               {M}║")
        print(f"╚════════════════════════════════════════════╝{RESET}")
        choice = input(f"{C}➤ Choix : {RESET}")
        if choice == '1': await bot.start_telegram()
        elif choice == '2':
            name = input("Nom : ")
            if name: 
                bot.accounts.append(name)
                with open('accounts.json', 'w') as f: json.dump(bot.accounts, f)
        elif choice == '4': break

if __name__ == '__main__':
    asyncio.run(main_menu())
