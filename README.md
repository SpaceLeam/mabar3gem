# Mabar3gem

[![Tech Stack](https://skillicons.dev/icons?i=py,html,flask)](https://skillicons.dev)

Multiplayer web game. 3 mini games: Love Calculator, Fortune Cookie, Dice Roller. Max 10 players per server.

## Installation

```bash
pip install -r requirements.txt
python server.py
```

Access: `http://localhost:5000`

## Multiplayer Setup

### Option 1: LAN (Same Network)

**Step 1:** Check server IP
```bash
# Windows
ipconfig

# Linux/Mac
ifconfig
```
Note your IPv4 (example: 192.168.1.5)

**Step 2:** Edit `templates/index.html` line 83
```javascript
// Change from
const socket = io(`http://${window.location.hostname}:5000`);

// To
const socket = io();
```

**Step 3:** Players access `http://192.168.1.5:5000` (use your IP)

**server.py already configured correctly:**
```python
socketio.run(app, host='0.0.0.0', port=5000)
```
Do not change this.

### Option 2: Internet (Ngrok)

**Step 1:** Download ngrok from ngrok.com

**Step 2:** Run server
```bash
python server.py
```

**Step 3:** New terminal, run ngrok
```bash
ngrok http 5000
```

**Step 4:** Copy the https URL (example: `https://abc123.ngrok.io`)

**Step 5:** Edit `templates/index.html` line 83
```javascript
const socket = io('https://abc123.ngrok.io');
```

**Step 6:** Share URL to players

### Option 3: Internet (Port Forward)

**Step 1:** Router settings → Port Forwarding → Forward port 5000 to your local IP

**Step 2:** Check public IP at whatismyip.com

**Step 3:** Edit `templates/index.html` line 83
```javascript
const socket = io('http://YOUR_PUBLIC_IP:5000');
```

**Step 4:** Players access `http://YOUR_PUBLIC_IP:5000`

## Troubleshooting

- Connection failed: Allow port 5000 in firewall
- Server full: Max 10 guests globally
- Port in use: Change port in server.py and index.html

## Usage

1. Create Room → Get Room ID
2. Share Room ID
3. Players Join Room → Enter ID
4. Play together

Room owner can reset scores.
