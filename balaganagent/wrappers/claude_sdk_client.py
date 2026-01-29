"""Client-level chaos wrapper for Claude Agent SDK.

Wraps ``ClaudeSDKClient`` via composition to inject chaos at the
query/response level — prompt corruption, query delays, API failure
simulation, and timeout injection.

Usage::

    from balaganagent.wrappers.claude_sdk_client import ChaosClaudeSDKClient

    client = ChaosClaudeSDKClient(
        options=my_options,
        chaos_level=0.5,
        prompt_corruption_rate=0.1,
        query_delay_range=(0.0, 2.0),
        api_failure_rate=0.05,
    )
    async with client:
        await client.query(prompt="Research quantum computing")
        async for msg in client.receive_response():
            ...
"""

import asyncio
import random
import time
from typing import Any, Optional

from ..metrics import MetricsCollector, MTTRCalculator


class ChaosClaudeSDKClient:
    """Chaos-injecting wrapper around ``ClaudeSDKClient``.

    This wrapper sits at the *client* level rather than the tool level,
    allowing injection of faults that affect the agent's query/response
    lifecycle:

    - **Prompt corruption**: randomly mutate the prompt text
    - **Query delays**: add latency before queries are sent
    - **API failures**: simulate API errors
    - **Timeouts**: simulate query timeouts
    """

    def __init__(
        self,
        options: Any,
        chaos_level: float = 0.5,
        prompt_corruption_rate: float = 0.0,
        query_delay_range: tuple[float, float] = (0.0, 0.0),
        api_failure_rate: float = 0.0,
        timeout_rate: float = 0.0,
        seed: Optional[int] = None,
    ):
        self._options = options
        self._chaos_level = chaos_level
        self._prompt_corruption_rate = prompt_corruption_rate
        self._query_delay_range = query_delay_range
        self._api_failure_rate = api_failure_rate
        self._timeout_rate = timeout_rate
        self._rng = random.Random(seed)

        self._client: Any = None  # ClaudeSDKClient instance
        self._metrics = MetricsCollector()
        self._mttr = MTTRCalculator()
        self._query_count = 0
        self._last_fault: Optional[str] = None

    # ------------------------------------------------------------------
    # Async context manager
    # ------------------------------------------------------------------

    async def __aenter__(self):
        # Lazy import to avoid hard dependency
        from claude_agent_sdk import ClaudeSDKClient

        self._client = ClaudeSDKClient(options=self._options)
        await self._client.__aenter__()
        return self

    async def __aexit__(self, *args):
        if self._client:
            await self._client.__aexit__(*args)

    # ------------------------------------------------------------------
    # Query with chaos
    # ------------------------------------------------------------------

    async def query(self, prompt: str, **kwargs) -> None:
        """Send a query with potential chaos injection.

        Chaos checks (in order):
        1. Inject delay before sending
        2. Simulate API failure (raise RuntimeError)
        3. Simulate timeout (raise TimeoutError)
        4. Corrupt prompt text
        5. Forward to real client
        """
        self._query_count += 1
        start = time.time()

        # 1. Delay injection
        if self._query_delay_range[1] > 0:
            delay = self._rng.uniform(*self._query_delay_range)
            if delay > 0:
                await asyncio.sleep(delay)

        # 2. API failure
        if self._rng.random() < self._api_failure_rate:
            duration = (time.time() - start) * 1000
            self._metrics.record_operation(
                "query", duration, success=False, fault_type="api_failure"
            )
            self._mttr.record_failure("query", "api_failure")
            self._last_fault = "api_failure"
            raise RuntimeError("Chaos injection: simulated API failure")

        # 3. Timeout
        if self._rng.random() < self._timeout_rate:
            duration = (time.time() - start) * 1000
            self._metrics.record_operation(
                "query", duration, success=False, fault_type="timeout"
            )
            self._mttr.record_failure("query", "timeout")
            self._last_fault = "timeout"
            raise TimeoutError("Chaos injection: simulated query timeout")

        # 4. Prompt corruption
        if self._rng.random() < self._prompt_corruption_rate:
            prompt = self._corrupt_prompt(prompt)

        # 5. Forward to real client
        await self._client.query(prompt=prompt, **kwargs)
        duration = (time.time() - start) * 1000
        self._metrics.record_operation("query", duration, success=True)

        # Record recovery if previous query had a fault
        if self._last_fault:
            self._mttr.record_recovery(
                "query", self._last_fault,
                recovery_method="retry", retries=0, success=True,
            )
            self._last_fault = None

    async def receive_response(self):
        """Proxy to underlying client's ``receive_response``."""
        async for msg in self._client.receive_response():
            yield msg

    # ------------------------------------------------------------------
    # Prompt corruption
    # ------------------------------------------------------------------

    def _corrupt_prompt(self, prompt: str) -> str:
        """Inject noise into prompt text.

        Strategies (chosen randomly):
        - Swap two random words
        - Insert a random noise word
        - Truncate the prompt
        """
        words = prompt.split()
        if len(words) < 2:
            return prompt

        strategy = self._rng.choice(["swap", "insert", "truncate"])

        if strategy == "swap" and len(words) >= 3:
            i, j = self._rng.sample(range(len(words)), 2)
            words[i], words[j] = words[j], words[i]
        elif strategy == "insert":
            noise = self._rng.choice(["CORRUPTED", "???", "NULL", "[ERROR]", "NOISE"])
            pos = self._rng.randint(0, len(words))
            words.insert(pos, noise)
        elif strategy == "truncate":
            cut = max(1, len(words) // 2)
            words = words[:cut]

        return " ".join(words)

    # ------------------------------------------------------------------
    # Metrics
    # ------------------------------------------------------------------

    @property
    def query_count(self) -> int:
        return self._query_count

    def get_metrics(self) -> dict[str, Any]:
        return {
            "query_count": self._query_count,
            "operations": self._metrics.get_summary(),
        }

    def get_mttr_stats(self) -> dict[str, Any]:
        return self._mttr.get_recovery_stats()

    def reset(self):
        self._query_count = 0
        self._metrics.reset()
        self._mttr.reset()
        self._last_fault = None
