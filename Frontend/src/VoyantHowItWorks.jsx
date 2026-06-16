import React, { useRef, useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { ClipboardList, Compass, Sparkles, Vote } from "lucide-react";

// Voyant — "How recommendations are made" as a journey.
// Forest/sage + warm gold nature theme. STATIC winding trail whose
// nodes line up with each stop. Stops alternate sides. Gentle
// scroll-reveal fade (not path-draw). Warm placeholders for visuals.

const C = {
  forest: "#2F5D50", sage: "#7BA697", sageDeep: "#4E7C6C",
  gold: "#E0A458", goldDeep: "#C98A3C",
  cream: "#F7F3EA", surface: "#FFFFFF",
  ink: "#243B34", textSoft: "#5E726B",
  sageWash: "#E6EEEA", line: "#DCE6E1",
};

const STOPS = [
  { tag: "Step 01", title: "Everyone shares what they want", desc: "Each friend fills a quick form — budget, vibe, dates that work, places they'd rather skip.", grad: ["#8FB8A8", "#4E7C6C"], Icon: ClipboardList, img: null },
  { tag: "Step 02", title: "AI reads the whole group", desc: "Voyant aggregates every answer, weighing shared preferences over any one person's outlier.", grad: ["#7BA697", "#2F5D50"], Icon: Compass, img: null },
  { tag: "Step 03", title: "Smart destinations, generated", desc: "The AI proposes places that fit the group — with reasoning, budgets, and best times to go.", grad: ["#E8C07A", "#E0A458"], Icon: Sparkles, img: null },
  { tag: "Step 04", title: "The group votes — fairly", desc: "A ranked-choice vote settles it, so the winner is the place the whole group actually wants.", grad: ["#6FAE91", "#3D6E5C"], Icon: Vote, img: null },
];

const ROW_H = 300; // vertical spacing per stop (matches CSS below)

function useInView(threshold = 0.25) {
  const ref = useRef(null);
  const [seen, setSeen] = useState(false);
  useEffect(() => {
    const el = ref.current; if (!el) return;
    const obs = new IntersectionObserver(([e]) => { if (e.isIntersecting) { setSeen(true); obs.disconnect(); } }, { threshold });
    obs.observe(el); return () => obs.disconnect();
  }, [threshold]);
  return [ref, seen];
}

function Stop({ stop, i }) {
  const left = i % 2 === 0; // even = visual left
  const [ref, seen] = useInView();
  return (
    <div ref={ref} style={{
      display: "grid", gridTemplateColumns: "1fr 1fr", gap: 48, alignItems: "center",
      height: ROW_H, position: "relative",
      opacity: seen ? 1 : 0, transform: seen ? "translateY(0)" : "translateY(28px)",
      transition: "opacity 600ms ease-out, transform 600ms cubic-bezier(0.22,1,0.36,1)",
    }}>
      <div style={{
        order: left ? 0 : 1, height: 200, borderRadius: 20, position: "relative", overflow: "hidden",
        background: stop.img
          ? `linear-gradient(140deg, rgba(36,59,52,0.25), rgba(36,59,52,0.45)), url(${stop.img}) center/cover`
          : `linear-gradient(140deg, ${stop.grad[0]}, ${stop.grad[1]})`,
        boxShadow: "0 16px 38px rgba(36,59,52,0.16)",
      }}>
        <div style={{ position: "absolute", top: 16, left: 16, width: 46, height: 46, borderRadius: 12, background: "rgba(255,255,255,0.9)", display: "grid", placeItems: "center" }}><stop.Icon size={22} strokeWidth={2} color={stop.grad[1]} /></div>
      </div>
      <div style={{ order: left ? 1 : 0, textAlign: left ? "left" : "right" }}>
        <div style={{ font: "700 0.74rem system-ui", letterSpacing: "0.16em", color: C.gold, textTransform: "uppercase", marginBottom: 10 }}>{stop.tag}</div>
        <div style={{ font: "600 1.65rem 'Fraunces', serif", color: C.forest, letterSpacing: "-0.005em", lineHeight: 1.15, marginBottom: 10 }}>{stop.title}</div>
        <div style={{ font: "400 0.98rem system-ui", color: C.textSoft, lineHeight: 1.65, maxWidth: 340, marginLeft: left ? 0 : "auto" }}>{stop.desc}</div>
      </div>
    </div>
  );
}

export default function VoyantHowItWorks() {
  const navigate = useNavigate();
  // Build a static S-curve whose bends sit at each row's vertical center.
  // Nodes alternate near the central column; the path weaves between them.
  const n = STOPS.length;
  const H = ROW_H * n;
  const cx = 400; // svg center x (viewBox 800 wide)
  const amp = 150; // how far the curve swings
  let d = `M ${cx} 0`;
  for (let i = 0; i < n; i++) {
    const yMid = ROW_H * i + ROW_H / 2;
    const yEnd = ROW_H * (i + 1);
    const swing = i % 2 === 0 ? cx - amp : cx + amp; // toward the visual side
    d += ` Q ${swing} ${yMid - ROW_H / 4}, ${swing} ${yMid}`;
    d += ` Q ${swing} ${yMid + ROW_H / 4}, ${cx} ${yEnd}`;
  }

  return (
    <section style={{ background: C.cream, padding: "100px 32px 90px", fontFamily: "'Inter', system-ui, sans-serif", position: "relative", overflow: "hidden" }}>
      <link href="https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,500;9..144,600;9..144,700&family=Caveat:wght@600;700&family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet" />
      <div style={{ textAlign: "center", marginBottom: 70, position: "relative", zIndex: 2 }}>
        <div style={{ font: "700 0.78rem system-ui", letterSpacing: "0.18em", color: C.gold, textTransform: "uppercase", marginBottom: 14 }}>How it works</div>
        <h2 style={{ font: "600 2.9rem 'Fraunces', serif", color: C.forest, margin: 0, letterSpacing: "-0.015em", lineHeight: 1.05 }}>
          From group chaos to{" "}
          <span style={{ fontFamily: "'Caveat', cursive", fontWeight: 700, color: C.gold, fontSize: "1.15em" }}>one perfect plan.</span>
        </h2>
        <p style={{ font: "400 1.05rem system-ui", color: C.textSoft, maxWidth: 480, margin: "16px auto 0", lineHeight: 1.6 }}>
          Follow the route — here's how Voyant turns everyone's wishes into a destination you'll all love.
        </p>
      </div>

      <div style={{ position: "relative", maxWidth: 980, margin: "0 auto" }}>
        {/* static winding trail behind the stops */}
        <svg viewBox={`0 0 800 ${H}`} preserveAspectRatio="none" style={{ position: "absolute", inset: 0, width: "100%", height: "100%", zIndex: 0, pointerEvents: "none" }}>
          <path d={d} fill="none" stroke={C.sage} strokeWidth="2.5" strokeDasharray="2 9" strokeLinecap="round" opacity="0.7" />
          {STOPS.map((_, i) => {
            const y = ROW_H * i + ROW_H / 2;
            return (
              <g key={i}>
                <circle cx={cx} cy={y} r="11" fill={C.cream} stroke={C.gold} strokeWidth="3" />
                <circle cx={cx} cy={y} r="4" fill={C.gold} />
              </g>
            );
          })}
        </svg>

        <div style={{ position: "relative", zIndex: 1 }}>
          {STOPS.map((s, i) => <Stop key={i} stop={s} i={i} />)}
        </div>

        {/* deeper-dive link to the AI engineering showcase */}
        <div style={{ textAlign: "center", marginTop: 24 }}>
          <span onClick={() => navigate("/how-ai")} style={{ font: "600 0.92rem 'Inter'", color: C.goldDeep || C.gold, cursor: "pointer", borderBottom: `2px solid ${C.gold}`, paddingBottom: 2 }}>
            See the AI engineering behind it →
          </span>
        </div>
      </div>
    </section>
  );
}