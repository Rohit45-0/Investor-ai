# Investor-ai

AI for the Indian Investor. This repository contains the hackathon build for
`Opportunity Radar`, `Chart Pattern Intelligence`, `Market ChatGPT`, and the
`AI Market Video Engine`.

This repository now contains a working MVP for PS 6, focused on the
`Opportunity Radar` track, with a LangGraph-based multi-agent review layer.

The app does six things:

1. Collect daily market disclosures from official NSE feeds
2. Normalize them into one event stream
3. Score them with rule-based signal logic
4. Parse filing attachments for top signals
5. Run a multi-agent debate on shortlisted signals
6. Serve a dashboard through FastAPI

It now also includes a parallel `Chart Pattern Intelligence` lane that scans OHLCV data for breakouts, reversals, support/resistance reactions, and divergences with stock-specific backtest context.
It also now includes a partial `AI Market Video Engine` lane that builds a Remotion-ready daily market-wrap video from the latest disclosure and chart runs.

## Submission Assets

- `submission/Investor_ai_Detailed_Submission.pdf` - detailed upload-ready submission document
- `submission/architecture.md` - architecture diagram and system description
- `submission/impact_model.md` - quantified impact assumptions
- `submission/pitch_video/Investor_ai_Hackathon_Demo.mp4` - 3-minute pitch video

## Stack

- Python
- FastAPI
- Requests
- python-dotenv
- LangGraph
- Static HTML/CSS/JS frontend

## Setup

Create a `.env` file:

```env
OPENAI_API_KEY=your_key_here
OPENAI_MODEL=gpt-4.1-mini
DATA_DIR=D:\\AIInvestorData
```

The OpenAI step is optional. Collection and rule-based scoring work without it.
By default, the app runs in `multi_agent` orchestration mode.
If your `C:` drive is tight on space, point `DATA_DIR` to a folder on `D:` and the API/UI will use that location for all runs.

## Commands

Collect only:

```bash
python scripts/collect_today.py
```

Score the latest run:

```bash
python scripts/score_signals.py
```

Explain the top signals with OpenAI:

```bash
python scripts/explain_signals.py --limit 5
```

Parse attachment evidence:

```bash
python scripts/parse_attachments.py --limit-signals 5
```

Run the full pipeline:

```bash
python scripts/run_mvp.py --mode multi_agent --days-back 1 --agent-signal-limit 5
```

Prepare the full hackathon demo in one command:

```bash
python scripts/prepare_demo.py --serve
```

Run the chart radar:

```bash
python scripts/run_chart_radar.py --symbol-limit 50 --skip-explanations
```

Build the latest daily market-wrap payload:

```bash
python scripts/build_market_video_payload.py
```

Render the full market-wrap video at reduced scale:

```bash
python scripts/render_market_video.py --scale 0.5
```

Render the full market-wrap video at the default full-quality 1080 layout:

```bash
python scripts/render_market_video.py
```

Render a faster preview clip:

```bash
python scripts/render_market_video.py --preview
```

Render the full 3-minute narrated hackathon demo film in 1080p:

```bash
python scripts/render_product_demo.py --overwrite-audio
```

Start the dashboard:

```bash
uvicorn app.main:app --reload
```

Initialize the chat schema:

```bash
$env:PYTHONPATH='.'; python scripts/init_chat_db.py
```

Index the latest run for grounded chat:

```bash
$env:PYTHONPATH='.'; python scripts/build_chat_index.py --run-label 2026-03-24
```

Then open:

```text
http://127.0.0.1:8000
```

Frontend pages:

- `/` - home page with the Opportunity Radar story and latest top alerts
- `/radar` - daily alert feed
- `/chart-radar` - chart-pattern feed across the NSE universe
- `/watchlist` - saved stocks and quick add
- `/brief?symbol=RELIANCE` - single-stock brief
- `/chat` - grounded RAG-style chat over indexed filings and signals

## Output Files

Collection outputs:

- `data/raw/<run_label>/corporate_announcements.json`
- `data/raw/<run_label>/insider_trades.json`
- `data/raw/<run_label>/bulk_deals.json`

Normalized data:

- `data/processed/<run_label>/events.json`
- `data/processed/<run_label>/manifest.json`

Signal outputs:

- `data/processed/<run_label>/signals.json`
- `data/processed/<run_label>/signals_enriched.json`
- `data/processed/<run_label>/signals_explained.json`

Chart outputs:

- `data/processed/chart/<run_label>/signals.json`
- `data/processed/chart/<run_label>/stocks/<symbol>.json`

Video outputs:

- `data/processed/video/<run_label>/daily_market_wrap.json`
- `data/processed/video/<run_label>/daily_market_wrap.mp4`
- `data/processed/video/<run_label>/daily_market_wrap_voiceover.mp3`

## API Endpoints

- `GET /api/health`
- `GET /api/runs`
- `GET /api/signals/latest`
- `GET /api/signals/{run_label}`
- `GET /api/chart-runs`
- `GET /api/chart-signals/latest`
- `GET /api/chart-signals/{run_label}`
- `GET /api/video/latest`
- `GET /api/video/status`
- `GET /api/stocks/{symbol}/chart`
- `GET /api/chat/status`
- `POST /api/chat/reindex`
- `POST /api/chat/query`
- `POST /api/run`
- `POST /api/chart-run`
- `POST /api/video-build`

Example run payload:

```json
{
  "days_back": 1,
  "orchestration_mode": "multi_agent",
  "include_explanations": true,
  "explanation_limit": 5,
  "agent_signal_limit": 5
}
```

## Multi-Agent Roles

The LangGraph workflow uses:

- `Scout`: collects the market universe
- `Router`: scores raw disclosures and shortlists candidates
- `Filing Analyst`: reads parsed attachment evidence
- `Bull Analyst`: argues the upside case
- `Bear Analyst`: argues the risk case
- `Referee`: decides the final investor-facing verdict

## Current Signal Logic

The scoring layer currently favors:

- promoter/director insider market purchases
- repeated insider accumulation
- order/contract disclosures
- acquisition or strategic-update disclosures

It downweights:

- clarifications
- trading-window notices
- press releases
- newspaper publications
- non-open-market insider transfers

## Chart Pattern Intelligence

The chart pipeline is separate from the disclosure radar and is built around:

- Yahoo Finance OHLCV candles as the chart data provider
- 5-minute intraday scans plus 2-year daily history
- pattern families: breakout, reversal, divergence
- pattern labels: bullish breakout, bearish breakdown, bullish reversal at support, bearish reversal at resistance, support bounce, resistance rejection, bullish divergence, bearish divergence
- 7-trading-day stock-specific backtests using a `+/- 1 ATR` outcome rule

## AI Market Video Engine

The first video slice is intentionally narrow and built for a strong proof point:

- a widescreen `Daily Market Wrap` composition rendered with Remotion
- backend payload generation from the latest disclosure run plus the latest chart run
- scene types for hero stats, filing board, chart board, research queue, and close
- automatic full-video re-rendering after disclosure refreshes, chart scans, and manual video builds
- default full-quality rendering now targets the full 1080 layout unless you override `VIDEO_RENDER_SCALE`
- optional AI narration generated from the wrap's `tts_script` and embedded into the MP4
- clearer narration defaults tuned for ticker symbols, percentages, price levels, and other market numbers
- D-drive render staging when the repo drive is too full for large Node dependencies or temporary frame files
- scripts that can build the payload only or export an MP4 without manual editing

### Video Automation

When you trigger a fresh disclosure run or chart scan, the backend now:

1. saves a new `daily_market_wrap.json` payload
2. queues a background MP4 render if `VIDEO_AUTO_RENDER=true`
3. tries to synthesize narration if `VIDEO_TTS_ENABLED=true` and `OPENAI_API_KEY` is present
4. exposes render status through `GET /api/video/status` and the render metadata inside `GET /api/video/latest`

Recommended env vars for the video lane:

```env
VIDEO_AUTO_RENDER=true
VIDEO_RENDER_SCALE=1.0
VIDEO_RENDER_WORKSPACE=D:\\AIInvestorVideoEngine\\workspace
VIDEO_TTS_ENABLED=true
VIDEO_TTS_MODEL=gpt-4o-mini-tts
VIDEO_TTS_VOICE=coral
VIDEO_TTS_INSTRUCTIONS=Speak like a calm Indian markets anchor in a studio bulletin. Enunciate ticker symbols, numbers, percentages, and price levels clearly. Keep a steady pace, use short pauses, and avoid hype.
VIDEO_TTS_SPEED=0.95
```

If `OPENAI_API_KEY` is missing, the video still renders, but it will stay silent and the render metadata will record why narration was skipped.

## Important Note

Your `C:` drive is nearly full. The current daily run is fine, but large backfills
can fail if they write to the repo folder. For wider test runs, use:

```bash
python scripts/run_mvp.py --days-back 7 --output-root D:\\AIInvestorDataTest
```
