"""Budget exhaustion injection for chaos testing AI agents."""

import time
from dataclasses import dataclass
from enum import Enum
from typing import Any, Optional

from .base import BaseInjector, FaultType, InjectorConfig


class BudgetType(Enum):
    """Types of budget constraints."""

    TOKEN_LIMIT = "token_limit"  # Token/API call limits
    TIME_LIMIT = "time_limit"  # Time-based limits
    COST_LIMIT = "cost_limit"  # Cost-based limits
    CALL_LIMIT = "call_limit"  # Number of calls
    RATE_LIMIT = "rate_limit"  # Rate limiting
    MEMORY_LIMIT = "memory_limit"  # Memory constraints
    CONCURRENT_LIMIT = "concurrent_limit"  # Concurrent operation limits


class BudgetExhaustedException(Exception):
    """Raised when a budget limit is exceeded."""

    def __init__(self, budget_type: BudgetType, current: float, limit: float, message: str):
        super().__init__(message)
        self.budget_type = budget_type
        self.current = current
        self.limit = limit


@dataclass
class BudgetConstraint:
    """A single budget constraint."""

    budget_type: BudgetType
    limit: float
    current: float = 0.0
    soft_limit_ratio: float = 0.8  # Warn at 80% by default

    @property
    def remaining(self) -> float:
        return max(0, self.limit - self.current)

    @property
    def usage_ratio(self) -> float:
        return self.current / self.limit if self.limit > 0 else 1.0

    @property
    def is_soft_limit_exceeded(self) -> bool:
        return self.usage_ratio >= self.soft_limit_ratio

    @property
    def is_exhausted(self) -> bool:
        return self.current >= self.limit

    def consume(self, amount: float) -> bool:
        """Consume budget. Returns True if successful, False if would exceed."""
        if self.current + amount > self.limit:
            return False
        self.current += amount
        return True


@dataclass
class BudgetExhaustionConfig(InjectorConfig):
    """Configuration for budget exhaustion injection."""

    # Budget limits to simulate
    token_limit: Optional[int] = 10000
    time_limit_seconds: Optional[float] = 60.0
    cost_limit_dollars: Optional[float] = 1.0
    call_limit: Optional[int] = 100
    rate_limit_per_minute: Optional[int] = 60
    memory_limit_mb: Optional[int] = 512
    concurrent_limit: Optional[int] = 5

    # Behavior settings
    fail_hard: bool = True  # Raise exception vs return error
    gradual_degradation: bool = False  # Slow down as limits approach
    warning_threshold: float = 0.8  # Warn at 80% usage

    # Cost simulation
    cost_per_token: float = 0.00001  # $0.01 per 1000 tokens
    cost_per_call: float = 0.001  # $0.001 per call

    # Token estimation
    tokens_per_char: float = 0.25  # Rough estimate


class BudgetExhaustionInjector(BaseInjector):
    """Injects budget exhaustion scenarios to test agent resource management."""

    def __init__(self, config: Optional[BudgetExhaustionConfig] = None):
        super().__init__(config or BudgetExhaustionConfig())
        self.config: BudgetExhaustionConfig = self.config

        self._constraints: dict[BudgetType, BudgetConstraint] = {}
        self._start_time = time.time()
        self._call_timestamps: list[float] = []
        self._concurrent_calls = 0

        self._initialize_constraints()

    def _initialize_constraints(self):
        """Initialize budget constraints from config."""
        if self.config.token_limit:
            self._constraints[BudgetType.TOKEN_LIMIT] = BudgetConstraint(
                BudgetType.TOKEN_LIMIT, self.config.token_limit
            )

        if self.config.time_limit_seconds:
            self._constraints[BudgetType.TIME_LIMIT] = BudgetConstraint(
                BudgetType.TIME_LIMIT, self.config.time_limit_seconds
            )

        if self.config.cost_limit_dollars:
            self._constraints[BudgetType.COST_LIMIT] = BudgetConstraint(
                BudgetType.COST_LIMIT, self.config.cost_limit_dollars
            )

        if self.config.call_limit:
            self._constraints[BudgetType.CALL_LIMIT] = BudgetConstraint(
                BudgetType.CALL_LIMIT, self.config.call_limit
            )

        if self.config.rate_limit_per_minute:
            self._constraints[BudgetType.RATE_LIMIT] = BudgetConstraint(
                BudgetType.RATE_LIMIT, self.config.rate_limit_per_minute
            )

        if self.config.memory_limit_mb:
            self._constraints[BudgetType.MEMORY_LIMIT] = BudgetConstraint(
                BudgetType.MEMORY_LIMIT, self.config.memory_limit_mb
            )

        if self.config.concurrent_limit:
            self._constraints[BudgetType.CONCURRENT_LIMIT] = BudgetConstraint(
                BudgetType.CONCURRENT_LIMIT, self.config.concurrent_limit
            )

    @property
    def fault_type(self) -> FaultType:
        return FaultType.BUDGET_EXHAUSTION

    def _estimate_tokens(self, data: Any) -> int:
        """Estimate token count for data."""
        text = str(data)
        return int(len(text) * self.config.tokens_per_char)

    def _get_rate_limit_usage(self) -> int:
        """Get number of calls in the last minute."""
        now = time.time()
        minute_ago = now - 60
        # Clean old timestamps
        self._call_timestamps = [t for t in self._call_timestamps if t > minute_ago]
        return len(self._call_timestamps)

    def _check_constraint(self, constraint: BudgetConstraint, amount: float) -> tuple[bool, str]:
        """Check if a constraint would be exceeded."""
        if constraint.current + amount > constraint.limit:
            return False, f"{constraint.budget_type.value} exceeded: {constraint.current + amount:.2f} > {constraint.limit:.2f}"
        return True, ""

    def get_budget_status(self) -> dict[str, Any]:
        """Get current budget status for all constraints."""
        status = {}

        for budget_type, constraint in self._constraints.items():
            # Update time constraint
            if budget_type == BudgetType.TIME_LIMIT:
                constraint.current = time.time() - self._start_time
            elif budget_type == BudgetType.RATE_LIMIT:
                constraint.current = self._get_rate_limit_usage()
            elif budget_type == BudgetType.CONCURRENT_LIMIT:
                constraint.current = self._concurrent_calls

            status[budget_type.value] = {
                "current": constraint.current,
                "limit": constraint.limit,
                "remaining": constraint.remaining,
                "usage_ratio": constraint.usage_ratio,
                "is_warning": constraint.is_soft_limit_exceeded,
                "is_exhausted": constraint.is_exhausted,
            }

        return status

    def inject(self, target: str, context: dict[str, Any]) -> tuple[Any, dict[str, Any]]:
        """Check and potentially exhaust budgets."""
        violations = []
        warnings = []

        data = context.get("data", context.get("input", ""))
        estimated_tokens = self._estimate_tokens(data)
        estimated_cost = (
            estimated_tokens * self.config.cost_per_token +
            self.config.cost_per_call
        )

        # Update and check each constraint
        for budget_type, constraint in self._constraints.items():
            # Update current values
            if budget_type == BudgetType.TOKEN_LIMIT:
                ok, msg = self._check_constraint(constraint, estimated_tokens)
                if ok:
                    constraint.consume(estimated_tokens)
                else:
                    violations.append((budget_type, msg))

            elif budget_type == BudgetType.TIME_LIMIT:
                constraint.current = time.time() - self._start_time
                if constraint.is_exhausted:
                    violations.append((budget_type, f"Time limit exceeded: {constraint.current:.1f}s"))

            elif budget_type == BudgetType.COST_LIMIT:
                ok, msg = self._check_constraint(constraint, estimated_cost)
                if ok:
                    constraint.consume(estimated_cost)
                else:
                    violations.append((budget_type, msg))

            elif budget_type == BudgetType.CALL_LIMIT:
                ok, msg = self._check_constraint(constraint, 1)
                if ok:
                    constraint.consume(1)
                else:
                    violations.append((budget_type, msg))

            elif budget_type == BudgetType.RATE_LIMIT:
                constraint.current = self._get_rate_limit_usage()
                if constraint.current >= constraint.limit:
                    violations.append((budget_type, f"Rate limit exceeded: {constraint.current}/min"))
                else:
                    self._call_timestamps.append(time.time())

            # Check for warnings
            if constraint.is_soft_limit_exceeded and not constraint.is_exhausted:
                warnings.append(f"{budget_type.value} at {constraint.usage_ratio:.0%}")

        details = {
            "tool_name": target,
            "estimated_tokens": estimated_tokens,
            "estimated_cost": estimated_cost,
            "budget_status": self.get_budget_status(),
            "warnings": warnings,
            "violations": [v[1] for v in violations],
        }

        self.record_injection(target, details)

        # Handle violations
        if violations:
            budget_type, message = violations[0]

            if self.config.fail_hard:
                raise BudgetExhaustedException(
                    budget_type,
                    self._constraints[budget_type].current,
                    self._constraints[budget_type].limit,
                    message,
                )

            return {
                "error": "budget_exhausted",
                "budget_type": budget_type.value,
                "message": message,
                "status": details["budget_status"],
            }, details

        # Apply gradual degradation if enabled
        if self.config.gradual_degradation:
            max_ratio = max(c.usage_ratio for c in self._constraints.values())
            if max_ratio > 0.5:
                # Simulate slowdown
                delay = (max_ratio - 0.5) * 2  # 0-1 second delay
                time.sleep(delay)
                details["degradation_delay"] = delay

        return None, details  # No error, proceed normally

    def reset(self):
        """Reset all budget constraints."""
        super().reset()
        self._start_time = time.time()
        self._call_timestamps.clear()
        self._concurrent_calls = 0
        self._initialize_constraints()


class BudgetTracker:
    """Utility class for tracking budgets across an experiment."""

    def __init__(self):
        self._budgets: dict[str, BudgetConstraint] = {}
        self._history: list[dict[str, Any]] = []

    def add_budget(self, name: str, budget_type: BudgetType, limit: float):
        """Add a budget to track."""
        self._budgets[name] = BudgetConstraint(budget_type, limit)

    def consume(self, name: str, amount: float) -> bool:
        """Consume from a budget."""
        if name not in self._budgets:
            return True

        budget = self._budgets[name]
        success = budget.consume(amount)

        self._history.append({
            "budget": name,
            "amount": amount,
            "success": success,
            "current": budget.current,
            "remaining": budget.remaining,
            "timestamp": time.time(),
        })

        return success

    def get_summary(self) -> dict[str, Any]:
        """Get summary of all budgets."""
        return {
            name: {
                "type": budget.budget_type.value,
                "limit": budget.limit,
                "current": budget.current,
                "remaining": budget.remaining,
                "usage_ratio": budget.usage_ratio,
                "exhausted": budget.is_exhausted,
            }
            for name, budget in self._budgets.items()
        }
