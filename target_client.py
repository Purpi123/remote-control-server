import time
import requests
import socket
import uuid
import ctypes
import json
import threading # Import threading module
import win32gui
import win32con
import psutil # Import psutil for system information
import wmi # For checking Windows Defender status
import win32security # For checking admin privileges
import win32api # Import win32api for monitor info
import mss # For screen capturing
import io # For handling byte streams
from PIL import Image
from plyer import notification # Import notification from plyer
from base64 import b64decode, b64encode # Import b64decode and b64encode for image data
import os # Import os for file operations
import tempfile # Import tempfile for temporary file handling
import threading # Import threading for delayed file deletion
import win32process # Import win32process for window enumeration
from pynput import keyboard, mouse # Import pynput for idle time tracking
import platform # Import platform module
import getpass # Import getpass for password related functionality (conceptual)
import base64 # Import base64 for image encoding
import imghdr # Import imghdr to guess image file types

SERVER_URL = "https://remote-control-server-1kt8.onrender.com"

# Function to set desktop background
def set_desktop_background(image_base64):
    try:
        # Decode the base64 image data
        image_data = b64decode(image_base64)
        
        # Create a temporary file to save the image
        temp_dir = tempfile.gettempdir()
        temp_image_path = os.path.join(temp_dir, f"background_{uuid.uuid4()}.bmp") # BMP is often safest for wallpaper
        
        with open(temp_image_path, 'wb') as f:
            f.write(image_data)

        # Set the wallpaper using SystemParametersInfo
        # SPI_SETDESKWALLPAPER = 0x0014
        # SPIF_UPDATEINIFILE = 0x01 (write to Win.ini)
        # SPIF_SENDCHANGE = 0x02 (send WM_SETTINGCHANGE message)
        ctypes.windll.user32.SystemParametersInfoW(0x0014, 0, temp_image_path, 0x01 | 0x02)
        
        print(f"🖼️ Desktop background changed to {temp_image_path}")
        
        # Schedule temporary file for deletion after a short delay
        threading.Timer(5, os.remove, args=[temp_image_path]).start()
        return True
    except Exception as e:
        print(f"❌ Error setting desktop background: {e}")
        return False

# MessageBoxW icon constants
MB_OK = 0x00000000 # OK button only
MB_ICONERROR = 0x00000010 # Error icon
MB_ICONQUESTION = 0x00000020 # Question mark icon
MB_ICONWARNING = 0x00000030 # Exclamation point icon
MB_ICONINFORMATION = 0x00000040 # Asterisk icon (Info)

# MessageBoxW Topmost constant
MB_TOPMOST = 0x00040000 # Message box is created as a topmost window

# Mapping for icon strings to MessageBoxW flags
ICON_MAP = {
    "info": MB_ICONINFORMATION,
    "warning": MB_ICONWARNING,
    "error": MB_ICONERROR
}

# MessageBoxW button constants
MB_OKCANCEL = 0x00000001
MB_ABORTRETRYIGNORE = 0x00000002
MB_YESNOCANCEL = 0x00000003
MB_YESNO = 0x00000004
MB_RETRYCANCEL = 0x00000005

# Mapping for button strings to MessageBoxW flags
BUTTON_MAP = {
    "ok": MB_OK,
    "okcancel": MB_OKCANCEL,
    "abortretryignore": MB_ABORTRETRYIGNORE,
    "yesnocancel": MB_YESNOCANCEL,
    "yesno": MB_YESNO,
    "retrycancel": MB_RETRYCANCEL
}

# Generera unikt klient-ID en gång
client_id = str(uuid.uuid4())

# Global variables for streaming
_is_streaming_active = False
_stream_thread = None
_selected_monitor_index = 1 # Default to primary monitor or the first available screen

# Global variables for active window tracking
_current_active_window_title = None
_active_window_start_time = None # Timestamp when the current active window became active

# Global variable for idle time tracking
_last_activity_time = time.time()

# List of common system/background process names to exclude
EXCLUDED_PROCESSES = [
    "svchost.exe", "csrss.exe", "wininit.exe", "dwm.exe", "smss.exe",
    "lsass.exe", "services.exe", "winlogon.exe", "explorer.exe", # Explorer can be an app but often runs in background
    "System Idle Process", "System", "Registry", "Mem Compression",
    "RuntimeBroker.exe", "WUDFHost.exe", "audiodg.exe", "spoolsv.exe",
    "SearchIndexer.exe", "SearchHost.exe", "SettingSyncHost.exe", "dllhost.exe",
    "conhost.exe", "fontdrvhost.exe", "taskhostw.exe", "WmiPrvSE.exe",
    "ApplicationFrameHost.exe", "SecurityHealthService.exe", "NisSrv.exe",
    "MsMpEng.exe", "msdtc.exe", # Windows Defender processes
    "python.exe", "py.exe", "pyw.exe", # Exclude self
    "TextInputHost.exe", # Exclude TextInputHost
    "NVIDIA Share.exe", "NVIDIA Web Helper.exe", "NVIDIA Container.exe" # Exclude common NVIDIA Overlay processes
]

def get_ip():
    try:
        return socket.gethostbyname(socket.gethostname())
    except:
        return "unknown"

# Function to get the current desktop wallpaper path
def get_desktop_wallpaper_path():
    try:
        # SPI_GETDESKWALLPAPER = 0x0073
        # Buffer size for path (MAX_PATH = 260)
        path_buffer = ctypes.create_unicode_buffer(260)
        ctypes.windll.user32.SystemParametersInfoW(0x0073, 260, path_buffer, 0)
        return path_buffer.value
    except Exception as e:
        print(f"❌ Error getting desktop wallpaper path: {e}")
        return None

# Function to get desktop background as base64
def get_desktop_background_base64():
    wallpaper_path = get_desktop_wallpaper_path()
    if wallpaper_path and os.path.exists(wallpaper_path):
        try:
            with open(wallpaper_path, 'rb') as f:
                image_data = f.read()
            
            # Determine image type
            img_type = imghdr.what(None, h=image_data) # Guess image type from bytes
            mime_type = 'application/octet-stream' # Default to generic

            if img_type:
                # Common types imghdr recognizes
                if img_type == 'jpeg':
                    mime_type = 'image/jpeg'
                elif img_type == 'png':
                    mime_type = 'image/png'
                elif img_type == 'gif':
                    mime_type = 'image/gif'
                elif img_type == 'bmp':
                    mime_type = 'image/bmp'
                # Add other types if necessary
            else:
                print(f"⚠️ Could not determine image type for {wallpaper_path}. Defaulting to generic MIME type.")

            encoded_image = base64.b64encode(image_data).decode('utf-8')
            return {"data": encoded_image, "type": mime_type}
        except Exception as e:
            print(f"❌ Error reading or encoding background image: {e}")
            return None
    return None

def _has_visible_window(pid):
    """Checks if a process has any visible windows."""
    def callback(hwnd, hwnds):
        if win32gui.IsWindowVisible(hwnd) and win32gui.GetWindowText(hwnd):
            _, found_pid = win32process.GetWindowThreadProcessId(hwnd)
            if found_pid == pid:
                hwnds.append(hwnd)
        return True

    hwnds = []
    win32gui.EnumWindows(callback, hwnds)
    return len(hwnds) > 0

# Function to get a list of running user-facing applications (heuristic-based)
def get_running_apps():
    apps = []
    # Include 'num_handles' in attrs for better filtering, though not strictly needed for window check
    for p in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_info', 'username', 'status', 'exe']):
        try:
            # Filter out non-running, zombie, or empty processes
            if not p.is_running() or p.status() == psutil.STATUS_ZOMBIE or not p.name() or not p.exe():
                continue

            # Exclude processes that are explicitly known system processes or services
            if p.name().lower() in [x.lower() for x in EXCLUDED_PROCESSES]:
                continue

            # --- NEW: Check for visible windows --- 
            # This is a more robust way to identify user-facing applications.
            if not _has_visible_window(p.pid):
                continue # Skip if no visible window

            apps.append({
                "pid": p.pid,
                "name": p.name(),
                "cpu": round(p.cpu_percent(interval=None), 2), # Use interval=None for non-blocking CPU percent
                "memory": round(p.memory_info().rss / (1024 * 1024), 2), # RSS in MB
                "user": p.username() if p.username() else "N/A"
            })
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            # Process no longer exists or access denied
            continue
        except Exception as e:
            print(f"Error getting process info for PID {p.pid}: {e}")
            continue
    return apps

# Function to get system information
def get_system_info():
    cpu_percent = psutil.cpu_percent(interval=1) # Get CPU usage over 1 second
    memory_info = psutil.virtual_memory()
    
    # Convert bytes to MB for used and total memory
    total_memory_mb = round(memory_info.total / (1024 * 1024), 2)
    used_memory_mb = round(memory_info.used / (1024 * 1024), 2)

    disk_info = []
    for part in psutil.disk_partitions():
        if 'cdrom' in part.opts or part.fstype == 'squashfs': # Skip CD-ROMs and certain virtual filesystems
            continue
        try:
            usage = psutil.disk_usage(part.mountpoint)
            disk_info.append({
                "device": part.device,
                "mountpoint": part.mountpoint,
                "total": round(usage.total / (1024 * 1024 * 1024), 2), # GB
                "used": round(usage.used / (1024 * 1024 * 1024), 2), # GB
                "free": round(usage.free / (1024 * 1024 * 1024), 2), # GB
                "percent": usage.percent
            })
        except Exception as e:
            print(f"Error getting disk info for {part.mountpoint}: {e}")

    # Get system uptime
    boot_time_timestamp = psutil.boot_time()
    uptime_seconds = int(time.time() - boot_time_timestamp)
    
    # Format uptime into a human-readable string
    days, remainder = divmod(uptime_seconds, 86400)
    hours, remainder = divmod(remainder, 3600)
    minutes, seconds = divmod(remainder, 60)
    
    uptime_string = ""
    if days > 0: uptime_string += f"{days}d "
    if hours > 0: uptime_string += f"{hours}h "
    if minutes > 0: uptime_string += f"{minutes}m "
    if seconds > 0 or uptime_string == "": uptime_string += f"{seconds}s"
    uptime_string = uptime_string.strip()

    # Get security information
    antivirus_status = False
    try:
        c = wmi.WMI(namespace="root\\SecurityCenter2")
        # Query for AntivirusProduct to find Windows Defender
        # ProductState values often indicate status (e.g., 393216 for up-to-date, 397312 for out of date, etc.)
        # A simpler check is just to see if the product exists and is enabled
        av_products = c.AntivirusProduct()
        for product in av_products:
            if "windows defender" in product.displayName.lower():
                # A product state of 393472 generally means enabled and up to date.
                # Other states might indicate issues. For simplicity, we'll assume
                # its presence and certain states imply "True".
                # It's safer to just check for its existence if it's the only one we care about.
                antivirus_status = True
                break
    except Exception as e:
        print(f"Error checking antivirus status: {e}")
        antivirus_status = "Error"

    is_admin = False
    try:
        is_admin = ctypes.windll.shell32.IsUserAnAdmin() != 0
    except Exception as e:
        print(f"Error checking admin privileges: {e}")
        is_admin = False

    monitor_info = get_monitor_info() # Get monitor information
    running_apps_info = get_running_apps() # Get running applications
    active_window_title = get_active_window_title() # Get active window title

    active_window_duration = 0
    if _active_window_start_time:
        active_window_duration = int(time.time() - _active_window_start_time)

    # Calculate idle time
    idle_time = int(time.time() - _last_activity_time)

    # Get OS Info
    os_name = platform.system()
    os_version = platform.version()
    os_architecture = platform.machine()

    # Get Device Name
    device_name = platform.node()

    # Get User Sessions (without password)
    user_sessions = []
    try:
        for user in psutil.users():
            user_sessions.append({
                "name": user.name,
                "started": user.started, # Timestamp of login
                "host": user.host, # Remote host if applicable, else None
                "has_password": True # Conceptual: indicates the *presence* of a password, not its value.
            })
    except Exception as e:
        print(f"Error getting user sessions: {e}")
        user_sessions.append({"name": "Error", "started": 0, "host": "N/A", "has_password": True})

    # Get current desktop background image as base64
    current_background_image_base64 = get_desktop_background_base64()

    return {
        "cpu": cpu_percent,
        "memory_total": total_memory_mb,
        "memory_used": used_memory_mb,
        "memory_percent": memory_info.percent,
        "disks": disk_info,
        "uptime": uptime_string,
        "antivirus": antivirus_status,
        "is_admin": is_admin,
        "monitors": monitor_info, # Add monitor info
        "running_apps": running_apps_info, # Add running apps info
        "active_window": active_window_title,
        "active_window_duration": active_window_duration,
        "idle_time": idle_time, # Add idle time
        "os_name": os_name,
        "os_version": os_version,
        "os_architecture": os_architecture,
        "device_name": device_name,
        "user_sessions": user_sessions,
        "current_background_image": current_background_image_base64 # Add current background image
    }

# Function to get monitor information
def get_monitor_info():
    monitors_data = []
    try:
        with mss.mss() as sct:
            # Add "All Monitors" as the first option (mss index 0)
            all_monitors_info = {
                "index": 0,
                "name": "All Monitors",
                "resolution": f"{sct.monitors[0]['width']}x{sct.monitors[0]['height']}",
                "hertz": "N/A" # Hertz is not easily available for combined view
            }
            monitors_data.append(all_monitors_info)

            # Enumerate individual active display monitors (mss indices 1 and up)
            # win32api is used here to get more detailed info like device name and refresh rate
            for i, monitor in enumerate(win32api.EnumDisplayMonitors()):
                hMonitor = monitor[0] # Monitor handle
                monitor_info = win32api.GetMonitorInfo(hMonitor) # Get monitor info
                
                device_name = monitor_info['Device']
                if isinstance(device_name, bytes):
                    device_name = device_name.decode('utf-8')
                device_name = device_name.strip('\x00') # Clean device name
                
                try:
                    devmode = win32api.EnumDisplaySettings(device_name, win32con.ENUM_CURRENT_SETTINGS)
                    resolution = f"{devmode.PelsWidth}x{devmode.PelsHeight}"
                    hertz = devmode.DisplayFrequency
                except Exception as e:
                    print(f"Error getting display settings for {device_name}: {e}")
                    resolution = "N/A"
                    hertz = "N/A"
                
                # Use i+1 to match mss's individual monitor indexing (starting from 1)
                monitors_data.append({
                    "index": i + 1,
                    "name": device_name if device_name else f"Monitor {i+1}",
                    "resolution": resolution,
                    "hertz": hertz
                })
    except Exception as e:
        print(f"Error enumerating monitors: {e}")
        monitors_data.append({"index": 0, "name": "Error", "resolution": "N/A", "hertz": "N/A"})
    return monitors_data

# Function to be run in a separate thread for the message box
def _display_message_box(message, title, combined_flag, topmost_owner):
    # Skapa ett osynligt fönster
    ex_style = win32con.WS_EX_TOPMOST if topmost_owner else 0
    
    hWnd = win32gui.CreateWindowEx(
        ex_style,
        "Static",
        None,
        0,
        0, 0, 0, 0,
        0,
        0,
        0,
        None
    )
    ctypes.windll.user32.MessageBoxExW(hWnd, message, title, combined_flag, 0)
    win32gui.DestroyWindow(hWnd)

# Modified show_message to accept title, message, icon, buttons, and topmost
def show_message(title="Meddelande", message="Hej från fjärrstyrning!", icon="", buttons="ok", topmost=False):
    message_box_icon_flag = ICON_MAP.get(icon.lower(), MB_OK)
    message_box_button_flag = BUTTON_MAP.get(buttons.lower(), MB_OK)
    
    combined_flag = message_box_icon_flag | message_box_button_flag

    print(f"📢 Visar meddelanderuta! Titel: '{title}', Innehåll: '{message}', Ikon: '{icon}' (Flag: {message_box_icon_flag}), Knappar: '{buttons}' (Flag: {message_box_button_flag}), Top Most: {topmost}, Kombinerad Flagga: {combined_flag})")
    
    # Run the message box in a new thread
    message_thread = threading.Thread(target=_display_message_box, args=(message, title, combined_flag, topmost))
    message_thread.daemon = True # Allow the main program to exit even if thread is running
    message_thread.start()

# Function to display a desktop notification with an optional image
def show_desktop_notification(title, message, image_base64=None):
    # icon_path = None # Not used anymore, will remove the variable if not needed
    if image_base64:
        try:
            image_data = b64decode(image_base64)
            # This image data is sent but not used as app_icon for Windows notifications directly.
            # For custom icons on Windows, it's generally required to package as .exe with PyInstaller.
            print(f"🖼️ Bilddata mottagen för notis men kommer inte att visas som ikon på Windows.")
        except Exception as e:
            print(f"❌ Fel vid hantering av notisbild (endast loggning, påverkar inte notisen längre): {e}")

    try:
        notification.notify(
            title=title,
            message=message,
            app_name='Fjärrkontroll Client',
            timeout=10 # Notification will disappear after 10 seconds
        )
        print(f"🔔 Skickade skrivbordsnotis: Titel='{title}', Meddelande='{message}'")
    except Exception as e:
        print(f"❌ Fel vid visning av skrivbordsnotis: {e}")
    finally:
        # No temporary file to delete for app_icon anymore
        pass # Keep this for future potential cleanup or if other temp files are introduced

# Helper function to delete a file after a delay (runs in a separate thread)
# This function is no longer needed if app_icon is not used.
def _delayed_delete_temp_file(file_path):
    try:
        if os.path.exists(file_path):
            os.remove(file_path)
            print(f"🗑️ Temporär notisbild borttagen: {file_path} (efter fördröjning)")
    except Exception as e:
        print(f"❌ Fel vid borttagning av temporär notisbild (i fördröjd tråd): {e}")

# Function to start/stop screen streaming
def toggle_screen_stream(enable):
    global _is_streaming_active, _stream_thread
    if enable and not _is_streaming_active:
        _is_streaming_active = True
        _stream_thread = threading.Thread(target=_stream_screen_loop)
        _stream_thread.daemon = True
        _stream_thread.start()
        print("🚀 Screen streaming started.")
    elif not enable and _is_streaming_active:
        _is_streaming_active = False
        if _stream_thread and _stream_thread.is_alive():
            # Give the thread a moment to finish its current loop iteration
            _stream_thread.join(timeout=1) 
        print("🛑 Screen streaming stopped.")

# Function to set the monitor index for streaming
def set_stream_monitor_index(index):
    global _selected_monitor_index
    _selected_monitor_index = int(index)
    print(f"Monitor for streaming set to index: {_selected_monitor_index}")

# Loop for continuous screen streaming
def _stream_screen_loop():
    with mss.mss() as sct:
        while _is_streaming_active:
            try:
                # Get raw pixels from the selected monitor
                # Ensure the index is valid
                monitor_count = len(sct.monitors)
                print(f"Stream loop: Detected {monitor_count} monitors. Attempting to stream index: {_selected_monitor_index}")

                if _selected_monitor_index >= monitor_count or _selected_monitor_index < 0:
                    print(f"⚠️ Selected monitor index {_selected_monitor_index} is out of range (total {monitor_count} monitors). Falling back to default (monitor 1). Current monitors: {sct.monitors}")
                    current_monitor_to_stream = sct.monitors[1] # Fallback to default if invalid
                else:
                    current_monitor_to_stream = sct.monitors[_selected_monitor_index]
                
                print(f"Using monitor for grab: {current_monitor_to_stream}")

                sct_img = sct.grab(current_monitor_to_stream)

                # Convert to PIL Image
                img = Image.frombytes("RGB", sct_img.size, sct_img.rgb)

                # Save as JPEG to a byte stream
                byte_arr = io.BytesIO()
                img.save(byte_arr, format='JPEG', quality=50) # Adjust quality as needed (0-95)

                # Send to server
                requests.post(f"{SERVER_URL}/stream", data=byte_arr.getvalue(), headers={'Content-Type': 'image/jpeg', 'Client-ID': client_id}, timeout=2)
                time.sleep(0.05) # Adjusted stream rate for 20 FPS
            except requests.exceptions.ConnectionError as ce:
                print(f"❌ Stream connection error: {ce}")
                time.sleep(1) # Wait before retrying
            except requests.exceptions.Timeout:
                print("⏳ Stream timeout: Server did not respond.")
                time.sleep(1) # Wait before retrying
            except Exception as e:
                print(f"❌ Error during screen streaming: {e}")
                time.sleep(1) # Wait before retrying

            # Rensa efter utfört kommando
            requests.post(f"{SERVER_URL}/send-command", data={"cmd": "", "client_id": client_id})

# Function to gracefully close a process by PID
def close_process(pid):
    try:
        p = psutil.Process(pid)
        p.terminate() # Attempt to terminate gracefully
        p.wait(timeout=3) # Wait for process to terminate
        if p.is_running():
            p.kill() # If still running, force kill
            print(f"💀 Process {pid} ({p.name()}) was forcefully killed.")
        else:
            print(f"🛑 Process {pid} ({p.name()}) terminated gracefully.")
        return True
    except psutil.NoSuchProcess:
        # If the process is not found here, it means it already terminated, which is success
        print(f"✅ Process {pid} successfully terminated or did not exist.")
        return True
    except psutil.AccessDenied:
        print(f"❌ Access denied to terminate process {pid}. (Requires higher privileges)")
        return False
    except Exception as e:
        print(f"❌ Error terminating process {pid}: {e}")
        return False

def get_active_window_title():
    """Gets the title of the currently active (foreground) window."""
    global _current_active_window_title, _active_window_start_time
    try:
        hwnd = win32gui.GetForegroundWindow()
        if hwnd:
            window_title = win32gui.GetWindowText(hwnd)
            # Filter out common background or placeholder window titles
            if window_title and window_title not in ["Default IME", "" ]:
                if window_title != _current_active_window_title:
                    # Window changed, reset timer
                    _current_active_window_title = window_title
                    _active_window_start_time = time.time()
                return window_title
        
        # If no active window or filtered, reset and return N/A
        if _current_active_window_title is not None:
            _current_active_window_title = None
            _active_window_start_time = None
        return "N/A"
    except Exception as e:
        print(f"Error getting active window title: {e}")
        # On error, also reset to avoid stale data
        if _current_active_window_title is not None:
            _current_active_window_title = None
            _active_window_start_time = None
        return "Error"

def _update_last_activity():
    """Helper to update the global last activity timestamp."""
    global _last_activity_time
    _last_activity_time = time.time()
    

def on_move(x, y):
    """Callback for mouse movement events."""
    _update_last_activity()

def on_click(x, y, button, pressed):
    """Callback for mouse click events."""
    _update_last_activity()

def on_scroll(x, y, dx, dy):
    """Callback for mouse scroll events."""
    _update_last_activity()

def on_release(key):
    """Callback function to update last activity time on keyboard release events."""
    _update_last_activity()

def main():
    print(f"🖥️ Klient startad med ID: {client_id}")
    
    # Setup keyboard and mouse listeners for idle time tracking
    keyboard_listener = keyboard.Listener(on_release=on_release)
    mouse_listener = mouse.Listener(on_move=on_move, on_click=on_click, on_scroll=on_scroll)

    # Start listeners in non-blocking mode (as threads)
    keyboard_listener.start()
    mouse_listener.start()

    while True:
        try:
            # Skicka heartbeat
            print("📡 Skickar heartbeat...")
            system_info = get_system_info()
            try:
                requests.post(f"{SERVER_URL}/heartbeat", json={"client_id": client_id, "ip": get_ip(), "system_info": system_info}, timeout=5) # Added timeout
                print("✅ Heartbeat skickad!")
            except requests.exceptions.ConnectionError as ce:
                print(f"❌ Fel vid anslutning till servern: {ce}. Kontrollera att servern körs och är nåbar.")
                time.sleep(3) # Wait a bit before retrying after connection error
                continue # Skip the rest of the loop and try heartbeat again
            except requests.exceptions.Timeout:
                print("⏳ Heartbeat timeout: Servern svarade inte i tid.")
                time.sleep(3) # Wait a bit before retrying after timeout
                continue # Skip the rest of the loop and try heartbeat again

            # Hämta kommando
            print("🔄 Hämtar kommando...")
            r = requests.get(f"{SERVER_URL}/get-command", params={"client_id": client_id})
            
            # Expect JSON response from server
            command_data = r.json() # Try to parse as JSON
            cmd = command_data.get("cmd")
            title = command_data.get("title", "Meddelande") # Default title
            message = command_data.get("message", "Inga meddelanden.") # Default message
            icon = command_data.get("icon", "") # Default empty string
            buttons = command_data.get("buttons", "ok") # Default to 'ok' buttons
            topmost = command_data.get("topmost", False) # Default to False

            print(f"🧠 Fick kommando: '{cmd}'")

            # Utför kommando
            if cmd == "show_message":
                show_message(title=title, message=message, icon=icon, buttons=buttons, topmost=topmost)
                # Rensa efter utfört kommando
                requests.post(f"{SERVER_URL}/send-command", data={"cmd": "", "client_id": client_id})
            elif cmd == "show_notification": # Handle desktop notification command
                image_data_base64 = command_data.get("image")
                show_desktop_notification(title=title, message=message, image_base64=image_data_base64)
                requests.post(f"{SERVER_URL}/send-command", data={"cmd": "", "client_id": client_id})
            elif cmd == "close_process": # Handle close process command
                process_pid = command_data.get("pid")
                if process_pid is not None:
                    success = close_process(process_pid)
                    if success:
                        print(f"✅ Successfully processed close_process command for PID: {process_pid}")
                    else:
                        print(f"❌ Failed to process close_process command for PID: {process_pid}")
                else:
                    print("⚠️ close_process command received without a PID.")
                requests.post(f"{SERVER_URL}/send-command", data={"cmd": "", "client_id": client_id})
            elif cmd == "start_stream":
                toggle_screen_stream(True)
                requests.post(f"{SERVER_URL}/send-command", data={"cmd": "", "client_id": client_id})
            elif cmd == "stop_stream":
                toggle_screen_stream(False)
                requests.post(f"{SERVER_URL}/send-command", data={"cmd": "", "client_id": client_id})
            elif cmd == "set_stream_monitor":
                # Only get monitor_index if the command is specifically for setting it
                monitor_index = command_data.get("monitor_index")
                if monitor_index is not None: # Ensure a value was actually sent
                    set_stream_monitor_index(monitor_index)
                else:
                    print("⚠️ set_stream_monitor command received without a monitor_index. Using current index.")
                requests.post(f"{SERVER_URL}/send-command", data={"cmd": "", "client_id": client_id})
            elif cmd == "change_background":
                image_data_base64 = command_data.get("image")
                if image_data_base64:
                    success = set_desktop_background(image_data_base64)
                    if success:
                        print(f"✅ Successfully changed desktop background.")
                    else:
                        print(f"❌ Failed to change desktop background.")
                else:
                    print("⚠️ change_background command received without image data.")
                requests.post(f"{SERVER_URL}/send-command", data={"cmd": "", "client_id": client_id})
            # For other commands (including empty ones), the _selected_monitor_index should remain unchanged.
            # No need to get monitor_index for other commands here.
            time.sleep(0.1) # Further reduced sleep for much faster command polling and heartbeats
        except json.JSONDecodeError:
            print("❌ Fel: Servern returnerade inte giltig JSON. Förväntade mig JSON-data för kommando.")
            cmd = r.text.strip() # Fallback to old behavior if not JSON
            if cmd == "show_message":
                # Cannot get title/message without JSON, display a generic message
                show_message(title="Meddelande", message="Fick ett meddelande, men kunde inte läsa titeln/innehållet.", icon="", buttons="ok", topmost=False)
                requests.post(f"{SERVER_URL}/send-command", data={"cmd": "", "client_id": client_id})
            time.sleep(1)
        except Exception as e:
            print("❌ Fel vid kontakt med server:", e)
            time.sleep(1)

if __name__ == "__main__":
    main()
