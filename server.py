from flask import Flask, request, jsonify

app = Flask(__name__)
client_commands = {}

@app.route('/heartbeat', methods=['POST'])
def heartbeat():
    data = request.form # Heartbeat sends form data
    client_id = data.get('client_id')
    ip = data.get('ip')
    # In a real app, you'd store client's last seen time, IP, etc.
    print(f"Heartbeat from {client_id} (IP: {ip})")
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

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5000)
