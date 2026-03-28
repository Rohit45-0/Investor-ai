from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path

REPORTLAB_FALLBACK = Path("D:/AIInvestorPyDeps/reportlab")
if REPORTLAB_FALLBACK.exists():
    sys.path.insert(0, str(REPORTLAB_FALLBACK))

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    Flowable,
    HRFlowable,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


ROOT_DIR = Path(__file__).resolve().parents[1]
OUTPUT_PATH = ROOT_DIR / "submission" / "Investor_ai_Detailed_Submission.pdf"
REPO_URL = "https://github.com/Rohit45-0/Investor-ai"
VIDEO_PATH = "submission/pitch_video/Investor_ai_Hackathon_Demo.mp4"
TODAY_LABEL = datetime.now().strftime("%d %B %Y")


class ArchitectureDiagram(Flowable):
    def __init__(self, width: float = 500, height: float = 260):
        super().__init__()
        self.width = width
        self.height = height
        self.base_width = 650
        self.base_height = 236
        self.draw_width = width
        self.draw_height = height

    def wrap(self, availWidth, availHeight):
        self.draw_width = min(availWidth, self.width)
        self.draw_height = self.height
        return self.draw_width, self.draw_height

    def draw_box(self, x, y, w, h, title, subtitle="", fill="#F6F3EC", stroke="#D6CDBF", title_color="#172033"):
        self.canv.saveState()
        self.canv.setFillColor(colors.HexColor(fill))
        self.canv.setStrokeColor(colors.HexColor(stroke))
        self.canv.setLineWidth(1)
        self.canv.roundRect(x, y, w, h, 10, fill=1, stroke=1)
        self.canv.setFillColor(colors.HexColor(title_color))
        self.canv.setFont("Helvetica-Bold", 10)
        self.canv.drawString(x + 10, y + h - 18, title)
        if subtitle:
            self.canv.setFont("Helvetica", 8.5)
            text = self.canv.beginText(x + 10, y + h - 32)
            text.setLeading(11)
            for line in subtitle.split("\n"):
                text.textLine(line)
            self.canv.drawText(text)
        self.canv.restoreState()

    def arrow(self, x1, y1, x2, y2, color="#2A4C7D"):
        self.canv.saveState()
        self.canv.setStrokeColor(colors.HexColor(color))
        self.canv.setFillColor(colors.HexColor(color))
        self.canv.setLineWidth(1.6)
        self.canv.line(x1, y1, x2, y2)
        if x2 >= x1:
            self.canv.line(x2, y2, x2 - 6, y2 + 4)
            self.canv.line(x2, y2, x2 - 6, y2 - 4)
        else:
            self.canv.line(x2, y2, x2 + 6, y2 + 4)
            self.canv.line(x2, y2, x2 + 6, y2 - 4)
        self.canv.restoreState()

    def draw(self):
        c = self.canv
        width = self.base_width
        height = self.base_height

        c.saveState()
        c.scale(self.draw_width / self.base_width, self.draw_height / self.base_height)
        c.setFillColor(colors.HexColor("#FBF7F0"))
        c.setStrokeColor(colors.HexColor("#E3D9C7"))
        c.roundRect(0, 0, width, height, 14, fill=1, stroke=1)

        self.draw_box(18, 192, 116, 44, "NSE Feeds", "Disclosures\ninsider trades")
        self.draw_box(18, 132, 116, 44, "OHLCV Feed", "Historical +\nintraday candles")

        self.draw_box(172, 192, 126, 44, "Collect + Normalize", "Event stream")
        self.draw_box(172, 132, 126, 44, "Chart Engine", "Indicators + patterns")

        self.draw_box(336, 192, 144, 44, "Agentic Review Desk", "Scout, Router,\nFiling, Bull, Bear, Referee")
        self.draw_box(336, 132, 144, 44, "Chart Publishing", "Backtests +\nranked setups")

        self.draw_box(516, 192, 134, 44, "Opportunity Radar", "Daily alerts")
        self.draw_box(516, 132, 134, 44, "Chart Intelligence", "NSE chart feed")

        self.draw_box(172, 52, 126, 46, "Chat Index", "Run-aware retrieval")
        self.draw_box(336, 52, 144, 46, "Video Payload Builder", "Scenes + narration")
        self.draw_box(516, 52, 134, 46, "Market ChatGPT", "Grounded answers")
        self.draw_box(516, 6, 134, 34, "Remotion Video Engine", "Pitch video + daily wrap", fill="#EEF5FF")

        self.arrow(134, 214, 172, 214)
        self.arrow(134, 154, 172, 154)
        self.arrow(298, 214, 336, 214)
        self.arrow(298, 154, 336, 154)
        self.arrow(480, 214, 516, 214)
        self.arrow(480, 154, 516, 154)
        self.arrow(580, 192, 580, 104)
        self.arrow(580, 132, 580, 104)
        self.arrow(516, 76, 480, 76)
        self.arrow(336, 76, 298, 76)
        self.arrow(480, 28, 516, 28)
        self.arrow(408, 192, 408, 98)
        self.arrow(240, 192, 240, 98)

        c.restoreState()


def build_styles():
    styles = getSampleStyleSheet()
    styles.add(
        ParagraphStyle(
            name="DocTitle",
            parent=styles["Title"],
            fontName="Helvetica-Bold",
            fontSize=26,
            leading=30,
            textColor=colors.HexColor("#16233B"),
            alignment=TA_LEFT,
            spaceAfter=10,
        )
    )
    styles.add(
        ParagraphStyle(
            name="DocSubtitle",
            parent=styles["BodyText"],
            fontName="Helvetica",
            fontSize=12,
            leading=17,
            textColor=colors.HexColor("#44506A"),
            spaceAfter=14,
        )
    )
    styles.add(
        ParagraphStyle(
            name="SectionTitle",
            parent=styles["Heading1"],
            fontName="Helvetica-Bold",
            fontSize=18,
            leading=22,
            textColor=colors.HexColor("#1C355E"),
            spaceBefore=6,
            spaceAfter=10,
        )
    )
    styles.add(
        ParagraphStyle(
            name="SubSectionTitle",
            parent=styles["Heading2"],
            fontName="Helvetica-Bold",
            fontSize=13,
            leading=16,
            textColor=colors.HexColor("#234574"),
            spaceBefore=8,
            spaceAfter=6,
        )
    )
    styles.add(
        ParagraphStyle(
            name="BodyCopy",
            parent=styles["BodyText"],
            fontName="Helvetica",
            fontSize=10.3,
            leading=15,
            textColor=colors.HexColor("#2A2F3A"),
            spaceAfter=7,
        )
    )
    styles.add(
        ParagraphStyle(
            name="BulletCopy",
            parent=styles["BodyText"],
            fontName="Helvetica",
            fontSize=10.1,
            leading=14.5,
            leftIndent=14,
            firstLineIndent=-8,
            bulletIndent=0,
            textColor=colors.HexColor("#2A2F3A"),
            spaceAfter=4,
        )
    )
    styles.add(
        ParagraphStyle(
            name="CenterSmall",
            parent=styles["BodyText"],
            fontName="Helvetica",
            fontSize=9.4,
            leading=13,
            alignment=TA_CENTER,
            textColor=colors.HexColor("#5B6274"),
        )
    )
    styles.add(
        ParagraphStyle(
            name="TableHeader",
            parent=styles["BodyText"],
            fontName="Helvetica-Bold",
            fontSize=9.1,
            leading=11,
            textColor=colors.white,
            alignment=TA_LEFT,
        )
    )
    styles.add(
        ParagraphStyle(
            name="TableCell",
            parent=styles["BodyText"],
            fontName="Helvetica",
            fontSize=8.9,
            leading=11,
            textColor=colors.HexColor("#232836"),
            wordWrap="CJK",
        )
    )
    styles.add(
        ParagraphStyle(
            name="TableCellSmall",
            parent=styles["BodyText"],
            fontName="Helvetica",
            fontSize=8.3,
            leading=10.2,
            textColor=colors.HexColor("#232836"),
            wordWrap="CJK",
        )
    )
    styles.add(
        ParagraphStyle(
            name="Callout",
            parent=styles["BodyText"],
            fontName="Helvetica-Bold",
            fontSize=11,
            leading=15,
            textColor=colors.white,
            alignment=TA_CENTER,
        )
    )
    return styles


def bullet(text: str, styles) -> Paragraph:
    return Paragraph(f"&bull; {text}", styles["BulletCopy"])


def wrap_table_rows(rows, styles, *, body_style: str = "TableCell", header_style: str = "TableHeader"):
    wrapped = []
    for row_index, row in enumerate(rows):
        style_name = header_style if row_index == 0 else body_style
        wrapped.append([Paragraph(str(cell), styles[style_name]) for cell in row])
    return wrapped


def section_heading(title: str, styles):
    return [Spacer(1, 6), Paragraph(title, styles["SectionTitle"]), HRFlowable(width="100%", color=colors.HexColor("#D7D1C5"), thickness=0.8), Spacer(1, 8)]


def metrics_table(styles):
    rows = [
        ["Metric", "Estimate", "Rationale"],
        ["Retail investor time saved", "416,700 hours/year", "1,000 serious users saving 100 minutes per market day"],
        ["Time-value efficiency", "~ INR 12.5 crore/year", "Assumes INR 300/hour value of investor time"],
        ["Direct improved-decision value", "~ INR 12 lakh/year", "Conservative monthly benefit on a small subset of users"],
        ["Analyst / creator media time", "250 hours/year per operator", "Automated market brief generation instead of manual editing"],
    ]
    table = Table(wrap_table_rows(rows, styles), colWidths=[108, 100, 257], repeatRows=1, hAlign="LEFT")
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#20365F")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("BACKGROUND", (0, 1), (-1, -1), colors.HexColor("#FBF7F0")),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.HexColor("#FBF7F0"), colors.HexColor("#F4EEE2")]),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#D8CEBF")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 7),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
            ]
        )
    )
    return table


def products_table(styles):
    rows = [
        ["Product", "Primary Input", "Output", "Why It Matters", "AI Mode"],
        [
            "Opportunity Radar",
            "NSE disclosures, results, insider trades, block/bulk deals",
            "Ranked investor alerts",
            "Finds missed opportunities from raw market events",
            "Agentic + rule-based",
        ],
        [
            "Chart Pattern Intelligence",
            "Historical + intraday OHLCV",
            "Backtested chart setups",
            "Adds technical confirmation with stock-specific context",
            "Deterministic + explanation",
        ],
        [
            "Market ChatGPT",
            "Indexed disclosure and chart runs",
            "Grounded cited answers",
            "Explains what changed and what to verify next",
            "Retrieval + LLM reasoning",
        ],
        [
            "AI Market Video Engine",
            "Signal bundles + chart breadth + queue logic",
            "Narrated MP4 briefings",
            "Publishes market intelligence with zero manual editing",
            "Payload + TTS + Remotion",
        ],
    ]
    table = Table(wrap_table_rows(rows, styles, body_style="TableCellSmall"), colWidths=[82, 103, 78, 129, 73], repeatRows=1, hAlign="LEFT")
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#20365F")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.HexColor("#FBF7F0"), colors.HexColor("#F2ECDF")]),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#D8CEBF")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    return table


def role_table(styles):
    rows = [
        ["Agent / Component", "Responsibility"],
        ["Scout", "Collects the market universe and surfaces candidate events for deeper review."],
        ["Router", "Prioritizes the strongest names so expensive reasoning is spent on the highest-signal cases."],
        ["Filing Analyst", "Turns filing evidence and parsed attachments into a structured brief."],
        ["Bull Analyst", "Builds the strongest evidence-backed upside case."],
        ["Bear Analyst", "Stress-tests the same signal with the strongest risk case."],
        ["Referee", "Weights both sides and publishes the final investor-facing verdict."],
        ["Retriever + Answerer", "Powers Market ChatGPT with grounded, run-aware responses."],
    ]
    table = Table(wrap_table_rows(rows, styles), colWidths=[122, 343], repeatRows=1, hAlign="LEFT")
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#20365F")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.HexColor("#FBF7F0"), colors.HexColor("#F4EEE2")]),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#D8CEBF")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 7),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
            ]
        )
    )
    return table


def page_decor(canvas, doc):
    canvas.saveState()
    canvas.setFillColor(colors.HexColor("#FBF7F0"))
    canvas.rect(0, 0, A4[0], A4[1], fill=1, stroke=0)
    canvas.setFillColor(colors.HexColor("#20365F"))
    canvas.rect(0, A4[1] - 26, A4[0], 26, fill=1, stroke=0)
    canvas.setFillColor(colors.white)
    canvas.setFont("Helvetica-Bold", 10)
    canvas.drawString(doc.leftMargin, A4[1] - 17, "Investor-ai | Detailed Submission")
    canvas.setFillColor(colors.HexColor("#5B6274"))
    canvas.setFont("Helvetica", 9)
    canvas.drawRightString(A4[0] - doc.rightMargin, 16, f"Page {doc.page}")
    canvas.drawString(doc.leftMargin, 16, REPO_URL)
    canvas.restoreState()


def story():
    styles = build_styles()
    items = []

    cover_box = Table(
        [[Paragraph("Hackathon Submission Packet", styles["Callout"])]],
        colWidths=[170],
        rowHeights=[28],
    )
    cover_box.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#20365F")),
                ("BOX", (0, 0), (-1, -1), 0, colors.white),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ]
        )
    )

    items.extend(
        [
            Spacer(1, 24),
            cover_box,
            Spacer(1, 22),
            Paragraph("Investor-ai", styles["DocTitle"]),
            Paragraph(
                "AI for the Indian Investor. A unified market-intelligence system spanning Opportunity Radar, Chart Pattern Intelligence, Market ChatGPT, and the AI Market Video Engine.",
                styles["DocSubtitle"],
            ),
            Paragraph(
                "Prepared for PS 6 submission on " + TODAY_LABEL,
                styles["BodyCopy"],
            ),
            Spacer(1, 14),
        ]
    )

    cover_points = [
        "Public GitHub repository with source code and commit history",
        "3-minute product walkthrough video included in the repo",
        "Architecture document describing agent roles, integrations, and flow",
        "Impact model estimating time savings and business value",
    ]
    for point in cover_points:
        items.append(bullet(point, styles))

    items.extend(
        [
            Spacer(1, 16),
            Table(
                wrap_table_rows(
                    [
                    ["Repository", REPO_URL],
                    ["Pitch video", VIDEO_PATH],
                    ["Core products", "Opportunity Radar | Chart Pattern Intelligence | Market ChatGPT | AI Market Video Engine"],
                    ["Verification", "Automated test suite passing: 30 tests"],
                    ],
                    styles,
                    body_style="TableCell",
                    header_style="TableCell",
                ),
                colWidths=[90, 375],
                hAlign="LEFT",
                style=TableStyle(
                    [
                        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F4EEE2")),
                        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#D8CEBF")),
                        ("LEFTPADDING", (0, 0), (-1, -1), 8),
                        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                        ("TOPPADDING", (0, 0), (-1, -1), 7),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
                        ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ]
                ),
            ),
            PageBreak(),
        ]
    )

    items.extend(section_heading("1. Problem Statement And Solution Thesis", styles))
    items.extend(
        [
            Paragraph(
                "Retail investors often react to tips, fragmented headlines, or chart noise because the real market signal is buried across disclosures, corporate actions, technical structure, and commentary changes. Investor-ai is designed as the intelligence layer that converts that raw market data into actionable decisions, grounded explanations, and communication-ready outputs.",
                styles["BodyCopy"],
            ),
            Paragraph(
                "The system is deliberately productized into four surfaces rather than one generic dashboard. Each surface solves a distinct investor problem, but all four share the same underlying market context so the user can move from discovery to validation to explanation without losing continuity.",
                styles["BodyCopy"],
            ),
            products_table(styles),
        ]
    )

    items.extend(section_heading("2. End-To-End Architecture", styles))
    items.extend(
        [
            Paragraph(
                "The platform combines deterministic ingestion and scoring, agentic review where judgment matters, retrieval-backed answering for chat, and programmatic publishing for video. This split keeps the system precise where it must be reproducible and flexible where it must reason across ambiguous evidence.",
                styles["BodyCopy"],
            ),
            Spacer(1, 8),
            ArchitectureDiagram(width=465, height=240),
            Spacer(1, 10),
            bullet("Disclosure data and chart data remain parallel pipelines until they are intentionally merged for chat and video.", styles),
            bullet("Opportunity Radar uses the deepest agentic workflow because filing interpretation benefits most from multi-role reasoning.", styles),
            bullet("Chart Pattern Intelligence remains rule-based first, so technical setups stay reproducible and backtestable.", styles),
            bullet("The AI Market Video Engine is a publishing layer that assembles data-driven scenes and narration automatically.", styles),
        ]
    )

    items.extend(section_heading("3. Agentic AI Design", styles))
    items.extend(
        [
            Paragraph(
                "The agentic core sits inside the disclosure-analysis lane. Instead of sending a filing through one large prompt, the system routes shortlisted signals through specialized roles that each contribute a different perspective before a final publishable verdict is produced.",
                styles["BodyCopy"],
            ),
            role_table(styles),
            Spacer(1, 10),
            Paragraph("Why this is genuinely agentic and not just prompt chaining:", styles["SubSectionTitle"]),
            bullet("The workflow is role-based, stateful, and explicit inside LangGraph.", styles),
            bullet("Each agent has a distinct responsibility and structured output contract.", styles),
            bullet("Bull and bear arguments are intentionally separated before the referee decision.", styles),
            bullet("The final published alert is the result of arbitration, not a one-shot summary.", styles),
            bullet("Chat also follows a retrieval-first reasoning path so responses stay grounded in indexed evidence.", styles),
        ]
    )

    items.extend(section_heading("4. Product Experience And Demo Flow", styles))
    items.extend(
        [
            Paragraph(
                "The project is demoed as one connected investor workflow rather than four disconnected tabs. The recommended order mirrors how a serious investor would use the system during the market day.",
                styles["BodyCopy"],
            ),
            Paragraph("Recommended live demo sequence:", styles["SubSectionTitle"]),
            bullet("Start on the homepage with the AI Market Video Engine to show the system can auto-publish an investor-facing briefing.", styles),
            bullet("Move to Opportunity Radar to show how disclosures are converted into ranked signals instead of summaries.", styles),
            bullet("Open Chart Pattern Intelligence to show breakouts, reversals, support/resistance reactions, and stock-specific backtest context.", styles),
            bullet("Finish with Market ChatGPT to show source-aware, run-aware analysis over the indexed market state.", styles),
            Paragraph("Operational readiness:", styles["SubSectionTitle"]),
            bullet("A one-command prep script refreshes the data, chart scan, video payload, and local demo server.", styles),
            bullet("The project also includes a dedicated 3-minute Remotion-generated pitch video in the repository.", styles),
            bullet("The backend test suite currently passes with 30 automated checks.", styles),
        ]
    )

    items.extend(section_heading("5. Technical Implementation Summary", styles))
    items.extend(
        [
            Paragraph(
                "The application is implemented as a FastAPI backend with static frontend pages, a LangGraph-based agent runtime, a chart-processing package, a retrieval-backed chat lane, and a Remotion rendering engine for market videos and pitch media.",
                styles["BodyCopy"],
            ),
            Paragraph("Primary stack:", styles["SubSectionTitle"]),
            bullet("Python, FastAPI, Requests, python-dotenv, LangGraph", styles),
            bullet("Static HTML, CSS, and JavaScript frontend", styles),
            bullet("OpenAI APIs for explanations, grounded answers, and narration audio", styles),
            bullet("Remotion for automated MP4 generation", styles),
            Paragraph("Core commands used in the repo:", styles["SubSectionTitle"]),
            bullet("`python scripts/prepare_demo.py --serve`", styles),
            bullet("`python scripts/run_mvp.py --mode multi_agent --days-back 1 --agent-signal-limit 5`", styles),
            bullet("`python scripts/run_chart_radar.py --symbol-limit 50 --skip-explanations`", styles),
            bullet("`python scripts/render_market_video.py`", styles),
            bullet("`python scripts/render_product_demo.py --overwrite-audio`", styles),
        ]
    )

    items.extend(section_heading("6. Impact Model", styles))
    items.extend(
        [
            Paragraph(
                "The value of Investor-ai comes from compressing the time between a market event and an actionable investor decision. The impact model below uses intentionally conservative assumptions for early adoption and separates workflow efficiency from direct decision-value upside.",
                styles["BodyCopy"],
            ),
            metrics_table(styles),
            Spacer(1, 10),
            bullet("The model assumes only 1,000 serious early users and does not assume every alert becomes a trade.", styles),
            bullet("The largest value driver is investor focus and time saved, not exaggerated prediction claims.", styles),
            bullet("The same intelligence layer also reduces media and analyst effort because it can publish itself as chat answers and videos.", styles),
        ]
    )

    items.extend(section_heading("7. Submission Checklist", styles))
    checklist_rows = [
        ["Requirement", "Status", "Artifact"],
        ["Public GitHub repository", "Complete", REPO_URL],
        ["3-minute pitch video", "Complete", VIDEO_PATH],
        ["Architecture document", "Complete", "submission/architecture.md"],
        ["Impact model", "Complete", "submission/impact_model.md"],
        ["Detailed PDF", "Complete", "submission/Investor_ai_Detailed_Submission.pdf"],
    ]
    checklist = Table(wrap_table_rows(checklist_rows, styles), colWidths=[122, 62, 281], repeatRows=1, hAlign="LEFT")
    checklist.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#20365F")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.HexColor("#FBF7F0"), colors.HexColor("#F4EEE2")]),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#D8CEBF")),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 7),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ]
        )
    )
    items.extend(
        [
            checklist,
            Spacer(1, 12),
            Paragraph(
                "Investor-ai is submission-ready as a coherent hackathon system: one intelligence layer, four product surfaces, a real agentic review path, a grounded chat lane, and auto-generated video outputs that demonstrate both product utility and communication readiness.",
                styles["BodyCopy"],
            ),
        ]
    )

    return items


def main() -> None:
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    doc = SimpleDocTemplate(
        str(OUTPUT_PATH),
        pagesize=A4,
        leftMargin=18 * mm,
        rightMargin=18 * mm,
        topMargin=20 * mm,
        bottomMargin=18 * mm,
        title="Investor-ai Detailed Submission",
        author="OpenAI Codex for Rohit45-0",
    )
    doc.build(story(), onFirstPage=page_decor, onLaterPages=page_decor)
    print(f"PDF written to: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
