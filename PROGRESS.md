# Progress Log

Read this together with `PLAN.md` (roadmap + the 2026-07-20 pivot note at the top) and
`CLAUDE.md`/`AGENTS.md` (both point to `docs/interview_flow_and_rubric_spec.md`) at the start of
any new session.

## Status: Phases 1 and 2 both done and browser-verified. Phase 3 (voice) not started.

The project pivoted on 2026-07-20 from a personal practice tool to a public portfolio/showcase
piece (see `PLAN.md`'s update note, and memory `project-goal-pivot-showcase`). Scope broadened
from Capital One-only to a general "Case Analysis Practice" tool; precision bar is lower than a
real-practice tool would need, in favor of visual polish and breadth.

---

## What's built

**Interviewer agent** (`agents/interviewer.py`) — gates the interview through 6 stages
(background → recap → clarifying questions → framework → quantitative analysis → recommendation),
only revealing case content the candidate has earned. Went through 8 bug fixes from browser
testing (grounding/hallucination, stage-2 over-strictness, progressive-data-release mismatch,
connection error handling, fail-on-repeated-wrong, infinite redirect looping, proactive
hint-giving) — all documented in `docs/interview_flow_and_rubric_spec.md` Part 5. One more
grounding bug was found and fixed after that (interviewer inventing fake product-line data when
asked to jump straight from stage 2 to stage 4 in one reply — fixed by widening
`case_loader.REVEAL_THRESHOLD` for stage 4 so real data is actually available at that point,
plus stronger "never invent case data" language in the system prompt).

**Evaluator agent** (`agents/evaluator.py`) — scores a completed transcript on Capital One's real
4-dimension rubric (Structured Thinking, Quantitative Analysis, Communication, Business Judgment;
1-5 scale each; anchor language sourced from the user's own real-mock-interview calibration notes
in `docs/scoring_calibration_samples.md`). These 4 dimensions are graded across the *whole*
transcript, not one-per-interviewer-stage. `passed` (all 4 dimensions ≥ `PASS_THRESHOLD` = 3) is
computed in Python, not asked of the model. Triggered automatically when the interviewer signals
`complete:yes` in its hidden tag (end of stage 5, after the recommendation pushback is resolved).

**UI** (`app.py`) — Streamlit, 3 cases in the sidebar dropdown (`data/case_1_farm_owner.md`,
`case_2_credit_card_partners.md`, `case_3_tipping_ab_test.md` — the last one is a data/product-
analyst-flavored A/B-test case, added to demonstrate the broadened scope). "Restart this case"
button. Case review renders as **star ratings** (★ filled / ☆ hollow, one color per dimension —
blue/green/violet/orange) rather than a bar chart, after a bar chart looked like a single solid
rectangle when every dimension scored the max. A `md_safe()` helper escapes literal `$` before
every `st.markdown()` call on dynamic content — Streamlit's markdown otherwise treats a pair of
`$` as a LaTeX span, which silently mangled any message with 2+ dollar amounts (this is a case
interview tool, so that was most messages).

Both agents were **browser-walked end-to-end** (not just scripted API self-tests) at least twice,
including the full happy path through to the star-rating scorecard.

---

## Key files

- `docs/interview_flow_and_rubric_spec.md` — Part 1 (interviewer stage logic, implemented) and
  Part 5 (bug-fix addenda) are current. **Part 2 (a 5-dimension rubric) is now superseded** by
  `docs/official_scoring_dimensions.md`'s real 4-dimension model, which `evaluator.py` actually
  implements — Part 2 hasn't been rewritten to match, just left stale. Not urgent to fix, but
  don't take Part 2 at face value if reading this doc fresh.
- `docs/official_scoring_dimensions.md` — the real Capital One 4-dimension rubric (web-research
  sourced). This is what `evaluator.py` implements.
- `docs/scoring_calibration_samples.md` — the user's own real mock-interview transcripts/notes,
  with dimension anchors and specific right/wrong examples. Source of the evaluator's anchor
  language. Also useful if the user ever wants to re-run a calibration check (see "Open items").
- `agents/interviewer.py`, `agents/evaluator.py`, `agents/case_loader.py` — the two agents and the
  stage-tagged case-file loader (`get_revealed_content()`, `REVEAL_THRESHOLD`).
- `data/case_1_farm_owner.md`, `case_2_credit_card_partners.md`, `case_3_tipping_ab_test.md` — all
  use `<!-- stage:N -->` markers (N=3,4,5) splitting Questions/Answer Key content by stage.
- `app.py` — session state: `display_messages`, `api_messages`, `current_stage`, `wrong_streak`,
  `case_over`, `interview_complete`, `evaluation`.
- `PLAN.md` — original 4-phase roadmap + the pivot note.

---

## Open items / not done

- **Phase 3 (browser speech), Phase 3b (Deepgram/ElevenLabs demo mode), Phase 4** — not started.
- **The new 4-dimension evaluator hasn't been calibration-tested against the user's real samples
  yet.** A calibration pass *was* done (5 real samples: A1/B4/D1/S3/C1 from
  `scoring_calibration_samples.md`, grounded against the real cases in the user's reference docx),
  but that was against the OLD 5-dimension rubric, before the user revealed the official 4-
  dimension standard and the rubric got reworked. Per standing instruction (see memory
  `workflow-preferences`), if this calibration is redone: **feed real user-provided samples, show
  raw scores, let the user judge accuracy — never self-author test scenarios or self-judge.**
- `docs/interview_flow_and_rubric_spec.md` Part 2 is stale (see Key Files above) — cosmetic, not
  blocking, but worth tidying if someone reads that doc as current.

---

## Reminders

- Commit discipline: only commit when explicitly asked — followed consistently across this
  project (most recent: `94bfe6a`).
- `.env` / `.claude/` are gitignored; never let API keys land in a commit.
- Demo strategy: no public hosted deployment — local run + screen recording only.
- User already set a monthly Anthropic spend limit; no need to re-prompt.
- If Streamlit's background process dies unexpectedly (seen a few times, no exception — likely
  laptop sleep or OS reclaiming an unfocused background process): `ps aux | grep streamlit`, then
  `pkill -f "streamlit run app.py"` and restart with `streamlit run app.py --server.headless true`.
