import os
import json
from flask import Flask, send_from_directory
from flask_socketio import SocketIO, send, join_room, emit
from pywebpush import webpush, WebPushException

app = Flask(__name__, static_url_path='', static_folder='.')
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'secret!')
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

VAPID_PRIVATE = """-----BEGIN PRIVATE KEY-----
MIGHAgEAMBMGByqGSM49AgEGCCqGSM49AwEHBG0wawIBAQQgTSZ4sDXvhXhsL8qk
VjdylUlT8vUAdfGqmhAZG3S1JA6hRANCAATwqzYyWeDrtljTq1W9Ew0vxyCSEwXq
L51pUdupjTWx7auUzZWGJVNGUAe/o7BOBIIIflULH9LAxzKeFmCl2h/X
-----END PRIVATE KEY-----"""

VAPID_PUBLIC = """-----BEGIN PUBLIC KEY-----
MFkwEwYHKoZIzj0CAQYIKoZIzj0DAQcDQgAE8Ks2Mlng67ZY06tVvRMNL8cgkhMF
6i+daVHbqY01se2rlM2VhiVTRlAHv6OwTgSCCH5VCx/SwMcynhZgpdof1w==
-----END PUBLIC KEY-----"""

VAPID_CLAIMS = {"sub": "mailto:admin@hab.local"}

rooms = {
    'Общая': '',
    'С паролем': '123',
    'Третья': 'qwerty'
}

history = {}
subscriptions = []

def send_push_notification(sub, message):
    try:
        webpush(
            subscription_info=sub,
            data=json.dumps({"title": "ХАБ", "body": message}),
            vapid_private_key=VAPID_PRIVATE,
            vapid_claims=VAPID_CLAIMS
        )
    except Exception:
        pass

@app.route('/')
def index():
    return send_from_directory('.', 'index.html')

@socketio.on('join')
def handle_join(data):
    room = data.get('room', 'Общая')
    password = data.get('password', '').strip()
    name = data.get('name', 'Гость')
    
    if room not in rooms:
        emit('message', {'type': 'system', 'text': f'Комната "{room}" не существует'})
        return
    
    if rooms[room] != '' and rooms[room] != password:
        emit('message', {'type': 'system', 'text': f'Неверный пароль для комнаты "{room}"'})
        return
    
    join_room(room)
    
    if room in history:
        for msg in history[room]:
            emit('message', msg)
    
    emit('message', {'type': 'system', 'text': f'{name} вошёл в комнату "{room}"'}, to=room)

@socketio.on('message')
def handle_message(msg):
    room = msg.get('room', 'Общая')
    
    if room not in history:
        history[room] = []
    history[room].append(msg)
    if len(history[room]) > 100:
        history[room] = history[room][-100:]
    
    # Отправляем push всем подписчикам
    nick = msg.get('nick', 'Кто-то')
    text = msg.get('text', '')
    for sub in subscriptions:
        send_push_notification(sub, f"{nick}: {text}")
    
    send(msg, to=room)

@socketio.on('clear')
def handle_clear(data):
    room = data.get('room', 'Общая')
    if room in history:
        history[room] = []
    emit('message', {'type': 'system', 'text': 'Чат очищен'}, to=room)

@socketio.on('subscribe')
def handle_subscribe(data):
    sub = data.get('subscription')
    if sub and sub not in subscriptions:
        subscriptions.append(sub)
        print('NEW SUBSCRIPTION:', len(subscriptions))
    else:
        print('DUPLICATE SUBSCRIPTION')

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    socketio.run(app, host='0.0.0.0', port=port)
