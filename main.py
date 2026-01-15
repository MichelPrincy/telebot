import os
import json
import asyncio
import re
import subprocess
import requests
from dotenv import load_dotenv
from telethon import TelegramClient, events
# Import pour les liens masqués
from telethon.tl.types import MessageEntityTextUrl

# ================== COULEURS ==================
RED = "\033[91m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
CYAN = "\033[96m"
MAGENTA = "\033[95m"
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

PAUSE_VIDEO = "530 1030" # Coordonnée pour mettre en pause
LIKE_BUTTON = "990 1200"
FOLLOW_BUTTON = "350 840"
SWIPE_REFRESH = "900 450 900 980 500"

# ================== TELEGRAM ==================
load_dotenv()
API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
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
        self.working = False

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

    # ---------- MISE À JOUR (FIXED) ----------
    def update_script(self):
        self.log("🌐 Téléchargement de la mise à jour...", CYAN)
        url = "https://raw.githubusercontent.com/MichelPrincy/telebot/main/main.py"
        try:
            response = requests.get(url)
            if response.status_code == 200:
                with open("main.py", "w") as f:
                    f.write(response.text)
                self.log("✅ Mise à jour réussie ! Relance le script.", GREEN)
                exit()
            else:
                self.log(f"❌ Erreur lors du téléchargement : {response.status_code}", RED)
        except Exception as e:
            self.log(f"❌ Erreur : {e}", RED)

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
        os.system(f"{self.adb} am force-stop {CLONE_CONTAINER_PACKAGE}")
        os.system(f"{self.adb} am kill-all")

    def focus_termux(self):
        os.system(f"{self.adb} am start --activity-brought-to-front {TERMUX_PACKAGE}")

    # ---------- ACTIONS TIKTOK ----------
    async def do_task(self, account_idx, link, action):
        try:
            self.cleanup_apps()
            coord_clone = APP_CHOOSER.get(account_idx, "150 1800")

            # --- PREMIÈRE TENTATIVE ---
            self.log(f"1ère tentative : Ouverture pour préparation...", CYAN)
            os.system(f'{self.adb} am start -a android.intent.action.VIEW -d "{link}"')
            await asyncio.sleep(4)
            os.system(f"{self.adb} input tap {coord_clone}")
            
            await asyncio.sleep(30)

            # --- DEUXIÈME TENTATIVE ---
            self.log(f"2ème tentative : Ouverture finale et action...", CYAN)
            os.system(f'{self.adb} am start -a android.intent.action.VIEW -d "{link}"')
            await asyncio.sleep(4)
            os.system(f"{self.adb} input tap {coord_clone}")
            
            await asyncio.sleep(20)

            if "Follow" in action or "profile" in action:
                self.log("🔄 Refresh profil et Follow...", BLUE)
                os.system(f"{self.adb} input swipe {SWIPE_REFRESH}")
                await asyncio.sleep(5)
                os.system(f"{self.adb} input tap {FOLLOW_BUTTON}")
            else:
                # ACTION LIKE AVEC PAUSE
                self.log("⏸️ Mise en pause de la vidéo...", YELLOW)
                os.system(f"{self.adb} input tap {PAUSE_VIDEO}")
                await asyncio.sleep(5) # Attendre que la pause soit effective
                
                self.log("❤️ Like en cours...", BLUE)
                os.system(f"{self.adb} input tap {LIKE_BUTTON}")

            await asyncio.sleep(5)
            os.system(f"{self.adb} am force-stop {CLONE_CONTAINER_PACKAGE}")
            self.focus_termux()
            return True

        except Exception as e:
            self.log(f"❌ Erreur Task : {e}", RED)
            os.system(f"{self.adb} am force-stop {CLONE_CONTAINER_PACKAGE}")
            return False

    # ---------- TELEGRAM ----------
    async def start_telegram(self):
        if not self.detect_device():
            self.log("❌ ADB non détecté", RED)
            return
        await self.client.start()
        self.client.add_event_handler(self.on_message, events.NewMessage(chats=TARGET_BOT))
        acc = self.accounts[self.index]
        self.log(f"\nrecherche de task sur le compte: {acc}...", MAGENTA)
        await self.client.send_message(TARGET_BOT, "TikTok")
        await self.client.run_until_disconnected()

    async def on_message(self, event):
        text = event.message.message or ""
        buttons = event.message.buttons

        if "Link :" in text and "Action :" in text:
            full_link = None
            if event.message.entities:
                for entity in event.message.entities:
                    if isinstance(entity, MessageEntityTextUrl):
                        full_link = entity.url
                        break
            
            if not full_link:
                match = re.search(r"Link\s*:\s*(https?://\S+)", text)
                if match:
                    full_link = match.group(1)

            if full_link:
                action = re.search(r"Action\s*:\s*(.+)", text).group(1)
                self.log(f"✅ Task trouvée, lien complet: {full_link}", GREEN)
                
                if await self.do_task(self.index + 1, full_link, action):
                    if buttons:
                        for i, row in enumerate(buttons):
                            for j, btn in enumerate(row):
                                if "Completed" in btn.text or "✅" in btn.text:
                                    await event.message.click(i, j)
                                    return

        elif "added" in text.lower() or "+" in text:
            gain = re.search(r"(\+?\d+(\.\d+)?)", text).group(1) if "+" in text else "1.1"
            self.log(f"like valide\n12 + {gain} cashcoins", YELLOW)
            await asyncio.sleep(2)
            await self.client.send_message(TARGET_BOT, "TikTok")

        elif "Sorry" in text or "No more" in text:
            self.log("pas de task sur ce compte", RED)
            self.index = (self.index + 1) % len(self.accounts)
            await asyncio.sleep(3)
            await self.client.send_message(TARGET_BOT, "TikTok")

        elif buttons:
            target = self.accounts[self.index]
            for i, row in enumerate(buttons):
                for j, btn in enumerate(row):
                    if btn.text == target:
                        await event.message.click(i, j)
                        return

    # ---------- MENU ----------
    async def menu(self):
        while True:
            clear_screen()
            print(f"""
{BLUE}╔════════════════════════════════════╗
║ 🤖 TIKTOK BOT PRO – CLONE WAXMOON  ║
╠════════════════════════════════════╣
║ 1️⃣  Lancer le bot                  ║
║ 2️⃣  Ajouter un compte               ║
║ 3️⃣  Voir / Supprimer comptes        ║
║ 4️⃣  Redétecter ADB                  ║
║ 5️⃣  MIS À JOUR (GITHUB)             ║
║ 6️⃣  Quitter                         ║
╚════════════════════════════════════╝
""")
            choice = input("Choix ➜ ")
            if choice == "1":
                if self.accounts: await self.start_telegram()
            elif choice == "2":
                name = input("Nom du compte TikTok : ")
                if name:
                    self.accounts.append(name)
                    self.save_json("accounts.json", self.accounts)
            elif choice == "3":
                clear_screen()
                print("📂 LISTE DES COMPTES :")
                for i, acc in enumerate(self.accounts, 1):
                    print(f"{i}. {acc}")
                input("\n[Any] Retour")
            elif choice == "4":
                self.detect_device()
            elif choice == "5":
                self.update_script()
            elif choice == "6":
                break

if __name__ == "__main__":
    bot = TikTokTaskBot()
    asyncio.run(bot.menu())
