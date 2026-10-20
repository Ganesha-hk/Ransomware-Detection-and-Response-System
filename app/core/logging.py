from pathlib import Path
from loguru import logger


def configure(config):
    Path(config.directory).mkdir(parents=True, exist_ok=True)
    ids = []
    for kind in ("system", "events", "alerts", "errors", "audit"):
        ids.append(
            logger.add(
                str(Path(config.directory) / (kind + ".log")),
                rotation=config.rotation,
                retention=config.retention,
                filter=lambda record, k=kind: record["extra"].get("kind") == k,
            )
        )
    return ids


def log(kind, message):
    logger.bind(kind=kind).info(message)
