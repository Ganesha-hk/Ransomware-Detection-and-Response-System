"""Self-contained, escaped, print-ready assessment reports from recorded facts."""
from html import escape


def export(report):
    def text(value):
        return escape(str(value if value is not None else 'Unavailable'), quote=True)

    def table(headers, rows):
        return '<table><thead><tr>' + ''.join(f'<th>{text(h)}</th>' for h in headers) + '</tr></thead><tbody>' + ''.join('<tr>' + ''.join(f'<td>{text(v)}</td>' for v in row) + '</tr>' for row in rows) + '</tbody></table>'

    incident = report['incident']
    peak = incident.get('peak_score', 0)
    settings = incident.get('settings_snapshot', {}).get('detection', {})
    level = 'Critical' if peak >= settings.get('critical_min', 70) else 'Warning' if peak >= settings.get('warning_min', 40) else 'Normal'
    signals = incident.get('peak_signals', {})
    copied = sum(e['status'] == 'copied' for e in report['evidence_manifest'])
    files = report.get('logical_files', [])
    findings = ''
    names = {'rapid_high_entropy_writes': 'Rapid high-entropy writes', 'mass_rename': 'Mass file renaming', 'high_entropy': 'High average entropy', 'cpu_spike': 'Elevated CPU activity', 'unknown_program': 'Unknown program signal'}
    for index, (key, weight) in enumerate(signals.get('contributions', {}).items(), 1):
        findings += f'<article><span class="tag">Behavioral signal · +{text(weight)} points</span><h3>RDRS-{index:03} · {text(names.get(key, key))}</h3><p>This rule contributed to the recorded incident peak. It is a behavioral observation, not proof of ransomware or a software vulnerability.</p></article>'
    facts = table(['Observed metric', 'Value'], signals.get('facts', {}).items())
    affected = table(['Last observed file', 'Previous paths', 'Entropy (bits/byte)', 'Observations'], ((f['path'], '; '.join(f.get('previous_paths', [])), f.get('entropy'), f.get('event_count')) for f in files))
    timeline = table(['Time (UTC)', 'Event', 'Source', 'Destination', 'Sampling'], ((e['timestamp'], e['event_type'], e['source_path'], e.get('destination_path', ''), e.get('sampling_status', '')) for e in sorted(report['event_timeline'], key=lambda e: e['timestamp'])))
    evidence = table(['Source', 'Copy status', 'Stored evidence', 'SHA-256'], ((e.get('source_path', e.get('original_path', '')), e['status'], e.get('stored_path', ''), e.get('sha256', '')) for e in report['evidence_manifest']))
    recommendations = ''.join('<li>' + text(r) + '</li>' for r in report['recommendations'])
    period = report.get('requested_period')
    scope = (f"Selected activity: {text(period['start'])} to {text(period['end_exclusive'])} (end excluded). File, timeline and evidence tables are limited to this period. Severity and rule findings describe the full incident's historical peak." if period else "Scope: complete recorded incident.")
    kind = 'INTERIM SNAPSHOT' if report['snapshot'] else 'FINAL INCIDENT REPORT'
    html = f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>RDRS Assessment · {text(incident['id'])}</title><style>
    *{{box-sizing:border-box}}body{{margin:0;background:#eef2f6;color:#18283a;font:15px/1.6 Arial,sans-serif}}main{{max-width:1120px;margin:32px auto;background:white;padding:54px;box-shadow:0 8px 35px #20304015}}header{{border-top:7px solid #126c80;padding-top:28px}}.brand{{letter-spacing:3px;color:#126c80;font-weight:bold}}h1{{font-size:38px;line-height:1.15;margin:16px 0}}h2{{font-size:23px;border-bottom:2px solid #e4eaf0;padding-bottom:12px;margin-top:42px}}h3{{margin:8px 0}}.muted{{color:#526579}}.tag{{display:inline-block;padding:4px 10px;background:#e8eff5;border-radius:4px;font-size:12px;font-weight:bold}}.critical{{color:#9a2332;background:#fde9ec}}.stats{{display:flex;gap:16px;margin:28px 0}}.stat{{flex:1;border:1px solid #dce4eb;padding:20px}}.stat strong{{display:block;font-size:30px}}nav{{padding:18px;background:#f4f7fa}}a{{color:#126c80;margin-right:16px}}article{{border-left:4px solid #126c80;background:#f6f9fb;padding:20px;margin:15px 0}}table{{border-collapse:collapse;width:100%;font-size:12px;table-layout:fixed}}th,td{{text-align:left;vertical-align:top;padding:10px;border-bottom:1px solid #dce4eb;overflow-wrap:anywhere}}th{{background:#eaf0f5}}tr:nth-child(even){{background:#f8fafc}}footer{{margin-top:40px;border-top:1px solid #ccd5df;padding-top:20px;font-size:12px}}@media(max-width:700px){{main{{padding:20px;margin:0}}.stats{{flex-wrap:wrap}}.stat{{min-width:40%}}}}@media print{{body{{background:white}}main{{margin:0;padding:0;box-shadow:none;max-width:none}}nav{{display:none}}h2,h3{{break-after:avoid}}tr,article,.stat{{break-inside:avoid}}thead{{display:table-header-group}}@page{{size:A4;margin:16mm}}}}
    </style></head><body><main><header><div class="brand">RDRS / SECURITY ASSESSMENT</div><p class="muted">{kind} · LOCAL EDUCATIONAL MONITOR</p><h1>File activity &amp; incident assessment</h1><p>Incident {text(incident['id'])}<br>Generated {text(report['generated_at'])}</p><span class="tag critical">{level} · historical peak {text(peak)}/100</span></header>
    <div class="stats"><div class="stat"><strong>{len(files)}</strong>Observed files</div><div class="stat"><strong>{len(report['event_timeline'])}</strong>Events</div><div class="stat"><strong>{copied}</strong>Evidence copies</div><div class="stat"><strong>{len(report['copy_failures'])}</strong>Copy failures</div></div>
    <nav><a href="#summary">Summary</a><a href="#findings">Findings</a><a href="#files">Files</a><a href="#timeline">Timeline</a><a href="#evidence">Evidence</a><a href="#actions">Actions</a></nav>
    <p class="muted">{scope}</p><h2 id="summary">01 / Executive summary</h2><p>RDRS recorded a <strong>{level.lower()}</strong> behavioral incident in <strong>{text(incident.get('root'))}</strong>. The historical peak was {text(peak)}/100. Review whether these changes were expected before deciding on further action.</p><p>Opened: {text(incident.get('opened_at'))}<br>Closed: {text(incident.get('closed_at'))}<br>Status: {text(incident.get('status'))} · Configuration version: {text(incident.get('settings_version'))}</p><p>Response mode: <strong>simulation / evidence copies only</strong>. No process termination, isolation or recovery is performed. Observed files include ordinary activity in the same detection window; they are not all confirmed malicious.</p>
    <h2 id="findings">02 / Findings &amp; supporting measurements</h2>{findings or '<p>No contributing rules recorded.</p>'}{facts}
    <h2 id="files">03 / Affected-file inventory</h2>{affected}
    <h2 id="timeline">04 / Event timeline</h2>{timeline}
    <h2 id="evidence">05 / Evidence preservation</h2><p>These are copy records and recorded SHA-256 values. This report does not independently re-hash current sources or copies. Copying preserves observed content; it does not undo the original changes.</p>{evidence}
    <h2 id="actions">06 / Recommended actions</h2><ol>{recommendations}</ol>
    <h2>07 / Methodology &amp; limitations</h2><p>Severity uses RDRS rule weights and the incident's saved thresholds. This is not a CVSS score or a vulnerability scan. Random and compressed content can trigger entropy rules. {text(report['attribution'])} A historical score does not describe the current live window. Evidence may capture an intermediate version while files are changing.</p><footer>RDRS · Standalone assessment report · Use your browser's Print / Save as PDF for a paginated copy. All paths and findings are escaped text; this report loads no external assets.</footer></main></body></html>'''
    return html.encode('utf-8')
