import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "./api";
import { ArrowLeft, ArrowRight } from "lucide-react";

// Voyant — Create Trip wizard. Step 1: details (name + dates).
// Step 2: invite friends by email. Green/gold + Fraunces.
//
// ── BACKEND MAPPING ──
//   Step 1 → POST create trip (name, start/end dates); creator = admin
//   Step 2 → invite endpoint per email (admin-only). Existing users are
//            added immediately; new emails get a PendingInvite.
// On finish → navigate to the new trip's detail page.

const C = {
  forest: "#2F5D50", forestDeep: "#21443A", sage: "#7BA697", sageDeep: "#4E7C6C",
  gold: "#E0A458", goldSoft: "#F0C97E", goldWash: "#F8EDD7", goldDeep: "#C98A3C",
  cream: "#F3EEE3", card: "#FBF8F1", surface: "#FFFFFF",
  ink: "#243B34", textSoft: "#6B7872", line: "#E8E1D4", sageWash: "#E7EFEA",
};

const inputStyle = {
  width: "100%", padding: "13px 15px", borderRadius: 12, border: `1.5px solid ${C.line}`,
  font: "400 0.95rem 'Inter'", color: C.ink, background: C.surface, outline: "none",
};


export default function VoyantCreateTrip() {
  const navigate = useNavigate();
  const [name, setName] = useState("");
  const [region, setRegion] = useState("");
  const [start, setStart] = useState("");
  const [end, setEnd] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");

  const canProceed = name.trim().length > 0;

  const handleCreate = async () => {
    if (!canProceed) return;
    setSubmitting(true);
    setError("");
    try {
      // create the trip (destination/dates optional — the group decides where,
      // and trip length comes from everyone's form answers)
      const res = await api.post("/trips/create", {
        name: name.trim(),
        destination: region.trim() || null,
        trip_date: start || null,
        description: null,
      });
      // go straight to the trip — invites happen there via a share link
      navigate("/trip/" + res.trip_id);
    } catch (e) {
      setError("Couldn't create the trip. Please try again.");
      setSubmitting(false);
    }
  };

  return (
    <div style={{ background: C.cream, minHeight: "100vh", fontFamily: "'Inter', system-ui, sans-serif", padding: "28px 40px 60px" }}>
      <link href="https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,500;9..144,600;9..144,700&family=Caveat:wght@600;700&family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet" />

      <button onClick={() => navigate("/dashboard")} style={{ border: "none", background: "transparent", color: C.textSoft, font: "600 0.85rem 'Inter'", cursor: "pointer", display: "flex", alignItems: "center", gap: 6, marginBottom: 22, padding: 0 }}>
        <ArrowLeft size={16} /> Cancel
      </button>

      <div style={{ maxWidth: 560, margin: "0 auto" }}>
        <h1 style={{ font: "600 2rem 'Fraunces', serif", color: C.forest, margin: "0 0 6px" }}>Start a new trip</h1>
        <p style={{ font: "400 0.95rem 'Inter'", color: C.textSoft, margin: "0 0 28px" }}>Just give it a name to get started. Where you go is decided by the group — and once it's created you'll get a link to invite everyone.</p>

        <label style={{ font: "600 0.82rem 'Inter'", color: C.ink, display: "block", marginBottom: 7 }}>Trip name</label>
        <input value={name} onChange={(e) => setName(e.target.value)} placeholder="e.g. Goa Reunion"
          onKeyDown={(e) => e.key === "Enter" && handleCreate()} style={{ ...inputStyle, marginBottom: 24 }} />

        {/* optional details, clearly secondary */}
        <div style={{ background: C.surface, border: `1px solid ${C.line}`, borderRadius: 14, padding: "18px 18px 4px" }}>
          <div style={{ font: "600 0.78rem 'Inter'", color: C.textSoft, textTransform: "uppercase", letterSpacing: "0.06em", marginBottom: 14 }}>Optional — you can skip all of this</div>

          <label style={{ font: "600 0.82rem 'Inter'", color: C.ink, display: "block", marginBottom: 7 }}>A starting idea for where? <span style={{ color: C.textSoft, fontWeight: 400 }}>(the group still votes)</span></label>
          <input value={region} onChange={(e) => setRegion(e.target.value)} placeholder="e.g. somewhere with beaches" style={{ ...inputStyle, marginBottom: 18 }} />

          <label style={{ font: "600 0.82rem 'Inter'", color: C.ink, display: "block", marginBottom: 7 }}>Rough dates, if you have them <span style={{ color: C.textSoft, fontWeight: 400 }}>(tentative)</span></label>
          <div style={{ display: "flex", gap: 14, marginBottom: 6 }}>
            <input type="date" value={start} onChange={(e) => setStart(e.target.value)} style={{ ...inputStyle, flex: 1 }} />
            <input type="date" value={end} onChange={(e) => setEnd(e.target.value)} style={{ ...inputStyle, flex: 1 }} />
          </div>
          <p style={{ font: "400 0.76rem 'Inter'", color: C.textSoft, margin: "0 0 14px", lineHeight: 1.5 }}>
            Trip length for recommendations comes from everyone's form answers, so dates here are just a tentative note.
          </p>
        </div>

        {error && <p style={{ font: "500 0.84rem 'Inter'", color: "#C0392B", margin: "18px 0 0" }}>{error}</p>}

        <button onClick={handleCreate} disabled={!canProceed || submitting}
          style={{ marginTop: 28, width: "100%", border: "none", background: (canProceed && !submitting) ? C.forest : C.line, color: (canProceed && !submitting) ? "#fff" : C.textSoft, font: "700 0.95rem 'Inter'", padding: "15px", borderRadius: 99, cursor: (canProceed && !submitting) ? "pointer" : "default", display: "flex", alignItems: "center", justifyContent: "center", gap: 8 }}>
          {submitting ? "Creating…" : <>Create trip <ArrowRight size={17} /></>}
        </button>
      </div>
    </div>
  );
}
