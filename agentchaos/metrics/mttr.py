"""Mean Time To Recovery (MTTR) calculation for AI agents."""

from dataclasses import dataclass, field
from typing import Any, Optional
import time
import statistics


@dataclass
class RecoveryEvent:
    """A single recovery event."""

    operation_name: str
    fault_type: str
    failure_time: float
    recovery_time: float
    recovery_method: str
    retries: int
    success: bool

    @property
    def time_to_recover(self) -> float:
        """Time from failure to recovery in seconds."""
        return self.recovery_time - self.failure_time


@dataclass
class FailureWindow:
    """A window of failure tracking."""

    start_time: float
    end_time: Optional[float] = None
    operations_during_failure: int = 0
    recovery_event: Optional[RecoveryEvent] = None

    @property
    def duration(self) -> float:
        if self.end_time is None:
            return time.time() - self.start_time
        return self.end_time - self.start_time

    @property
    def is_recovered(self) -> bool:
        return self.end_time is not None


class MTTRCalculator:
    """
    Calculates Mean Time To Recovery (MTTR) metrics for AI agents.

    MTTR is a key reliability metric that measures how quickly
    an agent can recover from failures.

    Tracks:
    - Time from fault injection to successful operation
    - Recovery patterns (retry, fallback, escalation)
    - Recovery success rates
    - Recovery time distributions
    """

    def __init__(self):
        self._recovery_events: list[RecoveryEvent] = []
        self._active_failures: dict[str, FailureWindow] = {}
        self._completed_windows: list[FailureWindow] = []

    def record_failure(
        self,
        operation_name: str,
        fault_type: str,
    ):
        """Record the start of a failure."""
        key = f"{operation_name}:{fault_type}"
        if key not in self._active_failures:
            self._active_failures[key] = FailureWindow(
                start_time=time.time(),
            )
        self._active_failures[key].operations_during_failure += 1

    def record_recovery(
        self,
        operation_name: str,
        fault_type: str,
        recovery_method: str = "retry",
        retries: int = 0,
        success: bool = True,
    ):
        """Record a recovery from failure."""
        key = f"{operation_name}:{fault_type}"
        now = time.time()

        # Find or create failure window
        if key in self._active_failures:
            window = self._active_failures[key]
            failure_time = window.start_time
        else:
            # Recovery without tracked failure (retroactive)
            failure_time = now - 1.0  # Assume 1 second ago

        event = RecoveryEvent(
            operation_name=operation_name,
            fault_type=fault_type,
            failure_time=failure_time,
            recovery_time=now,
            recovery_method=recovery_method,
            retries=retries,
            success=success,
        )

        self._recovery_events.append(event)

        # Close failure window
        if key in self._active_failures:
            window = self._active_failures[key]
            window.end_time = now
            window.recovery_event = event
            self._completed_windows.append(window)
            del self._active_failures[key]

    def calculate_mttr(self) -> float:
        """
        Calculate Mean Time To Recovery in seconds.

        Returns:
            MTTR in seconds, or 0 if no recoveries recorded.
        """
        if not self._recovery_events:
            return 0.0

        recovery_times = [e.time_to_recover for e in self._recovery_events if e.success]
        if not recovery_times:
            return 0.0

        return statistics.mean(recovery_times)

    def calculate_mttr_by_fault_type(self) -> dict[str, float]:
        """Calculate MTTR broken down by fault type."""
        by_type: dict[str, list[float]] = {}

        for event in self._recovery_events:
            if event.success:
                if event.fault_type not in by_type:
                    by_type[event.fault_type] = []
                by_type[event.fault_type].append(event.time_to_recover)

        return {
            fault_type: statistics.mean(times) if times else 0.0
            for fault_type, times in by_type.items()
        }

    def calculate_mttr_by_operation(self) -> dict[str, float]:
        """Calculate MTTR broken down by operation."""
        by_op: dict[str, list[float]] = {}

        for event in self._recovery_events:
            if event.success:
                if event.operation_name not in by_op:
                    by_op[event.operation_name] = []
                by_op[event.operation_name].append(event.time_to_recover)

        return {
            op: statistics.mean(times) if times else 0.0
            for op, times in by_op.items()
        }

    def calculate_mttr_percentiles(self) -> dict[str, float]:
        """Calculate MTTR percentiles."""
        recovery_times = sorted([
            e.time_to_recover for e in self._recovery_events if e.success
        ])

        if not recovery_times:
            return {"p50": 0.0, "p90": 0.0, "p95": 0.0, "p99": 0.0}

        def percentile(data: list[float], p: float) -> float:
            idx = int(len(data) * p / 100)
            return data[min(idx, len(data) - 1)]

        return {
            "p50": percentile(recovery_times, 50),
            "p90": percentile(recovery_times, 90),
            "p95": percentile(recovery_times, 95),
            "p99": percentile(recovery_times, 99),
        }

    def get_recovery_stats(self) -> dict[str, Any]:
        """Get comprehensive recovery statistics."""
        total_events = len(self._recovery_events)
        successful_events = sum(1 for e in self._recovery_events if e.success)
        failed_events = total_events - successful_events

        recovery_methods: dict[str, int] = {}
        total_retries = 0

        for event in self._recovery_events:
            method = event.recovery_method
            recovery_methods[method] = recovery_methods.get(method, 0) + 1
            total_retries += event.retries

        return {
            "total_recoveries": total_events,
            "successful_recoveries": successful_events,
            "failed_recoveries": failed_events,
            "recovery_rate": successful_events / total_events if total_events > 0 else 0,
            "mttr_seconds": self.calculate_mttr(),
            "mttr_percentiles": self.calculate_mttr_percentiles(),
            "mttr_by_fault_type": self.calculate_mttr_by_fault_type(),
            "mttr_by_operation": self.calculate_mttr_by_operation(),
            "recovery_methods": recovery_methods,
            "total_retries": total_retries,
            "avg_retries_per_recovery": total_retries / total_events if total_events > 0 else 0,
            "active_failures": len(self._active_failures),
        }

    def get_active_failures(self) -> list[dict[str, Any]]:
        """Get currently active (unrecovered) failures."""
        return [
            {
                "key": key,
                "duration_seconds": window.duration,
                "operations_affected": window.operations_during_failure,
            }
            for key, window in self._active_failures.items()
        ]

    def get_recovery_timeline(self) -> list[dict[str, Any]]:
        """Get timeline of recovery events."""
        return [
            {
                "operation": event.operation_name,
                "fault_type": event.fault_type,
                "failure_time": event.failure_time,
                "recovery_time": event.recovery_time,
                "time_to_recover": event.time_to_recover,
                "method": event.recovery_method,
                "retries": event.retries,
                "success": event.success,
            }
            for event in sorted(self._recovery_events, key=lambda e: e.recovery_time)
        ]

    def reset(self):
        """Reset all tracked data."""
        self._recovery_events.clear()
        self._active_failures.clear()
        self._completed_windows.clear()
