from __future__ import annotations

import math
import re
from typing import Any

from pydantic import BaseModel, Field

from app.agents.runtime import call_json_agent
from app.config import settings
from app.storage import latest_run_label

from .db import (
    add_chat_message,
    create_chat_session,
    fetch_candidate_chunks,
    fetch_recent_chunks,
    fetch_recent_messages,
    get_index_status,
    is_run_indexed,
)
from .indexer import embed_texts, index_run, normalize_text
from .schemas import ChatQueryRequest, ChatQueryResponse, ChatSource

CHAT_SYSTEM_PROMPT = """You are Opportunity Radar Chat, a grounded market-data assistant for Indian retail investors.
Use only the retrieved context provided to you.
If the context is insufficient, say that clearly.
Do not invent filings, numbers, or events.
Do not give financial advice or price targets.
Prefer crisp, direct answers with source-backed language.
Return only valid JSON.
"""


class ChatAnswerModel(BaseModel):
    answer: str
    confidence: float = Field(ge=0, le=100)
    cited_source_ids: list[str] = Field(default_factory=list)
    suggested_questions: list[str] = Field(default_factory=list)


def cosine_similarity(left: list[float] | None, right: list[float] | None) -> float:
    if not left or not right or len(left) != len(right):
        return 0.0
    dot = sum(a * b for a, b in zip(left, right))
    left_norm = math.sqrt(sum(a * a for a in left))
    right_norm = math.sqrt(sum(b * b for b in right))
    if left_norm == 0 or right_norm == 0:
        return 0.0
    return dot / (left_norm * right_norm)


def build_context_sources(rows: list[dict[str, Any]], query_embedding: list[float] | None, top_k: int) -> list[ChatSource]:
    if not rows:
        return []

    max_lexical = max(float(item.get("lexical_score") or 0.0) for item in rows) or 1.0
    scored: list[ChatSource] = []
    seen_external_ids: set[str] = set()

    for row in rows:
        external_id = str(row.get("external_id"))
        if external_id in seen_external_ids:
            continue
        seen_external_ids.add(external_id)

        lexical_score = float(row.get("lexical_score") or 0.0) / max_lexical
        semantic_score = cosine_similarity(query_embedding, row.get("embedding"))
        doc_type = str(row.get("doc_type") or "evidence")
        doc_boost = 0.06 if doc_type in {"signal", "chart_signal"} else 0.0
        final_score = (semantic_score * 0.65) + (lexical_score * 0.35) + doc_boost

        scored.append(
            ChatSource(
                source_id="",
                title=str(row.get("title") or row.get("symbol") or "Source"),
                symbol=row.get("symbol"),
                doc_type=doc_type,
                snippet=normalize_text(row.get("content"))[:420],
                source_url=row.get("source_url"),
                attachment_url=row.get("attachment_url"),
                metadata=row.get("metadata") or {},
                score=round(final_score, 4),
            )
        )

    scored.sort(key=lambda item: item.score, reverse=True)
    for index, item in enumerate(scored, start=1):
        item.source_id = f"S{index}"
    return scored[:top_k]


def infer_direction_filter(query: str) -> str | None:
    text = normalize_text(query).lower()
    bearish_terms = ("bearish", "risk", "negative", "downside", "selling", "sell")
    bullish_terms = ("bullish", "positive", "opportunity", "upside", "buying", "buy")
    bearish = any(term in text for term in bearish_terms)
    bullish = any(term in text for term in bullish_terms)
    if bearish and not bullish:
        return "bearish"
    if bullish and not bearish:
        return "bullish"
    return None


def normalize_confidence(value: float | int) -> int:
    numeric = float(value)
    if 0 <= numeric <= 1:
        numeric *= 100
    return max(0, min(100, int(round(numeric))))


def query_has_explicit_symbol(query: str) -> bool:
    text = str(query or "")
    tokens = re.findall(r"\b[A-Z][A-Z0-9&.-]{2,}\b", text)
    blacklist = {"WHY", "WHAT", "ANY", "SHOW", "RUN", "THE", "AND", "FOR", "TODAY"}
    return any(token not in blacklist for token in tokens)


def infer_symbol_from_query(query: str) -> str | None:
    text = str(query or "")
    tokens = re.findall(r"\b[A-Z][A-Z0-9&.-]{2,}\b", text)
    blacklist = {"WHY", "WHAT", "ANY", "SHOW", "RUN", "THE", "AND", "FOR", "TODAY"}
    for token in tokens:
        if token not in blacklist:
            return token
    return None


def build_prompt(
    *,
    query: str,
    run_label: str,
    symbol: str | None,
    watchlist: list[str],
    sources: list[ChatSource],
    history: list[dict[str, Any]],
) -> str:
    history_lines = []
    for item in history[-settings.chat_history_messages :]:
        role = str(item.get("role") or "user").upper()
        history_lines.append(f"{role}: {normalize_text(item.get('content'))}")

    source_lines = []
    for item in sources:
        source_lines.append(
            f"[{item.source_id}] title={item.title} | symbol={item.symbol or '-'} | type={item.doc_type} | snippet={item.snippet}"
        )

    return f"""
Answer the user's question using only the context below.

Run label: {run_label}
Focused symbol: {symbol or 'none'}
Watchlist: {', '.join(watchlist) if watchlist else 'none'}

Recent conversation:
{chr(10).join(history_lines) if history_lines else 'No prior conversation.'}

Retrieved context:
{chr(10).join(source_lines) if source_lines else 'No retrieved context.'}

User question:
{query}

Return JSON only:
{{
  "answer": "short but useful answer in plain English, mention when data is missing",
  "confidence": 0,
  "cited_source_ids": ["S1", "S2"],
  "suggested_questions": ["question 1", "question 2", "question 3"]
}}
""".strip()


def ensure_indexed(run_label: str) -> None:
    if not is_run_indexed(run_label):
        index_run(run_label)


def retrieve_sources(
    *,
    query: str,
    run_label: str,
    symbol: str | None,
    watchlist: list[str],
    top_k: int,
) -> list[ChatSource]:
    direction = infer_direction_filter(query)
    effective_symbol = symbol or infer_symbol_from_query(query)
    stock_specific = bool(effective_symbol) or query_has_explicit_symbol(query)
    embedding_rows = embed_texts([query])
    query_embedding = embedding_rows[0] if embedding_rows else None
    rows = fetch_candidate_chunks(
        query=query,
        run_label=run_label,
        symbol=effective_symbol,
        watchlist=watchlist,
        direction=direction,
        limit=max(36, top_k * 6),
    )
    if not rows and not stock_specific:
        rows = fetch_recent_chunks(
            run_label=run_label,
            symbol=effective_symbol,
            watchlist=watchlist,
            direction=direction,
            limit=max(18, top_k * 3),
        )
    return build_context_sources(rows, query_embedding, top_k)


def chat_status() -> list[dict[str, Any]]:
    return get_index_status()


def index_for_chat(run_label: str | None = None) -> dict[str, Any]:
    return index_run(run_label)


def answer_query(payload: ChatQueryRequest) -> ChatQueryResponse:
    chosen_run = payload.run_label or latest_run_label()
    if not chosen_run:
        raise FileNotFoundError("No processed runs found for chat.")

    symbol = payload.symbol.strip().upper() if payload.symbol else None
    watchlist = [item.strip().upper() for item in payload.watchlist if str(item).strip()]
    ensure_indexed(chosen_run)

    session_id = payload.session_id or create_chat_session(
        run_label=chosen_run,
        symbol=symbol,
        metadata={"watchlist": watchlist},
    )
    history = fetch_recent_messages(session_id, limit=settings.chat_history_messages)
    sources = retrieve_sources(
        query=payload.query,
        run_label=chosen_run,
        symbol=symbol,
        watchlist=watchlist,
        top_k=payload.top_k,
    )

    add_chat_message(
        session_id=session_id,
        role="user",
        content=payload.query,
        metadata={"run_label": chosen_run, "symbol": symbol, "watchlist": watchlist},
    )

    answer = call_json_agent(
        system_prompt=CHAT_SYSTEM_PROMPT,
        prompt=build_prompt(
            query=payload.query,
            run_label=chosen_run,
            symbol=symbol,
            watchlist=watchlist,
            sources=sources,
            history=history,
        ),
        response_model=ChatAnswerModel,
        model=settings.chat_model,
        max_output_tokens=520,
    )

    source_by_id = {item.source_id: item for item in sources}
    cited_sources = [source_by_id[item] for item in answer.get("cited_source_ids", []) if item in source_by_id]
    if not cited_sources:
        cited_sources = sources[: min(3, len(sources))]

    add_chat_message(
        session_id=session_id,
        role="assistant",
        content=answer["answer"],
        citations=[item.model_dump() for item in cited_sources],
        metadata={
            "run_label": chosen_run,
            "symbol": symbol,
            "confidence": normalize_confidence(answer["confidence"]),
            "suggested_questions": answer.get("suggested_questions", []),
        },
    )

    return ChatQueryResponse(
        session_id=session_id,
        run_label=chosen_run,
        answer=answer["answer"],
        confidence=normalize_confidence(answer["confidence"]),
        sources=cited_sources,
        suggested_questions=answer.get("suggested_questions", [])[:3],
        retrieved_chunks=len(sources),
    )
