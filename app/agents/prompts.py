from __future__ import annotations

from typing import Any

FILING_ANALYST_SYSTEM = """You are the filing analyst for an Indian-investor opportunity radar.
Return only valid JSON.
Use only the provided signal evidence and filing extracts.
Be precise and cautious. Avoid hype and investment advice.
"""

BULL_ANALYST_SYSTEM = """You are the bull analyst in a market-signal debate.
Return only valid JSON.
Build the strongest bullish interpretation that is supported by the evidence.
Do not invent catalysts, price targets, or unsupported numbers.
"""

BEAR_ANALYST_SYSTEM = """You are the bear analyst in a market-signal debate.
Return only valid JSON.
Build the strongest bearish or cautionary interpretation that is supported by the evidence.
Do not invent allegations, price targets, or unsupported numbers.
"""

REFEREE_SYSTEM = """You are the referee for a multi-agent market-signal workflow.
Return only valid JSON.
Weigh direct filing evidence more heavily than speculative reasoning.
Output a final investor-facing verdict without giving financial advice.
"""


def _trim(text: str, limit: int = 180) -> str:
    cleaned = " ".join(str(text or "").split())
    if len(cleaned) <= limit:
        return cleaned
    return cleaned[: limit - 3].rstrip() + "..."


def _attachment_lines(signal: dict[str, Any]) -> list[str]:
    lines = []
    for line in signal.get("attachment_highlights", [])[:5]:
        lines.append(f"- {line}")
    if lines:
        return lines

    seen: set[str] = set()
    for evidence in signal.get("evidence", [])[:3]:
        for line in evidence.get("attachment_parse", {}).get("highlights", [])[:2]:
            if line in seen:
                continue
            seen.add(line)
            lines.append(f"- {line}")
    return lines[:5]


def signal_snapshot(signal: dict[str, Any]) -> str:
    evidence_lines = []
    for item in signal.get("evidence", [])[:3]:
        bits = [
            f"type={item.get('event_type')}",
            f"headline={item.get('headline') or item.get('reason')}",
            f"score={item.get('score')}",
            f"date={item.get('event_date')}",
            f"details={_trim(item.get('raw_text') or item.get('reason') or '', 160)}",
        ]
        attachment_parse = item.get("attachment_parse") or {}
        if attachment_parse.get("highlights"):
            bits.append("attachment=" + " | ".join(_trim(line, 110) for line in attachment_parse["highlights"][:2]))
        evidence_lines.append("- " + " | ".join(bits))

    attachment_lines = _attachment_lines(signal)
    reasons = ", ".join(signal.get("reasons", [])[:4])
    tags = ", ".join(signal.get("tags", [])[:6])

    return "\n".join(
        [
            f"Symbol: {signal.get('symbol')}",
            f"Company: {signal.get('company')}",
            f"Rule direction: {signal.get('direction')}",
            f"Rule score: {signal.get('score')}",
            f"Primary reason: {signal.get('primary_reason')}",
            f"Other reasons: {reasons}",
            f"Event count: {signal.get('event_count')}",
            f"Tags: {tags}",
            "Evidence:",
            *evidence_lines,
            "Attachment highlights:",
            *(attachment_lines or ["- None parsed"]),
        ]
    )


def build_filing_prompt(signal: dict[str, Any]) -> str:
    return (
        "Review this filing-backed market signal and summarize only what the disclosed evidence supports.\n\n"
        + signal_snapshot(signal)
        + "\n\nReturn JSON only with this exact shape:\n"
        + "{\n"
        + '  "catalyst_type": "short category",\n'
        + '  "evidence_quality": "high|medium|low",\n'
        + '  "what_changed": "one crisp sentence",\n'
        + '  "key_facts": ["fact 1", "fact 2", "fact 3"],\n'
        + '  "bullish_clues": ["clue 1", "clue 2"],\n'
        + '  "bearish_clues": ["clue 1", "clue 2"],\n'
        + '  "watch_items": ["watch item 1", "watch item 2"]\n'
        + "}"
    )


def build_bull_prompt(signal: dict[str, Any], filing_brief: dict[str, Any]) -> str:
    return (
        "Build the strongest bullish case that is actually supported by the evidence below.\n\n"
        + signal_snapshot(signal)
        + "\n\nFiling analyst brief:\n"
        + f"- catalyst_type={filing_brief.get('catalyst_type')}\n"
        + f"- evidence_quality={filing_brief.get('evidence_quality')}\n"
        + f"- what_changed={filing_brief.get('what_changed')}\n"
        + "- bullish_clues="
        + " | ".join(filing_brief.get("bullish_clues", [])[:3])
        + "\n- bearish_clues="
        + " | ".join(filing_brief.get("bearish_clues", [])[:3])
        + "\n\nReturn JSON only with this exact shape:\n"
        + "{\n"
        + '  "stance": "bullish",\n'
        + '  "confidence": 0,\n'
        + '  "thesis": "one-sentence thesis",\n'
        + '  "summary": "1-2 sentences under 45 words",\n'
        + '  "supporting_points": ["point 1", "point 2", "point 3"],\n'
        + '  "cautions": ["caution 1", "caution 2"]\n'
        + "}"
    )


def build_bear_prompt(signal: dict[str, Any], filing_brief: dict[str, Any]) -> str:
    return (
        "Build the strongest bearish or cautionary case that is actually supported by the evidence below.\n\n"
        + signal_snapshot(signal)
        + "\n\nFiling analyst brief:\n"
        + f"- catalyst_type={filing_brief.get('catalyst_type')}\n"
        + f"- evidence_quality={filing_brief.get('evidence_quality')}\n"
        + f"- what_changed={filing_brief.get('what_changed')}\n"
        + "- bearish_clues="
        + " | ".join(filing_brief.get("bearish_clues", [])[:3])
        + "\n- watch_items="
        + " | ".join(filing_brief.get("watch_items", [])[:3])
        + "\n\nReturn JSON only with this exact shape:\n"
        + "{\n"
        + '  "stance": "bearish",\n'
        + '  "confidence": 0,\n'
        + '  "thesis": "one-sentence thesis",\n'
        + '  "summary": "1-2 sentences under 45 words",\n'
        + '  "supporting_points": ["point 1", "point 2", "point 3"],\n'
        + '  "cautions": ["caution 1", "caution 2"]\n'
        + "}"
    )


def build_referee_prompt(
    signal: dict[str, Any],
    filing_brief: dict[str, Any],
    bull_case: dict[str, Any],
    bear_case: dict[str, Any],
) -> str:
    return (
        "Decide the final investor-facing verdict for this signal after reviewing the filing analyst, bull analyst, and bear analyst outputs.\n\n"
        + signal_snapshot(signal)
        + "\n\nFiling analyst brief:\n"
        + f"- catalyst_type={filing_brief.get('catalyst_type')}\n"
        + f"- evidence_quality={filing_brief.get('evidence_quality')}\n"
        + f"- what_changed={filing_brief.get('what_changed')}\n"
        + "- key_facts="
        + " | ".join(filing_brief.get("key_facts", [])[:4])
        + "\n\nBull analyst:\n"
        + f"- confidence={bull_case.get('confidence')}\n"
        + f"- thesis={bull_case.get('thesis')}\n"
        + "- supporting_points="
        + " | ".join(bull_case.get("supporting_points", [])[:4])
        + "\n\nBear analyst:\n"
        + f"- confidence={bear_case.get('confidence')}\n"
        + f"- thesis={bear_case.get('thesis')}\n"
        + "- supporting_points="
        + " | ".join(bear_case.get("supporting_points", [])[:4])
        + "\n\nReturn JSON only with this exact shape:\n"
        + "{\n"
        + '  "direction": "bullish|bearish|neutral",\n'
        + '  "confidence": 0,\n'
        + '  "signal_label": "short headline under 8 words",\n'
        + '  "summary": "1-2 sentences under 45 words",\n'
        + '  "why_it_matters": "one sentence under 22 words",\n'
        + '  "risk_note": "one sentence under 22 words",\n'
        + '  "key_evidence": ["evidence 1", "evidence 2", "evidence 3"],\n'
        + '  "action": "highlight|monitor|needs_review"\n'
        + "}"
    )
