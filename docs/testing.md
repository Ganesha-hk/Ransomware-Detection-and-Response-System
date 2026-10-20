# Executed validation — 20 October 2026

Host Linux/Python 3.14.4: **52 passed**, **95.91%** application line coverage. Python 3.12 non-root Docker container: **52 passed**, **95.72%** coverage. Ruff: all checks passed. No tests were skipped and the 90% threshold was not lowered.

Commands:

```bash
pytest --cov=app --cov-report=term-missing --cov-report=html --cov-fail-under=90 -q
ruff check .
docker compose build
docker compose up -d
docker compose exec -T rdrs pytest --cov=app --cov-fail-under=90 -q
```

Exact outputs: `evidence/test-results/host-tests.txt`, `docker-tests.txt`, `ruff.txt`. One upstream Starlette warning advises HTTPX2; the requested HTTPX compatibility path passed and the warning is retained.

Tests include entropy fixtures, score boundaries and all six rule scenarios; settings/path validation; repeated-file deduplication, aliases and expiry; real create/modify/move/delete observation; multi-root separation; SQLite restart and lock timeout; process priming, denied metadata and disappearance; unknown attribution; evidence hashes, quotas and failures; API status/errors/authentication; scans excluded from live counters; version conflicts; actual JSON/CSV exports and formula escaping; incident cooldown/restart; queue degradation; and simulator sentinel protection.

The first container attempt failed because coverage could not write to the root-owned work directory; the Dockerfile now owns that directory as the non-root application user. The next run exposed per-transaction disk-sync stalls exceeding the deliberately short test window. WAL NORMAL synchronization fixed that bottleneck, and the unchanged 52-test suite then passed. No failed test was skipped or relaxed.

Real demo results: `evidence/demo/final-results.json`. Host first observed score 95 after final operation: 0.1405 seconds; container: 0.2064 seconds. These are single-run observations, not an SLA. Each final run copied 50 files without failures. Post-simulation source hashes were unchanged. Both original report downloads matched their stored hashes. Host and container evidence bytes were independently hashed, with results in the hash-verification text files. Container incident IDs survived restart.

Earlier combined profiles scored benign 0, isolated 0, archive 65, burst 95. The combined run reached the 100-copy quota and recorded five explicit failures. It drained more slowly; the earlier measurements are retained in host-results.json and pre-tuning-results.json rather than hidden. Final measurements were taken after the performance fix.

Browser verification observed Normal → actual Critical, contributions 40/30/25, one incident, unknown attribution, evidence statuses, and successful JSON and CSV generation. Screenshots: initial.png, critical.png, reports-ui.png, final-dashboard.png. The browser view uses real API data. No video or other-OS demonstration is included.

Remaining test gaps: adversarial multi-process path swapping, forced power loss, severe disk exhaustion, and long-duration/high-volume retention are not verified. Uncovered branches remain visible in coverage output. This is not a production endpoint-security certification.


## Completed workspace revision

The revised application passed **55 host tests (95.66% coverage)** and **55 Python 3.12 container tests (95.67%)**, with the same 90% gate. Results are `evidence/test-results/completion-host.txt` and `completion-docker.txt`. Additional tests cover per-incident pending evidence, logical file grouping across renames, monitoring scope, inventory progress and history.

Frontend logic is tested with Node 22 and jsdom 26.1.0: navigation, retained peaks, incident tables, untrusted filename rendering, actual event rendering, authenticated scan requests, token clearing and stale-data errors. The syntax check caught a settings-form syntax error during development; it was fixed before the final build. The passing output is `evidence/test-results/frontend.txt`.

To rerun frontend checks with Node installed:

```bash
cd tests/frontend
npm ci
node check.cjs
```

These are DOM logic checks, not a visual browser test. A subsequent live browser demonstration verified the redesigned interface; current screenshots are in `evidence/demo/local-demonstration/`. Earlier screenshots show the previous UI and remain historical evidence.

The final real container workflow is recorded in `evidence/demo/completed-workflow.json`: inventory without raising the live score, actual synthetic filesystem changes, 95/Critical, 50 distinct logical files, 50 successful evidence copies, unchanged sources and matching JSON/CSV download hashes.

A real rename-before-sample run exposed three duplicate logical-file entries in report presentation. Reports now resolve a missing identity through an unambiguous observed source/destination identity; ambiguous reused paths remain separate. The regression test includes missing identity before the rename. Repeated bursts inside the cooldown intentionally merge; the final independent demo waits for prior incident closure.

Final independent workflow: inventory completed for 150 existing files with live score remaining 0; fresh 50-file burst reached 95 in 0.321 seconds, with 50 distinct logical files, 50 successful copies, unchanged source hashes and zero dropped events. JSON/CSV download hashes and all stored evidence copy hashes verified. See completed-workflow.json and completion-hashes.txt under evidence/demo.


## Final local submission demonstration — 20 October 2026

56 host tests passed (947/990 covered statements, 95.66%); 56 Docker Python 3.12 tests passed (953/994, 95.88%). Ruff and frontend workflow checks passed. Logs use the `submission-` prefix under `evidence/test-results/`. The Docker startup log records a healthy service. See `SUBMISSION_INDEX.md` for the fresh browser demonstration, final reports, 53 verified evidence copies and unchanged source hashes.
