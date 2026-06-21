let STUDENTS = [];
let META = {};
let chart = null;
let currentView = "enquiries";
let repNames = [];          // persists agent names across redistributes
const filters = { tiers: new Set(), country: "", funding: "", intake: "", search: "" };

const $ = (id) => document.getElementById(id);

async function boot() {
  META = await (await fetch("/api/meta")).json();
  STUDENTS = await (await fetch("/api/students")).json();
  $("source-note").textContent = META.source_note;
  buildTierFilters();
  buildPillarLegend();
  buildSegments();
  render();
  wireEvents();
}

function buildTierFilters() {
  const box = $("tier-filters");
  box.innerHTML = "";
  META.tier_meta.forEach((t) => {
    const n = META.counts[t.name] || 0;
    const el = document.createElement("div");
    el.className = "tier-chip";
    el.innerHTML = `<span class="left"><span class="dot" style="background:${t.color}"></span>${t.name}</span><span class="cnt">${n}</span>`;
    el.onclick = () => {
      el.classList.toggle("active");
      filters.tiers.has(t.name) ? filters.tiers.delete(t.name) : filters.tiers.add(t.name);
      render();
    };
    box.appendChild(el);
  });
}

function buildPillarLegend() {
  const box = $("pillar-legend");
  const colors = { academic: "#22d3ee", financial: "#6366f1", intent: "#f59e0b" };
  box.innerHTML = "";
  Object.entries(META.weights || {}).forEach(([name, w]) => {
    const row = document.createElement("div");
    row.className = "pl-row";
    row.innerHTML = `<span class="pl-name">${cap(name)}</span>
      <span class="pl-bar"><span class="pl-fill" style="width:${w * 100}%;background:${colors[name]}"></span></span>
      <span class="pl-w">${Math.round(w * 100)}%</span>`;
    box.appendChild(row);
  });
}

function buildSegments() {
  const countries = [...new Set(STUDENTS.map((s) => s.target_country).filter(Boolean))].sort();
  const fundings = [...new Set(STUDENTS.map((s) => s.funding_type).filter(Boolean))].sort();
  const intakes = [...new Set(STUDENTS.map((s) => s.intake_year).filter(Boolean))].sort();
  fill($("country-filter"), countries, "All countries");
  fill($("funding-filter"), fundings, "All funding");
  fill($("intake-filter"), intakes, "All intakes");
}
function fill(sel, items, allLabel) {
  sel.innerHTML = `<option value="">${allLabel}</option>` +
    items.map((i) => `<option value="${esc(i)}">${esc(i)}</option>`).join("");
}

function wireEvents() {
  $("search").oninput = (e) => { filters.search = e.target.value.toLowerCase(); render(); };
  $("country-filter").onchange = (e) => { filters.country = e.target.value; render(); };
  $("funding-filter").onchange = (e) => { filters.funding = e.target.value; render(); };
  $("intake-filter").onchange = (e) => { filters.intake = e.target.value; render(); };
  $("overlay").onclick = closeDrawer;

  document.querySelectorAll(".tab").forEach((t) => {
    t.onclick = () => {
      document.querySelectorAll(".tab").forEach((x) => x.classList.remove("active"));
      t.classList.add("active");
      currentView = t.dataset.view;
      $("view-enquiries").hidden = currentView !== "enquiries";
      $("view-distribution").hidden = currentView !== "distribution";
      if (currentView === "distribution") distribute();
    };
  });
  $("redistribute").onclick = distribute;
  $("rep-count").onchange = distribute;
  $("export-assign").onclick = exportAssignments;
}

function applyFilters() {
  return STUDENTS.filter((s) => {
    if (filters.tiers.size && !filters.tiers.has(s.tier)) return false;
    if (filters.country && s.target_country !== filters.country) return false;
    if (filters.funding && s.funding_type !== filters.funding) return false;
    if (filters.intake && s.intake_year !== filters.intake) return false;
    if (filters.search) {
      const hay = `${s.name} ${s.email} ${s.target_course} ${s.target_country}`.toLowerCase();
      if (!hay.includes(filters.search)) return false;
    }
    return true;
  });
}

function render() {
  const rows = applyFilters();
  renderKpis();
  renderChart();
  renderTable(rows);
  $("result-count").textContent = `${rows.length} of ${STUDENTS.length}`;
  $("dist-sub").textContent = META.total ? `${META.total} contacts` : "";
  if (currentView === "distribution") distribute();
}

function renderKpis() {
  const priorityPct = META.total ? Math.round((META.priority / META.total) * 100) : 0;
  const kpis = [
    { v: META.total || 0, l: "Total enquiries" },
    { v: (META.average || 0), l: "Average strength score" },
    { v: META.priority || 0, l: "Priority (Strong + Very Good)", badge: priorityPct + "%", color: "#10b981" },
    { v: (META.counts && ((META.counts["Fair"] || 0) + (META.counts["Weak"] || 0))) || 0, l: "Guided / nurture track" },
  ];
  $("kpis").innerHTML = kpis.map((k) => `
    <div class="kpi">
      <div class="v">${k.v}</div>
      <div class="l">${k.l} ${k.badge ? `<span class="badge" style="background:${k.color}22;color:${k.color}">${k.badge}</span>` : ""}</div>
    </div>`).join("");
}

function renderChart() {
  const ctx = $("distChart");
  const labels = META.tier_order || [];
  const data = labels.map((t) => (META.counts && META.counts[t]) || 0);
  const colors = labels.map((t) => (META.tier_meta.find((m) => m.name === t) || {}).color);
  if (chart) chart.destroy();
  chart = new Chart(ctx, {
    type: "bar",
    data: { labels, datasets: [{ data, backgroundColor: colors, borderRadius: 8, maxBarThickness: 56 }] },
    options: {
      plugins: { legend: { display: false } },
      scales: {
        x: { grid: { display: false }, ticks: { color: "#8a98b8" } },
        y: { grid: { color: "#1c2741" }, ticks: { color: "#8a98b8", precision: 0 }, beginAtZero: true },
      },
    },
  });
}

function renderTable(rows) {
  const tb = $("tbody");
  $("empty").style.display = STUDENTS.length ? "none" : "block";
  tb.innerHTML = rows.map((s) => `
    <tr onclick="openDrawer(${s.rank})">
      <td class="rank">${s.rank}</td>
      <td><div class="s-name">${esc(s.name)}</div><div class="s-email">${esc(s.email)}</div></td>
      <td>${pill(s)}</td>
      <td class="score-cell">${s.score}</td>
      <td><span class="mini">${s.pillars.academic.score}</span></td>
      <td><span class="mini">${s.pillars.financial.score}</span></td>
      <td><span class="mini">${s.pillars.intent.score}</span></td>
      <td>${esc(s.target_country) || "—"}</td>
      <td>${esc(s.intake_year) || "—"}</td>
      <td>${esc(s.funding_type) || "—"}</td>
    </tr>`).join("");
}

function pill(s) {
  return `<span class="pill" style="background:${s.tier_color}22;color:${s.tier_color}">
    <span class="dot" style="background:${s.tier_color}"></span>${s.tier}</span>`;
}

function openDrawer(rank) {
  const s = STUDENTS.find((x) => x.rank === rank);
  if (!s) return;
  const pb = META.playbook[s.tier] || {};
  const pcolors = { academic: "#22d3ee", financial: "#6366f1", intent: "#f59e0b" };
  const pillarsHtml = Object.entries(s.pillars).map(([k, p]) => `
    <div class="d-pillar">
      <div class="top"><span>${cap(k)} <span class="muted">(${Math.round(p.weight * 100)}%)</span></span><b>${p.score}</b></div>
      <div class="bar"><span style="width:${p.score}%;background:${pcolors[k]}"></span></div>
      <div class="note">${esc(p.note)}</div>
    </div>`).join("");

  const flagsHtml = s.flags.length
    ? s.flags.map((f) => `<div class="flag">⚠ ${esc(f)}</div>`).join("")
    : `<div class="flag none">✓ No blockers flagged — clean profile.</div>`;

  const actions = (pb.actions || []).map((a) => `<li>${esc(a)}</li>`).join("");

  $("drawer").innerHTML = `
    <button class="close" onclick="closeDrawer()">×</button>
    <h3>${esc(s.name)}</h3>
    <div class="d-meta">${esc(s.email) || "no email"} · ${esc(s.phone) || "no phone"}</div>
    <div class="d-meta">${esc(s.target_course) || "course ?"} → ${esc(s.target_country) || "country ?"} · Intake ${esc(s.intake_year) || "?"} · ${esc(s.funding_type) || "funding ?"}</div>
    <div class="d-tier" style="background:${s.tier_color}22;color:${s.tier_color}">
      ${s.tier} · Score ${s.score} · Rank #${s.rank}</div>

    <div class="d-section"><h4>Score breakdown</h4>${pillarsHtml}</div>
    <div class="d-section"><h4>Flags to address</h4><div class="flags">${flagsHtml}</div></div>

    <div class="d-section"><h4>Customer-service playbook</h4>
      <div class="playbook">
        <div class="pb-head">${esc(pb.headline || "")}</div>
        <div class="pb-line"><b>SLA:</b> ${esc(pb.sla || "")}</div>
        <div class="pb-line"><b>Owner:</b> ${esc(pb.owner || "")}</div>
        <ul class="pb-actions">${actions}</ul>
        <div class="pb-track">“${esc(pb.talk_track || "")}”</div>
        <div class="pb-avoid">Avoid: ${esc(pb.avoid || "")}</div>
      </div>
    </div>`;
  $("drawer").classList.add("open");
  $("overlay").classList.add("open");
}
function closeDrawer() {
  $("drawer").classList.remove("open");
  $("overlay").classList.remove("open");
}

// ---------- Lead distribution (balanced by count AND quality) ----------
let lastAssignment = [];
const REP_PALETTE = ["#6366f1", "#22d3ee", "#10b981", "#f59e0b", "#ec4899",
  "#8b5cf6", "#14b8a6", "#f97316", "#3b82f6", "#84cc16", "#e11d48", "#06b6d4"];

function distribute() {
  const pool = applyFilters();
  const n = Math.max(1, Math.min(12, parseInt($("rep-count").value, 10) || 4));
  $("dist-pool").textContent = pool.length;

  const reps = Array.from({ length: n }, (_, i) => ({
    name: repNames[i] || `CS Agent ${i + 1}`,
    color: REP_PALETTE[i % REP_PALETTE.length],
    students: [], total: 0, tiers: {},
  }));

  // Go through students strongest-first; give each to the agent with the
  // fewest leads, breaking ties by the lowest total strength so far.
  // -> near-equal headcount AND near-equal average quality + tier mix.
  const sorted = [...pool].sort((a, b) => b.score - a.score);
  for (const s of sorted) {
    let best = reps[0];
    for (const r of reps) {
      if (r.students.length < best.students.length ||
        (r.students.length === best.students.length && r.total < best.total)) best = r;
    }
    best.students.push(s);
    best.total += s.score;
    best.tiers[s.tier] = (best.tiers[s.tier] || 0) + 1;
  }

  lastAssignment = reps;
  renderBalance(reps);
  renderRepCards(reps);
}

function renderBalance(reps) {
  const counts = reps.map((r) => r.students.length);
  const avgs = reps.map((r) => (r.students.length ? r.total / r.students.length : 0));
  const spread = avgs.length ? (Math.max(...avgs) - Math.min(...avgs)).toFixed(1) : 0;
  $("dist-balance").innerHTML = `
    <div>Headcount per agent: <b>${Math.min(...counts)}–${Math.max(...counts)}</b></div>
    <div>Avg strength range: <b>${avgs.length ? Math.min(...avgs).toFixed(1) : 0}–${avgs.length ? Math.max(...avgs).toFixed(1) : 0}</b></div>
    <div>Quality spread: <b>${spread} pts</b> (lower = fairer)</div>`;
}

function renderRepCards(reps) {
  const order = META.tier_order || [];
  $("dist-reps").innerHTML = reps.map((r, idx) => {
    const avg = r.students.length ? (r.total / r.students.length).toFixed(1) : "0";
    const tierBar = order.map((t) => {
      const c = r.tiers[t] || 0;
      if (!c) return "";
      const color = (META.tier_meta.find((m) => m.name === t) || {}).color;
      const pct = (c / r.students.length) * 100;
      return `<span style="width:${pct}%;background:${color}" title="${t}: ${c}"></span>`;
    }).join("");
    const rows = r.students.map((s) => `
      <div class="rep-row" onclick="openDrawer(${s.rank})">
        <span class="rdot" style="background:${s.tier_color}"></span>
        <span class="rname">${esc(s.name)}</span>
        <span class="muted">${esc(s.target_country)}</span>
        <span class="rscore">${s.score}</span>
      </div>`).join("");
    return `
      <div class="rep-card">
        <div class="rep-top">
          <div class="rep-avatar" style="background:${r.color}">${idx + 1}</div>
          <input class="rep-name" value="${esc(r.name)}" data-idx="${idx}"
                 onchange="renameRep(${idx}, this.value)">
        </div>
        <div class="rep-stats">
          <div class="rep-stat"><div class="v">${r.students.length}</div><div class="l">leads</div></div>
          <div class="rep-stat"><div class="v">${avg}</div><div class="l">avg score</div></div>
          <div class="rep-stat"><div class="v">${r.tiers["Strong"] || 0}+${r.tiers["Very Good"] || 0}</div><div class="l">priority</div></div>
        </div>
        <div class="rep-tiers">${tierBar}</div>
        <div class="rep-list">${rows || '<div class="muted" style="padding:8px">No leads</div>'}</div>
      </div>`;
  }).join("");
}

function renameRep(idx, value) {
  repNames[idx] = value.trim() || `CS Agent ${idx + 1}`;
  if (lastAssignment[idx]) lastAssignment[idx].name = repNames[idx];
}

function exportAssignments() {
  if (!lastAssignment.length) return;
  const head = ["Agent", "Rank", "Name", "Email", "Phone", "Score", "Tier",
    "Country", "Course", "Intake", "Funding"];
  const lines = [head.join(",")];
  lastAssignment.forEach((r) => {
    r.students.forEach((s) => {
      const row = [r.name, s.rank, s.name, s.email, s.phone, s.score, s.tier,
        s.target_country, s.target_course, s.intake_year, s.funding_type]
        .map((v) => `"${String(v == null ? "" : v).replace(/"/g, '""')}"`);
      lines.push(row.join(","));
    });
  });
  const blob = new Blob([lines.join("\n")], { type: "text/csv" });
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = "lead_assignments.csv";
  a.click();
  URL.revokeObjectURL(a.href);
}

const cap = (s) => s.charAt(0).toUpperCase() + s.slice(1);
const esc = (s) => String(s == null ? "" : s).replace(/[&<>"]/g, (c) =>
  ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));

boot();
