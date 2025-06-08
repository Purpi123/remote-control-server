from flask import Flask, request
from flask_cors import CORS


app = Flask(__name__)
CORS(app)
current_command = ""

@app.route('/send-command', methods=['POST'])
def send_command():
    global current_command
    current_command = request.form.get("cmd")
    return "OK"

@app.route('/get-command')
def get_command():
    global current_command
    cmd = current_command
    current_command = ""  # Nollställ efter att klienten hämtat
    return cmd

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5000)
