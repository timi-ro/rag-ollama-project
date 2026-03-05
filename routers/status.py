import os
from fastapi import APIRouter

router = APIRouter(tags=["status"])

_PROVIDER_DEFAULTS = {
    "openai":    "gpt-4o-mini",
    "gemini":    "gemini-2.0-flash",
    "anthropic": "claude-3-5-haiku-20241022",
}


@router.get("/status")
def status():
    provider = os.getenv("EXTERNAL_LLM_PROVIDER", "") or None
    if provider:
        model = os.getenv("EXTERNAL_LLM_MODEL", "") or _PROVIDER_DEFAULTS.get(provider)
        external_llm = {"provider": provider, "model": model}
    else:
        external_llm = {"provider": None, "model": None}

    return {
        "status": "ok",
        "version": "1.0.0",
        "ollama": {"model": os.getenv("OLLAMA_MODEL", "llama3.2")},
        "external_llm": external_llm,
    }
