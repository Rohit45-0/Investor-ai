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
import demoSamplePayload from "./demoSamplePayload";

const palette = {
  paper: "#f2ebdf",
  paperSoft: "#fbf7ef",
  ink: "#181924",
  slate: "#31405f",
  navy: "#1d2b49",
  navySoft: "#3d5076",
  navyInk: "#0f1729",
  mint: "#2e9075",
  coral: "#d7724d",
  rust: "#b85238",
  gold: "#cbab75",
  line: "rgba(24, 25, 36, 0.09)",
  lineStrong: "rgba(24, 25, 36, 0.18)",
  white: "#fffdfa",
  shadow: "0 26px 70px rgba(22, 30, 48, 0.16)",
  shadowHeavy: "0 50px 140px rgba(15, 23, 41, 0.2)",
};

const displayFont = '"Iowan Old Style", "Palatino Linotype", "Book Antiqua", Georgia, serif';
const bodyFont = '"Aptos", "Segoe UI", "Helvetica Neue", sans-serif';
const monoFont = '"IBM Plex Mono", "Courier New", monospace';

const normalize = (value) => String(value ?? "").replace(/\s+/g, " ").trim();

const titleCase = (value) =>
  normalize(value)
    .replace(/[_-]/g, " ")
    .replace(/\b\w/g, (match) => match.toUpperCase());

const toDisplayValue = (value) => {
  if (typeof value === "number") {
    return value.toLocaleString("en-IN");
  }
  return normalize(value);
};

const sectionOffsets = (sections) => {
  let cursor = 0;
  return (sections || []).map((section) => {
    const withOffset = { ...section, from: cursor };
    cursor += Number(section.duration_frames || 0);
    return withOffset;
  });
};

const directionTheme = (tone) => {
  if (tone === "bullish") {
    return {
      fill: "rgba(46, 144, 117, 0.12)",
      border: "rgba(46, 144, 117, 0.18)",
      text: palette.mint,
      bar: palette.mint,
    };
  }
  if (tone === "bearish") {
    return {
      fill: "rgba(184, 82, 56, 0.12)",
      border: "rgba(184, 82, 56, 0.16)",
      text: palette.rust,
      bar: palette.rust,
    };
  }
  return {
    fill: "rgba(29, 43, 73, 0.08)",
    border: "rgba(29, 43, 73, 0.12)",
    text: palette.navy,
    bar: palette.gold,
  };
};

const enter = (frame, fps, delay = 0, damping = 18, stiffness = 150) =>
  spring({
    fps,
    frame: Math.max(0, frame - delay),
    config: { damping, stiffness, mass: 0.8 },
  });

const fadeUpStyle = (frame, fps, delay = 0, distance = 34) => {
  const progress = enter(frame, fps, delay);
  return {
    opacity: progress,
    transform: `translateY(${(1 - progress) * distance}px)`,
  };
};

const fadeLeftStyle = (frame, fps, delay = 0, distance = 34) => {
  const progress = enter(frame, fps, delay);
  return {
    opacity: progress,
    transform: `translateX(${(1 - progress) * distance}px)`,
  };
};

const Atmosphere = () => {
  const frame = useCurrentFrame();
  const driftA = interpolate(frame, [0, 5400], [0, 110], {
    easing: Easing.inOut(Easing.cubic),
    extrapolateRight: "clamp",
  });
  const driftB = interpolate(frame, [0, 5400], [0, -120], {
    easing: Easing.inOut(Easing.quad),
    extrapolateRight: "clamp",
  });

  return (
    <AbsoluteFill
      style={{
        background: `linear-gradient(135deg, ${palette.paper} 0%, ${palette.paperSoft} 55%, #efe3d2 100%)`,
        overflow: "hidden",
      }}
    >
      <div
        style={{
          position: "absolute",
          inset: -200,
          background:
            "linear-gradient(rgba(24,25,36,0.04) 1px, transparent 1px), linear-gradient(90deg, rgba(24,25,36,0.04) 1px, transparent 1px)",
          backgroundSize: "64px 64px",
          opacity: 0.34,
          transform: `translateY(${frame * -0.07}px)`,
        }}
      />
      <div
        style={{
          position: "absolute",
          width: 880,
          height: 880,
          borderRadius: "50%",
          left: -170 + driftA,
          top: -240,
          background: "radial-gradient(circle, rgba(215,114,77,0.22) 0%, rgba(215,114,77,0.05) 48%, transparent 70%)",
          filter: "blur(16px)",
        }}
      />
      <div
        style={{
          position: "absolute",
          width: 980,
          height: 980,
          borderRadius: "50%",
          right: -160 + driftB,
          bottom: -280,
          background: "radial-gradient(circle, rgba(29,43,73,0.18) 0%, rgba(29,43,73,0.03) 52%, transparent 72%)",
          filter: "blur(18px)",
        }}
      />
      <div
        style={{
          position: "absolute",
          inset: 28,
          borderRadius: 38,
          border: `1px solid ${palette.line}`,
          boxShadow: "inset 0 0 0 1px rgba(255,255,255,0.42)",
        }}
      />
    </AbsoluteFill>
  );
};

const ShellPanel = ({ children, style = {} }) => (
  <div
    style={{
      background: "rgba(255, 253, 250, 0.78)",
      borderRadius: 34,
      border: `1px solid ${palette.line}`,
      boxShadow: palette.shadow,
      backdropFilter: "blur(10px)",
      ...style,
    }}
  >
    {children}
  </div>
);

const BrowserShell = ({ label, accent = palette.coral, rightLabel, children, style = {} }) => (
  <div
    style={{
      position: "relative",
      borderRadius: 34,
      background: palette.navyInk,
      boxShadow: palette.shadowHeavy,
      overflow: "hidden",
      ...style,
    }}
  >
    <div
      style={{
        height: 66,
        padding: "0 28px",
        borderBottom: "1px solid rgba(255,255,255,0.08)",
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
        background: "linear-gradient(180deg, rgba(255,255,255,0.06), rgba(255,255,255,0.02))",
      }}
    >
      <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
        {["#f87171", "#fbbf24", "#34d399"].map((color) => (
          <div
            key={color}
            style={{
              width: 11,
              height: 11,
              borderRadius: "50%",
              background: color,
            }}
          />
        ))}
      </div>
      <div
        style={{
          fontFamily: monoFont,
          fontSize: 18,
          letterSpacing: "0.12em",
          textTransform: "uppercase",
          color: "rgba(255,255,255,0.76)",
        }}
      >
        {label}
      </div>
      <div
        style={{
          padding: "8px 12px",
          borderRadius: 999,
          background: "rgba(255,255,255,0.08)",
          border: `1px solid ${accent}55`,
          color: accent,
          fontFamily: monoFont,
          fontSize: 13,
          letterSpacing: "0.11em",
          textTransform: "uppercase",
        }}
      >
        {rightLabel || "Live"}
      </div>
    </div>
    <div
      style={{
        padding: 24,
        background: "linear-gradient(180deg, rgba(248,244,238,0.98) 0%, rgba(244,236,223,0.98) 100%)",
        minHeight: 440,
      }}
    >
      {children}
    </div>
  </div>
);

const StatCard = ({ item, index = 0, compact = false }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  return (
    <ShellPanel
      style={{
        padding: compact ? "18px 20px" : "22px 24px",
        ...fadeUpStyle(frame, fps, 8 + index * 4, 24),
      }}
    >
      <div
        style={{
          fontFamily: monoFont,
          fontSize: compact ? 15 : 16,
          letterSpacing: "0.13em",
          textTransform: "uppercase",
          color: palette.navySoft,
          marginBottom: compact ? 10 : 14,
        }}
      >
        {item.label}
      </div>
      <div
        style={{
          fontFamily: displayFont,
          fontSize: compact ? 34 : 46,
          lineHeight: 0.95,
          color: palette.navyInk,
          marginBottom: compact ? 4 : 8,
        }}
      >
        {toDisplayValue(item.value)}
      </div>
      {item.note ? (
        <div
          style={{
            fontFamily: bodyFont,
            fontSize: 18,
            lineHeight: 1.35,
            color: "#495267",
          }}
        >
          {item.note}
        </div>
      ) : null}
    </ShellPanel>
  );
};

const SignalCard = ({ card, index = 0 }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const tone = directionTheme(card.direction || card.tone);

  return (
    <div
      style={{
        position: "relative",
        minHeight: 210,
        borderRadius: 28,
        padding: "20px 20px 18px",
        border: `1px solid ${palette.line}`,
        background: palette.white,
        boxShadow: "0 16px 32px rgba(24,25,36,0.08)",
        overflow: "hidden",
        ...fadeUpStyle(frame, fps, 6 + index * 5, 26),
      }}
    >
      <div
        style={{
          position: "absolute",
          inset: "0 auto 0 0",
          width: 6,
          background: tone.bar,
        }}
      />
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: 14, marginBottom: 16 }}>
        <div>
          <div
            style={{
              fontFamily: monoFont,
              fontSize: 15,
              letterSpacing: "0.14em",
              textTransform: "uppercase",
              color: palette.navySoft,
              marginBottom: 8,
            }}
          >
            {card.symbol || card.label || "Signal"}
          </div>
          <div
            style={{
              fontFamily: bodyFont,
              fontSize: 18,
              lineHeight: 1.3,
              color: "#50586a",
              maxWidth: "92%",
            }}
          >
            {card.company || card.label}
          </div>
        </div>
        <div
          style={{
            padding: "8px 12px",
            borderRadius: 999,
            background: tone.fill,
            border: `1px solid ${tone.border}`,
            color: tone.text,
            fontFamily: monoFont,
            fontSize: 13,
            letterSpacing: "0.12em",
            textTransform: "uppercase",
            whiteSpace: "nowrap",
          }}
        >
          {titleCase(card.direction || card.tone || "neutral")}
        </div>
      </div>
      <div
        style={{
          fontFamily: displayFont,
          fontSize: 28,
          lineHeight: 1,
          color: palette.ink,
          marginBottom: 14,
        }}
      >
        {card.headline}
      </div>
      <div
        style={{
          fontFamily: bodyFont,
          fontSize: 19,
          lineHeight: 1.45,
          color: "#3f485e",
          marginBottom: 18,
        }}
      >
        {card.summary || card.detail}
      </div>
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          gap: 20,
          alignItems: "flex-end",
        }}
      >
        <div
          style={{
            fontFamily: bodyFont,
            fontSize: 16,
            lineHeight: 1.3,
            color: "#687083",
          }}
        >
          {card.detail || card.note || "Evidence-first signal card"}
        </div>
        {card.metric_label ? (
          <div style={{ textAlign: "right" }}>
            <div
              style={{
                fontFamily: monoFont,
                fontSize: 13,
                letterSpacing: "0.11em",
                textTransform: "uppercase",
                color: "#6c7384",
                marginBottom: 6,
              }}
            >
              {card.metric_label}
            </div>
            <div
              style={{
                fontFamily: displayFont,
                fontSize: 23,
                color: palette.navy,
                lineHeight: 0.95,
              }}
            >
              {toDisplayValue(card.metric_value)}
            </div>
          </div>
        ) : null}
      </div>
    </div>
  );
};

const StepRail = ({ steps = [] }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  return (
    <ShellPanel style={{ padding: "26px 28px 24px" }}>
      <div
        style={{
          position: "relative",
          display: "grid",
          gridTemplateColumns: `repeat(${Math.max(steps.length, 1)}, minmax(0, 1fr))`,
          gap: 22,
        }}
      >
        <div
          style={{
            position: "absolute",
            left: 30,
            right: 30,
            top: 24,
            height: 2,
            background: "linear-gradient(90deg, rgba(29,43,73,0.2), rgba(29,43,73,0.05))",
          }}
        />
        {steps.map((step, index) => {
          const progress = enter(frame, fps, 6 + index * 5);
          return (
            <div
              key={`${step.step}-${index}`}
              style={{
                position: "relative",
                transform: `translateY(${(1 - progress) * 16}px)`,
                opacity: progress,
              }}
            >
              <div
                style={{
                  width: 48,
                  height: 48,
                  borderRadius: "50%",
                  background: index === steps.length - 1 ? palette.coral : palette.navy,
                  color: palette.white,
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  fontFamily: monoFont,
                  fontSize: 16,
                  letterSpacing: "0.12em",
                  marginBottom: 20,
                  boxShadow: "0 12px 24px rgba(15,23,41,0.18)",
                }}
              >
                {String(index + 1).padStart(2, "0")}
              </div>
              <div
                style={{
                  fontFamily: displayFont,
                  fontSize: 26,
                  lineHeight: 1,
                  color: palette.ink,
                  marginBottom: 12,
                }}
              >
                {step.step}
              </div>
              <div
                style={{
                  fontFamily: bodyFont,
                  fontSize: 18,
                  lineHeight: 1.4,
                  color: "#4d5569",
                  maxWidth: 320,
                }}
              >
                {step.detail}
              </div>
            </div>
          );
        })}
      </div>
    </ShellPanel>
  );
};

const InfoPanel = ({ section, stats = [] }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        gap: 18,
      }}
    >
      <ShellPanel style={{ padding: "28px 30px 30px", ...fadeLeftStyle(frame, fps, 8, 24) }}>
        <div
          style={{
            fontFamily: monoFont,
            fontSize: 18,
            letterSpacing: "0.16em",
            textTransform: "uppercase",
            color: palette.navySoft,
            marginBottom: 14,
          }}
        >
          {section.eyebrow}
        </div>
        <div
          style={{
            fontFamily: displayFont,
            fontSize: 60,
            lineHeight: 0.92,
            color: palette.ink,
            marginBottom: 18,
          }}
        >
          {section.title}
        </div>
        <div
          style={{
            fontFamily: bodyFont,
            fontSize: 24,
            lineHeight: 1.45,
            color: "#41495d",
          }}
        >
          {section.body}
        </div>
      </ShellPanel>
      <div style={{ display: "grid", gridTemplateColumns: "repeat(2, minmax(0, 1fr))", gap: 16 }}>
        {(stats || []).map((item, index) => (
          <StatCard key={`${item.label}-${index}`} item={item} index={index} compact />
        ))}
      </div>
    </div>
  );
};

const HeroScene = ({ section, payload }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  return (
    <div style={{ flex: 1, padding: "170px 96px 170px", display: "grid", gridTemplateColumns: "1.1fr 0.82fr", gap: 26 }}>
      <ShellPanel style={{ padding: "42px 46px 44px", position: "relative", overflow: "hidden", ...fadeUpStyle(frame, fps, 0, 26) }}>
        <div
          style={{
            position: "absolute",
            width: 340,
            height: 340,
            borderRadius: "50%",
            right: -80,
            top: -70,
            background: "radial-gradient(circle, rgba(46,144,117,0.16) 0%, transparent 70%)",
          }}
        />
        <div
          style={{
            fontFamily: monoFont,
            fontSize: 20,
            letterSpacing: "0.18em",
            textTransform: "uppercase",
            color: palette.navySoft,
            marginBottom: 16,
          }}
        >
          {section.eyebrow}
        </div>
        <div
          style={{
            fontFamily: displayFont,
            fontSize: 88,
            lineHeight: 0.9,
            color: palette.ink,
            marginBottom: 22,
            maxWidth: 820,
          }}
        >
          {section.title}
        </div>
        <div
          style={{
            fontFamily: bodyFont,
            fontSize: 30,
            lineHeight: 1.42,
            color: "#41495d",
            marginBottom: 30,
            maxWidth: 820,
          }}
        >
          {section.body}
        </div>
        <div
          style={{
            display: "inline-flex",
            gap: 14,
            alignItems: "center",
            padding: "16px 22px",
            borderRadius: 999,
            background: "rgba(29,43,73,0.08)",
            border: `1px solid ${palette.line}`,
          }}
        >
          <div
            style={{
              fontFamily: monoFont,
              fontSize: 16,
              letterSpacing: "0.12em",
              textTransform: "uppercase",
              color: palette.navy,
            }}
          >
            Source Runs
          </div>
          <div
            style={{
              fontFamily: bodyFont,
              fontSize: 20,
              color: "#394155",
            }}
          >
            Disclosure {payload.source_runs?.disclosure_run_label} | Chart {payload.source_runs?.chart_run_label}
          </div>
        </div>
      </ShellPanel>
      <div style={{ display: "grid", gridTemplateColumns: "repeat(2, minmax(0, 1fr))", gap: 18 }}>
        {(section.stats || []).map((item, index) => (
          <StatCard key={`${item.label}-${index}`} item={item} index={index} />
        ))}
      </div>
    </div>
  );
};

const OverviewScene = ({ section }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  return (
    <div style={{ flex: 1, padding: "170px 96px 156px" }}>
      <div style={{ maxWidth: 980, marginBottom: 28, ...fadeUpStyle(frame, fps, 0, 24) }}>
        <div
          style={{
            fontFamily: monoFont,
            fontSize: 20,
            letterSpacing: "0.18em",
            textTransform: "uppercase",
            color: palette.navySoft,
            marginBottom: 14,
          }}
        >
          {section.eyebrow}
        </div>
        <div
          style={{
            fontFamily: displayFont,
            fontSize: 76,
            lineHeight: 0.9,
            color: palette.ink,
            marginBottom: 18,
          }}
        >
          {section.title}
        </div>
        <div
          style={{
            fontFamily: bodyFont,
            fontSize: 28,
            lineHeight: 1.42,
            color: "#41495d",
          }}
        >
          {section.body}
        </div>
      </div>
      <div style={{ display: "grid", gridTemplateColumns: "repeat(2, minmax(0, 1fr))", gap: 18 }}>
        {(section.cards || []).map((card, index) => (
          <SignalCard key={`${card.label}-${index}`} card={card} index={index} />
        ))}
      </div>
    </div>
  );
};

const ShowcaseScene = ({ section }) => (
  <div style={{ flex: 1, padding: "166px 94px 162px", display: "grid", gridTemplateColumns: "1.1fr 0.82fr", gap: 24 }}>
    <BrowserShell label={section.title} rightLabel={section.eyebrow}>
      <div style={{ display: "grid", gridTemplateColumns: "repeat(2, minmax(0, 1fr))", gap: 16 }}>
        {(section.cards || []).map((card, index) => (
          <SignalCard key={`${card.symbol || card.label}-${index}`} card={card} index={index} />
        ))}
      </div>
    </BrowserShell>
    <InfoPanel section={section} stats={section.stats} />
  </div>
);

const WorkflowScene = ({ section }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  return (
    <div style={{ flex: 1, padding: "164px 94px 158px", display: "flex", flexDirection: "column", gap: 22 }}>
      <ShellPanel style={{ padding: "28px 32px 30px", ...fadeUpStyle(frame, fps, 0, 22) }}>
        <div
          style={{
            fontFamily: monoFont,
            fontSize: 18,
            letterSpacing: "0.16em",
            textTransform: "uppercase",
            color: palette.navySoft,
            marginBottom: 14,
          }}
        >
          {section.eyebrow}
        </div>
        <div
          style={{
            fontFamily: displayFont,
            fontSize: 66,
            lineHeight: 0.92,
            color: palette.ink,
            marginBottom: 16,
            maxWidth: 1200,
          }}
        >
          {section.title}
        </div>
        <div
          style={{
            fontFamily: bodyFont,
            fontSize: 24,
            lineHeight: 1.42,
            color: "#41495d",
            maxWidth: 1180,
          }}
        >
          {section.body}
        </div>
      </ShellPanel>
      <StepRail steps={section.steps} />
      <div style={{ display: "grid", gridTemplateColumns: "repeat(4, minmax(0, 1fr))", gap: 16 }}>
        {(section.cards || []).map((card, index) => (
          <SignalCard key={`${card.label}-${index}`} card={card} index={index} />
        ))}
      </div>
    </div>
  );
};

const SourcePill = ({ item, index = 0 }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  return (
    <div
      style={{
        padding: "12px 14px",
        borderRadius: 18,
        background: "rgba(29,43,73,0.06)",
        border: `1px solid ${palette.line}`,
        ...fadeUpStyle(frame, fps, 12 + index * 4, 18),
      }}
    >
      <div
        style={{
          fontFamily: monoFont,
          fontSize: 13,
          letterSpacing: "0.11em",
          textTransform: "uppercase",
          color: palette.navySoft,
          marginBottom: 6,
        }}
      >
        {item.label}
      </div>
      <div
        style={{
          fontFamily: bodyFont,
          fontSize: 17,
          color: palette.ink,
          lineHeight: 1.3,
        }}
      >
        {item.value}
      </div>
    </div>
  );
};

const ChatScene = ({ section }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  return (
    <div style={{ flex: 1, padding: "166px 94px 160px", display: "grid", gridTemplateColumns: "1.05fr 0.86fr", gap: 24 }}>
      <BrowserShell label="Grounded Answer" rightLabel="Cited">
        <div style={{ display: "flex", flexDirection: "column", gap: 18 }}>
          <div
            style={{
              alignSelf: "flex-end",
              maxWidth: "78%",
              padding: "18px 22px",
              borderRadius: "24px 24px 6px 24px",
              background: palette.navy,
              color: palette.white,
              boxShadow: "0 14px 24px rgba(15,23,41,0.18)",
              ...fadeUpStyle(frame, fps, 6, 20),
            }}
          >
            <div
              style={{
                fontFamily: monoFont,
                fontSize: 14,
                letterSpacing: "0.13em",
                textTransform: "uppercase",
                opacity: 0.72,
                marginBottom: 8,
              }}
            >
              Prompt
            </div>
            <div style={{ fontFamily: bodyFont, fontSize: 22, lineHeight: 1.35 }}>{section.prompt}</div>
          </div>
          <div
            style={{
              alignSelf: "flex-start",
              maxWidth: "92%",
              padding: "24px 26px",
              borderRadius: "26px 26px 26px 8px",
              background: palette.white,
              border: `1px solid ${palette.line}`,
              boxShadow: "0 16px 28px rgba(24,25,36,0.08)",
              ...fadeUpStyle(frame, fps, 14, 22),
            }}
          >
            <div
              style={{
                fontFamily: monoFont,
                fontSize: 14,
                letterSpacing: "0.13em",
                textTransform: "uppercase",
                color: palette.navySoft,
                marginBottom: 10,
              }}
            >
              Retrieved Answer
            </div>
            <div style={{ fontFamily: bodyFont, fontSize: 23, lineHeight: 1.48, color: "#374052" }}>{section.answer}</div>
          </div>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(3, minmax(0, 1fr))", gap: 12 }}>
            {(section.sources || []).map((item, index) => (
              <SourcePill key={`${item.label}-${index}`} item={item} index={index} />
            ))}
          </div>
        </div>
      </BrowserShell>
      <InfoPanel section={section} stats={section.stats} />
    </div>
  );
};

const CheckLine = ({ text, index }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  return (
    <div
      style={{
        display: "flex",
        alignItems: "center",
        gap: 14,
        ...fadeUpStyle(frame, fps, 8 + index * 4, 18),
      }}
    >
      <div
        style={{
          width: 28,
          height: 28,
          borderRadius: "50%",
          background: "rgba(46,144,117,0.14)",
          border: "1px solid rgba(46,144,117,0.2)",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          fontFamily: monoFont,
          fontSize: 14,
          color: palette.mint,
        }}
      >
        OK
      </div>
      <div style={{ fontFamily: bodyFont, fontSize: 23, lineHeight: 1.35, color: "#374052" }}>{text}</div>
    </div>
  );
};

const CommandScene = ({ section }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  return (
    <div style={{ flex: 1, padding: "170px 94px 164px", display: "grid", gridTemplateColumns: "0.86fr 1.14fr", gap: 24 }}>
      <InfoPanel section={section} stats={[]} />
      <BrowserShell label="Demo Prep Command" rightLabel="Single Command" accent={palette.mint}>
        <div style={{ display: "grid", gridTemplateColumns: "1fr", gap: 18 }}>
          <div
            style={{
              borderRadius: 26,
              background: palette.navyInk,
              color: palette.white,
              padding: "24px 28px",
              boxShadow: "0 22px 44px rgba(15,23,41,0.22)",
              ...fadeUpStyle(frame, fps, 4, 20),
            }}
          >
            <div
              style={{
                fontFamily: monoFont,
                fontSize: 15,
                letterSpacing: "0.14em",
                textTransform: "uppercase",
                color: "rgba(255,255,255,0.62)",
                marginBottom: 12,
              }}
            >
              Terminal
            </div>
            <div
              style={{
                fontFamily: monoFont,
                fontSize: 34,
                lineHeight: 1.38,
                color: "#f8f4ee",
                wordBreak: "break-word",
              }}
            >
              {section.command}
            </div>
          </div>
          <ShellPanel style={{ padding: "24px 26px" }}>
            <div
              style={{
                fontFamily: monoFont,
                fontSize: 16,
                letterSpacing: "0.14em",
                textTransform: "uppercase",
                color: palette.navySoft,
                marginBottom: 18,
              }}
            >
              What it does
            </div>
            <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
              {(section.checks || []).map((item, index) => (
                <CheckLine key={`${item}-${index}`} text={item} index={index} />
              ))}
            </div>
          </ShellPanel>
        </div>
      </BrowserShell>
    </div>
  );
};

const CloseScene = ({ section, payload }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  return (
    <div
      style={{
        flex: 1,
        padding: "180px 140px 190px",
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        textAlign: "center",
      }}
    >
      <div style={{ maxWidth: 1240, ...fadeUpStyle(frame, fps, 0, 22) }}>
        <div
          style={{
            fontFamily: monoFont,
            fontSize: 20,
            letterSpacing: "0.18em",
            textTransform: "uppercase",
            color: palette.navySoft,
            marginBottom: 16,
          }}
        >
          {section.eyebrow}
        </div>
        <div
          style={{
            fontFamily: displayFont,
            fontSize: 92,
            lineHeight: 0.9,
            color: palette.ink,
            marginBottom: 24,
          }}
        >
          {section.title}
        </div>
        <div
          style={{
            fontFamily: bodyFont,
            fontSize: 30,
            lineHeight: 1.46,
            color: "#41495d",
            marginBottom: 30,
          }}
        >
          {section.body}
        </div>
      </div>
      <div style={{ display: "flex", flexWrap: "wrap", justifyContent: "center", gap: 14, marginBottom: 22 }}>
        {(section.bullets || []).map((item, index) => (
          <div
            key={`${item}-${index}`}
            style={{
              padding: "14px 20px",
              borderRadius: 999,
              background: "rgba(255,253,250,0.8)",
              border: `1px solid ${palette.line}`,
              boxShadow: palette.shadow,
              fontFamily: bodyFont,
              fontSize: 22,
              color: palette.ink,
              ...fadeUpStyle(frame, fps, 10 + index * 4, 18),
            }}
          >
            {item}
          </div>
        ))}
      </div>
      <div
        style={{
          padding: "16px 22px",
          borderRadius: 999,
          background: palette.navy,
          color: palette.white,
          fontFamily: monoFont,
          fontSize: 18,
          letterSpacing: "0.14em",
          textTransform: "uppercase",
          boxShadow: palette.shadowHeavy,
        }}
      >
        {payload.brand?.name} | Demo-ready today
      </div>
    </div>
  );
};

const SceneRenderer = ({ section, payload }) => {
  if (section.type === "hero") {
    return <HeroScene section={section} payload={payload} />;
  }
  if (section.type === "overview") {
    return <OverviewScene section={section} />;
  }
  if (section.type === "workflow") {
    return <WorkflowScene section={section} />;
  }
  if (section.type === "chat") {
    return <ChatScene section={section} />;
  }
  if (section.type === "command") {
    return <CommandScene section={section} />;
  }
  if (section.type === "close") {
    return <CloseScene section={section} payload={payload} />;
  }
  return <ShowcaseScene section={section} />;
};

const PersistentChrome = ({ payload, section, sectionIndex, sectionCount, progress }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const barGrow = interpolate(progress, [0, 1], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  return (
    <>
      <div
        style={{
          position: "absolute",
          top: 42,
          left: 52,
          right: 52,
          padding: "18px 22px",
          borderRadius: 999,
          background: "rgba(255,253,250,0.78)",
          border: `1px solid ${palette.line}`,
          boxShadow: palette.shadow,
          display: "grid",
          gridTemplateColumns: "auto 1fr auto",
          alignItems: "center",
          gap: 20,
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: 14 }}>
          <div
            style={{
              width: 54,
              height: 54,
              borderRadius: 18,
              background: palette.navy,
              color: palette.white,
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              fontFamily: monoFont,
              fontSize: 20,
              letterSpacing: "0.12em",
            }}
          >
            OR
          </div>
          <div>
            <div
              style={{
                fontFamily: monoFont,
                fontSize: 16,
                letterSpacing: "0.14em",
                textTransform: "uppercase",
                color: palette.navySoft,
                marginBottom: 4,
              }}
            >
              {payload.brand?.tagline}
            </div>
            <div
              style={{
                fontFamily: bodyFont,
                fontSize: 28,
                color: palette.ink,
                fontWeight: 600,
              }}
            >
              {payload.brand?.name}
            </div>
          </div>
        </div>
        <div style={{ display: "flex", justifyContent: "center", gap: 12 }}>
          {(payload.tabs || []).map((tab, index) => {
            const active = tab.key === section.active_tab;
            const progressIn = enter(frame, fps, index * 2);
            return (
              <div
                key={tab.key}
                style={{
                  padding: "14px 20px",
                  borderRadius: 999,
                  background: active ? palette.navy : "rgba(29,43,73,0.04)",
                  color: active ? palette.white : palette.navy,
                  border: active ? "1px solid rgba(29,43,73,0.4)" : `1px solid ${palette.line}`,
                  boxShadow: active ? "0 18px 30px rgba(29,43,73,0.22)" : "none",
                  fontFamily: monoFont,
                  fontSize: 15,
                  letterSpacing: "0.12em",
                  textTransform: "uppercase",
                  transform: `translateY(${(1 - progressIn) * 8}px)`,
                  opacity: progressIn,
                }}
              >
                {tab.label}
              </div>
            );
          })}
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
          <div
            style={{
              padding: "12px 16px",
              borderRadius: 999,
              background: "rgba(46,144,117,0.1)",
              border: "1px solid rgba(46,144,117,0.18)",
              color: palette.mint,
              fontFamily: monoFont,
              fontSize: 14,
              letterSpacing: "0.12em",
              textTransform: "uppercase",
            }}
          >
            1080p | {titleCase(payload.audio?.voice || "Ash")}
          </div>
          <div
            style={{
              padding: "12px 16px",
              borderRadius: 999,
              background: "rgba(29,43,73,0.08)",
              border: `1px solid ${palette.line}`,
              color: palette.navy,
              fontFamily: monoFont,
              fontSize: 14,
              letterSpacing: "0.12em",
              textTransform: "uppercase",
            }}
          >
            {String(sectionIndex + 1).padStart(2, "0")} / {String(sectionCount).padStart(2, "0")}
          </div>
        </div>
      </div>
      <div
        style={{
          position: "absolute",
          left: 54,
          right: 54,
          bottom: 48,
          display: "grid",
          gridTemplateColumns: "1fr auto",
          gap: 20,
          alignItems: "end",
        }}
      >
        <div
          style={{
            padding: "18px 24px 20px",
            borderRadius: 28,
            background: "rgba(17, 24, 39, 0.88)",
            boxShadow: palette.shadowHeavy,
            color: "#f8f4ee",
          }}
        >
          <div
            style={{
              fontFamily: monoFont,
              fontSize: 14,
              letterSpacing: "0.14em",
              textTransform: "uppercase",
              opacity: 0.7,
              marginBottom: 8,
            }}
          >
            Narration
          </div>
          <div style={{ fontFamily: bodyFont, fontSize: 24, lineHeight: 1.38 }}>{section.voiceover}</div>
        </div>
        <div
          style={{
            width: 290,
            padding: "16px 18px",
            borderRadius: 24,
            background: "rgba(255,253,250,0.8)",
            border: `1px solid ${palette.line}`,
            boxShadow: palette.shadow,
          }}
        >
          <div
            style={{
              fontFamily: monoFont,
              fontSize: 14,
              letterSpacing: "0.13em",
              textTransform: "uppercase",
              color: palette.navySoft,
              marginBottom: 10,
            }}
          >
            Progress
          </div>
          <div
            style={{
              height: 12,
              borderRadius: 999,
              background: "rgba(29,43,73,0.08)",
              overflow: "hidden",
              marginBottom: 10,
            }}
          >
            <div
              style={{
                height: "100%",
                width: `${barGrow * 100}%`,
                borderRadius: 999,
                background: `linear-gradient(90deg, ${palette.coral}, ${palette.mint})`,
              }}
            />
          </div>
          <div
            style={{
              fontFamily: bodyFont,
              fontSize: 18,
              color: "#3f485e",
            }}
          >
            Disclosure {payload.source_runs?.disclosure_run_label} | Chart {payload.source_runs?.chart_run_label}
          </div>
        </div>
      </div>
    </>
  );
};

export const ProductDemoWalkthrough = ({ payload = demoSamplePayload }) => {
  const frame = useCurrentFrame();
  const { durationInFrames } = useVideoConfig();
  const sections = sectionOffsets(payload.sections || demoSamplePayload.sections);
  const matchedIndex = sections.findIndex(
    (section) => frame >= section.from && frame < section.from + Number(section.duration_frames || 0),
  );
  const activeIndex = matchedIndex >= 0 ? matchedIndex : 0;
  const activeSection = sections[activeIndex] || demoSamplePayload.sections[0];
  const preparedAudio =
    payload.audio?.available && payload.audio?.static_path ? payload.audio : demoSamplePayload.audio?.available ? demoSamplePayload.audio : null;
  const progress = durationInFrames <= 1 ? 0 : frame / (durationInFrames - 1);

  return (
    <AbsoluteFill style={{ background: palette.paper }}>
      <Atmosphere />
      {preparedAudio?.available && preparedAudio?.static_path ? <Audio src={staticFile(preparedAudio.static_path)} /> : null}
      {sections.map((section) => (
        <Sequence key={section.id} from={section.from} durationInFrames={section.duration_frames}>
          <AbsoluteFill>
            <SceneRenderer section={section} payload={payload} />
          </AbsoluteFill>
        </Sequence>
      ))}
      <PersistentChrome
        payload={payload}
        section={activeSection}
        sectionIndex={activeIndex}
        sectionCount={sections.length}
        progress={progress}
      />
    </AbsoluteFill>
  );
};

export default ProductDemoWalkthrough;
