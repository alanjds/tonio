# TonIO benchmarks

Run at: Sat 11 Jul 2026, 15:59    
Environment: AMD Ryzen 7 5700X @ Gentoo Linux 6.12.93 (CPUs: 16)    
Python version: 3.14    
TonIO version: 0.8.0    

### Running 1 million coroutines

Time to run 1 million coroutines (lower is better).


| Runtime | Creation time | Exec time | Total time | Relative performance |
| --- | --- | --- | --- | --- |
| TonIO yield | 111.021ms | 441.991ms | 553.012ms | 5.33x |
| TonIO async | 84.723ms | 800.13ms | 884.853ms | 3.33x |
| TonIO yield (context) | 73.389ms | 650.465ms | 723.854ms | 4.07x |
| TonIO async (context) | 51.94ms | 955.25ms | 1007.19ms | 2.93x |
| AsyncIO | 41.058ms | 2905.37ms | 2946.428ms | 1.0x |
| Trio | 2249.859ms | 5114.693ms | 7364.552ms | 0.4x |
| TinyIO | 72.036ms | 3361.385ms | 3433.422ms | 0.86x |

### Sockets

TCP echo server with raw sockets comparison using 1KB, 10KB and 100KB messages.


| Runtime | Throughput (1KB) | Throughput (10KB) | Throughput (100KB) |
| --- | --- | --- | --- |
| TonIO yield | 111902.5 (2.07x) | 95212.1 (1.97x) | 40422.7 (1.45x) | 
| TonIO async | 117049.0 (2.17x) | 100053.4 (2.07x) | 42627.0 (1.53x) | 
| TonIO yield (context) | 111189.5 (2.06x) | 96032.6 (1.99x) | 41971.6 (1.51x) | 
| TonIO async (context) | 115383.5 (2.14x) | 98284.6 (2.03x) | 41400.2 (1.49x) | 
| AsyncIO | 54043.6 (1.0x) | 48364.8 (1.0x) | 27852.0 (1.0x) | 
| Trio | 79770.4 (1.48x) | 69135.8 (1.43x) | 33809.1 (1.21x) | 

#### 1KB details

| Runtime | Total requests | Throughput | Mean latency | 99p latency | Latency stdev |
| --- | --- | --- | --- | --- | --- |
| TonIO yield | 1119025 | 111902.5 (2.07x) | 0.032ms | 0.049ms | 0.004 |
| TonIO async | 1170490 | 117049.0 (2.17x) | 0.03ms | 0.041ms | 0.002 |
| TonIO yield (context) | 1111895 | 111189.5 (2.06x) | 0.032ms | 0.049ms | 0.004 |
| TonIO async (context) | 1153835 | 115383.5 (2.14x) | 0.031ms | 0.047ms | 0.003 |
| AsyncIO | 540436 | 54043.6 (1.0x) | 0.071ms | 0.089ms | 0.004 |
| Trio | 797704 | 79770.4 (1.48x) | 0.049ms | 0.075ms | 0.01 |


#### 10KB details

| Runtime | Total requests | Throughput | Mean latency | 99p latency | Latency stdev |
| --- | --- | --- | --- | --- | --- |
| TonIO yield | 952121 | 95212.1 (1.97x) | 0.04ms | 0.05ms | 0.002 |
| TonIO async | 1000534 | 100053.4 (2.07x) | 0.04ms | 0.05ms | 0.004 |
| TonIO yield (context) | 960326 | 96032.6 (1.99x) | 0.04ms | 0.05ms | 0.003 |
| TonIO async (context) | 982846 | 98284.6 (2.03x) | 0.04ms | 0.05ms | 0.003 |
| AsyncIO | 483648 | 48364.8 (1.0x) | 0.081ms | 0.099ms | 0.004 |
| Trio | 691358 | 69135.8 (1.43x) | 0.056ms | 0.085ms | 0.011 |


#### 100KB details

| Runtime | Total requests | Throughput | Mean latency | 99p latency | Latency stdev |
| --- | --- | --- | --- | --- | --- |
| TonIO yield | 404227 | 40422.7 (1.45x) | 0.098ms | 0.117ms | 0.006 |
| TonIO async | 426270 | 42627.0 (1.53x) | 0.091ms | 0.109ms | 0.004 |
| TonIO yield (context) | 419716 | 41971.6 (1.51x) | 0.093ms | 0.11ms | 0.006 |
| TonIO async (context) | 414002 | 41400.2 (1.49x) | 0.093ms | 0.11ms | 0.005 |
| AsyncIO | 278520 | 27852.0 (1.0x) | 0.141ms | 0.167ms | 0.01 |
| Trio | 338091 | 33809.1 (1.21x) | 0.116ms | 0.166ms | 0.022 |


### Concurrency

#### 1 million coros


| Mode | Threads | Total time |
| --- | --- | --- |
| TonIO yield | 1 | 552.624ms |
| TonIO async | 1 | 885.205ms |
| TonIO yield | 2 | 809.889ms |
| TonIO async | 2 | 911.536ms |
| TonIO yield | 4 | 1001.58ms |
| TonIO async | 4 | 933.711ms |
| TonIO yield | 8 | 1234.083ms |
| TonIO async | 8 | 1311.115ms |

#### Sockets


| Mode | Threads | Throughput (10KB) |
| --- | --- | --- |
| TonIO yield | 1 | 94196.2 |
| TonIO async | 1 | 99679.0 |
| TonIO yield | 2 | 167536.7 |
| TonIO async | 2 | 179658.6 |
| TonIO yield | 4 | 238816.7 |
| TonIO async | 4 | 248321.7 |
| TonIO yield | 8 | 335412.8 |
| TonIO async | 8 | 340941.9 |
