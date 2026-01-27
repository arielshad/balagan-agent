"""Unit tests for the Meeting Notes -> Action Items agent.

TDD Step 1: Write failing tests first, then implement.
"""


class TestSummarizerAgent:
    """Tests for the Summarizer Agent that cleans notes into bullet points."""

    def test_summarizer_returns_bullet_points(self):
        from examples.meeting_notes_agent import SummarizerAgent

        agent = SummarizerAgent()
        raw_notes = (
            "We talked about the login bug, Sarah will check auth, maybe by next week. "
            "Also John mentioned we need to update the docs before the release."
        )
        result = agent.summarize(raw_notes)

        assert isinstance(result, list)
        assert len(result) > 0
        for item in result:
            assert isinstance(item, str)
            assert len(item) > 0

    def test_summarizer_splits_multiple_topics(self):
        from examples.meeting_notes_agent import SummarizerAgent

        agent = SummarizerAgent()
        raw_notes = (
            "Login bug needs fixing. Sarah will handle auth. "
            "Docs need updating before release. John to review API."
        )
        result = agent.summarize(raw_notes)

        assert len(result) >= 2

    def test_summarizer_handles_empty_input(self):
        from examples.meeting_notes_agent import SummarizerAgent

        agent = SummarizerAgent()
        result = agent.summarize("")
        assert isinstance(result, list)
        assert len(result) == 0

    def test_summarizer_handles_single_sentence(self):
        from examples.meeting_notes_agent import SummarizerAgent

        agent = SummarizerAgent()
        result = agent.summarize("Fix the login bug.")
        assert isinstance(result, list)
        assert len(result) == 1


class TestTaskExtractorAgent:
    """Tests for the Task Extractor Agent that turns bullets into action items."""

    def test_extractor_returns_action_items(self):
        from examples.meeting_notes_agent import ActionItem, TaskExtractorAgent

        agent = TaskExtractorAgent()
        bullets = [
            "Sarah will check auth for the login bug by next week",
            "John needs to update the docs before the release",
        ]
        result = agent.extract(bullets)

        assert isinstance(result, list)
        assert len(result) == 2
        for item in result:
            assert isinstance(item, ActionItem)
            assert item.task
            assert item.owner
            assert item.due_date

    def test_extractor_guesses_due_date_when_missing(self):
        from examples.meeting_notes_agent import TaskExtractorAgent

        agent = TaskExtractorAgent()
        bullets = ["Sarah will fix the login bug"]
        result = agent.extract(bullets)

        assert len(result) == 1
        assert result[0].due_date  # should guess a default

    def test_extractor_handles_empty_list(self):
        from examples.meeting_notes_agent import TaskExtractorAgent

        agent = TaskExtractorAgent()
        result = agent.extract([])
        assert result == []

    def test_extractor_parses_owner_from_text(self):
        from examples.meeting_notes_agent import TaskExtractorAgent

        agent = TaskExtractorAgent()
        bullets = ["Alice should review the PR by Friday"]
        result = agent.extract(bullets)

        assert len(result) == 1
        assert result[0].owner == "Alice"

    def test_extractor_parses_due_date_from_text(self):
        from examples.meeting_notes_agent import TaskExtractorAgent

        agent = TaskExtractorAgent()
        bullets = ["Bob will deploy the fix by next Monday"]
        result = agent.extract(bullets)

        assert len(result) == 1
        assert "Monday" in result[0].due_date or "next" in result[0].due_date.lower()


class TestMeetingNotesCrewPipeline:
    """Integration tests for the full pipeline: notes -> bullets -> action items."""

    def test_full_pipeline(self):
        from examples.meeting_notes_agent import MeetingNotesCrew

        crew = MeetingNotesCrew()
        raw_notes = (
            "We talked about the login bug, Sarah will check auth, maybe by next week. "
            "John mentioned we need to update the docs before the release."
        )
        result = crew.process(raw_notes)

        assert isinstance(result, list)
        assert len(result) >= 2
        for item in result:
            assert item.task
            assert item.owner
            assert item.due_date

    def test_pipeline_format_output(self):
        from examples.meeting_notes_agent import MeetingNotesCrew

        crew = MeetingNotesCrew()
        raw_notes = "Sarah will fix the login bug by next week."
        result = crew.process(raw_notes)
        formatted = crew.format_output(result)

        assert isinstance(formatted, str)
        assert "Sarah" in formatted
        assert "login" in formatted.lower() or "fix" in formatted.lower()
