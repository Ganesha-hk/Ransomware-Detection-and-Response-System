def severity(score, config):
    return (
        "Critical"
        if score >= config.critical_min
        else "Warning"
        if score >= config.warning_min
        else "Normal"
    )


def score(signals, config):
    contributions = {k: config.weights[k] for k, v in signals.items() if v}
    value = min(100, sum(contributions.values()))
    return dict(score=value, severity=severity(value, config), contributions=contributions)
