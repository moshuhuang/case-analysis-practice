import json
import os
import re
import time
from typing import Any

import streamlit as st
import streamlit.components.v1 as components
from anthropic import Anthropic, APIConnectionError, APIStatusError, APITimeoutError
from dotenv import load_dotenv
from streamlit_javascript import st_javascript

from agents.case_loader import STAGE_LABELS, list_cases, load_case
from agents.evaluator import PASS_THRESHOLD, evaluate_transcript
from agents.interviewer import get_interviewer_reply

MAX_WRONG_STREAK = 3  # more than this many consecutive wrong attempts on the same question -> fail

# One Streamlit built-in color name per dimension, just to visually tell the four rows apart.
DIMENSION_COLOR_NAMES = {
    "Structured Thinking": "blue",
    "Quantitative Analysis": "green",
    "Communication": "violet",
    "Business Judgment": "orange",
}

load_dotenv()


def md_safe(text: str) -> str:
    """Escape literal '$' so Streamlit's markdown renderer doesn't treat a pair of them as a
    LaTeX math span - case interview content is full of dollar amounts, and two or more '$' in
    the same message otherwise get silently rendered as garbled math/code instead of plain text."""
    return text.replace("$", "\\$")


def star_rating(score: int, max_score: int = 5) -> str:
    """Render a 1-5 score as filled/hollow stars, e.g. 3 -> '★★★☆☆'."""
    score = max(0, min(score, max_score))
    return "★" * score + "☆" * (max_score - score)


def speech_text(text: str) -> str:
    """Strip markdown syntax so text-to-speech doesn't read out '**', '#', etc."""
    text = re.sub(r"[*_`#]", "", text)
    return re.sub(r"\s+", " ", text).strip()


def speak(text: str) -> None:
    """Fire-and-forget: read `text` aloud via the browser's SpeechSynthesis API."""
    payload = json.dumps(speech_text(text))
    components.html(
        f"""
        <script>
        if (window.speechSynthesis) {{
            window.speechSynthesis.cancel();
            const utter = new SpeechSynthesisUtterance({payload});
            utter.lang = "en-US";
            window.speechSynthesis.speak(utter);
        }}
        </script>
        """,
        height=0,
    )


def stop_speaking() -> None:
    components.html(
        "<script>if (window.speechSynthesis) { window.speechSynthesis.cancel(); }</script>",
        height=0,
    )


VOICE_COMMAND_KEY = "case_voice_command"
VOICE_TRANSCRIPT_KEY = "case_voice_transcript"

# NOTE on architecture: an earlier version of this tried to `await` the whole recognition
# session through streamlit_javascript's bidirectional bridge (st_javascript) in one call.
# That bridge turned out to silently drop async results in practice (confirmed via browser
# console: "handleSetComponentValue: missing 'value' prop") - synchronous one-shot JS calls
# through it work fine, long-awaited async ones don't. So instead: recognition runs in a
# plain one-way components.html() injection (no round trip needed to start it) and writes
# each finalized chunk to localStorage as it goes; stopping is another one-way injection
# that just sets a command flag; reading the result back is a single *synchronous*
# st_javascript localStorage read, done only once the candidate clicks stop.


def start_recognition_js() -> None:
    """One-way: (re-)render the same recognition-launcher iframe every rerun while
    listening=True. Streamlit doesn't reload an iframe whose content is unchanged, so this
    keeps the *same* in-browser recognition session alive across reruns instead of
    restarting it - it only actually starts once, the very first time it's rendered."""
    components.html(
        f"""
        <script>
        if (!window.__caseRecognitionStarted) {{
            window.__caseRecognitionStarted = true;
            const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
            localStorage.setItem("{VOICE_TRANSCRIPT_KEY}", "");
            localStorage.removeItem("{VOICE_COMMAND_KEY}");
            if (SR) {{
                const recognition = new SR();
                recognition.lang = "en-US";
                recognition.continuous = true;
                recognition.interimResults = false;
                recognition.onresult = (event) => {{
                    let chunk = "";
                    for (let i = event.resultIndex; i < event.results.length; i++) {{
                        if (event.results[i].isFinal) {{
                            chunk += event.results[i][0].transcript + " ";
                        }}
                    }}
                    if (chunk) {{
                        const prev = localStorage.getItem("{VOICE_TRANSCRIPT_KEY}") || "";
                        localStorage.setItem("{VOICE_TRANSCRIPT_KEY}", prev + chunk);
                    }}
                }};
                const poller = setInterval(() => {{
                    const cmd = localStorage.getItem("{VOICE_COMMAND_KEY}");
                    if (!cmd) return;
                    localStorage.removeItem("{VOICE_COMMAND_KEY}");
                    clearInterval(poller);
                    if (cmd === "stop") {{ try {{ recognition.stop(); }} catch (e) {{}} }}
                    else if (cmd === "abort") {{ try {{ recognition.abort(); }} catch (e) {{}} }}
                }}, 200);
                recognition.start();
            }}
        }}
        </script>
        """,
        height=0,
    )


def send_voice_command(command: str) -> None:
    """One-way: tell the running recognition (above) to stop or abort, via a localStorage
    flag it polls for - same-origin iframes share localStorage regardless of nesting, unlike
    trying to reach into another iframe's JS objects directly."""
    components.html(
        f'<script>localStorage.setItem("{VOICE_COMMAND_KEY}", "{command}");</script>',
        height=0,
    )


def read_voice_transcript() -> Any:
    """Synchronous read-back of whatever's been transcribed so far. Returns the string once
    resolved, or the int default (0) while the round trip is still pending."""
    return st_javascript(
        f'localStorage.getItem("{VOICE_TRANSCRIPT_KEY}") || ""',
        key="voice_transcript_read",
    )


def render_voice_panel() -> str | None:
    """Mic button + editable transcript + send/discard. Returns the submitted answer text,
    or None if nothing was submitted this run."""
    supported = st_javascript(
        "!!(window.SpeechRecognition || window.webkitSpeechRecognition)",
        key="speech_supported_check",
    )
    if supported is not True:
        st.caption(
            "🎤 Voice input isn't supported in this browser (works best in Chrome/Edge) - "
            "type your answer below instead."
        )
        return None

    mic_col, stop_col, cancel_col, status_col = st.columns([1, 1, 1, 3])
    with mic_col:
        if not st.session_state.listening and st.button("🎤 Record answer"):
            st.session_state.listening = True
            st.rerun()
    with stop_col:
        if st.session_state.listening and st.button("⏹ Stop & transcribe"):
            send_voice_command("stop")
            time.sleep(0.5)  # let the recognizer finalize + flush its last chunk before we read
            st.session_state.listening = False
            st.session_state.reading_transcript = True
            st.rerun()
    with cancel_col:
        if st.session_state.listening and st.button("✖ Cancel"):
            send_voice_command("abort")
            st.session_state.listening = False
            st.rerun()
    with status_col:
        if st.session_state.listening:
            st.caption("🔴 Listening... click **Stop & transcribe** when you're done talking.")
        elif st.session_state.reading_transcript:
            st.caption("Finishing transcription...")

    if st.session_state.listening:
        start_recognition_js()

    if st.session_state.reading_transcript:
        transcript = read_voice_transcript()
        if isinstance(transcript, str):
            st.session_state.reading_transcript = False
            if transcript.strip():
                st.session_state.voice_draft = transcript.strip()
            st.rerun()

    submitted = None
    if st.session_state.voice_draft:
        edited = st.text_area(
            "Recognized text - review/edit, then send:",
            value=st.session_state.voice_draft,
            key="voice_draft_box",
        )
        send_col, discard_col = st.columns([1, 1])
        with send_col:
            if st.button("✅ Send voice answer"):
                submitted = edited
                st.session_state.voice_draft = ""
        with discard_col:
            if st.button("🗑️ Discard"):
                st.session_state.voice_draft = ""
                st.rerun()
    return submitted


st.set_page_config(page_title="Case Analysis Practice", page_icon="🧭")
st.title("Case Analysis Practice")
st.caption(
    "Practice structuring and talking through real business and data case scenarios - the "
    "interviewer only reveals information as you earn it, just like a real case interview."
)

api_key = os.getenv("ANTHROPIC_API_KEY")
if not api_key:
    st.error(
        "No ANTHROPIC_API_KEY found. Create a `.env` file in the project folder "
        "(copy `.env.example` and paste in your key), then restart the app."
    )
    st.stop()

client = Anthropic(api_key=api_key)

cases = list_cases()


def start_case(title: str) -> None:
    """Reset all session state for a fresh attempt at `title` (used both when the sidebar
    selection changes and when the candidate clicks "Restart this case")."""
    case_data = load_case(cases[title])
    opening_line = (
        f"Hi, I'm your interviewer today. Here's the situation:\n\n"
        f"**{case_data['context']}**\n\n"
        f"Before we dive in, go ahead and walk me through your understanding of the "
        f"situation and what we're trying to figure out."
    )

    st.session_state.case_title = title
    st.session_state.case_data = case_data
    st.session_state.current_stage = 1  # stage 0 (background) is the opening line itself
    st.session_state.display_messages = [{"role": "assistant", "content": opening_line}]
    st.session_state.api_messages = []
    st.session_state.wrong_streak = 0
    st.session_state.case_over = False
    st.session_state.interview_complete = False
    st.session_state.evaluation = None
    st.session_state.listening = False
    st.session_state.reading_transcript = False
    st.session_state.voice_draft = ""
    st.session_state.last_spoken_idx = -1


case_title = st.sidebar.selectbox("Choose a case", list(cases.keys()))

if st.session_state.get("case_title") != case_title:
    start_case(case_title)

if st.sidebar.button("🔄 Restart this case"):
    start_case(case_title)
    st.rerun()

with st.sidebar.expander("🐛 Dev tools"):
    st.caption("Testing shortcut - grades whatever conversation exists so far, skipping the rest of the case.")
    if st.button("⏭️ Skip to evaluation"):
        st.session_state.interview_complete = True
        with st.spinner("Preparing your case review..."):
            try:
                st.session_state.evaluation = evaluate_transcript(
                    client, st.session_state.case_data, st.session_state.api_messages
                )
            except (APIConnectionError, APITimeoutError, APIStatusError) as e:
                st.session_state.evaluation = None
                st.warning(f"Couldn't generate the case review just now: {e}")
        st.rerun()

st.sidebar.markdown(f"**Stage {st.session_state.current_stage}/5: {STAGE_LABELS[st.session_state.current_stage]}**")
with st.sidebar.expander("Case background", expanded=True):
    st.markdown(md_safe(st.session_state.case_data["context"]))
st.sidebar.caption(
    "Questions and data are revealed step by step during the interview, just like a real case "
    "interview - they won't be listed here in advance."
)

st.sidebar.divider()
st.sidebar.checkbox("🔊 Read interviewer replies aloud", value=True, key="auto_read")
if st.sidebar.button("🔇 Stop reading"):
    stop_speaking()

for message in st.session_state.display_messages:
    with st.chat_message(message["role"]):
        st.markdown(md_safe(message["content"]))

last_idx = len(st.session_state.display_messages) - 1
if (
    st.session_state.auto_read
    and last_idx >= 0
    and st.session_state.display_messages[last_idx]["role"] == "assistant"
    and st.session_state.last_spoken_idx < last_idx
):
    speak(st.session_state.display_messages[last_idx]["content"])
    st.session_state.last_spoken_idx = last_idx

chat_locked = st.session_state.case_over or st.session_state.interview_complete
if st.session_state.case_over:
    st.info("This case has ended. Use \"Restart this case\" in the sidebar to try again.")
    user_answer = None
elif st.session_state.interview_complete:
    user_answer = None
else:
    voice_answer = render_voice_panel()
    typed_answer = st.chat_input("Type your answer...")
    user_answer = voice_answer or typed_answer

if user_answer:
    st.session_state.display_messages.append({"role": "user", "content": user_answer})
    st.session_state.api_messages.append({"role": "user", "content": user_answer})
    with st.chat_message("user"):
        st.markdown(md_safe(user_answer))

    with st.chat_message("assistant"):
        with st.spinner("Interviewer is thinking..."):
            try:
                reply, new_stage, answer_status, is_complete = get_interviewer_reply(
                    client,
                    st.session_state.case_data,
                    st.session_state.current_stage,
                    st.session_state.api_messages,
                )
            except (APIConnectionError, APITimeoutError, APIStatusError) as e:
                st.error(
                    "Couldn't reach the interviewer model just now (network hiccup or API issue). "
                    "Nothing was recorded - just retype your last message and send it again.\n\n"
                    f"Details: {e}"
                )
                st.session_state.api_messages.pop()  # let the candidate resubmit cleanly
                st.session_state.display_messages.pop()
                st.stop()
        st.markdown(md_safe(reply))

    if answer_status == "incorrect":
        st.session_state.wrong_streak += 1
    elif answer_status == "correct":
        st.session_state.wrong_streak = 0

    if st.session_state.wrong_streak > MAX_WRONG_STREAK:
        st.session_state.case_over = True
        reply += (
            f"\n\n---\n**Case ended - not a pass.** You weren't able to resolve "
            f"**Stage {new_stage}/5: {STAGE_LABELS[new_stage]}** after several attempts on the "
            f"same question. In a real interview this section would likely be scored as a fail. "
            f"Review that section and try the case again when ready."
        )

    st.session_state.display_messages.append({"role": "assistant", "content": reply})
    st.session_state.api_messages.append({"role": "assistant", "content": reply})
    st.session_state.current_stage = new_stage

    if is_complete and not st.session_state.case_over:
        st.session_state.interview_complete = True
        with st.spinner("Preparing your case review..."):
            try:
                st.session_state.evaluation = evaluate_transcript(
                    client, st.session_state.case_data, st.session_state.api_messages
                )
            except (APIConnectionError, APITimeoutError, APIStatusError) as e:
                st.session_state.evaluation = None
                st.warning(f"Couldn't generate the case review just now: {e}")

    st.rerun()

evaluation = st.session_state.get("evaluation")
if evaluation:
    st.divider()
    st.subheader("📊 Your Case Review")

    if evaluation["parse_ok"]:
        if evaluation["passed"]:
            st.success(f"Overall: PASS - all 4 dimensions scored at least {PASS_THRESHOLD}/5.")
        else:
            st.warning(
                f"Overall: NOT A PASS - at least one dimension scored below {PASS_THRESHOLD}/5."
            )

        for d in evaluation["dimensions"]:
            color_name = DIMENSION_COLOR_NAMES.get(d["label"], "gray")
            stars = star_rating(d["score"])
            st.markdown(f"**{d['label']}** — :{color_name}[{stars}] ({d['score']}/5)")
            st.markdown(md_safe(d["comment"]))

        if evaluation["improvements"]:
            st.markdown("**Top things to improve next time:**")
            for point in evaluation["improvements"]:
                st.markdown(f"- {md_safe(point)}")
    else:
        st.markdown(md_safe(evaluation["raw_text"]))
