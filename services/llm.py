import os
from dotenv import load_dotenv

from langchain_core.messages import SystemMessage, HumanMessage, AIMessage

from services.plans import PLAN_CONFIG

load_dotenv()

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2")

_PROVIDER_DEFAULTS = {
    "openai":    "gpt-4o-mini",
    "gemini":    "gemini-2.0-flash",
    "anthropic": "claude-3-5-haiku-20241022",
}


def get_llm(plan: str = "free"):
    llm_type = PLAN_CONFIG[plan]["llm"]

    if llm_type == "ollama":
        from langchain_ollama import ChatOllama
        return ChatOllama(
            model=OLLAMA_MODEL,
            base_url=OLLAMA_BASE_URL,
            temperature=0,
        )

    # external
    provider = os.getenv("EXTERNAL_LLM_PROVIDER", "")
    if not provider:
        raise RuntimeError(
            "EXTERNAL_LLM_PROVIDER is not set. Configure it to use the gold plan."
        )
    model = os.getenv("EXTERNAL_LLM_MODEL", "") or _PROVIDER_DEFAULTS[provider]

    if provider == "openai":
        from langchain_openai import ChatOpenAI
        return ChatOpenAI(model=model, temperature=0)

    if provider == "gemini":
        from langchain_google_genai import ChatGoogleGenerativeAI
        return ChatGoogleGenerativeAI(model=model, temperature=0)

    if provider == "anthropic":
        from langchain_anthropic import ChatAnthropic
        return ChatAnthropic(model=model, temperature=0)

    raise RuntimeError(f"Unsupported EXTERNAL_LLM_PROVIDER: {provider!r}")


def _build_messages(question: str, context: str, conversation_history: list = None) -> list:
    messages = [
        SystemMessage(content=(
            "You are a helpful assistant. Use the following context to answer the question.\n"
            "If you don't know the answer based on the context, say so.\n\n"
            f"Context:\n{context}"
        ))
    ]

    if conversation_history:
        for msg in conversation_history:
            role = msg.get("role") if isinstance(msg, dict) else getattr(msg, "role", "")
            content = msg.get("content", "") if isinstance(msg, dict) else getattr(msg, "content", "")
            if role == "user":
                messages.append(HumanMessage(content=content))
            else:
                messages.append(AIMessage(content=content))

    messages.append(HumanMessage(content=question))
    return messages


def generate_answer(llm, question: str, context: str, conversation_history: list = None) -> str:
    return llm.invoke(_build_messages(question, context, conversation_history)).content


async def generate_answer_stream(llm, question: str, context: str, conversation_history: list = None):
    """Async generator yielding text tokens via LangChain astream."""
    async for chunk in llm.astream(_build_messages(question, context, conversation_history)):
        if hasattr(chunk, "content") and chunk.content:
            yield chunk.content