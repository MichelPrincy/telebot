import os
import json
import asyncio
import re
import subprocess
from dotenv import load_dotenv
from telethon import TelegramClient, events

# --- CONFIGURATION TÉLÉPHONE ---
MULTI_APP_PACKAGE = "com.waxmoon.ma.gp/com.waxmoon.mobile.module.home.MainActivity"
TIKTOK_PACKAGE = "com.zhiliaoapp.musically"

COORDINATES = {
    "LIKE_BUTTON": "950 1100",
    "FOLLOW_BUTTON": "950 850",
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
        self.adb_prefix = "adb shell" # Valeur par défaut

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

    # --- DÉTECTION DU MEILLEUR APPAREIL ---
    def detect_device(self):
        """Détecte l'appareil avec le statut 'device' et ignore 'unauthorized'"""
        try:
            output = subprocess.check_output(["adb", "devices"]).decode("utf-8")
            lines = output.strip().split('\n')[1:] # On ignore la première ligne
            
            authorized_devices = []
            for line in lines:
                if "\tdevice" in line:
                    authorized_devices.append(line.split('\t')[0])
            
            if not authorized_devices:
                print("❌ Aucun appareil autorisé trouvé (statut 'device' absent).")
                return False
            
            # On prend le premier appareil valide trouvé
            self.device_id = authorized_devices[0]
            self.adb_prefix = f"adb -s {self.device_id} shell"
            print(f"✅ Appareil détecté et ciblé : {self.device_id}")
            return True
        except Exception as e:
            print(f"❌ Erreur lors de la détection ADB : {e}")
            return False

    # --- LOGIQUE D'AUTOMATISATION ADB ---
    async def run_adb_interaction(self, account_idx, link, action):
        if not self.device_id:
            if not self.detect_device(): return False

        try:
            print(f"🤖 [Device: {self.device_id}] Lancement TikTok session n°{account_idx}...")
            
            # 1. Ouvrir Multi App
            os.system(f"{self.adb_prefix} am start -n {MULTI_APP_PACKAGE}")
            await asyncio.sleep(4)

            # 2. Cliquer sur le bloc TikTok
            pos = COORDINATES["APP_SLOTS"].get(account_idx, "540 400")
            os.system(f"{self.adb_prefix} input tap {pos}")
            await asyncio.sleep(6)

            # 3. Ouvrir le lien
            print(f"🔗 Ouverture du lien : {link}")
            os.system(f"{self.adb_prefix} am start -a android.intent.action.VIEW -d {link}")
            await asyncio.sleep(8)

            # 4. Action Like ou Follow
            if "Like" in action:
                os.system(f"{self.adb_prefix} input tap {COORDINATES['LIKE_BUTTON']}")
                print("❤️ Action : Like effectué")
            elif "Follow" in action or "profile" in action:
                os.system(f"{self.adb_prefix} input tap {COORDINATES['FOLLOW_BUTTON']}")
                print("👤 Action : Follow effectué")
            
            await asyncio.sleep(3)

            # 5. Fermer TikTok et revenir Termux
            os.system(f"{self.adb_prefix} am force-stop {TIKTOK_PACKAGE}")
            os.system(f"{self.adb_prefix} am start -n com.termux/.MainActivity")
            return True
        except Exception as e:
            print(f"❌ Erreur interaction : {e}")
            return False

    async def start_telegram(self):
        # Vérification du device avant de lancer Telegram
        if not self.detect_device():
            print("🛑 Abandon : Aucun téléphone connecté via ADB.")
            return

        print("\n--- Connexion à Telegram ---")
        try:
            await self.client.start()
            self.client.add_event_handler(self.message_handler, events.NewMessage(chats=TARGET_BOT))
            self.working = True
            await self.client.send_message(TARGET_BOT, 'TikTok')
            await self.client.run_until_disconnected()
        except Exception as e:
            print(f"❌ Erreur Telegram : {e}")

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

                print(f"⚡ Tâche pour {current_acc_name} (Session {account_num})")
                
                success = await self.run_adb_interaction(account_num, url, action)

                if success and buttons:
                    for i, row in enumerate(buttons):
                        for j, btn in enumerate(row):
                            if any(x in btn.text for x in ["Completed", "✅"]):
                                await event.message.click(i, j)
                                self.stats["total_earned"] += reward_val
                                self.save_stats_now()
                                print(f"💰 Succès ! Total : {self.stats['total_earned']:.2f}")
                                return

        elif "Sorry" in text:
            self.current_account_index = (self.current_account_index + 1) % len(self.accounts)
            await asyncio.sleep(2)
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
        print(f"\n--- MENU (Device: {bot.device_id or 'Non détecté'}) ---")
        print(f"Solde actuel: {bot.stats['total_earned']:.2f} coins")
        print("[1] Lancer le cycle")
        print("[2] Ajouter un compte")
        print("[3] Redétecter le téléphone (ADB)")
        print("[4] Quitter")
        
        choice = input("Choix : ")
        if choice == '1':
            if not bot.accounts: print("❌ Liste de comptes vide !"); continue
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
