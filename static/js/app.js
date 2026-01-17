const API_BASE = '/api';
let currentUser = null;

// Get CSRF token
function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}

const csrftoken = getCookie('csrftoken');

// API call wrapper
async function apiCall(endpoint, options = {}) {
    const defaultOptions = {
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': csrftoken
        },
        credentials: 'same-origin'
    };
    
    const response = await fetch(`${API_BASE}${endpoint}`, {
        ...defaultOptions,
        ...options,
        headers: { ...defaultOptions.headers, ...options.headers }
    });
    
    if (!response.ok) {
        const error = await response.json().catch(() => ({ error: 'Request failed' }));
        throw new Error(error.error || 'Request failed');
    }
    
    return response.json();
}

// Toast notifications
function showToast(message, type = 'success') {
    const container = document.getElementById('toastContainer');
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.innerHTML = `
        <i class="fas fa-${type === 'success' ? 'check-circle' : 'exclamation-circle'}"></i>
        <span>${message}</span>
    `;
    
    container.appendChild(toast);
    
    setTimeout(() => {
        toast.remove();
    }, 3000);
}

// ============================================================================
// AUTHENTICATION
// ============================================================================

async function checkAuth() {
    try {
        currentUser = await apiCall('/auth/me/');
    } catch (error) {
        currentUser = null;
    }
}

// Login
document.getElementById('loginForm')?.addEventListener('submit', async function(e) {
    e.preventDefault();
    
    const formData = new FormData(this);
    const data = Object.fromEntries(formData.entries());
    
    try {
        await apiCall('/auth/login/', {
            method: 'POST',
            body: JSON.stringify(data)
        });
        
        showToast('Login successful!', 'success');
        setTimeout(() => window.location.reload(), 1000);
    } catch (error) {
        showToast(error.message, 'error');
    }
});

// Sign up
document.getElementById('signupForm')?.addEventListener('submit', async function(e) {
    e.preventDefault();
    
    const formData = new FormData(this);
    const data = Object.fromEntries(formData.entries());
    
    try {
        await apiCall('/auth/register/', {
            method: 'POST',
            body: JSON.stringify(data)
        });
        
        showToast('Account created successfully!', 'success');
        setTimeout(() => window.location.reload(), 1000);
    } catch (error) {
        showToast(error.message, 'error');
    }
});

// Logout
document.getElementById('logoutBtn')?.addEventListener('click', async function(e) {
    e.preventDefault();
    
    try {
        await apiCall('/auth/logout/', { method: 'POST' });
        showToast('Logged out successfully', 'success');
        setTimeout(() => window.location.href = '/', 1000);
    } catch (error) {
        showToast(error.message, 'error');
    }
});

// ============================================================================
// MODAL MANAGEMENT
// ============================================================================

function openModal(modalId) {
    document.getElementById(modalId).classList.add('show');
}

function closeModal(modalId) {
    document.getElementById(modalId).classList.remove('show');
}

// Login/Signup buttons
document.getElementById('loginBtn')?.addEventListener('click', (e) => {
    e.preventDefault();
    openModal('loginModal');
});

document.getElementById('signupBtn')?.addEventListener('click', (e) => {
    e.preventDefault();
    openModal('signupModal');
});

// Switch between login and signup
document.getElementById('switchToSignup')?.addEventListener('click', (e) => {
    e.preventDefault();
    closeModal('loginModal');
    openModal('signupModal');
});

document.getElementById('switchToLogin')?.addEventListener('click', (e) => {
    e.preventDefault();
    closeModal('signupModal');
    openModal('loginModal');
});

// Close modal buttons
document.querySelectorAll('.close-modal').forEach(btn => {
    btn.addEventListener('click', function() {
        this.closest('.modal').classList.remove('show');
    });
});

// Close modal on outside click
document.querySelectorAll('.modal').forEach(modal => {
    modal.addEventListener('click', function(e) {
        if (e.target === this) {
            this.classList.remove('show');
        }
    });
});

// ============================================================================
// USER MENU
// ============================================================================

document.getElementById('userMenuBtn')?.addEventListener('click', function(e) {
    e.stopPropagation();
    document.getElementById('userDropdown').classList.toggle('show');
});

// Close dropdown when clicking outside
document.addEventListener('click', function(e) {
    const dropdown = document.getElementById('userDropdown');
    if (dropdown && !e.target.closest('.user-menu')) {
        dropdown.classList.remove('show');
    }
});

// ============================================================================
// SEARCH
// ============================================================================

let searchTimeout;
document.getElementById('searchInput')?.addEventListener('input', function(e) {
    clearTimeout(searchTimeout);
    
    const query = e.target.value.trim();
    if (query.length < 2) return;
    
    searchTimeout = setTimeout(() => {
        performSearch(query);
    }, 500);
});

async function performSearch(query) {
    try {
        const results = await apiCall(`/videos/?search=${encodeURIComponent(query)}`);
        // Display search results (implement as needed)
        console.log('Search results:', results);
    } catch (error) {
        console.error('Search error:', error);
    }
}

// Initialize
document.addEventListener('DOMContentLoaded', function() {
    checkAuth();
});