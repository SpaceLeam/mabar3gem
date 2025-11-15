from flask import Flask, render_template, request
from flask_socketio import SocketIO, emit, join_room, leave_room
import random
import hashlib
import string
from datetime import datetime
import time

app = Flask(__name__)
app.config['SECRET_KEY'] = 'mabar3gem-secret-key'
socketio = SocketIO(app, cors_allowed_origins="*")

# Game state
rooms = {}
guests = {}  # {session_id: {ip, name, room_id}}
racing_rooms = {}  # {room_id: racing state}

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

# Racing mini games data
mini_games = {
    'guess_number': {
        'type': 'guess_number',
        'question': 'Guess the number (1-10)',
        'answer': None  # Will be random
    },
    'math': [
        {'q': '5 + 3', 'a': '8'},
        {'q': '12 - 4', 'a': '8'},
        {'q': '7 + 2', 'a': '9'},
        {'q': '15 - 6', 'a': '9'},
        {'q': '8 + 4', 'a': '12'},
        {'q': '20 - 5', 'a': '15'},
        {'q': '6 + 7', 'a': '13'},
        {'q': '18 - 9', 'a': '9'},
        {'q': '9 + 6', 'a': '15'},
        {'q': '14 - 7', 'a': '7'}
    ],
    'type_word': [
        'speed', 'quick', 'fast', 'rush', 'zoom', 'dash', 'bolt', 
        'race', 'turbo', 'nitro', 'boost', 'power', 'fire', 'flash'
    ],
    'color': [
        {'text': 'RED', 'color': 'blue', 'answer': 'red'},
        {'text': 'BLUE', 'color': 'red', 'answer': 'blue'},
        {'text': 'GREEN', 'color': 'yellow', 'answer': 'green'},
        {'text': 'YELLOW', 'color': 'green', 'answer': 'yellow'},
        {'text': 'PURPLE', 'color': 'orange', 'answer': 'purple'},
        {'text': 'ORANGE', 'color': 'purple', 'answer': 'orange'}
    ]
}

cars = ['🚗', '🚙', '🚕', '🚓', '🏎️']

def generate_room_id():
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))

def generate_unique_guest_name():
    max_attempts = 1000
    for _ in range(max_attempts):
        guest_num = random.randint(1, 1000)
        guest_name = f"Guest{guest_num}"
        name_exists = any(g['name'] == guest_name for g in guests.values())
        if not name_exists:
            return guest_name
    import time
    return f"Guest{int(time.time()) % 10000}"

def calculate_love_score(name1, name2):
    n1 = ''.join(sorted(name1.lower().replace(' ', '')))
    n2 = ''.join(sorted(name2.lower().replace(' ', '')))
    combined = ''.join(sorted([n1, n2]))
    hash_obj = hashlib.md5(combined.encode())
    hash_int = int(hash_obj.hexdigest(), 16)
    score = (hash_int % 90) + 10
    return score

def generate_mini_game():
    game_type = random.choice(['guess_number', 'math', 'type_word', 'color'])
    
    if game_type == 'guess_number':
        answer = random.randint(1, 10)
        return {
            'type': 'guess_number',
            'question': 'Guess the number (1-10)',
            'answer': str(answer)
        }
    elif game_type == 'math':
        game = random.choice(mini_games['math'])
        return {
            'type': 'math',
            'question': game['q'],
            'answer': game['a']
        }
    elif game_type == 'type_word':
        word = random.choice(mini_games['type_word'])
        return {
            'type': 'type_word',
            'question': f'Type: {word}',
            'answer': word
        }
    elif game_type == 'color':
        game = random.choice(mini_games['color'])
        return {
            'type': 'color',
            'question': f'What color is the TEXT?',
            'text': game['text'],
            'color': game['color'],
            'answer': game['answer']
        }

@app.route('/')
def index():
    return render_template('racing.html')

@socketio.on('connect')
def handle_connect():
    session_id = request.sid
    client_ip = request.environ.get('HTTP_X_FORWARDED_FOR', request.remote_addr)
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
        if guest_name in rooms[room_id]['players']:
            rooms[room_id]['players'].remove(guest_name)
        if guest_name in rooms[room_id]['scores']:
            del rooms[room_id]['scores'][guest_name]
        
        if len(rooms[room_id]['players']) == 0:
            del rooms[room_id]
            if room_id in racing_rooms:
                del racing_rooms[room_id]
            print(f"[ROOM] Room {room_id} deleted (empty)")
        else:
            emit('player_left', {
                'players': rooms[room_id]['players'],
                'scores': rooms[room_id]['scores']
            }, room=room_id)
    
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
    
    idx = fortune_cookies.index(fortune)
    if idx < 40:
        category = 'positive'
    elif idx < 70:
        category = 'negative'
    else:
        category = 'maybe'
    
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
    
    rolls = [random.randint(1, dice_sides) for _ in range(num_dice)]
    total = sum(rolls)
    
    rooms[room_id]['scores'][guest_name] += total
    
    emit('dice_rolled', {
        'player': guest_name,
        'rolls': rolls,
        'total': total,
        'scores': rooms[room_id]['scores'],
        'timestamp': datetime.now().strftime('%H:%M:%S')
    }, room=room_id)

# Racing: Start Race
@socketio.on('start_racing')
def handle_start_racing(data):
    session_id = request.sid
    
    if session_id not in guests:
        emit('error', {'message': 'Session not found'})
        return
    
    room_id = guests[session_id].get('room_id')
    
    if not room_id or room_id not in rooms:
        emit('error', {'message': 'Room not found'})
        return
    
    guest_name = guests[session_id]['name']
    
    # Check if owner
    if guest_name != rooms[room_id]['players'][0]:
        emit('error', {'message': 'Only room owner can start race'})
        return
    
    max_players = data.get('max_players', 5)
    if max_players < 2 or max_players > 5:
        emit('error', {'message': 'Max players must be 2-5'})
        return
    
    # Select racers (first N players)
    racers = rooms[room_id]['players'][:max_players]
    
    if len(racers) < 2:
        emit('error', {'message': 'Need at least 2 players to race'})
        return
    
    # Assign random cars
    assigned_cars = random.sample(cars, len(racers))
    
    racing_rooms[room_id] = {
        'racers': racers,
        'cars': {racers[i]: assigned_cars[i] for i in range(len(racers))},
        'positions': {racer: 0 for racer in racers},
        'click_progress': {racer: 0 for racer in racers},
        'click_target': {racer: 20 for racer in racers},
        'items': {racer: {'bomb': 0, 'boost': 0, 'trap': 0} for racer in racers},
        'frozen': {racer: 0 for racer in racers},  # timestamp when unfrozen
        'finished': [],
        'phase': 'countdown',  # countdown, clicking, minigame
        'mini_game': None,
        'game_errors': {racer: 0 for racer in racers},
        'leaderboard': []
    }
    
    # Broadcast countdown
    emit('racing_countdown', {
        'racers': racers,
        'cars': racing_rooms[room_id]['cars']
    }, room=room_id)
    
    print(f"[RACING] {guest_name} started race in {room_id} with {len(racers)} racers")

# Racing: Click Progress
@socketio.on('racing_click')
def handle_racing_click():
    session_id = request.sid
    
    if session_id not in guests:
        return
    
    room_id = guests[session_id].get('room_id')
    guest_name = guests[session_id]['name']
    
    if not room_id or room_id not in racing_rooms:
        return
    
    race = racing_rooms[room_id]
    
    if race['phase'] != 'clicking':
        return
    
    if guest_name not in race['racers']:
        return
    
    if guest_name in race['finished']:
        return
    
    # Check if frozen
    if time.time() < race['frozen'][guest_name]:
        return
    
    race['click_progress'][guest_name] += 1
    
    # Check if completed clicks
    if race['click_progress'][guest_name] >= race['click_target'][guest_name]:
        # Move to mini game
        race['phase'] = 'minigame'
        race['mini_game'] = generate_mini_game()
        race['game_errors'] = {racer: 0 for racer in race['racers']}
        
        emit('racing_minigame', {
            'game': race['mini_game'],
            'positions': race['positions']
        }, room=room_id)
    else:
        emit('racing_click_update', {
            'player': guest_name,
            'progress': race['click_progress'][guest_name],
            'target': race['click_target'][guest_name]
        }, room=room_id)

# Racing: Answer Mini Game
@socketio.on('racing_answer')
def handle_racing_answer(data):
    session_id = request.sid
    
    if session_id not in guests:
        return
    
    room_id = guests[session_id].get('room_id')
    guest_name = guests[session_id]['name']
    answer = data.get('answer', '').strip().lower()
    
    if not room_id or room_id not in racing_rooms:
        return
    
    race = racing_rooms[room_id]
    
    if race['phase'] != 'minigame':
        return
    
    if guest_name not in race['racers']:
        return
    
    if guest_name in race['finished']:
        return
    
    # Check if frozen
    if time.time() < race['frozen'][guest_name]:
        return
    
    correct_answer = race['mini_game']['answer'].lower()
    
    if answer == correct_answer:
        # Correct answer - move forward 10
        race['positions'][guest_name] += 10
        
        # Reset click progress for next round
        race['click_progress'][guest_name] = 0
        
        # Calculate rank bonus
        sorted_positions = sorted(race['positions'].items(), key=lambda x: x[1], reverse=True)
        rank = next((i for i, (p, _) in enumerate(sorted_positions) if p == guest_name), -1)
        
        if rank == 0:
            race['click_target'][guest_name] = 20 + 4
            # 33% chance to get item
            if random.random() < 0.33:
                item_type = random.choice(['bomb', 'boost', 'trap'])
                race['items'][guest_name][item_type] += 1
                emit('racing_item_received', {
                    'player': guest_name,
                    'item': item_type
                }, room=room_id)
        elif rank == 1:
            race['click_target'][guest_name] = 20 + 3
        elif rank == 2:
            race['click_target'][guest_name] = 20 + 2
        else:
            race['click_target'][guest_name] = 20
        
        # Check if finished (150)
        if race['positions'][guest_name] >= 150:
            race['finished'].append(guest_name)
            race['leaderboard'].append({
                'player': guest_name,
                'position': race['positions'][guest_name],
                'rank': len(race['finished'])
            })
            
            emit('racing_player_finished', {
                'player': guest_name,
                'rank': len(race['finished']),
                'leaderboard': race['leaderboard']
            }, room=room_id)
            
            # Check if all finished
            if len(race['finished']) == len(race['racers']):
                emit('racing_game_over', {
                    'leaderboard': race['leaderboard']
                }, room=room_id)
                return
        
        # Move to clicking phase
        race['phase'] = 'clicking'
        
        emit('racing_answer_correct', {
            'player': guest_name,
            'positions': race['positions'],
            'click_targets': race['click_target']
        }, room=room_id)
        
    else:
        # Wrong answer
        race['game_errors'][guest_name] += 1
        
        if race['game_errors'][guest_name] >= 3:
            # Penalty: move back 5
            race['positions'][guest_name] = max(0, race['positions'][guest_name] - 5)
            race['game_errors'][guest_name] = 0
            
            emit('racing_penalty', {
                'player': guest_name,
                'positions': race['positions']
            }, room=room_id)
        else:
            emit('racing_answer_wrong', {
                'player': guest_name,
                'errors': race['game_errors'][guest_name]
            }, room=room_id)

# Racing: Use Item
@socketio.on('racing_use_item')
def handle_racing_use_item(data):
    session_id = request.sid
    
    if session_id not in guests:
        return
    
    room_id = guests[session_id].get('room_id')
    guest_name = guests[session_id]['name']
    item_type = data.get('item')
    target = data.get('target')
    
    if not room_id or room_id not in racing_rooms:
        return
    
    race = racing_rooms[room_id]
    
    if guest_name not in race['racers']:
        return
    
    if guest_name in race['finished']:
        return
    
    if race['items'][guest_name][item_type] <= 0:
        return
    
    race['items'][guest_name][item_type] -= 1
    
    if item_type == 'bomb':
        # Target loses 8 points
        if target and target in race['racers'] and target not in race['finished']:
            race['positions'][target] = max(0, race['positions'][target] - 8)
            emit('racing_item_used', {
                'player': guest_name,
                'item': 'bomb',
                'target': target,
                'positions': race['positions']
            }, room=room_id)
    
    elif item_type == 'boost':
        # Self gains 5 points
        race['positions'][guest_name] += 5
        
        # Check if finished
        if race['positions'][guest_name] >= 150 and guest_name not in race['finished']:
            race['finished'].append(guest_name)
            race['leaderboard'].append({
                'player': guest_name,
                'position': race['positions'][guest_name],
                'rank': len(race['finished'])
            })
            
            emit('racing_player_finished', {
                'player': guest_name,
                'rank': len(race['finished']),
                'leaderboard': race['leaderboard']
            }, room=room_id)
        else:
            emit('racing_item_used', {
                'player': guest_name,
                'item': 'boost',
                'positions': race['positions']
            }, room=room_id)
    
    elif item_type == 'trap':
        # Target frozen for 5 seconds
        if target and target in race['racers'] and target not in race['finished']:
            race['frozen'][target] = time.time() + 5
            emit('racing_item_used', {
                'player': guest_name,
                'item': 'trap',
                'target': target,
                'frozen_until': race['frozen'][target]
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
    
    if guest_name != rooms[room_id]['players'][0]:
        emit('error', {'message': 'Only room owner can reset'})
        return
    
    for player in rooms[room_id]['players']:
        rooms[room_id]['scores'][player] = 0
    
    rooms[room_id]['game_state'] = {}
    
    if room_id in racing_rooms:
        del racing_rooms[room_id]
    
    emit('game_reset', room=room_id)
    print(f"[RESET] {guest_name} reset room {room_id}")

if __name__ == '__main__':
    socketio.run(app, debug=True, host='0.0.0.0', port=5000)