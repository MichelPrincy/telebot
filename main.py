import os
import json
import asyncio
import re
import time
from dotenv import load_dotenv
from telethon import TelegramClient, events

# --- CONFIGURATION TÉLÉPHONE (À MODIFIER) ---
# Remplace par le nom du package de ton application Multi App
MULTI_APP_PACKAGE = "com.multi.app.package/.MainActivity" 

# Remplace les coordonnées X Y par les tiennes
COORDINATES = {
    "LIKE_BUTTON": "950 1100",
    "FOLLOW_BUTTON": "950 850",
    "ACCOUNTS": {
        "Compte1": "250 500", # Position de la 1ère icône TikTok dans Multi App
        "Compte2": "500 500", # Position de la 2ème icône
        "Compte3": "750 500", # Position de la 3ème icône
    }
}

# --- CONFIGURATION API ---
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

    def load_accounts(self):
        try:
            if os.path.exists('accounts.json') and os.path.getsize('accounts.json') > 0:
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

    def save_accounts(self):
        with open('accounts.json', 'w') as f:
            json.dump(self.accounts, f, indent=4)

    # --- LOGIQUE D'AUTOMATISATION ADB ---
    async def run_adb_interaction(self, account_name, link, action):
        print(f"🤖 Action Android en cours pour {account_name}...")
        
        # 1. Ouvrir Multi App
        os.system(f"am start -n {MULTI_APP_PACKAGE}")
        await asyncio.sleep(3)

        # 2. Cliquer sur l'icône TikTok spécifique
        pos = COORDINATES["ACCOUNTS"].get(account_name, "250 500")
        os.system(f"input tap {pos}")
        await asyncio.sleep(5) # Attente ouverture TikTok

        # 3. Ouvrir le lien de la vidéo
        os.system(f"am start -a android.intent.action.VIEW -d {link}")
        await asyncio.sleep(6) # Attente chargement vidéo

        # 4. Effectuer l'action
        if "Like" in action:
            os.system(f"input tap {COORDINATES['LIKE_BUTTON']}")
            print("❤️ Like envoyé")
        elif "Follow" in action or "Suivre" in action:
            os.system(f"input tap {COORDINATES['FOLLOW_BUTTON']}")
            print("👤 Follow envoyé")
        
        await asyncio.sleep(2)

        # 5. Retourner sur Termux/Telegram
        os.system("am start -n com.termux/.MainActivity")
        await asyncio.sleep(1)

    async def start_telegram(self):
        print("\n--- Connexion à Telegram ---")
        try:
            await self.client.start()
            print(f"✅ Connecté !")
            self.client.add_event_handler(self.message_handler, events.NewMessage(chats=TARGET_BOT))
            self.working = True
            await self.client.send_message(TARGET_BOT, 'TikTok')
            await self.client.run_until_disconnected()
        except Exception as e:
            print(f"❌ Erreur : {e}")

    async def message_handler(self, event):
        if not self.working: return
        text = event.message.message or ""
        buttons = event.message.buttons

        # --- DÉTECTION DE TÂCHE ET RÉCOMPENSE ---
        if "Link :" in text and "Action :" in text:
            # Extraction des infos
            link_match = re.search(r"Link\s*:\s*(https?://[^\s\n]+)", text)
            action_match = re.search(r"Action\s*:\s*([^\n]+)", text)
            reward_match = re.search(r"Reward\s*:\s*\n?(\d+\.?\d*)", text, re.IGNORECASE)

            if link_match and action_match:
                url = link_match.group(1)
                action = action_match.group(1)
                reward_val = float(reward_match.group(1)) if reward_match else 0.0
                current_acc = self.accounts[self.current_account_index]

                print(f"⏳ Tâche trouvée : {action} sur {current_acc}")
                
                # EXECUTION DE L'AUTOMATISATION
                await self.run_adb_interaction(current_acc, url, action)

                # CLIQUER SUR "COMPLETED" DANS TELEGRAM
                if buttons:
                    for i, row in enumerate(buttons):
                        for j, btn in enumerate(row):
                            if "Completed" in btn.text or "✅" in btn.text:
                                await event.message.click(i, j)
                                
                                # MISE À JOUR STATS
                                self.stats["total_earned"] += reward_val
                                self.stats["tasks_completed"] += 1
                                self.save_stats_now()
                                print(f"💰 +{reward_val} ajouté ! Total : {self.stats['total_earned']:.2f}")
                                return

        # --- GESTION DU "SORRY" (PAS DE TÂCHE) ---
        elif "Sorry" in text:
            print(f"❌ Pas de tâche sur : {self.accounts[self.current_account_index]}")
            self.current_account_index = (self.current_account_index + 1) % len(self.accounts)
            
            if self.current_account_index == 0:
                print("🔄 Cycle terminé. Pause de 10 secondes...")
                await asyncio.sleep(10)
            
            await asyncio.sleep(2)
            await self.client.send_message(TARGET_BOT, 'TikTok')

        # --- SÉLECTION DES COMPTES DANS LA LISTE ---
        elif buttons:
            current_target = self.accounts[self.current_account_index]
            for i, row in enumerate(buttons):
                for j, btn in enumerate(row):
                    if btn.text == current_target:
                        print(f"👤 Sélection du compte bot : {btn.text}")
                        await asyncio.sleep(1)
                        await event.message.click(i, j)
                        return
                    if "TikTok" in btn.text:
                        await asyncio.sleep(1)
                        await self.client.send_message(TARGET_BOT, 'TikTok')
                        return

# --- INTERFACE MENU ---
async def main_menu():
    bot = TaskBot()
    while True:
        print(f"\n[ SOLDE ACTUEL : {bot.stats['total_earned']:.2f} CashCoins ]")
        print("[1] Lancer le bot")
        print("[2] Ajouter un compte (ex: Compte1)")
        print("[3] Liste des comptes")
        print("[4] Quitter")
        
        c = input("Choix : ")
        if c == '1':
            if not bot.accounts: print("❌ Aucun compte !"); continue
            await bot.start_telegram()
        elif c == '2':
            name = input("Nom exact du compte (doit correspondre à COORDINATES) : ")
            if name: bot.accounts.append(name); bot.save_accounts(); print("✅ OK")
        elif c == '3':
            print(f"Comptes ({len(bot.accounts)}) :", bot.accounts)
        elif c == '4': break

if __name__ == '__main__':
    asyncio.run(main_menu())
