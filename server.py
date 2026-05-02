import os
from flask import Flask, send_from_directory
from flask_socketio import SocketIO, send, emit

app = Flask(__name__, static_url_path='', static_folder='.')
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'secret!')
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

@app.route('/')
def index():
    return send_from_directory('.', 'index.html')

@socketio.on('message')
def handle_message(msg):
    emit('message', msg, broadcast=True)

@socketio.on('join')
def handle_join(data):
    emit('message', {'type': 'system', 'text': data.get('name', 'Кто-то') + ' вошёл'}, broadcast=True)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    socketio.run(app, host='0.0.0.0', port=port)
