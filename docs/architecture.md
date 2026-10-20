# Architecture

Watchdog → bounded event queue → sampling worker → SQLite + per-root monotonic window → scoring → alerts/incidents → bounded evidence/report queue.

FastAPI lifespan owns the observer, event worker, process sampler, expiry timer and response worker. Module imports create no background workers. Synchronous API handlers run in FastAPI's worker pool. Shutdown stops the observer, drains intake, then drains response work with deadlines; unfinished work is audited.

Distinct file identity prevents callback multiplicity from inflating file counts. Source/destination aliases join rename chains. Content samples use the latest valid observation in the window; deleted and unreadable files have null entropy. The timer expires quiet windows. Incident peaks remain historical. Severity transitions produce alerts; the active incident remains open through the cooldown.

SQLite WAL permits concurrent readers. Connections have a finite busy timeout. Foreign keys link evidence and incident events to their parents. Schema version 1 refuses unknown versions. Archival is manual; database size appears in status.

Evidence uses a separate thread, pinned source descriptors, bounded streaming, SHA-256, before/after metadata, generated destination names, and atomic finalization. Failed captures remain explicit records. Sources are read only.

The dashboard polls API results without overlapping refreshes and renders untrusted text through textContent. Local assets work offline. Report generation requires a bearer token; downloads resolve stored report IDs.
