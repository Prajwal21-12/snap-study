import smtplib
from email.message import EmailMessage

import streamlit as st
from google import genai
from google.genai import types

from prompts import (
    SYSTEM_PROMPT,
    WELCOME_MESSAGE_TEMPLATE,
    SUMMARY_REQUEST_PROMPT,
)


# --------------------------------------------------
# CONFIGURATION
# --------------------------------------------------

MODEL_NAME = "gemini-3.5-flash-lite"

st.set_page_config(
    page_title="Snap & Study",
    page_icon="📚",
    layout="centered",
)

GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"]


# --------------------------------------------------
# GEMINI CLIENT
# --------------------------------------------------

@st.cache_resource
def get_gemini_client():
    return genai.Client(api_key=GEMINI_API_KEY)


gemini_client = get_gemini_client()


# --------------------------------------------------
# GMAIL FUNCTION
# --------------------------------------------------

def send_summary_email(summary):
    msg = EmailMessage()

    msg["Subject"] = "📚 Snap & Study - Study Summary"
    msg["From"] = st.secrets["GMAIL_ADDRESS"]
    msg["To"] = st.secrets["GMAIL_ADDRESS"]

    msg.set_content(summary)

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(
            st.secrets["GMAIL_ADDRESS"],
            st.secrets["GMAIL_APP_PASSWORD"],
        )

        server.send_message(msg)


# --------------------------------------------------
# ONBOARDING
# --------------------------------------------------

if "onboarded" not in st.session_state:

    st.title("📚 Snap & Study")
    st.caption("Your AI Study Assistant")

    with st.form("onboarding_form"):

        name = st.text_input("Your name")

        submitted = st.form_submit_button(
            "Let's Study 🚀"
        )

        if submitted:

            if not name.strip():

                st.warning(
                    "Please enter your name."
                )

            else:

                st.session_state.name = name.strip()

                st.session_state.chat = (
                    gemini_client.chats.create(
                        model=MODEL_NAME,
                        config=types.GenerateContentConfig(
                            system_instruction=SYSTEM_PROMPT
                        ),
                    )
                )

                st.session_state.messages = []

                st.session_state.onboarded = True

                st.rerun()

    st.stop()


# --------------------------------------------------
# GEMINI CHAT FUNCTION
# --------------------------------------------------

def ask_gemini(parts):

    try:

        response = st.session_state.chat.send_message(
            parts
        )

        return response.text

    except Exception as error:

        return (
            "Sorry, something went wrong:\n\n"
            f"{error}"
        )


# --------------------------------------------------
# MESSAGE FUNCTIONS
# --------------------------------------------------

def add_text_message(role, content):

    st.session_state.messages.append(
        {
            "role": role,
            "kind": "text",
            "content": content,
        }
    )


def add_image_message(role, content):

    st.session_state.messages.append(
        {
            "role": role,
            "kind": "image",
            "content": content,
        }
    )


def render_message(message):

    with st.chat_message(message["role"]):

        if message["kind"] == "text":

            st.write(message["content"])

        elif message["kind"] == "image":

            st.image(message["content"])


# --------------------------------------------------
# MAIN APP
# --------------------------------------------------

st.title("📚 Snap & Study")

st.caption(
    f"Welcome, {st.session_state.name}! "
    "Ask a question or upload a study image."
)


# --------------------------------------------------
# WELCOME MESSAGE
# --------------------------------------------------

if not st.session_state.messages:

    add_text_message(
        "assistant",
        WELCOME_MESSAGE_TEMPLATE.format(
            name=st.session_state.name
        ),
    )


# --------------------------------------------------
# DISPLAY CHAT HISTORY
# --------------------------------------------------

for message in st.session_state.messages:

    render_message(message)


# --------------------------------------------------
# CHAT INPUT + IMAGE UPLOAD
# --------------------------------------------------

user_input = st.chat_input(
    "Ask a question or attach an image...",
    accept_file=True,
    file_type=[
        "jpg",
        "jpeg",
        "png",
    ],
)


if user_input:

    photo = (
        user_input.files[0]
        if user_input.files
        else None
    )

    text = user_input.text

    parts = []


    # ----------------------------------------------
    # IMAGE
    # ----------------------------------------------

    if photo is not None:

        photo_bytes = photo.getvalue()

        add_image_message(
            "user",
            photo_bytes,
        )

        parts.append(
            types.Part.from_bytes(
                data=photo_bytes,
                mime_type=photo.type,
            )
        )


    # ----------------------------------------------
    # TEXT
    # ----------------------------------------------

    if text:

        add_text_message(
            "user",
            text,
        )

        parts.append(text)


    # ----------------------------------------------
    # IMAGE ONLY
    # ----------------------------------------------

    elif photo is not None:

        parts.append(
            """
            Explain this image as a study tutor.

            Identify the question, diagram, notes,
            formula, or important information.

            Explain the concept clearly in simple
            student-friendly language.

            If there is a question, solve it
            step by step and give the final answer.
            """
        )


    # ----------------------------------------------
    # GEMINI RESPONSE
    # ----------------------------------------------

    if parts:

        with st.spinner(
            "🔍 Understanding..."
        ):

            answer = ask_gemini(parts)


        add_text_message(
            "assistant",
            answer,
        )

        st.rerun()


# --------------------------------------------------
# SEND STUDY SUMMARY
# --------------------------------------------------

st.divider()

if st.button("📧 Send Study Summary"):

    conversation = []

    for message in st.session_state.messages:

        if message["kind"] == "text":

            conversation.append(
                f"{message['role'].upper()}: {message['content']}"
            )

    conversation_text = "\n\n".join(conversation)

    with st.spinner("📝 Creating your study summary..."):

        try:

            summary_response = gemini_client.models.generate_content(
                model=MODEL_NAME,
                contents=(
                    SUMMARY_REQUEST_PROMPT
                    + "\n\nConversation:\n"
                    + conversation_text
                ),
            )

            summary = summary_response.text

            send_summary_email(summary)

            st.success(
                "✅ Study summary sent to your Gmail!"
            )

        except Exception as error:

            st.error(
                f"❌ Email failed: {error}"
            )