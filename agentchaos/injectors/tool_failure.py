"""Tool failure injection for chaos testing."""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional

from .base import BaseInjector, FaultType, InjectorConfig


class FailureMode(Enum):
    """Types of tool failures to simulate."""

    EXCEPTION = "exception"  # Tool raises an exception
    TIMEOUT = "timeout"  # Tool times out
    EMPTY_RESPONSE = "empty_response"  # Tool returns empty/null
    MALFORMED_RESPONSE = "malformed_response"  # Tool returns invalid data
    PARTIAL_FAILURE = "partial_failure"  # Tool partially succeeds
    RATE_LIMIT = "rate_limit"  # Tool hits rate limit
    AUTH_FAILURE = "auth_failure"  # Authentication/authorization failure
    NOT_FOUND = "not_found"  # Resource not found
    SERVICE_UNAVAILABLE = "service_unavailable"  # Service temporarily unavailable


@dataclass
class ToolFailureConfig(InjectorConfig):
    """Configuration for tool failure injection."""

    failure_modes: list[FailureMode] = field(
        default_factory=lambda: list(FailureMode)
    )
    failure_mode_weights: Optional[dict[FailureMode, float]] = None
    custom_exceptions: dict[str, type[Exception]] = field(default_factory=dict)
    error_messages: dict[FailureMode, list[str]] = field(default_factory=dict)

    def __post_init__(self):
        super().__post_init__()
        # Default error messages
        if not self.error_messages:
            self.error_messages = {
                FailureMode.EXCEPTION: [
                    "Internal error occurred",
                    "Unexpected failure",
                    "Operation failed",
                ],
                FailureMode.TIMEOUT: [
                    "Request timed out after 30s",
                    "Connection timeout",
                    "Operation exceeded time limit",
                ],
                FailureMode.RATE_LIMIT: [
                    "Rate limit exceeded. Try again in 60 seconds.",
                    "Too many requests",
                    "API quota exhausted",
                ],
                FailureMode.AUTH_FAILURE: [
                    "Invalid credentials",
                    "Token expired",
                    "Unauthorized access",
                ],
                FailureMode.NOT_FOUND: [
                    "Resource not found",
                    "404: Not found",
                    "The requested item does not exist",
                ],
                FailureMode.SERVICE_UNAVAILABLE: [
                    "Service temporarily unavailable",
                    "503: Service unavailable",
                    "System under maintenance",
                ],
            }


class ToolFailureException(Exception):
    """Exception raised when a tool failure is injected."""

    def __init__(self, message: str, failure_mode: FailureMode, tool_name: str):
        super().__init__(message)
        self.failure_mode = failure_mode
        self.tool_name = tool_name


class ToolFailureInjector(BaseInjector):
    """Injects various types of tool failures."""

    def __init__(self, config: Optional[ToolFailureConfig] = None):
        super().__init__(config or ToolFailureConfig())
        self.config: ToolFailureConfig = self.config

    @property
    def fault_type(self) -> FaultType:
        return FaultType.TOOL_FAILURE

    def _select_failure_mode(self) -> FailureMode:
        """Select a failure mode based on weights or uniformly."""
        if self.config.failure_mode_weights:
            modes = list(self.config.failure_mode_weights.keys())
            weights = list(self.config.failure_mode_weights.values())
            return self._rng.choices(modes, weights=weights)[0]
        return self._rng.choice(self.config.failure_modes)

    def _get_error_message(self, mode: FailureMode) -> str:
        """Get an error message for the failure mode."""
        messages = self.config.error_messages.get(mode, ["Operation failed"])
        return self._rng.choice(messages)

    def inject(self, target: str, context: dict[str, Any]) -> tuple[Any, dict[str, Any]]:
        """Inject a tool failure."""
        failure_mode = self._select_failure_mode()
        error_message = self._get_error_message(failure_mode)

        details = {
            "failure_mode": failure_mode.value,
            "error_message": error_message,
            "tool_name": target,
        }

        self.record_injection(target, details)

        # Generate the appropriate failure response
        if failure_mode == FailureMode.EXCEPTION:
            exc_class = self.config.custom_exceptions.get(target, ToolFailureException)
            if exc_class == ToolFailureException:
                raise exc_class(error_message, failure_mode, target)
            raise exc_class(error_message)

        elif failure_mode == FailureMode.TIMEOUT:
            raise TimeoutError(error_message)

        elif failure_mode == FailureMode.EMPTY_RESPONSE:
            return None, details

        elif failure_mode == FailureMode.MALFORMED_RESPONSE:
            return {"error": True, "data": "<<<CORRUPTED>>>", "partial": b"\x00\xff"}, details

        elif failure_mode == FailureMode.PARTIAL_FAILURE:
            return {
                "status": "partial",
                "completed": self._rng.randint(1, 50),
                "total": 100,
                "error": error_message,
            }, details

        elif failure_mode == FailureMode.RATE_LIMIT:
            return {
                "error": "rate_limit_exceeded",
                "retry_after": self._rng.randint(30, 300),
                "message": error_message,
            }, details

        elif failure_mode == FailureMode.AUTH_FAILURE:
            return {
                "error": "authentication_failed",
                "code": 401,
                "message": error_message,
            }, details

        elif failure_mode == FailureMode.NOT_FOUND:
            return {
                "error": "not_found",
                "code": 404,
                "message": error_message,
            }, details

        elif failure_mode == FailureMode.SERVICE_UNAVAILABLE:
            return {
                "error": "service_unavailable",
                "code": 503,
                "message": error_message,
            }, details

        return None, details


def create_flaky_tool(
    tool_func: callable,
    failure_rate: float = 0.1,
    failure_modes: Optional[list[FailureMode]] = None,
) -> callable:
    """
    Decorator to make a tool function flaky for testing.

    Args:
        tool_func: The original tool function
        failure_rate: Probability of failure (0.0 to 1.0)
        failure_modes: List of failure modes to use

    Returns:
        A wrapped function that randomly fails
    """
    config = ToolFailureConfig(
        probability=failure_rate,
        failure_modes=failure_modes or list(FailureMode),
    )
    injector = ToolFailureInjector(config)

    def wrapper(*args, **kwargs):
        tool_name = tool_func.__name__
        if injector.should_inject(tool_name):
            result, _ = injector.inject(tool_name, {"args": args, "kwargs": kwargs})
            return result
        return tool_func(*args, **kwargs)

    wrapper.__name__ = tool_func.__name__
    wrapper.__doc__ = tool_func.__doc__
    wrapper._injector = injector

    return wrapper
