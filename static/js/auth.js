/**
 * auth.js — Login, register, and auth guard
 *
 * Auth flow:
 *  1. If no token in localStorage → redirect to login (for protected pages).
 *  2. If token exists → validate it server-side via GET /api/auth/me.
 *     If the server rejects it (user deleted, token expired, etc.) → clear
 *     localStorage and redirect to login. This ensures deleting a user from
 *     MongoDB immediately invalidates their session on the next page load.
 */

function clearAuthAndRedirect() {
    localStorage.removeItem("access_token");
    localStorage.removeItem("refresh_token");
    localStorage.removeItem("user");
    window.location.href = "/auth/login";
}

document.addEventListener("DOMContentLoaded", () => {
    const token = localStorage.getItem("access_token");
    const publicPaths = ["/auth/login", "/auth/register", "/"];
    const isPublic = publicPaths.some(p => window.location.pathname === p);

    if (!token) {
        // No token at all — redirect protected pages to login
        if (!isPublic) {
            window.location.href = "/auth/login";
            return;
        }
        applyNavState(false);
        setupHamburger();
        return;
    }

    // Token exists — verify it against the server before trusting it
    fetch("/api/auth/me", {
        headers: { "Authorization": "Bearer " + token }
    })
    .then(res => {
        if (!res.ok) {
            // Server rejected the token (401 = expired/invalid, 404 = user deleted)
            clearAuthAndRedirect();
            return;
        }
        // Token is valid
        if (window.location.pathname === "/auth/login" || window.location.pathname === "/auth/register") {
            window.location.href = "/dashboard";
            return;
        }
        applyNavState(true);
        setupHamburger();
    })
    .catch(() => {
        // Network error — don't log out, just proceed with cached state
        if (window.location.pathname === "/auth/login" || window.location.pathname === "/auth/register") {
            window.location.href = "/dashboard";
            return;
        }
        applyNavState(true);
        setupHamburger();
    });
});

function applyNavState(isLoggedIn) {
    const protectedIds = ["nav-dashboard", "nav-resume", "nav-jobs", "nav-courses", "nav-saved-courses", "nav-ats", "nav-cover", "logout-btn"];
    const loginBtnNav = document.getElementById("login-btn-nav");

    if (isLoggedIn) {
        protectedIds.forEach(id => {
            const el = document.getElementById(id);
            if (el) el.style.display = "";
        });
        if (loginBtnNav) loginBtnNav.style.display = "none";
    } else {
        protectedIds.forEach(id => {
            const el = document.getElementById(id);
            if (el) el.style.display = "none";
        });
        if (loginBtnNav) {
            loginBtnNav.style.display = window.location.pathname === "/auth/login" ? "none" : "";
        }
    }
}

function setupHamburger() {
    // Hamburger nav toggle (backup — also in base.html inline)
    const hamburger = document.getElementById("hamburger");
    const navLinks = document.getElementById("nav-links");
    if (hamburger && navLinks) {
        hamburger.addEventListener("click", () => navLinks.classList.toggle("open"));
    }
}
