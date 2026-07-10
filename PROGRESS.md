# Progress Log

Read this together with `PLAN.md` at the start of any new session to pick up where things left
off. Also read `CLAUDE.md`, which points to `docs/interview_flow_and_rubric_spec.md` — the design
spec for the interviewer's stage logic and the evaluator's rubric.

## Status
Phase 1 (interviewer agent) stage-gating + 8 bug fixes are implemented and **committed**
(`2afd11b`), but **not yet re-tested by the user in the browser** — the user explicitly decided to
defer that retest and move on to Phase 2 rather than block on it. Phase 2 (evaluator agent) is
about to start; nothing has been implemented for it yet.

---

## Phase 1 — Interviewer agent: bug-fix status (implemented, not yet re-tested)

All 8 fixes below are in `agents/interviewer.py` (system prompt) and `app.py`, committed in
`2afd11b`. Reference test plan is at the bottom of this file (Round 1 items 1-5, Round 2 items
6-8) — hand it to the user next time they sit down to test Phase 1 in the browser.

**Round 1** (5 bugs from the user's first browser test):
1. **Grounding / hallucinated objective** — interviewer once invented "production capacity" as the
   goal for a case actually about profitability. Fix: both case files' `## Context` now state an
   explicit "Business objective / decision to be made" line; interviewer prompt has a "Grounding"
   rule requiring every objective/number/term to be traceable to the case content.
2. **Stage 2 forced full topic coverage** — interviewer was requiring goal + scope + time-horizon
   all to be asked about before advancing. Fix: these are now explicitly "examples, not a
   checklist" — one reasonable on-topic question is enough to advance.
3. **Stage 4 progressive data release** — interviewer was trickling data out field-by-field instead
   of matching how these case files actually present sub-questions (each bundles its full data
   block already). Fix: interviewer now gives all data for a sub-question in one message, and
   candidate's job is to narrate the calculation using that data.
4. **Connection instability** — investigated; no `.streamlit/config.toml` exists, so this isn't a
   Streamlit timeout misconfig. Root cause is most likely OS/process-lifecycle (background
   Streamlit process getting reaped/suspended, e.g. laptop sleep) — not something fixable in code.
   Did fix the part that *is* a code issue: `app.py` now wraps the `client.messages.create()` call
   in try/except for `APIConnectionError` / `APITimeoutError` / `APIStatusError`, shows a friendly
   retry message, and rolls back the just-appended turn so retry doesn't duplicate it.
5. **No fail condition for repeated wrong answers** — interviewer's hidden tag changed from
   `[[stage:N]]` to `[[stage:N|answer:STATUS]]` (STATUS = `correct`/`incorrect`/`na`), grading the
   candidate's latest message against whatever gate is active. `app.py` tracks
   `st.session_state.wrong_streak`; once it exceeds `MAX_WRONG_STREAK = 3` (4th consecutive wrong
   attempt on the same question), the case ends immediately with a fail note and the chat input
   locks (`st.session_state.case_over`).

**Round 2** (3 more bugs from the user's second browser test — note the user re-used the labels
"Bug 2/3/4" for this round; these are different issues from Round 1's Bug 2-4, not recurrences):
6. **Interviewer looped indefinitely on the same sticking point** instead of moving on like a real
   interviewer would. Fix: added a "CAP ON REPEATED REDIRECTS" rule — max 3 redirects on the same
   gate; on the 3rd unresolved attempt, soft/qualitative gates (recap, clarifying-question
   specificity, framework shape) get accepted-with-a-noted-gap and advanced anyway, while hard
   gradable gates (Stage 4 math) rely on the Round-1 Bug-5 fail rule to end the case on the 4th
   consecutive `incorrect` tag.
7. **Interviewer was proactively inviting/hinting clarifying questions** (asking "do you have any
   clarifying questions?" or naming topics like "scope" before the candidate raised them). Fix:
   removed the "invite clarifying questions" instruction after recap; Stage 2 is now explicitly
   candidate-initiated and optional — skipping straight to a framework is legitimate.
8. **Interviewer was proactively supplying the analysis equation/formula** instead of waiting for
   the candidate to propose it. Fix: Stage 3/4 instructions now explicitly forbid stating or
   hinting at framework categories or equations; interviewer only evaluates what the candidate
   proposes on their own. Added a general "No leading/hinting" rule covering this everywhere.

All three Round 2 fixes are also reflected in `docs/interview_flow_and_rubric_spec.md` (Stage 1-3
sections reworded, new "Cap on repeated redirects" subsection, Part 5 items 3-5).

---

## Phase 2 — Evaluator agent: about to start, nothing implemented yet

**What's expected** (per `docs/interview_flow_and_rubric_spec.md` Part 2 and Part 4):
- Score each completed case on the 5 rubric dimensions in Part 2's table (Recap & Objective
  Alignment, Clarifying Questions, Framework Structure, Quantitative Execution, Recommendation/CSR)
  — each gets a short score (e.g. 1-4) **plus one concrete, specific comment**. No generic praise
  ("good job") or generic criticism ("needs work") — every comment must cite something specific the
  candidate actually said or didn't say.
- Use Part 4's three judgment principles (materiality / proportionality / justification-vs-namedropping)
  when the candidate raised points outside the core financial framework — reward material,
  proportionate, justified detours; don't penalize them just for being outside Financial/Customer/Market.
- Output format is specified exactly at the end of Part 2 (5 dimension lines + "Top 2 things to
  improve next time"). Runs once per completed case, not after every turn (cost + realism reasons
  already agreed on with the user).

**Process the user wants**: propose an implementation approach first (not code) — how the evaluator
will be triggered, what transcript/data it reads, how scoring will be produced — and get sign-off
before writing anything. This was in progress when the session was paused to update this file; the
next session should pick this back up rather than jumping straight to code.

**Open design question worth raising with the user before/while planning**: there is currently no
clean "interview fully completed" signal in `app.py`. The only session-state flag that marks an
end-state is `case_over`, which is set exclusively by the *fail* path (Round-1 Bug 5's wrong-streak
rule). When a candidate finishes normally (gets through Stage 5's recommendation + pushback and the
interviewer closes warmly), nothing in the code marks that as "done" — `current_stage` just stays
at 5 and the chat stays open. The evaluator needs a reliable trigger point and a defined transcript
boundary; that likely means either (a) extending the model's hidden tag to signal "interview
complete" at the end of Stage 5, or (b) adding an explicit "End interview / Get my feedback" button
the candidate clicks. Worth deciding this explicitly as part of the Phase 2 plan rather than
discovering it midway through implementation.

---

## Key files (where things live)

- `docs/interview_flow_and_rubric_spec.md` — **the design spec**, source of truth for both agents.
  Part 1 = interviewer stage logic (already implemented). Part 2 = evaluator scoring rubric (not
  yet implemented — this is what Phase 2 builds). Part 3 = state-design notes for the interviewer.
  Part 4 = judgment principles for off-framework candidate detours (used by both agents). Part 5 =
  addenda written after Phase 1 browser testing (grounding rule, same-question fail rule, redirect
  cap, no-hinting rules).
- `CLAUDE.md` — project-root instruction pointing here: read the spec doc before touching
  `agents/interviewer.py`, `agents/evaluator.py` (doesn't exist yet), or case file stage markers.
- `agents/interviewer.py` — the interviewer agent (stage-gating system prompt + `get_interviewer_reply()`).
- `agents/case_loader.py` — parses `data/case_*.md` into `context` / `stage_questions` /
  `stage_answer_key`, and `get_revealed_content()` assembles what the interviewer is allowed to see
  at the current stage.
- `agents/evaluator.py` — **does not exist yet**; this is what Phase 2 creates.
- `app.py` — Streamlit UI, holds all session state (`display_messages`, `api_messages`,
  `current_stage`, `wrong_streak`, `case_over`).
- `data/case_1_farm_owner.md`, `data/case_2_credit_card_partners.md` — the two case files, with
  `<!-- stage:N -->` markers (N=3,4,5) splitting Questions and Answer Key content by stage.
- `PLAN.md` — the original 4-phase roadmap (Phase 1 interviewer, Phase 2 evaluator, Phase 3 browser
  speech, Phase 3b Deepgram/ElevenLabs demo mode, Phase 4 polish).

---

## Known issues / things to watch for (found while fixing Phase 1 bugs, not yet addressed)

1. **No clean "interview complete" signal for the happy path** — see the Phase 2 open design
   question above. This is the most important one to resolve before/while building the evaluator.
2. **Restarting the same case doesn't work from the UI.** `app.py`'s reset logic
   (`if st.session_state.get("case_title") != case_title`) only fires when the sidebar dropdown
   value *changes*. If a case ends (either failed via `case_over` or finished normally) and the
   candidate wants to retry the *same* case, reselecting the same value in the selectbox is a
   no-op in Streamlit — nothing resets. The `case_over` info message currently says "choose a case
   from the sidebar (or reselect this one)," but reselecting the same one won't actually work. Needs
   an explicit "Restart this case" button or similar.
3. **`max_tokens=800` may be tight for Stage 4 replies now that data is front-loaded.** Since Round
   1 Bug 3's fix, the interviewer must fit a full data dump + acknowledgment + question in one
   reply, plus the required `[[stage:N|answer:STATUS]]` tag at the very end. If a reply gets
   truncated by the token limit, the tag is silently lost, and `get_interviewer_reply()` falls back
   to "no stage change, answer_status=na" with no visible error — this would look like the
   interviewer "not making progress" without any indication of why. Worth watching for during
   Phase 1 retesting, and possibly worth raising `max_tokens` further or adding an explicit warning
   if the tag is ever missing.
4. **Stage 4 sub-question progression still isn't tracked with an explicit counter** — this was a
   deliberate simplicity trade-off from the original Phase 1 build (the model infers sub-question
   position from conversation history + the stage-4 content block). It's worked fine for the
   interviewer so far, but it means there's no structured signal (like "sub-question 3 of 4") in
   the transcript — the evaluator will have to infer sub-question boundaries from conversation text
   alone when scoring "Quantitative Execution." Worth keeping in mind if evaluation quality on that
   dimension turns out to be inconsistent.
5. **Streamlit background process has died unexpectedly at least twice across sessions** (log just
   showed "Stopping..." twice, no exception — consistent with laptop sleep or the OS reclaiming an
   unfocused background process). Not a code bug; see Round-1 Bug 4 above for the mitigation that
   *was* possible (graceful API error handling). If it recurs: `ps aux | grep streamlit` to check,
   restart with `streamlit run app.py --server.headless true`, or prefix with `caffeinate -is` /
   run in a foreground terminal tab to rule out sleep as the cause.
6. **None of the 8 Phase 1 bug fixes have been re-verified by the user in the browser yet** — the
   user made an explicit call to proceed to Phase 2 first and come back to this. Flagging again
   here so it isn't lost: if Phase 2 testing surfaces confusing/low-quality interviewer transcripts,
   that's a signal to circle back and retest Phase 1 before trusting the evaluator's output.

---

## Design decisions worth knowing

- Two parallel message lists live in `st.session_state`: `display_messages` (what's shown in the
  chat UI, includes the canned opening) and `api_messages` (sent to Claude, starts from the
  candidate's first real message). The evaluator will most likely want `api_messages` (or
  `display_messages` minus the opening) as its transcript input.
- Stage state (`st.session_state.current_stage`, int 0-5) is the source of truth for what case
  content gets built into the system prompt each turn — this is a hard gate (the model literally
  doesn't have stage N+2 content in its context yet), not just an instruction-based gate, for the
  stage-skip risk that matters most (leaking future numeric data).
- The `wrong_streak` counter resets on any `answer:correct` tag regardless of whether the stage
  number changed, so it correctly tracks "same sub-question" even without an explicit sub-question
  counter (see Known Issue 4 above for the limitation this doesn't cover).
- Evaluator agent (Phase 2, per spec Part 2) was deliberately **not** built in the Phase 1 passes —
  the user asked to split the spec doc's asks into separate rounds so each could be verified before
  moving on. That verification (Phase 1 browser retest) is now explicitly deferred, not skipped.

---

## Not done yet / blocked

- Phase 1 browser retest — deferred by user's explicit choice (see Status above), not forgotten.
- Evaluator agent (Phase 2) — about to start; see the Phase 2 section above for expected scope and
  the open design question to resolve first.
- Phase 3 (browser speech), Phase 3b (Deepgram/ElevenLabs demo mode), Phase 4 (optional polish) —
  not started, not blocking anything currently.

---

## Test plan for Phase 1's 8 fixes (hand to user whenever the retest happens)

Round 1:
1. **Grounding** — the interviewer should never mention a goal/term not in the case text (e.g. no
   "production capacity" for Case 1, no invented metrics for Case 2). Read the sidebar case
   background first — it now states the objective explicitly.
2. **Stage 2 coverage** — ask just ONE reasonable clarifying question (e.g. only about scope). The
   interviewer should be willing to move to Stage 3 without demanding you also ask about
   goal/time-horizon.
3. **Stage 4 data up front** — after your framework is accepted, the interviewer should dump the
   full data for the first sub-question in that same message (not make you ask for pieces). Try
   answering with just a bare number, no logic — it should ask you to walk through your
   calculation instead of accepting/rejecting it outright.
4. **Connection stability** — just note whether disconnects still happen; if the API call itself
   fails mid-test you should now see a friendly red error box (not a raw crash/traceback).
5. **Fail-on-repeated-wrong** — deliberately give a wrong answer to the same Stage 4 sub-question
   4 times in a row. The case should end after the 4th wrong attempt with a short "Case ended - not
   a pass" note naming the stage, and the chat input should become disabled.

Round 2:
6. **No infinite looping** — deliberately give a weak/wrong answer to the same point 2-3 times.
   By the 3rd unresolved attempt, the interviewer should either move on (accepting it with a noted
   gap, for soft gates like recap/framework) or the case should end via the fail rule (for hard
   gates like Stage 4 math) — it should never keep circling the same point indefinitely.
7. **No proactive clarifying-question prompting** — after a correct recap, the interviewer should
   just briefly confirm and go quiet, NOT ask "do you have any clarifying questions?" or hint at
   topics. Try skipping clarifying questions entirely and jumping straight to a framework — that
   should be accepted, not blocked.
8. **No proactive equation/framework hints** — the interviewer should never state or suggest the
   framework categories or the equation/formula itself at any point; it should only react to what
   you propose.

Also worth trying while retesting, tied to Known Issues above: let a case run all the way through
Stage 5 to a natural close, and separately try to restart a case from the sidebar, to see Known
Issues 1 and 2 firsthand.

---

## Reminders for later

- Before publishing to GitHub: double check `.env` is never staged (`git status` should never
  show it — it's in `.gitignore`).
- User already set a monthly spend limit in the Anthropic console; don't need to re-prompt.
- Demo strategy: no public hosted deployment. Local run + screen recording only.
- Commit discipline: only commit when the user explicitly asks (confirmed standing preference,
  followed successfully for the `2afd11b` commit).
