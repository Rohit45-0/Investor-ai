from __future__ import annotations

import argparse
import json
import io
import re
import xml.etree.ElementTree as ET
import zipfile
from collections import OrderedDict
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import fitz
import requests

from app.collect import DEFAULT_HEADERS
from app.config import settings
from app.storage import (
    enriched_signals_path,
    explained_signals_path,
    latest_run_label,
    load_json,
    save_json,
    signals_path,
)

PDF_KEYWORDS = [
    "order",
    "contract",
    "agreement",
    "acquisition",
    "allotment",
    "debenture",
    "ncd",
    "board",
    "results",
    "resignation",
    "closure",
    "issue",
    "private placement",
    "investor",
    "promoter",
]

XML_PRIORITY_KEYS = [
    "NameOfTheCompany",
    "NameOfThePerson",
    "CategoryOfPerson",
    "SecuritiesAcquiredOrDisposedTransactionType",
    "ModeOfAcquisitionOrDisposal",
    "TypeOfInstrument",
    "SecuritiesAcquiredOrDisposedNumberOfSecurity",
    "SecuritiesAcquiredOrDisposedValueOfSecurity",
    "SecuritiesHeldPostAcquistionOrDisposalNumberOfSecurity",
    "SecuritiesHeldPostAcquistionOrDisposalPercentageOfShareholding",
    "DateOfIntimationToCompany",
    "ExchangeOnWhichTheTradeWasExecuted",
]

SKIP_XML_TAGS = {
    "identifier",
    "instant",
    "measure",
    "ChangeInHoldingOfSecuritiesDomain",
    "schemaRef",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Parse top signal attachments and extract evidence.")
    parser.add_argument("--run-label", help="Processed run label to enrich. Defaults to latest.")
    parser.add_argument(
        "--data-root",
        default=str(settings.data_dir),
        help="Data directory that contains raw/ and processed/.",
    )
    parser.add_argument("--limit-signals", type=int, default=12)
    parser.add_argument("--attachments-per-signal", type=int, default=2)
    parser.add_argument("--force", action="store_true")
    return parser.parse_args()


def collapse_whitespace(text: str) -> str:
    return re.sub(r"\s+", " ", text or "").strip()


def file_name_from_url(url: str) -> str:
    return Path(urlparse(url).path).name or "attachment"


def extension_from_name(name: str) -> str:
    suffix = Path(name).suffix.lower()
    return suffix.lstrip(".")


def format_inr_like(value: str | None) -> str | None:
    if not value:
        return None
    cleaned = re.sub(r"[^0-9.\-]", "", value)
    if not cleaned:
        return value
    if "." in cleaned:
        number = float(cleaned)
        if number.is_integer():
            return f"INR {int(number):,}"
        return f"INR {number:,.2f}"
    return f"INR {int(cleaned):,}"


class AttachmentClient:
    def __init__(self) -> None:
        self.session = requests.Session()
        self.session.headers.update(
            {
                **DEFAULT_HEADERS,
                "Accept": "*/*",
                "Accept-Encoding": "identity",
            }
        )

    def download(self, url: str) -> bytes:
        response = self.session.get(url, timeout=(20, 120), stream=True)
        response.raise_for_status()
        return b"".join(chunk for chunk in response.iter_content(65536) if chunk)


def local_name(tag: str) -> str:
    return tag.split("}", 1)[-1]


def top_text_lines(text: str, *, limit: int = 4) -> list[str]:
    candidates = []
    seen: set[str] = set()
    for raw in re.split(r"[\r\n]+", text):
        line = collapse_whitespace(raw)
        if len(line) < 30 or len(line) > 260:
            continue
        if line.lower() in seen:
            continue
        seen.add(line.lower())
        score = 0
        lowered = line.lower()
        for keyword in PDF_KEYWORDS:
            if keyword in lowered:
                score += 4
        if any(char.isdigit() for char in line):
            score += 1
        if ":" in line:
            score += 1
        candidates.append((score, len(line), line))

    candidates.sort(key=lambda item: (-item[0], item[1]))
    lines = [line for _, _, line in candidates[:limit]]
    if not lines:
        lines = [collapse_whitespace(text)[:220]] if collapse_whitespace(text) else []
    return lines


def parse_pdf_bytes(content: bytes, file_name: str) -> dict[str, Any]:
    doc = fitz.open(stream=content, filetype="pdf")
    page_count = doc.page_count
    text_parts = [doc.load_page(i).get_text("text") for i in range(min(page_count, 4))]
    text = collapse_whitespace("\n".join(text_parts))
    return {
        "attachment_type": "pdf",
        "file_name": file_name,
        "page_count": page_count,
        "byte_size": len(content),
        "excerpt": text[:900],
        "highlights": top_text_lines(text),
        "facts": {},
    }


def ordered_facts_from_xml(content: bytes) -> OrderedDict[str, str]:
    root = ET.fromstring(content)
    fact_map: OrderedDict[str, str] = OrderedDict()
    for elem in root.iter():
        if len(elem):
            continue
        value = collapse_whitespace(elem.text or "")
        if not value:
            continue
        tag = local_name(elem.tag)
        if tag in SKIP_XML_TAGS or tag in fact_map:
            continue
        fact_map[tag] = value
    ordered = OrderedDict()
    for key in XML_PRIORITY_KEYS:
        if key in fact_map:
            ordered[key] = fact_map[key]
    for key, value in fact_map.items():
        if key not in ordered and len(ordered) < 16:
            ordered[key] = value
    return ordered


def xml_highlights(facts: OrderedDict[str, str]) -> list[str]:
    person = facts.get("NameOfThePerson")
    category = facts.get("CategoryOfPerson")
    transaction = facts.get("SecuritiesAcquiredOrDisposedTransactionType")
    quantity = facts.get("SecuritiesAcquiredOrDisposedNumberOfSecurity")
    instrument = facts.get("TypeOfInstrument")
    mode = facts.get("ModeOfAcquisitionOrDisposal")
    value = format_inr_like(facts.get("SecuritiesAcquiredOrDisposedValueOfSecurity"))
    post_no = facts.get("SecuritiesHeldPostAcquistionOrDisposalNumberOfSecurity")
    post_pct = facts.get("SecuritiesHeldPostAcquistionOrDisposalPercentageOfShareholding")
    exchange = facts.get("ExchangeOnWhichTheTradeWasExecuted")

    lines = []
    if person and transaction and quantity:
        fragment = f"{person} {transaction.lower()} {quantity} {instrument or 'securities'}"
        if category:
            fragment += f" as {category}"
        lines.append(fragment)
    if mode or value:
        detail = " | ".join(part for part in [f"Mode: {mode}" if mode else None, value] if part)
        if detail:
            lines.append(detail)
    if post_no or post_pct:
        lines.append(
            "Post-holding: "
            + " ".join(part for part in [post_no and f"{post_no} shares", post_pct and f"({post_pct}%)"] if part)
        )
    if exchange:
        lines.append(f"Executed on: {exchange}")
    return lines[:4]


def parse_xml_bytes(content: bytes, file_name: str) -> dict[str, Any]:
    facts = ordered_facts_from_xml(content)
    excerpt = "; ".join(f"{key}: {value}" for key, value in list(facts.items())[:8])
    return {
        "attachment_type": "xml",
        "file_name": file_name,
        "byte_size": len(content),
        "excerpt": excerpt[:900],
        "highlights": xml_highlights(facts),
        "facts": dict(facts),
    }


def parse_text_bytes(content: bytes, file_name: str) -> dict[str, Any]:
    text = collapse_whitespace(content.decode("utf-8", "ignore"))
    return {
        "attachment_type": "text",
        "file_name": file_name,
        "byte_size": len(content),
        "excerpt": text[:900],
        "highlights": top_text_lines(text),
        "facts": {},
    }


def parse_zip_bytes(content: bytes, file_name: str) -> dict[str, Any]:
    zf = zipfile.ZipFile(io.BytesIO(content))
    children = []
    combined_highlights = []
    combined_facts: OrderedDict[str, str] = OrderedDict()
    for child_name in zf.namelist()[:4]:
        ext = extension_from_name(child_name)
        child_bytes = zf.read(child_name)
        if ext == "pdf":
            parsed = parse_pdf_bytes(child_bytes, child_name)
        elif ext == "xml":
            parsed = parse_xml_bytes(child_bytes, child_name)
        elif ext in {"txt", "html", "htm"}:
            parsed = parse_text_bytes(child_bytes, child_name)
        else:
            continue
        children.append(
            {
                "file_name": parsed["file_name"],
                "attachment_type": parsed["attachment_type"],
                "highlights": parsed["highlights"][:3],
                "excerpt": parsed["excerpt"][:300],
            }
        )
        for line in parsed["highlights"]:
            if line not in combined_highlights:
                combined_highlights.append(line)
        for key, value in parsed.get("facts", {}).items():
            if key not in combined_facts and len(combined_facts) < 16:
                combined_facts[key] = value

    return {
        "attachment_type": "zip",
        "file_name": file_name,
        "byte_size": len(content),
        "excerpt": "; ".join(child["file_name"] for child in children)[:900],
        "highlights": combined_highlights[:5],
        "facts": dict(combined_facts),
        "child_documents": children,
    }


def parse_attachment_bytes(content: bytes, file_name: str) -> dict[str, Any]:
    ext = extension_from_name(file_name)
    if ext == "pdf":
        return parse_pdf_bytes(content, file_name)
    if ext == "xml":
        return parse_xml_bytes(content, file_name)
    if ext == "zip":
        return parse_zip_bytes(content, file_name)
    if ext in {"txt", "html", "htm"}:
        return parse_text_bytes(content, file_name)
    return {
        "attachment_type": ext or "unknown",
        "file_name": file_name,
        "byte_size": len(content),
        "excerpt": "",
        "highlights": [],
        "facts": {},
    }


def parse_attachment_url(url: str, client: AttachmentClient) -> dict[str, Any]:
    file_name = file_name_from_url(url)
    content = client.download(url)
    parsed = parse_attachment_bytes(content, file_name)
    parsed["url"] = url
    return parsed


def refresh_top_lists(document: dict[str, Any]) -> None:
    signals = document.get("signals", [])
    document["top_opportunities"] = [item for item in signals if item.get("direction") == "bullish"][:8]
    document["top_risks"] = [item for item in signals if item.get("direction") == "bearish"][:5]


def enrich_signal(
    signal: dict[str, Any],
    *,
    attachments_per_signal: int = 2,
    client: AttachmentClient | None = None,
    cache: dict[str, dict[str, Any]] | None = None,
) -> tuple[dict[str, Any], dict[str, int]]:
    enriched_signal = json.loads(json.dumps(signal))
    active_client = client or AttachmentClient()
    active_cache = cache if cache is not None else {}
    attempted = 0
    completed = 0
    signal_highlights: list[str] = []

    for evidence in enriched_signal.get("evidence", [])[:attachments_per_signal]:
        url = evidence.get("attachment_url")
        if not url:
            continue
        attempted += 1
        if url not in active_cache:
            try:
                active_cache[url] = parse_attachment_url(url, active_client)
            except Exception as exc:  # noqa: BLE001
                active_cache[url] = {"url": url, "error": str(exc), "highlights": [], "facts": {}}
        parsed = active_cache[url]
        if "error" not in parsed:
            completed += 1
        evidence["attachment_parse"] = parsed
        for line in parsed.get("highlights", []):
            if line not in signal_highlights:
                signal_highlights.append(line)

    if signal_highlights:
        enriched_signal["attachment_highlights"] = signal_highlights[:5]

    return enriched_signal, {
        "attempted": attempted,
        "completed": completed,
        "parsed_urls": len(active_cache),
    }


def enrich_document(
    document: dict[str, Any],
    *,
    limit_signals: int = 12,
    attachments_per_signal: int = 2,
) -> dict[str, Any]:
    enriched = json.loads(json.dumps(document))
    client = AttachmentClient()
    cache: dict[str, dict[str, Any]] = {}
    attempted = 0
    completed = 0

    for index, signal in enumerate(enriched.get("signals", [])[:limit_signals]):
        enriched_signal, summary = enrich_signal(
            signal,
            attachments_per_signal=attachments_per_signal,
            client=client,
            cache=cache,
        )
        enriched["signals"][index] = enriched_signal
        attempted += summary["attempted"]
        completed += summary["completed"]

    refresh_top_lists(enriched)
    enriched["attachment_parsing"] = {
        "attempted": attempted,
        "completed": completed,
        "signal_limit": limit_signals,
        "attachments_per_signal": attachments_per_signal,
        "parsed_urls": len(cache),
    }
    return enriched


def source_path_for_enrichment(run_label: str, data_root: Path, force: bool) -> Path:
    scored = signals_path(run_label, data_root)
    enriched = enriched_signals_path(run_label, data_root)
    if force or not enriched.exists():
        return scored
    if scored.exists() and scored.stat().st_mtime > enriched.stat().st_mtime:
        return scored
    return enriched


def enrich_run(
    run_label: str,
    *,
    data_root: Path | None = None,
    limit_signals: int = 12,
    attachments_per_signal: int = 2,
    force: bool = False,
) -> dict[str, Any]:
    root = data_root or settings.data_dir
    source_path = source_path_for_enrichment(run_label, root, force)
    document = load_json(source_path)
    enriched = enrich_document(
        document,
        limit_signals=limit_signals,
        attachments_per_signal=attachments_per_signal,
    )
    save_json(enriched_signals_path(run_label, root), enriched)
    return enriched


def main() -> None:
    args = parse_args()
    data_root = Path(args.data_root)
    run_label = args.run_label or latest_run_label(data_root)
    if not run_label:
        raise SystemExit("No processed runs found to enrich.")

    enriched = enrich_run(
        run_label,
        data_root=data_root,
        limit_signals=args.limit_signals,
        attachments_per_signal=args.attachments_per_signal,
        force=args.force,
    )
    summary = enriched.get("attachment_parsing", {})
    print(f"Run label: {run_label}")
    print(f"Attachments attempted: {summary.get('attempted', 0)}")
    print(f"Attachments completed: {summary.get('completed', 0)}")
    print(f"Enriched signals file: {enriched_signals_path(run_label, data_root)}")


if __name__ == "__main__":
    main()
