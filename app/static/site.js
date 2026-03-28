const WATCHLIST_KEY = "opportunity-radar-watchlist";

const FACT_LABELS = {
  NameOfTheCompany: "Company",
  NameOfThePerson: "Person",
  CategoryOfPerson: "Category",
  SecuritiesAcquiredOrDisposedTransactionType: "Transaction",
  ModeOfAcquisitionOrDisposal: "Mode",
  TypeOfInstrument: "Instrument",
  SecuritiesAcquiredOrDisposedNumberOfSecurity: "Quantity",
  SecuritiesAcquiredOrDisposedValueOfSecurity: "Value",
  SecuritiesHeldPostAcquistionOrDisposalNumberOfSecurity: "Post-holding Shares",
  SecuritiesHeldPostAcquistionOrDisposalPercentageOfShareholding: "Post-holding %",
  DateOfIntimationToCompany: "Intimation Date",
  ExchangeOnWhichTheTradeWasExecuted: "Exchange",
};

export function escapeHtml(value) {
  return String(value ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/\"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

export async function fetchJSON(url, options = {}) {
  const response = await fetch(url, options);
  if (!response.ok) {
    const detail = await response.text().catch(() => "");
    throw new Error(detail || `Request failed: ${response.status}`);
  }
  return response.json();
}

export function readWatchlist() {
  try {
    const raw = localStorage.getItem(WATCHLIST_KEY);
    const parsed = raw ? JSON.parse(raw) : [];
    return Array.isArray(parsed)
      ? parsed.map((item) => String(item || "").trim().toUpperCase()).filter(Boolean).slice(0, 12)
      : [];
  } catch {
    return [];
  }
}

export function saveWatchlist(items) {
  localStorage.setItem(WATCHLIST_KEY, JSON.stringify(items.slice(0, 12)));
}

export function addWatchlistSymbol(items, symbol) {
  const normalized = String(symbol || "").trim().toUpperCase();
  if (!normalized) {
    return items;
  }
  if (items.includes(normalized)) {
    return items;
  }
  const next = [normalized, ...items].slice(0, 12);
  saveWatchlist(next);
  return next;
}

export function removeWatchlistSymbol(items, symbol) {
  const normalized = String(symbol || "").trim().toUpperCase();
  const next = items.filter((item) => item !== normalized);
  saveWatchlist(next);
  return next;
}

export function toggleWatchlistSymbol(items, symbol) {
  const normalized = String(symbol || "").trim().toUpperCase();
  return items.includes(normalized) ? removeWatchlistSymbol(items, normalized) : addWatchlistSymbol(items, normalized);
}

export function number(value) {
  return new Intl.NumberFormat("en-IN").format(Number(value || 0));
}

export function formatPercent(value, digits = 1) {
  const numeric = Number(value);
  if (!Number.isFinite(numeric)) {
    return "-";
  }
  return `${numeric.toFixed(digits)}%`;
}

export function formatDate(value) {
  if (!value) {
    return "Unknown date";
  }
  const date = /^\d{4}-\d{2}-\d{2}$/.test(value) ? new Date(`${value}T00:00:00`) : new Date(value);
  if (Number.isNaN(date.getTime())) {
    return String(value);
  }
  return new Intl.DateTimeFormat("en-IN", {
    day: "2-digit",
    month: "short",
    year: "numeric",
  }).format(date);
}

export function formatDateShort(value) {
  if (!value) {
    return "-";
  }
  const date = /^\d{4}-\d{2}-\d{2}$/.test(value) ? new Date(`${value}T00:00:00`) : new Date(value);
  if (Number.isNaN(date.getTime())) {
    return String(value);
  }
  return new Intl.DateTimeFormat("en-IN", {
    day: "2-digit",
    month: "short",
  }).format(date);
}

export function formatDateTime(value) {
  if (!value) {
    return "-";
  }
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return String(value);
  }
  return new Intl.DateTimeFormat("en-IN", {
    day: "2-digit",
    month: "short",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  }).format(date);
}

export function formatToday() {
  return new Intl.DateTimeFormat("en-IN", {
    weekday: "long",
    day: "2-digit",
    month: "short",
  }).format(new Date());
}

export function truncateText(text, limit = 140) {
  const cleaned = String(text || "").replace(/\s+/g, " ").trim();
  if (cleaned.length <= limit) {
    return cleaned;
  }
  return `${cleaned.slice(0, limit - 1).trimEnd()}...`;
}

export function directionClass(value) {
  return value === "bullish" || value === "bearish" ? value : "neutral";
}

export function headlineFor(signal) {
  return signal?.llm_explanation?.signal_label || signal?.primary_reason || "Market signal";
}

export function summaryFor(signal) {
  return signal?.llm_explanation?.summary || signal?.primary_reason || "Rule-based signal";
}

export function whyItMatters(signal) {
  return signal?.llm_explanation?.why_it_matters || signal?.reasons?.[1] || signal?.reasons?.[0] || "Keep an eye on this filing.";
}

export function riskNoteFor(signal) {
  return signal?.llm_explanation?.risk_note || "Treat this as a research trigger, not a trade instruction.";
}

export function confidenceFor(signal) {
  return signal?.llm_explanation?.confidence ?? signal?.confidence ?? 0;
}

export function chartHeadlineFor(signal) {
  return signal?.llm_explanation?.signal_label || signal?.pattern_label || "Chart pattern";
}

export function chartSummaryFor(signal) {
  return signal?.llm_explanation?.summary || signal?.pattern_label || "Chart pattern signal";
}

export function chartWhyItMatters(signal) {
  return signal?.llm_explanation?.why_it_matters || signal?.reasons?.[0] || "Watch how price behaves around the nearby levels.";
}

export function chartRiskNoteFor(signal) {
  return signal?.llm_explanation?.risk_note || "Treat this as a research trigger, not a trading instruction.";
}

export function coverageSummary(coverage) {
  if (!coverage) {
    return "No fresh disclosure was collected for this stock in the current run.";
  }

  const count = Number(coverage.event_count || 0);
  const label = count === 1 ? "disclosure" : "disclosures";
  const latest = coverage.latest_headline
    ? `Latest note: ${truncateText(coverage.latest_headline, 96)}`
    : "The stock appeared in the raw exchange feed.";
  return `${count} raw ${label} found. ${latest}`;
}

export function quoteSummary(profile, symbol = "") {
  const quote = profile?.quote;
  if (!quote) {
    return `${symbol || "This stock"} does not have a live quote snapshot right now.`;
  }
  const price = typeof quote.last_price === "number" ? `${quote.last_price.toFixed(2)} INR` : "Price unavailable";
  const move = typeof quote.percent_change === "number"
    ? `${quote.percent_change >= 0 ? "+" : ""}${quote.percent_change.toFixed(2)}% today`
    : "Change unavailable";
  return `${price}. ${move}. ${quote.industry || quote.basic_industry || "Industry unavailable"}.`;
}

export function badge(text, tone = "neutral") {
  return `<span class="pill ${escapeHtml(tone)}">${escapeHtml(text)}</span>`;
}

export function buildBriefUrl(symbol, runLabel = "") {
  const params = new URLSearchParams({ symbol: String(symbol || "").trim().toUpperCase() });
  if (runLabel) {
    params.set("run", runLabel);
  }
  return `/brief?${params.toString()}`;
}

export function renderEmptyState(message) {
  return `<div class="empty-state">${escapeHtml(message)}</div>`;
}

export function renderStatCard(label, value, note) {
  return `
    <article class="stat-card">
      <span class="eyebrow">${escapeHtml(label)}</span>
      <strong>${escapeHtml(String(value))}</strong>
      <p>${escapeHtml(note)}</p>
    </article>
  `;
}

export function firstLevel(levels = []) {
  const item = Array.isArray(levels) ? levels.find((entry) => entry && entry.price != null) : null;
  return item ? Number(item.price) : null;
}

export function backtestSummary(signal) {
  const backtest = signal?.backtest || {};
  const success = backtest?.success_rate;
  const sample = Number(backtest?.sample_size || 0);
  const horizon = Number(backtest?.horizon_days || 0);
  if (success == null || !sample) {
    return "Backtest history is still thin on this setup.";
  }
  return `${formatPercent(success)} success over ${horizon || 7} trading days across ${number(sample)} prior occurrences.`;
}

export function signalBySymbol(bundle, symbol) {
  const normalized = String(symbol || "").trim().toUpperCase();
  return Array.isArray(bundle?.signals) ? bundle.signals.find((item) => item.symbol === normalized) || null : null;
}

export function coverageBySymbol(bundle, symbol) {
  const normalized = String(symbol || "").trim().toUpperCase();
  const map = bundle?.coverage?.by_symbol;
  return map && typeof map === "object" ? map[normalized] || null : null;
}

export function sortSignals(bundle, watchlist = []) {
  const items = Array.isArray(bundle?.signals) ? [...bundle.signals] : [];
  const saved = new Set(watchlist.map((item) => String(item || "").trim().toUpperCase()));
  return items.sort((left, right) => {
    const watchGap = Number(saved.has(right.symbol)) - Number(saved.has(left.symbol));
    if (watchGap !== 0) {
      return watchGap;
    }
    const scoreGap = Math.abs(Number(right.score || 0)) - Math.abs(Number(left.score || 0));
    if (scoreGap !== 0) {
      return scoreGap;
    }
    return Number(confidenceFor(right) || 0) - Number(confidenceFor(left) || 0);
  });
}

export function topSignals(bundle, watchlist = [], limit = 6) {
  return sortSignals(bundle, watchlist).slice(0, limit);
}

export function attachmentHighlights(signal) {
  if (Array.isArray(signal?.attachment_highlights) && signal.attachment_highlights.length) {
    return signal.attachment_highlights.slice(0, 6);
  }

  const lines = [];
  for (const evidence of signal?.evidence || []) {
    for (const line of evidence?.attachment_parse?.highlights || []) {
      if (!lines.includes(line)) {
        lines.push(line);
      }
      if (lines.length >= 6) {
        return lines;
      }
    }
  }
  return lines;
}

export function factPairs(signal, limit = 8) {
  const pairs = [];
  const seen = new Set();
  for (const evidence of signal?.evidence || []) {
    const facts = evidence?.attachment_parse?.facts || {};
    for (const [key, value] of Object.entries(facts)) {
      if (!value) {
        continue;
      }
      const label = FACT_LABELS[key] || key.replace(/([a-z])([A-Z])/g, "$1 $2");
      const token = `${label}|${value}`;
      if (seen.has(token)) {
        continue;
      }
      seen.add(token);
      pairs.push([label, value]);
      if (pairs.length >= limit) {
        return pairs;
      }
    }
  }
  return pairs;
}

export function stockState(bundle, symbol, profile = null) {
  const normalized = String(symbol || "").trim().toUpperCase();
  const signal = signalBySymbol(bundle, normalized);
  const coverage = coverageBySymbol(bundle, normalized);

  if (signal) {
    return {
      symbol: normalized,
      signal,
      coverage,
      profile,
      mode: directionClass(signal.direction),
      title: signal.symbol,
      company: signal.company || profile?.master?.company || normalized,
      summary: whyItMatters(signal),
      note: headlineFor(signal),
    };
  }

  return {
    symbol: normalized,
    signal: null,
    coverage,
    profile,
    mode: "neutral",
    title: normalized,
    company: coverage?.company || profile?.master?.company || normalized,
    summary: coverage ? coverageSummary(coverage) : quoteSummary(profile, normalized),
    note: coverage ? "Tracked but quiet" : "No fresh activity",
  };
}

export function renderSignalCard(signal, options = {}) {
  const watchlist = options.watchlist || [];
  const runLabel = options.runLabel || "";
  const tone = directionClass(signal.direction);
  const inWatchlist = watchlist.includes(signal.symbol);
  const footerNote = inWatchlist ? "In your watchlist" : signal.direction === "bearish" ? "Needs caution" : "Worth opening";

  return `
    <article class="signal-card ${escapeHtml(tone)}">
      <div class="signal-head">
        <div>
          <p class="eyebrow">${escapeHtml(headlineFor(signal))}</p>
          <h3>${escapeHtml(signal.symbol)}</h3>
          <p class="card-company">${escapeHtml(signal.company || "Unknown company")}</p>
        </div>
        <div class="tag-row">
          ${badge(signal.direction || "neutral", tone)}
          ${badge(`${number(signal.score)} score`, tone)}
          ${badge(`${number(confidenceFor(signal))}% confidence`, tone)}
        </div>
      </div>
      <p class="signal-summary">${escapeHtml(summaryFor(signal))}</p>
      <p class="signal-text">${escapeHtml(truncateText(whyItMatters(signal), 180))}</p>
      <div class="card-footer">
        <span class="summary-pill">${escapeHtml(footerNote)}</span>
        <div class="button-row">
          <a class="btn primary small" href="${buildBriefUrl(signal.symbol, runLabel)}">Open Brief</a>
          <button type="button" class="btn ghost small js-watchlist-toggle" data-watchlist-toggle="${escapeHtml(signal.symbol)}">${inWatchlist ? "Saved" : "Save"}</button>
        </div>
      </div>
    </article>
  `;
}

export function renderChartSignalCard(signal, options = {}) {
  const watchlist = options.watchlist || [];
  const runLabel = options.runLabel || "";
  const tone = directionClass(signal.direction);
  const inWatchlist = watchlist.includes(signal.symbol);
  const support = firstLevel(signal.support_levels);
  const resistance = firstLevel(signal.resistance_levels);
  const backtest = signal.backtest || {};
  const family = String(signal.pattern_family || "pattern").replace(/_/g, " ");

  return `
    <article class="signal-card chart-signal-card ${escapeHtml(tone)}">
      <div class="signal-head">
        <div>
          <p class="eyebrow">${escapeHtml(chartHeadlineFor(signal))}</p>
          <h3>${escapeHtml(signal.symbol)}</h3>
          <p class="card-company">${escapeHtml(signal.company || "Unknown company")}</p>
        </div>
        <div class="tag-row">
          ${badge(signal.direction || "neutral", tone)}
          ${badge(family, tone)}
          ${badge(signal.timeframe || "1d", "neutral")}
        </div>
      </div>
      <p class="signal-summary">${escapeHtml(chartSummaryFor(signal))}</p>
      <div class="chart-meta-grid">
        <div class="chart-meta-card">
          <span class="eyebrow">Support</span>
          <strong>${support != null ? `${support.toFixed(2)} INR` : "Not mapped"}</strong>
        </div>
        <div class="chart-meta-card">
          <span class="eyebrow">Resistance</span>
          <strong>${resistance != null ? `${resistance.toFixed(2)} INR` : "Not mapped"}</strong>
        </div>
        <div class="chart-meta-card">
          <span class="eyebrow">7D Success</span>
          <strong>${backtest?.success_rate != null ? formatPercent(backtest.success_rate) : "Low sample"}</strong>
        </div>
        <div class="chart-meta-card">
          <span class="eyebrow">Sample</span>
          <strong>${number(backtest?.sample_size || 0)}</strong>
        </div>
      </div>
      <p class="signal-text">${escapeHtml(chartWhyItMatters(signal))}</p>
      <div class="card-footer">
        <span class="summary-pill">${escapeHtml(backtestSummary(signal))}</span>
        <div class="button-row">
          <a class="btn primary small" href="${buildBriefUrl(signal.symbol, runLabel)}">Open Brief</a>
          <button type="button" class="btn ghost small js-watchlist-toggle" data-watchlist-toggle="${escapeHtml(signal.symbol)}">${inWatchlist ? "Saved" : "Save"}</button>
        </div>
      </div>
    </article>
  `;
}

export function renderWatchCard(entry, options = {}) {
  const runLabel = options.runLabel || "";
  const inWatchlist = (options.watchlist || []).includes(entry.symbol);
  const tone = entry.signal ? directionClass(entry.signal.direction) : "neutral";
  const quietLabel = entry.signal ? headlineFor(entry.signal) : entry.note;
  const meta = entry.signal
    ? `${number(confidenceFor(entry.signal))}% confidence`
    : entry.coverage
      ? `${number(entry.coverage.event_count || 0)} raw events`
      : entry.profile?.quote?.last_price != null
        ? `${entry.profile.quote.last_price.toFixed(2)} INR`
        : "No quote snapshot";

  return `
    <article class="watch-card ${escapeHtml(tone)}">
      <div class="signal-head">
        <div>
          <p class="eyebrow">${escapeHtml(quietLabel)}</p>
          <h3>${escapeHtml(entry.symbol)}</h3>
          <p class="card-company">${escapeHtml(entry.company || entry.symbol)}</p>
        </div>
        <div class="tag-row">
          ${badge(meta, tone)}
          ${entry.signal ? badge(entry.signal.direction || "neutral", tone) : badge("quiet", "neutral")}
        </div>
      </div>
      <p class="signal-text">${escapeHtml(truncateText(entry.summary, 170))}</p>
      <div class="card-footer">
        <span class="summary-pill">${escapeHtml(inWatchlist ? "Saved to watchlist" : "Not saved")}</span>
        <div class="button-row">
          <a class="btn primary small" href="${buildBriefUrl(entry.symbol, runLabel)}">Open Brief</a>
          <button type="button" class="btn ghost small js-watchlist-remove" data-watchlist-remove="${escapeHtml(entry.symbol)}">Remove</button>
        </div>
      </div>
    </article>
  `;
}

export function renderEvidenceCard(item) {
  const attachmentList = (item?.attachment_parse?.highlights || [])
    .slice(0, 3)
    .map((line) => `<li>${escapeHtml(line)}</li>`)
    .join("");

  return `
    <article class="detail-card evidence-card">
      <div class="signal-head compact">
        <div>
          <p class="eyebrow">${escapeHtml(item.event_type || "Event")}</p>
          <h4>${escapeHtml(item.headline || item.reason || "Disclosure")}</h4>
        </div>
        <div class="tag-row">
          ${badge(formatDateShort(item.event_date || ""))}
          ${badge(`${number(item.score || 0)} score`)}
        </div>
      </div>
      <p class="signal-text">${escapeHtml(truncateText(item.raw_text || item.reason || "", 220))}</p>
      ${attachmentList ? `<ul class="detail-list">${attachmentList}</ul>` : ""}
      <div class="button-row">
        ${item.attachment_url ? `<a class="btn ghost small" href="${escapeHtml(item.attachment_url)}" target="_blank" rel="noreferrer">Open Filing</a>` : ""}
        ${item.source_url ? `<a class="btn ghost small" href="${escapeHtml(item.source_url)}" target="_blank" rel="noreferrer">Exchange Page</a>` : ""}
      </div>
    </article>
  `;
}

export function renderFactGrid(signal) {
  const facts = factPairs(signal);
  if (!facts.length) {
    return renderEmptyState("No structured facts were extracted for this signal yet.");
  }
  return facts
    .map(
      ([label, value]) => `
        <div class="fact-card">
          <span class="eyebrow">${escapeHtml(label)}</span>
          <strong>${escapeHtml(String(value))}</strong>
        </div>
      `,
    )
    .join("");
}

export function renderHighlightList(signal) {
  const highlights = attachmentHighlights(signal);
  if (!highlights.length) {
    return renderEmptyState("No attachment highlights were parsed for this signal yet.");
  }
  return `<ul class="detail-list">${highlights.map((line) => `<li>${escapeHtml(line)}</li>`).join("")}</ul>`;
}

export function renderRunOptions(selectEl, runs, selectedRun = "") {
  if (!selectEl) {
    return;
  }
  const items = Array.isArray(runs) ? runs : [];
  selectEl.innerHTML = items.length
    ? items.map((run) => `<option value="${escapeHtml(run.run_label)}">${escapeHtml(run.run_label)}</option>`).join("")
    : '<option value="">No runs yet</option>';
  if (selectedRun) {
    selectEl.value = selectedRun;
  }
}

export function runLabelFromQuery() {
  const params = new URLSearchParams(window.location.search);
  return params.get("run") || "";
}

export function symbolFromQuery() {
  const params = new URLSearchParams(window.location.search);
  return (params.get("symbol") || "").trim().toUpperCase();
}

export function updateQuery(params) {
  const url = new URL(window.location.href);
  for (const [key, value] of Object.entries(params)) {
    if (value) {
      url.searchParams.set(key, value);
    } else {
      url.searchParams.delete(key);
    }
  }
  window.history.replaceState({}, "", url);
}

export async function loadBundle(runLabel = "") {
  return fetchJSON(runLabel ? `/api/signals/${encodeURIComponent(runLabel)}` : "/api/signals/latest");
}

export async function loadChartBundle(runLabel = "") {
  return fetchJSON(runLabel ? `/api/chart-signals/${encodeURIComponent(runLabel)}` : "/api/chart-signals/latest");
}

export async function loadVideoBundle(options = {}) {
  const params = new URLSearchParams();
  if (options.runLabel) {
    params.set("run_label", options.runLabel);
  }
  if (options.chartRunLabel) {
    params.set("chart_run_label", options.chartRunLabel);
  }
  if (options.disclosureLimit) {
    params.set("disclosure_limit", String(options.disclosureLimit));
  }
  if (options.chartLimit) {
    params.set("chart_limit", String(options.chartLimit));
  }
  const query = params.toString() ? `?${params.toString()}` : "";
  return fetchJSON(`/api/video/latest${query}`);
}

export async function loadRuns() {
  return fetchJSON("/api/runs");
}

export async function loadChartRuns() {
  return fetchJSON("/api/chart-runs");
}

export async function loadChartRunStatus() {
  return fetchJSON("/api/chart-run/status");
}

export async function loadUniverse(limit = 5000) {
  return fetchJSON(`/api/universe?limit=${limit}`);
}

export async function loadStock(symbol, runLabel = "") {
  const query = runLabel ? `?run_label=${encodeURIComponent(runLabel)}` : "";
  return fetchJSON(`/api/stocks/${encodeURIComponent(String(symbol || "").trim().toUpperCase())}${query}`);
}

export async function loadStockChart(symbol, runLabel = "") {
  const params = new URLSearchParams();
  if (runLabel) {
    params.set("run_label", runLabel);
  }
  const query = params.toString() ? `?${params.toString()}` : "";
  return fetchJSON(`/api/stocks/${encodeURIComponent(String(symbol || "").trim().toUpperCase())}/chart${query}`);
}

export async function triggerPipelineRun() {
  return fetchJSON("/api/run", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      days_back: 1,
      include_attachments: true,
      include_explanations: true,
    }),
  });
}

export async function triggerChartRun(options = {}) {
  return fetchJSON("/api/chart-run", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      include_explanations: options.include_explanations ?? true,
      explanation_limit: options.explanation_limit ?? 12,
      symbol_limit: options.symbol_limit ?? null,
      force_refresh: options.force_refresh ?? false,
    }),
  });
}

export function renderInlinePriceChart(candles = [], levels = {}) {
  const items = Array.isArray(candles) ? candles.filter((item) => item && item.close != null) : [];
  if (items.length < 2) {
    return renderEmptyState("Not enough candle history to draw the chart yet.");
  }

  const width = 760;
  const height = 260;
  const padding = 18;
  const prices = items.map((item) => Number(item.close));
  const levelPrices = [
    ...(levels?.support || []).map((item) => Number(item.price)).filter((value) => Number.isFinite(value)),
    ...(levels?.resistance || []).map((item) => Number(item.price)).filter((value) => Number.isFinite(value)),
  ];
  const high = Math.max(...prices, ...(levelPrices.length ? levelPrices : [Math.max(...prices)]));
  const low = Math.min(...prices, ...(levelPrices.length ? levelPrices : [Math.min(...prices)]));
  const range = Math.max(high - low, high * 0.02);
  const xStep = (width - padding * 2) / Math.max(items.length - 1, 1);
  const yFor = (value) => height - padding - (((Number(value) - low) / range) * (height - padding * 2));
  const points = items.map((item, index) => `${(padding + (index * xStep)).toFixed(2)},${yFor(item.close).toFixed(2)}`).join(" ");
  const rising = prices[prices.length - 1] >= prices[0];
  const lineColor = rising ? "#0e8a64" : "#c65f45";

  const zoneLines = [
    ...(levels?.support || []).slice(0, 2).map((item) => ({ ...item, tone: "#0e8a64" })),
    ...(levels?.resistance || []).slice(0, 2).map((item) => ({ ...item, tone: "#c65f45" })),
  ].map((item) => `
      <line x1="${padding}" y1="${yFor(item.price).toFixed(2)}" x2="${width - padding}" y2="${yFor(item.price).toFixed(2)}"
        stroke="${item.tone}" stroke-opacity="0.28" stroke-dasharray="8 8" />
      <text x="${width - padding}" y="${(yFor(item.price) - 6).toFixed(2)}" text-anchor="end"
        fill="${item.tone}" font-size="11" font-family="'IBM Plex Mono', monospace">${Number(item.price).toFixed(2)}</text>
    `).join("");

  return `
    <svg class="price-svg" viewBox="0 0 ${width} ${height}" role="img" aria-label="Recent price trend">
      <defs>
        <linearGradient id="chartAreaGradient" x1="0%" x2="0%" y1="0%" y2="100%">
          <stop offset="0%" stop-color="${lineColor}" stop-opacity="0.28"></stop>
          <stop offset="100%" stop-color="${lineColor}" stop-opacity="0"></stop>
        </linearGradient>
      </defs>
      <rect x="0" y="0" width="${width}" height="${height}" rx="22" fill="rgba(255,255,255,0.58)"></rect>
      ${zoneLines}
      <polyline
        fill="none"
        stroke="${lineColor}"
        stroke-width="3.2"
        stroke-linecap="round"
        stroke-linejoin="round"
        points="${points}"
      ></polyline>
      <polyline
        fill="url(#chartAreaGradient)"
        stroke="none"
        points="${points} ${width - padding},${height - padding} ${padding},${height - padding}"
      ></polyline>
    </svg>
  `;
}
