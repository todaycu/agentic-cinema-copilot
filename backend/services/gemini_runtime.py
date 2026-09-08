"""Bounded, non-blocking access to Gemini for the FastAPI agent runtime."""

import asyncio


async def generate_content(client, *, model: str, contents: str, attempts: int = 1):
    """Retry transient provider failures without blocking mission SSE or health routes."""
    last_error = None
    for attempt in range(attempts):
        try:
            return await asyncio.wait_for(
                asyncio.to_thread(client.models.generate_content, model=model, contents=contents),
                timeout=12,
            )
        except Exception as error:
            last_error = error
            if attempt < attempts - 1:
                await asyncio.sleep(1.5 * (attempt + 1))
    raise last_error
