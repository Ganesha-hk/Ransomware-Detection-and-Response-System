> Current submission review: the original FSD and Hands-On Build Guide were supplied and reviewed on 20 October 2026. See `../submission/PROJECT_REPORT.md` for the current assessment. Older notes below describe earlier verification stages. Reports now require explicit format selection; automatic closure exports have been removed.

# Requirements matrix

Traceability follows the supplied build pack; original Word documents were unavailable. All FRs have an implementation and exercised acceptance path. This does not claim every failure branch or external submission criterion is verified.

| Requirement | Module | Validation | Evidence/result | Status |
|---|---|---|---|---|
| FR-1 Configuration | core/config.py; settings_service.py | test_core.py; test_services.py | Validated settings, hot versions and conflicts | Implemented and tested |
| FR-2 Four event kinds | file_monitor.py; event_pipeline.py | test_pipeline.py | Real native observer and mounted polling demo | Implemented and tested |
| FR-3 Shannon entropy | core/entropy.py | test_core.py; test_failures.py | Empty/repeated/uniform and failure semantics | Implemented and tested |
| FR-4 Process metadata | process_monitor.py | test_failures.py; test_pipeline.py | Priming, denied/disappearing processes, unknown attribution | Implemented and tested |
| FR-5 Persistence | database/session.py | test_services.py; test_failures.py | WAL, foreign keys, lock bounds, restart | Implemented and tested |
| FR-6 Window | sliding_window.py; runtime.py | test_core.py; test_pipeline.py | Distinct identity, monotonic expiry, multiple roots | Implemented and tested |
| FR-7 Scores | rules.py; scoring.py | test_core.py | 0/39/40/69/70/100 and specified scenarios | Implemented and tested |
| FR-8 Incidents | incident_service.py | test_failures.py; test_pipeline.py | Deduplication, cooldown, closure, restart | Implemented and tested |
| FR-9 Copy-only evidence | evidence_service.py | test_services.py; test_pipeline.py | 50 verified final copies per mode; source hashes unchanged | Implemented and tested |
| FR-10 REST API | api/main.py; schemas.py | test_api.py | Routes, auth, filters, errors, downloads | Implemented and tested |
| FR-11 Live dashboard | dashboard/ | Browser demonstration | Actual activity and screenshot artifacts | Implemented and tested |
| FR-12 JSON/CSV | report_service.py; reports/ | test_services.py; demo runs | Downloaded bytes verified; sanitized derivatives provided | Implemented and tested |
| FR-13 Tests and Docker | tests/; Dockerfile; Compose | Host and Docker outputs | 52 pass in each environment; coverage >90%; restart verified | Implemented and tested |

Evidence: `evidence/test-results/` and `evidence/demo/`; exact limitations are in `limitations.md` and `testing.md`. Narrated video, other operating systems and unavailable institutional documents remain unverified.
