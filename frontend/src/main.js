import { api, apiUrl, escapeHtml, formatBytes } from "./api.js";

const root = document.querySelector("#app");
const state = {
  user: null,
  checking: true,
  registerMode: false,
  screen: "files",
  folderId: null,
  search: "",
  files: [],
  folders: [],
  dashboard: null,
  busy: false,
  error: "",
  notice: "",
  avatarRevision: Date.now(),
};

const icon = {
  cloud: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M20 16.2A4.8 4.8 0 0 0 18 7h-1.1A7 7 0 1 0 5 17h13a4 4 0 0 0 2-0.8Z"/></svg>',
  home: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="m3 10 9-7 9 7"/><path d="M5 9v12h14V9M9 21v-7h6v7"/></svg>',
  folder: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M3 7a2 2 0 0 1 2-2h5l2 2h7a2 2 0 0 1 2 2v10a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/></svg>',
  upload: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 16V4m0 0L7 9m5-5 5 5"/><path d="M5 14v5a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2v-5"/></svg>',
  trash: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M3 6h18M8 6V4h8v2m3 0-1 14H6L5 6m4 4v6m6-6v6"/></svg>',
  search: '<svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="10.8" cy="10.8" r="6.8"/><path d="m16 16 5 5"/></svg>',
  settings: '<svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="12" cy="12" r="3"/><path d="m19.4 15 .1.1a1.7 1.7 0 1 1-2.4 2.4l-.1-.1a1.7 1.7 0 0 0-2.9 1.2v.3a1.7 1.7 0 1 1-3.4 0v-.2a1.7 1.7 0 0 0-2.9-1.2l-.1.1a1.7 1.7 0 1 1-2.4-2.4l.1-.1a1.7 1.7 0 0 0-1.2-2.9H4a1.7 1.7 0 1 1 0-3.4h.2a1.7 1.7 0 0 0 1.2-2.9l-.1-.1a1.7 1.7 0 1 1 2.4-2.4l.1.1a1.7 1.7 0 0 0 2.9-1.2V2a1.7 1.7 0 1 1 3.4 0v.2a1.7 1.7 0 0 0 2.9 1.2l.1-.1a1.7 1.7 0 1 1 2.4 2.4l-.1.1a1.7 1.7 0 0 0 1.2 2.9h.3a1.7 1.7 0 1 1 0 3.4h-.2a1.7 1.7 0 0 0-1.2 2.9Z"/></svg>',
  shield: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 22s8-4 8-11V5l-8-3-8 3v6c0 7 8 11 8 11Z"/><path d="m9 12 2 2 4-4"/></svg>',
  user: '<svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="12" cy="8" r="4"/><path d="M5 21a7 7 0 0 1 14 0"/></svg>',
  file: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M13 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V9z"/><path d="M13 2v7h7"/></svg>',
  image: '<svg viewBox="0 0 24 24" aria-hidden="true"><rect x="3" y="3" width="18" height="18" rx="2"/><circle cx="8.5" cy="8.5" r="1.5"/><path d="m21 15-5-5L5 21"/></svg>',
  camera: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M14 5h-4L8 7H4a2 2 0 0 0-2 2v10a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2V9a2 2 0 0 0-2-2h-4z"/><circle cx="12" cy="13" r="3"/></svg>',
  phone: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M22 16.9v3a2 2 0 0 1-2.2 2 19.8 19.8 0 0 1-8.6-3.1 19.4 19.4 0 0 1-6-6A19.8 19.8 0 0 1 2.1 4.2 2 2 0 0 1 4.1 2h3a2 2 0 0 1 2 1.7l.5 3a2 2 0 0 1-.6 1.7L7.7 9.7a16 16 0 0 0 6.6 6.6l1.3-1.3a2 2 0 0 1 1.7-.6l3 .5a2 2 0 0 1 1.7 2z"/></svg>',
  mail: '<svg viewBox="0 0 24 24" aria-hidden="true"><rect x="2" y="4" width="20" height="16" rx="2"/><path d="m22 7-10 6L2 7"/></svg>',
  check: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="m5 12 4 4L19 6"/></svg>',
  close: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="m18 6-12 12M6 6l12 12"/></svg>',
  logout: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M10 17l5-5-5-5m5 5H3"/><path d="M12 3h7a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2h-7"/></svg>',
};

function avatarMarkup(user, extraClass = "") {
  const photo = user.avatar_url
    ? `<img src="${escapeHtml(apiUrl(user.avatar_url))}?v=${state.avatarRevision}" alt="">`
    : escapeHtml(user.name.slice(0, 1).toUpperCase());
  return `<span class="avatar ${extraClass}">${photo}</span>`;
}

function flashMarkup() {
  return `${state.notice ? `<div class="alert success">${escapeHtml(state.notice)}<button data-action="clear-flash" aria-label="Dismiss">${icon.close}</button></div>` : ""}
    ${state.error ? `<div class="alert error">${escapeHtml(state.error)}<button data-action="clear-flash" aria-label="Dismiss">${icon.close}</button></div>` : ""}`;
}

function renderAuth() {
  return `<main class="auth-shell">
    <section class="auth-card">
      <div class="brand-mark">${icon.cloud}</div>
      <div class="eyebrow">YOUR SPACE, YOURS ALONE</div>
      <h1>${state.registerMode ? "Create your cloud" : "Welcome back"}</h1>
      <p class="muted">${state.registerMode ? "A calm, private place for your files." : "Your files are right where you left them."}</p>
      ${flashMarkup()}
      <form id="auth-form" class="auth-form">
        ${state.registerMode ? '<label>Your name<input name="name" autocomplete="name" required maxlength="120"></label>' : ""}
        <label>Email address<input name="email" type="email" autocomplete="email" required></label>
        <label>Password<input name="password" type="password" autocomplete="${state.registerMode ? "new-password" : "current-password"}" required ${state.registerMode ? "minlength=\"12\"" : ""}></label>
        ${state.registerMode ? "<small>Use at least 12 characters.</small>" : ""}
        <button class="primary full" ${state.busy ? "disabled" : ""}>${state.busy ? "Please wait…" : state.registerMode ? "Create account" : "Sign in"} <span>→</span></button>
      </form>
      <div class="switch-auth">${state.registerMode ? "Already have an account?" : "New to Nimbus?"}
        <button data-action="toggle-auth">${state.registerMode ? "Sign in" : "Create account"}</button>
      </div>
      <div class="secure-note">${icon.shield} Private storage, protected by your account</div>
    </section>
  </main>`;
}

function renderProfile() {
  const photo = state.user.avatar_url
    ? `<img src="${escapeHtml(apiUrl(state.user.avatar_url))}?v=${state.avatarRevision}" alt="${escapeHtml(state.user.name)}'s profile">`
    : escapeHtml(state.user.name.slice(0, 1).toUpperCase());
  return `<section class="content settings-content">
    <div class="settings-heading">
      <button class="back-link" data-action="files">← Back to My files</button>
      <h1>Profile &amp; settings</h1>
      <p>Manage how you appear and update your account details.</p>
    </div>
    ${flashMarkup()}
    <div class="settings-layout">
      <section class="settings-card photo-card">
        <div class="settings-card-heading"><div><h2>Your photo</h2><p>This picture appears beside your name.</p></div></div>
        <div class="photo-editor">
          <div class="profile-photo">${photo}</div>
          <div class="photo-copy">
            <strong>${escapeHtml(state.user.name)}</strong>
            <span>JPEG, PNG or WebP · up to 5 MB</span>
            <div class="photo-actions">
              <label class="secondary photo-upload">${icon.camera} ${state.busy ? "Please wait…" : "Choose a photo"}
                <input id="avatar-input" type="file" accept="image/jpeg,image/png,image/webp" ${state.busy ? "disabled" : ""} hidden>
              </label>
              ${state.user.avatar_url ? '<button class="text-button" data-action="remove-avatar">Remove photo</button>' : ""}
            </div>
          </div>
        </div>
      </section>
      <section class="settings-card">
        <div class="settings-card-heading">
          <div><h2>Personal information</h2><p>Keep your account details up to date.</p></div>
          <span class="private-pill">${icon.shield} Private</span>
        </div>
        <form id="profile-form" class="profile-form">
          <label><span>${icon.user} Full name</span>
            <input name="name" value="${escapeHtml(state.user.name)}" autocomplete="name" maxlength="120" required>
          </label>
          <label><span>${icon.mail} Email address</span>
            <input name="email" type="email" value="${escapeHtml(state.user.email)}" autocomplete="email" maxlength="320" required>
            <small>Used to identify your account.</small>
          </label>
          <label><span>${icon.phone} Phone number <em>Optional</em></span>
            <input name="phone" type="tel" value="${escapeHtml(state.user.phone ?? "")}" autocomplete="tel" maxlength="32" placeholder="+1 555 010 1234">
            <small>Your phone number is only visible to you.</small>
          </label>
          <div class="profile-form-footer">
            <span>${icon.shield} Your account details are stored privately.</span>
            <button class="primary save-profile" ${state.busy ? "disabled" : ""}>${icon.check} ${state.busy ? "Saving…" : "Save changes"}</button>
          </div>
        </form>
      </section>
    </div>
    ${footerMarkup()}
  </section>`;
}

function footerMarkup() {
  return `<footer class="footer"><span>Made for what matters.</span><span>${icon.shield} Your files are private by default</span></footer>`;
}

function fileIcon(item) {
  if (item.mime_type.startsWith("image/")) return icon.image;
  return icon.file;
}

function renderFileRow(item) {
  const actions = state.screen === "trash"
    ? `<button data-action="restore" data-id="${item.id}" title="Restore">↶</button><button data-action="permanent-delete" data-id="${item.id}" title="Delete permanently">${icon.close}</button>`
    : `<button data-action="download" data-id="${item.id}" title="Download">${icon.upload}</button><button data-action="trash" data-id="${item.id}" title="Move to Trash">${icon.trash}</button>`;
  return `<div class="file-row">
    <div class="file-name"><span class="file-icon ${item.mime_type.startsWith("image/") ? "image" : item.mime_type === "application/pdf" ? "pdf" : ""}">${fileIcon(item)}</span>
      <div><strong>${escapeHtml(item.name)}</strong><span>${escapeHtml(item.mime_type)}</span></div>
    </div>
    <span class="file-meta">${formatBytes(item.size_bytes)}</span>
    <span class="file-meta">${new Date(item.modified_at).toLocaleDateString()}</span>
    <div class="row-actions">${actions}</div>
  </div>`;
}

function renderBrowser() {
  const currentFolder = state.folders.find((folder) => folder.id === state.folderId);
  const visibleFolders = state.screen === "files"
    ? state.folders.filter((folder) => folder.parent_id === state.folderId)
    : [];
  const usedPercent = state.dashboard
    ? Math.min(100, state.dashboard.used_bytes / state.dashboard.quota_bytes * 100)
    : 0;
  const isTrash = state.screen === "trash";

  return `<div class="app-shell">
    <aside class="sidebar">
      <button class="logo" data-action="files"><span class="brand-mark">${icon.cloud}</span><span>Nimbus<span class="logo-period">.</span></span></button>
      <button class="upload-cta" data-action="choose-upload">${icon.upload} Upload files</button>
      <input id="upload-input" type="file" multiple hidden>
      <nav class="nav">
        <button class="${state.screen === "files" ? "active" : ""}" data-action="files">${icon.home} My files</button>
        <button class="${isTrash ? "active" : ""}" data-action="trash-screen">${icon.trash} Trash</button>
        <button class="${state.screen === "profile" ? "active" : ""}" data-action="profile">${icon.settings} Profile &amp; settings</button>
      </nav>
      <div class="sidebar-bottom">
        <div class="storage-card"><div class="storage-title">${icon.file} Storage</div>
          <div class="progress"><span style="width:${usedPercent}%"></span></div>
          <div class="storage-caption">${state.dashboard ? `${formatBytes(state.dashboard.used_bytes)} of ${formatBytes(state.dashboard.quota_bytes)} used` : "Loading storage…"}</div>
        </div>
        <div class="profile">${avatarMarkup(state.user)}
          <div class="profile-info"><strong>${escapeHtml(state.user.name)}</strong><span>${escapeHtml(state.user.email)}</span></div>
          <button class="icon-button" title="Profile and settings" data-action="profile">${icon.settings}</button>
          <button class="icon-button" title="Sign out" data-action="logout">${icon.logout}</button>
        </div>
      </div>
    </aside>
    <main class="main">
      <header class="topbar">
        <div class="mobile-brand">${icon.cloud} Nimbus</div>
        <label class="search-box">${icon.search}<input id="search-input" placeholder="Search your files" value="${escapeHtml(state.search)}"><kbd>⌘ K</kbd></label>
        <div class="top-actions"><span class="private-pill">${icon.shield} Private space</span>
          <button class="avatar-button" title="Profile and settings" data-action="profile">${avatarMarkup(state.user, "small")}</button>
        </div>
      </header>
      ${state.screen === "profile" ? renderProfile() : `<section class="content">
        <div class="page-heading">
          <div><div class="breadcrumbs"><button data-action="files">My files</button>${currentFolder ? `<span>/</span><span>${escapeHtml(currentFolder.name)}</span>` : ""}</div>
            <h1>${isTrash ? "Trash" : state.search ? "Search results" : escapeHtml(currentFolder?.name ?? "Good things, in one place.")}</h1>
            <p>${isTrash ? "Items here are only visible to you." : currentFolder ? "Your files, neatly gathered." : "A little room for everything that matters."}</p>
          </div>
          <div class="heading-actions">${!isTrash ? '<button class="secondary" data-action="new-folder">' + icon.folder + ' New folder</button>' : ""}
            <label class="primary upload-button">${icon.upload} Upload<input class="hidden-input" type="file" multiple data-upload></label>
          </div>
        </div>
        ${flashMarkup()}
        <div class="summary-row">
          <div><span class="summary-label">FILES</span><strong>${state.dashboard?.file_count ?? "—"}</strong></div>
          <div><span class="summary-label">FOLDERS</span><strong>${state.dashboard?.folder_count ?? "—"}</strong></div>
          <div><span class="summary-label">AVAILABLE</span><strong>${state.dashboard ? formatBytes(state.dashboard.remaining_bytes) : "—"}</strong></div>
        </div>
        ${!isTrash ? `<div class="section-title"><h2>Folders</h2><span>${visibleFolders.length} folders</span></div>
          ${visibleFolders.length ? `<div class="folder-grid">${visibleFolders.map((folder) => `<button class="folder-card" data-action="open-folder" data-id="${folder.id}"><span class="folder-icon">${icon.folder}</span><span class="folder-label"><strong>${escapeHtml(folder.name)}</strong><small>Folder</small></span><span class="folder-arrow">→</span></button>`).join("")}</div>` : ""}` : ""}
        <div class="section-title file-title"><h2>${isTrash ? "Deleted items" : "Files"}</h2><span>${state.files.length} ${state.files.length === 1 ? "item" : "items"}</span></div>
        ${state.busy ? '<div class="loading-bar"></div>' : ""}
        ${state.files.length ? `<div class="file-list"><div class="file-header"><span>Name</span><span>File size</span><span>Last modified</span><span>Actions</span></div>${state.files.map(renderFileRow).join("")}</div>`
          : `<div class="empty-state"><div class="empty-icon">${isTrash ? icon.trash : icon.cloud}</div><h3>${isTrash ? "Trash is clear" : state.search ? "No matches found" : "Your space is ready"}</h3><p>${isTrash ? "Deleted files will show up here." : state.search ? "Try a different name or keyword." : "Upload a file or create a folder to get started."}</p>${!isTrash && !state.search ? `<button class="secondary" data-action="choose-upload">${icon.upload} Upload your first file</button>` : ""}</div>`}
        ${footerMarkup()}
      </section>`}
    </main>
  </div>`;
}

function render() {
  if (state.checking) {
    root.innerHTML = `<div class="loading-screen">${icon.cloud}<span>Preparing your cloud...</span></div>`;
    return;
  }
  root.innerHTML = state.user ? renderBrowser() : renderAuth();
}

async function refresh() {
  if (!state.user || state.screen === "profile") return;
  try {
    const folder = state.folderId === null ? "" : `folder_id=${state.folderId}&`;
    const [files, folders, dashboard] = await Promise.all([
      api(`/api/v1/files?${folder}search=${encodeURIComponent(state.search)}&include_trash=${state.screen === "trash"}`),
      api("/api/v1/folders"),
      api("/api/v1/dashboard"),
    ]);
    state.files = files;
    state.folders = folders;
    state.dashboard = dashboard;
    state.error = "";
  } catch (error) {
    state.error = error.message;
  }
  render();
}

async function authenticate(form) {
  const data = new FormData(form);
  state.busy = true;
  state.error = "";
  render();
  try {
    if (state.registerMode) {
      await api("/api/v1/auth/register", {
        method: "POST",
        body: JSON.stringify({ name: data.get("name"), email: data.get("email"), password: data.get("password") }),
      });
    }
    state.user = await api("/api/v1/auth/login", {
      method: "POST",
      body: JSON.stringify({ email: data.get("email"), password: data.get("password") }),
    });
    state.screen = "files";
    state.notice = state.registerMode ? "Your account is ready. Welcome to Nimbus." : "";
    state.busy = false;
    await refresh();
  } catch (error) {
    state.error = error.message;
    state.busy = false;
    render();
  }
}

async function updateProfile(form) {
  const data = new FormData(form);
  state.busy = true;
  state.error = "";
  state.notice = "";
  render();
  try {
    state.user = await api("/api/v1/profile", {
      method: "PATCH",
      body: JSON.stringify({
        name: data.get("name"),
        email: data.get("email"),
        phone: data.get("phone"),
      }),
    });
    state.notice = "Your profile information has been saved.";
  } catch (error) {
    state.error = error.message;
  } finally {
    state.busy = false;
    render();
  }
}

async function uploadAvatar(file) {
  if (!file) return;
  state.busy = true;
  state.error = "";
  state.notice = "";
  render();
  try {
    const form = new FormData();
    form.append("file", file);
    state.user = await api("/api/v1/profile/avatar", { method: "POST", body: form });
    state.avatarRevision = Date.now();
    state.notice = "Your profile photo has been updated.";
  } catch (error) {
    state.error = error.message;
  } finally {
    state.busy = false;
    render();
  }
}

async function uploadFiles(input) {
  const selected = Array.from(input.files ?? []);
  if (!selected.length) return;
  state.busy = true;
  state.error = "";
  render();
  try {
    for (const file of selected) {
      const form = new FormData();
      form.append("file", file);
      const folder = state.folderId === null ? "" : `?folder_id=${state.folderId}`;
      await api(`/api/v1/files${folder}`, { method: "POST", body: form });
    }
    state.notice = `${selected.length} file${selected.length === 1 ? "" : "s"} uploaded.`;
    state.busy = false;
    await refresh();
  } catch (error) {
    state.error = error.message;
    state.busy = false;
    render();
  }
}

async function downloadFile(id) {
  try {
    const response = await fetch(apiUrl(`/api/v1/files/${id}/download`), { credentials: "include" });
    if (!response.ok) {
      const result = await response.json().catch(() => ({}));
      throw new Error(result.detail ?? `Request failed (${response.status})`);
    }
    const file = state.files.find((item) => item.id === Number(id));
    const url = URL.createObjectURL(await response.blob());
    const link = document.createElement("a");
    link.href = url;
    link.download = file?.name ?? "download";
    link.click();
    URL.revokeObjectURL(url);
  } catch (error) {
    state.error = error.message;
    render();
  }
}

async function handleAction(action, element) {
  const id = Number(element.dataset.id);
  try {
    switch (action) {
      case "toggle-auth":
        state.registerMode = !state.registerMode;
        state.error = "";
        state.notice = "";
        render();
        return;
      case "files":
        state.screen = "files";
        state.folderId = null;
        state.search = "";
        break;
      case "trash-screen":
        state.screen = "trash";
        state.folderId = null;
        state.search = "";
        break;
      case "profile":
        state.screen = "profile";
        state.error = "";
        state.notice = "";
        render();
        return;
      case "open-folder":
        state.folderId = id;
        break;
      case "choose-upload":
        document.querySelector("#upload-input")?.click();
        return;
      case "new-folder": {
        const name = window.prompt("Name your new folder");
        if (!name?.trim()) return;
        await api("/api/v1/folders", {
          method: "POST",
          body: JSON.stringify({ name: name.trim(), parent_id: state.folderId }),
        });
        state.notice = "Folder created.";
        break;
      }
      case "trash": {
        const item = state.files.find((file) => file.id === id);
        if (!item || !window.confirm(`Move "${item.name}" to Trash?`)) return;
        await api(`/api/v1/files/${id}`, { method: "DELETE" });
        state.notice = "Moved to Trash.";
        break;
      }
      case "restore":
        await api(`/api/v1/files/${id}/restore`, { method: "POST" });
        state.notice = "File restored.";
        break;
      case "permanent-delete": {
        const item = state.files.find((file) => file.id === id);
        if (!item || !window.confirm(`Permanently delete "${item.name}"? This cannot be undone.`)) return;
        await api(`/api/v1/files/${id}/permanent`, { method: "DELETE" });
        state.notice = "File permanently deleted.";
        break;
      }
      case "download":
        await downloadFile(id);
        return;
      case "remove-avatar":
        if (!window.confirm("Remove your profile photo?")) return;
        state.user = await api("/api/v1/profile/avatar", { method: "DELETE" });
        state.avatarRevision = Date.now();
        state.notice = "Your profile photo has been removed.";
        render();
        return;
      case "logout":
        await api("/api/v1/auth/logout", { method: "POST" });
        state.user = null;
        state.files = [];
        state.folders = [];
        state.dashboard = null;
        state.screen = "files";
        state.notice = "";
        state.error = "";
        render();
        return;
      case "clear-flash":
        state.error = "";
        state.notice = "";
        render();
        return;
      default:
        return;
    }
    state.error = "";
    await refresh();
  } catch (error) {
    state.error = error.message;
    render();
  }
}

root.addEventListener("click", (event) => {
  const button = event.target.closest("[data-action]");
  if (button) void handleAction(button.dataset.action, button);
});

root.addEventListener("submit", (event) => {
  if (event.target.id === "auth-form") {
    event.preventDefault();
    void authenticate(event.target);
  } else if (event.target.id === "profile-form") {
    event.preventDefault();
    void updateProfile(event.target);
  }
});

root.addEventListener("change", (event) => {
  if (event.target.id === "avatar-input") void uploadAvatar(event.target.files?.[0]);
  if (event.target.matches("[data-upload]")) void uploadFiles(event.target);
});

let searchTimer;
root.addEventListener("input", (event) => {
  if (event.target.id !== "search-input") return;
  state.search = event.target.value;
  clearTimeout(searchTimer);
  searchTimer = setTimeout(() => void refresh(), 250);
});

async function start() {
  try {
    state.user = await api("/api/v1/auth/me");
  } catch (error) {
    state.user = null;
    if (error.status !== 401) {
      state.error = "Could not connect to your account service. Check that the API is running and try again.";
    }
  } finally {
    state.checking = false;
    render();
    if (state.user) await refresh();
  }
}

render();
void start();
