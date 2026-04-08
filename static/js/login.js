const loginForm = document.getElementById('loginForm');
const errorMessage = document.getElementById('errorMessage');

loginForm?.addEventListener('submit', async (e) => {
    e.preventDefault();
    
    const username = document.getElementById('username')?.value.trim();
    const password = document.getElementById('password')?.value.trim();
    const peerId = document.getElementById('peerId')?.value.trim() || generatePeerId();
    
    if (!username) {
        showError('Please enter a username');
        return;
    }
    
    if (!password) {
        showError('Please enter a password');
        return;
    }

    try {
        // First do the login POST - note we're using form-urlencoded as specified in the original code
        const loginResponse = await fetch('login', {
            method: 'POST',
            headers: { 
                'Content-Type': 'application/x-www-form-urlencoded'
            },
            body: `username=${encodeURIComponent(username)}&password=${encodeURIComponent(password)}&peerId=${encodeURIComponent(peerId)}`,
            credentials: 'same-origin'
        });

        if (loginResponse.ok) {
            // After successful login, try to register the peer
            try {
                const peerResponse = await fetch('submit-info', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        id: peerId,
                        ip: window.location.hostname || 'localhost',
                        port: 8000
                    })
                });

                if (!peerResponse.ok) {
                    console.error('Peer registration failed but continuing with login');
                }
            } catch (peerError) {
                console.error('Peer registration error:', peerError);
                // Continue anyway as login was successful
            }

            // Store user info regardless of peer registration
            sessionStorage.setItem('userInfo', JSON.stringify({
                username: username,
                peerId: peerId,
                loginTime: new Date().toISOString()
            }));
            
            // Set auth cookie
            document.cookie = 'auth=true; path=/';
            
            // Log success and redirect
            console.log('Login successful, redirecting...');
            window.location.href = 'index.html';
        } else {
            // Handle specific error cases
            if (loginResponse.status === 401) {
                window.location.href = '401.html';
            } else {
                showError(`Login failed: ${loginResponse.status}`);
            }
            console.error('Login failed:', loginResponse.status);
        }
    } catch (error) {
        showError('Connection failed. Please try again.');
        console.error('Login error:', error);
    }
});

function generatePeerId() {
    return 'peer-' + Math.random().toString(36).substr(2, 9);
}

function showError(message) {
    if (errorMessage) {
        errorMessage.textContent = message;
        errorMessage.classList.add('show');
        setTimeout(() => {
            errorMessage.classList.remove('show');
        }, 3000);
    }
    console.error(message); // Also log errors to console
}

// Check login status on page load
document.addEventListener('DOMContentLoaded', () => {
    const isLoginPage = window.location.pathname.includes('login.html') || window.location.pathname === '';
    const isAuthenticated = document.cookie.includes('auth=true');
    
    if (isAuthenticated && isLoginPage) {
        window.location.href = 'index.html';
    }
    
    // Add form submission logging
    loginForm?.addEventListener('submit', () => {
        console.log('Form submitted');
    });
});