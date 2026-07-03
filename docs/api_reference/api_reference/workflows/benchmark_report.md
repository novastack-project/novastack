---
title: Benchmarks Report
---

## 🧪 Environment

- **Python Version**: 3.11
- **Machine**: arm64
- **Processor**: arm
- **CPU Cores**: 14 cores
- **CPU Frequency**: 4 MHz
- **Total Memory**: 36.00 GB
- **novastack-workflows Version**: 1.1.2

## 1. 📈 Scalability

How performance scales with workflow complexity and data size.

### O(1) Workflow

| Metric | Value |
|--------|-------|
| Iterations | 100 |
| Avg Latency | 0.45 ms |
| Min Latency | 0.42 ms |
| Max Latency | 0.61 ms |
| Std Deviation | 0.03 ms |
| Throughput | 2227.98 wf/s |
| Peak Memory | 0.03 MB |

### O(n) Workflow

| Data Size | Avg Latency | Throughput | Peak Memory |
|-----------|-------------|------------|-------------|
| 10 | 0.90 ms | 1115.98 wf/s | 0.01 MB |
| 100 | 0.89 ms | 1121.85 wf/s | 0.01 MB |
| 1,000 | 0.91 ms | 1099.38 wf/s | 0.02 MB |
| 10,000 | 1.12 ms | 894.12 wf/s | 0.09 MB |

## 2. 🔄 Concurrency

How performance scales with parallel workflow execution.

### O(1) Workflow

| Concurrency | Throughput | Avg Latency/WF | Peak Memory |
|-------------|------------|----------------|-------------|
| 1 | 1905.47 wf/s | 0.52 ms | 0.01 MB |
| 10 | 4370.18 wf/s | 0.23 ms | 0.09 MB |
| 50 | 5015.76 wf/s | 0.20 ms | 0.45 MB |
| 100 | 5168.48 wf/s | 0.19 ms | 0.88 MB |

### O(n) Workflow

| Concurrency | Throughput | Avg Latency/WF | Peak Memory |
|-------------|------------|----------------|-------------|
| 1 | 989.39 wf/s | 1.01 ms | 0.01 MB |
| 10 | 2176.67 wf/s | 0.46 ms | 0.12 MB |
| 50 | 2385.43 wf/s | 0.42 ms | 0.62 MB |
| 100 | 2146.29 wf/s | 0.47 ms | 1.31 MB |
