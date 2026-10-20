from pathlib import Path
from app.core.models import uid, utc


def normalize(root, kind, source, destination, arrival, synthetic=False):
    return dict(
        id=uid(),
        timestamp=utc(),
        root=root,
        event_type=kind,
        source_path=source,
        destination_path=destination or None,
        old_suffix=Path(source).suffix,
        new_suffix=Path(destination or source).suffix,
        arrival=arrival,
        synthetic=synthetic,
        source_kind="live",
        attribution="unknown",
    )
