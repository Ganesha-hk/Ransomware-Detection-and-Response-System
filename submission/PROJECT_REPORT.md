# RDRS internship project report

## Purpose and outcome

RDRS is a local educational system that detects ransomware-like file activity using transparent rules. It observes configured folders, records file and process information, calculates a threat score and preserves evidence copies. A safe demonstration reached 95 out of 100 and produced a Critical incident. The implementation includes a browser dashboard, SQLite persistence, reports, automated tests and Docker deployment. It requires no cloud service or trained model.

This submission is intended for the internship evaluator. The supplied Functional Specification Document version 1.0 and Hands-On Build Guide define the scope. The work was developed with OpenAI Codex assistance; the student should be prepared to explain and demonstrate the implementation and disclose assistance according to the provider's rules.

## Architecture and design

The watchdog observer collects create, modify, rename and delete events into a bounded queue. A processor samples up to 64 KB of file content, calculates Shannon entropy and maintains a sliding window for each monitored root. Weighted rules produce scores capped at 100. SQLite stores observations, scores, alerts, incidents and evidence manifests. A separate response worker copies evidence without changing source files. FastAPI provides the dashboard and report APIs; psutil provides contextual process snapshots.

The default window is 60 seconds. Rapid high-entropy writes contribute 40 points, mass renaming 30 and high average entropy 25. Scores below 40 are Normal, 40 to below 70 are Warning, and 70 or more are Critical. Independent roots cover a general sandbox and five synthetic department folders. These folders do not represent connected business systems.

Process snapshots cannot reliably identify the writer of a changed file. The application reports attribution as unknown and disables unsupported process-based scoring instead of selecting a likely process. This is a limitation relative to the guide's aspiration to identify a suspect process. Responses remain copy-only; there is no process termination, host isolation or restoration.

## Requirements coverage

FR-1 through FR-6 are addressed by YAML configuration, filesystem observation, Shannon entropy, psutil snapshots, SQLite storage and sliding-window analysis. FR-7 through FR-9 are addressed by weighted scoring, persistent alerts and incidents, and copy-only quarantine. FR-10 through FR-13 are addressed by FastAPI endpoints, the live dashboard, JSON and CSV exports, automated tests and Docker deployment.

The dashboard provides Overview, Incidents, File activity, Reports, and Setup and test pages. Reports support an explicit local date/time range and HTML, JSON and CSV selection. Only requested formats are generated. Period reports filter observations and related evidence while retaining clearly labeled historical incident severity. HTML provides a readable assessment and supports browser printing. A dedicated PDF exporter is not implemented; PDF is optional in the guide.

## Executed demonstration

On 20 October 2026, ordinary edits to three new text files produced Normal status and score 0. A separate safe simulator then created 50 new throwaway files, wrote random bytes into those files and renamed them with a .locked suffix. The detector produced a Critical score of 95 with no dropped events. Random-content generation is not encryption and a suffix alone does not prove ransomware.

Incident 1b1b6d96-2a87-4632-84d9-64e25067cc41 recorded 156 observations and 53 distinct files. The three ordinary files remained in the same detection window and therefore appear in the incident inventory; inclusion does not establish that every listed file is malicious. All 53 evidence copies succeeded. Every stored copy matched its recorded SHA-256 value, and all 53 final source hashes matched the simulator or ordinary-edit manifests. These checks show that the response did not alter the final sources; the simulator did intentionally change its own new files.

Current screenshots, source-integrity checks, quarantine-integrity checks and Docker logs are under evidence/demo/local-demonstration. The sample-reports folder contains HTML, JSON and CSV derived from the same final incident data. Process context is omitted from the shared samples and the JSON retains the original report hash and redaction notice. The readable report does not itself perform a new integrity check.

## Testing and deployment

The latest verification passed 58 tests with 1003 of 1054 application statements covered, or 95.16 percent. The suite exercises entropy, score boundaries, time-window expiry, real filesystem events, API authorization, report format and date filtering, evidence limits, path escapes and failure handling. Results are in evidence/test-results/submission-current.txt. Earlier Docker verification passed 56 tests; later report features were verified by the 58-test host run and the running Docker service. These results must not be conflated.

Docker runs as a non-root user, exposes localhost port 8000, mounts watched source folders read-only and preserves runtime data in a named volume. Start with scripts/start.sh after installing Docker Compose and Python 3. For native execution use Python 3.12 or newer and the pinned requirements. README.md contains the complete commands, token setup and demonstration steps. Linux is the verified platform.

## Reflection

The main design choice was to make each score explainable and preserve uncertainty. A modular pipeline separates observation, detection, storage and response, while the dashboard and reports use recorded facts. A bounded evidence worker keeps copying away from the event processor. Copy-only handling protects the source from changes by the detector, but it cannot prevent or reverse an attack.

Testing combined pure scoring tests with real file operations and source/evidence hash comparisons. A benign archive-like workload of many random files can reach Warning because compressed or random data has high entropy. This is a meaningful false-positive case: analysts must check whether backups, archiving or other bulk operations were expected before interpreting the alert as malicious activity.

Future improvements include durable queues, retention controls, more benign-workload evaluation, platform-specific writer attribution and broader operating-system testing. SQLite WAL with NORMAL synchronization improves throughput but may lose recent transactions on power loss. Coverage is evidence of exercised code, not a guarantee of security or detection accuracy.

## Submission contents and references

The repository includes source code, pinned dependencies, Docker configuration, README setup instructions, architecture documentation, tests, screenshots, sample reports, detection logs and a separate one-page reflection at docs/reflection.md. The Hands-On Build Guide section 16 requires these items and permits screenshots instead of a recording. Neither supplied document names a submission recipient, deadline or portal address.

References are the supplied RDRS Functional Specification Document version 1.0, the RDRS Hands-On Build Guide sections 5 through 18, and the supplied Astra Build Pack. Libraries include FastAPI, Starlette, Uvicorn, watchdog, psutil, SQLAlchemy, Pydantic, PyYAML, Loguru and Jinja2. Tests use pytest, coverage, HTTPX and Ruff. No ransomware or external malware dataset was used.
