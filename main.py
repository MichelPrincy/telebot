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
MAGENTA = "\033[95m"
RESET = "\033[0m"

# ================== PACKAGES ==================
CLONE_CONTAINER_PACKAGE = "com.waxmoon.ma.gp"
MULTI_APP_MAIN = "com.waxmoon.ma.gp/com.waxmoon.mobile.module.home.MainActivity"
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
            with open(file, "r") as f:
                return json.load(f)
        return default

    def save_json(self, file, data):
        with open(file, "w") as f:
            json.dump(data, f, indent=4)

    def detect_device(self):
        try:
            out = subprocess.check_output(["adb", "devices"]).decode()
            for line in out.splitlines():
                if "\tdevice" in line:
                    self.device_id = line.split("\t")[0]
                    self.adb = f"adb -s {self.device_id} shell"
                    self.log(f"✔ Device détecté : {self.device_id}", GREEN)
                    return True
            self.log("❌ Aucun appareil détecté", RED)
            return False
        except Exception as e:
            self.log(f"ADB ERROR : {e}", RED)
            return False

    # ---------- GESTION DES APPS ----------
    def cleanup_apps(self):
        """Ferme tout sauf Termux et le Multi-App principal"""
        self.log("🧹 Nettoyage des applications en cours...", YELLOW)
        # On force l'arrêt du container avant de commencer
        os.system(f"{self.adb} am force-stop {CLONE_CONTAINER_PACKAGE}")
        # On peut ajouter d'autres apps connues à fermer ici si besoin
        os.system(f"{self.adb} am kill-all") 
        # On s'assure que Termux reste actif (normalement il l'est puisqu'on tourne dedans)

    def focus_termux(self):
        """Ramène Termux au premier plan"""
        os.system(f"{self.adb} am start --activity-brought-to-front {TERMUX_PACKAGE}")

    # ---------- CORE TASK ----------
    async def perform_single_action(self, account_idx, link, action):
        """Une seule itération : Ouvrir -> Action -> Fermer"""
        try:
            # Ouverture du lien
            os.system(f'{self.adb} am start -a android.intent.action.VIEW -d "{link}"')
            await asyncio.sleep(4)

            # Sélection du clone
            os.system(f"{self.adb} input tap {APP_CHOOSER[account_idx]}")
            
            # Attente chargement (réduit à 30s pour efficacité, à ajuster si besoin)
            await asyncio.sleep(30)

            if "Follow" in action or "profile" in action:
                os.system(f"{self.adb} input swipe {SWIPE_REFRESH}")
                await asyncio.sleep(4)
                os.system(f"{self.adb} input tap {FOLLOW_BUTTON}")
            else:
                os.system(f"{self.adb} input tap {LIKE_BUTTON}")

            await asyncio.sleep(3)
            
            # Fermeture du clone
            os.system(f"{self.adb} am force-stop {CLONE_CONTAINER_PACKAGE}")
            return True
        except Exception as e:
            self.log(f"Erreur durant l'action : {e}", RED)
            return False

    async def do_task(self, account_idx, link, action):
        self.cleanup_apps()
        
        # --- RÉPÉTITION DE LA MÉTHODE 2 FOIS ---
        for i in range(1, 3):
            self.log(f"🔄 Exécution itération {i}/2...", CYAN)
            success = await self.perform_single_action(account_idx, link, action)
            if not success: return False
            await asyncio.sleep(2)

        # Retour final sur Termux
        self.focus_termux()
        return True

    # ---------- TELEGRAM HANDLER ----------
    async def start_telegram(self):
        if not self.detect_device(): return
        self.log("📡 Connexion Telegram...", CYAN)
        await self.client.start()
        self.client.add_event_handler(self.on_message, events.NewMessage(chats=TARGET_BOT))
        self.working = True
        
        # Premier lancement
        acc = self.accounts[self.index]
        self.log(f"\nrecherche de task sur le compte: {acc}...", MAGENTA)
        await self.client.send_message(TARGET_BOT, "TikTok")
        await self.client.run_until_disconnected()

    async def on_message(self, event):
        text = event.message.message or ""
        buttons = event.message.buttons

        # 1. Détection de Task
        if "Link :" in text and "Action :" in text:
            link_match = re.search(r"Link\s*:\s*(https?://\S+)", text)
            action_match = re.search(r"Action\s*:\s*(.+)", text)

            if link_match and action_match:
                link = link_match.group(1)
                action_type = action_match.group(1)
                
                self.log(f"task trouver, lien: {link}   type: {action_type}", GREEN)
                
                idx = self.index + 1
                ok = await self.do_task(idx, link, action_type)

                if ok and buttons:
                    for i, row in enumerate(buttons):
                        for j, btn in enumerate(row):
                            if "Completed" in btn.text or "✅" in btn.text:
                                await event.message.click(i, j)
                                return

        # 2. Détection de validation (Gain de coins)
        elif "added" in text.lower() or "success" in text.lower() or "+" in text:
            # On essaie d'extraire le montant si présent
            gain = re.search(r"(\+?\d+(\.\d+)?)", text)
            gain_str = gain.group(1) if gain else "1.1"
            
            self.log(f"\n✅ validation réussie", GREEN)
            self.log(f"12 + {gain_str} cashcoins", YELLOW)
            
            # Relancer la recherche
            acc = self.accounts[self.index]
            self.log(f"\nrecherche de task sur le compte: {acc}...", MAGENTA)
            await asyncio.sleep(2)
            await self.client.send_message(TARGET_BOT, "TikTok")

        # 3. Aucun task trouvé
        elif "Sorry" in text or "No more" in text:
            self.log(f"pas de task sur ce compte.", RED)
            
            # Passer au compte suivant
            self.index = (self.index + 1) % len(self.accounts)
            acc = self.accounts[self.index]
            
            self.log(f"\nrecherche de task sur le compte: {acc}...", MAGENTA)
            await asyncio.sleep(3)
            await self.client.send_message(TARGET_BOT, "TikTok")

        # 4. Sélection du compte au début
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
║ 📊 Comptes actifs : {len(self.accounts)}              ║
╠════════════════════════════════════╣
║ 1️⃣  Lancer le bot                  ║
║ 2️⃣  Ajouter un compte               ║
║ 3️⃣  Voir les comptes               ║
║ 4️⃣  Quitter                         ║
╚════════════════════════════════════╝
""")
            choice = input("Choix ➜ ")
            if choice == "1":
                if not self.accounts:
                    print("❌ Ajoute un compte d'abord")
                    await asyncio.sleep(2)
                else:
                    await self.start_telegram()
            elif choice == "2":
                name = input("Nom exact du compte TikTok : ")
                if name:
                    self.accounts.append(name)
                    self.save_json("accounts.json", self.accounts)
            elif choice == "3":
                print(self.accounts)
                input("\nEntrée pour continuer...")
            elif choice == "4":
                break

if __name__ == "__main__":
    bot = TikTokTaskBot()
    try:
        asyncio.run(bot.menu())
    except KeyboardInterrupt:
        print("\nArrêt demandé.")
