// Simple P2P Chat Client - Multi-channel support (DEBUG VERSION)
(function() {
    const $ = id => document.getElementById(id);
    
    let currentUser = null;
    let currentChannel = 'general';
    let lastMessageCount = 0;
    let channels = [];

    // Initialize
    function init() {
        console.log('[INIT] Starting chat application...');
        
        // Check if logged in
        if (!document.cookie.includes('auth=true')) {
            console.log('[INIT] No auth cookie, redirecting to login');
            window.location.href = '/login.html';
            return;
        }

        // Get user info from sessionStorage, or create default if not found
        let userInfo = sessionStorage.getItem('userInfo');
        if (!userInfo) {
            console.log('[INIT] No sessionStorage, creating default user');
            const defaultPeerId = 'peer-' + Math.random().toString(36).substr(2, 9);
            const defaultUser = {
                username: 'admin',
                peerId: defaultPeerId,
                loginTime: new Date().toISOString()
            };
            sessionStorage.setItem('userInfo', JSON.stringify(defaultUser));
            userInfo = JSON.stringify(defaultUser);
        }

        currentUser = JSON.parse(userInfo);
        console.log('[INIT] Current user:', currentUser);
        $('currentUsername').textContent = currentUser.username;
        
        // Register this user as a peer
        registerPeer();
        
        // Load initial data
        loadChannels();
        loadMessages();
        
        // Start auto-refresh
        setInterval(() => {
            loadChannels();
            loadMessages();
        }, 5000);
        
        console.log('[INIT] Initialization complete');
    }

    // Register as peer
    async function registerPeer() {
        try {
            await fetch('/submit-info', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                credentials: 'same-origin',
                body: JSON.stringify({
                    id: currentUser.peerId,
                    peerId: currentUser.peerId,
                    username: currentUser.username,
                    ip: window.location.hostname,
                    port: 8000
                })
            });
            console.log('[PEER] Registered as peer:', currentUser.username);
        } catch (e) {
            console.error('[PEER] Register failed:', e);
        }
    }

    // Load channels and online users
    async function loadChannels() {
        try {
            // Fetch both in parallel for speed
            const [channelRes, userRes] = await Promise.all([
                fetch('/channels', { credentials: 'same-origin' }),
                fetch('/get-list', { credentials: 'same-origin' })
            ]);
            
            const channelData = await channelRes.json();
            const userData = await userRes.json();
            
            const chatChannels = channelData.channels || [];
            const onlineUsers = userData.peers || [];
            
            console.log('[CHANNELS] Loaded:', chatChannels.length, 'channels,', onlineUsers.length, 'users');
            
            renderSidebar(chatChannels, onlineUsers);
        } catch (e) {
            console.error('[CHANNELS] Load failed:', e);
        }
    }

    // Render sidebar with channels and users separately
    function renderSidebar(chatChannels, onlineUsers) {
        const list = $('usersList');
        let html = '';

        // Render CHANNELS section
        if (chatChannels.length > 0) {
            html += '<div style="padding: 10px 20px; font-size: 12px; color: #999; font-weight: 600;">CHANNELS</div>';
            chatChannels.forEach(channel => {
                const isActive = currentChannel === channel.id;
                html += `
                    <div class="user-item ${isActive ? 'active' : ''}" onclick="selectChannel('${channel.id}', '${channel.name}')">
                        <div class="user-avatar">#</div>
                        <div class="user-details">
                            <div class="user-name">${escapeHtml(channel.name)}</div>
                            <div class="user-status">● ${channel.status}</div>
                        </div>
                    </div>
                `;
            });
        }

        // Render ONLINE USERS section
        html += '<div style="padding: 10px 20px; font-size: 12px; color: #999; font-weight: 600; margin-top: 10px;">ONLINE USERS</div>';
        
        if (onlineUsers.length === 0) {
            html += '<div style="padding: 20px; text-align: center; color: #999; font-size: 14px;">No other users online</div>';
        } else {
            const otherUsers = onlineUsers.filter(user => user.id !== currentUser.peerId);
            
            if (otherUsers.length === 0) {
                html += '<div style="padding: 20px; text-align: center; color: #999; font-size: 14px;">No other users online</div>';
            } else {
                otherUsers.forEach(user => {
                    const username = user.username || 'Anonymous';
                    html += `
                        <div class="user-item">
                            <div class="user-avatar">${username.charAt(0).toUpperCase()}</div>
                            <div class="user-details">
                                <div class="user-name">${escapeHtml(username)}</div>
                                <div class="user-status">● online</div>
                            </div>
                        </div>
                    `;
                });
            }
        }

        list.innerHTML = html;
    }

    // Select a channel
    window.selectChannel = function(channelId, channelName) {
        console.log('[CHANNEL] Switching to channel:', channelId);
        currentChannel = channelId;
        lastMessageCount = -1; // Force reload by setting to -1
        $('messagesHeader').textContent = channelName;
        loadChannels();
        
        // Load messages immediately and show loading state
        const container = $('messagesContainer');
        container.innerHTML = '<div style="padding: 40px; text-align: center; color: #999;">Loading messages...</div>';
        loadMessages();
    }

    // Load messages for current channel
    async function loadMessages() {
        try {
            console.log('[MESSAGES] Loading messages for channel:', currentChannel);
            const url = `/messages?channel=${currentChannel}`;
            console.log('[MESSAGES] Fetching:', url);
            
            const res = await fetch(url, {
                credentials: 'same-origin'
            });
            
            console.log('[MESSAGES] Response status:', res.status);
            
            if (!res.ok) {
                console.error('[MESSAGES] Response not OK:', res.status, res.statusText);
                return;
            }
            
            const messages = await res.json();
            console.log('[MESSAGES] Received', messages.length, 'messages:', messages);
            
            // Always update if message count changed
            if (messages.length !== lastMessageCount) {
                console.log('[MESSAGES] Message count changed from', lastMessageCount, 'to', messages.length);
                lastMessageCount = messages.length;
                renderMessages(messages);
            } else {
                console.log('[MESSAGES] No change in message count');
            }
        } catch (e) {
            console.error('[MESSAGES] Load failed:', e);
        }
    }

    // Render messages
    function renderMessages(messages) {
        console.log('[RENDER] Rendering', messages.length, 'messages');
        const container = $('messagesContainer');
        
        if (!messages || messages.length === 0) {
            console.log('[RENDER] No messages, showing empty state');
            container.innerHTML = `
                <div class="empty-state">
                    <div class="empty-state-icon">💬</div>
                    <p>No messages yet. Say hello!</p>
                </div>
            `;
            return;
        }

        const wasScrolledToBottom = container.scrollHeight - container.scrollTop <= container.clientHeight + 50;

        container.innerHTML = messages.map(msg => {
            const isSent = msg.sender === currentUser.username;
            const time = new Date(msg.timestamp * 1000).toLocaleTimeString([], {hour: '2-digit', minute: '2-digit'});
            
            return `
                <div class="message ${isSent ? 'sent' : 'received'}">
                    <div class="message-header">
                        <span class="message-sender">${escapeHtml(msg.sender)}</span>
                        <span class="message-time">${time}</span>
                    </div>
                    <div class="message-bubble">${escapeHtml(msg.text)}</div>
                </div>
            `;
        }).join('');

        console.log('[RENDER] Messages rendered successfully');

        if (wasScrolledToBottom) {
            container.scrollTop = container.scrollHeight;
        }
    }

    // Send message
    async function sendMessage() {
        const input = $('messageInput');
        const text = input.value.trim();
        
        if (!text) {
            console.log('[SEND] Empty message, ignoring');
            return;
        }

        const payload = {
            sender: currentUser.username,
            text: text,
            timestamp: Date.now() / 1000,
            channel: currentChannel
        };

        console.log('[SEND] Sending message to channel:', currentChannel);
        console.log('[SEND] Payload:', payload);

        try {
            const res = await fetch('/send', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                credentials: 'same-origin',
                body: JSON.stringify(payload)
            });

            console.log('[SEND] Response status:', res.status);
            
            if (res.ok) {
                const result = await res.json();
                console.log('[SEND] Response:', result);
                
                input.value = '';
                console.log('[SEND] Message sent successfully, reloading messages...');
                
                // Force reload messages
                lastMessageCount = 0;
                await loadMessages();
            } else {
                console.error('[SEND] Failed with status:', res.status);
                alert('Failed to send message');
            }
        } catch (e) {
            console.error('[SEND] Error:', e);
            alert('Failed to send message: ' + e.message);
        }
    }

    // Logout
    function logout() {
        sessionStorage.removeItem('userInfo');
        document.cookie = 'auth=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/;';
        window.location.href = '/login.html';
    }

    // Escape HTML
    function escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    // Event handlers
    window.addEventListener('load', () => {
        init();
        
        $('sendBtn').addEventListener('click', () => {
            console.log('[UI] Send button clicked');
            sendMessage();
        });
        
        $('messageInput').addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                console.log('[UI] Enter key pressed');
                e.preventDefault();
                sendMessage();
            }
        });
        
        $('logoutBtn').addEventListener('click', logout);
        
        $('mobileMenuBtn').addEventListener('click', () => {
            $('sidebar').classList.toggle('mobile-open');
        });
    });
})();