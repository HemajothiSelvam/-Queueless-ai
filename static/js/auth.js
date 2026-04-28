/**
 * auth.js — Client-side validation and form handling for login and registration.
 * All validations run without page reload.
 */

const EMAIL_REGEX = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

// ─── Helpers ────────────────────────────────────────────────────────────────

function showFieldError(fieldId, message) {
    const input = document.getElementById(fieldId);
    const errorEl = document.getElementById(fieldId + "-error");
    if (input) input.classList.add("error");
    if (errorEl) {
        errorEl.textContent = message;
        errorEl.style.display = "block";
    }
}

function clearFieldError(fieldId) {
    const input = document.getElementById(fieldId);
    const errorEl = document.getElementById(fieldId + "-error");
    if (input) input.classList.remove("error");
    if (errorEl) {
        errorEl.textContent = "";
        errorEl.style.display = "none";
    }
}

function showAlert(message, type) {
    const alertBox = document.getElementById("alert-box");
    if (!alertBox) return;
    alertBox.textContent = message;
    alertBox.className = "alert alert-" + type;
    alertBox.style.display = "block";
}

function hideAlert() {
    const alertBox = document.getElementById("alert-box");
    if (alertBox) alertBox.style.display = "none";
}

// ─── Password Strength ───────────────────────────────────────────────────────

/**
 * Returns a score 0–4 and a label for the given password.
 * Criteria: length ≥ 8, has digit, has uppercase, has special char.
 */
function getPasswordStrength(password) {
    if (!password) return { score: 0, label: "" };

    let score = 0;
    if (password.length >= 8) score++;
    if (/\d/.test(password)) score++;
    if (/[A-Z]/.test(password)) score++;
    if (/[^A-Za-z0-9]/.test(password)) score++;

    const labels = ["", "Weak", "Fair", "Good", "Strong"];
    const classes = ["", "strength-weak", "strength-fair", "strength-good", "strength-strong"];
    const widths = ["0%", "25%", "50%", "75%", "100%"];
    const colors = ["", "#e74c3c", "#f39c12", "#27ae60", "#2980b9"];

    return {
        score,
        label: labels[score] || "Weak",
        cssClass: classes[score] || "strength-weak",
        width: widths[score] || "25%",
        color: colors[score] || "#e74c3c"
    };
}

function updateStrengthIndicator(password) {
    const container = document.getElementById("strength-container");
    const fill = document.getElementById("strength-fill");
    const label = document.getElementById("strength-label");
    if (!container || !fill || !label) return;

    if (!password) {
        container.style.display = "none";
        return;
    }

    container.style.display = "block";
    const strength = getPasswordStrength(password);
    fill.style.width = strength.width;
    fill.style.background = strength.color;
    label.textContent = strength.label;
    label.className = "strength-label " + strength.cssClass;
}

// ─── Registration Form ───────────────────────────────────────────────────────

function validateRegisterForm(name, email, phone, password) {
    let valid = true;

    // Name
    clearFieldError("name");
    if (!name.trim()) {
        showFieldError("name", "Full name is required");
        valid = false;
    }

    // Email
    clearFieldError("email");
    if (!email.trim()) {
        showFieldError("email", "Email address is required");
        valid = false;
    } else if (!EMAIL_REGEX.test(email)) {
        showFieldError("email", "Please enter a valid email address");
        valid = false;
    }

    // Phone
    clearFieldError("phone");
    if (!phone.trim()) {
        showFieldError("phone", "Phone number is required");
        valid = false;
    }

    // Password
    clearFieldError("password");
    if (!password) {
        showFieldError("password", "Password is required");
        valid = false;
    } else if (password.length < 8) {
        showFieldError("password", "Password must be at least 8 characters");
        valid = false;
    } else if (!/\d/.test(password)) {
        showFieldError("password", "Password must contain at least one number");
        valid = false;
    }

    return valid;
}

function initRegisterForm() {
    const form = document.getElementById("register-form");
    if (!form) return;

    // Real-time password strength indicator
    const passwordInput = document.getElementById("password");
    if (passwordInput) {
        passwordInput.addEventListener("input", function () {
            updateStrengthIndicator(this.value);
        });
    }

    // Real-time email validation
    const emailInput = document.getElementById("email");
    if (emailInput) {
        emailInput.addEventListener("blur", function () {
            if (this.value && !EMAIL_REGEX.test(this.value)) {
                showFieldError("email", "Please enter a valid email address");
            } else {
                clearFieldError("email");
            }
        });
    }

    form.addEventListener("submit", async function (e) {
        e.preventDefault();
        hideAlert();

        const name = document.getElementById("name").value;
        const email = document.getElementById("email").value;
        const phone = document.getElementById("phone").value;
        const password = document.getElementById("password").value;

        if (!validateRegisterForm(name, email, phone, password)) return;

        const submitBtn = document.getElementById("submit-btn");
        submitBtn.disabled = true;
        submitBtn.textContent = "Creating account…";

        try {
            const response = await fetch("/api/auth/register", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ name, email, phone, password })
            });

            const data = await response.json();

            if (response.ok) {
                showAlert("Account created! Redirecting to login…", "success");
                setTimeout(() => { window.location.href = "/login"; }, 1500);
            } else {
                showAlert(data.error || "Registration failed. Please try again.", "error");
                submitBtn.disabled = false;
                submitBtn.textContent = "Create Account";
            }
        } catch (err) {
            showAlert("Network error. Please check your connection.", "error");
            submitBtn.disabled = false;
            submitBtn.textContent = "Create Account";
        }
    });
}

// ─── Login Form ──────────────────────────────────────────────────────────────

function validateLoginForm(email, password) {
    let valid = true;

    clearFieldError("email");
    if (!email.trim()) {
        showFieldError("email", "Email address is required");
        valid = false;
    } else if (!EMAIL_REGEX.test(email)) {
        showFieldError("email", "Please enter a valid email address");
        valid = false;
    }

    clearFieldError("password");
    if (!password) {
        showFieldError("password", "Password is required");
        valid = false;
    }

    return valid;
}

function initLoginForm() {
    const form = document.getElementById("login-form");
    if (!form) return;

    form.addEventListener("submit", async function (e) {
        e.preventDefault();
        hideAlert();

        const email = document.getElementById("email").value;
        const password = document.getElementById("password").value;

        if (!validateLoginForm(email, password)) return;

        const submitBtn = document.getElementById("submit-btn");
        submitBtn.disabled = true;
        submitBtn.textContent = "Signing in…";

        try {
            const response = await fetch("/api/auth/login", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ email, password })
            });

            const data = await response.json();

            if (response.ok) {
                const role = data.user && data.user.role;
                if (role === "admin") {
                    window.location.href = "/admin/dashboard";
                } else {
                    window.location.href = "/dashboard";
                }
            } else {
                showAlert(data.error || "Login failed. Please try again.", "error");
                submitBtn.disabled = false;
                submitBtn.textContent = "Sign In";
            }
        } catch (err) {
            showAlert("Network error. Please check your connection.", "error");
            submitBtn.disabled = false;
            submitBtn.textContent = "Sign In";
        }
    });
}
