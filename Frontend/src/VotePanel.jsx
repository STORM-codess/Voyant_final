import React, { useState, useEffect } from "react";
import { Trophy, Users, ChevronUp, ChevronDown, Check, Lock } from "lucide-react";
import { api } from "./api";

// Voyant — Vote tab (real). Ranked-choice voting backed by /votes/*.
// Flow: admin opens a session from the recommendations → members rank &
// submit ballots → live first-choice tally → admin closes → instant-runoff
// winner (or a revote on a tie).

const C = {
  forest: "#2F5D50", forestDeep: "#21443A", sage: "#7BA697", sageDeep: "#4E7C6C",
  gold: "#E0A458", goldSoft: "#F0C97E", goldWash: "#F8EDD7", goldDeep: "#C98A3C",
  cream: "#F3EEE3", card: "#FBF8F1", surface: "#FFFFFF",
  ink: "#243B34", textSoft: "#6B7872", line: "#E8E1D4", sageWash: "#E7EFEA",
};

function Card({ children, style }) {
  return <div style={{ background: C.card, borderRadius: 20, border: `1px solid ${C.line}`, padding: 24, ...style }}>{children}</div>;
}

function deadlineLabel(iso) {
  if (!iso) return "";
  const ms = new Date(iso) - new Date();
  if (ms <= 0) return "Deadline passed";
  const hrs = Math.round(ms / 3600000);
  if (hrs < 24) return `${hrs}h left`;
  return `${Math.round(hrs / 24)}d left`;
}

export default function VotePanel({ tripId, isAdmin }) {
  const [loading, setLoading] = useState(true);
  const [session, setSession] = useState(null);   // the active (or latest) session
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);         // create/close in flight
  const [ranking, setRanking] = useState([]);      // option ids in my order
  const [submitting, setSubmitting] = useState(false);
  const [recs, setRecs] = useState([]);            // for opening a session

  const load = async () => {
    setError("");
    try {
      const data = await api.get(`/votes/${tripId}/sessions`);
      const sessions = data.sessions || [];
      // prefer an actively-votable session (open OR revote), else most recent
      const active = sessions.find((s) => s.status === "open" || s.status === "revote")
        || sessions[sessions.length - 1] || null;
      setSession(active);
      if (active) {
        // seed my ranking: existing ballot, else option order
        setRanking(active.user_rankings || active.options.map((o) => o.id));
      }
    } catch (e) {
      if (e.status === 403) setError("You need to be a trip member to vote.");
      else setError("Couldn't load voting.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, [tripId]);

  // admin: load recs so we can open a session from them
  useEffect(() => {
    if (!isAdmin || session) return;
    (async () => {
      try {
        const data = await api.get(`/recommendations/${tripId}`);
        const byV = data.recommendations_by_version || {};
        const versions = Object.keys(byV).map(Number);
        if (versions.length) setRecs(byV[Math.max(...versions)] || []);
      } catch { /* leave empty */ }
    })();
  }, [isAdmin, session, tripId]);

  const openVoting = async () => {
    setBusy(true);
    setError("");
    try {
      await api.post(`/votes/${tripId}/create-session`, {
        title: "Where should we go?",
        description: "Rank the destinations the AI suggested.",
        options: recs.map((r) => r.destination),
        deadline_hours: 72,
      });
      await load();
    } catch (e) {
      if (e.status === 403) setError("Only the trip creator can open voting.");
      else if (e.status === 400) setError("Need at least 2 recommendations to open voting.");
      else setError("Couldn't open voting.");
    } finally {
      setBusy(false);
    }
  };

  const move = (i, dir) => {
    const j = i + dir;
    if (j < 0 || j >= ranking.length) return;
    const next = [...ranking];
    [next[i], next[j]] = [next[j], next[i]];
    setRanking(next);
  };

  const submitBallot = async () => {
    setSubmitting(true);
    setError("");
    try {
      await api.post(`/votes/${tripId}/cast`, { session_id: session.session_id, rankings: ranking });
      await load();
    } catch (e) {
      if (e.status === 400) setError("Voting is closed or your ballot was invalid.");
      else setError("Couldn't submit your ballot.");
    } finally {
      setSubmitting(false);
    }
  };

  const closeVoting = async () => {
    setBusy(true);
    setError("");
    try {
      await api.post(`/votes/${tripId}/close/${session.session_id}`, {});
      await load();
    } catch (e) {
      setError("Couldn't close voting.");
    } finally {
      setBusy(false);
    }
  };

  if (loading) return <Card style={{ textAlign: "center", padding: 40, color: C.textSoft }}>Loading voting…</Card>;

  // ── No session yet ──
  if (!session) {
    return (
      <Card style={{ textAlign: "center", padding: "44px 28px", maxWidth: 480, margin: "0 auto" }}>
        <div style={{ font: "600 1.3rem 'Fraunces', serif", color: C.forest, marginBottom: 8 }}>Voting hasn't started</div>
        {isAdmin ? (
          <>
            <p style={{ font: "400 0.92rem 'Inter'", color: C.textSoft, lineHeight: 1.6, marginBottom: 20 }}>
              Once you're happy with the recommendations, open voting so the group can rank them. This locks the recommendations as the ballot.
            </p>
            <button onClick={openVoting} disabled={busy || recs.length < 2}
              style={{ border: "none", background: recs.length < 2 ? C.line : C.forest, color: "#fff", font: "700 0.9rem 'Inter'", padding: "13px 28px", borderRadius: 99, cursor: busy || recs.length < 2 ? "default" : "pointer", opacity: busy ? 0.7 : 1 }}>
              {busy ? "Opening…" : "Open voting"}
            </button>
            {recs.length < 2 && <p style={{ font: "400 0.8rem 'Inter'", color: C.textSoft, marginTop: 12 }}>Generate at least 2 recommendations first.</p>}
          </>
        ) : (
          <p style={{ font: "400 0.92rem 'Inter'", color: C.textSoft, lineHeight: 1.6 }}>
            The trip admin hasn't opened voting yet. You'll rank the destinations here once they do.
          </p>
        )}
        {error && <p style={{ font: "500 0.82rem 'Inter'", color: "#C0392B", marginTop: 14 }}>{error}</p>}
      </Card>
    );
  }

  const isRevote = session.status === "revote";
  const isOpen = session.status === "open" || isRevote;
  const optionById = Object.fromEntries(session.options.map((o) => [o.id, o]));
  const maxFirst = Math.max(1, ...session.options.map((o) => o.first_choice_votes || 0));
  const winner = session.winner_option_id ? optionById[session.winner_option_id] : null;

  return (
    <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 20 }}>
      {/* ballot */}
      <Card>
        {isRevote && (
          <div style={{ background: C.goldWash, border: `1px solid ${C.goldSoft}`, borderRadius: 12, padding: "10px 14px", marginBottom: 14, font: "500 0.84rem 'Inter'", color: C.goldDeep }}>
            It was a tie last round — everyone's ballots were reset. Please rank again to break the tie.
          </div>
        )}
        <div style={{ font: "600 1.1rem 'Fraunces', serif", color: C.forest, marginBottom: 4 }}>
          {isOpen ? "Rank your choices" : "Your ballot"}
        </div>
        <p style={{ font: "400 0.85rem 'Inter'", color: C.textSoft, margin: "0 0 16px" }}>
          {isOpen ? "Your top pick counts first in the ranked-choice vote." : "Voting is closed."}
        </p>
        <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
          {ranking.map((oid, i) => {
            const opt = optionById[oid];
            if (!opt) return null;
            return (
              <div key={oid} style={{ display: "flex", alignItems: "center", gap: 12, padding: "12px 14px", background: C.surface, borderRadius: 12, border: `1px solid ${i === 0 ? C.gold : C.line}` }}>
                <span style={{ font: "700 0.9rem 'Fraunces', serif", color: i === 0 ? C.goldDeep : C.textSoft, width: 18 }}>{i + 1}</span>
                <span style={{ flex: 1, font: "600 0.92rem 'Inter'", color: C.ink }}>{opt.text}</span>
                {isOpen && (
                  <div style={{ display: "flex", flexDirection: "column" }}>
                    <button onClick={() => move(i, -1)} style={{ border: "none", background: "transparent", cursor: "pointer", padding: 0, color: C.textSoft }}><ChevronUp size={16} /></button>
                    <button onClick={() => move(i, 1)} style={{ border: "none", background: "transparent", cursor: "pointer", padding: 0, color: C.textSoft }}><ChevronDown size={16} /></button>
                  </div>
                )}
              </div>
            );
          })}
        </div>
        {isOpen && (
          <button onClick={submitBallot} disabled={submitting}
            style={{ marginTop: 18, width: "100%", border: "none", background: C.forest, color: "#fff", font: "700 0.9rem 'Inter'", padding: "13px", borderRadius: 99, cursor: submitting ? "default" : "pointer", opacity: submitting ? 0.7 : 1 }}>
            {submitting ? "Submitting…" : (session.user_rankings ? "Update my ranking" : "Submit my ranking")}
          </button>
        )}
        {session.user_rankings && isOpen && (
          <p style={{ font: "500 0.78rem 'Inter'", color: C.sageDeep, textAlign: "center", marginTop: 10, display: "flex", alignItems: "center", justifyContent: "center", gap: 5 }}>
            <Check size={14} /> Your ballot is in — you can still change it.
          </p>
        )}
        {error && <p style={{ font: "500 0.82rem 'Inter'", color: "#C0392B", marginTop: 12 }}>{error}</p>}
      </Card>

      {/* tally / results */}
      <Card>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16 }}>
          <span style={{ font: "600 1.1rem 'Fraunces', serif", color: C.forest }}>{isOpen ? "Live first choices" : "Final result"}</span>
          {isOpen
            ? <span style={{ font: "500 0.76rem 'Inter'", color: C.goldDeep, background: C.goldWash, padding: "4px 10px", borderRadius: 99 }}>{isRevote ? "Revote · " : ""}{deadlineLabel(session.deadline)}</span>
            : <span style={{ font: "500 0.76rem 'Inter'", color: C.sageDeep, background: C.sageWash, padding: "4px 10px", borderRadius: 99, display: "inline-flex", alignItems: "center", gap: 5 }}><Lock size={12} /> Closed</span>}
        </div>

        {winner && (
          <div style={{ background: `linear-gradient(135deg, ${C.gold}, ${C.goldDeep})`, color: "#fff", borderRadius: 14, padding: "16px 18px", marginBottom: 16 }}>
            <div style={{ font: "500 0.72rem 'Inter'", textTransform: "uppercase", letterSpacing: "0.08em", opacity: 0.85 }}>Winner{session.is_random_winner ? " (tie-break)" : ""}</div>
            <div style={{ font: "600 1.5rem 'Fraunces', serif", display: "flex", alignItems: "center", gap: 8 }}><Trophy size={20} /> {winner.text}</div>
          </div>
        )}

        <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
          {session.options.map((o) => {
            const lead = winner ? o.id === winner.id : (o.first_choice_votes === maxFirst && o.first_choice_votes > 0);
            return (
              <div key={o.id}>
                <div style={{ display: "flex", justifyContent: "space-between", font: "600 0.86rem 'Inter'", marginBottom: 5 }}>
                  <span style={{ color: lead ? C.goldDeep : C.ink }}>{o.text}</span>
                  <span style={{ color: C.textSoft }}>{o.first_choice_votes} {o.first_choice_votes === 1 ? "vote" : "votes"}</span>
                </div>
                <div style={{ height: 9, borderRadius: 99, background: C.sageWash }}>
                  <div style={{ height: "100%", width: `${((o.first_choice_votes || 0) / maxFirst) * 100}%`, borderRadius: 99, background: lead ? C.gold : C.sage, transition: "width 400ms" }} />
                </div>
              </div>
            );
          })}
        </div>

        <div style={{ marginTop: 18, paddingTop: 16, borderTop: `1px solid ${C.line}`, font: "400 0.84rem 'Inter'", color: C.textSoft, display: "flex", alignItems: "center", gap: 7 }}>
          <Users size={15} /> {session.total_ballots} {session.total_ballots === 1 ? "ballot" : "ballots"} cast
        </div>

        {isAdmin && isOpen && (
          <button onClick={closeVoting} disabled={busy}
            style={{ marginTop: 16, width: "100%", border: `1.5px solid ${C.line}`, background: "transparent", color: C.sageDeep, font: "600 0.85rem 'Inter'", padding: "11px", borderRadius: 99, cursor: busy ? "default" : "pointer", opacity: busy ? 0.6 : 1 }}>
            {busy ? "Closing…" : "Close voting & decide winner"}
          </button>
        )}
      </Card>
    </div>
  );
}