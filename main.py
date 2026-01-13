import os
import json
import asyncio
import re
from dotenv import load_dotenv
from telethon import TelegramClient, events

# --- CONFIGURATION ---
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
        """Sauvegarde immédiate sur le disque"""
        with open('stats.json', 'w') as f:
            json.dump(self.stats, f, indent=4)

    def save_accounts(self):
        with open('accounts.json', 'w') as f:
            json.dump(self.accounts, f, indent=4)

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
            reward_val = 0.0
            # Extraction du Reward dans le message
            match = re.search(r"Reward\s*:\s*\n?(\d+\.?\d*)", text, re.IGNORECASE)
            if match:
                reward_val = float(match.group(1))

            if buttons:
                for i, row in enumerate(buttons):
                    for j, btn in enumerate(row):
                        if "Completed" in btn.text or "✅" in btn.text:
                            print(f"⏳ Tâche détectée ({reward_val} coins). Attente 5s...")
                            await asyncio.sleep(5)
                            
                            # ACTION DE CLIQUER
                            await event.message.click(i, j)
                            
                            # --- MISE À JOUR INSTANTANÉE ---
                            self.stats["total_earned"] += reward_val
                            self.stats["tasks_completed"] += 1
                            self.save_stats_now() # On écrit sur le fichier tout de suite
                            
                            print(f"💰 +{reward_val} ajouté ! Nouveau total : {self.stats['total_earned']:.2f} CashCoins")
                            return

        # --- GESTION DU "SORRY" (PAS DE TÂCHE) ---
        elif "Sorry" in text:
            print(f"❌ Pas de tâche sur : {self.accounts[self.current_account_index]}")
            self.current_account_index = (self.current_account_index + 1) % len(self.accounts)
            
            # Si on a fini le tour des comptes
            if self.current_account_index == 0:
                print("🔄 Cycle terminé. Pause de 20 secondes...")
                await asyncio.sleep(10)
            
            await asyncio.sleep(2)
            await self.client.send_message(TARGET_BOT, 'TikTok')

        # --- SÉLECTION DES COMPTES DANS LA LISTE ---
        elif buttons:
            current_target = self.accounts[self.current_account_index]
            for i, row in enumerate(buttons):
                for j, btn in enumerate(row):
                    if btn.text == current_target:
                        print(f"👤 Clic sur le compte : {btn.text}")
                        await asyncio.sleep(1.5)
                        await event.message.click(i, j)
                        return
                    if "TikTok" in btn.text: # Si on est au menu principal
                        await asyncio.sleep(1)
                        await self.client.send_message(TARGET_BOT, 'TikTok')
                        return

# --- INTERFACE MENU ---
async def main_menu():
    bot = TaskBot()
    while True:
        print(f"\n[ SOLDE ACTUEL : {bot.stats['total_earned']:.2f} CashCoins ]")
        print("[1] Lancer le bot")
        print("[2] Ajouter un compte")
        print("[3] Liste des comptes")
        print("[4] Quitter")
        
        c = input("Choix : ")
        if c == '1':
            if not bot.accounts: print("❌ Aucun compte !"); continue
            await bot.start_telegram()
        elif c == '2':
            name = input("Nom du compte : ")
            if name: bot.accounts.append(name); bot.save_accounts(); print("✅ OK")
        elif c == '3':
            print(f"Comptes ({len(bot.accounts)}) :", bot.accounts)
        elif c == '4': break

if __name__ == '__main__':
    asyncio.run(main_menu())
