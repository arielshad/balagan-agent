"""Meeting Notes -> Action Items Bot.

A simple CrewAI-style agent pipeline:
1. SummarizerAgent - cleans raw meeting notes into bullet points
2. TaskExtractorAgent - turns bullet points into structured action items

This is a self-contained example that does NOT require an LLM API key.
All logic is rule-based for deterministic, testable behavior.
"""

from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass
class ActionItem:
    """A structured action item extracted from meeting notes."""

    task: str
    owner: str
    due_date: str


# Common name patterns (capitalized words that appear before action verbs)
_ACTION_VERBS = re.compile(
    r"\b(will|should|needs? to|must|has to|going to|is going to)\b",
    re.IGNORECASE,
)

_DUE_DATE_PATTERNS = re.compile(
    r"\b(by\s+(?:next\s+)?(?:Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday"
    r"|tomorrow|end of (?:day|week|month|sprint)|next week|next month"
    r"|EOD|EOM|EOW|\d{1,2}/\d{1,2}(?:/\d{2,4})?))\b",
    re.IGNORECASE,
)

_NAME_PATTERN = re.compile(r"\b([A-Z][a-z]{1,15})\b")


class SummarizerAgent:
    """Cleans raw meeting notes into a list of bullet-point sentences."""

    def summarize(self, raw_notes: str) -> list[str]:
        if not raw_notes or not raw_notes.strip():
            return []

        # Split on sentence boundaries
        sentences = re.split(r"(?<=[.!?])\s+|(?:,\s*(?:also|and)\s+)", raw_notes.strip())
        bullets = []
        for s in sentences:
            s = s.strip().rstrip(".")
            if s and len(s) > 2:
                bullets.append(s)
        return bullets


class TaskExtractorAgent:
    """Extracts structured action items from bullet-point summaries."""

    def extract(self, bullets: list[str]) -> list[ActionItem]:
        if not bullets:
            return []

        items: list[ActionItem] = []
        for bullet in bullets:
            owner = self._extract_owner(bullet)
            due_date = self._extract_due_date(bullet)
            task = self._extract_task(bullet, owner)
            items.append(ActionItem(task=task, owner=owner, due_date=due_date))
        return items

    def _extract_owner(self, text: str) -> str:
        # Find a capitalized name that appears before an action verb
        verb_match = _ACTION_VERBS.search(text)
        if verb_match:
            preceding = text[: verb_match.start()]
            names = _NAME_PATTERN.findall(preceding)
            # Filter out common non-name words
            skip = {"We", "The", "This", "That", "Also", "And", "But", "Maybe", "If", "Or"}
            names = [n for n in names if n not in skip]
            if names:
                return names[-1]

        # Fallback: first capitalized word that looks like a name
        all_names = _NAME_PATTERN.findall(text)
        skip = {"We", "The", "This", "That", "Also", "And", "But", "Maybe", "If", "Or", "Fix"}
        for name in all_names:
            if name not in skip:
                return name
        return "Unassigned"

    def _extract_due_date(self, text: str) -> str:
        match = _DUE_DATE_PATTERNS.search(text)
        if match:
            return match.group(1).strip()
        # Check for loose temporal references
        if re.search(r"\bnext week\b", text, re.IGNORECASE):
            return "next week"
        if re.search(r"\btomorrow\b", text, re.IGNORECASE):
            return "tomorrow"
        return "TBD"

    def _extract_task(self, text: str, owner: str) -> str:
        # Remove the owner name and action verb prefix to get the task description
        task = text
        verb_match = _ACTION_VERBS.search(task)
        if verb_match:
            task = task[verb_match.end() :].strip()
            # Remove leading articles
            task = re.sub(r"^(the|a|an)\s+", "", task, flags=re.IGNORECASE)
        # Remove due date suffix
        task = _DUE_DATE_PATTERNS.sub("", task).strip().rstrip(",. ")
        if not task:
            task = text
        return task[0].upper() + task[1:] if task else text


class MeetingNotesCrew:
    """Pipeline that chains SummarizerAgent -> TaskExtractorAgent.

    Mimics a CrewAI crew with two agents working sequentially.
    """

    def __init__(self):
        self.summarizer = SummarizerAgent()
        self.extractor = TaskExtractorAgent()

    def process(self, raw_notes: str) -> list[ActionItem]:
        bullets = self.summarizer.summarize(raw_notes)
        return self.extractor.extract(bullets)

    def format_output(self, items: list[ActionItem]) -> str:
        lines = []
        for item in items:
            lines.append(f"* {item.task} — **Owner:** {item.owner} — **Due:** {item.due_date}")
        return "\n".join(lines)
