import copy
from app.core.config import Settings

ALLOWED = {
    "rapid_write_min_files",
    "mass_rename_min_files",
    "extension_change_min_files",
    "high_entropy_min_files",
    "entropy_threshold",
    "cpu_threshold_percent",
    "weights",
    "warning_min",
    "critical_min",
}


def update(runtime, expected_version, patch):
    with runtime.lock:
        if expected_version != runtime.version:
            raise FileExistsError("Settings version conflict")
        if set(patch) - {"detection", "dashboard"}:
            raise ValueError("Restart required for these settings")
        if set(patch.get("detection", {})) - ALLOWED or set(patch.get("dashboard", {})) - {
            "poll_interval_seconds"
        }:
            raise ValueError("Restart required or unknown setting")
        data = copy.deepcopy(runtime.config.model_dump())
        for section, values in patch.items():
            data[section].update(values)
        candidate = Settings.model_validate(data)
        version = runtime.version + 1
        runtime.store.save(
            "settings_versions",
            dict(
                id=str(version),
                version=version,
                settings=candidate.model_dump(),
                change_summary="Validated hot settings update",
            ),
        )
        runtime.config = candidate
        runtime.version = version
        for root in runtime.windows:
            runtime.evaluate(root)
        return dict(version=version, settings=candidate.model_dump())
