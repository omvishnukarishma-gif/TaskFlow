/**
 * app.js — TaskFlow frontend (redesigned)
 *
 * All original API calls, localStorage cache, sort/search, CRUD, stats,
 * Quick-Add, and cascade behaviour are fully preserved.
 *
 * Changes vs original:
 *  - Tab switching targets both .topnav and .mobile-nav nav-tab buttons.
 *  - Project filter is a button list (#project-filter-list) instead of a <select>.
 *  - algo-info now has a child <span id="algo-info-text"> for the message.
 *  - Stats update also drives the progress bar and priority mini-bars.
 *  - Task cards use the new .task-card structure with a check-circle toggle.
 *  - Project/User lists use .item-card structure.
 *  - toggleNewProjectForm / toggleNewUserForm update aria-expanded.
 *  - All user data still rendered via textContent / createElement (no innerHTML
 *    with untrusted data).
 */

/**
 * ============================================================
 * THEME — Light / Dark mode
 *
 * Applied immediately on script parse (before DOMContentLoaded)
 * to prevent any flash of the wrong theme on page load.
 *
 * Storage key : "taskflow_theme"
 * Values      : "light" | "dark"
 * Fallback    : system prefers-color-scheme, then "light"
 * ============================================================
 */
const THEME_KEY = "taskflow_theme";

(function applyThemeEarly() {
  const saved = localStorage.getItem(THEME_KEY);
  const prefersDark = window.matchMedia &&
                      window.matchMedia("(prefers-color-scheme: dark)").matches;
  const theme = saved || (prefersDark ? "dark" : "light");
  if (theme === "dark") {
    document.documentElement.setAttribute("data-theme", "dark");
  }
})();

function _updateToggleButton(isDark) {
  const buttons = [
    document.getElementById("theme-toggle-btn"),
    document.getElementById("login-theme-toggle-btn")
  ].filter(Boolean);

  if (buttons.length === 0) return;

  buttons.forEach((btn) => {
    if (isDark) {
      btn.textContent = "🌙";
      btn.setAttribute("aria-label", "Switch to light mode");
      btn.setAttribute("title", "Switch to light mode");
    } else {
      btn.textContent = "☀️";
      btn.setAttribute("aria-label", "Switch to dark mode");
      btn.setAttribute("title", "Switch to dark mode");
    }
  });
}

function toggleTheme() {
  const isDark = document.documentElement.getAttribute("data-theme") === "dark";
  if (isDark) {
    document.documentElement.removeAttribute("data-theme");
    localStorage.setItem(THEME_KEY, "light");
    _updateToggleButton(false);
  } else {
    document.documentElement.setAttribute("data-theme", "dark");
    localStorage.setItem(THEME_KEY, "dark");
    _updateToggleButton(true);
  }
}

/**
 * ============================================================
 * AUTH — Session management
 *
 * Design:
 *  - Session token stored in localStorage under AUTH_TOKEN_KEY.
 *  - Safe user info (id, name, email) stored under AUTH_USER_KEY.
 *  - Passwords are NEVER stored locally.
 *  - On page load, checkAuth() validates the stored token with
 *    GET /auth/me. If valid → show app. If invalid → show login.
 *  - All existing API calls are completely unchanged (no auth
 *    headers added to /tasks, /projects, /users, etc.).
 * ============================================================
 */
const AUTH_TOKEN_KEY = "taskflow_auth_token";
const AUTH_USER_KEY  = "taskflow_auth_user";

// ── Auth helpers ──────────────────────────────────────────────────────────────

function getStoredToken() {
  return localStorage.getItem(AUTH_TOKEN_KEY) || "";
}

function storeSession(token, user) {
  localStorage.setItem(AUTH_TOKEN_KEY, token);
  // Only safe fields — never store password_hash
  localStorage.setItem(AUTH_USER_KEY, JSON.stringify({
    id:    user.user_id    ?? user.id,
    name:  user.user_name  ?? user.name,
    email: user.user_email ?? user.email,
  }));
}

function clearSession() {
  localStorage.removeItem(AUTH_TOKEN_KEY);
  localStorage.removeItem(AUTH_USER_KEY);
}

function getStoredUser() {
  try {
    const raw = localStorage.getItem(AUTH_USER_KEY);
    return raw ? JSON.parse(raw) : null;
  } catch (_) { return null; }
}

// ── UI show/hide ──────────────────────────────────────────────────────────────

function showLoginScreen() {
  const ls = document.getElementById("login-screen");
  const aw = document.getElementById("app-shell-wrapper");
  const tb = document.getElementById("topbar-app-content");  // topnav + mobile-nav
  const mn = document.querySelector(".mobile-nav");
  const topnav = document.querySelector(".topnav");
  if (ls) ls.classList.remove("hidden");
  if (aw) aw.classList.add("hidden");
  if (mn) mn.classList.add("hidden");
  if (topnav) topnav.classList.add("hidden");
  const authBar = document.getElementById("auth-topbar");
  if (authBar) authBar.classList.add("hidden");
}

function showApp(user) {
  const ls = document.getElementById("login-screen");
  const aw = document.getElementById("app-shell-wrapper");
  const mn = document.querySelector(".mobile-nav");
  const topnav = document.querySelector(".topnav");
  if (ls) ls.classList.add("hidden");
  if (aw) aw.classList.remove("hidden");
  if (mn) mn.classList.remove("hidden");
  if (topnav) topnav.classList.remove("hidden");
  // Show auth topbar with username
  const authBar = document.getElementById("auth-topbar");
  const nameEl  = document.getElementById("auth-username");
  if (authBar) authBar.classList.remove("hidden");
  if (nameEl && user) nameEl.textContent = user.name || user.user_name || "";
}

// ── Login pane / Register pane switch ────────────────────────────────────────

function showLoginPane() {
  document.getElementById("login-pane").classList.remove("hidden");
  document.getElementById("register-pane").classList.add("hidden");
  document.getElementById("forgot-pane").classList.add("hidden");
  document.getElementById("tab-btn-login").classList.add("active");
  document.getElementById("tab-btn-login").setAttribute("aria-selected", "true");
  document.getElementById("tab-btn-register").classList.remove("active");
  document.getElementById("tab-btn-register").setAttribute("aria-selected", "false");
  clearAuthErrors();
}

function showRegisterPane() {
  document.getElementById("register-pane").classList.remove("hidden");
  document.getElementById("login-pane").classList.add("hidden");
  document.getElementById("forgot-pane").classList.add("hidden");
  document.getElementById("tab-btn-register").classList.add("active");
  document.getElementById("tab-btn-register").setAttribute("aria-selected", "true");
  document.getElementById("tab-btn-login").classList.remove("active");
  document.getElementById("tab-btn-login").setAttribute("aria-selected", "false");
  clearAuthErrors();
}

function clearAuthErrors() {
  [
    "login-error", "register-error", "register-success", "register-success-login",
    "forgot-error", "forgot-info", "reset-error", "reset-success",
  ].forEach(id => {
    const el = document.getElementById(id);
    if (el) { el.textContent = ""; el.classList.add("hidden"); }
  });
}

function setLoginButtonState(loading) {
  const btn = document.getElementById("login-submit-btn");
  if (!btn) return;
  btn.disabled = loading;
  btn.textContent = loading ? "Signing in…" : "Sign In";
}

function setRegisterButtonState(loading) {
  const btn = document.getElementById("register-submit-btn");
  if (!btn) return;
  btn.disabled = loading;
  btn.textContent = loading ? "Creating account…" : "Create Account";
}

// ── Forgot-password pane ──────────────────────────────────────────────────────

function showForgotPane() {
  // Hide login and register panes, deactivate tab highlights
  document.getElementById("login-pane").classList.add("hidden");
  document.getElementById("register-pane").classList.add("hidden");
  document.getElementById("forgot-pane").classList.remove("hidden");
  // Deactivate both tabs visually (neither is "active" in the forgot view)
  document.getElementById("tab-btn-login").classList.remove("active");
  document.getElementById("tab-btn-login").setAttribute("aria-selected", "false");
  document.getElementById("tab-btn-register").classList.remove("active");
  document.getElementById("tab-btn-register").setAttribute("aria-selected", "false");
  clearAuthErrors();
  // Always start at step 1 (email entry)
  document.getElementById("forgot-step-email").classList.remove("hidden");
  document.getElementById("forgot-step-reset").classList.add("hidden");
  const emailInput = document.getElementById("forgot-email");
  if (emailInput) { emailInput.value = ""; emailInput.focus(); }
}

function setForgotButtonState(loading) {
  const btn = document.getElementById("forgot-submit-btn");
  if (!btn) return;
  btn.disabled = loading;
  btn.textContent = loading ? "Sending…" : "Send Reset Token";
}

function setResetButtonState(loading) {
  const btn = document.getElementById("reset-submit-btn");
  if (!btn) return;
  btn.disabled = loading;
  btn.textContent = loading ? "Updating…" : "Set New Password";
}

async function submitForgotPassword() {
  clearAuthErrors();

  const email = (document.getElementById("forgot-email").value || "").trim();
  if (!email) {
    const el = document.getElementById("forgot-error");
    el.textContent = "Please enter your email address.";
    el.classList.remove("hidden");
    return;
  }

  setForgotButtonState(true);

  try {
    const res = await fetch("http://localhost:8000/auth/forgot-password", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email }),
    });
    const data = await res.json().catch(() => ({}));

    if (res.ok) {
      // Always show the generic success message — never reveal whether the
      // email exists.  Show step 2 so the user can paste the token.
      const infoEl = document.getElementById("forgot-info");
      infoEl.textContent =
        data.detail ||
        "If that email is registered, a reset token has been sent. " +
        "Check the server console (dev mode) and paste the token below.";
      infoEl.classList.remove("hidden");

      // Transition to step 2
      document.getElementById("forgot-step-email").classList.add("hidden");
      document.getElementById("forgot-step-reset").classList.remove("hidden");

      // In dev mode the raw token comes back in the response — pre-fill the
      // token field as a convenience so testers do not have to copy from the
      // console manually.
      if (data.dev_token) {
        const tokenInput = document.getElementById("reset-token");
        if (tokenInput) tokenInput.value = data.dev_token;
      }
    } else {
      const msg = data?.detail || "Request failed. Please try again.";
      const el = document.getElementById("forgot-error");
      el.textContent = typeof msg === "string" ? msg : "Request failed.";
      el.classList.remove("hidden");
    }
  } catch (_) {
    const el = document.getElementById("forgot-error");
    el.textContent = "Could not reach the server. Please try again.";
    el.classList.remove("hidden");
  } finally {
    setForgotButtonState(false);
  }
}

async function submitResetPassword() {
  // Clear only the reset-step error/success elements
  ["reset-error", "reset-success"].forEach(id => {
    const el = document.getElementById(id);
    if (el) { el.textContent = ""; el.classList.add("hidden"); }
  });

  const token       = (document.getElementById("reset-token").value || "").trim();
  const newPassword = document.getElementById("reset-new-password").value || "";

  if (!token) {
    const el = document.getElementById("reset-error");
    el.textContent = "Please enter the reset token.";
    el.classList.remove("hidden");
    return;
  }
  if (newPassword.length < 8) {
    const el = document.getElementById("reset-error");
    el.textContent = "New password must be at least 8 characters.";
    el.classList.remove("hidden");
    return;
  }

  setResetButtonState(true);

  try {
    const res = await fetch("http://localhost:8000/auth/reset-password", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ token, new_password: newPassword }),
    });
    const data = await res.json().catch(() => ({}));

    if (res.ok) {
      // Show success message, then after a short pause redirect to login pane
      const el = document.getElementById("reset-success");
      el.textContent =
        data.detail || "Password updated successfully. Please log in.";
      el.classList.remove("hidden");
      // Clear the password field immediately for security
      document.getElementById("reset-new-password").value = "";
      document.getElementById("reset-token").value = "";
      // Navigate back to login after 1.5 s so the user can read the message
      setTimeout(() => {
        showLoginPane();
        // Pre-populate success message on login pane
        const loginSuccessEl = document.getElementById("register-success-login");
        if (loginSuccessEl) {
          loginSuccessEl.textContent = "Password updated. Please log in with your new password.";
          loginSuccessEl.classList.remove("hidden");
        }
      }, 1500);
    } else {
      const msg = data?.detail || "Password reset failed. The token may be invalid or expired.";
      const el = document.getElementById("reset-error");
      el.textContent = typeof msg === "string" ? msg : "Password reset failed.";
      el.classList.remove("hidden");
    }
  } catch (_) {
    const el = document.getElementById("reset-error");
    el.textContent = "Could not reach the server. Please try again.";
    el.classList.remove("hidden");
  } finally {
    setResetButtonState(false);
  }
}

// ── Core auth flow ────────────────────────────────────────────────────────────

async function checkAuth() {
  const token = getStoredToken();
  if (!token) {
    showLoginScreen();
    return;
  }
  // Validate token with server
  const res = await fetch("http://localhost:8000/auth/me", {
    headers: { "Authorization": "Bearer " + token }
  }).catch(() => null);

  if (res && res.ok) {
    const user = await res.json().catch(() => null);
    showApp(user || getStoredUser());
    // Run the normal bootstrap
    await loadUsers();
    await loadProjects();
    await loadTasks();
  } else {
    // Token invalid or server unreachable — clear and show login
    clearSession();
    showLoginScreen();
  }
}

async function submitLogin(event) {
  event.preventDefault();
  clearAuthErrors();

  const email    = document.getElementById("login-email").value.trim();
  const password = document.getElementById("login-password").value;

  if (!email || !password) {
    const el = document.getElementById("login-error");
    el.textContent = "Please enter your email and password.";
    el.classList.remove("hidden");
    return;
  }

  setLoginButtonState(true);

  try {
    const res = await fetch("http://localhost:8000/auth/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, password }),
    });
    const data = await res.json().catch(() => ({}));

    if (res.ok) {
      storeSession(data.token, data);
      showApp(data);
      // Clear the password field for security
      document.getElementById("login-password").value = "";
      await loadUsers();
      await loadProjects();
      await loadTasks();
    } else {
      const msg = data?.detail || "Login failed. Please check your email and password.";
      const el = document.getElementById("login-error");
      el.textContent = typeof msg === "string" ? msg : "Login failed. Please try again.";
      el.classList.remove("hidden");
    }
  } catch (_) {
    const el = document.getElementById("login-error");
    el.textContent = "Could not reach the server. Please try again.";
    el.classList.remove("hidden");
  } finally {
    setLoginButtonState(false);
  }
}

async function submitRegister(event) {
  event.preventDefault();
  clearAuthErrors();

  const name     = document.getElementById("reg-name").value.trim();
  const email    = document.getElementById("reg-email").value.trim();
  const password = document.getElementById("reg-password").value;

  if (!name || !email || !password) {
    const el = document.getElementById("register-error");
    el.textContent = "Please fill in all fields.";
    el.classList.remove("hidden");
    return;
  }
  if (password.length < 8) {
    const el = document.getElementById("register-error");
    el.textContent = "Password must be at least 8 characters.";
    el.classList.remove("hidden");
    return;
  }

  setRegisterButtonState(true);

  try {
    const res = await fetch("http://localhost:8000/auth/register", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name, email, password }),
    });
    const data = await res.json().catch(() => ({}));

    if (res.ok) {
      // Account created — do NOT auto-login. Return to login pane and prompt
      // the user to sign in manually with their new credentials.
      document.getElementById("reg-name").value     = "";
      document.getElementById("reg-email").value    = "";
      document.getElementById("reg-password").value = "";
      showLoginPane();
      const successEl = document.getElementById("register-success-login");
      if (successEl) {
        successEl.textContent = "Account created successfully. Please log in.";
        successEl.classList.remove("hidden");
      }
    } else {
      const msg = data?.detail || "Registration failed. Please try again.";
      const el = document.getElementById("register-error");
      el.textContent = typeof msg === "string" ? msg : "Registration failed.";
      el.classList.remove("hidden");
    }
  } catch (_) {
    const el = document.getElementById("register-error");
    el.textContent = "Could not reach the server. Please try again.";
    el.classList.remove("hidden");
  } finally {
    setRegisterButtonState(false);
  }
}

async function logoutUser() {
  const token = getStoredToken();
  if (token) {
    // Tell the server to invalidate the session (fire-and-forget; always clear locally)
    fetch("http://localhost:8000/auth/logout", {
      method: "POST",
      headers: { "Authorization": "Bearer " + token },
    }).catch(() => {});
  }
  clearSession();
  // Reset login form state
  const lf = document.getElementById("login-form");
  const rf = document.getElementById("register-form");
  if (lf) lf.reset();
  if (rf) rf.reset();
  clearAuthErrors();
  showLoginPane();
  showLoginScreen();
}

"use strict";

const API_BASE = "http://localhost:8000";
const CACHE_KEY = "taskflow_tasks";

// ── State ────────────────────────────────────────────────────────────────────
let allTasks            = [];
let allProjects         = [];
let allUsers            = [];
let activeProjectFilter = "";   // "" = All, otherwise project id as string

// ============================================================
// Generic fetch wrapper
// Returns { ok, status, data, headers }  — never throws.
// ============================================================
async function apiFetch(path, options = {}) {
  try {
    const res = await fetch(API_BASE + path, {
      headers: { "Content-Type": "application/json", ...options.headers },
      ...options,
    });
    let data = null;
    const ct = res.headers.get("content-type") || "";
    if (ct.includes("application/json")) data = await res.json();
    return { ok: res.ok, status: res.status, data, headers: res.headers };
  } catch (err) {
    return { ok: false, status: 0, data: null, headers: null, error: err.message };
  }
}

// ============================================================
// UI helpers
// ============================================================
function setVisible(id, visible) {
  const el = document.getElementById(id);
  if (!el) return;
  visible ? el.classList.remove("hidden") : el.classList.add("hidden");
}

function showError(elementId, message) {
  const el = document.getElementById(elementId);
  if (!el) return;
  el.textContent = message;
  el.classList.remove("hidden");
}

function clearError(elementId) {
  const el = document.getElementById(elementId);
  if (!el) return;
  el.textContent = "";
  el.classList.add("hidden");
}

// ============================================================
// Tab switching
// Syncs both .topnav and .mobile-nav button sets.
// ============================================================
function switchTab(tabName, clickedBtn) {
  // Hide all tab panels
  document.querySelectorAll(".tab-content").forEach(el => el.classList.add("hidden"));

  // Deactivate every nav-tab button in both navbars
  document.querySelectorAll(".nav-tab").forEach(b => {
    b.classList.remove("active");
    b.removeAttribute("aria-current");
  });

  // Show target panel
  const panel = document.getElementById("tab-" + tabName);
  if (panel) panel.classList.remove("hidden");

  // Activate all buttons whose data-tab matches (topnav + mobile-nav)
  document.querySelectorAll(`.nav-tab[data-tab="${tabName}"]`).forEach(b => {
    b.classList.add("active");
    b.setAttribute("aria-current", "page");
  });

  // Lazy-load data for the activated tab
  if (tabName === "tasks")       loadTasks();
  if (tabName === "projects")    loadProjects();
  if (tabName === "users")       loadUsers();
  if (tabName === "create-task") loadProjects();   // populate project select
}

// ============================================================
// localStorage cache
// ============================================================
function saveTasksToCache(tasks) {
  try { localStorage.setItem(CACHE_KEY, JSON.stringify(tasks)); } catch (_) {}
}

function loadTasksFromCache() {
  try {
    const raw = localStorage.getItem(CACHE_KEY);
    return raw ? JSON.parse(raw) : null;
  } catch (_) { return null; }
}

// ============================================================
// TASKS — load, filter, render
// ============================================================
async function loadTasks() {
  // Show cached data immediately so the list is never blank while fetching
  const cacheBadge = document.getElementById("cache-badge");
  const cached = loadTasksFromCache();
  if (cached) {
    allTasks = cached;
    cacheBadge.classList.remove("hidden");
    renderTasks(filterByProject(allTasks));
  }

  const result = await apiFetch("/tasks");

  if (result.ok && Array.isArray(result.data)) {
    allTasks = result.data;
    saveTasksToCache(allTasks);
    cacheBadge.classList.add("hidden");
    renderTasks(filterByProject(allTasks));
  } else if (!cached) {
    renderTasksEmpty(
      "📡",
      "Could not reach the server",
      "No cached data available. Start the server and refresh."
    );
  }
  // If live fetch failed but cache was shown, leave the cache rendering and badge visible

  loadStats();
}

function filterByProject(tasks) {
  if (!activeProjectFilter) return tasks;
  return tasks.filter(t => String(t.project_id) === String(activeProjectFilter));
}

// ── Project filter list (sidebar button list) ─────────────────────────────
function renderProjectFilterList() {
  const container = document.getElementById("project-filter-list");
  if (!container) return;
  container.innerHTML = "";

  // "All projects" entry
  const allBtn = buildFilterItem("", "All Projects", "☰", activeProjectFilter === "");
  container.appendChild(allBtn);

  // One entry per project
  allProjects.forEach(proj => {
    const initial = proj.name.charAt(0).toUpperCase();
    const btn = buildFilterItem(String(proj.id), proj.name, initial, String(activeProjectFilter) === String(proj.id));
    container.appendChild(btn);
  });
}

function buildFilterItem(value, label, iconText, isActive) {
  const btn = document.createElement("button");
  btn.className = "project-filter-item" + (isActive ? " active" : "");
  btn.setAttribute("role", "option");
  btn.setAttribute("aria-selected", isActive ? "true" : "false");
  btn.dataset.projectId = value;

  const icon = document.createElement("span");
  icon.className = "proj-icon";
  icon.textContent = iconText;
  icon.setAttribute("aria-hidden", "true");

  const name = document.createElement("span");
  name.textContent = label;          // safe: textContent

  btn.appendChild(icon);
  btn.appendChild(name);

  btn.addEventListener("click", () => {
    activeProjectFilter = value;
    renderProjectFilterList();
    renderTasks(filterByProject(allTasks));
    loadStats();
  });

  return btn;
}

// ── Render task list ──────────────────────────────────────────────────────
function renderTasks(tasks) {
  const container = document.getElementById("task-list");
  container.innerHTML = "";

  if (!tasks || tasks.length === 0) {
    container.appendChild(buildEmptyState(
      "📋",
      "No tasks found",
      activeProjectFilter
        ? "No tasks in this project yet. Create one with Quick-Add or New Task."
        : "No tasks yet. Use Quick-Add or the New Task tab to get started."
    ));
    return;
  }

  tasks.forEach(task => container.appendChild(buildTaskCard(task)));
}

function renderTasksEmpty(icon, title, subtitle) {
  const container = document.getElementById("task-list");
  container.innerHTML = "";
  container.appendChild(buildEmptyState(icon, title, subtitle));
}

function buildEmptyState(icon, title, subtitle) {
  const wrap = document.createElement("div");
  wrap.className = "empty-state";

  const ic = document.createElement("span");
  ic.className = "empty-icon";
  ic.setAttribute("aria-hidden", "true");
  ic.textContent = icon;

  const h = document.createElement("p");
  h.className = "empty-title";
  h.textContent = title;

  const sub = document.createElement("p");
  sub.className = "empty-subtitle";
  sub.textContent = subtitle;

  wrap.appendChild(ic);
  wrap.appendChild(h);
  wrap.appendChild(sub);
  return wrap;
}

// ── Build a single task card ──────────────────────────────────────────────
function buildTaskCard(task) {
  const priorityClass = { low: "priority-low", medium: "priority-medium", high: "priority-high" };
  const badgeClass    = { low: "badge-low",    medium: "badge-medium",    high: "badge-high"    };

  const card = document.createElement("div");
  card.className =
    "task-card " +
    (priorityClass[task.priority] || "") +
    (task.completed ? " task-completed" : "");
  card.dataset.taskId = task.id;

  // ── Top row: check circle + body + actions ──
  const top = document.createElement("div");
  top.className = "task-top";

  // Check-circle toggle (Complete / Reopen)
  const check = document.createElement("button");
  check.className = "task-check" + (task.completed ? " checked" : "");
  check.setAttribute("aria-label", task.completed ? "Reopen task" : "Mark task complete");
  check.setAttribute("title",      task.completed ? "Reopen"       : "Mark complete");
  check.addEventListener("click", () => toggleTaskComplete(task));

  // Body
  const body = document.createElement("div");
  body.className = "task-body";

  const titleEl = document.createElement("p");
  titleEl.className = "task-title";
  titleEl.textContent = task.title;             // safe: textContent

  body.appendChild(titleEl);

  if (task.description) {
    const desc = document.createElement("p");
    desc.className = "task-description";
    desc.textContent = task.description;        // safe: textContent
    body.appendChild(desc);
  }

  // Action buttons (revealed on hover via CSS)
  const actions = document.createElement("div");
  actions.className = "task-actions";

  const editBtn = document.createElement("button");
  editBtn.className = "task-action-edit";
  editBtn.setAttribute("aria-label", "Edit task");
  editBtn.setAttribute("title", "Edit");
  editBtn.innerHTML = "✎ <span>Edit</span>";
  editBtn.addEventListener("click", () => openEditModal(task));

  const delBtn = document.createElement("button");
  delBtn.className = "task-action-delete";
  delBtn.setAttribute("aria-label", "Delete task");
  delBtn.setAttribute("title", "Delete");
  delBtn.innerHTML = "✕ <span>Delete</span>";
  delBtn.addEventListener("click", () => deleteTask(task.id));

  actions.appendChild(editBtn);
  actions.appendChild(delBtn);

  top.appendChild(check);
  top.appendChild(body);
  top.appendChild(actions);
  card.appendChild(top);

  // ── Meta row: priority badge + due date + done badge ──
  const meta = document.createElement("div");
  meta.className = "task-meta";
  // Indent to align under title (offset by check width + gap)
  meta.style.paddingLeft = "30px";

  // Priority badge
  const badge = document.createElement("span");
  badge.className = "badge " + (badgeClass[task.priority] || "badge-medium");
  badge.textContent = task.priority.charAt(0).toUpperCase() + task.priority.slice(1);
  meta.appendChild(badge);

  // Due date
  if (task.due_date) {
    const due = document.createElement("span");
    due.className = "task-due";
    due.textContent = task.due_date;            // safe: textContent
    meta.appendChild(due);
  }

  // Completed badge
  if (task.completed) {
    const doneBadge = document.createElement("span");
    doneBadge.className = "badge badge-done";
    doneBadge.textContent = "Done";
    meta.appendChild(doneBadge);
  }

  card.appendChild(meta);
  return card;
}

// ── Toggle complete ───────────────────────────────────────────────────────
async function toggleTaskComplete(task) {
  const result = await apiFetch(`/tasks/${task.id}`, {
    method: "PUT",
    body: JSON.stringify({ completed: !task.completed }),
  });
  if (result.ok) loadTasks();
}

// ── Delete task ───────────────────────────────────────────────────────────
async function deleteTask(taskId) {
  if (!confirm("Delete this task? This cannot be undone.")) return;
  const result = await apiFetch(`/tasks/${taskId}`, { method: "DELETE" });
  if (result.ok) loadTasks();
}

// ── Create task form ──────────────────────────────────────────────────────
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

  const result = await apiFetch("/tasks", {
    method: "POST",
    body: JSON.stringify({
      title,
      description: desc,
      priority,
      due_date: dueRaw || null,
      completed,
      project_id: projectId,
    }),
  });

  if (result.ok) {
    document.getElementById("create-task-form").reset();
    switchTab("tasks", document.querySelector('.nav-tab[data-tab="tasks"]'));
  } else {
    const msg = result.data?.detail || "Failed to create task.";
    showError("create-task-error", typeof msg === "string" ? msg : JSON.stringify(msg));
  }
}

// ── Edit modal ────────────────────────────────────────────────────────────
function openEditModal(task) {
  document.getElementById("edit-task-id").value     = task.id;
  document.getElementById("edit-title").value       = task.title;
  document.getElementById("edit-desc").value        = task.description || "";
  document.getElementById("edit-priority").value    = task.priority;
  document.getElementById("edit-due").value         = task.due_date || "";
  document.getElementById("edit-completed").checked = task.completed;
  clearError("edit-error");
  document.getElementById("edit-modal").classList.remove("hidden");
  // Focus first input for keyboard users
  document.getElementById("edit-title").focus();
}

function closeEditModal(event) {
  if (event.target === document.getElementById("edit-modal")) {
    document.getElementById("edit-modal").classList.add("hidden");
  }
}

async function submitEditTask(event) {
  event.preventDefault();
  clearError("edit-error");

  const taskId    = parseInt(document.getElementById("edit-task-id").value, 10);
  const title     = document.getElementById("edit-title").value.trim();
  const desc      = document.getElementById("edit-desc").value.trim() || null;
  const priority  = document.getElementById("edit-priority").value;
  const dueRaw    = document.getElementById("edit-due").value;
  const completed = document.getElementById("edit-completed").checked;

  const result = await apiFetch(`/tasks/${taskId}`, {
    method: "PUT",
    body: JSON.stringify({
      title,
      description: desc,
      priority,
      due_date: dueRaw || null,
      completed,
    }),
  });

  if (result.ok) {
    document.getElementById("edit-modal").classList.add("hidden");
    loadTasks();
  } else {
    const msg = result.data?.detail || "Update failed.";
    showError("edit-error", typeof msg === "string" ? msg : JSON.stringify(msg));
  }
}

// ── Keyboard: close modal on Escape ──────────────────────────────────────
document.addEventListener("keydown", e => {
  if (e.key === "Escape") {
    const modal = document.getElementById("edit-modal");
    if (modal && !modal.classList.contains("hidden")) {
      modal.classList.add("hidden");
    }
  }
});

// ============================================================
// STATS
// ============================================================
async function loadStats() {
  let url = "/tasks/stats";
  if (activeProjectFilter) url += `?project_id=${activeProjectFilter}`;

  const result = await apiFetch(url);
  if (!result.ok || !result.data) return;

  const s = result.data;
  const total     = s.total     || 0;
  const completed = s.completed || 0;
  const pending   = s.pending   || 0;
  const low       = s.by_priority?.low    || 0;
  const medium    = s.by_priority?.medium || 0;
  const high      = s.by_priority?.high   || 0;
  const rate      = s.completion_rate     || 0;

  // Key metric chips
  document.getElementById("stat-total").textContent     = total;
  document.getElementById("stat-completed").textContent = completed;
  document.getElementById("stat-pending").textContent   = pending;
  document.getElementById("stat-rate").textContent      = rate + "%";

  // Progress bar
  const pct = Math.min(Math.max(Math.round(rate), 0), 100);
  const barFill = document.getElementById("stat-rate-bar");
  const barPct  = document.getElementById("stat-rate-bar-pct");
  if (barFill) barFill.style.width = pct + "%";
  if (barPct)  barPct.textContent  = pct + "%";

  // Progress bar ARIA
  const track = barFill?.parentElement;
  if (track) track.setAttribute("aria-valuenow", pct);

  // Priority counts
  document.getElementById("stat-low").textContent    = low;
  document.getElementById("stat-medium").textContent = medium;
  document.getElementById("stat-high").textContent   = high;

  // Priority mini-bars (proportional to total)
  function setPriorityBar(id, count) {
    const el = document.getElementById(id);
    if (!el) return;
    const pct = total > 0 ? Math.round((count / total) * 100) : 0;
    el.style.width = pct + "%";
  }
  setPriorityBar("pbar-low",    low);
  setPriorityBar("pbar-medium", medium);
  setPriorityBar("pbar-high",   high);
}

// ============================================================
// QUICK-ADD
// ============================================================
async function submitQuickAdd() {
  clearError("quick-add-error");

  const text      = document.getElementById("quick-add-input").value.trim();
  const projectId = parseInt(document.getElementById("quick-add-project").value, 10);

  if (!text)      return showError("quick-add-error", "Please enter a task description.");
  if (!projectId) return showError("quick-add-error", "Please select a project first.");

  const result = await apiFetch("/tasks/quick-add", {
    method: "POST",
    body: JSON.stringify({ description: text, project_id: projectId }),
  });

  if (result.ok) {
    document.getElementById("quick-add-input").value = "";
    // Stay on tasks tab (or switch to it)
    switchTab("tasks", document.querySelector('.nav-tab[data-tab="tasks"]'));
  } else {
    const msg = result.data?.detail || "Quick-add failed.";
    showError("quick-add-error", typeof msg === "string" ? msg : JSON.stringify(msg));
  }
}

// Allow Enter key in quick-add input
document.addEventListener("DOMContentLoaded", () => {
  const qaInput = document.getElementById("quick-add-input");
  if (qaInput) {
    qaInput.addEventListener("keydown", e => {
      if (e.key === "Enter") submitQuickAdd();
    });
  }
});

// ============================================================
// SORT  (GET /tasks?sort=priority — insertion sort endpoint)
// ============================================================
async function sortTasks() {
  const field = document.getElementById("sort-field").value;
  if (!field) { loadTasks(); hideAlgoInfo(); return; }

  const result = await apiFetch(`/tasks?sort=${encodeURIComponent(field)}`);

  if (result.ok && Array.isArray(result.data)) {
    const tasks       = result.data;
    const comparisons = result.headers?.get("x-sort-comparisons");
    renderTasks(tasks);
    showAlgoInfo(
      `Sorted by "${field}" using insertion sort` +
      (comparisons ? ` — ${comparisons} comparisons` : "") + "."
    );
  }
}

// ============================================================
// SEARCH  (GET /tasks/search?title=...&algo=... )
// ============================================================
async function searchTasks() {
  const q    = document.getElementById("search-input").value.trim();
  const algo = document.getElementById("search-method").value;

  if (!q) { loadTasks(); hideAlgoInfo(); return; }

  const result = await apiFetch(
    `/tasks/search?title=${encodeURIComponent(q)}&algo=${encodeURIComponent(algo)}`
  );

  if (result.ok && result.data) {
    const tasks    = result.data.tasks    || [];
    const steps    = result.data.steps;
    const usedAlgo = result.data.algorithm || algo;
    renderTasks(tasks);
    showAlgoInfo(
      `${usedAlgo.charAt(0).toUpperCase() + usedAlgo.slice(1)} search ` +
      `for "${q}" — ${steps ?? "?"} step${steps !== 1 ? "s" : ""}, ` +
      `${tasks.length} result${tasks.length !== 1 ? "s" : ""} found.`
    );
  } else if (result.status === 404) {
    renderTasksEmpty(
      "🔍",
      "No results found",
      `No task with the exact title "${q}" was found.`
    );
    showAlgoInfo(
      `${algo.charAt(0).toUpperCase() + algo.slice(1)} search ` +
      `for "${q}" — 0 results.`
    );
  }
}

function clearSearch() {
  document.getElementById("search-input").value = "";
  hideAlgoInfo();
  loadTasks();
}

function showAlgoInfo(text) {
  const banner   = document.getElementById("algo-info");
  const textNode = document.getElementById("algo-info-text");
  if (!banner || !textNode) return;
  textNode.textContent = text;           // safe: textContent
  banner.classList.remove("hidden");
}

function hideAlgoInfo() {
  const banner = document.getElementById("algo-info");
  if (banner) banner.classList.add("hidden");
}

// ============================================================
// PROJECTS
// ============================================================
async function loadProjects() {
  const result = await apiFetch("/projects");
  if (!result.ok || !Array.isArray(result.data)) return;
  allProjects = result.data;
  renderProjects(allProjects);
  populateProjectSelects();
  renderProjectFilterList();        // update sidebar filter list
}

function renderProjects(projects) {
  const container = document.getElementById("project-list");
  container.innerHTML = "";

  if (!projects.length) {
    container.appendChild(buildEmptyState(
      "◫",
      "No projects yet",
      "Create your first project to start organising tasks."
    ));
    return;
  }

  projects.forEach(proj => {
    const card = document.createElement("div");
    card.className = "item-card";

    // Avatar with first letter
    const avatar = document.createElement("div");
    avatar.className = "item-avatar";
    avatar.setAttribute("aria-hidden", "true");
    avatar.textContent = proj.name.charAt(0).toUpperCase();

    // Info
    const info = document.createElement("div");
    info.className = "item-info";

    const name = document.createElement("p");
    name.className = "item-name";
    name.textContent = proj.name;              // safe: textContent

    info.appendChild(name);

    if (proj.description) {
      const desc = document.createElement("p");
      desc.className = "item-sub";
      desc.textContent = proj.description;    // safe: textContent
      info.appendChild(desc);
    }

    const ownerTag = document.createElement("p");
    ownerTag.className = "item-sub";
    ownerTag.textContent = "Owner ID: " + proj.owner_id;
    info.appendChild(ownerTag);

    // Actions
    const actions = document.createElement("div");
    actions.className = "item-actions";

    const delBtn = document.createElement("button");
    delBtn.className = "btn btn-danger-ghost btn-sm";
    delBtn.textContent = "Delete";
    delBtn.setAttribute("aria-label", `Delete project "${proj.name}"`);
    delBtn.addEventListener("click", () => deleteProject(proj.id));
    actions.appendChild(delBtn);

    card.appendChild(avatar);
    card.appendChild(info);
    card.appendChild(actions);
    container.appendChild(card);
  });
}

function populateProjectSelects() {
  // IDs of all <select> elements that list projects
  const selectIds = ["quick-add-project", "new-project"];

  selectIds.forEach(id => {
    const sel = document.getElementById(id);
    if (!sel) return;
    const placeholder = sel.options[0];   // keep "Select project…"
    sel.innerHTML = "";
    sel.appendChild(placeholder);

    allProjects.forEach(proj => {
      const opt = document.createElement("option");
      opt.value       = proj.id;
      opt.textContent = proj.name;        // safe: textContent
      sel.appendChild(opt);
    });
  });
}

function toggleNewProjectForm() {
  const form = document.getElementById("new-project-form");
  const btn  = document.getElementById("new-project-btn");
  const hidden = form.classList.toggle("hidden");
  if (btn) btn.setAttribute("aria-expanded", hidden ? "false" : "true");
  if (!hidden) populateOwnerSelect();
}

function populateOwnerSelect() {
  const sel = document.getElementById("proj-owner");
  if (!sel) return;
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

  if (!name)    return showError("create-project-error", "Project name is required.");
  if (!ownerId) return showError("create-project-error", "Please select an owner.");

  const result = await apiFetch("/projects", {
    method: "POST",
    body: JSON.stringify({ name, description: desc, owner_id: ownerId }),
  });

  if (result.ok) {
    // Reset and hide form
    document.getElementById("new-project-form").querySelector("form").reset();
    document.getElementById("new-project-form").classList.add("hidden");
    const btn = document.getElementById("new-project-btn");
    if (btn) btn.setAttribute("aria-expanded", "false");
    loadProjects();
  } else {
    const msg = result.data?.detail || "Failed to create project.";
    showError("create-project-error", typeof msg === "string" ? msg : JSON.stringify(msg));
  }
}

async function deleteProject(projectId) {
  if (!confirm("Delete this project and all its tasks? This cannot be undone.")) return;
  const result = await apiFetch(`/projects/${projectId}`, { method: "DELETE" });
  if (result.ok) {
    // If this was the active filter, reset it
    if (String(activeProjectFilter) === String(projectId)) {
      activeProjectFilter = "";
    }
    loadProjects();
    loadTasks();
  }
}

// ============================================================
// USERS
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
    container.appendChild(buildEmptyState(
      "◯",
      "No users yet",
      "Create a user first, then you can create projects and tasks."
    ));
    return;
  }

  users.forEach(user => {
    const card = document.createElement("div");
    card.className = "item-card";

    // Avatar
    const avatar = document.createElement("div");
    avatar.className = "item-avatar";
    avatar.setAttribute("aria-hidden", "true");
    avatar.textContent = user.name.charAt(0).toUpperCase();

    // Info
    const info = document.createElement("div");
    info.className = "item-info";

    const name = document.createElement("p");
    name.className = "item-name";
    name.textContent = user.name;            // safe: textContent

    const email = document.createElement("p");
    email.className = "item-sub";
    email.textContent = user.email;          // safe: textContent

    info.appendChild(name);
    info.appendChild(email);

    // Actions
    const actions = document.createElement("div");
    actions.className = "item-actions";

    const delBtn = document.createElement("button");
    delBtn.className = "btn btn-danger-ghost btn-sm";
    delBtn.textContent = "Delete";
    delBtn.setAttribute("aria-label", `Delete user "${user.name}"`);
    delBtn.addEventListener("click", () => deleteUser(user.id));
    actions.appendChild(delBtn);

    card.appendChild(avatar);
    card.appendChild(info);
    card.appendChild(actions);
    container.appendChild(card);
  });
}

function toggleNewUserForm() {
  const form = document.getElementById("new-user-form");
  const btn  = document.getElementById("new-user-btn");
  const hidden = form.classList.toggle("hidden");
  if (btn) btn.setAttribute("aria-expanded", hidden ? "false" : "true");
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
    document.getElementById("new-user-form").querySelector("form").reset();
    document.getElementById("new-user-form").classList.add("hidden");
    const btn = document.getElementById("new-user-btn");
    if (btn) btn.setAttribute("aria-expanded", "false");
    loadUsers();
  } else {
    const msg = result.data?.detail || "Failed to create user.";
    showError("create-user-error", typeof msg === "string" ? msg : JSON.stringify(msg));
  }
}

async function deleteUser(userId) {
  if (!confirm("Delete this user, all their projects, and all tasks? This cannot be undone.")) return;
  const result = await apiFetch(`/users/${userId}`, { method: "DELETE" });
  if (result.ok) {
    loadUsers();
    loadProjects();
    loadTasks();
  }
}

// ============================================================
// Bootstrap — load data on page ready
// ============================================================
document.addEventListener("DOMContentLoaded", async () => {
  // Sync toggle button icon with the theme already applied by the IIFE
  _updateToggleButton(
    document.documentElement.getAttribute("data-theme") === "dark"
  );
  await checkAuth();        // show login screen OR restore session and load data
});
