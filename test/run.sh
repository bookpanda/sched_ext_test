#!/bin/bash
# usage: ./test/run.sh linux|simple

set -euo pipefail

if [[ $# -ne 1 || ( "$1" != linux && "$1" != simple ) ]]; then
	echo "usage: $0 linux|simple" >&2
	exit 1
fi

sched=$1
root=$(cd "$(dirname "$0")/.." && pwd)
schbench=$(cd "$root/.." && pwd)/schbench/schbench
out="$root/test/results/$(date +%Hh%M-%d-%m-%Y)-${sched}"

scx="$root/simple/build/scx_simple"

if [[ ! -x "$schbench" ]]; then
	echo "missing schbench at $schbench" >&2
	exit 1
fi

state=$(cat /sys/kernel/sched_ext/state 2>/dev/null || echo missing)
if [[ "$state" != disabled ]]; then
	echo "sched_ext state is '$state'; stop the current scheduler first" >&2
	exit 1
fi

mkdir -p "$out"
scx_pid=
mpstat_pid=

cleanup() {
	if [[ -n "$mpstat_pid" ]]; then
		kill "$mpstat_pid" 2>/dev/null || true
		wait "$mpstat_pid" 2>/dev/null || true
		mpstat_pid=
	fi
	if [[ -n "$scx_pid" ]]; then
		sudo kill -INT "$scx_pid" 2>/dev/null || true
		wait "$scx_pid" 2>/dev/null || true
		scx_pid=
	fi
}
trap cleanup EXIT

if [[ "$sched" == simple ]]; then
	if [[ ! -x "$scx" ]]; then
		echo "missing $scx (build it with make -C simple)" >&2
		exit 1
	fi
	sudo "$scx" >"$out/scx_simple.txt" 2>&1 &
	scx_pid=$!
	attached=
	for _ in $(seq 1 50); do
		if [[ "$(cat /sys/kernel/sched_ext/state)" == enabled ]]; then
			attached=1
			break
		fi
		sleep 0.1
	done
	if [[ -z "$attached" ]]; then
		echo "scx_simple did not attach; see $out/scx_simple.txt" >&2
		exit 1
	fi
fi

python="$root/.venv/bin/python"
if [[ ! -x "$python" ]]; then
    python=python3
fi

run_bench() {
	local name=$1
	shift # drops $1 and slides the rest down ($@)
    echo "⏰ running $name..."
	mpstat -P ALL 1 >"$out/mpstat-${name}.txt" &
	mpstat_pid=$!
	sudo perf stat -o "$out/perf-stat-${name}.txt" \
		-e task-clock,context-switches,cpu-migrations,page-faults \
		-- "$@" >"$out/${name}.txt" 2>&1
	kill "$mpstat_pid" 2>/dev/null || true
	wait "$mpstat_pid" 2>/dev/null || true
	mpstat_pid=
    echo "✅ done $name, plotting mpstat..."
	
	"$python" "$root/test/plot_mpstat.py" \
		"$out/mpstat-${name}.txt" \
		"$out/mpstat-${name}.png"
}

# $1 is 1st arg, $@ is all args
run_bench stress-ng stress-ng --cpu 0 --timeout 60s --metrics-brief
run_bench schbench "$schbench" -m 1 -t "$(nproc)" -r 60

echo "$out"
