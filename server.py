import os
import json
import smtplib
from email.mime.text import MIMEText
from flask import Flask, send_from_directory
from flask_socketio import SocketIO, send, join_room, emit

app = Flask(__name__, static_url_path='', static_folder='.')
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'secret!')
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

# Email
EMAIL_FROM = "HABaccount@yandex.ru"
EMAIL_PASSWORD = "ypuoaanotpezzebu"
EMAIL_TO = "HABaccount@yandex.ru"

DATA_FILE = 'data.json'

def load_data():
    try:
        with open(DATA_FILE, 'r') as f:
            return json.load(f)
    except:
        return {'pending': [], 'approved': [], 'banned': []}

def save_data():
    with open(DATA_FILE, 'w') as f:
        json.dump({'pending': pending_users, 'approved': approved_users, 'banned': banned_users}, f)

data = load_data()
pending_users = data['pending']
approved_users = data['approved']
banned_users = data['banned']

def send_email(subject, body):
    try:
        msg = MIMEText(body)
        msg['Subject'] = subject
        msg['From'] = EMAIL_FROM
        msg['To'] = EMAIL_TO
        server = smtplib.SMTP_SSL('smtp.yandex.ru', 465)
        server.login(EMAIL_FROM, EMAIL_PASSWORD)
        server.sendmail(EMAIL_FROM, EMAIL_TO, msg.as_string())
        server.quit()
    except Exception as e:
        print('Email error:', str(e))

rooms = {
    'Общая': '',
    'С паролем': '123',
    'Третья': 'qwerty'
}

history = {}

@app.route('/')
def index():
    return send_from_directory('.', 'index.html')

@socketio.on('join')
def handle_join(data):
    room = data.get('room', 'Общая')
    password = data.get('password', '').strip()
    name = data.get('name', 'Гость')
    
    if name in banned_users:
        emit('message', {'type': 'system', 'text': 'Вы забанены.'})
        return
    
    if room not in rooms:
        emit('message', {'type': 'system', 'text': f'Комната "{room}" не существует'})
        return
    
    if rooms[room] != '' and rooms[room] != password:
        emit('message', {'type': 'system', 'text': f'Неверный пароль'})
        return
    
    if name not in approved_users:
        if name not in pending_users:
            pending_users.append(name)
            save_data()
            send_email('ХАБ: Новая заявка', f'Пользователь {name} ожидает одобрения.')
        emit('message', {'type': 'system', 'text': f'{name}, вы на модерации. Не покидайте окно, ожидайте.'})
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
        save_data()
        emit('message', {'type': 'system', 'text': f'{name} одобрен!'})

@socketio.on('admin_ban')
def handle_ban(data):
    name = data.get('name', '')
    if name not in banned_users:
        banned_users.append(name)
    if name in approved_users:
        approved_users.remove(name)
    if name in pending_users:
        pending_users.remove(name)
    save_data()
    emit('message', {'type': 'system', 'text': f'{name} забанен.'}, broadcast=True)

@socketio.on('get_lists')
def handle_get_lists():
    emit('admin_lists', {
        'pending': pending_users,
        'approved': approved_users,
        'banned': banned_users
    })

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    socketio.run(app, host='0.0.0.0', port=port)
