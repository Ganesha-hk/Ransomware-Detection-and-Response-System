# Limits and remaining verification

- Educational rules detect suspicious patterns, not ransomware identity. Compression, archives and legitimate encryption can trigger warnings. Small, slow or low-entropy attacks can be missed.
- Portable watchdog events cannot prove which process wrote a file. Process-based rules never trigger from unrelated host load; snapshots are context only. Exact attribution needs a separate platform collector.
- Only Linux is tested. File descriptor protections and process locking use Linux/POSIX features. Windows/macOS support is not claimed.
- Native and polling observation can miss activity when overloaded, between polls, or while stopped. Restart deliberately clears monotonic live windows and marks active incidents interrupted. Dropped queues degrade readiness. No durable event queue or replay exists.
- WAL synchronous=NORMAL avoids per-event sync stalls but a machine power loss can lose the most recent commits. Clean restart persistence is tested. There is no recovery promise after sudden power failure.
- Evidence copies are best-effort. Files can disappear or change before copying. Quotas deliberately skip excess captures with explicit failure records; copying never cleans or restores a source. Evidence/report stores are assumed locally trusted and writable only by their owner.
- Report materialization and startup reconciliation currently bound reads at 100,000 records per category. This is appropriate for the bounded classroom demo, not long-running enterprise retention. Archive manually before reaching that scale. Disk exhaustion is not prevented by log rotation.
- The local API has bearer protection for writes, local host checking, and no cross-origin grants. It is not designed for public networking, shared-host confidentiality, multiple tenants, or adversarial administrators.
- Initial heavy combined demonstration exceeded the proposed five-second target; final measured timings are recorded separately. No institutional real-time SLA is asserted.
- Original Word source documents, PED and portal instructions were unavailable. Narrated video and other OS demonstrations are not included. Screenshots, runbooks and real test/demo artifacts are provided.

- The redesigned five-page workspace has passing JavaScript/DOM tests, but fresh visual browser verification is unavailable because local browser access is disabled. Earlier screenshots depict the earlier interface.
