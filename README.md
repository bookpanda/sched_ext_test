# sched_ext_test
```bash
sudo apt-get install -y clang
bear -- make

cat /sys/kernel/sched_ext/state
# which scheduler is running
cat /sys/kernel/sched_ext/root/ops
# diagnostic counters
cat /sys/kernel/sched_ext/root/events
```

