import React from "react";

// Voyant — Footer (minimal, no dead links). Brand + script + copyright.

const C = {
  forestDeep: "#21443A", sage: "#7BA697", gold: "#E0A458",
  faint: "rgba(255,255,255,0.7)", fainter: "rgba(255,255,255,0.45)",
  line: "rgba(255,255,255,0.12)",
};

export default function VoyantFooter() {
  return (
    <footer style={{ background: C.forestDeep, color: "#fff", fontFamily: "'Inter', system-ui, sans-serif", padding: "56px 32px 36px" }}>
      <link href="https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,500;9..144,600&family=Caveat:wght@600;700&family=Inter:wght@400;500&display=swap" rel="stylesheet" />
      <div style={{ maxWidth: 1100, margin: "0 auto", textAlign: "center" }}>
        <div style={{ display: "flex", alignItems: "center", justifyContent: "center", gap: 9, marginBottom: 12 }}>
          <span style={{ font: "600 1.5rem 'Fraunces', serif" }}>Voyant</span>
        </div>
        <div style={{ fontFamily: "'Caveat', cursive", fontWeight: 700, fontSize: "1.6rem", color: C.gold, marginBottom: 24 }}>
          Let's go somewhere.
        </div>
        <div style={{ height: 1, background: C.line, maxWidth: 240, margin: "0 auto 22px" }} />
        <div style={{ font: "400 0.84rem 'Inter'", color: C.fainter }}>
          © {new Date().getFullYear()} Voyant · Group trips, decided together.
        </div>
      </div>
    </footer>
  );
}