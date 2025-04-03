// Main JavaScript file for the MP4 to MP3 converter app

// Check if user is logged in
function isLoggedIn() {
    return localStorage.getItem('token') !== null;
}

// Add token to all fetch requests
const originalFetch = window.fetch;
window.fetch = function(url, options = {}) {
    const token = localStorage.getItem('token');
    if (token) {
        options.headers = options.headers || {};
        options.headers['Authorization'] = `Bearer ${token}`;
    }
    return originalFetch(url, options);
};

// Update navigation based on authentication status
function updateNavigation() {
    const loggedIn = isLoggedIn();

    // Redirect based on auth status and current page
    if (window.location.pathname === '/login' && loggedIn) {
        window.location.href = '/dashboard';
        return;
    }

    if (window.location.pathname === '/dashboard' && !loggedIn) {
        window.location.href = '/login';
        return;
    }

    // Update UI elements based on login status
    document.querySelectorAll('.nav-item').forEach(item => {
        const link = item.querySelector('a');
        if (!link) return;

        // Show/hide nav items based on auth status
        if (loggedIn && (link.getAttribute('href') === '/login')) {
            item.style.display = 'none';
        } else if (!loggedIn && (link.getAttribute('href') === '/dashboard' || link.getAttribute('href') === '/logout')) {
            item.style.display = 'none';
        } else {
            item.style.display = 'block';
        }
    });
}

// Handle logout
function logout() {
    localStorage.removeItem('token');
    window.location.href = '/login';
}

// Add event listeners when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    updateNavigation();

    // Add logout functionality to logout links
    const logoutLinks = document.querySelectorAll('a[href="/logout"]');
    logoutLinks.forEach(link => {
        link.addEventListener('click', function(e) {
            e.preventDefault();
            logout();
        });
    });
});
