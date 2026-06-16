import React, { useState, useEffect, useRef, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import goa from "./assets/Goa.jpg";
import manali from "./assets/Manali.jpg";
import mumbai from "./assets/Mumbai.jpg";
import kerala from "./assets/Kerala.jpg";
import kutch from "./assets/Kutch.jpg";
import hampta_pass from "./assets/Hampta_pass.jpg"

// Voyant — Cinematic destination hero with a card->background shared-element
// (FLIP) transition: clicking a card makes that card's image grow to fill the
// full hero background, then commits the new active destination underneath and
// removes the flying overlay (no flicker). Auto-advance and arrows use the same
// transition path so motion is consistent.

const C = {
  forest: "#2F5D50", sage: "#7BA697", sageDeep: "#4E7C6C",
  gold: "#E0A458", goldDeep: "#C98A3C",
  navy: "#243B34", white: "#FFFFFF", ink: "#1A2B26",
  coral: "#E0A458", coralLight: "#E8C07A",
};

const DESTS = [
  { name: "Goa", region: "India · Beaches", grad: ["#E8C07A", "#C98A3C"], img: goa },
  { name: "Manali", region: "Himachal · Mountains", grad: ["#7BA697", "#2F5D50"], img: manali },
  { name: "Mumbai", region: "Maharashtra · City", grad: ["#9CB89A", "#4E7C6C"], img: mumbai },
  { name: "Kerala", region: "India · Backwaters", grad: ["#8FC8A0", "#3E8E6A"], img: kerala },
  { name: "Hampta Pass", region: "Gujrat · Desert", grad: ["#8FC8A0", "#3E8E6A"], img: hampta_pass },
];

const AUTO_MS = 5200;        // time each destination stays before auto-advancing
const MORPH_MS = 900;        // card->background grow duration

// full-bleed background for a destination (darkened for legible overlay text)
const heroBg = (d) =>
  d.img
    ? `linear-gradient(90deg, rgba(20,21,40,0.75) 0%, rgba(20,21,40,0.3) 45%, rgba(20,21,40,0.15) 100%), url(${d.img}) center/cover`
    : `linear-gradient(90deg, rgba(20,21,40,0.78) 0%, rgba(20,21,40,0.35) 50%, rgba(20,21,40,0.2) 100%), linear-gradient(135deg, ${d.grad[0]}, ${d.grad[1]})`;

// background for a small card (bottom-weighted scrim for the card label)
const cardBg = (d) =>
  d.img
    ? `linear-gradient(180deg, rgba(20,21,40,0) 40%, rgba(20,21,40,0.75) 100%), url(${d.img}) center/cover`
    : `linear-gradient(180deg, rgba(20,21,40,0.05) 30%, rgba(20,21,40,0.7) 100%), linear-gradient(150deg, ${d.grad[0]}, ${d.grad[1]})`;

const glassBtn = {
  width: 44, height: 44, borderRadius: 99,
  border: "1.5px solid rgba(255,255,255,0.45)",
  background: "rgba(255,255,255,0.12)", backdropFilter: "blur(8px)",
  WebkitBackdropFilter: "blur(8px)",
  color: "#FFFFFF", cursor: "pointer", fontSize: "1rem",
};

export default function VoyantHero() {
  const navigate = useNavigate();
  const [active, setActive] = useState(0);
  const [loaded, setLoaded] = useState(false);
  const [interacted, setInteracted] = useState(0);

  // FLIP overlay state: a fixed element flies from `from` rect to fullscreen
  const [flier, setFlier] = useState(null); // { dest, from:{top,left,width,height}, grow:bool }
  const cardRefs = useRef({});               // idx -> card DOM node
  const animating = useRef(false);
  const rootRef = useRef(null);
  const [inView, setInView] = useState(true); // hero visible in viewport?

  useEffect(() => { const t = setTimeout(() => setLoaded(true), 80); return () => clearTimeout(t); }, []);

  // pause the auto-advance (and its full-screen morph overlay) whenever the
  // hero is scrolled out of view — otherwise the fixed overlay flashes across
  // the page over other sections when the timer fires.
  useEffect(() => {
    const el = rootRef.current;
    if (!el) return;
    const obs = new IntersectionObserver(
      ([entry]) => setInView(entry.isIntersecting),
      { threshold: 0.35 }
    );
    obs.observe(el);
    return () => obs.disconnect();
  }, []);

  const transitionTo = useCallback((to, sourceRect) => {
    if (animating.current || to === active) return;
    animating.current = true;

    const dest = DESTS[to];
    const from = sourceRect || {
      top: window.innerHeight * 0.55,
      left: window.innerWidth * 0.62,
      width: 190, height: 280,
    };

    // hide the source card immediately so the only thing the eye sees is the
    // overlay growing — making it read as the card ITSELF expanding.
    setFlier({ dest, from, grow: false, flyingIdx: to });

    requestAnimationFrame(() => requestAnimationFrame(() => {
      setFlier((f) => (f ? { ...f, grow: true } : f));
    }));

    setTimeout(() => {
      setActive(to);
      requestAnimationFrame(() => {
        setFlier(null);
        animating.current = false;
      });
    }, MORPH_MS);
  }, [active]);

  // get the live rect of a destination card if it's currently shown
  const rectOf = (idx) => {
    const node = cardRefs.current[idx];
    if (!node) return null;
    const r = node.getBoundingClientRect();
    return { top: r.top, left: r.left, width: r.width, height: r.height };
  };

  useEffect(() => {
    if (!inView) return;        // don't cycle (or flash the overlay) when scrolled away
    const id = setInterval(() => {
      const to = (active + 1) % DESTS.length;
      // the "Up next" card IS the next destination — morph from it
      transitionTo(to, rectOf(to));
    }, AUTO_MS);
    return () => clearInterval(id);
  }, [active, interacted, transitionTo, inView]);

  const selectCard = (idx) => {
    setInteracted((n) => n + 1);
    transitionTo(idx, rectOf(idx));
  };
  const next = () => {
    setInteracted((n) => n + 1);
    const to = (active + 1) % DESTS.length;
    transitionTo(to, rectOf(to));
  };
  const prev = () => {
    setInteracted((n) => n + 1);
    const to = (active - 1 + DESTS.length) % DESTS.length;
    // prev target isn't shown as a card; fly from the last visible card so it
    // still originates from the card row rather than empty background.
    const lastShownIdx = (active + (DESTS.length - 1)) % DESTS.length;
    transitionTo(to, rectOf(lastShownIdx));
  };

  const hero = DESTS[active];

  const reveal = (i) => ({
    opacity: loaded ? 1 : 0,
    transform: loaded ? "translateY(0)" : "translateY(20px)",
    transition: `opacity 700ms ease-out ${i * 120}ms, transform 700ms cubic-bezier(0.22,1,0.36,1) ${i * 120}ms`,
  });
  const enter = (i) => ({ animation: `heroTextIn 820ms cubic-bezier(0.22,1,0.36,1) ${i * 110}ms both` });

  return (
    <div ref={rootRef} style={{
      position: "relative", minHeight: "100vh", overflow: "hidden",
      fontFamily: "'Inter', system-ui, sans-serif", color: C.white, background: "#141528",
    }}>
      <link href="https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,500;9..144,600;9..144,700&family=Caveat:wght@600;700&family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet" />
      <style>{`
        @keyframes heroTextIn {
          0%   { opacity: 0; transform: translateY(28px); filter: blur(5px); }
          100% { opacity: 1; transform: translateY(0);    filter: blur(0); }
        }
        @keyframes heroCardIn {
          0%   { opacity: 0; transform: translateY(24px) scale(0.96); }
          100% { opacity: 1; transform: translateY(0) scale(1); }
        }
        @keyframes heroCardBackIn {
          0%   { opacity: 0; transform: translateY(0) translateX(20px) scale(0.96); }
          100% { opacity: 1; transform: translateY(0) translateX(0) scale(1); }
        }
        @keyframes heroKenBurns {
          0%   { transform: scale(1.06); }
          100% { transform: scale(1.0); }
        }
        @keyframes heroProgress {
          0%   { transform: scaleX(0); }
          100% { transform: scaleX(1); }
        }
      `}</style>

      {/* base background = active destination, slow parallax zoom */}
      <div aria-hidden key={`bg-${active}`} style={{
        position: "absolute", inset: 0, zIndex: 0, background: heroBg(hero),
        transformOrigin: "center", animation: `heroKenBurns ${AUTO_MS + 1500}ms ease-out both`,
        willChange: "transform",
      }} />

      {/* FLIP flying overlay: card image growing into the full background.
          Gated on inView so a fixed overlay can never flash over other sections. */}
      {flier && inView && (
        <div aria-hidden style={{
          position: "fixed", zIndex: 3,
          top: flier.grow ? 0 : flier.from.top,
          left: flier.grow ? 0 : flier.from.left,
          width: flier.grow ? "100vw" : flier.from.width,
          height: flier.grow ? "100vh" : flier.from.height,
          background: flier.grow ? heroBg(flier.dest) : cardBg(flier.dest),
          borderRadius: flier.grow ? 0 : 18,
          boxShadow: flier.grow ? "none" : "0 14px 36px rgba(0,0,0,0.35)",
          transition: `top ${MORPH_MS}ms cubic-bezier(0.7,0,0.2,1), left ${MORPH_MS}ms cubic-bezier(0.7,0,0.2,1), width ${MORPH_MS}ms cubic-bezier(0.7,0,0.2,1), height ${MORPH_MS}ms cubic-bezier(0.7,0,0.2,1), border-radius ${MORPH_MS}ms ease-out`,
          overflow: "hidden", willChange: "top,left,width,height",
        }} />
      )}

      {/* NAVBAR */}
      <header style={{ position: "relative", zIndex: 5, display: "flex", alignItems: "center", justifyContent: "space-between", padding: "26px 52px" }}>
        <div style={{ display: "flex", alignItems: "center", gap: 9 }}>
          <span style={{ font: "600 1.5rem 'Fraunces', serif", letterSpacing: "0.02em" }}>VOYANT</span>
        </div>
        <div style={{ display: "flex", gap: 14, alignItems: "center" }}>
          <span onClick={() => navigate("/auth")} style={{ font: "600 0.8rem system-ui", cursor: "pointer", opacity: 0.9 }}>Sign in</span>
          <button onClick={() => navigate("/auth")} style={{ border: "none", background: C.coral, color: C.white, font: "700 0.8rem system-ui", padding: "9px 18px", borderRadius: 99, cursor: "pointer" }}>Get started</button>
        </div>
      </header>

      {/* HERO CONTENT */}
      <div style={{ position: "relative", zIndex: 4, padding: "60px 52px 0", maxWidth: 640 }}>
        <div key={`region-${active}`} style={{ ...reveal(0), ...enter(0), font: "600 0.82rem system-ui", letterSpacing: "0.22em", textTransform: "uppercase", opacity: 0.85, marginBottom: 16 }}>
          ✦ {hero.region}
        </div>
        <h1 key={`name-${active}`} style={{ ...reveal(1), ...enter(1), font: "600 5rem 'Fraunces', serif", margin: 0, lineHeight: 0.95, letterSpacing: "-0.02em", textTransform: "uppercase", textShadow: "0 4px 30px rgba(0,0,0,0.3)" }}>
          {hero.name}
        </h1>
        <p style={{ ...reveal(2), font: "400 1.05rem system-ui", color: "rgba(255,255,255,0.85)", maxWidth: 400, margin: "22px 0 0", lineHeight: 1.6 }}>
          Picked by your group, decided by a vote. Start planning the trip everyone actually wants.
        </p>
        <div style={{ ...reveal(3), display: "flex", gap: 14, marginTop: 32, alignItems: "center" }}>
          <button onClick={() => navigate("/auth")} style={{ border: "none", background: C.coral, color: C.white, font: "700 0.92rem system-ui", padding: "15px 30px", borderRadius: 99, cursor: "pointer", boxShadow: "0 12px 30px rgba(232,103,76,0.45)" }}>
            Start a trip
          </button>
        </div>
      </div>

      {/* DESTINATION CARD ROW + controls (bottom) */}
      <div style={{ position: "absolute", left: 0, right: 0, bottom: 0, zIndex: 4, padding: "0 52px 40px" }}>
        <div style={{ display: "flex", alignItems: "flex-end", justifyContent: "space-between", gap: 24 }}>
          <div style={{ ...reveal(4), display: "flex", flexDirection: "column", gap: 14, paddingBottom: 8 }}>
            <div style={{ display: "flex", alignItems: "center", gap: 18 }}>
              <div style={{ display: "flex", gap: 10 }}>
                <button onClick={prev} style={glassBtn}>‹</button>
                <button onClick={next} style={glassBtn}>›</button>
              </div>
              <div style={{ font: "300 2.4rem system-ui", letterSpacing: "0.02em", opacity: 0.9 }}>
                {String(active + 1).padStart(2, "0")}
                <span style={{ font: "400 0.9rem system-ui", opacity: 0.6 }}> / {String(DESTS.length).padStart(2, "0")}</span>
              </div>
            </div>
            <div style={{ width: 168, height: 3, borderRadius: 99, background: "rgba(255,255,255,0.22)", overflow: "hidden" }}>
              <div key={`prog-${active}-${interacted}`} style={{
                height: "100%", background: C.gold, transformOrigin: "left",
                animation: `heroProgress ${AUTO_MS}ms linear both`,
              }} />
            </div>
          </div>

          <div style={{ position: "relative", height: 296, width: (DESTS.length - 1) * (190 + 18), overflow: "visible" }}>
            {DESTS.map((d, idx) => {
              // slot = position in the queue (0 = Up next, ... last = just used)
              const slot = (idx - active - 1 + DESTS.length) % DESTS.length;
              const lifted = slot === 0;               // Up next, emphasized
              const isBack = slot === DESTS.length - 1; // last slot = just-cycled card
              const CARD_W = 190, LIFT_W = 200, GAP = 18;
              const left = slot * (CARD_W + GAP);
              return (
                <button
                  key={d.name}
                  ref={(el) => { cardRefs.current[idx] = el; }}
                  onClick={() => selectCard(idx)}
                  style={{
                    position: "absolute", top: 0, left,
                    width: lifted ? LIFT_W : CARD_W, height: lifted ? 296 : 280,
                    borderRadius: 18, border: lifted ? "1.5px solid rgba(224,164,88,0.6)" : "none", cursor: "pointer",
                    background: cardBg(d), backgroundSize: "cover",
                    boxShadow: lifted ? "0 18px 44px rgba(0,0,0,0.45)" : "0 14px 36px rgba(0,0,0,0.35)",
                    overflow: "hidden", textAlign: "left",
                    transform: lifted ? "translateY(-16px)" : "translateY(0)",
                    // the just-cycled card sits at the back: it fades in there
                    // rather than sliding across the row (we kill its left-
                    // transition so it doesn't travel through the others).
                    opacity: isBack ? 0 : 1,
                    animation: isBack ? "heroCardBackIn 620ms ease-out 180ms forwards" : "none",
                    transition: isBack
                      ? "transform 420ms cubic-bezier(0.22,1,0.36,1), width 420ms cubic-bezier(0.22,1,0.36,1), height 420ms cubic-bezier(0.22,1,0.36,1)"
                      : "left 560ms cubic-bezier(0.5,0,0.2,1), transform 420ms cubic-bezier(0.22,1,0.36,1), width 420ms cubic-bezier(0.22,1,0.36,1), height 420ms cubic-bezier(0.22,1,0.36,1), box-shadow 360ms ease",
                    visibility: flier && flier.flyingIdx === idx ? "hidden" : "visible",
                    zIndex: lifted ? 2 : 1,
                  }}
                  onMouseEnter={(e) => (e.currentTarget.style.transform = "translateY(-20px)")}
                  onMouseLeave={(e) => (e.currentTarget.style.transform = lifted ? "translateY(-16px)" : "translateY(0)")}
                >
                  {lifted && (
                    <div style={{ position: "absolute", top: 12, left: 12, font: "600 0.6rem 'Inter'", letterSpacing: "0.1em", textTransform: "uppercase", color: C.navy, background: C.gold, padding: "3px 8px", borderRadius: 99 }}>Up next</div>
                  )}
                  <div style={{ position: "absolute", left: 16, right: 16, bottom: 16, whiteSpace: "nowrap" }}>
                    <div style={{ font: "500 0.66rem 'Inter'", letterSpacing: "0.08em", color: "rgba(255,255,255,0.85)", textTransform: "uppercase", marginBottom: 4 }}>{d.region}</div>
                    <div style={{ font: "600 1.25rem 'Fraunces', serif", color: C.white, lineHeight: 1.1 }}>{d.name}</div>
                  </div>
                </button>
              );
            })}
          </div>
        </div>
      </div>
    </div>
  );
}
