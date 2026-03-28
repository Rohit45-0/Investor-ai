from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any

import requests

from app.config import settings
from app.storage import ensure_dir, save_json

BASE_URL = "https://www.nseindia.com"
DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/122.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": f"{BASE_URL}/",
}


@dataclass(frozen=True)
class DateRange:
    from_date: date
    to_date: date

    @property
    def nse_from(self) -> str:
        return self.from_date.strftime("%d-%m-%Y")

    @property
    def nse_to(self) -> str:
        return self.to_date.strftime("%d-%m-%Y")

    @property
    def iso_from(self) -> str:
        return self.from_date.isoformat()

    @property
    def iso_to(self) -> str:
        return self.to_date.isoformat()

    @property
    def label(self) -> str:
        if self.from_date == self.to_date:
            return self.iso_to
        return f"{self.iso_from}_to_{self.iso_to}"


class NSECollector:
    def __init__(self) -> None:
        self.session = requests.Session()
        self.session.headers.update(DEFAULT_HEADERS)
        self._warmup()

    def _warmup(self) -> None:
        try:
            self.session.get(BASE_URL, timeout=20)
        except requests.RequestException:
            pass

    def _get_json(self, path: str, params: dict[str, Any]) -> tuple[str, Any]:
        response = self.session.get(f"{BASE_URL}{path}", params=params, timeout=30)
        response.raise_for_status()
        return response.url, response.json()

    def fetch_announcements(self, date_range: DateRange) -> dict[str, Any]:
        url, payload = self._get_json(
            "/api/corporate-announcements",
            {
                "index": "equities",
                "from_date": date_range.nse_from,
                "to_date": date_range.nse_to,
            },
        )
        return self._wrap_payload("nse_corporate_announcements", url, payload)

    def fetch_insider_trades(self, date_range: DateRange) -> dict[str, Any]:
        url, payload = self._get_json(
            "/api/corporates-pit",
            {
                "index": "equities",
                "from_date": date_range.nse_from,
                "to_date": date_range.nse_to,
            },
        )
        return self._wrap_payload("nse_insider_trading", url, payload)

    def fetch_bulk_deals(self, date_range: DateRange) -> dict[str, Any]:
        url, payload = self._get_json(
            "/api/historicalOR/bulk-block-short-deals",
            {
                "optionType": "bulk_deals",
                "from": date_range.nse_from,
                "to": date_range.nse_to,
            },
        )
        return self._wrap_payload("nse_bulk_deals", url, payload)

    @staticmethod
    def _wrap_payload(source: str, url: str, payload: Any) -> dict[str, Any]:
        return {
            "source": source,
            "url": url,
            "fetched_at": datetime.now().isoformat(timespec="seconds"),
            "payload": payload,
        }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Collect NSE announcements, insider trades, and bulk deals."
    )
    parser.add_argument("--days-back", type=int, default=1)
    parser.add_argument("--from-date")
    parser.add_argument("--to-date")
    parser.add_argument(
        "--output-root",
        default=str(settings.data_dir),
        help="Root directory for raw and processed outputs.",
    )
    return parser.parse_args()


def resolve_date_range(
    *,
    days_back: int = 1,
    from_date_text: str | None = None,
    to_date_text: str | None = None,
) -> DateRange:
    if from_date_text or to_date_text:
        if not (from_date_text and to_date_text):
            raise ValueError("Both from_date_text and to_date_text are required together.")
        from_dt = date.fromisoformat(from_date_text)
        to_dt = date.fromisoformat(to_date_text)
    else:
        to_dt = date.today()
        from_dt = to_dt - timedelta(days=max(days_back - 1, 0))

    if from_dt > to_dt:
        raise ValueError("from_date_text must be on or before to_date_text.")

    return DateRange(from_date=from_dt, to_date=to_dt)


def announcement_rows(raw: dict[str, Any]) -> list[dict[str, Any]]:
    payload = raw["payload"]
    return payload if isinstance(payload, list) else []


def insider_rows(raw: dict[str, Any]) -> list[dict[str, Any]]:
    payload = raw["payload"]
    if isinstance(payload, dict):
        return payload.get("data", [])
    return []


def bulk_rows(raw: dict[str, Any]) -> list[dict[str, Any]]:
    payload = raw["payload"]
    if isinstance(payload, dict):
        return payload.get("data", [])
    return []


def normalize_announcements(raw: dict[str, Any]) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    for row in announcement_rows(raw):
        headline = row.get("desc") or "Corporate announcement"
        summary = row.get("attchmntText") or headline
        events.append(
            {
                "source": raw["source"],
                "company": row.get("sm_name"),
                "symbol": row.get("symbol"),
                "event_type": "corporate_announcement",
                "headline": headline,
                "event_date": row.get("sort_date") or row.get("an_dt"),
                "attachment_url": row.get("attchmntFile"),
                "raw_text": summary,
                "source_url": raw["url"],
                "details": {
                    "record_id": row.get("seq_id"),
                    "industry": row.get("smIndustry"),
                    "broadcast_at": row.get("an_dt"),
                    "has_xbrl": row.get("hasXbrl"),
                },
            }
        )
    return events


def normalize_insider_trades(raw: dict[str, Any]) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    for row in insider_rows(raw):
        quantity = row.get("secAcq") or row.get("buyQuantity") or row.get("sellquantity")
        transaction_type = row.get("tdpTransactionType") or "Transaction"
        person = row.get("acqName") or "Unknown party"
        sec_type = row.get("secType") or "security"
        headline = f"{person} {transaction_type.lower()} {quantity} {sec_type}".strip()
        raw_text_parts = [
            f"Category: {row.get('personCategory') or '-'}",
            f"Mode: {row.get('acqMode') or '-'}",
            f"Period: {row.get('acqfromDt') or '-'} to {row.get('acqtoDt') or '-'}",
            f"Value: {row.get('secVal') or '-'}",
            f"Remarks: {row.get('remarks') or '-'}",
        ]
        events.append(
            {
                "source": raw["source"],
                "company": row.get("company"),
                "symbol": row.get("symbol"),
                "event_type": "insider_trade",
                "headline": headline,
                "event_date": row.get("date") or row.get("intimDt"),
                "attachment_url": row.get("xbrl"),
                "raw_text": " | ".join(raw_text_parts),
                "source_url": raw["url"],
                "details": {
                    "person": person,
                    "person_category": row.get("personCategory"),
                    "transaction_type": transaction_type,
                    "quantity": quantity,
                    "value": row.get("secVal"),
                    "mode": row.get("acqMode"),
                },
            }
        )
    return events


def normalize_bulk_deals(raw: dict[str, Any]) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    for row in bulk_rows(raw):
        quantity = row.get("BD_QTY_TRD")
        price = row.get("BD_TP_WATP")
        remarks = row.get("BD_REMARKS")
        headline = (
            f"{row.get('BD_CLIENT_NAME')} {str(row.get('BD_BUY_SELL', '')).lower()} "
            f"{quantity} shares at {price}"
        ).strip()
        raw_text = f"Remarks: {remarks}" if remarks else "Remarks: -"
        events.append(
            {
                "source": raw["source"],
                "company": row.get("BD_SCRIP_NAME"),
                "symbol": row.get("BD_SYMBOL"),
                "event_type": "bulk_deal",
                "headline": headline,
                "event_date": row.get("BD_DT_DATE"),
                "attachment_url": None,
                "raw_text": raw_text,
                "source_url": raw["url"],
                "details": {
                    "client_name": row.get("BD_CLIENT_NAME"),
                    "side": row.get("BD_BUY_SELL"),
                    "quantity": quantity,
                    "price": price,
                    "remarks": remarks,
                },
            }
        )
    return events


def write_outputs(
    output_root: Path,
    date_range: DateRange,
    announcements: dict[str, Any],
    insider: dict[str, Any],
    bulk: dict[str, Any],
) -> dict[str, Any]:
    raw_dir = output_root / "raw" / date_range.label
    processed_dir = output_root / "processed" / date_range.label
    ensure_dir(raw_dir)
    ensure_dir(processed_dir)

    save_json(raw_dir / "corporate_announcements.json", announcements)
    save_json(raw_dir / "insider_trades.json", insider)
    save_json(raw_dir / "bulk_deals.json", bulk)

    events = []
    events.extend(normalize_announcements(announcements))
    events.extend(normalize_insider_trades(insider))
    events.extend(normalize_bulk_deals(bulk))
    events.sort(
        key=lambda event: (event.get("event_date") or "", event.get("source") or ""),
        reverse=True,
    )

    manifest = {
        "run_label": date_range.label,
        "from_date": date_range.iso_from,
        "to_date": date_range.iso_to,
        "source_counts": {
            "nse_corporate_announcements": len(announcement_rows(announcements)),
            "nse_insider_trading": len(insider_rows(insider)),
            "nse_bulk_deals": len(bulk_rows(bulk)),
        },
        "normalized_event_count": len(events),
    }

    events_path = processed_dir / "events.json"
    manifest_path = processed_dir / "manifest.json"
    save_json(events_path, events)
    save_json(manifest_path, manifest)

    return {
        "run_label": date_range.label,
        "events_path": events_path,
        "manifest_path": manifest_path,
        "raw_dir": raw_dir,
        "processed_dir": processed_dir,
        "manifest": manifest,
    }


def collect_and_write(
    *,
    date_range: DateRange,
    output_root: Path | None = None,
) -> dict[str, Any]:
    target_root = output_root or settings.data_dir
    collector = NSECollector()
    announcements = collector.fetch_announcements(date_range)
    insider = collector.fetch_insider_trades(date_range)
    bulk = collector.fetch_bulk_deals(date_range)
    return write_outputs(target_root, date_range, announcements, insider, bulk)


def main() -> None:
    args = parse_args()
    date_range = resolve_date_range(
        days_back=args.days_back,
        from_date_text=args.from_date,
        to_date_text=args.to_date,
    )
    result = collect_and_write(date_range=date_range, output_root=Path(args.output_root))
    manifest = result["manifest"]
    print(f"Run label: {manifest['run_label']}")
    print(
        "Source counts: "
        f"announcements={manifest['source_counts']['nse_corporate_announcements']}, "
        f"insider={manifest['source_counts']['nse_insider_trading']}, "
        f"bulk={manifest['source_counts']['nse_bulk_deals']}"
    )
    print(f"Normalized events: {manifest['normalized_event_count']}")
    print(f"Events file: {result['events_path']}")
    print(f"Manifest file: {result['manifest_path']}")


if __name__ == "__main__":
    main()
