"""Tests for the timestamp markdown file generation."""

import re
from argparse import Namespace
from unittest.mock import patch

from balaganagent.cli import generate_timestamp


class TestGenerateTimestamp:
    """Tests for generate_timestamp CLI command."""

    def test_generates_file(self, tmp_path):
        output = tmp_path / "timestamp.md"
        args = Namespace(output=str(output))

        generate_timestamp(args)

        assert output.exists()

    def test_file_contains_timestamp_header(self, tmp_path):
        output = tmp_path / "timestamp.md"
        args = Namespace(output=str(output))

        generate_timestamp(args)

        content = output.read_text()
        assert content.startswith("# Timestamp\n")

    def test_file_contains_iso_timestamp(self, tmp_path):
        output = tmp_path / "timestamp.md"
        args = Namespace(output=str(output))

        generate_timestamp(args)

        content = output.read_text()
        # ISO 8601 UTC timestamp pattern
        assert re.search(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z", content)

    def test_creates_parent_directories(self, tmp_path):
        output = tmp_path / "nested" / "dir" / "timestamp.md"
        args = Namespace(output=str(output))

        generate_timestamp(args)

        assert output.exists()

    def test_uses_utc_time(self, tmp_path):
        from datetime import datetime, timezone

        output = tmp_path / "timestamp.md"
        args = Namespace(output=str(output))

        with patch("balaganagent.cli.datetime") as mock_dt:
            fixed_time = datetime(2026, 3, 16, 12, 30, 45, tzinfo=timezone.utc)
            mock_dt.now.return_value = fixed_time
            mock_dt.side_effect = lambda *a, **kw: datetime(*a, **kw)
            # Keep timezone accessible
            mock_dt.now.return_value = fixed_time

            generate_timestamp(args)

        content = output.read_text()
        assert "2026-03-16T12:30:45Z" in content

    def test_overwrites_existing_file(self, tmp_path):
        output = tmp_path / "timestamp.md"
        output.write_text("old content")
        args = Namespace(output=str(output))

        generate_timestamp(args)

        content = output.read_text()
        assert "old content" not in content
        assert "# Timestamp" in content
