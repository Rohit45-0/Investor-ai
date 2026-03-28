const samplePayload = {
  video_id: "daily-market-wrap",
  title: "Opportunity Radar Daily Market Wrap",
  generated_at: "2026-03-27T18:20:00+05:30",
  market_date: "2026-03-27",
  fps: 30,
  width: 1920,
  height: 1080,
  duration_in_frames: 1260,
  duration_seconds: 42,
  brand: {
    name: "Opportunity Radar",
    tagline: "AI for the Indian Investor",
  },
  source_runs: {
    disclosure_run_label: "2026-03-24",
    chart_run_label: "2026-03-27T13-08-08+05-30",
  },
  summary: {
    tone: "mixed",
    headline: "The tape is mixed: selective filings, active charts, and no single market regime yet.",
    subhead: "Use the wrap as a research queue. Conviction is still stock-specific.",
  },
  stats: {
    filing_alerts: 107,
    chart_alerts: 743,
    fresh_disclosures: 2021,
    cross_signal_names: 3,
  },
  generation_matrix: [
    {
      label: "Filing alerts",
      value: 107,
      note: "Ranked disclosure-led signals available to the wrap from filings, insider trades, and bulk deals.",
      source: "disclosure radar",
    },
    {
      label: "Fresh disclosures",
      value: 2021,
      note: "Raw exchange events considered before the disclosure scorer narrows the board.",
      source: "exchange feed",
    },
    {
      label: "Chart alerts",
      value: 743,
      note: "Published chart setups from breakout, reversal, support or resistance, and divergence scans.",
      source: "chart radar",
    },
    {
      label: "Pattern families",
      value: 4,
      note: "How many distinct chart pattern families are active in the current chart run.",
      source: "chart radar",
    },
    {
      label: "Bull vs bear",
      value: "5 bull / 2 bear",
      note: "The headline tone comes from the directional spread across the filing and chart cards pulled into the wrap.",
      source: "mixed",
    },
    {
      label: "Cross-radar overlap",
      value: 3,
      note: "Names appearing across both disclosure and chart lanes rise higher in the research queue.",
      source: "merged queue",
    },
    {
      label: "Top filing score",
      value: 217,
      note: "Highest rule-based disclosure score in the latest disclosure run.",
      source: "disclosure radar",
    },
    {
      label: "Top chart score",
      value: 98,
      note: "Highest chart setup score in the latest chart run after confirmation and backtest context.",
      source: "chart radar",
    },
    {
      label: "Research queue",
      value: 4,
      note: "Merged carry-forward list after combining both lanes into a single research queue.",
      source: "video engine",
    },
  ],
  generation_methodology: [
    "The hero tone is driven by the bullish-versus-bearish spread across the strongest disclosure and chart cards.",
    "The filing board selects the highest-ranking disclosure signals from the latest disclosure run.",
    "The chart board selects the highest-ranking chart setups with support, resistance, and stock-specific 7-day hit-rate context.",
    "The research queue merges both lanes so overlap names rise while strong single-lens outliers still stay visible.",
  ],
  audio: {
    enabled: true,
    available: false,
    provider: "openai",
    model: "gpt-4o-mini-tts",
    voice: "coral",
    ai_generated: true,
    disclosure: "Narration uses an AI-generated voice.",
  },
  render: {
    status: "synced",
    label: "Rendered video is synced to the latest runs.",
    is_synced: true,
    video_run_label: "2026-03-27T18-20-00+05-30",
    generated_at: "2026-03-27T18:20:00+05:30",
    rendered_at: "2026-03-27T18:25:00+05:30",
    media_available: true,
    media_url: "/api/video/media/2026-03-27T18-20-00+05-30",
    render_mode: "full",
    render_duration_seconds: 42,
    audio_included: true,
    audio_disclosure: "Narration uses an AI-generated voice.",
  },
  scenes: [
    {
      id: "hero",
      type: "hero",
      duration_frames: 180,
      eyebrow: "Opportunity Radar",
      headline: "Selective filings. Active charts. No broad-market verdict yet.",
      subhead:
        "A vertically rendered market wrap for the strongest disclosure and chart signals in one research-ready reel.",
      voiceover:
        "Selective filings and active charts are shaping today's market wrap. Use this as a research queue, not a blanket verdict.",
      stats: [
        { label: "Filing alerts", value: 107 },
        { label: "Chart alerts", value: 743 },
        { label: "Fresh disclosures", value: 2021 },
        { label: "Cross-signal names", value: 3 }
      ]
    },
    {
      id: "filings",
      type: "board",
      duration_frames: 300,
      eyebrow: "Filing Radar",
      title: "Disclosure-led ideas in focus",
      subtitle: "Signals pulled from exchange filings, insider activity, and bulk deals.",
      voiceover:
        "On the filing radar, the strongest research triggers are CELEBRITY, PREMIERPOL, and RELIANCE.",
      items: [
        {
          symbol: "CELEBRITY",
          company: "Celebrity Fashions Limited",
          direction: "bullish",
          headline: "Director Preferential Offer Buy",
          summary: "Insider and promoter participation kept stacking up in the latest filing bundle.",
          score: 217,
          confidence: 85,
          metric_label: "Signal score",
          metric_value: 217,
          detail: "Preferential offer participation remains the leading disclosure clue.",
          source: "disclosure"
        },
        {
          symbol: "PREMIERPOL",
          company: "Premier Polyfilm Limited",
          direction: "bullish",
          headline: "Promoter Group Insider Buys",
          summary: "Multiple promoter-linked open-market purchases landed in the same run.",
          score: 178,
          confidence: 84,
          metric_label: "Signal score",
          metric_value: 178,
          detail: "Clustered promoter buying often deserves follow-through research.",
          source: "disclosure"
        },
        {
          symbol: "RELIANCE",
          company: "Reliance Industries Limited",
          direction: "bullish",
          headline: "Promoter Buying Cluster",
          summary: "Capital allocation signals and promoter action both keep attention on the name.",
          score: 84,
          confidence: 82,
          metric_label: "Signal score",
          metric_value: 84,
          detail: "This is a filing-led watchlist candidate with broad investor familiarity.",
          source: "disclosure"
        },
        {
          symbol: "INFY",
          company: "Infosys Limited",
          direction: "bearish",
          headline: "Clarification Overhang",
          summary: "The latest disclosure flow is more cautionary than confirmatory.",
          score: 66,
          confidence: 70,
          metric_label: "Signal score",
          metric_value: 66,
          detail: "This is the defensive counterweight on the board.",
          source: "disclosure"
        }
      ]
    },
    {
      id: "charts",
      type: "board",
      duration_frames: 360,
      eyebrow: "Chart Radar",
      title: "Price structure is active here",
      subtitle: "Breakouts, reversals, and divergences ranked with stock-specific hit-rate context.",
      voiceover:
        "On the chart radar, price structure is most active in GRAPHITE, SGMART, and RELIANCE.",
      items: [
        {
          symbol: "GRAPHITE",
          company: "Graphite India Limited",
          direction: "bullish",
          headline: "Bullish Breakout",
          summary: "Price cleared resistance with volume, but the prior hit rate has been mixed.",
          score: 98,
          confidence: 87,
          metric_label: "7D hit rate",
          metric_value: "35.7%",
          detail: "5m | Support 520.20 / Resistance 534.60 | 14 samples",
          timeframe: "5m",
          success_rate: 35.7,
          sample_size: 14,
          sparkline: [0.1, 0.14, 0.18, 0.15, 0.21, 0.25, 0.28, 0.24, 0.34, 0.38, 0.44, 0.47, 0.52, 0.56, 0.61, 0.68, 0.7, 0.72, 0.77, 0.81, 0.86, 0.88, 0.9, 0.95, 1],
          source: "chart"
        },
        {
          symbol: "SGMART",
          company: "SG Mart Limited",
          direction: "bullish",
          headline: "Bullish Breakout",
          summary: "Fresh strength arrived above resistance, but the stock-specific history is still thin.",
          score: 98,
          confidence: 87,
          metric_label: "7D hit rate",
          metric_value: "50.0%",
          detail: "5m | Support 452.40 / Resistance 479.10 | 4 samples",
          timeframe: "5m",
          success_rate: 50,
          sample_size: 4,
          sparkline: [0.05, 0.08, 0.11, 0.1, 0.09, 0.16, 0.2, 0.23, 0.19, 0.28, 0.31, 0.36, 0.4, 0.44, 0.42, 0.48, 0.53, 0.59, 0.62, 0.67, 0.7, 0.74, 0.79, 0.85, 1],
          source: "chart"
        },
        {
          symbol: "RELIANCE",
          company: "Reliance Industries Limited",
          direction: "bullish",
          headline: "Bullish Breakout",
          summary: "The stock is pushing above an intraday trigger, keeping it on both radar lanes.",
          score: 91,
          confidence: 85,
          metric_label: "7D hit rate",
          metric_value: "57.1%",
          detail: "5m | Support 2825.50 / Resistance 2862.40 | 14 samples",
          timeframe: "5m",
          success_rate: 57.1,
          sample_size: 14,
          sparkline: [0.04, 0.06, 0.05, 0.11, 0.14, 0.19, 0.24, 0.22, 0.31, 0.33, 0.39, 0.43, 0.47, 0.52, 0.55, 0.58, 0.61, 0.66, 0.69, 0.75, 0.8, 0.84, 0.89, 0.93, 1],
          source: "chart"
        },
        {
          symbol: "TCS",
          company: "Tata Consultancy Services Limited",
          direction: "bearish",
          headline: "Resistance Rejection",
          summary: "The stock stalled near overhead supply and turned lower on the daily chart.",
          score: 74,
          confidence: 76,
          metric_label: "7D hit rate",
          metric_value: "43.8%",
          detail: "1d | Support 3930.20 / Resistance 4015.70 | 16 samples",
          timeframe: "1d",
          success_rate: 43.8,
          sample_size: 16,
          sparkline: [1, 0.97, 0.94, 0.96, 0.92, 0.88, 0.85, 0.82, 0.8, 0.76, 0.72, 0.68, 0.64, 0.58, 0.55, 0.53, 0.49, 0.45, 0.42, 0.4, 0.36, 0.31, 0.27, 0.19, 0.08],
          source: "chart"
        }
      ]
    },
    {
      id: "queue",
      type: "queue",
      duration_frames: 240,
      eyebrow: "Research Queue",
      title: "Names to carry forward",
      subtitle: "Compound names deserve first attention, but single-lens outliers can still matter.",
      voiceover:
        "Names worth carrying into the next research queue are RELIANCE, CELEBRITY, and GRAPHITE.",
      items: [
        {
          symbol: "RELIANCE",
          company: "Reliance Industries Limited",
          direction: "bullish",
          headline: "Promoter Buying Cluster",
          sources: ["chart radar", "filing radar"],
          conviction: 175,
          thesis: "Both filing activity and chart structure are active.",
          detail: "Promoter buying cluster plus bullish intraday breakout."
        },
        {
          symbol: "CELEBRITY",
          company: "Celebrity Fashions Limited",
          direction: "bullish",
          headline: "Director Preferential Offer Buy",
          sources: ["filing radar"],
          conviction: 217,
          thesis: "Disclosure activity is leading the research queue.",
          detail: "Filing lane is still the main signal source here."
        },
        {
          symbol: "GRAPHITE",
          company: "Graphite India Limited",
          direction: "bullish",
          headline: "Bullish Breakout",
          sources: ["chart radar"],
          conviction: 98,
          thesis: "Price structure is leading the research queue.",
          detail: "Intraday participation is strong enough to keep the setup in focus."
        },
        {
          symbol: "TCS",
          company: "Tata Consultancy Services Limited",
          direction: "bearish",
          headline: "Resistance Rejection",
          sources: ["chart radar"],
          conviction: 74,
          thesis: "Price structure is leading the research queue.",
          detail: "The stock is the main defensive note in the current board."
        }
      ]
    },
    {
      id: "close",
      type: "close",
      duration_frames: 180,
      eyebrow: "Auto-generated",
      title: "Zero human editing, one research-ready wrap",
      subtitle:
        "This first cut proves the market-wrap lane. Next scenes can add race charts, sector rotations, FII/DII flows, and IPO trackers.",
      voiceover:
        "This wrap was assembled automatically from the latest Opportunity Radar and Chart Radar runs.",
      badges: ["Daily market wrap", "Disclosure radar", "Chart radar", "Remotion-ready"]
    }
  ],
  narration: [
    {
      scene_id: "hero",
      text:
        "Selective filings and active charts are shaping today's market wrap. Use this as a research queue, not a blanket verdict."
    }
  ],
  tts_script:
    "Selective filings and active charts are shaping today's market wrap. Use this as a research queue, not a blanket verdict."
};

export default samplePayload;
