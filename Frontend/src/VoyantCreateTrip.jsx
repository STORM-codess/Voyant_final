import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "./api";
import { ArrowLeft, ArrowRight, Check, Plus, X, Mail, MapPin, Calendar } from "lucide-react";

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

const STEPS = ["Trip details", "Invite friends"];

export default function VoyantCreateTrip() {
  const navigate = useNavigate();
  const [step, setStep] = useState(0);
  const [name, setName] = useState("");
  const [region, setRegion] = useState("");
  const [start, setStart] = useState("");
  const [end, setEnd] = useState("");
  const [emailInput, setEmailInput] = useState("");
  const [invites, setInvites] = useState([]);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");

  const canProceed = name.trim().length > 0;
  const validEmail = /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(emailInput);

  const addInvite = () => {
    if (validEmail && !invites.includes(emailInput.toLowerCase())) {
      setInvites([...invites, emailInput.toLowerCase()]);
      setEmailInput("");
    }
  };
  const removeInvite = (e) => setInvites(invites.filter((x) => x !== e));

  const handleCreate = async () => {
    setSubmitting(true);
    setError("");
    try {
      // 1) create the trip (destination/date optional — group decides later)
      const res = await api.post("/trips/create", {
        name: name.trim(),
        destination: region.trim() || null,
        trip_date: start || null,
        description: null,
      });
      const tripId = res.trip_id;

      // 2) send invites one at a time (email is a query param on the backend)
      for (const email of invites) {
        try {
          await api.post(`/trips/${tripId}/invite?email=${encodeURIComponent(email)}`);
        } catch {
          // a single failed invite shouldn't abort the whole flow; the trip
          // is already created. Could collect these to show later.
        }
      }

      // 3) go to the new trip
      navigate("/trip/" + tripId);
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
        {/* step indicator */}
        <div style={{ display: "flex", alignItems: "center", gap: 0, marginBottom: 36 }}>
          {STEPS.map((s, i) => (
            <React.Fragment key={s}>
              <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
                <div style={{
                  width: 30, height: 30, borderRadius: 99, display: "grid", placeItems: "center",
                  font: "700 0.82rem 'Inter'",
                  background: i < step ? C.sageDeep : i === step ? C.gold : C.line,
                  color: i <= step ? "#fff" : C.textSoft,
                }}>{i < step ? <Check size={15} /> : i + 1}</div>
                <span style={{ font: `${i === step ? 700 : 500} 0.88rem 'Inter'`, color: i === step ? C.forest : C.textSoft }}>{s}</span>
              </div>
              {i < STEPS.length - 1 && <div style={{ flex: 1, height: 2, background: C.line, margin: "0 14px" }} />}
            </React.Fragment>
          ))}
        </div>

        {/* STEP 1 — details */}
        {step === 0 && (
          <div>
            <h1 style={{ font: "600 2rem 'Fraunces', serif", color: C.forest, margin: "0 0 6px" }}>Start a new trip</h1>
            <p style={{ font: "400 0.95rem 'Inter'", color: C.textSoft, margin: "0 0 28px" }}>Give it a name and a rough timeframe — you can change these later.</p>

            <label style={{ font: "600 0.82rem 'Inter'", color: C.ink, display: "block", marginBottom: 7 }}>Trip name</label>
            <input value={name} onChange={(e) => setName(e.target.value)} placeholder="e.g. Goa Reunion" style={{ ...inputStyle, marginBottom: 20 }} />

            <label style={{ font: "600 0.82rem 'Inter'", color: C.ink, display: "block", marginBottom: 7 }}>Where to? <span style={{ color: C.textSoft, fontWeight: 400 }}>(optional — the group can decide)</span></label>
            <input value={region} onChange={(e) => setRegion(e.target.value)} placeholder="e.g. somewhere with beaches" style={{ ...inputStyle, marginBottom: 20 }} />

            <div style={{ display: "flex", gap: 14 }}>
              <div style={{ flex: 1 }}>
                <label style={{ font: "600 0.82rem 'Inter'", color: C.ink, display: "block", marginBottom: 7 }}>Start date</label>
                <input type="date" value={start} onChange={(e) => setStart(e.target.value)} style={inputStyle} />
              </div>
              <div style={{ flex: 1 }}>
                <label style={{ font: "600 0.82rem 'Inter'", color: C.ink, display: "block", marginBottom: 7 }}>End date</label>
                <input type="date" value={end} onChange={(e) => setEnd(e.target.value)} style={inputStyle} />
              </div>
            </div>

            <button onClick={() => canProceed && setStep(1)} disabled={!canProceed}
              style={{ marginTop: 32, width: "100%", border: "none", background: canProceed ? C.forest : C.line, color: canProceed ? "#fff" : C.textSoft, font: "700 0.95rem 'Inter'", padding: "15px", borderRadius: 99, cursor: canProceed ? "pointer" : "default", display: "flex", alignItems: "center", justifyContent: "center", gap: 8 }}>
              Continue <ArrowRight size={17} />
            </button>
          </div>
        )}

        {/* STEP 2 — invites */}
        {step === 1 && (
          <div>
            <h1 style={{ font: "600 2rem 'Fraunces', serif", color: C.forest, margin: "0 0 6px" }}>Invite your friends</h1>
            <p style={{ font: "400 0.95rem 'Inter'", color: C.textSoft, margin: "0 0 28px" }}>Add their emails — they'll get an invite to join <strong>{name || "your trip"}</strong>.</p>

            <label style={{ font: "600 0.82rem 'Inter'", color: C.ink, display: "block", marginBottom: 7 }}>Friend's email</label>
            <div style={{ display: "flex", gap: 10, marginBottom: 16 }}>
              <input value={emailInput} onChange={(e) => setEmailInput(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && addInvite()}
                placeholder="friend@email.com" style={{ ...inputStyle, flex: 1 }} />
              <button onClick={addInvite} disabled={!validEmail}
                style={{ border: "none", background: validEmail ? C.gold : C.line, color: validEmail ? "#fff" : C.textSoft, borderRadius: 12, padding: "0 18px", cursor: validEmail ? "pointer" : "default", display: "grid", placeItems: "center" }}>
                <Plus size={20} />
              </button>
            </div>

            {/* invited list */}
            {invites.length > 0 ? (
              <div style={{ display: "flex", flexDirection: "column", gap: 8, marginBottom: 8 }}>
                {invites.map((e) => (
                  <div key={e} style={{ display: "flex", alignItems: "center", gap: 11, padding: "11px 14px", background: C.surface, borderRadius: 12, border: `1px solid ${C.line}` }}>
                    <div style={{ width: 30, height: 30, borderRadius: 99, background: C.sageWash, display: "grid", placeItems: "center" }}><Mail size={15} color={C.sageDeep} /></div>
                    <span style={{ flex: 1, font: "500 0.9rem 'Inter'", color: C.ink }}>{e}</span>
                    <button onClick={() => removeInvite(e)} style={{ border: "none", background: "transparent", cursor: "pointer", color: C.textSoft, padding: 4 }}><X size={16} /></button>
                  </div>
                ))}
              </div>
            ) : (
              <div style={{ textAlign: "center", padding: "26px", color: C.textSoft, font: "400 0.88rem 'Inter'", background: C.surface, borderRadius: 12, border: `1px dashed ${C.line}`, marginBottom: 8 }}>
                No one invited yet — add a few friends, or invite them later.
              </div>
            )}

            {error && <p style={{ font: "500 0.84rem 'Inter'", color: "#C0392B", margin: "16px 0 0" }}>{error}</p>}

            <div style={{ display: "flex", gap: 12, marginTop: 28 }}>
              <button onClick={() => setStep(0)} disabled={submitting} style={{ border: `1.5px solid ${C.line}`, background: "transparent", color: C.ink, font: "600 0.92rem 'Inter'", padding: "14px 22px", borderRadius: 99, cursor: submitting ? "default" : "pointer", display: "flex", alignItems: "center", gap: 7, opacity: submitting ? 0.6 : 1 }}>
                <ArrowLeft size={16} /> Back
              </button>
              <button onClick={handleCreate} disabled={submitting} style={{ flex: 1, border: "none", background: C.forest, color: "#fff", font: "700 0.95rem 'Inter'", padding: "14px", borderRadius: 99, cursor: submitting ? "default" : "pointer", opacity: submitting ? 0.7 : 1 }}>
                {submitting ? "Creating…" : (invites.length > 0 ? `Create trip & invite ${invites.length}` : "Create trip")}
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}