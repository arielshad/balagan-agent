"""Agent wrappers for popular AI agent frameworks."""

from .autogen import AutoGenFunctionProxy, AutoGenMultiAgentWrapper, AutoGenWrapper
from .crewai import CrewAIToolProxy, CrewAIWrapper

__all__ = [
    "CrewAIWrapper",
    "CrewAIToolProxy",
    "AutoGenWrapper",
    "AutoGenFunctionProxy",
    "AutoGenMultiAgentWrapper",
]
