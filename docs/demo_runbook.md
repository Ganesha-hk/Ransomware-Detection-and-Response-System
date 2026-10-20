# Demonstration and recording runbook

1. Start the app as described in README. Show the simulation badge, running health, zero dropped events, sandbox path in `/settings`, and Normal score. Explain that the score is a behavioral heuristic.
2. Run `python scripts/simulate_activity.py --profile benign`. Show actual create/modify events and no alert. Use isolated for one high-entropy file; it should still score 0.
3. Run archive independently after the previous window clears. Expected 65/Warning is a benign false positive, not a malware verdict. Explain the limitation honestly.
4. Wait for a clean live window, then run burst. Show the actual score, signals (40+30+25), and one incident. Do not hardcode scores or manufacture incidents through an API.
5. Open the incident. Inspect copy statuses and failures. Show original synthetic files still present. Compare every final file hash with the simulator's manifest; compare evidence hashes with the report manifest.
6. Enter the local token, generate JSON and CSV, and download them. Explain snapshot/final labels. Reports reflect stored observations and unknown writer attribution.
7. Wait 60 seconds for score decay and another 60 seconds for closure. Show automatic final reports, then restart and show persistent history and empty live windows.
8. Show test outputs and coverage, Docker health/non-root user/read-only sandbox, and limitations. Container and native modes must be labeled separately.

Actual screenshots are included under `evidence/demo/`. No narrated video recording is included; record this sequence if required by the evaluator. Do not imply that screenshots are a video or that institutional submission requirements were verified.

In the finished UI use Overview for monitoring scope, File activity for filtered observations, Incidents for readable investigation, Reports for downloads, and Setup & test for authorized inventory/settings and the controlled test instructions. Run independent burst demonstrations only after the previous incident closes; otherwise related activity is deliberately grouped and shares its evidence quota.
