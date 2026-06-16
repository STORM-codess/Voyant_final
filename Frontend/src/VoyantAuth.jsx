import React, { useState, useRef, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "./AuthContext";
import { ArrowLeft } from "lucide-react";

// Voyant — Auth page. Split layout: auth card LEFT, INTERACTIVE
// particle-constellation panel RIGHT (reacts to the mouse).
// Google-only sign-in, login/register toggle, green/gold theme.
//
// WIRING: replace handleGoogle() with Firebase signInWithPopup.

const C = {
  forest: "#2F5D50", forestDeep: "#1B3B32", sage: "#7BA697", sageDeep: "#4E7C6C",
  gold: "#E0A458", goldDeep: "#C98A3C",
  cream: "#F7F3EA", surface: "#FFFFFF",
  ink: "#243B34", textSoft: "#5E726B", line: "#DCE6E1",
};

// Ripple panel: click (or move) to send out concentric rings that
// expand and fade, like drops on water. Green/gold forest panel.
function RipplePanel() {
  const wrapRef = useRef(null);
  const [ripples, setRipples] = useState([]);
  const idRef = useRef(0);
  const lastMove = useRef(0);

  const addRipple = (e, big) => {
    const r = wrapRef.current.getBoundingClientRect();
    const x = e.clientX - r.left, y = e.clientY - r.top;
    const id = idRef.current++;
    setRipples((rs) => [...rs, { id, x, y, big }]);
    setTimeout(() => setRipples((rs) => rs.filter((p) => p.id !== id)), 2000);
  };

  const onClick = (e) => addRipple(e, true);
  const onMove = (e) => {
    const now = Date.now();
    if (now - lastMove.current > 220) {
      lastMove.current = now;
      addRipple(e, false);
    }
  };

  return (
    <div ref={wrapRef} onClick={onClick} onMouseMove={onMove}
      style={{ position: "relative", height: "100%", minHeight: 480, overflow: "hidden", cursor: "pointer",
        background: `radial-gradient(120% 100% at 70% 30%, ${C.sageDeep} 0%, ${C.forest} 45%, ${C.forestDeep} 100%)` }}>
      <style>{`
        @keyframes rippleExpand {
          0%   { transform: translate(-50%,-50%) scale(0); opacity: 0.55; }
          100% { transform: translate(-50%,-50%) scale(1); opacity: 0; }
        }
      `}</style>

      {ripples.map((p) => (
        <span key={p.id} style={{
          position: "absolute", left: p.x, top: p.y,
          width: p.big ? 520 : 260, height: p.big ? 520 : 260,
          borderRadius: "50%",
          border: `2px solid ${p.big ? C.gold : "rgba(255,255,255,0.6)"}`,
          animation: "rippleExpand 2s ease-out forwards",
          pointerEvents: "none",
        }} />
      ))}

      {/* faint ambient ripples so it's alive before interaction */}
      <span style={{ position: "absolute", left: "60%", top: "40%", width: 400, height: 400, borderRadius: "50%", border: `1.5px solid rgba(224,164,88,0.3)`, animation: "rippleExpand 6s ease-out infinite", pointerEvents: "none" }} />
      <span style={{ position: "absolute", left: "35%", top: "65%", width: 360, height: 360, borderRadius: "50%", border: `1.5px solid rgba(255,255,255,0.2)`, animation: "rippleExpand 7s ease-out infinite 2s", pointerEvents: "none" }} />

      <div style={{ position: "absolute", left: 44, bottom: 46, color: "#fff", pointerEvents: "none" }}>
        <div style={{ fontFamily: "'Caveat', cursive", fontWeight: 700, fontSize: "1.7rem", color: C.gold, marginBottom: 6 }}>
          Where to next?
        </div>
        <h2 style={{ font: "600 1.7rem 'Fraunces', serif", margin: 0, lineHeight: 1.2, maxWidth: 320, textShadow: "0 2px 16px rgba(0,0,0,0.3)" }}>
          Plan the trip your whole group agrees on.
        </h2>
      </div>
    </div>
  );
}

// Magnetic metaballs: blobs drift and are pulled toward the cursor; an
// SVG gooey filter makes them MERGE when close and SPLIT as they part,
// with liquid connecting bridges. Green/gold on a forest panel.
function MetaballPanel() {
  const wrapRef = useRef(null);
  const blobsRef = useRef(null);

  useEffect(() => {
    const wrap = wrapRef.current;
    if (!wrap) return;

    // blob definitions: base position (0..1), drift params, size, color
    const defs = [
      { bx: 0.30, by: 0.30, r: 150, color: "#7BA697", ax: 0.10, ay: 0.08, sx: 0.7, sy: 0.5, mag: 0.5 },
      { bx: 0.62, by: 0.40, r: 175, color: "#2F5D50", ax: 0.12, ay: 0.10, sx: 0.5, sy: 0.8, mag: 0.35 },
      { bx: 0.45, by: 0.65, r: 130, color: "#E0A458", ax: 0.09, ay: 0.11, sx: 0.9, sy: 0.6, mag: 0.7 },
      { bx: 0.70, by: 0.70, r: 145, color: "#4E7C6C", ax: 0.11, ay: 0.07, sx: 0.6, sy: 0.9, mag: 0.45 },
      { bx: 0.25, by: 0.72, r: 120, color: "#E0A458", ax: 0.08, ay: 0.09, sx: 0.8, sy: 0.7, mag: 0.6 },
    ];
    const nodes = blobsRef.current.children;
    let raf, t = 0;

    const tick = () => {
      const W = wrap.clientWidth, H = wrap.clientHeight;
      t += 0.005;
      for (let i = 0; i < defs.length; i++) {
        const d = defs[i];
        // autonomous drift only (no cursor interaction)
        const x = (d.bx + Math.sin(t * d.sx + i) * d.ax) * W;
        const y = (d.by + Math.cos(t * d.sy + i) * d.ay) * H;
        const n = nodes[i];
        n.style.transform = `translate(${x - d.r / 2}px, ${y - d.r / 2}px)`;
      }
      raf = requestAnimationFrame(tick);
    };
    tick();

    return () => { cancelAnimationFrame(raf); };
  }, []);

  const defs = [
    { r: 150, color: "#7BA697" }, { r: 175, color: "#2F5D50" }, { r: 130, color: "#E0A458" },
    { r: 145, color: "#4E7C6C" }, { r: 120, color: "#E0A458" },
  ];

  return (
    <div ref={wrapRef}
      style={{ position: "relative", height: "100%", minHeight: 480, overflow: "hidden", background: `linear-gradient(150deg, ${C.forestDeep}, ${C.forest})` }}>
      {/* SVG gooey filter */}
      <svg style={{ position: "absolute", width: 0, height: 0 }}>
        <defs>
          <filter id="goo">
            <feGaussianBlur in="SourceGraphic" stdDeviation="16" result="blur" />
            <feColorMatrix in="blur" mode="matrix" values="1 0 0 0 0  0 1 0 0 0  0 0 1 0 0  0 0 0 22 -10" result="goo" />
            <feBlend in="SourceGraphic" in2="goo" />
          </filter>
        </defs>
      </svg>

      {/* blob layer with the gooey filter applied */}
      <div ref={blobsRef} style={{ position: "absolute", inset: 0, filter: "url(#goo)" }}>
        {defs.map((d, i) => (
          <div key={i} style={{
            position: "absolute", top: 0, left: 0,
            width: d.r, height: d.r, borderRadius: "50%",
            background: d.color, willChange: "transform",
          }} />
        ))}
      </div>

      {/* copy */}
      <div style={{ position: "absolute", left: 44, bottom: 46, color: "#fff", pointerEvents: "none" }}>
        <div style={{ fontFamily: "'Caveat', cursive", fontWeight: 700, fontSize: "1.7rem", color: C.gold, marginBottom: 6 }}>
          Where to next?
        </div>
        <h2 style={{ font: "600 1.7rem 'Fraunces', serif", margin: 0, lineHeight: 1.2, maxWidth: 320, textShadow: "0 2px 16px rgba(0,0,0,0.3)" }}>
          Plan the trip your whole group agrees on.
        </h2>
      </div>
    </div>
  );
}

// ── Pick the right-panel visual here: <RipplePanel /> or <MetaballPanel /> ──
function VisualPanel() {
  return <MetaballPanel />;
}

export default function VoyantAuth() {
  const navigate = useNavigate();
  const { signInWithGoogle } = useAuth();
  const [mode, setMode] = useState("login");
  const [loading, setLoading] = useState(false);
  const isLogin = mode === "login";

  const copy = isLogin
    ? { eyebrow: "Welcome back", title: "Sign in to Voyant", sub: "Pick up planning right where your group left off.", toggleText: "New to Voyant?", toggleLink: "Create an account" }
    : { eyebrow: "Let's get started", title: "Create your account", sub: "Start planning trips your whole group will actually agree on.", toggleText: "Already have an account?", toggleLink: "Sign in" };

  const [error, setError] = useState("");

  const handleGoogle = async () => {
    setLoading(true);
    setError("");
    try {
      await signInWithGoogle();          // Firebase popup
      // AuthProvider syncs the backend user (GET /users/me or POST register)
      navigate("/dashboard");
    } catch (e) {
      console.error(e);
      setError("Sign-in failed. Please try again.");
      setLoading(false);
    }
  };

  return (
    <div style={{ minHeight: "100vh", background: C.cream, fontFamily: "'Inter', system-ui, sans-serif" }}>
      <link href="https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,500;9..144,600;9..144,700&family=Caveat:wght@600;700&family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet" />

      <div onClick={() => navigate("/")} title="Back to home" style={{ position: "fixed", top: 26, left: 32, display: "flex", alignItems: "center", gap: 7, zIndex: 10, cursor: "pointer" }}>
        <ArrowLeft size={18} color={C.textSoft} />
        <span style={{ font: "600 1.3rem 'Fraunces', serif", color: C.forest }}>Voyant</span>
      </div>

      <div className="auth-split" style={{ display: "grid", gridTemplateColumns: "1fr 1fr", minHeight: "100vh" }}>
        {/* LEFT — auth card */}
        <div style={{ display: "flex", alignItems: "center", justifyContent: "center", padding: "40px" }}>
          <div style={{ width: "100%", maxWidth: 380 }}>
            <div style={{ font: "700 0.74rem 'Inter'", letterSpacing: "0.16em", color: C.gold, textTransform: "uppercase", marginBottom: 14 }}>{copy.eyebrow}</div>
            <h1 style={{ font: "600 2.3rem 'Fraunces', serif", color: C.forest, margin: 0, letterSpacing: "-0.01em", lineHeight: 1.1 }}>{copy.title}</h1>
            <p style={{ font: "400 1rem 'Inter'", color: C.textSoft, lineHeight: 1.6, margin: "12px 0 0", maxWidth: 320 }}>{copy.sub}</p>

            <button onClick={handleGoogle} disabled={loading}
              style={{ width: "100%", marginTop: 30, padding: "15px 20px", borderRadius: 14, border: `1.5px solid ${C.line}`, background: C.surface, cursor: loading ? "default" : "pointer", display: "flex", alignItems: "center", justifyContent: "center", gap: 12, font: "600 0.98rem 'Inter'", color: C.ink, transition: "all 200ms ease-out", opacity: loading ? 0.7 : 1 }}
              onMouseEnter={(e) => { if (!loading) { e.currentTarget.style.borderColor = C.gold; e.currentTarget.style.boxShadow = "0 8px 20px rgba(36,59,52,0.08)"; } }}
              onMouseLeave={(e) => { e.currentTarget.style.borderColor = C.line; e.currentTarget.style.boxShadow = "none"; }}>
              <svg width="20" height="20" viewBox="0 0 48 48">
                <path fill="#EA4335" d="M24 9.5c3.54 0 6.71 1.22 9.21 3.6l6.85-6.85C35.9 2.38 30.47 0 24 0 14.62 0 6.51 5.38 2.56 13.22l7.98 6.19C12.43 13.72 17.74 9.5 24 9.5z"/>
                <path fill="#4285F4" d="M46.98 24.55c0-1.57-.15-3.09-.38-4.55H24v9.02h12.94c-.58 2.96-2.26 5.48-4.78 7.18l7.73 6c4.51-4.18 7.09-10.36 7.09-17.65z"/>
                <path fill="#FBBC05" d="M10.53 28.59c-.48-1.45-.76-2.99-.76-4.59s.27-3.14.76-4.59l-7.98-6.19C.92 16.46 0 20.12 0 24c0 3.88.92 7.54 2.56 10.78l7.97-6.19z"/>
                <path fill="#34A853" d="M24 48c6.48 0 11.93-2.13 15.89-5.81l-7.73-6c-2.15 1.45-4.92 2.3-8.16 2.3-6.26 0-11.57-4.22-13.47-9.91l-7.98 6.19C6.51 42.62 14.62 48 24 48z"/>
              </svg>
              {loading ? "Signing in…" : "Continue with Google"}
            </button>

            {error && <p style={{ font: "500 0.82rem 'Inter'", color: "#C0392B", margin: "12px 0 0" }}>{error}</p>}

            <p style={{ font: "400 0.78rem 'Inter'", color: C.textSoft, lineHeight: 1.5, margin: "16px 0 0", maxWidth: 320 }}>By continuing you agree to Voyant's Terms and Privacy Policy.</p>
            <div style={{ height: 1, background: C.line, margin: "26px 0 18px" }} />
            <div style={{ font: "400 0.9rem 'Inter'", color: C.textSoft }}>
              {copy.toggleText}{" "}
              <span onClick={() => setMode(isLogin ? "register" : "login")} style={{ color: C.goldDeep, fontWeight: 600, cursor: "pointer", textDecoration: "underline", textUnderlineOffset: 3 }}>{copy.toggleLink}</span>
            </div>
          </div>
        </div>

        {/* RIGHT — magnetic metaball blobs */}
        <div className="auth-visual"><VisualPanel /></div>
      </div>

      <style>{`
        @media (max-width: 820px){
          .auth-split{ grid-template-columns: 1fr !important; }
          .auth-visual{ display:none; }
        }
      `}</style>
    </div>
  );
}