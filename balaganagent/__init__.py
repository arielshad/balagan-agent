"""
BalaganAgent - Chaos Engineering Framework for AI Agents

A reliability testing framework that stress-tests AI agents through:
- Random tool failures
- Delayed responses
- Hallucination injection
- Context corruption
- Budget exhaustion

Outputs reliability metrics including MTTR, recovery quality, and reliability scores.
"""

__version__ = "0.2.1"

from .engine import ChaosEngine
from .experiment import Experiment, ExperimentConfig
from .reporting import ReportGenerator
from .runner import ExperimentRunner
from .verbose import get_logger, is_verbose, set_verbose
from .wrapper import AgentWrapper, ToolProxy

__all__ = [
    "ChaosEngine",
    "Experiment",
    "ExperimentConfig",
    "AgentWrapper",
    "ToolProxy",
    "ExperimentRunner",
    "ReportGenerator",
    "set_verbose",
    "is_verbose",
    "get_logger",
]
