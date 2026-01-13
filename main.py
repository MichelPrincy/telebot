import os
import json
import asyncio
import re
import time
from dotenv import load_dotenv
from telethon import TelegramClient, events

# --- CONFIGURATION TÉLÉPHONE ---
# Ton application Multi App (Vérifié via ton package précédent)
MULTI_APP_PACKAGE = "com.waxmoon.ma.gp/com.waxmoon.mobile.module.home.MainActivity"
TIKTOK_PACKAGE = "com.zhiliaoapp.musically" # Package standard TikTok (même cloné)

# Coordonnées basées sur la structure visuelle de ta photo (à ajuster selon ton écran)
COORDINATES = {
    "LIKE_BUTTON": "950 1100",   # Coordonnée du coeur sur TikTok
    "FOLLOW_BUTTON": "950 850",   # Coordonnée du bouton Suivre
    "APP_SLOTS": {
        1: "540 400",  # Centre du rectangle TikTok n°1
        2: "540 700",  # Centre du rectangle TikTok n°2
        3: "540 1000", # Centre du rectangle TikTok n°3
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

    # --- LOGIQUE D'AUTOMATISATION ADB ---
    async def run_adb_interaction(self, account_idx, link, action):
        """
        account_idx: 1, 2 ou 3 (correspond au numéro sur ta photo)
        """
        try:
            print(f"🤖 Lancement de TikTok session n°{account_idx}...")
            
            # 1. Ouvrir Multi App
            os.system(f"adb shell am start -n {MULTI_APP_PACKAGE}")
            await asyncio.sleep(3)

            # 2. Cliquer sur le bloc TikTok correspondant (1, 2 ou 3)
            pos = COORDINATES["APP_SLOTS"].get(account_idx, "540 400")
            os.system(f"adb shell input tap {pos}")
            await asyncio.sleep(6) # Attente chargement du clone

            # 3. Envoyer le lien vers l'instance TikTok ouverte
            print(f"🔗 Ouverture du lien : {link}")
            os.system(f"adb shell am start -a android.intent.action.VIEW -d {link}")
            await asyncio.sleep(7) # Attente chargement vidéo

            # 4. Action Like ou Follow
            if "Like" in action:
                os.system(f"adb shell input tap {COORDINATES['LIKE_BUTTON']}")
                print("❤️ Action : Like effectué")
            elif "Follow" in action or "Suivre" in action:
                os.system(f"adb shell input tap {COORDINATES['FOLLOW_BUTTON']}")
                print("👤 Action : Follow effectué")
            
            await asyncio.sleep(2)

            # 5. Fermer TikTok (force-stop) pour nettoyer avant la prochaine tâche
            os.system(f"adb shell am force-stop {TIKTOK_PACKAGE}")
            
            # 6. Revenir sur Termux
            os.system("adb shell am start -n com.termux/.MainActivity")
            return True # Succès
        except Exception as e:
            print(f"❌ Erreur ADB : {e}")
            return False

    async def start_telegram(self):
        print("\n--- Bot d'Interaction TikTok Lancé ---")
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

        # DETECTION DE TÂCHE
        if "Link :" in text and "Action :" in text:
            link_match = re.search(r"Link\s*:\s*(https?://[^\s\n]+)", text)
            action_match = re.search(r"Action\s*:\s*([^\n]+)", text)
            reward_match = re.search(r"Reward\s*:\s*\n?(\d+\.?\d*)", text, re.IGNORECASE)

            if link_match and action_match:
                url = link_match.group(1)
                action = action_match.group(1)
                reward_val = float(reward_match.group(1)) if reward_match else 0.0
                
                # On utilise l'index actuel + 1 pour correspondre aux chiffres 1, 2, 3 de ta photo
                account_num = self.current_account_index + 1
                current_acc_name = self.accounts[self.current_account_index]

                print(f"⚡ Tâche reçue pour {current_acc_name} (Session {account_num})")
                
                # --- AUTOMATISATION PHYSIQUE ---
                success = await self.run_adb_interaction(account_num, url, action)

                # --- VALIDATION SUR TELEGRAM ---
                # On ne clique sur "Completed" que si ADB a réussi
                if success and buttons:
                    for i, row in enumerate(buttons):
                        for j, btn in enumerate(row):
                            if "Completed" in btn.text or "✅" in btn.text:
                                print("✅ Envoi de la confirmation au bot Telegram...")
                                await event.message.click(i, j)
                                
                                # Mise à jour des stats
                                self.stats["total_earned"] += reward_val
                                self.stats["tasks_completed"] += 1
                                self.save_stats_now()
                                print(f"💰 Gain : +{reward_val} | Total : {self.stats['total_earned']:.2f}")
                                return
                else:
                    print("⚠️ Échec de l'automatisation. Pas de validation envoyée.")

        # GESTION SANS TÂCHE (SORRY)
        elif "Sorry" in text:
            print(f"😴 Pas de tâche sur : {self.accounts[self.current_account_index]}")
            self.current_account_index = (self.current_account_index + 1) % len(self.accounts)
            await asyncio.sleep(2)
            await self.client.send_message(TARGET_BOT, 'TikTok')

        # SÉLECTION DU COMPTE
        elif buttons:
            current_target = self.accounts[self.current_account_index]
            for i, row in enumerate(buttons):
                for j, btn in enumerate(row):
                    if btn.text == current_target:
                        print(f"👤 Switch vers compte : {btn.text}")
                        await event.message.click(i, j)
                        return

async def main_menu():
    bot = TaskBot()
    while True:
        print(f"\n--- MENU BOT (Solde: {bot.stats['total_earned']:.2f}) ---")
        print("[1] Lancer le cycle")
        print("[2] Ajouter un compte")
        print("[3] Quitter")
        
        choice = input("Choix : ")
        if choice == '1':
            if not bot.accounts: print("❌ Liste de comptes vide !"); continue
            await bot.start_telegram()
        elif choice == '2':
            name = input("Nom du compte (ex: ella_renk) : ")
            if name: 
                bot.accounts.append(name)
                with open('accounts.json', 'w') as f: json.dump(bot.accounts, f)
                print("✅ Ajouté")
        elif choice == '3': break

if __name__ == '__main__':
    asyncio.run(main_menu())
