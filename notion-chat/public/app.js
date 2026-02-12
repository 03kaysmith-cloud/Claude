// --- State ---
const STORAGE_KEY = "notion_chat_saved_dbs";
let savedDatabases = JSON.parse(localStorage.getItem(STORAGE_KEY) || "[]");

// --- DOM refs ---
const chat = document.getElementById("chat");
const form = document.getElementById("input-form");
const input = document.getElementById("user-input");
const status = document.getElementById("status");
const dbList = document.getElementById("db-list");
const dbUrlInput = document.getElementById("db-url-input");
const btnAddDb = document.getElementById("btn-add-db");
const btnDiscover = document.getElementById("btn-discover");
const btnToggleSidebar = document.getElementById("btn-toggle-sidebar");
const btnOpenSidebar = document.getElementById("btn-open-sidebar");
const sidebar = document.getElementById("sidebar");

// --- Helpers ---
function setStatus(text, loading = false) {
  status.textContent = text;
  status.className = "status" + (loading ? " loading" : "");
}

function addMessage(html, type = "system") {
  const div = document.createElement("div");
  div.className = `message ${type}`;
  div.innerHTML = html;
  chat.appendChild(div);
  chat.scrollTop = chat.scrollHeight;
}

function extractDbId(urlOrId) {
  // Handles full Notion URLs or raw IDs
  const match = urlOrId.match(/([a-f0-9]{32})/);
  if (match) return match[1];
  // Try with dashes
  const dashMatch = urlOrId.match(
    /([a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12})/
  );
  if (dashMatch) return dashMatch[1].replace(/-/g, "");
  return urlOrId.trim();
}

async function api(path, options = {}) {
  setStatus("Loading...", true);
  try {
    const res = await fetch(path, {
      headers: { "Content-Type": "application/json" },
      ...options,
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || `HTTP ${res.status}`);
    setStatus("Ready");
    return data;
  } catch (err) {
    setStatus("Error", true);
    throw err;
  }
}

// --- Notion property value extraction ---
function extractPropValue(prop) {
  if (!prop) return "";
  switch (prop.type) {
    case "title":
      return (prop.title || []).map((t) => t.plain_text).join("");
    case "rich_text":
      return (prop.rich_text || []).map((t) => t.plain_text).join("");
    case "number":
      return prop.number != null ? prop.number : "";
    case "select":
      return prop.select ? prop.select.name : "";
    case "multi_select":
      return (prop.multi_select || []).map((s) => s.name).join(", ");
    case "date":
      return prop.date ? prop.date.start : "";
    case "checkbox":
      return prop.checkbox ? "Yes" : "No";
    case "url":
      return prop.url || "";
    case "email":
      return prop.email || "";
    case "phone_number":
      return prop.phone_number || "";
    case "status":
      return prop.status ? prop.status.name : "";
    case "people":
      return (prop.people || []).map((p) => p.name || p.id).join(", ");
    case "relation":
      return (prop.relation || []).map((r) => r.id).join(", ");
    case "formula":
      if (prop.formula.type === "string") return prop.formula.string || "";
      if (prop.formula.type === "number") return prop.formula.number ?? "";
      if (prop.formula.type === "boolean") return prop.formula.boolean ? "Yes" : "No";
      if (prop.formula.type === "date") return prop.formula.date?.start || "";
      return "";
    case "rollup":
      if (prop.rollup.type === "number") return prop.rollup.number ?? "";
      if (prop.rollup.type === "array")
        return (prop.rollup.array || []).map((i) => extractPropValue(i)).join(", ");
      return "";
    case "created_time":
      return new Date(prop.created_time).toLocaleString();
    case "last_edited_time":
      return new Date(prop.last_edited_time).toLocaleString();
    case "created_by":
      return prop.created_by?.name || prop.created_by?.id || "";
    case "last_edited_by":
      return prop.last_edited_by?.name || prop.last_edited_by?.id || "";
    default:
      return JSON.stringify(prop[prop.type] ?? "");
  }
}

function renderTable(pages) {
  if (!pages.length) return "<em>No results.</em>";

  // Gather all property names from first page
  const propNames = Object.keys(pages[0].properties || {});
  const displayProps = propNames.slice(0, 6); // limit columns

  let html = '<div style="overflow-x:auto"><table class="data-table"><thead><tr>';
  displayProps.forEach((p) => (html += `<th>${esc(p)}</th>`));
  html += "</tr></thead><tbody>";

  pages.forEach((page) => {
    html += "<tr>";
    displayProps.forEach((p) => {
      html += `<td>${esc(String(extractPropValue(page.properties[p])))}</td>`;
    });
    html += "</tr>";
  });

  html += "</tbody></table></div>";
  if (propNames.length > 6)
    html += `<p style="color:var(--text-muted);font-size:12px;margin-top:4px">Showing ${displayProps.length} of ${propNames.length} columns</p>`;
  return html;
}

function renderBlockContent(blocks) {
  return blocks
    .map((b) => {
      const type = b.type;
      const data = b[type];
      if (!data) return "";
      if (data.rich_text) {
        const text = data.rich_text.map((t) => t.plain_text).join("");
        if (type === "heading_1") return `<h3>${esc(text)}</h3>`;
        if (type === "heading_2") return `<h4>${esc(text)}</h4>`;
        if (type === "heading_3") return `<h5>${esc(text)}</h5>`;
        if (type === "bulleted_list_item") return `<li>${esc(text)}</li>`;
        if (type === "numbered_list_item") return `<li>${esc(text)}</li>`;
        if (type === "to_do")
          return `<li>${data.checked ? "[x]" : "[ ]"} ${esc(text)}</li>`;
        if (type === "code")
          return `<pre><code>${esc(text)}</code></pre>`;
        return `<p>${esc(text)}</p>`;
      }
      if (type === "divider") return "<hr>";
      return "";
    })
    .filter(Boolean)
    .join("");
}

function esc(str) {
  const d = document.createElement("div");
  d.textContent = str;
  return d.innerHTML;
}

// --- Database sidebar ---
function saveDatabases() {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(savedDatabases));
}

function renderDbList() {
  dbList.innerHTML = "";
  if (!savedDatabases.length) {
    dbList.innerHTML =
      '<p style="color:var(--text-muted);font-size:13px;padding:12px">No databases saved yet. Paste a Notion URL above or click Discover.</p>';
    return;
  }
  savedDatabases.forEach((db, idx) => {
    const card = document.createElement("div");
    card.className = "db-card";
    card.innerHTML = `
      <div class="db-title">${esc(db.title)}</div>
      <div class="db-id">${db.id}</div>
      <button class="db-remove" data-idx="${idx}" title="Remove">&times;</button>
    `;
    card.addEventListener("click", (e) => {
      if (e.target.classList.contains("db-remove")) return;
      handleCommand(`/query ${db.title}`);
    });
    card.querySelector(".db-remove").addEventListener("click", () => {
      savedDatabases.splice(idx, 1);
      saveDatabases();
      renderDbList();
      addMessage(`Removed <strong>${esc(db.title)}</strong> from saved databases.`);
    });
    dbList.appendChild(card);
  });
}

function addDatabase(id, title) {
  if (savedDatabases.find((d) => d.id === id)) return;
  savedDatabases.push({ id, title: title || "Untitled" });
  saveDatabases();
  renderDbList();
}

btnAddDb.addEventListener("click", async () => {
  const raw = dbUrlInput.value.trim();
  if (!raw) return;
  const id = extractDbId(raw);
  try {
    const db = await api(`/api/databases/${id}`);
    const title = (db.title || []).map((t) => t.plain_text).join("") || "Untitled";
    addDatabase(id, title);
    addMessage(`Saved database: <strong>${esc(title)}</strong>`);
    dbUrlInput.value = "";
  } catch (err) {
    addMessage(`Could not fetch database: ${esc(err.message)}`, "error");
  }
});

btnDiscover.addEventListener("click", async () => {
  await handleCommand("/databases");
});

// Sidebar toggle
btnToggleSidebar.addEventListener("click", () => sidebar.classList.toggle("collapsed"));
btnOpenSidebar.addEventListener("click", () => sidebar.classList.remove("collapsed"));

// --- Command handling ---
async function handleCommand(text) {
  const trimmed = text.trim();

  if (trimmed.startsWith("/databases")) {
    addMessage("Discovering all accessible databases...", "system");
    try {
      const dbs = await api("/api/databases");
      if (!dbs.length) {
        addMessage("No databases found. Make sure you've shared databases with your integration in Notion.", "system");
        return;
      }
      let html = `<strong>Found ${dbs.length} database(s):</strong><ul>`;
      dbs.forEach((db) => {
        const title =
          (db.title || []).map((t) => t.plain_text).join("") || "Untitled";
        html += `<li><strong>${esc(title)}</strong> <span style="color:var(--text-muted);font-size:11px">(${db.id})</span></li>`;
        addDatabase(db.id, title);
      });
      html += "</ul><p>All databases saved to sidebar.</p>";
      addMessage(html);
    } catch (err) {
      addMessage(`Error: ${esc(err.message)}`, "error");
    }
    return;
  }

  if (trimmed.startsWith("/query ")) {
    const name = trimmed.slice(7).trim();
    const db = findDb(name);
    if (!db) {
      addMessage(`Database "<strong>${esc(name)}</strong>" not found in saved list. Try <code>/databases</code> first.`, "error");
      return;
    }
    addMessage(`Querying <strong>${esc(db.title)}</strong>...`, "system");
    try {
      const result = await api(`/api/databases/${db.id}/query`, {
        method: "POST",
        body: JSON.stringify({}),
      });
      if (!result.results || !result.results.length) {
        addMessage("Database is empty or returned no results.");
        return;
      }
      addMessage(
        `<strong>${esc(db.title)}</strong> (${result.results.length} rows):` +
          renderTable(result.results)
      );
    } catch (err) {
      addMessage(`Error querying: ${esc(err.message)}`, "error");
    }
    return;
  }

  if (trimmed.startsWith("/view ")) {
    const name = trimmed.slice(6).trim();
    const db = findDb(name);
    if (!db) {
      addMessage(`Database "<strong>${esc(name)}</strong>" not found. Try <code>/databases</code> first.`, "error");
      return;
    }
    try {
      const schema = await api(`/api/databases/${db.id}`);
      const title = (schema.title || []).map((t) => t.plain_text).join("") || "Untitled";
      let html = `<strong>${esc(title)}</strong> schema:<ul>`;
      Object.entries(schema.properties || {}).forEach(([name, prop]) => {
        html += `<li><strong>${esc(name)}</strong>: ${esc(prop.type)}`;
        if (prop.type === "select" && prop.select?.options) {
          html += ` (${prop.select.options.map((o) => esc(o.name)).join(", ")})`;
        }
        if (prop.type === "multi_select" && prop.multi_select?.options) {
          html += ` (${prop.multi_select.options.map((o) => esc(o.name)).join(", ")})`;
        }
        if (prop.type === "status" && prop.status?.options) {
          html += ` (${prop.status.options.map((o) => esc(o.name)).join(", ")})`;
        }
        html += "</li>";
      });
      html += "</ul>";
      addMessage(html);
    } catch (err) {
      addMessage(`Error: ${esc(err.message)}`, "error");
    }
    return;
  }

  if (trimmed.startsWith("/search ")) {
    const query = trimmed.slice(8).trim();
    addMessage(`Searching for "<strong>${esc(query)}</strong>"...`, "system");
    try {
      const data = await api(`/api/search?query=${encodeURIComponent(query)}`);
      if (!data.results || !data.results.length) {
        addMessage("No results found.");
        return;
      }
      let html = `<strong>${data.results.length} result(s):</strong><ul>`;
      data.results.forEach((item) => {
        let title = "Untitled";
        if (item.object === "page" && item.properties) {
          const titleProp = Object.values(item.properties).find(
            (p) => p.type === "title"
          );
          if (titleProp) title = extractPropValue(titleProp) || "Untitled";
        } else if (item.object === "database" && item.title) {
          title = item.title.map((t) => t.plain_text).join("") || "Untitled";
        }
        html += `<li><strong>${esc(title)}</strong> <span style="color:var(--text-muted)">[${item.object}]</span> <span style="color:var(--text-muted);font-size:11px">${item.id}</span></li>`;
      });
      html += "</ul>";
      addMessage(html);
    } catch (err) {
      addMessage(`Error: ${esc(err.message)}`, "error");
    }
    return;
  }

  if (trimmed.startsWith("/read ")) {
    const query = trimmed.slice(6).trim();
    addMessage(`Looking for page "<strong>${esc(query)}</strong>"...`, "system");
    try {
      const data = await api(`/api/search?query=${encodeURIComponent(query)}`);
      const page = (data.results || []).find((r) => r.object === "page");
      if (!page) {
        addMessage("No matching page found.");
        return;
      }
      let title = "Untitled";
      const titleProp = Object.values(page.properties || {}).find(
        (p) => p.type === "title"
      );
      if (titleProp) title = extractPropValue(titleProp) || "Untitled";

      const blocks = await api(`/api/blocks/${page.id}/children`);
      const content = renderBlockContent(blocks.results || []);
      addMessage(
        `<strong>${esc(title)}</strong>` + (content || "<p><em>Page has no content blocks.</em></p>")
      );
    } catch (err) {
      addMessage(`Error: ${esc(err.message)}`, "error");
    }
    return;
  }

  if (trimmed.startsWith("/add ")) {
    // Format: /add Database Name | Property: Value, Property2: Value2
    const parts = trimmed.slice(5).split("|");
    if (parts.length < 2) {
      addMessage('Usage: <code>/add Database Name | Property: value, Property: value</code>', "error");
      return;
    }
    const dbName = parts[0].trim();
    const propsRaw = parts[1].trim();
    const db = findDb(dbName);
    if (!db) {
      addMessage(`Database "<strong>${esc(dbName)}</strong>" not found.`, "error");
      return;
    }
    try {
      // Get schema to know property types
      const schema = await api(`/api/databases/${db.id}`);
      const properties = {};
      propsRaw.split(",").forEach((pair) => {
        const [key, ...valueParts] = pair.split(":");
        const propName = key.trim();
        const value = valueParts.join(":").trim();
        const propSchema = schema.properties[propName];
        if (!propSchema) return;
        switch (propSchema.type) {
          case "title":
            properties[propName] = { title: [{ text: { content: value } }] };
            break;
          case "rich_text":
            properties[propName] = {
              rich_text: [{ text: { content: value } }],
            };
            break;
          case "number":
            properties[propName] = { number: parseFloat(value) };
            break;
          case "select":
            properties[propName] = { select: { name: value } };
            break;
          case "multi_select":
            properties[propName] = {
              multi_select: value.split(";").map((v) => ({ name: v.trim() })),
            };
            break;
          case "checkbox":
            properties[propName] = {
              checkbox: value.toLowerCase() === "true" || value === "1" || value.toLowerCase() === "yes",
            };
            break;
          case "url":
            properties[propName] = { url: value };
            break;
          case "email":
            properties[propName] = { email: value };
            break;
          case "date":
            properties[propName] = { date: { start: value } };
            break;
          case "status":
            properties[propName] = { status: { name: value } };
            break;
          default:
            // Try rich_text as fallback
            properties[propName] = {
              rich_text: [{ text: { content: value } }],
            };
        }
      });
      const page = await api("/api/pages", {
        method: "POST",
        body: JSON.stringify({
          parent_database_id: db.id,
          properties,
        }),
      });
      addMessage(`Entry added to <strong>${esc(db.title)}</strong>.`);
    } catch (err) {
      addMessage(`Error adding entry: ${esc(err.message)}`, "error");
    }
    return;
  }

  // Default: search
  addMessage(`Searching workspace for "<strong>${esc(trimmed)}</strong>"...`, "system");
  try {
    const data = await api(`/api/search?query=${encodeURIComponent(trimmed)}`);
    if (!data.results || !data.results.length) {
      addMessage("No results found. Try a different search term or use <code>/databases</code> to browse.");
      return;
    }
    let html = `<strong>${data.results.length} result(s) for "${esc(trimmed)}":</strong><ul>`;
    data.results.slice(0, 20).forEach((item) => {
      let title = "Untitled";
      if (item.object === "page" && item.properties) {
        const titleProp = Object.values(item.properties).find(
          (p) => p.type === "title"
        );
        if (titleProp) title = extractPropValue(titleProp) || "Untitled";
      } else if (item.object === "database" && item.title) {
        title = item.title.map((t) => t.plain_text).join("") || "Untitled";
      }
      html += `<li><strong>${esc(title)}</strong> <span style="color:var(--text-muted)">[${item.object}]</span></li>`;
    });
    html += "</ul>";
    addMessage(html);
  } catch (err) {
    addMessage(`Error: ${esc(err.message)}`, "error");
  }
}

function findDb(name) {
  const lower = name.toLowerCase();
  return (
    savedDatabases.find((d) => d.title.toLowerCase() === lower) ||
    savedDatabases.find((d) => d.title.toLowerCase().includes(lower)) ||
    savedDatabases.find((d) => d.id === name || d.id.includes(name))
  );
}

// --- Form submit ---
form.addEventListener("submit", (e) => {
  e.preventDefault();
  const text = input.value.trim();
  if (!text) return;
  addMessage(esc(text), "user");
  input.value = "";
  handleCommand(text);
});

// --- Keyboard shortcut ---
input.addEventListener("keydown", (e) => {
  if (e.key === "Escape") {
    input.value = "";
  }
});

// --- Init ---
renderDbList();
