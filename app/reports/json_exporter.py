import json


def export(report):
    return json.dumps(report, indent=2, ensure_ascii=False).encode()
