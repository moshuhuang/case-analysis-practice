import os

import streamlit as st
from anthropic import Anthropic, APIConnectionError, APIStatusError, APITimeoutError
from dotenv import load_dotenv

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


case_title = st.sidebar.selectbox("Choose a case", list(cases.keys()))

if st.session_state.get("case_title") != case_title:
    start_case(case_title)

if st.sidebar.button("🔄 Restart this case"):
    start_case(case_title)
    st.rerun()

st.sidebar.markdown(f"**Stage {st.session_state.current_stage}/5: {STAGE_LABELS[st.session_state.current_stage]}**")
with st.sidebar.expander("Case background", expanded=True):
    st.markdown(md_safe(st.session_state.case_data["context"]))
st.sidebar.caption(
    "Questions and data are revealed step by step during the interview, just like a real case "
    "interview - they won't be listed here in advance."
)

for message in st.session_state.display_messages:
    with st.chat_message(message["role"]):
        st.markdown(md_safe(message["content"]))

chat_locked = st.session_state.case_over or st.session_state.interview_complete
if st.session_state.case_over:
    st.info("This case has ended. Use \"Restart this case\" in the sidebar to try again.")
    user_answer = None
elif st.session_state.interview_complete:
    user_answer = None
else:
    user_answer = st.chat_input("Type your answer...")

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
