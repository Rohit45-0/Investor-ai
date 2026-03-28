import {
  formatDate,
  loadBundle,
  loadRuns,
  number,
  readWatchlist,
  renderEmptyState,
  renderRunOptions,
  renderSignalCard,
  renderStatCard,
  toggleWatchlistSymbol,
  topSignals,
  triggerPipelineRun,
} from "/static/site.js";

const ACTIVE_RUN_KEY = "opportunity-radar-active-run";
const runSelect = document.getElementById("radarRunSelect");
const refreshButton = document.getElementById("radarRefreshButton");
const filterGroup = document.getElementById("radarFilterGroup");
const summaryRoot = document.getElementById("radarSummary");
const processRoot = document.getElementById("radarProcess");
const countBadge = document.getElementById("radarCount");
const feedTitle = document.getElementById("radarFeedTitle");
const feedRoot = document.getElementById("radarFeed");

const state = {
  bundle: null,
  runs: [],
  watchlist: readWatchlist(),
  filter: "all",
};

function filteredSignals() {
  const all = topSignals(state.bundle, state.watchlist, 200);
  if (state.filter === "watchlist") {
    return all.filter((signal) => state.watchlist.includes(signal.symbol));
  }
  if (state.filter === "bullish") {
    return all.filter((signal) => signal.direction === "bullish");
  }
  if (state.filter === "bearish") {
    return all.filter((signal) => signal.direction === "bearish");
  }
  return all;
}

function updateFilterButtons() {
  for (const button of filterGroup.querySelectorAll("[data-filter]")) {
    button.classList.toggle("active", button.getAttribute("data-filter") === state.filter);
  }
}

function renderRadar() {
  const bundle = state.bundle;
  localStorage.setItem(ACTIVE_RUN_KEY, bundle.run_label);
  renderRunOptions(runSelect, state.runs, bundle.run_label);
  updateFilterButtons();

  const coverage = Number(bundle?.coverage?.total_symbols || 0);
  const totalEvents = Number(bundle?.overview?.total_events || 0);
  const shortlist = Number(bundle?.overview?.total_signals || 0);
  const watchlistHits = state.watchlist.filter((symbol) => bundle?.signals?.some((item) => item.symbol === symbol)).length;

  summaryRoot.innerHTML = [
    renderStatCard("Scanned", number(totalEvents), `${number(coverage)} stocks appeared in this run`),
    renderStatCard("Shortlisted", number(shortlist), "Signals made it into today's investor feed"),
    renderStatCard("Watchlist Hits", number(watchlistHits), "Your saved names that surfaced today"),
    renderStatCard("Run Date", formatDate(bundle?.manifest?.to_date), `${bundle.run_label} | ${formatDate(bundle?.manifest?.from_date)} to ${formatDate(bundle?.manifest?.to_date)}`),
  ].join("");

  processRoot.innerHTML = `
    <span class="pipeline-chip">Raw ${number(bundle?.overview?.total_events || 0)}</span>
    <span class="pipeline-chip">Scored ${number(bundle?.overview?.scored_events || 0)}</span>
    <span class="pipeline-chip">Signals ${number(bundle?.overview?.total_signals || 0)}</span>
    <span class="pipeline-chip">AI ${number(bundle?.explanations?.completed || 0)}</span>
    <span class="pipeline-note">Use filters to focus on watchlist, bullish, or bearish alerts.</span>
  `;

  const signals = filteredSignals();
  const filterTitle = {
    all: "Top daily alerts",
    watchlist: "Watchlist alerts",
    bullish: "Bullish alerts",
    bearish: "Bearish alerts",
  };
  feedTitle.textContent = filterTitle[state.filter] || "Top daily alerts";
  countBadge.textContent = `${signals.length} ${signals.length === 1 ? "alert" : "alerts"}`;
  feedRoot.innerHTML = signals.length
    ? signals.map((signal) => renderSignalCard(signal, { watchlist: state.watchlist, runLabel: bundle.run_label })).join("")
    : renderEmptyState("No alerts match this filter right now.");
}

async function loadRadar(runLabel = "") {
  state.bundle = await loadBundle(runLabel);
  renderRadar();
}

async function bootstrap() {
  try {
    state.runs = await loadRuns();
    const chosenRun = state.runs[0]?.run_label || "";
    await loadRadar(chosenRun);
  } catch (error) {
    const message = error instanceof Error ? error.message : "Could not load the radar feed.";
    summaryRoot.innerHTML = renderEmptyState(message);
    processRoot.innerHTML = "";
    feedRoot.innerHTML = renderEmptyState(message);
    countBadge.textContent = "Error";
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
  renderRadar();
});

refreshButton.addEventListener("click", async () => {
  refreshButton.disabled = true;
  refreshButton.textContent = "Refreshing...";
  try {
    const result = await triggerPipelineRun();
    state.runs = await loadRuns();
    await loadRadar(result.run_label || state.runs[0]?.run_label || "");
  } catch (error) {
    const message = error instanceof Error ? error.message : "Could not refresh the run.";
    feedRoot.innerHTML = renderEmptyState(message);
  } finally {
    refreshButton.disabled = false;
    refreshButton.textContent = "Refresh Opportunity Radar";
  }
});

document.addEventListener("click", (event) => {
  const button = event.target.closest("[data-watchlist-toggle]");
  if (!button) {
    return;
  }
  state.watchlist = toggleWatchlistSymbol(state.watchlist, button.getAttribute("data-watchlist-toggle"));
  renderRadar();
});

void bootstrap();
