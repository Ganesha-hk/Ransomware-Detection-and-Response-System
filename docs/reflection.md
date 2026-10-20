# Reflection

The project turns a filesystem event stream into explanations a student can inspect. A modular monolith keeps the runtime understandable: collection, bounded sampling, sliding windows, transparent rules, persistence and copy-only evidence. The dashboard uses the same stored data as reports, so it cannot silently invent a successful demonstration.

The most important design choice is preserving uncertainty. Shannon entropy can reveal compressed or random content, but it cannot prove encryption. A process snapshot does not identify the writer. The UI and reports therefore retain unknown attribution instead of selecting the busiest process. The benign archive workload produced a Warning, demonstrating a real false-positive case rather than claiming perfect accuracy.

Tests cover pure rules and real operations: repeated-file callbacks, rename chains, boundary scores, window expiry, database locks, process disappearance, source-path escapes, evidence quotas, API authorization and settings conflicts. Real native and container demonstrations verify observed incidents, report downloads and final-source hashes. Coverage measures exercised lines, not security completeness.

Performance verification found that repeated incident lookups and disk synchronization on each small transaction delayed processing. Cached incident relationships and WAL NORMAL synchronization reduced that overhead, with the explicit tradeoff that a machine power loss can lose recent transactions. The original slower measurement remains documented; later results must not erase it.

Next work would add durable queues, batched transactional writes with explicit durability policy, bounded retention/archival tools, platform-specific writer attribution, a larger benign workload study, and portability tests. None of those future capabilities are claimed by this educational detector. Copying evidence remains fundamentally different from preventing an attack or restoring files.
