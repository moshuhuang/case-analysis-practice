# Progress Log

Read this together with `PLAN.md` at the start of any new session to pick up where things left off.

## Status: Phase 1 in progress

### Done
- Project scaffolded: `app.py` (Streamlit UI), `agents/interviewer.py` (interviewer agent logic),
  `agents/case_loader.py` (loads and parses case files).
- Two case files saved in `data/`: `case_1_farm_owner.md`, `case_2_credit_card_partners.md`.
  Each file has a candidate-visible section (context + questions) and an "Answer Key" section
  used only as an internal reference for the interviewer agent — never shown to the candidate.
- Local git repo initialized. `.gitignore` excludes `.env` and the venv so the API key never
  gets committed.
- Python virtual environment created at `.venv/`, dependencies installed from `requirements.txt`
  (streamlit, anthropic, python-dotenv).
- Default model: `claude-sonnet-4-6` (set in `agents/interviewer.py` as `INTERVIEWER_MODEL`).
  Chosen for reasoning quality on the core "decide follow-up vs. advance" behavior. If API
  costs run higher than expected, this is the one constant to swap to a cheaper model.

### Design decisions worth knowing
- The interviewer's opening line (context + Question 1) is generated deterministically in
  `app.py`, not via an API call — saves a call and avoids the awkwardness of the Anthropic
  Messages API requiring the first message in a conversation to have the `user` role.
- Two parallel message lists are kept in `st.session_state`: `display_messages` (what's shown
  in the chat UI, includes the canned opening) and `api_messages` (what's actually sent to
  Claude, starts from the candidate's first real answer). The model doesn't need the canned
  opening repeated back to it because the system prompt already contains the full case text.
- All interviewer behavior (follow-up vs. advance logic) lives in one system prompt in
  `agents/interviewer.py` — no separate classifier/tool call. Kept simple for Phase 1.

### Not done yet / blocked
- Waiting on the user to create a local `.env` file with their `ANTHROPIC_API_KEY`
  (instructed to do this directly in VS Code, not paste the key into chat).
- Phase 1 acceptance test (5+ rounds, 4+ genuinely specific follow-ups) not yet run.
- Phase 2 (evaluator agent), Phase 3 (browser speech), Phase 3b (Deepgram/ElevenLabs demo
  mode), Phase 4 (optional polish) not started.

### Reminders for later
- Before publishing to GitHub: double check `.env` is never staged (`git status` should never
  show it — it's in `.gitignore`).
- User set a monthly spend limit in the Anthropic console already (per their message);
  don't need to re-prompt for that.
- Demo strategy: no public hosted deployment. Local run + screen recording only.
