let DATA = {};                 // payload from /api/agents
let STUDENTS = [];
let currentView = "overview";
let currentAgent = null;       // selected agent in the workspace tab
let search = "";

const $ = (id) => document.getElementById(id);
const STATUS_COLORS = {
  "New": "#8a98b8", "Attempted": "#f59e0b", "Contacted": "#3b82f6",
  "In Progress": "#8b5cf6", "Converted": "#10b981", "Lost": "#ef4444",
};

async function boot() {
  await refresh();
  wireEvents();
}

async function refresh() {
  DATA = await (await fetch("/api/agents")).json();
  STUDENTS = DATA.students || [];
  $("source-note").textContent = DATA.source_note || "—";
  if (currentAgent && !DATA.roster.includes(currentAgent)) currentAgent = null;
  if (!currentAgent) currentAgent = DATA.roster[0] || null;
  render();
}

function wireEvents() {
  $("overlay").onclick = closeDrawer;
  $("search").oninput = (e) => { search = e.target.value.toLowerCase(); render(); };

  document.querySelectorAll(".tab").forEach((t) => {
    t.onclick = () => {
      document.querySelectorAll(".tab").forEach((x) => x.classList.remove("active"));
      t.classList.add("active");
      currentView = t.dataset.view;
      $("view-overview").hidden = currentView !== "overview";
      $("view-agent").hidden = currentView !== "agent";
      $("view-audit").hidden = currentView !== "audit";
      render();
    };
  });

  $("agent-picker").onchange = (e) => { currentAgent = e.target.value; render(); };
  $("audit-agent").onchange = renderAudit;
}

function render() {
  if (currentView === "overview") renderOverview();
  if (currentView === "agent") renderAgent();
  if (currentView === "audit") renderAudit();
}

/* ---------------- Team overview ---------------- */
function renderOverview() {
  const agents = DATA.agents || [];
  const totalLeads = agents.reduce((a, r) => a + r.leads, 0);
  const contacted = agents.reduce((a, r) => a + r.contacted, 0);
  const converted = agents.reduce((a, r) => a + r.converted, 0);
  const actions = agents.reduce((a, r) => a + r.actions, 0);
  const contactedPct = totalLeads ? Math.round((contacted / totalLeads) * 100) : 0;

  const kpis = [
    { v: DATA.roster.length, l: "Customer-service agents" },
    { v: totalLeads, l: "Leads assigned" },
    { v: contacted, l: "Contacted", badge: contactedPct + "%", color: "#3b82f6" },
    { v: actions, l: "Actions logged", badge: converted + " won", color: "#10b981" },
  ];
  $("team-kpis").innerHTML = kpis.map((k) => `
    <div class="kpi">
      <div class="v">${k.v}</div>
      <div class="l">${k.l} ${k.badge ? `<span class="badge" style="background:${k.color}22;color:${k.color}">${k.badge}</span>` : ""}</div>
    </div>`).join("");

  $("overview-empty").style.display = totalLeads ? "none" : "block";

  const order = DATA.tier_order || [];
  const visible = agents.filter((r) => !search || r.name.toLowerCase().includes(search));
  $("agent-grid").innerHTML = visible.map((r) => {
    const tierBar = order.map((t) => {
      const c = r.tiers[t] || 0;
      if (!c) return "";
      const color = tierColor(t);
      return `<span style="width:${(c / r.leads) * 100}%;background:${color}" title="${t}: ${c}"></span>`;
    }).join("");
    return `
      <div class="rep-card" onclick="openAgent('${esc(r.name)}')">
        <div class="rep-top">
          <div class="rep-avatar" style="background:${avatarColor(r.name)}">${initials(r.name)}</div>
          <div style="flex:1">
            <div class="rep-name" style="border:none">${esc(r.name)}</div>
            <div class="muted" style="font-size:11px">${lastActive(r.last_active)}</div>
          </div>
        </div>
        <div class="rep-stats">
          <div class="rep-stat"><div class="v">${r.leads}</div><div class="l">leads</div></div>
          <div class="rep-stat"><div class="v">${r.avg}</div><div class="l">avg score</div></div>
          <div class="rep-stat"><div class="v">${r.contacted}</div><div class="l">contacted</div></div>
          <div class="rep-stat"><div class="v">${r.actions}</div><div class="l">actions</div></div>
        </div>
        <div class="rep-tiers">${tierBar || '<span style="width:100%;background:#23304f"></span>'}</div>
        <div class="rep-foot">
          <span class="chip" style="background:#10b98122;color:#10b981">${r.converted} won</span>
          <span class="chip" style="background:rgba(232,113,46,.15);color:#f6a870">${r.priority} priority</span>
        </div>
      </div>`;
  }).join("") || `<div class="muted" style="padding:10px">No agents on the roster. Click <b>Edit agents</b>.</div>`;
}

/* ---------------- Agent workspace ---------------- */
function openAgent(name) {
  currentAgent = name;
  currentView = "agent";
  document.querySelectorAll(".tab").forEach((x) =>
    x.classList.toggle("active", x.dataset.view === "agent"));
  $("view-overview").hidden = true;
  $("view-agent").hidden = false;
  $("view-audit").hidden = true;
  render();
}

function renderAgent() {
  const picker = $("agent-picker");
  picker.innerHTML = DATA.roster.map((a) =>
    `<option value="${esc(a)}" ${a === currentAgent ? "selected" : ""}>${esc(a)}</option>`).join("");

  const summary = (DATA.agents || []).find((a) => a.name === currentAgent) || { tiers: {} };
  const mine = STUDENTS.filter((s) => s.agent === currentAgent);
  const order = DATA.tier_order || [];

  $("agent-head").innerHTML = `
    <div class="agent-id">
      <div class="rep-avatar" style="background:${avatarColor(currentAgent || "")}">${initials(currentAgent || "")}</div>
      <div>
        <div class="agent-name">${esc(currentAgent || "—")}</div>
        <div class="muted">${lastActive(summary.last_active)}</div>
      </div>
    </div>
    <div class="rep-stats">
      <div class="rep-stat"><div class="v">${mine.length}</div><div class="l">leads</div></div>
      <div class="rep-stat"><div class="v">${summary.avg || 0}</div><div class="l">avg score</div></div>
      <div class="rep-stat"><div class="v">${summary.contacted || 0}</div><div class="l">contacted</div></div>
      <div class="rep-stat"><div class="v">${summary.converted || 0}</div><div class="l">won</div></div>
      <div class="rep-stat"><div class="v">${summary.actions || 0}</div><div class="l">actions</div></div>
    </div>
    <div class="tier-counts">${order.map((t) => {
      const c = (summary.tiers || {})[t] || 0;
      return `<span class="tc"><span class="dot" style="background:${tierColor(t)}"></span>${t}: <b>${c}</b></span>`;
    }).join("")}</div>`;

  const rows = mine
    .filter((s) => !search || `${s.name} ${s.email} ${s.target_course}`.toLowerCase().includes(search))
    .sort((a, b) => b.score - a.score);

  $("agent-empty").style.display = rows.length ? "none" : "block";
  $("agent-count").textContent = `${rows.length} lead${rows.length === 1 ? "" : "s"}`;
  $("agent-tbody").innerHTML = rows.map((s) => `
    <tr>
      <td><div class="s-name">${esc(s.name)}</div><div class="s-email">${esc(s.email)}</div></td>
      <td>${pill(s)}</td>
      <td class="score-cell">${s.score}</td>
      <td>${statusBadge(s.status)}</td>
      <td>${s.last_action ? esc(s.last_action) : "—"}</td>
      <td><span class="mini">${s.activity_count || 0}</span></td>
      <td><button class="btn-sm" onclick="openLog('${esc(s.email)}')">Log</button></td>
    </tr>`).join("");
}

/* ---------------- Audit log ---------------- */
async function renderAudit() {
  const sel = $("audit-agent");
  if (sel.dataset.filled !== "1") {
    sel.innerHTML = `<option value="">All agents</option>` +
      DATA.roster.map((a) => `<option value="${esc(a)}">${esc(a)}</option>`).join("");
    sel.dataset.filled = "1";
  }
  const agent = sel.value;
  const url = "/api/activity" + (agent ? `?agent=${encodeURIComponent(agent)}` : "");
  let log = await (await fetch(url)).json();
  if (search) {
    log = log.filter((e) => `${e.agent} ${e.student} ${e.action} ${e.note}`.toLowerCase().includes(search));
  }
  $("audit-empty").style.display = log.length ? "none" : "block";
  $("audit-count").textContent = `${log.length} event${log.length === 1 ? "" : "s"}`;
  $("audit-tbody").innerHTML = log.map((e) => `
    <tr>
      <td class="muted" style="white-space:nowrap">${fmtTime(e.ts)}</td>
      <td><span class="s-name">${esc(e.agent)}</span></td>
      <td>${esc(e.student) || esc(e.email)}</td>
      <td><span class="mini" style="background:#0f1730">${esc(e.action)}</span></td>
      <td>${e.status ? statusBadge(e.status) : "—"}</td>
      <td class="note-cell">${esc(e.note) || "—"}</td>
    </tr>`).join("");
}

/* ---------------- Log-action drawer ---------------- */
async function openLog(email) {
  const s = STUDENTS.find((x) => x.email === email);
  if (!s) return;
  const pb = (DATA.playbook || {})[s.tier] || {};
  const history = await (await fetch(`/api/activity?email=${encodeURIComponent(email)}`)).json();

  const actionOpts = (DATA.actions || []).map((a) => `<option value="${esc(a)}">${esc(a)}</option>`).join("");
  const statusOpts = `<option value="">— keep current —</option>` +
    (DATA.statuses || []).map((st) =>
      `<option value="${esc(st)}" ${st === s.status ? "selected" : ""}>${esc(st)}</option>`).join("");

  const histHtml = history.length
    ? history.map((e) => `
        <div class="hist-row">
          <span class="hist-dot" style="background:${e.status ? (STATUS_COLORS[e.status] || "#3b82f6") : "#3b82f6"}"></span>
          <div>
            <div class="hist-top"><b>${esc(e.action)}</b>${e.status ? ` → ${statusBadge(e.status)}` : ""}
              <span class="muted"> · ${esc(e.agent)}</span></div>
            <div class="muted" style="font-size:11px">${fmtTime(e.ts)}</div>
            ${e.note ? `<div class="hist-note">${esc(e.note)}</div>` : ""}
          </div>
        </div>`).join("")
    : `<div class="muted" style="font-size:13px">No activity logged yet.</div>`;

  $("drawer").innerHTML = `
    <button class="close" onclick="closeDrawer()">×</button>
    <h3>${esc(s.name)}</h3>
    <div class="d-meta">${esc(s.email) || "no email"} · ${esc(s.phone) || "no phone"}</div>
    <div class="d-meta">${esc(s.target_course) || "course ?"} → ${esc(s.target_country) || "country ?"} · Intake ${esc(s.intake_year) || "?"}</div>
    <div class="d-tier" style="background:${s.tier_color}22;color:${s.tier_color}">
      ${s.tier} · Score ${s.score}</div>
    <div class="d-meta">Owner: <b>${esc(s.agent)}</b> · Status: ${statusBadge(s.status)}</div>

    ${pb.sla ? `<div class="d-section"><h4>Playbook</h4>
      <div class="playbook">
        <div class="pb-head">${esc(pb.headline || "")}</div>
        <div class="pb-line"><b>SLA:</b> ${esc(pb.sla)}</div>
        ${pb.talk_track ? `<div class="pb-track">“${esc(pb.talk_track)}”</div>` : ""}
      </div></div>` : ""}

    <div class="d-section"><h4>Log an action</h4>
      <div class="logform">
        <label class="flabel">Action</label>
        <select id="log-action" class="select">${actionOpts}</select>
        <label class="flabel">Set status</label>
        <select id="log-status" class="select">${statusOpts}</select>
        <label class="flabel">Note</label>
        <textarea id="log-note" class="ta" placeholder="What happened? (optional)"></textarea>
        <button class="side-btn" id="log-save">Save to audit trail</button>
      </div>
    </div>

    <div class="d-section"><h4>History</h4><div class="hist">${histHtml}</div></div>`;

  $("log-save").onclick = () => saveLog(email);
  $("drawer").classList.add("open");
  $("overlay").classList.add("open");
}

async function saveLog(email) {
  const s = STUDENTS.find((x) => x.email === email);
  const btn = $("log-save");
  btn.disabled = true; btn.textContent = "Saving…";
  await fetch("/api/activity", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      email,
      agent: s ? s.agent : "",
      action: $("log-action").value,
      status: $("log-status").value,
      note: $("log-note").value,
    }),
  });
  closeDrawer();
  await refresh();
}

function closeDrawer() {
  $("drawer").classList.remove("open");
  $("overlay").classList.remove("open");
}

/* ---------------- helpers ---------------- */
function tierColor(t) { return ((DATA.tier_meta || []).find((m) => m.name === t) || {}).color || "#3b82f6"; }
function pill(s) {
  return `<span class="pill" style="background:${s.tier_color}22;color:${s.tier_color}">
    <span class="dot" style="background:${s.tier_color}"></span>${s.tier}</span>`;
}
function statusBadge(st) {
  const c = STATUS_COLORS[st] || "#8a98b8";
  return `<span class="pill" style="background:${c}22;color:${c}"><span class="dot" style="background:${c}"></span>${esc(st)}</span>`;
}
function initials(name) {
  return name.split(/\s+/).filter(Boolean).slice(0, 2).map((w) => w[0].toUpperCase()).join("") || "?";
}
const AV_PALETTE = ["#3b82f6", "#e8712e", "#10b981", "#f59e0b", "#ec4899", "#8b5cf6", "#14b8a6", "#f97316"];
function avatarColor(name) {
  let h = 0; for (const c of name) h = (h * 31 + c.charCodeAt(0)) >>> 0;
  return AV_PALETTE[h % AV_PALETTE.length];
}
function fmtTime(iso) {
  if (!iso) return "—";
  const d = new Date(iso);
  return d.toLocaleString([], { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" });
}
function lastActive(iso) { return iso ? "Last active " + fmtTime(iso) : "No activity yet"; }
const esc = (s) => String(s == null ? "" : s).replace(/[&<>"]/g, (c) =>
  ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));

boot();
