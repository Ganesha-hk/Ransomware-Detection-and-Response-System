const { JSDOM } = require("jsdom");
const fs = require("fs");
const assert = require("node:assert/strict");
const path = require("node:path");
const source =
  process.env.RDRS_UI_SOURCE || path.resolve(__dirname, "../../app/dashboard");
const html = fs.readFileSync(path.join(source, "templates/index.html"), "utf8");
const js = fs.readFileSync(path.join(source, "static/dashboard.js"), "utf8");
const dom = new JSDOM(html, {
  url: "http://localhost/",
  runScripts: "outside-only",
});
const w = dom.window;
const bad = "<img src=x onerror=alert(1)>";
const incident = {
  id: "incident-test",
  root: "/sandbox",
  peak_score: 95,
  status: "closed",
  opened_at: new Date().toISOString(),
  closed_at: new Date().toISOString(),
  peak_signals: {
    contributions: { mass_rename: 30 },
    facts: { moved_files: 50, suffix_changes: 50 },
  },
};
const settings = {
  version: 1,
  settings: {
    detection: { warning_min: 40, critical_min: 70, entropy_threshold: 7.5 },
    dashboard: { poll_interval_seconds: 2 },
  },
};
const report = {
  id: "report-test",
  incident_id: incident.id,
  format: "json",
  timestamp: new Date().toISOString(),
  snapshot: false,
  sha256: "abc",
};
let fail = false;
let roots = ["/sandbox"];
const calls = [];
w.AbortSignal.timeout = () => new w.AbortController().signal;
w.setTimeout = () => 0;
w.fetch = async (url, options = {}) => {
  calls.push([url, options]);
  if (fail) throw Error("offline");
  let data;
  if (url === "/status")
    data = {
      score: 0,
      severity: "Normal",
      monitor_state: "running",
      roots: [],
      watch_paths: roots,
      window_seconds: 60,
      cooldown_seconds: 60,
      database_bytes: 1024,
      queue_depth: 0,
      response_queue_depth: 0,
      dropped_events: 0,
      process_visibility: "container",
      poll_interval_seconds: 2,
    };
  else if (url.startsWith("/alerts")) data = [];
  else if (url.startsWith("/incidents/"))
    data = {
      incident,
      event_timeline: [
        {
          timestamp: new Date().toISOString(),
          event_type: "moved",
          source_path: bad,
          destination_path: bad + ".locked",
          sampling_status: "ok",
        },
      ],
      logical_files: [
        { path: bad, previous_paths: [], entropy: 8, event_count: 1 },
      ],
      evidence_manifest: [],
      copy_failures: [],
      evidence_state: "complete",
      recommendations: ["Review the files"],
      attribution: "Unknown writer",
    };
  else if (url.startsWith("/incidents")) data = [incident];
  else if (url.startsWith("/metrics")) data = { scores: [], processes: [] };
  else if (url.startsWith("/reports"))
    data = options.method ? report : [report];
  else if (url.startsWith("/settings")) data = settings;
  else if (url.startsWith("/scans")) data = [];
  else if (url.startsWith("/events"))
    data = [
      {
        timestamp: new Date().toISOString(),
        event_type: "moved",
        source_path: bad,
        entropy: 8,
        sampling_status: "ok",
        source_kind: "live",
      },
    ];
  else if (url === "/scan") data = { id: "job" };
  else throw Error(url);
  return { ok: true, json: async () => data };
};
w.eval(js + "\nwindow.testPoll = poll;");
const flush = () => new Promise((resolve) => setTimeout(resolve, 30));
(async () => {
  await flush();
  assert.equal(w.document.getElementById("score").textContent, "0");
  assert.match(
    w.document.getElementById("latestIncident").textContent,
    /Peak 95/,
  );
  assert.match(w.document.getElementById("watchRoots").textContent, /sandbox/);
  w.document.querySelector('[data-page="incidents"]').click();
  w.document.querySelector("#incidents button").click();
  await flush();
  assert.match(
    w.document.getElementById("details").textContent,
    /Affected files/,
  );
  assert.equal(w.document.querySelectorAll("#details img").length, 0);
  assert.ok(w.document.getElementById("details").textContent.includes(bad));
  w.document.querySelector('[data-page="activity"]').click();
  w.document.getElementById("refreshEvents").click();
  await flush();
  assert.equal(w.document.querySelectorAll("#events img").length, 0);
  assert.ok(w.document.getElementById("events").textContent.includes(bad));
  w.document.querySelector('[data-page="setup"]').click();
  w.document.getElementById("token").value = "local-test-token";
  w.document.getElementById("startScan").click();
  await flush();
  assert.equal(
    calls.find(([url]) => url === "/scan")[1].headers.Authorization,
    "Bearer local-test-token",
  );
  w.document.getElementById("forgetToken").click();
  assert.equal(w.document.getElementById("token").value, "");
  roots=['/sandbox','/sensitive-lab/finance','/sensitive-lab/hr','/sensitive-lab/customer-data','/sensitive-lab/legal','/sensitive-lab/backups'];
  await w.testPoll();
  assert.equal(w.document.getElementById('scanRoot').options.length,6);
  assert.equal(w.document.getElementById('eventRoot').options.length,7);
  w.document.getElementById('scanRoot').value='/sensitive-lab/hr';
  await w.testPoll();
  assert.equal(w.document.getElementById('scanRoot').value,'/sensitive-lab/hr');
  roots=['/sandbox','/sensitive-lab/finance'];
  await w.testPoll();
  assert.equal(w.document.getElementById('scanRoot').value,'/sandbox');
  fail = true;
  await w.testPoll();
  assert.equal(w.document.getElementById("error").hidden, false);
  assert.match(w.document.getElementById("error").textContent, /stale/);
  console.log(
    "PASS: navigation, persistent peak, monitored scope, incident tables, filename escaping, event rendering, authenticated scan, token clearing, and stale-data errors.",
  );
})();
