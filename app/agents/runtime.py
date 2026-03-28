from __future__ import annotations

import json
from typing import Any, TypeVar

import requests
from pydantic import BaseModel

from app.config import settings

ModelT = TypeVar("ModelT", bound=BaseModel)


def extract_output_text(payload: dict[str, Any]) -> str:
    texts: list[str] = []
    for item in payload.get("output", []):
        if item.get("type") != "message":
            continue
        for content in item.get("content", []):
            if content.get("type") == "output_text":
                texts.append(content.get("text", ""))
    if texts:
        return "\n".join(texts).strip()
    output_text = payload.get("output_text")
    return output_text.strip() if isinstance(output_text, str) else ""


def parse_json_object(text: str) -> dict[str, Any]:
    text = text.strip()
    if not text:
        raise ValueError("Empty model response.")
    if text.startswith("{") and text.endswith("}"):
        return json.loads(text)

    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or start >= end:
        raise ValueError("Could not find JSON object in model response.")
    return json.loads(text[start : end + 1])


def call_json_agent(
    *,
    system_prompt: str,
    prompt: str,
    response_model: type[ModelT],
    model: str | None = None,
    max_output_tokens: int = 260,
) -> dict[str, Any]:
    if not settings.openai_api_key:
        raise RuntimeError("OPENAI_API_KEY is not set.")

    response = requests.post(
        f"{settings.openai_base_url.rstrip('/')}/responses",
        headers={
            "Authorization": f"Bearer {settings.openai_api_key}",
            "Content-Type": "application/json",
        },
        json={
            "model": model or settings.agent_model,
            "instructions": system_prompt,
            "input": prompt,
            "max_output_tokens": max_output_tokens,
            "store": False,
        },
        timeout=90,
    )
    response.raise_for_status()
    payload = response.json()
    text = extract_output_text(payload)
    parsed = parse_json_object(text)
    validated = response_model.model_validate(parsed).model_dump()
    validated["_usage"] = payload.get("usage", {})
    validated["_model"] = payload.get("model")
    return validated
