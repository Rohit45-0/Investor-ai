from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Any

import requests

from app.config import settings
from app.storage import (
    enriched_signals_path,
    explained_signals_path,
    latest_run_label,
    load_json,
    save_json,
    signals_path,
)

SYSTEM_PROMPT = """You are an equity-market signal analyst.
Return only valid JSON.
Use only the evidence provided.
Do not make price targets or investment advice.
Keep the tone crisp, factual, and useful for a retail investor dashboard.
The JSON object must contain:
signal_label, direction, confidence, summary, why_it_matters, risk_note
"""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Add OpenAI explanations to top signals.")
    parser.add_argument("--run-label", help="Processed run label to explain. Defaults to latest.")
    parser.add_argument(
        "--data-root",
        default=str(settings.data_dir),
        help="Data directory that contains raw/ and processed/.",
    )
    parser.add_argument("--limit", type=int, default=settings.explanation_limit)
    parser.add_argument("--force", action="store_true")
    return parser.parse_args()


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


def build_prompt(signal: dict[str, Any]) -> str:
    evidence_lines = []
    for item in signal.get("evidence", [])[:3]:
        detail = str(item.get("raw_text") or "").strip()
        if len(detail) > 140:
            detail = detail[:137].rstrip() + "..."
        attachment_bits = []
        parsed = item.get("attachment_parse") or {}
        if parsed.get("highlights"):
            attachment_bits.append("attachment=" + " | ".join(parsed["highlights"][:2]))
        evidence_lines.append(
            f"- [{item.get('event_type')}] {item.get('headline')} "
            f"(score={item.get('score')}, date={item.get('event_date')}) "
            f"details={detail}"
            + (f" {' '.join(attachment_bits)}" if attachment_bits else "")
        )

    return f"""
Create a compact investor-facing explanation for this signal.

Symbol: {signal.get('symbol')}
Company: {signal.get('company')}
Rule-based direction: {signal.get('direction')}
Rule-based score: {signal.get('score')}
Primary reason: {signal.get('primary_reason')}
Other reasons: {', '.join(signal.get('reasons', []))}

Evidence:
{chr(10).join(evidence_lines)}

Return JSON only, with this exact shape:
{{
  "signal_label": "short headline under 8 words",
  "direction": "bullish|bearish|neutral",
  "confidence": 0,
  "summary": "1-2 sentences under 45 words total",
  "why_it_matters": "one sentence under 22 words",
  "risk_note": "one sentence under 22 words"
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


def explain_document(
    document: dict[str, Any],
    *,
    limit: int = settings.explanation_limit,
    force: bool = False,
) -> dict[str, Any]:
    enriched = json.loads(json.dumps(document))
    attempted = 0
    completed = 0

    signals = sorted(enriched.get("signals", []), key=lambda item: item.get("score", 0), reverse=True)
    for signal in signals[:limit]:
        if signal.get("llm_explanation") and not force:
            continue
        attempted += 1
        try:
            explanation = call_openai(build_prompt(signal))
            confidence = explanation.get("confidence")
            if isinstance(confidence, (int, float)):
                confidence = max(0, min(100, int(confidence)))
            else:
                confidence = signal.get("confidence")
            signal.pop("llm_explanation_error", None)
            signal["llm_explanation"] = {
                "signal_label": str(explanation.get("signal_label") or "").strip(),
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
    }

    enriched["top_opportunities"] = [
        signal for signal in enriched.get("signals", []) if signal.get("direction") == "bullish"
    ][:8]
    enriched["top_risks"] = [
        signal for signal in enriched.get("signals", []) if signal.get("direction") == "bearish"
    ][:5]
    return enriched


def explain_run(
    run_label: str,
    *,
    data_root: Path | None = None,
    limit: int = settings.explanation_limit,
    force: bool = False,
) -> dict[str, Any]:
    root = data_root or settings.data_dir
    explained_path = explained_signals_path(run_label, root)
    scored_path = signals_path(run_label, root)
    enriched_path = enriched_signals_path(run_label, root)
    freshest_base = enriched_path if enriched_path.exists() else scored_path
    if force or not explained_path.exists():
        source_path = freshest_base
    elif freshest_base.exists() and freshest_base.stat().st_mtime > explained_path.stat().st_mtime:
        source_path = freshest_base
    else:
        source_path = explained_path

    document = load_json(source_path)
    enriched = explain_document(document, limit=limit, force=force)
    save_json(explained_path, enriched)
    return enriched


def main() -> None:
    args = parse_args()
    data_root = Path(args.data_root)
    run_label = args.run_label or latest_run_label(data_root)
    if not run_label:
        raise SystemExit("No processed runs found to explain.")

    enriched = explain_run(run_label, data_root=data_root, limit=args.limit, force=args.force)
    explanations = enriched.get("explanations", {})
    print(f"Run label: {enriched['run_label']}")
    print(f"Explanations attempted: {explanations.get('attempted', 0)}")
    print(f"Explanations completed: {explanations.get('completed', 0)}")
    print(f"Explained signals file: {explained_signals_path(run_label, data_root)}")


if __name__ == "__main__":
    main()
