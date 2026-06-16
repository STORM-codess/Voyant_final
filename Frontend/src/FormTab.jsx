import React, { useState, useEffect } from "react";
import { Check, Clock, Send, Trash2, Plus } from "lucide-react";
import { api } from "./api";

// Voyant — Form tab: the member-fill experience.
// Fetches the trip's latest form (GET /forms/{tripId}/form), renders each
// question by type, and submits answers (POST /forms/{tripId}/submit).
// Handles: no form yet, already-submitted, validation, all 5 question types
// (text, single_choice, multiple_choice, scale, range).

const C = {
  forest: "#2F5D50", forestDeep: "#21443A", sage: "#7BA697", sageDeep: "#4E7C6C",
  gold: "#E0A458", goldSoft: "#F0C97E", goldWash: "#F8EDD7", goldDeep: "#C98A3C",
  cream: "#F3EEE3", card: "#FBF8F1", surface: "#FFFFFF",
  ink: "#243B34", textSoft: "#6B7872", line: "#E8E1D4", sageWash: "#E7EFEA",
};

function Card({ children, style }) {
  return <div style={{ background: C.card, borderRadius: 20, border: `1px solid ${C.line}`, padding: 24, ...style }}>{children}</div>;
}

// derive [min, max] for scale/range questions from options, with a sane default
function scaleBounds(options) {
  if (Array.isArray(options) && options.length >= 2) {
    const nums = options.map(Number).filter((n) => !Number.isNaN(n));
    if (nums.length >= 2) return [Math.min(...nums), Math.max(...nums)];
  }
  return [1, 5];
}

export default function FormTab({ tripId, isAdmin }) {
  const [loading, setLoading] = useState(true);
  const [form, setForm] = useState(null);
  const [notFound, setNotFound] = useState(false);
  const [error, setError] = useState("");
  const [answers, setAnswers] = useState({});      // questionId → { text } | { options: [] }
  const [submitting, setSubmitting] = useState(false);
  const [submitted, setSubmitted] = useState(false);

  // admin create-form sub-flow
  const [templates, setTemplates] = useState(null);
  const [creating, setCreating] = useState(false);
  const [adminError, setAdminError] = useState("");
  // custom-form builder
  const [builder, setBuilder] = useState(null);     // { template, questions:[{...,include}] } or null

  const QTYPES = [
    { v: "single_choice", label: "Single choice" },
    { v: "multiple_choice", label: "Multiple choice" },
    { v: "text", label: "Text" },
    { v: "scale", label: "Scale (1–5)" },
  ];

  const load = async () => {
    setLoading(true);
    setError("");
    try {
      const data = await api.get(`/forms/${tripId}/form`);
      setForm(data);
      setSubmitted(!!data.already_submitted);
      // pre-fill any existing answers
      const initial = {};
      (data.answers || []).forEach((a) => {
        initial[a.question_id] = {
          text: a.answer_text || "",
          options: a.answer_options || [],
        };
      });
      setAnswers(initial);
    } catch (e) {
      if (e.status === 404) setNotFound(true);
      else if (e.status === 403) setError("You need to be a trip member to view the form.");
      else setError("Couldn't load the form.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, [tripId]);

  // ── admin: load templates when there's no form and viewer is admin ──
  const loadTemplates = async () => {
    setAdminError("");
    try {
      const data = await api.get("/forms/templates");
      setTemplates(data || []);
    } catch (e) {
      setAdminError("Couldn't load form templates.");
    }
  };
  useEffect(() => {
    if (notFound && isAdmin && templates === null) loadTemplates();
  }, [notFound, isAdmin]);

  // create a form from a template, then publish it immediately, then reload
  const handleCreateAndPublish = async (template) => {
    // custom template → open the builder instead of creating immediately
    if (template.is_custom) {
      setBuilder({
        template,
        questions: (template.questions || []).map((q) => ({
          question_text: q.question_text,
          question_type: q.question_type,
          options: q.options ? [...q.options] : [],
          is_required: q.is_required,
          placeholder: q.placeholder || "",
          include: true,
        })),
      });
      return;
    }
    await doCreate(template.id, null);
  };

  // shared create+publish; custom_questions null = copy template questions
  const doCreate = async (templateId, customQuestions, title) => {
    setCreating(true);
    setAdminError("");
    try {
      const body = {
        template_id: templateId,
        title: title || "Trip preferences",
        description: null,
      };
      if (customQuestions) body.custom_questions = customQuestions;
      await api.post(`/forms/${tripId}/create`, body);
      await api.post(`/forms/${tripId}/publish`, {});
      setBuilder(null);
      setNotFound(false);
      await load();
    } catch (e) {
      if (e.status === 400) setAdminError(e.message || "There's already an active form, or a question is invalid.");
      else if (e.status === 403) setAdminError("Only trip members can create the form.");
      else setAdminError("Couldn't create the form. Please try again.");
      setCreating(false);
    }
  };

  // ── builder helpers ──
  const bUpdate = (i, patch) => setBuilder((b) => ({ ...b, questions: b.questions.map((q, idx) => idx === i ? { ...q, ...patch } : q) }));
  const bRemove = (i) => setBuilder((b) => ({ ...b, questions: b.questions.filter((_, idx) => idx !== i) }));
  const bAddQuestion = () => setBuilder((b) => ({ ...b, questions: [...b.questions, { question_text: "", question_type: "single_choice", options: ["", ""], is_required: false, placeholder: "", include: true }] }));
  const bSetOption = (qi, oi, val) => setBuilder((b) => ({ ...b, questions: b.questions.map((q, idx) => idx === qi ? { ...q, options: q.options.map((o, oidx) => oidx === oi ? val : o) } : q) }));
  const bAddOption = (qi) => setBuilder((b) => ({ ...b, questions: b.questions.map((q, idx) => idx === qi ? { ...q, options: [...q.options, ""] } : q) }));
  const bRemoveOption = (qi, oi) => setBuilder((b) => ({ ...b, questions: b.questions.map((q, idx) => idx === qi ? { ...q, options: q.options.filter((_, oidx) => oidx !== oi) } : q) }));

  const submitBuilder = async () => {
    const chosen = builder.questions.filter((q) => q.include);
    if (chosen.length === 0) { setAdminError("Include at least one question."); return; }
    for (const q of chosen) {
      if (!q.question_text.trim()) { setAdminError("Every included question needs text."); return; }
      if (q.question_type === "single_choice" || q.question_type === "multiple_choice") {
        const opts = q.options.map((o) => o.trim()).filter(Boolean);
        if (opts.length < 2) { setAdminError(`"${q.question_text || "A choice question"}" needs at least 2 options.`); return; }
      }
    }
    const payload = chosen.map((q) => {
      const isChoice = q.question_type === "single_choice" || q.question_type === "multiple_choice";
      const isScale = q.question_type === "scale" || q.question_type === "range";
      return {
        question_text: q.question_text.trim(),
        question_type: q.question_type,
        options: isChoice ? q.options.map((o) => o.trim()).filter(Boolean) : (isScale ? ["1", "5"] : null),
        is_required: q.is_required,
        placeholder: q.placeholder || null,
      };
    });
    await doCreate(builder.template.id, payload, "Trip preferences");
  };

  // ── answer setters ──
  const setText = (qid, text) => setAnswers((p) => ({ ...p, [qid]: { ...p[qid], text } }));
  const setSingle = (qid, opt) => setAnswers((p) => ({ ...p, [qid]: { options: [opt] } }));
  const toggleMulti = (qid, opt) => setAnswers((p) => {
    const cur = p[qid]?.options || [];
    const next = cur.includes(opt) ? cur.filter((o) => o !== opt) : [...cur, opt];
    return { ...p, [qid]: { options: next } };
  });

  const handleSubmit = async () => {
    if (!form) return;
    // client-side required check (server re-validates)
    for (const q of form.questions) {
      if (!q.is_required) continue;
      const a = answers[q.id];
      const hasText = a?.text && a.text.trim();
      const hasOpts = a?.options && a.options.length > 0;
      if (!hasText && !hasOpts) {
        setError(`Please answer: "${q.question_text}"`);
        return;
      }
    }
    setSubmitting(true);
    setError("");
    try {
      const payload = {
        answers: form.questions
          .filter((q) => {
            const a = answers[q.id];
            return (a?.text && a.text.trim()) || (a?.options && a.options.length);
          })
          .map((q) => {
            const a = answers[q.id];
            const isChoice = q.question_type === "single_choice" || q.question_type === "multiple_choice";
            return isChoice
              ? { question_id: q.id, answer_options: a.options || [] }
              : { question_id: q.id, answer_text: (a.text || "").toString() };
          }),
      };
      await api.post(`/forms/${tripId}/submit`, payload);
      setSubmitted(true);
    } catch (e) {
      if (e.status === 422) setError("Some answers need fixing — please check required questions and choices.");
      else if (e.status === 400) setError("This form is no longer accepting responses.");
      else setError("Couldn't submit your answers. Please try again.");
    } finally {
      setSubmitting(false);
    }
  };

  if (loading) return <Card style={{ textAlign: "center", padding: 40, color: C.textSoft }}>Loading form…</Card>;

  // no form created yet
  if (notFound) {
    // ── ADMIN: custom-form builder (shown after picking the Custom template) ──
    if (isAdmin && builder) {
      return (
        <Card style={{ padding: "30px 26px" }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: 10, marginBottom: 6 }}>
            <div style={{ font: "600 1.3rem 'Fraunces', serif", color: C.forest }}>Build your form</div>
            <button onClick={() => { setBuilder(null); setAdminError(""); }} style={{ border: `1.5px solid ${C.line}`, background: "transparent", color: C.textSoft, font: "600 0.8rem 'Inter'", padding: "7px 14px", borderRadius: 99, cursor: "pointer" }}>← Back to templates</button>
          </div>
          <p style={{ font: "400 0.88rem 'Inter'", color: C.textSoft, lineHeight: 1.6, margin: "0 0 8px", maxWidth: 580 }}>
            Toggle the questions you want, edit any of them, or add your own. The budget, trip-length, vibe and route questions give the AI the strongest signal — custom questions are passed along as extra context.
          </p>

          <div style={{ display: "flex", flexDirection: "column", gap: 14, marginTop: 18 }}>
            {builder.questions.map((q, i) => (
              <div key={i} style={{ border: `1.5px solid ${q.include ? C.line : "#EFEAE0"}`, background: q.include ? C.surface : "#FAF7F0", borderRadius: 14, padding: "14px 16px", opacity: q.include ? 1 : 0.6 }}>
                <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 10 }}>
                  <button onClick={() => bUpdate(i, { include: !q.include })} title={q.include ? "Exclude" : "Include"}
                    style={{ width: 22, height: 22, borderRadius: 6, border: `1.5px solid ${q.include ? C.forest : C.line}`, background: q.include ? C.forest : "transparent", cursor: "pointer", display: "grid", placeItems: "center", flexShrink: 0 }}>
                    {q.include && <Check size={14} color="#fff" />}
                  </button>
                  <input value={q.question_text} onChange={(e) => bUpdate(i, { question_text: e.target.value })} placeholder="Question text"
                    style={{ flex: 1, border: "none", borderBottom: `1.5px solid ${C.line}`, background: "transparent", font: "600 0.92rem 'Inter'", color: C.ink, padding: "4px 2px", outline: "none" }} />
                  <button onClick={() => bRemove(i)} title="Remove" style={{ border: "none", background: "transparent", color: C.textSoft, cursor: "pointer", padding: 4 }}><Trash2 size={15} /></button>
                </div>

                <div style={{ display: "flex", alignItems: "center", gap: 10, flexWrap: "wrap", marginBottom: q.question_type.includes("choice") ? 10 : 0 }}>
                  <select value={q.question_type} onChange={(e) => bUpdate(i, { question_type: e.target.value, options: e.target.value.includes("choice") ? (q.options.length ? q.options : ["", ""]) : q.options })}
                    style={{ border: `1.5px solid ${C.line}`, borderRadius: 8, padding: "6px 10px", font: "500 0.8rem 'Inter'", color: C.ink, background: C.surface }}>
                    {QTYPES.map((t) => <option key={t.v} value={t.v}>{t.label}</option>)}
                  </select>
                  <label style={{ font: "500 0.8rem 'Inter'", color: C.textSoft, display: "flex", alignItems: "center", gap: 6, cursor: "pointer" }}>
                    <input type="checkbox" checked={q.is_required} onChange={(e) => bUpdate(i, { is_required: e.target.checked })} /> Required
                  </label>
                </div>

                {(q.question_type === "single_choice" || q.question_type === "multiple_choice") && (
                  <div style={{ display: "flex", flexDirection: "column", gap: 6, paddingLeft: 32 }}>
                    {q.options.map((opt, oi) => (
                      <div key={oi} style={{ display: "flex", alignItems: "center", gap: 8 }}>
                        <input value={opt} onChange={(e) => bSetOption(i, oi, e.target.value)} placeholder={`Option ${oi + 1}`}
                          style={{ flex: 1, border: `1px solid ${C.line}`, borderRadius: 8, padding: "6px 10px", font: "400 0.84rem 'Inter'", color: C.ink, background: C.surface }} />
                        {q.options.length > 2 && <button onClick={() => bRemoveOption(i, oi)} style={{ border: "none", background: "transparent", color: C.textSoft, cursor: "pointer", padding: 2 }}><Trash2 size={13} /></button>}
                      </div>
                    ))}
                    <button onClick={() => bAddOption(i)} style={{ alignSelf: "flex-start", border: "none", background: "transparent", color: C.sageDeep, font: "600 0.8rem 'Inter'", cursor: "pointer", padding: "2px 0" }}>+ Add option</button>
                  </div>
                )}
              </div>
            ))}
          </div>

          <button onClick={bAddQuestion} style={{ marginTop: 14, border: `1.5px dashed ${C.line}`, background: "transparent", color: C.sageDeep, font: "600 0.85rem 'Inter'", padding: "11px 18px", borderRadius: 12, cursor: "pointer", display: "flex", alignItems: "center", gap: 7 }}>
            <Plus size={16} /> Add your own question
          </button>

          {adminError && <p style={{ font: "500 0.84rem 'Inter'", color: "#C0392B", marginTop: 16 }}>{adminError}</p>}

          <button onClick={submitBuilder} disabled={creating} style={{ marginTop: 20, border: "none", background: C.forest, color: "#fff", font: "700 0.9rem 'Inter'", padding: "13px 28px", borderRadius: 99, cursor: creating ? "default" : "pointer", opacity: creating ? 0.7 : 1 }}>
            {creating ? "Publishing…" : "Publish form"}
          </button>
        </Card>
      );
    }

    // ── ADMIN: pick a template to create + publish the form ──
    if (isAdmin) {
      return (
        <Card style={{ padding: "32px 28px" }}>
          <div style={{ font: "600 1.3rem 'Fraunces', serif", color: C.forest, marginBottom: 6 }}>Set up the preferences form</div>
          <p style={{ font: "400 0.92rem 'Inter'", color: C.textSoft, lineHeight: 1.6, margin: "0 0 22px", maxWidth: 560 }}>
            Pick a starting template. Your group answers these questions, and the AI uses everyone's responses to suggest destinations. Choosing one publishes it right away so members can start filling it in.
          </p>

          {templates === null ? (
            <div style={{ color: C.textSoft, font: "400 0.9rem 'Inter'" }}>Loading templates…</div>
          ) : (
            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(220px, 1fr))", gap: 14 }}>
              {templates.map((t) => (
                <button key={t.id} onClick={() => !creating && handleCreateAndPublish(t)} disabled={creating}
                  style={{ textAlign: "left", border: `1.5px solid ${C.line}`, background: C.surface, borderRadius: 16, padding: "18px 18px", cursor: creating ? "default" : "pointer", opacity: creating ? 0.6 : 1, transition: "border-color 150ms" }}
                  onMouseEnter={(e) => { if (!creating) e.currentTarget.style.borderColor = C.gold; }}
                  onMouseLeave={(e) => { e.currentTarget.style.borderColor = C.line; }}>
                  <div style={{ font: "600 1.05rem 'Fraunces', serif", color: C.forest, marginBottom: 5 }}>{t.name}</div>
                  <div style={{ font: "400 0.82rem 'Inter'", color: C.textSoft, lineHeight: 1.5, marginBottom: 10 }}>{t.description || "A set of preference questions for your group."}</div>
                  <div style={{ font: "500 0.74rem 'Inter'", color: C.sageDeep, background: C.sageWash, display: "inline-block", padding: "3px 9px", borderRadius: 99 }}>{t.question_count} questions</div>
                </button>
              ))}
            </div>
          )}

          {creating && <p style={{ font: "500 0.85rem 'Inter'", color: C.sageDeep, marginTop: 18 }}>Creating and publishing the form…</p>}
          {adminError && <p style={{ font: "500 0.84rem 'Inter'", color: "#C0392B", marginTop: 16 }}>{adminError}</p>}
        </Card>
      );
    }

    // ── MEMBER: nothing to do until admin sets it up ──
    return (
      <Card style={{ textAlign: "center", padding: "44px 28px", maxWidth: 460, margin: "0 auto" }}>
        <div style={{ font: "600 1.3rem 'Fraunces', serif", color: C.forest, marginBottom: 8 }}>No preferences form yet</div>
        <p style={{ font: "400 0.92rem 'Inter'", color: C.textSoft, lineHeight: 1.6 }}>
          The trip admin hasn't set up the preferences form yet. Once they do, you'll answer a few questions here so the AI can suggest destinations for your group.
        </p>
      </Card>
    );
  }

  if (error && !form) {
    return <Card style={{ textAlign: "center", padding: 40 }}><span style={{ color: "#C0392B", font: "500 0.92rem 'Inter'" }}>{error}</span></Card>;
  }

  // already submitted
  if (submitted) {
    return (
      <Card style={{ textAlign: "center", padding: "44px 28px", maxWidth: 460, margin: "0 auto" }}>
        <div style={{ width: 54, height: 54, borderRadius: 99, background: C.sageWash, display: "grid", placeItems: "center", margin: "0 auto 14px" }}>
          <Check size={26} color={C.sageDeep} />
        </div>
        <div style={{ font: "600 1.3rem 'Fraunces', serif", color: C.forest, marginBottom: 8 }}>Your answers are in</div>
        <p style={{ font: "400 0.92rem 'Inter'", color: C.textSoft, lineHeight: 1.6, marginBottom: 18 }}>
          Thanks for sharing your preferences. The AI will use everyone's answers to suggest destinations once the admin generates recommendations.
        </p>
        <button onClick={() => setSubmitted(false)} style={{ border: `1.5px solid ${C.line}`, background: "transparent", color: C.sageDeep, font: "600 0.85rem 'Inter'", padding: "10px 20px", borderRadius: 99, cursor: "pointer" }}>
          Edit my answers
        </button>
      </Card>
    );
  }

  // ── the fillable form ──
  return (
    <Card>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 6, flexWrap: "wrap", gap: 8 }}>
        <div style={{ font: "600 1.2rem 'Fraunces', serif", color: C.forest }}>{form.title || "Trip preferences"}</div>
        {form.deadline && (
          <span style={{ font: "500 0.74rem 'Inter'", color: C.goldDeep, background: C.goldWash, padding: "4px 11px", borderRadius: 99, display: "inline-flex", alignItems: "center", gap: 5 }}>
            <Clock size={13} /> Due {new Date(form.deadline).toLocaleDateString(undefined, { month: "short", day: "numeric" })}
          </span>
        )}
      </div>
      <p style={{ font: "400 0.9rem 'Inter'", color: C.textSoft, margin: "0 0 22px" }}>
        {form.description || "Your answers feed the AI recommendations for the whole group."}
      </p>

      <div style={{ display: "flex", flexDirection: "column", gap: 22 }}>
        {form.questions.map((q, idx) => (
          <div key={q.id}>
            <label style={{ font: "600 0.95rem 'Inter'", color: C.ink, display: "block", marginBottom: 10 }}>
              <span style={{ color: C.gold, marginRight: 8 }}>{String(idx + 1).padStart(2, "0")}</span>
              {q.question_text}
              {q.is_required && <span style={{ color: C.goldDeep, marginLeft: 4 }}>*</span>}
            </label>

            {/* TEXT */}
            {q.question_type === "text" && (
              <textarea
                value={answers[q.id]?.text || ""}
                onChange={(e) => setText(q.id, e.target.value)}
                placeholder={q.placeholder || "Type your answer…"}
                rows={3}
                style={{ width: "100%", boxSizing: "border-box", border: `1.5px solid ${C.line}`, borderRadius: 12, padding: "12px 14px", font: "400 0.92rem 'Inter'", color: C.ink, background: C.surface, resize: "vertical" }}
              />
            )}

            {/* SINGLE CHOICE */}
            {q.question_type === "single_choice" && (
              <div style={{ display: "flex", flexWrap: "wrap", gap: 9 }}>
                {(q.options || []).map((opt) => {
                  const active = (answers[q.id]?.options || [])[0] === opt;
                  return (
                    <button key={opt} onClick={() => setSingle(q.id, opt)} style={{
                      border: `1.5px solid ${active ? C.forest : C.line}`, background: active ? C.forest : C.surface,
                      color: active ? "#fff" : C.ink, font: "500 0.88rem 'Inter'", padding: "9px 16px",
                      borderRadius: 99, cursor: "pointer",
                    }}>{opt}</button>
                  );
                })}
              </div>
            )}

            {/* MULTIPLE CHOICE */}
            {q.question_type === "multiple_choice" && (
              <div style={{ display: "flex", flexWrap: "wrap", gap: 9 }}>
                {(q.options || []).map((opt) => {
                  const active = (answers[q.id]?.options || []).includes(opt);
                  return (
                    <button key={opt} onClick={() => toggleMulti(q.id, opt)} style={{
                      border: `1.5px solid ${active ? C.sageDeep : C.line}`, background: active ? C.sageWash : C.surface,
                      color: active ? C.sageDeep : C.ink, font: "500 0.88rem 'Inter'", padding: "9px 16px",
                      borderRadius: 99, cursor: "pointer", display: "inline-flex", alignItems: "center", gap: 6,
                    }}>{active && <Check size={14} />}{opt}</button>
                  );
                })}
              </div>
            )}

            {/* SCALE / RANGE */}
            {(q.question_type === "scale" || q.question_type === "range") && (() => {
              const [min, max] = scaleBounds(q.options);
              const val = answers[q.id]?.text ?? "";
              return (
                <div>
                  <input
                    type="range" min={min} max={max} step={1}
                    value={val === "" ? Math.round((min + max) / 2) : val}
                    onChange={(e) => setText(q.id, e.target.value)}
                    style={{ width: "100%", accentColor: C.gold }}
                  />
                  <div style={{ display: "flex", justifyContent: "space-between", font: "400 0.78rem 'Inter'", color: C.textSoft, marginTop: 4 }}>
                    <span>{min}</span>
                    <span style={{ font: "700 0.9rem 'Inter'", color: C.forest }}>{val === "" ? "—" : val}</span>
                    <span>{max}</span>
                  </div>
                </div>
              );
            })()}
          </div>
        ))}
      </div>

      {error && <p style={{ font: "500 0.84rem 'Inter'", color: "#C0392B", margin: "18px 0 0" }}>{error}</p>}

      <button onClick={handleSubmit} disabled={submitting} style={{
        marginTop: 24, border: "none", background: C.forest, color: "#fff", font: "700 0.9rem 'Inter'",
        padding: "13px 26px", borderRadius: 99, cursor: submitting ? "default" : "pointer",
        opacity: submitting ? 0.7 : 1, display: "inline-flex", alignItems: "center", gap: 8,
      }}>
        <Send size={16} /> {submitting ? "Submitting…" : "Submit my answers"}
      </button>
    </Card>
  );
}