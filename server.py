import os
import json
import requests
from flask import Flask, send_from_directory
from flask_socketio import SocketIO, send, join_room, emit

app = Flask(__name__, static_url_path='', static_folder='.')
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'secret!')
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

# Telegram
TG_TOKEN = "8740693953:AAEhjvmXBnU_afFiJmDAvzqJ87ABJeKVCNA"
TG_CHAT_ID = "6789836295"

def send_tg(msg):
    try:
        requests.post(
            f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage",
            json={"chat_id": TG_CHAT_ID, "text": msg},
            timeout=5
        )
    except:
        pass

DATA_FILE = 'data.json'


def load_data():
    try:
        with open(DATA_FILE, 'r') as f:
            data = json.load(f)
            return {
                'pending': data.get('pending', []),
                'approved': data.get('approved', []),
                'banned': data.get('banned', []),
                'pending_tracks': data.get('pending_tracks', []),
                'approved_tracks': data.get('approved_tracks', [])
            }
    except:
        return {'pending': [], 'approved': [], 'banned': [], 'pending_tracks': [], 'approved_tracks': []}

def save_data():
    global pending_users, approved_users, banned_users, pending_tracks, approved_tracks
    with open(DATA_FILE, 'w') as f:
        json.dump({
            'pending': pending_users,
            'approved': approved_users,
            'banned': banned_users,
            'pending_tracks': pending_tracks,
            'approved_tracks': approved_tracks
        }, f)
        
data = load_data()
pending_users = data['pending']
approved_users = data['approved']
banned_users = data['banned']
pending_tracks = data['pending_tracks']
approved_tracks = data['approved_tracks']

FALLBACK_APPROVED = ['vivbu', 'viva', 'zeti', 'ars', 'арс', 'Тимур', 'ZT', 'ГУСЕВ_КОРОЛЬ_МИРА']



rooms = {
    'Общая': '',
    'С паролем': '123',
    'Третья': 'qwerty'
}

history = {}

@socketio.on('submit_track')
def handle_submit_track(data):
    global pending_tracks
    if data is None:
        data = {}
    track = data.get('track')
    # Пробуем получить напрямую
    if not track:
        track = {'name': data.get('name', 'неизвестно'), 'from': data.get('from', ''), 'size': data.get('size', ''), 'base64': data.get('base64', '')}
    if track:
        pending_tracks.append(track)
        save_data()
        emit('track_submitted', {'success': True, 'name': track.get('name', '')})

@socketio.on('get_track_file')
def handle_get_track_file(data):
    name = data.get('name')
    print('Requested file:', name)
    print('Pending tracks:', pending_tracks)
    for t in pending_tracks:
        if t['name'] == name:
            emit('track_file', {'name': name, 'base64': t.get('base64', '')})
            break
            
@socketio.on('get_pending_tracks')
def handle_get_pending_tracks():
    emit('pending_tracks', pending_tracks)

@socketio.on('approve_track_server')
def handle_approve_track(data):
    name = data.get('name')
    for t in pending_tracks:
        if t['name'] == name:
            pending_tracks.remove(t)
            approved_tracks.append(t)
            save_data()
            emit('message', {'type': 'system', 'text': f'Трек {name} одобрен!'}, broadcast=True)
            break

@socketio.on('reject_track_server')
def handle_reject_track(data):
    name = data.get('name')
    for t in pending_tracks:
        if t['name'] == name:
            pending_tracks.remove(t)
            save_data()
            break

@socketio.on('get_approved_tracks')
def handle_get_approved_tracks():
    emit('approved_tracks', approved_tracks)

@app.route('/')
def index():
    return send_from_directory('.', 'index.html')

@socketio.on('admin_unban')
def handle_unban(data):
    name = data.get('name', '')
    if name in banned_users:
        banned_users.remove(name)
    if name not in approved_users:
        approved_users.append(name)
    if name not in FALLBACK_APPROVED:
        FALLBACK_APPROVED.append(name)
    save_data()
    emit('message', {'type': 'system', 'text': f'{name} разбанен.'}, broadcast=True)

@socketio.on('join')
def handle_join(data):
    room = data.get('room', 'Общая')
    password = data.get('password', '').strip()
    name = data.get('name', 'Гость')
    
    if name in banned_users:
        send({'type': 'system', 'text': 'Вы забанены.'})
        return
    
    if room not in rooms:
        send({'type': 'system', 'text': f'Комната "{room}" не существует'})
        return
    if name in FALLBACK_APPROVED and name not in approved_users:
        approved_users.append(name)
        save_data()

        # Проверка, что ник не занят
    # if name in approved_users:
    #     send({'type': 'system', 'text': f'Ник "{name}" уже занят. Выберите другой.'})
    #     return
        
    # Сначала модерация
    if name not in approved_users:
        if name not in pending_users:
            pending_users.append(name)
            save_data()
        send({'type': 'system', 'text': f'{name}, вы на модерации. Не покидайте окно, ожидайте.'})
        return
    
    # Потом пароль
    if rooms[room] != '' and rooms[room] != password:
        send({'type': 'system', 'text': f'Неверный пароль'})
        return
    
    join_room(room)
    
    if room in history:
        for msg in history[room]:
            emit('message', msg)
    
    emit('message', {'type': 'system', 'text': f'{name} вошёл в комнату "{room}"'}, to=room)
    
@socketio.on('message')
def handle_message(msg):
    room = msg.get('room', 'Общая')
    nick = msg.get('nick', '')
    
    if nick in banned_users:
        return
    
    if room not in history:
        history[room] = []
    history[room].append(msg)
    if len(history[room]) > 100:
        history[room] = history[room][-100:]
    
    send(msg, to=room)

@socketio.on('clear')
def handle_clear(data):
    room = data.get('room', 'Общая')
    if room in history:
        history[room] = []
    emit('message', {'type': 'system', 'text': 'Чат очищен'}, to=room)

@socketio.on('admin_approve')
def handle_approve(data):
    name = data.get('name', '')
    if name in pending_users:
        pending_users.remove(name)
        approved_users.append(name)
        if name not in FALLBACK_APPROVED:
            FALLBACK_APPROVED.append(name)
        save_data()
        # Отправляем ТОЛЬКО тому, кого одобрили
        emit('message', {'type': 'system', 'text': 'Вы прошли модерацию! Перезайдите, не меняя ник.'})


@socketio.on('admin_ban')
def handle_ban(data):
    name = data.get('name', '')
    if name not in banned_users:
        banned_users.append(name)
    if name in approved_users:
        approved_users.remove(name)
    if name in pending_users:
        pending_users.remove(name)
    # Удаляем из FALLBACK
    if name in FALLBACK_APPROVED:
        FALLBACK_APPROVED.remove(name)
    save_data()
    emit('message', {'type': 'system', 'text': f'{name} забанен.'}, broadcast=True)
    
@socketio.on('get_lists')
def handle_get_lists():
    all_approved = list(set(approved_users + FALLBACK_APPROVED))
    emit('admin_lists', {
        'pending': pending_users,
        'approved': all_approved,
        'banned': banned_users
    })

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    socketio.run(app, host='0.0.0.0', port=port)
