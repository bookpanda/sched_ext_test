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


COLORS = {
    "usr": "#1f77b4",
    "nice": "#ff7f0e",
    "sys": "#2ca02c",
    "iowait": "#d62728",
    "irq": "#9467bd",
    "soft": "#8c564b",
    "idle": "#7f7f7f",
}


def plot(path, dest):
    elapsed, series = parse_mpstat(path)
    width, height = 960, 480
    left, right, top, bottom = 70, 160, 30, 50
    plot_w = width - left - right
    plot_h = height - top - bottom
    x_max = max(elapsed) or 1

    def x_of(second):
        return left + plot_w * second / x_max

    def y_of(percent):
        return top + plot_h * (1 - percent / 100)

    parts = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}">',
        '<rect width="100%" height="100%" fill="white"/>',
        f'<text x="{left + plot_w / 2}" y="{height - 12}" text-anchor="middle" font-size="14">time (s)</text>',
        f'<text x="18" y="{top + plot_h / 2}" text-anchor="middle" font-size="14" transform="rotate(-90 18 {top + plot_h / 2})">% average CPU</text>',
    ]
    for tick in range(0, 101, 25):
        y = y_of(tick)
        parts.append(f'<line x1="{left}" y1="{y:.1f}" x2="{left + plot_w}" y2="{y:.1f}" stroke="#e0e0e0"/>')
        parts.append(f'<text x="{left - 8}" y="{y + 4:.1f}" text-anchor="end" font-size="12">{tick}</text>')
    parts.append(f'<text x="{left}" y="{height - bottom + 18}" font-size="12">0</text>')
    parts.append(
        f'<text x="{left + plot_w}" y="{height - bottom + 18}" text-anchor="end" font-size="12">{x_max:.0f}</text>'
    )
    parts.append(
        f'<rect x="{left}" y="{top}" width="{plot_w}" height="{plot_h}" fill="none" stroke="#333"/>'
    )
    for name in FIELDS:
        points = " ".join(
            f"{x_of(second):.1f},{y_of(percent):.1f}"
            for second, percent in zip(elapsed, series[name])
        )
        parts.append(
            f'<polyline fill="none" stroke="{COLORS[name]}" stroke-width="2" points="{points}"/>'
        )
    legend_x = left + plot_w + 16
    for index, name in enumerate(FIELDS):
        y = top + 16 + index * 22
        parts.append(f'<line x1="{legend_x}" y1="{y}" x2="{legend_x + 18}" y2="{y}" stroke="{COLORS[name]}" stroke-width="3"/>')
        parts.append(f'<text x="{legend_x + 24}" y="{y + 4}" font-size="13">{name}</text>')
    parts.append("</svg>")
    Path(dest).write_text("\n".join(parts) + "\n")


def main():
    if len(sys.argv) not in (2, 3):
        raise SystemExit(f"usage: {sys.argv[0]} mpstat.txt [mpstat.png]")
    source = Path(sys.argv[1])
    dest = Path(sys.argv[2]) if len(sys.argv) == 3 else source.with_suffix(".svg")
    plot(source, dest)


if __name__ == "__main__":
    main()
