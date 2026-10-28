# sched_ext_test
```bash
./setup.sh
bear -- make

cat /sys/kernel/sched_ext/state
# which scheduler is running
cat /sys/kernel/sched_ext/root/ops
# diagnostic counters
cat /sys/kernel/sched_ext/root/events
```

## testing
```bash
sudo ./simple/build/scx_simple 
stress-ng --cpu 0 --timeout 60s --metrics-brief 2>&1 | tee stress-ng.log

```