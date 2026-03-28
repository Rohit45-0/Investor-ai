from __future__ import annotations

import json
import operator
from datetime import datetime
from pathlib import Path
from typing import Annotated, Any, TypedDict

from langgraph.graph import END, START, StateGraph

from app.attachments import enrich_document, enrich_signal, refresh_top_lists
from app.collect import collect_and_write, resolve_date_range
from app.config import settings
from app.scoring import score_run
from app.storage import explained_signals_path, enriched_signals_path, save_json, signals_path

from .prompts import (
    BEAR_ANALYST_SYSTEM,
    BULL_ANALYST_SYSTEM,
    FILING_ANALYST_SYSTEM,
    REFEREE_SYSTEM,
    build_bear_prompt,
    build_bull_prompt,
    build_filing_prompt,
    build_referee_prompt,
)
from .runtime import call_json_agent
from .schemas import DebateCase, FilingBrief, Verdict


class SignalAgentState(TypedDict, total=False):
    signal: dict[str, Any]
    attachments_per_signal: int
    include_attachments: bool
    filing_brief: dict[str, Any]
    bull_case: dict[str, Any]
    bear_case: dict[str, Any]
    verdict: dict[str, Any]
    final_signal: dict[str, Any]
    trace: Annotated[list[dict[str, Any]], operator.add]


class MarketAgentState(TypedDict, total=False):
    days_back: int
    from_date_text: str | None
    to_date_text: str | None
    output_root: str | None
    include_explanations: bool
    explanation_limit: int
    include_attachments: bool
    attachment_signal_limit: int
    attachments_per_signal: int
    agent_signal_limit: int
    run_label: str
    collection: dict[str, Any]
    scored_document: dict[str, Any]
    candidate_signals: list[dict[str, Any]]
    reviewed_signals: list[dict[str, Any]]
    final_document: dict[str, Any]
    timeline: Annotated[list[dict[str, Any]], operator.add]


_SIGNAL_GRAPH = None
_MARKET_GRAPH = None


def now_stamp() -> str:
    return datetime.now().isoformat(timespec="seconds")


def clone(payload: Any) -> Any:
    return json.loads(json.dumps(payload))


def trace_event(agent: str, message: str, **metadata: Any) -> dict[str, Any]:
    event = {
        "agent": agent,
        "message": message,
        "timestamp": now_stamp(),
    }
    if metadata:
        event["metadata"] = metadata
    return event


def trim_headline(text: str, words: int = 6) -> str:
    parts = [part for part in str(text or "").replace("|", " ").split() if part]
    if not parts:
        return "Market Signal"
    return " ".join(parts[:words])


def clamp_confidence(value: Any, fallback: int = 50) -> int:
    if isinstance(value, (int, float)):
        return max(0, min(100, int(value)))
    return fallback


def sanitize_direction(value: str | None, fallback: str = "neutral") -> str:
    lowered = str(value or "").strip().lower()
    if lowered in {"bullish", "bearish", "neutral"}:
        return lowered
    return fallback


def sanitize_action(value: str | None, fallback: str = "monitor") -> str:
    lowered = str(value or "").strip().lower()
    if lowered in {"highlight", "monitor", "needs_review"}:
        return lowered
    return fallback


def leading_points(items: list[str] | None, *, limit: int = 3) -> list[str]:
    cleaned = []
    for item in items or []:
        text = " ".join(str(item or "").split())
        if text and text not in cleaned:
            cleaned.append(text)
        if len(cleaned) >= limit:
            break
    return cleaned


def aggregate_usage(*payloads: dict[str, Any]) -> dict[str, Any]:
    total = {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0}
    for payload in payloads:
        usage = payload.get("_usage") or {}
        for key in total:
            value = usage.get(key)
            if isinstance(value, (int, float)):
                total[key] += int(value)
    return total


def filing_fallback(signal: dict[str, Any], parsing: dict[str, int], error: str | None = None) -> dict[str, Any]:
    highlights = leading_points(signal.get("attachment_highlights") or [])
    facts = []
    for evidence in signal.get("evidence", [])[:3]:
        facts.extend(leading_points(evidence.get("attachment_parse", {}).get("highlights"), limit=2))
        if len(facts) >= 3:
            break
    reasons = leading_points(signal.get("reasons"), limit=3)
    bullish_clues = reasons[:2] if signal.get("direction") == "bullish" else highlights[:2]
    bearish_clues = reasons[:2] if signal.get("direction") == "bearish" else []
    watch_items = [
        "Check the full exchange filing for size, timing, and follow-up disclosures.",
    ]
    brief = FilingBrief(
        catalyst_type=signal.get("primary_reason") or "Disclosure update",
        evidence_quality="high" if parsing.get("completed") else "medium" if signal.get("evidence") else "low",
        what_changed=highlights[0] if highlights else (reasons[0] if reasons else "A potentially material filing was identified."),
        key_facts=leading_points(highlights + facts + reasons, limit=4),
        bullish_clues=leading_points(bullish_clues, limit=3),
        bearish_clues=leading_points(bearish_clues, limit=3),
        watch_items=leading_points(watch_items + signal.get("reasons", []), limit=3),
    ).model_dump()
    if error:
        brief["_error"] = error
    brief["_model"] = "heuristic"
    brief["_usage"] = {}
    brief["attachment_parsing"] = parsing
    return brief


def bull_fallback(signal: dict[str, Any], filing_brief: dict[str, Any], error: str | None = None) -> dict[str, Any]:
    base = 72 if signal.get("direction") == "bullish" else 48
    case = DebateCase(
        stance="bullish",
        confidence=clamp_confidence(base + signal.get("positive_event_count", 0) * 4, base),
        thesis=f"{signal.get('symbol')} has a constructive disclosure signal worth investor attention.",
        summary=f"{filing_brief.get('what_changed') or signal.get('primary_reason')} The upside case depends on follow-through after the filing.",
        supporting_points=leading_points((filing_brief.get("bullish_clues") or []) + signal.get("reasons", []), limit=3),
        cautions=leading_points(filing_brief.get("watch_items"), limit=2),
    ).model_dump()
    if error:
        case["_error"] = error
    case["_model"] = "heuristic"
    case["_usage"] = {}
    return case


def bear_fallback(signal: dict[str, Any], filing_brief: dict[str, Any], error: str | None = None) -> dict[str, Any]:
    base = 72 if signal.get("direction") == "bearish" else 46
    case = DebateCase(
        stance="bearish",
        confidence=clamp_confidence(base + signal.get("negative_event_count", 0) * 4, base),
        thesis=f"{signal.get('symbol')} may need caution until the market fully digests the filing.",
        summary=f"{filing_brief.get('what_changed') or signal.get('primary_reason')} The risk case comes from incomplete context or adverse interpretation.",
        supporting_points=leading_points((filing_brief.get("bearish_clues") or []) + filing_brief.get("watch_items", []), limit=3),
        cautions=leading_points(signal.get("reasons"), limit=2),
    ).model_dump()
    if error:
        case["_error"] = error
    case["_model"] = "heuristic"
    case["_usage"] = {}
    return case


def referee_fallback(
    signal: dict[str, Any],
    filing_brief: dict[str, Any],
    bull_case: dict[str, Any],
    bear_case: dict[str, Any],
    error: str | None = None,
) -> dict[str, Any]:
    bull_conf = clamp_confidence(bull_case.get("confidence"), 45)
    bear_conf = clamp_confidence(bear_case.get("confidence"), 45)
    base_direction = sanitize_direction(signal.get("direction"), "neutral")
    if bull_conf >= bear_conf + 10:
        direction = "bullish"
        confidence = bull_conf
        why = bull_case.get("thesis") or signal.get("primary_reason")
    elif bear_conf >= bull_conf + 10:
        direction = "bearish"
        confidence = bear_conf
        why = bear_case.get("thesis") or signal.get("primary_reason")
    else:
        direction = base_direction if base_direction != "neutral" else "neutral"
        confidence = max(bull_conf, bear_conf, clamp_confidence(signal.get("confidence"), 50))
        why = filing_brief.get("what_changed") or signal.get("primary_reason")

    verdict = Verdict(
        direction=direction,
        confidence=confidence,
        signal_label=trim_headline(signal.get("primary_reason") or signal.get("headline") or "Market Signal", words=6),
        summary=f"{filing_brief.get('what_changed') or signal.get('primary_reason')} {why}"[:180],
        why_it_matters=(why or "The filing could move investor attention.")[:120],
        risk_note=(leading_points(bear_case.get("cautions"), limit=1) or ["Treat this as a research trigger, not an instruction."])[0][:120],
        key_evidence=leading_points(
            (filing_brief.get("key_facts") or [])
            + (bull_case.get("supporting_points") or [])
            + (bear_case.get("supporting_points") or []),
            limit=3,
        ),
        action="highlight" if confidence >= 70 else "monitor",
    ).model_dump()
    if error:
        verdict["_error"] = error
    verdict["_model"] = "heuristic"
    verdict["_usage"] = {}
    return verdict


def clean_agent_output(payload: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in payload.items() if not key.startswith("_")}


def filing_analyst_node(state: SignalAgentState) -> dict[str, Any]:
    signal = clone(state["signal"])
    parsing = {"attempted": 0, "completed": 0, "parsed_urls": 0}
    if state.get("include_attachments", True):
        signal, parsing = enrich_signal(
            signal,
            attachments_per_signal=state.get("attachments_per_signal", 2),
        )

    try:
        brief = call_json_agent(
            system_prompt=FILING_ANALYST_SYSTEM,
            prompt=build_filing_prompt(signal),
            response_model=FilingBrief,
            max_output_tokens=260,
        )
        brief["attachment_parsing"] = parsing
        status = "completed"
    except Exception as exc:  # noqa: BLE001
        brief = filing_fallback(signal, parsing, str(exc))
        status = "fallback"

    return {
        "signal": signal,
        "filing_brief": brief,
        "trace": [
            trace_event(
                "filing_analyst",
                f"Filing analysis {status}",
                attachment_attempted=parsing.get("attempted", 0),
                attachment_completed=parsing.get("completed", 0),
            )
        ],
    }


def bull_analyst_node(state: SignalAgentState) -> dict[str, Any]:
    try:
        case = call_json_agent(
            system_prompt=BULL_ANALYST_SYSTEM,
            prompt=build_bull_prompt(state["signal"], state.get("filing_brief", {})),
            response_model=DebateCase,
            max_output_tokens=220,
        )
        status = "completed"
    except Exception as exc:  # noqa: BLE001
        case = bull_fallback(state["signal"], state.get("filing_brief", {}), str(exc))
        status = "fallback"

    case["stance"] = "bullish"
    case["confidence"] = clamp_confidence(case.get("confidence"), 50)
    case["supporting_points"] = leading_points(case.get("supporting_points"), limit=3)
    case["cautions"] = leading_points(case.get("cautions"), limit=2)

    return {
        "bull_case": case,
        "trace": [
            trace_event(
                "bull_analyst",
                f"Bull thesis {status}",
                confidence=case.get("confidence"),
            )
        ],
    }


def bear_analyst_node(state: SignalAgentState) -> dict[str, Any]:
    try:
        case = call_json_agent(
            system_prompt=BEAR_ANALYST_SYSTEM,
            prompt=build_bear_prompt(state["signal"], state.get("filing_brief", {})),
            response_model=DebateCase,
            max_output_tokens=220,
        )
        status = "completed"
    except Exception as exc:  # noqa: BLE001
        case = bear_fallback(state["signal"], state.get("filing_brief", {}), str(exc))
        status = "fallback"

    case["stance"] = "bearish"
    case["confidence"] = clamp_confidence(case.get("confidence"), 50)
    case["supporting_points"] = leading_points(case.get("supporting_points"), limit=3)
    case["cautions"] = leading_points(case.get("cautions"), limit=2)

    return {
        "bear_case": case,
        "trace": [
            trace_event(
                "bear_analyst",
                f"Bear thesis {status}",
                confidence=case.get("confidence"),
            )
        ],
    }


def compose_final_signal(
    signal: dict[str, Any],
    filing_brief: dict[str, Any],
    bull_case: dict[str, Any],
    bear_case: dict[str, Any],
    verdict: dict[str, Any],
    trace: list[dict[str, Any]],
) -> dict[str, Any]:
    final_signal = clone(signal)
    direction = sanitize_direction(verdict.get("direction"), sanitize_direction(signal.get("direction"), "neutral"))
    confidence = clamp_confidence(verdict.get("confidence"), clamp_confidence(signal.get("confidence"), 50))
    verdict_usage = aggregate_usage(filing_brief, bull_case, bear_case, verdict)

    final_signal["direction"] = direction
    final_signal["confidence"] = confidence
    final_signal["llm_explanation"] = {
        "signal_label": verdict.get("signal_label") or trim_headline(signal.get("primary_reason") or "Market Signal"),
        "direction": direction,
        "confidence": confidence,
        "summary": verdict.get("summary") or filing_brief.get("what_changed") or signal.get("primary_reason"),
        "why_it_matters": verdict.get("why_it_matters") or bull_case.get("thesis") or bear_case.get("thesis"),
        "risk_note": verdict.get("risk_note") or (bear_case.get("cautions") or ["Treat this as a research trigger, not an instruction."])[0],
        "model": verdict.get("_model") or settings.agent_model,
        "usage": verdict_usage,
    }
    final_signal["agent_outputs"] = {
        "filing_analyst": clean_agent_output(filing_brief),
        "bull_analyst": clean_agent_output(bull_case),
        "bear_analyst": clean_agent_output(bear_case),
        "referee": clean_agent_output(verdict),
    }
    final_signal["agent_trace"] = trace
    final_signal["review_action"] = sanitize_action(verdict.get("action"), "monitor")

    key_evidence = leading_points(verdict.get("key_evidence"), limit=3)
    if key_evidence:
        reasons = leading_points(final_signal.get("reasons"), limit=4)
        for item in key_evidence:
            if item not in reasons:
                reasons.append(item)
        final_signal["reasons"] = reasons[:5]

    return final_signal


def referee_node(state: SignalAgentState) -> dict[str, Any]:
    try:
        verdict = call_json_agent(
            system_prompt=REFEREE_SYSTEM,
            prompt=build_referee_prompt(
                state["signal"],
                state.get("filing_brief", {}),
                state.get("bull_case", {}),
                state.get("bear_case", {}),
            ),
            response_model=Verdict,
            max_output_tokens=240,
        )
        status = "completed"
    except Exception as exc:  # noqa: BLE001
        verdict = referee_fallback(
            state["signal"],
            state.get("filing_brief", {}),
            state.get("bull_case", {}),
            state.get("bear_case", {}),
            str(exc),
        )
        status = "fallback"

    verdict["direction"] = sanitize_direction(verdict.get("direction"), sanitize_direction(state["signal"].get("direction"), "neutral"))
    verdict["confidence"] = clamp_confidence(verdict.get("confidence"), clamp_confidence(state["signal"].get("confidence"), 50))
    verdict["action"] = sanitize_action(verdict.get("action"), "monitor")
    verdict["key_evidence"] = leading_points(verdict.get("key_evidence"), limit=3)

    referee_trace = trace_event(
        "referee",
        f"Final verdict {status}",
        direction=verdict.get("direction"),
        confidence=verdict.get("confidence"),
        action=verdict.get("action"),
    )
    full_trace = [*state.get("trace", []), referee_trace]
    final_signal = compose_final_signal(
        state["signal"],
        state.get("filing_brief", {}),
        state.get("bull_case", {}),
        state.get("bear_case", {}),
        verdict,
        full_trace,
    )

    return {
        "verdict": verdict,
        "final_signal": final_signal,
        "trace": [referee_trace],
    }


def scout_market_universe_node(state: MarketAgentState) -> dict[str, Any]:
    target_root = Path(state.get("output_root") or settings.data_dir)
    date_range = resolve_date_range(
        days_back=state.get("days_back", 1),
        from_date_text=state.get("from_date_text"),
        to_date_text=state.get("to_date_text"),
    )
    collection = collect_and_write(date_range=date_range, output_root=target_root)
    return {
        "run_label": collection["run_label"],
        "collection": collection,
        "timeline": [
            trace_event(
                "scout",
                "Collected the daily market universe",
                run_label=collection["run_label"],
                normalized_event_count=collection["manifest"]["normalized_event_count"],
            )
        ],
    }


def router_node(state: MarketAgentState) -> dict[str, Any]:
    target_root = Path(state.get("output_root") or settings.data_dir)
    run_label = state["run_label"]
    scored = score_run(run_label, target_root)
    max_agent_signals = max(1, state.get("agent_signal_limit") or settings.agent_signal_limit)
    requested_limit = max(1, state.get("explanation_limit") or settings.explanation_limit)
    shortlist_limit = min(len(scored.get("signals", [])), max_agent_signals, requested_limit)
    candidate_signals = [clone(signal) for signal in scored.get("signals", [])[:shortlist_limit]]

    updates: dict[str, Any] = {
        "scored_document": scored,
        "candidate_signals": candidate_signals,
        "timeline": [
            trace_event(
                "router",
                "Scored disclosures and shortlisted candidate signals",
                shortlisted=len(candidate_signals),
                total_signals=scored["overview"]["total_signals"],
            )
        ],
    }

    if not state.get("include_explanations", True):
        if state.get("include_attachments", True):
            enriched = enrich_document(
                scored,
                limit_signals=state.get("attachment_signal_limit", 12),
                attachments_per_signal=state.get("attachments_per_signal", 2),
            )
            save_json(enriched_signals_path(run_label, target_root), enriched)
            updates["final_document"] = enriched
        else:
            updates["final_document"] = scored
        updates["candidate_signals"] = []

    return updates


def review_candidates_node(state: MarketAgentState) -> dict[str, Any]:
    candidates = state.get("candidate_signals", [])
    if not candidates or not state.get("include_explanations", True):
        return {
            "reviewed_signals": [],
            "timeline": [trace_event("agent_desk", "Skipped multi-agent review", shortlisted=len(candidates))],
        }

    graph = get_signal_graph()
    reviewed = []
    for rank, signal in enumerate(candidates, start=1):
        result = graph.invoke(
            {
                "signal": signal,
                "attachments_per_signal": state.get("attachments_per_signal", 2),
                "include_attachments": state.get("include_attachments", True),
            }
        )
        final_signal = clone(result.get("final_signal") or signal)
        final_signal["shortlist_rank"] = rank
        reviewed.append(final_signal)

    return {
        "reviewed_signals": reviewed,
        "timeline": [
            trace_event(
                "agent_desk",
                "Completed multi-agent review on shortlisted signals",
                reviewed=len(reviewed),
            )
        ],
    }


def publish_node(state: MarketAgentState) -> dict[str, Any]:
    target_root = Path(state.get("output_root") or settings.data_dir)
    run_label = state["run_label"]
    include_explanations = state.get("include_explanations", True)

    if state.get("final_document") and not include_explanations:
        document = clone(state["final_document"])
    else:
        document = clone(state["scored_document"])
        reviewed_by_symbol = {signal["symbol"]: signal for signal in state.get("reviewed_signals", [])}
        document["signals"] = [reviewed_by_symbol.get(signal["symbol"], signal) for signal in document.get("signals", [])]

    document["signals"].sort(
        key=lambda item: (item.get("direction") != "bullish", -int(item.get("score", 0)), item.get("symbol", ""))
    )
    refresh_top_lists(document)
    document["generated_at"] = now_stamp()
    document["workflow"] = {
        "mode": "multi_agent",
        "framework": "langgraph",
        "agent_model": settings.agent_model,
        "agent_signal_limit": len(state.get("candidate_signals", [])),
    }
    document["agents"] = {
        "framework": "langgraph",
        "roles": ["scout", "router", "filing_analyst", "bull_analyst", "bear_analyst", "referee"],
        "signals_reviewed": len(state.get("reviewed_signals", [])),
        "run_label": run_label,
    }
    document["agent_timeline"] = state.get("timeline", [])

    if include_explanations:
        reviewed = state.get("reviewed_signals", [])
        attachment_attempted = 0
        attachment_completed = 0
        for signal in reviewed:
            filing = (signal.get("agent_outputs") or {}).get("filing_analyst") or {}
            parsing = filing.get("attachment_parsing") or {}
            attachment_attempted += int(parsing.get("attempted", 0))
            attachment_completed += int(parsing.get("completed", 0))
        document["attachment_parsing"] = {
            "attempted": attachment_attempted,
            "completed": attachment_completed,
            "signal_limit": len(reviewed),
            "attachments_per_signal": state.get("attachments_per_signal", 2),
            "parsed_urls": attachment_completed,
        }
        document["explanations"] = {
            "provider": "openai",
            "model": settings.agent_model,
            "attempted": len(reviewed),
            "completed": sum(1 for signal in reviewed if signal.get("llm_explanation")),
            "generated_at": now_stamp(),
            "mode": "multi_agent_referee",
        }
        save_json(explained_signals_path(run_label, target_root), document)
    elif state.get("include_attachments", True):
        save_json(enriched_signals_path(run_label, target_root), document)
    else:
        save_json(signals_path(run_label, target_root), document)

    return {
        "final_document": document,
        "timeline": [trace_event("publisher", "Published the market edition", run_label=run_label)],
    }


def build_signal_graph():
    builder = StateGraph(SignalAgentState)
    builder.add_node("filing_analyst", filing_analyst_node)
    builder.add_node("bull_analyst", bull_analyst_node)
    builder.add_node("bear_analyst", bear_analyst_node)
    builder.add_node("referee", referee_node)
    builder.add_edge(START, "filing_analyst")
    builder.add_edge("filing_analyst", "bull_analyst")
    builder.add_edge("filing_analyst", "bear_analyst")
    builder.add_edge("bull_analyst", "referee")
    builder.add_edge("bear_analyst", "referee")
    builder.add_edge("referee", END)
    return builder.compile()


def get_signal_graph():
    global _SIGNAL_GRAPH
    if _SIGNAL_GRAPH is None:
        _SIGNAL_GRAPH = build_signal_graph()
    return _SIGNAL_GRAPH


def build_market_graph():
    builder = StateGraph(MarketAgentState)
    builder.add_node("scout", scout_market_universe_node)
    builder.add_node("router", router_node)
    builder.add_node("agent_desk", review_candidates_node)
    builder.add_node("publisher", publish_node)
    builder.add_edge(START, "scout")
    builder.add_edge("scout", "router")
    builder.add_edge("router", "agent_desk")
    builder.add_edge("agent_desk", "publisher")
    builder.add_edge("publisher", END)
    return builder.compile()


def get_market_graph():
    global _MARKET_GRAPH
    if _MARKET_GRAPH is None:
        _MARKET_GRAPH = build_market_graph()
    return _MARKET_GRAPH


def run_multi_agent_pipeline(
    *,
    days_back: int = 1,
    from_date_text: str | None = None,
    to_date_text: str | None = None,
    output_root: Path | None = None,
    include_explanations: bool = True,
    explanation_limit: int | None = None,
    attachment_signal_limit: int = 12,
    attachments_per_signal: int = 2,
    include_attachments: bool = True,
    agent_signal_limit: int | None = None,
) -> dict[str, Any]:
    graph = get_market_graph()
    result = graph.invoke(
        {
            "days_back": days_back,
            "from_date_text": from_date_text,
            "to_date_text": to_date_text,
            "output_root": str(output_root or settings.data_dir),
            "include_explanations": include_explanations,
            "explanation_limit": explanation_limit or settings.explanation_limit,
            "include_attachments": include_attachments,
            "attachment_signal_limit": attachment_signal_limit,
            "attachments_per_signal": attachments_per_signal,
            "agent_signal_limit": agent_signal_limit or settings.agent_signal_limit,
        }
    )

    return {
        "run_label": result["run_label"],
        "collection": result.get("collection"),
        "signals": result.get("scored_document"),
        "enriched_signals": result.get("final_document") if not include_explanations and include_attachments else None,
        "explained_signals": result.get("final_document") if include_explanations else None,
        "final_document": result.get("final_document"),
        "timeline": result.get("timeline", []),
    }
