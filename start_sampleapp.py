#
# Copyright (C) 2025 pdnguyen of HCMC University of Technology VNU-HCM.
# All rights reserved.
# This file is part of the CO3093/CO3094 course,
# and is released under the "MIT License Agreement". Please see the LICENSE
# file that should have been included as part of this package.
#
# WeApRous release
#
# The authors hereby grant to Licensee personal permission to use
# and modify the Licensed Source Code for the sole purpose of studying
# while attending the course
#


"""
start_sampleapp
~~~~~~~~~~~~~~~~~

This module provides a sample RESTful web application using the WeApRous framework.

It defines basic route handlers and launches a TCP-based backend server to serve
HTTP requests. The application includes a login endpoint and a greeting endpoint,
and can be configured via command-line arguments.
"""

import json
import socket
import argparse
import time
import threading

from daemon.weaprous import WeApRous

PORT = 8000  # Default port

# In-memory registry of peers maintained by the tracker.
# Each entry: {"ip": str, "port": int, "last_seen": float}
PEERS = {}
PEER_TTL = 300.0  # Peers not refreshed within this window are considered inactive

lock = threading.Lock()

app = WeApRous()


def _prune_peers():
    """Remove peers not seen within PEER_TTL."""
    now = time.time()
    with lock:
        to_delete = [k for k, v in PEERS.items() if now - v.get("last_seen", 0) > PEER_TTL]
        for k in to_delete:
            del PEERS[k]

def serve_static_file(file_path, mime_type):
    """Helper to serve static files with proper mime type"""
    try:
        with open(file_path, "rb") as f:
            return {
                "_status": 200,
                "_content": f.read(),
                "_mime": mime_type
            }
    except FileNotFoundError:
        return {
            "_status": 404,
            "_content": b"File not found",
            "_mime": "text/plain"
        }

def check_cookie(headers):
    """Check if auth=true cookie exists"""
    if not isinstance(headers, dict):
        return False
    cookie = headers.get('cookie', '') or headers.get('Cookie', '')
    return 'auth=true' in cookie

# Add routes with both path variations
@app.route('/login.html', methods=['GET'])
def get_login(headers="", body=""):
    return serve_static_file("www/login.html", "text/html")

@app.route('/401.html', methods=['GET'])
def get_401(headers="", body=""):
    return serve_static_file("www/401.html", "text/html")

@app.route('/static/css/login.css', methods=['GET'])
def get_login_css(headers="", body=""):
    return serve_static_file("static/css/login.css", "text/css")

@app.route('/static/css/chat.css', methods=['GET'])
def get_chat_css(headers="", body=""):
    return serve_static_file("static/css/chat.css", "text/css")

@app.route('/static/js/login.js', methods=['GET'])
def get_login_js(headers="", body=""):
    return serve_static_file("static/js/login.js", "application/javascript")

@app.route('/static/js/chat.js', methods=['GET'])
def get_chat_js(headers="", body=""):
    return serve_static_file("static/js/chat.js", "application/javascript")

@app.route('/favicon.ico', methods=['GET'])
def get_favicon(headers="", body=""):
    return {"_status": 200, "_content": b"", "_mime": "image/x-icon"}

# ============================================================================
# Authentication Routes
# ============================================================================

@app.route('/login', methods=['POST'])
def login(headers="", body=""):
    """Handle login - Task 1A"""
    print("\n[LOGIN] POST /login")
    print(f"Body: {body}")
    
    try:
        # Parse form data
        params = {}
        if body:
            for pair in body.split('&'):
                if '=' in pair:
                    k, v = pair.split('=', 1)
                    params[k] = v
        
        username = params.get('username', '')
        password = params.get('password', '')
        
        print(f"Username: {username}, Password: {password}")
        
        # Validate credentials (admin/password)
        if username == 'admin' and password == 'password' or username == 'user1' and password == 'password1' or username == 'user2' and password == 'password2':
            print("✓ Valid credentials - Setting cookie")
            
            # Serve index.html with Set-Cookie header
            with open('www/index.html', 'rb') as f:
                content = f.read()
            
            return {
                "_status": 200,
                "_content": content,
                "_mime": "text/html",
                "Set-Cookie": "auth=true; Path=/; HttpOnly"
            }
        else:
            print("✗ Invalid credentials - 401")
            return {
                "_status": 401,
                "_content": b"<html><body><h1>401 Unauthorized</h1><p>Invalid credentials</p><a href='/login.html'>Try Again</a></body></html>",
                "_mime": "text/html"
            }
    except Exception as e:
        print(f"Login error: {e}")
        return {"error": str(e)}

@app.route('/', methods=['GET'])
@app.route('/index.html', methods=['GET'])
def get_index(headers="", body=""):
    """Serve chat page - Task 1B: Check cookie"""
    print("\n[INDEX] GET /")
    
    if check_cookie(headers):
        print("✓ Cookie valid - Serving chat")
        return serve_static_file("www/index.html", "text/html")
    else:
        print("✗ No cookie - 401")
        return {
            "_status": 401,
            "_content": b"<html><body><h1>401 Unauthorized</h1><p>Please login</p><a href='/login.html'>Login</a></body></html>",
            "_mime": "text/html"
        }

# ============================================================================
# Chat API Routes
# ============================================================================

@app.route('/channels', methods=['GET'])
def get_channels(headers="", body=""):
    """Get list of ONLY chat channels (not users)"""
    print("\n[CHANNELS] GET /channels")
    
    # if not check_cookie(headers):
    #     return {"_status": 401, "_content": b'{"error":"Unauthorized"}', "_mime": "application/json"}
    
    with lock:
        # Return ONLY the CHANNELS list, NOT peers
        channel_list = [{'id': ch, 'name': ch.capitalize(), 'status': 'online'} for ch in CHANNELS]
    
    print(f"Returning {len(channel_list)} channels: {[ch['name'] for ch in channel_list]}")
    return {
        '_status': 200,
        '_content': json.dumps({'channels': channel_list}).encode('utf-8'),
        '_mime': 'application/json'
    }

@app.route('/messages', methods=['GET'])
def get_messages(headers="", body=""):
    """Get messages for a channel"""
    print("\n[MESSAGES] GET /messages")
    
    # Initialize channel at the top to avoid scope issues
    channel = 'general'
    
    # Ensure headers is a dict
    if not isinstance(headers, dict):
        headers = {}
    
    # if not check_cookie(headers):
    #     return {"_status": 401, "_content": b'{"error":"Unauthorized"}', "_mime": "application/json"}
    
    try:   
        # Try to get channel from query string - check multiple sources
        path = headers.get('path', '') or headers.get('Path', '') or ''
        
        # Also check if the path is in other common header locations
        if not path:
            # Try to reconstruct from request line if available
            for key in headers:
                if key.lower() in ['request-uri', 'uri', 'url']:
                    path = headers[key]
                    break
        
        print(f"Path from headers: '{path}'")
        
        if '?' in path:
            query = path.split('?', 1)[1]
            print(f"Query string: {query}")
            for param in query.split('&'):
                if '=' in param:
                    k, v = param.split('=', 1)
                    if k == 'channel':
                        channel = v
                        print(f"Found channel parameter: {channel}")
        else:
            print(f"No query string found in path")
        
        print(f"Using channel: {channel}")
        
        with lock:
            messages = MESSAGES.get(channel, [])
        
        print(f"Returning {len(messages)} messages for channel '{channel}'")
        
        return {
            "_status": 200,
            "_content": json.dumps(messages).encode('utf-8'),
            "_mime": "application/json"
        }
    except Exception as e:
        print(f"ERROR in get_messages for channel '{channel}': {e}")
        import traceback
        traceback.print_exc()
        return {
            "_status": 500,
            "_content": json.dumps({"error": str(e)}).encode('utf-8'),
            "_mime": "application/json"
        }


@app.route('/send', methods=['POST'])
def send_message(headers="", body=""):
    """Send a message"""
    print("\n[SEND] POST /send")
    print(f"Body: {body}")
    
    # if not check_cookie(headers):
    #     return {"_status": 401, "_content": b'{"error":"Unauthorized"}', "_mime": "application/json"}
    
    try:
        data = json.loads(body)
        channel = data.get('channel', 'general')
        
        message = {
            'sender': data.get('sender'),
            'text': data.get('text'),
            'timestamp': data.get('timestamp', time.time())
        }
        
        with lock:
            if channel not in MESSAGES:
                MESSAGES[channel] = []
                if channel not in CHANNELS:
                    CHANNELS.append(channel)
            
            MESSAGES[channel].append(message)
        
        print(f"✓ Message saved: [{message['sender']}] {message['text']}")
        
        return {
            '_status': 200,
            '_content': json.dumps({'status': 'sent'}).encode('utf-8'),
            '_mime': 'application/json'
        }
    except Exception as e:
        print(f"Error: {e}")
        return {
            '_status': 500,
            '_content': json.dumps({'error': str(e)}).encode('utf-8'),
            '_mime': 'application/json'
        }
        
@app.route('/hello', methods=['GET'])
def hello(headers, body):
    return {'message': 'Hello, world!'}


@app.route('/submit-info', methods=['POST'])
def submit_info(headers, body):
    """Register or refresh a peer in the tracker."""
    try:
        data = json.loads(body or "{}")
    except Exception:
        return {"error": "Invalid JSON"}

    ip = data.get('ip')
    port = data.get('port')
    username = data.get('username', 'Anonymous')  # ← Add this
    if not ip or not port:
        return {"error": "Missing IP or port"}

    peer_id = data.get('id') or data.get('peerId') or f"{ip}:{port}"
    now = time.time()
    with lock:
        PEERS[peer_id] = {
            "ip": ip, 
            "port": int(port), 
            "username": username,  # ← Add this
            "last_seen": now
        }

    print(f"✓ Peer registered: {peer_id} ({username})")  # ← Update log
    return {"status": "ok", "id": peer_id, "peers": len(PEERS)}


@app.route('/get-list', methods=['GET'])
def get_list(headers, body):
    """Returns a JSON list of currently-active USERS (peers)"""
    print("\n[GET-LIST] GET /get-list")
    
    # if not check_cookie(headers):
    #     return {"_status": 401, "_content": b'{"error":"Unauthorized"}', "_mime": "application/json"}
    
    _prune_peers()
    with lock:
        peers = [
            {
                "id": pid, 
                "ip": info["ip"], 
                "port": info["port"],
                "username": info.get("username", "Anonymous")
            }
            for pid, info in PEERS.items()
        ]
    
    print(f"Returning {len(peers)} users")
    return {"peers": peers}


@app.route('/connect-peer', methods=['POST'])
def connect_peer(headers, body):
    """
    Tracker-assisted connection helper.

    Request body JSON: {"from_id": "a", "target_id": "b"}
    The tracker will attempt to open a short TCP connection from tracker to target
    to verify reachability and return the result. This is useful for NAT-checks and
    simple connectivity validation but does not proxy messages.
    """
    try:
        data = json.loads(body or "{}")
    except Exception:
        return {"error": "Invalid JSON"}

    target_id = data.get('target_id')
    if not target_id:
        return {"error": "Missing target_id"}

    with lock:
        target = PEERS.get(target_id)
    if not target:
        return {"error": "Unknown target"}

    # Try to open a short TCP connection to the target to test reachability
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(3.0)
    try:
        s.connect((target['ip'], target['port']))
        # Optional lightweight handshake
        payload = json.dumps({"type": "connect_probe", "by": data.get('from_id') or 'tracker'})
        s.sendall(payload.encode('utf-8'))
        s.close()
        return {"status": "ok", "target": target_id}
    except Exception as e:
        return {"status": "unreachable", "error": str(e)}


@app.route('/broadcast-peer', methods=['POST'])
def broadcast_peer(headers, body):
    """
    Broadcast a message to all registered peers.

    Body JSON: {"from_id": "a", "message": "hello"}
    The tracker will open direct TCP connections to each peer and send a small JSON
    payload: {"type":"message","from":from_id,"message":...}
    """
    try:
        data = json.loads(body or "{}")
    except Exception:
        return {"error": "Invalid JSON"}

    message = data.get('message')
    from_id = data.get('from_id')
    if message is None:
        return {"error": "Missing message"}

    _prune_peers()
    sent = 0
    failures = []
    with lock:
        targets = [(pid, info) for pid, info in PEERS.items() if pid != from_id]

    payload = json.dumps({"type": "message", "from": from_id, "message": message}).encode('utf-8')

    # Connect to each peer and send the message; do not block tracker for long
    def _send_to_target(pid, info):
        nonlocal sent
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(3.0)
            s.connect((info['ip'], info['port']))
            s.sendall(payload)
            s.close()
            with lock:
                sent += 1
        except Exception as e:
            with lock:
                failures.append({"target": pid, "error": str(e)})

    threads = []
    for pid, info in targets:
        t = threading.Thread(target=_send_to_target, args=(pid, info), daemon=True)
        t.start()
        threads.append(t)

    # Optionally wait a short while for sends to finish
    for t in threads:
        t.join(timeout=1.0)

    return {"status": "ok", "sent": sent, "failures": failures}

MESSAGES = {'general': [], 'random': [], 'tech': []}  # Channel -> list of messages
CHANNELS = ['general', 'random', 'tech']  # List of channel names

@app.route('create-channel', methods=['POST'])
@app.route('/create-channel', methods=['POST'])
def create_channel(headers="", body=""):
    """Create a new channel"""
    try:
        data = json.loads(body)
        channel_name = data.get('name')
        
        if channel_name and channel_name not in CHANNELS:
            CHANNELS.append(channel_name)
            MESSAGES[channel_name] = []
            
            return {
                '_status': 200,
                '_content': json.dumps({
                    'success': True,
                    'channel': channel_name
                }).encode('utf-8'),
                '_mime': 'application/json'
            }
        else:
            return {
                '_status': 400,
                '_content': json.dumps({
                    'error': 'Invalid channel name or channel already exists'
                }).encode('utf-8'),
                '_mime': 'application/json'
            }
    except Exception as e:
        return {
            '_status': 500,
            '_content': json.dumps({'error': str(e)}).encode('utf-8'),
            '_mime': 'application/json'
        }


if __name__ == "__main__":
    # Parse command-line arguments to configure server IP and port
    parser = argparse.ArgumentParser(prog='Backend', description='', epilog='Backend daemon')
    parser.add_argument('--server-ip', default='0.0.0.0')
    parser.add_argument('--server-port', type=int, default=PORT)

    args = parser.parse_args()
    ip = args.server_ip
    port = args.server_port

    # Prepare and launch the RESTful application
    app.prepare_address(ip, port)
    app.run()