from flask import Flask, render_template, request
from flask_socketio import SocketIO, emit, join_room, leave_room
import random
import hashlib
import string
from datetime import datetime

app = Flask(__name__)
app.config['SECRET_KEY'] = 'mabar3gem-secret-key'
socketio = SocketIO(app, cors_allowed_origins="*")

# Game state
rooms = {}
guests = {}  # {session_id: {ip, name, room_id}}
fortune_cookies = [
    # Positive (40)
    "Your hard work will soon pay off.", "Good fortune is coming your way.", 
    "Success is in your future.", "A pleasant surprise awaits you.",
    "Your creativity will bring great results.", "New opportunities are on the horizon.",
    "Happiness is just around the corner.", "Your kindness will be rewarded.",
    "A dream will come true soon.", "You will find peace in unexpected places.",
    "Your efforts will be recognized.", "A new friendship will bring joy.",
    "Your passion will lead to success.", "Good news is on its way.",
    "You will overcome all obstacles.", "Your talent will shine bright.",
    "A positive change is coming.", "Your patience will be rewarded.",
    "Love is in the air for you.", "You will achieve your goals soon.",
    "Your determination will inspire others.", "A lucky day is approaching.",
    "Your generosity will come back to you.", "You will find what you seek.",
    "Your wisdom will guide you well.", "A joyful event is near.",
    "Your courage will be rewarded.", "You will make someone very happy.",
    "A wonderful opportunity awaits.", "Your dreams are within reach.",
    "You will find inner strength.", "A breakthrough is coming soon.",
    "Your positive energy attracts good things.", "You will discover hidden talents.",
    "A new adventure begins today.", "Your smile brightens someone's day.",
    "You will receive unexpected help.", "Your intuition is guiding you right.",
    "A special moment is coming.", "Your persistence will pay off handsomely.",
    
    # Negative (30)
    "Be cautious with your decisions today.", "Not everything is as it seems.",
    "Patience is needed in difficult times.", "Learn from your mistakes.",
    "Things may not go as planned.", "Be prepared for unexpected challenges.",
    "Sometimes the path is unclear.", "Trust is earned, not given freely.",
    "Not all risks are worth taking.", "Disappointment may be temporary.",
    "Some doors close for a reason.", "Rethink your current strategy.",
    "Words can hurt more than actions.", "Not everyone has your best interests.",
    "Some battles aren't worth fighting.", "Pride comes before the fall.",
    "What seems easy may be difficult.", "Shortcuts often lead nowhere.",
    "Not every question has an answer.", "Some things are beyond your control.",
    "Hasty decisions lead to regret.", "Not all that glitters is gold.",
    "Your assumptions may be wrong.", "Some friendships fade with time.",
    "Failure is part of the journey.", "Not every investment pays off.",
    "Some secrets are better kept.", "Your fears may be justified.",
    "Not everyone will understand you.", "Some bridges have already burned.",
    
    # Maybe (30)
    "The answer lies within you.", "Time will reveal all truths.",
    "Perhaps a different approach is needed.", "The future remains unwritten.",
    "It depends on your next move.", "Only you can decide your fate.",
    "The path ahead is uncertain.", "Trust your instincts on this one.",
    "The outcome is still in question.", "Consider all possibilities carefully.",
    "Things could go either way.", "The choice is yours to make.",
    "Destiny is what you make of it.", "The answer is not yet clear.",
    "Both options have merit.", "Listen to your heart and mind.",
    "The truth is more complex than it seems.", "Your guess is as good as mine.",
    "Everything happens for a reason, maybe.", "The universe works in mysterious ways.",
    "Sometimes yes, sometimes no.", "It's possible but not guaranteed.",
    "The stars are not aligned yet.", "Wait and see what unfolds.",
    "The outcome depends on many factors.", "There's a 50-50 chance.",
    "Ask again at a different time.", "The answer is hiding in plain sight.",
    "Neither yes nor no, but perhaps.", "Only time will tell for sure."
]

def generate_room_id():
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))

def generate_unique_guest_name():
    """Generate unique guest name yang belum dipake"""
    max_attempts = 1000
    for _ in range(max_attempts):
        guest_num = random.randint(1, 1000)
        guest_name = f"Guest{guest_num}"
        
        # Check if name already exists
        name_exists = any(g['name'] == guest_name for g in guests.values())
        if not name_exists:
            return guest_name
    
    # Fallback: use timestamp if all random failed
    import time
    return f"Guest{int(time.time()) % 10000}"

def calculate_love_score(name1, name2):
    # Normalize names (lowercase, remove spaces)
    n1 = ''.join(sorted(name1.lower().replace(' ', '')))
    n2 = ''.join(sorted(name2.lower().replace(' ', '')))
    
    # Create consistent hash regardless of order
    combined = ''.join(sorted([n1, n2]))
    hash_obj = hashlib.md5(combined.encode())
    hash_int = int(hash_obj.hexdigest(), 16)
    
    # Generate consistent score 10-99%
    score = (hash_int % 90) + 10
    return score

@app.route('/')
def index():
    return render_template('index.html')

@socketio.on('connect')
def handle_connect():
    session_id = request.sid
    client_ip = request.environ.get('HTTP_X_FORWARDED_FOR', request.remote_addr)
    
    # Generate unique guest name
    guest_name = generate_unique_guest_name()
    
    guests[session_id] = {
        'ip': client_ip,
        'name': guest_name,
        'room_id': None
    }
    
    emit('connected', {'guest_name': guest_name, 'session_id': session_id})
    print(f"[CONNECT] {guest_name} ({client_ip}) connected. Total guests: {len(guests)}")

@socketio.on('create_room')
def handle_create_room():
    session_id = request.sid
    if session_id not in guests:
        emit('error', {'message': 'Session not found'})
        return
    
    # Check max 10 guests globally
    if len(guests) >= 10:
        emit('error', {'message': 'Server full (max 10 guests)'})
        return
    
    room_id = generate_room_id()
    guest_name = guests[session_id]['name']
    
    rooms[room_id] = {
        'players': [guest_name],
        'scores': {guest_name: 0},
        'current_game': None,
        'game_state': {}
    }
    
    guests[session_id]['room_id'] = room_id
    join_room(room_id)
    
    emit('room_created', {
        'room_id': room_id,
        'players': rooms[room_id]['players']
    })
    print(f"[ROOM] {guest_name} created room {room_id}")

@socketio.on('join_room')
def handle_join_room(data):
    session_id = request.sid
    room_id = data.get('room_id', '').strip().upper()
    
    if session_id not in guests:
        emit('error', {'message': 'Session not found'})
        return
    
    if not room_id:
        emit('error', {'message': 'Room ID required'})
        return
    
    if room_id not in rooms:
        emit('error', {'message': 'Room not found'})
        return
    
    if len(rooms[room_id]['players']) >= 10:
        emit('error', {'message': 'Room full'})
        return
    
    guest_name = guests[session_id]['name']
    
    # Check if already in room
    if guest_name in rooms[room_id]['players']:
        emit('error', {'message': 'Already in room'})
        return
    
    rooms[room_id]['players'].append(guest_name)
    rooms[room_id]['scores'][guest_name] = 0
    guests[session_id]['room_id'] = room_id
    
    join_room(room_id)
    
    emit('player_joined', {
        'players': rooms[room_id]['players'],
        'scores': rooms[room_id]['scores']
    }, room=room_id)
    print(f"[JOIN] {guest_name} joined room {room_id}")

@socketio.on('disconnect')
def handle_disconnect():
    session_id = request.sid
    if session_id not in guests:
        return
    
    guest_name = guests[session_id]['name']
    room_id = guests[session_id].get('room_id')
    
    if room_id and room_id in rooms:
        # Remove from room
        if guest_name in rooms[room_id]['players']:
            rooms[room_id]['players'].remove(guest_name)
        if guest_name in rooms[room_id]['scores']:
            del rooms[room_id]['scores'][guest_name]
        
        # Delete room if empty
        if len(rooms[room_id]['players']) == 0:
            del rooms[room_id]
            print(f"[ROOM] Room {room_id} deleted (empty)")
        else:
            emit('player_left', {
                'players': rooms[room_id]['players'],
                'scores': rooms[room_id]['scores']
            }, room=room_id)
    
    # Remove guest from dictionary
    del guests[session_id]
    print(f"[DISCONNECT] {guest_name} disconnected. Total guests: {len(guests)}")

# Game: Love Calculator
@socketio.on('love_calculate')
def handle_love_calculate(data):
    session_id = request.sid
    
    if session_id not in guests:
        emit('error', {'message': 'Session not found'})
        return
    
    room_id = guests[session_id].get('room_id')
    guest_name = guests[session_id]['name']
    
    name1 = data.get('name1', '').strip()
    name2 = data.get('name2', '').strip()
    
    if not name1 or not name2:
        emit('error', {'message': 'Both names required'})
        return
    
    score = calculate_love_score(name1, name2)
    
    # Broadcast to all players in room
    if room_id and room_id in rooms:
        emit('love_result', {
            'player': guest_name,
            'name1': name1,
            'name2': name2,
            'score': score
        }, room=room_id)
    else:
        emit('love_result', {
            'player': guest_name,
            'name1': name1,
            'name2': name2,
            'score': score
        })

# Game: Fortune Cookie
@socketio.on('crack_cookie')
def handle_crack_cookie():
    session_id = request.sid
    
    if session_id not in guests:
        emit('error', {'message': 'Session not found'})
        return
    
    room_id = guests[session_id].get('room_id')
    guest_name = guests[session_id]['name']
    
    fortune = random.choice(fortune_cookies)
    
    # Determine category
    idx = fortune_cookies.index(fortune)
    if idx < 40:
        category = 'positive'
    elif idx < 70:
        category = 'negative'
    else:
        category = 'maybe'
    
    # Broadcast to all players in room
    if room_id and room_id in rooms:
        emit('fortune_result', {
            'player': guest_name,
            'fortune': fortune,
            'category': category
        }, room=room_id)
    else:
        emit('fortune_result', {
            'player': guest_name,
            'fortune': fortune,
            'category': category
        })

# Game: Dice Roller (Battle Mode)
@socketio.on('roll_dice')
def handle_roll_dice(data):
    session_id = request.sid
    
    if session_id not in guests:
        emit('error', {'message': 'Session not found'})
        return
    
    room_id = guests[session_id].get('room_id')
    
    if not room_id or room_id not in rooms:
        emit('error', {'message': 'Join a room first'})
        return
    
    guest_name = guests[session_id]['name']
    num_dice = data.get('num_dice', 1)
    dice_sides = data.get('dice_sides', 6)
    
    # Roll dice
    rolls = [random.randint(1, dice_sides) for _ in range(num_dice)]
    total = sum(rolls)
    
    # Update score
    rooms[room_id]['scores'][guest_name] += total
    
    # Broadcast to room
    emit('dice_rolled', {
        'player': guest_name,
        'rolls': rolls,
        'total': total,
        'scores': rooms[room_id]['scores'],
        'timestamp': datetime.now().strftime('%H:%M:%S')
    }, room=room_id)

# Game: Reset (Owner Only)
@socketio.on('reset_game')
def handle_reset_game(data):
    session_id = request.sid
    
    if session_id not in guests:
        emit('error', {'message': 'Session not found'})
        return
    
    room_id = data.get('room_id')
    
    if not room_id or room_id not in rooms:
        emit('error', {'message': 'Room not found'})
        return
    
    guest_name = guests[session_id]['name']
    
    # Check if owner
    if guest_name != rooms[room_id]['players'][0]:
        emit('error', {'message': 'Only room owner can reset'})
        return
    
    # Reset scores
    for player in rooms[room_id]['players']:
        rooms[room_id]['scores'][player] = 0
    
    rooms[room_id]['game_state'] = {}
    
    # Broadcast reset to all
    emit('game_reset', room=room_id)
    print(f"[RESET] {guest_name} reset room {room_id}")

if __name__ == '__main__':
    socketio.run(app, debug=True, host='0.0.0.0', port=5000)