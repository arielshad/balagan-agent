"""Recovery quality analysis for AI agents."""

import statistics
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional


class RecoveryQuality(Enum):
    """Quality levels of recovery."""

    EXCELLENT = "excellent"  # Full recovery, correct output
    GOOD = "good"  # Recovery with minor degradation
    ACCEPTABLE = "acceptable"  # Recovery with noticeable degradation
    POOR = "poor"  # Partial recovery
    FAILED = "failed"  # No recovery


@dataclass
class RecoveryAssessment:
    """Assessment of a single recovery attempt."""

    operation_name: str
    fault_type: str
    quality: RecoveryQuality
    score: float  # 0.0 to 1.0
    factors: dict[str, float]  # Contributing factors
    notes: list[str] = field(default_factory=list)


class RecoveryQualityAnalyzer:
    """
    Analyzes the quality of agent recovery from failures.

    Evaluates recovery based on:
    - Output correctness
    - State consistency
    - Performance degradation
    - Resource efficiency
    - Graceful degradation
    """

    # Weights for different quality factors
    DEFAULT_WEIGHTS = {
        "correctness": 0.35,
        "completeness": 0.25,
        "timeliness": 0.20,
        "resource_efficiency": 0.10,
        "state_consistency": 0.10,
    }

    def __init__(self, weights: Optional[dict[str, float]] = None):
        self.weights = weights or self.DEFAULT_WEIGHTS
        self._assessments: list[RecoveryAssessment] = []

    def assess_recovery(
        self,
        operation_name: str,
        fault_type: str,
        expected_output: Any,
        actual_output: Any,
        baseline_latency_ms: float,
        actual_latency_ms: float,
        retries: int,
        state_before: Optional[dict] = None,
        state_after: Optional[dict] = None,
        max_retries: int = 3,
    ) -> RecoveryAssessment:
        """
        Assess the quality of a recovery attempt.

        Args:
            operation_name: Name of the operation that failed
            fault_type: Type of fault that was injected
            expected_output: What the output should have been
            actual_output: What the output actually was
            baseline_latency_ms: Normal latency for this operation
            actual_latency_ms: Latency including recovery time
            retries: Number of retries needed
            state_before: Agent state before failure
            state_after: Agent state after recovery
            max_retries: Maximum allowed retries

        Returns:
            RecoveryAssessment with quality score
        """
        factors = {}
        notes = []

        # 1. Correctness - did we get the right output?
        correctness = self._assess_correctness(expected_output, actual_output)
        factors["correctness"] = correctness
        if correctness < 1.0:
            notes.append(f"Output correctness: {correctness:.0%}")

        # 2. Completeness - is the output complete?
        completeness = self._assess_completeness(expected_output, actual_output)
        factors["completeness"] = completeness
        if completeness < 1.0:
            notes.append(f"Output completeness: {completeness:.0%}")

        # 3. Timeliness - how fast was recovery?
        timeliness = self._assess_timeliness(
            baseline_latency_ms, actual_latency_ms, retries, max_retries
        )
        factors["timeliness"] = timeliness
        if timeliness < 0.5:
            notes.append(
                f"Recovery took {actual_latency_ms/baseline_latency_ms:.1f}x longer than normal"
            )

        # 4. Resource efficiency - how many retries?
        resource_efficiency = self._assess_resource_efficiency(retries, max_retries)
        factors["resource_efficiency"] = resource_efficiency
        if retries > 0:
            notes.append(f"Required {retries} retries")

        # 5. State consistency - is state intact?
        state_consistency = self._assess_state_consistency(state_before, state_after)
        factors["state_consistency"] = state_consistency
        if state_consistency < 1.0:
            notes.append("Some state inconsistency detected")

        # Calculate weighted score
        score = sum(factors[factor] * weight for factor, weight in self.weights.items())

        # Determine quality level
        quality = self._score_to_quality(score)

        assessment = RecoveryAssessment(
            operation_name=operation_name,
            fault_type=fault_type,
            quality=quality,
            score=score,
            factors=factors,
            notes=notes,
        )

        self._assessments.append(assessment)
        return assessment

    def _assess_correctness(self, expected: Any, actual: Any) -> float:
        """Assess output correctness (0.0 to 1.0)."""
        if actual is None:
            return 0.0

        if expected == actual:
            return 1.0

        # Type mismatch
        if type(expected) is not type(actual):
            return 0.2

        # Partial correctness for collections
        if isinstance(expected, dict) and isinstance(actual, dict):
            if not expected:
                return 1.0 if not actual else 0.5
            matching_keys = set(expected.keys()) & set(actual.keys())
            matching_values = sum(1 for k in matching_keys if expected.get(k) == actual.get(k))
            return matching_values / len(expected)

        if isinstance(expected, (list, tuple)) and isinstance(actual, (list, tuple)):
            if not expected:
                return 1.0 if not actual else 0.5
            matching = sum(1 for e, a in zip(expected, actual) if e == a)
            return matching / max(len(expected), len(actual))

        if isinstance(expected, str) and isinstance(actual, str):
            if not expected:
                return 1.0 if not actual else 0.5
            # Simple similarity based on common characters
            common = sum(1 for c in expected if c in actual)
            return common / max(len(expected), len(actual))

        # Numeric tolerance
        if isinstance(expected, (int, float)) and isinstance(actual, (int, float)):
            if expected == 0:
                return 1.0 if actual == 0 else 0.5
            relative_error = abs(expected - actual) / abs(expected)
            return max(0, 1 - relative_error)

        return 0.5  # Unknown comparison

    def _assess_completeness(self, expected: Any, actual: Any) -> float:
        """Assess output completeness (0.0 to 1.0)."""
        if actual is None:
            return 0.0

        if isinstance(expected, dict) and isinstance(actual, dict):
            if not expected:
                return 1.0
            return len(set(expected.keys()) & set(actual.keys())) / len(expected)

        if isinstance(expected, (list, tuple)) and isinstance(actual, (list, tuple)):
            if not expected:
                return 1.0
            return min(len(actual) / len(expected), 1.0)

        if isinstance(expected, str) and isinstance(actual, str):
            if not expected:
                return 1.0
            return min(len(actual) / len(expected), 1.0)

        return 1.0 if actual is not None else 0.0

    def _assess_timeliness(
        self,
        baseline_ms: float,
        actual_ms: float,
        retries: int,
        max_retries: int,
    ) -> float:
        """Assess recovery timeliness (0.0 to 1.0)."""
        if baseline_ms <= 0:
            return 1.0

        # Calculate slowdown factor
        slowdown = actual_ms / baseline_ms

        if slowdown <= 1.0:
            return 1.0
        elif slowdown <= 2.0:
            return 0.8
        elif slowdown <= 5.0:
            return 0.6
        elif slowdown <= 10.0:
            return 0.4
        else:
            return max(0.1, 1.0 / slowdown)

    def _assess_resource_efficiency(self, retries: int, max_retries: int) -> float:
        """Assess resource efficiency based on retries (0.0 to 1.0)."""
        if max_retries <= 0:
            return 1.0 if retries == 0 else 0.5

        if retries == 0:
            return 1.0

        # Score decreases with retries
        return max(0, 1.0 - (retries / max_retries) * 0.8)

    def _assess_state_consistency(
        self,
        state_before: Optional[dict],
        state_after: Optional[dict],
    ) -> float:
        """Assess state consistency (0.0 to 1.0)."""
        if state_before is None or state_after is None:
            return 1.0  # Can't assess, assume good

        # Check for critical state keys that should remain unchanged
        critical_keys = ["config", "credentials", "session", "context"]

        inconsistencies: float = 0
        total_checks = 0

        for key in critical_keys:
            if key in state_before:
                total_checks += 1
                if key not in state_after:
                    inconsistencies += 1
                elif state_before[key] != state_after[key]:
                    inconsistencies += 0.5  # Modified is less bad than missing

        if total_checks == 0:
            return 1.0

        return 1.0 - (inconsistencies / total_checks)

    def _score_to_quality(self, score: float) -> RecoveryQuality:
        """Convert numeric score to quality level."""
        if score >= 0.9:
            return RecoveryQuality.EXCELLENT
        elif score >= 0.75:
            return RecoveryQuality.GOOD
        elif score >= 0.5:
            return RecoveryQuality.ACCEPTABLE
        elif score >= 0.25:
            return RecoveryQuality.POOR
        else:
            return RecoveryQuality.FAILED

    def get_summary(self) -> dict[str, Any]:
        """Get summary of all recovery assessments."""
        if not self._assessments:
            return {
                "total_assessments": 0,
                "average_score": 0,
                "quality_distribution": {},
            }

        scores = [a.score for a in self._assessments]
        quality_counts: dict[str, int] = {}
        factor_averages: dict[str, list[float]] = {}

        for assessment in self._assessments:
            quality = assessment.quality.value
            quality_counts[quality] = quality_counts.get(quality, 0) + 1

            for factor, value in assessment.factors.items():
                if factor not in factor_averages:
                    factor_averages[factor] = []
                factor_averages[factor].append(value)

        return {
            "total_assessments": len(self._assessments),
            "average_score": statistics.mean(scores),
            "score_std_dev": statistics.stdev(scores) if len(scores) > 1 else 0,
            "min_score": min(scores),
            "max_score": max(scores),
            "quality_distribution": quality_counts,
            "factor_averages": {
                factor: statistics.mean(values) for factor, values in factor_averages.items()
            },
            "assessments_by_fault_type": self._group_by_fault_type(),
        }

    def _group_by_fault_type(self) -> dict[str, dict[str, Any]]:
        """Group assessments by fault type."""
        by_type: dict[str, list[RecoveryAssessment]] = {}

        for assessment in self._assessments:
            ft = assessment.fault_type
            if ft not in by_type:
                by_type[ft] = []
            by_type[ft].append(assessment)

        return {
            fault_type: {
                "count": len(assessments),
                "average_score": statistics.mean([a.score for a in assessments]),
                "quality_distribution": {
                    q.value: sum(1 for a in assessments if a.quality == q) for q in RecoveryQuality
                },
            }
            for fault_type, assessments in by_type.items()
        }

    def get_weakest_areas(self, top_n: int = 3) -> list[dict[str, Any]]:
        """Identify the weakest recovery areas."""
        if not self._assessments:
            return []

        # Group by operation + fault type
        groups: dict[str, list[float]] = {}
        for assessment in self._assessments:
            key = f"{assessment.operation_name}:{assessment.fault_type}"
            if key not in groups:
                groups[key] = []
            groups[key].append(assessment.score)

        # Calculate average score for each group
        averages = [
            {"key": key, "average_score": statistics.mean(scores), "count": len(scores)}
            for key, scores in groups.items()
        ]

        # Sort by average score (ascending) and return top_n
        from typing import cast

        return sorted(averages, key=lambda x: cast(float, x["average_score"]))[:top_n]

    def reset(self):
        """Reset all assessments."""
        self._assessments.clear()
