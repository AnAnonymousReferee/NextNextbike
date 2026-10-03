// Validierungsfunktionen
function validateUsername(username) {
    if (!username) return "Username ist erforderlich";
    if (username.length < 3) return "Username muss mindestens 3 Zeichen lang sein";
    if (username.length > 32) return "Username darf maximal 32 Zeichen lang sein";
    if (!/^[A-Za-z0-9_.-]+$/.test(username)) {
        return "Username darf nur Buchstaben, Zahlen, Unterstrich (_), Punkt (.) und Bindestrich (-) enthalten";
    }
    return null;
}

function validateEmail(email) {
    if (!email) return "E-Mail ist erforderlich";
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!emailRegex.test(email)) return "Bitte gib eine gültige E-Mail-Adresse ein";
    return null;
}

function validatePassword(password) {
    if (!password) return "Passwort ist erforderlich";
    if (password.length < 8) return "Passwort muss mindestens 8 Zeichen lang sein";
    if (password.length > 128) return "Passwort darf maximal 128 Zeichen lang sein";
    return null;
}

function showError(elementId, message) {
    const element = document.getElementById(elementId);
    if (!element) return;
    
    // Remove existing error message
    const existingError = element.parentElement.querySelector('.error-message');
    if (existingError) existingError.remove();
    
    if (message) {
        const errorDiv = document.createElement('div');
        errorDiv.className = 'error-message text-red-500 text-sm mt-1';
        errorDiv.textContent = message;
        element.parentElement.appendChild(errorDiv);
        element.classList.add('border-red-500');
        return false;
    } else {
        element.classList.remove('border-red-500');
        return true;
    }
}

// Menüs ein- und ausblenden
function openLoginModal() {
    const registerModal = document.getElementById('register-modal');
    if (registerModal) {
        registerModal.classList.add('hidden');
    }
    const storedApiKey = localStorage.getItem("user_api_key");
    const isLoggedIn = Boolean(storedApiKey || apiKeyUser);

    if (isLoggedIn) {
        handleLogout();
    } else {
        document.getElementById('login-modal').classList.remove('hidden');
    }
}

function closeLoginModal() {
    document.getElementById('login-modal').classList.add('hidden');
}

function openRegisterModal() {
    document.getElementById('login-modal').classList.add('hidden');
    document.getElementById('register-modal').classList.remove('hidden');
}

function closeRegisterModal() {
    document.getElementById('register-modal').classList.add('hidden');
}

function toggleSettingsMenu() {
    const menu = document.getElementById('settings-menu');
    menu.classList.toggle('hidden');
}

// Login verarbeiten und mit map.js synchronisieren
async function handleLogin() {
    const user = document.getElementById('username-input').value;
    const pass = document.getElementById('password-input').value;

    // Validierung
    const userError = validateUsername(user);
    const passError = validatePassword(pass);
    
    showError('username-input', userError);
    showError('password-input', passError);
    
    if (userError || passError) return;

    try {
        const response = await fetch(`${API_BASE_URL}/login`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ username: user, passwort: pass })
        });

        if (!response.ok) {
            showError('username-input', 'Username oder Passwort falsch');
            return;
        }

        const data = await response.json();
        const token = data.api_key;

        localStorage.setItem("user_api_key", token);
        apiKeyUser = token;
        document.getElementById('auth-tab-text').innerText = "Logout";
        closeLoginModal();
        alert("Erfolgreich eingeloggt! Favoriten-Funktion ist jetzt freigeschaltet.");
    } catch (err) {
        console.error(err);
        alert("Verbindung zum Server fehlgeschlagen.");
    }
}
// Registrierung verarbeiten
async function handleRegister() {
    const user = document.getElementById('register-username-input').value;
    const email = document.getElementById('register-email-input').value;
    const pass = document.getElementById('register-password-input').value;

    // Validierung
    const userError = validateUsername(user);
    const emailError = validateEmail(email);
    const passError = validatePassword(pass);
    
    showError('register-username-input', userError);
    showError('register-email-input', emailError);
    showError('register-password-input', passError);
    
    if (userError || emailError || passError) return;

    try {
        const response = await fetch(`${API_BASE_URL}/register`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ username: user, email: email, passwort: pass })
        });

        if (!response.ok) {
            const error = await response.json().catch(() => ({}));
            showError('register-username-input', error.error || "Registrierung fehlgeschlagen. Username oder E-Mail existiert bereits.");
            return;
        }

        closeRegisterModal();
        document.getElementById('username-input').value = user;
        document.getElementById('password-input').value = pass;
        document.getElementById('login-modal').classList.remove('hidden');
        alert("Registrierung erfolgreich. Du kannst dich jetzt einloggen.");
    } catch (err) {
        console.error(err);
        alert("Verbindung zum Server fehlgeschlagen.");
    }
}
// passwort vergessen option
async function handleForgotPassword() {
    const email = prompt("Bitte gib deine E-Mail-Adresse für den Passwort-Reset ein:");

    if (email === null) {
        return;
    }

    const normalizedEmail = email.trim();
    const emailError = validateEmail(normalizedEmail);
    if (emailError) {
        alert(emailError);
        return;
    }

    try {
        const response = await fetch(`${API_BASE_URL}/password-reset`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ email: normalizedEmail })
        });

        if (!response.ok) {
            const error = await response.json().catch(() => ({}));
            alert(error.error || "Passwort-Reset konnte nicht angefordert werden.");
            return;
        }

        alert("Wenn die E-Mail existiert, wurde ein Reset-Link geschickt. Bitte prüfe dein Postfach.");
    } catch (err) {
        console.error(err);
        alert("Verbindung zum Server fehlgeschlagen.");
    }
}

function handleLogout() {
    localStorage.removeItem("user_api_key");
    sessionStorage.clear();

    // Immediate in-memory cleanup so stale state is not visible before reload.
    if (typeof clearRoute === "function") {
        clearRoute();
    }
    if (typeof clearBikeMarkers === "function") {
        clearBikeMarkers();
    }
    if (typeof map !== "undefined" && typeof userMarker !== "undefined" && userMarker) {
        map.removeLayer(userMarker);
        userMarker = null;
    }

    apiKeyUser = "";
    document.getElementById('auth-tab-text').innerText = "Login";

    // Hard reset of map/session UI state after logout (cache-busting fallback).
    const nextUrl = `${window.location.pathname}?logout=${Date.now()}`;
    window.location.replace(nextUrl);
    setTimeout(function () {
        window.location.reload();
    }, 150);
}

// Remove temporary logout cache-busting param from the visible URL.
if (window.location.search.includes("logout=")) {
    window.history.replaceState({}, document.title, window.location.pathname);
}

// Beim Laden der Seite prüfen, ob wir noch eingeloggt sind
if (localStorage.getItem("user_api_key")) {
    apiKeyUser = localStorage.getItem("user_api_key");
    document.getElementById('auth-tab-text').innerText = "Logout";
}