(function () {
    "use strict";
    var csrfToken = null;

    async function apiRequest(path, options) {
        options = options || {};
        var method = options.method || "GET";
        var headers = { "Accept": "application/json" };
        if (!["GET", "HEAD", "OPTIONS"].includes(method.toUpperCase())) {
            if (!csrfToken) {
                var csrfResponse = await fetch("/api/csrf", { credentials: "same-origin" });
                if (!csrfResponse.ok) throw new Error("Unable to establish a secure session.");
                csrfToken = (await csrfResponse.json()).csrf_token;
            }
            headers["X-CSRFToken"] = csrfToken;
        }
        if (options.body !== undefined) headers["Content-Type"] = "application/json";
        var response;
        try {
            response = await fetch(path, {
                method: method,
                headers: headers,
                credentials: "same-origin",
                body: options.body === undefined ? undefined : JSON.stringify(options.body)
            });
        } catch (error) {
            throw new Error("Unable to connect to the server. Please try again.");
        }
        var data = response.status === 204 ? null : await response.json();
        if (!response.ok) {
            var error = new Error(data && data.error ? data.error : "Request failed.");
            error.status = response.status;
            if (data && data.error && data.error.startsWith("CSRF")) csrfToken = null;
            throw error;
        }
        if (path === "/api/login" || path === "/api/logout") csrfToken = null;
        return data;
    }
    window.taskApi = apiRequest;
})();
