#!/usr/bin/env python3
"""Plot mpstat -P ALL samples: average CPU time in each state."""

import sys
from datetime import datetime
from pathlib import Path


FIELDS = ("usr", "nice", "sys", "iowait", "irq", "soft", "idle")


def _seconds(stamp):
    for fmt in ("%I:%M:%S %p", "%H:%M:%S"):
        try:
            parsed = datetime.strptime(stamp, fmt)
        except ValueError:
            continue
        return parsed.hour * 3600 + parsed.minute * 60 + parsed.second
    raise ValueError(f"unrecognized mpstat timestamp {stamp!r}")


def parse_mpstat(path):
    """Return elapsed seconds and {field: [percent, ...]} for the 'all' CPU."""
    columns = None
    time_tokens = None
    elapsed = []
    series = {name: [] for name in FIELDS}
    origin = None
    previous = None

    for raw in Path(path).read_text().splitlines():
        parts = raw.split()
        if not parts or parts[0].startswith("Linux"):
            continue
        if "CPU" in parts and any(part.startswith("%") for part in parts):
            cpu_at = parts.index("CPU")
            columns = {}
            for index, name in enumerate(parts):
                if name.startswith("%"):
                    columns[name[1:]] = index
            time_tokens = cpu_at
            continue
        if columns is None or parts[0] == "Average:":
            continue
        if len(parts) <= time_tokens or parts[time_tokens] != "all":
            continue

        stamp = " ".join(parts[:time_tokens])
        now = _seconds(stamp)
        if origin is None:
            origin = now
            previous = now
        elif now < previous:
            # Clock wrapped past midnight between samples.
            origin -= 24 * 3600
        previous = now
        elapsed.append(now - origin)
        for name in FIELDS:
            series[name].append(float(parts[columns[name]]))

    if not elapsed:
        raise SystemExit(f"no per-interval 'all' rows in {path}")
    return elapsed, series


def plot(path, dest):
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    elapsed, series = parse_mpstat(path)
    figure, axis = plt.subplots(figsize=(10, 5))
    for name in FIELDS:
        axis.plot(elapsed, series[name], label=name)
    axis.set_xlabel("time (s)")
    axis.set_ylabel("% average CPU")
    axis.set_ylim(0, 100)
    axis.legend(loc="upper right")
    axis.grid(True, alpha=0.3)
    figure.tight_layout()
    figure.savefig(dest)
    plt.close(figure)


def main():
    if len(sys.argv) not in (2, 3):
        raise SystemExit(f"usage: {sys.argv[0]} mpstat.txt [mpstat.png]")
    source = Path(sys.argv[1])
    dest = Path(sys.argv[2]) if len(sys.argv) == 3 else source.with_suffix(".png")
    plot(source, dest)


if __name__ == "__main__":
    main()
