"""Generate labeled synthetic samples and real moves in a new sandbox folder."""
import hashlib
import json
import math
import os
from collections import Counter
from pathlib import Path
import time
from uuid import uuid4


def run_demo():
    base = Path(__file__).resolve().parents[1] / 'data' / 'sandbox'
    if any(p.is_symlink() for p in (base, *base.parents)):
        raise ValueError('Sandbox must not use symlinks')
    base.mkdir(parents=True, exist_ok=True)
    run = base / ('synthetic-varied-' + uuid4().hex)
    run.mkdir(exist_ok=False)
    incoming, destination = run / 'incoming', run / 'processed'
    incoming.mkdir()
    destination.mkdir()
    records = []
    # Each alphabet yields a different measured entropy, approximately 0–8 bits/byte.
    for stage, symbols in enumerate((1, 2, 4, 16, 64, 256)):
        for index in range(4):
            content = bytes(value % symbols for value in os.urandom(24000 + index * 4000))
            source = incoming / f'synthetic-level-{stage}-{index}.bin'
            target = destination / f'synthetic-level-{stage}-{index}.sample'
            with source.open('xb') as stream:
                stream.write(content)
            counts = Counter(content)
            entropy = -sum((n / len(content)) * math.log2(n / len(content)) for n in counts.values())
            records.append(dict(synthetic=True, source=str(source), destination=str(target),
                                bytes=len(content), entropy_bits_per_byte=round(entropy, 4),
                                sha256=hashlib.sha256(content).hexdigest()))
        # Let the polling monitor observe creation before moving these files.
        time.sleep(2)
        for record in records[-4:]:
            source, target = Path(record['source']), Path(record['destination'])
            if source.is_symlink() or target.exists() or incoming.is_symlink() or destination.is_symlink():
                raise ValueError('Demo boundary changed')
            source.rename(target)
        time.sleep(2)
    output = base.parent / 'demo-manifests'
    output.mkdir(exist_ok=True)
    manifest = output / (run.name + '.json')
    manifest.write_text(json.dumps(dict(synthetic=True, description='Demo data, not a real attack', files=records), indent=2))
    print(manifest)


if __name__ == '__main__':
    run_demo()
