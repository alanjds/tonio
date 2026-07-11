# TonIO benchmarks

Run at: Sat 11 Jul 2026, 17:32    
Environment: AMD Ryzen 7 5700X @ Gentoo Linux 6.12.93 (CPUs: 16)    
Python version: 3.14    
TonIO version: 0.8.0    

### Running 1 million coroutines

Time to run 1 million coroutines (lower is better).


| Runtime | Creation time | Exec time | Total time | Relative performance |
| --- | --- | --- | --- | --- |
| TonIO yield | 111.586ms | 436.158ms | 547.744ms | 5.42x |
| TonIO async | 84.363ms | 801.735ms | 886.097ms | 3.35x |
| TonIO yield (context) | 73.089ms | 634.501ms | 707.59ms | 4.19x |
| TonIO async (context) | 51.898ms | 944.138ms | 996.036ms | 2.98x |
| AsyncIO | 41.32ms | 2925.154ms | 2966.474ms | 1.0x |
| Trio | 2820.314ms | 5084.876ms | 7905.19ms | 0.38x |
| TinyIO | 72.162ms | 3357.313ms | 3429.475ms | 0.86x |

### Sockets

TCP echo server with raw sockets comparison using 1KB, 10KB and 100KB messages.


| Runtime | Throughput (1KB) | Throughput (10KB) | Throughput (100KB) |
| --- | --- | --- | --- |
| TonIO yield | 112356.9 (2.1x) | 97099.9 (2.02x) | 41348.7 (1.47x) | 
| TonIO async | 115874.9 (2.16x) | 98661.5 (2.05x) | 42115.7 (1.5x) | 
| TonIO yield (context) | 108955.4 (2.03x) | 93965.4 (1.95x) | 41269.4 (1.47x) | 
| TonIO async (context) | 115194.2 (2.15x) | 96699.6 (2.01x) | 42667.8 (1.52x) | 
| AsyncIO | 53615.7 (1.0x) | 48099.5 (1.0x) | 28082.0 (1.0x) | 
| Trio | 79265.5 (1.48x) | 69249.4 (1.44x) | 35605.7 (1.27x) | 

#### 1KB details

| Runtime | Total requests | Throughput | Mean latency | 99p latency | Latency stdev |
| --- | --- | --- | --- | --- | --- |
| TonIO yield | 1123569 | 112356.9 (2.1x) | 0.032ms | 0.049ms | 0.004 |
| TonIO async | 1158749 | 115874.9 (2.16x) | 0.03ms | 0.046ms | 0.002 |
| TonIO yield (context) | 1089554 | 108955.4 (2.03x) | 0.039ms | 0.05ms | 0.003 |
| TonIO async (context) | 1151942 | 115194.2 (2.15x) | 0.031ms | 0.048ms | 0.003 |
| AsyncIO | 536157 | 53615.7 (1.0x) | 0.071ms | 0.09ms | 0.004 |
| Trio | 792655 | 79265.5 (1.48x) | 0.049ms | 0.076ms | 0.009 |


#### 10KB details

| Runtime | Total requests | Throughput | Mean latency | 99p latency | Latency stdev |
| --- | --- | --- | --- | --- | --- |
| TonIO yield | 970999 | 97099.9 (2.02x) | 0.04ms | 0.05ms | 0.001 |
| TonIO async | 986615 | 98661.5 (2.05x) | 0.04ms | 0.05ms | 0.002 |
| TonIO yield (context) | 939654 | 93965.4 (1.95x) | 0.04ms | 0.05ms | 0.002 |
| TonIO async (context) | 966996 | 96699.6 (2.01x) | 0.04ms | 0.05ms | 0.001 |
| AsyncIO | 480995 | 48099.5 (1.0x) | 0.081ms | 0.097ms | 0.003 |
| Trio | 692494 | 69249.4 (1.44x) | 0.056ms | 0.085ms | 0.011 |


#### 100KB details

| Runtime | Total requests | Throughput | Mean latency | 99p latency | Latency stdev |
| --- | --- | --- | --- | --- | --- |
| TonIO yield | 413487 | 41348.7 (1.47x) | 0.093ms | 0.112ms | 0.006 |
| TonIO async | 421157 | 42115.7 (1.5x) | 0.093ms | 0.11ms | 0.007 |
| TonIO yield (context) | 412694 | 41269.4 (1.47x) | 0.096ms | 0.111ms | 0.008 |
| TonIO async (context) | 426678 | 42667.8 (1.52x) | 0.091ms | 0.108ms | 0.004 |
| AsyncIO | 280820 | 28082.0 (1.0x) | 0.14ms | 0.164ms | 0.008 |
| Trio | 356057 | 35605.7 (1.27x) | 0.11ms | 0.157ms | 0.021 |


### Concurrency

#### 1 million coros


| Mode | Threads | Total time |
| --- | --- | --- |
| TonIO yield | 1 | 547.222ms |
| TonIO async | 1 | 894.152ms |
| TonIO yield | 2 | 676.385ms |
| TonIO async | 2 | 911.002ms |
| TonIO yield | 4 | 876.487ms |
| TonIO async | 4 | 911.071ms |
| TonIO yield | 8 | 1217.088ms |
| TonIO async | 8 | 1136.173ms |

#### Sockets


| Mode | Threads | Throughput (10KB) |
| --- | --- | --- |
| TonIO yield | 1 | 95122.2 |
| TonIO async | 1 | 96835.5 |
| TonIO yield | 2 | 170683.5 |
| TonIO async | 2 | 178237.0 |
| TonIO yield | 4 | 236133.5 |
| TonIO async | 4 | 249259.3 |
| TonIO yield | 8 | 330499.5 |
| TonIO async | 8 | 346245.6 |
