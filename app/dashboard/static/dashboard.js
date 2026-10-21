"use strict";
const $ = (id) => document.getElementById(id);
let signedIn = null;
const state = {
  page: "overview",
  selected: null,
  interval: 2000,
  eventOffset: 0,
  incidentLimit: 20,
  reportLimit: 20,
  settings: null,
  incidents: [],
  reports: [],
  busy: false,
  settingsDirty: false,
  detailSignature: null,
};
const names = {
  rapid_high_entropy_writes: "Rapid high-entropy writes",
  mass_rename: "Mass renaming",
  high_entropy: "High average entropy",
  cpu_spike: "Supported CPU heuristic",
  unknown_program: "Supported executable heuristic",
};
const time = (v) => (v ? new Date(v).toLocaleString() : "—");
const number = (v) =>
  v === null || v === undefined ? "—" : Number(v).toFixed(2);
function node(tag, value, cls) {
  const n = document.createElement(tag);
  if (value !== undefined) n.textContent = value;
  if (cls) n.className = cls;
  return n;
}
function clear(id) {
  $(id).replaceChildren();
  return $(id);
}
function message(text, error = false) {
  const box = $(error ? "error" : "notice");
  box.hidden = false;
  box.textContent = text;
}
async function api(url, options) {
  const response = await fetch(url, {
    ...options,
    signal: AbortSignal.timeout(15000),
  });
  if (!response.ok) {
    let detail;
    try {
      detail = (await response.json()).detail;
    } catch {
      detail = response.statusText;
    }
    throw Error(
      response.status === 401
        ? (signedIn?.mode !== "local" ? "Your session has expired. Sign in again at /login." : "Enter your local admin token in Setup & test to perform this action.")
        : response.status === 409
          ? "The state changed. Refresh and try again."
          : typeof detail === "string"
            ? detail
            : `Request failed (${response.status}). Check the entered values.`,
    );
  }
  return response.json();
}
async function mutate(url, body) {
  return api(url, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: "Bearer " + $("token").value,
      "X-CSRF-Token": signedIn?.user?.csrf || "",
    },
    body: JSON.stringify(body),
  });
}
function button(label, action, cls) {
  const b = node("button", label, cls);
  b.onclick = async () => {
    b.disabled = true;
    try {
      await action();
    } catch (e) {
      message(e.message, true);
    } finally {
      b.disabled = false;
    }
  };
  return b;
}
function table(headers, rows) {
  const wrap = node("div", undefined, "tablewrap"),
    t = node("table"),
    head = node("thead"),
    tr = node("tr");
  headers.forEach((h) => tr.append(node("th", h)));
  head.append(tr);
  t.append(head);
  const body = node("tbody");
  rows.forEach((row) => {
    const tr = node("tr");
    row.forEach((value) => {
      const td = node("td");
      if (value instanceof Node) td.append(value);
      else td.textContent = value ?? "—";
      tr.append(td);
    });
    body.append(tr);
  });
  t.append(body);
  wrap.append(t);
  return wrap;
}
function list(id, items, render, empty) {
  const box = clear(id);
  if (!items.length) box.append(node("p", empty, "empty"));
  else items.forEach((item) => box.append(render(item)));
}
function navigate(page) {
  state.page = page;
  document
    .querySelectorAll(".page")
    .forEach((n) => (n.hidden = n.id !== "page-" + page));
  document
    .querySelectorAll(".nav")
    .forEach((n) => n.classList.toggle("active", n.dataset.page === page));
  $("pageTitle").textContent = {
    overview: "Overview",
    incidents: "Incidents",
    activity: "File activity",
    reports: "Reports",
    setup: "Setup & test",
  }[page];
  location.hash = page;
}
document
  .querySelectorAll("[data-page]")
  .forEach((b) => (b.onclick = () => navigate(b.dataset.page)));
document
  .querySelectorAll("[data-go]")
  .forEach((b) => (b.onclick = () => navigate(b.dataset.go)));
function contributions(box, signals, facts = {}) {
  box.replaceChildren();
  const entries = Object.entries(signals || {});
  if (!entries.length) {
    box.append(
      node("p", "No detection rules are currently triggered.", "empty"),
    );
    return;
  }
  for (const [key, weight] of entries) {
    const row = node("div", undefined, "signal"),
      description = node("div");
    description.append(node("span", names[key] || key));
    const explanation =
      key === "mass_rename"
        ? `${facts.moved_files ?? 0} distinct moved files; ${facts.suffix_changes ?? 0} extension changes`
        : key === "rapid_high_entropy_writes"
          ? `${facts.high_entropy_files ?? 0} distinct files with high-entropy content`
          : key === "high_entropy"
            ? `${facts.valid_samples ?? 0} valid samples; average ${number(facts.mean_entropy)} bits/byte`
            : "Heuristic context, not confirmed writer identity";
    description.append(node("p", explanation, "muted"));
    row.append(description, node("b", "+" + weight));
    box.append(row);
  }
}
function chart(id, rows, key, max) {
  const svg = $(id);
  svg.replaceChildren();
  const valid = rows.some((r) => r[key] !== null && r[key] !== undefined);
  if (!valid) {
    const text = document.createElementNS("http://www.w3.org/2000/svg", "text");
    text.setAttribute("x", "18");
    text.setAttribute("y", "58");
    text.setAttribute("class", "chart-label");
    text.textContent = "No measurements available yet";
    svg.append(text);
    return;
  }
  let points = [];
  const draw = () => {
    if (points.length) {
      const line = document.createElementNS(
        "http://www.w3.org/2000/svg",
        "polyline",
      );
      line.setAttribute("points", points.join(" "));
      svg.append(line);
      points = [];
    }
  };
  rows.forEach((row, i) => {
    const value = row[key];
    if (value === null || value === undefined) {
      draw();
      return;
    }
    points.push(
      `${(i * 600) / Math.max(1, rows.length - 1)},${100 - (value / Math.max(1, max)) * 90}`,
    );
  });
  draw();
}
function incidentButton(i) {
  const b = button(
    `Peak ${i.peak_score} · ${i.status}`,
    async () => {
      state.selected = i.id;
      state.detailSignature = null;
      navigate("incidents");
      await showIncident();
    },
    "incident" + (state.selected === i.id ? " selected" : ""),
  );
  b.append(node("small", time(i.opened_at)), node("small", i.root));
  return b;
}
function renderOverview(s, alerts, metrics) {
  $("score").textContent = s.score;
  $("severity").textContent = s.severity;
  $("severity").className = "pill " + s.severity.toLowerCase();
  $("fill").style.width = s.score + "%";
  $("fill").style.background =
    s.severity === "Critical"
      ? "#f58b8b"
      : s.severity === "Warning"
        ? "#e9c26c"
        : "#82e2c1";
  $("scoreExplanation").textContent =
    `Activity in the last ${s.window_seconds} seconds. Historical incident peaks are retained after this score decays.`;
  $("monitor").textContent = s.monitor_state;
  const health = clear("health");
  for (const [k, v] of Object.entries({
    "Last event": time(s.last_processed),
    "Event queue": s.queue_depth,
    "Evidence queue": s.response_queue_depth,
    "Dropped events": s.dropped_events,
    "Process visibility": s.process_visibility,
    Database: (s.database_bytes / 1048576).toFixed(1) + " MB",
  }))
    health.append(node("dt", k), node("dd", v));
  for (const id of ["watchRoots", "setupRoots"])
    list(
      id,
      s.watch_paths,
      (p) => node("code", p, "path"),
      "No folders configured.",
    );
  if ($('folderScores')) {
    const labels={'finance':'Finance','hr':'Human Resources','customer-data':'Customer Data','legal':'Legal','backups':'Backups','sandbox':'General sandbox'};
    const rows=s.watch_paths.map(path=>{
      const live=s.roots.find(root=>root.root===path);
      const name=path.split('/').filter(Boolean).pop();
      return [labels[name]||name,path,live?live.score:'—',live?live.severity:'Starting',live?.facts?.changed_files??0,live?.facts?.moved_files??0];
    });
    clear('folderScores').append(table(['Department','Watched path','Score','Level','Changed files','Renamed files'],rows));
  }
  const latest = clear("latestIncident");
  if (state.incidents.length) {
    latest.append(
      incidentButton(state.incidents[0]),
      node(
        "p",
        "This historical peak is retained even when current activity is Normal.",
        "muted",
      ),
    );
  } else
    latest.append(
      node(
        "p",
        "No Critical incident recorded. Use Setup & test to verify the workflow.",
        "empty",
      ),
    );
  const peak = s.roots.reduce((a, b) => (a.score > b.score ? a : b), {
    score: -1,
  });
  contributions($("signals"), peak.contributions, peak.facts);
  list(
    "alerts",
    alerts,
    (a) => {
      const row = node("div", undefined, "row");
      row.append(
        node(
          "span",
          a.severity + " · " + a.score,
          "pill " + a.severity.toLowerCase(),
        ),
        node("small", time(a.timestamp)),
      );
      return row;
    },
    "No alert transitions recorded.",
  );
  const rows = metrics.scores
    .slice()
    .reverse()
    .map((x) => ({ ...x, entropy: x.facts.mean_entropy }));
  chart("entropyChart", rows, "entropy", 8);
  chart(
    "cpuChart",
    rows,
    "cpu_percent",
    Math.max(100, ...rows.map((r) => r.cpu_percent || 0)),
  );
}
function renderReports(id, items) {
  list(
    id,
    items,
    (r) => {
      const row = node("div", undefined, "report-row"),
        a = node("a", r.format === "html" ? "Open assessment report" : `Download ${r.format.toUpperCase()}`);
      a.href = "/reports/" + r.id + (r.format === "html" ? "/view" : "/download");
      if (r.format === "html") { a.target = "_blank"; a.rel = "noopener"; }
      if (r.requested_period) row.append(node("p", "Selected period: " + time(r.requested_period.start) + " → " + time(r.requested_period.end_exclusive), "muted"));
      row.append(
        a,
        node("span", r.snapshot ? "Snapshot" : "Final", "pill"),
        node(
          "p",
          time(r.timestamp) + " · Incident " + r.incident_id.slice(0, 8),
          "muted",
        ),
        node("p", "SHA-256 " + r.sha256, "hash"),
      );
      return row;
    },
    "No reports generated for this selection.",
  );
}
async function generate(format) {
  await mutate("/reports", { incident_id: state.selected, format });
  state.reports = await api("/reports?limit=" + state.reportLimit);
  message(
    format.toUpperCase() + " report generated. Use its download link below.",
  );
  await showIncident();
}
async function showIncident() {
  if (!state.selected) return;
  const requested = state.selected,
    d = await api("/incidents/" + requested);
  if (requested !== state.selected) return;
  const signature = JSON.stringify([
    requested,
    d.incident.status,
    d.incident.peak_score,
    d.event_timeline.length,
    d.evidence_manifest.length,
    d.evidence_state,
    state.reports.filter((r) => r.incident_id === requested).map((r) => r.id),
  ]);
  if (state.detailSignature === signature) return;
  state.detailSignature = signature;
  const box = clear("details"),
    i = d.incident;
  box.className = "";
  const heading = node("div", undefined, "sectiontitle");
  heading.append(
    node("h2", "Incident " + i.id.slice(0, 8)),
    node("span", i.status, "pill"),
  );
  box.append(
    heading,
    node(
      "p",
      `Opened ${time(i.opened_at)} · ${i.closed_at ? "Closed " + time(i.closed_at) : "Waiting for the activity window and cooldown to finish."}`,
      "muted",
    ),
  );
  const stats = node("div", undefined, "detail-stats");
  for (const [v, label] of [
    [i.peak_score, "Historical peak"],
    [(d.logical_files || []).length, "Distinct observed files"],
    [
      d.evidence_manifest.filter((e) => e.status === "copied").length,
      "Evidence copies",
    ],
    [d.copy_failures.length, "Copy failures"],
  ]) {
    const n = node("div");
    n.append(node("strong", v), node("span", label));
    stats.append(n);
  }
  box.append(stats, node("h3", "Detection reasons"));
  const signals = node("div");
  contributions(signals, i.peak_signals?.contributions, i.peak_signals?.facts);
  box.append(
    signals,
    node("p", d.attribution, "muted"),
    node("h3", "Affected files"),
  );
  box.append(
    table(
      [
        "Current / last observed path",
        "Previous path",
        "Entropy",
        "Observations",
      ],
      (d.logical_files || []).map((f) => [
        f.path,
        f.previous_paths.join(" → ") || "—",
        number(f.entropy),
        f.event_count,
      ]),
    ),
  );
  box.append(
    node("h3", "Evidence · " + d.evidence_state),
    node(
      "p",
      "Evidence is a copy of observed content, not a clean backup. Source files are never modified by the response.",
      "muted",
    ),
  );
  box.append(
    table(
      ["Source file", "Capture", "Bytes", "SHA-256 / reason"],
      d.evidence_manifest.map((e) => [
        e.source_path,
        e.status,
        e.bytes,
        e.error || e.sha256,
      ]),
    ),
  );
  const timeline = node("details");
  timeline.append(
    node("summary", `Event timeline · ${d.event_timeline.length} observations`),
    table(
      ["Time", "Event", "Source → destination", "Sample"],
      d.event_timeline.map((e) => [
        time(e.timestamp),
        e.event_type,
        e.source_path + (e.destination_path ? " → " + e.destination_path : ""),
        e.sampling_status,
      ]),
    ),
  );
  box.append(timeline, node("h3", "Reports"));
  const controls = node("div", undefined, "toolbar");
  controls.append(
    button("Generate assessment report", () => generate("html")),
    button("Generate JSON", () => generate("json")),
    button("Generate CSV", () => generate("csv")),
    button("Enter admin token", () => navigate("setup")),
  );
  box.append(controls);
  const downloads = node("div");
  downloads.id = "incidentReports";
  box.append(downloads);
  renderReports(
    "incidentReports",
    state.reports.filter((r) => r.incident_id === i.id),
  );
  box.append(node("h3", "Recommended next steps"));
  const ul = node("ul");
  d.recommendations.forEach((t) => ul.append(node("li", t)));
  box.append(ul);
}
async function loadEvents() {
  const q = new URLSearchParams({
    limit: "50",
    offset: String(state.eventOffset),
  });
  if ($("eventType").value) q.set("type", $("eventType").value);
  if ($("eventRoot").value) q.set("root", $("eventRoot").value);
  const events = await api("/events?" + q);
  const body = clear("events");
  events.forEach((e) => {
    const tr = node("tr");
    [
      time(e.timestamp),
      e.event_type,
      e.source_path + (e.destination_path ? " → " + e.destination_path : ""),
      number(e.entropy),
      e.sampling_status,
      e.source_kind === "scan" ? "Inventory" : "Live",
    ].forEach((v) => tr.append(node("td", v)));
    body.append(tr);
  });
  $("eventsEmpty").hidden = events.length !== 0;
  $("eventPage").textContent =
    `Showing ${events.length ? state.eventOffset + 1 : 0}–${state.eventOffset + events.length}`;
  $("previousEvents").disabled = state.eventOffset === 0;
  $("nextEvents").disabled = events.length < 50;
}
function guarded(action) {
  return async () => {
    try {
      await action();
    } catch (e) {
      message(e.message, true);
    }
  };
}
$("refreshEvents").onclick = guarded(loadEvents);
$("previousEvents").onclick = guarded(async () => {
  state.eventOffset = Math.max(0, state.eventOffset - 50);
  await loadEvents();
});
$("nextEvents").onclick = guarded(async () => {
  state.eventOffset += 50;
  await loadEvents();
});
for (const id of ["eventType", "eventRoot"])
  $(id).onchange = guarded(async () => {
    state.eventOffset = 0;
    await loadEvents();
  });
$("olderIncidents").onclick = () => {
  state.incidentLimit = Math.min(200, state.incidentLimit + 20);
};
$("olderReports").onclick = () => {
  state.reportLimit = Math.min(200, state.reportLimit + 20);
};
$("forgetToken").onclick = () => {
  $("token").value = "";
  message("Token cleared from this page.");
};
$("startScan").onclick = guarded(async () => {
  const job = await mutate("/scan", { root: $("scanRoot").value });
  message("Inventory started. Job " + job.id.slice(0, 8));
});
$("settingsForm").oninput = () => {
  state.settingsDirty = true;
};
$("settingsForm").onsubmit = async (event) => {
  event.preventDefault();
  try {
    const result = await mutate("/settings", {
      expected_version: state.settings.version,
      patch: {
        detection: {
          warning_min: Number($("warning").value),
          critical_min: Number($("critical").value),
          entropy_threshold: Number($("entropy").value),
        },
        dashboard: { poll_interval_seconds: Number($("pollSeconds").value) },
      },
    });
    state.settings = result;
    state.settingsDirty = false;
    message("Settings saved as version " + result.version + ".");
  } catch (e) {
    message(e.message, true);
    state.settings = await api("/settings");
  }
};
async function poll() {
  try {
    const [s, alerts, incidents, metrics, reports, settings, scans] =
      await Promise.all(
        [
          "/status",
          "/alerts?limit=8",
          "/incidents?limit=" + state.incidentLimit,
          "/metrics?limit=100",
          "/reports?limit=" + state.reportLimit,
          "/settings",
          "/scans?limit=5",
        ].map((u) => api(u)),
      );
    state.incidents = incidents;
    state.reports = reports;
    state.interval = s.poll_interval_seconds * 1000;
    $("connection").textContent = "Updated " + new Date().toLocaleTimeString();
    $("error").hidden = true;
    $("incidentCount").textContent = incidents.length;
    renderOverview(s, alerts, metrics);
    list(
      "incidents",
      incidents,
      incidentButton,
      "No incidents recorded. Critical activity creates an incident automatically.",
    );
    renderReports("reports", reports);
    const labels = {sandbox:'General sandbox',finance:'Finance',hr:'Human Resources','customer-data':'Customer Data',legal:'Legal',backups:'Backups'};
    for (const id of ['scanRoot','eventRoot']) {
      const select=$(id), previous=select.value;
      const paths=id==='eventRoot'?['',...s.watch_paths]:s.watch_paths;
      if (JSON.stringify(Array.from(select.options,o=>o.value))!==JSON.stringify(paths)) {
        select.replaceChildren(...paths.map(root=>{
          const name=root.split('/').filter(Boolean).pop();
          const option=node('option',root?`${labels[name]||name} — ${root}`:'All watched folders');
          option.value=root;
          return option;
        }));
        select.value=paths.includes(previous)?previous:paths[0]||'';
      }
    }
    if (!state.settingsDirty) {
      state.settings = settings;
      $("warning").value = settings.settings.detection.warning_min;
      $("critical").value = settings.settings.detection.critical_min;
      $("entropy").value = settings.settings.detection.entropy_threshold;
      $("pollSeconds").value =
        settings.settings.dashboard.poll_interval_seconds;
    }
    $("settingsVersion").textContent = " Effective version " + settings.version;
    list(
      "scans",
      scans,
      (j) =>
        node(
          "p",
          `${j.status} · ${j.count} files · ${j.failures} unavailable · ${j.error || time(j.timestamp)}`,
          "muted",
        ),
      "No inventories run yet.",
    );
    if (state.page === "activity") await loadEvents();
    if (state.page === "incidents" && state.selected) await showIncident();
  } catch (e) {
    message("Live data may be stale. " + e.message, true);
    $("connection").textContent = "Connection unavailable";
  } finally {
    setTimeout(poll, state.interval);
  }
}
const initial = location.hash.slice(1);
navigate(
  ["overview", "incidents", "activity", "reports", "setup"].includes(initial)
    ? initial
    : "overview",
);
poll();

function localInputDate(date) {
  return new Date(date.getTime() - date.getTimezoneOffset() * 60000).toISOString().slice(0, 16);
}
$("reportStart").value = localInputDate(new Date(new Date().setHours(0, 0, 0, 0)));
$("reportEnd").value = localInputDate(new Date(Date.now() + 60000));
$("createSelectedReports").onclick = guarded(async () => {
  const formats = [["formatHtml", "html"], ["formatJson", "json"], ["formatCsv", "csv"]]
    .filter(([id]) => $(id).checked).map(([, format]) => format);
  const start = new Date($("reportStart").value), end = new Date($("reportEnd").value);
  if (!formats.length || !Number.isFinite(+start) || !Number.isFinite(+end) || start >= end)
    throw Error("Choose at least one format and an end date/time later than the start.");
  $("createSelectedReports").disabled = true;
  clear("selectedReports");
  try {
    const result = await mutate("/reports/selection", {formats, start: start.toISOString(), end: end.toISOString()});
    $("reportSelectionMessage").textContent = result.message;
    renderReports("selectedReports", result.reports);
  } finally { $("createSelectedReports").disabled = false; }
});

api("/auth/me").then((account) => {
  signedIn = account;
  if (account.mode !== "local" && account.user) {
    $("accountName").textContent = account.user.email;
    $("signOut").hidden = false;
    $("signOut").onclick = guarded(async () => {
      await mutate("/auth/logout", {});
      location.assign("/login");
    });
  }
}).catch(() => {});
