var loginTab = document.getElementById("login-tab");
var registerTab = document.getElementById("register-tab");
var loginSection = document.getElementById("login-section");
var registerSection = document.getElementById("register-section");

loginTab.addEventListener("click", function () {
    loginSection.hidden = false;
    registerSection.hidden = true;
});
registerTab.addEventListener("click", function () {
    loginSection.hidden = true;
    registerSection.hidden = false;
});

document.getElementById("register-form").addEventListener("submit", async function (event) {
    event.preventDefault();
    var form = event.currentTarget;
    var button = form.querySelector("button[type=submit]");
    var username = document.getElementById("register-username").value.trim();
    var password = document.getElementById("register-password").value;
    var confirmPassword = document.getElementById("confirm-password").value;
    var message = document.getElementById("register-message");
    message.style.color = "red";
    if (!username || !password || !confirmPassword) {
        message.textContent = "Please fill in all fields.";
        return;
    }
    if (password !== confirmPassword) {
        message.textContent = "Passwords do not match.";
        return;
    }
    button.disabled = true;
    try {
        await taskApi("/api/register", { method: "POST", body: { username: username, password: password } });
        message.textContent = "Registration successful. Please log in.";
        message.style.color = "green";
        document.getElementById("login-username").value = username;
        form.reset();
        setTimeout(function () { loginTab.click(); }, 1000);
    } catch (error) {
        message.textContent = error.message;
    } finally {
        button.disabled = false;
    }
});

document.getElementById("login-form").addEventListener("submit", async function (event) {
    event.preventDefault();
    var form = event.currentTarget;
    var button = form.querySelector("button[type=submit]");
    var message = document.getElementById("login-message");
    button.disabled = true;
    try {
        await taskApi("/api/login", {
            method: "POST",
            body: {
                username: document.getElementById("login-username").value.trim(),
                password: document.getElementById("login-password").value
            }
        });
        window.location.href = "/index.html";
    } catch (error) {
        message.textContent = error.message;
        message.style.color = "red";
    } finally {
        button.disabled = false;
    }
});
