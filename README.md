# sched_ext_test
```bash
./setup.sh
# select python interpreter as the one in ./.venv/bin/python
bear -- make

cat /sys/kernel/sched_ext/state
# which scheduler is running
cat /sys/kernel/sched_ext/root/ops
# diagnostic counters
cat /sys/kernel/sched_ext/root/events
```

## testing
Use schbench for latency percentiles and more targeted tracing (bpftrace) when you need to investigate why latency changed.
```bash
sudo ./simple/build/scx_simple 

# test everything: <cores> <scheduler>
./test/run.sh 4 linux
./test/run.sh 4 simple



# CPU throughput
stress-ng --cpu 0 --timeout 60s --metrics-brief 2>&1 | tee stress-ng.log

# Scheduling latency
../schbench/schbench -m 1 -t "$(nproc)" -r 60 2>&1 | tee schbench.log

perf stat -r 3 \
  -e task-clock,context-switches,cpu-migrations,page-faults \
  -- stress-ng --cpu 0 --timeout 30s --metrics-brief

sudo bpftrace ./test/sched.bt

# investigate whether your scheduler callbacks are becoming expensive
# use this while your scheduler is running a benchmark
sudo bpftop
```