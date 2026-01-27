"""Experiment definitions for chaos engineering."""

import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional


class ExperimentStatus(Enum):
    """Status of an experiment."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    ABORTED = "aborted"


@dataclass
class ExperimentConfig:
    """Configuration for a chaos experiment."""

    name: str
    description: str = ""

    # Duration settings
    duration_seconds: Optional[float] = None  # None = run until completion
    max_iterations: Optional[int] = None

    # Fault injection settings
    enable_tool_failures: bool = True
    enable_delays: bool = True
    enable_hallucinations: bool = True
    enable_context_corruption: bool = True
    enable_budget_exhaustion: bool = True

    # Global probability multiplier
    chaos_level: float = 1.0  # 0.0 = no chaos, 1.0 = normal, 2.0 = double

    # Recovery settings
    allow_retries: bool = True
    max_retries: int = 3
    retry_delay_seconds: float = 1.0

    # Abort conditions
    abort_on_critical_failure: bool = True
    max_consecutive_failures: int = 5

    # Seed for reproducibility
    seed: Optional[int] = None

    # Custom metadata
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class ExperimentEvent:
    """A single event in an experiment."""

    timestamp: float
    event_type: str
    details: dict[str, Any]
    experiment_id: str

    @classmethod
    def create(cls, event_type: str, details: dict[str, Any], experiment_id: str) -> "ExperimentEvent":
        return cls(
            timestamp=time.time(),
            event_type=event_type,
            details=details,
            experiment_id=experiment_id,
        )


@dataclass
class ExperimentResult:
    """Results from a completed experiment."""

    experiment_id: str
    config: ExperimentConfig
    status: ExperimentStatus

    # Timing
    start_time: float
    end_time: float

    # Counts
    total_operations: int
    successful_operations: int
    failed_operations: int
    recovered_operations: int

    # Fault injection stats
    faults_injected: int
    faults_by_type: dict[str, int]

    # Events
    events: list[ExperimentEvent]

    # Raw metrics for analysis
    metrics: dict[str, Any]

    # Error information
    errors: list[dict[str, Any]]

    @property
    def duration_seconds(self) -> float:
        return self.end_time - self.start_time

    @property
    def success_rate(self) -> float:
        if self.total_operations == 0:
            return 0.0
        return self.successful_operations / self.total_operations

    @property
    def recovery_rate(self) -> float:
        if self.failed_operations == 0:
            return 1.0
        return self.recovered_operations / self.failed_operations

    def to_dict(self) -> dict[str, Any]:
        return {
            "experiment_id": self.experiment_id,
            "config": {
                "name": self.config.name,
                "description": self.config.description,
                "chaos_level": self.config.chaos_level,
            },
            "status": self.status.value,
            "duration_seconds": self.duration_seconds,
            "total_operations": self.total_operations,
            "successful_operations": self.successful_operations,
            "failed_operations": self.failed_operations,
            "recovered_operations": self.recovered_operations,
            "success_rate": self.success_rate,
            "recovery_rate": self.recovery_rate,
            "faults_injected": self.faults_injected,
            "faults_by_type": self.faults_by_type,
            "metrics": self.metrics,
            "errors": self.errors,
        }


class Experiment:
    """
    A chaos experiment that tests an agent's resilience.

    Usage:
        experiment = Experiment(config)
        experiment.start()

        # Run agent operations
        with experiment.operation("tool_call") as op:
            result = agent.call_tool(...)
            op.record_result(result)

        result = experiment.complete()
    """

    def __init__(self, config: ExperimentConfig):
        self.config = config
        self.id = str(uuid.uuid4())[:8]
        self.status = ExperimentStatus.PENDING

        self._start_time: Optional[float] = None
        self._end_time: Optional[float] = None
        self._events: list[ExperimentEvent] = []
        self._operations: list[dict[str, Any]] = []
        self._errors: list[dict[str, Any]] = []
        self._consecutive_failures = 0
        self._cached_result: Optional[ExperimentResult] = None

        # Metrics accumulators
        self._metrics: dict[str, list[float]] = {
            "operation_durations": [],
            "recovery_times": [],
            "retry_counts": [],
        }

    def start(self):
        """Start the experiment."""
        if self.status != ExperimentStatus.PENDING:
            raise RuntimeError(f"Cannot start experiment in status {self.status}")

        self.status = ExperimentStatus.RUNNING
        self._start_time = time.time()

        self._record_event("experiment_started", {
            "config_name": self.config.name,
            "chaos_level": self.config.chaos_level,
        })

    def operation(self, name: str) -> "OperationContext":
        """Create an operation context for tracking."""
        return OperationContext(self, name)

    def record_operation(
        self,
        name: str,
        success: bool,
        duration: float,
        retries: int = 0,
        recovered: bool = False,
        fault_injected: Optional[str] = None,
        error: Optional[str] = None,
    ):
        """Record an operation result."""
        operation = {
            "name": name,
            "success": success,
            "duration": duration,
            "retries": retries,
            "recovered": recovered,
            "fault_injected": fault_injected,
            "error": error,
            "timestamp": time.time(),
        }
        self._operations.append(operation)
        self._metrics["operation_durations"].append(duration)

        if retries > 0:
            self._metrics["retry_counts"].append(retries)

        if success:
            self._consecutive_failures = 0
        else:
            self._consecutive_failures += 1
            if error:
                self._errors.append({
                    "operation": name,
                    "error": error,
                    "timestamp": time.time(),
                })

        # Check abort conditions
        if (self.config.abort_on_critical_failure and
            self._consecutive_failures >= self.config.max_consecutive_failures):
            self.abort(f"Too many consecutive failures: {self._consecutive_failures}")

        self._record_event("operation_completed", operation)

    def record_recovery(self, operation_name: str, recovery_time: float):
        """Record a recovery event."""
        self._metrics["recovery_times"].append(recovery_time)
        self._record_event("recovery", {
            "operation": operation_name,
            "recovery_time": recovery_time,
        })

    def abort(self, reason: str):
        """Abort the experiment."""
        self.status = ExperimentStatus.ABORTED
        self._end_time = time.time()
        self._record_event("experiment_aborted", {"reason": reason})

    def complete(self) -> ExperimentResult:
        """Complete the experiment and return results."""
        # Return cached result if already completed
        if self._cached_result is not None:
            return self._cached_result

        if self.status == ExperimentStatus.ABORTED:
            pass  # Already ended
        elif self.status != ExperimentStatus.RUNNING:
            raise RuntimeError(f"Cannot complete experiment in status {self.status}")
        else:
            self.status = ExperimentStatus.COMPLETED
            self._end_time = time.time()
            self._record_event("experiment_completed", {})

        # Calculate results
        total = len(self._operations)
        successful = sum(1 for op in self._operations if op["success"])
        failed = total - successful
        recovered = sum(1 for op in self._operations if op.get("recovered"))

        faults_by_type: dict[str, int] = {}
        for op in self._operations:
            if op.get("fault_injected"):
                fault_type = op["fault_injected"]
                faults_by_type[fault_type] = faults_by_type.get(fault_type, 0) + 1

        result = ExperimentResult(
            experiment_id=self.id,
            config=self.config,
            status=self.status,
            start_time=self._start_time or 0,
            end_time=self._end_time or time.time(),
            total_operations=total,
            successful_operations=successful,
            failed_operations=failed,
            recovered_operations=recovered,
            faults_injected=sum(faults_by_type.values()),
            faults_by_type=faults_by_type,
            events=self._events.copy(),
            metrics=dict(self._metrics),
            errors=self._errors.copy(),
        )
        self._cached_result = result
        return result

    def _record_event(self, event_type: str, details: dict[str, Any]):
        """Record an event."""
        event = ExperimentEvent.create(event_type, details, self.id)
        self._events.append(event)

    def should_continue(self) -> bool:
        """Check if experiment should continue."""
        if self.status != ExperimentStatus.RUNNING:
            return False

        if self.config.duration_seconds:
            elapsed = time.time() - (self._start_time or 0)
            if elapsed >= self.config.duration_seconds:
                return False

        if self.config.max_iterations:
            if len(self._operations) >= self.config.max_iterations:
                return False

        return True


class OperationContext:
    """Context manager for tracking individual operations."""

    def __init__(self, experiment: Experiment, name: str):
        self.experiment = experiment
        self.name = name
        self._start_time: Optional[float] = None
        self._success = True
        self._retries = 0
        self._recovered = False
        self._fault_injected: Optional[str] = None
        self._error: Optional[str] = None

    def __enter__(self) -> "OperationContext":
        self._start_time = time.time()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        duration = time.time() - (self._start_time or 0)

        if exc_type is not None:
            self._success = False
            self._error = str(exc_val)

        self.experiment.record_operation(
            name=self.name,
            success=self._success,
            duration=duration,
            retries=self._retries,
            recovered=self._recovered,
            fault_injected=self._fault_injected,
            error=self._error,
        )

        # Don't suppress exceptions
        return False

    def record_fault(self, fault_type: str):
        """Record that a fault was injected."""
        self._fault_injected = fault_type

    def record_retry(self):
        """Record a retry attempt."""
        self._retries += 1

    def record_recovery(self):
        """Record successful recovery."""
        self._recovered = True
        recovery_time = time.time() - (self._start_time or 0)
        self.experiment.record_recovery(self.name, recovery_time)

    def record_failure(self, error: str):
        """Record a failure."""
        self._success = False
        self._error = error

    def record_success(self):
        """Record success."""
        self._success = True
