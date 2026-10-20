# Implementation decisions

Reference: the user-designated `/home/ubunt/projects/RDRS/RDRS_Astra_Build_Pack.md`, read again after the update request on 20 October 2026. Its source FSD and Hands-On DOCX files were not available, so traceability follows the pack's FR summary and is not independent verification of those documents.

- Local Linux implementation; host Python 3.14 is available, container targets Python 3.12. No Windows/macOS claim.
- Source lives in this chat's outputs directory because the previously started external project directory was absent after interruption. The user-supplied pack is preserved.
- Modular services use SQLAlchemy Core transactions rather than a shared ORM session. Each table stores versioned JSON facts plus indexed identifiers/timestamps, actual foreign keys and a unique incident/event relation. No automatic migration or destructive database reset.
- SQLite is the authoritative last-good hot-settings store. Validated updates are persisted before becoming effective; YAML remains the startup baseline. Only hot keys override YAML after restart. No mutable paths or worker topology.
- Shared runtime lock serializes detection/settings state; independent evidence and process threads use their own DB connections. Observer callbacks do lexical checks and enqueue only; workers do resolved path checks and reads.
- File reads use Linux directory descriptors and O_NOFOLLOW to guard intermediate path substitution. This increases safety at the cost of Windows portability.
- An advisory lock on the database prevents a second local runtime from opening collectors. Use one server worker, without reload.
- CPU and unknown executable rules exist, but the portable collector never marks a process as a supported writer candidate. Thus snapshots alone cannot trigger process contributions.
- Process context is retained locally in reports; sanitized submission exports omit raw process listings.
- The build pack's many suggested small route/model files are consolidated where they would only forward calls. The component boundaries remain intact.
- JSON/CSV are required; PDF, restoration, isolation, real encryption and process termination remain outside scope.

- SQLite WAL uses synchronous=NORMAL to avoid per-event disk-sync stalls observed on the container filesystem. A machine power loss may lose recently committed transactions; this is an educational monitor, not a durable forensic recorder. Clean restarts are tested.
