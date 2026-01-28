"""Verbose logging utilities for BalaganAgent."""

import sys
import time
from contextlib import contextmanager
from datetime import datetime
from typing import Any, Optional


class VerboseLogger:
    """
    Logger for verbose output in BalaganAgent.

    Provides colored, structured logging for chaos engineering events
    including tool calls, fault injections, and experiment progress.
    """

    # ANSI color codes
    COLORS = {
        "reset": "\033[0m",
        "bold": "\033[1m",
        "dim": "\033[2m",
        "red": "\033[31m",
        "green": "\033[32m",
        "yellow": "\033[33m",
        "blue": "\033[34m",
        "magenta": "\033[35m",
        "cyan": "\033[36m",
        "white": "\033[37m",
    }

    def __init__(self, enabled: bool = False, output=None):
        """
        Initialize the verbose logger.

        Args:
            enabled: Whether verbose logging is enabled
            output: Output stream (defaults to sys.stdout)
        """
        self.enabled = enabled
        self.output = output or sys.stdout
        self._indent_level = 0
        self._start_time = time.time()

    def _colorize(self, text: str, color: str) -> str:
        """Apply color to text."""
        if not self.output.isatty():
            return text
        return f"{self.COLORS.get(color, '')}{text}{self.COLORS['reset']}"

    def _timestamp(self) -> str:
        """Get elapsed time since logger creation."""
        elapsed = time.time() - self._start_time
        return f"{elapsed:7.3f}s"

    def _indent(self) -> str:
        """Get current indentation."""
        return "  " * self._indent_level

    def log(self, message: str, color: Optional[str] = None, level: int = 0):
        """
        Log a message with optional color and indentation.

        Args:
            message: Message to log
            color: Color name (e.g., 'green', 'red')
            level: Additional indentation level
        """
        if not self.enabled:
            return

        indent = "  " * (self._indent_level + level)
        timestamp = self._colorize(self._timestamp(), "dim")

        if color:
            message = self._colorize(message, color)

        self.output.write(f"{timestamp} {indent}{message}\n")
        self.output.flush()

    def header(self, text: str):
        """Log a header/section."""
        if not self.enabled:
            return

        separator = "=" * 60
        self.log(separator, "bold")
        self.log(text, "bold")
        self.log(separator, "bold")

    def section(self, text: str):
        """Log a section separator."""
        if not self.enabled:
            return

        self.log(f"\n{text}", "cyan")
        self.log("-" * len(text), "dim")

    def tool_call(self, tool_name: str, args: tuple, kwargs: dict):
        """Log a tool call."""
        if not self.enabled:
            return

        args_str = ", ".join(repr(a) for a in args)
        kwargs_str = ", ".join(f"{k}={v!r}" for k, v in kwargs.items())
        params = ", ".join(filter(None, [args_str, kwargs_str]))

        self.log(f"🔧 Tool call: {tool_name}({params})", "blue")

    def tool_result(self, result: Any, duration_ms: float):
        """Log a tool result."""
        if not self.enabled:
            return

        result_str = str(result)
        if len(result_str) > 100:
            result_str = result_str[:97] + "..."

        self.log(f"✓ Result: {result_str} ({duration_ms:.2f}ms)", "green", level=1)

    def tool_error(self, error: Exception, duration_ms: float):
        """Log a tool error."""
        if not self.enabled:
            return

        self.log(f"✗ Error: {type(error).__name__}: {error} ({duration_ms:.2f}ms)", "red", level=1)

    def fault_injected(self, fault_type: str, tool_name: str, details: dict):
        """Log a fault injection."""
        if not self.enabled:
            return

        details_str = ", ".join(f"{k}={v}" for k, v in details.items() if k not in ["timestamp"])
        self.log(f"💥 FAULT INJECTED: {fault_type} on {tool_name}", "yellow")
        if details_str:
            self.log(f"   Details: {details_str}", "dim", level=1)

    def retry(self, attempt: int, max_retries: int, delay: float):
        """Log a retry attempt."""
        if not self.enabled:
            return

        self.log(f"🔄 Retry {attempt}/{max_retries} (waiting {delay:.1f}s...)", "yellow", level=1)

    def recovery(self, tool_name: str, retries: int, success: bool):
        """Log recovery from a fault."""
        if not self.enabled:
            return

        status = "✓ successful" if success else "✗ failed"
        self.log(f"🔄 Recovery {status} for {tool_name} after {retries} retries", "green" if success else "red")

    def experiment_start(self, name: str, chaos_level: float):
        """Log experiment start."""
        if not self.enabled:
            return

        self.section(f"Experiment: {name}")
        self.log(f"Chaos level: {chaos_level}", "cyan")

    def experiment_end(self, name: str, duration: float, success_rate: float):
        """Log experiment end."""
        if not self.enabled:
            return

        color = "green" if success_rate > 0.9 else "yellow" if success_rate > 0.7 else "red"
        self.log(f"Experiment '{name}' completed in {duration:.2f}s", color)
        self.log(f"Success rate: {success_rate:.1%}", color)

    def metric(self, name: str, value: Any):
        """Log a metric."""
        if not self.enabled:
            return

        self.log(f"📊 {name}: {value}", "cyan")

    def indent(self):
        """Increase indentation level."""
        self._indent_level += 1

    def dedent(self):
        """Decrease indentation level."""
        self._indent_level = max(0, self._indent_level - 1)

    @contextmanager
    def indented(self):
        """Context manager for temporary indentation."""
        self.indent()
        try:
            yield
        finally:
            self.dedent()

    def enable(self):
        """Enable verbose logging."""
        self.enabled = True

    def disable(self):
        """Disable verbose logging."""
        self.enabled = False


# Global logger instance
_global_logger: Optional[VerboseLogger] = None


def get_logger() -> VerboseLogger:
    """Get the global verbose logger instance."""
    global _global_logger
    if _global_logger is None:
        _global_logger = VerboseLogger(enabled=False)
    return _global_logger


def set_verbose(enabled: bool):
    """Enable or disable verbose logging globally."""
    logger = get_logger()
    if enabled:
        logger.enable()
    else:
        logger.disable()


def is_verbose() -> bool:
    """Check if verbose logging is enabled."""
    return get_logger().enabled
