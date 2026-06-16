import React, { useState, useEffect } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { ArrowLeft, Trophy, Calendar, Wallet, Clock, MapPin, Sun, Star, Sparkles } from "lucide-react";
import { api } from "./api";

// Voyant — Recommendation Plan Detail. Reads /plan/:tripId/:recId, fetches
// the real recommendation, and shows its day-by-day itinerary (generated
// on demand via POST /recommendations/{tripId}/{recId}/itinerary).

const C = {
  forest: "#2F5D50", forestDeep: "#21443A", sage: "#7BA697", sageDeep: "#4E7C6C",
  gold: "#E0A458", goldSoft: "#F0C97E", goldWash: "#F8EDD7", goldDeep: "#C98A3C",
  cream: "#F3EEE3", card: "#FBF8F1", surface: "#FFFFFF",
  ink: "#243B34", textSoft: "#6B7872", line: "#E8E1D4", sageWash: "#E7EFEA",
};

function Card({ children, style }) {
  return <div style={{ background: C.card, borderRadius: 20, border: `1px solid ${C.line}`, padding: 24, ...style }}>{children}</div>;
}

function Stat({ icon: Icon, label, value }) {
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
      <div style={{ width: 38, height: 38, borderRadius: 11, background: C.goldWash, display: "grid", placeItems: "center", flexShrink: 0 }}>
        <Icon size={18} color={C.goldDeep} />
      </div>
      <div>
        <div style={{ font: "400 0.72rem 'Inter'", color: C.textSoft }}>{label}</div>
        <div style={{ font: "600 0.92rem 'Inter'", color: C.ink }}>{value}</div>
      </div>
    </div>
  );
}

export default function VoyantPlanDetail() {
  const navigate = useNavigate();
  const { tripId, recId } = useParams();
  const [rec, setRec] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [itinerary, setItinerary] = useState(null);
  const [genItin, setGenItin] = useState(false);
  const [itinError, setItinError] = useState("");

  useEffect(() => {
    let alive = true;
    (async () => {
      try {
        const data = await api.get(`/recommendations/${tripId}/${recId}`);
        if (!alive) return;
        setRec(data);
        setItinerary(data.itinerary || null);
      } catch (e) {
        if (alive) setError("Couldn't load this recommendation.");
      } finally {
        if (alive) setLoading(false);
      }
    })();
    return () => { alive = false; };
  }, [tripId, recId]);

  const handleGenerateItinerary = async () => {
    setGenItin(true);
    setItinError("");
    try {
      const res = await api.post(`/recommendations/${tripId}/${recId}/itinerary`);
      setItinerary(res.itinerary || []);
    } catch (e) {
      setItinError("Couldn't generate the itinerary. Please try again.");
    } finally {
      setGenItin(false);
    }
  };

  if (loading) {
    return <div style={{ background: C.cream, minHeight: "100vh", display: "grid", placeItems: "center", fontFamily: "'Inter', system-ui, sans-serif", color: C.textSoft }}>Loading…</div>;
  }
  if (error || !rec) {
    return (
      <div style={{ background: C.cream, minHeight: "100vh", display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", gap: 16, fontFamily: "'Inter', system-ui, sans-serif" }}>
        <div style={{ font: "600 1.3rem 'Fraunces', serif", color: C.forest }}>{error || "Not found."}</div>
        <button onClick={() => navigate(-1)} style={{ border: "none", background: C.forest, color: "#fff", font: "700 0.88rem 'Inter'", padding: "12px 24px", borderRadius: 99, cursor: "pointer" }}>Go back</button>
      </div>
    );
  }

  // budget may be a dict like {hotel_per_night, transport_from_major_city}
  const budgetText = (() => {
    const b = rec.estimated_budget;
    if (!b) return "—";
    if (typeof b === "string") return b;
    const vals = Object.values(b).filter(Boolean);
    return vals.length ? vals[0] : "—";
  })();
  const activities = Array.isArray(rec.activities) ? rec.activities : [];
  const stops = Array.isArray(rec.stops) ? rec.stops : [];

  return (
    <div style={{ background: C.cream, minHeight: "100vh", fontFamily: "'Inter', system-ui, sans-serif", padding: "28px 40px 70px" }}>
      <link href="https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,500;9..144,600;9..144,700&family=Caveat:wght@600;700&family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet" />

      <button onClick={() => navigate(-1)} style={{ border: "none", background: "transparent", color: C.textSoft, font: "600 0.85rem 'Inter'", cursor: "pointer", display: "flex", alignItems: "center", gap: 6, marginBottom: 18, padding: 0 }}>
        <ArrowLeft size={16} /> Back to recommendations
      </button>

      {/* hero */}
      <div style={{ borderRadius: 24, overflow: "hidden", marginBottom: 22, position: "relative", height: 200, background: `linear-gradient(135deg, ${C.gold}, ${C.goldDeep})` }}>
        <div style={{ position: "absolute", inset: 0, background: "linear-gradient(180deg, rgba(0,0,0,0) 40%, rgba(36,59,52,0.55) 100%)" }} />
        <div style={{ position: "absolute", bottom: 18, left: 22, color: "#fff" }}>
          <div style={{ font: "500 0.74rem 'Inter'", letterSpacing: "0.08em", textTransform: "uppercase", opacity: 0.85 }}>Recommendation</div>
          <h1 style={{ font: "600 2.6rem 'Fraunces', serif", margin: "2px 0 0", lineHeight: 1 }}>{rec.destination}</h1>
        </div>
      </div>

      {/* stat strip — only the fields we actually have */}
      <Card style={{ display: "flex", gap: 30, flexWrap: "wrap", marginBottom: 22 }}>
        <Stat icon={Wallet} label="Est. budget" value={budgetText} />
        {activities.length > 0 && <Stat icon={Star} label="Highlights" value={activities.slice(0, 2).join(", ")} />}
      </Card>

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1.6fr", gap: 22, alignItems: "start" }}>
        {/* why */}
        <Card>
          <div style={{ font: "600 1.1rem 'Fraunces', serif", color: C.forest, marginBottom: 12 }}>Why the group picked this</div>
          <p style={{ font: "400 0.92rem 'Inter'", color: C.ink, lineHeight: 1.7, margin: 0 }}>{rec.reasoning}</p>

          {stops.length > 0 && (
            <div style={{ marginTop: 18 }}>
              <div style={{ font: "600 0.82rem 'Inter'", color: C.sageDeep, textTransform: "uppercase", letterSpacing: "0.06em", marginBottom: 10 }}>The route</div>
              <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                {stops.map((s, i) => (
                  <div key={i} style={{ display: "flex", alignItems: "flex-start", gap: 10, padding: "10px 12px", background: C.surface, borderRadius: 10, border: `1px solid ${C.line}` }}>
                    <span style={{ font: "700 0.78rem 'Inter'", color: "#fff", background: C.sageDeep, width: 20, height: 20, borderRadius: 99, display: "grid", placeItems: "center", flexShrink: 0, marginTop: 1 }}>{i + 1}</span>
                    <div>
                      <div style={{ font: "600 0.9rem 'Inter'", color: C.ink }}>{s.place}{s.nights ? <span style={{ color: C.textSoft, fontWeight: 400 }}> · {s.nights} {s.nights === 1 ? "night" : "nights"}</span> : null}</div>
                      {Array.isArray(s.highlights) && s.highlights.length > 0 && (
                        <div style={{ font: "400 0.8rem 'Inter'", color: C.textSoft, marginTop: 2 }}>{s.highlights.join(" · ")}</div>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
          {activities.length > 0 && (
            <div style={{ display: "flex", flexWrap: "wrap", gap: 8, marginTop: 18 }}>
              {activities.map((h, i) => (
                <span key={i} style={{ font: "500 0.78rem 'Inter'", color: C.sageDeep, background: C.sageWash, padding: "6px 12px", borderRadius: 99 }}>{h}</span>
              ))}
            </div>
          )}
        </Card>

        {/* itinerary */}
        <Card>
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 18 }}>
            <div style={{ font: "600 1.1rem 'Fraunces', serif", color: C.forest }}>Day-by-day itinerary</div>
            {itinerary && <span style={{ font: "500 0.72rem 'Inter'", color: C.goldDeep, background: C.goldWash, padding: "4px 10px", borderRadius: 99 }}>AI-suggested</span>}
          </div>

          {itinerary && itinerary.length > 0 ? (
            <div style={{ position: "relative", paddingLeft: 28 }}>
              <div style={{ position: "absolute", left: 9, top: 6, bottom: 6, width: 2, background: C.line }} />
              {itinerary.map((d) => (
                <div key={d.day} style={{ position: "relative", marginBottom: 24 }}>
                  <div style={{ position: "absolute", left: -28, top: 0, width: 20, height: 20, borderRadius: 99, background: C.gold, color: "#fff", display: "grid", placeItems: "center", font: "700 0.7rem 'Inter'" }}>{d.day}</div>
                  <div style={{ font: "600 1rem 'Fraunces', serif", color: C.forest, marginBottom: 8 }}>Day {d.day} · {d.title}</div>
                  <div style={{ display: "flex", flexDirection: "column", gap: 7 }}>
                    {(d.items || []).map((it, i) => (
                      <div key={i} style={{ display: "flex", alignItems: "flex-start", gap: 9, font: "400 0.88rem 'Inter'", color: C.ink }}>
                        <MapPin size={15} color={C.sage} style={{ marginTop: 2, flexShrink: 0 }} /> {it}
                      </div>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          ) : (
            // no itinerary yet → offer to generate one
            <div style={{ textAlign: "center", padding: "28px 16px" }}>
              <p style={{ font: "400 0.9rem 'Inter'", color: C.textSoft, lineHeight: 1.6, marginBottom: 18 }}>
                No itinerary yet. Generate a suggested day-by-day plan for {rec.destination}.
              </p>
              <button onClick={handleGenerateItinerary} disabled={genItin}
                style={{ border: "none", background: C.forest, color: "#fff", font: "700 0.88rem 'Inter'", padding: "12px 24px", borderRadius: 99, cursor: genItin ? "default" : "pointer", opacity: genItin ? 0.7 : 1, display: "inline-flex", alignItems: "center", gap: 8 }}>
                <Sparkles size={16} /> {genItin ? "Generating…" : "Generate itinerary"}
              </button>
              {itinError && <p style={{ font: "500 0.82rem 'Inter'", color: "#C0392B", marginTop: 14 }}>{itinError}</p>}
            </div>
          )}
        </Card>
      </div>
    </div>
  );
}