from __future__ import annotations

import argparse
import re
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any

from app.config import settings
from app.storage import (
    events_path,
    latest_run_label,
    load_json,
    manifest_path,
    save_json,
    signals_path,
)

NOISE_KEYWORDS = [
    "general updates",
    "press release",
    "copy of newspaper publication",
    "trading window",
    "analysts/institutional investor meet",
    "investor meet",
    "conference call updates",
    "con. call updates",
]

ORDER_KEYWORDS = [
    "order",
    "contract",
    "work order",
    "purchase order",
    "agreement",
    "mou",
    "license",
    "award",
]

ACQUISITION_KEYWORDS = [
    "acquisition",
    "acquire",
    "stake",
    "subsidiary",
    "divest",
    "sale of",
    "slump sale",
]

RESULT_KEYWORDS = [
    "financial results",
    "results",
    "board meeting",
    "earnings",
    "outcome of board meeting",
]

NEGATIVE_ANNOUNCEMENT_KEYWORDS = [
    "default",
    "downgrade",
    "fraud",
    "penalty",
    "liquidation",
    "insolvency",
    "nclt",
    "closure",
    "suspension",
    "resignation",
    "fire accident",
]

FUNDRAISING_KEYWORDS = [
    "qip",
    "preferential",
    "rights issue",
    "warrants",
    "fund raising",
    "allotment",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Score normalized market events into signals.")
    parser.add_argument("--run-label", help="Processed run label to score. Defaults to latest.")
    parser.add_argument(
        "--data-root",
        default=str(settings.data_dir),
        help="Data directory that contains raw/ and processed/.",
    )
    return parser.parse_args()


def parse_number(value: Any) -> float:
    if value is None:
        return 0.0
    if isinstance(value, (int, float)):
        return float(value)
    cleaned = re.sub(r"[^0-9.\-]", "", str(value))
    if cleaned in {"", "-", ".", "-."}:
        return 0.0
    try:
        return float(cleaned)
    except ValueError:
        return 0.0


def compact_event(event: dict[str, Any], event_score: int, reason: str, tags: list[str]) -> dict[str, Any]:
    return {
        "event_type": event.get("event_type"),
        "headline": event.get("headline"),
        "event_date": event.get("event_date"),
        "raw_text": event.get("raw_text"),
        "attachment_url": event.get("attachment_url"),
        "source_url": event.get("source_url"),
        "score": event_score,
        "reason": reason,
        "tags": tags,
    }


def classify_insider_trade(event: dict[str, Any]) -> dict[str, Any]:
    details = event.get("details", {})
    transaction_type = str(details.get("transaction_type") or "").lower()
    category = str(details.get("person_category") or "").lower()
    mode = str(details.get("mode") or "").lower()
    value = parse_number(details.get("value"))

    direction = "neutral"
    direction_sign = 0
    if any(token in transaction_type for token in ["buy", "acquisition"]):
        direction = "bullish"
        direction_sign = 1
    elif any(token in transaction_type for token in ["sell", "sale", "disposal"]):
        direction = "bearish"
        direction_sign = -1

    score = 18
    tags = ["insider_trade"]

    if "promoter" in category:
        score += 18
        tags.append("promoter")
    elif any(token in category for token in ["director", "kmp", "designated"]):
        score += 14
        tags.append("leadership")
    elif any(token in category for token in ["connected", "immediate relative"]):
        score += 9
        tags.append("connected_person")
    else:
        score += 5

    if "market purchase" in mode:
        score += 16
        tags.append("market_purchase")
    elif "market sale" in mode:
        score += 14
        tags.append("market_sale")
    elif any(token in mode for token in ["conversion", "allotment", "esop"]):
        score -= 6
        tags.append("non_open_market")

    if value >= 10_000_000:
        score += 18
        tags.append("large_value")
    elif value >= 5_000_000:
        score += 12
    elif value >= 1_000_000:
        score += 6

    if direction_sign == 0:
        return {
            "score": 0,
            "direction": "neutral",
            "reason": "Unclear insider transaction direction",
            "tags": tags,
        }

    final_score = int(score * direction_sign)
    reason = (
        f"{details.get('person_category') or 'Insider'} {details.get('mode') or 'transaction'} "
        f"{details.get('transaction_type') or 'move'}"
    )
    return {
        "score": final_score,
        "direction": direction,
        "reason": reason.strip(),
        "tags": tags,
    }


def classify_announcement(event: dict[str, Any]) -> dict[str, Any]:
    headline = str(event.get("headline") or "")
    raw_text = str(event.get("raw_text") or "")
    blob = f"{headline} {raw_text}".lower()
    tags = ["corporate_announcement"]

    if any(keyword in blob for keyword in NOISE_KEYWORDS):
        return {
            "score": 0,
            "direction": "neutral",
            "reason": "Routine announcement with low signal value",
            "tags": tags + ["noise"],
        }

    if "reply to clarification" in blob or "clarification" in blob:
        return {
            "score": -4,
            "direction": "neutral",
            "reason": "Clarification response rather than a fresh catalyst",
            "tags": tags + ["clarification"],
        }

    negative_hits = [keyword for keyword in NEGATIVE_ANNOUNCEMENT_KEYWORDS if keyword in blob]
    if negative_hits:
        return {
            "score": -28,
            "direction": "bearish",
            "reason": f"Potential negative disclosure: {negative_hits[0]}",
            "tags": tags + ["negative_disclosure", negative_hits[0].replace(" ", "_")],
        }

    order_hits = [keyword for keyword in ORDER_KEYWORDS if keyword in blob]
    if order_hits:
        return {
            "score": 26,
            "direction": "bullish",
            "reason": "Potential revenue catalyst from order/contract update",
            "tags": tags + ["order_contract", order_hits[0].replace(" ", "_")],
        }

    acquisition_hits = [keyword for keyword in ACQUISITION_KEYWORDS if keyword in blob]
    if acquisition_hits:
        return {
            "score": 20,
            "direction": "bullish",
            "reason": "Strategic acquisition or stake-related update",
            "tags": tags + ["strategic_update", acquisition_hits[0].replace(" ", "_")],
        }

    fundraising_hits = [keyword for keyword in FUNDRAISING_KEYWORDS if keyword in blob]
    if fundraising_hits:
        return {
            "score": 8,
            "direction": "neutral",
            "reason": "Fundraising or allotment-related disclosure",
            "tags": tags + ["fundraising", fundraising_hits[0].replace(" ", "_")],
        }

    if any(keyword in blob for keyword in RESULT_KEYWORDS):
        return {
            "score": 11,
            "direction": "neutral",
            "reason": "Result-related filing that may need follow-up analysis",
            "tags": tags + ["results_update"],
        }

    if any(keyword in blob for keyword in ["presentation", "transcript", "analyst", "conference call"]):
        return {
            "score": 5,
            "direction": "neutral",
            "reason": "Management communication that could support later analysis",
            "tags": tags + ["management_commentary"],
        }

    return {
        "score": 0,
        "direction": "neutral",
        "reason": "Announcement did not match a strong rule-based pattern",
        "tags": tags + ["unclassified"],
    }


def score_event(event: dict[str, Any]) -> dict[str, Any]:
    if event.get("event_type") == "insider_trade":
        classified = classify_insider_trade(event)
    elif event.get("event_type") == "corporate_announcement":
        classified = classify_announcement(event)
    else:
        classified = {"score": 0, "direction": "neutral", "reason": "Unsupported event type", "tags": []}

    return {
        "symbol": event.get("symbol") or "UNKNOWN",
        "company": event.get("company") or "Unknown Company",
        "score": int(classified["score"]),
        "direction": classified["direction"],
        "reason": classified["reason"],
        "tags": classified["tags"],
        "event": compact_event(event, int(classified["score"]), classified["reason"], classified["tags"]),
    }


def confidence_from_signal(net_score: int, insider_count: int, positive_count: int, negative_count: int) -> int:
    confidence = 38 + min(36, abs(net_score))
    if insider_count:
        confidence += 8
    if positive_count and negative_count:
        confidence -= 10
    return max(25, min(95, confidence))


def strength_from_score(score: int) -> str:
    if score >= 80:
        return "high"
    if score >= 45:
        return "medium"
    return "low"


def build_signals_document(events: list[dict[str, Any]], run_label: str, manifest: dict[str, Any]) -> dict[str, Any]:
    scored_events = [score_event(event) for event in events]
    kept_events = [item for item in scored_events if item["score"] != 0]

    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for item in kept_events:
        grouped[item["symbol"]].append(item)

    signals = []
    for symbol, items in grouped.items():
        company = Counter(item["company"] for item in items).most_common(1)[0][0]
        positive_count = sum(1 for item in items if item["score"] > 0)
        negative_count = sum(1 for item in items if item["score"] < 0)
        insider_count = sum(1 for item in items if item["event"]["event_type"] == "insider_trade")
        announcement_count = sum(
            1 for item in items if item["event"]["event_type"] == "corporate_announcement"
        )
        market_purchase_count = sum(
            1 for item in items if "market_purchase" in item["tags"] and item["score"] > 0
        )
        non_open_market_count = sum(1 for item in items if "non_open_market" in item["tags"])
        strong_announcement_count = sum(
            1 for item in items if "order_contract" in item["tags"] or "strategic_update" in item["tags"]
        )

        net_score = sum(item["score"] for item in items)
        combo_bonus = 0
        combo_notes: list[str] = []
        if market_purchase_count > 1:
            bonus = min(20, (market_purchase_count - 1) * 5)
            combo_bonus += bonus
            combo_notes.append("Cluster of insider market purchases")
        if insider_count and strong_announcement_count:
            combo_bonus += 10
            combo_notes.append("Insider activity aligned with a corporate catalyst")

        if net_score > 0:
            net_score += combo_bonus
        elif net_score < 0:
            net_score -= combo_bonus

        if insider_count and non_open_market_count == insider_count and market_purchase_count == 0:
            net_score = int(net_score * 0.22)
            combo_notes.append("Mostly non-open-market transfers, so conviction is lower")

        score = abs(net_score)
        if score < 18:
            continue

        direction = "neutral"
        if net_score >= 18:
            direction = "bullish"
        elif net_score <= -18:
            direction = "bearish"

        top_items = sorted(items, key=lambda item: abs(item["score"]), reverse=True)
        reasons = []
        seen_reasons: set[str] = set()
        for item in top_items:
            if item["reason"] not in seen_reasons:
                seen_reasons.add(item["reason"])
                reasons.append(item["reason"])
        for note in combo_notes:
            if note not in seen_reasons:
                reasons.append(note)

        confidence = confidence_from_signal(net_score, insider_count, positive_count, negative_count)
        signal = {
            "symbol": symbol,
            "company": company,
            "net_score": net_score,
            "score": score,
            "direction": direction,
            "strength": strength_from_score(score),
            "confidence": confidence,
            "primary_reason": reasons[0] if reasons else "Rule-based signal",
            "reasons": reasons[:5],
            "event_count": len(items),
            "insider_event_count": insider_count,
            "announcement_event_count": announcement_count,
            "positive_event_count": positive_count,
            "negative_event_count": negative_count,
            "tags": sorted({tag for item in items for tag in item["tags"]}),
            "evidence": [item["event"] for item in top_items[:5]],
        }
        signals.append(signal)

    signals.sort(key=lambda item: (item["direction"] != "bullish", -item["score"], item["symbol"]))
    bullish = [item for item in signals if item["direction"] == "bullish"]
    bearish = [item for item in signals if item["direction"] == "bearish"]

    return {
        "run_label": run_label,
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "manifest": manifest,
        "overview": {
            "total_events": len(events),
            "scored_events": len(kept_events),
            "total_signals": len(signals),
            "bullish_signals": len(bullish),
            "bearish_signals": len(bearish),
            "neutral_signals": len([item for item in signals if item["direction"] == "neutral"]),
        },
        "top_opportunities": bullish[:8],
        "top_risks": bearish[:5],
        "signals": signals,
    }


def score_run(run_label: str, data_root: Path | None = None) -> dict[str, Any]:
    root = data_root or settings.data_dir
    events = load_json(events_path(run_label, root))
    manifest = load_json(manifest_path(run_label, root))
    document = build_signals_document(events, run_label, manifest)
    save_json(signals_path(run_label, root), document)
    return document


def main() -> None:
    args = parse_args()
    data_root = Path(args.data_root)
    run_label = args.run_label or latest_run_label(data_root)
    if not run_label:
        raise SystemExit("No processed runs found to score.")

    document = score_run(run_label, data_root)
    print(f"Run label: {document['run_label']}")
    print(f"Signals generated: {document['overview']['total_signals']}")
    print(f"Bullish signals: {document['overview']['bullish_signals']}")
    print(f"Bearish signals: {document['overview']['bearish_signals']}")
    print(f"Signals file: {signals_path(run_label, data_root)}")


if __name__ == "__main__":
    main()
