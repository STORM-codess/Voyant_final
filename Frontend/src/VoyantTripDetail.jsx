import React, { useState, useEffect } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { ArrowLeft, Trophy, X, LogOut } from "lucide-react";
import { api } from "./api";
import { useAuth } from "./AuthContext";
import FormTab from "./FormTab";
import VotePanel from "./VotePanel";

// Voyant — Trip Detail page. Tabbed: Overview / Form / Recommendations
// / Vote. Shows a trip MID-VOTING (richest state). Green/gold + Fraunces.
// All tabs map to real backend concepts; MOCK DATA marked below.
//
// ── BACKEND MAPPING ──
//   Overview        → trip + TripMember list + status
//   Form            → Form/FormQuestion + which members completed
//   Recommendations → Recommendation rows (versioned) for the trip
//   Vote            → VoteSession + VoteOption + Vote.rankings (ranked-choice)

const C = {
  forest: "#2F5D50", forestDeep: "#21443A", sage: "#7BA697", sageDeep: "#4E7C6C",
  gold: "#E0A458", goldSoft: "#F0C97E", goldWash: "#F8EDD7", goldDeep: "#C98A3C",
  cream: "#F3EEE3", card: "#FBF8F1", surface: "#FFFFFF",
  ink: "#243B34", textSoft: "#6B7872", line: "#E8E1D4", sageWash: "#E7EFEA",
};

const TABS = ["Overview", "Form", "Recommendations", "Vote"];

const AVATAR_COLORS = [C.gold, C.sage, C.sageDeep, C.forest, C.goldDeep];
function Avatar({ m, size = 34 }) {
  const name = m.name || "?";
  // stable color from the name so real members get consistent colors
  const color = m.c || AVATAR_COLORS[(name.charCodeAt(0) || 0) % AVATAR_COLORS.length];
  return <div style={{ width: size, height: size, borderRadius: 99, background: color, color: "#fff", display: "grid", placeItems: "center", font: `700 ${size * 0.38}px 'Inter'`, flexShrink: 0 }}>{name[0].toUpperCase()}</div>;
}

function Card({ children, style, onClick }) {
  return <div onClick={onClick} style={{ background: C.card, borderRadius: 20, border: `1px solid ${C.line}`, padding: 24, ...style }}>{children}</div>;
}

// ── TAB PANELS ──
function Overview({ trip, tripId, isAdmin, isCreator, onChanged, navigate }) {
  const members = trip.members || [];
  const pending = trip.pending_invites || [];
  const [email, setEmail] = useState("");
  const [inviting, setInviting] = useState(false);
  const [inviteMsg, setInviteMsg] = useState(null); // {ok, text}
  const [busyEmail, setBusyEmail] = useState(null);  // which pending invite is being cancelled
  const [leaving, setLeaving] = useState(false);

  const validEmail = /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email);

  const sendInvite = async () => {
    if (!validEmail) return;
    setInviting(true);
    setInviteMsg(null);
    try {
      await api.post(`/trips/${tripId}/invite?email=${encodeURIComponent(email.toLowerCase())}`);
      setInviteMsg({ ok: true, text: `Invite sent to ${email}` });
      setEmail("");
      onChanged && onChanged();
    } catch (e) {
      if (e.status === 403) setInviteMsg({ ok: false, text: "Only the trip admin can invite." });
      else if (e.status === 400) setInviteMsg({ ok: false, text: "That person is already invited or a member." });
      else setInviteMsg({ ok: false, text: "Couldn't send the invite." });
    } finally {
      setInviting(false);
    }
  };

  const cancelInvite = async (em) => {
    setBusyEmail(em);
    try {
      await api.del(`/trips/${tripId}/invite?email=${encodeURIComponent(em)}`);
      onChanged && onChanged();
    } catch {
      setInviteMsg({ ok: false, text: "Couldn't cancel that invite." });
    } finally {
      setBusyEmail(null);
    }
  };

  const leaveTrip = async () => {
    if (!window.confirm("Leave this trip? You'll need a new invite to rejoin.")) return;
    setLeaving(true);
    try {
      await api.del(`/trips/${tripId}/leave`);
      navigate("/dashboard");
    } catch (e) {
      setInviteMsg({ ok: false, text: e.status === 400 ? "The trip creator can't leave their own trip." : "Couldn't leave the trip." });
      setLeaving(false);
    }
  };

  return (
    <div style={{ display: "grid", gridTemplateColumns: "1.4fr 1fr", gap: 20 }}>
      <Card>
        <div style={{ font: "600 1.1rem 'Fraunces', serif", color: C.forest, marginBottom: 16 }}>Trip members</div>
        <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
          {members.map((m) => (
            <div key={m.user_id || m.name} style={{ display: "flex", alignItems: "center", gap: 12 }}>
              <Avatar m={m} />
              <div style={{ flex: 1 }}>
                <div style={{ font: "600 0.92rem 'Inter'", color: C.ink }}>{m.name || "Member"} {m.is_admin && <span style={{ font: "600 0.68rem 'Inter'", color: C.goldDeep, background: C.goldWash, padding: "2px 7px", borderRadius: 99, marginLeft: 4 }}>admin</span>}</div>
                {m.email && <div style={{ font: "400 0.74rem 'Inter'", color: C.textSoft }}>{m.email}</div>}
              </div>
            </div>
          ))}
        </div>

        {isAdmin && (
          <div style={{ marginTop: 18, paddingTop: 16, borderTop: `1px solid ${C.line}` }}>
            <div style={{ font: "600 0.82rem 'Inter'", color: C.textSoft, marginBottom: 8 }}>Invite a friend</div>
            <div style={{ display: "flex", gap: 8 }}>
              <input value={email} onChange={(e) => setEmail(e.target.value)} placeholder="friend@email.com" type="email"
                onKeyDown={(e) => { if (e.key === "Enter") sendInvite(); }}
                style={{ flex: 1, border: `1.5px solid ${C.line}`, borderRadius: 10, padding: "9px 12px", font: "400 0.88rem 'Inter'", color: C.ink, background: C.surface, outline: "none" }} />
              <button onClick={sendInvite} disabled={!validEmail || inviting}
                style={{ border: "none", background: validEmail && !inviting ? C.forest : C.line, color: "#fff", font: "700 0.84rem 'Inter'", padding: "9px 18px", borderRadius: 10, cursor: validEmail && !inviting ? "pointer" : "default" }}>
                {inviting ? "Sending…" : "Invite"}
              </button>
            </div>
            {inviteMsg && <div style={{ font: "500 0.8rem 'Inter'", color: inviteMsg.ok ? C.sageDeep : "#C0392B", marginTop: 8 }}>{inviteMsg.text}</div>}

            {pending.length > 0 && (
              <div style={{ marginTop: 16 }}>
                <div style={{ font: "600 0.78rem 'Inter'", color: C.textSoft, marginBottom: 8 }}>Pending invites</div>
                <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
                  {pending.map((p) => (
                    <div key={p.email} style={{ display: "flex", alignItems: "center", gap: 8, padding: "7px 10px", background: C.surface, border: `1px solid ${C.line}`, borderRadius: 9 }}>
                      <span style={{ flex: 1, font: "400 0.82rem 'Inter'", color: C.ink }}>{p.email}</span>
                      <span style={{ font: "500 0.68rem 'Inter'", color: C.goldDeep, background: C.goldWash, padding: "2px 7px", borderRadius: 99 }}>pending</span>
                      <button onClick={() => cancelInvite(p.email)} disabled={busyEmail === p.email} title="Cancel invite"
                        style={{ border: "none", background: "transparent", cursor: "pointer", color: C.textSoft, padding: 2, display: "grid", placeItems: "center" }}>
                        <X size={15} />
                      </button>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}

        {/* non-creator members can leave the trip */}
        {!isCreator && (
          <div style={{ marginTop: 18, paddingTop: 16, borderTop: `1px solid ${C.line}` }}>
            <button onClick={leaveTrip} disabled={leaving}
              style={{ border: `1.5px solid ${C.line}`, background: "transparent", color: "#C0392B", font: "600 0.82rem 'Inter'", padding: "9px 16px", borderRadius: 10, cursor: leaving ? "default" : "pointer", display: "flex", alignItems: "center", gap: 7 }}>
              <LogOut size={15} /> {leaving ? "Leaving…" : "Leave trip"}
            </button>
          </div>
        )}
      </Card>

      <Card style={{ background: `linear-gradient(150deg, ${C.forest}, ${C.forestDeep})`, color: "#fff" }}>
        <div style={{ font: "500 0.72rem 'Inter'", letterSpacing: "0.1em", textTransform: "uppercase", color: C.goldSoft, marginBottom: 8 }}>Trip status</div>
        <div style={{ font: "600 1.6rem 'Fraunces', serif", marginBottom: 16, textTransform: "capitalize" }}>{trip.status || "Planning"}</div>
        <div style={{ display: "flex", flexDirection: "column", gap: 12, font: "400 0.88rem 'Inter'", color: "rgba(255,255,255,0.85)" }}>
          <div style={{ display: "flex", justifyContent: "space-between" }}><span>Members</span><span>{members.length}</span></div>
          <div style={{ display: "flex", justifyContent: "space-between" }}><span>Destination</span><span>{trip.destination || "To be decided"}</span></div>
          <div style={{ display: "flex", justifyContent: "space-between" }}><span>Date</span><span>{trip.trip_date ? new Date(trip.trip_date).toLocaleDateString(undefined, { month: "short", day: "numeric", year: "numeric" }) : "TBD"}</span></div>
        </div>
      </Card>
    </div>
  );
}

function Recommendations({ tripId, isAdmin }) {
  const navigate = useNavigate();
  const [recs, setRecs] = useState(null);   // array of latest-version recs, or null
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [error, setError] = useState("");

  const loadRecs = async () => {
    try {
      const data = await api.get(`/recommendations/${tripId}`);
      const byVersion = data.recommendations_by_version || {};
      const versions = Object.keys(byVersion).map(Number);
      if (versions.length === 0) {
        setRecs([]);
      } else {
        const latest = Math.max(...versions);
        setRecs(byVersion[latest] || []);
      }
    } catch (e) {
      setRecs([]); // treat fetch failure as "none yet" rather than hard error
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { loadRecs(); }, [tripId]);

  const handleGenerate = async () => {
    setGenerating(true);
    setError("");
    try {
      await api.post(`/recommendations/${tripId}/generate`);
      await loadRecs();
    } catch (e) {
      if (e.status === 403) setError("Only the trip admin can generate recommendations.");
      else if (e.status === 409) setError("Voting is open — recommendations are locked.");
      else if (e.status === 400) setError("No form responses yet. Members need to fill the form first.");
      else setError("Couldn't generate recommendations. Please try again.");
    } finally {
      setGenerating(false);
    }
  };

  if (loading) {
    return <Card style={{ textAlign: "center", padding: "40px", color: C.textSoft }}>Loading recommendations…</Card>;
  }

  const hasRecs = recs && recs.length > 0;

  // ── COLLECTING: no recs yet ──
  if (!hasRecs) {
    return (
      <Card style={{ textAlign: "center", padding: "48px 28px", maxWidth: 480, margin: "0 auto" }}>
        <div style={{ fontFamily: "'Caveat', cursive", fontWeight: 700, fontSize: "1.6rem", color: C.gold }}>Almost there</div>
        <div style={{ font: "600 1.4rem 'Fraunces', serif", color: C.forest, margin: "6px 0 10px" }}>No recommendations yet</div>
        <p style={{ font: "400 0.92rem 'Inter'", color: C.textSoft, lineHeight: 1.6, marginBottom: 22 }}>
          Once your group has filled in their preferences, the AI reads everyone's answers and suggests destinations.
        </p>
        {isAdmin ? (
          <>
            <button onClick={handleGenerate} disabled={generating}
              style={{ border: "none", background: C.forest, color: "#fff", font: "700 0.9rem 'Inter'", padding: "13px 28px", borderRadius: 99, cursor: generating ? "default" : "pointer", opacity: generating ? 0.7 : 1 }}>
              {generating ? "Generating…" : "Generate recommendations"}
            </button>
            <p style={{ font: "400 0.78rem 'Inter'", color: C.textSoft, margin: "12px 0 0" }}>
              As the trip admin, you decide when to close collection and let the AI suggest destinations.
            </p>
          </>
        ) : (
          <p style={{ font: "500 0.85rem 'Inter'", color: C.sageDeep }}>
            Waiting for the trip admin to generate recommendations.
          </p>
        )}
        {error && <p style={{ font: "500 0.82rem 'Inter'", color: "#C0392B", margin: "14px 0 0" }}>{error}</p>}
      </Card>
    );
  }

  // ── REVIEWING: recs exist ──
  return (
    <div>
      <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 16, flexWrap: "wrap" }}>
        <span style={{ font: "600 1.1rem 'Fraunces', serif", color: C.forest }}>AI recommendations</span>
        <span style={{ font: "500 0.74rem 'Inter'", color: C.textSoft, background: C.goldWash, padding: "4px 10px", borderRadius: 99 }}>{recs.length} destinations</span>
      </div>
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(260px, 1fr))", gap: 16 }}>
        {recs.map((r, i) => (
          <Card key={r.id} onClick={() => navigate(`/plan/${tripId}/${r.id}`)} style={{ padding: 0, overflow: "hidden", cursor: "pointer" }}>
            <div style={{ height: 90, background: `linear-gradient(135deg, ${i===0?C.gold:C.sage}, ${i===0?C.goldDeep:C.sageDeep})`, position: "relative" }}>
              {i === 0 && <span style={{ position: "absolute", top: 10, left: 12, font: "600 0.68rem 'Inter'", color: C.forestDeep, background: "rgba(255,255,255,0.9)", padding: "4px 9px", borderRadius: 99, display: "flex", alignItems: "center", gap: 4 }}><Trophy size={12} /> Top pick</span>}
            </div>
            <div style={{ padding: "16px 18px 18px" }}>
              <div style={{ font: "600 1.2rem 'Fraunces', serif", color: C.forest }}>{r.destination}</div>
              <p style={{ font: "400 0.86rem 'Inter'", color: C.ink, lineHeight: 1.55, margin: "8px 0 0" }}>{r.reasoning}</p>
            </div>
          </Card>
        ))}
      </div>

      {/* regenerate: admin only (backend rejects if voting is open) */}
      {isAdmin && (
        <div style={{ marginTop: 18, display: "flex", alignItems: "center", gap: 14, flexWrap: "wrap" }}>
          <button onClick={handleGenerate} disabled={generating}
            style={{ border: `1.5px solid ${C.line}`, background: "transparent", color: C.sageDeep, font: "600 0.85rem 'Inter'", padding: "11px 20px", borderRadius: 99, cursor: generating ? "default" : "pointer", opacity: generating ? 0.6 : 1 }}>
            {generating ? "Regenerating…" : "Regenerate"}
          </button>
          <span style={{ font: "400 0.8rem 'Inter'", color: C.textSoft }}>Regenerating replaces the current set with a fresh version.</span>
        </div>
      )}
      {error && <p style={{ marginTop: 14, font: "500 0.82rem 'Inter'", color: "#C0392B" }}>{error}</p>}
    </div>
  );
}

export default function VoyantTripDetail() {
  const navigate = useNavigate();
  const { id } = useParams();
  const { profile } = useAuth();
  const [tab, setTab] = useState("Overview");
  const [trip, setTrip] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    let alive = true;
    (async () => {
      try {
        const data = await api.get(`/trips/${id}`);
        if (alive) setTrip(data);
      } catch (e) {
        if (alive) setError(e.status === 404 ? "Trip not found." : "Couldn't load this trip.");
      } finally {
        if (alive) setLoading(false);
      }
    })();
    return () => { alive = false; };
  }, [id]);

  const reloadTrip = async () => {
    try { setTrip(await api.get(`/trips/${id}`)); } catch { /* keep current */ }
  };

  if (loading) {
    return (
      <div style={{ background: C.cream, minHeight: "100vh", display: "grid", placeItems: "center", fontFamily: "'Inter', system-ui, sans-serif", color: C.textSoft }}>
        Loading trip…
      </div>
    );
  }

  if (error || !trip) {
    return (
      <div style={{ background: C.cream, minHeight: "100vh", display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", gap: 16, fontFamily: "'Inter', system-ui, sans-serif" }}>
        <link href="https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,600&family=Inter:wght@400;600;700&display=swap" rel="stylesheet" />
        <div style={{ font: "600 1.4rem 'Fraunces', serif", color: C.forest }}>{error || "Trip not found."}</div>
        <button onClick={() => navigate("/dashboard")} style={{ border: "none", background: C.forest, color: "#fff", font: "700 0.88rem 'Inter'", padding: "12px 24px", borderRadius: 99, cursor: "pointer" }}>Back to dashboard</button>
      </div>
    );
  }

  const members = trip.members || [];
  const isAdmin = members.some((m) => m.user_id === profile?.id && m.is_admin);

  return (
    <div style={{ background: C.cream, minHeight: "100vh", fontFamily: "'Inter', system-ui, sans-serif", padding: "28px 40px 60px" }}>
      <link href="https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,500;9..144,600;9..144,700&family=Caveat:wght@600;700&family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet" />

      {/* back + breadcrumb */}
      <button onClick={() => navigate("/dashboard")} style={{ border: "none", background: "transparent", color: C.textSoft, font: "600 0.85rem 'Inter'", cursor: "pointer", display: "flex", alignItems: "center", gap: 6, marginBottom: 18, padding: 0 }}>
        <ArrowLeft size={16} /> All trips
      </button>

      {/* trip header */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-end", marginBottom: 24, flexWrap: "wrap", gap: 16 }}>
        <div>
          <div style={{ font: "500 0.78rem 'Inter'", letterSpacing: "0.06em", color: C.textSoft, textTransform: "uppercase" }}>{trip.destination || "Destination TBD"}</div>
          <h1 style={{ font: "600 2.4rem 'Fraunces', serif", color: C.forest, margin: "4px 0 6px" }}>{trip.name}</h1>
          <div style={{ font: "400 0.92rem 'Inter'", color: C.textSoft }}>{trip.trip_date ? new Date(trip.trip_date).toLocaleDateString(undefined, { month: "long", day: "numeric", year: "numeric" }) : "Dates to be decided"}</div>
        </div>
        <div style={{ display: "flex", alignItems: "center" }}>
          <div style={{ display: "flex" }}>
            {members.map((m, i) => (
              <div key={m.user_id || i} style={{ marginLeft: i ? -10 : 0 }}><div style={{ border: "2.5px solid " + C.cream, borderRadius: 99 }}><Avatar m={m} size={38} /></div></div>
            ))}
          </div>
        </div>
      </div>

      {/* tabs */}
      <div style={{ display: "flex", gap: 6, borderBottom: `1px solid ${C.line}`, marginBottom: 26 }}>
        {TABS.map((t) => (
          <button key={t} onClick={() => setTab(t)} style={{
            border: "none", background: "transparent", cursor: "pointer",
            font: `${tab===t?700:500} 0.92rem 'Inter'`, color: tab===t?C.forest:C.textSoft,
            padding: "10px 16px", position: "relative",
          }}>
            {t}
            {tab === t && <span style={{ position: "absolute", left: 16, right: 16, bottom: -1, height: 3, borderRadius: 99, background: C.gold }} />}
          </button>
        ))}
      </div>

      {/* panel */}
      {tab === "Overview" && <Overview trip={trip} tripId={id} isAdmin={isAdmin} isCreator={trip.creator_id === profile?.id} onChanged={reloadTrip} navigate={navigate} />}
      {tab === "Form" && <FormTab tripId={id} isAdmin={isAdmin} />}
      {tab === "Recommendations" && <Recommendations tripId={id} isAdmin={isAdmin} />}
      {tab === "Vote" && <VotePanel tripId={id} isAdmin={isAdmin} />}
    </div>
  );
}
