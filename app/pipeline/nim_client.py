import base64
import json
import logging
import re
from typing import Any

import httpx

from app.pipeline.prompts import mock_json_response, vision_user_prompt
from app.settings import Settings

logger = logging.getLogger(__name__)

_JSON_FENCE = re.compile(r"```(?:json)?\s*([\s\S]*?)\s*```", re.IGNORECASE)


def _extract_json_object(text: str) -> dict[str, Any]:
    text = text.strip()
    m = _JSON_FENCE.search(text)
    if m:
        text = m.group(1).strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        start = text.find("{")
        end = text.rfind("}")
        if start >= 0 and end > start:
            return json.loads(text[start : end + 1])
        raise


async def call_vision_llm(
    settings: Settings,
    *,
    image_png_or_jpeg: bytes,
    media_type: str,
) -> dict[str, Any]:
    if settings.use_mock_vision:
        return json.loads(mock_json_response())

    if not settings.nim_api_key:
        raise RuntimeError("NIM_API_KEY is required when USE_MOCK_VISION is false")

    b64 = base64.b64encode(image_png_or_jpeg).decode("ascii")
    url = f"{settings.nim_base_url.rstrip('/')}/chat/completions"
    system = (
        "You are a KYC document OCR and reasoning engine for Indian identity documents. "
        "Respond with JSON ONLY."
    )
    user_text = vision_user_prompt()
    payload: dict[str, Any] = {
        "model": settings.vision_model,
        "temperature": 0.05,
        "max_tokens": 4096,
        "messages": [
            {"role": "system", "content": system},
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": user_text},
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:{media_type};base64,{b64}"},
                    },
                ],
            },
        ],
    }

    headers = {
        "Authorization": f"Bearer {settings.nim_api_key}",
        "Content-Type": "application/json",
    }

    async with httpx.AsyncClient(timeout=settings.request_timeout_s) as client:
        r = await client.post(url, headers=headers, json=payload)
        r.raise_for_status()
        body = r.json()

    content = body["choices"][0]["message"]["content"]
    if isinstance(content, list):
        text_parts = [c.get("text", "") for c in content if isinstance(c, dict)]
        text = "".join(text_parts)
    else:
        text = str(content)

    return _extract_json_object(text)
