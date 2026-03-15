"""Metrics collection for chaos experiments."""

import statistics
import time
from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class ConsistencyViolation:
    """Record of a state consistency violation."""

    timestamp: float
    node_name: str
    violation_type: str
    details: str

    def __repr__(self) -> str:
        """Return a readable representation."""
        return f"ConsistencyViolation({self.node_name}, {self.violation_type}: {self.details})"


@dataclass
class EdgeTraversalEvent:
    """Record of an edge traversal between nodes."""

    source_node: str
    target_node: str
    traversal_start: float
    traversal_end: Optional[float] = None

    @property
    def delay_ms(self) -> float:
        """Get traversal delay in milliseconds."""
        if self.traversal_end is None:
            return 0.0
        return (self.traversal_end - self.traversal_start) * 1000

    @property
    def edge_id(self) -> str:
        """Get edge identifier as source->target."""
        return f"{self.source_node}->{self.target_node}"


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
        self.points.append(
            MetricPoint(
                name=self.name,
                value=value,
                timestamp=time.time(),
                labels=labels or {},
            )
        )

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
    - Edge traversal timing (between nodes)
    - State mutation sizes
    """

    def __init__(self):
        self._series: dict[str, MetricSeries] = {}
        self._counters: dict[str, int] = {}
        self._start_time = time.time()

        # Edge traversal tracking
        self._edge_traversals: list[EdgeTraversalEvent] = []

        # State consistency tracking
        self._consistency_violations: list[ConsistencyViolation] = []
        self._state_schemas: dict[str, set[str]] = {}  # Track expected fields per node

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
        self.record(
            "recovery_time_ms",
            recovery_time_ms,
            {
                "operation": operation_name,
                "method": recovery_method,
            },
        )
        self.increment("recoveries_total")

    def record_fault_injection(self, fault_type: str, target: str):
        """Record a fault injection event."""
        self.increment(f"injections_{fault_type}")
        self.increment("injections_total")
        self.record(
            "fault_injection_rate",
            1.0,
            {
                "fault_type": fault_type,
                "target": target,
            },
        )

    def record_edge_traversal_start(self, source_node: str, target_node: str) -> float:
        """Record the start of an edge traversal and return the timestamp.

        Args:
            source_node: Name of the source node
            target_node: Name of the target node

        Returns:
            The traversal start timestamp
        """
        start_time = time.time()
        self.increment(f"edge_traversals_{source_node}_to_{target_node}")
        self.increment("edge_traversals_total")
        return start_time

    def record_edge_traversal_end(
        self,
        source_node: str,
        target_node: str,
        traversal_start: float,
        state_mutation_size: int = 0,
    ) -> None:
        """Record the end of an edge traversal.

        Args:
            source_node: Name of the source node
            target_node: Name of the target node
            traversal_start: The traversal start timestamp
            state_mutation_size: Size of state changes between nodes in bytes
        """
        event = EdgeTraversalEvent(
            source_node=source_node,
            target_node=target_node,
            traversal_start=traversal_start,
            traversal_end=time.time(),
        )
        self._edge_traversals.append(event)

        # Record edge delay metric
        self.record(
            "edge_delay_ms",
            event.delay_ms,
            {
                "source": source_node,
                "target": target_node,
            },
        )

        # Record state mutation size if provided
        if state_mutation_size > 0:
            self.record(
                "state_mutation_size_bytes",
                state_mutation_size,
                {
                    "source": source_node,
                    "target": target_node,
                },
            )

    def get_edge_metrics(self) -> dict[str, Any]:
        """Get edge traversal metrics.

        Returns:
            Dictionary with edge traversal statistics including delay and mutation sizes
        """
        if not self._edge_traversals:
            return {
                "total_edge_traversals": 0,
                "edges": {},
            }

        edges_by_id: dict[str, list[EdgeTraversalEvent]] = {}
        for event in self._edge_traversals:
            if event.edge_id not in edges_by_id:
                edges_by_id[event.edge_id] = []
            edges_by_id[event.edge_id].append(event)

        edge_stats = {}
        for edge_id, events in edges_by_id.items():
            delays_ms = [e.delay_ms for e in events]
            edge_stats[edge_id] = {
                "traversal_count": len(events),
                "delay_ms": {
                    "mean": statistics.mean(delays_ms) if delays_ms else 0.0,
                    "min": min(delays_ms) if delays_ms else 0.0,
                    "max": max(delays_ms) if delays_ms else 0.0,
                    "median": statistics.median(delays_ms) if delays_ms else 0.0,
                    "stdev": statistics.stdev(delays_ms) if len(delays_ms) > 1 else 0.0,
                },
            }

        return {
            "total_edge_traversals": len(self._edge_traversals),
            "edges": edge_stats,
        }

    def get_edge_traversals(self) -> list[EdgeTraversalEvent]:
        """Get all recorded edge traversal events.

        Returns:
            List of EdgeTraversalEvent objects
        """
        return self._edge_traversals.copy()

    def get_edge_traversals_between(
        self, source_node: str, target_node: str
    ) -> list[EdgeTraversalEvent]:
        """Get all traversals for a specific edge.

        Args:
            source_node: Source node name
            target_node: Target node name

        Returns:
            List of traversal events for this edge
        """
        return [
            e
            for e in self._edge_traversals
            if e.source_node == source_node and e.target_node == target_node
        ]

    def validate_state_schema(self, node_name: str, state: Any) -> None:
        """Validate state schema consistency for a node.

        Establishes schema on first call, checks consistency on subsequent calls.

        Args:
            node_name: Name of the node
            state: The state object to validate
        """
        if not isinstance(state, dict):
            # Can't validate non-dict states easily
            return

        state_fields = set(state.keys())

        # Establish schema on first call
        if node_name not in self._state_schemas:
            self._state_schemas[node_name] = state_fields
            return

        expected_fields = self._state_schemas[node_name]

        # Check for new unexpected fields
        new_fields = state_fields - expected_fields
        if new_fields:
            violation = ConsistencyViolation(
                timestamp=time.time(),
                node_name=node_name,
                violation_type="unexpected_fields",
                details=f"New fields appeared: {sorted(new_fields)}",
            )
            self._consistency_violations.append(violation)
            self.increment("consistency_violations")

        # Check for missing fields
        missing_fields = expected_fields - state_fields
        if missing_fields:
            violation = ConsistencyViolation(
                timestamp=time.time(),
                node_name=node_name,
                violation_type="missing_fields",
                details=f"Fields disappeared: {sorted(missing_fields)}",
            )
            self._consistency_violations.append(violation)
            self.increment("consistency_violations")

    def check_state_mutation_reasonableness(
        self, node_name: str, state_before: Any, state_after: Any
    ) -> None:
        """Check if state mutations are reasonable (e.g., collection sizes don't explode).

        Args:
            node_name: Name of the node
            state_before: State before mutation
            state_after: State after mutation
        """
        if not isinstance(state_before, dict) or not isinstance(state_after, dict):
            return

        for key in state_before:
            if key not in state_after:
                continue

            before_val = state_before[key]
            after_val = state_after[key]

            # Check for explosive collection growth
            if isinstance(before_val, (list, dict, str)):
                before_size = len(before_val)
                after_size = len(after_val)

                # Flag if size increased by >10x
                if before_size > 0 and after_size > before_size * 10:
                    violation = ConsistencyViolation(
                        timestamp=time.time(),
                        node_name=node_name,
                        violation_type="explosive_growth",
                        details=f"Field '{key}': {before_size} -> {after_size} items (10x growth)",
                    )
                    self._consistency_violations.append(violation)
                    self.increment("consistency_violations")

    def get_consistency_violations(self) -> list[ConsistencyViolation]:
        """Get all recorded consistency violations.

        Returns:
            List of ConsistencyViolation objects
        """
        return self._consistency_violations.copy()

    def get_consistency_violations_for_node(self, node_name: str) -> list[ConsistencyViolation]:
        """Get consistency violations for a specific node.

        Args:
            node_name: Name of the node

        Returns:
            List of violations for this node
        """
        return [v for v in self._consistency_violations if v.node_name == node_name]

    def get_consistency_summary(self) -> dict[str, Any]:
        """Get a summary of state consistency violations.

        Returns:
            Dictionary with:
            - total_violations: Total number of violations
            - violations_by_type: Count by violation type
            - violations_by_node: Count by node
            - recent_violations: Last 10 violations
        """
        violations_by_type: dict[str, int] = {}
        violations_by_node: dict[str, int] = {}

        for violation in self._consistency_violations:
            violations_by_type[violation.violation_type] = (
                violations_by_type.get(violation.violation_type, 0) + 1
            )
            violations_by_node[violation.node_name] = (
                violations_by_node.get(violation.node_name, 0) + 1
            )

        return {
            "total_violations": len(self._consistency_violations),
            "violations_by_type": violations_by_type,
            "violations_by_node": violations_by_node,
            "recent_violations": [
                {
                    "node": v.node_name,
                    "type": v.violation_type,
                    "details": v.details,
                    "timestamp": v.timestamp,
                }
                for v in self._consistency_violations[-10:]
            ],
        }

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
        fault_types = [
            "tool_failure",
            "delay",
            "hallucination",
            "context_corruption",
            "budget_exhaustion",
        ]
        summary["faults_by_type"] = {ft: self.get_counter(f"faults_{ft}") for ft in fault_types}

        return summary

    def reset(self):
        """Reset all metrics."""
        self._series.clear()
        self._counters.clear()
        self._start_time = time.time()
        self._edge_traversals.clear()
        self._consistency_violations.clear()
        self._state_schemas.clear()
        self._init_standard_metrics()

    def export_prometheus(self) -> str:
        """Export metrics in Prometheus format."""
        lines = []

        # Export counters
        for name, value in self._counters.items():
            lines.append(f"balaganagent_{name} {value}")

        # Export series summaries
        for name, series in self._series.items():
            if series.count > 0:
                lines.append(f"balaganagent_{name}_count {series.count}")
                lines.append(f"balaganagent_{name}_mean {series.mean()}")
                lines.append(f"balaganagent_{name}_p50 {series.percentile(50)}")
                lines.append(f"balaganagent_{name}_p90 {series.percentile(90)}")
                lines.append(f"balaganagent_{name}_p99 {series.percentile(99)}")

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
