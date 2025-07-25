import os
import hashlib
from flask import Blueprint, render_template, request
from flask_socketio import emit, join_room, leave_room
from datetime import datetime

reuniao_blueprint = Blueprint('reuniao', __name__, template_folder='templates')

# Estrutura: { sala: { socket_id: nome } }
salas_usuarios = {}

def gerar_nome_unico():
    aleatorio = os.urandom(4).hex()
    hash_nome = hashlib.sha256(aleatorio.encode()).hexdigest()[:6]
    return f"User_{hash_nome}"

@reuniao_blueprint.route('/<sala>')
def reuniao(sala):
    nome_gerado = gerar_nome_unico()
    return render_template('reuniao.html', sala=sala, nome=nome_gerado)

def configurar_socketio(socketio):

    @socketio.on('entrar_sala')
    def handle_entrar_sala(data):
        nome = data.get('nome', 'Anônimo')
        sala = data.get('sala')
        sid = request.sid

        if not sala:
            return

        if sala not in salas_usuarios:
            salas_usuarios[sala] = {}

        salas_usuarios[sala][sid] = nome
        join_room(sala)

        emit('mensagem', {
            'nome': 'Sistema',
            'mensagem': f'{nome} entrou na sala.',
            'hora': datetime.now().strftime('%H:%M')
        }, room=sala)

    @socketio.on('mensagem')
    def handle_mensagem(data):
        nome = data.get('nome', 'Anônimo')
        sala = data.get('sala')
        mensagem = data.get('mensagem')
        hora = datetime.now().strftime('%H:%M')

        if not sala or not mensagem:
            return

        emit('mensagem', {
            'nome': nome,
            'mensagem': mensagem,
            'hora': hora
        }, room=sala)

    # Evento para quando o usuário ativa o áudio
    @socketio.on('ready_audio')
    def on_ready_audio(data):
        sala = data.get('sala')
        nome = data.get('nome', 'Anônimo')
        sid = request.sid

        if not sala:
            return

        if sala not in salas_usuarios:
            salas_usuarios[sala] = {}

        salas_usuarios[sala][sid] = nome
        join_room(sala)

        # Envia a lista dos usuários já na sala para o novo usuário (exceto ele mesmo)
        outros = [
            {'socketId': s, 'nome': salas_usuarios[sala][s]}
            for s in salas_usuarios.get(sala, {})
            if s != sid
        ]
        emit('usuarios_existentes', outros, room=sid)

        # Notifica os demais que um novo usuário entrou para áudio
        emit('new_user', {'socketId': sid, 'nome': nome}, room=sala, include_self=False)

    # Evento para receber a lista dos usuários da sala
    @socketio.on('pegar_usuarios_sala')
    def pegar_usuarios_sala(data):
        sala = data.get('sala')
        sid = request.sid

        if not sala or sala not in salas_usuarios:
            emit('usuarios_existentes', [], room=sid)
            return

        outros = [
            {'socketId': s, 'nome': salas_usuarios[sala][s]}
            for s in salas_usuarios[sala]
            if s != sid
        ]
        emit('usuarios_existentes', outros, room=sid)

    @socketio.on('signal')
    def on_signal(data):
        to_sid = data.get('to')
        signal = data.get('signal')
        from_sid = request.sid

        if not to_sid or not signal:
            return

        emit('signal', {'from': from_sid, 'signal': signal}, room=to_sid)

    @socketio.on('leave_audio')
    def on_leave_audio(data):
        sala = data.get('sala')
        sid = request.sid

        if not sala:
            return

        nome = salas_usuarios.get(sala, {}).get(sid, 'Alguém')
        leave_room(sala)

        emit('user_left', {'socketId': sid, 'nome': nome}, room=sala)

        if sid in salas_usuarios.get(sala, {}):
            del salas_usuarios[sala][sid]

    @socketio.on('disconnect')
    def on_disconnect():
        sid = request.sid

        for sala, usuarios in list(salas_usuarios.items()):
            if sid in usuarios:
                nome = usuarios[sid]
                leave_room(sala)
                emit('mensagem', {
                    'nome': 'Sistema',
                    'mensagem': f'{nome} saiu da sala.',
                    'hora': datetime.now().strftime('%H:%M')
                }, room=sala)
                del usuarios[sid]

        # Limpa salas vazias (opcional)
        for sala in list(salas_usuarios):
            if not salas_usuarios[sala]:
                del salas_usuarios[sala]
