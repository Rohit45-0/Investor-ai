import {
  formatDateTime,
  loadChartBundle,
  loadChartRunStatus,
  loadChartRuns,
  number,
  readWatchlist,
  renderChartSignalCard,
  renderEmptyState,
  renderRunOptions,
  renderStatCard,
  toggleWatchlistSymbol,
  triggerChartRun,
} from "/static/site.js";

const ACTIVE_RUN_KEY = "opportunity-radar-active-chart-run";
const runSelect = document.getElementById("chartRunSelect");
const refreshButton = document.getElementById("chartRefreshButton");
const filterGroup = document.getElementById("chartFilterGroup");
const summaryRoot = document.getElementById("chartSummary");
const processRoot = document.getElementById("chartProcess");
const countBadge = document.getElementById("chartCount");
const feedTitle = document.getElementById("chartFeedTitle");
const feedRoot = document.getElementById("chartFeed");

const state = {
  bundle: null,
  runs: [],
  runStatus: null,
  pollHandle: null,
  watchlist: readWatchlist(),
  filter: "all",
};

function syncRefreshButton() {
  const running = state.runStatus?.status === "running";
  refreshButton.disabled = running;
  refreshButton.textContent = running ? "Scan Running..." : "Run Live Chart Scan";
}

function filteredSignals() {
  const all = Array.isArray(state.bundle?.signals) ? [...state.bundle.signals] : [];
  if (state.filter === "watchlist") {
    return all.filter((signal) => state.watchlist.includes(signal.symbol));
  }
  if (state.filter === "bullish" || state.filter === "bearish") {
    return all.filter((signal) => signal.direction === state.filter);
  }
  if (["breakout", "reversal", "divergence"].includes(state.filter)) {
    return all.filter((signal) => signal.pattern_family === state.filter);
  }
  return all;
}

function updateFilterButtons() {
  for (const button of filterGroup.querySelectorAll("[data-filter]")) {
    button.classList.toggle("active", button.getAttribute("data-filter") === state.filter);
  }
}

function renderProcessLine(baseMarkup = "") {
  const status = state.runStatus?.status || "idle";
  const startedAt = state.runStatus?.started_at;
  const lastRun = state.runStatus?.last_run_label || state.runStatus?.latest_available_run;
  let statusNote = "";

  if (status === "running") {
    statusNote = `<span class="pipeline-note">Chart scan started ${startedAt ? `at ${startedAt}` : "recently"} and is running in the background. You can stay on this page while it finishes.</span>`;
  } else if (status === "failed") {
    statusNote = `<span class="pipeline-note">The latest background scan failed: ${state.runStatus?.error || "Unknown error"}.</span>`;
  } else if (status === "completed" && lastRun) {
    statusNote = `<span class="pipeline-note">Latest completed chart scan: ${lastRun}.</span>`;
  }

  processRoot.innerHTML = `${baseMarkup}${statusNote}`;
}

function renderZeroState(message, countLabel = "0 alerts") {
  renderRunOptions(runSelect, state.runs, "");
  updateFilterButtons();
  syncRefreshButton();
  summaryRoot.innerHTML = renderEmptyState(message);
  renderProcessLine("");
  feedRoot.innerHTML = renderEmptyState(message);
  countBadge.textContent = countLabel;
}

function renderChartRadar() {
  if (!state.bundle) {
    renderZeroState("No chart runs are available yet. Start a chart scan to build the first bundle.");
    return;
  }

  const bundle = state.bundle;
  localStorage.setItem(ACTIVE_RUN_KEY, bundle.run_label);
  renderRunOptions(runSelect, state.runs, bundle.run_label);
  updateFilterButtons();
  syncRefreshButton();

  const overview = bundle?.overview || {};
  const manifest = bundle?.manifest || {};
  const watchlistHits = state.watchlist.filter((symbol) => bundle?.signals?.some((item) => item.symbol === symbol)).length;

  summaryRoot.innerHTML = [
    renderStatCard("Universe", number(manifest.universe_size || 0), `${number(overview.symbols_scanned || 0)} symbols scanned in this run`),
    renderStatCard("Published", number(overview.signals_published || 0), "High-conviction chart alerts made the feed"),
    renderStatCard("Watchlist Hits", number(watchlistHits), "Saved names that surfaced in the chart feed"),
    renderStatCard("Latest Scan", formatDateTime(bundle.generated_at), `Run ${bundle.run_label}`),
  ].join("");

  renderProcessLine(`
    <span class="pipeline-chip">Breakouts ${number(overview.breakout_signals || 0)}</span>
    <span class="pipeline-chip">Reversals ${number(overview.reversal_signals || 0)}</span>
    <span class="pipeline-chip">Divergences ${number(overview.divergence_signals || 0)}</span>
    <span class="pipeline-chip">Interval ${manifest.intraday_interval || "5m"}</span>
    <span class="pipeline-note">Backtests use a ${number(manifest.backtest_horizon_days || 7)}-day follow-through window.</span>
  `);

  const signals = filteredSignals();
  const filterTitle = {
    all: "Top chart alerts",
    watchlist: "Watchlist chart alerts",
    bullish: "Bullish chart alerts",
    bearish: "Bearish chart alerts",
    breakout: "Breakout alerts",
    reversal: "Reversal alerts",
    divergence: "Divergence alerts",
  };
  feedTitle.textContent = filterTitle[state.filter] || "Top chart alerts";
  countBadge.textContent = `${signals.length} ${signals.length === 1 ? "alert" : "alerts"}`;
  feedRoot.innerHTML = signals.length
    ? signals.map((signal) => renderChartSignalCard(signal, { watchlist: state.watchlist, runLabel: bundle.run_label })).join("")
    : renderEmptyState("No chart alerts match this filter right now.");
}

async function loadRadar(runLabel = "") {
  state.bundle = await loadChartBundle(runLabel);
  renderChartRadar();
}

function stopPolling() {
  if (state.pollHandle) {
    window.clearInterval(state.pollHandle);
    state.pollHandle = null;
  }
}

async function refreshRunStatus() {
  state.runStatus = await loadChartRunStatus();
  const status = state.runStatus?.status;

  if (status === "completed") {
    stopPolling();
    state.runs = await loadChartRuns();
    if (state.runStatus?.last_run_label) {
      await loadRadar(state.runStatus.last_run_label);
      return;
    }
  }

  if (status === "failed") {
    stopPolling();
  }

  if (state.bundle) {
    renderChartRadar();
  } else {
    const message = status === "running"
      ? "Chart scan is running in the background. The first bundle will appear here as soon as it completes."
      : status === "failed"
        ? `Chart scan failed: ${state.runStatus?.error || "Unknown error"}`
        : "No chart runs are available yet. Start a chart scan to build the first bundle.";
    renderZeroState(message, status === "running" ? "Scanning" : "0 alerts");
  }
}

function beginStatusPolling() {
  stopPolling();
  state.pollHandle = window.setInterval(() => {
    void refreshRunStatus();
  }, 4000);
}

async function bootstrap() {
  try {
    const [runs, status] = await Promise.all([
      loadChartRuns(),
      loadChartRunStatus().catch(() => null),
    ]);
    state.runs = runs;
    state.runStatus = status;

    if (state.runs.length) {
      await loadRadar(state.runs[0].run_label);
    } else {
      const message = state.runStatus?.status === "running"
        ? "Chart scan is running in the background. The first bundle will appear here as soon as it completes."
        : "No chart runs are available yet. Start a chart scan to build the first bundle.";
      renderZeroState(message, state.runStatus?.status === "running" ? "Scanning" : "0 alerts");
    }

    if (state.runStatus?.status === "running") {
      beginStatusPolling();
    }
  } catch (error) {
    const message = error instanceof Error ? error.message : "Could not load the chart radar feed.";
    renderZeroState(message, "Error");
  }
}

runSelect.addEventListener("change", async (event) => {
  const target = event.currentTarget;
  if (!(target instanceof HTMLSelectElement) || !target.value) {
    return;
  }
  await loadRadar(target.value);
});

filterGroup.addEventListener("click", (event) => {
  const button = event.target.closest("[data-filter]");
  if (!button) {
    return;
  }
  state.filter = button.getAttribute("data-filter") || "all";
  if (state.bundle) {
    renderChartRadar();
  } else {
    renderZeroState("No chart runs are available yet. Start a chart scan to build the first bundle.");
  }
});

refreshButton.addEventListener("click", async () => {
  refreshButton.textContent = "Starting...";
  try {
    state.runStatus = await triggerChartRun({ force_refresh: true });
    if (state.runStatus?.status === "running") {
      beginStatusPolling();
    }
    if (state.bundle) {
      renderChartRadar();
    } else {
      renderZeroState("Chart scan is running in the background. The first bundle will appear here as soon as it completes.", "Scanning");
    }
  } catch (error) {
    const message = error instanceof Error ? error.message : "Could not start the chart scan.";
    if (state.bundle) {
      feedRoot.innerHTML = renderEmptyState(message);
    } else {
      renderZeroState(message, "Error");
    }
  } finally {
    syncRefreshButton();
  }
});

document.addEventListener("click", (event) => {
  const button = event.target.closest("[data-watchlist-toggle]");
  if (!button) {
    return;
  }
  state.watchlist = toggleWatchlistSymbol(state.watchlist, button.getAttribute("data-watchlist-toggle"));
  if (state.bundle) {
    renderChartRadar();
  }
});

void bootstrap();
