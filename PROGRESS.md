# Progress Log

Read this together with `PLAN.md` at the start of any new session to pick up where things left
off. Also read `CLAUDE.md`, which points to `docs/interview_flow_and_rubric_spec.md` — the design
spec for the interviewer's stage logic and the (not yet built) evaluator's rubric.

## Status: Phase 1 stage-gating + 2 rounds of browser-testing bug fixes (5 + 3 bugs) done, not yet
## re-confirmed by user in the browser. Evaluator (Phase 2) not started.

### Done — round 2 (3 more bugs found during the user's second browser test)
Note: the user re-used the labels "Bug 2/3/4" for this round — these are different bugs from
round 1's Bug 2-4 below, not the same ones recurring.
1. **Interviewer looped indefinitely on the same sticking point** instead of moving on like a real
   interviewer would (max 2-3 redirects, then either advance or fail). Added a "CAP ON REPEATED
   REDIRECTS" rule to `agents/interviewer.py`'s system prompt: never redirect the same gate more
   than 3 times in a row; on the 3rd unresolved attempt, soft/qualitative gates (recap, clarifying
   question specificity, framework shape) get accepted-with-a-noted-gap and advanced anyway, while
   hard gradable gates (Stage 4 math) rely on the existing Bug-5 same-question fail rule to end the
   case after a 4th consecutive `incorrect` tag — no infinite loop either way.
2. **Interviewer was proactively inviting/hinting clarifying questions** (e.g. asking "do you have
   any clarifying questions?" or naming topics like "scope"/"profitability" before the candidate
   raised them) — unrealistic, since real candidates have to initiate this themselves. Removed the
   "invite clarifying questions" instruction from the Stage 1→2 transition; Stage 2 is now
   explicitly candidate-initiated and optional (skipping straight to a framework is legitimate).
   Added a general "No leading/hinting" rule covering this everywhere, not just Stage 2.
3. **Interviewer was proactively supplying the analysis equation/formula** instead of waiting for
   the candidate to propose it in Stage 3/4. Stage 3 and Stage 4 instructions now explicitly
   forbid stating or hinting at framework categories or equations - the interviewer only
   evaluates/confirms/challenges what the candidate proposes on their own.

All three fixes are also reflected in `docs/interview_flow_and_rubric_spec.md` (Stage 1-3 sections
reworded, new "Cap on repeated redirects" subsection, Part 5 items 3-5 added).

### Done — round 1 (5 bugs found during the user's first browser test of stage-gating)
1. **Grounding / hallucinated objective** ("production capacity" was invented for a case that's
   actually about profitability): both `data/case_1_farm_owner.md` and
   `data/case_2_credit_card_partners.md` now have an explicit "Business objective / decision to be
   made" line in `## Context`, naming the real objective and explicitly ruling out unrelated ones.
   `agents/interviewer.py`'s system prompt also gained a "Grounding" rule under GENERAL RULES:
   any objective/number/term the interviewer states must be traceable to the case content, never
   invented.
2. **Stage 2 forced full topic coverage**: system prompt now treats goal/scope/time-horizon as
   *example* clarifying-question directions, not a checklist — one reasonable on-topic question is
   enough to advance to Stage 3. Spec doc (`docs/interview_flow_and_rubric_spec.md` Part 1 Stage 2)
   updated to match.
3. **Stage 4 progressive data release replaced with give-it-all-up-front**: the original design
   (data trickled out only as asked) didn't match how these case files are actually written (each
   sub-question already bundles its full data block). System prompt now tells the interviewer to
   give the full data set for a sub-question in the same message as the question; the candidate's
   job is to state the equation, plug in the given numbers, and narrate the logic — if they skip to
   a bare final number, the interviewer asks "Can you walk me through how you calculated that?".
   Spec doc Stage 4 section updated to match.
4. **Connection instability**: no `.streamlit/config.toml` exists (defaults are in use), so this
   isn't a Streamlit timeout misconfiguration. Root cause is most likely OS/process-lifecycle (the
   background streamlit process getting reaped/suspended, e.g. laptop sleep — matches the earlier
   "Stopping..." log with no exception). Mitigated the part that *is* a code issue: `app.py` now
   wraps the `client.messages.create()` call in try/except for `APIConnectionError` /
   `APITimeoutError` / `APIStatusError`, showing a friendly retry message instead of an uncaught
   crash, and cleanly rolls back the just-appended user turn so retry doesn't duplicate it.
   Remaining mitigation is environmental, not code — see "Reminders for later" below.
5. **No fail condition for repeated wrong answers**: the interviewer's hidden tag changed from
   `[[stage:N]]` to `[[stage:N|answer:STATUS]]`, where STATUS is `correct` / `incorrect` / `na`,
   grading the candidate's latest message against whichever gate/question is currently active.
   `agents/interviewer.py`'s `get_interviewer_reply()` now returns `(reply, new_stage,
   answer_status)`. `app.py` tracks `st.session_state.wrong_streak`, incrementing on `incorrect`
   and resetting on `correct`; once it exceeds `MAX_WRONG_STREAK = 3` (i.e. a 4th consecutive wrong
   attempt on the same question), the case ends immediately with a short fail note naming the
   stage, and the chat input is disabled (`st.session_state.case_over`). Spec doc gained a new
   "Part 5 — Addenda from Phase 1 browser testing" section documenting both this and the grounding
   rule.

**None of this round's 5 fixes has been re-tested by the user in the browser yet** — that's the
next step (see bottom of this file for the test plan to hand the user).

### Done — earlier stage-gating rewrite
- Original Phase 1 scaffold (Streamlit UI, interviewer agent, case loader) built and passed a
  5-round self-test on follow-up specificity.
- Removed "Think about: ..." / "Consider: ..." hint lines from the candidate-facing question
  text in both case files — they handed the candidate the answer's category framework, which
  defeated the point of testing structured thinking.
- **Stage-gating rewrite** (per `docs/interview_flow_and_rubric_spec.md` Part 1 and Part 4):
  - Case files (`data/case_1_farm_owner.md`, `data/case_2_credit_card_partners.md`) now have
    `<!-- stage:N -->` markers (N = 3, 4, or 5) in both the Questions and Answer Key sections,
    grouping content by which interview stage it belongs to. Stages 0-2 (background, recap,
    clarifying questions) have no case-specific content — they're governed by generic
    instructions in the interviewer's system prompt.
  - `agents/case_loader.py`: `load_case()` now returns `context`, `stage_questions` (dict of
    stage -> text), `stage_answer_key` (dict of stage -> text). New `get_revealed_content()`
    assembles only the content the interviewer is allowed to know about: content for stage N is
    included once `current_stage >= N - 1` (one stage ahead of the live gate), so the model has
    what it needs to transition the moment the candidate clears the current gate, but never
    further ahead than that.
  - `agents/interviewer.py`: system prompt rewritten with explicit per-stage behavior rules
    (recap correction, clarifying-question scope limiting, framework-before-numbers gate,
    progressive data release + equation-first/assumption-flagging in the quant stage, CSR +
    pushback in the recommendation stage) plus the three Part 4 cross-cutting judgment
    principles (materiality / proportionality / justification vs. name-dropping) for candidate
    detours outside the core framework. The model is required to end every reply with a hidden
    `[[stage:N]]` tag reporting the stage after that turn; `get_interviewer_reply()` parses and
    strips it, falling back to no stage change if the tag is missing.
  - `app.py`: opening message now only shows the case background and asks the candidate to
    recap — it no longer shows Question 1 upfront. Sidebar only shows the background (not the
    full question list), matching the "information revealed progressively" design. Shows a
    "Stage N/5: <label>" indicator.
- **Self-tested** the stage-gating with a scripted conversation deliberately trying to skip
  gates (jumping to a clarifying question before recapping, asking for numbers before giving a
  framework). Both skip attempts were correctly redirected without advancing the stage; correct
  recaps/frameworks were specifically acknowledged and advanced the stage; Stage 4 also
  spontaneously did progressive data release (gave only the ingredient data first, asked what
  else was needed, rather than dumping the whole data block). User has not yet run this
  themselves in the browser.

### Design decisions worth knowing
- Two parallel message lists are kept in `st.session_state`: `display_messages` (what's shown
  in the chat UI, includes the canned opening) and `api_messages` (sent to Claude, starts from
  the candidate's first real message).
- Stage state (`st.session_state.current_stage`, int 0-5) is the source of truth for what case
  content gets built into the system prompt each turn — this is a hard gate (the model literally
  doesn't have stage N+2 content in its context yet), not just an instruction-based gate, for the
  stage-skip risk that matters most (leaking future numeric data).
- Within stage 4 (which spans several sub-questions, e.g. Q2-Q5), sub-question progression is
  NOT tracked with a separate counter — same as original Phase 1, it relies on the model reading
  conversation history + the stage-4 content block. This was a deliberate simplicity trade-off,
  consistent with previous self-test results showing this works well. The Bug 5 fix's
  `wrong_streak` counter works around this: it resets on any `answer:correct` tag regardless of
  whether the stage number changed, so it correctly tracks "same sub-question" even without an
  explicit sub-question counter.
- Evaluator agent (Phase 2, per spec Part 2) was deliberately **not** built in this pass — the
  user asked to split the spec doc's asks into two separate rounds so each could be verified on
  its own before moving on, consistent with the "confirm before advancing" project rhythm.

### Not done yet / blocked
- **User still needs to try the fixed stage-gated interviewer themselves in the browser and
  confirm all 5 bug fixes above feel right — not yet confirmed as of this note.** See the test
  plan below.
- **Streamlit background process has died unexpectedly at least twice across sessions** (log just
  showed "Stopping..." twice, no crash/exception each time — consistent with the laptop sleeping
  or the OS reclaiming an unfocused background process, not a Streamlit config issue; there's no
  `.streamlit/config.toml` and defaults are in use). If it happens again mid-test: run `ps aux |
  grep streamlit` to confirm, then restart with `streamlit run app.py --server.headless true`. For
  a longer-lived session, running it in a normal foreground Terminal tab (not backgrounded) or
  prefixing with `caffeinate -is` to block sleep while it runs would help confirm/rule out the
  sleep theory.
- **All of the stage-gating rewrite + this round's 5 bug fixes are uncommitted.** Run `git status`
  / `git diff --stat` at the start of the next session — do not commit until the user explicitly
  asks, per their standing preference, and ideally not until they've confirmed the browser test.
- Evaluator agent (Phase 2, using `docs/interview_flow_and_rubric_spec.md` Part 2's five-
  dimension rubric) — separate round, deliberately deferred, not started.
- Phase 3 (browser speech), Phase 3b (Deepgram/ElevenLabs demo mode), Phase 4 (optional polish)
  not started.

### Test plan for both rounds of fixes (hand to user)
Run through one case end-to-end in the browser (http://localhost:8501) and check:

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

### Reminders for later
- Before publishing to GitHub: double check `.env` is never staged (`git status` should never
  show it — it's in `.gitignore`).
- User already set a monthly spend limit in the Anthropic console; don't need to re-prompt.
- Demo strategy: no public hosted deployment. Local run + screen recording only.
