# Progress Log

Read this together with `PLAN.md` (roadmap + the 2026-07-20 pivot note at the top) and
`CLAUDE.md`/`AGENTS.md` (both point to `docs/interview_flow_and_rubric_spec.md`) at the start of
any new session.

## Status: Phases 1, 2, 3 done and verified. Phase 3.5 (demo-readiness polish) done and verified. Phase 3b/4 (optional, professional voice + polish) not started.

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

## 3. Phase 3 — Browser speech: done, verified

Per `PLAN.md`: free browser-native Web Speech API — `SpeechRecognition` for mic input,
`SpeechSynthesis` for reading the interviewer's replies aloud — for daily practice use, no paid
service. Implemented entirely in `app.py` (no agent/backend changes needed).

**How it's built:**
- Recognition runs inside a one-way `st.components.v1.html()` injection (`start_recognition_js()`)
  that keeps the *same* in-browser recognition session alive across Streamlit reruns instead of
  restarting it each time — Streamlit doesn't reload an iframe whose content is unchanged.
  Finalized transcript chunks are written to `localStorage` as they come in.
- Stopping/cancelling is a second one-way injection that sets a `localStorage` command flag the
  running recognition polls for (`send_voice_command()`); same-origin iframes share `localStorage`
  regardless of nesting, which is what makes this work.
- Reading the finished transcript back is a single **synchronous** `st_javascript` localStorage
  read (`read_voice_transcript()`), done once, only after the candidate clicks stop.
- **Architecture note (don't redo this mistake):** an earlier version tried to `await` the whole
  recognition session through `streamlit_javascript`'s bidirectional bridge in one call. That
  silently dropped async results in practice (confirmed via browser console: `handleSetComponentValue:
  missing 'value' prop`). Synchronous one-shot calls through that bridge work; long-awaited async
  ones don't. Hence the one-way-injection + localStorage-polling design above.
- Recognition requires a manual "Stop & transcribe" click (Chrome doesn't reliably auto-stop a
  `continuous: true` session) — the recognized text lands in an editable review box before the
  candidate sends it, so misheard words can be fixed before submitting.
- TTS auto-reads each new interviewer reply (toggleable in the sidebar), with a "Stop reading"
  button and markdown stripped from the spoken text first (`speech_text()`).

**Verified** live in-browser by the user: recorded a voice answer, reviewed/edited the transcript,
sent it, and confirmed the interviewer's replies are read aloud correctly across several question
rounds. A live-amplitude waveform visualization was attempted and then explicitly removed at the
user's request (see Phase 3.5) — not because it didn't work, but because it looked bad.

---

## 3.5. Demo-readiness polish (UI restyle + Case 1 rework) — done, verified

Not a named phase in `PLAN.md`, but real work done in the same session right after Phase 3 landed,
specifically to make the tool look and flow better for a recorded portfolio demo. Two independent
tracks, both visual/content only — no interviewer or evaluator *logic* changed.

**UI restyle (`app.py`, pure CSS/markup, zero logic changes):**
- Injected Google Font **Baloo 2** (800 weight, rounded-terminal display font) for the app's main
  title and a new per-case heading that appears at the top of the page once a case is selected
  (previously the case name only showed in the sidebar dropdown).
- Restyled every `st.button` as a pill (`border-radius: 999px`), using Streamlit's built-in
  `type="primary"/"secondary"` to get solid-white-fill (forward/confirm actions: Record, Stop &
  transcribe, Send) vs. white-outline-hollow (Cancel, Discard, and other secondary buttons) —
  matched against user-supplied reference screenshots.
- Verified visually via browser screenshots at each step (font rendering, pill shape, button
  color pairing) — see the conversation for before/after screenshots.

**Case 1 rework (credit card partnership case promoted to default, trimmed for demo pace):**
- File renamed `case_2_credit_card_partners.md` → `case_1_credit_card_partners.md` (now the
  default-selected case); the old Case 1 (Farm Owner) is now `case_2_farm_owner.md`. Content
  unchanged for Farm Owner and `case_3_tipping_ab_test.md`.
- Case 1's content trimmed from 7 questions + a Stage-5 recommendation block down to exactly one
  Stage-3 framework question + one Stage-4 quant question (both user-specified verbatim, with
  user-specified reference answers). No case-specific Stage 5 content — the interviewer's existing
  generic Stage 5 behavior (Conclusion → Supporting data → Risks → Next steps, with pushback)
  handles the recommendation using the Context alone, so this still works without a written Q6/A6.
- **New mechanism**: `agents/case_loader.py` now supports an optional `## Objective` section,
  separate from the candidate-visible `## Context`. This fixes the "background over-reveals the
  objective" issue flagged earlier in the session (the sidebar background box literally showed the
  bolded objective sentence before the candidate even attempted a recap) — for Case 1, the
  candidate-visible background is now exactly the one sentence the user specified, while the
  objective used for internal recap-grounding is a separate field never shown directly. This fix is
  scoped to Case 1 only; Case 2/3 still combine both into `## Context` as before (untouched,
  not broken, just not using the new mechanism yet).
- `agents/evaluator.py`'s grounding also picks up `## Objective` when present.
- **Two behavior bugs found and fixed via live testing, both scoped to Case 1's case-file content
  (no interviewer.py system-prompt changes):**
  1. Interviewer was hinting at the objective's internal structure when redirecting an imprecise
     recap (literally said "what **two** things would we need to evaluate") — fixed by softening
     the Objective wording (dropped explicit "(1)... (2)..." enumeration) and adding an explicit
     instruction in `case_loader.get_revealed_content()`'s internal-grounding label: accept any
     reasonable recap attempt, never quote/count/hint at sub-parts when redirecting.
  2. Even after that, the interviewer was still nitpicking recap precision at all (asking "can you
     be more specific") — the user wanted zero pushback for this demo case. Fixed with a `STAGE 1
     OVERRIDE FOR THIS CASE` note in `data/case_1_credit_card_partners.md`'s `## Objective` section:
     accept the candidate's very first recap attempt unconditionally, brief acknowledgment only,
     move straight to Stage 2 - no follow-up questions at all. **This override is case-specific by
     design** (lives in the case file, not in the shared `agents/interviewer.py` prompt) so it
     doesn't loosen Stage 1 for Case 2/Case 3, which were already validated with the stricter
     behavior in Phase 1.
  3. A related third gap surfaced from the same root cause: because Stage 1 now only ever replies
     "That's right." with nothing else, the Stage 3 framework-prompt handoff came out as a floating,
     unanchored "How would you structure your analysis for this case?" — no restatement of what the
     actual decision being analyzed was. Fixed with a `GROUNDING NOTE` in the same `## Objective`
     section instructing the interviewer to restate the business decision in its own words (anchored
     to what the candidate already said in their recap) before asking for a framework, without naming
     framework categories. Verified live: the interviewer now says something like *"Great - so to
     decide whether to move forward with this partnership, how would you structure your analysis?"*

**Verified** via multiple live browser walkthroughs after each fix (not just code review): fresh
case load shows the new font/pill styling and the trimmed one-sentence background; a deliberately
terse recap ("We need to decide whether to move forward with this new credit card.") is now
accepted immediately with no pushback; the Stage 3 handoff correctly restates the business decision;
Stage 4's quant question and data are revealed correctly without leaking the answer key. **Not yet
re-verified in this session**: a full run all the way through Case 1's Stage 4 answer, Stage 5
recommendation, and the final evaluator scorecard with the new trimmed content — worth doing once
before recording an actual demo take (see section 6 below).

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
stage-tagged case loader, now also parsing an optional `## Objective` section - see section 3.5);
`data/case_1_credit_card_partners.md` (default case, trimmed, has `## Objective`),
`data/case_2_farm_owner.md`, `data/case_3_tipping_ab_test.md` (both use `<!-- stage:N -->` markers,
N=3,4,5, and still combine background+objective into a single `## Context` - not yet migrated to
the `## Objective` split); `app.py` (session state: `display_messages`, `api_messages`,
`current_stage`, `wrong_streak`, `case_over`, `interview_complete`, `evaluation`, plus voice-related
state `listening`, `reading_transcript`, `voice_draft`, `last_spoken_idx`); `PLAN.md` (roadmap +
pivot note).

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
- **`case_3_tipping_ab_test.md` is an invented case**; `case_2_farm_owner.md` is sourced verbatim
  from the user's real reference pack (`CapitalOne_Case_Interview_Pack.docx`, in Downloads, not
  committed to the repo); `case_1_credit_card_partners.md` started from that same pack but was
  trimmed/rewritten by the user this session (down to one framework question + one quant question,
  see section 3.5) — so it's no longer verbatim, just derived from it. The reference pack actually
  has 10 full real cases with answer keys (Sports Stadium Lease, New Energy Investment, Vegan
  Burger, 3D Printer, Ride Share, Streamline Advertisement, Subscription Media, Apartment
  Investment, plus the two already used) — worth knowing these exist if the user wants to swap in a
  real case instead of the invented one, or add more for breadth.
- **Streamlit's background process has died unexpectedly a few times** across sessions (log just
  shows "Stopping...", no exception — consistent with laptop sleep or the OS reclaiming an
  unfocused background process). Not a code bug. If it recurs: `ps aux | grep streamlit`, then
  `pkill -f "streamlit run app.py"` and restart with `streamlit run app.py --server.headless true`.
  **This is a real risk for demo recording** — a long single take is exactly the kind of session
  that has triggered this before; worth a quick server-alive check right before hitting record.
- **`case_2`/`case_3` still combine background+objective into one `## Context` block** (not
  migrated to the `## Objective` split added this session for `case_1`) — meaning their sidebar
  "Case background" box still shows the bolded objective sentence upfront, same over-reveal
  behavior flagged early in this session and only fixed for `case_1` so far. Not broken, just
  inconsistent with `case_1` now. Worth migrating if those two cases are ever used in a demo.

---

## 6. What's left / not started

- **Phase 3b (optional)** — swap the free browser voice for Deepgram (speech-to-text) + ElevenLabs
  (text-to-speech) behind a separate "demo mode" toggle, purely to make a recorded LinkedIn video
  sound better (natural TTS voice, more accurate transcription) than the browser's native voices.
  Requires the user to register both services and grab API keys (free tiers, no card required per
  `PLAN.md`, but worth double-checking that's still current before signing up). Not started.
- **Phase 4 (optional)** — voice naturalness polish + "barge-in"/interruption support (candidate
  can talk over the AI). Explicitly gated on Phase 3b landing first and re-scoping based on real
  experience; not started, not blocking.
- **One full live run of Case 1 through Stage 5 + the evaluator scorecard** hasn't happened yet
  since the trim/rework (see section 3.5's last paragraph) — Stage 1 through the start of Stage 4
  is verified; the quant answer, the generic Stage 5 recommendation exchange, and the final 4-
  dimension scorecard rendering with the new short transcript have not been walked end-to-end this
  session. Cheap to check with the sidebar "🐛 Dev tools → Skip to evaluation" shortcut, or a full
  real run.
- **`case_2`/`case_3` background over-reveal + Stage-1 strictness** — see the two bullets above in
  section 5. Not required for a Case-1-only demo, but relevant if either gets used on camera.

## 7. Demo-readiness assessment (job-search showcase purposes)

**Bottom line: close, not quite record-ready as-is.** Core functionality (interviewer, evaluator,
voice) is done and each piece has been verified working in the browser at least once. What's
standing between here and hitting record on a real take:

1. **Do the one missing full run** (section 6, bullet 3) — walk Case 1 start to finish for real
   (not the dev-tools shortcut) at least once, out loud, with voice on, before recording the actual
   take. Nothing suggests it's broken, but nothing has confirmed the *whole* thing end-to-end since
   the rework, and a demo recording is the wrong place to discover a gap live.
2. **Voice quality is browser-native, not the polished Phase 3b voice** — functional and verified,
   but Chrome's built-in TTS voice sounds robotic and speech recognition accuracy is "good enough,"
   not great. `PLAN.md` explicitly designed Phase 3b to close this exact gap for video quality. Not
   required to record *a* demo, but relevant if the bar is "sounds professional in a LinkedIn video."
3. **Server stability during a long take** (section 5, bullet on the background process dying) —
   worth a fresh restart and a quick sanity check immediately before recording, given this has
   actually happened before across sessions.
4. **No rehearsed script/talking points** for what to say while narrating the demo (what to
   highlight, what order to show features in) — outside this project's code, but worth having
   before recording, especially since Case 1 was specifically trimmed this session to keep a demo
   run short and clean.

Everything else — the core three-stage pipeline, the visual polish (font/buttons/case heading), and
Case 1 being tuned for a smooth no-friction run — is in good shape for a portfolio piece.

---

## Reminders

- Commit discipline: only commit when explicitly asked — followed consistently across this
  project (most recent: `2ba4676`).
- `.env` / `.claude/` are gitignored; never let API keys land in a commit.
- Demo strategy: no public hosted deployment — local run + screen recording only.
- User already set a monthly Anthropic spend limit; no need to re-prompt.
