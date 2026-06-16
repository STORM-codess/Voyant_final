import React, { useState } from "react";
import { useNavigate, useLocation } from "react-router-dom";
import { Sparkles } from "lucide-react";

// Voyant — a small distinctive right-edge tab that "peeks" in, inviting
// visitors to the AI-engineering showcase. Shown on public marketing pages
// only (hidden on /how-ai itself and on the signed-in app routes).

const C = {
  forest: "#2F5D50", forestDeep: "#21443A", gold: "#E0A458", goldSoft: "#F0C97E",
};

// routes where the tab should NOT appear
const HIDE_ON = ["/how-ai", "/auth", "/dashboard", "/create", "/trip", "/plan"];

export default function AIPeekTab() {
  const navigate = useNavigate();
  const location = useLocation();
  const [hover, setHover] = useState(false);

  const hidden = HIDE_ON.some((p) => location.pathname === p || location.pathname.startsWith(p + "/"));
  if (hidden) return null;

  return (
    <div
      onClick={() => navigate("/how-ai")}
      onMouseEnter={() => setHover(true)}
      onMouseLeave={() => setHover(false)}
      role="button"
      title="See how our AI works"
      style={{
        position: "fixed",
        right: 0,
        top: "42%",
        transform: `translateY(-50%) translateX(${hover ? "0" : "10px"})`,
        transition: "transform 260ms cubic-bezier(0.34,1.56,0.64,1), box-shadow 260ms ease",
        zIndex: 50,
        cursor: "pointer",
        display: "flex",
        alignItems: "center",
        gap: 9,
        padding: "14px 16px 14px 18px",
        background: `linear-gradient(150deg, ${C.forest}, ${C.forestDeep})`,
        color: "#fff",
        borderRadius: "16px 0 0 16px",
        boxShadow: hover
          ? "-8px 0 28px rgba(33,68,58,0.35)"
          : "-4px 0 18px rgba(33,68,58,0.22)",
        writingMode: "vertical-rl",
        textOrientation: "mixed",
        fontFamily: "'Inter', system-ui, sans-serif",
      }}
    >
      {/* subtle pulsing dot to draw the eye */}
      <span style={{ position: "relative", width: 18, height: 18, display: "grid", placeItems: "center" }}>
        <span style={{
          position: "absolute", inset: 0, borderRadius: "50%",
          background: C.gold, opacity: 0.35,
          animation: "voyantPeekPulse 2.4s ease-out infinite",
        }} />
        <Sparkles size={14} color={C.goldSoft} style={{ transform: "rotate(90deg)" }} />
      </span>
      <span style={{ font: "700 0.82rem 'Inter'", letterSpacing: "0.04em" }}>
        How our AI works
      </span>

      <style>{`
        @keyframes voyantPeekPulse {
          0%   { transform: scale(1);   opacity: 0.45; }
          70%  { transform: scale(2.2); opacity: 0;    }
          100% { transform: scale(2.2); opacity: 0;    }
        }
      `}</style>
    </div>
  );
}
