"""Agent wrappers for popular AI agent frameworks."""

from .autogen import AutoGenFunctionProxy, AutoGenMultiAgentWrapper, AutoGenWrapper
from .claude_sdk import ClaudeAgentSDKToolProxy, ClaudeAgentSDKWrapper
from .crewai import CrewAIToolProxy, CrewAIWrapper
from .langchain import (
    ChaosCallbackHandler,
    LangChainAgentWrapper,
    LangChainChainWrapper,
    LangChainToolProxy,
)

__all__ = [
    "CrewAIWrapper",
    "CrewAIToolProxy",
    "AutoGenWrapper",
    "AutoGenFunctionProxy",
    "AutoGenMultiAgentWrapper",
    "ClaudeAgentSDKWrapper",
    "ClaudeAgentSDKToolProxy",
    "LangChainAgentWrapper",
    "LangChainToolProxy",
    "LangChainChainWrapper",
    "ChaosCallbackHandler",
]
