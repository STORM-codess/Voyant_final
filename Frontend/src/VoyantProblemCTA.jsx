import React, { useRef, useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";

// Voyant — Problem section + closing CTA band. Forest/sage/gold theme.
// Honest: shows the group-chat-chaos pain, then a clean call to action.

const C = {
  forest: "#2F5D50", sage: "#7BA697", sageDeep: "#4E7C6C",
  gold: "#E0A458", goldDeep: "#C98A3C",
  cream: "#F7F3EA", surface: "#FFFFFF",
  ink: "#243B34", textSoft: "#5E726B",
  sageWash: "#E6EEEA", line: "#DCE6E1",
};

function useInView(threshold = 0.2) {
  const ref = useRef(null);
  const [seen, setSeen] = useState(false);
  useEffect(() => {
    const el = ref.current; if (!el) return;
    const obs = new IntersectionObserver(([e]) => { if (e.isIntersecting) { setSeen(true); obs.disconnect(); } }, { threshold });
    obs.observe(el); return () => obs.disconnect();
  }, [threshold]);
  return [ref, seen];
}

// the messy "group chat" mock that illustrates the pain
const CHAT = [
  { who: "Riya", side: "l", text: "guys where are we going for the long weekend??", c: "#7BA697" },
  { who: "Arjun", side: "l", text: "beach!! goa 🏖️", c: "#E0A458" },
  { who: "Meera", side: "r", text: "ugh goa again? let's do manali", c: "#8FB8A8" },
  { who: "Sam", side: "l", text: "i can't do those dates btw", c: "#C98A3C" },
  { who: "Riya", side: "l", text: "ok someone just decide 😩", c: "#7BA697" },
  { who: "Arjun", side: "l", text: "...", c: "#E0A458" },
];

function ProblemSection() {
  const [textRef, textSeen] = useInView();
  const [chatRef, chatSeen] = useInView(0.15);
  return (
    <section style={{ background: C.surface, padding: "100px 32px", fontFamily: "'Inter', system-ui, sans-serif" }}>
      <link href="https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,500;9..144,600;9..144,700&family=Caveat:wght@600;700&family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet" />
      <div style={{ maxWidth: 1040, margin: "0 auto", display: "grid", gridTemplateColumns: "1fr 1fr", gap: 60, alignItems: "center" }}>
        {/* left: the words */}
        <div ref={textRef} style={{
          opacity: textSeen ? 1 : 0, transform: textSeen ? "translateY(0)" : "translateY(22px)",
          transition: "opacity 600ms ease-out, transform 600ms cubic-bezier(0.22,1,0.36,1)",
        }}>
          <div style={{ font: "700 0.78rem system-ui", letterSpacing: "0.18em", color: C.gold, textTransform: "uppercase", marginBottom: 16 }}>The problem</div>
          <h2 style={{ font: "600 2.9rem 'Fraunces', serif", color: C.forest, margin: 0, letterSpacing: "-0.015em", lineHeight: 1.08 }}>
            Planning a group trip<br />shouldn't feel like{" "}
            <span style={{ fontFamily: "'Caveat', cursive", fontWeight: 700, color: C.gold, fontSize: "1.15em" }}>herding cats.</span>
          </h2>
          <p style={{ font: "400 1.05rem system-ui", color: C.textSoft, lineHeight: 1.7, margin: "22px 0 0", maxWidth: 420 }}>
            Everyone has different budgets, dates, and dream destinations. The loudest voice wins, half the group goes quiet, and the plan slowly dies in the chat.
          </p>
          <p style={{ font: "600 1.05rem system-ui", color: C.forest, lineHeight: 1.6, margin: "20px 0 0" }}>
            Voyant turns that mess into one fair, simple decision.
          </p>
        </div>

        {/* right: messy chat mock */}
        <div ref={chatRef} style={{ background: C.cream, borderRadius: 22, padding: "24px 22px", border: `1px solid ${C.line}`, boxShadow: "0 16px 40px rgba(36,59,52,0.1)" }}>
          <div style={{ font: "600 0.72rem system-ui", color: C.textSoft, textTransform: "uppercase", letterSpacing: "0.08em", marginBottom: 16, textAlign: "center" }}>
            🌴 Trip Squad · 6 members
          </div>
          {CHAT.map((m, i) => (
            <div key={i} style={{
              display: "flex", justifyContent: m.side === "r" ? "flex-end" : "flex-start", marginBottom: 10,
              opacity: chatSeen ? 1 : 0, transform: chatSeen ? "translateY(0)" : "translateY(10px)",
              transition: `opacity 400ms ease-out ${i*110}ms, transform 400ms ease-out ${i*110}ms`,
            }}>
              <div style={{ maxWidth: "78%" }}>
                {m.side === "l" && <div style={{ font: "600 0.66rem system-ui", color: m.c, marginBottom: 3, marginLeft: 4 }}>{m.who}</div>}
                <div style={{
                  background: m.side === "r" ? C.sageDeep : C.surface,
                  color: m.side === "r" ? "#fff" : C.ink,
                  font: "400 0.86rem system-ui", padding: "9px 13px",
                  borderRadius: 14, border: m.side === "r" ? "none" : `1px solid ${C.line}`,
                  lineHeight: 1.4,
                }}>{m.text}</div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

function CTABand() {
  const [ref, seen] = useInView();
  const navigate = useNavigate();
  return (
    <section style={{ background: C.cream, padding: "40px 32px 90px", fontFamily: "system-ui, sans-serif" }}>
      <div ref={ref} style={{
        maxWidth: 980, margin: "0 auto", borderRadius: 28, padding: "64px 40px", textAlign: "center",
        background: `linear-gradient(135deg, ${C.forest} 0%, ${C.sageDeep} 100%)`,
        position: "relative", overflow: "hidden",
        opacity: seen ? 1 : 0, transform: seen ? "translateY(0)" : "translateY(24px)",
        transition: "opacity 600ms ease-out, transform 600ms cubic-bezier(0.22,1,0.36,1)",
      }}>
        {/* soft decorative circles */}
        <div style={{ position: "absolute", top: -40, right: -20, width: 160, height: 160, borderRadius: "50%", background: C.gold, opacity: 0.18 }} />
        <div style={{ position: "absolute", bottom: -50, left: -10, width: 140, height: 140, borderRadius: "50%", background: C.sage, opacity: 0.25 }} />
        <h2 style={{ font: "600 2.8rem 'Fraunces', serif", color: "#fff", margin: 0, letterSpacing: "-0.015em", lineHeight: 1.1, position: "relative" }}>
          Your next{" "}
          <span style={{ fontFamily: "'Caveat', cursive", fontWeight: 700, color: C.gold, fontSize: "1.2em" }}>adventure</span><br />is one vote away.
        </h2>
        <p style={{ font: "400 1.05rem system-ui", color: "rgba(255,255,255,0.85)", margin: "16px auto 0", maxWidth: 420, lineHeight: 1.6, position: "relative" }}>
          Start a trip, invite your friends, and let the group decide — together.
        </p>
        <button onClick={() => navigate("/auth")} style={{
          border: "none", background: C.gold, color: "#3A2A12", font: "700 1rem system-ui",
          padding: "16px 38px", borderRadius: 99, cursor: "pointer", marginTop: 30, position: "relative",
          boxShadow: "0 12px 30px rgba(224,164,88,0.4)",
        }}>
          Start a trip — free
        </button>
      </div>
    </section>
  );
}

export { ProblemSection, CTABand };

export default function VoyantProblemCTA() {
  return (<><ProblemSection /><CTABand /></>);
}