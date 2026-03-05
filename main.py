import os
import json
import asyncio
import httpx
import re
import subprocess
import time
import requests
import threading
# Ajoute cet import en haut
from supabase import create_client, Client, ClientOptions
import uiautomator2 as u2
from dotenv import load_dotenv
from telethon import TelegramClient, events
from telethon.tl.types import MessageEntityTextUrl
from supabase import create_client, Client # Import Supabase

# ================== CONFIGURATION SUPABASE ==================
# REMPLACE CECI PAR TES INFOS SUPABASE
SUPABASE_URL = "https://kxgowljjsnlcdijcntzv.supabase.co" 
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Imt4Z293bGpqc25sY2RpamNudHp2Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzAyNzExMjQsImV4cCI6MjA4NTg0NzEyNH0.6DQsDuqMV_1_ZAXLdEZCs9qUVjEzvSz2p6ucoNoqxNs" 

# ================== COULEURS & STYLES ==================
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
CHROME_PKG_NAME = "com.android.chrome"
CHROME_ACTIVITY = "com.android.chrome/com.google.android.apps.chrome.Main"

# ================== VALEURS DES GAINS ==================
GAIN_LIKE = 1.1
GAIN_FOLLOW = 3.0

APP_CHOOSER = {
    1: "150 1800",
}
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
        self.d = None 
        self.last_sent_msg = "TikTok" 
        
        # --- SUPABASE INIT ---
        
        
        # Modifie la ligne dans ton __init__
        self.supabase: Client = create_client(
            SUPABASE_URL, 
            SUPABASE_KEY,
            options=ClientOptions(
                postgrest_client_timeout=10,
                http_client=httpx.Client(http2=False)
            )
        )
        self.user_session_file = "user_session.json"
        self.current_user = None # Stockera les infos de l'utilisateur connecté
        self.dynamic_chooser = APP_CHOOSER.copy()

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

    # ================== GESTION UTILISATEUR (SUPABASE) ==================
    def authenticate_user(self):
        """Gère la connexion et charge les coordonnées personnalisées"""
        clear_screen()
        print(f"{CYAN}🔒 AUTHENTIFICATION UTILISATEUR{RESET}")
        
        nom = ""
        password = ""
        
        if os.path.exists(self.user_session_file):
            session_data = self.load_json(self.user_session_file, {})
            nom = session_data.get("nom")
            password = session_data.get("pass")
        
        if not nom or not password:
            print(f"{WHITE}Veuillez vous connecter (Infos Database){RESET}")
            nom = input(f"{BOLD}Nom d'utilisateur : {RESET}")
            password = input(f"{BOLD}Mot de passe      : {RESET}")

        print(f"{YELLOW}🌐 Vérification auprès du serveur...{RESET}")

        try:
            # 1. Connexion Utilisateur
            response = self.supabase.table("userbot").select("*").eq("nom", nom).eq("pass", password).execute()
            
            if response.data and len(response.data) > 0:
                self.current_user = response.data[0]
                print(f"{GREEN}✅ Connexion réussie ! Bienvenue {self.current_user['nom']}.{RESET}")
                
                self.save_json(self.user_session_file, {"nom": nom, "pass": password})
                self.check_limits_strict()

                # ==========================================================
                # 2. CHARGEMENT DES COORDONNÉES (NOUVEAU CODE)
                # ==========================================================
                print(f"{CYAN}📐 Chargement de la configuration écran...{RESET}")
                user_id = self.current_user['id']
                
                conf_resp = self.supabase.table("user_config").select("coords").eq("user_id", user_id).execute()
                
                if conf_resp.data and len(conf_resp.data) > 0:
                    # Cas 1 : Config trouvée en DB
                    raw_coords = conf_resp.data[0]['coords']
                    # Conversion des clés JSON (str) en int pour le script
                    self.dynamic_chooser = {int(k): v for k, v in raw_coords.items()}
                    print(f"{GREEN}✅ Coordonnées personnalisées chargées.{RESET}")
                else:
                    # Cas 2 : Pas de config, on crée celle par défaut en DB
                    print(f"{YELLOW}⚠️ Aucune config trouvée, création des défauts...{RESET}")
                    default_coords = APP_CHOOSER # Utilise la constante globale
                    self.supabase.table("user_config").insert({
                        "user_id": user_id,
                        "coords": default_coords
                    }).execute()
                    self.dynamic_chooser = default_coords
                    print(f"{GREEN}💾 Configuration par défaut sauvegardée en DB.{RESET}")
                
                time.sleep(2)
                return True
            else:
                print(f"{RED}❌ Identifiants incorrects.{RESET}")
                if os.path.exists(self.user_session_file): os.remove(self.user_session_file)
                input("Appuyez sur Entrée...")
                return self.authenticate_user()

        except Exception as e:
            print(f"{RED}❌ Erreur DB : {e}{RESET}")
            exit()

    def check_limits_strict(self):
        """Vérifie si cashnow >= max. Si oui, bloque tout."""
        if not self.current_user: return

        cashnow = float(self.current_user['cashnow'])
        maximum = float(self.current_user['max'])

        if cashnow >= maximum:
            clear_screen()
            print(f"""
{RED}██████╗ ██╗      ██████╗  ██████╗██╗  ██╗
██╔══██╗██║     ██╔═══██╗██╔════╝██║ ██╔╝
██████╔╝██║     ██║   ██║██║     █████╔╝ 
██╔══██╗██║     ██║   ██║██║     ██╔═██╗ 
██████╔╝███████╗╚██████╔╝╚██████╗██║  ██╗
╚═════╝ ╚══════╝ ╚═════╝  ╚═════╝╚═╝  ╚═╝{RESET}
{DIM}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{RESET}
{YELLOW}⚠️  LIMITE ATTEINTE ({cashnow}/{maximum} CC){RESET}
{DIM}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{RESET}
Votre accès a été restreint car vous avez atteint
votre limite de CashCoin.

{WHITE}📞 Pour débloquer, contactez l'admin :{RESET}

👤 {CYAN}Michel Princy{RESET}
🌐 {BLUE}https://www.facebook.com/michel.princy2709/{RESET}
📱 {GREEN}+261 38 299 46 93{RESET} (WhatsApp/Telegram)
{DIM}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{RESET}
""")
            input(f"{RED}[Appuyez sur Entrée pour fermer]{RESET}")
            exit()

    def update_cashcoin(self, amount):
        """Ajoute le gain à la DB et vérifie la limite"""
        try:
            # 1. Récupérer les données fraîches pour éviter les conflits
            user_id = self.current_user['id']
            refresh = self.supabase.table("userbot").select("*").eq("id", user_id).execute()
            
            if refresh.data:
                self.current_user = refresh.data[0]
                current_cash = float(self.current_user['cashnow'])
                new_cash = current_cash + amount
                
                # 2. Mise à jour Supabase
                self.supabase.table("userbot").update({"cashnow": new_cash}).eq("id", user_id).execute()
                print(f"{MAGENTA}💾 DB Updated: {current_cash:.2f} -> {new_cash:.2f} CC{RESET}")
                
                # 3. Mettre à jour l'objet local et vérifier la limite
                self.current_user['cashnow'] = new_cash
                self.check_limits_strict()
                
        except Exception as e:
            print(f"{RED}⚠️ Erreur mise à jour DB : {e}{RESET}")

    # ================== FIN GESTION UTILISATEUR ==================

    def get_next_active_index(self):
        start_index = self.index
        for _ in range(len(self.accounts)):
            self.index = (self.index + 1) % len(self.accounts)
            current_name = self.accounts[self.index]
            if current_name not in self.paused_accounts:
                return self.index
        print(f"{RED}⚠️ ATTENTION : Tous les comptes sont en pause !{RESET}")
        return start_index 

    async def send_bot_command(self, message):
        self.last_sent_msg = message
        await self.client.send_message(TARGET_BOT, message)

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
                try:
                    if self.d is None:
                        print(f"{YELLOW}🔌 Connexion uiautomator2...{RESET}")
                        self.d = u2.connect(self.device_id)
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

    # ---------- ALARME SONORE ----------
    def play_alarm_loop(self):
        """Joue le son ET vibre en boucle"""
        print(f"{RED}{BOLD}🔊 SONNERIE ET VIBRATION ACTIVÉES !{RESET}")
        
        while self.alarm_active:
            # 1. Jouer le son avec termux-media-player (votre commande)
            if os.path.exists("alarm.mp3"):
                os.system("mpv alarm.mp3 > /dev/null 2>&1")
            else:
                os.system(f"{self.adb} input keyevent 24") # Beep volume si pas de mp3
            
            # 2. Vibreur via ADB (votre commande)
            # On lance 3 vibrations rapides
            os.system(f"{self.adb} cmd vibrator vibrate 1000")
            time.sleep(4) # Attendre que la vibration finisse
            
            # Petite pause avant de recommencer la boucle si le MP3 est court
            # Si le MP3 est long, termux-media-player rend la main tout de suite, 
            # donc on peut ajouter un sleep ici pour ne pas spammer la commande play
            time.sleep(4)
    async def trigger_manual_check(self):
        """Active le volume MEDIA max et lance la boucle de son"""
        
        # 1. Monter le volume MEDIA (Stream 3) au maximum
        # Stream 3 = Musique/Média. On le force à 15 (le max standard sur Android)
        print(f"{YELLOW}🔊 Augmentation du volume MÉDIA...{RESET}")
        
        # Méthode 1 : La plus propre (Android 10+)
        # --stream 3 cible la musique, --set 15 met le volume à fond direct
        os.system(f"{self.adb} cmd media_session volume --stream 3 --set 30")
        
        # Méthode 2 (Sécurité) : Si la commande du dessus échoue, on utilise l'ancienne méthode
        # MAIS on lance le son AVANT de monter le volume pour être sûr de cibler le média
        self.alarm_active = True
        alarm_thread = threading.Thread(target=self.play_alarm_loop)
        alarm_thread.start()
        
        # On attend un tout petit peu que le lecteur audio prenne la priorité
        await asyncio.sleep(0.5) 
        
        # Petite rafale de Volume Up au cas où le "set 15" n'a pas marché
        for _ in range(5): 
             os.system(f"{self.adb} input keyevent 24")

        # 3. Attendre l'action de l'utilisateur
        print(f"\n{RED}████████████████████████████████████████{RESET}")
        print(f"{RED}🚨  SECURITY CHECK COMPLEXE DÉTECTÉ !  🚨{RESET}")
        print(f"{YELLOW}👉 Résous le captcha sur ton téléphone.{RESET}")
        print(f"{YELLOW}👉 Une fois fini, appuie sur [ENTRÉE] ici.{RESET}")
        print(f"{RED}████████████████████████████████████████{RESET}\n")
        
        # Astuce: input() est bloquant
        await asyncio.to_thread(input, f"{BOLD}Appuie sur Entrée pour arrêter l'alarme...{RESET}")
        
        # 4. Arrêter le son et le player Termux
        self.alarm_active = False
        os.system("termux-media-player stop") # Arrêt immédiat du son
        print(f"{GREEN}✅ Alarme arrêtée. Reprise du script...{RESET}")
        alarm_thread.join()
    # ---------- ACTIONS  ----------
    async def do_task(self, account_idx, link, action, specific_text=None):
        try:
            self.cleanup_apps()
            coord_clone = self.dynamic_chooser.get(account_idx, "100 1100")
            
            # 1. Ouverture ADB
            os.system(f'{self.adb} am start -a android.intent.action.VIEW -d "{link}" > /dev/null 2>&1')
            await asyncio.sleep(4)
            os.system(f"{self.adb} input tap {coord_clone}")
            await asyncio.sleep(15) # Chargement

            # 2. Refresh
            os.system(f'{self.adb} am start -a android.intent.action.VIEW -d "{link}" > /dev/null 2>&1')
            await asyncio.sleep(3)
            os.system(f"{self.adb} input tap {coord_clone}")
            
            print(f"{YELLOW}⏳ Attente stricte 6s...{RESET}", flush=True)
            await asyncio.sleep(5)

            # --- LOGIQUE UIAUTOMATOR ---
            FOLLOW_KEYWORDS = ["Suivre", "S'abonner", "Follow", "Seguir"]
            LIKE_DESC_REGEX = "(?i)(like|j'aime|love|gostar|aimer)"
            action_lower = action.lower()
            
            # --- COMMENTAIRE ---
            if "comment" in action_lower:
                print(f"{MAGENTA}    💬 Mode Commentaire...{RESET}", flush=True)
                os.system(f"{self.adb} input tap 990 1370")
                await asyncio.sleep(3)

                if self.d(className="android.widget.EditText").exists:
                    self.d(className="android.widget.EditText").click()
                    await asyncio.sleep(1)
                    
                    text_to_send = specific_text if specific_text else "Wow super video 🔥"
                    print(f"{MAGENTA}    -> Écriture : {text_to_send}{RESET}")
                    self.d.send_keys(text_to_send)
                    await asyncio.sleep(1)

                    sent = False
                    send_btn = self.d(resourceIdMatches="(?i).*id/(send_btn|publish_button|comment_publish_img)")
                    if send_btn.exists:
                        self.d.click(978, 1320)
                        sent = True
                    
                    if not sent:
                        self.d.click(978, 1320) 
                        sent = True
                    
                    print(f"{GREEN}    -> Commentaire envoyé !{RESET}")
                    await asyncio.sleep(2)
                    os.system(f"{self.adb} input tap 500 200") 
                else:
                    print(f"{RED}    ❌ Champ texte introuvable !{RESET}")

            # --- FOLLOW ---
            if "follow" in action_lower or "profile" in action_lower:
                print(f"{CYAN}    👤 Recherche bouton Follow...{RESET}", flush=True)
                clicked = False
                for keyword in FOLLOW_KEYWORDS:
                    if self.d(textContains=keyword).exists:
                        self.d(textContains=keyword).click()
                        print(f"{GREEN}    -> Clic sur '{keyword}'{RESET}")
                        clicked = True
                        break
                
                if not clicked:
                    if self.d(resourceIdMatches=".*follow_btn.*").exists:
                         self.d(resourceIdMatches=".*follow_btn.*").click()
                         print(f"{GREEN}    -> Clic sur Follow (via ID){RESET}")
                    else:
                        print(f"{RED}    ❌ Bouton Follow introuvable{RESET}")
            
            # --- LIKE ---
            else:
                print(f"{CYAN}    ❤️  Mode Like...{RESET}", flush=True)
                self.d.click(0.5, 0.5) 
                await asyncio.sleep(0.5)
            
                liked_success = False
                if self.d(descriptionMatches=LIKE_DESC_REGEX).exists:
                    self.d(descriptionMatches=LIKE_DESC_REGEX).click()
                    liked_success = True
                elif not liked_success:
                    print(f"{MAGENTA}    🚀 Fallback : DOUBLE TAP{RESET}")
                    self.d.double_click(0.5, 0.5, duration=0.1) 
                    liked_success = True

            await asyncio.sleep(3)
            os.system(f"{self.adb} am force-stop {CLONE_CONTAINER_PACKAGE}")
            self.focus_termux()
            return True

        except Exception as e:
            print(f"Erreur Task: {e}", flush=True)
            return False

    # ---------- TELEGRAM ----------
    async def start_telegram(self):
        # Vérification DB avant de démarrer le bot
        self.check_limits_strict()

        if not self.detect_device():
            print(f"{RED}❌ ADB non détecté.{RESET}", flush=True)
            input("Appuie sur Entrée...")
            return
        
        await self.client.start()
        self.client.remove_event_handler(self.on_message)
        self.client.add_event_handler(self.on_message, events.NewMessage(chats=TARGET_BOT))
        
        if not self.accounts:
            print(f"{RED}⚠️ Aucun compte configuré !{RESET}")
            return

        current_acc = self.accounts[self.index]
        print(f"\n{BOLD}{WHITE}🚀 Démarrage sur : {CYAN}{current_acc}{RESET}", flush=True)
        
        await self.send_bot_command("TikTok") 
        await self.client.run_until_disconnected()

    async def on_message(self, event):
        text = event.message.message or ""
        buttons = event.message.buttons

        # =========================================================================
        # 🛡️ GESTION DU SECURITY CHECK 
        # =========================================================================
        if "Security check" in text and "verification" in text:
            print(f"\n{RED}{BOLD}🛡️ SECURITY CHECK DETECTÉ !{RESET}")
            # --- DETECTION DU TYPE DE CHECK ---
            # Si le texte contient "Correct answer", "emoji" ou "image", c'est le check difficile
            is_hard_check = "Correct answer" in text or "emoji" in text or "image" in text

            if is_hard_check:
                # 🚨 CAS 2 : CHALLENGE COMPLEXE -> ALARME
                await self.trigger_manual_check()
                
                # Une fois que l'utilisateur a appuyé sur Entrée :
                print(f"{CYAN}🔄 Renvoi de la dernière commande après résolution manuelle...{RESET}")
                await self.send_bot_command(self.last_sent_msg)
                return

            else:
                # 🤖 CAS 1 : CHECK SIMPLE -> AUTO-SOLVE (Ton ancien code)
                full_link = None
                if event.message.entities:
                    for entity in event.message.entities:
                        if isinstance(entity, MessageEntityTextUrl):
                            if "smmkingdom.com" in entity.url:
                                full_link = entity.url
                                break
                
                if not full_link:
                    url_match = re.search(r'(https?://smmkingdom\.com/tasker/captcha-test/\S+)', text)
                    if url_match:
                        full_link = url_match.group(1).rstrip(')')
    
                if full_link:
                    print(f"{WHITE}🔗 Lien Captcha Trouvé : {CYAN}{full_link}{RESET}")
                    print(f"{YELLOW}🌍 Ouverture Chrome...{RESET}")
                    cmd_open = f'{self.adb} am start -n {CHROME_ACTIVITY} -d "{full_link}" > /dev/null 2>&1'
                    os.system(cmd_open)
                    
                    print(f"{YELLOW}⏱️  Attente 25 secondes pour chargement...{RESET}")
                    await asyncio.sleep(25)
                    
                    print(f"{YELLOW}point_up  Tentative de clic sur le bouton de vérification...{RESET}")
                    try:
                        d = u2.connect() 
                        if d(textContains="Continue").exists(timeout=5):
                            d(textContains="Continue").click()
                            print(f"{GREEN}✅ Clic effectué sur 'Click here'{RESET}")
                        elif d(textContains="Verify").exists(timeout=2):
                            d(textContains="Verify").click()
                            print(f"{GREEN}✅ Clic effectué sur 'Verify'{RESET}")
                        elif d(className="android.widget.Button").exists(timeout=2):
                            d(className="android.widget.Button").click()
                            print(f"{GREEN}✅ Clic effectué sur un bouton générique{RESET}")
                        else:
                            print(f"{RED}⚠️ Aucun bouton détecté.{RESET}")
                        await asyncio.sleep(5)
                    except Exception as e:
                        print(f"{RED}❌ Erreur uiautomator2 : {e}{RESET}")
    
                    print(f"{YELLOW}🔒 Fermeture Chrome...{RESET}")
                    os.system(f'{self.adb} am force-stop {CHROME_PKG_NAME} > /dev/null 2>&1')
                    os.system(f"{self.adb} am kill-all > /dev/null 2>&1")
                    self.focus_termux()
                    
                    print(f"{GREEN}✅ Vérification terminée.{RESET}")
                    print(f"{CYAN}🔄 Renvoi de la dernière commande : {BOLD}{self.last_sent_msg}{RESET}")
                    await self.send_bot_command(self.last_sent_msg)
                    return
                else:
                    print(f"{RED}❌ Impossible d'extraire le lien du Security Check.{RESET}")
                    await self.send_bot_command("TikTok")
                    return

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
                
                # --- COMMENTAIRE ---
                if "comment" in action.lower():
                    await asyncio.sleep(0.5) 
                    history = await self.client.get_messages(TARGET_BOT, limit=1)
                    comment_text = history[0].message if history else None
                    if comment_text and "Link :" in comment_text:
                        comment_text = "Wow amazing video 🔥"
                    
                    success = await self.do_task(self.index + 1, full_link, action, specific_text=comment_text)

                    if success:
                        local_gain = 2.0
                        self.stats["earned"] += local_gain
                        self.stats["tasks"] += 1
                        self.save_json("stats.json", self.stats)
                        
                        # --- SUPABASE UPDATE ---
                        self.update_cashcoin(local_gain)
                        # -----------------------

                        print(f"{GREEN}✅ COMMENT TERMINE (+{local_gain}){RESET}")

                        if buttons:
                            for i, row in enumerate(buttons):
                                for j, btn in enumerate(row):
                                    if "Completed" in btn.text or "✅" in btn.text:
                                        self.last_sent_msg = btn.text
                                        print(f"{MAGENTA}💾 Sauvegarde état : {btn.text}{RESET}")
                                        await event.message.click(i, j)
                                        return

                # --- LIKE / FOLLOW ---
                else:
                    success = await self.do_task(self.index + 1, full_link, action)
                    
                    if success:
                        local_gain = GAIN_FOLLOW if ("follow" in action.lower() or "profile" in action.lower()) else GAIN_LIKE
                        self.stats["earned"] += local_gain
                        self.stats["tasks"] += 1
                        self.save_json("stats.json", self.stats)

                        # --- SUPABASE UPDATE ---
                        self.update_cashcoin(local_gain)
                        # -----------------------

                        print(f"{GREEN}✅ TASK TERMINE (+{local_gain}){RESET}")
                        print(f"{CYAN}➡️  Validation Task...{RESET}", flush=True)
                        
                        if buttons:
                            for i, row in enumerate(buttons):
                                for j, btn in enumerate(row):
                                    if "Completed" in btn.text or "✅" in btn.text:
                                        self.last_sent_msg = btn.text
                                        print(f"{MAGENTA}💾 Sauvegarde état : {btn.text}{RESET}")
                                        await event.message.click(i, j)
                                        return

        # --- 2. GESTION SUIVANTE ---
        elif "added" in text.lower() or "credited" in text.lower():
            await asyncio.sleep(4)
            self.last_sent_msg = "Tiktok"
            await self.send_bot_command("TikTok")

        # --- 3. PAS DE TASK ---
        elif "Sorry" in text or "No more" in text:
            print(f"{RED}🚫 Pas de task sur ce compte.{RESET}", flush=True)
            self.get_next_active_index()
            next_acc = self.accounts[self.index]
            
            if next_acc in self.paused_accounts:
                print(f"{RED}Tous les comptes sont en pause.{RESET}")
                await self.client.disconnect()
                return

            await asyncio.sleep(4)
            print(f"\n{WHITE}🔍 Switch vers : {CYAN}{next_acc}{RESET}", flush=True)
            self.last_sent_msg = "Tiktok"
            await self.send_bot_command("TikTok")

        # --- 4. GESTION BOUTONS COMPTE ---
        elif buttons and "Link" not in text:
            target = self.accounts[self.index]
            clicked = False
            for i, row in enumerate(buttons):
                for j, btn in enumerate(row):
                    if btn.text == target:
                        self.last_sent_msg = btn.text
                        print(f"{MAGENTA}💾 Sauvegarde état : {btn.text}{RESET}")
                        await event.message.click(i, j)
                        clicked = True
                        return
            if not clicked and "Select account" in text:
                 print(f"{RED}Compte {target} introuvable.{RESET}", flush=True)
        
        # --- 5. COMPTE A RÉPARER ---
        elif "too" in text or "warnings" in text:
            if text and len(text.strip()) > 0:
                print(f"{YELLOW}⚠️ Compte à réparer : {text}{RESET}", flush=True)
                self.get_next_active_index()
                next_acc = self.accounts[self.index]
                if next_acc in self.paused_accounts:
                    await self.client.disconnect()
                    return
                await asyncio.sleep(2)
                print(f"\n{WHITE}🔍 Switch vers : {CYAN}{next_acc}{RESET}", flush=True)
                self.last_sent_msg = "Tiktok"
                await self.send_bot_command("TikTok")

    # ---------- MENU PRINCIPAL ----------
    async def menu(self):
        # AUTHENTIFICATION OBLIGATOIRE AU DÉMARRAGE
        self.authenticate_user()

        while True:
            clear_screen()
            adb_status = f"{GREEN}CONNECTÉ{RESET}" if self.detect_device() else f"{RED}DÉCONNECTÉ{RESET}"
            acc_count = len(self.accounts)
            total_earned = self.stats.get("earned", 0.0)
            
            # Affichage de l'utilisateur connecté
            user_info = f"{CYAN}{self.current_user['nom']}{RESET}" if self.current_user else "Inconnu"
            db_cash = f"{YELLOW}{self.current_user['cashnow']}/{self.current_user['max']}{RESET}" if self.current_user else "0/0"

            print(f"""
{BLUE}███╗   ███╗██╗ ██████╗██╗  ██╗
████╗ ████║██║██╔════╝██║  ██║
██╔████╔██║██║██║     ███████║
██║╚██╔╝██║██║██║     ██╔══██║
██║ ╚═╝ ██║██║╚██████╗██║  ██║
╚═╝     ╚═╝╚═╝ ╚═════╝╚═╝  ╚═╝{RESET}
{DIM}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{RESET}
{WHITE}🤖 BOT AUTOMATION V1.3 (test) {DIM}|{RESET} {CYAN}BY MICH{RESET}
{DIM}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{RESET}
 👤 User          : {user_info}
 💳 CashCoin (DB) : {db_cash}
 📱 Status ADB    : {adb_status}
 👥 Comptes       : {WHITE}{acc_count}{RESET}
 💰 Session Local : {YELLOW}{total_earned:.1f} CC{RESET}
{DIM}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{RESET}
 {WHITE}[1]{RESET} ▶️  LANCER LE FARMING
 {WHITE}[2]{RESET} ➕  AJOUTER UN COMPTE
 {WHITE}[3]{RESET} 📋  GÉRER LES COMPTES
 {WHITE}[4]{RESET} 🔄  RE-SCAN ADB
 {WHITE}[5]{RESET} ☁️  MISE À JOUR
 {WHITE}[6]{RESET} ❌  QUITTER
{DIM}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{RESET}
""")
            choice = input(f"{BOLD}{BLUE}➜ CHOIX : {RESET}")

            if choice == "1":
                if self.accounts: 
                    self.stats["earned"] = 0.0   
                    self.stats["tasks"] = 0        
                    self.save_json("stats.json", self.stats)
                    print(f"{GREEN}💰 Compteur remis à 0 pour cette session.{RESET}")
                    await asyncio.sleep(1)
                    await self.start_telegram()
                else:
                    input(f"{RED}Ajoute un compte d'abord ! [Entrée]{RESET}")

            elif choice == "2":
                while True:
                    clear_screen()
                    print(f"{CYAN}=== ➕ AJOUT DE COMPTE ==={RESET}")
                    name = input(f"Nom du compte n°{len(self.accounts)+1} : ")
                    if not name.strip(): break
                    if name not in self.accounts:
                        self.accounts.append(name)
                        self.save_json("accounts.json", self.accounts)
                        print(f"{GREEN}✅ Compte ajouté.{RESET}")
                        await asyncio.sleep(0.5)

            elif choice == "3":
                while True: 
                    clear_screen()
                    print(f"{CYAN}=== 📋 GESTION ==={RESET}")
                    for i, acc in enumerate(self.accounts, 1):
                        status = f"{RED}[PAUSE]{RESET}" if acc in self.paused_accounts else f"{GREEN}[ACTIF]{RESET}"
                        print(f"{CYAN}{i}.{RESET} {acc} {status}")
                    print(f"\n{YELLOW}[P]{RESET} Pause/Reprendre | {RED}[S]{RESET} Supprimer | {WHITE}[Entrée]{RESET} Retour")
                    cmd = input("➜ ").lower()
                    if cmd == 'p':
                        try:
                            idx = int(input("Numéro : ")) - 1
                            target = self.accounts[idx]
                            if target in self.paused_accounts: self.paused_accounts.remove(target)
                            else: self.paused_accounts.append(target)
                            self.save_json("paused.json", self.paused_accounts)
                        except: pass
                    elif cmd == 's':
                        try:
                            idx = int(input("Numéro : ")) - 1
                            rem = self.accounts.pop(idx)
                            if rem in self.paused_accounts: self.paused_accounts.remove(rem)
                            self.save_json("accounts.json", self.accounts)
                        except: pass
                    else: break

            elif choice == "4": self.detect_device()
            elif choice == "5": self.update_script()
            elif choice == "6": break

if __name__ == "__main__":
    bot = TikTokTaskBot()
    try:
        asyncio.run(bot.menu())
    except KeyboardInterrupt:
        print("\nArrêt forcé.")
