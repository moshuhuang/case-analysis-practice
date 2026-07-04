import os

import streamlit as st
from anthropic import Anthropic
from dotenv import load_dotenv

from agents.case_loader import extract_context_and_first_question, list_cases, load_case
from agents.interviewer import build_system_prompt, get_interviewer_reply

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
    context, first_question = extract_context_and_first_question(case_data["candidate_view"])
    opening_line = (
        f"Hi, I'm your interviewer today. Let's dive into today's case.\n\n"
        f"**Context:** {context}\n\n**{first_question}**"
    )

    st.session_state.case_title = case_title
    st.session_state.system_prompt = build_system_prompt(case_data["full_text"])
    st.session_state.candidate_view = case_data["candidate_view"]
    st.session_state.display_messages = [{"role": "assistant", "content": opening_line}]
    st.session_state.api_messages = []

with st.sidebar.expander("Case material", expanded=True):
    st.markdown(st.session_state.candidate_view)

for message in st.session_state.display_messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

user_answer = st.chat_input("Type your answer...")

if user_answer:
    st.session_state.display_messages.append({"role": "user", "content": user_answer})
    st.session_state.api_messages.append({"role": "user", "content": user_answer})
    with st.chat_message("user"):
        st.markdown(user_answer)

    with st.chat_message("assistant"):
        with st.spinner("Interviewer is thinking..."):
            reply = get_interviewer_reply(
                client, st.session_state.system_prompt, st.session_state.api_messages
            )
        st.markdown(reply)

    st.session_state.display_messages.append({"role": "assistant", "content": reply})
    st.session_state.api_messages.append({"role": "assistant", "content": reply})
