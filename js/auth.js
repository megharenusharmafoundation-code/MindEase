(function () {
  function getOrCreateMessageNode(formId) {
    var form = document.getElementById(formId);
    if (!form) return null;
    var msg = form.parentElement.querySelector(".auth-message[data-for='" + formId + "']");
    if (!msg) {
      msg = document.createElement("p");
      msg.className = "auth-message";
      msg.setAttribute("data-for", formId);
      msg.style.marginTop = "0.75rem";
      msg.style.fontSize = "0.95rem";
      form.insertAdjacentElement("afterend", msg);
    }
    return msg;
  }

  function showMessage(formId, text, type) {
    var node = getOrCreateMessageNode(formId);
    if (!node) return;
    node.textContent = text || "";
    node.style.color = type === "success" ? "#2D5F4F" : "#C67C6E";
  }

  async function postJson(url, payload) {
    var response = await fetch(url, {
      method: "POST",
      headers: {
        "Content-Type": "application/json"
      },
      body: JSON.stringify(payload || {})
    });

    var data = {};
    try {
      data = await response.json();
    } catch (err) {
      data = {};
    }

    if (!response.ok) {
      throw new Error(data.error || "Request failed");
    }

    return data;
  }

  function storeSession(data) {
    if (!data || !data.access_token || !data.user) return;

    localStorage.setItem("mindease_session_user", data.user.email || data.user.id || "mindease");
    localStorage.setItem("mindease_token", data.access_token);
    localStorage.setItem("mindease_user", JSON.stringify({
      uid: data.user.id || "",
      email: data.user.email || ""
    }));
  }

  function init(app) {
    var loginForm = document.getElementById("login-form");
    var signupForm = document.getElementById("signup-form");
    var loginContainer = document.getElementById("login-form-container");
    var signupContainer = document.getElementById("signup-form-container");

    if (signupForm) {
      signupForm.addEventListener("submit", async function (e) {
        e.preventDefault();
        showMessage("signup-form", "Creating account...", "success");

        var email = (document.getElementById("signup-email")?.value || "").trim();
        var password = document.getElementById("signup-password")?.value || "";
        var confirm = document.getElementById("signup-confirm")?.value || "";

        if (password !== confirm) {
          showMessage("signup-form", "Passwords do not match.", "error");
          return;
        }
        if (password.length < 6) {
          showMessage("signup-form", "Password must be at least 6 characters.", "error");
          return;
        }

        try {
          var signupData = await postJson("/api/register", {
            email: email,
            password: password
          });

          if (signupData.access_token && signupData.user) {
            storeSession(signupData);
            if (app && typeof app.navigateTo === "function") {
              app.navigateTo("welcome");
            }
            return;
          }

          if (signupContainer && loginContainer) {
            signupContainer.style.display = "none";
            loginContainer.style.display = "block";
          }
          showMessage("login-form", signupData.message || "Account created! Please log in.", "success");
        } catch (err) {
          showMessage("signup-form", err.message || "Signup failed", "error");
        }
      });
    }

    if (loginForm) {
      loginForm.addEventListener("submit", async function (e) {
        e.preventDefault();
        showMessage("login-form", "Logging in...", "success");

        var email = (document.getElementById("login-email")?.value || "").trim();
        var password = document.getElementById("login-password")?.value || "";

        try {
          var loginData = await postJson("/api/login", {
            email: email,
            password: password
          });

          storeSession(loginData);

          if (app && typeof app.navigateTo === "function") {
            app.navigateTo("welcome");
          }
        } catch (err) {
          showMessage("login-form", err.message || "Login failed", "error");
        }
      });
    }
  }

  window.MindEaseAuth = { init: init };
})();
