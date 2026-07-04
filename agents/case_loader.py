"""Loads case files from the data/ folder and splits candidate-facing content from the internal answer key."""

import re
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / "data"

ANSWER_KEY_MARKER = "## Answer Key"


def list_cases() -> dict[str, Path]:
    """Return a mapping of case title -> file path for every case file in data/."""
    cases = {}
    for path in sorted(DATA_DIR.glob("case_*.md")):
        title = path.stem.replace("_", " ").title()
        cases[title] = path
    return cases


def load_case(path: Path) -> dict:
    """Read a case file and split it into the candidate-visible part and the full text (with answer key)."""
    full_text = path.read_text(encoding="utf-8")
    marker_index = full_text.find(ANSWER_KEY_MARKER)
    candidate_view = full_text if marker_index == -1 else full_text[:marker_index].strip()
    return {
        "path": path,
        "full_text": full_text,
        "candidate_view": candidate_view,
    }


def extract_context_and_first_question(candidate_view: str) -> tuple[str, str]:
    """Pull out the Context paragraph and the text of Question 1, used to build the interviewer's opening line."""
    context_match = re.search(r"## Context\s*\n(.*?)\n##", candidate_view, re.S)
    context = context_match.group(1).strip() if context_match else ""

    questions_section = candidate_view.split("## Questions", 1)[-1].strip()
    question_blocks = re.split(r"\n(?=Q\d+\.)", questions_section)
    first_question = question_blocks[0].strip() if question_blocks else ""

    return context, first_question
