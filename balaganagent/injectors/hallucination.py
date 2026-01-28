"""Hallucination injection for chaos testing AI agents."""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional

from .base import BaseInjector, FaultType, InjectorConfig


class HallucinationType(Enum):
    """Types of hallucinations to inject."""

    WRONG_VALUE = "wrong_value"  # Replace values with incorrect ones
    FABRICATED_DATA = "fabricated_data"  # Add fake data
    CONTRADICTORY = "contradictory"  # Add contradicting information
    CONFIDENT_WRONG = "confident_wrong"  # Confidently wrong statements
    PARTIAL_TRUTH = "partial_truth"  # Mix correct and incorrect
    OUTDATED = "outdated"  # Inject outdated information
    NONEXISTENT_REFERENCE = "nonexistent_reference"  # Reference things that don't exist


@dataclass
class HallucinationConfig(InjectorConfig):
    """Configuration for hallucination injection."""

    hallucination_types: list[HallucinationType] = field(
        default_factory=lambda: list(HallucinationType)
    )
    severity: float = 0.5  # 0.0 = subtle, 1.0 = obvious
    preserve_structure: bool = True  # Keep data structure, just corrupt values

    # Templates for different hallucination types
    fabricated_templates: list[str] = field(
        default_factory=lambda: [
            "According to internal documentation, {claim}",
            "The system reports that {claim}",
            "Based on the data, {claim}",
        ]
    )

    contradictory_templates: list[str] = field(
        default_factory=lambda: [
            "However, {contradiction}",
            "Note that {contradiction}",
            "Actually, {contradiction}",
        ]
    )

    # Fake data pools
    fake_names: list[str] = field(
        default_factory=lambda: [
            "John Smith",
            "Jane Doe",
            "Alex Johnson",
            "Sam Wilson",
            "Chris Lee",
            "Morgan Chen",
            "Taylor Kim",
            "Jordan Park",
        ]
    )

    fake_numbers: list[int] = field(
        default_factory=lambda: [
            42,
            1337,
            9999,
            404,
            500,
            123,
            777,
            888,
            999,
            100,
        ]
    )

    fake_urls: list[str] = field(
        default_factory=lambda: [
            "https://example.com/fake-resource",
            "https://docs.example.org/nonexistent",
            "https://api.fake-service.io/v2/data",
        ]
    )


class HallucinationInjector(BaseInjector):
    """Injects hallucinations into agent responses and tool outputs."""

    def __init__(self, config: Optional[HallucinationConfig] = None):
        super().__init__(config or HallucinationConfig())
        self.config: HallucinationConfig = self.config

    @property
    def fault_type(self) -> FaultType:
        return FaultType.HALLUCINATION

    def _select_hallucination_type(self) -> HallucinationType:
        """Select a hallucination type."""
        return self._rng.choice(self.config.hallucination_types)

    def _corrupt_string(self, value: str) -> str:
        """Corrupt a string value."""
        if not value:
            return self._rng.choice(self.config.fake_names)

        # Various corruption strategies based on severity
        if self._rng.random() < self.config.severity:
            # Complete replacement
            if value.isdigit():
                return str(self._rng.choice(self.config.fake_numbers))
            elif "@" in value:
                name = self._rng.choice(self.config.fake_names).lower().replace(" ", ".")
                return f"{name}@example.com"
            elif value.startswith("http"):
                return self._rng.choice(self.config.fake_urls)
            else:
                return self._rng.choice(self.config.fake_names)
        else:
            # Subtle corruption
            if len(value) > 3:
                # Swap some characters
                chars = list(value)
                idx = self._rng.randint(0, len(chars) - 1)
                chars[idx] = self._rng.choice("abcdefghijklmnopqrstuvwxyz0123456789")
                return "".join(chars)
            return value + "_corrupted"

    def _corrupt_number(self, value: float) -> float:
        """Corrupt a numeric value."""
        if self._rng.random() < self.config.severity:
            # Major corruption
            return float(self._rng.choice(self.config.fake_numbers))
        else:
            # Subtle corruption - off by some factor
            factor = self._rng.uniform(0.5, 2.0)
            return value * factor

    def _corrupt_value(self, value: Any) -> Any:
        """Corrupt any value based on its type."""
        if value is None:
            return self._rng.choice([None, "", 0, False, "N/A"])
        elif isinstance(value, bool):
            return not value if self._rng.random() < self.config.severity else value
        elif isinstance(value, int):
            return int(self._corrupt_number(value))
        elif isinstance(value, float):
            return self._corrupt_number(value)
        elif isinstance(value, str):
            return self._corrupt_string(value)
        elif isinstance(value, list):
            if self.config.preserve_structure:
                return [self._corrupt_value(item) for item in value]
            else:
                # Add or remove items
                corrupted = [self._corrupt_value(item) for item in value]
                if self._rng.random() < 0.3:
                    corrupted.append(self._rng.choice(self.config.fake_names))
                return corrupted
        elif isinstance(value, dict):
            return self._corrupt_dict(value)
        return value

    def _corrupt_dict(self, data: dict) -> dict:
        """Corrupt a dictionary."""
        corrupted = {}

        for key, value in data.items():
            if self._rng.random() < self.config.probability:
                corrupted[key] = self._corrupt_value(value)
            else:
                corrupted[key] = value

        # Possibly add fabricated fields
        if not self.config.preserve_structure and self._rng.random() < self.config.severity * 0.5:
            fake_keys = ["internal_id", "legacy_value", "cached_result", "temp_data"]
            corrupted[self._rng.choice(fake_keys)] = self._rng.choice(self.config.fake_numbers)

        return corrupted

    def _inject_wrong_value(self, data: Any) -> Any:
        """Replace values with incorrect ones."""
        return self._corrupt_value(data)

    def _inject_fabricated_data(self, data: Any) -> dict:
        """Add fabricated data to the response."""
        if isinstance(data, dict):
            data = data.copy()
            data["_fabricated"] = {
                "source": self._rng.choice(self.config.fake_urls),
                "confidence": round(self._rng.uniform(0.8, 0.99), 2),
                "verified": True,  # Falsely claims verification
                "additional_info": self._rng.choice(
                    [
                        "Data validated by internal systems",
                        "Cross-referenced with external sources",
                        "Confirmed by automated checks",
                    ]
                ),
            }
            return data
        return {
            "original": data,
            "_fabricated_metadata": {
                "source": self._rng.choice(self.config.fake_urls),
                "timestamp": "2024-01-15T12:00:00Z",
            },
        }

    def _inject_contradictory(self, data: Any) -> dict:
        """Add contradicting information."""
        contradiction = {
            "warning": "Conflicting data detected",
            "alternative_value": self._corrupt_value(data),
            "note": self._rng.choice(self.config.contradictory_templates).format(
                contradiction="the values may not be accurate"
            ),
        }

        if isinstance(data, dict):
            data = data.copy()
            data["_contradiction"] = contradiction
            return data
        return {"value": data, "_contradiction": contradiction}

    def _inject_confident_wrong(self, data: Any) -> dict:
        """Return confidently wrong information."""
        wrong_data = self._corrupt_value(data)
        return {
            "result": wrong_data,
            "confidence": 0.98,  # High confidence in wrong answer
            "verified": True,
            "source": "authoritative",
        }

    def _inject_nonexistent_reference(self, data: Any) -> dict:
        """Add references to things that don't exist."""
        fake_refs = [
            f"See documentation at {self._rng.choice(self.config.fake_urls)}",
            f"Refer to {self._rng.choice(self.config.fake_names)}'s implementation",
            f"As specified in RFC-{self._rng.randint(10000, 99999)}",
            f"Following the {self._rng.choice(['Alpha', 'Beta', 'Gamma', 'Delta'])} protocol v{self._rng.randint(1, 5)}.{self._rng.randint(0, 9)}",
        ]

        if isinstance(data, dict):
            data = data.copy()
            data["_reference"] = self._rng.choice(fake_refs)
            return data
        return {"value": data, "reference": self._rng.choice(fake_refs)}

    def inject(self, target: str, context: dict[str, Any]) -> tuple[Any, dict[str, Any]]:
        """Inject a hallucination into the data."""
        hallucination_type = self._select_hallucination_type()
        original_data = context.get("data", context.get("response", {}))

        injection_map = {
            HallucinationType.WRONG_VALUE: self._inject_wrong_value,
            HallucinationType.FABRICATED_DATA: self._inject_fabricated_data,
            HallucinationType.CONTRADICTORY: self._inject_contradictory,
            HallucinationType.CONFIDENT_WRONG: self._inject_confident_wrong,
            HallucinationType.PARTIAL_TRUTH: self._inject_wrong_value,  # Uses same logic
            HallucinationType.OUTDATED: self._inject_wrong_value,
            HallucinationType.NONEXISTENT_REFERENCE: self._inject_nonexistent_reference,
        }

        inject_func = injection_map.get(hallucination_type, self._inject_wrong_value)
        corrupted_data = inject_func(original_data)

        details = {
            "hallucination_type": hallucination_type.value,
            "severity": self.config.severity,
            "tool_name": target,
            "original_type": type(original_data).__name__,
        }

        self.record_injection(target, details)

        return corrupted_data, details
