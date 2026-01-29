"""Agent wrappers for popular AI agent frameworks."""

from .autogen import AutoGenFunctionProxy, AutoGenMultiAgentWrapper, AutoGenWrapper
from .claude_sdk import ClaudeAgentSDKToolProxy, ClaudeAgentSDKWrapper
from .claude_sdk_client import ChaosClaudeSDKClient
from .claude_sdk_hooks import ClaudeSDKChaosIntegration
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
    "ChaosClaudeSDKClient",
    "ClaudeSDKChaosIntegration",
    "LangChainAgentWrapper",
    "LangChainToolProxy",
    "LangChainChainWrapper",
    "ChaosCallbackHandler",
]
