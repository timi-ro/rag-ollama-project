import asyncio
import os

# Only one embedding job runs at a time to prevent Ollama/CPU saturation.
embed_semaphore = asyncio.Semaphore(1)

# Caps total inflight upload requests. Excess requests receive a 503 immediately
# instead of queuing indefinitely and exhausting memory.
MAX_INFLIGHT_UPLOADS = int(os.getenv("MAX_INFLIGHT_UPLOADS", "10"))
upload_semaphore = asyncio.Semaphore(MAX_INFLIGHT_UPLOADS)