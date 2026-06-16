import React, { useRef, useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Cpu, GitBranch, ShieldCheck, BarChart3, Layers, Zap, CheckCircle2, ArrowRight } from "lucide-react";
import { API_BASE } from "./api";

// Voyant — "How our AI works" — public, polished showcase of the AI
// engineering (model gateway, prompt versioning, A/B testing, eval,
// observability). Green/gold + Fraunces.
//
// Live numbers come from GET /ai-metrics/public (no auth). When the DB
// has no AI calls yet, we fall back to representative placeholders so
// the page never looks broken on a fresh deploy.

const C = {
  forest: "#2F5D50", forestDeep: "#1B3B32", sage: "#7BA697", sageDeep: "#4E7C6C",
  gold: "#E0A458", goldSoft: "#F0C97E", goldWash: "#F8EDD7", goldDeep: "#C98A3C",
  cream: "#F3EEE3", card: "#FBF8F1", surface: "#FFFFFF",
  ink: "#243B34", textSoft: "#6B7872", line: "#E8E1D4", sageWash: "#E7EFEA",
};

// ── FALLBACK metrics (shown only until real AI calls accumulate) ──
const FALLBACK_SUMMARY = [
  { label: "AI calls logged", value: "—", icon: Cpu },
  { label: "Avg. response", value: "—", icon: Zap },
  { label: "Success rate", value: "—", icon: ShieldCheck },
  { label: "Avg. eval score", value: "—", icon: CheckCircle2 },
];
const FALLBACK_GATEWAY = [
  { model: "Groq · Llama 3.1 8B", role: "Primary", share: 0, color: C.forest },
  { model: "Groq · Llama 3.3 70B", role: "Fallback", share: 0, color: C.sageDeep },
  { model: "Gemini Flash", role: "Last resort", share: 0, color: C.gold },
];
const FALLBACK_PROMPTS = [
  { v: "recommendations_v2", status: "Consensus-weighted", eval: null, cost: "—", winner: false },
  { v: "recommendations_v1", status: "Baseline", eval: null, cost: "—", winner: false },
];
const EVAL_CHECKS = [
  "Returns valid, parseable JSON", "Exactly 10 destinations", "All required fields present",
  "No duplicate destinations", "Match scores within range", "Respects group's exclusions",
];
const PIPELINE = [
  { n: 1, t: "Aggregate", d: "Combine every member's form answers into one group preference profile." },
  { n: 2, t: "Prompt", d: "Render a versioned prompt template with the group's data." },
  { n: 3, t: "Gateway", d: "Try Groq, then a stronger Groq model, then Gemini — logging tokens, cost & latency." },
  { n: 4, t: "Evaluate", d: "Score the output against deterministic quality checks (0–1)." },
  { n: 5, t: "Store", d: "Save as a new version so history is never overwritten." },
];

// friendly labels for known model IDs
const MODEL_LABELS = {
  "llama-3.1-8b-instant": "Groq · Llama 3.1 8B",
  "llama-3.3-70b-versatile": "Groq · Llama 3.3 70B",
  "gemini-2.5-flash": "Gemini Flash",
};
const ROLE_BY_POSITION = ["Primary", "Fallback", "Last resort"];

function useInView(th = 0.15) {
  const ref = useRef(null); const [seen, setSeen] = useState(false);
  useEffect(() => { const el = ref.current; if (!el) return;
    const o = new IntersectionObserver(([e]) => e.isIntersecting && (setSeen(true), o.disconnect()), { threshold: th });
    o.observe(el); return () => o.disconnect();
  }, [th]);
  return [ref, seen];
}

function Section({ children, style }) {
  const [ref, seen] = useInView();
  return <div ref={ref} style={{ opacity: seen ? 1 : 0, transform: seen ? "translateY(0)" : "translateY(24px)", transition: "opacity 600ms ease-out, transform 600ms cubic-bezier(0.22,1,0.36,1)", ...style }}>{children}</div>;
}

function Card({ children, style }) {
  return <div style={{ background: C.card, borderRadius: 20, border: `1px solid ${C.line}`, padding: 26, ...style }}>{children}</div>;
}

export default function VoyantHowAI() {
  const navigate = useNavigate();
  const [summary, setSummary] = useState(FALLBACK_SUMMARY);
  const [gateway, setGateway] = useState(FALLBACK_GATEWAY);
  const [prompts, setPrompts] = useState(FALLBACK_PROMPTS);

  useEffect(() => {
    (async () => {
      try {
        const res = await fetch(`${API_BASE}/ai-metrics/public`);
        if (!res.ok) return;            // keep fallbacks
        const d = await res.json();
        if (!d || !d.total_calls) return; // no real calls yet → keep fallbacks

        // summary tiles
        setSummary([
          { label: "AI calls logged", value: d.total_calls.toLocaleString(), icon: Cpu },
          { label: "Avg. response", value: d.avg_latency_ms ? `${(d.avg_latency_ms / 1000).toFixed(1)}s` : "—", icon: Zap },
          { label: "Success rate", value: d.success_rate != null ? `${Math.round(d.success_rate * 100)}%` : "—", icon: ShieldCheck },
          { label: "Avg. eval score", value: d.avg_eval_score != null ? d.avg_eval_score.toFixed(2) : "—", icon: CheckCircle2 },
        ]);

        // gateway usage split (per_model), ordered by share desc
        if (Array.isArray(d.per_model) && d.per_model.length) {
          const colors = [C.forest, C.sageDeep, C.gold];
          const sorted = [...d.per_model].sort((a, b) => (b.share || 0) - (a.share || 0));
          setGateway(sorted.map((m, i) => ({
            model: MODEL_LABELS[m.model] || m.model,
            role: ROLE_BY_POSITION[i] || "Model",
            share: Math.round((m.share || 0) * 100),
            color: colors[i % colors.length],
          })));
        }

        // prompt versions (eval + cost)
        if (Array.isArray(d.prompt_versions) && d.prompt_versions.length) {
          const pv = [...d.prompt_versions].sort((a, b) => (b.avg_eval_score || 0) - (a.avg_eval_score || 0));
          const topScore = pv[0]?.avg_eval_score;
          setPrompts(pv.map((p) => ({
            v: p.prompt_version,
            status: p.prompt_version.includes("v2") ? "Consensus-weighted" : "Baseline",
            eval: p.avg_eval_score,
            cost: p.avg_cost_per_call_usd != null ? `$${p.avg_cost_per_call_usd.toFixed(4)}` : "—",
            winner: p.avg_eval_score != null && p.avg_eval_score === topScore,
          })));
        }
      } catch {
        // network/CORS issue → keep fallbacks, page still looks complete
      }
    })();
  }, []);

  return (
    <div style={{ background: C.cream, minHeight: "100vh", fontFamily: "'Inter', system-ui, sans-serif" }}>
      <link href="https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,500;9..144,600;9..144,700&family=Caveat:wght@600;700&family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet" />

      {/* hero */}
      <div style={{ background: `linear-gradient(160deg, ${C.forest}, ${C.forestDeep})`, color: "#fff", padding: "26px 32px 90px", textAlign: "center", position: "relative" }}>
        {/* clickable brand = home button */}
        <div onClick={() => navigate("/")} style={{ position: "absolute", top: 24, left: 32, display: "flex", alignItems: "center", gap: 9, cursor: "pointer" }}>
          <span style={{ font: "600 1.3rem 'Fraunces', serif", color: "#fff" }}>Voyant</span>
        </div>
        <div style={{ fontFamily: "'Caveat', cursive", fontWeight: 700, fontSize: "1.7rem", color: C.goldSoft, marginBottom: 8, marginTop: 54 }}>Under the hood</div>
        <h1 style={{ font: "600 3rem 'Fraunces', serif", margin: "0 auto", maxWidth: 720, lineHeight: 1.08, letterSpacing: "-0.02em" }}>
          How Voyant's AI actually works
        </h1>
        <p style={{ font: "400 1.1rem 'Inter'", color: "rgba(255,255,255,0.8)", maxWidth: 560, margin: "18px auto 0", lineHeight: 1.6 }}>
          Not a thin wrapper around an API. A resilient, observable recommendation engine — with fallback, versioned prompts, automated evaluation, and full cost tracking.
        </p>
      </div>

      <div style={{ maxWidth: 1040, margin: "0 auto", padding: "0 32px 90px" }}>
        {/* summary metrics — pulled up over the hero */}
        <Section style={{ marginTop: -50 }}>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 16 }}>
            {summary.map((s) => (
              <Card key={s.label} style={{ textAlign: "center" }}>
                <s.icon size={22} color={C.gold} style={{ marginBottom: 10 }} />
                <div style={{ font: "600 1.8rem 'Fraunces', serif", color: C.forest, lineHeight: 1 }}>{s.value}</div>
                <div style={{ font: "400 0.78rem 'Inter'", color: C.textSoft, marginTop: 6 }}>{s.label}</div>
              </Card>
            ))}
          </div>
        </Section>

        {/* pipeline */}
        <Section style={{ marginTop: 70 }}>
          <h2 style={{ font: "600 2rem 'Fraunces', serif", color: C.forest, textAlign: "center", margin: "0 0 8px" }}>The recommendation pipeline</h2>
          <p style={{ font: "400 1rem 'Inter'", color: C.textSoft, textAlign: "center", margin: "0 0 36px" }}>Every suggestion runs through five engineered stages.</p>
          <div style={{ display: "flex", alignItems: "stretch", gap: 0, flexWrap: "wrap", justifyContent: "center" }}>
            {PIPELINE.map((p, i) => (
              <React.Fragment key={p.n}>
                <Card style={{ flex: "1 1 170px", minWidth: 170, textAlign: "center" }}>
                  <div style={{ width: 38, height: 38, borderRadius: 11, background: C.goldWash, color: C.goldDeep, display: "grid", placeItems: "center", font: "700 0.95rem 'Inter'", margin: "0 auto 12px" }}>{p.n}</div>
                  <div style={{ font: "600 1.05rem 'Fraunces', serif", color: C.forest, marginBottom: 6 }}>{p.t}</div>
                  <div style={{ font: "400 0.82rem 'Inter'", color: C.textSoft, lineHeight: 1.5 }}>{p.d}</div>
                </Card>
                {i < PIPELINE.length - 1 && <div style={{ display: "flex", alignItems: "center", padding: "0 6px", color: C.sage }}><ArrowRight size={18} /></div>}
              </React.Fragment>
            ))}
          </div>
        </Section>

        {/* gateway + prompts side by side */}
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 20, marginTop: 60 }}>
          <Section>
            <Card style={{ height: "100%" }}>
              <div style={{ display: "flex", alignItems: "center", gap: 9, marginBottom: 6 }}>
                <ShieldCheck size={20} color={C.gold} />
                <span style={{ font: "600 1.2rem 'Fraunces', serif", color: C.forest }}>Model gateway & fallback</span>
              </div>
              <p style={{ font: "400 0.88rem 'Inter'", color: C.textSoft, margin: "0 0 18px", lineHeight: 1.55 }}>
                If a provider fails or rate-limits, requests roll to the next automatically — so the feature never goes down.
              </p>
              {gateway.map((g) => (
                <div key={g.model} style={{ marginBottom: 14 }}>
                  <div style={{ display: "flex", justifyContent: "space-between", font: "600 0.85rem 'Inter'", color: C.ink, marginBottom: 5 }}>
                    <span>{g.model} <span style={{ color: C.textSoft, fontWeight: 400 }}>· {g.role}</span></span>
                    <span style={{ color: C.textSoft }}>{g.share}%</span>
                  </div>
                  <div style={{ height: 8, borderRadius: 99, background: C.sageWash }}>
                    <div style={{ height: "100%", width: `${g.share}%`, borderRadius: 99, background: g.color }} />
                  </div>
                </div>
              ))}
            </Card>
          </Section>

          <Section>
            <Card style={{ height: "100%" }}>
              <div style={{ display: "flex", alignItems: "center", gap: 9, marginBottom: 6 }}>
                <GitBranch size={20} color={C.gold} />
                <span style={{ font: "600 1.2rem 'Fraunces', serif", color: C.forest }}>Prompt versioning & A/B tests</span>
              </div>
              <p style={{ font: "400 0.88rem 'Inter'", color: C.textSoft, margin: "0 0 18px", lineHeight: 1.55 }}>
                Prompts are versioned and tested head-to-head. The higher-scoring, cheaper version wins.
              </p>
              {prompts.map((p) => (
                <div key={p.v} style={{ display: "flex", alignItems: "center", gap: 12, padding: "12px 14px", borderRadius: 12, marginBottom: 10, background: p.winner ? C.goldWash : C.surface, border: `1px solid ${p.winner ? C.gold : C.line}` }}>
                  <div style={{ flex: 1 }}>
                    <div style={{ font: "600 0.86rem 'Inter'", color: C.ink, fontFamily: "ui-monospace, monospace" }}>{p.v}</div>
                    <div style={{ font: "400 0.72rem 'Inter'", color: C.textSoft }}>{p.status}{p.winner && " · winner"}</div>
                  </div>
                  <div style={{ textAlign: "right" }}>
                    <div style={{ font: "700 0.9rem 'Inter'", color: p.winner ? C.goldDeep : C.ink }}>{p.eval != null ? p.eval.toFixed(2) : "—"}</div>
                    <div style={{ font: "400 0.68rem 'Inter'", color: C.textSoft }}>eval · {p.cost}/call</div>
                  </div>
                </div>
              ))}
            </Card>
          </Section>
        </div>

        {/* eval checks */}
        <Section style={{ marginTop: 60 }}>
          <Card>
            <div style={{ display: "flex", alignItems: "center", gap: 9, marginBottom: 6 }}>
              <CheckCircle2 size={20} color={C.gold} />
              <span style={{ font: "600 1.2rem 'Fraunces', serif", color: C.forest }}>Automated quality evaluation</span>
            </div>
            <p style={{ font: "400 0.9rem 'Inter'", color: C.textSoft, margin: "0 0 18px", lineHeight: 1.55, maxWidth: 640 }}>
              Every AI response is scored against deterministic checks before it reaches users — no guesswork, no LLM-judging-an-LLM. Each call gets a 0–1 quality score, stored alongside its prompt version and cost.
            </p>
            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(240px, 1fr))", gap: 10 }}>
              {EVAL_CHECKS.map((c) => (
                <div key={c} style={{ display: "flex", alignItems: "center", gap: 9, padding: "11px 14px", background: C.sageWash, borderRadius: 10, font: "500 0.84rem 'Inter'", color: C.ink }}>
                  <CheckCircle2 size={16} color={C.sageDeep} /> {c}
                </div>
              ))}
            </div>
          </Card>
        </Section>

        {/* closing line */}
        <Section style={{ marginTop: 50, textAlign: "center" }}>
          <p style={{ font: "400 0.95rem 'Inter'", color: C.textSoft, maxWidth: 560, margin: "0 auto", lineHeight: 1.6 }}>
            Every metric here is logged per call in a dedicated observability table — making the AI measurable, debuggable, and improvable over time.
          </p>
        </Section>
      </div>
    </div>
  );
}