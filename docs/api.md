# API

Open `/docs` for the generated request schemas. Read routes are local and unauthenticated. Mutations require `Authorization: Bearer <RDRS_ADMIN_TOKEN>`. No cross-origin permissions are granted; allowed hosts are localhost/127.0.0.1. An unset token disables mutation access, not observation.

| Route | Purpose |
|---|---|
| GET /health | Ready status; 503 on worker failure or data loss |
| GET /status | Scores per root, worker health, queues, dropped events, database size |
| GET /events | limit 1–200, offset, root, since/until ISO timestamp, type, incident filters |
| GET /alerts | limit/offset, severity, since/until filters |
| GET /incidents | Paginated persistent history |
| GET /incidents/{id} | Timeline, contributions, evidence and unknown attribution |
| GET /metrics | Bounded actual score and process samples |
| GET /reports | Artifact metadata |
| POST /reports | `{ "incident_id": "...", "format": "json" }` (or csv) |
| GET /reports/{id}/download | Stored artifact download |
| POST /scan | `{ "root": "configured absolute root" }`; 202 job |
| GET /scans | Paginated inventory job history |
| GET /scans/{id} | Inventory result; scan rows do not affect live signals |
| GET /settings | Effective settings and version |
| POST /settings | `{ "expected_version": 1, "patch": { "detection": { "entropy_threshold": 7.6 } } }` |

404 means missing record, 422 invalid input, 401 missing/wrong token, 409 concurrent scan or stale settings version. Only detection thresholds/weights and dashboard polling may change without restart.

CSV schema is `record_type,incident_id,record_id,field,value`. Each record's fields occupy separate rows. Types: summary, event, evidence, process_context, recommendation. Nested structures use JSON values. Strings whose first non-space character starts a spreadsheet formula are prefixed with an apostrophe. JSON preserves source strings.
