import os
import json
import asyncio
import re
import subprocess
import requests
from dotenv import load_dotenv
from telethon import TelegramClient, events

# ================== COULEURS ==================
RED, GREEN, YELLOW, BLUE, CYAN, WHITE, RESET = "\033[91m", "\033[92m", "\033[93m", "\033[94m", "\033[96m", "\033[97m", "\033[0m"

# ================== PACKAGES ==================
CLONE_CONTAINER_PACKAGE = "com.waxmoon.ma.gp"
TERMUX_PACKAGE = "com.termux/com.termux.app.TermuxActivity"
TIKTOK_MAIN_PACKAGE = "com.zhiliaoapp.musically"

# ================== COORDONNÉES ==================
APP_CHOOSER = {1: "145 2015", 2: "340 2015", 3: "535 2015"}
LIKE_BUTTON = "990 1200"
FOLLOW_BUTTON = "350 840"
SWIPE_REFRESH = "500 800 500 400 500" # Swipe vers le bas pour refresh

# ================== CONFIG ==================
load_dotenv()
API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
TARGET_BOT = "@SmmKingdomTasksBot"

class TikTokTaskBot:
    def __init__(self):
        self.accounts = self.load_json("accounts.json", [])
        self.stats = self.load_json("stats.json", {"earned": 0.0, "tasks": 0})
        self.index = 0
        self.device_id = None
        self.adb = "adb shell"
        self.client = TelegramClient("session_bot", API_ID, API_HASH)
        self.working = False

    def load_json(self, file, default):
        if os.path.exists(file):
            with open(file, "r") as f: return json.load(f)
        return default

    def save_json(self, file, data):
        with open(file, "w") as f: json.dump(data, f, indent=4)

    def detect_device(self):
        try:
            out = subprocess.check_output(["adb", "devices"]).decode()
            lines = [line for line in out.splitlines() if "\tdevice" in line]
            if lines:
                self.device_id = lines[0].split("\t")[0]
                self.adb = f"adb -s {self.device_id} shell"
                return True
            return False
        except: return False

    def clean_apps(self):
        """ Ferme TikTok original et s'assure que WaxMoon est prêt """
        os.system(f"{self.adb} am force-stop {TIKTOK_MAIN_PACKAGE}")
        # On ne ferme pas WaxMoon ici car il contient les clones, 
        # mais on ferme les processus de clones potentiellement bloqués
        os.system(f"{self.adb} am kill-all") 

    def focus_termux(self):
        """ Remet Termux au premier plan """
        os.system(f"{self.adb} am start -n {TERMUX_PACKAGE} > /dev/null 2>&1")

    async def execute_sub_task(self, account_idx, link, action, step):
        """ Une phase d'ouverture et d'action """
        print(f"   {CYAN}➜ Phase {step}/2 : Ouverture lien...{RESET}")
        os.system(f'{self.adb} am start -a android.intent.action.VIEW -d "{link}"')
        await asyncio.sleep(4)

        # Sélection du clone
        os.system(f"{self.adb} input tap {APP_CHOOSER.get(account_idx, '145 2015')}")
        
        print(f"   {YELLOW}⏳ Attente chargement clone (40s)...{RESET}")
        await asyncio.sleep(40)

        if "Follow" in action or "profile" in action:
            os.system(f"{self.adb} input tap {FOLLOW_BUTTON}")
        else:
            os.system(f"{self.adb} input tap {LIKE_BUTTON}")
        
        await asyncio.sleep(3)
        # Fermeture du clone (via force-stop du container pour être sûr)
        os.system(f"{self.adb} am force-stop {CLONE_CONTAINER_PACKAGE}")
        await asyncio.sleep(1)

    async def do_task(self, account_idx, link, action):
        try:
            # 1. Nettoyage avant de commencer
            self.clean_apps()

            # 2. Répéter l'action 2 fois
            for i in range(1, 3):
                await self.execute_sub_task(account_idx, link, action, i)

            # 3. Retour Termux avant validation
            self.focus_termux()
            return True
        except Exception as e:
            print(f"{RED}❌ Erreur : {e}{RESET}")
            return False

    async def on_message(self, event):
        text = event.message.message or ""
        buttons = event.message.buttons

        # LOGIQUE DE RECHERCHE / DETECTION DE TASK
        if "Link :" in text and "Action :" in text:
            link_match = re.search(r"Link\s*:\s*(https?://\S+)", text)
            action_match = re.search(r"Action\s*:\s*(.+)", text)
            
            if link_match and action_match:
                url = link_match.group(1)
                act_type = "like" if "Like" in action_match.group(1) else "follow"
                
                print(f"{GREEN}task trouver, lien:{CYAN}{url[:30]}...{GREEN} type: {YELLOW}{act_type}{RESET}")
                
                success = await self.do_task(self.index + 1, url, action_match.group(1))

                if success and buttons:
                    for i, row in enumerate(buttons):
                        for j, btn in enumerate(row):
                            if "Completed" in btn.text or "✅" in btn.text:
                                await asyncio.sleep(1)
                                await event.message.click(i, j)
                                return

        # LOGIQUE DE VALIDATION ET GAINS
        elif "added" in text.lower() or "reward" in text.lower() or "success" in text.lower():
            # Extraction du gain (ex: 12 + 1.1) via regex
            reward = re.findall(r"(\d+\.?\d*)", text)
            if len(reward) >= 2:
                print(f"{GREEN}✅ {act_type if 'act_type' in locals() else 'task'} valide{RESET}")
                print(f"{WHITE}{reward[0]} + {reward[1]} cashcoins{RESET}\n")
            
            self.stats["tasks"] += 1
            self.save_json("stats.json", self.stats)
            
            # Relancer sur le même compte ou suivant ? Ici on redemande une task
            await asyncio.sleep(2)
            acc = self.accounts[self.index]
            print(f"{BLUE}recherche de task sur le compte: {WHITE}{acc}...{RESET}")
            await self.client.send_message(TARGET_BOT, "TikTok")

        elif "Sorry" in text:
            print(f"{YELLOW}pas de task sur ce compte.{RESET}")
            self.index = (self.index + 1) % len(self.accounts)
            await asyncio.sleep(3)
            acc = self.accounts[self.index]
            print(f"{BLUE}recherche de task sur le compte: {WHITE}{acc}...{RESET}")
            await self.client.send_message(TARGET_BOT, "TikTok")

        # Sélection du compte au début
        elif buttons:
            target = self.accounts[self.index]
            for i, row in enumerate(buttons):
                for j, btn in enumerate(row):
                    if btn.text == target:
                        print(f"{BLUE}recherche de task sur le compte: {WHITE}{target}...{RESET}")
                        await event.message.click(i, j)
                        return

    async def start_bot(self):
        if not self.detect_device():
            print(f"{RED}❌ Connectez un téléphone en ADB d'abord !{RESET}")
            return
        
        await self.client.start()
        self.client.add_event_handler(self.on_message, events.NewMessage(chats=TARGET_BOT))
        print(f"{GREEN}🚀 Bot démarré !{RESET}")
        await self.client.send_message(TARGET_BOT, "TikTok")
        await self.client.run_until_disconnected()

    async def menu(self):
        while True:
            os.system("clear")
            print(f"{BLUE}╔════════════════════════════════════╗")
            print(f"║   TIKTOK MULTI-CLONE AUTO V2       ║")
            print(f"╚════════════════════════════════════╝{RESET}")
            print(f"1. Lancer l'automatisation")
            print(f"2. Ajouter un compte")
            print(f"3. Quitter")
            
            choice = input("\nChoix ➜ ")
            if choice == "1":
                if self.accounts: await self.start_bot()
                else: print(f"{RED}Ajoutez des comptes session d'abord !{RESET}"); await asyncio.sleep(2)
            elif choice == "2":
                name = input("Nom du compte session : ")
                if name: self.accounts.append(name); self.save_json("accounts.json", self.accounts)
            elif choice == "3": break

if __name__ == "__main__":
    bot = TikTokTaskBot()
    asyncio.run(bot.menu())
