import os
from dotenv import load_dotenv

from langchain_core.messages import SystemMessage, HumanMessage, AIMessage

from services.crypto import decrypt_field
from services.plans import PLAN_CONFIG

load_dotenv()

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2")

PROVIDER_DEFAULTS = {
    "openai":    "gpt-4o-mini",
    "gemini":    "gemini-2.0-flash",
    "anthropic": "claude-3-5-haiku-20241022",
}

VALID_PROVIDERS = set(PROVIDER_DEFAULTS)


def get_llm(site):
    """Return the appropriate LangChain chat model for the given site.

    Ollama plans (free, plus, enterprise) use the shared local Ollama instance.
    Business plan sites use the provider/model/api_key stored on the site record.
    """
    llm_type = PLAN_CONFIG[site.plan]["llm"]

    if llm_type == "ollama":
        from langchain_ollama import ChatOllama
        return ChatOllama(model=OLLAMA_MODEL, base_url=OLLAMA_BASE_URL, temperature=0)

    # business plan — use per-site credentials
    provider = site.llm_provider
    if not provider:
        raise RuntimeError(
            "External LLM not configured for this site. "
            "Ask your administrator to set it via PATCH /admin/sites/{id}/llm."
        )

    api_key = decrypt_field(site.llm_api_key) if site.llm_api_key else None
    if not api_key:
        raise RuntimeError(
            f"API key missing for provider '{provider}'. "
            "Ask your administrator to set it via PATCH /admin/sites/{id}/llm."
        )

    model = site.llm_model or PROVIDER_DEFAULTS.get(provider, "")

    if provider == "openai":
        from langchain_openai import ChatOpenAI
        return ChatOpenAI(model=model, temperature=0, openai_api_key=api_key)

    if provider == "gemini":
        from langchain_google_genai import ChatGoogleGenerativeAI
        return ChatGoogleGenerativeAI(model=model, temperature=0, google_api_key=api_key)

    if provider == "anthropic":
        from langchain_anthropic import ChatAnthropic
        return ChatAnthropic(model=model, temperature=0, anthropic_api_key=api_key)

    raise RuntimeError(f"Unsupported LLM provider: {provider!r}")


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