import React, { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { Compass, Users, Check, Plus, ChevronRight, MapPin, LogOut } from "lucide-react";
import { api } from "./api";
import { useAuth } from "./AuthContext";

// Voyant — Dashboard (bento). Wired to real data:
//   stat tiles    → GET /dashboard/stats
//   upcoming/past → GET /trips/my-trips
// Tiles that need data we don't surface yet (active-vote tile, activity
// feed) are intentionally omitted rather than shown with mock data; they
// return when the voting flow / an activity endpoint are wired.

const C = {
  forest: "#2F5D50", forestDeep: "#21443A", sage: "#7BA697", sageDeep: "#4E7C6C",
  gold: "#E0A458", goldSoft: "#F0C97E", goldWash: "#F8EDD7",
  cream: "#F3EEE3", card: "#FBF8F1", surface: "#FFFFFF", dark: "#26312C",
  ink: "#243B34", textSoft: "#6B7872", line: "#E8E1D4", sageWash: "#E7EFEA",
};

const R = 22;

// rotating gradient palette for trip thumbnails (purely cosmetic)
const GRADS = [
  ["#E8C07A", "#C98A3C"], ["#7BA697", "#2F5D50"],
  ["#9CB89A", "#4E7C6C"], ["#8FC8A0", "#3E8E6A"],
];

function Tile({ children, style }) {
  return <div style={{ background: C.card, borderRadius: R, border: `1px solid ${C.line}`, padding: 22, ...style }}>{children}</div>;
}

// format an ISO date → "Jul 12"
function shortDate(iso) {
  if (!iso) return "Dates TBD";
  try {
    return new Date(iso).toLocaleDateString(undefined, { month: "short", day: "numeric" });
  } catch { return "Dates TBD"; }
}

// days until a trip date (for the next-departure tile)
function daysUntil(iso) {
  if (!iso) return null;
  const diff = Math.ceil((new Date(iso) - new Date()) / 86400000);
  return diff;
}

export default function VoyantDashboard() {
  const navigate = useNavigate();
  const { profile, signOutUser } = useAuth();

  const handleSignOut = async () => {
    try { await signOutUser(); } catch (e) { /* ignore */ }
    navigate("/");
  };

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [stats, setStats] = useState(null);
  const [upcoming, setUpcoming] = useState([]);
  const [previous, setPrevious] = useState([]);

  const firstName = profile?.name ? profile.name.split(" ")[0] : "";
  const initial = profile?.name ? profile.name[0].toUpperCase() : "·";

  useEffect(() => {
    let alive = true;
    (async () => {
      try {
        const [statsRes, tripsRes] = await Promise.all([
          api.get("/dashboard/stats"),
          api.get("/trips/my-trips"),
        ]);
        if (!alive) return;
        setStats(statsRes);
        setUpcoming(tripsRes.upcoming || []);
        setPrevious(tripsRes.previous || []);
      } catch (e) {
        if (alive) setError("Couldn't load your dashboard. Please try again.");
      } finally {
        if (alive) setLoading(false);
      }
    })();
    return () => { alive = false; };
  }, []);

  const statTiles = stats ? [
    { label: "Trips planned", value: stats.trips_planned, Icon: Compass },
    { label: "Friends traveling", value: stats.friends_traveling, Icon: Users },
    { label: "Decisions made", value: stats.decisions_made, Icon: Check },
  ] : [];

  // next departure = soonest upcoming trip with a date
  const nextTrip = upcoming
    .filter((t) => t.trip_date)
    .sort((a, b) => new Date(a.trip_date) - new Date(b.trip_date))[0];
  const nextDays = nextTrip ? daysUntil(nextTrip.trip_date) : null;

  const hasNoTrips = !loading && upcoming.length === 0 && previous.length === 0;

  return (
    <div style={{ display: "flex", background: C.cream, minHeight: "100vh", fontFamily: "'Inter', system-ui, sans-serif", padding: 14, gap: 14 }}>
      <link href="https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,500;9..144,600;9..144,700&family=Caveat:wght@600;700&family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet" />

      {/* slim icon rail */}
      <aside style={{ width: 66, background: C.dark, borderRadius: 26, display: "flex", flexDirection: "column", alignItems: "center", padding: "22px 0", gap: 8 }}>
        <button onClick={() => navigate("/dashboard")} title="Dashboard" style={{ width: 42, height: 42, borderRadius: 14, border: "none", cursor: "pointer", display: "grid", placeItems: "center", background: C.gold }}>
          <Compass size={20} strokeWidth={2} color={C.forestDeep} />
        </button>

        <div style={{ marginTop: "auto", display: "flex", flexDirection: "column", alignItems: "center", gap: 10 }}>
          <button onClick={handleSignOut} title="Sign out" style={{ width: 42, height: 42, borderRadius: 14, border: "none", cursor: "pointer", display: "grid", placeItems: "center", background: "transparent" }}>
            <LogOut size={20} strokeWidth={2} color="rgba(255,255,255,0.7)" />
          </button>
          <div title={profile?.name || ""} style={{ width: 38, height: 38, borderRadius: 99, background: C.gold, color: C.dark, display: "grid", placeItems: "center", font: "700 0.9rem 'Inter'" }}>{initial}</div>
        </div>
      </aside>

      {/* main */}
      <main style={{ flex: 1, display: "flex", flexDirection: "column", gap: 16 }}>
        {/* header */}
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "8px 6px" }}>
          <div>
            <h1 style={{ font: "600 2rem 'Fraunces', serif", color: C.forest, margin: 0 }}>{firstName ? `Welcome back, ${firstName}` : "Welcome back"}</h1>
            <div style={{ font: "400 0.9rem 'Inter'", color: C.textSoft, marginTop: 2 }}>Here's what your groups are deciding today.</div>
          </div>
          <button onClick={() => navigate("/create")} style={{ border: "none", background: C.forest, color: "#fff", font: "700 0.88rem 'Inter'", padding: "12px 22px", borderRadius: 99, cursor: "pointer", display: "flex", alignItems: "center", gap: 7 }}><Plus size={17} strokeWidth={2.5} /> New trip</button>
        </div>

        {/* loading */}
        {loading && (
          <div style={{ padding: "80px 0", textAlign: "center", color: C.textSoft, font: "400 0.95rem 'Inter'" }}>
            Loading your trips…
          </div>
        )}

        {/* error */}
        {!loading && error && (
          <Tile style={{ textAlign: "center", padding: "40px" }}>
            <div style={{ font: "500 0.95rem 'Inter'", color: "#C0392B" }}>{error}</div>
          </Tile>
        )}

        {/* empty state — brand new user, no trips */}
        {hasNoTrips && !error && (
          <div style={{ textAlign: "center", padding: "70px 20px", maxWidth: 440, margin: "0 auto" }}>
            <div style={{ fontFamily: "'Caveat', cursive", fontWeight: 700, fontSize: "1.8rem", color: C.gold }}>Where to next?</div>
            <h2 style={{ font: "600 1.9rem 'Fraunces', serif", color: C.forest, margin: "8px 0 12px" }}>No trips yet</h2>
            <p style={{ font: "400 1rem 'Inter'", color: C.textSoft, lineHeight: 1.6, marginBottom: 26 }}>
              Start your first trip, invite your friends, and let the group decide where you're all headed.
            </p>
            <button onClick={() => navigate("/create")} style={{ border: "none", background: C.gold, color: "#3A2A12", font: "700 0.95rem 'Inter'", padding: "14px 30px", borderRadius: 99, cursor: "pointer" }}>
              Create your first trip
            </button>
          </div>
        )}

        {/* BENTO GRID — only when there's data */}
        {!loading && !error && !hasNoTrips && (
          <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gridAutoRows: "minmax(96px, auto)", gap: 16 }}>

            {/* Stat tiles */}
            {statTiles.map((s) => (
              <Tile key={s.label} style={{ display: "flex", flexDirection: "column", justifyContent: "center", gap: 6 }}>
                <s.Icon size={20} strokeWidth={2} color={C.gold} />
                <div style={{ font: "600 1.9rem 'Fraunces', serif", color: C.forest, lineHeight: 1 }}>{s.value ?? 0}</div>
                <div style={{ font: "400 0.78rem 'Inter'", color: C.textSoft }}>{s.label}</div>
              </Tile>
            ))}

            {/* Next departure — only if there's a dated upcoming trip */}
            {nextTrip && nextDays != null && (
              <Tile style={{ background: C.gold, color: C.forestDeep, display: "flex", flexDirection: "column", justifyContent: "center" }}>
                <div style={{ font: "500 0.72rem 'Inter'", letterSpacing: "0.08em", textTransform: "uppercase", opacity: 0.7 }}>Next departure</div>
                <div style={{ font: "600 2.4rem 'Fraunces', serif", lineHeight: 1, margin: "4px 0" }}>{Math.max(nextDays, 0)}<span style={{ fontSize: "1rem" }}> days</span></div>
                <div style={{ font: "500 0.8rem 'Inter'" }}>{nextTrip.name}</div>
              </Tile>
            )}

            {/* Upcoming trips */}
            <Tile style={{ gridColumn: "span 2" }}>
              <div style={{ font: "600 1.05rem 'Fraunces', serif", color: C.forest, marginBottom: 14 }}>Upcoming trips</div>
              {upcoming.length === 0 ? (
                <div style={{ font: "400 0.88rem 'Inter'", color: C.textSoft, padding: "8px 0" }}>No upcoming trips yet.</div>
              ) : (
                <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
                  {upcoming.map((t, i) => (
                    <div key={t.id} onClick={() => navigate("/trip/" + t.id)} style={{ display: "flex", alignItems: "center", gap: 12, cursor: "pointer" }}>
                      <div style={{ width: 44, height: 44, borderRadius: 12, background: `linear-gradient(135deg, ${GRADS[i % GRADS.length][0]}, ${GRADS[i % GRADS.length][1]})`, flexShrink: 0 }} />
                      <div style={{ flex: 1 }}>
                        <div style={{ font: "600 0.95rem 'Inter'", color: C.ink }}>{t.name}</div>
                        <div style={{ font: "400 0.78rem 'Inter'", color: C.textSoft }}>{shortDate(t.trip_date)} · {t.destination || "Destination TBD"}</div>
                      </div>
                      <ChevronRight size={18} color={C.textSoft} />
                    </div>
                  ))}
                </div>
              )}
            </Tile>

            {/* Past adventures */}
            <Tile style={{ gridColumn: "span 2" }}>
              <div style={{ font: "600 1.05rem 'Fraunces', serif", color: C.forest, marginBottom: 14 }}>Past adventures</div>
              {previous.length === 0 ? (
                <div style={{ font: "400 0.88rem 'Inter'", color: C.textSoft, padding: "8px 0" }}>No past trips yet.</div>
              ) : (
                <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
                  {previous.map((t, i) => (
                    <div key={t.id} onClick={() => navigate("/trip/" + t.id)} style={{ display: "flex", alignItems: "center", gap: 12, cursor: "pointer" }}>
                      <div style={{ width: 44, height: 44, borderRadius: 12, background: C.sageWash, display: "grid", placeItems: "center", flexShrink: 0 }}>
                        <MapPin size={18} color={C.sageDeep} />
                      </div>
                      <div style={{ flex: 1 }}>
                        <div style={{ font: "600 0.95rem 'Inter'", color: C.ink }}>{t.name}</div>
                        <div style={{ font: "400 0.78rem 'Inter'", color: C.textSoft }}>{shortDate(t.trip_date)} · {t.destination || "—"}</div>
                      </div>
                      <ChevronRight size={18} color={C.textSoft} />
                    </div>
                  ))}
                </div>
              )}
            </Tile>

          </div>
        )}
      </main>
    </div>
  );
}