"""Readable fictional business activity followed by an isolated safe burst."""
import hashlib
import json
import os
from pathlib import Path
import sys
import time
from uuid import uuid4
import zipfile

from simulate_activity import BASE, simulate


def run_demo():
    if any(path.is_symlink() for path in (BASE, *BASE.parents)):
        raise ValueError('Sandbox must not use symlinks')
    BASE.mkdir(parents=True, exist_ok=True)
    run = BASE / ('fictional-business-' + uuid4().hex)
    run.mkdir(exist_ok=False)
    documents = {
        'finance/invoice-1001.csv': 'demo_notice,FICTIONAL DEMO DATA\ninvoice,customer,item,amount,currency\n1001,Example Customer,Training service,1250,INR\n',
        'hr/employee-directory.csv': 'demo_notice,FICTIONAL DEMO DATA\nemployee_id,name,department,email\nDEMO001,Sample Employee,Operations,employee@example.invalid\n',
        'customers/customers.csv': 'demo_notice,FICTIONAL DEMO DATA\ncustomer_id,company,email\nC001,Fictional Retail,customer@example.invalid\n',
        'legal/service-agreement.txt': 'FICTIONAL DEMO DATA — NOT A REAL CONTRACT\nExample supplier provides a training demonstration to Example Customer.\nNo personal information or binding terms.\n',
        'operations/application.log': 'FICTIONAL DEMO DATA\nINFO Demo application started\nINFO Sample invoice loaded\n',
        'README.txt': 'FICTIONAL BUSINESS DEMONSTRATION\nThese readable files stay intact. The suspicious burst uses a separate fresh sandbox directory.\n',
    }
    records = []
    for relative, content in documents.items():
        path = run / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open('x') as stream:
            stream.write(content)
        records.append({'source': str(path), 'destination': None, 'kind': 'fictional_business_document'})
    time.sleep(2)
    log = run / 'operations/application.log'
    with log.open('a') as stream:
        stream.write('INFO Ordinary edit: sample invoice approved for demo\n')
    processed = run / 'finance/processed'
    processed.mkdir()
    invoice = run / 'finance/invoice-1001.csv'
    target = processed / invoice.name
    invoice.rename(target)
    records[0]['destination'] = str(target)
    backup = run / 'backups/fictional-documents.zip'
    backup.parent.mkdir()
    with zipfile.ZipFile(backup, 'x', compression=zipfile.ZIP_DEFLATED) as archive:
        for record in records:
            path = Path(record['destination'] or record['source'])
            archive.write(path, path.relative_to(run))
    records.append({'source': str(backup), 'destination': None, 'kind': 'legitimate_demo_archive'})
    for record in records:
        path = Path(record['destination'] or record['source'])
        record['sha256'] = hashlib.sha256(path.read_bytes()).hexdigest()
    # Attribution is supplied by the simulator itself, never inferred from psutil.
    manifest = {
        'synthetic': True,
        'run': str(run),
        'known_simulator_process': {
            'pid': os.getpid(), 'parent_pid': os.getppid(),
            'name': Path(sys.executable).name, 'executable': sys.executable,
            'script': Path(__file__).name,
            'attribution_method': 'simulator_self_reported',
            'label': 'Known simulator process — not detector-attributed file writer',
            'scope': 'Host process; PID may not be visible inside the Docker container',
        },
        'files': records,
    }
    output = BASE.parent / 'demo-manifests'
    output.mkdir(exist_ok=True)
    manifest_path = output / (run.name + '.json')
    manifest_path.write_text(json.dumps(manifest, indent=2))
    print('Readable fictional files:', run, flush=True)
    print('Known simulator PID:', os.getpid(), '(self-reported demo context)', flush=True)
    time.sleep(3)
    manifest['burst_manifest'] = str(simulate('burst'))
    manifest['business_files_unchanged_by_burst'] = all(
        hashlib.sha256(Path(r['destination'] or r['source']).read_bytes()).hexdigest() == r['sha256']
        for r in records
    )
    manifest_path.write_text(json.dumps(manifest, indent=2))
    print('Demo manifest:', manifest_path, flush=True)
    return manifest_path


if __name__ == '__main__':
    run_demo()
