# Frontend logic checks

Requires Node 22 and npm. From this directory run:

```sh
npm ci
node check.cjs
```

The test uses jsdom with deterministic mocked API fixtures. These fixtures are test-only and are not imported by the application. It checks navigation, persistent historical peaks, monitoring scope, readable incident tables, filename injection escaping, activity rendering, authenticated scan requests, token clearing and stale-data feedback. Live backend demonstrations separately exercise the real filesystem and database. This is not visual browser verification.
