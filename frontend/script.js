var form = document.getElementById("task-form");
var titleInput = document.getElementById("task-title");
var descriptionInput = document.getElementById("task-description");
var taskList = document.getElementById("task-list");
var emptyMessage = document.getElementById("empty-message");
var totalTasks = document.getElementById("total-tasks");
var completedTasks = document.getElementById("completed-tasks");
var formHeading = document.getElementById("form-heading");
var saveButton = document.getElementById("save-button");
var cancelButton = document.getElementById("cancel-button");
var usernameDisplay = document.getElementById("current-username");
var logoutButton = document.getElementById("logout-button");
var message = document.getElementById("task-message");
var tasks = [];
var editingId = null;
var busy = false;
var ready = false;

function setBusy(value) {
    busy = value;
    saveButton.disabled = value || !ready;
    cancelButton.disabled = value || !ready;
    logoutButton.disabled = value || !ready;
    taskList.querySelectorAll("button, input").forEach(function (control) { control.disabled = value; });
}

function handleError(error) {
    if (error.status === 401) {
        window.location.href = "/account.html";
        return;
    }
    message.textContent = error.message;
    message.style.color = "red";
}

async function runAction(action) {
    if (busy || !ready) return;
    setBusy(true);
    message.textContent = "";
    try {
        await action();
    } catch (error) {
        handleError(error);
        renderTasks();
    } finally {
        setBusy(false);
    }
}

async function loadTasks() {
    tasks = (await taskApi("/api/tasks")).tasks;
    renderTasks();
}

function renderTasks() {
    taskList.replaceChildren();
    totalTasks.textContent = tasks.length;
    completedTasks.textContent = tasks.filter(function (task) { return task.completed; }).length;
    emptyMessage.hidden = tasks.length > 0;
    tasks.forEach(function (task) {
        var card = document.createElement("article");
        card.className = "task-card";
        if (task.completed) card.classList.add("completed");
        var heading = document.createElement("h3");
        heading.textContent = task.title;
        var description = document.createElement("p");
        description.textContent = task.description || "No description";
        var status = document.createElement("label");
        status.className = "task-status";
        var checkbox = document.createElement("input");
        checkbox.type = "checkbox";
        checkbox.checked = task.completed;
        var statusText = document.createElement("span");
        statusText.textContent = task.completed ? "Completed" : "In progress";
        checkbox.addEventListener("change", function () {
            var nextValue = checkbox.checked;
            runAction(async function () {
                await taskApi("/api/tasks/" + task.id, { method: "PATCH", body: { completed: nextValue } });
                await loadTasks();
            });
        });
        status.append(checkbox, statusText);
        var actions = document.createElement("div");
        actions.className = "task-actions";
        var editButton = document.createElement("button");
        editButton.type = "button";
        editButton.className = "edit-button";
        editButton.textContent = "Edit";
        editButton.addEventListener("click", function () {
            titleInput.value = task.title;
            descriptionInput.value = task.description;
            editingId = task.id;
            formHeading.textContent = "Edit Task";
            saveButton.textContent = "Save Changes";
            cancelButton.hidden = false;
            titleInput.focus();
        });
        var deleteButton = document.createElement("button");
        deleteButton.type = "button";
        deleteButton.className = "delete-button";
        deleteButton.textContent = "Delete";
        deleteButton.addEventListener("click", function () {
            runAction(async function () {
                await taskApi("/api/tasks/" + task.id, { method: "DELETE" });
                if (editingId === task.id) resetForm();
                await loadTasks();
            });
        });
        actions.append(editButton, deleteButton);
        card.append(heading, description, status, actions);
        taskList.append(card);
    });
}

function resetForm() {
    form.reset();
    editingId = null;
    formHeading.textContent = "Add a Task";
    saveButton.textContent = "Add Task";
    cancelButton.hidden = true;
}

form.addEventListener("submit", function (event) {
    event.preventDefault();
    runAction(async function () {
        var body = { title: titleInput.value.trim(), description: descriptionInput.value.trim() };
        await taskApi(editingId === null ? "/api/tasks" : "/api/tasks/" + editingId, {
            method: editingId === null ? "POST" : "PATCH", body: body
        });
        resetForm();
        await loadTasks();
    });
});
cancelButton.addEventListener("click", resetForm);
logoutButton.addEventListener("click", function () {
    runAction(async function () {
        await taskApi("/api/logout", { method: "POST" });
        window.location.href = "/account.html";
    });
});

async function initialize() {
    setBusy(true);
    try {
        usernameDisplay.textContent = (await taskApi("/api/me")).user.username;
        await loadTasks();
        ready = true;
    } catch (error) {
        handleError(error);
    } finally {
        setBusy(false);
    }
}
initialize();
