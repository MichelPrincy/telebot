import os
import json
import asyncio
import re
import subprocess
from dotenv import load_dotenv
from telethon import TelegramClient, events

# ====== COULEURS TERMINAL ======
RED = "\033[91m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
CYAN = "\033[96m"
RESET = "\033[0m"

# ====== PACKAGES ======
TIKTOK_PACKAGE = "com.zhiliaoapp.musically"
TERMUX_PACKAGE = "com.termux/com.termux.app.TermuxActivity"

# ====== COORDONNÉES ======
APP_CHOOSER = {
    1: "145 2015",
    2: "340 2015",
    3: "535 2015",
}

LIKE_BUTTON = "990 1200"
FOLLOW_BUTTON = "350 840"

# ====== TELEGRAM ======
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

    # ====== UTILS ======
    def load_json(self, file, default):
        if os.path.exists(file):
            with open(file, "r") as f:
                return json.load(f)
        return default

    def save_json(self, file, data):
        with open(file, "w") as f:
            json.dump(data, f, indent=4)

    # ====== ADB ======
    def detect_device(self):
        try:
            out = subprocess.check_output(["adb", "devices"]).decode()
            for line in out.splitlines():
                if "\tdevice" in line:
                    self.device_id = line.split("\t")[0]
                    self.adb = f"adb -s {self.device_id} shell"
                    print(f"{GREEN}✔ Device détecté : {self.device_id}{RESET}")
                    return True
            print(f"{RED}❌ Aucun device autorisé{RESET}")
            return False
        except Exception as e:
            print(f"{RED}ADB ERROR : {e}{RESET}")
            return False

    # ====== ADB TASK ======
    async def do_task(self, account_idx, link, action):
        try:
            os.system(f"{self.adb} am force-stop {TIKTOK_PACKAGE}")
            await asyncio.sleep(1)

            print(f"{CYAN}🔗 Ouverture lien TikTok{RESET}")
            os.system(f'{self.adb} am start -a android.intent.action.VIEW -d "{link}"')
            await asyncio.sleep(3)

            pos = APP_CHOOSER.get(account_idx)
            if not pos:
                print(f"{RED}Clone inexistant{RESET}")
                return False

            print(f"{BLUE}👉 Clone TikTok #{account_idx}{RESET}")
            os.system(f"{self.adb} input tap {pos}")

            print(f"{YELLOW}⏳ Chargement TikTok...{RESET}")
            await asyncio.sleep(40)

            if "Like" in action:
                os.system(f"{self.adb} input tap {LIKE_BUTTON}")
                print(f"{GREEN}❤️ Like OK{RESET}")

            elif "Follow" in action or "profile" in action:
                os.system(f"{self.adb} input tap {FOLLOW_BUTTON}")
                print(f"{GREEN}👤 Follow OK{RESET}")

            await asyncio.sleep(3)
            os.system(f"{self.adb} am force-stop {TIKTOK_PACKAGE}")
            os.system(f"{self.adb} am start -n {TERMUX_PACKAGE}")

            self.stats["earned"] += 0
            self.stats["tasks"] += 1
            self.save_json("stats.json", self.stats)
            return True

        except Exception as e:
            print(f"{RED}TASK ERROR : {e}{RESET}")
            return False

    # ====== TELEGRAM ======
    async def start_telegram(self):
        if not self.detect_device():
            return

        print(f"{CYAN}Connexion Telegram...{RESET}")
        await self.client.start()
        self.client.add_event_handler(self.on_message, events.NewMessage(chats=TARGET_BOT))
        self.working = True
        await self.client.send_message(TARGET_BOT, "TikTok")
        await self.client.run_until_disconnected()

    async def on_message(self, event):
        text = event.message.message or ""
        buttons = event.message.buttons

        if "Link :" in text:
            link = re.search(r"Link\s*:\s*(https?://\S+)", text)
            action = re.search(r"Action\s*:\s*(.+)", text)

            if link and action:
                acc = self.accounts[self.index]
                idx = self.index + 1

                print(f"\n{BLUE}⚡ TASK | {acc} | Clone #{idx}{RESET}")
                ok = await self.do_task(idx, link.group(1), action.group(1))

                if ok and buttons:
                    for i, row in enumerate(buttons):
                        for j, btn in enumerate(row):
                            if "Completed" in btn.text or "✅" in btn.text:
                                await event.message.click(i, j)
                                print(f"{GREEN}✔ Task validée{RESET}")
                                break

        elif "Sorry" in text:
            self.index = (self.index + 1) % len(self.accounts)
            await asyncio.sleep(4)
            await self.client.send_message(TARGET_BOT, "TikTok")

        elif buttons:
            target = self.accounts[self.index]
            for i, row in enumerate(buttons):
                for j, btn in enumerate(row):
                    if btn.text == target:
                        await event.message.click(i, j)

    # ====== MENU ======
    def show_accounts(self):
        print(f"\n{CYAN}📂 LISTE DES COMPTES{RESET}")
        for i, acc in enumerate(self.accounts, 1):
            print(f"{i}. {acc}")
        print("-" * 30)

    async def menu(self):
        while True:
            print(f"""
{BLUE}╔════════════════════════════════╗
║   🤖 TIKTOK BOT PRO (ADB)       ║
╠════════════════════════════════╣
║ 💰 Gain : {self.stats['earned']}               ║
║ 📊 Tasks : {self.stats['tasks']}               ║
╠════════════════════════════════╣
║ 1️⃣  Lancer le bot               ║
║ 2️⃣  Ajouter un compte           ║
║ 3️⃣  Voir les comptes            ║
║ 4️⃣  Redétecter ADB              ║
║ 5️⃣  Quitter                     ║
╚════════════════════════════════╝
""")

            choice = input(f"{YELLOW}Choix ➜ {RESET}")

            if choice == "1":
                if not self.accounts:
                    print(f"{RED}Aucun compte !{RESET}")
                else:
                    await self.start_telegram()

            elif choice == "2":
                name = input("Nom du compte : ")
                if name:
                    self.accounts.append(name)
                    self.save_json("accounts.json", self.accounts)

            elif choice == "3":
                self.show_accounts()

            elif choice == "4":
                self.detect_device()

            elif choice == "5":
                print("Bye 👋")
                break


# ====== MAIN ======
if __name__ == "__main__":
    bot = TikTokTaskBot()
    asyncio.run(bot.menu())
