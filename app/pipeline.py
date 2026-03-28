from __future__ import annotations

from pathlib import Path
from typing import Any

from app.agents.graph import run_multi_agent_pipeline
from app.attachments import enrich_run
from app.collect import collect_and_write, resolve_date_range
from app.config import settings
from app.explain import explain_run
from app.scoring import score_run


def run_classic_pipeline(
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
    force_attachments: bool = False,
    force_explanations: bool = False,
) -> dict[str, Any]:
    target_root = output_root or settings.data_dir
    date_range = resolve_date_range(
        days_back=days_back,
        from_date_text=from_date_text,
        to_date_text=to_date_text,
    )
    collection = collect_and_write(date_range=date_range, output_root=target_root)
    scored = score_run(collection["run_label"], target_root)
    if include_attachments:
        enriched = enrich_run(
            collection["run_label"],
            data_root=target_root,
            limit_signals=attachment_signal_limit,
            attachments_per_signal=attachments_per_signal,
            force=force_attachments,
        )
    else:
        enriched = None

    if include_explanations:
        explained = explain_run(
            collection["run_label"],
            data_root=target_root,
            limit=explanation_limit or settings.explanation_limit,
            force=force_explanations,
        )
    else:
        explained = None

    return {
        "run_label": collection["run_label"],
        "collection": collection,
        "signals": scored,
        "enriched_signals": enriched,
        "explained_signals": explained,
    }


def run_pipeline(
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
    force_attachments: bool = False,
    force_explanations: bool = False,
    orchestration_mode: str | None = None,
    agent_signal_limit: int | None = None,
) -> dict[str, Any]:
    mode = (orchestration_mode or settings.orchestration_mode).strip().lower()
    if mode == "classic":
        return run_classic_pipeline(
            days_back=days_back,
            from_date_text=from_date_text,
            to_date_text=to_date_text,
            output_root=output_root,
            include_explanations=include_explanations,
            explanation_limit=explanation_limit,
            attachment_signal_limit=attachment_signal_limit,
            attachments_per_signal=attachments_per_signal,
            include_attachments=include_attachments,
            force_attachments=force_attachments,
            force_explanations=force_explanations,
        )

    return run_multi_agent_pipeline(
        days_back=days_back,
        from_date_text=from_date_text,
        to_date_text=to_date_text,
        output_root=output_root,
        include_explanations=include_explanations,
        explanation_limit=explanation_limit,
        attachment_signal_limit=attachment_signal_limit,
        attachments_per_signal=attachments_per_signal,
        include_attachments=include_attachments,
        agent_signal_limit=agent_signal_limit,
    )
