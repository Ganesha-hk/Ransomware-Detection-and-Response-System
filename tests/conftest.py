import time
import pytest
import yaml
from app.services.runtime import Runtime


@pytest.fixture
def config_path(tmp_path):
    path = tmp_path / "config.yaml"
    path.write_text(
        yaml.safe_dump(
            dict(
                detection=dict(window_seconds=2, tick_seconds=0.1, incident_cooldown_seconds=0.3),
                processes=dict(sample_interval_seconds=0.2),
            )
        )
    )
    return path


@pytest.fixture
def runtime(config_path):
    r = Runtime(config_path)
    r.start()
    yield r
    r.stop()


def wait_for(predicate, timeout=8):
    until = time.monotonic() + timeout
    while time.monotonic() < until:
        value = predicate()
        if value:
            return value
        time.sleep(0.03)
    raise AssertionError("Condition did not become true")
