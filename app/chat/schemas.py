from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class ChatSource(BaseModel):
    source_id: str
    title: str
    symbol: str | None = None
    doc_type: str
    snippet: str
    source_url: str | None = None
    attachment_url: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    score: float = 0.0


class ChatAnswerPayload(BaseModel):
    answer: str
    confidence: int = Field(ge=0, le=100)
    cited_source_ids: list[str] = Field(default_factory=list)
    suggested_questions: list[str] = Field(default_factory=list)


class ChatQueryRequest(BaseModel):
    query: str = Field(min_length=1)
    session_id: str | None = None
    run_label: str | None = None
    symbol: str | None = None
    watchlist: list[str] = Field(default_factory=list)
    top_k: int = Field(default=8, ge=3, le=12)


class ChatQueryResponse(BaseModel):
    session_id: str
    run_label: str
    answer: str
    confidence: int
    sources: list[ChatSource] = Field(default_factory=list)
    suggested_questions: list[str] = Field(default_factory=list)
    retrieved_chunks: int = 0


class ChatIndexRequest(BaseModel):
    run_label: str | None = None
    force: bool = False


class ChatIndexResponse(BaseModel):
    run_label: str
    documents_indexed: int
    chunks_indexed: int
    embedding_model: str
