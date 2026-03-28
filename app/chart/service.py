from __future__ import annotations

import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from app.config import settings
from app.market import load_stock_master
from app.storage import (
    chart_signals_path,
    chart_stock_detail_path,
    chart_summary_for_symbol,
    chart_run_dir,
    latest_chart_run_label,
    load_chart_bundle,
    load_json,
    processed_chart_root,
    save_json,
)

from .backtest import backtest_pattern, build_family_baselines
from .explain import explain_chart_document, heuristic_explanation
from .indicators import enrich_candles, indicator_snapshot
from .levels import build_support_resistance
from .patterns import detect_patterns
from .provider import MarketDataProvider, get_market_data_provider

IST = ZoneInfo("Asia/Kolkata")


def now_ist() -> datetime:
    return datetime.now(IST)


def timestamped_run_label(now: datetime | None = None) -> str:
    stamp = (now or now_ist()).astimezone(IST)
    offset = stamp.strftime("%z")
    offset_slug = f"{offset[:3]}-{offset[3:]}" if len(offset) == 5 else offset
    return stamp.strftime("%Y-%m-%dT%H-%M-%S") + offset_slug


def _copy(payload: Any) -> Any:
    return json.loads(json.dumps(payload))


def load_chart_runs(data_root: Path | None = None) -> list[dict[str, Any]]:
    root = processed_chart_root(data_root)
    if not root.exists():
        return []

    runs = []
    for path in sorted(root.iterdir(), key=lambda item: item.stat().st_mtime, reverse=True):
        if not path.is_dir():
            continue
        signal_path = path / "signals.json"
        signal_count = 0
        if signal_path.exists():
            try:
                signal_count = len(load_json(signal_path).get("signals", []))
            except Exception:  # noqa: BLE001
                signal_count = 0
        runs.append(
            {
                "run_label": path.name,
                "has_signals": signal_path.exists(),
                "signal_count": signal_count,
            }
        )
    return runs


def load_chart_signal_bundle(
    run_label: str | None = None,
    data_root: Path | None = None,
) -> dict[str, Any]:
    return load_chart_bundle(run_label, data_root)


def _top_lists(signals: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    bullish = [item for item in signals if item.get("direction") == "bullish"]
    bearish = [item for item in signals if item.get("direction") == "bearish"]
    return bullish[:10], bearish[:8]


def _family_counts(signals: list[dict[str, Any]]) -> dict[str, int]:
    counts = {"breakout": 0, "reversal": 0, "divergence": 0}
    for item in signals:
        family = str(item.get("pattern_family") or "")
        if family in counts:
            counts[family] += 1
    return counts


def _trim_candles(candles: list[dict[str, Any]], limit: int = 120) -> list[dict[str, Any]]:
    return candles[-limit:]


def _pattern_key(symbol: str, timeframe: str, pattern_label: str) -> str:
    return f"{symbol}:{timeframe}:{pattern_label}"


def _finalize_pattern(
    pattern: dict[str, Any],
    *,
    symbol: str,
    company: str,
    backtest: dict[str, Any],
) -> dict[str, Any]:
    finalized = _copy(pattern)
    finalized["symbol"] = symbol
    finalized["company"] = company
    finalized["primary_reason"] = finalized.get("pattern_label")
    finalized["tags"] = [
        "chart_pattern",
        str(finalized.get("pattern_family") or "pattern"),
        str(finalized.get("timeframe") or "timeframe"),
        str(finalized.get("direction") or "neutral"),
    ]
    finalized["signal_key"] = _pattern_key(symbol, str(finalized.get("timeframe")), str(finalized.get("pattern_label")))
    finalized["backtest"] = backtest
    finalized["llm_explanation"] = heuristic_explanation(finalized)
    return finalized


def analyze_symbol_chart(
    symbol: str,
    *,
    company: str | None = None,
    provider: MarketDataProvider | None = None,
    data_root: Path | None = None,
    force_refresh: bool = False,
) -> dict[str, Any]:
    normalized = str(symbol or "").strip().upper()
    if not normalized:
        raise ValueError("Symbol is required.")

    chart_provider = provider or get_market_data_provider()
    company_name = company or normalized
    detail: dict[str, Any] = {
        "symbol": normalized,
        "company": company_name,
        "summary": None,
        "patterns": [],
        "pattern_backtests": [],
        "candles": {},
        "levels": {},
        "indicators": {},
        "backtest": None,
        "chart_status": {},
    }

    daily_raw = chart_provider.fetch_candles(
        normalized,
        "1d",
        lookback_days=settings.chart_daily_lookback_days,
        data_root=data_root,
        force_refresh=force_refresh,
    )
    if len(daily_raw) < settings.chart_min_history_bars:
        detail["chart_status"] = {
            "eligible": False,
            "reason": "insufficient_history",
            "daily_bars": len(daily_raw),
            "required_daily_bars": settings.chart_min_history_bars,
        }
        return detail

    daily_candles = enrich_candles(daily_raw)
    liquidity = float(daily_candles[-1].get("traded_value_median_20") or 0.0)
    if liquidity < settings.chart_liquidity_floor:
        detail["candles"]["1d"] = _trim_candles(daily_candles)
        detail["indicators"]["1d"] = indicator_snapshot(daily_candles[-1])
        detail["chart_status"] = {
            "eligible": False,
            "reason": "illiquid",
            "daily_bars": len(daily_candles),
            "median_traded_value_20": liquidity,
            "liquidity_floor": settings.chart_liquidity_floor,
        }
        return detail

    intraday_candles: list[dict[str, Any]] = []
    try:
        intraday_raw = chart_provider.fetch_candles(
            normalized,
            settings.chart_intraday_interval,
            lookback_days=settings.chart_intraday_lookback_days,
            data_root=data_root,
            force_refresh=force_refresh,
        )
        intraday_candles = enrich_candles(intraday_raw) if len(intraday_raw) >= 60 else []
    except Exception:  # noqa: BLE001
        intraday_candles = []

    daily_levels = build_support_resistance(daily_candles)
    intraday_levels = build_support_resistance(intraday_candles) if intraday_candles else {"support": [], "resistance": [], "pivots": {"highs": [], "lows": []}}

    current_patterns = detect_patterns(daily_candles, timeframe="1d", levels=daily_levels)
    if intraday_candles:
        current_patterns.extend(
            detect_patterns(
                intraday_candles,
                timeframe=settings.chart_intraday_interval,
                levels=intraday_levels,
            )
        )

    current_patterns.sort(key=lambda item: (-int(item.get("score") or 0), -int(item.get("confidence") or 0)))

    backtests_by_label: dict[str, dict[str, Any]] = {}
    finalized_patterns: list[dict[str, Any]] = []
    for pattern in current_patterns:
        label = str(pattern.get("pattern_label") or "Chart Pattern")
        backtest = backtests_by_label.get(label)
        if backtest is None:
            backtest = backtest_pattern(
                daily_candles,
                label,
                horizon_days=settings.chart_backtest_horizon_days,
                min_sample_size=settings.chart_min_sample_size,
            )
            backtests_by_label[label] = backtest
        finalized_patterns.append(
            _finalize_pattern(
                pattern,
                symbol=normalized,
                company=company_name,
                backtest=backtest,
            )
        )

    detail["candles"]["1d"] = _trim_candles(daily_candles)
    if intraday_candles:
        detail["candles"][settings.chart_intraday_interval] = _trim_candles(intraday_candles)
    detail["levels"]["1d"] = {
        "support": daily_levels.get("support", []),
        "resistance": daily_levels.get("resistance", []),
    }
    if intraday_candles:
        detail["levels"][settings.chart_intraday_interval] = {
            "support": intraday_levels.get("support", []),
            "resistance": intraday_levels.get("resistance", []),
        }
    detail["indicators"]["1d"] = indicator_snapshot(daily_candles[-1])
    if intraday_candles:
        detail["indicators"][settings.chart_intraday_interval] = indicator_snapshot(intraday_candles[-1])
    detail["patterns"] = finalized_patterns
    detail["pattern_backtests"] = list(backtests_by_label.values())
    detail["chart_status"] = {
        "eligible": True,
        "reason": "ok",
        "daily_bars": len(daily_candles),
        "intraday_bars": len(intraday_candles),
        "median_traded_value_20": liquidity,
    }

    shortlisted = [
        item
        for item in finalized_patterns
        if int(item.get("score") or 0) >= settings.chart_score_threshold
    ]
    shortlisted.sort(key=lambda item: (-int(item.get("score") or 0), -int(item.get("confidence") or 0)))
    detail["summary"] = shortlisted[0] if shortlisted else None
    detail["backtest"] = (detail["summary"] or {}).get("backtest")
    return detail


def _apply_family_baselines(
    signals: list[dict[str, Any]],
    details: list[dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    all_backtests = []
    for detail in details:
        all_backtests.extend(detail.get("pattern_backtests", []))

    baselines = build_family_baselines(all_backtests)
    for signal in signals:
        backtest = signal.get("backtest") or {}
        if str(backtest.get("reliability")) == "low_sample":
            family = str(signal.get("pattern_family") or "")
            if family in baselines:
                backtest["fallback_baseline"] = baselines[family]
                signal["backtest"] = backtest
                signal["reasons"] = list(signal.get("reasons", []))[:4] + [
                    f"Stock-specific sample is limited, so the {family} baseline is shown as fallback context."
                ]
    return baselines


def _update_details_from_document(
    document: dict[str, Any],
    details: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    by_key = {
        str(signal.get("signal_key")): signal
        for signal in document.get("signals", [])
        if signal.get("signal_key")
    }
    updated: list[dict[str, Any]] = []
    for detail in details:
        cloned = _copy(detail)
        patterns = []
        for pattern in cloned.get("patterns", []):
            patterns.append(by_key.get(str(pattern.get("signal_key")), pattern))
        cloned["patterns"] = patterns
        summary = cloned.get("summary")
        if summary and summary.get("signal_key") in by_key:
            cloned["summary"] = by_key[str(summary.get("signal_key"))]
            cloned["backtest"] = (cloned["summary"] or {}).get("backtest")
        updated.append(cloned)
    return updated


def run_chart_pipeline(
    *,
    data_root: Path | None = None,
    include_explanations: bool = True,
    explanation_limit: int | None = None,
    symbol_limit: int | None = None,
    force_refresh: bool = False,
) -> dict[str, Any]:
    target_root = data_root or settings.data_dir
    run_label = timestamped_run_label()
    started_at = now_ist().isoformat(timespec="seconds")

    master = load_stock_master(data_root=target_root)
    universe = [
        item
        for item in master.get("symbols", [])
        if str(item.get("series") or "").strip().upper() == "EQ"
    ]
    if symbol_limit:
        universe = universe[: max(1, int(symbol_limit))]

    details: list[dict[str, Any]] = []
    max_workers = max(1, int(settings.chart_scan_workers))
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(
                analyze_symbol_chart,
                item["symbol"],
                company=item.get("company"),
                data_root=target_root,
                force_refresh=force_refresh,
            ): item
            for item in universe
        }
        for future in as_completed(futures):
            item = futures[future]
            try:
                details.append(future.result())
            except Exception as exc:  # noqa: BLE001
                details.append(
                    {
                        "symbol": item.get("symbol"),
                        "company": item.get("company"),
                        "summary": None,
                        "patterns": [],
                        "pattern_backtests": [],
                        "candles": {},
                        "levels": {},
                        "indicators": {},
                        "backtest": None,
                        "chart_status": {
                            "eligible": False,
                            "reason": "error",
                            "error": str(exc),
                        },
                    }
                )

    signals = [detail["summary"] for detail in details if detail.get("summary")]
    signals.sort(key=lambda item: (-int(item.get("score") or 0), -int(item.get("confidence") or 0), str(item.get("symbol") or "")))
    bullish, bearish = _top_lists(signals)
    family_counts = _family_counts(signals)
    baselines = _apply_family_baselines(signals, details)

    document = {
        "run_label": run_label,
        "generated_at": now_ist().isoformat(timespec="seconds"),
        "manifest": {
            "provider": settings.chart_data_provider,
            "intraday_interval": settings.chart_intraday_interval,
            "daily_lookback_days": settings.chart_daily_lookback_days,
            "intraday_lookback_days": settings.chart_intraday_lookback_days,
            "backtest_horizon_days": settings.chart_backtest_horizon_days,
            "scan_started_at": started_at,
            "scan_finished_at": now_ist().isoformat(timespec="seconds"),
            "universe_size": len(universe),
            "symbols_scanned": len(details),
            "signals_published": len(signals),
            "score_threshold": settings.chart_score_threshold,
            "liquidity_floor": settings.chart_liquidity_floor,
            "min_history_bars": settings.chart_min_history_bars,
        },
        "overview": {
            "symbols_scanned": len(details),
            "signals_published": len(signals),
            "bullish_signals": len([item for item in signals if item.get("direction") == "bullish"]),
            "bearish_signals": len([item for item in signals if item.get("direction") == "bearish"]),
            "breakout_signals": family_counts["breakout"],
            "reversal_signals": family_counts["reversal"],
            "divergence_signals": family_counts["divergence"],
        },
        "workflow": {
            "mode": "chart_patterns",
            "provider": settings.chart_data_provider,
            "scan_workers": max_workers,
        },
        "top_opportunities": bullish,
        "top_risks": bearish,
        "signals": signals,
        "baselines": baselines,
    }

    if include_explanations:
        document = explain_chart_document(
            document,
            limit=explanation_limit or settings.chart_explanation_limit,
        )

    detail_dir = chart_run_dir(run_label, target_root)
    save_json(chart_signals_path(run_label, target_root), document)
    explained_details = _update_details_from_document(document, [detail for detail in details if detail.get("summary")])
    for detail in explained_details:
        save_json(chart_stock_detail_path(run_label, detail["symbol"], target_root), detail)

    return document


def _build_on_demand_detail(
    symbol: str,
    *,
    run_label: str | None,
    data_root: Path | None = None,
    force_refresh: bool = False,
) -> dict[str, Any]:
    master = load_stock_master(data_root=data_root)
    master_row = master.get("by_symbol", {}).get(symbol)
    detail = analyze_symbol_chart(
        symbol,
        company=(master_row or {}).get("company"),
        data_root=data_root,
        force_refresh=force_refresh,
    )
    detail["run_label"] = run_label
    return detail


def load_stock_chart(
    symbol: str,
    *,
    run_label: str | None = None,
    data_root: Path | None = None,
    force_refresh: bool = False,
) -> dict[str, Any]:
    normalized = str(symbol or "").strip().upper()
    if not normalized:
        raise ValueError("Symbol is required.")

    chosen_run = run_label or latest_chart_run_label(data_root)
    if chosen_run:
        detail_path = chart_stock_detail_path(chosen_run, normalized, data_root)
        if detail_path.exists():
            detail = load_json(detail_path)
            detail["run_label"] = chosen_run
            return detail

    detail = _build_on_demand_detail(
        normalized,
        run_label=chosen_run,
        data_root=data_root,
        force_refresh=force_refresh,
    )
    detail["chart_summary"] = chart_summary_for_symbol(normalized, chosen_run, data_root)
    return detail
