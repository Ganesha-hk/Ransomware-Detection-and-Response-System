> Current submission review: the original FSD and Hands-On Build Guide were supplied and reviewed on 20 October 2026. See `../submission/PROJECT_REPORT.md` for the current assessment. Older notes below describe earlier verification stages. Reports now require explicit format selection; automatic closure exports have been removed.

# Local demonstration and submission index

Executed 20 October 2026 against the Docker service at http://127.0.0.1:8000. This is a local educational demonstration; no cloud dashboard or endpoint agent is needed. The supplied Build Pack is included. Original FSD/Hands-On Word documents were not available for independent comparison.

## Demonstration evidence

Screenshots and supporting observations are in [local-demonstration](../evidence/demo/local-demonstration/).

1. **Start:** `01-start.png` and `01-status.json` show the running monitor, simulation mode, six watched roots and score 0. Docker startup/health is in [the startup log](../evidence/test-results/local-demo-docker-startup.txt).
2. **Ordinary changes:** three newly created text files were edited. `02-normal-status.json` records Normal/0; `02-events.json` records actual events. `02-normal.png` shows the dashboard. A later ordinary-only follow-up after closure is pictured in `09-ordinary-events.png`.
3. **Safe simulator:** `scripts/simulate_activity.py --profile burst` created a new exclusive `locked-files-test-8ab16075f93144e3a081ec84402fd024` directory. Fifty synthetic files received random content and a `.locked` suffix. No encryption or existing user-file selection occurred.
4. **Detection:** `04-critical.png` and `04-critical-status.json` show 95/Critical: rapid high-entropy writes +40, mass rename +30, average entropy +25. Incident `1b1b6d96-2a87-4632-84d9-64e25067cc41` contains 156 observations and 53 distinct observed files. The three ordinary files are included because they were still in the same 60-second window; inclusion does not establish maliciousness. `05-incident.png` and `06-timeline-evidence.png` show details and expanded timeline.
5. **Evidence:** 53 copies succeeded with no copy failures. `quarantine-listing.txt` shows actual stored files; `quarantine-integrity.json` records matching hashes for every copy. `source-integrity.json` verifies all 53 sources against their post-simulator/edit hashes. The detector uses read-only source mounts. These checks establish that the response did not change the final sources; they do not claim the simulator itself left its newly created files unchanged.
6. **Reports:** generated JSON and CSV through the dashboard; `08-reports.png` shows exports. Final automatic reports were downloaded after closure, parsed and hash-verified (`report-downloads.json`). [JSON](../evidence/reports/local-demonstration.json) and [CSV](../evidence/reports/local-demonstration.csv) are explicitly marked sanitized derivatives, omitting process context; original download hashes are retained. Both were requested open in Codex file panels.
7. **Validation:** 56 host tests and 56 Docker tests passed, each about 96% coverage. See [host output](../evidence/test-results/submission-host.txt), [Docker output](../evidence/test-results/submission-docker.txt), [Ruff](../evidence/test-results/submission-ruff.txt), and [frontend checks](../evidence/test-results/submission-frontend.txt). One upstream deprecation warning remains. Docker is healthy, runs as non-root, and only exposes localhost.

## Deliverables

- Code repository: all application, test, configuration and script sources in this folder; distributed as `RDRS-project.zip`.
- [README/setup](../README.md), [architecture](architecture.md), [API](api.md), [repeatable demo instructions](demo_runbook.md).
- Current screenshots under `evidence/demo/local-demonstration/`; screenshots are supplied instead of a narrated recording.
- Sample JSON/CSV reports, runtime/startup logs, integrity checks, test and coverage output under `evidence/`.
- [One-page reflection](reflection.md): design, tests, the benign archive false-positive case and improvements.
- [Limitations](limitations.md) and [requirements mapping](requirements_matrix.md).

The live score decays to Normal after the window clears. The recorded incident and its peak remain available. Previous runs are retained and clearly timestamped; current evidence above identifies this run explicitly.
