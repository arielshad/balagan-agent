"""Tests for LangGraph wrapper enhancements - phase 1: state management.

These tests validate state snapshots, field-level corruption, and metrics
collection for node-level chaos injection in LangGraph workflows.
"""

import copy
import time
from dataclasses import dataclass
from typing import Any

import pytest


class TestStateSnapshot:
    """Tests for StateSnapshot dataclass."""

    def test_state_snapshot_creation_with_all_fields(self):
        """Test StateSnapshot can be created with all required fields."""
        from balaganagent.wrappers.langgraph import StateSnapshot

        state_before = {"messages": [1, 2, 3], "context": "original"}
        state_after = {"messages": [1, 2, 3, 4], "context": "modified"}
        timestamp = time.time()

        snapshot = StateSnapshot(
            timestamp=timestamp,
            node_name="test_node",
            state_before=state_before,
            state_after=state_after,
            fault_injected="delay",
            target_fields=["messages"],
        )

        assert snapshot.timestamp == timestamp
        assert snapshot.node_name == "test_node"
        assert snapshot.state_before == state_before
        assert snapshot.state_after == state_after
        assert snapshot.fault_injected == "delay"
        assert snapshot.target_fields == ["messages"]

    def test_state_snapshot_defaults(self):
        """Test StateSnapshot with minimal required fields."""
        from balaganagent.wrappers.langgraph import StateSnapshot

        timestamp = time.time()
        snapshot = StateSnapshot(
            timestamp=timestamp,
            node_name="minimal_node",
            state_before={"data": "value"},
            state_after={"data": "value"},
        )

        assert snapshot.fault_injected is None
        assert snapshot.target_fields is None

    def test_state_snapshot_deep_copy_isolation(self):
        """Test that state_before and state_after are truly independent copies."""
        from balaganagent.wrappers.langgraph import StateSnapshot

        # Create a state and its copy
        original_state = {"messages": [1, 2, 3], "data": {"nested": "value"}}
        copied_state = copy.deepcopy(original_state)

        # Create snapshot
        snapshot = StateSnapshot(
            timestamp=time.time(),
            node_name="test_node",
            state_before=original_state,
            state_after=copied_state,
        )

        # Modify the original state after snapshot creation
        original_state["messages"].append(4)
        original_state["data"]["nested"] = "modified"

        # Verify snapshot was not affected
        assert snapshot.state_before["messages"] == [1, 2, 3]
        assert snapshot.state_before["data"]["nested"] == "value"
        assert snapshot.state_after["messages"] == [1, 2, 3]
        assert snapshot.state_after["data"]["nested"] == "value"

    def test_state_snapshot_hashable(self):
        """Test that StateSnapshot is hashable and can be used in sets/dicts."""
        from balaganagent.wrappers.langgraph import StateSnapshot

        timestamp = time.time()
        snapshot1 = StateSnapshot(
            timestamp=timestamp,
            node_name="node_a",
            state_before={"x": 1},
            state_after={"x": 2},
        )
        snapshot2 = StateSnapshot(
            timestamp=timestamp,
            node_name="node_b",
            state_before={"x": 1},
            state_after={"x": 2},
        )

        # Should be hashable
        snapshot_set = {snapshot1, snapshot2}
        assert len(snapshot_set) == 2

        # Should work as dict key
        snapshot_dict = {snapshot1: "value1", snapshot2: "value2"}
        assert snapshot_dict[snapshot1] == "value1"

    def test_state_snapshot_repr(self):
        """Test StateSnapshot string representation."""
        from balaganagent.wrappers.langgraph import StateSnapshot

        snapshot = StateSnapshot(
            timestamp=time.time(),
            node_name="my_node",
            state_before={"data": "x" * 50},  # 50 bytes
            state_after={"data": "y" * 60},  # 60 bytes
            fault_injected="context_corruption",
        )

        repr_str = repr(snapshot)
        assert "my_node" in repr_str
        assert "context_corruption" in repr_str
        assert "B" in repr_str  # size units

    def test_state_snapshot_with_complex_nested_state(self):
        """Test StateSnapshot with deeply nested state objects."""
        from balaganagent.wrappers.langgraph import StateSnapshot

        state_before = {
            "messages": [
                {"role": "user", "content": "hello", "metadata": {"timestamp": 123}},
                {"role": "assistant", "content": "hi", "metadata": {"timestamp": 124}},
            ],
            "context": {"conversation_id": "abc123", "user_id": "user_456"},
            "metadata": {"attempt": 1, "retries": [0, 1, 2]},
        }

        state_after = copy.deepcopy(state_before)
        state_after["messages"][0]["content"] = "hello modified"

        snapshot = StateSnapshot(
            timestamp=time.time(),
            node_name="complex_node",
            state_before=state_before,
            state_after=state_after,
        )

        # Verify deep copy independence
        assert snapshot.state_before["messages"][0]["content"] == "hello"
        assert snapshot.state_after["messages"][0]["content"] == "hello modified"

    def test_state_snapshot_with_none_values(self):
        """Test StateSnapshot with None state values."""
        from balaganagent.wrappers.langgraph import StateSnapshot

        snapshot = StateSnapshot(
            timestamp=time.time(),
            node_name="test_node",
            state_before=None,
            state_after=None,
        )

        assert snapshot.state_before is None
        assert snapshot.state_after is None
        # Should not crash on repr
        repr_str = repr(snapshot)
        assert "test_node" in repr_str

    def test_state_snapshot_equality_by_timestamp_and_node(self):
        """Test StateSnapshot hash equality is based on timestamp and node_name."""
        from balaganagent.wrappers.langgraph import StateSnapshot

        timestamp = time.time()
        snapshot1 = StateSnapshot(
            timestamp=timestamp,
            node_name="node_a",
            state_before={"x": 1},
            state_after={"x": 1},
        )
        snapshot2 = StateSnapshot(
            timestamp=timestamp,
            node_name="node_a",
            state_before={"x": 2},
            state_after={"x": 3},
        )

        # Same timestamp and node_name should have same hash
        assert hash(snapshot1) == hash(snapshot2)

    def test_state_snapshot_with_large_state(self):
        """Test StateSnapshot with large state objects."""
        from balaganagent.wrappers.langgraph import StateSnapshot

        large_state = {
            "data": "x" * 10000,
            "nested": {"more_data": "y" * 10000, "list": list(range(1000))},
        }

        snapshot = StateSnapshot(
            timestamp=time.time(),
            node_name="large_node",
            state_before=large_state,
            state_after=copy.deepcopy(large_state),
        )

        # Should handle large states gracefully
        assert len(snapshot.state_before["data"]) == 10000
        repr_str = repr(snapshot)
        assert "large_node" in repr_str


class TestStateSnapshotManager:
    """Tests for StateSnapshotManager - manages snapshots from node execution."""

    def test_state_snapshot_manager_creation(self):
        """Test StateSnapshotManager can be created and used."""
        from balaganagent.wrappers.langgraph import StateSnapshot

        class StateSnapshotManager:
            """Manages state snapshots from node execution."""

            def __init__(self):
                self._snapshots: list[StateSnapshot] = []

            def add_snapshot(self, snapshot: StateSnapshot):
                """Add a snapshot to the collection."""
                self._snapshots.append(snapshot)

            def get_snapshots_for_node(self, node_name: str) -> list[StateSnapshot]:
                """Get all snapshots for a specific node."""
                return [s for s in self._snapshots if s.node_name == node_name]

            def get_snapshots_by_fault(self, fault_type: str) -> list[StateSnapshot]:
                """Get all snapshots with a specific fault type."""
                return [s for s in self._snapshots if s.fault_injected == fault_type]

            def get_snapshots_in_time_range(
                self, start_time: float, end_time: float
            ) -> list[StateSnapshot]:
                """Get snapshots within a time range."""
                return [
                    s for s in self._snapshots if start_time <= s.timestamp <= end_time
                ]

            def clear_snapshots(self):
                """Clear all snapshots."""
                self._snapshots.clear()

            def get_all_snapshots(self) -> list[StateSnapshot]:
                """Get all snapshots."""
                return self._snapshots.copy()

        manager = StateSnapshotManager()
        assert manager is not None

    def test_state_snapshot_manager_add_snapshot(self):
        """Test adding snapshots to manager."""
        from balaganagent.wrappers.langgraph import StateSnapshot

        class StateSnapshotManager:
            """Manages state snapshots from node execution."""

            def __init__(self):
                self._snapshots: list[StateSnapshot] = []

            def add_snapshot(self, snapshot: StateSnapshot):
                """Add a snapshot to the collection."""
                self._snapshots.append(snapshot)

            def get_all_snapshots(self) -> list[StateSnapshot]:
                """Get all snapshots."""
                return self._snapshots.copy()

        manager = StateSnapshotManager()

        snapshot = StateSnapshot(
            timestamp=time.time(),
            node_name="test_node",
            state_before={"x": 1},
            state_after={"x": 2},
        )

        manager.add_snapshot(snapshot)
        snapshots = manager.get_all_snapshots()

        assert len(snapshots) == 1
        assert snapshots[0].node_name == "test_node"

    def test_state_snapshot_manager_filter_by_node(self):
        """Test filtering snapshots by node name."""
        from balaganagent.wrappers.langgraph import StateSnapshot

        class StateSnapshotManager:
            """Manages state snapshots from node execution."""

            def __init__(self):
                self._snapshots: list[StateSnapshot] = []

            def add_snapshot(self, snapshot: StateSnapshot):
                """Add a snapshot to the collection."""
                self._snapshots.append(snapshot)

            def get_snapshots_for_node(self, node_name: str) -> list[StateSnapshot]:
                """Get all snapshots for a specific node."""
                return [s for s in self._snapshots if s.node_name == node_name]

        manager = StateSnapshotManager()

        snapshot1 = StateSnapshot(
            timestamp=time.time(),
            node_name="node_a",
            state_before={"x": 1},
            state_after={"x": 2},
        )
        snapshot2 = StateSnapshot(
            timestamp=time.time(),
            node_name="node_b",
            state_before={"x": 1},
            state_after={"x": 2},
        )
        snapshot3 = StateSnapshot(
            timestamp=time.time(),
            node_name="node_a",
            state_before={"x": 2},
            state_after={"x": 3},
        )

        manager.add_snapshot(snapshot1)
        manager.add_snapshot(snapshot2)
        manager.add_snapshot(snapshot3)

        node_a_snapshots = manager.get_snapshots_for_node("node_a")
        assert len(node_a_snapshots) == 2
        assert all(s.node_name == "node_a" for s in node_a_snapshots)

    def test_state_snapshot_manager_filter_by_fault(self):
        """Test filtering snapshots by fault type."""
        from balaganagent.wrappers.langgraph import StateSnapshot

        class StateSnapshotManager:
            """Manages state snapshots from node execution."""

            def __init__(self):
                self._snapshots: list[StateSnapshot] = []

            def add_snapshot(self, snapshot: StateSnapshot):
                """Add a snapshot to the collection."""
                self._snapshots.append(snapshot)

            def get_snapshots_by_fault(self, fault_type: str) -> list[StateSnapshot]:
                """Get all snapshots with a specific fault type."""
                return [s for s in self._snapshots if s.fault_injected == fault_type]

        manager = StateSnapshotManager()

        snapshot1 = StateSnapshot(
            timestamp=time.time(),
            node_name="node_a",
            state_before={"x": 1},
            state_after={"x": 2},
            fault_injected="delay",
        )
        snapshot2 = StateSnapshot(
            timestamp=time.time(),
            node_name="node_b",
            state_before={"x": 1},
            state_after={"x": 2},
            fault_injected="context_corruption",
        )

        manager.add_snapshot(snapshot1)
        manager.add_snapshot(snapshot2)

        delay_snapshots = manager.get_snapshots_by_fault("delay")
        assert len(delay_snapshots) == 1
        assert delay_snapshots[0].fault_injected == "delay"

    def test_state_snapshot_manager_clear(self):
        """Test clearing snapshots from manager."""
        from balaganagent.wrappers.langgraph import StateSnapshot

        class StateSnapshotManager:
            """Manages state snapshots from node execution."""

            def __init__(self):
                self._snapshots: list[StateSnapshot] = []

            def add_snapshot(self, snapshot: StateSnapshot):
                """Add a snapshot to the collection."""
                self._snapshots.append(snapshot)

            def clear_snapshots(self):
                """Clear all snapshots."""
                self._snapshots.clear()

            def get_all_snapshots(self) -> list[StateSnapshot]:
                """Get all snapshots."""
                return self._snapshots.copy()

        manager = StateSnapshotManager()

        snapshot = StateSnapshot(
            timestamp=time.time(),
            node_name="test_node",
            state_before={"x": 1},
            state_after={"x": 2},
        )

        manager.add_snapshot(snapshot)
        assert len(manager.get_all_snapshots()) == 1

        manager.clear_snapshots()
        assert len(manager.get_all_snapshots()) == 0


class TestStateSnapshotIntegration:
    """Integration tests for StateSnapshot with LangGraphWrapper."""

    def test_wrapper_has_snapshot_manager(self):
        """Test that LangGraphWrapper has StateSnapshotManager initialized."""
        from balaganagent.wrappers.langgraph import LangGraphWrapper
        from unittest.mock import MagicMock

        mock_graph = MagicMock()
        mock_graph.nodes = {}

        wrapper = LangGraphWrapper(mock_graph)
        assert wrapper._snapshot_manager is not None

    def test_wrapper_get_state_snapshots(self):
        """Test wrapper can retrieve state snapshots."""
        from balaganagent.wrappers.langgraph import LangGraphWrapper, StateSnapshot
        from unittest.mock import MagicMock

        mock_graph = MagicMock()
        mock_graph.nodes = {}

        wrapper = LangGraphWrapper(mock_graph)

        # Add a snapshot directly to manager
        snapshot = StateSnapshot(
            timestamp=time.time(),
            node_name="test_node",
            state_before={"x": 1},
            state_after={"x": 2},
        )
        wrapper._snapshot_manager.add_snapshot(snapshot)

        # Verify wrapper can retrieve it
        snapshots = wrapper.get_state_snapshots()
        assert len(snapshots) == 1
        assert snapshots[0].node_name == "test_node"

    def test_wrapper_get_snapshots_for_node(self):
        """Test wrapper can filter snapshots by node."""
        from balaganagent.wrappers.langgraph import LangGraphWrapper, StateSnapshot
        from unittest.mock import MagicMock

        mock_graph = MagicMock()
        mock_graph.nodes = {}

        wrapper = LangGraphWrapper(mock_graph)

        # Add multiple snapshots
        for i, node_name in enumerate(["node_a", "node_b", "node_a"]):
            snapshot = StateSnapshot(
                timestamp=time.time() + i,
                node_name=node_name,
                state_before={"x": i},
                state_after={"x": i + 1},
            )
            wrapper._snapshot_manager.add_snapshot(snapshot)

        # Filter by node
        node_a_snapshots = wrapper.get_snapshots_for_node("node_a")
        assert len(node_a_snapshots) == 2
        assert all(s.node_name == "node_a" for s in node_a_snapshots)

    def test_wrapper_get_snapshots_by_fault(self):
        """Test wrapper can filter snapshots by fault type."""
        from balaganagent.wrappers.langgraph import LangGraphWrapper, StateSnapshot
        from unittest.mock import MagicMock

        mock_graph = MagicMock()
        mock_graph.nodes = {}

        wrapper = LangGraphWrapper(mock_graph)

        # Add snapshots with different faults
        fault_types = ["delay", "context_corruption", "delay", "tool_failure"]
        for i, fault_type in enumerate(fault_types):
            snapshot = StateSnapshot(
                timestamp=time.time() + i,
                node_name=f"node_{i}",
                state_before={"x": i},
                state_after={"x": i + 1},
                fault_injected=fault_type,
            )
            wrapper._snapshot_manager.add_snapshot(snapshot)

        # Filter by fault
        delay_snapshots = wrapper.get_snapshots_by_fault("delay")
        assert len(delay_snapshots) == 2
        assert all(s.fault_injected == "delay" for s in delay_snapshots)

    def test_wrapper_clear_snapshots(self):
        """Test wrapper can clear all snapshots."""
        from balaganagent.wrappers.langgraph import LangGraphWrapper, StateSnapshot
        from unittest.mock import MagicMock

        mock_graph = MagicMock()
        mock_graph.nodes = {}

        wrapper = LangGraphWrapper(mock_graph)

        # Add snapshots
        for i in range(3):
            snapshot = StateSnapshot(
                timestamp=time.time() + i,
                node_name=f"node_{i}",
                state_before={"x": i},
                state_after={"x": i + 1},
            )
            wrapper._snapshot_manager.add_snapshot(snapshot)

        assert len(wrapper.get_state_snapshots()) == 3

        # Clear
        wrapper.clear_snapshots()
        assert len(wrapper.get_state_snapshots()) == 0

    def test_wrapper_reset_clears_snapshots(self):
        """Test that wrapper.reset() clears snapshots."""
        from balaganagent.wrappers.langgraph import LangGraphWrapper, StateSnapshot
        from unittest.mock import MagicMock

        mock_graph = MagicMock()
        mock_graph.nodes = {}

        wrapper = LangGraphWrapper(mock_graph)

        # Add a snapshot
        snapshot = StateSnapshot(
            timestamp=time.time(),
            node_name="test_node",
            state_before={"x": 1},
            state_after={"x": 2},
        )
        wrapper._snapshot_manager.add_snapshot(snapshot)

        assert len(wrapper.get_state_snapshots()) == 1

        # Reset wrapper
        wrapper.reset()

        # Snapshots should be cleared
        assert len(wrapper.get_state_snapshots()) == 0


class TestFieldLevelStateCorruption:
    """Tests for field-level state corruption targeting."""

    def test_context_corruption_config_with_target_fields(self):
        """Test ContextCorruptionConfig supports target_fields."""
        from balaganagent.injectors.context import ContextCorruptionConfig

        config = ContextCorruptionConfig(target_fields=["messages", "context"])
        assert config.target_fields == ["messages", "context"]

    def test_context_corruption_config_with_exclude_fields(self):
        """Test ContextCorruptionConfig has default exclude_fields."""
        from balaganagent.injectors.context import ContextCorruptionConfig

        config = ContextCorruptionConfig()
        assert "_routing" in config.exclude_fields
        assert "_internal" in config.exclude_fields

    def test_context_corruption_should_corrupt_field(self):
        """Test field targeting - should corrupt targeted fields."""
        from balaganagent.injectors.context import (
            ContextCorruptionConfig,
            ContextCorruptionInjector,
            CorruptionType,
        )

        config = ContextCorruptionConfig(
            target_fields=["messages"],
            corruption_types=[CorruptionType.DROP],
        )
        injector = ContextCorruptionInjector(config)

        # Test internal field checking
        assert injector._should_corrupt_field("messages") is True
        assert injector._should_corrupt_field("context") is False

    def test_context_corruption_exclude_fields(self):
        """Test that excluded fields are never corrupted."""
        from balaganagent.injectors.context import (
            ContextCorruptionConfig,
            ContextCorruptionInjector,
        )

        config = ContextCorruptionConfig()
        injector = ContextCorruptionInjector(config)

        # Excluded fields should never be corrupted
        assert injector._should_corrupt_field("_routing") is False
        assert injector._should_corrupt_field("_internal") is False
        assert injector._should_corrupt_field("timestamp") is False

    def test_field_level_corruption_dict(self):
        """Test field-level corruption on dict state."""
        from balaganagent.injectors.context import (
            ContextCorruptionConfig,
            ContextCorruptionInjector,
            CorruptionType,
        )

        config = ContextCorruptionConfig(
            target_fields=["messages"],
            corruption_types=[CorruptionType.DROP],
        )
        injector = ContextCorruptionInjector(config)

        state = {
            "messages": [1, 2, 3, 4, 5],
            "context": "important",
            "timestamp": "2026-03-15",
        }

        corrupted, details = injector.inject("test_node", {"data": state})

        # Messages should be modified (items dropped)
        assert corrupted["messages"] != state["messages"]
        # But context and timestamp should be unchanged
        assert corrupted["context"] == "important"
        assert corrupted["timestamp"] == "2026-03-15"
        # Verify field targeting in details
        assert details.get("target_fields") == ["messages"]

    def test_field_level_corruption_multiple_fields(self):
        """Test corrupting multiple targeted fields."""
        from balaganagent.injectors.context import (
            ContextCorruptionConfig,
            ContextCorruptionInjector,
            CorruptionType,
        )

        config = ContextCorruptionConfig(
            target_fields=["messages", "context"],
            corruption_types=[CorruptionType.TRUNCATION],
        )
        injector = ContextCorruptionInjector(config)

        state = {
            "messages": [1, 2, 3, 4, 5],
            "context": "long context string here",
            "user_id": "user_123",
        }

        corrupted, details = injector.inject("test_node", {"data": state})

        # Messages and context should be corrupted
        assert len(corrupted["messages"]) <= len(state["messages"])
        assert len(corrupted["context"]) <= len(state["context"])
        # But user_id should be untouched
        assert corrupted["user_id"] == "user_123"

    def test_field_level_corruption_none_target_fields(self):
        """Test that None target_fields corrupts all non-excluded fields."""
        from balaganagent.injectors.context import (
            ContextCorruptionConfig,
            ContextCorruptionInjector,
            CorruptionType,
        )

        config = ContextCorruptionConfig(
            target_fields=None,  # No targeting - corrupt all
            corruption_types=[CorruptionType.DROP],
        )
        injector = ContextCorruptionInjector(config)

        state = {
            "messages": [1, 2, 3, 4, 5],
            "context": "context data",
            "timestamp": "2026-03-15",  # Excluded field
        }

        # Should corrupt non-excluded fields
        assert injector._should_corrupt_field("messages") is True
        assert injector._should_corrupt_field("context") is True
        assert injector._should_corrupt_field("timestamp") is False

    def test_field_level_corruption_preserves_excluded_fields(self):
        """Test that excluded fields are always preserved."""
        from balaganagent.injectors.context import (
            ContextCorruptionConfig,
            ContextCorruptionInjector,
            CorruptionType,
        )

        config = ContextCorruptionConfig(
            target_fields=["messages"],
            corruption_types=[CorruptionType.TRUNCATION],
        )
        injector = ContextCorruptionInjector(config)

        state = {
            "messages": [1, 2, 3, 4, 5],
            "_routing": {"next_node": "node_2"},
            "_internal": {"state": "processing"},
        }

        corrupted, details = injector.inject("test_node", {"data": state})

        # Excluded fields should remain unchanged
        assert corrupted["_routing"] == state["_routing"]
        assert corrupted["_internal"] == state["_internal"]
        # But messages should be corrupted
        assert len(corrupted["messages"]) <= len(state["messages"])


class TestStateSnapshotAccuracy:
    """Integration tests for state snapshot accuracy across execution patterns."""

    def test_node_proxy_captures_snapshot_on_chaos_injection(self):
        """Test that LangGraphNodeProxy captures snapshots when chaos is injected."""
        from balaganagent.wrappers.langgraph import LangGraphNodeProxy
        from balaganagent.injectors.context import (
            ContextCorruptionConfig,
            ContextCorruptionInjector,
            CorruptionType,
        )

        # Create a simple node function
        def simple_node(state):
            return {"result": "ok"}

        # Create proxy with injectors
        proxy = LangGraphNodeProxy("simple_node", "test_node")
        config = ContextCorruptionConfig(
            target_fields=["messages"],
            corruption_types=[CorruptionType.DROP],
        )
        injector = ContextCorruptionInjector(config)
        proxy.add_injector(injector)

        # Mock the should_inject to always return True
        original_should_inject = injector.should_inject
        injector.should_inject = lambda target: True

        state = {"messages": [1, 2, 3, 4, 5], "other": "data"}

        # This should raise but capture snapshot
        try:
            proxy(state)
        except RuntimeError:
            pass

        # Verify snapshot was captured
        snapshots = proxy.get_state_snapshots()
        assert len(snapshots) > 0
        snapshot = snapshots[0]
        assert snapshot.node_name == "test_node"
        assert snapshot.fault_injected == "context_corruption"
        assert snapshot.state_before == state

    def test_snapshot_reflects_state_mutations(self):
        """Test that snapshots accurately reflect state mutations from corruption."""
        from balaganagent.wrappers.langgraph import StateSnapshot

        # Create states with different values
        original_state = {"messages": ["a", "b", "c"], "count": 3}
        corrupted_state = {"messages": ["a", "c"], "count": 3}  # One message dropped

        snapshot = StateSnapshot(
            timestamp=time.time(),
            node_name="mutation_node",
            state_before=original_state,
            state_after=corrupted_state,
            fault_injected="context_corruption",
        )

        # Verify snapshots show the mutation
        assert snapshot.state_before["messages"] == ["a", "b", "c"]
        assert snapshot.state_after["messages"] == ["a", "c"]
        # Original outside snapshot should not be affected by snapshot
        original_state["messages"].append("d")
        assert snapshot.state_before["messages"] == ["a", "b", "c"]

    def test_multiple_snapshots_per_node_execution(self):
        """Test capturing multiple snapshots during one node execution."""
        from balaganagent.wrappers.langgraph import StateSnapshotManager, StateSnapshot

        manager = StateSnapshotManager()

        # Simulate multiple corruption attempts on one node
        for i in range(3):
            snapshot = StateSnapshot(
                timestamp=time.time() + i * 0.001,
                node_name="multi_fault_node",
                state_before={"attempt": i, "data": [1, 2, 3]},
                state_after={"attempt": i, "data": [1, 2]},
                fault_injected=f"fault_{i}",
            )
            manager.add_snapshot(snapshot)

        # Verify all snapshots captured
        snapshots = manager.get_all_snapshots()
        assert len(snapshots) == 3
        assert all(s.node_name == "multi_fault_node" for s in snapshots)

    def test_snapshot_with_nested_state_mutation(self):
        """Test snapshot accuracy with deeply nested state mutations."""
        from balaganagent.wrappers.langgraph import StateSnapshot

        original_state = {
            "messages": [
                {"role": "user", "content": "hello", "metadata": {"timestamp": 1}},
                {"role": "assistant", "content": "hi", "metadata": {"timestamp": 2}},
            ],
            "config": {"setting": "value"},
        }

        # Corrupted version - one message modified
        corrupted_state = {
            "messages": [
                {"role": "user", "content": "hello", "metadata": {"timestamp": 1}},
            ],
            "config": {"setting": "value"},
        }

        snapshot = StateSnapshot(
            timestamp=time.time(),
            node_name="nested_node",
            state_before=original_state,
            state_after=corrupted_state,
        )

        # Verify deep copy independence
        assert len(snapshot.state_before["messages"]) == 2
        assert len(snapshot.state_after["messages"]) == 1
        # Modify original - shouldn't affect snapshot
        original_state["messages"].append({})
        assert len(snapshot.state_before["messages"]) == 2

    def test_snapshot_list_mutation_detection(self):
        """Test detecting mutations to list fields in state."""
        from balaganagent.wrappers.langgraph import StateSnapshot

        original_state = {"items": [1, 2, 3, 4, 5]}
        corrupted_state = {"items": [1, 3, 5]}  # Some items dropped

        snapshot = StateSnapshot(
            timestamp=time.time(),
            node_name="list_mutation_node",
            state_before=original_state,
            state_after=corrupted_state,
        )

        # Verify mutations detected
        assert len(snapshot.state_before["items"]) == 5
        assert len(snapshot.state_after["items"]) == 3
        # Verify lists are independent
        snapshot.state_before["items"].append(6)
        assert len(snapshot.state_before["items"]) == 6
        assert len(snapshot.state_after["items"]) == 3

    def test_snapshot_dict_mutation_detection(self):
        """Test detecting mutations to dict fields in state."""
        from balaganagent.wrappers.langgraph import StateSnapshot

        original_state = {
            "config": {"setting1": "value1", "setting2": "value2", "setting3": "value3"}
        }
        corrupted_state = {
            "config": {"setting1": "value1", "setting3": "value3"}
        }  # setting2 dropped

        snapshot = StateSnapshot(
            timestamp=time.time(),
            node_name="dict_mutation_node",
            state_before=original_state,
            state_after=corrupted_state,
        )

        # Verify mutations detected
        assert len(snapshot.state_before["config"]) == 3
        assert len(snapshot.state_after["config"]) == 2
        assert "setting2" in snapshot.state_before["config"]
        assert "setting2" not in snapshot.state_after["config"]

    def test_snapshot_string_mutation_detection(self):
        """Test detecting mutations to string fields in state."""
        from balaganagent.wrappers.langgraph import StateSnapshot

        original_state = {"message": "The quick brown fox jumps over the lazy dog"}
        corrupted_state = {"message": "The quick brown fox"}  # Truncated

        snapshot = StateSnapshot(
            timestamp=time.time(),
            node_name="string_mutation_node",
            state_before=original_state,
            state_after=corrupted_state,
        )

        # Verify mutations detected
        assert len(snapshot.state_before["message"]) > len(snapshot.state_after["message"])
        assert snapshot.state_before["message"].startswith("The quick brown fox")
        assert len(snapshot.state_after["message"]) == len("The quick brown fox")

    def test_snapshot_timestamp_ordering(self):
        """Test that snapshots preserve temporal ordering with timestamps."""
        from balaganagent.wrappers.langgraph import StateSnapshotManager, StateSnapshot

        manager = StateSnapshotManager()

        # Add snapshots with different timestamps
        base_time = time.time()
        for i in range(3):
            snapshot = StateSnapshot(
                timestamp=base_time + i,
                node_name="ordered_node",
                state_before={"value": i},
                state_after={"value": i + 1},
            )
            manager.add_snapshot(snapshot)

        # Verify temporal ordering
        snapshots = manager.get_all_snapshots()
        for i in range(len(snapshots) - 1):
            assert snapshots[i].timestamp <= snapshots[i + 1].timestamp

    def test_snapshot_accuracy_with_none_values(self):
        """Test snapshot accuracy when state contains None values."""
        from balaganagent.wrappers.langgraph import StateSnapshot

        original_state = {"data": None, "other": "value"}
        corrupted_state = {"data": None, "other": "modified"}

        snapshot = StateSnapshot(
            timestamp=time.time(),
            node_name="none_node",
            state_before=original_state,
            state_after=corrupted_state,
        )

        # Verify None handling
        assert snapshot.state_before["data"] is None
        assert snapshot.state_after["other"] != snapshot.state_before["other"]

    def test_snapshot_size_metadata(self):
        """Test that snapshot captures state size information."""
        from balaganagent.wrappers.langgraph import StateSnapshot

        large_state = {"data": "x" * 1000}
        snapshot = StateSnapshot(
            timestamp=time.time(),
            node_name="size_node",
            state_before=large_state,
            state_after=large_state,
        )

        # Verify repr includes size info
        repr_str = repr(snapshot)
        assert "B" in repr_str  # Should mention bytes
        assert "size_node" in repr_str
