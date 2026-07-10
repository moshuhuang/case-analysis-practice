import os

import streamlit as st
from anthropic import Anthropic, APIConnectionError, APIStatusError, APITimeoutError
from dotenv import load_dotenv

from agents.case_loader import STAGE_LABELS, list_cases, load_case
from agents.interviewer import get_interviewer_reply

MAX_WRONG_STREAK = 3  # more than this many consecutive wrong attempts on the same question -> fail

load_dotenv()

st.set_page_config(page_title="Capital One Case Interview Practice", page_icon="🎤")
st.title("Capital One Case Interview Practice")

api_key = os.getenv("ANTHROPIC_API_KEY")
if not api_key:
    st.error(
        "No ANTHROPIC_API_KEY found. Create a `.env` file in the project folder "
        "(copy `.env.example` and paste in your key), then restart the app."
    )
    st.stop()

client = Anthropic(api_key=api_key)

cases = list_cases()
case_title = st.sidebar.selectbox("Choose a case", list(cases.keys()))

if st.session_state.get("case_title") != case_title:
    case_data = load_case(cases[case_title])
    opening_line = (
        f"Hi, I'm your interviewer today. Here's the situation:\n\n"
        f"**{case_data['context']}**\n\n"
        f"Before we dive in, go ahead and walk me through your understanding of the "
        f"situation and what we're trying to figure out."
    )

    st.session_state.case_title = case_title
    st.session_state.case_data = case_data
    st.session_state.current_stage = 1  # stage 0 (background) is the opening line itself
    st.session_state.display_messages = [{"role": "assistant", "content": opening_line}]
    st.session_state.api_messages = []
    st.session_state.wrong_streak = 0
    st.session_state.case_over = False

st.sidebar.markdown(f"**Stage {st.session_state.current_stage}/5: {STAGE_LABELS[st.session_state.current_stage]}**")
with st.sidebar.expander("Case background", expanded=True):
    st.markdown(st.session_state.case_data["context"])
st.sidebar.caption(
    "Questions and data are revealed step by step during the interview, just like a real case "
    "interview - they won't be listed here in advance."
)

for message in st.session_state.display_messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

if st.session_state.case_over:
    st.info("This case has ended. Choose a case from the sidebar (or reselect this one) to start a fresh attempt.")
    user_answer = None
else:
    user_answer = st.chat_input("Type your answer...")

if user_answer:
    st.session_state.display_messages.append({"role": "user", "content": user_answer})
    st.session_state.api_messages.append({"role": "user", "content": user_answer})
    with st.chat_message("user"):
        st.markdown(user_answer)

    with st.chat_message("assistant"):
        with st.spinner("Interviewer is thinking..."):
            try:
                reply, new_stage, answer_status = get_interviewer_reply(
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
        st.markdown(reply)

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
    st.rerun()
