## README.txt
CO3093 / CO3094 – P2P Tracker and Peer System  
HCMC University of Technology – bksysnet

This project implements:
1. A backend tracker server (WeApRous application)  
2. A reverse proxy web server  
3. Peer-to-peer clients that register and communicate via the tracker  

Directory structure (important folders):  
start_backend.py        → Runs the backend tracker  
start_proxy.py          → Runs the reverse proxy (optional)  
start_sampleapp.py      → Sample app & route testing  
apps/peer.py            → P2P client program  
www/                    → HTML UI files  
static/                 → CSS and images  

---
1. Running the system
---
Open three terminal windows.

Terminal 1 – Start the backend server:  
python start_backend.py

Terminal 2 – Start the reverse proxy (frontend server):  
python start_proxy.py

Terminal 3 – Start the sample application version:  
python start_sampleapp.py

Access in browser:  
http://localhost:8080/

---
2. Web Login Authentication (Task 1A / 1B)
---
Login expects:  
`username = admin`  
`password = password`

Test root path (unauthenticated - should return 401):  
curl -i "http://localhost:8080/"

Test login (unauthenticated request):  
curl -i -X POST "http://localhost:8080/login"

Submit valid login and store cookie:  
curl -i -c cookies.txt -X POST "http://localhost:8080/login" -d "username=admin&password=password"

Access home page with stored cookie:  
curl -i -b cookies.txt "http://localhost:8080/"

Access index.html directly:  
curl -i -b cookies.txt "http://localhost:8080/index.html"

Invalid login:  
curl -i -X POST "http://localhost:8080/login" -d "username=foo&password=bar"

---
3. Tracker API Testing
---
Submit a peer:  
curl -i -b cookies.txt -X POST "http://localhost:8080/submit-info" -H "Content-Type: application/json" -d "{\"ip\":\"127.0.0.1\",\"port\":5000}"

Submit a peer with custom ID:  
curl -i -b cookies.txt -X POST "http://localhost:8080/submit-info" -H "Content-Type: application/json" -d "{\"id\":\"peer1\",\"ip\":\"127.0.0.1\",\"port\":5000}"

Get peer list:  
curl -i -b cookies.txt "http://localhost:8080/get-list"

Connect peer reachability test (may fail if peer not running):  
curl -i -b cookies.txt -X POST "http://localhost:8080/connect-peer" -H "Content-Type: application/json" -d "{\"from_id\":\"me\",\"target_id\":\"127.0.0.1:5000\"}"

Broadcast a message to all peers registered:  
curl -i -b cookies.txt -X POST "http://localhost:8080/broadcast-peer" -H "Content-Type: application/json" -d "{\"from_id\":\"me\",\"message\":\"hello all\"}"

Simple test endpoint:  
curl -i -b cookies.txt "http://localhost:8080/hello"

---
4. Chat/Channel API Testing
---
Get list of channels:  
curl -i -b cookies.txt "http://localhost:8080/channels"

Get messages from a channel:  
curl -i -b cookies.txt "http://localhost:8080/messages?channel=general"

Send a message to a channel:  
curl -i -b cookies.txt -X POST "http://localhost:8080/send" -H "Content-Type: application/json" -d "{\"channel\":\"general\",\"sender\":\"admin\",\"text\":\"Hello everyone!\",\"timestamp\":\"2025-11-08T10:30:00Z\"}"

Create a new channel:  
curl -i -b cookies.txt -X POST "http://localhost:8080/create-channel" -H "Content-Type: application/json" -d "{\"name\":\"developers\"}"

Get messages from the new channel:  
curl -i -b cookies.txt "http://localhost:8080/messages?channel=developers"

Send message to new channel:  
curl -i -b cookies.txt -X POST "http://localhost:8080/send" -H "Content-Type: application/json" -d "{\"channel\":\"developers\",\"sender\":\"admin\",\"text\":\"Welcome to developers channel\",\"timestamp\":\"2025-11-08T10:35:00Z\"}"

---
5. Static File Testing
---
Get login page:  
curl -i "http://localhost:8080/login.html"

Get login CSS:  
curl -i "http://localhost:8080/static/css/login.css"

Get login JavaScript:  
curl -i "http://localhost:8080/static/js/login.js"

Get chat CSS:  
curl -i -b cookies.txt "http://localhost:8080/static/css/chat.css"

Get chat JavaScript:  
curl -i -b cookies.txt "http://localhost:8080/static/js/chat.js"

Get 401 error page:  
curl -i "http://localhost:8080/401.html"

Get favicon:  
curl -i "http://localhost:8080/favicon.ico"

---
6. Running P2P Peers
---
Open 2 separate terminals.

Peer #1:  
python apps/peer.py --tracker-host 127.0.0.1 --tracker-port 9000 --listen-port 5000 --id peer1

Peer #2:  
python apps/peer.py --tracker-host 127.0.0.1 --tracker-port 9000 --listen-port 5001 --id peer2

Peers will:
1. Register automatically using `/submit-info`  
2. Fetch peer list via `/get-list`  
3. Attempt direct TCP peer-to-peer connections  

To manually refresh connection list:  
> /refresh

To send message to all connected peers:  
> hello from peer1

Expected output in the other peer terminal:  
[incoming message] from peer1: hello from peer1

To exit a peer:  
> /exit

---
7. Complete API Test Sequence
---
# Step 1: Login and save cookie
curl -i -c cookies.txt -X POST "http://localhost:8080/login" -d "username=admin&password=password"

# Step 2: Access authenticated homepage
curl -i -b cookies.txt "http://localhost:8080/"

# Step 3: Register two peers
curl -i -b cookies.txt -X POST "http://localhost:8080/submit-info" -H "Content-Type: application/json" -d "{\"id\":\"peer1\",\"ip\":\"127.0.0.1\",\"port\":5000}"
curl -i -b cookies.txt -X POST "http://localhost:8080/submit-info" -H "Content-Type: application/json" -d "{\"id\":\"peer2\",\"ip\":\"127.0.0.1\",\"port\":5001}"

# Step 4: Get peer list
curl -i -b cookies.txt "http://localhost:8080/get-list"

# Step 5: Get available channels
curl -i -b cookies.txt "http://localhost:8080/channels"

# Step 6: Send messages to general channel
curl -i -b cookies.txt -X POST "http://localhost:8080/send" -H "Content-Type: application/json" -d "{\"channel\":\"general\",\"sender\":\"peer1\",\"text\":\"Hi from peer1\",\"timestamp\":\"2025-11-08T10:00:00Z\"}"
curl -i -b cookies.txt -X POST "http://localhost:8080/send" -H "Content-Type: application/json" -d "{\"channel\":\"general\",\"sender\":\"peer2\",\"text\":\"Hi from peer2\",\"timestamp\":\"2025-11-08T10:01:00Z\"}"

# Step 7: Retrieve messages
curl -i -b cookies.txt "http://localhost:8080/messages?channel=general"

# Step 8: Create new channel
curl -i -b cookies.txt -X POST "http://localhost:8080/create-channel" -H "Content-Type: application/json" -d "{\"name\":\"testing\"}"

# Step 9: Test broadcast to peers
curl -i -b cookies.txt -X POST "http://localhost:8080/broadcast-peer" -H "Content-Type: application/json" -d "{\"from_id\":\"peer1\",\"message\":\"Broadcasting to all\"}"

---
***To reset cookies: del cookies.txt (Windows) or rm cookies.txt (Linux/Mac)
---

8. Troubleshooting
---
* If peer connect fails: ensure listen ports (5000, 5001, etc.) are not blocked by Windows Firewall.  
* If login does not work: ensure `Set-Cookie` returned, and use `-b cookies.txt` with curl.  
* If page loads but images/CSS missing: check that static/ and www/ folders are correctly located.
* If 401 error on APIs: ensure you're using `-b cookies.txt` to send the auth cookie.
* If channel messages not appearing: verify the channel exists with `/channels` first.
* To see detailed response headers: use `-i` flag with curl commands.
* To see only headers: use `-I` flag with curl commands.