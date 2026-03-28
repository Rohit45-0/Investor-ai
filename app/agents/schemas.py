from __future__ import annotations

from pydantic import BaseModel, Field


class AgentBaseModel(BaseModel):
    model_config = {"extra": "ignore"}


class FilingBrief(AgentBaseModel):
    catalyst_type: str = "General disclosure"
    evidence_quality: str = "medium"
    what_changed: str = "The filing indicates a potentially material update."
    key_facts: list[str] = Field(default_factory=list)
    bullish_clues: list[str] = Field(default_factory=list)
    bearish_clues: list[str] = Field(default_factory=list)
    watch_items: list[str] = Field(default_factory=list)


class DebateCase(AgentBaseModel):
    stance: str = "neutral"
    confidence: int = 50
    thesis: str = "Mixed evidence."
    summary: str = "The filing presents a mixed signal."
    supporting_points: list[str] = Field(default_factory=list)
    cautions: list[str] = Field(default_factory=list)


class Verdict(AgentBaseModel):
    direction: str = "neutral"
    confidence: int = 50
    signal_label: str = "Market Signal"
    summary: str = "The signal needs investor review."
    why_it_matters: str = "The filing may matter if confirmed by follow-up disclosures."
    risk_note: str = "Treat this as a research trigger, not an instruction."
    key_evidence: list[str] = Field(default_factory=list)
    action: str = "monitor"
