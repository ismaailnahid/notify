import os
import sys
import platform
import socket
import getpass
from datetime import datetime, timedelta
import requests
import time
import json
import logging
import tempfile
import subprocess

try:
    import cv2
except ImportError:
    print("OpenCV not installed. Run: python -m pip install opencv-python")
    sys.exit(1)

try:
    import psutil
except ImportError:
    print("psutil not installed. Run: python -m pip install psutil")
    sys.exit(1)

# ---------------------------
# CONFIGURATION
# ---------------------------
TOKEN = "8375011972:AAF5NvgWpB_ERP1hqjmcrUpoMz3q8pd5JO4"
CHAT_ID = "5846327099"
CACHE_FILE = os.path.join(tempfile.gettempdir(), "pc_notifications.json")
TEMP_DIR = tempfile.gettempdir()

# Logging setup
logging.basicConfig(
    filename=os.path.join(TEMP_DIR, "pc_monitor.log"),
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

# ---------------------------
# Helper Functions
# ---------------------------

def get_network_type() -> str:
    """নেটওয়ার্ক টাইপ (Wi-Fi/Ethernet/Disconnected) রিটার্ন করে।"""
    stats = psutil.net_if_stats()
    interfaces = []
    for iface, info in stats.items():
        if info.isup:
            iface_lower = iface.lower()
            if "wi-fi" in iface_lower or "wlan" in iface_lower:
                interfaces.append("Wi-Fi")
            elif "ethernet" in iface_lower or "eth" in iface_lower:
                interfaces.append("Ethernet")
    if interfaces:
        return " & ".join(interfaces)
    return "Disconnected"

def is_internet_available():
    for url in ["https://api.telegram.org", "https://google.com"]:
        try:
            requests.get(url, timeout=5)
            return True
        except:
            continue
    return False

def get_public_ip():
    try:
        r = requests.get("https://ipinfo.io/json", timeout=5)
        data = r.json()
        ip = data.get("ip", "Unknown")
        city = data.get("city", "")
        region = data.get("region", "")
        country = data.get("country", "")
        location = f"{city}, {region}, {country}".strip(", ")
        return ip, location
    except Exception as e:
        logging.warning(f"Failed to get public IP: {e}")
        return "Unknown", "Unknown"

def get_battery_status():
    if hasattr(psutil, "sensors_battery"):
        battery = psutil.sensors_battery()
        if battery:
            percent = battery.percent
            charging = battery.power_plugged
            icon = "🔋" if percent > 80 else "⚡" if percent > 30 else "❌"
            status = "🔌 Charging" if charging else "Not Charging"
            if percent < 20 and not charging:
                status += " ⚠️ Low Battery!"
            return f"{icon} {percent}% ({status})"
    return "No Battery Info"

def get_resource_status():
    cpu = psutil.cpu_percent()
    ram = psutil.virtual_memory().percent
    status = []
    if cpu > 90:
        status.append(f"⚠️ CPU {cpu}%")
    if ram > 90:
        status.append(f"⚠️ RAM {ram}%")
    return " | ".join(status) if status else "✅ CPU/RAM Normal"

# ---------------------------
# Message Builder
# ---------------------------

def build_message(event: str):
    now = datetime.now()
    time_str = now.strftime("%I:%M:%S %p")
    date_str = now.strftime("%Y-%m-%d")
    hostname = socket.gethostname()
    user = getpass.getuser()
    system = platform.platform()
    network_type = get_network_type()
    ip, location = get_public_ip()
    battery = get_battery_status()
    resources = get_resource_status()

    # Uptime calculation
    uptime_str = ""
    if event.lower() in ["shutdown", "sleep", "hibernate", "wakeup"]:
        boot_time = datetime.fromtimestamp(psutil.boot_time())
        uptime = now - boot_time
        uptime_str = f"`Uptime:` {str(timedelta(seconds=int(uptime.total_seconds())))}"

    # Headers & Status
    headers = {
        "startup/login": "✨🟢 Welcome! PC Started or User Logged In 🟢✨",
        "shutdown": "🛑 PC Shutdown Alert 🛑",
        "sleep": "💤 PC Sleeping 💤",
        "hibernate": "🌙 PC Hibernating 🌙",
        "wakeup": "🔔 PC Woke Up 🔔",
        "default": "💻 PC Notification 💻"
    }
    header = headers.get(event.lower(), headers["default"])

    status_lines = {
        "startup/login": "🎉 আপনার কম্পিউটার চালু হয়েছে অথবা লগইন সম্পন্ন হয়েছে!\nসবকিছু ঠিকঠাক চলছে। শুভ দিন শুরু হোক! 😊",
        "shutdown": "⚠️ PC has been safely turned off.",
        "sleep": "💤 Sleep mode ON. Scheduled wake-up.",
        "hibernate": "🌙 Hibernate mode ON. Energy saving.",
        "wakeup": "🔔 PC awake and operational.",
        "default": "ℹ️ Event recorded."
    }
    status = status_lines.get(event.lower(), status_lines["default"])

    net_icon = "🌐" if network_type != "Disconnected" else "⚠️"

    message = (
        f"*{header}*\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"💡 *Quick Summary*\n"
        f"• {net_icon} Network: `{network_type}`\n"
        f"• 🔋 Battery: `{battery}`\n"
        f"• 🌍 IP: `{ip}` | Location: `{location}`\n"
        f"• 🕒 Time: `{time_str}` | 📅 Date: `{date_str}`\n\n"
        f"💻 *System Info*\n"
        f"• 🖥 Hostname: `{hostname}`\n"
        f"• 👤 User: `{user}`\n"
        f"• 🛠 OS: `{system}`\n\n"
        f"⚡ *Resource Status*\n"
        f"• {resources}\n\n"
        f"✨ *Smart Status*\n"
        f"• {status}\n"
        f"{uptime_str}\n"
        f"━━━━━━━━━━━━━━━━━━━━━━"
    )
    return message

# ---------------------------
# Telegram & Cache Functions
# ---------------------------

def save_offline(event, message, img_path):
    data = {"event": event, "message": message, "image": img_path if img_path else ""}
    cache = []
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, "r") as f:
                cache = json.load(f)
        except Exception as e:
            logging.warning(f"Cache file corrupted: {e}")
            cache = []
    cache.append(data)
    with open(CACHE_FILE, "w") as f:
        json.dump(cache, f)
    logging.info(f"Saved offline cache for event: {event}")

def send_telegram_message(message):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    try:
        r = requests.post(
            url,
            data={"chat_id": CHAT_ID, "text": message, "parse_mode": "Markdown"},
            timeout=5
        )
        if r.status_code == 200:
            return True
        else:
            logging.warning(f"Failed to send message: {r.text}")
            return False
    except Exception as e:
        logging.warning(f"Exception sending message: {e}")
        return False

def send_telegram_photo(img_path, caption):
    url = f"https://api.telegram.org/bot{TOKEN}/sendPhoto"
    try:
        with open(img_path, "rb") as img_file:
            r = requests.post(
                url,
                data={"chat_id": CHAT_ID, "caption": caption},
                files={"photo": img_file},
                timeout=5
            )
        if r.status_code == 200:
            return True
        else:
            logging.warning(f"Failed to send photo: {r.text}")
            return False
    except Exception as e:
        logging.warning(f"Exception sending photo: {e}")
        return False

def capture_photo(event):
    cap = cv2.VideoCapture(0)
    img_path = None
    if cap.isOpened():
        # Stabilize camera
        for _ in range(5):
            ret, frame = cap.read()
            time.sleep(0.1)
        ret, frame = cap.read()
        cap.release()
        if ret:
            img_path = os.path.join(TEMP_DIR, f"pc_photo_{int(time.time())}.jpg")
            cv2.putText(
                frame,
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                (10, 30),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
                (0, 255, 0),
                2
            )
            cv2.imwrite(img_path, frame)
            logging.info(f"Captured photo for event: {event}")
        else:
            logging.warning("Failed to capture photo.")
    else:
        logging.warning("Camera not available.")
    return img_path

def process_offline_cache():
    if not os.path.exists(CACHE_FILE):
        return
    if not is_internet_available():
        return
    try:
        with open(CACHE_FILE, "r") as f:
            cache = json.load(f)
    except Exception as e:
        logging.warning(f"Cache file corrupted: {e}")
        os.remove(CACHE_FILE)
        return
    remaining_cache = []
    for item in cache:
        success_msg = send_telegram_message(item["message"])
        success_photo = True
        if item["image"] and os.path.exists(item["image"]):
            success_photo = send_telegram_photo(item["image"], f"📸 {item['event']} Snapshot")
            if success_photo:
                os.remove(item["image"])
        if not (success_msg and success_photo):
            remaining_cache.append(item)
    # Save remaining cache if some items failed
    if remaining_cache:
        with open(CACHE_FILE, "w") as f:
            json.dump(remaining_cache, f)
    else:
        os.remove(CACHE_FILE)
    logging.info("Processed offline cache.")

# ---------------------------
# Package Installer
# ---------------------------

REQUIRED_PACKAGES = ["opencv-python", "psutil", "requests"]

def ensure_packages():
    import importlib
    for pkg in REQUIRED_PACKAGES:
        try:
            # opencv-python এর জন্য import cv2, বাকি গুলো নামেই ইম্পোর্ট
            mod = "cv2" if pkg == "opencv-python" else pkg
            importlib.import_module(mod)
        except ImportError:
            print(f"Installing missing package: {pkg} ...")
            subprocess.check_call([sys.executable, "-m", "pip", "install", pkg])

ensure_packages()

# ---------------------------
# Main
# ---------------------------

def main():
    event_name = sys.argv[1] if len(sys.argv) > 1 else "Startup/Login"
    message = build_message(event_name)
    img_path = capture_photo(event_name)

    if is_internet_available():
        if not send_telegram_message(message):
            save_offline(event_name, message, img_path)
        if img_path:
            if not send_telegram_photo(img_path, f"📸 {event_name} Snapshot"):
                save_offline(event_name, message, img_path)
            else:
                if os.path.exists(img_path):
                    os.remove(img_path)
    else:
        save_offline(event_name, message, img_path)

    process_offline_cache()

def print_help():
    print("Usage: python notify_runner.py [event_name]")
    print("Example: python notify_runner.py startup/login")
    sys.exit(0)

if "--help" in sys.argv or "-h" in sys.argv:
    print_help()

if __name__ == "__main__":
    main()
