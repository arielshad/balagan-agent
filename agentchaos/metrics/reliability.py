"""Reliability scoring for AI agents."""

from dataclasses import dataclass, field
from typing import Any, Optional
from enum import Enum
import statistics
import math


class ReliabilityGrade(Enum):
    """Reliability grades (inspired by SRE practices)."""

    FIVE_NINES = "99.999%"  # 5.26 minutes downtime/year
    FOUR_NINES = "99.99%"   # 52.6 minutes downtime/year
    THREE_NINES = "99.9%"   # 8.77 hours downtime/year
    TWO_NINES = "99%"       # 3.65 days downtime/year
    ONE_NINE = "90%"        # 36.5 days downtime/year
    BELOW_90 = "<90%"       # More than 36.5 days downtime/year


@dataclass
class ReliabilityReport:
    """Comprehensive reliability report."""

    overall_score: float
    grade: ReliabilityGrade
    availability: float
    mttr_seconds: float
    mtbf_seconds: float
    error_budget_remaining: float
    component_scores: dict[str, float]
    recommendations: list[str]
    raw_metrics: dict[str, Any]


class ReliabilityScorer:
    """
    Calculates comprehensive reliability scores for AI agents.

    Based on SRE principles, evaluates:
    - Availability (uptime)
    - Error rate
    - Latency (p50, p90, p99)
    - MTTR (Mean Time To Recovery)
    - MTBF (Mean Time Between Failures)
    - Throughput consistency
    """

    # SLO (Service Level Objective) defaults
    DEFAULT_SLOS = {
        "availability": 0.99,       # 99% availability
        "error_rate": 0.01,         # 1% max error rate
        "latency_p50_ms": 100,      # 100ms p50
        "latency_p90_ms": 500,      # 500ms p90
        "latency_p99_ms": 2000,     # 2s p99
        "mttr_seconds": 60,         # 1 minute MTTR
    }

    # Component weights for overall score
    DEFAULT_WEIGHTS = {
        "availability": 0.30,
        "error_handling": 0.25,
        "latency": 0.20,
        "recovery": 0.15,
        "consistency": 0.10,
    }

    def __init__(
        self,
        slos: Optional[dict[str, float]] = None,
        weights: Optional[dict[str, float]] = None,
        error_budget_period_hours: float = 720,  # 30 days
    ):
        self.slos = {**self.DEFAULT_SLOS, **(slos or {})}
        self.weights = {**self.DEFAULT_WEIGHTS, **(weights or {})}
        self.error_budget_period_hours = error_budget_period_hours

        # Tracked metrics
        self._total_operations = 0
        self._successful_operations = 0
        self._failed_operations = 0
        self._latencies_ms: list[float] = []
        self._failure_times: list[float] = []
        self._recovery_times: list[float] = []
        self._operation_timestamps: list[float] = []

    def record_operation(
        self,
        success: bool,
        latency_ms: float,
        timestamp: Optional[float] = None,
    ):
        """Record an operation result."""
        import time
        ts = timestamp or time.time()

        self._total_operations += 1
        self._latencies_ms.append(latency_ms)
        self._operation_timestamps.append(ts)

        if success:
            self._successful_operations += 1
        else:
            self._failed_operations += 1
            self._failure_times.append(ts)

    def record_recovery(self, recovery_time_seconds: float):
        """Record a recovery event."""
        self._recovery_times.append(recovery_time_seconds)

    def calculate_availability(self) -> float:
        """Calculate availability percentage."""
        if self._total_operations == 0:
            return 1.0
        return self._successful_operations / self._total_operations

    def calculate_error_rate(self) -> float:
        """Calculate error rate."""
        if self._total_operations == 0:
            return 0.0
        return self._failed_operations / self._total_operations

    def calculate_latency_percentiles(self) -> dict[str, float]:
        """Calculate latency percentiles."""
        if not self._latencies_ms:
            return {"p50": 0, "p90": 0, "p95": 0, "p99": 0}

        sorted_latencies = sorted(self._latencies_ms)

        def percentile(data: list[float], p: float) -> float:
            idx = int(len(data) * p / 100)
            return data[min(idx, len(data) - 1)]

        return {
            "p50": percentile(sorted_latencies, 50),
            "p90": percentile(sorted_latencies, 90),
            "p95": percentile(sorted_latencies, 95),
            "p99": percentile(sorted_latencies, 99),
        }

    def calculate_mttr(self) -> float:
        """Calculate Mean Time To Recovery."""
        if not self._recovery_times:
            return 0.0
        return statistics.mean(self._recovery_times)

    def calculate_mtbf(self) -> float:
        """Calculate Mean Time Between Failures."""
        if len(self._failure_times) < 2:
            return float('inf')

        sorted_failures = sorted(self._failure_times)
        intervals = [
            sorted_failures[i+1] - sorted_failures[i]
            for i in range(len(sorted_failures) - 1)
        ]

        return statistics.mean(intervals)

    def calculate_error_budget(self) -> dict[str, float]:
        """
        Calculate error budget status.

        Error budget = allowed errors based on SLO over the budget period.
        """
        slo_availability = self.slos["availability"]
        allowed_error_rate = 1 - slo_availability

        # Calculate budget in terms of operations
        total_budget = self._total_operations * allowed_error_rate
        budget_consumed = self._failed_operations
        budget_remaining = max(0, total_budget - budget_consumed)

        return {
            "total_budget": total_budget,
            "consumed": budget_consumed,
            "remaining": budget_remaining,
            "remaining_percent": budget_remaining / total_budget if total_budget > 0 else 1.0,
            "burn_rate": budget_consumed / total_budget if total_budget > 0 else 0.0,
        }

    def _score_availability(self) -> float:
        """Score availability component (0-1)."""
        availability = self.calculate_availability()
        slo = self.slos["availability"]

        if availability >= slo:
            return 1.0
        elif availability >= slo * 0.9:  # Within 10% of SLO
            return 0.8
        elif availability >= slo * 0.8:  # Within 20% of SLO
            return 0.6
        elif availability >= 0.5:
            return 0.4
        else:
            return 0.2

    def _score_error_handling(self) -> float:
        """Score error handling component (0-1)."""
        error_rate = self.calculate_error_rate()
        slo_error_rate = self.slos["error_rate"]

        if error_rate <= slo_error_rate:
            return 1.0
        elif error_rate <= slo_error_rate * 2:
            return 0.7
        elif error_rate <= slo_error_rate * 5:
            return 0.4
        else:
            return 0.1

    def _score_latency(self) -> float:
        """Score latency component (0-1)."""
        percentiles = self.calculate_latency_percentiles()

        scores = []

        # P50 score
        p50_ratio = percentiles["p50"] / self.slos["latency_p50_ms"]
        scores.append(min(1.0, 1.0 / max(p50_ratio, 0.1)))

        # P90 score
        p90_ratio = percentiles["p90"] / self.slos["latency_p90_ms"]
        scores.append(min(1.0, 1.0 / max(p90_ratio, 0.1)))

        # P99 score
        p99_ratio = percentiles["p99"] / self.slos["latency_p99_ms"]
        scores.append(min(1.0, 1.0 / max(p99_ratio, 0.1)))

        # Weighted average (p99 matters more)
        return scores[0] * 0.2 + scores[1] * 0.3 + scores[2] * 0.5

    def _score_recovery(self) -> float:
        """Score recovery component (0-1)."""
        mttr = self.calculate_mttr()
        slo_mttr = self.slos["mttr_seconds"]

        if mttr == 0:
            return 1.0  # No failures to recover from

        if mttr <= slo_mttr:
            return 1.0
        elif mttr <= slo_mttr * 2:
            return 0.7
        elif mttr <= slo_mttr * 5:
            return 0.4
        else:
            return 0.1

    def _score_consistency(self) -> float:
        """Score consistency component (0-1)."""
        if len(self._latencies_ms) < 2:
            return 1.0

        # Lower coefficient of variation = more consistent
        mean = statistics.mean(self._latencies_ms)
        if mean == 0:
            return 1.0

        std_dev = statistics.stdev(self._latencies_ms)
        cv = std_dev / mean  # Coefficient of variation

        if cv <= 0.1:
            return 1.0
        elif cv <= 0.25:
            return 0.8
        elif cv <= 0.5:
            return 0.6
        elif cv <= 1.0:
            return 0.4
        else:
            return 0.2

    def _determine_grade(self, availability: float) -> ReliabilityGrade:
        """Determine reliability grade based on availability."""
        if availability >= 0.99999:
            return ReliabilityGrade.FIVE_NINES
        elif availability >= 0.9999:
            return ReliabilityGrade.FOUR_NINES
        elif availability >= 0.999:
            return ReliabilityGrade.THREE_NINES
        elif availability >= 0.99:
            return ReliabilityGrade.TWO_NINES
        elif availability >= 0.9:
            return ReliabilityGrade.ONE_NINE
        else:
            return ReliabilityGrade.BELOW_90

    def _generate_recommendations(
        self,
        component_scores: dict[str, float],
        metrics: dict[str, Any],
    ) -> list[str]:
        """Generate improvement recommendations."""
        recommendations = []

        if component_scores["availability"] < 0.8:
            recommendations.append(
                f"Availability is {metrics['availability']:.1%}, below SLO of {self.slos['availability']:.1%}. "
                "Consider implementing retry logic or circuit breakers."
            )

        if component_scores["error_handling"] < 0.7:
            recommendations.append(
                f"Error rate is {metrics['error_rate']:.1%}. "
                "Review error handling and implement graceful degradation."
            )

        if component_scores["latency"] < 0.6:
            percentiles = metrics["latency_percentiles"]
            recommendations.append(
                f"P99 latency is {percentiles['p99']:.0f}ms, above SLO of {self.slos['latency_p99_ms']}ms. "
                "Consider caching or optimizing slow operations."
            )

        if component_scores["recovery"] < 0.7:
            recommendations.append(
                f"MTTR is {metrics['mttr_seconds']:.1f}s, above target of {self.slos['mttr_seconds']}s. "
                "Improve recovery mechanisms and reduce retry delays."
            )

        if component_scores["consistency"] < 0.6:
            recommendations.append(
                "High latency variance detected. "
                "Investigate sources of inconsistency like GC pauses or cold starts."
            )

        error_budget = metrics["error_budget"]
        if error_budget["remaining_percent"] < 0.2:
            recommendations.append(
                f"Error budget is {error_budget['remaining_percent']:.0%} remaining. "
                "Consider freezing changes until budget recovers."
            )

        if not recommendations:
            recommendations.append("All metrics within SLO targets. Continue monitoring.")

        return recommendations

    def calculate_score(self) -> ReliabilityReport:
        """Calculate comprehensive reliability score."""
        # Calculate component scores
        component_scores = {
            "availability": self._score_availability(),
            "error_handling": self._score_error_handling(),
            "latency": self._score_latency(),
            "recovery": self._score_recovery(),
            "consistency": self._score_consistency(),
        }

        # Calculate weighted overall score
        overall_score = sum(
            component_scores[component] * weight
            for component, weight in self.weights.items()
        )

        # Gather raw metrics
        availability = self.calculate_availability()
        error_budget = self.calculate_error_budget()

        raw_metrics = {
            "total_operations": self._total_operations,
            "successful_operations": self._successful_operations,
            "failed_operations": self._failed_operations,
            "availability": availability,
            "error_rate": self.calculate_error_rate(),
            "latency_percentiles": self.calculate_latency_percentiles(),
            "mttr_seconds": self.calculate_mttr(),
            "mtbf_seconds": self.calculate_mtbf(),
            "error_budget": error_budget,
        }

        recommendations = self._generate_recommendations(component_scores, raw_metrics)

        return ReliabilityReport(
            overall_score=overall_score,
            grade=self._determine_grade(availability),
            availability=availability,
            mttr_seconds=raw_metrics["mttr_seconds"],
            mtbf_seconds=raw_metrics["mtbf_seconds"],
            error_budget_remaining=error_budget["remaining_percent"],
            component_scores=component_scores,
            recommendations=recommendations,
            raw_metrics=raw_metrics,
        )

    def reset(self):
        """Reset all tracked metrics."""
        self._total_operations = 0
        self._successful_operations = 0
        self._failed_operations = 0
        self._latencies_ms.clear()
        self._failure_times.clear()
        self._recovery_times.clear()
        self._operation_timestamps.clear()
