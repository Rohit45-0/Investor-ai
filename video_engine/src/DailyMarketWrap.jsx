import React from "react";
import {
  AbsoluteFill,
  Audio,
  Easing,
  Sequence,
  interpolate,
  spring,
  staticFile,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";
import samplePayload from "./samplePayload";

const palette = {
  paper: "#f4ecdf",
  paperGlow: "#fff9f1",
  ink: "#111827",
  navy: "#1e2e4d",
  navySoft: "#33476b",
  coral: "#e5764d",
  mint: "#2d8f74",
  rust: "#b44a30",
  gold: "#d4b06d",
  line: "rgba(17, 24, 39, 0.09)",
  shadow: "0 40px 80px rgba(23, 28, 45, 0.16)",
};

const displayFont = '"Iowan Old Style", "Palatino Linotype", "Book Antiqua", Georgia, serif';
const bodyFont = '"Aptos", "Segoe UI", "Helvetica Neue", sans-serif';
const monoFont = '"IBM Plex Mono", "Courier New", monospace';

const sceneOffsets = (scenes) => {
  let cursor = 0;
  return scenes.map((scene) => {
    const result = { ...scene, from: cursor };
    cursor += Number(scene.duration_frames || 0);
    return result;
  });
};

const directionPalette = (direction) => {
  if (direction === "bullish") {
    return { chip: "rgba(45, 143, 116, 0.14)", text: palette.mint, bar: palette.mint };
  }
  if (direction === "bearish") {
    return { chip: "rgba(180, 74, 48, 0.14)", text: palette.rust, bar: palette.rust };
  }
  return { chip: "rgba(30, 46, 77, 0.12)", text: palette.navy, bar: palette.gold };
};

const toLabel = (value) =>
  String(value || "")
    .replace(/_/g, " ")
    .replace(/\b\w/g, (match) => match.toUpperCase());

const tickerText = (payload) => {
  const disclosure = payload.source_runs?.disclosure_run_label || "No disclosure run";
  const chart = payload.source_runs?.chart_run_label || "No chart run";
  return `Daily Market Wrap | ${payload.market_date} | Filing Run ${disclosure} | Chart Run ${chart}`;
};

const Atmosphere = ({ tone }) => {
  const frame = useCurrentFrame();
  const driftA = interpolate(frame, [0, 900], [0, 120], {
    easing: Easing.inOut(Easing.cubic),
    extrapolateRight: "clamp",
  });
  const driftB = interpolate(frame, [0, 900], [0, -90], {
    easing: Easing.inOut(Easing.quad),
    extrapolateRight: "clamp",
  });
  const accent = tone === "defensive" ? palette.rust : tone === "risk_on" ? palette.mint : palette.coral;

  return (
    <AbsoluteFill
      style={{
        background: `linear-gradient(135deg, ${palette.paper} 0%, ${palette.paperGlow} 52%, #efe4d2 100%)`,
        overflow: "hidden",
      }}
    >
      <div
        style={{
          position: "absolute",
          inset: -180,
          background:
            "linear-gradient(rgba(17,24,39,0.05) 1px, transparent 1px), linear-gradient(90deg, rgba(17,24,39,0.05) 1px, transparent 1px)",
          backgroundSize: "60px 60px",
          opacity: 0.3,
          transform: `translateY(${frame * -0.08}px)`,
        }}
      />
      <div
        style={{
          position: "absolute",
          width: 900,
          height: 900,
          borderRadius: "50%",
          left: -180 + driftA,
          top: -220,
          background: `radial-gradient(circle, ${accent}33 0%, transparent 70%)`,
          filter: "blur(10px)",
        }}
      />
      <div
        style={{
          position: "absolute",
          width: 760,
          height: 760,
          borderRadius: "50%",
          right: -120 + driftB,
          bottom: -180,
          background: `radial-gradient(circle, ${palette.navy}22 0%, transparent 72%)`,
          filter: "blur(12px)",
        }}
      />
      <div
        style={{
          position: "absolute",
          inset: 32,
          borderRadius: 42,
          border: `1px solid ${palette.line}`,
          boxShadow: "inset 0 0 0 1px rgba(255,255,255,0.4)",
        }}
      />
    </AbsoluteFill>
  );
};

const Chrome = ({ payload, sceneIndex, sceneCount, voiceover }) => (
  <>
    <div
      style={{
        position: "absolute",
        top: 48,
        left: 60,
        right: 60,
        display: "flex",
        justifyContent: "space-between",
        alignItems: "center",
        fontFamily: monoFont,
        letterSpacing: "0.18em",
        textTransform: "uppercase",
        fontSize: 24,
        color: palette.navy,
      }}
    >
      <span>{payload.brand?.tagline || "AI for the Indian Investor"}</span>
      <div style={{ display: "flex", alignItems: "center", gap: 16 }}>
        {payload.audio?.available ? (
          <span
            style={{
              padding: "10px 16px",
              borderRadius: 999,
              background: "rgba(45, 143, 116, 0.12)",
              color: palette.mint,
              border: "1px solid rgba(45, 143, 116, 0.16)",
            }}
          >
            AI narration
          </span>
        ) : null}
        <span>
          {String(sceneIndex + 1).padStart(2, "0")} / {String(sceneCount).padStart(2, "0")}
        </span>
      </div>
    </div>
    <div
      style={{
        position: "absolute",
        left: 60,
        right: 60,
        top: 104,
        padding: "16px 24px",
        borderRadius: 999,
        background: "rgba(255,255,255,0.56)",
        border: `1px solid ${palette.line}`,
        boxShadow: palette.shadow,
        fontFamily: monoFont,
        fontSize: 21,
        letterSpacing: "0.11em",
        textTransform: "uppercase",
        color: "#2d3650",
      }}
    >
      {tickerText(payload)}
    </div>
    <div
      style={{
        position: "absolute",
        left: 60,
        right: 60,
        bottom: 52,
        display: "flex",
        justifyContent: "space-between",
        alignItems: "flex-end",
        gap: 24,
      }}
    >
      <div
        style={{
          flex: 1,
          padding: "20px 24px",
          borderRadius: 28,
          background: "rgba(17, 24, 39, 0.86)",
          color: "#f8f4ee",
          boxShadow: palette.shadow,
        }}
      >
        <div
          style={{
            fontFamily: monoFont,
            letterSpacing: "0.15em",
            textTransform: "uppercase",
            fontSize: 19,
            opacity: 0.72,
            marginBottom: 10,
          }}
        >
          Voiceover cue
        </div>
        <div
          style={{
            fontFamily: bodyFont,
            fontSize: 31,
            lineHeight: 1.25,
          }}
        >
          {voiceover}
        </div>
      </div>
      <div
        style={{
          minWidth: 210,
          padding: "18px 22px",
          borderRadius: 24,
          background: "rgba(255,255,255,0.68)",
          border: `1px solid ${palette.line}`,
          boxShadow: palette.shadow,
          color: palette.navy,
        }}
      >
        <div
          style={{
            fontFamily: monoFont,
            fontSize: 16,
            letterSpacing: "0.15em",
            textTransform: "uppercase",
            marginBottom: 8,
          }}
        >
          Mode
        </div>
        <div
          style={{
            fontFamily: displayFont,
            fontSize: 40,
            lineHeight: 1,
          }}
        >
          {toLabel(payload.summary?.tone || "mixed")}
        </div>
      </div>
    </div>
  </>
);

const SceneHeading = ({ eyebrow, title, subtitle, align = "left" }) => (
  <div
    style={{
      display: "flex",
      flexDirection: "column",
      gap: 18,
      alignItems: align === "center" ? "center" : "flex-start",
      textAlign: align,
    }}
  >
    <div
      style={{
        fontFamily: monoFont,
        fontSize: 22,
        letterSpacing: "0.18em",
        textTransform: "uppercase",
        color: palette.navySoft,
      }}
    >
      {eyebrow}
    </div>
    <h1
      style={{
        margin: 0,
        fontFamily: displayFont,
        fontSize: 106,
        lineHeight: 0.92,
        color: palette.ink,
        maxWidth: 760,
      }}
    >
      {title}
    </h1>
    <p
      style={{
        margin: 0,
        fontFamily: bodyFont,
        fontSize: 34,
        lineHeight: 1.34,
        color: "rgba(17, 24, 39, 0.74)",
        maxWidth: 760,
      }}
    >
      {subtitle}
    </p>
  </div>
);

const StatCard = ({ label, value, index }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const appear = spring({
    frame: frame - index * 7,
    fps,
    config: { damping: 20, stiffness: 140, mass: 0.9 },
  });
  return (
    <div
      style={{
        opacity: appear,
        transform: `translateY(${interpolate(appear, [0, 1], [42, 0])}px)`,
        padding: "30px 28px",
        borderRadius: 28,
        background: "rgba(255,255,255,0.7)",
        border: `1px solid ${palette.line}`,
        boxShadow: palette.shadow,
      }}
    >
      <div
        style={{
          fontFamily: monoFont,
          fontSize: 17,
          letterSpacing: "0.15em",
          textTransform: "uppercase",
          color: palette.navySoft,
          marginBottom: 16,
        }}
      >
        {label}
      </div>
      <div
        style={{
          fontFamily: displayFont,
          fontSize: 66,
          lineHeight: 1,
          color: palette.navy,
        }}
      >
        {value}
      </div>
    </div>
  );
};

const Meter = ({ value, color }) => (
  <div
    style={{
      marginTop: 18,
      height: 8,
      borderRadius: 999,
      background: "rgba(17, 24, 39, 0.08)",
      overflow: "hidden",
    }}
  >
    <div
      style={{
        width: `${Math.max(10, Math.min(100, Number(value || 0)))}%`,
        height: "100%",
        borderRadius: 999,
        background: color,
      }}
    />
  </div>
);

const Sparkline = ({ points = [], color }) => {
  if (!points.length) {
    return null;
  }
  const width = 260;
  const height = 84;
  const segments = points
    .map((point, index) => {
      const x = (index / Math.max(points.length - 1, 1)) * width;
      const y = height - point * (height - 8) - 4;
      return `${x},${y}`;
    })
    .join(" ");

  return (
    <svg width={width} height={height} viewBox={`0 0 ${width} ${height}`}>
      <polyline
        fill="none"
        stroke={color}
        strokeWidth="5"
        strokeLinecap="round"
        strokeLinejoin="round"
        points={segments}
      />
    </svg>
  );
};

const BoardCard = ({ item, index }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const appear = spring({
    frame: frame - index * 6,
    fps,
    config: { damping: 22, stiffness: 150, mass: 0.9 },
  });
  const colors = directionPalette(item.direction);

  return (
    <div
      style={{
        opacity: appear,
        transform: `translateY(${interpolate(appear, [0, 1], [48, 0])}px) scale(${interpolate(appear, [0, 1], [0.95, 1])})`,
        padding: "28px 28px 26px",
        borderRadius: 30,
        background: "rgba(255,255,255,0.72)",
        border: `1px solid ${palette.line}`,
        boxShadow: palette.shadow,
        minHeight: 330,
        display: "flex",
        flexDirection: "column",
        justifyContent: "space-between",
      }}
    >
      <div>
        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "flex-start",
            gap: 16,
            marginBottom: 18,
          }}
        >
          <div>
            <div
              style={{
                fontFamily: monoFont,
                fontSize: 18,
                letterSpacing: "0.12em",
                textTransform: "uppercase",
                color: palette.navySoft,
                marginBottom: 8,
              }}
            >
              {item.symbol}
            </div>
            <div
              style={{
                fontFamily: bodyFont,
                fontSize: 24,
                lineHeight: 1.25,
                color: "rgba(17, 24, 39, 0.65)",
                maxWidth: 260,
              }}
            >
              {item.company}
            </div>
          </div>
          <div
            style={{
              padding: "10px 14px",
              borderRadius: 999,
              background: colors.chip,
              color: colors.text,
              fontFamily: monoFont,
              fontSize: 16,
              letterSpacing: "0.12em",
              textTransform: "uppercase",
              whiteSpace: "nowrap",
            }}
          >
            {item.direction || "neutral"}
          </div>
        </div>
        <div
          style={{
            fontFamily: displayFont,
            fontSize: 46,
            lineHeight: 0.95,
            color: palette.ink,
            marginBottom: 16,
          }}
        >
          {item.headline}
        </div>
        <div
          style={{
            fontFamily: bodyFont,
            fontSize: 27,
            lineHeight: 1.35,
            color: "rgba(17, 24, 39, 0.78)",
            minHeight: 110,
          }}
        >
          {item.summary}
        </div>
      </div>
      <div>
        {item.sparkline?.length ? (
          <div style={{ marginBottom: 12 }}>
            <Sparkline points={item.sparkline} color={colors.bar} />
          </div>
        ) : null}
        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            gap: 16,
            alignItems: "flex-end",
          }}
        >
          <div>
            <div
              style={{
                fontFamily: monoFont,
                fontSize: 16,
                letterSpacing: "0.12em",
                textTransform: "uppercase",
                color: palette.navySoft,
                marginBottom: 8,
              }}
            >
              {item.metric_label}
            </div>
            <div
              style={{
                fontFamily: displayFont,
                fontSize: 42,
                lineHeight: 1,
                color: palette.navy,
              }}
            >
              {item.metric_value}
            </div>
          </div>
          <div
            style={{
              maxWidth: 270,
              textAlign: "right",
              fontFamily: bodyFont,
              fontSize: 21,
              lineHeight: 1.3,
              color: "rgba(17, 24, 39, 0.6)",
            }}
          >
            {item.detail}
          </div>
        </div>
        <Meter value={item.confidence || item.score} color={colors.bar} />
      </div>
    </div>
  );
};

const QueueCard = ({ item, index }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const appear = spring({
    frame: frame - index * 7,
    fps,
    config: { damping: 20, stiffness: 160, mass: 0.9 },
  });
  const colors = directionPalette(item.direction);

  return (
    <div
      style={{
        opacity: appear,
        transform: `translateY(${interpolate(appear, [0, 1], [44, 0])}px)`,
        padding: "30px 28px",
        borderRadius: 30,
        background: "rgba(255,255,255,0.74)",
        border: `1px solid ${palette.line}`,
        boxShadow: palette.shadow,
        display: "flex",
        flexDirection: "column",
        gap: 16,
      }}
    >
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          gap: 18,
          alignItems: "flex-start",
        }}
      >
        <div>
          <div
            style={{
              fontFamily: monoFont,
              fontSize: 18,
              letterSpacing: "0.12em",
              textTransform: "uppercase",
              color: palette.navySoft,
              marginBottom: 8,
            }}
          >
            {item.symbol}
          </div>
          <div
            style={{
              fontFamily: displayFont,
              fontSize: 40,
              lineHeight: 0.98,
              color: palette.ink,
              marginBottom: 8,
            }}
          >
            {item.headline}
          </div>
          <div
            style={{
              fontFamily: bodyFont,
              fontSize: 24,
              lineHeight: 1.3,
              color: "rgba(17, 24, 39, 0.75)",
            }}
          >
            {item.company}
          </div>
        </div>
        <div style={{ minWidth: 110, textAlign: "right" }}>
          <div
            style={{
              fontFamily: monoFont,
              fontSize: 15,
              letterSpacing: "0.12em",
              textTransform: "uppercase",
              color: palette.navySoft,
              marginBottom: 8,
            }}
          >
            Conviction
          </div>
          <div
            style={{
              fontFamily: displayFont,
              fontSize: 36,
              lineHeight: 1,
              color: colors.text,
            }}
          >
            {Math.round(Number(item.conviction || 0))}
          </div>
        </div>
      </div>
      <div style={{ display: "flex", gap: 10, flexWrap: "wrap" }}>
        {(item.sources || []).map((source) => (
          <div
            key={source}
            style={{
              padding: "8px 14px",
              borderRadius: 999,
              background: colors.chip,
              color: colors.text,
              fontFamily: monoFont,
              fontSize: 15,
              letterSpacing: "0.11em",
              textTransform: "uppercase",
            }}
          >
            {source}
          </div>
        ))}
      </div>
      <div
        style={{
          fontFamily: bodyFont,
          fontSize: 25,
          lineHeight: 1.35,
          color: "rgba(17, 24, 39, 0.82)",
        }}
      >
        {item.thesis}
      </div>
      <div
        style={{
          fontFamily: bodyFont,
          fontSize: 22,
          lineHeight: 1.3,
          color: "rgba(17, 24, 39, 0.62)",
        }}
      >
        {item.detail}
      </div>
      <Meter value={Math.min(100, Number(item.conviction || 0) / 2)} color={colors.bar} />
    </div>
  );
};

const HeroScene = ({ payload, scene }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const reveal = spring({
    frame,
    fps,
    config: { damping: 18, stiffness: 125, mass: 0.95 },
  });

  return (
    <AbsoluteFill style={{ padding: "194px 78px 210px", color: palette.ink }}>
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "1.2fr 0.8fr",
          gap: 34,
          height: "100%",
        }}
      >
        <div
          style={{
            display: "flex",
            flexDirection: "column",
            justifyContent: "center",
            opacity: reveal,
            transform: `translateY(${interpolate(reveal, [0, 1], [42, 0])}px)`,
          }}
        >
          <SceneHeading eyebrow={scene.eyebrow} title={scene.headline} subtitle={scene.subhead} />
        </div>
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "1fr 1fr",
            gap: 18,
            alignContent: "center",
          }}
        >
          {(scene.stats || []).map((stat, index) => (
            <StatCard key={stat.label} label={stat.label} value={stat.value} index={index} />
          ))}
        </div>
      </div>
      <div
        style={{
          position: "absolute",
          left: 78,
          top: 118,
          padding: "16px 22px",
          borderRadius: 24,
          background: "rgba(255,255,255,0.65)",
          border: `1px solid ${palette.line}`,
          fontFamily: monoFont,
          fontSize: 18,
          letterSpacing: "0.13em",
          textTransform: "uppercase",
          color: palette.navySoft,
        }}
      >
        {payload.market_date}
      </div>
    </AbsoluteFill>
  );
};

const BoardScene = ({ scene }) => (
  <AbsoluteFill style={{ padding: "194px 78px 210px" }}>
    <div
      style={{
        display: "grid",
        gridTemplateColumns: "0.9fr 1.1fr",
        gap: 28,
        height: "100%",
      }}
    >
      <div style={{ paddingTop: 18 }}>
        <SceneHeading eyebrow={scene.eyebrow} title={scene.title} subtitle={scene.subtitle} />
      </div>
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "1fr 1fr",
          gap: 18,
          alignContent: "start",
        }}
      >
        {(scene.items || []).slice(0, 4).map((item, index) => (
          <BoardCard key={`${item.symbol}-${index}`} item={item} index={index} />
        ))}
      </div>
    </div>
  </AbsoluteFill>
);

const QueueScene = ({ scene }) => (
  <AbsoluteFill style={{ padding: "194px 78px 210px" }}>
    <div style={{ marginBottom: 28 }}>
      <SceneHeading eyebrow={scene.eyebrow} title={scene.title} subtitle={scene.subtitle} />
    </div>
    <div
      style={{
        display: "grid",
        gridTemplateColumns: "1fr 1fr",
        gap: 18,
      }}
    >
      {(scene.items || []).slice(0, 4).map((item, index) => (
        <QueueCard key={`${item.symbol}-${index}`} item={item} index={index} />
      ))}
    </div>
  </AbsoluteFill>
);

const CloseScene = ({ scene }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const reveal = spring({
    frame,
    fps,
    config: { damping: 18, stiffness: 130, mass: 0.9 },
  });

  return (
    <AbsoluteFill
      style={{
        padding: "214px 88px 250px",
        justifyContent: "center",
        alignItems: "center",
        textAlign: "center",
      }}
    >
      <div
        style={{
          opacity: reveal,
          transform: `translateY(${interpolate(reveal, [0, 1], [48, 0])}px)`,
          maxWidth: 860,
        }}
      >
        <SceneHeading eyebrow={scene.eyebrow} title={scene.title} subtitle={scene.subtitle} align="center" />
        <div
          style={{
            marginTop: 34,
            display: "flex",
            gap: 14,
            flexWrap: "wrap",
            justifyContent: "center",
          }}
        >
          {(scene.badges || []).map((badge) => (
            <div
              key={badge}
              style={{
                padding: "12px 18px",
                borderRadius: 999,
                background: "rgba(255,255,255,0.7)",
                border: `1px solid ${palette.line}`,
                boxShadow: palette.shadow,
                fontFamily: monoFont,
                fontSize: 18,
                letterSpacing: "0.11em",
                textTransform: "uppercase",
                color: palette.navy,
              }}
            >
              {badge}
            </div>
          ))}
        </div>
      </div>
    </AbsoluteFill>
  );
};

export const DailyMarketWrap = ({ payload = samplePayload }) => {
  const prepared = payload?.scenes?.length ? payload : samplePayload;
  const offsets = sceneOffsets(prepared.scenes || []);
  const audioSrc = prepared.audio?.available && prepared.audio?.static_path ? staticFile(prepared.audio.static_path) : null;

  return (
    <AbsoluteFill
      style={{
        backgroundColor: palette.paper,
        fontFamily: bodyFont,
        color: palette.ink,
      }}
    >
      {audioSrc ? <Audio src={audioSrc} /> : null}
      <Atmosphere tone={prepared.summary?.tone} />
      {offsets.map((scene, index) => (
        <Sequence key={scene.id} from={scene.from} durationInFrames={scene.duration_frames}>
          <>
            <Chrome
              payload={prepared}
              sceneIndex={index}
              sceneCount={offsets.length}
              voiceover={scene.voiceover}
            />
            {scene.type === "hero" ? <HeroScene payload={prepared} scene={scene} /> : null}
            {scene.type === "board" ? <BoardScene scene={scene} /> : null}
            {scene.type === "queue" ? <QueueScene scene={scene} /> : null}
            {scene.type === "close" ? <CloseScene scene={scene} /> : null}
          </>
        </Sequence>
      ))}
    </AbsoluteFill>
  );
};
