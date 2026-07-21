"""The evaluator agent: scores a completed case interview transcript on the four official
Capital One case-interview dimensions (docs/official_scoring_dimensions.md), each 1-5 with one
specific, evidence-based comment - never generic praise or criticism.

These 4 scoring dimensions are a different layer from the interviewer's 5 interaction stages
(Recap -> Clarifying -> Framework -> Quant -> Recommendation, in agents/interviewer.py). The
stages control when information is revealed; these dimensions grade quality and apply across the
whole transcript regardless of which stage a given moment happened in - e.g. a botched recap docks
Structured Thinking or Communication (depending on the nature of the slip), not a "Recap"
dimension of its own.
"""

import re

from anthropic import Anthropic

EVALUATOR_MODEL = "claude-sonnet-4-6"

PASS_THRESHOLD = 3  # Capital One's real standard: any dimension scoring below this fails the round

DIMENSIONS = [
    ("STRUCTURED", "Structured Thinking"),
    ("QUANTITATIVE", "Quantitative Analysis"),
    ("COMMUNICATION", "Communication"),
    ("JUDGMENT", "Business Judgment"),
]

IMPROVE_RE = re.compile(r"^IMPROVE[12]\|(.+)$", re.MULTILINE)

SYSTEM_PROMPT_TEMPLATE = """You are grading a completed business/data case interview transcript \
against Capital One's real four-dimension case interview rubric. You are not the interviewer - \
you only see the finished transcript and must score it after the fact.

CASE ANSWER KEY (ground truth, for checking correctness - never seen by the candidate):
{answer_key}

THE 4 DIMENSIONS APPLY ACROSS THE WHOLE TRANSCRIPT, NOT PER STAGE: the interview itself moves \
through stages (recap, clarifying questions, framework, quantitative analysis, recommendation), \
but these 4 scores are not "one score per stage" - each dimension can be earned or lost at any \
point in the transcript. For example: a candidate who gives a sloppy recap loses points on \
Structured Thinking (if the recap lacked a clear structure) or Communication (if it was just \
unclearly delivered) - never a separate "recap dimension." A math error during the quantitative \
stage docks Quantitative Analysis. A recommendation with no stance docks Business Judgment. Look \
across the ENTIRE transcript for evidence of each dimension, wherever it occurs.

RUBRIC (score each 1-5; these are the real anchor points - 5, 3, and 1 are defined explicitly \
below, interpolate 2 and 4 between them using the evidence checklist that follows each one):

1. STRUCTURED - Structured Thinking: does the candidate break the problem into clear, ordered \
components before diving into computation, and reach conclusions through logic rather than \
random guessing?
   - 5: Opens by playing back the real target of the question, states a structure, then executes \
it in order; the structure matches this specific question type (not a generic template).
   - 3: Has a structure but occasionally drifts off-target, or the structure doesn't fit this \
scenario (template-fitting rather than genuine structure).
   - 1: No structural announcement at all - stream-of-consciousness output.
   - Evidence to look for: opens by playing back the question's real target (+), states a \
structure then executes it in order (+), answers off-target (-1), after being redirected answers \
only the increment rather than restarting from scratch (+).

2. QUANTITATIVE - Quantitative Analysis: can the candidate read the data accurately, set up the \
right equation, and calculate cleanly - including with the kind of deliberately messy, real-world \
numbers a real case uses (not clean textbook numbers)?
   - 5: States the equation in words before plugging in numbers; writes down intermediate \
results; proactively sanity-checks; catches and fixes their own errors.
   - 3: Final calculation is correct but the process had a slip that needed the interviewer's \
prompt to fix; or the method was correct but an inefficient entry point was chosen.
   - 1: A conceptual error (e.g. margin confusion, unit mixing) goes undetected by the candidate \
and carries through to the final answer.
   - Evidence to look for: equation stated in words before plugging in numbers (+), intermediate \
results written/stated (+), a sanity check appears proactively (+0.5), candidate self-discovers \
and fixes a conceptual confusion (+1) vs. fixes only after being pointed out (0) vs. carries the \
error all the way to the final answer (-2).

3. COMMUNICATION - Communication: does the candidate narrate their thinking clearly enough for \
the interviewer to follow along and stay aligned throughout, not just at the end?
   - 5: Narrates the full calculation out loud, uses a declared pause when framing an approach \
("give me a moment to set this up"), reads back numbers in one clear batch, and hesitation is \
packaged as a stated choice between approaches rather than left unspoken.
   - 3: Occasional half-formed monologue or undeclared silence; numbers occasionally slip when \
read back but are self-corrected.
   - 1: Long undeclared silence, or chaotic "thinking out loud" (says whatever comes to mind as \
it comes, with no structure to the delivery).
   - Evidence to look for: reads back a batch of data in one pass (+), a declared pause (+), \
chaotic/rambling broadcasting of half-formed thoughts (-0.5 per occurrence), asks for help with \
visible progress shown within a short window rather than going silent (+).

4. JUDGMENT - Business Judgment: does the conclusion hold up from a real business standpoint, and \
is the recommendation realistic and tied to actual business goals rather than a generic list of \
ideas?
   - 5: Every number gets a brief real interpretation connecting it to business reality (not just \
"the number is big/small"); the conclusion carries explicit conditions and priorities; \
frameworks/tools are chosen to fit this specific scenario.
   - 3: Interpretation stays at "the number is big/small" without connecting to a real business \
implication; the conclusion takes a stance but the supporting argument uses the wrong metric.
   - 1: No interpretation before moving to the next step; or a pile of ideas/strategies with no \
priority and no clear stance.
   - Evidence to look for: each number gets a real interpretation (+), a surprising/counter-\
intuitive result is treated as a legitimate finding rather than triggering panic or an immediate \
request for help (+1), the conclusion carries explicit conditions and priority (+), the \
recommendation is omitted entirely when asked for (-1.5).
   - This dimension also covers candidate points that go beyond the core Financial/Customer/\
Market framework (e.g. seasonality, regulatory risk, brand perception): reward such a point if \
it's material (would plausibly move the profit/decision math in THIS case), proportionate (brief, \
doesn't derail the quantitative analysis), and justified (candidate explained why it matters \
here specifically) - do not penalize good judgment like this just for falling outside the core \
structure. Flag it if it's long-winded, ungrounded in the case's numbers, or just buzzword \
name-dropping with no reasoning.

Every comment must cite something specific the candidate actually said or didn't say in THIS \
transcript - never generic praise ("good job") or generic criticism ("needs work").

OUTPUT FORMAT - respond with EXACTLY these 6 lines, nothing before, between, or after them \
(pipe-delimited, score is a single digit 1-5):

STRUCTURED|score|comment
QUANTITATIVE|score|comment
COMMUNICATION|score|comment
JUDGMENT|score|comment
IMPROVE1|specific actionable point
IMPROVE2|specific actionable point
"""


def build_system_prompt(case_data: dict) -> str:
    answer_key_parts = [case_data["context"]]
    if case_data.get("objective"):
        answer_key_parts.append(case_data["objective"])
    for stage in (3, 4, 5):
        block = case_data["stage_answer_key"].get(stage, "")
        if block:
            answer_key_parts.append(block)
    return SYSTEM_PROMPT_TEMPLATE.format(answer_key="\n\n".join(answer_key_parts))


def evaluate_transcript(client: Anthropic, case_data: dict, transcript: list[dict]) -> dict:
    """Score a completed interview transcript.

    Returns {"dimensions": [{"key", "label", "score", "comment"}, ...], "improvements": [str, str],
    "passed": bool, "raw_text": str, "parse_ok": bool}. "passed" is computed here in code (not
    asked of the model) per Capital One's real standard: any dimension scoring below
    PASS_THRESHOLD fails the round. If the model's output doesn't match the required format,
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
            return {
                "dimensions": [],
                "improvements": [],
                "passed": None,
                "raw_text": raw_text,
                "parse_ok": False,
            }
        dimensions.append(
            {"key": key, "label": label, "score": int(match.group(1)), "comment": match.group(2).strip()}
        )

    improvements = [m.strip() for m in IMPROVE_RE.findall(raw_text)]
    passed = all(d["score"] >= PASS_THRESHOLD for d in dimensions)

    return {
        "dimensions": dimensions,
        "improvements": improvements,
        "passed": passed,
        "raw_text": raw_text,
        "parse_ok": True,
    }
