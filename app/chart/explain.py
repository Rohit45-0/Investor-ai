from __future__ import annotations

import json
from datetime import datetime
from typing import Any

import requests

from app.config import settings

SYSTEM_PROMPT = """You are a technical-pattern analyst for Indian equity investors.
Return only valid JSON.
Use only the structured signal evidence provided.
Do not make price targets or investment advice.
Keep the tone crisp, plain-English, and retail-friendly.
The JSON object must contain:
signal_label, direction, confidence, summary, why_it_matters, risk_note
"""


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


def heuristic_explanation(signal: dict[str, Any]) -> dict[str, Any]:
    backtest = signal.get("backtest") or {}
    family = str(signal.get("pattern_family") or "pattern").replace("_", " ")
    direction = str(signal.get("direction") or "neutral")
    label = str(signal.get("pattern_label") or signal.get("primary_reason") or "Chart Pattern").strip()
    timeframe = str(signal.get("timeframe") or "1d").strip()
    success_rate = backtest.get("success_rate")
    sample_size = int(backtest.get("sample_size") or 0)
    support = (signal.get("support_levels") or [{}])[0]
    resistance = (signal.get("resistance_levels") or [{}])[0]
    support_text = f"support near {float(support.get('price')):.2f}" if support and support.get("price") is not None else "near an observed support zone"
    resistance_text = f"resistance near {float(resistance.get('price')):.2f}" if resistance and resistance.get("price") is not None else "near an observed resistance zone"

    if direction == "bullish":
        summary = f"{label} is active on the {timeframe} chart, with price reacting around {support_text} and trying to extend higher."
        why = "It can mark fresh upside momentum if price keeps holding above the trigger zone."
        risk = "The setup weakens fast if price slips back under the breakout or support area."
    else:
        summary = f"{label} is active on the {timeframe} chart, with price reacting around {resistance_text} and starting to lose momentum."
        why = "It can warn that supply is building and the next move may favor downside follow-through."
        risk = "The setup weakens fast if price reclaims resistance and invalidates the trigger."

    if success_rate is not None and sample_size:
        summary += f" Historical 7-day success on this stock is {success_rate:.1f}% across {sample_size} occurrences."
    elif family:
        why += f" This belongs to the {family} family of chart setups."

    return {
        "signal_label": label,
        "direction": direction,
        "confidence": int(signal.get("confidence") or 0),
        "summary": summary[:220],
        "why_it_matters": why[:140],
        "risk_note": risk[:140],
        "model": "heuristic",
        "usage": {},
    }


def build_prompt(signal: dict[str, Any]) -> str:
    evidence_lines = []
    for item in signal.get("evidence", [])[:4]:
        evidence_lines.append(f"- {item.get('label')}: {item.get('detail')}")

    backtest = signal.get("backtest") or {}
    return f"""
Explain this chart-pattern signal in plain English for an Indian retail investor dashboard.

Symbol: {signal.get('symbol')}
Company: {signal.get('company')}
Timeframe: {signal.get('timeframe')}
Pattern family: {signal.get('pattern_family')}
Pattern label: {signal.get('pattern_label')}
Direction: {signal.get('direction')}
Score: {signal.get('score')}
Confidence: {signal.get('confidence')}

Backtest:
- success_rate={backtest.get('success_rate')}
- sample_size={backtest.get('sample_size')}
- horizon_days={backtest.get('horizon_days')}
- avg_forward_return={backtest.get('avg_forward_return')}
- reliability={backtest.get('reliability')}

Evidence:
{chr(10).join(evidence_lines)}

Return JSON only with this exact shape:
{{
  "signal_label": "short label under 8 words",
  "direction": "bullish|bearish|neutral",
  "confidence": 0,
  "summary": "1-2 sentences under 55 words",
  "why_it_matters": "one sentence under 24 words",
  "risk_note": "one sentence under 24 words"
}}
""".strip()


def call_openai(prompt: str) -> dict[str, Any]:
    if not settings.openai_api_key:
        raise RuntimeError("OPENAI_API_KEY is not set.")

    response = requests.post(
        f"{settings.openai_base_url.rstrip('/')}/responses",
        headers={
            "Authorization": f"Bearer {settings.openai_api_key}",
            "Content-Type": "application/json",
        },
        json={
            "model": settings.openai_model,
            "instructions": SYSTEM_PROMPT,
            "input": prompt,
            "max_output_tokens": 220,
            "store": False,
        },
        timeout=90,
    )
    response.raise_for_status()
    payload = response.json()
    text = extract_output_text(payload)
    parsed = parse_json_object(text)
    parsed["_usage"] = payload.get("usage", {})
    parsed["_model"] = payload.get("model")
    return parsed


def explain_chart_document(
    document: dict[str, Any],
    *,
    limit: int = settings.chart_explanation_limit,
) -> dict[str, Any]:
    enriched = json.loads(json.dumps(document))
    attempted = 0
    completed = 0

    for signal in enriched.get("signals", []):
        signal["llm_explanation"] = heuristic_explanation(signal)

    signals = sorted(enriched.get("signals", []), key=lambda item: int(item.get("score") or 0), reverse=True)
    for signal in signals[:limit]:
        attempted += 1
        try:
            explanation = call_openai(build_prompt(signal))
            confidence = explanation.get("confidence")
            if isinstance(confidence, (int, float)):
                confidence = max(0, min(100, int(confidence)))
            else:
                confidence = int(signal.get("confidence") or 0)
            signal["llm_explanation"] = {
                "signal_label": str(explanation.get("signal_label") or signal.get("pattern_label") or "").strip(),
                "direction": str(explanation.get("direction") or signal.get("direction")).strip(),
                "confidence": confidence,
                "summary": str(explanation.get("summary") or "").strip(),
                "why_it_matters": str(explanation.get("why_it_matters") or "").strip(),
                "risk_note": str(explanation.get("risk_note") or "").strip(),
                "model": explanation.get("_model"),
                "usage": explanation.get("_usage"),
            }
            completed += 1
        except Exception as exc:  # noqa: BLE001
            signal["llm_explanation_error"] = str(exc)

    enriched["explanations"] = {
        "provider": "openai",
        "model": settings.openai_model,
        "attempted": attempted,
        "completed": completed,
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "mode": "chart_patterns",
    }
    return enriched
