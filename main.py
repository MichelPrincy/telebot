import os
import json
import asyncio
import re
import subprocess
import time
import cv2
import requests
import uiautomator2 as u2  # <--- NOUVEL IMPORT
from dotenv import load_dotenv
from telethon import TelegramClient, events
from telethon.tl.types import MessageEntityTextUrl

# ================== COULEURS & STYLES (DESIGN) ==================
RED = "\033[91m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
CYAN = "\033[96m"
MAGENTA = "\033[95m"
WHITE = "\033[97m"
BOLD = "\033[1m"
DIM = "\033[2m"
RESET = "\033[0m"

# ================== PACKAGES ==================
CLONE_CONTAINER_PACKAGE = "com.waxmoon.ma.gp"
TERMUX_PACKAGE = "com.termux/com.termux.app.TermuxActivity"

# ================== VALEURS DES GAINS ==================
GAIN_LIKE = 1.1
GAIN_FOLLOW = 3.0

# ================== COORDONNÉES (ADB FALLBACK) ==================
APP_CHOOSER = {
    1: "150 1800", 2: "350 1800", 3: "530 1800", 4: "740 1800",
    5: "930 1800", 6: "150 2015", 7: "340 2015", 8: "530 2015",
}
FOLLOW_BUTTON = "180 547"
# On garde les coordonnées pour le refresh manuel si besoin
SWIPE_REFRESH = "900 450 900 980 500"

# ================== TELEGRAM ==================
API_ID = 21426921
API_HASH = "07a304c39fc55aca132175b1dce4ad55"
TARGET_BOT = "@SmmKingdomTasksBot"

# ================== UTILS ==================
def clear_screen():
    os.system("clear")

class TikTokTaskBot:
    
    def __init__(self):
        self.accounts = self.load_json("accounts.json", [])
        self.paused_accounts = self.load_json("paused.json", [])
        self.stats = self.load_json("stats.json", {"earned": 0.0, "tasks": 0})
        self.index = 0
        self.device_id = None
        self.adb = "adb shell"
        self.client = TelegramClient("session_bot", API_ID, API_HASH)
        self.d = None # Instance uiautomator2

    def load_json(self, file, default):
        if os.path.exists(file):
            try:
                with open(file, "r") as f:
                    return json.load(f)
            except: return default
        return default

    def save_json(self, file, data):
        with open(file, "w") as f:
            json.dump(data, f, indent=4)

    def get_next_active_index(self):
        start_index = self.index
        for _ in range(len(self.accounts)):
            self.index = (self.index + 1) % len(self.accounts)
            current_name = self.accounts[self.index]
            if current_name not in self.paused_accounts:
                return self.index
        print(f"{RED}⚠️ ATTENTION : Tous les comptes sont en pause !{RESET}")
        return start_index 

     # ---------- MISE À JOUR ----------
    def update_script(self):
        print(f"{CYAN}🌐 Vérification mise à jour...{RESET}", flush=True)
        url = "https://raw.githubusercontent.com/MichelPrincy/telebot/main/main.py"
        try:
            response = requests.get(url)
            if response.status_code == 200:
                with open("main.py", "w") as f:
                    f.write(response.text)
                print(f"{GREEN}✅ Mise à jour installée.{RESET}", flush=True)
                exit()
        except Exception: pass

    # ---------- ADB & UIAUTOMATOR ----------
    def detect_device(self):
        try:
            out = subprocess.check_output(["adb", "devices"]).decode()
            found = False
            for line in out.splitlines():
                if "\tdevice" in line:
                    self.device_id = line.split("\t")[0]
                    self.adb = f"adb -s {self.device_id} shell"
                    found = True
                    break
            
            if found:
                # Connexion Uiautomator2
                try:
                    print(f"{YELLOW}🔌 Connexion uiautomator2...{RESET}")
                    self.d = u2.connect(self.device_id)
                    # Optionnel: Accélère u2
                    self.d.implicitly_wait(10.0) 
                    self.d.settings['operation_delay'] = (0.2, 0.2)
                    print(f"{GREEN}✅ Uiautomator2 Connecté!{RESET}")
                except Exception as e:
                    print(f"{RED}Erreur connexion U2: {e}{RESET}")
                return True
            return False
        except: return False

    def cleanup_apps(self):
        os.system(f"{self.adb} am force-stop {CLONE_CONTAINER_PACKAGE} > /dev/null 2>&1")
        os.system(f"{self.adb} am kill-all > /dev/null 2>&1")

    def focus_termux(self):
        os.system(f"{self.adb} am start --activity-brought-to-front {TERMUX_PACKAGE} > /dev/null 2>&1")

    # ---------- ACTIONS TIKTOK (HYBRIDE ADB + U2) ----------
    async def do_task(self, account_idx, link, action):
        try:
            self.cleanup_apps()
            coord_clone = APP_CHOOSER.get(account_idx, "100 1100")
            
            # 1. Ouverture ADB (Classique)
            os.system(f'{self.adb} am start -a android.intent.action.VIEW -d "{link}" > /dev/null 2>&1')
            await asyncio.sleep(5)
            os.system(f"{self.adb} input tap {coord_clone}")
            await asyncio.sleep(30) # Temps de chargement

            # 2. Réouverture / Refresh ADB (Classique)
            os.system(f'{self.adb} am start -a android.intent.action.VIEW -d "{link}" > /dev/null 2>&1')
            await asyncio.sleep(5)
            os.system(f"{self.adb} input tap {coord_clone}")
            
            print(f"{YELLOW}⏳ Attente stricte 10s...{RESET}", flush=True)
            await asyncio.sleep(10)

            # ================== UIAUTOMATOR2 LOGIC ==================
            action_lower = action.lower()

            # --- CAS FOLLOW ---
            if "follow" in action_lower or "profile" in action_lower:
                print(f"{CYAN}   👤 Recherche bouton Follow (U2)...{RESET}", flush=True)
                
                # Swipe léger pour être sûr d'être actif (optionnel)
                os.system(f"{self.adb} input swipe {SWIPE_REFRESH}")
                await asyncio.sleep(2)

                # Recherche intelligente du texte
                # On cherche un bouton qui contient "Follow" ou "Suivre"
                if self.d(text="Follow").exists:
                    self.d(text="Follow").click()
                    print(f"{GREEN}   -> Clic sur 'Follow'{RESET}")
                elif self.d(text="Suivre").exists:
                    self.d(text="Suivre").click()
                    print(f"{GREEN}   -> Clic sur 'Suivre'{RESET}")
                # Parfois c'est juste un bouton rouge avec du texte
                elif self.d(textContains="Follow").exists:
                    self.d(textContains="Follow").click()
                else:
                    print(f"{RED}   ❌ Bouton Follow introuvable !{RESET}")
                    # Fallback ADB si échec U2 (Ta coordonnée originale)
                    # os.system(f"{self.adb} input tap 240 800")

            else:
                print(f"{CYAN}   ❤️  Mode Like (U2)...{RESET}", flush=True)
                
                # 1. PAUSE (Clic au centre)
                self.d.click(0.5, 0.5) 
                print(f"{DIM}   -> Vidéo mise en pause{RESET}")
                await asyncio.sleep(1)

                # 2. CHERCHER LE COEUR BLANC
                # Le bouton Like a souvent la description "Like video" (J'aime) quand il n'est pas activé
                # S'il est déjà liké, la description change souvent (ex: "Undo like")
                
                # Essai par Description (Le plus fiable pour les icônes sans texte)
                if self.d(descriptionContains="Like").exists:
                    self.d(descriptionContains="Like").click()
                    print(f"{GREEN}   -> Clic sur l'icône Like (Desc){RESET}")
                
                # Essai par Resource ID (Plus risqué car change souvent)
                elif self.d(resourceId="com.zhiliaoapp.musically:id/b_o").exists: # ID exemple
                    self.d(resourceId="com.zhiliaoapp.musically:id/b_o").click()
                
                # Essai générique U2 si l'image est détectée (avancé) ou fallback ADB
                else:
                    print(f"{YELLOW}   ⚠️ Cœur U2 non détecté, tentative ADB...{RESET}")
                    os.system(f"{self.adb} input tap 990 1200") # Ta coordonnée originale en secours

            await asyncio.sleep(3)
            os.system(f"{self.adb} am force-stop {CLONE_CONTAINER_PACKAGE}")
            self.focus_termux()
            return True

        except Exception as e:
            print(f"Erreur Task: {e}", flush=True)
            return False

    # ---------- TELEGRAM ----------
    async def start_telegram(self):
        if not self.detect_device():
            print(f"{RED}❌ ADB non détecté. Vérifie ta connexion USB/Wifi.{RESET}", flush=True)
            input("Appuie sur Entrée pour revenir au menu...")
            return
        
        await self.client.start()
        # --- CORRECTION ICI ---
        self.client.remove_event_handler(self.on_message)
        self.client.add_event_handler(self.on_message, events.NewMessage(chats=TARGET_BOT))
        # ----------------------
        
        if not self.accounts:
            print(f"{RED}⚠️ Aucun compte configuré !{RESET}", flush=True)
            return
        if self.accounts[self.index] in self.paused_accounts:
            print(f"{YELLOW}Le compte actuel est en pause, recherche du suivant...{RESET}")
            self.get_next_active_index()

        current_acc = self.accounts[self.index]
        print(f"\n{BOLD}{WHITE}🚀 Démarrage sur le compte : {CYAN}{current_acc}{RESET}", flush=True)
        await self.client.send_message(TARGET_BOT, "TikTok")
        await self.client.run_until_disconnected()

    async def on_message(self, event):
        text = event.message.message or ""
        buttons = event.message.buttons

        # --- 1. DETECTION DE TÂCHE ---
        if "Link :" in text and "Action :" in text:
            full_link = None
            if event.message.entities:
                for entity in event.message.entities:
                    if isinstance(entity, MessageEntityTextUrl):
                        full_link = entity.url
                        break
            if not full_link:
                match = re.search(r"Link\s*:\s*(https?://\S+)", text)
                if match: full_link = match.group(1)

            if full_link:
                action = re.search(r"Action\s*:\s*(.+)", text).group(1)
                
                print(f"\n{DIM}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{RESET}", flush=True)
                print(f"{WHITE}🔗 Task: {BOLD}{action}{RESET}", flush=True)
                
                # --- CAS COMMENTAIRE (On skip) ---
                if "comment" in action.lower():
                    print(f"{MAGENTA}💬 Commentaire détecté : {RED}SKIPPED (Pas de gain){RESET}", flush=True)
                    await asyncio.sleep(2)
                    if buttons:
                        for i, row in enumerate(buttons):
                            for j, btn in enumerate(row):
                                if "Completed" in btn.text or "✅" in btn.text:
                                    await event.message.click(i, j)
                                    return
                    return

                # --- CAS LIKE / FOLLOW ---
                else:
                    print(f"{YELLOW}⏳ Exécution en cours sur le téléphone...{RESET}", flush=True)
                    
                    success = await self.do_task(self.index + 1, full_link, action)
                    
                    if success:
                        # 1. DETERMINER LE GAIN LOCALEMENT
                        local_gain = 0.0
                        if "follow" in action.lower() or "profile" in action.lower():
                            local_gain = GAIN_FOLLOW
                            action_name = "👤 FOLLOW"
                        else:
                            local_gain = GAIN_LIKE
                            action_name = "❤️ LIKE"

                        # 2. MISE A JOUR DES STATS
                        old_balance = self.stats["earned"]
                        new_balance = old_balance + local_gain
                        self.stats["earned"] = new_balance
                        self.stats["tasks"] += 1
                        self.save_json("stats.json", self.stats)

                        # 3. AFFICHAGE DU COMPTAGE
                        print(f"{GREEN}✅ {action_name} TERMINE{RESET}", flush=True)
                        print(
                            f"{MAGENTA}💰 SOLDE: {old_balance:.1f} + "
                            f"{local_gain:.1f} = {BOLD}{new_balance:.1f} CC{RESET}",
                            flush=True
                        )

                        # 4. ENVOI DU BOUTON COMPLETE
                        print(f"{CYAN}➡️  Validation Task...{RESET}", flush=True)
                        
                        if buttons:
                            for i, row in enumerate(buttons):
                                for j, btn in enumerate(row):
                                    if "Completed" in btn.text or "✅" in btn.text:
                                        await event.message.click(i, j)
                                        return

        # --- 2. GESTION SUIVANTE (On ignore "added" pour le comptage) ---
        elif "added" in text.lower() or "credited" in text.lower():
            # Juste pour le délai humain, on n'ajoute rien ici car déjà fait
            await asyncio.sleep(2)
            await self.client.send_message(TARGET_BOT, "TikTok")

        # --- 3. PAS DE TASK ---
        elif "Sorry" in text or "No more" in text:
            print(f"{RED}🚫 Pas de task sur ce compte.{RESET}", flush=True)
            
            self.get_next_active_index()

            next_acc = self.accounts[self.index]
            
            # Vérification de sécurité si tout est en pause
            if next_acc in self.paused_accounts:
                print(f"{RED}Tous les comptes sont en pause. Arrêt temporaire.{RESET}")
                await self.client.disconnect()
                return

            await asyncio.sleep(2)
            print(f"\n{WHITE}🔍 Switch vers : {CYAN}{next_acc}{RESET}", flush=True)
            await self.client.send_message(TARGET_BOT, "TikTok")

        # --- 4. GESTION BOUTONS COMPTE ---
        elif buttons and "Link" not in text:
            target = self.accounts[self.index]
            clicked = False
            for i, row in enumerate(buttons):
                for j, btn in enumerate(row):
                    if btn.text == target:
                        await event.message.click(i, j)
                        clicked = True
                        return
            if not clicked and "Select account" in text:
                 print(f"{RED}Compte {target} introuvable dans le menu bot.{RESET}", flush=True)
        
        # --- 5. COMPTE A RÉPARER ---
        elif "too" in text or "warnings" in text:
            if text and len(text.strip()) > 0:
                print(f"{YELLOW}⚠️ Ce compte a besoin d'être réparé : {text}{RESET}", flush=True)

    # ---------- MENU PRINCIPAL ----------
    async def menu(self):
        while True:
            clear_screen()
            adb_status = f"{GREEN}CONNECTÉ{RESET}" if self.detect_device() else f"{RED}DÉCONNECTÉ{RESET}"
            acc_count = len(self.accounts)
            total_earned = self.stats.get("earned", 0.0)

            print(f"""
{BLUE}███╗   ███╗██╗ ██████╗██╗  ██╗
████╗ ████║██║██╔════╝██║  ██║
██╔████╔██║██║██║     ███████║
██║╚██╔╝██║██║██║     ██╔══██║
██║ ╚═╝ ██║██║╚██████╗██║  ██║
╚═╝     ╚═╝╚═╝ ╚═════╝╚═╝  ╚═╝{RESET}
{DIM}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{RESET}
{WHITE}🤖 BOT AUTOMATION V3.2.2 {DIM}|{RESET} {CYAN}BY MICH{RESET}
{DIM}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{RESET}
 📱 Status ADB    : {adb_status}
 👥 Comptes        : {WHITE}{acc_count}{RESET}
 💰 Total Gagné    : {YELLOW}{total_earned:.1f} CashCoins{RESET}
{DIM}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{RESET}
 {WHITE}[1]{RESET} ▶️  LANCER LE FARMING
 {WHITE}[2]{RESET} ➕  AJOUTER UN COMPTE
 {WHITE}[3]{RESET} 📋  GÉRER LES COMPTES
 {WHITE}[4]{RESET} 🔄  RE-SCAN ADB
 {WHITE}[5]{RESET} ☁️  MISE À JOUR
 {WHITE}[6]{RESET} ❌  QUITTER
{DIM}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{RESET}
""", flush=True)
            choice = input(f"{BOLD}{BLUE}➜ CHOIX : {RESET}")

            if choice == "1":
                if self.accounts: 
                    # --- DEBUT MODIFICATION ---
                    self.stats["earned"] = 0.0   # Remet les gains à 0
                    self.stats["tasks"] = 0      # (Optionnel) Remet aussi le compteur de tâches à 0
                    self.save_json("stats.json", self.stats) # Sauvegarde la remise à zéro
                    print(f"{GREEN}💰 Compteur remis à 0 pour cette session.{RESET}")
                    await asyncio.sleep(1)
                    # --- FIN MODIFICATION ---
                    
                    await self.start_telegram()
                else:
                    input(f"{RED}Ajoute au moins un compte d'abord ! [Entrée]{RESET}")

            elif choice == "2":
                while True:
                    clear_screen()
                    print(f"{CYAN}=== ➕ AJOUT DE COMPTE ==={RESET}", flush=True)
                    print(f"{DIM}Entrée vide pour retour.{RESET}\n", flush=True)
                    
                    name = input(f"Nom du compte n°{len(self.accounts)+1} : ")
                    if not name.strip(): break
                    
                    if name in self.accounts:
                        print(f"{RED}Ce compte existe déjà !{RESET}", flush=True)
                        await asyncio.sleep(1)
                    else:
                        self.accounts.append(name)
                        self.save_json("accounts.json", self.accounts)
                        print(f"{GREEN}✅ Compte ajouté.{RESET}", flush=True)
                        await asyncio.sleep(0.5)

            elif choice == "3":
                while True: 
                    clear_screen()
                    print(f"{CYAN}=== 📋 GESTION DES COMPTES ==={RESET}", flush=True)
                    
                    # Affichage avec statut
                    for i, acc in enumerate(self.accounts, 1):
                        status = f"{RED}[PAUSE]{RESET}" if acc in self.paused_accounts else f"{GREEN}[ACTIF]{RESET}"
                        print(f"{CYAN}{i}.{RESET} {acc} {status}", flush=True)
                    
                    print(f"\n{YELLOW}[P]{RESET} Pause/Reprendre | {RED}[S]{RESET} Supprimer | {WHITE}[Entrée]{RESET} Retour", flush=True)
                    cmd = input("➜ ").lower()

                    if cmd == 'p':
                        try:
                            idx = int(input("Numéro du compte à modifier : ")) - 1
                            if 0 <= idx < len(self.accounts):
                                target = self.accounts[idx]
                                if target in self.paused_accounts:
                                    self.paused_accounts.remove(target) # On retire de la pause
                                else:
                                    self.paused_accounts.append(target) # On ajoute en pause
                                
                                self.save_json("paused.json", self.paused_accounts)
                        except: pass
                    
                    elif cmd == 's':
                        try:
                            idx = int(input("Numéro à supprimer : ")) - 1
                            if 0 <= idx < len(self.accounts):
                                removed = self.accounts.pop(idx)
                                # Nettoyage si le compte était en pause
                                if removed in self.paused_accounts:
                                    self.paused_accounts.remove(removed)
                                    self.save_json("paused.json", self.paused_accounts)
                                self.save_json("accounts.json", self.accounts)
                        except: pass
                    
                    else:
                        break # Sortir du menu gestion

            elif choice == "4":
                self.detect_device()
            elif choice == "5":
                self.update_script()
            elif choice == "6":
                print(f"{CYAN}Bye !{RESET}", flush=True)
                break

if __name__ == "__main__":
    bot = TikTokTaskBot()
    try:
        asyncio.run(bot.menu())
    except KeyboardInterrupt:
        print("\nArrêt forcé.", flush=True)
