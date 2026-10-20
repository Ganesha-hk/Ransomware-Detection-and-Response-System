> Current submission review: the original FSD and Hands-On Build Guide were supplied and reviewed on 20 October 2026. See `../submission/PROJECT_REPORT.md` for the current assessment. Older notes below describe earlier verification stages. Reports now require explicit format selection; automatic closure exports have been removed.

# Build status — 20 October 2026

The educational application is implemented and exercised on Linux locally and in Docker. Institutional submission readiness is not asserted: original Word documents, PED/portal requirements and a narrated video remain unavailable/unverified.

| Phase | Delivered and observed |
|---|---|
| 0 Preparation | Pack reread after user update request; environment inspected; AGENTS, architecture, decisions and requirements matrix present. Original DOCX sources absent. |
| 1 Foundation | Strict configuration, path guards, bounded entropy sampling and error semantics; foundation tests pass. |
| 2 Observation | Real watchdog callbacks, bounded queue, exclusions, duplicate coalescing and rename aliases; live four-event test passes. |
| 3 Persistence/processes | SQLAlchemy/SQLite WAL, schema version, indexed records, foreign keys, lock timeout, process metadata and availability; restart/denied-process tests pass. |
| 4 Detection | Distinct-file windows, explainable weighted signals, boundaries and timer decay; six scenarios pass. |
| 5 Incidents/evidence | Severity alerts, root-scoped incidents/cooldown, persistent interruption markers, bounded copy worker; final 50-copy manifests verified in both modes. |
| 6 API | Documented endpoints, token-protected mutations, scans, versioned hot settings and downloads; API suite passes. |
| 7 Dashboard | Local dark UI with real telemetry, contributions, alerts, events, charts, incident evidence and report controls; browser observed actual Critical and report generation. |
| 8 Reports | JSON and documented formula-safe CSV; original downloads match stored hashes; sanitized real derivatives included. |
| 9 Verification | Host 52 tests pass at 95.91%; Docker 52 pass at 95.72%; Ruff passes. Benign and false-positive profiles measured. |
| 10 Packaging | Pinned dependencies, non-root Python 3.12 image, loopback-only Compose, read-only sandbox, persistent volume, health check, restart proof, documentation and source archive. Video not recorded. |

Commands and original outputs are in `docs/testing.md` and `evidence/test-results/`. All application, test, configuration, script, documentation and dashboard files were added during this build. Generated runtime directories are ignored and excluded from the archive.

Final burst: host 0.1405 seconds and container 0.2064 seconds to first observed 95 after final operation; 50 copies each, zero failures, unchanged final source hashes. Both JSON/CSV download hashes checked, and Docker restart preserved incident identity. These single-run measurements are not a performance guarantee.

Build corrections were driven by actual failures: non-root coverage output permission, then container disk-sync latency; neither coverage gates nor failing tests were weakened. Earlier slower measurements and combined-workload quota failures remain documented.

Consolidations from the proposed file tree and storage/durability decisions are recorded in `decisions.md`. Known limitations include no exact writer attribution, no prevention/recovery, no durable queue, manual archival and Linux-only verification. Remaining action outside this implementation: compare against the original FSD/guide and any portal requirements, and record the narrated demo if required.

## Fresh user-requested run
Previous active demo history and sandbox were archived on 20 October 2026. Active app at port 8000 was restarted with empty history. A new exclusive locked-files-test folder was observed by the real watcher: 50 files, score 95, one incident, 50 successful evidence copies and unchanged final source hashes. Details: evidence/demo/fresh-test.json. Dashboard wording distinguishes live monitoring from simulated response. Browser screenshot verification for this latest run was unavailable because local browser use is disabled in Work settings. API results were verified.


## Completed workspace revision

Replaced the single-page technical demonstration with a responsive five-page workspace: overview, incident investigation, filtered/paginated activity, report library, and setup/test controls. Historical peaks remain prominent after live score decay. Incident detail uses readable logical-file and evidence tables instead of raw JSON. Admin tokens stay only in page memory. Added inventory history/progress, threshold editing, safe test instructions and an executable Docker launcher with private first-run token creation.

Fixed incident evidence status to account for queued and in-progress copies for that incident, rather than global queue length. Added logical file grouping to reports and exposed configured monitoring scope/window in status. Tests: 55 host pass / 95.66%; 55 Docker pass / 95.67%; frontend syntax and DOM workflow checks pass; Ruff passes. Final executed workflow is in `evidence/demo/completed-workflow.json`.

The redesigned UI was subsequently verified in the browser on 20 October 2026; current screenshots are in `evidence/demo/local-demonstration/`. Earlier screenshots remain historical evidence. All required application capabilities are implemented; known educational/platform limitations and unavailable external submission criteria remain documented.

Final independent workflow: inventory completed for 150 existing files with live score remaining 0; fresh 50-file burst reached 95 in 0.321 seconds, with 50 distinct logical files, 50 successful copies, unchanged source hashes and zero dropped events. JSON/CSV download hashes and all stored evidence copy hashes verified. See completed-workflow.json and completion-hashes.txt under evidence/demo.


## Multiple sensitive folders

Six independent roots are enabled: general sandbox plus Finance, HR, Customer Data, Legal and Backups. The five department directories live under `data/sensitive-lab/` on the host and `/sensitive-lab/` in Docker. They contain synthetic demonstration files only; no real business data or external folders are connected. The parent is not itself watched, avoiding overlapping roots and duplicate counting. Docker mounts both lab areas read-only.

Overview shows each root’s score, severity and file counts. File activity can filter by root; Setup & test can inventory any configured root. Incidents are grouped independently by root.

Run a controlled test in one department:

```bash
python scripts/simulate_activity.py --profile benign --department hr
python scripts/simulate_activity.py --profile burst --department finance
```

Allowed departments: finance, hr, customer-data, legal, backups. The simulator still creates an exclusive new run folder and never modifies existing files. The normal default remains the general sandbox.

Verified: real benign writes in all five departments followed by a Finance-only burst produced Finance 95 and all other roots 0, with zero dropped events. Results: `evidence/demo/multiple-folders.json`. To connect real business folders, specify their exact approved paths and add explicit read-only mounts/configured roots; do not mount or monitor the whole VM by default.

Folder selector correction: Inventory and File activity now reconcile configured roots on every refresh, preserving valid selections and removing stale roots. Regression tests passed for growth from one to six roots, selection preservation, and removal fallback. Setup text lists all department mappings. Deployed service verified with six configured roots.


## Final local submission demonstration — 20 October 2026

56 host tests passed (947/990 covered statements, 95.66%); 56 Docker Python 3.12 tests passed (953/994, 95.88%). Ruff and frontend workflow checks passed. Logs use the `submission-` prefix under `evidence/test-results/`. The Docker startup log records a healthy service. See `SUBMISSION_INDEX.md` for the fresh browser demonstration, final reports, 53 verified evidence copies and unchanged source hashes.
