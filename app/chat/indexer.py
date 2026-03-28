from __future__ import annotations

import math
from typing import Any

import requests

from app.chart.service import load_chart_signal_bundle
from app.config import settings
from app.storage import latest_run_label, load_dashboard_bundle

from .db import replace_run_index


def normalize_text(value: Any) -> str:
    return " ".join(str(value or "").replace("\r", " ").replace("\n", " ").split())


def chunk_text(text: str, *, max_chars: int = 900, overlap: int = 120) -> list[str]:
    cleaned = normalize_text(text)
    if not cleaned:
        return []
    if len(cleaned) <= max_chars:
        return [cleaned]

    words = cleaned.split()
    chunks: list[str] = []
    current: list[str] = []
    current_len = 0

    for word in words:
        word_len = len(word) + (1 if current else 0)
        if current and current_len + word_len > max_chars:
            current_text = " ".join(current)
            chunks.append(current_text)
            tail = current_text[-overlap:]
            current = tail.split() if tail else []
            current_len = len(" ".join(current))
        current.append(word)
        current_len += word_len

    if current:
        chunks.append(" ".join(current))
    return chunks


def build_signal_document(signal: dict[str, Any], run_label: str) -> dict[str, Any]:
    explanation = signal.get("llm_explanation") or {}
    reasons = [normalize_text(item) for item in signal.get("reasons", []) if normalize_text(item)]
    evidence_bits = []
    for item in signal.get("evidence", [])[:3]:
        headline = normalize_text(item.get("headline"))
        raw_text = normalize_text(item.get("raw_text"))
        if headline or raw_text:
            evidence_bits.append(f"{headline}. {raw_text}".strip())

    lines = [
        f"Run label: {run_label}",
        f"Stock: {signal.get('company') or signal.get('symbol')} ({signal.get('symbol')})",
        f"Direction: {signal.get('direction')}",
        f"Score: {signal.get('score')}",
        f"Confidence: {explanation.get('confidence') or signal.get('confidence')}",
        f"Primary reason: {signal.get('primary_reason')}",
        f"Summary: {explanation.get('summary') or signal.get('primary_reason')}",
        f"Why it matters: {explanation.get('why_it_matters') or (reasons[0] if reasons else '')}",
        f"Risk note: {explanation.get('risk_note') or ''}",
        f"Reasons: {' | '.join(reasons[:5])}",
        f"Tags: {' | '.join(signal.get('tags', []))}",
        f"Signal event counts: total={signal.get('event_count', 0)}, insider={signal.get('insider_event_count', 0)}, announcements={signal.get('announcement_event_count', 0)}",
    ]
    if evidence_bits:
        lines.append("Key evidence: " + " | ".join(evidence_bits))

    metadata = {
        "run_label": run_label,
        "doc_type": "signal",
        "symbol": signal.get("symbol"),
        "company": signal.get("company"),
        "direction": signal.get("direction"),
        "score": signal.get("score"),
        "tags": signal.get("tags", []),
        "event_count": signal.get("event_count", 0),
        "source_count": len(signal.get("evidence", [])),
    }

    source_url = None
    attachment_url = None
    if signal.get("evidence"):
        source_url = signal["evidence"][0].get("source_url")
        attachment_url = signal["evidence"][0].get("attachment_url")

    content = "\n".join(line for line in lines if normalize_text(line))
    return {
        "external_id": f"signal:{run_label}:{signal.get('symbol')}",
        "run_label": run_label,
        "doc_type": "signal",
        "symbol": signal.get("symbol"),
        "company": signal.get("company"),
        "title": f"{signal.get('symbol')} market signal",
        "content": content,
        "search_text": normalize_text(" ".join([content, signal.get("company") or "", signal.get("symbol") or ""])),
        "metadata": metadata,
        "source_url": source_url,
        "attachment_url": attachment_url,
        "score": int(signal.get("score") or 0),
        "event_date": signal.get("evidence", [{}])[0].get("event_date"),
    }


def build_evidence_document(signal: dict[str, Any], evidence: dict[str, Any], run_label: str, index: int) -> dict[str, Any]:
    parsed = evidence.get("attachment_parse") or {}
    highlights = [normalize_text(item) for item in parsed.get("highlights", []) if normalize_text(item)]
    facts = parsed.get("facts") or {}
    fact_lines = [f"{key}: {value}" for key, value in facts.items() if normalize_text(value)]

    lines = [
        f"Run label: {run_label}",
        f"Stock: {signal.get('company') or signal.get('symbol')} ({signal.get('symbol')})",
        f"Event type: {evidence.get('event_type')}",
        f"Headline: {evidence.get('headline')}",
        f"Event date: {evidence.get('event_date')}",
        f"Rule reason: {evidence.get('reason')}",
        f"Raw disclosure text: {evidence.get('raw_text')}",
        f"Attachment highlights: {' | '.join(highlights)}",
        f"Attachment facts: {' | '.join(fact_lines[:12])}",
    ]

    metadata = {
        "run_label": run_label,
        "doc_type": "evidence",
        "symbol": signal.get("symbol"),
        "company": signal.get("company"),
        "event_type": evidence.get("event_type"),
        "headline": evidence.get("headline"),
        "event_date": evidence.get("event_date"),
        "direction": signal.get("direction"),
        "score": evidence.get("score"),
    }

    content = "\n".join(line for line in lines if normalize_text(line))
    return {
        "external_id": f"evidence:{run_label}:{signal.get('symbol')}:{index}",
        "run_label": run_label,
        "doc_type": "evidence",
        "symbol": signal.get("symbol"),
        "company": signal.get("company"),
        "title": normalize_text(evidence.get("headline") or f"{signal.get('symbol')} evidence {index + 1}"),
        "content": content,
        "search_text": normalize_text(" ".join([content, evidence.get("headline") or "", evidence.get("raw_text") or ""])),
        "metadata": metadata,
        "source_url": evidence.get("source_url"),
        "attachment_url": evidence.get("attachment_url"),
        "score": int(evidence.get("score") or 0),
        "event_date": evidence.get("event_date"),
    }


def build_coverage_document(coverage: dict[str, Any], run_label: str) -> dict[str, Any]:
    event_types = coverage.get("event_types") or []
    lines = [
        f"Run label: {run_label}",
        f"Stock: {coverage.get('company') or coverage.get('symbol')} ({coverage.get('symbol')})",
        "Coverage state: tracked but not shortlisted",
        f"Raw event count: {coverage.get('event_count', 0)}",
        f"Attachment count: {coverage.get('attachment_count', 0)}",
        f"Latest event type: {coverage.get('latest_event_type')}",
        f"Latest headline: {coverage.get('latest_headline')}",
        f"Event types: {' | '.join(event_types)}",
    ]

    content = "\n".join(line for line in lines if normalize_text(line))
    return {
        "external_id": f"coverage:{run_label}:{coverage.get('symbol')}",
        "run_label": run_label,
        "doc_type": "coverage",
        "symbol": coverage.get("symbol"),
        "company": coverage.get("company"),
        "title": f"{coverage.get('symbol')} coverage snapshot",
        "content": content,
        "search_text": normalize_text(" ".join([content, coverage.get("company") or "", coverage.get("symbol") or ""])),
        "metadata": {
            "run_label": run_label,
            "doc_type": "coverage",
            "symbol": coverage.get("symbol"),
            "company": coverage.get("company"),
            "event_count": coverage.get("event_count", 0),
            "event_types": event_types,
        },
        "source_url": None,
        "attachment_url": None,
        "score": int(coverage.get("event_count") or 0),
        "event_date": coverage.get("latest_event_date"),
    }


def build_chart_signal_document(
    signal: dict[str, Any],
    *,
    run_label: str,
    chart_run_label: str,
) -> dict[str, Any]:
    explanation = signal.get("llm_explanation") or {}
    evidence_bits = []
    for item in signal.get("evidence", [])[:4]:
        label = normalize_text(item.get("label"))
        detail = normalize_text(item.get("detail"))
        if label or detail:
            evidence_bits.append(f"{label}: {detail}".strip(": "))

    backtest = signal.get("backtest") or {}
    support_levels = " | ".join(str(item.get("price")) for item in signal.get("support_levels", [])[:3] if item.get("price") is not None)
    resistance_levels = " | ".join(str(item.get("price")) for item in signal.get("resistance_levels", [])[:3] if item.get("price") is not None)
    lines = [
        f"Index run label: {run_label}",
        f"Chart run label: {chart_run_label}",
        f"Stock: {signal.get('company') or signal.get('symbol')} ({signal.get('symbol')})",
        f"Pattern: {signal.get('pattern_label')}",
        f"Pattern family: {signal.get('pattern_family')}",
        f"Timeframe: {signal.get('timeframe')}",
        f"Direction: {signal.get('direction')}",
        f"Score: {signal.get('score')}",
        f"Confidence: {explanation.get('confidence') or signal.get('confidence')}",
        f"Summary: {explanation.get('summary') or signal.get('pattern_label')}",
        f"Why it matters: {explanation.get('why_it_matters') or ''}",
        f"Risk note: {explanation.get('risk_note') or ''}",
        f"Support levels: {support_levels}",
        f"Resistance levels: {resistance_levels}",
        f"Backtest success rate: {backtest.get('success_rate')}",
        f"Backtest sample size: {backtest.get('sample_size')}",
        f"Backtest reliability: {backtest.get('reliability')}",
        f"Evidence: {' | '.join(evidence_bits)}",
    ]

    content = "\n".join(line for line in lines if normalize_text(line))
    return {
        "external_id": f"chart_signal:{chart_run_label}:{signal.get('symbol')}:{signal.get('timeframe')}:{signal.get('pattern_label')}",
        "run_label": run_label,
        "doc_type": "chart_signal",
        "symbol": signal.get("symbol"),
        "company": signal.get("company"),
        "title": f"{signal.get('symbol')} {signal.get('pattern_label')} chart signal",
        "content": content,
        "search_text": normalize_text(" ".join([content, signal.get("company") or "", signal.get("symbol") or ""])),
        "metadata": {
            "run_label": run_label,
            "chart_run_label": chart_run_label,
            "doc_type": "chart_signal",
            "symbol": signal.get("symbol"),
            "company": signal.get("company"),
            "direction": signal.get("direction"),
            "pattern_family": signal.get("pattern_family"),
            "pattern_label": signal.get("pattern_label"),
            "timeframe": signal.get("timeframe"),
            "score": signal.get("score"),
        },
        "source_url": None,
        "attachment_url": None,
        "score": int(signal.get("score") or 0),
        "event_date": signal.get("as_of"),
    }


def build_documents(bundle: dict[str, Any], chart_bundle: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    run_label = bundle["run_label"]
    documents: list[dict[str, Any]] = []
    signal_symbols = set()

    for signal in bundle.get("signals", []):
        symbol = signal.get("symbol")
        if not symbol:
            continue
        signal_symbols.add(symbol)
        documents.append(build_signal_document(signal, run_label))
        for index, evidence in enumerate(signal.get("evidence", [])):
            documents.append(build_evidence_document(signal, evidence, run_label, index))

    for coverage in bundle.get("coverage", {}).get("symbols", []):
        if coverage.get("symbol") in signal_symbols:
            continue
        documents.append(build_coverage_document(coverage, run_label))

    if chart_bundle:
        chart_run_label = str(chart_bundle.get("run_label") or "")
        for signal in chart_bundle.get("signals", []):
            documents.append(
                build_chart_signal_document(
                    signal,
                    run_label=run_label,
                    chart_run_label=chart_run_label,
                )
            )

    return documents


def estimate_tokens(text: str) -> int:
    return max(1, math.ceil(len(text) / 4))


def embed_texts(texts: list[str]) -> list[list[float] | None]:
    if not texts:
        return []
    if not settings.openai_api_key:
        return [None for _ in texts]

    vectors: list[list[float] | None] = []
    batch_size = 64
    for start in range(0, len(texts), batch_size):
        batch = texts[start : start + batch_size]
        response = requests.post(
            f"{settings.openai_base_url.rstrip('/')}/embeddings",
            headers={
                "Authorization": f"Bearer {settings.openai_api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": settings.embedding_model,
                "input": batch,
                "encoding_format": "float",
            },
            timeout=120,
        )
        response.raise_for_status()
        payload = response.json()
        for item in sorted(payload.get("data", []), key=lambda row: row.get("index", 0)):
            vectors.append(item.get("embedding"))
    return vectors


def build_chunks(documents: list[dict[str, Any]]) -> list[dict[str, Any]]:
    chunks: list[dict[str, Any]] = []
    payloads: list[str] = []

    for document in documents:
        text_chunks = chunk_text(document["content"])
        for index, chunk in enumerate(text_chunks):
            chunks.append(
                {
                    "document_external_id": document["external_id"],
                    "external_id": f"{document['external_id']}:chunk:{index}",
                    "doc_type": document["doc_type"],
                    "symbol": document.get("symbol"),
                    "company": document.get("company"),
                    "chunk_index": index,
                    "content": chunk,
                    "token_estimate": estimate_tokens(chunk),
                    "metadata": document.get("metadata") or {},
                    "source_url": document.get("source_url"),
                    "attachment_url": document.get("attachment_url"),
                    "lexical_text": normalize_text(f"{document['title']} {chunk}"),
                    "embedding": None,
                    "embedding_model": settings.embedding_model,
                }
            )
            payloads.append(chunk)

    embeddings = embed_texts(payloads)
    for chunk, embedding in zip(chunks, embeddings):
        chunk["embedding"] = embedding
    return chunks


def index_run(run_label: str | None = None) -> dict[str, Any]:
    chosen_run = run_label or latest_run_label()
    if not chosen_run:
        raise FileNotFoundError("No processed runs found to index for chat.")

    bundle = load_dashboard_bundle(chosen_run)
    try:
        chart_bundle = load_chart_signal_bundle()
    except FileNotFoundError:
        chart_bundle = None
    documents = build_documents(bundle, chart_bundle)
    chunks = build_chunks(documents)
    replace_run_index(
        run_label=chosen_run,
        manifest=bundle.get("manifest", {}),
        overview=bundle.get("overview", {}),
        workflow=bundle.get("workflow", {}),
        documents=documents,
        chunks=chunks,
    )
    return {
        "run_label": chosen_run,
        "documents_indexed": len(documents),
        "chunks_indexed": len(chunks),
        "embedding_model": settings.embedding_model,
    }
