core experiment should run two workloads simultaneously:
1. Latency-critical workload: Memcached serving requests with a controlled offered load.
2. Bandwidth-intensive side load: a workload that competes for CPU, memory bandwidth, or shared caches.

## competition
1. Default Linux EEVDF
2. EEVDF + static cpusets
3. dynamic sched_ext scheduler (SLO-aware)


## claims
- Claim 1: SLO protection
  - Can your scheduler sustain the required peak Memcached load under CPU, memory-bandwidth, and cache contention without violating the agreed SLO?
- Claim 2: Better resource utilization
  - When the protected workload is below peak demand, can the side load consume spare capacity and complete more useful work than under static partitioning?
- Claim 3: Dynamic adaptation
  - When demand changes, can the scheduler adapt quickly enough to protect latency while avoiding unnecessary idle CPU capacity?

most compelling results will be plots of Memcached p99 latency and side-load throughput against offered Memcached load

Add SLO and CPU-utilization markers, plus a time-series plot showing how the scheduler reacts to a sudden workload increase.

your side load should include more than one type of contention. 
- A CPU-heavy load tests CPU scheduling
- a memory-bandwidth-heavy load tests whether your scheduler can protect latency even when tasks contend for memory bandwidth, which CPU scheduling alone cannot directly partition.

can run server/client on the same machine, or on different machines.
begin with local TCP loopback. First prove that your scheduler can preserve Memcached's tail latency while allowing the side load to use otherwise available CPU capacity.