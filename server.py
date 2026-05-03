import os
from flask import Flask, send_from_directory
from flask_socketio import SocketIO, send, join_room, emit

app = Flask(__name__, static_url_path='', static_folder='.')
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'secret!')
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')


rooms = {
    'Общая': '',
    'С паролем': '123',
    'Третья': 'qwerty'
}

# Хранилище сообщений (по комнатам)
history = {}

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
    
    # Отправляем историю новому пользователю
    if room in history:
        for msg in history[room]:
               emit('message', {'type': 'system', 'text': f'Комната "{room}" не существует'})
    
    emit('message', {'type': 'system', 'text': f'{name} вошёл в комнату "{room}"'}, to=room)

@socketio.on('message')
def handle_message(msg):
    room = msg.get('room', 'Общая')
    
    # Сохраняем в историю (последние 100 сообщений)
    if room not in history:
        history[room] = []
    history[room].append(msg)
    if len(history[room]) > 100:
        history[room] = history[room][-100:]
    
        emit('message', msg, to=room)

@socketio.on('clear')
def handle_clear(data):
    room = data.get('room', 'Общая')
    if room in history:
        history[room] = []
    emit('message', {'type': 'system', 'text': 'Чат очищен'}, to=room)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    socketio.run(app, host='0.0.0.0', port=port)
