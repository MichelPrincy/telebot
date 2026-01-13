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

# Configuration des logs (pour voir ce qui se passe)
logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger("BotLogger")

class TaskBot:
    def __init__(self):
        self.accounts = self.load_accounts()
        self.current_account_index = 0
        self.client = TelegramClient('session_pc', int(API_ID), API_HASH)
        self.working = False # Pour savoir si on est en mode "Start"

    # --- GESTION DES COMPTES (JSON) ---
    def load_accounts(self):
        try:
            with open('accounts.json', 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            return []

    def save_accounts(self):
        with open('accounts.json', 'w') as f:
            json.dump(self.accounts, f, indent=4)

    def add_account(self):
        name = input("Entrez le nom du compte TikTok (ex: gat_gainer) : ")
        if name:
            self.accounts.append(name)
            self.save_accounts()
            print(f"✅ Compte '{name}' ajouté !")

    def list_accounts(self):
        print("\n--- LISTE DES COMPTES TIKTOK ---")
        for i, acc in enumerate(self.accounts):
            print(f"[{i+1}] {acc}")
        print("--------------------------------")

    # --- LOGIQUE D'AUTHENTIFICATION ET DÉMARRAGE ---
    async def start_telegram(self):
        print("\n--- Connexion à Telegram ---")
        
        # .start() gère automatiquement :
        # 1. La demande du numéro si la session n'existe pas
        # 2. L'envoi du code de vérification
        # 3. La demande du mot de passe (2FA) si activé
        try:
            await self.client.start()
        except Exception as e:
            print(f"❌ Erreur lors de la connexion : {e}")
            return

        # Une fois connecté, on vérifie qui on est
        me = await self.client.get_me()
        print(f"✅ Connecté avec succès en tant que : {me.first_name} (@{me.username or 'pas de username'})")

        # On attache l'écouteur d'événements pour le bot SmmKingdom
        self.client.add_event_handler(self.message_handler, events.NewMessage(chats=TARGET_BOT))
        
        # On lance la séquence
        self.working = True
        print(f"🚀 Lancement de l'automatisation sur {TARGET_BOT}...")
        await self.trigger_main_menu()

        # On attend la déconnexion ou l'arrêt manuel
        await self.client.run_until_disconnected()

    async def trigger_main_menu(self):
        """Initie le premier contact avec le bot"""
        print("🔄 Envoi du message 'TikTok' pour démarrer la séquence...")
        try:
            await self.client.send_message(TARGET_BOT, 'TikTok')
        except Exception as e:
            print(f"⚠️ Impossible de contacter le bot : {e}")

    async def trigger_main_menu(self):
        """Fonction pour relancer le menu principal (bouton TikTok)"""
        # On essaie d'envoyer 'TikTok' pour simuler le clic du menu principal
        # Ou on envoie /start si le bot est bloqué
        print("🔄 Envoi de la commande 'TikTok'...")
        await self.client.send_message(TARGET_BOT, 'TikTok')

    async def message_handler(self, event):
        """C'est ici que toute l'intelligence se trouve"""
        if not self.working:
            return

        text = event.message.message
        buttons = event.message.buttons
        
        # --- CAS 1 : LE BOT NOUS DEMANDE DE CHOISIR UN COMPTE ---
        # On suppose que le bot nous montre la liste des comptes après avoir cliqué sur "TikTok"
        # On doit trouver le bouton qui correspond à notre compte actuel
        if self.accounts and any(self.accounts[self.current_account_index] in str(row) for row in (buttons or [])):
            
            target_account = self.accounts[self.current_account_index]
            print(f"👉 Sélection du compte : {target_account}")
            
            # Chercher et cliquer sur le bouton du compte
            found = False
            if buttons:
                for i, row in enumerate(buttons):
                    for j, btn in enumerate(row):
                        if btn.text == target_account:
                            await asyncio.sleep(1.5) # Pause humaine
                            await event.message.click(i, j)
                            found = True
                            break
                    if found: break
            
            if not found:
                print(f"⚠️ Bouton pour {target_account} non trouvé !")

        # --- CAS 2 : PAS DE TACHE (SORRY) ---
        elif "Sorry" in text:
            print(f"❌ Pas de tâche pour : {self.accounts[self.current_account_index]}")
            
            # On passe au compte suivant
            self.current_account_index += 1
            
            # Si on a fait tous les comptes, on recommence à 0
            if self.current_account_index >= len(self.accounts):
                print("--- Tous les comptes vérifiés, retour au premier ---")
                self.current_account_index = 0
                await asyncio.sleep(5) # Pause plus longue avant de refaire le tour
            
            # Le prompt dit : "le bot reaffiche automatiquement les 3 boutons"
            # Donc on attend juste de voir le bouton "TikTok" revenir, ou on force le clic
            # Si le bot ne réaffiche pas tout seul, on peut décommenter la ligne suivante :
            # await self.client.send_message(TARGET_BOT, 'TikTok')
            
            # NOTE: Si le bot réaffiche le menu principal automatiquement, 
            # le script va détecter le bouton "TikTok" dans le prochain message et cliquer dessus ? 
            # Non, on doit explicitement cliquer sur TikTok si on voit le menu principal.

        # --- CAS 3 : LE MENU PRINCIPAL (Instagram, TikTok, Back) ---
        elif buttons and any("TikTok" in btn.text for row in buttons for btn in row):
            # C'est le menu principal, on clique sur TikTok pour lancer la liste
            print("🔘 Menu principal détecté. Clic sur 'TikTok'...")
            await asyncio.sleep(1)
            # Trouver le bouton TikTok
            for i, row in enumerate(buttons):
                for j, btn in enumerate(row):
                    if "TikTok" in btn.text:
                        await event.message.click(i, j)
                        return

        # --- CAS 4 : TACHE TROUVÉE (LINK + ACTION) ---
        elif "Link:" in text and "Action:" in text:
            # Afficher tout le message
            print(f"\n📄 Message complet reçu :\n{text}\n")
            
            # Détecter le type (Like ou Follow)
            action_type = "Inconnu"
            if "Like" in text: action_type = "Like"
            elif "Follow" in text: action_type = "Follow"
            
            print(f"✅ Tache trouver type: {action_type}")
            
            # Chercher le bouton "Completed"
            if buttons:
                for i, row in enumerate(buttons):
                    for j, btn in enumerate(row):
                        # Adaptez le texte si c'est "Completed", "Done", "Check", etc.
                        if "Completed" in btn.text or "✅" in btn.text:
                            print("👆 Clic sur 'Completed'...")
                            await asyncio.sleep(2) # IMPORTANT : Délai pour simuler qu'on fait la tache
                            await event.message.click(i, j)
                            return

# --- MENU PRINCIPAL (CLI) ---
async def main_menu():
    bot = TaskBot()
    
    while True:
        print("\n=== MENU PRINCIPAL ===")
        print("[1] Démarrer le Bot")
        print("[2] Liste des comptes (Ajouter/Voir)")
        print("[3] Exit")
        
        choice = input("Choix : ")
        
        if choice == '1':
            if not bot.accounts:
                print("⚠️ Aucun compte enregistré ! Allez dans le menu 2.")
                continue
            
            print("🚀 Démarrage... (CTRL+C pour arrêter)")
            bot.working = True
            try:
                await bot.start_telegram()
            except KeyboardInterrupt:
                print("\nArrêt du bot.")
                bot.working = False
            except Exception as e:
                print(f"Erreur: {e}")

        elif choice == '2':
            while True:
                bot.list_accounts()
                print("a: Ajouter un compte | r: Retour")
                sub = input("Choix : ")
                if sub == 'a':
                    bot.add_account()
                elif sub == 'r':
                    break
        
        elif choice == '3':
            print("Bye !")
            break
        else:
            print("Choix invalide.")

if __name__ == '__main__':
    asyncio.run(main_menu())