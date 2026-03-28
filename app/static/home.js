import {
  escapeHtml,
  formatDate,
  formatDateTime,
  loadBundle,
  loadChartBundle,
  loadVideoBundle,
  number,
  readWatchlist,
  renderChartSignalCard,
  renderEmptyState,
  renderSignalCard,
  toggleWatchlistSymbol,
  topSignals,
} from "/static/site.js";

const runBadge = document.getElementById("homeRunBadge");
const statsRoot = document.getElementById("homeStats");
const topSignalsRoot = document.getElementById("homeTopSignals");
const chartSignalsRoot = document.getElementById("homeChartSignals");
const videoSyncBadge = document.getElementById("homeVideoSyncBadge");
const videoPlayerRoot = document.getElementById("homeVideoPlayer");
const videoMetaRoot = document.getElementById("homeVideoMeta");
const videoMatrixRoot = document.getElementById("homeVideoMatrix");

const state = {
  bundle: null,
  chartBundle: null,
  videoBundle: null,
  watchlist: readWatchlist(),
};

let filmObserver = null;
let videoPollTimer = null;
const VIDEO_POLL_MS = 10000;

function videoToneClass(video) {
  if (video?.summary?.tone === "risk_on") {
    return "bullish";
  }
  if (video?.summary?.tone === "defensive") {
    return "bearish";
  }
  return "neutral";
}

function videoStatusClass(render, renderJob = {}) {
  if (renderJob?.status === "running") {
    return "running";
  }
  if (renderJob?.status === "failed") {
    return "failed";
  }
  return String(render?.status || "missing").replace(/_/g, "-");
}

function formatDuration(seconds) {
  const numeric = Number(seconds || 0);
  if (!Number.isFinite(numeric) || numeric <= 0) {
    return "-";
  }
  const minutes = Math.floor(numeric / 60);
  const remainder = Math.round(numeric % 60);
  if (!minutes) {
    return `${remainder} sec`;
  }
  return `${minutes}m ${remainder}s`;
}

function syncBadgeCopy(render, renderJob = {}) {
  if (renderJob?.status === "running") {
    return "Rendering fresh film now";
  }
  if (renderJob?.status === "failed") {
    return "Latest film render failed";
  }
  const status = render?.status;
  if (status === "synced") {
    return "Film synced to latest data";
  }
  if (status === "stale") {
    return "Showing an older render";
  }
  if (status === "payload_ready") {
    return "Storyboard ready, render pending";
  }
  return "No rendered film yet";
}

function renderJobCopy(renderJob = {}) {
  if (renderJob?.status === "running") {
    return "A fresh market film is rendering in the background from the latest radar and chart runs.";
  }
  if (renderJob?.status === "completed") {
    return `Latest background render finished at ${formatDateTime(renderJob.completed_at)}.`;
  }
  if (renderJob?.status === "failed") {
    return renderJob?.error || "The latest background render failed before the homepage film could update.";
  }
  if (renderJob?.status === "disabled") {
    return "Automatic market video rendering is disabled in the current environment.";
  }
  return "";
}

function narrationCopy(render = {}, renderJob = {}) {
  if (render?.audio_included) {
    return render?.audio_disclosure || "This film includes AI-generated narration. Unmute the player to hear it.";
  }
  if (render?.audio_error) {
    return `Narration was skipped for the latest render: ${render.audio_error}`;
  }
  if (renderJob?.status === "running") {
    return "The next film is rendering now. If narration is enabled, the new MP4 will include it when the render finishes.";
  }
  return "The inline player starts muted. When narration is available, use the player controls to unmute it.";
}

function clearVideoPolling() {
  if (!videoPollTimer) {
    return;
  }
  window.clearTimeout(videoPollTimer);
  videoPollTimer = null;
}

function shouldPollVideo(video) {
  const render = video?.render || {};
  const renderJob = video?.render_job || {};
  if (renderJob?.status === "running" || Boolean(renderJob?.pending_video_run_label)) {
    return true;
  }
  return render?.status === "payload_ready" && !["failed", "disabled"].includes(renderJob?.status);
}

async function refreshVideoBundle(options = {}) {
  const silent = options.silent !== false;
  try {
    state.videoBundle = await loadVideoBundle();
    renderVideoSection();
  } catch (error) {
    clearVideoPolling();
    if (!silent) {
      const message = error instanceof Error ? error.message : "Could not refresh the market video section.";
      videoSyncBadge.textContent = message;
      videoPlayerRoot.innerHTML = renderEmptyState(message);
      videoMetaRoot.innerHTML = renderEmptyState(message);
      videoMatrixRoot.innerHTML = renderEmptyState(message);
    }
  }
}

function scheduleVideoPolling(video = state.videoBundle) {
  clearVideoPolling();
  if (!shouldPollVideo(video)) {
    return;
  }
  videoPollTimer = window.setTimeout(() => {
    void refreshVideoBundle({ silent: true });
  }, VIDEO_POLL_MS);
}

function bindInlineFilmPlayer() {
  const video = videoPlayerRoot.querySelector(".js-home-film");
  if (!video) {
    if (filmObserver) {
      filmObserver.disconnect();
      filmObserver = null;
    }
    return;
  }

  video.muted = true;
  video.defaultMuted = true;
  video.loop = true;

  const tryPlay = () => {
    video.play().catch(() => {});
  };

  if (filmObserver) {
    filmObserver.disconnect();
  }

  filmObserver = new IntersectionObserver(
    (entries) => {
      const current = entries[0];
      if (!current) {
        return;
      }
      if (current.isIntersecting && current.intersectionRatio >= 0.45) {
        tryPlay();
      } else {
        video.pause();
      }
    },
    { threshold: [0.2, 0.45, 0.75] },
  );

  filmObserver.observe(video);
  tryPlay();
}

function renderVideoPlayer(video) {
  if (!video) {
    videoPlayerRoot.innerHTML = renderEmptyState("The market video engine does not have enough data to build a wrap yet.");
    bindInlineFilmPlayer();
    return;
  }

  const render = video.render || {};
  const renderJob = video.render_job || {};
  const tone = videoToneClass(video);
  const status = videoStatusClass(render, renderJob);
  const headline = escapeHtml(video?.summary?.headline || "Daily market wrap");
  const subhead = escapeHtml(video?.summary?.subhead || "The latest radar runs are turned into a short-form video briefing.");
  const statusCopy = escapeHtml(render?.label || "No rendered film is available yet.");
  const renderJobMessage = escapeHtml(renderJobCopy(renderJob));
  const narrationMessage = escapeHtml(narrationCopy(render, renderJob));
  const durationLabel = escapeHtml(formatDuration(render?.render_duration_seconds || video?.duration_seconds));
  const renderTime = escapeHtml(formatDateTime(render?.rendered_at || render?.generated_at || video?.generated_at));
  const qualityLabel = escapeHtml(render?.quality_label || "1080p target");
  const metadataLine = [
    video?.market_date ? `Market date ${formatDate(video.market_date)}` : "",
    `Length ${durationLabel}`,
    `Render ${qualityLabel}`,
  ].filter(Boolean).join(" | ");

  if (render?.media_url) {
    videoPlayerRoot.innerHTML = `
      <div class="film-stage-shell">
        <div class="film-stage-head">
          <div class="film-stage-copy">
            <p class="eyebrow">Daily Market Wrap</p>
            <h3>${headline}</h3>
            <p>${subhead}</p>
          </div>
          <div class="film-stage-badges">
            <span class="film-stage-pill">${escapeHtml(syncBadgeCopy(render, renderJob))}</span>
            <span class="film-stage-pill">${durationLabel}</span>
            <span class="film-stage-pill">${qualityLabel}</span>
            <span class="film-stage-pill">${renderTime}</span>
          </div>
        </div>
        <div class="film-frame wide ${escapeHtml(tone)} ${escapeHtml(status)}">
          <div class="film-frame-topline">
            <span class="film-status-pill ${escapeHtml(status)}">Auto-playing while visible</span>
            ${render?.audio_included ? `<span class="film-status-pill ${escapeHtml(status)}">AI narration ready</span>` : ""}
            <span class="film-status-pill ${escapeHtml(status)}">${escapeHtml(video?.market_date || "")}</span>
          </div>
          <video
            class="film-video js-home-film"
            controls
            muted
            autoplay
            loop
            playsinline
            preload="metadata"
            src="${escapeHtml(render.media_url)}"
          ></video>
        </div>
      </div>
      <div class="film-player-footer">
        <p class="film-player-note">The homepage keeps the film at roughly seventy percent of the stage width so the right rail can stay useful without crowding the video.</p>
        <p class="film-player-note">${narrationMessage}</p>
        <p class="film-player-note">${statusCopy}</p>
        ${renderJobMessage ? `<p class="film-player-note">${renderJobMessage}</p>` : ""}
        ${metadataLine ? `<p class="film-player-meta">${escapeHtml(metadataLine)}</p>` : ""}
      </div>
    `;
    bindInlineFilmPlayer();
    return;
  }

  videoPlayerRoot.innerHTML = `
    <div class="film-stage-shell">
      <div class="film-stage-head">
        <div class="film-stage-copy">
          <p class="eyebrow">Daily Market Wrap</p>
          <h3>${headline}</h3>
          <p>${subhead}</p>
        </div>
        <div class="film-stage-badges">
          <span class="film-stage-pill">${escapeHtml(syncBadgeCopy(render, renderJob))}</span>
          <span class="film-stage-pill">${durationLabel}</span>
          <span class="film-stage-pill">${qualityLabel}</span>
        </div>
      </div>
    </div>
    <div class="film-frame wide placeholder ${escapeHtml(tone)} ${escapeHtml(status)}">
      <div class="film-placeholder-copy">
        <strong>${headline}</strong>
        <p>${subhead}</p>
        <p class="film-player-note">${narrationMessage}</p>
        <p class="film-player-note">${statusCopy}</p>
        ${renderJobMessage ? `<p class="film-player-note">${renderJobMessage}</p>` : ""}
        <p class="film-player-note">Render the full wrap with <code>python scripts/render_market_video.py</code>. Preview clips are no longer used on the homepage.</p>
        ${metadataLine ? `<p class="film-player-meta">${escapeHtml(metadataLine)}</p>` : ""}
      </div>
    </div>
  `;
  bindInlineFilmPlayer();
}

function renderVideoMeta(video) {
  if (!video) {
    videoMetaRoot.innerHTML = renderEmptyState("Video metadata will appear here after the first payload is built.");
    return;
  }

  const render = video.render || {};
  const renderJob = video.render_job || {};
  const sourceRuns = video.source_runs || {};
  const methodology = Array.isArray(video.generation_methodology) ? video.generation_methodology : [];
  const resolutionLabel = render?.quality_label
    ? `${render.quality_label} studio render`
    : render?.output_height
      ? `${render.output_width || "-"} x ${render.output_height}`
      : "Pending full render";
  const narrationHeadline = render?.audio_included
    ? `AI voice: ${render.audio_voice || "enabled"}`
    : render?.audio_error
      ? "Narration skipped"
      : "No audio track yet";
  const narrationBody = render?.audio_included
    ? render?.audio_disclosure || "The current film includes AI-generated narration."
    : render?.audio_error || narrationCopy(render, renderJob);

  videoMetaRoot.innerHTML = `
    <article class="film-meta-card">
      <span class="eyebrow">Market Date</span>
      <strong>${escapeHtml(formatDate(video.market_date))}</strong>
      <p>Wrap clock: ${escapeHtml(formatDuration(video.duration_seconds))}</p>
    </article>
    <article class="film-meta-card">
      <span class="eyebrow">Rendered</span>
      <strong>${escapeHtml(formatDateTime(render.rendered_at || render.generated_at || video.generated_at))}</strong>
      <p>${escapeHtml(render.label || "The homepage only publishes a full render when it is available.")}</p>
    </article>
    <article class="film-meta-card">
      <span class="eyebrow">Resolution</span>
      <strong>${escapeHtml(resolutionLabel)}</strong>
      <p>${escapeHtml(render?.render_scale ? `Render scale ${render.render_scale}` : "The player prefers the full-quality MP4 when it is available.")}</p>
    </article>
    <article class="film-meta-card">
      <span class="eyebrow">Narration</span>
      <strong>${escapeHtml(narrationHeadline)}</strong>
      <p>${escapeHtml(narrationBody)}</p>
    </article>
    <article class="film-meta-card">
      <span class="eyebrow">Source Runs</span>
      <strong>${escapeHtml(sourceRuns.disclosure_run_label || "No disclosure run")}</strong>
      <p>Chart run: ${escapeHtml(sourceRuns.chart_run_label || "No chart run")}</p>
    </article>
    <article class="film-meta-card film-meta-card-wide">
      <span class="eyebrow">Generation Logic</span>
      <strong>${escapeHtml(video?.summary?.headline || "Daily market wrap")}</strong>
      <p>${escapeHtml(methodology[0] || "The wrap combines disclosure radar, chart radar, and a merged research queue.")}</p>
    </article>
  `;
}

function renderVideoMatrix(video) {
  const matrix = Array.isArray(video?.generation_matrix) ? video.generation_matrix : [];
  videoMatrixRoot.innerHTML = matrix.length
    ? matrix.slice(0, 6).map((item) => `
        <article class="film-matrix-card">
          <span class="eyebrow">${escapeHtml(item.label || "Metric")}</span>
          <strong>${escapeHtml(String(item.value ?? "-"))}</strong>
          <p>${escapeHtml(item.note || "")}</p>
          <span class="film-matrix-source">${escapeHtml(item.source || "video engine")}</span>
        </article>
      `).join("")
    : renderEmptyState("Generation metrics will appear here after the first market wrap payload is built.");
}

function renderVideoSection() {
  const video = state.videoBundle;
  const render = video?.render || {};
  const renderJob = video?.render_job || {};
  const status = videoStatusClass(render, renderJob);
  videoSyncBadge.className = `run-badge video-sync-badge ${status}`;
  videoSyncBadge.textContent = syncBadgeCopy(render, renderJob);
  renderVideoPlayer(video);
  renderVideoMeta(video);
  renderVideoMatrix(video);
  scheduleVideoPolling(video);
}

function renderUsecaseCards(bundle) {
  const disclosureSignals = Number(bundle?.overview?.total_signals || 0);
  const totalEvents = Number(bundle?.overview?.total_events || 0);
  const chartAlerts = Number(state.chartBundle?.overview?.signals_published || 0);
  const chartUniverse = Number(state.chartBundle?.manifest?.universe_size || 0);
  const aiBriefs = Number(bundle?.explanations?.completed || 0);
  const film = state.videoBundle?.render || {};
  const filmMetric = film?.quality_label || (state.videoBundle ? formatDuration(film?.render_duration_seconds || state.videoBundle?.duration_seconds) : "Pending");
  const filmNote = film?.audio_included
    ? "Latest market film is synced with AI narration."
    : "Latest market film is waiting for the newest full render.";

  return [
    {
      eyebrow: "01",
      title: "Opportunity Radar",
      metric: `${number(disclosureSignals)} alerts`,
      note: `${number(totalEvents)} fresh events were scanned to surface missed opportunities.`,
      href: "/radar",
    },
    {
      eyebrow: "02",
      title: "Chart Pattern Intelligence",
      metric: `${number(chartAlerts)} published`,
      note: `${number(chartUniverse)} NSE symbols are in the current technical universe.`,
      href: "/chart-radar",
    },
    {
      eyebrow: "03",
      title: "Market ChatGPT",
      metric: `${number(aiBriefs)} AI briefs`,
      note: "Grounded answers use indexed runs, evidence, and source-cited retrieval.",
      href: "/chat",
    },
    {
      eyebrow: "04",
      title: "AI Market Video Engine",
      metric: filmMetric,
      note: filmNote,
      href: "/",
    },
  ].map((item) => `
    <a class="usecase-card" href="${escapeHtml(item.href)}">
      <span class="eyebrow">${escapeHtml(item.eyebrow)}</span>
      <strong>${escapeHtml(item.title)}</strong>
      <span class="usecase-metric">${escapeHtml(item.metric)}</span>
      <p>${escapeHtml(item.note)}</p>
    </a>
  `).join("");
}

function renderHome() {
  const bundle = state.bundle;
  const disclosureDate = formatDate(bundle?.manifest?.to_date);
  const chartRunLabel = state.chartBundle?.run_label || "waiting for chart lane";
  runBadge.textContent = `Opportunity Radar ${bundle.run_label} | Chart ${chartRunLabel} | Market ${disclosureDate}`;
  statsRoot.innerHTML = renderUsecaseCards(bundle);

  const highlights = topSignals(bundle, state.watchlist, 2);
  topSignalsRoot.innerHTML = highlights.length
    ? highlights.map((signal) => renderSignalCard(signal, { watchlist: state.watchlist, runLabel: bundle.run_label })).join("")
    : renderEmptyState("No ranked alerts are available yet for this run.");

  const chartHighlights = Array.isArray(state.chartBundle?.signals) ? state.chartBundle.signals.slice(0, 2) : [];
  chartSignalsRoot.innerHTML = chartHighlights.length
    ? chartHighlights.map((signal) => renderChartSignalCard(signal, { watchlist: state.watchlist, runLabel: bundle.run_label })).join("")
    : renderEmptyState("Chart Pattern Intelligence has not published a run yet.");

  renderVideoSection();
}

async function bootstrap() {
  try {
    const [bundle, chartBundle, videoBundle] = await Promise.all([
      loadBundle(),
      loadChartBundle().catch(() => null),
      loadVideoBundle().catch(() => null),
    ]);
    state.bundle = bundle;
    state.chartBundle = chartBundle;
    state.videoBundle = videoBundle;
    renderHome();
  } catch (error) {
    clearVideoPolling();
    const message = error instanceof Error ? error.message : "Could not load the latest radar bundle.";
    runBadge.textContent = message;
    statsRoot.innerHTML = renderEmptyState(message);
    topSignalsRoot.innerHTML = renderEmptyState(message);
    chartSignalsRoot.innerHTML = renderEmptyState(message);
    videoSyncBadge.textContent = message;
    videoPlayerRoot.innerHTML = renderEmptyState(message);
    videoMetaRoot.innerHTML = renderEmptyState(message);
    videoMatrixRoot.innerHTML = renderEmptyState(message);
  }
}

document.addEventListener("click", (event) => {
  const button = event.target.closest("[data-watchlist-toggle]");
  if (!button) {
    return;
  }

  state.watchlist = toggleWatchlistSymbol(state.watchlist, button.getAttribute("data-watchlist-toggle"));
  renderHome();
});

window.addEventListener("beforeunload", () => {
  clearVideoPolling();
});

void bootstrap();
