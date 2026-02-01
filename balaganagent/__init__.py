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

__version__ = "0.4.1"

from .engine import ChaosEngine
from .experiment import Experiment, ExperimentConfig
from .hooks import ChaosHookEngine
from .reporting import ReportGenerator
from .runner import ExperimentRunner
from .verbose import get_logger, is_verbose, set_verbose
from .wrapper import AgentWrapper, ToolProxy
from .wrappers.claude_sdk_client import ChaosClaudeSDKClient
from .wrappers.claude_sdk_hooks import ClaudeSDKChaosIntegration

__all__ = [
    "ChaosEngine",
    "Experiment",
    "ExperimentConfig",
    "AgentWrapper",
    "ToolProxy",
    "ExperimentRunner",
    "ReportGenerator",
    "ChaosHookEngine",
    "ChaosClaudeSDKClient",
    "ClaudeSDKChaosIntegration",
    "set_verbose",
    "is_verbose",
    "get_logger",
]
