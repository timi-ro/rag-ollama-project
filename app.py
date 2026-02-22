import datetime
import streamlit as st
from main import initialize, query_stream


def build_markdown_export(messages: list, model: str) -> str:
    lines = [
        f"# Chat Export",
        f"**Model:** {model}  ",
        f"**Date:** {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}",
        "",
    ]
    for msg in messages:
        if msg["role"] == "user":
            lines += [f"### You", msg["content"], ""]
        else:
            lines += [f"### Assistant", msg["content"]]
            if msg.get("sources"):
                lines.append(f"*Sources: {', '.join(msg['sources'])}*")
            if msg.get("feedback"):
                lines.append(f"*Feedback: {msg['feedback']}*")
            lines.append("")
    return "\n".join(lines)

st.title("RAG Chat")
st.caption("Ask questions about your documents")

AVAILABLE_MODELS = ["llama3.2", "mistral", "phi3", "codellama", "gemma2"]

with st.sidebar:
    st.header("Settings")
    selected_model = st.selectbox(
        "Model",
        AVAILABLE_MODELS,
        index=0,
    )
    st.caption("Switching models rebuilds the vector store.")

    st.divider()
    st.header("Export")
    if st.session_state.get("messages"):
        st.download_button(
            label="Download chat (.md)",
            data=build_markdown_export(st.session_state.messages, st.session_state.get("current_model", "unknown")),
            file_name=f"chat_{datetime.datetime.now().strftime('%Y%m%d_%H%M')}.md",
            mime="text/markdown",
        )
    else:
        st.caption("No chat to export yet.")


@st.cache_resource
def get_chain(model: str):
    return initialize(model)


# Clear chat when model changes
if st.session_state.get("current_model") != selected_model:
    st.session_state.current_model = selected_model
    st.session_state.chat_history = []
    st.session_state.messages = []

try:
    rag_chain = get_chain(selected_model)
except Exception as e:
    if "not found" in str(e).lower() or "404" in str(e):
        st.error(f"Model **{selected_model}** is not installed. Run `ollama pull {selected_model}` in your terminal, then reload.")
    else:
        st.error(f"Failed to initialize model: {e}")
    st.stop()

if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "messages" not in st.session_state:
    st.session_state.messages = []

if st.session_state.messages:
    if st.button("Clear chat"):
        st.session_state.chat_history = []
        st.session_state.messages = []
        st.rerun()

# Display previous messages
for i, message in enumerate(st.session_state.messages):
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
        if message.get("sources"):
            st.caption(f"Sources: {', '.join(message['sources'])}")
        if message["role"] == "assistant":
            feedback = message.get("feedback")
            col1, col2, _ = st.columns([1, 1, 10])
            with col1:
                if st.button("👍", key=f"up_{i}", disabled=feedback is not None):
                    st.session_state.messages[i]["feedback"] = "up"
                    st.rerun()
            with col2:
                if st.button("👎", key=f"down_{i}", disabled=feedback is not None):
                    st.session_state.messages[i]["feedback"] = "down"
                    st.rerun()
            if feedback:
                st.caption("Thanks for the feedback!")

# Chat input
if prompt := st.chat_input("Ask a question about your documents"):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        placeholder = st.empty()
        full_response = ""
        sources = []
        try:
            for token, final_sources in query_stream(prompt, rag_chain, st.session_state.chat_history):
                if final_sources is not None:
                    sources = final_sources
                else:
                    full_response += token
                    placeholder.markdown(full_response + "▌")
            placeholder.markdown(full_response)
            if sources:
                st.caption(f"Sources: {', '.join(sources)}")
        except Exception as e:
            placeholder.empty()
            if "not found" in str(e).lower() or "404" in str(e):
                st.error(f"Model **{selected_model}** is not installed. Run `ollama pull {selected_model}` in your terminal, then reload.")
            else:
                st.error(f"Something went wrong: {e}")
            st.session_state.messages.pop()
            st.stop()

    st.session_state.messages.append({"role": "assistant", "content": full_response, "sources": sources, "feedback": None})