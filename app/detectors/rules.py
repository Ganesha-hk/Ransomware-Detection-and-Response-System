from app.detectors.scoring import score


def evaluate(files, config, context=(), allowlist=()):
    values = list(files.values())
    changed = [f for f in values if f["changed"]]
    valid = [f["entropy"] for f in changed if f["entropy"] is not None]
    high = sum(v >= config.entropy_threshold for v in valid)
    mean = sum(valid) / len(valid) if valid else None
    moves = sum(f["moved"] for f in values)
    suffix = sum(f["suffix_changed"] for f in values)
    supported = [p for p in context if p.get("supported_candidate")]
    signals = dict(
        rapid_high_entropy_writes=high >= config.rapid_write_min_files,
        mass_rename=moves >= config.mass_rename_min_files
        and suffix >= config.extension_change_min_files,
        high_entropy=len(valid) >= config.high_entropy_min_files
        and mean >= config.entropy_threshold,
        cpu_spike=config.cpu_signal_enabled
        and any(
            p.get("cpu_percent") is not None and p["cpu_percent"] >= config.cpu_threshold_percent
            for p in supported
        ),
        unknown_program=config.unknown_program_signal_enabled
        and bool(allowlist)
        and any(p.get("executable") and p["executable"] not in allowlist for p in supported),
    )
    return {
        **score(signals, config),
        "facts": dict(
            changed_files=len(changed),
            moved_files=moves,
            suffix_changes=suffix,
            valid_samples=len(valid),
            high_entropy_files=high,
            mean_entropy=mean,
        ),
    }
