"""Base classes for fault injectors."""

import random
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional


class FaultType(Enum):
    """Types of faults that can be injected."""
    TOOL_FAILURE = "tool_failure"
    DELAY = "delay"
    HALLUCINATION = "hallucination"
    CONTEXT_CORRUPTION = "context_corruption"
    BUDGET_EXHAUSTION = "budget_exhaustion"


@dataclass
class InjectorConfig:
    """Configuration for a fault injector."""

    enabled: bool = True
    probability: float = 0.1  # 10% chance by default
    seed: Optional[int] = None
    target_tools: list[str] = field(default_factory=list)  # Empty = all tools
    exclude_tools: list[str] = field(default_factory=list)
    max_injections: Optional[int] = None  # None = unlimited
    cooldown_seconds: float = 0.0  # Minimum time between injections

    def __post_init__(self):
        if not 0.0 <= self.probability <= 1.0:
            raise ValueError("Probability must be between 0.0 and 1.0")


@dataclass
class InjectionEvent:
    """Record of a fault injection event."""

    fault_type: FaultType
    timestamp: float
    target: str
    details: dict[str, Any]
    injector_id: str


class BaseInjector(ABC):
    """Abstract base class for all fault injectors."""

    def __init__(self, config: Optional[InjectorConfig] = None):
        self.config = config or InjectorConfig()
        self._rng = random.Random(self.config.seed)
        self._injection_count = 0
        self._last_injection_time = 0.0
        self._events: list[InjectionEvent] = []
        self._id = f"{self.fault_type.value}_{id(self)}"

    @property
    @abstractmethod
    def fault_type(self) -> FaultType:
        """The type of fault this injector produces."""
        pass

    @abstractmethod
    def inject(self, target: str, context: dict[str, Any]) -> tuple[Any, dict[str, Any]]:
        """
        Inject a fault into the target.

        Args:
            target: The target to inject fault into (e.g., tool name)
            context: Current execution context

        Returns:
            Tuple of (modified_result, injection_details)
        """
        pass

    def should_inject(self, target: str) -> bool:
        """Determine if a fault should be injected."""
        if not self.config.enabled:
            return False

        # Check max injections limit
        if (self.config.max_injections is not None and
            self._injection_count >= self.config.max_injections):
            return False

        # Check cooldown
        current_time = time.time()
        if current_time - self._last_injection_time < self.config.cooldown_seconds:
            return False

        # Check target filters
        if self.config.target_tools and target not in self.config.target_tools:
            return False
        if target in self.config.exclude_tools:
            return False

        # Random probability check
        return self._rng.random() < self.config.probability

    def record_injection(self, target: str, details: dict[str, Any]) -> InjectionEvent:
        """Record an injection event."""
        event = InjectionEvent(
            fault_type=self.fault_type,
            timestamp=time.time(),
            target=target,
            details=details,
            injector_id=self._id,
        )
        self._events.append(event)
        self._injection_count += 1
        self._last_injection_time = event.timestamp
        return event

    def get_events(self) -> list[InjectionEvent]:
        """Get all injection events."""
        return self._events.copy()

    def reset(self):
        """Reset injector state."""
        self._injection_count = 0
        self._last_injection_time = 0.0
        self._events.clear()
        if self.config.seed is not None:
            self._rng.seed(self.config.seed)


class CompositeInjector(BaseInjector):
    """Combines multiple injectors into one."""

    def __init__(self, injectors: list[BaseInjector]):
        super().__init__()
        self.injectors = injectors

    @property
    def fault_type(self) -> FaultType:
        return FaultType.TOOL_FAILURE  # Default, but composite can have any

    def inject(self, target: str, context: dict[str, Any]) -> tuple[Any, dict[str, Any]]:
        """Inject faults from all child injectors that trigger."""
        results = []
        combined_details = {"injectors": []}

        for injector in self.injectors:
            if injector.should_inject(target):
                result, details = injector.inject(target, context)
                results.append(result)
                combined_details["injectors"].append({
                    "type": injector.fault_type.value,
                    "details": details,
                })

        return results[-1] if results else None, combined_details

    def should_inject(self, target: str) -> bool:
        """Check if any child injector should inject."""
        return any(inj.should_inject(target) for inj in self.injectors)

    def get_events(self) -> list[InjectionEvent]:
        """Get events from all child injectors."""
        events = []
        for injector in self.injectors:
            events.extend(injector.get_events())
        return sorted(events, key=lambda e: e.timestamp)

    def reset(self):
        """Reset all child injectors."""
        super().reset()
        for injector in self.injectors:
            injector.reset()
