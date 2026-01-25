"""
AgentChaos - Chaos Engineering Framework for AI Agents

A reliability testing framework that stress-tests AI agents through:
- Random tool failures
- Delayed responses
- Hallucination injection
- Context corruption
- Budget exhaustion

Outputs reliability metrics including MTTR, recovery quality, and reliability scores.
"""

__version__ = "0.1.0"

from .engine import ChaosEngine
from .experiment import Experiment, ExperimentConfig
from .wrapper import AgentWrapper, ToolProxy
from .runner import ExperimentRunner
from .reporting import ReportGenerator

__all__ = [
    "ChaosEngine",
    "Experiment",
    "ExperimentConfig",
    "AgentWrapper",
    "ToolProxy",
    "ExperimentRunner",
    "ReportGenerator",
]
