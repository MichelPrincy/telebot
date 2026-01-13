import os
import json
import asyncio
import logging
import re
from dotenv import load_dotenv
from telethon import TelegramClient, events

# --- CONFIGURATION ---
load_dotenv()
API_ID = os.getenv('API_ID')
API_HASH = os.getenv('API_HASH')
TARGET_BOT = '@SmmKingdomTasksBot'

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger("BotLogger")

class TaskBot:
    def __init__(self):
        self.accounts = self.load_accounts()
        self.current_account_index = 0
        self.client = TelegramClient('session_telebot', int(API_ID), API_HASH)
        self.working = False

    def load_accounts(self):
        try:
            if os.path.exists('accounts.json') and os.path.getsize('accounts.json') > 0:
                with open('accounts.json', 'r') as f:
                    return json.load(f)
            return []
        except Exception as e:
            print(f"Erreur chargement comptes: {e}")
            return []

    def save_accounts(self):
        with open('accounts.json', 'w') as f:
            json.dump(self.accounts, f, indent=4)

    async def start_telegram(self):
        print("\n--- Connexion à Telegram ---")
        try:
            await self.client.start()
        except Exception as e:
            print(f"❌ Erreur : {e}")
            return

        me = await self.client.get_me()
        print(f"✅ Connecté : {me.first_name}")
        
        self.client.add_event_handler(self.message_handler, events.NewMessage(chats=TARGET_BOT))
        self.working = True
        await self.send_tiktok_command()
        await self.client.run_until_disconnected()

    async def send_tiktok_command(self):
        """Envoie le message TikTok pour ouvrir le menu des comptes"""
        print(f"🤖 [Action] Envoi de 'TikTok'...")
        await self.client.send_message(TARGET_BOT, 'TikTok')

    async def message_handler(self, event):
        if not self.working:
            return

        text = event.message.message or ""
        buttons = event.message.buttons
        
        # --- CAS 1 : TACHE TROUVÉE (Extraction des infos) ---
        if "Link :" in text and "Action :" in text:
            # Extraction propre des données
            lines = [l.strip() for l in text.split('\n') if l.strip()]
            task_link = "Inconnu"
            task_type = "Autre"

            for i, line in enumerate(lines):
                if "Link" in line and (i + 1) < len(lines):
                    # On prend le premier lien trouvé sur la ligne suivante (avant la parenthèse)
                    task_link = lines[i+1].split(' ')[0]
                if "Action" in line and (i + 1) < len(lines):
                    action_text = lines[i+1].lower()
                    if "like" in action_text: task_type = "Like"
                    elif "follow" in action_text: task_type = "Follow"
                    elif "comment" in action_text: task_type = "Comment"

            # --- AFFICHAGE DEMANDÉ ---
            print("\n" + "="*30)
            print("🎯 Task trouver")
            print(f"🔗 lien: {task_link}")
            print(f"📝 Type: {task_type}")
            print("="*30)
            
            if buttons:
                for i, row in enumerate(buttons):
                    for j, btn in enumerate(row):
                        if "Completed" in btn.text or "✅" in btn.text:
                            # Pause plus longue pour simuler le temps d'ouverture de TikTok
                            print(f"⏳ Simulation de la tâche ({task_type})...")
                            await asyncio.sleep(5) 
                            print("👆 Clic sur 'Completed'...")
                            await event.message.click(i, j)
                            return

        # --- CAS 2 : PAS DE TACHE (SORRY) ---
        elif "Sorry" in text:
            print(f"❌ Pas de tâche pour : {self.accounts[self.current_account_index]}")
            self.current_account_index += 1
            
            if self.current_account_index >= len(self.accounts):
                print("🔄 Fin de liste. Reprise dans 15s...")
                self.current_account_index = 0
                await asyncio.sleep(15)
            
            await asyncio.sleep(2)
            await self.send_tiktok_command()

        # --- CAS 3 : NAVIGATION MENU (TikTok / Liste comptes) ---
        elif buttons:
            current_target = self.accounts[self.current_account_index]
            is_main_menu = False

            for i, row in enumerate(buttons):
                for j, btn in enumerate(row):
                    if btn.text == current_target:
                        print(f"👤 Sélection du compte : {btn.text}")
                        await asyncio.sleep(1.5)
                        await event.message.click(i, j)
                        return
                    if "TikTok" in btn.text:
                        is_main_menu = True

            if is_main_menu:
                await asyncio.sleep(1)
                await self.send_tiktok_command()

    # --- MÉTHODES DU MENU ---
    def add_account(self):
        name = input("Nom du compte TikTok (ex: gat_gainer) : ")
        if name:
            self.accounts.append(name)
            self.save_accounts()
            print("✅ Compte ajouté avec succès.")

    def list_accounts(self):
        print("\n--- COMPTES TikTok ENREGISTRÉS ---")
        if not self.accounts:
            print("Aucun compte.")
        for i, acc in enumerate(self.accounts):
            print(f"[{i}] {acc}")

async def main_menu():
    bot = TaskBot()
    while True:
        print("\n=== BOT SMM KINGDOM TASK ===")
        print("[1] Démarrer l'automatisation")
        print("[2] Gérer les comptes (Liste/Ajout)")
        print("[3] Quitter")
        
        choice = input("👉 Choix : ")
        
        if choice == '1':
            if not bot.accounts:
                print("⚠️ Erreur : Ajoutez au moins un compte dans le menu [2]")
                continue
            await bot.start_telegram()
        elif choice == '2':
            bot.list_accounts()
            print("\nOptions : [a] Ajouter | [any] Retour")
            opt = input("👉 Option : ").lower()
            if opt == 'a':
                bot.add_account()
        elif choice == '3':
            print("Fermeture du bot...")
            break

if __name__ == '__main__':
    try:
        asyncio.run(main_menu())
    except KeyboardInterrupt:
        pass
