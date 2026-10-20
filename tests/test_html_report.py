import json
from pathlib import Path
from app.reports.html_exporter import export


def test_assessment_is_self_contained_and_escapes_untrusted_paths():
    report = json.loads(Path('evidence/reports/local-demonstration.json').read_text())
    report['logical_files'][0]['path'] = '<script>alert("file")</script>'
    html = export(report).decode()
    assert '<script>' not in html
    assert '&lt;script&gt;' in html
    for section in ['Executive summary', 'Findings', 'Event timeline', 'Evidence preservation', 'Recommended actions', 'Methodology']:
        assert section in html
    assert 'FINAL INCIDENT REPORT' in html
    assert '95.0/100' in html
    assert '@media print' in html
    assert 'src=' not in html


def test_selected_period_filters_events_and_only_requested_format(config_path, monkeypatch):
    from fastapi.testclient import TestClient
    from app.api.main import create_app
    monkeypatch.setenv('RDRS_ADMIN_TOKEN', 'test-token')
    with TestClient(create_app(config_path)) as client:
        r = client.app.state.runtime
        sample = json.loads(Path('evidence/reports/local-demonstration.json').read_text())
        incident = r.store.save('incidents', sample['incident'])
        for event in sample['event_timeline']:
            r.store.save('events', event)
            r.store.save('incident_events', {'incident_id': incident['id'], 'event_id': event['id']})
        body = {'formats': ['json'], 'start': '2026-10-20T16:41:46+00:00', 'end': '2026-10-20T16:41:48+00:00'}
        assert client.post('/reports/selection', json=body).status_code == 401
        auth = {'Authorization': 'Bearer test-token'}
        response = client.post('/reports/selection', json=body, headers=auth)
        assert response.status_code == 200
        rows = response.json()['reports']
        assert len(rows) == 1 and rows[0]['format'] == 'json'
        data = client.get('/reports/' + rows[0]['id'] + '/download').json()
        assert len(data['event_timeline']) == 6
        assert len(data['logical_files']) == 3
        assert len(r.store.rows('reports')) == 1
        body['end'] = body['start']
        assert client.post('/reports/selection', json=body, headers=auth).status_code == 422
