"""Metrics collection for chaos experiments."""

import statistics
import time
from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class MetricPoint:
    """A single metric data point."""

    name: str
    value: float
    timestamp: float
    labels: dict[str, str] = field(default_factory=dict)


@dataclass
class MetricSeries:
    """A time series of metric values."""

    name: str
    points: list[MetricPoint] = field(default_factory=list)

    def add(self, value: float, labels: Optional[dict[str, str]] = None):
        """Add a data point."""
        self.points.append(MetricPoint(
            name=self.name,
            value=value,
            timestamp=time.time(),
            labels=labels or {},
        ))

    @property
    def values(self) -> list[float]:
        return [p.value for p in self.points]

    @property
    def count(self) -> int:
        return len(self.points)

    def mean(self) -> float:
        if not self.points:
            return 0.0
        return statistics.mean(self.values)

    def median(self) -> float:
        if not self.points:
            return 0.0
        return statistics.median(self.values)

    def std_dev(self) -> float:
        if len(self.points) < 2:
            return 0.0
        return statistics.stdev(self.values)

    def percentile(self, p: float) -> float:
        """Get the p-th percentile (0-100)."""
        if not self.points:
            return 0.0
        sorted_values = sorted(self.values)
        idx = int(len(sorted_values) * p / 100)
        return sorted_values[min(idx, len(sorted_values) - 1)]

    def min(self) -> float:
        if not self.points:
            return 0.0
        return min(self.values)

    def max(self) -> float:
        if not self.points:
            return 0.0
        return max(self.values)

    def rate(self, window_seconds: float = 60.0) -> float:
        """Calculate rate per second over the window."""
        if len(self.points) < 2:
            return 0.0

        now = time.time()
        window_start = now - window_seconds
        window_points = [p for p in self.points if p.timestamp >= window_start]

        if len(window_points) < 2:
            return 0.0

        duration = window_points[-1].timestamp - window_points[0].timestamp
        if duration == 0:
            return 0.0

        return len(window_points) / duration

    def summary(self) -> dict[str, float]:
        """Get a summary of the metric."""
        return {
            "count": self.count,
            "mean": self.mean(),
            "median": self.median(),
            "std_dev": self.std_dev(),
            "min": self.min(),
            "max": self.max(),
            "p50": self.percentile(50),
            "p90": self.percentile(90),
            "p95": self.percentile(95),
            "p99": self.percentile(99),
        }


class MetricsCollector:
    """
    Collects and aggregates metrics from chaos experiments.

    Tracks:
    - Operation latencies
    - Failure rates
    - Recovery times
    - Retry counts
    - Fault injection rates
    """

    def __init__(self):
        self._series: dict[str, MetricSeries] = {}
        self._counters: dict[str, int] = {}
        self._start_time = time.time()

        # Initialize standard metrics
        self._init_standard_metrics()

    def _init_standard_metrics(self):
        """Initialize standard metric series."""
        standard_metrics = [
            "operation_latency_ms",
            "recovery_time_ms",
            "retry_count",
            "fault_injection_rate",
            "success_rate",
            "error_rate",
        ]
        for name in standard_metrics:
            self._series[name] = MetricSeries(name=name)

    def record(
        self,
        name: str,
        value: float,
        labels: Optional[dict[str, str]] = None,
    ):
        """Record a metric value."""
        if name not in self._series:
            self._series[name] = MetricSeries(name=name)
        self._series[name].add(value, labels)

    def increment(self, name: str, amount: int = 1):
        """Increment a counter."""
        self._counters[name] = self._counters.get(name, 0) + amount

    def get_counter(self, name: str) -> int:
        """Get a counter value."""
        return self._counters.get(name, 0)

    def get_series(self, name: str) -> Optional[MetricSeries]:
        """Get a metric series."""
        return self._series.get(name)

    def record_operation(
        self,
        operation_name: str,
        latency_ms: float,
        success: bool,
        retries: int = 0,
        fault_type: Optional[str] = None,
    ):
        """Record an operation with all its metrics."""
        labels = {"operation": operation_name}
        if fault_type:
            labels["fault_type"] = fault_type

        self.record("operation_latency_ms", latency_ms, labels)
        self.record("retry_count", retries, labels)

        if success:
            self.increment("operations_successful")
            self.record("success_rate", 1.0, labels)
        else:
            self.increment("operations_failed")
            self.record("success_rate", 0.0, labels)
            self.record("error_rate", 1.0, labels)

        self.increment("operations_total")

        if fault_type:
            self.increment(f"faults_{fault_type}")
            self.increment("faults_total")

    def record_recovery(
        self,
        operation_name: str,
        recovery_time_ms: float,
        recovery_method: str = "retry",
    ):
        """Record a recovery event."""
        self.record("recovery_time_ms", recovery_time_ms, {
            "operation": operation_name,
            "method": recovery_method,
        })
        self.increment("recoveries_total")

    def record_fault_injection(self, fault_type: str, target: str):
        """Record a fault injection event."""
        self.increment(f"injections_{fault_type}")
        self.increment("injections_total")
        self.record("fault_injection_rate", 1.0, {
            "fault_type": fault_type,
            "target": target,
        })

    def get_summary(self) -> dict[str, Any]:
        """Get a summary of all collected metrics."""
        elapsed = time.time() - self._start_time

        total_ops = self.get_counter("operations_total")
        successful_ops = self.get_counter("operations_successful")
        failed_ops = self.get_counter("operations_failed")

        summary = {
            "duration_seconds": elapsed,
            "operations": {
                "total": total_ops,
                "successful": successful_ops,
                "failed": failed_ops,
                "success_rate": successful_ops / total_ops if total_ops > 0 else 0,
            },
            "recoveries": {
                "total": self.get_counter("recoveries_total"),
            },
            "faults": {
                "total": self.get_counter("faults_total"),
            },
            "latency": {},
            "recovery_time": {},
        }

        # Add latency stats
        latency_series = self.get_series("operation_latency_ms")
        if latency_series and latency_series.count > 0:
            summary["latency"] = latency_series.summary()

        # Add recovery time stats
        recovery_series = self.get_series("recovery_time_ms")
        if recovery_series and recovery_series.count > 0:
            summary["recovery_time"] = recovery_series.summary()

        # Add per-fault-type stats
        fault_types = ["tool_failure", "delay", "hallucination", "context_corruption", "budget_exhaustion"]
        summary["faults_by_type"] = {
            ft: self.get_counter(f"faults_{ft}")
            for ft in fault_types
        }

        return summary

    def reset(self):
        """Reset all metrics."""
        self._series.clear()
        self._counters.clear()
        self._start_time = time.time()
        self._init_standard_metrics()

    def export_prometheus(self) -> str:
        """Export metrics in Prometheus format."""
        lines = []

        # Export counters
        for name, value in self._counters.items():
            lines.append(f"agentchaos_{name} {value}")

        # Export series summaries
        for name, series in self._series.items():
            if series.count > 0:
                lines.append(f"agentchaos_{name}_count {series.count}")
                lines.append(f"agentchaos_{name}_mean {series.mean()}")
                lines.append(f"agentchaos_{name}_p50 {series.percentile(50)}")
                lines.append(f"agentchaos_{name}_p90 {series.percentile(90)}")
                lines.append(f"agentchaos_{name}_p99 {series.percentile(99)}")

        return "\n".join(lines)

    def export_json(self) -> dict[str, Any]:
        """Export metrics as JSON-serializable dict."""
        return {
            "counters": dict(self._counters),
            "series": {
                name: {
                    "count": series.count,
                    "summary": series.summary(),
                    "recent_values": series.values[-100:],  # Last 100 values
                }
                for name, series in self._series.items()
            },
            "summary": self.get_summary(),
        }
