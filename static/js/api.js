/**
 * Central API client — handles auth headers, JSON parsing, and token refresh.
 */
const API_BASE = "/api";

function getToken() {
    return localStorage.getItem("access_token");
}

async function apiFetch(endpoint, options = {}) {
    const token = getToken();
    const headers = {
        "Content-Type": "application/json",
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
        ...options.headers,
    };

    const response = await fetch(`${API_BASE}${endpoint}`, {
        ...options,
        headers,
    });

    // Auto-refresh on 401
    if (response.status === 401) {
        const refreshed = await refreshAccessToken();
        if (refreshed) {
            headers.Authorization = `Bearer ${getToken()}`;
            return fetch(`${API_BASE}${endpoint}`, { ...options, headers });
        } else {
            logout();
            return null;
        }
    }

    return response;
}

async function refreshAccessToken() {
    const refresh = localStorage.getItem("refresh_token");
    if (!refresh) return false;
    try {
        const res = await fetch(`${API_BASE}/auth/refresh`, {
            method: "POST",
            headers: {
                Authorization: `Bearer ${refresh}`,
                "Content-Type": "application/json",
            },
        });
        if (res.ok) {
            const data = await res.json();
            localStorage.setItem("access_token", data.access_token);
            return true;
        }
    } catch (e) { }
    return false;
}

// Helper methods
const API = {
    get: (url) => apiFetch(url),
    post: (url, body) => apiFetch(url, { method: "POST", body: JSON.stringify(body) }),
    patch: (url, body) => apiFetch(url, { method: "PATCH", body: JSON.stringify(body) }),
    delete: (url) => apiFetch(url, { method: "DELETE" }),
    postForm: async (url, formData) => {
        let token = getToken();
        let headers = { ...(token ? { Authorization: `Bearer ${token}` } : {}) };
        let res = await fetch(`${API_BASE}${url}`, { method: "POST", body: formData, headers });
        if (res.status === 401) {
            const refreshed = await refreshAccessToken();
            if (refreshed) {
                token = getToken();
                headers = { ...(token ? { Authorization: `Bearer ${token}` } : {}) };
                return fetch(`${API_BASE}${url}`, { method: "POST", body: formData, headers });
            } else {
                logout();
                return null;
            }
        }
        return res;
    },
};

function logout() {
    localStorage.removeItem("access_token");
    localStorage.removeItem("refresh_token");
    localStorage.removeItem("user_name");
    window.location.href = "/auth/login";
}

// Guard: redirect to login if no token (call on protected pages)
function requireAuth() {
    if (!getToken()) {
        window.location.href = "/auth/login";
    }
}

// Show a toast notification
function showToast(message, type = "success") {
    const existing = document.getElementById("toast");
    if (existing) existing.remove();

    const toast = document.createElement("div");
    toast.id = "toast";
    toast.textContent = message;
    toast.style.cssText = `
        position: fixed; bottom: 2rem; right: 2rem;
        background: ${type === "success" ? "var(--success)" : type === "error" ? "var(--danger)" : "var(--primary)"};
        color: white; padding: 1rem 1.5rem; border-radius: var(--radius);
        font-family: var(--font); font-weight: 500; font-size: 0.95rem;
        box-shadow: 0 4px 20px rgba(0,0,0,0.3); z-index: 9999;
        animation: slideIn 0.3s ease;
    `;
    document.body.appendChild(toast);
    setTimeout(() => toast.remove(), 3500);
}
