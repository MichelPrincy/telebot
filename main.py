import os
import json
import asyncio
import re
import subprocess
import numpy as np
from PIL import Image
from dotenv import load_dotenv
from telethon import TelegramClient, events

# --- SYSTÈME DE COULEURS ÉTENDU ---
R = "\033[1;91m"  # Rouge vif
G = "\033[1;92m"  # Vert vif
Y = "\033[1;93m"  # Jaune vif
B = "\033[1;94m"  # Bleu vif
M = "\033[1;95m"  # Magenta
C = "\033[1;96m"  # Cyan
W = "\033[1;97m"  # Blanc
RESET = "\033[0m"
BOLD = "\033[1m"
UNDERLINE = "\033[4m"

# --- CONFIGURATION ---
MULTI_APP_PACKAGE = "com.waxmoon.ma.gp/com.waxmoon.mobile.module.home.MainActivity"
TIKTOK_PACKAGE = "com.zhiliaoapp.musically"
TERMUX_PACKAGE = "com.termux/com.termux.app.TermuxActivity"

# OFFSET DU CLIC (4cm bas / 5cm droite environ)
OFFSET_X = 250  
OFFSET_Y = 200  

COORDINATES = {
    "LIKE_BUTTON": "950 1100",
    "FOLLOW_BUTTON": "950 850",
    "SEARCH_ICON": "980 130", 
    "FIRST_RESULT": "300 600",
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
            authorized_devices = []
            for line in lines:
                if "\tdevice" in line:
                    authorized_devices.append(line.split('\t')[0])
            
            if not authorized_devices:
                print(f"{R}❌ Aucun appareil autorisé trouvé.{RESET}")
                return False
            
            self.device_id = authorized_devices[0]
            self.adb_prefix = f"adb -s {self.device_id} shell"
            print(f"{G}✅ Appareil détecté : {C}{self.device_id}{RESET}")
            return True
        except Exception as e:
            print(f"{R}❌ Erreur détection ADB : {e}{RESET}")
            return False

    def adb_type_text(self, text):
        escaped_text = text.replace("&", "\&").replace("?", "\?").replace("=", "\=")
        os.system(f"{self.adb_prefix} input text \"{escaped_text}\"")

    # --- REMPLACEMENT DE CV2 PAR PILLOW + NUMPY ---
    def find_image_and_click(self, target_image_path):
        """Recherche visuelle utilisant Pillow et Numpy (Template Matching manuel)"""
        try:
            print(f"{Y}📸 Recherche visuelle : {C}{target_image_path}...{RESET}")
            
            # Capture d'écran
            os.system(f"adb -s {self.device_id} shell screencap -p /sdcard/screen.png")
            os.system(f"adb -s {self.device_id} pull /sdcard/screen.png screen.png > /dev/null 2>&1")
            
            if not os.path.exists('screen.png') or not os.path.exists(target_image_path):
                return False

            # Ouvrir avec Pillow et convertir en niveaux de gris (L) pour la vitesse
            img_screen = Image.open('screen.png').convert('L')
            img_target = Image.open(target_image_path).convert('L')

            # Conversion en tableaux Numpy
            screen_arr = np.array(img_screen)
            target_arr = np.array(img_target)

            sw, sh = screen_arr.shape[::-1] # Largeur, Hauteur écran
            tw, th = target_arr.shape[::-1] # Largeur, Hauteur cible

            # On utilise une méthode de corrélation simple par Numpy
            # Note : Sur Termux, c'est moins rapide que CV2 mais ça fonctionne sans lib complexe
            # Pour gagner du temps, on peut sous-échantillonner si nécessaire
            
            # Recherche de la zone la plus proche (simplifiée)
            # On cherche le pixel le plus haut/gauche pour démarrer
            best_val = -1
            best_loc = (0, 0)

            # Optimisation : On ne scanne qu'une partie de l'écran ou on utilise un pas de 2
            for y in range(0, sh - th, 10): # Pas de 10 pour la rapidité sur Termux
                for x in range(0, sw - tw, 10):
                    region = screen_arr[y:y+th, x:x+tw]
                    # Mesure de similitude (inverse de la différence absolue moyenne)
                    diff = np.mean(np.abs(region - target_arr))
                    if best_val == -1 or diff < best_val:
                        best_val = diff
                        best_loc = (x, y)

            # Si la différence moyenne est faible (seuil arbitraire, à ajuster)
            if best_val < 30: 
                found_x, found_y = best_loc
                click_x = found_x + OFFSET_X
                click_y = found_y + OFFSET_Y
                
                print(f"{G}👁️ Trouvé (diff:{best_val:.2f}) -> {C}{click_x} {click_y}{RESET}")
                os.system(f"{self.adb_prefix} input tap {click_x} {click_y}")
                return True
            else:
                print(f"{R}❌ Image non détectée (Seuil trop haut : {best_val:.2f}){RESET}")
                return False

        except Exception as e:
            print(f"{R}❌ Erreur Vision : {e}{RESET}")
            return False

    async def run_adb_interaction(self, account_idx, link, action):
        if not self.device_id:
            if not self.detect_device(): return False

        try:
            os.system(f"{self.adb_prefix} am force-stop {TIKTOK_PACKAGE}")
            await asyncio.sleep(1)

            print(f"{Y}⏳ Ouverture Multi-App...{RESET}")
            os.system(f"{self.adb_prefix} am start -n {MULTI_APP_PACKAGE} > /dev/null 2>&1")
            await asyncio.sleep(8) 

            target_image = f"{account_idx}.png"
            if os.path.exists(target_image):
                found = self.find_image_and_click(target_image)
                if not found:
                    # Fallback
                    os.system(f"{self.adb_prefix} input tap 540 400")
            else:
                os.system(f"{self.adb_prefix} input tap 540 400")
            
            await asyncio.sleep(10)

            # --- RECHERCHE ET ACTION ---
            print(f"{C}🔍 Recherche du contenu...{RESET}")
            os.system(f"{self.adb_prefix} input tap {COORDINATES['SEARCH_ICON']}")
            await asyncio.sleep(2)
            self.adb_type_text(link)
            await asyncio.sleep(2)
            os.system(f"{self.adb_prefix} input keyevent 66") 
            await asyncio.sleep(5)
            os.system(f"{self.adb_prefix} input tap {COORDINATES['FIRST_RESULT']}")
            await asyncio.sleep(6)

            if "Like" in action:
                os.system(f"{self.adb_prefix} input tap {COORDINATES['LIKE_BUTTON']}")
                print(f"{M}❤️ J'aime effectué{RESET}")
            elif "Follow" in action or "profile" in action:
                os.system(f"{self.adb_prefix} input tap {COORDINATES['FOLLOW_BUTTON']}")
                print(f"{M}👤 Follow effectué{RESET}")
            
            await asyncio.sleep(3)
            os.system(f"{self.adb_prefix} am force-stop {TIKTOK_PACKAGE}")
            os.system(f"{self.adb_prefix} am start -n {TERMUX_PACKAGE} > /dev/null 2>&1")
            return True

        except Exception as e:
            print(f"{R}❌ Erreur séquence : {e}{RESET}")
            return False

    async def start_telegram(self):
        if not self.detect_device(): return
        print(f"\n{M}┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓")
        print(f"┃      {W}CONNEXION TELEGRAM EN COURS{M}     ┃")
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
                url = link_match.group(1)
                action = action_match.group(1)
                reward_val = float(reward_match.group(1)) if reward_match else 0.0
                
                account_num = self.current_account_index + 1
                current_acc_name = self.accounts[self.current_account_index]

                print(f"\n{B}⚡ Tâche : {W}{action} {B}sur {C}{current_acc_name}{RESET}")
                success = await self.run_adb_interaction(account_num, url, action)

                if success and buttons:
                    for i, row in enumerate(buttons):
                        for j, btn in enumerate(row):
                            if any(x in btn.text for x in ["Completed", "✅"]):
                                await asyncio.sleep(2)
                                await event.message.click(i, j)
                                self.stats["total_earned"] += reward_val
                                self.save_stats_now()
                                print(f"{G}💰 +{reward_val} ajouté ! Total : {self.stats['total_earned']:.2f}{RESET}")
                                return

        elif "Sorry" in text:
            print(f"{Y}😴 Pas de tâche sur : {self.accounts[self.current_account_index]}{RESET}")
            self.current_account_index = (self.current_account_index + 1) % len(self.accounts)
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
        os.system('clear')
        print(f"{M}╔════════════════════════════════════════════╗{RESET}")
        print(f"{M}║{W} {BOLD}      SMM KINGDOM BOT v5 - VISION         {RESET}{M} ║{RESET}")
        print(f"{M}╠════════════════════════════════════════════╣{RESET}")
        print(f"{M}║{RESET}  {G}💰 SOLDE ACTUEL : {W}{bot.stats['total_earned']:.2f} USD{RESET}          {M}║{RESET}")
        print(f"{M}║{RESET}  {B}👤 COMPTES : {W}{len(bot.accounts)}{RESET}                      {M}║{RESET}")
        print(f"{M}╠════════════════════════════════════════════╣{RESET}")
        print(f"{M}║{RESET}  {Y}[1]{RESET} Lancer l'automatisation           {M}║{RESET}")
        print(f"{M}║{RESET}  {Y}[2]{RESET} Ajouter un compte (nom)           {M}║{RESET}")
        print(f"{M}║{RESET}  {Y}[3]{RESET} Redétecter l'appareil ADB         {M}║{RESET}")
        print(f"{M}║{RESET}  {R}[4]{RESET} Quitter                           {M}║{RESET}")
        print(f"{M}╚════════════════════════════════════════════╝{RESET}")
        
        choice = input(f"\n{C}➤ Faire un choix : {RESET}")
        if choice == '1':
            if not bot.accounts: 
                print(f"{R}❌ Ajoutez d'abord un compte !{RESET}")
                await asyncio.sleep(2)
                continue
            await bot.start_telegram()
        elif choice == '2':
            name = input(f"{W}Nom du compte (ex: Session1) : {RESET}")
            if name: 
                bot.accounts.append(name)
                with open('accounts.json', 'w') as f: json.dump(bot.accounts, f)
        elif choice == '3':
            bot.detect_device()
            await asyncio.sleep(2)
        elif choice == '4':
            print(f"{Y}Au revoir !{RESET}")
            break

if __name__ == '__main__':
    asyncio.run(main_menu())
