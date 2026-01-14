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
MULTI_APP_PACKAGE = "com.waxmoon.ma.gp"
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
        out = subprocess.check_output(["adb", "devices"]).decode()
        for line in out.splitlines():
            if "\tdevice" in line:
                self.device_id = line.split("\t")[0]
                self.adb = f"adb -s {self.device_id} shell"
                self.log(f"✔ Device détecté : {self.device_id}", GREEN)
                return True
        self.log("❌ Aucun device ADB", RED)
        return False

    def close_all_except(self):
        self.log("🧹 Fermeture apps inutiles", BLUE)
        out = subprocess.check_output(f"{self.adb} pm list packages", shell=True).decode()
        for line in out.splitlines():
            pkg = line.replace("package:", "").strip()
            if not pkg.startswith("com.termux") and not pkg.startswith("com.waxmoon.ma.gp"):
                os.system(f"{self.adb} am force-stop {pkg}")

    def back_to_termux(self):
        os.system(f"{self.adb} am start -n {TERMUX_PACKAGE}")

    # ---------- LIEN ----------
    def test_link_alive(self, url):
        try:
            r = requests.head(url, timeout=10, allow_redirects=True)
            return r.status_code < 400
        except:
            return False

    # ---------- TASK ----------
    async def do_task(self, acc_idx, link, action):
        self.close_all_except()

        if "Like" in action and not self.test_link_alive(link):
            self.log("❌ lien invalide", RED)
            return False

        for round in range(2):
            self.log(f"🔗 ouverture lien (tentative {round+1})", CYAN)
            os.system(f'{self.adb} am start -a android.intent.action.VIEW -d "{link}"')
            await asyncio.sleep(3)

            self.log(f"👉 choix clone #{acc_idx}", BLUE)
            os.system(f"{self.adb} input tap {APP_CHOOSER[acc_idx]}")
            await asyncio.sleep(40)

            if "Follow" in action:
                os.system(f"{self.adb} input swipe {SWIPE_REFRESH}")
                await asyncio.sleep(3)
                os.system(f"{self.adb} input tap {FOLLOW_BUTTON}")
                self.log("👤 follow effectué", GREEN)
            else:
                os.system(f"{self.adb} input tap {LIKE_BUTTON}")
                self.log("❤️ like effectué", GREEN)

            await asyncio.sleep(3)
            os.system(f"{self.adb} am force-stop {MULTI_APP_PACKAGE}")
            self.back_to_termux()

        self.stats["tasks"] += 1
        self.stats["earned"] += 1.1
        self.save_json("stats.json", self.stats)
        self.log("like valide", GREEN)
        self.log(f"{self.stats['tasks']} + 1.1 cashcoins", CYAN)
        return True

    # ---------- TELEGRAM ----------
    async def start_telegram(self):
        if not self.detect_device():
            return
        await self.client.start()
        self.client.add_event_handler(self.on_message, events.NewMessage(chats=TARGET_BOT))
        await self.client.send_message(TARGET_BOT, "TikTok")
        await self.client.run_until_disconnected()

    async def on_message(self, event):
        text = event.message.message or ""
        buttons = event.message.buttons

        acc = self.accounts[self.index]
        self.log(f"recherche de task sur le compte : {acc}", BLUE)

        if "Link :" in text and "Action :" in text:
            link = re.search(r"Link\s*:\s*(https?://\S+)", text)
            action = re.search(r"Action\s*:\s*(.+)", text)
            if link and action:
                self.log(f"task trouvée, lien : {link.group(1)}  type : {action.group(1)}", CYAN)
                ok = await self.do_task(self.index+1, link.group(1), action.group(1))
                if ok and buttons:
                    for i, row in enumerate(buttons):
                        for j, btn in enumerate(row):
                            if "Completed" in btn.text:
                                await event.message.click(i, j)
                                return

        else:
            self.log("pas de task sur ce compte", YELLOW)
            self.index = (self.index + 1) % len(self.accounts)
            await asyncio.sleep(3)
            await self.client.send_message(TARGET_BOT, "TikTok")

    # ---------- MENU ----------
    async def menu(self):
        while True:
            clear_screen()
            print(f"""
{BLUE}╔════════════════════════════════════╗
║ 🤖 TIKTOK BOT WAXMOON PRO           ║
╠════════════════════════════════════╣
║ 📊 Tasks : {self.stats['tasks']}   ║
╠════════════════════════════════════╣
║ 1️⃣  Lancer le bot                  ║
║ 2️⃣  Ajouter un compte              ║
║ 3️⃣  Voir les comptes               ║
║ 4️⃣  Redétecter ADB                 ║
║ 5️⃣  Quitter                        ║
╚════════════════════════════════════╝
""")
            c = input("Choix ➜ ")
            if c == "1":
                await self.start_telegram()
            elif c == "2":
                self.accounts.append(input("Nom compte : "))
                self.save_json("accounts.json", self.accounts)
            elif c == "3":
                for i, a in enumerate(self.accounts, 1):
                    print(i, a)
                input("Entrée...")
            elif c == "4":
                self.detect_device()
                input("Entrée...")
            elif c == "5":
                break


# ================== MAIN ==================
if __name__ == "__main__":
    bot = TikTokTaskBot()
    asyncio.run(bot.menu())
