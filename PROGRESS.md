# Progress Log

Read this together with `PLAN.md` (roadmap + the 2026-07-20 pivot note at the top) and
`CLAUDE.md`/`AGENTS.md` (both point to `docs/interview_flow_and_rubric_spec.md`) at the start of
any new session.

## Status: Phases 1 and 2 done and verified. Phase 3 (voice) about to start.

The project pivoted on 2026-07-20 from a personal practice tool to a public portfolio/showcase
piece (see `PLAN.md`'s update note, and memory `project-goal-pivot-showcase`). Scope broadened
from Capital One-only to a general "Case Analysis Practice" tool; precision bar is lower than a
real-practice tool would need, in favor of visual polish and breadth.

---

## 1. Phase 1 — Interviewer agent: done, verified

`agents/interviewer.py` gates the interview through 6 stages (background → recap → clarifying
questions → framework → quantitative analysis → recommendation), only revealing case content the
candidate has earned (`case_loader.get_revealed_content()` / `REVEAL_THRESHOLD`). Went through 8
bug fixes from browser testing (grounding/hallucination, stage-2 over-strictness, progressive-
data-release mismatch, connection error handling, fail-on-repeated-wrong, infinite redirect
looping, proactive hint-giving — all documented in `docs/interview_flow_and_rubric_spec.md`
Part 5), plus one more grounding bug found afterward (interviewer inventing fake product-line data
when asked to jump straight from stage 2 to stage 4 in one reply — fixed by widening
`REVEAL_THRESHOLD` for stage 4 so real data is actually available at that point, plus stronger
"never invent case data" language in the system prompt).

**Verified** by walking full conversations through the actual browser UI (not just scripted API
calls) across multiple sessions, including the happy path all the way to interview completion.

---

## 2. Phase 2 — Evaluator agent: done, rubric finalized

`agents/evaluator.py` scores a completed transcript on Capital One's **real, official 4-dimension
rubric** — Structured Thinking, Quantitative Analysis, Communication, Business Judgment — each
1-5, graded across the *whole* transcript rather than one-dimension-per-interviewer-stage. Anchor
language (what a 5/3/1 looks like on each dimension) is sourced directly from the user's own real
mock-interview calibration notes in `docs/scoring_calibration_samples.md`. `passed` (all 4
dimensions ≥ `PASS_THRESHOLD` = 3) is computed in Python, never asked of the model. Triggered
automatically when the interviewer signals `complete:yes` in its hidden tag.

**On calibration/validation — this is settled, not open:** the user confirmed scoring accuracy
should be judged by **a human reading the reasoning behind each score**, not by chasing numeric
alignment between rubric versions or model runs. Rationale (recorded by the user in
`docs/project_story_notes.md` #1): scoring a case interview is an open-ended judgment call, not a
math problem with one right answer, so comparing two AI-generated scores against each other proves
nothing — what matters is whether the stated reasoning holds up, which only a person with real
case-interview experience can judge. This matches real "calibration" practice at consulting firms
/ OSCE medical exams / hiring panels. **No further numeric calibration pass is needed or wanted** —
if evaluator quality ever needs rechecking, the method is: feed real user-provided transcript
samples, show the raw scores + reasoning, let the user judge. Never self-author test scenarios or
self-judge accuracy (see memory `workflow-preferences`).

**Verified** the same way as Phase 1 — full browser walkthroughs through to the star-rating
scorecard, plus one earlier calibration pass against 5 real samples (done before this rubric was
finalized, against an earlier 5-dimension draft — superseded, not wasted, just not the final rubric).

---

## 3. Phase 3 — Browser speech: about to start, not yet implemented

Per `PLAN.md`: free browser-native Web Speech API (SpeechRecognition for mic input, SpeechSynthesis
for reading the interviewer's replies aloud) for daily practice use — no paid service. Nothing
built yet. Known planning considerations for whoever picks this up:
- Web Speech API support is strongest in Chrome/Edge; Safari/Firefox support is partial or absent
  — worth deciding upfront whether to detect/warn on unsupported browsers or just document the
  requirement.
- `localhost` satisfies the "secure context" requirement these APIs need, so no HTTPS setup is
  required for local dev.
- Will need to fit into Streamlit's execution model (a Python rerun-on-every-interaction app) —
  likely means a small custom HTML/JS component (`st.components.v1.html`) to own the mic/speech
  lifecycle client-side and hand transcribed text back to Streamlit, rather than trying to drive
  speech APIs from Python directly.
- Phase 3b (Deepgram/ElevenLabs demo-mode voice) and Phase 4 (voice polish/interruption) come after
  this and are still untouched.

---

## 4. Key reference files

- `docs/official_scoring_dimensions.md` — the real Capital One 4-dimension rubric (web-research
  sourced). This is what `agents/evaluator.py` actually implements.
- `docs/scoring_calibration_samples.md` — the user's own real mock-interview transcripts/notes,
  with dimension anchors and specific right/wrong examples. Source of the evaluator's anchor
  language, and the reference to use if a future calibration read is ever wanted.
- `docs/project_story_notes.md` — the user's running notes on resume/LinkedIn-worthy insights from
  building this project (e.g. the calibration-philosophy insight in section 2 above). Add to this
  file, don't just let insights live in chat history — that's its whole purpose.
- `docs/interview_flow_and_rubric_spec.md` — the interviewer's stage-gating design (Part 1) and
  bug-fix addenda (Part 5) are current and authoritative. **Part 2 of this doc (an earlier
  5-dimension rubric) is stale/superseded by `official_scoring_dimensions.md` — don't take Part 2
  at face value if reading this doc fresh; it was never rewritten after the rubric changed to the
  real 4-dimension model.**

Also: `agents/interviewer.py`, `agents/evaluator.py`, `agents/case_loader.py` (the two agents +
stage-tagged case loader); `data/case_1_farm_owner.md`, `case_2_credit_card_partners.md`,
`case_3_tipping_ab_test.md` (all use `<!-- stage:N -->` markers, N=3,4,5); `app.py` (session state:
`display_messages`, `api_messages`, `current_stage`, `wrong_streak`, `case_over`,
`interview_complete`, `evaluation`); `PLAN.md` (roadmap + pivot note).

---

## 5. Unresolved issues / things to watch for

- **`docs/interview_flow_and_rubric_spec.md` Part 2 is stale** (repeated from above since it's an
  actual latent trap) — cosmetic, not blocking, but worth tidying eventually so nobody implements
  against the wrong rubric by accident.
- **`max_tokens=800` on the interviewer may be tight** now that stage-4 replies front-load a full
  data block in one message. If a reply gets truncated, the required `[[stage:N|answer:STATUS|
  complete:yes/no]]` tag is silently lost, and `get_interviewer_reply()` falls back to "no stage
  change, answer_status=na, complete=False" with no visible error — would look like the
  interviewer "stalling" with no indication why. Not yet hit in testing, but never specifically
  stress-tested either.
- **Stage-4 sub-question progression isn't tracked with an explicit counter** — the model infers
  position from conversation history + the stage-4 content block. Has worked fine in testing, but
  there's no structured "sub-question 3 of 4" signal if it ever needs debugging.
- **`case_3_tipping_ab_test.md` is an invented case**, unlike `case_1`/`case_2` which are sourced
  verbatim from the user's real reference pack (`CapitalOne_Case_Interview_Pack.docx`, in
  Downloads, not committed to the repo). That reference pack actually has 10 full real cases with
  answer keys (Sports Stadium Lease, New Energy Investment, Vegan Burger, 3D Printer, Ride Share,
  Streamline Advertisement, Subscription Media, Apartment Investment, plus the two already used) —
  worth knowing these exist if the user wants to swap in a real case instead of the invented one,
  or add more for breadth.
- **Streamlit's background process has died unexpectedly a few times** across sessions (log just
  shows "Stopping...", no exception — consistent with laptop sleep or the OS reclaiming an
  unfocused background process). Not a code bug. If it recurs: `ps aux | grep streamlit`, then
  `pkill -f "streamlit run app.py"` and restart with `streamlit run app.py --server.headless true`.
  Worth keeping in mind for Phase 3 - voice testing sessions will run longer than text testing did.

---

## Reminders

- Commit discipline: only commit when explicitly asked — followed consistently across this
  project (most recent: `b02a1c3`).
- `.env` / `.claude/` are gitignored; never let API keys land in a commit.
- Demo strategy: no public hosted deployment — local run + screen recording only.
- User already set a monthly Anthropic spend limit; no need to re-prompt.
