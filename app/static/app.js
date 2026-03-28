
const heroPanel = document.getElementById("heroPanel");
const statusPill = document.getElementById("statusPill");
const runSelect = document.getElementById("runSelect");
const alertsToggleButton = document.getElementById("alertsToggleButton");
const runPipelineButton = document.getElementById("runPipelineButton");
const watchlistForm = document.getElementById("watchlistForm");
const watchlistInput = document.getElementById("watchlistInput");
const signalSuggestions = document.getElementById("signalSuggestions");
const quickAdd = document.getElementById("quickAdd");
const watchlistCards = document.getElementById("watchlistCards");
const watchlistCount = document.getElementById("watchlistCount");
const notificationCount = document.getElementById("notificationCount");
const notificationList = document.getElementById("notificationList");
const snapshotGrid = document.getElementById("snapshotGrid");
const pipelineMini = document.getElementById("pipelineMini");
const opportunityFeed = document.getElementById("opportunityFeed");
const riskFeed = document.getElementById("riskFeed");
const detailPanel = document.getElementById("detailPanel");
const detailSection = document.getElementById("detailSection");
const signalTape = document.getElementById("signalTape");
const toastStack = document.getElementById("toastStack");

const WATCHLIST_KEY = "opportunity-radar-watchlist";
const ALERTS_KEY = "opportunity-radar-alerts";

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

const state = {
  data: null,
  runs: [],
  universe: null,
  stockProfiles: {},
  selectedSymbol: null,
  watchlist: loadWatchlist(),
  alertsEnabled: loadAlertsPreference(),
  deliveredNotes: new Set(),
};

function loadWatchlist() {
  try {
    const raw = localStorage.getItem(WATCHLIST_KEY);
    const parsed = raw ? JSON.parse(raw) : [];
    return Array.isArray(parsed)
      ? parsed.map((item) => String(item || "").toUpperCase()).filter(Boolean).slice(0, 12)
      : [];
  } catch {
    return [];
  }
}

function saveWatchlist() {
  localStorage.setItem(WATCHLIST_KEY, JSON.stringify(state.watchlist.slice(0, 12)));
}

function loadAlertsPreference() {
  return localStorage.getItem(ALERTS_KEY) === "enabled";
}

function saveAlertsPreference(enabled) {
  localStorage.setItem(ALERTS_KEY, enabled ? "enabled" : "disabled");
}

function escapeHtml(value) {
  return String(value ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

function safeUrl(value) {
  if (!value) {
    return "#";
  }
  try {
    return new URL(value, window.location.origin).href;
  } catch {
    return "#";
  }
}

function number(value) {
  return new Intl.NumberFormat("en-IN").format(Number(value || 0));
}

function formatDate(value) {
  if (!value) {
    return "Unknown date";
  }
  const date = /^\d{4}-\d{2}-\d{2}$/.test(value) ? new Date(`${value}T00:00:00`) : new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }
  return new Intl.DateTimeFormat("en-IN", {
    day: "2-digit",
    month: "short",
    year: "numeric",
  }).format(date);
}

function formatToday() {
  return new Intl.DateTimeFormat("en-IN", {
    weekday: "long",
    day: "2-digit",
    month: "short",
  }).format(new Date());
}

function truncateText(text, limit = 120) {
  const cleaned = String(text || "").replace(/\s+/g, " ").trim();
  if (cleaned.length <= limit) {
    return cleaned;
  }
  return `${cleaned.slice(0, limit - 1).trimEnd()}...`;
}

function directionClass(value) {
  return value === "bullish" || value === "bearish" ? value : "neutral";
}

function headlineFor(signal) {
  return signal?.llm_explanation?.signal_label || signal?.primary_reason || "Market Signal";
}

function summaryFor(signal) {
  return signal?.llm_explanation?.summary || signal?.primary_reason || "Rule-based signal";
}

function whyItMatters(signal) {
  return signal?.llm_explanation?.why_it_matters || signal?.reasons?.[1] || signal?.reasons?.[0] || "Keep an eye on this filing.";
}

function riskNoteFor(signal) {
  return signal?.llm_explanation?.risk_note || "Treat this as a research trigger, not a trade instruction.";
}

function confidenceFor(signal) {
  return signal?.llm_explanation?.confidence ?? signal?.confidence ?? 0;
}

function getSignals() {
  return Array.isArray(state.data?.signals) ? state.data.signals : [];
}

function signalBySymbol(symbol) {
  const normalized = String(symbol || "").trim().toUpperCase();
  return getSignals().find((item) => item.symbol === normalized) || null;
}

function coverageMap() {
  const map = state.data?.coverage?.by_symbol;
  return map && typeof map === "object" ? map : {};
}

function universeItems() {
  return Array.isArray(state.universe?.items) ? state.universe.items : [];
}

function universeBySymbol(symbol) {
  const normalized = String(symbol || "").trim().toUpperCase();
  if (!normalized) {
    return null;
  }
  return universeItems().find((item) => item.symbol === normalized) || null;
}

function stockProfile(symbol) {
  const normalized = String(symbol || "").trim().toUpperCase();
  return normalized ? state.stockProfiles[normalized] || null : null;
}

function coverageForSymbol(symbol) {
  const normalized = String(symbol || "").trim().toUpperCase();
  return normalized ? coverageMap()[normalized] || null : null;
}

function availableSymbols() {
  if (Array.isArray(state.data?.coverage?.symbols) && state.data.coverage.symbols.length) {
    return state.data.coverage.symbols;
  }

  return getSignals().map((signal) => ({
    symbol: signal.symbol,
    company: signal.company,
    event_count: signal.event_count || 0,
    attachment_count: 0,
    has_ranked_signal: true,
  }));
}

function coverageSummary(coverage) {
  if (!coverage) {
    return "No raw disclosures or ranked signal in the latest run.";
  }

  const count = Number(coverage.event_count || 0);
  const label = count === 1 ? "disclosure" : "disclosures";
  const latest = coverage.latest_headline
    ? `Latest note: ${truncateText(coverage.latest_headline, 88)}`
    : "The stock appeared in the raw exchange feed.";
  return `${count} raw ${label} found. ${latest}`;
}

function quoteSummary(symbol) {
  const profile = stockProfile(symbol);
  const quote = profile?.quote;
  if (!quote) {
    return "We do not have a ranked signal for this stock, but quote data can still load when available.";
  }

  const price = typeof quote.last_price === "number" ? `${quote.last_price.toFixed(2)} INR` : "Price unavailable";
  const move =
    typeof quote.percent_change === "number"
      ? `${quote.percent_change >= 0 ? "+" : ""}${quote.percent_change.toFixed(2)}% today`
      : "Change unavailable";
  const industry = quote.industry || quote.basic_industry || profile?.master?.company || symbol;
  return `${industry}. ${price}. ${move}.`;
}

function attachmentHighlights(signal) {
  if (Array.isArray(signal?.attachment_highlights) && signal.attachment_highlights.length) {
    return signal.attachment_highlights.slice(0, 5);
  }

  const lines = [];
  for (const evidence of signal?.evidence || []) {
    for (const line of evidence?.attachment_parse?.highlights || []) {
      if (!lines.includes(line)) {
        lines.push(line);
      }
      if (lines.length >= 5) {
        return lines;
      }
    }
  }
  return lines;
}

function factPairs(signal, limit = 8) {
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

function chip(text, tone = "neutral") {
  return `<span class="signal-chip ${escapeHtml(tone)}">${escapeHtml(text)}</span>`;
}

function toneMeta(signal) {
  const direction = directionClass(signal?.direction);
  if (direction === "bullish") {
    return { mode: "glow", label: "Glow", title: `${signal.symbol} is glowing right now` };
  }
  if (direction === "bearish") {
    return { mode: "tension", label: "Tension", title: `${signal.symbol} feels tense` };
  }
  return { mode: "calm", label: "Calm", title: `${signal?.symbol || "This stock"} is quiet for now` };
}

function getLeadSignal() {
  const watchlistHit = state.watchlist.map((symbol) => signalBySymbol(symbol)).find(Boolean);
  if (watchlistHit) {
    return watchlistHit;
  }
  const opportunities = Array.isArray(state.data?.top_opportunities) ? state.data.top_opportunities : [];
  return opportunities[0] || getSignals()[0] || null;
}

function ensureSelectedSymbol() {
  const allSignals = getSignals();
  const allCoverage = availableSymbols();
  if (!allSignals.length && !allCoverage.length) {
    state.selectedSymbol = null;
    return;
  }

  if (
    state.selectedSymbol &&
    (signalBySymbol(state.selectedSymbol) || coverageForSymbol(state.selectedSymbol) || state.watchlist.includes(state.selectedSymbol))
  ) {
    return;
  }

  const watchlistHit = state.watchlist.map((symbol) => signalBySymbol(symbol)).find(Boolean);
  const watchlistCoverage = state.watchlist.find((symbol) => coverageForSymbol(symbol));
  state.selectedSymbol =
    watchlistHit?.symbol ||
    watchlistCoverage ||
    getLeadSignal()?.symbol ||
    allCoverage[0]?.symbol ||
    allSignals[0]?.symbol ||
    null;
}

function selectedSignal() {
  if (state.selectedSymbol) {
    return signalBySymbol(state.selectedSymbol);
  }
  return getLeadSignal();
}

function selectedCoverage() {
  return state.selectedSymbol ? coverageForSymbol(state.selectedSymbol) : null;
}

function selectionContext() {
  const signal = selectedSignal();
  if (signal) {
    return {
      symbol: signal.symbol,
      signal,
      coverage: coverageForSymbol(signal.symbol),
    };
  }

  const coverage = selectedCoverage();
  if (coverage) {
    return {
      symbol: coverage.symbol,
      signal: null,
      coverage,
    };
  }

  if (state.selectedSymbol) {
    return {
      symbol: state.selectedSymbol,
      signal: null,
      coverage: null,
    };
  }

  const lead = getLeadSignal();
  if (lead) {
    return {
      symbol: lead.symbol,
      signal: lead,
      coverage: coverageForSymbol(lead.symbol),
    };
  }

  const firstCoverage = availableSymbols()[0] || null;
  return {
    symbol: firstCoverage?.symbol || null,
    signal: null,
    coverage: firstCoverage,
  };
}

function watchlistEntries() {
  return state.watchlist.map((symbol) => {
    const signal = signalBySymbol(symbol);
    const coverage = coverageForSymbol(symbol);
    const profile = stockProfile(symbol);
    if (!signal) {
      const summary = coverage
        ? coverageSummary(coverage)
        : profile
          ? quoteSummary(symbol)
          : "No raw disclosures or ranked signal on this name in the latest run.";
      return {
        symbol,
        signal: null,
        coverage,
        profile,
        mode: "calm",
        label: coverage ? "Tracked" : profile ? "Profile" : "Quiet",
        summary,
        title: coverage ? `${symbol} is covered but quiet today` : `${symbol} is quiet today`,
      };
    }
    const tone = toneMeta(signal);
    return {
      symbol,
      signal,
      coverage,
      mode: tone.mode,
      label: tone.label,
      summary: summaryFor(signal),
      title: tone.title,
    };
  });
}
function buildNotifications() {
  const entries = watchlistEntries();
  const notes = [];

  if (!entries.length) {
    for (const signal of getSignals().slice(0, 4)) {
      const tone = toneMeta(signal);
      notes.push({
        id: `discover-${signal.symbol}`,
        symbol: signal.symbol,
        signal,
        tone: directionClass(signal.direction),
        title: tone.title,
        body: whyItMatters(signal),
        urgent: confidenceFor(signal) >= 70,
        tag: "Discover",
      });
    }
    return notes;
  }

  for (const entry of entries) {
    if (!entry.signal) {
      notes.push({
        id: `quiet-${entry.symbol}`,
        symbol: entry.symbol,
        signal: null,
        tone: "neutral",
        title: entry.coverage ? `${entry.symbol} is quiet, not missing` : `${entry.symbol} is calm for now`,
        body: entry.summary,
        urgent: false,
        tag: entry.coverage ? "Tracked" : "Quiet",
      });
      continue;
    }

    const signal = entry.signal;
    const tone = directionClass(signal.direction);
    notes.push({
      id: `${signal.symbol}-${signal.score}-${tone}`,
      symbol: signal.symbol,
      signal,
      tone,
      title: toneMeta(signal).title,
      body: whyItMatters(signal),
      urgent: confidenceFor(signal) >= 72 || signal.score >= 70,
      tag: signal.review_action === "highlight" ? "Hot" : "Watch",
    });
  }

  return notes.sort((a, b) => {
    const urgencyGap = Number(b.urgent) - Number(a.urgent);
    if (urgencyGap !== 0) {
      return urgencyGap;
    }
    return (b.signal?.score || 0) - (a.signal?.score || 0);
  });
}

function updateAlertToggleLabel() {
  const supported = typeof Notification !== "undefined";
  if (!supported) {
    alertsToggleButton.textContent = "Alerts Unsupported";
    alertsToggleButton.disabled = true;
    return;
  }

  const permission = Notification.permission;
  if (state.alertsEnabled && permission === "granted") {
    alertsToggleButton.textContent = "Alerts On";
    alertsToggleButton.disabled = false;
    return;
  }

  alertsToggleButton.textContent = permission === "denied" ? "Alerts Blocked" : "Enable Alerts";
  alertsToggleButton.disabled = permission === "denied";
}

function renderRunSelect() {
  if (!runSelect) {
    return;
  }

  const runs = Array.isArray(state.runs) ? state.runs : [];
  runSelect.innerHTML = runs.length
    ? runs
        .map((run) => `<option value="${escapeHtml(run.run_label)}">${escapeHtml(run.run_label)}</option>`)
        .join("")
    : '<option value="">No runs yet</option>';

  if (state.data?.run_label) {
    runSelect.value = state.data.run_label;
  }

  runSelect.disabled = !runs.length;
}

async function loadRuns() {
  const response = await fetch("/api/runs");
  if (!response.ok) {
    throw new Error("Could not load available runs.");
  }
  state.runs = await response.json();
  renderRunSelect();
}

async function loadUniverse() {
  const response = await fetch("/api/universe?limit=5000");
  if (!response.ok) {
    throw new Error("Could not load the stock universe.");
  }
  state.universe = await response.json();
  renderSuggestions();
  renderSnapshot();
}

async function loadStockProfile(symbol, force = false) {
  const normalized = String(symbol || "").trim().toUpperCase();
  if (!normalized) {
    return null;
  }
  if (!force && state.stockProfiles[normalized]) {
    return state.stockProfiles[normalized];
  }

  const runLabel = state.data?.run_label ? `?run_label=${encodeURIComponent(state.data.run_label)}` : "";
  const response = await fetch(`/api/stocks/${encodeURIComponent(normalized)}${runLabel}`);
  if (!response.ok) {
    throw new Error(`Could not load stock profile for ${normalized}.`);
  }

  const payload = await response.json();
  state.stockProfiles[normalized] = payload;
  return payload;
}

async function hydrateSelectionProfile() {
  const context = selectionContext();
  if (!context.symbol || context.signal) {
    return;
  }

  const normalized = String(context.symbol).toUpperCase();
  const hadProfile = Boolean(state.stockProfiles[normalized]);

  try {
    await loadStockProfile(normalized);
    if (!hadProfile) {
      renderAll();
    }
  } catch {
    // Quietly skip profile hydration if the quote endpoint does not respond.
  }
}

async function hydrateWatchlistProfiles() {
  const symbols = state.watchlist
    .filter((symbol) => !signalBySymbol(symbol) && !state.stockProfiles[String(symbol).toUpperCase()])
    .slice(0, 4);

  if (!symbols.length) {
    return;
  }

  await Promise.all(
    symbols.map(async (symbol) => {
      try {
        await loadStockProfile(symbol);
      } catch {
        // Ignore individual symbol failures and keep the rest of the app interactive.
      }
    }),
  );
  renderAll();
}

function pushToast(title, body, actions = {}) {
  const toast = document.createElement("div");
  toast.className = "toast";
  toast.innerHTML = `
    <h3 class="toast-title">${escapeHtml(title)}</h3>
    <p class="toast-body">${escapeHtml(body)}</p>
    <div class="toast-actions">
      <button type="button" data-close-toast="true">Dismiss</button>
      ${actions.symbol ? `<button type="button" data-open-symbol="${escapeHtml(actions.symbol)}">Open Brief</button>` : ""}
    </div>
  `;
  toastStack.prepend(toast);
  window.setTimeout(() => {
    toast.remove();
  }, 6500);
}

function maybeDeliverAlerts(notes, source = "load") {
  const urgentNotes = notes.filter((item) => item.urgent).slice(0, 2);
  if (!urgentNotes.length) {
    return;
  }

  for (const note of urgentNotes) {
    const deliveryKey = `${source}:${note.id}`;
    if (state.deliveredNotes.has(deliveryKey)) {
      continue;
    }
    state.deliveredNotes.add(deliveryKey);
    pushToast(note.title, note.body, { symbol: note.symbol });

    if (state.alertsEnabled && typeof Notification !== "undefined" && Notification.permission === "granted") {
      new Notification(note.title, {
        body: note.body,
        tag: note.id,
      });
    }
  }
}

function snapshotMetric(label, value, note) {
  return `
    <article class="metric-card">
      <div class="mini-kicker">${escapeHtml(label)}</div>
      <div class="metric-value">${escapeHtml(String(value))}</div>
      <p class="metric-note">${escapeHtml(note)}</p>
    </article>
  `;
}

function pipelineRow(label, value, maxValue) {
  const numericValue = Number(value || 0);
  const ratio = numericValue > 0 && maxValue > 0 ? Math.max(8, Math.round((numericValue / maxValue) * 100)) : 0;
  return `
    <div class="pipeline-row">
      <span class="pipeline-label">${escapeHtml(label)}</span>
      <div class="pipeline-bar"><span style="width:${ratio}%"></span></div>
      <strong>${number(numericValue)}</strong>
    </div>
  `;
}

function todaySignals(limit = 6) {
  return [...getSignals()]
    .sort((left, right) => {
      const watchlistGap = Number(state.watchlist.includes(right.symbol)) - Number(state.watchlist.includes(left.symbol));
      if (watchlistGap !== 0) {
        return watchlistGap;
      }

      const scoreGap = Math.abs(Number(right.score || 0)) - Math.abs(Number(left.score || 0));
      if (scoreGap !== 0) {
        return scoreGap;
      }

      return Number(confidenceFor(right) || 0) - Number(confidenceFor(left) || 0);
    })
    .slice(0, limit);
}

function todaySignalCard(signal) {
  const selected = state.selectedSymbol === signal.symbol;
  const inWatchlist = state.watchlist.includes(signal.symbol);
  const tone = directionClass(signal.direction);
  const note = inWatchlist ? "In your watchlist" : signal.direction === "bearish" ? "Needs caution" : "Worth opening";

  return `
    <article class="feed-item ${selected ? "selected" : ""}">
      <div class="card-topline">
        <div class="card-main">
          <span class="mini-kicker">${escapeHtml(headlineFor(signal))}</span>
          <h3>${escapeHtml(signal.symbol)}</h3>
          <p class="card-company">${escapeHtml(signal.company || "Unknown company")}</p>
        </div>
        <div class="feed-actions">
          ${chip(signal.direction || "neutral", tone)}
          ${chip(`${number(signal.score)} score`, tone)}
          ${inWatchlist ? chip("watchlist", "neutral") : ""}
        </div>
      </div>
      <p class="feed-body">${escapeHtml(truncateText(whyItMatters(signal), 160))}</p>
      <div class="card-footer">
        <span class="summary-note">${escapeHtml(note)}</span>
        <div class="card-actions">
          <button type="button" class="mini-button action-button" data-open-symbol="${escapeHtml(signal.symbol)}">Open Brief</button>
          <button type="button" class="mini-button subtle-button" data-toggle-watchlist="${escapeHtml(signal.symbol)}">${inWatchlist ? "Saved" : "Save"}</button>
        </div>
      </div>
    </article>
  `;
}

function flashDetailSection() {
  if (!detailSection) {
    return;
  }
  detailSection.classList.remove("focused");
  window.requestAnimationFrame(() => {
    detailSection.classList.add("focused");
    window.setTimeout(() => detailSection.classList.remove("focused"), 1500);
  });
}

function openSymbol(symbol, options = {}) {
  const normalized = String(symbol || "").trim().toUpperCase();
  if (!normalized) {
    return;
  }

  const shouldScroll = options.scroll !== false;
  state.selectedSymbol = normalized;
  renderAll();
  void hydrateSelectionProfile();

  if (shouldScroll && detailSection) {
    const behavior = window.matchMedia("(prefers-reduced-motion: reduce)").matches ? "auto" : "smooth";
    window.requestAnimationFrame(() => {
      detailSection.scrollIntoView({ behavior, block: "start" });
      flashDetailSection();
    });
  }
}

function heroMarkup(signal) {
  if (!signal) {
    return '<div class="empty-state">Run the pipeline to load today\'s market pulse.</div>';
  }

  const tone = toneMeta(signal);
  const highlights = attachmentHighlights(signal)
    .slice(0, 3)
    .map((line) => `<li>${escapeHtml(line)}</li>`)
    .join("");
  const inWatchlist = state.watchlist.includes(signal.symbol);

  return `
    <div class="hero-copy">
      <div>
        <div class="hero-topline">
          <p class="eyebrow">${escapeHtml(formatToday())}</p>
          <span class="watchlist-mode ${escapeHtml(tone.mode)}">${escapeHtml(tone.label)} Mode</span>
        </div>
        <h2>${escapeHtml(tone.title)}</h2>
        <p class="hero-summary">${escapeHtml(summaryFor(signal))}</p>
        <p class="hero-support">${escapeHtml(whyItMatters(signal))}</p>
      </div>

      <div>
        <div class="hero-meta">
          ${chip(signal.direction || "neutral", directionClass(signal.direction))}
          ${chip(`${number(signal.score)} score`, directionClass(signal.direction))}
          ${chip(`${number(confidenceFor(signal))}% confidence`, directionClass(signal.direction))}
          ${chip(signal.review_action || "watch")}
        </div>
        <div class="summary-actions">
          <button type="button" class="mini-button action-button" data-open-symbol="${escapeHtml(signal.symbol)}">Open Brief</button>
          <button type="button" class="mini-button subtle-button" data-toggle-watchlist="${escapeHtml(signal.symbol)}">${inWatchlist ? "Remove From Watchlist" : "Add To Watchlist"}</button>
        </div>
      </div>
    </div>

    <aside class="hero-side">
      <div class="hero-side-stat">
        <span class="mini-kicker">Ticker</span>
        <span class="hero-side-value">${escapeHtml(signal.symbol)}</span>
      </div>
      <div class="hero-side-stat">
        <span class="mini-kicker">Company</span>
        <span>${escapeHtml(signal.company || "Unknown company")}</span>
      </div>
      <div class="hero-side-stat">
        <span class="mini-kicker">Moodboard</span>
        <div class="summary-badges">
          ${chip(signal.strength || "medium", directionClass(signal.direction))}
          ${chip(`${number(signal.event_count)} events`)}
          ${chip(`${number(signal.insider_event_count || 0)} insider`)}
        </div>
      </div>
      <div class="hero-side-stat">
        <span class="mini-kicker">Why it popped</span>
        ${highlights ? `<ul class="hero-side-list">${highlights}</ul>` : `<p class="quiet-copy">No attachment highlights parsed yet.</p>`}
      </div>
    </aside>
  `;
}

function quietHeroMarkup(symbol, coverage) {
  const inWatchlist = state.watchlist.includes(symbol);
  const eventTypes = Array.isArray(coverage?.event_types) ? coverage.event_types.slice(0, 3) : [];
  const profile = stockProfile(symbol);
  const quote = profile?.quote;
  const master = profile?.master || universeBySymbol(symbol);
  const hasCoverage = Boolean(coverage);
  const title = hasCoverage
    ? `${symbol} is covered, but not a top signal today.`
    : `${symbol} has no fresh exchange activity in the latest run.`;
  const support = hasCoverage
    ? "We did see this stock in the raw exchange feed. It simply did not cross the scoring threshold to become a ranked opportunity or risk alert."
    : "This stock is still on your watchlist, but we did not collect a fresh disclosure for it in the current run. Baseline company and quote data can still help you stay oriented.";

  return `
    <div class="hero-copy">
      <div>
        <div class="hero-topline">
          <p class="eyebrow">${escapeHtml(formatToday())}</p>
          <span class="watchlist-mode calm">${hasCoverage ? "Tracked Quietly" : "Watchlist Only"}</span>
        </div>
        <h2>${escapeHtml(title)}</h2>
        <p class="hero-summary">${escapeHtml(hasCoverage ? coverageSummary(coverage) : quoteSummary(symbol))}</p>
        <p class="hero-support">${escapeHtml(support)}</p>
      </div>

      <div>
        <div class="hero-meta">
          ${chip(hasCoverage ? "tracked" : "no fresh activity", "neutral")}
          ${chip(`${number(coverage?.event_count || 0)} raw events`, "neutral")}
          ${chip(`${number(coverage?.attachment_count || 0)} attachments`, "neutral")}
          ${quote?.last_price ? chip(`${quote.last_price.toFixed(2)} INR`, "neutral") : ""}
        </div>
        <div class="summary-actions">
          <button type="button" class="mini-button action-button" data-open-symbol="${escapeHtml(symbol)}">Open Brief</button>
          <button type="button" class="mini-button subtle-button" data-toggle-watchlist="${escapeHtml(symbol)}">${inWatchlist ? "Remove From Watchlist" : "Add To Watchlist"}</button>
        </div>
      </div>
    </div>

    <aside class="hero-side">
      <div class="hero-side-stat">
        <span class="mini-kicker">Ticker</span>
        <span class="hero-side-value">${escapeHtml(symbol)}</span>
      </div>
      <div class="hero-side-stat">
        <span class="mini-kicker">Company</span>
        <span>${escapeHtml(coverage?.company || quote?.company || master?.company || symbol)}</span>
      </div>
      <div class="hero-side-stat">
        <span class="mini-kicker">Price pulse</span>
        <span>${escapeHtml(
          quote?.percent_change != null
            ? `${quote.percent_change >= 0 ? "+" : ""}${quote.percent_change.toFixed(2)}% today`
            : "Quote snapshot unavailable"
        )}</span>
      </div>
      <div class="hero-side-stat">
        <span class="mini-kicker">Latest headline</span>
        <p class="quiet-copy">${escapeHtml(coverage?.latest_headline || "No disclosure was collected for this stock in the current run.")}</p>
      </div>
      <div class="hero-side-stat">
        <span class="mini-kicker">Coverage</span>
        <div class="summary-badges">
          ${eventTypes.length ? eventTypes.map((type) => chip(type.replaceAll("_", " "))).join("") : chip(hasCoverage ? "raw coverage" : "watchlist only", "neutral")}
          ${quote?.industry ? chip(quote.industry, "neutral") : ""}
        </div>
      </div>
    </aside>
  `;
}

function watchlistCard(entry) {
  const selected = state.selectedSymbol === entry.symbol;
  if (!entry.signal) {
    return `
      <article class="watchlist-entry ${selected ? "selected" : ""}">
        <div class="watchlist-top">
          <div>
            <h3>${escapeHtml(entry.symbol)}</h3>
            <p class="watchlist-summary">${escapeHtml(entry.summary)}</p>
          </div>
          <span class="watchlist-mode calm">${escapeHtml(entry.label)}</span>
        </div>
        <div class="watchlist-actions">
          <button type="button" class="mini-button action-button" data-open-symbol="${escapeHtml(entry.symbol)}">Open Brief</button>
          <button type="button" class="mini-button subtle-button" data-remove-watchlist="${escapeHtml(entry.symbol)}">Remove</button>
        </div>
      </article>
    `;
  }

  const signal = entry.signal;
  return `
    <article class="watchlist-entry ${selected ? "selected" : ""}">
      <div class="watchlist-top">
        <div>
          <h3>${escapeHtml(signal.symbol)}</h3>
          <p class="watchlist-summary">${escapeHtml(truncateText(summaryFor(signal), 110))}</p>
        </div>
        <span class="watchlist-mode ${escapeHtml(entry.mode)}">${escapeHtml(entry.label)}</span>
      </div>
      <div class="watchlist-tags">
        ${chip(headlineFor(signal), directionClass(signal.direction))}
        ${chip(`${number(confidenceFor(signal))}% confidence`, directionClass(signal.direction))}
      </div>
      <div class="watchlist-actions">
        <button type="button" class="mini-button action-button" data-open-symbol="${escapeHtml(signal.symbol)}">Open Brief</button>
        <button type="button" class="mini-button subtle-button" data-remove-watchlist="${escapeHtml(signal.symbol)}">Remove</button>
      </div>
    </article>
  `;
}

function notificationCard(note) {
  const selected = state.selectedSymbol === note.symbol;
  return `
    <article class="notification-item ${selected ? "selected" : ""}">
      <div class="notification-top">
        <div>
          <div class="note-row">
            <span class="note-tag ${escapeHtml(note.tone)}">${escapeHtml(note.tag)}</span>
            <span class="symbol-tag ${escapeHtml(note.tone)}">${escapeHtml(note.symbol)}</span>
          </div>
          <h3 class="notification-title">${escapeHtml(note.title)}</h3>
        </div>
        <button type="button" class="mini-button action-button" data-open-symbol="${escapeHtml(note.symbol)}">Open Brief</button>
      </div>
      <p class="notification-body">${escapeHtml(note.body)}</p>
    </article>
  `;
}

function feedCard(signal) {
  const selected = state.selectedSymbol === signal.symbol;
  return `
    <article class="feed-item ${selected ? "selected" : ""}">
      <div class="card-topline">
        <div class="card-main">
          <span class="mini-kicker">${escapeHtml(headlineFor(signal))}</span>
          <h3>${escapeHtml(signal.symbol)}</h3>
          <p class="card-company">${escapeHtml(signal.company || "Unknown company")}</p>
        </div>
        <div class="feed-actions">
          ${chip(`${number(signal.score)} score`, directionClass(signal.direction))}
          ${chip(signal.direction || "neutral", directionClass(signal.direction))}
        </div>
      </div>
      <p class="feed-body">${escapeHtml(truncateText(summaryFor(signal), 120))}</p>
      <div class="card-actions">
        <button type="button" class="mini-button action-button" data-open-symbol="${escapeHtml(signal.symbol)}">Open Brief</button>
        <button type="button" class="mini-button subtle-button" data-toggle-watchlist="${escapeHtml(signal.symbol)}">${state.watchlist.includes(signal.symbol) ? "Saved" : "Save"}</button>
      </div>
    </article>
  `;
}

function tapeCard(signal) {
  const selected = state.selectedSymbol === signal.symbol;
  return `
    <article class="tape-item ${selected ? "selected" : ""}">
      <div class="tape-summary">
        <div>
          <span class="mini-kicker">${escapeHtml(headlineFor(signal))}</span>
          <h3>${escapeHtml(signal.symbol)}</h3>
        </div>
        <div class="summary-badges">
          ${chip(signal.direction || "neutral", directionClass(signal.direction))}
          ${chip(`${number(confidenceFor(signal))}%`, directionClass(signal.direction))}
        </div>
      </div>
      <p class="feed-body">${escapeHtml(truncateText(summaryFor(signal), 110))}</p>
      <div class="card-actions">
        <button type="button" class="mini-button action-button" data-open-symbol="${escapeHtml(signal.symbol)}">Open Brief</button>
        <button type="button" class="mini-button subtle-button" data-toggle-watchlist="${escapeHtml(signal.symbol)}">${state.watchlist.includes(signal.symbol) ? "Saved" : "Save"}</button>
      </div>
    </article>
  `;
}
function renderHero() {
  const context = selectionContext();
  if (context.signal) {
    heroPanel.innerHTML = heroMarkup(context.signal);
    return;
  }

  if (context.coverage) {
    heroPanel.innerHTML = quietHeroMarkup(context.symbol, context.coverage);
    return;
  }

  heroPanel.innerHTML = heroMarkup(null);
}

function renderSuggestions() {
  const symbols = universeItems().length ? universeItems() : availableSymbols();
  signalSuggestions.innerHTML = symbols
    .map((item) => `<option value="${escapeHtml(item.symbol)}">${escapeHtml(item.company || item.symbol)}</option>`)
    .join("");
}

function renderQuickAdd() {
  const buttons = getSignals()
    .filter((signal) => !state.watchlist.includes(signal.symbol))
    .slice(0, 4)
    .map(
      (signal) => `
        <button type="button" class="quick-add-button" data-add-watchlist="${escapeHtml(signal.symbol)}">
          <span class="mini-kicker">${escapeHtml(headlineFor(signal))}</span>
          <strong>${escapeHtml(signal.symbol)}</strong>
          <span class="quiet-copy">${escapeHtml(signal.direction || "neutral")} pulse</span>
        </button>
      `,
    )
    .join("");

  quickAdd.innerHTML = buttons || '<div class="empty-state">Your watchlist already covers today\'s loudest symbols.</div>';
}

function renderWatchlist() {
  const entries = watchlistEntries();
  watchlistCount.textContent = `${entries.length} ${entries.length === 1 ? "stock" : "stocks"}`;
  watchlistCards.innerHTML = entries.length
    ? entries.map((entry) => watchlistCard(entry)).join("")
    : '<div class="empty-state">Add a few symbols and we will shape the app around your personal watchlist.</div>';
}

function renderNotifications() {
  const changes = todaySignals();
  notificationCount.textContent = `${changes.length} ${changes.length === 1 ? "signal" : "signals"}`;
  notificationList.innerHTML = changes.length
    ? changes.map((signal) => todaySignalCard(signal)).join("")
    : '<div class="empty-state">No ranked changes yet. Run the pipeline to load today\'s shortlist.</div>';
}

function renderSnapshot() {
  const overview = state.data?.overview || {};
  const manifest = state.data?.manifest || {};
  const coverage = state.data?.coverage || {};
  const universeTotal = Number(state.universe?.total_symbols || 0);
  const changes = todaySignals();
  const watchlistHits = watchlistEntries().filter((entry) => entry.signal).length;
  const explainedCount = Number(state.data?.explanations?.completed || 0);

  snapshotGrid.innerHTML = [
    snapshotMetric("Scanned", number(coverage.total_symbols || 0), `${number(overview.total_events || 0)} raw disclosures seen`),
    snapshotMetric("Shortlisted", number(changes.length), `${number(overview.total_signals || 0)} ranked signals today`),
    snapshotMetric("Your Hits", number(watchlistHits), `${explainedCount} AI briefs generated in this run`),
  ].join("");

  pipelineMini.innerHTML = `
    <div class="pipeline-inline">
      <span class="pipeline-note">${escapeHtml(`${state.data?.run_label || "-"} • ${formatDate(manifest.from_date)} to ${formatDate(manifest.to_date)}`)}</span>
      <span class="pipeline-chip">Raw ${number(overview.total_events || 0)}</span>
      <span class="pipeline-chip">Scored ${number(overview.scored_events || 0)}</span>
      <span class="pipeline-chip">Signals ${number(overview.total_signals || 0)}</span>
      <span class="pipeline-chip">AI ${number(explainedCount)}</span>
      <span class="pipeline-note">${escapeHtml(`${number(universeTotal)} stocks are available in the stock master`)}</span>
    </div>
  `;
}

function renderFeeds() {
  if (!opportunityFeed && !riskFeed) {
    return;
  }

  const opportunities = Array.isArray(state.data?.top_opportunities) ? state.data.top_opportunities.slice(0, 4) : [];
  const risks = Array.isArray(state.data?.top_risks) ? state.data.top_risks.slice(0, 4) : [];

  if (opportunityFeed) {
    opportunityFeed.innerHTML = opportunities.length
      ? opportunities.map((signal) => feedCard(signal)).join("")
      : '<div class="empty-state">No bullish names in the current bundle.</div>';
  }

  if (riskFeed) {
    riskFeed.innerHTML = risks.length
      ? risks.map((signal) => feedCard(signal)).join("")
      : '<div class="empty-state">No bearish names in the current bundle.</div>';
  }
}

function detailMarkup(signal) {
  if (!signal) {
    return '<div class="empty-state">Pick a stock from your watchlist or the feed to open the deep dive.</div>';
  }

  const highlights = attachmentHighlights(signal)
    .map((line) => `<li>${escapeHtml(line)}</li>`)
    .join("");
  const facts = factPairs(signal)
    .map(
      ([label, value]) => `
        <div class="fact-card">
          <div class="fact-label">${escapeHtml(label)}</div>
          <div class="fact-value">${escapeHtml(value)}</div>
        </div>
      `,
    )
    .join("");
  const evidenceCards = (signal.evidence || [])
    .slice(0, 4)
    .map((item) => {
      const attachmentList = (item?.attachment_parse?.highlights || [])
        .slice(0, 3)
        .map((line) => `<li>${escapeHtml(line)}</li>`)
        .join("");
      return `
        <article class="evidence-card">
          <div class="evidence-meta">
            <div>
              <div class="mini-kicker">${escapeHtml(item.event_type || "Event")}</div>
              <h4>${escapeHtml(item.headline || item.reason || "Disclosure")}</h4>
            </div>
            <div class="summary-badges">
              ${chip(formatDate(item.event_date || ""))}
              ${chip(`${number(item.score || 0)} score`)}
            </div>
          </div>
          <p class="evidence-text">${escapeHtml(truncateText(item.raw_text || item.reason || "", 180))}</p>
          ${attachmentList ? `<ul>${attachmentList}</ul>` : ""}
          <div class="card-actions">
            ${item.attachment_url ? `<a class="mini-button evidence-link" href="${safeUrl(item.attachment_url)}" target="_blank" rel="noreferrer">Open Filing</a>` : ""}
            ${item.source_url ? `<a class="mini-button evidence-link" href="${safeUrl(item.source_url)}" target="_blank" rel="noreferrer">Exchange Page</a>` : ""}
          </div>
        </article>
      `;
    })
    .join("");

  const agentEvidence = signal.agent_outputs?.referee?.key_evidence || [];
  const inWatchlist = state.watchlist.includes(signal.symbol);

  return `
    <div class="detail-layout">
      <div class="detail-main">
        <div class="detail-header">
          <div class="detail-topline">
            <div>
              <p class="eyebrow">Selected Signal</p>
              <h3>${escapeHtml(signal.symbol)}</h3>
            </div>
            <div class="detail-stats">
              ${chip(signal.direction || "neutral", directionClass(signal.direction))}
              ${chip(`${number(signal.score)} score`, directionClass(signal.direction))}
              ${chip(`${number(confidenceFor(signal))}% confidence`, directionClass(signal.direction))}
            </div>
          </div>
          <p class="detail-text">${escapeHtml(summaryFor(signal))}</p>
          <div class="summary-actions">
            <button type="button" class="mini-button subtle-button" data-toggle-watchlist="${escapeHtml(signal.symbol)}">${inWatchlist ? "Remove From Watchlist" : "Add To Watchlist"}</button>
            <span class="panel-pill">${escapeHtml(headlineFor(signal))}</span>
          </div>
        </div>

        <section class="detail-panel">
          <h4>Why this matters</h4>
          <p class="detail-text">${escapeHtml(whyItMatters(signal))}</p>
          <div class="note-row">
            ${(signal.reasons || []).slice(0, 4).map((reason) => chip(reason)).join("")}
          </div>
        </section>

        <section class="detail-panel">
          <h4>Evidence Trail</h4>
          <div class="evidence-grid">${evidenceCards || '<div class="empty-state">No evidence cards available.</div>'}</div>
        </section>
      </div>

      <aside class="detail-side">
        <section class="side-panel">
          <h4>Attachment highlights</h4>
          ${highlights ? `<ul>${highlights}</ul>` : '<div class="empty-state">No attachment highlights on this signal yet.</div>'}
        </section>

        <section class="side-panel">
          <h4>Referee notes</h4>
          ${agentEvidence.length ? `<ul>${agentEvidence.map((line) => `<li>${escapeHtml(line)}</li>`).join("")}</ul>` : `<p class="detail-text">${escapeHtml(riskNoteFor(signal))}</p>`}
        </section>

        <section class="side-panel">
          <h4>Extracted facts</h4>
          ${facts ? `<div class="fact-grid">${facts}</div>` : '<div class="empty-state">No structured facts were extracted for this stock.</div>'}
        </section>
      </aside>
    </div>
  `;
}

function quietDetailMarkup(symbol, coverage) {
  const eventTypes = Array.isArray(coverage?.event_types) ? coverage.event_types : [];
  const latestDate = coverage?.latest_event_date ? formatDate(coverage.latest_event_date) : "Unknown date";
  const profile = stockProfile(symbol);
  const quote = profile?.quote;
  const master = profile?.master || universeBySymbol(symbol);
  const hasCoverage = Boolean(coverage);

  return `
    <div class="detail-layout">
      <div class="detail-main">
        <div class="detail-header">
          <div class="detail-topline">
            <div>
              <p class="eyebrow">Tracked Stock</p>
              <h3>${escapeHtml(symbol)}</h3>
            </div>
            <div class="detail-stats">
              ${chip(hasCoverage ? "quiet" : "no fresh activity", "neutral")}
              ${chip(`${number(coverage?.event_count || 0)} raw events`, "neutral")}
              ${chip(`${number(coverage?.attachment_count || 0)} attachments`, "neutral")}
              ${quote?.last_price ? chip(`${quote.last_price.toFixed(2)} INR`, "neutral") : ""}
            </div>
          </div>
          <p class="detail-text">${escapeHtml(hasCoverage ? coverageSummary(coverage) : quoteSummary(symbol))}</p>
          <div class="summary-actions">
            <button type="button" class="mini-button subtle-button" data-toggle-watchlist="${escapeHtml(symbol)}">${state.watchlist.includes(symbol) ? "Remove From Watchlist" : "Add To Watchlist"}</button>
            <span class="panel-pill">Not shortlisted today</span>
          </div>
        </div>

        <section class="detail-panel">
          <h4>Why this is still shown</h4>
          <p class="detail-text">${escapeHtml(
            hasCoverage
              ? "This stock appeared in the raw disclosures we collected, so it is part of the monitored universe. It simply did not generate a strong enough rule-based score to enter the main opportunity or risk list."
              : "This stock is on your watchlist, but there was no fresh exchange disclosure for it in the latest run. That means we cannot build a ranked signal for it yet."
          )}</p>
          <div class="note-row">
            ${eventTypes.length ? eventTypes.slice(0, 4).map((type) => chip(type.replaceAll("_", " "), "neutral")).join("") : chip(hasCoverage ? "raw coverage" : "watchlist only", "neutral")}
          </div>
        </section>

        <section class="detail-panel">
          <h4>Latest raw activity</h4>
          <p class="detail-text">${escapeHtml(coverage?.latest_headline || "No disclosure was collected for this stock in the current run.")}</p>
          <div class="note-row">
            ${chip(`Last seen ${latestDate}`, "neutral")}
            ${chip(`${number(coverage?.event_count || 0)} disclosures`, "neutral")}
            ${quote?.market_status ? chip(quote.market_status, "neutral") : ""}
          </div>
        </section>
      </div>

      <aside class="detail-side">
        <section class="side-panel">
          <h4>Stock profile</h4>
          <ul>
            <li>${escapeHtml(coverage?.company || quote?.company || master?.company || symbol)}</li>
            <li>${escapeHtml(quote?.industry || quote?.basic_industry || master?.series || "Industry unavailable")}</li>
            <li>${escapeHtml(quote?.last_price != null ? `Last price ${quote.last_price.toFixed(2)} INR` : "Quote unavailable")}</li>
          </ul>
        </section>

        <section class="side-panel">
          <h4>Coverage summary</h4>
          <ul>
            <li>${escapeHtml(`${number(coverage?.event_count || 0)} raw events in the latest run`)}</li>
            <li>${escapeHtml(`${number(coverage?.attachment_count || 0)} attachment-linked events`)}</li>
            <li>${escapeHtml(master?.listing_date ? `Listed on ${master.listing_date}` : "Listing date unavailable")}</li>
          </ul>
        </section>

        <section class="side-panel">
          <h4>How to read this</h4>
          <p class="detail-text">${escapeHtml(
            hasCoverage
              ? "Covered but quiet means the stock was seen by the data pipeline, but no unusually strong bullish or bearish pattern was detected yet."
              : "Watchlist only means the stock is saved by the user, but the current market run did not return any fresh disclosure for it."
          )}</p>
        </section>
      </aside>
    </div>
  `;
}

function renderDetail() {
  const context = selectionContext();
  if (context.signal) {
    detailPanel.innerHTML = detailMarkup(context.signal);
    return;
  }

  if (context.coverage) {
    detailPanel.innerHTML = quietDetailMarkup(context.symbol, context.coverage);
    return;
  }

  detailPanel.innerHTML = detailMarkup(null);
}

function renderTape() {
  signalTape.innerHTML = getSignals().length
    ? getSignals().slice(0, 20).map((signal) => tapeCard(signal)).join("")
    : '<div class="empty-state">The full tape will appear after the pipeline runs.</div>';
}

function renderAll() {
  ensureSelectedSymbol();
  renderHero();
  renderSuggestions();
  renderQuickAdd();
  renderWatchlist();
  renderNotifications();
  renderSnapshot();
  renderFeeds();
  renderDetail();
  renderTape();
  updateAlertToggleLabel();

  const context = selectionContext();
  if (context.signal) {
    statusPill.textContent = `Live on ${state.data?.run_label || "latest run"} • ${context.signal.symbol} in focus`;
  } else if (context.coverage) {
    statusPill.textContent = `Live on ${state.data?.run_label || "latest run"} • ${context.symbol} is tracked but quiet`;
  } else if (context.symbol) {
    statusPill.textContent = `Live on ${state.data?.run_label || "latest run"} • ${context.symbol} has no fresh activity`;
  } else {
    statusPill.textContent = "No ranked signals yet";
  }
}
function addToWatchlist(symbol, silent = false) {
  const normalized = String(symbol || "").trim().toUpperCase();
  if (!normalized) {
    return;
  }
  if (state.watchlist.includes(normalized)) {
    if (!silent) {
      pushToast(`${normalized} is already saved`, "It is already part of your watchlist.", { symbol: normalized });
    }
    return;
  }

  state.watchlist = [normalized, ...state.watchlist].slice(0, 12);
  saveWatchlist();
  if (!silent) {
    const signal = signalBySymbol(normalized);
    pushToast(
      `${normalized} added to watchlist`,
      signal ? whyItMatters(signal) : "We will start checking this name in your next market refresh.",
      { symbol: normalized },
    );
  }
  state.selectedSymbol = normalized;
  renderAll();
  void hydrateSelectionProfile();
}

function removeFromWatchlist(symbol) {
  state.watchlist = state.watchlist.filter((item) => item !== symbol);
  saveWatchlist();
  pushToast(`${symbol} removed`, "This stock is no longer in your watchlist.");
  if (state.selectedSymbol === symbol) {
    state.selectedSymbol = null;
  }
  renderAll();
}

async function toggleAlerts() {
  if (typeof Notification === "undefined") {
    return;
  }

  if (state.alertsEnabled && Notification.permission === "granted") {
    state.alertsEnabled = false;
    saveAlertsPreference(false);
    updateAlertToggleLabel();
    pushToast("Browser alerts paused", "You will still see in-app alerts inside the app.");
    return;
  }

  const permission = await Notification.requestPermission();
  const enabled = permission === "granted";
  state.alertsEnabled = enabled;
  saveAlertsPreference(enabled);
  updateAlertToggleLabel();
  pushToast(
    enabled ? "Browser alerts enabled" : "Browser alerts unavailable",
    enabled ? "Urgent watchlist signals can now notify you here too." : "You can still use the in-app alerts inside the app.",
  );
}

async function loadSignalBundle(runLabel = null, source = "load") {
  const endpoint = runLabel ? `/api/signals/${encodeURIComponent(runLabel)}` : "/api/signals/latest";
  const response = await fetch(endpoint);
  if (!response.ok) {
    throw new Error(runLabel ? `Could not load run ${runLabel}.` : "Could not load the latest market pulse.");
  }
  state.data = await response.json();
  renderRunSelect();
  ensureSelectedSymbol();
  renderAll();
  maybeDeliverAlerts(buildNotifications(), source);
  void hydrateSelectionProfile();
  void hydrateWatchlistProfiles();
}

async function triggerRun() {
  runPipelineButton.disabled = true;
  runPipelineButton.textContent = "Refreshing...";
  statusPill.textContent = "Refreshing the latest market pulse...";

  try {
    const response = await fetch("/api/run", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        days_back: 1,
        include_attachments: true,
        include_explanations: true,
      }),
    });

    if (!response.ok) {
      throw new Error("Refresh failed.");
    }

    const payload = await response.json();
    await loadRuns();
    await loadSignalBundle(payload.run_label, "refresh");
    pushToast("Pulse refreshed", "Your dashboard and watchlist notes are now up to date.");
  } catch (error) {
    const message = error instanceof Error ? error.message : "Refresh failed.";
    statusPill.textContent = message;
    pushToast("Could not refresh", message);
  } finally {
    runPipelineButton.disabled = false;
    runPipelineButton.textContent = "Refresh Pulse";
  }
}

watchlistForm.addEventListener("submit", (event) => {
  event.preventDefault();
  addToWatchlist(watchlistInput.value);
  watchlistInput.value = "";
});

alertsToggleButton.addEventListener("click", toggleAlerts);
runPipelineButton.addEventListener("click", triggerRun);
runSelect.addEventListener("change", async (event) => {
  const target = event.currentTarget;
  if (!(target instanceof HTMLSelectElement) || !target.value) {
    return;
  }

  statusPill.textContent = `Loading run ${target.value}...`;
  try {
    await loadSignalBundle(target.value, "run-switch");
    pushToast("Run switched", `You are now viewing ${target.value}.`);
  } catch (error) {
    const message = error instanceof Error ? error.message : "Could not switch runs.";
    statusPill.textContent = message;
    pushToast("Run switch failed", message);
  }
});

document.addEventListener("click", (event) => {
  const openButton = event.target.closest("[data-open-symbol]");
  if (openButton) {
    openSymbol(openButton.getAttribute("data-open-symbol"));
    return;
  }

  const selectButton = event.target.closest("[data-select-symbol]");
  if (selectButton) {
    state.selectedSymbol = selectButton.getAttribute("data-select-symbol");
    renderAll();
    void hydrateSelectionProfile();
    return;
  }

  const addButton = event.target.closest("[data-add-watchlist]");
  if (addButton) {
    addToWatchlist(addButton.getAttribute("data-add-watchlist"));
    return;
  }

  const removeButton = event.target.closest("[data-remove-watchlist]");
  if (removeButton) {
    removeFromWatchlist(removeButton.getAttribute("data-remove-watchlist"));
    return;
  }

  const toggleButton = event.target.closest("[data-toggle-watchlist]");
  if (toggleButton) {
    const symbol = toggleButton.getAttribute("data-toggle-watchlist");
    if (state.watchlist.includes(symbol)) {
      removeFromWatchlist(symbol);
    } else {
      addToWatchlist(symbol);
    }
    return;
  }

  if (event.target.closest("[data-close-toast]")) {
    event.target.closest(".toast")?.remove();
  }
});

async function bootstrap() {
  try {
    await Promise.allSettled([loadRuns(), loadUniverse()]);
    await loadSignalBundle();
  } catch (error) {
    const message = error instanceof Error ? error.message : "The app could not load the signal bundle.";
    statusPill.textContent = message;
    heroPanel.innerHTML = `<div class="empty-state">${escapeHtml(message)}</div>`;
    watchlistCards.innerHTML = '<div class="empty-state">Add a few symbols once the app reconnects.</div>';
    notificationList.innerHTML = `<div class="empty-state">${escapeHtml(message)}</div>`;
    snapshotGrid.innerHTML = `<div class="empty-state">${escapeHtml(message)}</div>`;
    pipelineMini.innerHTML = "";
    if (opportunityFeed) {
      opportunityFeed.innerHTML = `<div class="empty-state">${escapeHtml(message)}</div>`;
    }
    if (riskFeed) {
      riskFeed.innerHTML = `<div class="empty-state">${escapeHtml(message)}</div>`;
    }
    detailPanel.innerHTML = `<div class="empty-state">${escapeHtml(message)}</div>`;
    signalTape.innerHTML = `<div class="empty-state">${escapeHtml(message)}</div>`;
    updateAlertToggleLabel();
  }
}

void bootstrap();
