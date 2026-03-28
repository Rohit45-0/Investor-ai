import {
  addWatchlistSymbol,
  loadBundle,
  loadStock,
  loadUniverse,
  readWatchlist,
  removeWatchlistSymbol,
  renderEmptyState,
  renderSignalCard,
  renderWatchCard,
  stockState,
  toggleWatchlistSymbol,
  topSignals,
} from "/static/site.js";

const form = document.getElementById("watchlistPageForm");
const input = document.getElementById("watchlistPageInput");
const suggestions = document.getElementById("watchlistSuggestions");
const summaryBadge = document.getElementById("watchlistSummaryBadge");
const quickAddRoot = document.getElementById("watchlistQuickAdd");
const feedRoot = document.getElementById("watchlistFeed");

const state = {
  bundle: null,
  universe: null,
  watchlist: readWatchlist(),
  profiles: {},
};

function renderSuggestions() {
  const items = Array.isArray(state.universe?.items) ? state.universe.items : [];
  suggestions.innerHTML = items.map((item) => `<option value="${item.symbol}">${item.company}</option>`).join("");
}

function renderQuickAdd() {
  const candidates = topSignals(state.bundle, state.watchlist, 4).filter((signal) => !state.watchlist.includes(signal.symbol));
  quickAddRoot.innerHTML = candidates.length
    ? candidates.map((signal) => renderSignalCard(signal, { watchlist: state.watchlist, runLabel: state.bundle.run_label })).join("")
    : renderEmptyState("Your watchlist already covers the strongest names from this run.");
}

function renderWatchlist() {
  summaryBadge.textContent = `${state.watchlist.length} saved`;

  if (!state.watchlist.length) {
    feedRoot.innerHTML = renderEmptyState("No saved stocks yet. Add a few symbols and this page will become your personal daily radar.");
    return;
  }

  const entries = state.watchlist.map((symbol) => stockState(state.bundle, symbol, state.profiles[symbol] || null));
  feedRoot.innerHTML = entries.map((entry) => renderWatchCard(entry, { watchlist: state.watchlist, runLabel: state.bundle.run_label })).join("");
}

async function hydrateProfiles() {
  const missing = state.watchlist.filter((symbol) => !state.profiles[symbol]);
  if (!missing.length) {
    return;
  }

  await Promise.all(
    missing.map(async (symbol) => {
      try {
        state.profiles[symbol] = await loadStock(symbol, state.bundle?.run_label || "");
      } catch {
        state.profiles[symbol] = null;
      }
    }),
  );
}

async function bootstrap() {
  try {
    const [bundle, universe] = await Promise.all([loadBundle(), loadUniverse()]);
    state.bundle = bundle;
    state.universe = universe;
    renderSuggestions();
    renderQuickAdd();
    await hydrateProfiles();
    renderWatchlist();
  } catch (error) {
    const message = error instanceof Error ? error.message : "Could not load the watchlist page.";
    quickAddRoot.innerHTML = renderEmptyState(message);
    feedRoot.innerHTML = renderEmptyState(message);
  }
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  const symbol = input.value.trim().toUpperCase();
  if (!symbol) {
    return;
  }
  state.watchlist = addWatchlistSymbol(state.watchlist, symbol);
  input.value = "";
  try {
    state.profiles[symbol] = await loadStock(symbol, state.bundle?.run_label || "");
  } catch {
    state.profiles[symbol] = null;
  }
  renderQuickAdd();
  renderWatchlist();
});

document.addEventListener("click", async (event) => {
  const quick = event.target.closest("[data-watchlist-toggle]");
  if (quick) {
    const symbol = quick.getAttribute("data-watchlist-toggle");
    state.watchlist = toggleWatchlistSymbol(state.watchlist, symbol);
    if (state.watchlist.includes(symbol) && !state.profiles[symbol]) {
      try {
        state.profiles[symbol] = await loadStock(symbol, state.bundle?.run_label || "");
      } catch {
        state.profiles[symbol] = null;
      }
    }
    renderQuickAdd();
    renderWatchlist();
    return;
  }

  const remove = event.target.closest("[data-watchlist-remove]");
  if (remove) {
    state.watchlist = removeWatchlistSymbol(state.watchlist, remove.getAttribute("data-watchlist-remove"));
    renderQuickAdd();
    renderWatchlist();
  }
});

void bootstrap();
