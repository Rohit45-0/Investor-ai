import {
  attachmentHighlights,
  backtestSummary,
  badge,
  chartHeadlineFor,
  chartRiskNoteFor,
  chartSummaryFor,
  chartWhyItMatters,
  buildBriefUrl,
  confidenceFor,
  coverageSummary,
  escapeHtml,
  factPairs,
  firstLevel,
  formatDate,
  formatPercent,
  headlineFor,
  loadStock,
  loadStockChart,
  number,
  quoteSummary,
  readWatchlist,
  renderInlinePriceChart,
  renderEmptyState,
  renderEvidenceCard,
  riskNoteFor,
  summaryFor,
  symbolFromQuery,
  toggleWatchlistSymbol,
  updateQuery,
  whyItMatters,
  runLabelFromQuery,
  directionClass,
} from "/static/site.js";

const heroRoot = document.getElementById("briefHero");
const chartRoot = document.getElementById("briefChart");
const summaryRoot = document.getElementById("briefSummary");
const highlightsRoot = document.getElementById("briefHighlights");
const factsRoot = document.getElementById("briefFacts");

const state = {
  symbol: symbolFromQuery(),
  runLabel: runLabelFromQuery(),
  stock: null,
  chart: null,
  watchlist: readWatchlist(),
};

function renderHero() {
  const payload = state.stock;
  if (!payload) {
    heroRoot.innerHTML = renderEmptyState("Choose a stock from the Daily Radar to open its brief.");
    return;
  }

  const signal = payload.signal;
  const coverage = payload.coverage;
  const quote = payload.quote;
  const company = payload.master?.company || quote?.company || coverage?.company || state.symbol;
  const tone = signal ? directionClass(signal.direction) : "neutral";
  const inWatchlist = state.watchlist.includes(state.symbol);

  heroRoot.innerHTML = `
    <div class="brief-hero-grid">
      <div>
        <p class="eyebrow">Stock Brief</p>
        <h1>${escapeHtml(state.symbol)}</h1>
        <p class="card-company big">${escapeHtml(company)}</p>
        <p class="lead-copy">${escapeHtml(signal ? summaryFor(signal) : coverage ? coverageSummary(coverage) : quoteSummary(payload, state.symbol))}</p>
        <div class="tag-row spread">
          ${signal ? badge(signal.direction || "neutral", tone) : badge("quiet", "neutral")}
          ${signal ? badge(`${number(signal.score)} score`, tone) : ""}
          ${signal ? badge(`${number(confidenceFor(signal))}% confidence`, tone) : ""}
          ${quote?.last_price != null ? badge(`${quote.last_price.toFixed(2)} INR`, "neutral") : ""}
        </div>
      </div>
      <div class="hero-actions-stack">
        <a class="btn secondary" href="/radar">Back to Radar</a>
        <a class="btn ghost" href="/watchlist">My Watchlist</a>
        <button type="button" id="briefWatchlistButton" class="btn primary">${inWatchlist ? "Remove From Watchlist" : "Save To Watchlist"}</button>
        <div class="run-badge">${escapeHtml(payload.run_label || state.runLabel || "latest")}</div>
      </div>
    </div>
  `;

  const watchlistButton = document.getElementById("briefWatchlistButton");
  watchlistButton?.addEventListener("click", () => {
    state.watchlist = toggleWatchlistSymbol(state.watchlist, state.symbol);
    renderHero();
  });
}

function renderSummary() {
  const payload = state.stock;
  if (!payload) {
    summaryRoot.innerHTML = renderEmptyState("No stock selected.");
    return;
  }

  if (!payload.signal) {
    summaryRoot.innerHTML = `
      <div class="detail-stack">
        <article class="detail-card">
          <h3>What changed</h3>
          <p>${escapeHtml(payload.coverage ? coverageSummary(payload.coverage) : quoteSummary(payload, state.symbol))}</p>
        </article>
        <article class="detail-card">
          <h3>Why this is still shown</h3>
          <p>${escapeHtml(
            payload.coverage
              ? "This stock appeared in the raw exchange disclosures, but it did not cross the threshold to become a top ranked alert."
              : "This stock did not have a fresh disclosure in the latest run, but the watchlist still keeps it visible with baseline market context."
          )}</p>
        </article>
      </div>
    `;
    return;
  }

  const evidence = (payload.signal.evidence || []).slice(0, 4).map((item) => renderEvidenceCard(item)).join("");
  summaryRoot.innerHTML = `
    <div class="detail-stack">
      <article class="detail-card">
        <h3>What changed</h3>
        <p>${escapeHtml(whyItMatters(payload.signal))}</p>
      </article>
      <article class="detail-card">
        <h3>Risk note</h3>
        <p>${escapeHtml(riskNoteFor(payload.signal))}</p>
      </article>
      <div class="evidence-grid">
        ${evidence || renderEmptyState("No evidence cards available for this alert.")}
      </div>
    </div>
  `;
}

function renderChartPanel() {
  const payload = state.chart;
  if (!payload) {
    chartRoot.innerHTML = renderEmptyState("Chart context is not available for this stock yet.");
    return;
  }

  const summary = payload.summary;
  const chartStatus = payload.chart_status || {};
  const chartRunLabel = payload.run_label || "";
  const timeframe = summary?.timeframe || "1d";
  const candles = payload.candles?.[timeframe] || payload.candles?.["1d"] || [];
  const levelSet = payload.levels?.[timeframe] || payload.levels?.["1d"] || { support: [], resistance: [] };

  if (!summary) {
    const reason = chartStatus.reason === "illiquid"
      ? "This name is tracked, but the recent traded-value profile is below the chart-radar liquidity floor."
      : chartStatus.reason === "insufficient_history"
        ? "This name does not have enough price history in cache yet for the chart-pattern engine."
        : "There is no high-conviction chart setup on this stock right now.";
    chartRoot.innerHTML = `
      <div class="detail-stack">
        <article class="detail-card">
          <h3>Chart status</h3>
          <p>${escapeHtml(reason)}</p>
        </article>
        <article class="detail-card">
          <h3>Latest run</h3>
          <p>${escapeHtml(chartRunLabel || "Chart Radar has not stored a dedicated run for this stock yet.")}</p>
        </article>
        <div class="detail-card chart-figure-card">
          ${renderInlinePriceChart(candles, levelSet)}
        </div>
      </div>
    `;
    return;
  }

  const support = firstLevel(summary.support_levels);
  const resistance = firstLevel(summary.resistance_levels);
  const topPatterns = (payload.patterns || []).slice(0, 3)
    .map((item) => `<li><strong>${escapeHtml(item.pattern_label)}</strong> on ${escapeHtml(item.timeframe)} <span>${escapeHtml(item.direction)}</span></li>`)
    .join("");

  chartRoot.innerHTML = `
    <div class="detail-stack">
      <article class="detail-card chart-summary-card ${escapeHtml(directionClass(summary.direction))}">
        <div class="section-head compact">
          <div>
            <p class="eyebrow">${escapeHtml(chartHeadlineFor(summary))}</p>
            <h3>${escapeHtml(summary.pattern_label)}</h3>
          </div>
          <div class="tag-row">
            ${badge(summary.direction || "neutral", directionClass(summary.direction))}
            ${badge(summary.timeframe || "1d")}
            ${badge(`${number(summary.score)} score`, directionClass(summary.direction))}
            ${badge(`${number(summary.confidence)}% confidence`, directionClass(summary.direction))}
          </div>
        </div>
        <p class="detail-text">${escapeHtml(chartSummaryFor(summary))}</p>
        <p class="detail-text">${escapeHtml(chartWhyItMatters(summary))}</p>
        <p class="detail-text">${escapeHtml(chartRiskNoteFor(summary))}</p>
      </article>
      <div class="chart-metric-grid">
        <article class="fact-card">
          <span class="eyebrow">Support</span>
          <strong>${support != null ? `${support.toFixed(2)} INR` : "Not mapped"}</strong>
        </article>
        <article class="fact-card">
          <span class="eyebrow">Resistance</span>
          <strong>${resistance != null ? `${resistance.toFixed(2)} INR` : "Not mapped"}</strong>
        </article>
        <article class="fact-card">
          <span class="eyebrow">7D Success</span>
          <strong>${summary.backtest?.success_rate != null ? formatPercent(summary.backtest.success_rate) : "Low sample"}</strong>
        </article>
        <article class="fact-card">
          <span class="eyebrow">Sample Size</span>
          <strong>${number(summary.backtest?.sample_size || 0)}</strong>
        </article>
      </div>
      <div class="detail-card chart-figure-card">
        ${renderInlinePriceChart(candles, levelSet)}
      </div>
      <div class="detail-stack split-detail">
        <article class="detail-card">
          <h3>Backtest context</h3>
          <p>${escapeHtml(backtestSummary(summary))}</p>
          <p>${escapeHtml(summary.backtest?.fallback_baseline ? `Fallback ${summary.backtest.fallback_baseline.pattern_family} baseline: ${formatPercent(summary.backtest.fallback_baseline.success_rate)} over ${number(summary.backtest.fallback_baseline.sample_size)} samples.` : "This setup uses stock-specific outcomes first, then falls back to family baselines only when sample sizes are thin.")}</p>
        </article>
        <article class="detail-card">
          <h3>Other active patterns</h3>
          ${topPatterns ? `<ul class="detail-list">${topPatterns}</ul>` : `<p>${escapeHtml("No secondary chart patterns are active right now.")}</p>`}
        </article>
      </div>
    </div>
  `;
}

function renderHighlights() {
  const payload = state.stock;
  if (!payload) {
    highlightsRoot.innerHTML = renderEmptyState("No stock selected.");
    return;
  }

  if (!payload.signal) {
    highlightsRoot.innerHTML = `
      <ul class="detail-list">
        <li>${escapeHtml(payload.coverage?.latest_headline || "No filing headline available for this stock in the current run.")}</li>
        <li>${escapeHtml(payload.quote?.industry || payload.quote?.basic_industry || payload.master?.series || "Industry unavailable")}</li>
        <li>${escapeHtml(payload.quote?.last_update_time ? `Quote updated ${payload.quote.last_update_time}` : "Live quote timing unavailable")}</li>
      </ul>
    `;
    return;
  }

  const highlights = attachmentHighlights(payload.signal);
  highlightsRoot.innerHTML = highlights.length
    ? `<ul class="detail-list">${highlights.map((line) => `<li>${escapeHtml(line)}</li>`).join("")}</ul>`
    : renderEmptyState("No attachment highlights were parsed for this signal yet.");
}

function renderFacts() {
  const payload = state.stock;
  if (!payload) {
    factsRoot.innerHTML = renderEmptyState("No stock selected.");
    return;
  }

  if (payload.signal) {
    const facts = factPairs(payload.signal, 8);
    factsRoot.innerHTML = facts.length
      ? facts.map(([label, value]) => `
          <article class="fact-card">
            <span class="eyebrow">${escapeHtml(label)}</span>
            <strong>${escapeHtml(String(value))}</strong>
          </article>
        `).join("")
      : renderEmptyState("No structured facts were extracted for this alert.");
    return;
  }

  factsRoot.innerHTML = [
    payload.master?.listing_date ? `<article class="fact-card"><span class="eyebrow">Listing</span><strong>${escapeHtml(payload.master.listing_date)}</strong></article>` : "",
    payload.quote?.industry ? `<article class="fact-card"><span class="eyebrow">Industry</span><strong>${escapeHtml(payload.quote.industry)}</strong></article>` : "",
    payload.quote?.market_status ? `<article class="fact-card"><span class="eyebrow">Market Status</span><strong>${escapeHtml(payload.quote.market_status)}</strong></article>` : "",
    payload.quote?.percent_change != null ? `<article class="fact-card"><span class="eyebrow">Daily Move</span><strong>${escapeHtml(`${payload.quote.percent_change >= 0 ? "+" : ""}${payload.quote.percent_change.toFixed(2)}%`)}</strong></article>` : "",
  ].filter(Boolean).join("") || renderEmptyState("No baseline stock facts are available.");
}

async function bootstrap() {
  if (!state.symbol) {
    heroRoot.innerHTML = `
      <div class="empty-state">
        Open a stock from the <a href="/radar">Daily Radar</a> or <a href="/watchlist">Watchlist</a> to see its brief.
      </div>
    `;
    chartRoot.innerHTML = renderEmptyState("No stock selected.");
    summaryRoot.innerHTML = renderEmptyState("No stock selected.");
    highlightsRoot.innerHTML = renderEmptyState("No stock selected.");
    factsRoot.innerHTML = renderEmptyState("No stock selected.");
    return;
  }

  try {
    const [stock, chart] = await Promise.all([
      loadStock(state.symbol, state.runLabel),
      loadStockChart(state.symbol).catch(() => null),
    ]);
    state.stock = stock;
    state.chart = chart;
    if (state.stock?.run_label && !state.runLabel) {
      state.runLabel = state.stock.run_label;
      updateQuery({ symbol: state.symbol, run: state.runLabel });
    }
    renderHero();
    renderChartPanel();
    renderSummary();
    renderHighlights();
    renderFacts();
  } catch (error) {
    const message = error instanceof Error ? error.message : "Could not load the stock brief.";
    heroRoot.innerHTML = renderEmptyState(message);
    chartRoot.innerHTML = renderEmptyState(message);
    summaryRoot.innerHTML = renderEmptyState(message);
    highlightsRoot.innerHTML = renderEmptyState(message);
    factsRoot.innerHTML = renderEmptyState(message);
  }
}

void bootstrap();
