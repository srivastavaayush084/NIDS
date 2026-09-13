import math
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field, asdict


@dataclass
class LatencyStats:
    count: int = 0
    mean_ms: float = 0.0
    min_ms: float = 0.0
    max_ms: float = 0.0
    std_dev_ms: float = 0.0
    p50_ms: float = 0.0
    p90_ms: float = 0.0
    p95_ms: float = 0.0
    p99_ms: float = 0.0
    throughput_rps: float = 0.0
    total_duration_s: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "count": self.count,
            "mean_ms": round(self.mean_ms, 3),
            "min_ms": round(self.min_ms, 3),
            "max_ms": round(self.max_ms, 3),
            "std_dev_ms": round(self.std_dev_ms, 3),
            "p50_ms": round(self.p50_ms, 3),
            "p90_ms": round(self.p90_ms, 3),
            "p95_ms": round(self.p95_ms, 3),
            "p99_ms": round(self.p99_ms, 3),
            "throughput_rps": round(self.throughput_rps, 2),
            "total_duration_s": round(self.total_duration_s, 3),
        }


def compute_latency_stats(
    latencies_ms: List[float],
    total_duration_s: Optional[float] = None,
) -> LatencyStats:
    """
    Compute rigorous statistical metrics from a list of latency samples (in milliseconds).
    """
    if not latencies_ms:
        return LatencyStats()

    sorted_lats = sorted(latencies_ms)
    n = len(sorted_lats)
    mean_val = sum(sorted_lats) / n
    min_val = sorted_lats[0]
    max_val = sorted_lats[-1]

    # Standard deviation
    variance = sum((x - mean_val) ** 2 for x in sorted_lats) / n if n > 1 else 0.0
    std_dev = math.sqrt(variance)

    def percentile(p: float) -> float:
        if n == 1:
            return sorted_lats[0]
        k = (n - 1) * (p / 100.0)
        f = math.floor(k)
        c = math.ceil(k)
        if f == c:
            return sorted_lats[int(k)]
        d0 = sorted_lats[int(f)] * (c - k)
        d1 = sorted_lats[int(c)] * (k - f)
        return d0 + d1

    p50 = percentile(50.0)
    p90 = percentile(90.0)
    p95 = percentile(95.0)
    p99 = percentile(99.0)

    duration = total_duration_s if total_duration_s and total_duration_s > 0 else (sum(latencies_ms) / 1000.0)
    throughput = (n / duration) if duration > 0 else 0.0

    return LatencyStats(
        count=n,
        mean_ms=mean_val,
        min_ms=min_val,
        max_ms=max_val,
        std_dev_ms=std_dev,
        p50_ms=p50,
        p90_ms=p90,
        p95_ms=p95,
        p99_ms=p99,
        throughput_rps=throughput,
        total_duration_s=duration,
    )
