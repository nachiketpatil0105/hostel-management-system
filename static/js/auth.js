// Token helpers
function getToken() {
    return localStorage.getItem("session_token");
}

function getUser() {
    const token = getToken();
    if (!token) return null;
    try {
        const payload = token.split(".")[1];
        return JSON.parse(atob(payload));
    } catch (e) {
        return null;
    }
}

function logout() {
    localStorage.removeItem("session_token");
    window.location.href = "/login";
}

// Redirect to login if no token found
function requireAuth() {
    if (!getToken()) {
        window.location.href = "/login";
    }
}

// Redirect to role dashboard if already logged in
function redirectIfLoggedIn() {
    const user = getUser();
    if (!user) return;
    const role = user.role.toLowerCase();
    const destinations = {
        admin: "/admin/dashboard",
        warden: "/warden/dashboard",
        security: "/security/dashboard",
        student: "/student/profile"
    };
    if (destinations[role]) {
        window.location.href = destinations[role];
    }
}

// Show logged-in user name in navbar if element exists
function setNavUser() {
    const el = document.getElementById("nav-user");
    if (!el) return;
    const user = getUser();
    if (user) el.textContent = user.username + " (" + user.role + ")";
}

document.addEventListener("DOMContentLoaded", function () {
    setNavUser();
});