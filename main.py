import os
import json
import asyncio
import re
import subprocess
import requests
from dotenv import load_dotenv
from telethon import TelegramClient, events

# ================== COULEURS ==================
RED = "\033[91m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
CYAN = "\033[96m"
RESET = "\033[0m"

# ================== PACKAGES ==================
CLONE_CONTAINER_PACKAGE = "com.waxmoon.ma.gp"
TERMUX_PACKAGE = "com.termux/com.termux.app.TermuxActivity"

# ================== COORDONNÉES ==================
APP_CHOOSER = {
    1: "145 2015",
    2: "340 2015",
    3: "535 2015",
}

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
    os.system("cls" if os.name == "nt" else "clear")


class TikTokTaskBot:
    def __init__(self):
        self.accounts = self.load_json("accounts.json", [])
        self.stats = self.load_json("stats.json", {"earned": 0.0, "tasks": 0})
        self.index = 0
        self.device_id = None
        self.adb = "adb shell"
        self.client = TelegramClient("session_bot", API_ID, API_HASH)
        self.working = False

    # ---------- LOG ----------
    def log(self, msg, color=RESET):
        print(f"{color}{msg}{RESET}")

    # ---------- JSON ----------
    def load_json(self, file, default):
        if os.path.exists(file):
            with open(file, "r") as f:
                return json.load(f)
        return default

    def save_json(self, file, data):
        with open(file, "w") as f:
            json.dump(data, f, indent=4)

    # ---------- ADB ----------
    def detect_device(self):
        try:
            out = subprocess.check_output(["adb", "devices"]).decode()
            for line in out.splitlines():
                if "\tdevice" in line:
                    self.device_id = line.split("\t")[0]
                    self.adb = f"adb -s {self.device_id} shell"
                    self.log(f"✔ Device détecté : {self.device_id}", GREEN)
                    return True
            self.log("❌ Aucun appareil autorisé", RED)
            return False
        except Exception as e:
            self.log(f"ADB ERROR : {e}", RED)
            return False

    # ---------- TEST LIEN ----------
    def test_link_alive(self, url):
        try:
            r = requests.head(url, allow_redirects=True, timeout=10)
            return r.status_code < 400
        except:
            return False

    # ---------- TASK ----------
    async def do_task(self, account_idx, link, action):
        try:
            self.log("🧹 Fermeture complète du clone (WaxMoon)", BLUE)
            os.system(f"{self.adb} am force-stop {CLONE_CONTAINER_PACKAGE}")
            await asyncio.sleep(1)

            if "Like" in action:
                self.log("🔎 Test disponibilité du lien", CYAN)
                if not self.test_link_alive(link):
                    self.log("❌ Lien invalide ou supprimé", RED)
                    return False

            self.log("🔗 Ouverture du lien TikTok", CYAN)
            os.system(f'{self.adb} am start -a android.intent.action.VIEW -d "{link}"')
            await asyncio.sleep(3)

            self.log(f"👉 Sélection clone TikTok #{account_idx}", BLUE)
            os.system(f"{self.adb} input tap {APP_CHOOSER[account_idx]}")

            self.log("⏳ Chargement du clone (40s)", YELLOW)
            await asyncio.sleep(40)

            if "Follow" in action or "profile" in action:
                self.log("🔄 Refresh profil", YELLOW)
                os.system(f"{self.adb} input swipe {SWIPE_REFRESH}")
                await asyncio.sleep(5)
                os.system(f"{self.adb} input tap {FOLLOW_BUTTON}")
                self.log("👤 Follow tenté", GREEN)

            elif "Like" in action:
                os.system(f"{self.adb} input tap {LIKE_BUTTON}")
                self.log("❤️ Like effectué", GREEN)

            await asyncio.sleep(3)

            self.log("❌ Fermeture du clone (WaxMoon)", BLUE)
            os.system(f"{self.adb} am force-stop {CLONE_CONTAINER_PACKAGE}")
            await asyncio.sleep(1)

            self.stats["tasks"] += 1
            self.save_json("stats.json", self.stats)
            return True

        except Exception as e:
            self.log(f"❌ ERREUR TASK : {e}", RED)
            return False

    # ---------- TELEGRAM ----------
    async def start_telegram(self):
        if not self.detect_device():
            return

        self.log("📡 Connexion Telegram...", CYAN)
        await self.client.start()
        self.client.add_event_handler(self.on_message, events.NewMessage(chats=TARGET_BOT))
        self.working = True
        await self.client.send_message(TARGET_BOT, "TikTok")
        await self.client.run_until_disconnected()

    async def on_message(self, event):
        text = event.message.message or ""
        buttons = event.message.buttons

        if "Link :" in text and "Action :" in text:
            link = re.search(r"Link\s*:\s*(https?://\S+)", text)
            action = re.search(r"Action\s*:\s*(.+)", text)

            if link and action:
                acc = self.accounts[self.index]
                idx = self.index + 1
                self.log(f"🔍 Recherche task sur le compte : {acc}", BLUE)
                ok = await self.do_task(idx, link.group(1), action.group(1))

                if ok and buttons:
                    for i, row in enumerate(buttons):
                        for j, btn in enumerate(row):
                            if "Completed" in btn.text or "✅" in btn.text:
                                await event.message.click(i, j)
                                self.log("✅ Task validée", GREEN)
                                return

        elif "Sorry" in text:
            self.log("😴 Aucune task trouvée", YELLOW)
            self.index = (self.index + 1) % len(self.accounts)
            await asyncio.sleep(4)
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
║ 🤖 TIKTOK BOT PRO – CLONE WAXMOON   ║
╠════════════════════════════════════╣
║ 📊 Tasks : {self.stats['tasks']}               ║
╠════════════════════════════════════╣
║ 1️⃣  Lancer le bot                  ║
║ 2️⃣  Ajouter un compte              ║
║ 3️⃣  Voir les comptes               ║
║ 4️⃣  Redétecter ADB                 ║
║ 5️⃣  Quitter                        ║
╚════════════════════════════════════╝
""")
            choice = input("Choix ➜ ")

            if choice == "1":
                if not self.accounts:
                    self.log("❌ Aucun compte ajouté", RED)
                    input("Entrée pour continuer...")
                else:
                    await self.start_telegram()

            elif choice == "2":
                name = input("Nom du compte : ")
                if name:
                    self.accounts.append(name)
                    self.save_json("accounts.json", self.accounts)

            elif choice == "3":
                clear_screen()
                self.log("📂 LISTE DES COMPTES", CYAN)
                for i, acc in enumerate(self.accounts, 1):
                    print(f"{i}. {acc}")
                input("\nEntrée pour revenir...")

            elif choice == "4":
                self.detect_device()
                input("Entrée pour continuer...")

            elif choice == "5":
                self.log("👋 Arrêt du bot", GREEN)
                break


# ================== MAIN ==================
if __name__ == "__main__":
    bot = TikTokTaskBot()
    asyncio.run(bot.menu())
