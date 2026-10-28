#!/usr/bin/env python3
"""Turn one run.sh result directory into metrics.json."""

import json
import re
import sys
from pathlib import Path


def parse_stress_ng(path):
    text = Path(path).read_text()
    row = re.search(
        r"stress-ng: metrc: \[\d+\]\s+(\S+)\s+"
        r"([\d.]+)\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)",
        text,
    )
    if row is None:
        raise SystemExit(f"no stress-ng metrics row in {path}")
    passed = re.search(r"passed:\s*(\d+)", text)
    failed = re.search(r"failed:\s*(\d+)", text)
    skipped = re.search(r"skipped:\s*(\d+)", text)
    return {
        "stressor": row.group(1),
        "bogo_ops": int(float(row.group(2))),
        "real_time_s": float(row.group(3)),
        "usr_time_s": float(row.group(4)),
        "sys_time_s": float(row.group(5)),
        "bogo_ops_per_s_real": float(row.group(6)),
        "bogo_ops_per_s_cpu": float(row.group(7)),
        "passed": int(passed.group(1)) if passed else None,
        "failed": int(failed.group(1)) if failed else None,
        "skipped": int(skipped.group(1)) if skipped else None,
    }


def _number(token):
    return float(token.replace(",", ""))


def parse_perf_stat(path):
    text = Path(path).read_text()
    command = re.search(r"Performance counter stats for '([^']*)'", text)
    counters = {}
    for line in text.splitlines():
        match = re.match(r"\s*([\d,\.]+)\s+(?:msec\s+)?([A-Za-z0-9_-]+)\s*$", line)
        if match is None:
            continue
        counters[match.group(2).replace("-", "_")] = _number(match.group(1))
    elapsed = re.search(r"([\d.]+) seconds time elapsed", text)
    user = re.search(r"([\d.]+) seconds user", text)
    sys_time = re.search(r"([\d.]+) seconds sys", text)
    if "task_clock" not in counters or elapsed is None:
        raise SystemExit(f"no perf stat counters in {path}")
    return {
        "command": command.group(1) if command else None,
        "task_clock_ms": counters["task_clock"],
        "context_switches": int(counters.get("context_switches", 0)),
        "cpu_migrations": int(counters.get("cpu_migrations", 0)),
        "page_faults": int(counters.get("page_faults", 0)),
        "time_elapsed_s": float(elapsed.group(1)),
        "user_s": float(user.group(1)) if user else None,
        "sys_s": float(sys_time.group(1)) if sys_time else None,
    }


def _percentile_key(label):
    if label.endswith(".0"):
        return "p" + label[:-2]
    return "p" + label.replace(".", "_")


def parse_schbench(path):
    text = Path(path).read_text()
    header = re.compile(
        r"^(Wakeup Latencies|Request Latencies|RPS) percentiles "
        r"\((usec|requests)\) runtime (\d+) \(s\) \((\d+) total samples\)"
    )
    percentile = re.compile(r"^\*?\s*([\d.]+)th:\s*(\d+)")
    minmax = re.compile(r"min=(\d+), max=(\d+)")
    sections = {
        "Wakeup Latencies": None,
        "Request Latencies": None,
        "RPS": None,
    }
    current = None
    sched_delay = None
    average_rps = None

    for raw in text.splitlines():
        line = raw.strip()
        found = header.match(line)
        if found:
            kind, unit, runtime_s, samples = found.groups()
            current = {
                "runtime_s": int(runtime_s),
                "samples": int(samples),
                "unit": unit,
            }
            sections[kind] = current
            continue
        if current is not None:
            point = percentile.match(line)
            if point:
                current[_percentile_key(point.group(1))] = int(point.group(2))
                continue
            bounds = minmax.search(line)
            if bounds:
                current["min"] = int(bounds.group(1))
                current["max"] = int(bounds.group(2))
                current = None
                continue
        delay = re.search(r"sched delay: message (\d+) \(usec\) worker (\d+) \(usec\)", line)
        if delay:
            message, worker = int(delay.group(1)), int(delay.group(2))
            if message or worker or sched_delay is None:
                sched_delay = {"message": message, "worker": worker}
            continue
        rps = re.search(r"average rps:\s*([\d.]+)", line)
        if rps:
            average_rps = float(rps.group(1))

    if sections["Wakeup Latencies"] is None or average_rps is None:
        raise SystemExit(f"no schbench summary in {path}")
    return {
        "wakeup_latency_usec": sections["Wakeup Latencies"],
        "request_latency_usec": sections["Request Latencies"],
        "rps": sections["RPS"],
        "average_rps": average_rps,
        "sched_delay_usec": sched_delay,
    }


MPSTAT_FIELDS = ("usr", "nice", "sys", "iowait", "irq", "soft", "idle")


def parse_mpstat_avg(path):
    """Average % time in each state across the CPUs recorded in an mpstat log."""
    columns = None
    time_tokens = None
    totals = {name: 0.0 for name in MPSTAT_FIELDS}
    cpus = set()
    samples = 0
    intervals = set()

    for raw in Path(path).read_text().splitlines():
        parts = raw.split()
        if not parts or parts[0].startswith("Linux") or parts[0] == "Average:":
            continue
        if "CPU" in parts and any(part.startswith("%") for part in parts):
            cpu_at = parts.index("CPU")
            columns = {}
            for index, name in enumerate(parts):
                if name.startswith("%"):
                    columns[name[1:]] = index
            time_tokens = cpu_at
            continue
        if columns is None or len(parts) <= time_tokens:
            continue
        cpu = parts[time_tokens]
        if cpu == "all" or not cpu.isdigit():
            continue
        cpus.add(int(cpu))
        intervals.add(" ".join(parts[:time_tokens]))
        samples += 1
        for name in MPSTAT_FIELDS:
            totals[name] += float(parts[columns[name]])

    if samples == 0:
        raise SystemExit(f"no per-CPU mpstat rows in {path}")
    averages = {name: round(totals[name] / samples, 2) for name in MPSTAT_FIELDS}
    return {
        "cpus": sorted(cpus),
        "intervals": len(intervals),
        **averages,
    }


def summarize(result_dir):
    directory = Path(result_dir)
    benches = []
    if (directory / "stress-ng.txt").exists():
        benches.append({
            "bench": "stress-ng",
            "stress_ng": parse_stress_ng(directory / "stress-ng.txt"),
            "perf": parse_perf_stat(directory / "perf-stat-stress-ng.txt"),
            "mpstat": parse_mpstat_avg(directory / "mpstat-stress-ng.txt"),
        })
    if (directory / "schbench.txt").exists():
        benches.append({
            "bench": "schbench",
            "schbench": parse_schbench(directory / "schbench.txt"),
            "perf": parse_perf_stat(directory / "perf-stat-schbench.txt"),
            "mpstat": parse_mpstat_avg(directory / "mpstat-schbench.txt"),
        })
    if not benches:
        raise SystemExit(f"no benchmark logs in {directory}")
    return benches


def main():
    if len(sys.argv) != 2:
        raise SystemExit(f"usage: {sys.argv[0]} result-dir")
    directory = Path(sys.argv[1])
    destination = directory / "metrics.json"
    destination.write_text(json.dumps(summarize(directory), indent=2) + "\n")


if __name__ == "__main__":
    main()
