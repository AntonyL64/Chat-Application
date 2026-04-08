import socket
import threading
import json
import time
import argparse


class Peer:
    """Lightweight peer supporting registration with a tracker, direct P2P connections,
    and broadcast messaging to connected peers.

    This peer uses raw TCP sockets. The tracker endpoints expect HTTP requests, so
    helper methods craft minimal HTTP requests for tracker interactions.
    """

    def __init__(self, tracker_host, tracker_port, listen_host='0.0.0.0', listen_port=10001, peer_id=None):
        self.tracker_host = tracker_host
        self.tracker_port = tracker_port
        self.listen_host = listen_host
        self.listen_port = listen_port
        self.id = peer_id or f"{self._get_local_ip()}:{self.listen_port}"

        # Connected peers: id -> socket
        self.peers = {}
        self.peers_lock = threading.Lock()
        self.listener = None
        self.running = False

    def _get_local_ip(self):
        # Try to obtain a usable local IP
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except Exception:
            return '127.0.0.1'

    def _send_http_request(self, host, port, path, method='GET', body=None, headers=None):
        if headers is None:
            headers = {}
        body_bytes = b''
        if body is not None:
            if isinstance(body, (dict, list)):
                body_bytes = json.dumps(body).encode('utf-8')
                headers['Content-Type'] = 'application/json'
            elif isinstance(body, str):
                body_bytes = body.encode('utf-8')
            else:
                body_bytes = body
        headers['Content-Length'] = str(len(body_bytes))
        req = f"{method} {path} HTTP/1.1\r\nHost: {host}:{port}\r\n"
        for k, v in headers.items():
            req += f"{k}: {v}\r\n"
        req += "\r\n"
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(4.0)
            s.connect((host, port))
            s.sendall(req.encode('utf-8') + body_bytes)
            data = b""
            while True:
                chunk = s.recv(4096)
                if not chunk:
                    break
                data += chunk
            s.close()
            # Split header/body
            parts = data.split(b"\r\n\r\n", 1)
            if len(parts) == 2:
                body = parts[1]
                try:
                    return body.decode('utf-8')
                except Exception:
                    return body
            return data.decode('utf-8', errors='ignore')
        except Exception as e:
            return json.dumps({"error": str(e)})

    def register(self):
        body = {"id": self.id, "ip": self._get_local_ip(), "port": self.listen_port}
        resp = self._send_http_request(self.tracker_host, self.tracker_port, '/submit-info', 'POST', body)
        try:
            return json.loads(resp)
        except Exception:
            return {"raw": resp}

    def get_peers(self):
        resp = self._send_http_request(self.tracker_host, self.tracker_port, '/get-list', 'GET')
        try:
            data = json.loads(resp)
            return data.get('peers', [])
        except Exception:
            return []

    def connect_to_peers(self, refresh_from_tracker=True):
        if refresh_from_tracker:
            peers = self.get_peers()
        else:
            peers = []
        for p in peers:
            pid = p.get('id')
            if not pid or pid == self.id:
                continue
            ip = p.get('ip')
            port = p.get('port')
            if not ip or not port:
                continue
            with self.peers_lock:
                if pid in self.peers:
                    continue
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                s.settimeout(4.0)
                s.connect((ip, port))
                # Connection succeeded; switch to blocking mode so recv doesn't
                # raise socket.timeout and cause the socket to be closed.
                try:
                    s.settimeout(None)
                except Exception:
                    pass
                # Start a receiver thread for this socket
                t = threading.Thread(target=self._peer_receiver, args=(pid, s), daemon=True)
                t.start()
                with self.peers_lock:
                    self.peers[pid] = s
                print(f"Connected to peer {pid}")
            except Exception as e:
                print(f"Failed to connect to {pid}: {e}")

    def _peer_receiver(self, pid, sock):
        # Read messages from an established peer socket; on error, remove socket
        try:
            while True:
                data = sock.recv(4096)
                if not data:
                    break
                try:
                    txt = data.decode('utf-8')
                    # If it looks like HTTP request, find body
                    body = txt.split('\r\n\r\n', 1)[1] if '\r\n\r\n' in txt else txt
                    try:
                        payload = json.loads(body)
                    except Exception:
                        # Fallback: try whole data
                        try:
                            payload = json.loads(txt)
                        except Exception:
                            payload = {"raw": body}
                    # Handle types
                    ptype = payload.get('type') if isinstance(payload, dict) else None
                    print(
                        f"[incoming message] from {payload.get('from')}: {payload.get('message')}"
                        if ptype == 'message'
                        else f"[incoming] {body}"
                    )
                except Exception:
                    txt = str(data)
                    print(f"[msg from {pid}] {txt}")
        except Exception:
            pass
        finally:
            with self.peers_lock:
                if pid in self.peers and self.peers[pid] is sock:
                    del self.peers[pid]
            try:
                sock.close()
            except Exception:
                pass
            print(f"Connection to {pid} closed")

    def start_listener(self):
        self.running = True
        self.listener = threading.Thread(target=self._listener_thread, daemon=True)
        self.listener.start()

    def _listener_thread(self):
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind((self.listen_host, self.listen_port))
        s.listen(10)
        print(f"Peer listening on {self.listen_host}:{self.listen_port}")
        while self.running:
            try:
                conn, addr = s.accept()
                # Spawn handler thread
                t = threading.Thread(target=self._incoming_handler, args=(conn, addr), daemon=True)
                t.start()
            except Exception:
                time.sleep(0.1)
        s.close()

    def _incoming_handler(self, conn, addr):
        # Accept a new incoming connection and read a single message then keep the socket
        # for potential two-way comms. The tracker may perform quick probes too.
        try:
            data = conn.recv(4096)
            if not data:
                conn.close()
                return
            # Try to parse as JSON
            try:
                txt = data.decode('utf-8')
                # If it looks like HTTP request, find body
                if '\r\n\r\n' in txt:
                    body = txt.split('\r\n\r\n', 1)[1]
                else:
                    body = txt
                payload = None
                try:
                    payload = json.loads(body)
                except Exception:
                    # Fallback: try whole data
                    try:
                        payload = json.loads(txt)
                    except Exception:
                        payload = {"raw": body}
                # Handle types
                ptype = payload.get('type') if isinstance(payload, dict) else None
                if ptype == 'connect_probe':
                    # Tracker/peer is probing reachability; reply briefly
                    reply = json.dumps({"type": "probe_ack", "to": payload.get('by')})
                    conn.sendall(reply.encode('utf-8'))
                    conn.close()
                    return
                elif ptype == 'message':
                    print(f"[incoming message] from {payload.get('from')}: {payload.get('message')}")
                    # Keep connection open for future messages
                    # ensure the accepted socket is in blocking mode so receiver
                    # will not be interrupted by a timeout
                    try:
                        conn.settimeout(None)
                    except Exception:
                        pass
                    with self.peers_lock:
                        pid = payload.get('from') or f"{addr[0]}:{addr[1]}"
                        self.peers[pid] = conn
                    # Start receiver loop on this socket
                    self._peer_receiver(pid, conn)
                    return
                else:
                    # Treat as generic text message
                    print(f"[incoming] {body}")
                    conn.close()
                    return
            except Exception as e:
                print(f"Error parsing incoming: {e}")
                conn.close()
        except Exception:
            try:
                conn.close()
            except Exception:
                pass

    def broadcast(self, message):
        with self.peers_lock:
            targets = list(self.peers.items())
        payload = json.dumps({"type": "message", "from": self.id, "message": message}).encode('utf-8')
        for pid, s in targets:
            try:
                s.sendall(payload)
            except Exception as e:
                print(f"send to {pid} failed: {e}")
                with self.peers_lock:
                    if pid in self.peers:
                        try:
                            self.peers[pid].close()
                        except Exception:
                            pass
                        del self.peers[pid]

    def stop(self):
        self.running = False
        with self.peers_lock:
            for s in self.peers.values():
                try:
                    s.close()
                except Exception:
                    pass
            self.peers.clear()


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--tracker-host', default='127.0.0.1')
    parser.add_argument('--tracker-port', type=int, default=8000)
    parser.add_argument('--listen-port', type=int, default=10001)
    parser.add_argument('--id', default=None)
    args = parser.parse_args()

    peer = Peer(args.tracker_host, args.tracker_port, listen_port=args.listen_port, peer_id=args.id)
    peer.start_listener()
    print('Registering with tracker...')
    print(peer.register())
    time.sleep(0.2)
    print('Fetching peer list...')
    peers = peer.get_peers()
    print('Peers:', peers)
    print('Connecting to peers...')
    peer.connect_to_peers()

    try:
        while True:
            line = input('> ')
            if not line:
                continue
            if line.strip() == '/refresh':
                print('Refreshing peer list and reconnecting...')
                peer.connect_to_peers(refresh_from_tracker=True)
                continue
            if line.strip() == '/exit':
                break
            # Check for private message command
            if line.startswith('/msg '):
                # Format: /msg <peer_id> <message>
                parts = line.split(' ', 2)
                if len(parts) < 3:
                    print("Usage: /msg <peer_id> <message>")
                    continue
                target_id, msg = parts[1], parts[2]
                with peer.peers_lock:
                    sock = peer.peers.get(target_id)
                if sock:
                    payload = json.dumps({"type": "message", "from": peer.id, "message": msg}).encode('utf-8')
                    try:
                        sock.sendall(payload)
                        print(f"✓ Message sent to {target_id}")
                    except Exception as e:
                        print(f"Failed to send to {target_id}: {e}")
                else:
                    print(f"Peer {target_id} not connected")
                continue
            # Broadcast to all connected peers
            peer.broadcast(line)

    except KeyboardInterrupt:
        pass
    finally:
        peer.stop()
        print('Stopped')
