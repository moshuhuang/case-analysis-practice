"""Loads case files from the data/ folder and splits them into stage-tagged blocks so the
interviewer only ever sees the case content that belongs to a stage it has actually reached."""

import re
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / "data"

STAGE_MARKER_RE = re.compile(r"<!--\s*stage:(\d)\s*-->\s*\n")

# Stages that have case-specific question/answer content. Stages 0-2 (background, recap,
# clarifying questions) are governed by generic interviewer instructions, not case text.
CONTENT_STAGES = (3, 4, 5)

STAGE_LABELS = {
    0: "Background",
    1: "Recap",
    2: "Clarifying Questions",
    3: "Framework",
    4: "Quantitative Analysis",
    5: "Recommendation",
}


def list_cases() -> dict[str, Path]:
    """Return a mapping of case title -> file path for every case file in data/."""
    cases = {}
    for path in sorted(DATA_DIR.glob("case_*.md")):
        title = path.stem.replace("_", " ").title()
        cases[title] = path
    return cases


def _split_by_stage(section_text: str) -> dict[int, str]:
    """Split a section of text on <!-- stage:N --> markers into {stage_num: block_text}."""
    parts = STAGE_MARKER_RE.split(section_text)
    blocks = {}
    for i in range(1, len(parts), 2):
        blocks[int(parts[i])] = parts[i + 1].strip()
    return blocks


def load_case(path: Path) -> dict:
    """Read a case file and split it into context, stage-tagged questions, and stage-tagged
    answer key entries."""
    full_text = path.read_text(encoding="utf-8")

    context_match = re.search(r"## Context\s*\n(.*?)\n##", full_text, re.S)
    context = context_match.group(1).strip() if context_match else ""

    questions_section = full_text.split("## Questions", 1)[1].split("## Answer Key", 1)[0]
    answer_key_section = full_text.split("## Answer Key", 1)[1]

    return {
        "path": path,
        "context": context,
        "stage_questions": _split_by_stage(questions_section),
        "stage_answer_key": _split_by_stage(answer_key_section),
    }


def get_revealed_content(case_data: dict, current_stage: int) -> str:
    """Assemble the case content the interviewer is allowed to know about right now.

    Content for a given content-stage is included once `current_stage` reaches one stage
    before it, so the interviewer already has what it needs to transition smoothly the
    moment the candidate clears the gate it's currently stuck at.
    """
    parts = [f"CONTEXT (always visible to the candidate):\n{case_data['context']}"]

    for stage in CONTENT_STAGES:
        if current_stage >= stage - 1:
            question_block = case_data["stage_questions"].get(stage, "")
            answer_block = case_data["stage_answer_key"].get(stage, "")
            parts.append(
                f"[STAGE {stage} ({STAGE_LABELS[stage]}) QUESTION(S) — only ask about or "
                f"reference these once stage {stage} is actually reached]\n{question_block}\n\n"
                f"[STAGE {stage} ANSWER KEY — internal reference only, never reveal directly]\n"
                f"{answer_block}"
            )

    return "\n\n---\n\n".join(parts)
