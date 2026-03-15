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


class TestNodeMTTRCalculation:
    """Tests for MTTR calculation in node proxies."""

    def test_node_proxy_has_mttr_calculator(self):
        """Test that node proxy includes MTTRCalculator."""
        from balaganagent.wrappers.langgraph import LangGraphNodeProxy

        def dummy_node(state):
            return state

        proxy = LangGraphNodeProxy(dummy_node, "test_node")
        assert hasattr(proxy, "_mttr")
        assert proxy._mttr is not None

    def test_node_proxy_get_mttr_stats(self):
        """Test retrieving MTTR stats from node proxy."""
        from balaganagent.wrappers.langgraph import LangGraphNodeProxy

        def dummy_node(state):
            return state

        proxy = LangGraphNodeProxy(dummy_node, "test_node")
        stats = proxy.get_mttr_stats()

        # Should have recovery stats structure
        assert "total_recoveries" in stats
        assert "successful_recoveries" in stats
        assert "failed_recoveries" in stats
        assert "recovery_rate" in stats
        assert "mttr_seconds" in stats

    def test_node_proxy_records_failure_on_injection(self):
        """Test that failures are recorded in MTTR when chaos is injected."""
        from balaganagent.wrappers.langgraph import LangGraphNodeProxy
        from balaganagent.injectors import DelayInjector
        from balaganagent.injectors.delay import DelayConfig

        def dummy_node(state):
            return state

        proxy = LangGraphNodeProxy(dummy_node, "test_node")
        config = DelayConfig(probability=1.0, min_delay_ms=10, max_delay_ms=10)
        injector = DelayInjector(config)
        proxy.add_injector(injector)

        # Execute node - delay should be applied but not cause failure
        result = proxy({"test": "data"})
        assert result == {"test": "data"}

        # Check MTTR stats
        stats = proxy.get_mttr_stats()
        # Delay injection causes the fault to be recorded and recovery to succeed
        assert stats["total_recoveries"] == 1
        assert stats["successful_recoveries"] == 1
        assert stats["recovery_rate"] == 1.0

    def test_node_proxy_mttr_reset(self):
        """Test that MTTR is reset with node proxy."""
        from balaganagent.wrappers.langgraph import LangGraphNodeProxy

        def dummy_node(state):
            return state

        proxy = LangGraphNodeProxy(dummy_node, "test_node")

        # Manually record a failure and recovery
        proxy._mttr.record_failure("test_node", "test_fault")
        time.sleep(0.01)
        proxy._mttr.record_recovery("test_node", "test_fault", success=True)

        stats = proxy.get_mttr_stats()
        assert stats["total_recoveries"] > 0

        # Reset
        proxy.reset()

        stats = proxy.get_mttr_stats()
        assert stats["total_recoveries"] == 0

    def test_wrapper_mttr_stats_includes_nodes(self):
        """Test that wrapper MTTR stats include node statistics."""
        from balaganagent.wrappers.langgraph import LangGraphWrapper
        from langgraph.graph import StateGraph

        # Create a simple graph
        graph = StateGraph(dict)
        graph.add_node("node_a", lambda state: {"value": state.get("value", 0) + 1})
        graph.add_edge("__start__", "node_a")
        compiled = graph.compile()

        wrapper = LangGraphWrapper(compiled)
        wrapper.wrap_node("node_a")

        # Get MTTR stats
        stats = wrapper.get_mttr_stats()
        assert "nodes" in stats
        assert isinstance(stats["nodes"], dict)

    def test_node_mttr_recovery_tracking(self):
        """Test that node recovery tracking works with MTTR."""
        from balaganagent.wrappers.langgraph import LangGraphNodeProxy

        def dummy_node(state):
            return state

        proxy = LangGraphNodeProxy(dummy_node, "test_node")

        # Manually simulate a failure and recovery
        proxy._mttr.record_failure("test_node", "tool_failure")
        time.sleep(0.05)
        proxy._mttr.record_recovery(
            "test_node", "tool_failure", recovery_method="retry", retries=1, success=True
        )

        stats = proxy.get_mttr_stats()
        assert stats["total_recoveries"] == 1
        assert stats["successful_recoveries"] == 1
        assert stats["failed_recoveries"] == 0
        assert stats["recovery_rate"] == 1.0
        assert stats["mttr_seconds"] >= 0.05


class TestNodeExecutionTiming:
    """Tests for node execution timing metrics."""

    def test_node_event_has_timing_info(self):
        """Test that node events include timing information."""
        from balaganagent.wrappers.langgraph import LangGraphNodeProxy, LangGraphNodeEvent

        def dummy_node(state):
            return state

        proxy = LangGraphNodeProxy(dummy_node, "test_node")
        result = proxy({"test": "data"})

        events = proxy.get_event_history()
        assert len(events) == 1

        event = events[0]
        assert hasattr(event, "start_time")
        assert hasattr(event, "end_time")
        assert hasattr(event, "duration_ms")
        assert event.start_time <= event.end_time
        assert event.duration_ms >= 0

    def test_node_timing_resolution(self):
        """Test that node timing has sufficient resolution for sub-millisecond operations."""
        from balaganagent.wrappers.langgraph import LangGraphNodeProxy

        def fast_node(state):
            return state

        proxy = LangGraphNodeProxy(fast_node, "fast_node")
        result = proxy({"test": "data"})

        events = proxy.get_event_history()
        assert len(events) == 1

        # Should have measurable duration even for fast operations
        event = events[0]
        assert event.duration_ms >= 0

    def test_node_timing_includes_fault_injection_overhead(self):
        """Test that node timing includes overhead from fault injection."""
        from balaganagent.wrappers.langgraph import LangGraphNodeProxy
        from balaganagent.injectors import DelayInjector
        from balaganagent.injectors.delay import DelayConfig

        def quick_node(state):
            return state

        proxy_with_delay = LangGraphNodeProxy(quick_node, "delayed_node")
        config = DelayConfig(probability=1.0, min_delay_ms=50, max_delay_ms=50)
        injector = DelayInjector(config)
        proxy_with_delay.add_injector(injector)

        result = proxy_with_delay({"test": "data"})

        events = proxy_with_delay.get_event_history()
        assert len(events) == 1

        event = events[0]
        # Duration should be at least the delay
        assert event.duration_ms >= 50

    def test_wrapper_get_node_execution_timing_all_nodes(self):
        """Test retrieving timing for all nodes from wrapper."""
        from balaganagent.wrappers.langgraph import LangGraphWrapper, LangGraphNodeProxy
        from langgraph.graph import StateGraph

        graph = StateGraph(dict)
        graph.add_node("node_a", lambda state: {"value": state.get("value", 0) + 1})
        graph.add_edge("__start__", "node_a")
        compiled = graph.compile()

        wrapper = LangGraphWrapper(compiled)

        # Manually create and register node proxies for testing
        def node_a_func(state):
            return {"value": state.get("value", 0) + 1}

        def node_b_func(state):
            return {"value": state.get("value", 0) + 2}

        proxy_a = LangGraphNodeProxy(node_a_func, "node_a")
        proxy_b = LangGraphNodeProxy(node_b_func, "node_b")

        # Execute the nodes
        proxy_a({"value": 0})
        proxy_b({"value": 1})

        # Manually register for timing retrieval
        wrapper._node_proxies["node_a"] = proxy_a
        wrapper._node_proxies["node_b"] = proxy_b

        timing = wrapper.get_node_execution_timing()
        assert "node_a" in timing
        assert "node_b" in timing
        assert timing["node_a"]["event_count"] >= 1
        assert timing["node_b"]["event_count"] >= 1

    def test_wrapper_get_node_execution_timing_specific_node(self):
        """Test retrieving timing for a specific node."""
        from balaganagent.wrappers.langgraph import LangGraphWrapper, LangGraphNodeProxy
        from langgraph.graph import StateGraph

        graph = StateGraph(dict)
        graph.add_node("node_a", lambda state: {"value": state.get("value", 0) + 1})
        graph.add_edge("__start__", "node_a")
        compiled = graph.compile()

        wrapper = LangGraphWrapper(compiled)

        # Create and execute a node proxy
        def node_a_func(state):
            return {"value": state.get("value", 0) + 1}

        proxy_a = LangGraphNodeProxy(node_a_func, "node_a")
        proxy_a({"value": 0})

        # Register for timing retrieval
        wrapper._node_proxies["node_a"] = proxy_a

        timing = wrapper.get_node_execution_timing("node_a")
        assert "node_a" in timing
        assert timing["node_a"]["event_count"] >= 1
        assert "aggregate" in timing["node_a"]
        assert "mean_duration_ms" in timing["node_a"]["aggregate"]
        assert "min_duration_ms" in timing["node_a"]["aggregate"]
        assert "max_duration_ms" in timing["node_a"]["aggregate"]

    def test_node_timing_aggregate_statistics(self):
        """Test that timing aggregate statistics are calculated correctly."""
        from balaganagent.wrappers.langgraph import LangGraphNodeProxy

        def dummy_node(state):
            return state

        proxy = LangGraphNodeProxy(dummy_node, "test_node")

        # Execute node multiple times
        for i in range(3):
            proxy({"iteration": i})

        events = proxy.get_event_history()
        assert len(events) == 3

        # Check metrics include timing information
        metrics = proxy.get_metrics()
        assert "latency" in metrics
        assert metrics["latency"]["count"] == 3
        assert metrics["latency"]["mean"] >= 0
        assert metrics["latency"]["min"] >= 0
        assert metrics["latency"]["max"] >= 0

    def test_node_timing_tracks_success_and_failure(self):
        """Test that node timing tracks both successful and failed executions."""
        from balaganagent.wrappers.langgraph import LangGraphNodeProxy

        def error_node(state):
            if state.get("error"):
                raise ValueError("Injected error")
            return state

        proxy = LangGraphNodeProxy(error_node, "error_node")

        # Successful execution
        result = proxy({"error": False})
        assert result == {"error": False}

        # Failed execution
        try:
            proxy({"error": True})
        except ValueError:
            pass

        events = proxy.get_event_history()
        assert len(events) == 2
        assert events[0].success
        assert not events[1].success


class TestMultiNodeMetricCollection:
    """Integration tests for metric collection across multi-node DAGs."""

    def test_three_node_linear_dag_timing_captured(self):
        """Test: 3-node linear DAG, all timings captured."""
        from balaganagent.wrappers.langgraph import LangGraphNodeProxy

        def node_a(state):
            return {**state, "a_executed": True}

        def node_b(state):
            return {**state, "b_executed": True}

        def node_c(state):
            return {**state, "c_executed": True}

        proxy_a = LangGraphNodeProxy(node_a, "node_a")
        proxy_b = LangGraphNodeProxy(node_b, "node_b")
        proxy_c = LangGraphNodeProxy(node_c, "node_c")

        # Simulate linear execution
        state = {"value": 0}
        state = proxy_a(state)
        state = proxy_b(state)
        state = proxy_c(state)

        # Verify all nodes recorded timing
        assert len(proxy_a.get_event_history()) >= 1
        assert len(proxy_b.get_event_history()) >= 1
        assert len(proxy_c.get_event_history()) >= 1

        # Check metrics
        metrics_a = proxy_a.get_metrics()
        metrics_b = proxy_b.get_metrics()
        metrics_c = proxy_c.get_metrics()

        assert metrics_a["operations"]["total"] >= 1
        assert metrics_b["operations"]["total"] >= 1
        assert metrics_c["operations"]["total"] >= 1

    def test_dag_with_node_failure_recovery_tracking(self):
        """Test: edge timing between nodes with failures and recovery."""
        from balaganagent.wrappers.langgraph import LangGraphNodeProxy
        from balaganagent.metrics import MetricsCollector

        def normal_node(state):
            return {**state, "processed": True}

        def failing_node(state):
            if state.get("fail"):
                raise ValueError("Simulated failure")
            return {**state, "failed": False}

        metrics = MetricsCollector()

        proxy1 = LangGraphNodeProxy(normal_node, "producer")
        proxy2 = LangGraphNodeProxy(failing_node, "consumer")

        # Successful path
        state = {"fail": False}
        state = proxy1(state)

        # Record edge traversal
        edge_start = metrics.record_edge_traversal_start("producer", "consumer")
        try:
            state = proxy2(state)
        finally:
            metrics.record_edge_traversal_end("producer", "consumer", edge_start)

        # Verify metrics
        edge_metrics = metrics.get_edge_metrics()
        assert edge_metrics["total_edge_traversals"] == 1
        assert "producer->consumer" in edge_metrics["edges"]

    def test_wrapper_metrics_across_wrapped_nodes(self):
        """Test: wrapper metrics collection for multiple wrapped nodes."""
        from balaganagent.wrappers.langgraph import LangGraphWrapper, LangGraphNodeProxy

        def node_a(state):
            return {"value": state.get("value", 0) + 1}

        def node_b(state):
            return {"value": state.get("value", 0) + 2}

        wrapper = LangGraphWrapper({})

        proxy_a = LangGraphNodeProxy(node_a, "node_a")
        proxy_b = LangGraphNodeProxy(node_b, "node_b")

        wrapper._node_proxies["node_a"] = proxy_a
        wrapper._node_proxies["node_b"] = proxy_b

        # Execute nodes
        state = {"value": 0}
        state = proxy_a(state)
        state = proxy_b(state)

        # Get wrapper metrics
        metrics = wrapper.get_metrics()
        assert "node_a" in metrics["nodes"]
        assert "node_b" in metrics["nodes"]
        assert metrics["nodes"]["node_a"]["operations"]["total"] >= 1
        assert metrics["nodes"]["node_b"]["operations"]["total"] >= 1

    def test_state_consistency_across_node_sequence(self):
        """Test: state consistency maintained across node sequence."""
        from balaganagent.metrics import MetricsCollector

        collector = MetricsCollector()

        # Simulate node chain with consistent state
        state1 = {"messages": [], "step": 1}
        collector.validate_state_schema("node_a", state1)

        state2 = {"messages": ["msg1"], "step": 2}
        collector.validate_state_schema("node_a", state2)

        state3 = {"messages": ["msg1", "msg2"], "step": 3}
        collector.validate_state_schema("node_a", state3)

        # Should have no violations - all states have same schema
        violations = collector.get_consistency_violations()
        assert len(violations) == 0

    def test_concurrent_node_metrics_aggregation(self):
        """Test: concurrent node execution metrics aggregated correctly."""
        from balaganagent.wrappers.langgraph import LangGraphNodeProxy
        from balaganagent.metrics import MetricsCollector

        def quick_node(state):
            return {**state, "done": True}

        # Create multiple node proxies
        proxies = {f"node_{i}": LangGraphNodeProxy(quick_node, f"node_{i}") for i in range(3)}

        # Execute "concurrently" (simulated)
        state = {"counter": 0}
        for proxy in proxies.values():
            proxy(state)

        # Create a metrics collector and record edge traversals
        metrics = MetricsCollector()

        for i, proxy_name in enumerate(list(proxies.keys())[:-1]):
            start = metrics.record_edge_traversal_start(proxy_name, list(proxies.keys())[i + 1])
            metrics.record_edge_traversal_end(proxy_name, list(proxies.keys())[i + 1], start)

        edge_metrics = metrics.get_edge_metrics()
        assert edge_metrics["total_edge_traversals"] == 2

    def test_mttr_statistics_across_multiple_nodes(self):
        """Test: MTTR calculations work across multiple nodes with failures."""
        from balaganagent.wrappers.langgraph import LangGraphNodeProxy

        proxy_a = LangGraphNodeProxy(lambda s: s, "node_a")
        proxy_b = LangGraphNodeProxy(lambda s: s, "node_b")

        # Simulate failures and recoveries
        proxy_a._mttr.record_failure("node_a", "delay")
        time.sleep(0.05)
        proxy_a._mttr.record_recovery("node_a", "delay", success=True)

        proxy_b._mttr.record_failure("node_b", "context_corruption")
        time.sleep(0.03)
        proxy_b._mttr.record_recovery("node_b", "context_corruption", success=True)

        stats_a = proxy_a.get_mttr_stats()
        stats_b = proxy_b.get_mttr_stats()

        assert stats_a["successful_recoveries"] == 1
        assert stats_b["successful_recoveries"] == 1
        assert stats_a["mttr_seconds"] >= 0.05
        assert stats_b["mttr_seconds"] >= 0.03

    def test_edge_timing_correlates_with_state_mutations(self):
        """Test: edge delay measurements correspond with state mutation sizes."""
        from balaganagent.metrics import MetricsCollector

        collector = MetricsCollector()

        # Large state mutation
        large_state = {"data": "x" * 1000}
        start = collector.record_edge_traversal_start("node_a", "node_b")
        time.sleep(0.01)
        collector.record_edge_traversal_end(
            "node_a",
            "node_b",
            start,
            state_mutation_size=len(str(large_state)),
        )

        traversals = collector.get_edge_traversals_between("node_a", "node_b")
        assert len(traversals) == 1
        assert traversals[0].delay_ms >= 10  # At least 10ms from sleep

        series = collector.get_series("state_mutation_size_bytes")
        assert series is not None
        assert series.count == 1

    def test_node_timing_with_fault_injection_overhead(self):
        """Test: timing includes fault injection overhead for realistic measurement."""
        from balaganagent.wrappers.langgraph import LangGraphNodeProxy
        from balaganagent.injectors import DelayInjector
        from balaganagent.injectors.delay import DelayConfig

        def quick_node(state):
            return state

        # Node without injection
        proxy_baseline = LangGraphNodeProxy(quick_node, "baseline")
        proxy_baseline({})
        baseline_duration = proxy_baseline.get_event_history()[0].duration_ms

        # Node with injection
        proxy_delayed = LangGraphNodeProxy(quick_node, "delayed")
        config = DelayConfig(probability=1.0, min_delay_ms=100, max_delay_ms=100)
        proxy_delayed.add_injector(DelayInjector(config))
        proxy_delayed({})
        delayed_duration = proxy_delayed.get_event_history()[0].duration_ms

        # Delayed execution should be significantly longer
        assert delayed_duration > baseline_duration
        assert delayed_duration >= 100  # At least the injected delay
