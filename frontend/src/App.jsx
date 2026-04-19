import React, { useState, useEffect } from "react";

const API = "/api";
const SEV = { low: "#0A8A0A", medium: "#CC6600", high: "#CC0000", critical: "#8B0000" };
const SCORES = { do_nothing: "✅ Do Nothing", monitor: "👀 Monitor", mitigate: "⚠️ Mitigate", escalate: "🚨 Escalate" };
const RISK_COLORS = { low: "#0A8A0A", medium: "#CC6600", high: "#CC0000", critical: "#8B0000" };

const DEMO = {
  sourceType: "logistics", sourceName: "Port of Long Beach", region: "US-West",
  affectedLane: "Shanghai -> Phoenix", supplier: "Supplier A",
  event: "Port congestion causing 3-day delay risk",
  affectedProducts: ["SKU-101", "SKU-204"], priorityCustomers: ["Customer-X"],
};

export default function App() {
  const [incidents, setIncidents] = useState([]);
  const [card, setCard] = useState(null);
  const [loading, setLoading] = useState(false);
  const [form, setForm] = useState(DEMO);
  const [reviewer, setReviewer] = useState("");

  const load = async () => {
    try { setIncidents(await (await fetch(`${API}/incidents`)).json()); } catch {}
  };
  useEffect(() => { load(); }, []);

  const analyze = async () => {
    setLoading(true);
    try {
      const r = await fetch(`${API}/incidents/analyze`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify(form),
      });
      if (!r.ok) { const e = await r.json(); alert(e.detail || "Failed"); setLoading(false); return; }
      setCard(await r.json());
      load();
    } catch (e) { alert("Failed: " + e.message); }
    setLoading(false);
  };

  const handleApproval = async (action) => {
    if (!reviewer.trim()) { alert("Enter reviewer name"); return; }
    try {
      const r = await fetch(`${API}/incidents/${card.incidentId}/approve`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ action, reviewer: reviewer.trim(), comment: action === "reject" ? "Rejected via UI" : null }),
      });
      const result = await r.json();
      setCard({ ...card, status: result.status });
      load();
    } catch (e) { alert("Approval failed: " + e.message); }
  };

  const F = (k) => (
    <label key={k} style={{ fontSize: 13 }}>
      {k}: <input value={form[k] || ""} onChange={(e) => setForm({ ...form, [k]: e.target.value })}
        style={{ width: "100%", padding: 6, borderRadius: 4, border: "1px solid #ccc" }} />
    </label>
  );

  return (
    <div style={{ fontFamily: "Calibri, Arial, sans-serif", maxWidth: 1100, margin: "0 auto", padding: 24 }}>
      <header style={{ background: "#232F3E", color: "#fff", padding: "16px 24px", borderRadius: 8, marginBottom: 24 }}>
        <h1 style={{ margin: 0, fontSize: 22 }}>
          <span style={{ color: "#FF9900" }}>⚡</span> Supply Chain Disruption Response Agent
        </h1>
        <p style={{ margin: "4px 0 0", opacity: 0.8, fontSize: 14 }}>Control Tower Copilot — Amazon Bedrock + EKS</p>
      </header>

      {/* Incident Form */}
      <section style={{ background: "#f9f9f9", padding: 20, borderRadius: 8, marginBottom: 24, border: "1px solid #ddd" }}>
        <h2 style={{ margin: "0 0 12px", fontSize: 16, borderBottom: "2px solid #FF9900", paddingBottom: 6 }}>Submit Disruption Event</h2>
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
          {["sourceName", "region", "supplier", "affectedLane"].map(F)}
        </div>
        <label style={{ display: "block", marginTop: 12, fontSize: 13 }}>
          Event: <textarea value={form.event} onChange={(e) => setForm({ ...form, event: e.target.value })}
            style={{ width: "100%", padding: 6, borderRadius: 4, border: "1px solid #ccc", minHeight: 60 }} />
        </label>
        <button onClick={analyze} disabled={loading}
          style={{ marginTop: 12, background: "#FF9900", color: "#232F3E", border: "none", padding: "10px 28px",
            borderRadius: 6, fontWeight: "bold", fontSize: 14, cursor: "pointer" }}>
          {loading ? "Analyzing..." : "Analyze with Claude"}
        </button>
      </section>

      {/* Response Card */}
      {card && (
        <section style={{ background: "#fff", padding: 20, borderRadius: 8, marginBottom: 24,
          border: `2px solid ${SEV[card.severity] || "#ddd"}` }}>
          <h2 style={{ margin: "0 0 8px", fontSize: 16 }}>
            Response Card — {card.incidentId}
            <span style={{ float: "right", fontSize: 13, color: SEV[card.severity] }}>
              {card.severity?.toUpperCase()} | {(card.confidence * 100).toFixed(0)}% confidence
            </span>
          </h2>
          <p style={{ fontSize: 18, fontWeight: "bold" }}>{SCORES[card.responseScore]}</p>

          {/* Risk Prediction */}
          {card.riskPrediction && (
            <div style={{ background: "#f0f4f8", padding: 12, borderRadius: 6, marginBottom: 12, border: "1px solid #d0d8e0" }}>
              <span style={{ fontSize: 13, fontWeight: "bold" }}>Predictive Risk Score: </span>
              <span style={{ color: RISK_COLORS[card.riskPrediction.riskTier], fontWeight: "bold", fontSize: 15 }}>
                {(card.riskPrediction.riskProbability * 100).toFixed(0)}% ({card.riskPrediction.riskTier.toUpperCase()})
              </span>
              <span style={{ fontSize: 11, color: "#888", marginLeft: 8 }}>model: {card.riskPrediction.modelVersion}</span>
              {card.riskPrediction.factors && (
                <div style={{ marginTop: 6, fontSize: 12, color: "#555" }}>
                  {card.riskPrediction.factors.map((f, i) => (
                    <span key={i} style={{ marginRight: 12 }}>{f.factor}: +{(f.contribution * 100).toFixed(0)}%</span>
                  ))}
                </div>
              )}
            </div>
          )}

          <p><b>Summary:</b> {card.summary}</p>
          <p><b>Cause:</b> {card.likelyCause}</p>
          <p><b>Impacted:</b> {card.impactedAreas?.join(", ")}</p>

          <h3 style={{ fontSize: 14, marginTop: 16, borderBottom: "1px solid #FF9900", paddingBottom: 4 }}>Recommended Actions</h3>
          <ol>{card.recommendedActions?.map((a, i) => (
            <li key={i} style={{ marginBottom: 6 }}><b>{a.action}</b> — {a.reason}</li>
          ))}</ol>

          {card.escalate && <p style={{ color: "#CC0000", fontWeight: "bold" }}>🚨 Escalation: {card.escalationReason}</p>}

          {/* Guardrail Warnings */}
          {card.guardrailWarnings?.length > 0 && (
            <div style={{ background: "#FFF8E1", padding: 10, borderRadius: 6, marginTop: 12, border: "1px solid #FFD54F" }}>
              <span style={{ fontSize: 13, fontWeight: "bold", color: "#CC6600" }}>⚠ Guardrail Warnings:</span>
              <ul style={{ margin: "4px 0 0", paddingLeft: 20, fontSize: 12 }}>
                {card.guardrailWarnings.map((w, i) => <li key={i}>{w}</li>)}
              </ul>
            </div>
          )}

          {/* Approval Gate */}
          {card.status === "pending_approval" && (
            <div style={{ background: "#FFF3E0", padding: 16, borderRadius: 6, marginTop: 16, border: "2px solid #FF9900" }}>
              <h3 style={{ margin: "0 0 8px", fontSize: 14, color: "#232F3E" }}>🔒 Approval Required</h3>
              <p style={{ fontSize: 13, margin: "0 0 10px" }}>
                This high-severity incident requires human approval before escalation is triggered.
              </p>
              <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
                <input placeholder="Reviewer name" value={reviewer}
                  onChange={(e) => setReviewer(e.target.value)}
                  style={{ padding: 6, borderRadius: 4, border: "1px solid #ccc", flex: 1 }} />
                <button onClick={() => handleApproval("approve")}
                  style={{ background: "#0A8A0A", color: "#fff", border: "none", padding: "8px 20px",
                    borderRadius: 6, fontWeight: "bold", cursor: "pointer" }}>
                  ✅ Approve
                </button>
                <button onClick={() => handleApproval("reject")}
                  style={{ background: "#CC0000", color: "#fff", border: "none", padding: "8px 20px",
                    borderRadius: 6, fontWeight: "bold", cursor: "pointer" }}>
                  ❌ Reject
                </button>
              </div>
            </div>
          )}
          {card.status === "approved" && <p style={{ color: "#0A8A0A", fontWeight: "bold" }}>✅ Approved and escalated</p>}
          {card.status === "rejected" && <p style={{ color: "#CC0000", fontWeight: "bold" }}>❌ Rejected by reviewer</p>}
        </section>
      )}

      {/* Incident History */}
      <section>
        <h2 style={{ fontSize: 16, borderBottom: "2px solid #FF9900", paddingBottom: 6 }}>Incident History</h2>
        {incidents.length === 0 ? <p style={{ color: "#888" }}>No incidents yet.</p> : (
          <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
            <thead><tr style={{ background: "#232F3E", color: "#fff" }}>
              {["ID", "Source", "Region", "Severity", "Risk", "Status", "Created"].map(h =>
                <th key={h} style={{ padding: "8px 10px", textAlign: "left" }}>{h}</th>)}
            </tr></thead>
            <tbody>{incidents.map(inc => {
              const rc = inc.responseCard || {};
              const rp = rc.riskPrediction || {};
              return (
                <tr key={inc.incidentId} onClick={() => setCard(rc)}
                  style={{ cursor: "pointer", borderBottom: "1px solid #eee" }}>
                  <td style={{ padding: 8 }}>{inc.incidentId}</td>
                  <td>{inc.input?.sourceName}</td>
                  <td>{inc.input?.region}</td>
                  <td style={{ color: SEV[rc.severity] }}>{rc.severity || "—"}</td>
                  <td style={{ color: RISK_COLORS[rp.riskTier] }}>
                    {rp.riskProbability ? `${(rp.riskProbability * 100).toFixed(0)}%` : "—"}
                  </td>
                  <td>{rc.status || "pending"}</td>
                  <td>{inc.createdAt?.slice(0, 10)}</td>
                </tr>);
            })}</tbody>
          </table>
        )}
      </section>
    </div>
  );
}
