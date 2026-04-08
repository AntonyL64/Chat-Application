# P2P Tracker and Peer System

![Status](https://img.shields.io/badge/Status-Completed-success)
![Course](https://img.shields.io/badge/Course-CO3093%20%2F%20CO3094-blue)
![Type](https://img.shields.io/badge/System-P2P%20Tracker-orange)

A peer-to-peer communication system with a centralized tracker server and reverse proxy, developed at **HCMC University of Technology (HCMUT)**.

The system allows multiple peers to register with a tracker, discover each other, and communicate directly using TCP connections, while also supporting a web interface and REST APIs.

---

## 📌 Overview

This project includes:

* Backend Tracker Server (WeApRous application)
* Reverse Proxy Web Server
* Peer-to-Peer Clients
* Web UI + REST APIs

---

## 🏗️ System Architecture

1. Tracker Server

   * Maintains peer registry
   * Provides peer discovery APIs

2. Reverse Proxy

   * Handles HTTP requests
   * Routes traffic

3. P2P Clients

   * Register with tracker
   * Discover peers
   * Connect via TCP

---

## 📁 Directory Structure

| Path                 | Description          |
| -------------------- | -------------------- |
| `start_backend.py`   | Runs backend tracker |
| `start_proxy.py`     | Runs reverse proxy   |
| `start_sampleapp.py` | Sample app           |
| `apps/peer.py`       | P2P client           |
| `www/`               | HTML UI              |
| `static/`            | Assets               |

---

## 🚀 Getting Started

Open **3 terminals**:

### Terminal 1 – Backend

```
python start_backend.py
```

### Terminal 2 – Proxy

```
python start_proxy.py
```

### Terminal 3 – Sample App

```
python start_sampleapp.py
```

Access:
http://localhost:8080/

---

## 🔐 Authentication

Credentials:
username = admin
password = password

Test:
curl -i http://localhost:8080/

Login:
curl -i -X POST http://localhost:8080/login

Login + Cookie:
curl -i -c cookies.txt -X POST http://localhost:8080/login -d "username=admin&password=password"

Use Cookie:
curl -i -b cookies.txt http://localhost:8080/

---

## 🔗 Tracker API

Submit peer:
curl -i -b cookies.txt -X POST http://localhost:8080/submit-info -H "Content-Type: application/json" -d "{"ip":"127.0.0.1","port":5000}"

Submit with ID:
curl -i -b cookies.txt -X POST http://localhost:8080/submit-info -H "Content-Type: application/json" -d "{"id":"peer1","ip":"127.0.0.1","port":5000}"

Get list:
curl -i -b cookies.txt http://localhost:8080/get-list

Broadcast:
curl -i -b cookies.txt -X POST http://localhost:8080/broadcast-peer -H "Content-Type: application/json" -d "{"from_id":"me","message":"hello"}"

---

## 💬 Chat API

Channels:
curl -i -b cookies.txt http://localhost:8080/channels

Messages:
curl -i -b cookies.txt "http://localhost:8080/messages?channel=general"

Send:
curl -i -b cookies.txt -X POST http://localhost:8080/send -H "Content-Type: application/json" -d "{"channel":"general","sender":"admin","text":"Hello","timestamp":"2025-11-08T10:30:00Z"}"

---

## 🔄 Running Peers

Peer 1:
python apps/peer.py --tracker-host 127.0.0.1 --tracker-port 9000 --listen-port 5000 --id peer1

Peer 2:
python apps/peer.py --tracker-host 127.0.0.1 --tracker-port 9000 --listen-port 5001 --id peer2

Commands:
/refresh
/exit

Send message:
hello from peer1

Expected:
[incoming message] from peer1: hello from peer1

---

## 🧪 Test Flow

```
curl -i -c cookies.txt -X POST http://localhost:8080/login -d "username=admin&password=password"
curl -i -b cookies.txt http://localhost:8080/
curl -i -b cookies.txt http://localhost:8080/get-list
```

---

## ♻️ Reset Cookies

Windows:
del cookies.txt

Linux/Mac:
rm cookies.txt

---

## 🛠 Troubleshooting

* Check firewall ports (5000, 5001)
* Always use cookies.txt after login
* Verify static/ and www/ paths
* Ensure channel exists before sending
* Use `-i` for headers
