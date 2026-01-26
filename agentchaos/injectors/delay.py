"""Delay injection for chaos testing."""

import asyncio
import time
from dataclasses import dataclass
from enum import Enum
from typing import Any, Optional

from .base import BaseInjector, FaultType, InjectorConfig


class DelayPattern(Enum):
    """Patterns for injecting delays."""

    FIXED = "fixed"  # Constant delay
    UNIFORM = "uniform"  # Uniform random between min and max
    EXPONENTIAL = "exponential"  # Exponential distribution
    SPIKE = "spike"  # Occasional large spikes
    DEGRADING = "degrading"  # Gradually increasing delays
    JITTER = "jitter"  # Small random variations


@dataclass
class DelayConfig(InjectorConfig):
    """Configuration for delay injection."""

    pattern: DelayPattern = DelayPattern.UNIFORM
    min_delay_ms: float = 100.0  # Minimum delay in milliseconds
    max_delay_ms: float = 5000.0  # Maximum delay in milliseconds
    spike_multiplier: float = 10.0  # Multiplier for spike delays
    spike_probability: float = 0.1  # Probability of spike when using SPIKE pattern
    degradation_factor: float = 1.1  # Factor for degrading delays
    jitter_percent: float = 20.0  # Percentage jitter to add

    def __post_init__(self):
        super().__post_init__()
        if self.min_delay_ms < 0:
            raise ValueError("min_delay_ms must be non-negative")
        if self.max_delay_ms < self.min_delay_ms:
            raise ValueError("max_delay_ms must be >= min_delay_ms")


class DelayInjector(BaseInjector):
    """Injects delays into tool calls to simulate latency."""

    def __init__(self, config: Optional[DelayConfig] = None):
        super().__init__(config or DelayConfig())
        self.config: DelayConfig = self.config
        self._degradation_level = 1.0

    @property
    def fault_type(self) -> FaultType:
        return FaultType.DELAY

    def _calculate_delay(self) -> float:
        """Calculate delay in milliseconds based on pattern."""
        pattern = self.config.pattern
        min_ms = self.config.min_delay_ms
        max_ms = self.config.max_delay_ms

        if pattern == DelayPattern.FIXED:
            delay = min_ms

        elif pattern == DelayPattern.UNIFORM:
            delay = self._rng.uniform(min_ms, max_ms)

        elif pattern == DelayPattern.EXPONENTIAL:
            # Exponential with mean at midpoint
            mean = (min_ms + max_ms) / 2
            delay = min(self._rng.expovariate(1 / mean), max_ms)
            delay = max(delay, min_ms)

        elif pattern == DelayPattern.SPIKE:
            if self._rng.random() < self.config.spike_probability:
                # Spike: multiply by spike_multiplier
                base_delay = self._rng.uniform(min_ms, max_ms)
                delay = min(base_delay * self.config.spike_multiplier, max_ms * self.config.spike_multiplier)
            else:
                delay = self._rng.uniform(min_ms, max_ms / 2)

        elif pattern == DelayPattern.DEGRADING:
            # Each call increases delay
            base_delay = self._rng.uniform(min_ms, max_ms)
            delay = base_delay * self._degradation_level
            self._degradation_level *= self.config.degradation_factor

        elif pattern == DelayPattern.JITTER:
            # Base delay with random jitter
            base_delay = (min_ms + max_ms) / 2
            jitter_range = base_delay * (self.config.jitter_percent / 100)
            delay = base_delay + self._rng.uniform(-jitter_range, jitter_range)
            delay = max(min_ms, min(delay, max_ms))

        else:
            delay = min_ms

        return delay

    def inject(self, target: str, context: dict[str, Any]) -> tuple[float, dict[str, Any]]:
        """
        Inject a delay.

        Returns:
            Tuple of (delay_ms, details)
        """
        delay_ms = self._calculate_delay()

        details = {
            "delay_ms": delay_ms,
            "pattern": self.config.pattern.value,
            "tool_name": target,
        }

        self.record_injection(target, details)

        # Actually apply the delay
        time.sleep(delay_ms / 1000.0)

        return delay_ms, details

    async def inject_async(self, target: str, context: dict[str, Any]) -> tuple[float, dict[str, Any]]:
        """Async version of inject."""
        delay_ms = self._calculate_delay()

        details = {
            "delay_ms": delay_ms,
            "pattern": self.config.pattern.value,
            "tool_name": target,
        }

        self.record_injection(target, details)

        await asyncio.sleep(delay_ms / 1000.0)

        return delay_ms, details

    def reset(self):
        """Reset injector state including degradation level."""
        super().reset()
        self._degradation_level = 1.0


class LatencySimulator:
    """
    Simulates realistic network latency patterns.

    Can be used to simulate various network conditions:
    - Good network: low latency, low jitter
    - Poor network: high latency, high jitter
    - Degrading network: increasing latency over time
    - Intermittent issues: occasional spikes
    """

    PRESETS = {
        "good": DelayConfig(
            pattern=DelayPattern.JITTER,
            min_delay_ms=10,
            max_delay_ms=50,
            jitter_percent=10,
            probability=1.0,
        ),
        "moderate": DelayConfig(
            pattern=DelayPattern.UNIFORM,
            min_delay_ms=50,
            max_delay_ms=200,
            probability=1.0,
        ),
        "poor": DelayConfig(
            pattern=DelayPattern.UNIFORM,
            min_delay_ms=200,
            max_delay_ms=2000,
            probability=1.0,
        ),
        "degrading": DelayConfig(
            pattern=DelayPattern.DEGRADING,
            min_delay_ms=50,
            max_delay_ms=500,
            degradation_factor=1.2,
            probability=1.0,
        ),
        "spiky": DelayConfig(
            pattern=DelayPattern.SPIKE,
            min_delay_ms=20,
            max_delay_ms=100,
            spike_multiplier=20,
            spike_probability=0.15,
            probability=1.0,
        ),
    }

    @classmethod
    def create(cls, preset: str) -> DelayInjector:
        """Create a delay injector from a preset."""
        if preset not in cls.PRESETS:
            raise ValueError(f"Unknown preset: {preset}. Available: {list(cls.PRESETS.keys())}")
        return DelayInjector(cls.PRESETS[preset])
