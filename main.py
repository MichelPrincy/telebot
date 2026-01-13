import os
import json
import asyncio
import logging
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
        
        # 1. CAS : TACHE TROUVÉE (Priorité haute)
        if "Link:" in text and "Action:" in text:
            print(f"\n🎯 TACHE TROUVÉE !")
            print(f"📝 Type: {'Like' if 'Like' in text else 'Follow' if 'Follow' in text else 'Autre'}")
            
            if buttons:
                for i, row in enumerate(buttons):
                    for j, btn in enumerate(row):
                        if "Completed" in btn.text or "✅" in btn.text:
                            print("👆 Clic sur 'Completed'...")
                            await asyncio.sleep(3) # Pause pour simuler l'action
                            await event.message.click(i, j)
                            return

        # 2. CAS : PAS DE TACHE (SORRY)
        elif "Sorry" in text:
            print(f"❌ Pas de tâche pour le compte actuel.")
            self.current_account_index += 1
            
            if self.current_account_index >= len(self.accounts):
                print("🔄 Tous les comptes ont été vérifiés. On recommence dans 10s...")
                self.current_account_index = 0
                await asyncio.sleep(10)
            
            # Après un "Sorry", on doit retourner au menu TikTok pour changer de compte
            await asyncio.sleep(2)
            await self.send_tiktok_command()

        # 3. CAS : LISTE DES COMPTES (Détecter si nos boutons de comptes sont là)
        elif buttons:
            current_target = self.accounts[self.current_account_index]
            found_account_btn = False
            is_main_menu = False

            for i, row in enumerate(buttons):
                for j, btn in enumerate(row):
                    # Est-ce le bouton de mon compte TikTok actuel ?
                    if btn.text == current_target:
                        print(f"👤 Compte trouvé dans la liste : {btn.text}. Clic...")
                        await asyncio.sleep(1.5)
                        await event.message.click(i, j)
                        return
                    
                    # Est-ce le menu principal (au cas où le bot réaffiche TikTok/Instagram)
                    if "TikTok" in btn.text:
                        is_main_menu = True

            if is_main_menu:
                print("🏠 Menu principal détecté. Clic sur 'TikTok'...")
                await asyncio.sleep(1)
                await self.send_tiktok_command()

    # --- MÉTHODES MENU ---
    def add_account(self):
        name = input("Nom du compte TikTok (ex: gat_gainer) : ")
        if name:
            self.accounts.append(name)
            self.save_accounts()
            print("✅ Ajouté.")

    def list_accounts(self):
        print("\n--- COMPTES ENREGISTRÉS ---")
        for i, acc in enumerate(self.accounts): print(f"[{i}] {acc}")

async def main_menu():
    bot = TaskBot()
    while True:
        print("\n=== BOT SMM KINGDOM ===")
        print("[1] Démarrer l'Automatisation")
        print("[2] Gérer les comptes TikTok")
        print("[3] Quitter")
        c = input("Choix : ")
        if c == '1':
            if not bot.accounts: print("❌ Ajoutez des comptes d'abord !"); continue
            await bot.start_telegram()
        elif c == '2':
            bot.list_accounts()
            if input("Tapez 'a' pour ajouter ou 'Entrée' pour retour : ") == 'a': bot.add_account()
        elif c == '3': break

if __name__ == '__main__':
    asyncio.run(main_menu())
