# RDRS build structure and Astra implementation brief

Prepared 20 October 2026. This is a build specification and agent handoff, not an implemented or tested application.

## 1. Read this first

Build the Ransomware Detection and Response System as a local, rules-based educational detector. Complete the required pipeline before adding optional features. No paid API, AI model, training dataset, cloud service, endpoint license, or real malware is required by the supplied documents. Existing computer capacity and package downloads are still needed. The user can use Astra to implement the project; Astra is the coding assistant, not a component of the detector.

Source precedence: the supplied FSD defines required functions; the Hands-On Build Guide supplies implementation expectations and submission criteria. This pack resolves unspecified behavior with explicit engineering decisions. Those decisions are proposed defaults, not additional requirements asserted to come from the institution. If a later PED or evaluator instruction conflicts, record the difference before changing scope.

Source documents reviewed in full:

- `RDRS_Functional_Specification_Document_FSD.docx`, version 1.0, sections 1–7.
- `RDRS_HandsOn_Build_Guide (1).docx`, sections 1–18, including ten phases and the grading rubric.

Deliver Markdown instructions alongside the repository because Astra can read them directly. Do not spend the first phase creating a polished dashboard while the detection pipeline remains mocked.

## 2. Review findings and decisions

| Finding in the supplied material | Build decision |
|---|---|
| FSD FR-1 through FR-13 describe a modest Python application | Implement all thirteen; use a modular monolith rather than microservices |
| Guide specifies rules rather than AI | Use transparent weighted signals; no ML or LLM integration |
| Guide score bands overlap at 40 and 70 | Normal: 0 <= score < 40; Warning: 40 <= score < 70; Critical: 70 <= score <= 100 |
| Signal weights total 120 | Add triggered weights and cap at 100; persist individual contributions |
| Guide calls one signal rapid encryption | Implement a rapid high-entropy write heuristic; label it suspected behavior, not proof of encryption |
| Guide implies process snapshots identify the writer | Treat process snapshots as context; writer identity remains unknown unless independently supported |
| Example watches all of `data` | Default to `data/sandbox`; always exclude database, logs, evidence, reports, and runtime state |
| Demo loops over all existing `*.txt` files | Replace it with an exclusive new run directory and an exact manifest of files created by that run |
| API, monitor, and dashboard startup ownership is not specified | One service owns all runtime components through application lifespan; one server worker |
| HTTP behavior and settings mutability are unspecified | Use the explicit contracts in this pack and validate settings atomically |
| File bursts can produce repetitive alerts | Aggregate incidents by watched root with a defined lifecycle and cooldown |
| Evidence copy may race with rename/delete/write | Store copy results, hashes, and stability state; failures never become successful evidence records |
| Docker is required but host visibility is unspecified | Monitor the mounted sandbox; describe process visibility as container-scoped |
| JSON and CSV required; HTML and PDF optional | Finish and test JSON and CSV before considering other report formats |
| Coverage is an aspiration in the guide | Set a proposed >=90% application line-coverage gate, backed by meaningful tests and real demo evidence |

The earlier conversational suggestions to isolate hosts, kill processes, or demonstrate recovery are outside the supplied baseline. Do not implement them. Evidence copying is not file recovery and does not prevent ransomware.

## 3. Scope and architecture

Required product: configuration, filesystem events, entropy sampling, process snapshots, persistence, sliding-window detection, scoring, alerts, incident evidence copies, REST API, live dashboard, JSON/CSV reports, tests, Docker, and submission evidence.

Out of scope: real malware, actual encryption of user files, process termination, host isolation, kernel drivers, EDR integration, production ransomware prevention, automatic restoration, multi-tenancy, remote agents, authentication providers, React unless genuinely needed, and paid infrastructure.

Default environment: Python 3.12, local Linux development first. Keep the Python logic portable, but do not claim Windows/macOS support without testing those systems. Use plain HTML/CSS/JavaScript, FastAPI, SQLite, SQLAlchemy, watchdog, psutil, Pydantic, PyYAML, Loguru, and Jinja2. Add pytest, pytest-cov, HTTPX, and Ruff for development. Pin a compatible tested dependency set during implementation; do not guess current package versions from this brief. ReportLab is optional and unnecessary for required JSON/CSV output.

### Runtime ownership

The FastAPI lifespan starts the observer, event-processing worker, periodic process sampler, score-expiry timer, and response/report worker. Shutdown stops intake, drains bounded work with a timeout, joins workers, and closes the database. Importing modules must not start background workers.

1. Watchdog callbacks normalize and enqueue filesystem events without doing expensive I/O.
2. A processing worker samples content safely, persists events, and updates per-root windows.
3. A pure detection/scoring module returns signals and explanations.
4. An incident service persists alerts and transitions, then queues evidence work.
5. API reads committed data; the dashboard polls the same API.
6. Reports use stored incident evidence and settings snapshots, not transient UI state.

Use bounded queues and expose queue depth, dropped events, worker health, and last successful processing time. A queue overflow makes status degraded; it must not silently imply complete coverage. Do not run blocking filesystem or database work on the API event loop. Keep ORM sessions scoped to their thread or operation; never share sessions across threads.

### Component boundaries

| Component | Owns | Must not own |
|---|---|---|
| Core | Validated configuration, event DTOs, path checks, clocks, logging | Dashboard or database queries |
| Collectors | Watchdog normalization and psutil snapshots | Incident decisions |
| Detection | Window statistics, rules, score calculation | File mutation or HTTP |
| Database | Schema, transactions, repositories | Watchdog lifecycle |
| Services | Runtime, incidents, evidence, scans, reports | HTML styling |
| API | Request validation and response serialization | Duplicated scoring logic |
| Dashboard | Polling and rendering API data | Invented sample incidents in live mode |

## 4. Repository structure

Create the following layout. Directory names are a specification, not evidence that code already exists. Add `__init__.py` in Python packages as needed.

```text
rdrs/
  README.md
  AGENTS.md
  pyproject.toml
  requirements.txt
  requirements-dev.txt
  config.yaml
  config.docker.yaml
  .env.example
  .gitignore
  .dockerignore
  Dockerfile
  docker-compose.yml
  app/
    main.py
    core/
      config.py
      logging.py
      entropy.py
      paths.py
      clock.py
      models.py
    detectors/
      file_monitor.py
      process_monitor.py
      event_normalizer.py
      sliding_window.py
      rules.py
      scoring.py
    database/
      session.py
      models.py
      repositories.py
      schema.py
    services/
      runtime.py
      event_pipeline.py
      incident_service.py
      evidence_service.py
      scan_service.py
      report_service.py
      settings_service.py
    api/
      main.py
      dependencies.py
      schemas.py
      routes_health.py
      routes_events.py
      routes_alerts.py
      routes_incidents.py
      routes_reports.py
      routes_settings.py
      routes_scans.py
      routes_metrics.py
    dashboard/
      templates/index.html
      static/dashboard.js
      static/styles.css
    reports/
      json_exporter.py
      csv_exporter.py
      recommendations.py
  scripts/
    simulate_activity.py
    verify_evidence.py
    collect_submission.py
  tests/
    conftest.py
    unit/
      test_config.py
      test_entropy.py
      test_paths.py
      test_windows.py
      test_rules.py
      test_scoring.py
      test_process_snapshots.py
    integration/
      test_pipeline.py
      test_incident_lifecycle.py
      test_evidence.py
      test_persistence.py
      test_api.py
      test_reports.py
      test_settings.py
    e2e/
      test_live_monitor.py
      test_demo_boundaries.py
  docs/
    requirements_matrix.md
    architecture.md
    decisions.md
    api.md
    testing.md
    demo_runbook.md
    limitations.md
    reflection.md
    BUILD_STATUS.md
  data/
    sandbox/
    quarantine/
    reports/
    rdrs.db
  logs/
  evidence/
    README.md
    demo/
    test-results/
    reports/
```

Runtime directories and the database are created at startup, not committed with private data. `evidence/` contains deliberately selected, sanitized submission artifacts only. Exclude virtual environments, caches, credentials, raw host process listings, generated runtime data, and local tokens from Git. Keep fixture data small and synthetic.

## 5. Configuration contract

The following YAML is the proposed baseline, to be validated by Pydantic. Values are starting points for the controlled demonstration, not calibrated detection claims.

```yaml
app:
  host: 127.0.0.1
  port: 8000
  simulation_mode: true
monitor:
  watch_paths: [./data/sandbox]
  recursive: true
  observer: native
  queue_capacity: 10000
  debounce_ms: 100
  sample_bytes: 65536
  sample_retries: 2
  exclude_paths: [./data/quarantine, ./data/reports, ./logs, ./evidence]
database:
  path: ./data/rdrs.db
  busy_timeout_ms: 5000
detection:
  window_seconds: 60
  tick_seconds: 1
  rapid_write_min_files: 20
  mass_rename_min_files: 20
  extension_change_min_files: 10
  high_entropy_min_files: 5
  entropy_threshold: 7.5
  cpu_threshold_percent: 80
  cpu_signal_enabled: false
  unknown_program_signal_enabled: false
  weights:
    rapid_high_entropy_writes: 40
    mass_rename: 30
    high_entropy: 25
    cpu_spike: 15
    unknown_program: 10
  warning_min: 40
  critical_min: 70
  incident_cooldown_seconds: 60
processes:
  sample_interval_seconds: 5
  allowlisted_executables: []
response:
  evidence_dir: ./data/quarantine
  max_files_per_incident: 100
  max_file_bytes: 10485760
  max_incident_bytes: 104857600
  simulate_termination: false
reports:
  output_dir: ./data/reports
dashboard:
  poll_interval_seconds: 2
logging:
  directory: ./logs
  rotation: 10 MB
  retention: 7 days
```

Resolve relative paths against the configuration file directory. Create only expected runtime directories. Reject filesystem roots and home-directory-wide default watches. Add mandatory exclusions for the SQLite file and its WAL/SHM sidecars regardless of YAML. Disallow watched output directories and overlapping watched roots in v1 to prevent double counting. Do not follow symlinks out of approved roots. Use safe YAML parsing, strict numeric bounds, and meaningful errors.

Validate `0 < warning_min < critical_min <= 100`, positive durations and limits, finite nonnegative weights, entropy within 0–8, and sampling bounds. `simulation_mode: false` is rejected in this educational version. `simulate_termination: true` only adds an audit entry describing an action that was not performed.

## 6. Event and process semantics

An event records a UUID, UTC timestamp, monotonic arrival time for live-window calculations, watched-root ID, event type, source path, destination path for moves, previous/new suffix, file identity when available, size, sampled bytes, entropy, sampling status, and source kind (`live` or `scan`). Record whether the observer synthesized the event. Do not store file contents in event rows.

Handle create, modify, move, and delete. Ignore directory-change noise for threat statistics. Never infer a delete's entropy from a failed file read. Empty readable files have entropy 0; missing, denied, oversized-policy-rejected, or unstable samples have null entropy plus a reason. Sample up to the first 65,536 bytes. Retain sample time because sampled bytes may represent a later state than the original event.

Debounce repetitive equivalent modify notifications without suppressing meaningful create/move/delete events. Keep a count of suppressed duplicates. Count distinct file identities per window so repeated callbacks on one file cannot become a mass-file attack. Track move chains using OS file identity when available and an in-window alias map otherwise. Distinguish old and new suffixes and preserve both paths in evidence.

For moves, sample the destination; if a queued modification refers to a vanished old path, resolve a known move alias and attempt a bounded retry. Sampling completion must trigger reevaluation so a fast rename cannot permanently hide the high-entropy signal. Do not follow arbitrary relocated paths outside approved roots.

Take process snapshots separately: PID, creation time, parent PID, name, executable if readable, CPU percentage, memory bytes, and cumulative write bytes if available. Derive write-rate from deltas only when two valid samples exist. Keep CPU units explicit; multi-core process percentages may exceed 100 under psutil semantics. Handle denied access and disappearing processes as expected conditions, not crashes. Prime CPU measurement and mark the first unavailable measurement unknown.

Portable watchdog file events do not provide a reliable writer PID. Temporal overlap or open-file observations may be shown as candidate context, never as confirmed causation. Store attribution method and confidence. Do not select the busiest process and call it the attacker. Missing metadata is unknown, not suspicious by itself. Exact writer attribution would require a separately scoped platform-specific collector.

## 7. Detection and scoring specification

Keep a separate window per configured root. Use monotonic arrival time for live expiry; use an injected clock in tests. Evict expired observations on every event and on a one-second timer so a quiet dashboard returns to Normal. Keep historical incident peaks after the live score decays.

Track distinct changed files, distinct moves, suffix-changing moves, successful content samples, average entropy, high-entropy file count, and supported process context. For statistics, use the latest valid content sample for each logical file still in the window, not repeated samples as additional files.

| Signal | Proposed trigger within the window | Weight |
|---|---|---:|
| Rapid high entropy writes | At least 20 distinct create/modify files whose current successful sample is >=7.5 | 40 |
| Mass rename | At least 20 distinct moved files, including at least 10 suffix changes | 30 |
| High entropy | At least 5 valid distinct changed-file samples and their mean entropy >=7.5 | 25 |
| CPU spike | Enabled explicitly; supported candidate context with a valid measurement >= configured CPU threshold | 15 |
| Unknown program | Enabled explicitly; readable executable absent from an explicit allowlist and supported candidate context | 10 |

The process signals are implemented and testable but disabled by default because portable file-to-process attribution is limited. Do not treat an empty allowlist as proof every process is malicious. Even when enabled, label process-based contributions heuristic. Do not let unrelated host CPU activity raise a root's score.

Calculate `min(100, sum(triggered_weights))`. Persist trigger facts, configured weights, configuration version, score, and severity. Boundary tests must cover 0, 39, 40, 69, 70, and 100. Configurable thresholds must remain ordered and validated.

Expected controlled scenarios with defaults:

- Small low-entropy edits: 0, Normal.
- One high-entropy file: 0 because minimum count is unmet.
- Five high-entropy files without a burst/rename: 25, Normal.
- Fifty high-entropy writes without renames: 65, Warning.
- Fifty text-file renames with suffix changes: 30, Normal.
- Fifty high-entropy writes plus matching mass renames: 95, Critical.

These are specified expected rule outcomes, not measured results. Compressed files, backup tools, and legitimate encryption can resemble the signals. Do not silently suppress all compressed extensions; demonstrate a benign workload and document residual false positives. This system cannot certify that files are safe or that ransomware was prevented.

### Incident lifecycle

Create an alert on entry to Warning or Critical; avoid a new alert for each event at the same level. On first Critical for a root, create one active incident with peak score and signal snapshot. Subsequent related events update the incident's last-seen time, affected files, and peak. Queue newly eligible evidence files once; do not recopy everything for every event.

After the score drops below Critical, wait 60 seconds without another Critical evaluation before closing the incident. A return to Critical during that cooldown updates the same incident. A later burst after closure creates a new incident. Scope state by root, not global. Persist lifecycle state so a restart does not blindly create duplicate open incidents. Mark an interrupted runtime and rebuild the live window honestly; do not reuse stale monotonic timestamps across restarts.

## 8. Persistence model

Enable SQLite foreign keys, use short transactions and bounded busy retries, and evaluate WAL mode for concurrent readers. A single ordered writer path is preferred. Keep a schema version and migration policy; never delete an existing database to solve a migration failure.

| Table | Essential fields and relationships |
|---|---|
| events | UUID, root, event type, observed time, source/destination path, suffixes, sample results, source kind; index root/time |
| processes | Snapshot ID, timestamp, PID plus creation time, parent, metadata and availability flags |
| scores | Root, timestamp, window summary, triggered contributions, score, severity, settings version |
| alerts | ID, root, score reference, severity transition, timestamp, optional incident reference |
| incidents | ID, root, opened/last-seen/closed times, status, peak score, settings snapshot, attribution status |
| incident_events | Incident/event relation with uniqueness constraint |
| evidence_files | Incident, originating event, source identity/path, stored relative path, hash, bytes, copy status, timestamp, error |
| reports | ID, incident, format, relative artifact path, hash, creation time and report version |
| scan_jobs | ID, approved root, status, counts, timestamps, error summary |
| settings_versions | Version, validated settings snapshot, timestamp, change summary without secrets |
| audit_records | Timestamp, action, target, outcome, details without credentials |

Use nullable fields for absent facts. Serialize ORM objects through API schemas, not raw internals. Freeze enough incident facts to make an old report understandable after settings change. Preserve incident-linked events when introducing retention. Log rotation alone does not bound database growth: v1 can document manual archival, but must expose database size and avoid deleting evidence automatically.

## 9. Evidence copying and simulated response

Copy eligible regular files into `data/quarantine/<incident_id>/` using unique generated names; retain the original relative path in a manifest. Never move, rename, delete, chmod, truncate, encrypt, quarantine in place, or modify source files as a response. Evidence copies may contain already changed content; they are not clean backups.

Validate both lexical and resolved paths. Reject symlinks, traversal, FIFOs, devices, and out-of-root files. Revalidate the opened file identity where supported to reduce path-swap races. Copy through a bounded stream to a temporary destination and atomically finalize the evidence file. Respect file count, file bytes, and incident bytes limits; record every skipped file and why. Hash the copied bytes using SHA-256.

Record source stat metadata before/after the copy. If a file changes during copying, label the capture unstable and retry only within a fixed limit; do not call it a forensic snapshot. Deleted/locked/missing files remain timeline evidence with an explicit copy failure. The manifest includes incident ID, event IDs, original path, stored path, byte count, SHA-256, copy time, status, and limitations. Evidence copy completion is separate from incident creation, and the UI shows pending/partial/complete state.

Write rotating `system`, `events`, `alerts`, `errors`, and `audit` logs without duplicating every message into every sink. Simulated termination logs `would_terminate` with `executed=false`; if identity is unknown, log that no target is established. Never invoke process-control APIs.

## 10. API and UI contracts

Bind to localhost by default. A random local admin token from an environment variable protects mutations; never commit it or expose it in logs. Dashboard reads can remain local without login. Restrict allowed hosts and cross-origin access. Do not automatically expose the service publicly. Container host publishing must remain loopback-only. Document a token creation/setup step or securely generate it on first run; the core read-only demonstration must not depend on an external account.

All data endpoints return JSON except the explicit report download route. Use ISO 8601 UTC times, stable IDs, bounded pagination (default 50, max 200), and consistent errors. Validation errors: 422; missing record: 404; unauthorized mutation: 401/403; conflicting scan/settings state: 409; unavailable subsystem: 503.

| Method and path | Required behavior |
|---|---|
| GET /health | Liveness and readiness; 503 when required runtime components fail |
| GET /status | Live per-root and maximum overall score, severity, active incidents, monitor state, simulation flag, uptime, queue/drop counters, process visibility |
| GET /events | Paginated events; filters for root, time, type and incident |
| GET /alerts | Paginated alert transitions; severity/time filters |
| GET /incidents | Paginated incidents with status and peak |
| GET /incidents/{id} | Timeline references, signals, files, attribution uncertainty and evidence state |
| GET /metrics | Bounded time series of CPU, entropy and counts, with timestamps and nulls for unavailable values |
| GET /reports | Generated report metadata only |
| POST /reports | Authorized generation for an existing incident and JSON/CSV format; return report metadata |
| GET /reports/{id}/download | Resolve only a stored report ID; never accept an arbitrary file path |
| POST /scan | Authorized bounded inventory of a configured root, returning 202 plus job ID |
| GET /scans/{id} | Scan progress, completion, results summary and failures |
| GET /settings | Effective non-secret settings and version |
| POST /settings | Authorized, strict partial update with expected version; validate and apply atomically |

`/scan` reads and inventories files; it does not create fake filesystem modifications. Persist inventory with source `scan` and keep it out of live burst counters. Limit concurrent scans, file count, total bytes, duration, and approved roots. Return a clear limit-reached state rather than silently omitting results.

Hot-update only thresholds, weights, and dashboard polling interval in v1. Reject runtime changes to paths, database, server bind, simulation mode, and worker topology with a restart-required explanation. Serialize config writes; retain a last-good configuration and rollback on failure. An expected-version mismatch returns 409. Record which settings version produced each score.

Dashboard sections: threat score and level; simulation badge; running/degraded/stopped monitor; recent alerts; recent events; top modified files by distinct logical file; CPU and mean-entropy time series; incident details and evidence state; JSON/CSV download buttons. Use a simple dark theme and local assets so the demo works without a CDN. Poll every two seconds, prevent overlapping requests, and show stale-data and API-error states. Escape filenames and process names before rendering. Do not present mocked charts as live telemetry.

## 11. Reporting contract

JSON contains schema version, incident ID and lifecycle, generation time, monitored root, settings snapshot, peak score and contributions, event timeline, affected files, process context with attribution caveats, evidence manifest, copy failures, and recommendations. Recommendations are defensive next steps for a human, not claims that response was executed.

CSV uses a documented record schema with `record_type` values such as summary, event, evidence, process_context, and recommendation. Include incident ID and relevant shared columns; leave non-applicable fields blank. This allows the required report information to survive CSV export without placing all metadata in an undocumented comment header. Escape spreadsheet formula-leading strings in untrusted text cells and quote using the standard CSV library. Keep JSON values faithful and make the CSV escaping policy explicit.

Write reports atomically to configured storage. Reports of active incidents are clearly timestamped snapshots and versioned; a final report is generated after closure and evidence work settles. Test that API data, stored rows, downloaded files, and evidence hashes agree. Do not fabricate a sample report before running the system.

## 12. Safe simulation and demonstrations

The simulator uses a dedicated `data/sandbox/<new-unique-run-id>/` directory created exclusively. It refuses an existing run directory, resolves the sandbox boundary, rejects symlinks, and operates only on files listed in its own manifest. It never globs arbitrary existing text files for mutation and has no option to target arbitrary user directories.

Positive demo: create 50 new text files; wait briefly for the monitor to observe the baseline; replace only those new files with 20,000 random bytes each; rename those files to `.locked`. This is random-content generation, not encryption. Leave run files for inspection. The simulator does not call the API to manufacture incidents. Its manifest is ground truth for evaluation, not a privileged signal consumed by the detector.

Add benign profiles for a few ordinary edits, isolated high-entropy content, and a backup/archive-like burst. Record expected versus observed behavior. Use uniquely named sentinel files outside the run directory and verify their hashes do not change. Demonstrate that evidence copying does not modify the final simulated source files; compare against hashes taken after simulation, not the initial text hashes intentionally changed by the simulator.

Proposed CLI contracts to implement and verify:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-dev.txt
python -m app.main --config config.yaml
# A second terminal, with the same virtual environment activated:
python scripts/simulate_activity.py --profile benign
python scripts/simulate_activity.py --profile burst
pytest --cov=app --cov-report=term-missing --cov-report=html --cov-fail-under=90
ruff check .
docker compose up --build
```

These are target interfaces, not commands already tested by this review. Include correct Windows activation instructions in the README if supporting Windows. `python -m app.main --watch ./data/sandbox` should be a validated convenience override. `uvicorn app.api.main:app` must use the same lifecycle; do not run it alongside a second standalone monitor on the same database. Run one worker and avoid reload in the recorded demo.

## 13. Build phases and gates

| Phase | Implement | Completion evidence |
|---|---|---|
| 0 Preparation | Read sources, inventory environment, architecture, requirements matrix, decision log, AGENTS.md | Every FR has a module and planned test; no undeclared scope expansion |
| 1 Foundation | Configuration, safe path policy, logging, entropy, DTOs | Entropy empty/repeated/uniform-byte tests; invalid YAML/path tests |
| 2 Observation | Real watcher, queue, normalization, exclusions, move handling | Actual create/modify/move/delete events captured; outputs excluded |
| 3 Persistence and processes | Schema, repositories, snapshots and availability flags | Restart persistence, concurrency check, denied/exited process handling |
| 4 Detection | Clock-injected windows, rules, scoring, timer expiry | Boundary, duplicate, multi-root, decay and all rule tests pass |
| 5 Incidents and evidence | Lifecycle, copy worker, manifest, simulated response | Exactly one incident per burst/cooldown; copies verified; sources unchanged by response |
| 6 API | Contract endpoints, bounded pagination, scans, versioned settings | Success and error cases tested; scans do not trigger live bursts |
| 7 Dashboard | Live views, charts, incident detail, errors, report controls | Observed browser update from real monitored changes |
| 8 Reports | Complete JSON/CSV, download and escaping | Parse exports, compare against stored incident, verify hashes |
| 9 Verification | Unit, integration, live filesystem demo, benign cases | Real test output, >=90% application line coverage or clearly documented remaining gap |
| 10 Packaging | Docker, Compose, README, submission artifacts | Fresh startup, persistent restart, live mounted-sandbox demo and actual demo evidence |

After each phase update `docs/BUILD_STATUS.md` with completed items, exact validation commands, results, limitations, next action, and changed files. Continue across routine implementation choices. Stop only for a genuine missing capability or decision that changes scope; do not ask permission after every file. Never report a later phase as done because its folder exists.

## 14. Acceptance and traceability

| FSD requirement | Main implementation | Acceptance proof |
|---|---|---|
| FR-1 config.yaml | core/config.py | Valid settings load; invalid values fail clearly; settings version retained |
| FR-2 four file event kinds | file_monitor.py, event_normalizer.py | Live filesystem test produces each event kind |
| FR-3 Shannon entropy | core/entropy.py | Empty=0; repeated byte=0; uniform 256-value fixture=8; I/O failures distinguished |
| FR-4 process metadata | process_monitor.py | Real snapshots plus denied/disappearing-process tests |
| FR-5 SQLite storage | database/ | Events, processes, scores, alerts, incidents survive restart |
| FR-6 sliding window | sliding_window.py | Injected-clock boundary and expiry tests; idle decay |
| FR-7 score 0–100 | rules.py, scoring.py | Explainable contributions; cap and severity boundary tests |
| FR-8 alerts and incidents | incident_service.py | Critical burst creates incident; repeated events update it without flooding |
| FR-9 simulated quarantine copy | evidence_service.py | Evidence exists, hashes match, original post-simulation files unchanged |
| FR-10 REST API | api/ | Required paths tested with real database and validation failures |
| FR-11 live dashboard | dashboard/ | Browser evidence shows actual event-to-UI update |
| FR-12 JSON/CSV reports | reports/, report_service.py | Both downloaded exports parse and agree with incident state |
| FR-13 testing and Docker | tests/, Dockerfile, Compose | Test logs plus real Compose startup and monitored demo |

Also verify rotating logging, documentation, simulation default, modularity and sandbox-only demonstrations. Separate measured latency from the vague source requirement “real time.” Proposed demo target: first Critical within five seconds of the final triggering operation, and dashboard visibility within one polling interval plus processing delay. Measure on the actual host and report the environment; do not treat this proposed target as an institutional SLA.

Required negative and failure tests: deleted-before-read file, permission denied, symlink escape, path traversal, duplicate events, one file modified repeatedly, rename-before-sample, empty sample, corrupted configuration, database lock, queue overflow, API unavailability, unsafe settings mutation, malicious HTML in a filename, CSV formula text, evidence quota exceeded, partial copy failure, shutdown during work, and process attribution unknown.

Use mocks for controlled error cases and pure-rule tests. At least one integration test must exercise the real database and filesystem, and one end-to-end demo must use the real observer. Do not satisfy all tests with mocks. Do not weaken coverage settings, skip failing tests, or redefine success to make the dashboard appear complete. Record uncovered platform cases honestly.

## 15. Docker and operational details

Use one non-root application container. Persist database, reports, evidence and logs in a writable data volume. Mount the host sandbox read-only for the monitoring service; the host-run simulator writes only within that sandbox. Publish `127.0.0.1:8000:8000`, with the service bound to `0.0.0.0` inside the container. Use a fixed configuration that refers to container paths. Do not request privileged mode, host PID namespace, Docker socket access, or the entire host filesystem.

Compose must initialize its runtime paths without permission errors and expose a health check. Prove restart persistence. Watcher delivery can differ by platform and mounted filesystem: offer a documented polling observer fallback and record its limitations. Process statistics in the container describe the container's visible processes, not an identified host writer. Demonstrate the host-local and container modes separately and label results.

## 16. Submission package and rubric alignment

Create a repository with working source, reproducible dependency files, architecture explanation, API documentation, configuration reference, safe demo instructions, limitations and troubleshooting. The guide's rubric assigns 30 points to detection, 15 each to code quality, testing, architecture/docs and feature breadth, and 10 to demo/write-up. Prioritize a working measured pipeline over optional PDF or UI embellishments.

Collect a sanitized evidence package after a real run:

1. Test and coverage outputs, command lines, runtime/package versions, OS, timestamp and commit SHA when available.
2. Screenshots or a short recording showing initial state, safe simulation, Critical incident, score contributions, evidence copies and both report downloads.
3. Generated JSON and CSV, corresponding logs, manifest and SHA-256 values.
4. A one-page reflection covering design, testing, a benign false-positive case, attribution limits and future work.
5. Requirements matrix with each FR marked implemented/tested/blocked and links to exact evidence.

Suggested recording sequence: show simulation mode and watched sandbox; demonstrate benign edits; run the burst; open the resulting incident; explain the 95-point score if that is the actual result; inspect copied evidence and hashes; download both reports; show passing tests. Do not stage a score or use edited footage to imply behavior that did not occur. If recording tools are unavailable, produce an exact runbook and real screenshots where possible, and mark the recording incomplete.

Do not claim institutional submission readiness without checking any additional PED or portal requirements. Only the two supplied documents were available for this review.

## 17. Master prompt for Astra

Copy the following prompt into Astra with this entire build pack and both original DOCX files attached or placed in the project workspace.

```text
You are implementing my Ransomware Detection and Response System educational project.
Read both supplied source documents and RDRS_Astra_Build_Pack.md completely before coding.
My main focus is offensive security; make this defensive project straightforward to run,
understand, demonstrate, and maintain. Use the sources for required scope and the build
pack for explicit engineering decisions. Record conflicts rather than silently dropping
requirements. Build the application, not merely a plan or a static dashboard.

First inspect the workspace, existing code, repository instructions, Python environment,
available browser/testing tools, and Docker availability. Preserve existing user work.
Use Python 3.12 with a modular FastAPI application, SQLite/SQLAlchemy, watchdog, psutil,
Pydantic/PyYAML, Loguru, and a small local HTML/CSS/JavaScript dashboard. Check primary
documentation as needed and pin dependencies after validating compatibility. Avoid paid
services, ML, cloud hosting and unnecessary frameworks.

Create docs/requirements_matrix.md, docs/decisions.md, docs/BUILD_STATUS.md and AGENTS.md.
Map FR-1 through FR-13 to modules, tests and evidence. Implement phases 0 through 10 in
order. Finish each phase's validation before advancing. Make reasonable reversible
implementation decisions autonomously and keep a concise progress record.

Hard requirements:
- Real filesystem monitoring, persisted events, process snapshots, windowed signals,
  explainable 0–100 scores, incidents, evidence copies, API, live dashboard and JSON/CSV.
- Simulation mode always on. No malware, real encryption, process killing, host isolation,
  deletion of original files, or automatic recovery. Evidence copying is copy-only.
- Simulator creates a fresh exclusive run folder and only changes files it created.
- Do not pretend watchdog plus psutil identifies the exact file-writing process.
  Unknown attribution must remain unknown in the UI, database and reports.
- One runtime owns collectors. No duplicate observers from API imports or multiple workers.
- Exclude logs, database sidecars, reports and evidence from monitoring. Bound queues and
  work; expose degraded status and dropped events instead of hiding data loss.
- Use unambiguous score boundaries, periodic decay, incident deduplication, guarded
  evidence copying, settings validation, API limits and safe report exports.
- The UI and reports must read real stored results. Do not hardcode demo incidents,
  fabricate screenshots or claim tests passed without execution.

Test pure rules and error cases, then the real database/filesystem pipeline, then a real
observer-driven sandbox demo. Target >=90% application line coverage with meaningful
tests. Run the benign cases and document false positives. Verify that evidence copying
leaves the post-simulation source files unchanged and that nothing outside the new run
directory was modified by the simulator. Build and test Docker if the environment allows.

Keep docs/BUILD_STATUS.md updated after each phase with commands, outputs, limitations,
remaining work and the exact next action. If you cannot run Docker, a supported OS, browser
checks or video recording, mark it unverified and provide an exact verification runbook;
never substitute an assumption for a passing result. Do not ask me to approve routine
file edits or each phase. Ask only for a real blocker or a material scope decision.

At completion provide: how to start the app; how to run the safe demo; which tests actually
passed; coverage; Docker verification status; sample generated reports; submission evidence;
known limitations; and any unfinished requirement. Credit libraries/sample code, and make
the documentation understandable enough for me to explain the design during evaluation.
Start with workspace inspection and phase 0, then continue into implementation.
```

### Continuation prompt

```text
Continue the RDRS implementation. Read AGENTS.md, docs/BUILD_STATUS.md,
docs/requirements_matrix.md, docs/decisions.md and RDRS_Astra_Build_Pack.md.
Inspect the actual code and latest validation outputs before trusting completion claims.
Resume the earliest incomplete phase, preserve existing work, fix relevant failures,
and continue through the remaining gates. Do not replace working modules with a new
framework or repeat completed phases without a concrete reason. Keep simulation-only
response and sandbox boundaries intact. Update the status file with verified results.
```

### Final review prompt

```text
Audit the actual RDRS repository against FR-1 through FR-13 and the build-pack acceptance
criteria. Verify the real monitoring path, severity boundaries, score decay, incident
deduplication, uncertainty of process attribution, safe evidence copying, report accuracy,
API validation, real dashboard data and Docker startup. Inspect tests for over-mocking,
unjustified skips and weakened coverage. Run applicable checks. Produce a concise
implemented/tested/unverified/missing matrix with evidence paths and commands. Do not
change code during this audit; list concrete fixes separately. Do not call it complete
while a required acceptance criterion is missing or unverified.
```

## 18. Technical references

The design was checked against these primary references on 20 October 2026. Dependency versions still need to be selected and tested in the actual build environment.

- Watchdog event API: https://python-watchdog.readthedocs.io/en/latest/api/events.html — event paths/types and move semantics; the portable event model does not supply a writer PID.
- psutil documentation: https://psutil.readthedocs.io/stable/ — process snapshots, CPU measurement behavior, PID identity, unavailable fields and access exceptions.
- Docker bind mounts: https://docs.docker.com/engine/storage/bind-mounts/ — explicit host-path mapping and read-only mount configuration.

Everything else in this pack is a source-derived requirement, a clearly stated proposed design decision, or an acceptance test to be implemented. No application build, test result, measured latency, coverage percentage or detection accuracy is claimed by this document.
