"""Loads case files from the data/ folder and splits them into stage-tagged blocks so the
interviewer only ever sees the case content that belongs to a stage it has actually reached."""

import re
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / "data"

STAGE_MARKER_RE = re.compile(r"<!--\s*stage:(\d)\s*-->\s*\n")

# Stages that have case-specific question/answer content, mapped to the current_stage value at
# which their content becomes visible to the interviewer. Normally this is "one stage ahead" (so
# the model has what it needs to transition the moment a gate clears), but stage 4 is revealed two
# stages ahead: a candidate may legally skip stage 2 (clarifying questions, optional) and go
# straight from stage 2 into giving a framework, which the interviewer must then evaluate and, if
# it's good, cascade all the way to presenting the first stage-4 question - in the SAME reply,
# while current_stage is still 2. Without stage 4's content available that early, the model has
# nothing real to present and will invent data instead.
REVEAL_THRESHOLD = {3: 2, 4: 2, 5: 4}
CONTENT_STAGES = tuple(REVEAL_THRESHOLD)

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

    Content for a given content-stage is included once `current_stage` reaches its entry in
    REVEAL_THRESHOLD, so the interviewer already has what it needs to transition smoothly (and
    never has to invent data) the moment the candidate clears whatever gate it's currently stuck
    at - including the legal skip-ahead path where stage 2 is skipped entirely.
    """
    parts = [f"CONTEXT (always visible to the candidate):\n{case_data['context']}"]

    for stage in CONTENT_STAGES:
        if current_stage >= REVEAL_THRESHOLD[stage]:
            question_block = case_data["stage_questions"].get(stage, "")
            answer_block = case_data["stage_answer_key"].get(stage, "")
            parts.append(
                f"[STAGE {stage} ({STAGE_LABELS[stage]}) QUESTION(S) — only ask about or "
                f"reference these once stage {stage} is actually reached]\n{question_block}\n\n"
                f"[STAGE {stage} ANSWER KEY — internal reference only, never reveal directly]\n"
                f"{answer_block}"
            )

    return "\n\n---\n\n".join(parts)
