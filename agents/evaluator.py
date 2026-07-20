"""The evaluator agent: scores a completed case interview transcript on the five rubric
dimensions from docs/interview_flow_and_rubric_spec.md Part 2, each with a 1-4 score and one
specific, evidence-based comment - never generic praise or criticism."""

import re

from anthropic import Anthropic

EVALUATOR_MODEL = "claude-sonnet-4-6"

DIMENSIONS = [
    ("RECAP", "Recap & Objective Alignment"),
    ("CLARIFYING", "Clarifying Questions"),
    ("FRAMEWORK", "Framework Structure"),
    ("QUANT", "Quantitative Execution"),
    ("RECOMMENDATION", "Recommendation (CSR)"),
]

IMPROVE_RE = re.compile(r"^IMPROVE[12]\|(.+)$", re.MULTILINE)

SYSTEM_PROMPT_TEMPLATE = """You are grading a completed business/data case interview transcript \
against a fixed five-dimension rubric. You are not the interviewer - you only see the finished \
transcript and must score it after the fact.

CASE ANSWER KEY (ground truth, for checking correctness - never seen by the candidate):
{answer_key}

RUBRIC (score each 1-4; 4 = strong, 1 = missing/weak):
1. RECAP - Recap & Objective Alignment: strong = concise, correctly identifies the real decision \
to be made, phrased as a confirming question. Weak = skipped entirely, or restates the story \
without naming the actual objective.
2. CLARIFYING - Clarifying Questions: strong = sharp, on-topic question(s) covering a real gap \
(goal/scope/time-horizon-type). Weak = vague/scattered/excessive (5+) questions. Skipping this \
stage entirely to go straight to a framework is a legitimate candidate choice per real \
case-interview norms - do not penalize a skip by itself; only score low if questions WERE asked \
and were vague, unfocused, or excessive.
3. FRAMEWORK - Framework Structure: strong = financial-first structure with revenue/cost \
breakdown, customer & market present but brief. Weak = framework missing entirely, all buckets \
given equal unfocused depth, or jumped to numbers with no framework.
4. QUANT - Quantitative Execution: strong = states equation before calculating, labels numbers, \
flags assumptions, correct math, handles follow-ups well. Weak = silent number-crunching with no \
stated logic, unlabeled figures, unstated assumptions, or an unresolved math error.
5. RECOMMENDATION - Recommendation (CSR): strong = clear conclusion tied back to the specific \
numbers calculated, names a real risk, gives a concrete next step, holds up under the \
interviewer's pushback. Weak = conclusion only, generic risk ("market could change"), or caves \
immediately when challenged.

CROSS-CUTTING JUDGMENT for any candidate point outside the core Financial/Customer/Market \
framework (e.g. seasonality, regulatory risk, brand perception): reward it if it's material \
(would plausibly move the profit/decision math in this case), proportionate (brief, doesn't \
derail the quantitative analysis), and justified (candidate explained why it matters here \
specifically) - do not penalize good judgment like this just for falling outside the core \
structure. Flag it if it's long-winded, ungrounded in the case's numbers, or just buzzword \
name-dropping with no reasoning.

Every comment must cite something specific the candidate actually said or didn't say in THIS \
transcript - never generic praise ("good job") or generic criticism ("needs work").

OUTPUT FORMAT - respond with EXACTLY these 7 lines, nothing before, between, or after them \
(pipe-delimited, score is a single digit 1-4):

RECAP|score|comment
CLARIFYING|score|comment
FRAMEWORK|score|comment
QUANT|score|comment
RECOMMENDATION|score|comment
IMPROVE1|specific actionable point
IMPROVE2|specific actionable point
"""


def build_system_prompt(case_data: dict) -> str:
    answer_key_parts = [case_data["context"]]
    for stage in (3, 4, 5):
        block = case_data["stage_answer_key"].get(stage, "")
        if block:
            answer_key_parts.append(block)
    return SYSTEM_PROMPT_TEMPLATE.format(answer_key="\n\n".join(answer_key_parts))


def evaluate_transcript(client: Anthropic, case_data: dict, transcript: list[dict]) -> dict:
    """Score a completed interview transcript.

    Returns {"dimensions": [{"key", "label", "score", "comment"}, ...], "improvements": [str, str],
    "raw_text": str, "parse_ok": bool}. If the model's output doesn't match the required format,
    parse_ok is False and the caller should fall back to showing raw_text as-is instead of
    charting it.
    """
    system_prompt = build_system_prompt(case_data)
    transcript_text = "\n\n".join(
        f"{'CANDIDATE' if m['role'] == 'user' else 'INTERVIEWER'}: {m['content']}"
        for m in transcript
    )
    response = client.messages.create(
        model=EVALUATOR_MODEL,
        max_tokens=800,
        system=system_prompt,
        messages=[{"role": "user", "content": f"TRANSCRIPT:\n\n{transcript_text}"}],
    )
    raw_text = response.content[0].text

    dimensions = []
    for key, label in DIMENSIONS:
        match = re.search(rf"^{key}\|(\d)\|(.+)$", raw_text, re.MULTILINE)
        if not match:
            return {"dimensions": [], "improvements": [], "raw_text": raw_text, "parse_ok": False}
        dimensions.append(
            {"key": key, "label": label, "score": int(match.group(1)), "comment": match.group(2).strip()}
        )

    improvements = [m.strip() for m in IMPROVE_RE.findall(raw_text)]

    return {"dimensions": dimensions, "improvements": improvements, "raw_text": raw_text, "parse_ok": True}
