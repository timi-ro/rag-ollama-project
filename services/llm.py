import os
from langchain_community.llms import Ollama
from dotenv import load_dotenv

load_dotenv()

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2")


def get_llm(model: str = None) -> Ollama:
    return Ollama(
        model=model or OLLAMA_MODEL,
        base_url=OLLAMA_BASE_URL,
        temperature=0,
    )


def generate_answer(llm: Ollama, question: str, context: str, conversation_history: list = None) -> str:
    history_text = ""
    if conversation_history:
        for msg in conversation_history:
            role = "User" if msg.get("role") == "user" else "Assistant"
            history_text += f"{role}: {msg.get('content', '')}\n"

    prompt = f"""You are a helpful assistant. Use the following context to answer the question.
If you don't know the answer based on the context, say so.

Context:
{context}
{f"Conversation history:{chr(10)}{history_text}" if history_text else ""}
Question: {question}

Answer:"""
    return llm.invoke(prompt)
