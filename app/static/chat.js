import {
  fetchJSON,
  loadBundle,
  loadRuns,
  readWatchlist,
  renderEmptyState,
  renderRunOptions,
  renderStatCard,
} from "/static/site.js";

const ACTIVE_RUN_KEY = "opportunity-radar-active-run";
const statusRoot = document.getElementById("chatStatusCards");
const suggestionsRoot = document.getElementById("chatSuggestions");
const sourcesRoot = document.getElementById("chatSources");
const transcriptRoot = document.getElementById("chatTranscript");
const form = document.getElementById("chatForm");
const input = document.getElementById("chatInput");
const symbolInput = document.getElementById("chatSymbolInput");
const runSelect = document.getElementById("chatRunSelect");
const indexButton = document.getElementById("chatIndexButton");

const state = {
  sessionId: null,
  bundle: null,
  runs: [],
  watchlist: readWatchlist(),
  latestSources: [],
  messages: [],
};

function setActiveRun(runLabel) {
  if (runLabel) {
    localStorage.setItem(ACTIVE_RUN_KEY, runLabel);
  }
}

function resetConversation() {
  state.sessionId = null;
  state.latestSources = [];
  state.messages = [];
  renderTranscript();
  renderSources();
}

function coverageMap() {
  return state.bundle?.coverage?.by_symbol || {};
}

function symbolInRun(symbol) {
  const normalized = String(symbol || "").trim().toUpperCase();
  if (!normalized || !state.bundle) {
    return false;
  }
  return Boolean(coverageMap()[normalized]) || (state.bundle.signals || []).some((item) => item.symbol === normalized);
}

function renderTranscript() {
  if (!state.messages.length) {
    transcriptRoot.innerHTML = renderEmptyState("Ask Radar about the selected run. Try a stock in the alert feed, a bullish or bearish screen, or a watchlist name that actually appeared in this run.");
    return;
  }

  transcriptRoot.innerHTML = state.messages.map((item) => `
    <article class="chat-message ${item.role}">
      <span class="eyebrow">${item.role === "user" ? "You" : "Radar"}</span>
      <p>${item.content}</p>
    </article>
  `).join("");
  transcriptRoot.scrollTop = transcriptRoot.scrollHeight;
}

function renderSources() {
  sourcesRoot.innerHTML = state.latestSources.length
    ? state.latestSources.map((item) => `
        <article class="detail-card source-card">
          <span class="eyebrow">${item.doc_type}</span>
          <h4>${item.title}</h4>
          <p>${item.snippet}</p>
          <div class="button-row">
            ${item.source_url ? `<a class="btn ghost small" target="_blank" rel="noreferrer" href="${item.source_url}">Exchange Page</a>` : ""}
            ${item.attachment_url ? `<a class="btn ghost small" target="_blank" rel="noreferrer" href="${item.attachment_url}">Attachment</a>` : ""}
          </div>
        </article>
      `).join("")
    : renderEmptyState("Sources used in the latest answer will appear here.");
}

function uniquePrompts(items) {
  const seen = new Set();
  const result = [];
  for (const item of items) {
    const prompt = String(item || "").trim();
    if (!prompt || seen.has(prompt)) {
      continue;
    }
    seen.add(prompt);
    result.push(prompt);
  }
  return result;
}

function buildPromptStarters() {
  if (!state.bundle) {
    return [];
  }

  const runLabel = state.bundle.run_label;
  const signals = Array.isArray(state.bundle.signals) ? state.bundle.signals : [];
  const bullish = signals.filter((item) => item.direction === "bullish").slice(0, 3);
  const bearish = signals.filter((item) => item.direction === "bearish").slice(0, 3);
  const watchlistMatches = state.watchlist.filter((symbol) => symbolInRun(symbol)).slice(0, 2);
  const promoterSignals = signals.filter((item) => (item.tags || []).includes("promoter") || /promoter/i.test(item.primary_reason || "")).slice(0, 2);

  return uniquePrompts([
    ...watchlistMatches.map((symbol) => `What changed in ${symbol} in run ${runLabel}?`),
    ...bullish.slice(0, 2).map((signal) => `Why is ${signal.symbol} bullish in run ${runLabel}?`),
    ...bearish.slice(0, 2).map((signal) => `Why is ${signal.symbol} bearish in run ${runLabel}?`),
    promoterSignals.length ? `Which promoter buying signals stand out in run ${runLabel}?` : "",
    bearish.length ? `What are the top bearish risks in run ${runLabel}?` : "",
    bullish.length ? `What are the top bullish opportunities in run ${runLabel}?` : "",
    `Summarize the most important signals in run ${runLabel}.`,
  ]).slice(0, 6);
}

function renderSuggestions() {
  const prompts = buildPromptStarters();
  suggestionsRoot.innerHTML = prompts.length
    ? prompts.map((prompt) => `
        <button class="quick-add-button chat-prompt" type="button" data-chat-prompt="${prompt.replace(/"/g, '&quot;')}">
          <span class="eyebrow">Ask</span>
          <strong>${prompt}</strong>
        </button>
      `).join("")
    : renderEmptyState("No run-aware prompt starters are available yet. Index or refresh a run first.");
}

async function renderStatus(runLabel = state.bundle?.run_label || "") {
  try {
    const query = runLabel ? `?run_label=${encodeURIComponent(runLabel)}` : "";
    const status = await fetchJSON(`/api/chat/status${query}`);
    const selected = Array.isArray(status) && status.length ? status[0] : null;
    const documents = selected?.indexed_documents || 0;
    const chunks = selected?.indexed_chunks || 0;
    const stateLabel = selected ? "Indexed" : "Needs index";
    statusRoot.innerHTML = [
      renderStatCard("Selected Run", runLabel || "none", "This is the run the chat will answer from right now."),
      renderStatCard("Chat State", stateLabel, selected ? "This run is ready for grounded retrieval." : "Ask or index once to prepare this run for chat."),
      renderStatCard("Documents", documents, selected ? "Signal, evidence, and coverage docs available in Postgres." : "No indexed docs yet for this selected run."),
      renderStatCard("Chunks", chunks, selected ? "Retrieval chunks available for this selected run." : "Chunks will appear after indexing completes."),
    ].join("");
  } catch (error) {
    const message = error instanceof Error ? error.message : "Could not load chat status.";
    statusRoot.innerHTML = renderEmptyState(message);
  }
}

async function loadChatRun(runLabel = "") {
  const preferred = runLabel || "";
  const available = new Set((state.runs || []).map((item) => item.run_label));
  const chosen = preferred && available.has(preferred) ? preferred : (state.runs[0]?.run_label || "");
  state.bundle = await loadBundle(chosen);
  setActiveRun(state.bundle.run_label);
  renderRunOptions(runSelect, state.runs, state.bundle.run_label);
  if (symbolInput.value && !symbolInRun(symbolInput.value)) {
    symbolInput.value = "";
  }
  renderSuggestions();
  await renderStatus(state.bundle.run_label);
}

async function bootstrap() {
  try {
    state.runs = await loadRuns();
    await loadChatRun();
    renderTranscript();
    renderSources();
  } catch (error) {
    const message = error instanceof Error ? error.message : "Could not load chat page.";
    statusRoot.innerHTML = renderEmptyState(message);
    suggestionsRoot.innerHTML = renderEmptyState(message);
    transcriptRoot.innerHTML = renderEmptyState(message);
    sourcesRoot.innerHTML = renderEmptyState(message);
  }
}

async function askRadar(query) {
  const selectedRun = runSelect.value || state.bundle?.run_label;
  if (!selectedRun) {
    state.messages.push({ role: "assistant", content: "I need a processed run before I can answer anything." });
    renderTranscript();
    return;
  }

  state.messages.push({ role: "user", content: query });
  renderTranscript();

  try {
    const response = await fetchJSON("/api/chat/query", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        query,
        session_id: state.sessionId,
        run_label: selectedRun,
        symbol: symbolInput.value.trim().toUpperCase() || null,
        watchlist: state.watchlist.filter((symbol) => symbolInRun(symbol)),
      }),
    });

    state.sessionId = response.session_id;
    state.latestSources = response.sources || [];
    state.messages.push({ role: "assistant", content: response.answer });
    renderTranscript();
    renderSources();
    await renderStatus(selectedRun);
  } catch (error) {
    const message = error instanceof Error ? error.message : "Chat request failed.";
    state.messages.push({ role: "assistant", content: `I couldn't answer that yet: ${message}` });
    renderTranscript();
  }
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  const query = input.value.trim();
  if (!query) {
    return;
  }
  input.value = "";
  await askRadar(query);
});

runSelect.addEventListener("change", async (event) => {
  const target = event.currentTarget;
  if (!(target instanceof HTMLSelectElement) || !target.value) {
    return;
  }
  await loadChatRun(target.value);
  resetConversation();
});

document.addEventListener("click", (event) => {
  const promptButton = event.target.closest("[data-chat-prompt]");
  if (!promptButton) {
    return;
  }
  const prompt = promptButton.getAttribute("data-chat-prompt") || "";
  input.value = prompt;
  input.focus();
});

indexButton.addEventListener("click", async () => {
  const selectedRun = runSelect.value || state.bundle?.run_label;
  if (!selectedRun) {
    return;
  }

  indexButton.disabled = true;
  indexButton.textContent = "Indexing selected run...";
  try {
    await fetchJSON("/api/chat/reindex", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ run_label: selectedRun }),
    });
    await renderStatus(selectedRun);
  } catch (error) {
    const message = error instanceof Error ? error.message : "Could not index chat data.";
    statusRoot.innerHTML = renderEmptyState(message);
  } finally {
    indexButton.disabled = false;
    indexButton.textContent = "Index Selected Run";
  }
});

window.addEventListener("storage", async (event) => {
  if (event.key !== ACTIVE_RUN_KEY || !event.newValue || event.newValue === state.bundle?.run_label) {
    return;
  }
  await loadChatRun(event.newValue);
  resetConversation();
});

void bootstrap();
