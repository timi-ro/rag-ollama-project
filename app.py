import streamlit as st
from main import initialize, query

st.title("RAG Chat")
st.caption("Ask questions about your documents")


@st.cache_resource
def get_chain():
    return initialize()


rag_chain = get_chain()

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
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
        if message.get("sources"):
            st.caption(f"Sources: {', '.join(message['sources'])}")

# Chat input
if prompt := st.chat_input("Ask a question about your documents"):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            answer, sources = query(prompt, rag_chain, st.session_state.chat_history)
        st.markdown(answer)
        if sources:
            st.caption(f"Sources: {', '.join(sources)}")

    st.session_state.messages.append({"role": "assistant", "content": answer, "sources": sources})