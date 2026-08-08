/**
 * app.js — TaskFlow frontend
 *
 * Rules enforced:
 *  - All user-controlled data is rendered via textContent / createElement.
 *    innerHTML is NEVER used with data from the API.
 *  - localStorage caches the last successful task list under "taskflow_tasks".
 *    When the backend is unreachable the cached data is shown with a [cached] badge.
 *  - All API calls go to API_BASE (defaults to same-origin, allowing the FastAPI
 *    static file mount to serve both frontend and backend from one server).
 */

"use strict";

const API_BASE = "http://localhost:8000";

// Cache key for localStorage
const CACHE_KEY = "taskflow_tasks";

// State
let allTasks     = [];   // currently displayed tasks
let allProjects  = [];
let allUsers     = [];
let activeProjectFilter = "";

// ============================================================
// Utility helpers
// ============================================================

/**
 * Generic fetch wrapper.
 * Returns { ok, data, status } — never throws.
 */
async function apiFetch(path, options = {}) {
  try {
    const res = await fetch(API_BASE + path, {
      headers: { "Content-Type": "application/json", ...options.headers },
      ...options,
    });
    let data = null;
    const ct = res.headers.get("content-type") || "";
    if (ct.includes("application/json")) {
      data = await res.json();
    }
    return { ok: res.ok, status: res.status, data };
  } catch (err) {
    return { ok: false, status: 0, data: null, error: err.message };
  }
}

/** Show or hide an element by id. */
function setVisible(id, visible) {
  const el = document.getElementById(id);
  if (!el) return;
  if (visible) el.classList.remove("hidden");
  else el.classList.add("hidden");
}

/** Display an error message in a named element. */
function showError(elementId, message) {
  const el = document.getElementById(elementId);
  if (!el) return;
  el.textContent = message;
  el.classList.remove("hidden");
}

/** Hide an error message element. */
function clearError(elementId) {
  const el = document.getElementById(elementId);
  if (!el) return;
  el.textContent = "";
  el.classList.add("hidden");
}

// ============================================================
// Tabs
// ============================================================

function switchTab(tabName, btn) {
  // Hide all tab content panels
  document.querySelectorAll(".tab-content").forEach(el => el.classList.add("hidden"));
  // Deactivate all tab buttons
  document.querySelectorAll(".tab-btn").forEach(b => b.classList.remove("active"));
  // Show the selected tab and mark button active
  const panel = document.getElementById("tab-" + tabName);
  if (panel) panel.classList.remove("hidden");
  if (btn) btn.classList.add("active");

  // Lazy-load data when switching tabs
  if (tabName === "tasks")    loadTasks();
  if (tabName === "projects") loadProjects();
  if (tabName === "users")    loadUsers();
}

// ============================================================
// localStorage cache helpers
// ============================================================

function saveTasksToCache(tasks) {
  try {
    localStorage.setItem(CACHE_KEY, JSON.stringify(tasks));
  } catch (_) { /* storage might be full */ }
}

function loadTasksFromCache() {
  try {
    const raw = localStorage.getItem(CACHE_KEY);
    return raw ? JSON.parse(raw) : null;
  } catch (_) {
    return null;
  }
}

// ============================================================
// Tasks
// ============================================================

async function loadTasks() {
  const result = await apiFetch("/tasks");
  const cacheBadge = document.getElementById("cache-badge");

  if (result.ok && Array.isArray(result.data)) {
    allTasks = result.data;
    saveTasksToCache(allTasks);
    cacheBadge.classList.add("hidden");
    renderTasks(filterByProject(allTasks));
  } else {
    // Network or server error — fall back to cache
    const cached = loadTasksFromCache();
    if (cached) {
      allTasks = cached;
      cacheBadge.classList.remove("hidden");
      renderTasks(filterByProject(allTasks));
    } else {
      renderTasksEmpty("Could not load tasks and no cached data available.");
    }
  }

  // Also refresh stats
  loadStats();
}

function filterByProject(tasks) {
  if (!activeProjectFilter) return tasks;
  return tasks.filter(t => String(t.project_id) === String(activeProjectFilter));
}

function applyProjectFilter() {
  activeProjectFilter = document.getElementById("filter-project").value;
  renderTasks(filterByProject(allTasks));
  loadStats();
}

/**
 * Render an array of task objects into #task-list.
 * Uses only textContent and createElement — no innerHTML with API data.
 */
function renderTasks(tasks) {
  const container = document.getElementById("task-list");
  container.innerHTML = ""; // safe: clearing structure, not inserting user data

  if (!tasks || tasks.length === 0) {
    const msg = document.createElement("p");
    msg.className = "empty-msg";
    msg.textContent = "No tasks found.";
    container.appendChild(msg);
    return;
  }

  tasks.forEach(task => {
    container.appendChild(buildTaskCard(task));
  });
}

function renderTasksEmpty(msg) {
  const container = document.getElementById("task-list");
  container.innerHTML = "";
  const p = document.createElement("p");
  p.className = "empty-msg";
  p.textContent = msg;
  container.appendChild(p);
}

/** Build a task card DOM node safely — no innerHTML with user data. */
function buildTaskCard(task) {
  const card = document.createElement("div");
  card.className = "task-card" + (task.completed ? " completed-card" : "");
  card.dataset.taskId = task.id;

  // Title
  const title = document.createElement("p");
  title.className = "task-title";
  title.textContent = task.title;                  // safe: textContent
  card.appendChild(title);

  // Description (optional)
  if (task.description) {
    const desc = document.createElement("p");
    desc.className = "task-desc";
    desc.textContent = task.description;           // safe: textContent
    card.appendChild(desc);
  }

  // Meta row: priority badge + due date + completed badge
  const meta = document.createElement("div");
  meta.className = "task-meta";

  const priorityBadge = document.createElement("span");
  const pClass = { low: "badge-low", medium: "badge-medium", high: "badge-high" };
  priorityBadge.className = "badge " + (pClass[task.priority] || "badge-medium");
  priorityBadge.textContent = task.priority;      // safe: textContent
  meta.appendChild(priorityBadge);

  if (task.due_date) {
    const due = document.createElement("span");
    due.className = "task-due";
    due.textContent = "Due: " + task.due_date;    // safe: textContent
    meta.appendChild(due);
  }

  if (task.completed) {
    const doneBadge = document.createElement("span");
    doneBadge.className = "badge badge-done";
    doneBadge.textContent = "Done";
    meta.appendChild(doneBadge);
  }

  card.appendChild(meta);

  // Action buttons
  const actions = document.createElement("div");
  actions.className = "task-actions";

  // Toggle complete
  const toggleBtn = document.createElement("button");
  toggleBtn.className = "btn btn-secondary btn-sm";
  toggleBtn.textContent = task.completed ? "Reopen" : "Complete";
  toggleBtn.addEventListener("click", () => toggleTaskComplete(task));
  actions.appendChild(toggleBtn);

  // Edit
  const editBtn = document.createElement("button");
  editBtn.className = "btn btn-ghost btn-sm";
  editBtn.textContent = "Edit";
  editBtn.addEventListener("click", () => openEditModal(task));
  actions.appendChild(editBtn);

  // Delete
  const delBtn = document.createElement("button");
  delBtn.className = "btn btn-danger btn-sm";
  delBtn.textContent = "Delete";
  delBtn.addEventListener("click", () => deleteTask(task.id));
  actions.appendChild(delBtn);

  card.appendChild(actions);
  return card;
}

async function toggleTaskComplete(task) {
  const result = await apiFetch(`/tasks/${task.id}`, {
    method: "PUT",
    body: JSON.stringify({ completed: !task.completed }),
  });
  if (result.ok) {
    loadTasks();
  }
}

async function deleteTask(taskId) {
  if (!confirm("Delete this task?")) return;
  const result = await apiFetch(`/tasks/${taskId}`, { method: "DELETE" });
  if (result.ok) loadTasks();
}

// ---- Create task form ----

async function submitCreateTask(event) {
  event.preventDefault();
  clearError("create-task-error");

  const title     = document.getElementById("new-title").value.trim();
  const desc      = document.getElementById("new-desc").value.trim() || null;
  const priority  = document.getElementById("new-priority").value;
  const dueRaw    = document.getElementById("new-due").value;
  const projectId = parseInt(document.getElementById("new-project").value, 10);
  const completed = document.getElementById("new-completed").checked;

  if (!title)     return showError("create-task-error", "Title is required.");
  if (!projectId) return showError("create-task-error", "Please select a project.");

  const payload = {
    title,
    description: desc,
    priority,
    due_date: dueRaw || null,
    completed,
    project_id: projectId,
  };

  const result = await apiFetch("/tasks", {
    method: "POST",
    body: JSON.stringify(payload),
  });

  if (result.ok) {
    document.getElementById("create-task-form").reset();
    switchTab("tasks", document.querySelector('[data-tab="tasks"]'));
    loadTasks();
  } else {
    const msg = result.data?.detail || "Failed to create task.";
    showError("create-task-error", typeof msg === "string" ? msg : JSON.stringify(msg));
  }
}

// ---- Edit modal ----

function openEditModal(task) {
  document.getElementById("edit-task-id").value  = task.id;
  document.getElementById("edit-title").value    = task.title;
  document.getElementById("edit-desc").value     = task.description || "";
  document.getElementById("edit-priority").value = task.priority;
  document.getElementById("edit-due").value      = task.due_date || "";
  document.getElementById("edit-completed").checked = task.completed;
  clearError("edit-error");
  document.getElementById("edit-modal").classList.remove("hidden");
}

function closeEditModal(event) {
  if (event.target === document.getElementById("edit-modal")) {
    document.getElementById("edit-modal").classList.add("hidden");
  }
}

async function submitEditTask(event) {
  event.preventDefault();
  clearError("edit-error");

  const taskId   = parseInt(document.getElementById("edit-task-id").value, 10);
  const title    = document.getElementById("edit-title").value.trim();
  const desc     = document.getElementById("edit-desc").value.trim() || null;
  const priority = document.getElementById("edit-priority").value;
  const dueRaw   = document.getElementById("edit-due").value;
  const completed = document.getElementById("edit-completed").checked;

  const payload = {
    title,
    description: desc,
    priority,
    due_date: dueRaw || null,
    completed,
  };

  const result = await apiFetch(`/tasks/${taskId}`, {
    method: "PUT",
    body: JSON.stringify(payload),
  });

  if (result.ok) {
    document.getElementById("edit-modal").classList.add("hidden");
    loadTasks();
  } else {
    const msg = result.data?.detail || "Update failed.";
    showError("edit-error", typeof msg === "string" ? msg : JSON.stringify(msg));
  }
}

// ============================================================
// Stats
// ============================================================

async function loadStats() {
  let url = "/tasks/stats";
  if (activeProjectFilter) url += `?project_id=${activeProjectFilter}`;

  const result = await apiFetch(url);
  if (!result.ok || !result.data) return;

  const s = result.data;
  document.getElementById("stat-total").textContent     = s.total;
  document.getElementById("stat-completed").textContent = s.completed;
  document.getElementById("stat-pending").textContent   = s.pending;
  document.getElementById("stat-rate").textContent      = s.completion_rate + "%";
  document.getElementById("stat-low").textContent       = s.by_priority.low;
  document.getElementById("stat-medium").textContent    = s.by_priority.medium;
  document.getElementById("stat-high").textContent      = s.by_priority.high;
}

// ============================================================
// Quick-Add
// ============================================================

async function submitQuickAdd() {
  clearError("quick-add-error");
  const text      = document.getElementById("quick-add-input").value.trim();
  const projectId = parseInt(document.getElementById("quick-add-project").value, 10);

  if (!text)      return showError("quick-add-error", "Please enter a task description.");
  if (!projectId) return showError("quick-add-error", "Please select a project.");

  const result = await apiFetch("/tasks/quick-add", {
    method: "POST",
    body: JSON.stringify({ text, project_id: projectId }),
  });

  if (result.ok) {
    document.getElementById("quick-add-input").value = "";
    switchTab("tasks", document.querySelector('[data-tab="tasks"]'));
    loadTasks();
  } else {
    const msg = result.data?.detail || "Quick-add failed.";
    showError("quick-add-error", typeof msg === "string" ? msg : JSON.stringify(msg));
  }
}

// ============================================================
// Sort (calls /tasks/sorted — Section 2 endpoint)
// ============================================================

async function sortTasks() {
  const field = document.getElementById("sort-field").value;
  if (!field) { loadTasks(); return; }

  const order  = document.getElementById("sort-order").value;
  const result = await apiFetch(`/tasks/sorted?field=${field}&order=${order}`);

  if (result.ok && result.data) {
    const tasks       = result.data.tasks   || result.data;
    const comparisons = result.data.comparisons;
    renderTasks(tasks);
    const infoEl = document.getElementById("algo-info");
    infoEl.textContent =
      `Sorted by "${field}" (${order}) using insertion sort — ${comparisons ?? "?"} comparisons.`;
    infoEl.classList.remove("hidden");
  }
}

// ============================================================
// Search (calls /tasks/search — Section 2 endpoint)
// ============================================================

async function searchTasks() {
  const q      = document.getElementById("search-input").value.trim();
  const field  = document.getElementById("search-field").value;
  const method = document.getElementById("search-method").value;

  if (!q) { loadTasks(); return; }

  const result = await apiFetch(
    `/tasks/search?q=${encodeURIComponent(q)}&field=${field}&method=${method}`
  );

  if (result.ok && result.data) {
    const tasks = result.data.results || result.data;
    const steps = result.data.steps;
    renderTasks(tasks);
    const infoEl = document.getElementById("algo-info");
    infoEl.textContent =
      `${method} search for "${q}" in "${field}" — ${steps ?? "?"} steps, ${tasks.length} result(s).`;
    infoEl.classList.remove("hidden");
  }
}

function clearSearch() {
  document.getElementById("search-input").value = "";
  document.getElementById("algo-info").classList.add("hidden");
  loadTasks();
}

// ============================================================
// Projects
// ============================================================

async function loadProjects() {
  const result = await apiFetch("/projects");
  if (!result.ok || !Array.isArray(result.data)) return;
  allProjects = result.data;
  renderProjects(allProjects);
  populateProjectSelects();
}

function renderProjects(projects) {
  const container = document.getElementById("project-list");
  container.innerHTML = "";

  if (!projects.length) {
    const p = document.createElement("p");
    p.className = "empty-msg";
    p.textContent = "No projects yet.";
    container.appendChild(p);
    return;
  }

  projects.forEach(proj => {
    const row = document.createElement("div");
    row.className = "item-row";

    const info = document.createElement("div");
    info.className = "item-info";

    const h3 = document.createElement("h3");
    h3.textContent = proj.name;                    // safe: textContent
    info.appendChild(h3);

    if (proj.description) {
      const p = document.createElement("p");
      p.textContent = proj.description;            // safe: textContent
      info.appendChild(p);
    }

    const ownTag = document.createElement("p");
    ownTag.textContent = "Owner ID: " + proj.owner_id; // safe: textContent
    info.appendChild(ownTag);

    row.appendChild(info);

    const actions = document.createElement("div");
    actions.className = "item-actions";

    const delBtn = document.createElement("button");
    delBtn.className = "btn btn-danger btn-sm";
    delBtn.textContent = "Delete";
    delBtn.addEventListener("click", () => deleteProject(proj.id));
    actions.appendChild(delBtn);

    row.appendChild(actions);
    container.appendChild(row);
  });
}

/** Populate all project <select> dropdowns across the page. */
function populateProjectSelects() {
  const selects = [
    document.getElementById("filter-project"),
    document.getElementById("quick-add-project"),
    document.getElementById("new-project"),
    document.getElementById("proj-owner"),  // not a project select but needs users
  ];

  // Project selects (filter, quick-add, new-task)
  const projectSelects = [
    document.getElementById("filter-project"),
    document.getElementById("quick-add-project"),
    document.getElementById("new-project"),
  ];

  projectSelects.forEach(sel => {
    if (!sel) return;
    // Keep first placeholder option
    const placeholder = sel.options[0];
    sel.innerHTML = "";
    sel.appendChild(placeholder);

    allProjects.forEach(proj => {
      const opt = document.createElement("option");
      opt.value       = proj.id;
      opt.textContent = proj.name;               // safe: textContent
      sel.appendChild(opt);
    });
  });
}

function toggleNewProjectForm() {
  const form = document.getElementById("new-project-form");
  form.classList.toggle("hidden");
  // populate owner select
  populateOwnerSelect();
}

function populateOwnerSelect() {
  const sel = document.getElementById("proj-owner");
  const placeholder = sel.options[0];
  sel.innerHTML = "";
  sel.appendChild(placeholder);
  allUsers.forEach(u => {
    const opt = document.createElement("option");
    opt.value       = u.id;
    opt.textContent = u.name + " <" + u.email + ">";  // safe: textContent
    sel.appendChild(opt);
  });
}

async function submitCreateProject(event) {
  event.preventDefault();
  clearError("create-project-error");

  const name    = document.getElementById("proj-name").value.trim();
  const desc    = document.getElementById("proj-desc").value.trim() || null;
  const ownerId = parseInt(document.getElementById("proj-owner").value, 10);

  if (!name)    return showError("create-project-error", "Name is required.");
  if (!ownerId) return showError("create-project-error", "Please select an owner.");

  const result = await apiFetch("/projects", {
    method: "POST",
    body: JSON.stringify({ name, description: desc, owner_id: ownerId }),
  });

  if (result.ok) {
    document.getElementById("new-project-form").reset();
    document.getElementById("new-project-form").classList.add("hidden");
    loadProjects();
  } else {
    const msg = result.data?.detail || "Failed to create project.";
    showError("create-project-error", typeof msg === "string" ? msg : JSON.stringify(msg));
  }
}

async function deleteProject(projectId) {
  if (!confirm("Delete this project and all its tasks?")) return;
  const result = await apiFetch(`/projects/${projectId}`, { method: "DELETE" });
  if (result.ok) loadProjects();
}

// ============================================================
// Users
// ============================================================

async function loadUsers() {
  const result = await apiFetch("/users");
  if (!result.ok || !Array.isArray(result.data)) return;
  allUsers = result.data;
  renderUsers(allUsers);
}

function renderUsers(users) {
  const container = document.getElementById("user-list");
  container.innerHTML = "";

  if (!users.length) {
    const p = document.createElement("p");
    p.className = "empty-msg";
    p.textContent = "No users yet.";
    container.appendChild(p);
    return;
  }

  users.forEach(user => {
    const row = document.createElement("div");
    row.className = "item-row";

    const info = document.createElement("div");
    info.className = "item-info";

    const h3 = document.createElement("h3");
    h3.textContent = user.name;                   // safe: textContent
    info.appendChild(h3);

    const p = document.createElement("p");
    p.textContent = user.email;                   // safe: textContent
    info.appendChild(p);

    row.appendChild(info);

    const actions = document.createElement("div");
    actions.className = "item-actions";

    const delBtn = document.createElement("button");
    delBtn.className = "btn btn-danger btn-sm";
    delBtn.textContent = "Delete";
    delBtn.addEventListener("click", () => deleteUser(user.id));
    actions.appendChild(delBtn);

    row.appendChild(actions);
    container.appendChild(row);
  });
}

function toggleNewUserForm() {
  document.getElementById("new-user-form").classList.toggle("hidden");
}

async function submitCreateUser(event) {
  event.preventDefault();
  clearError("create-user-error");

  const name  = document.getElementById("user-name").value.trim();
  const email = document.getElementById("user-email").value.trim();

  if (!name)  return showError("create-user-error", "Name is required.");
  if (!email) return showError("create-user-error", "Email is required.");

  const result = await apiFetch("/users", {
    method: "POST",
    body: JSON.stringify({ name, email }),
  });

  if (result.ok) {
    document.getElementById("new-user-form").reset();
    document.getElementById("new-user-form").classList.add("hidden");
    loadUsers();
  } else {
    const msg = result.data?.detail || "Failed to create user.";
    showError("create-user-error", typeof msg === "string" ? msg : JSON.stringify(msg));
  }
}

async function deleteUser(userId) {
  if (!confirm("Delete this user, their projects, and all tasks?")) return;
  const result = await apiFetch(`/users/${userId}`, { method: "DELETE" });
  if (result.ok) {
    loadUsers();
    loadProjects();  // cascade may have removed projects
    loadTasks();
  }
}

// ============================================================
// Bootstrap — load initial data on page load
// ============================================================

document.addEventListener("DOMContentLoaded", async () => {
  // Load users first (needed to populate project owner selects)
  await loadUsers();
  // Load projects (needed for all project selects)
  await loadProjects();
  // Load tasks (default visible tab)
  await loadTasks();
});
