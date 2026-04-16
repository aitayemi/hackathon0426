import React, { useState, useEffect } from "react";

const API = "/api";

const SEVERITY_COLORS = { low: "#0A8A0A", medium: "#CC6600", high: "#CC0000", critical: "#8B0000" };
const SCORE_LABELS = { do_nothing: "✅ Do Nothing", monitor: "👀 Monitor", mitigate: "⚠️ Mitigate", escalate: "🚨 Escalate" };

const DEMO_INCIDENT = {
  sourceType: "logistics",
  sourceName: "Port of Long Beach",
  region: "US-West",
  affectedLane: "Shanghai -> Phoenix",
  supplier: "Supplier A",
  event: "Port congestion causing 3-day delay risk",
  affectedProducts: ["SKU-101", "SKU-204"],
  priorityCustomers: ["Customer-X"],
};

export default function App() {
  const [incidents, setIncidents] = useState([]);
  const [selected, setSelected] = useState(null);
  const [loading, setLoading] = useState(false);
  const [formData, setFormData] = useState(DEMO_INCIDENT);

  const fetchIncidents = async () => {
    const res = await fetch(`${API}/incidents`);
    setIncidents(await res.json());
  };

  useEffect(() => { fetchIncidents(); }, []);

  const submitIncident = async () => {
    setLoading(true);
    try {
      const res = await fetch(`${API}/incidents/analyze`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(formData),
      });
      const card = await res.json();
      setSelected(card);
      fetchIncidents();
    } catch (e) { alert("Analysis failed: " + e.message); }
    setLoading(false);
  };

  return (
    <div style={{ fontFamily: "Calibri, Arial, sans-serif", maxWidth: 1100, margin: "0 auto", padding: 24 }}>
      <header style={{ background: "#232F3E", color: "#fff", padding: "16px 24px", borderRadius: 8, marginBottom: 24 }}>
        <h1 style={{ margin: 0, fontSize: 22 }}>
          <span style={{ color: "#FF9900" }}>⚡</span> Supply Chain Disruption Response Agent
        </h1>
        <p style={{ margin: "4px 0 0", opacity: 0.8, fontSize: 14 }}>Control Tower Copilot — Powered by Amazon Bedrock</p>
      </header>

      {/* Incident Form */}
      <section style={{ background: "#f9f9f9", padding: 20, borderRadius: 8, marginBottom: 24, border: "1px solid #ddd" }}>
        <h2 style={{ margin: "0 0 12px", fontSize: 16, borderBottom: "2px solid #FF9900", paddingBottom: 6 }}>Submit Disruption Event</h2>
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
          {["sourceName", "region", "supplier", "affectedLane"].map((f) => (
            <label key={f} style={{ fontSize: 13 }}>
              {f}: <input value={formData[f] || ""} onChange={(e) => setFormData({ ...formData, [f]: e.target.value })}
                style={{ width: "100%", padding: 6, borderRadius: 4, border: "1px solid #ccc" }} />
            </label>
          ))}
        </div>
        <label style={{ display: "block", marginTop: 12, fontSize: 13 }}>
          Event: <textarea value={formData.event} onChange={(e) => setFormData({ ...formData, event: e.target.value })}
            style={{ width: "100%", padding: 6, borderRadius: 4, border: "1px solid #ccc", minHeight: 60 }} />
        </label>
        <button onClick={submitIncident} disabled={loading}
          style={{ marginTop: 12, background: "#FF9900", color: "#232F3E", border: "none", padding: "10px 28px",
            borderRadius: 6, fontWeight: "bold", fontSize: 14, cursor: "pointer" }}>
          {loading ? "Analyzing..." : "Analyze with Claude"}
        </button>
      </section>

      {/* Response Card */}
      {selected && (
        <section style={{ background: "#fff", padding: 20, borderRadius: 8, marginBottom: 24,
          border: `2px solid ${SEVERITY_COLORS[selected.severity] || "#ddd"}` }}>
          <h2 style={{ margin: "0 0 8px", fontSize: 16 }}>
            Response Card — {selected.incidentId}
            <span style={{ float: "right", fontSize: 13, color: SEVERITY_COLORS[selected.severity] }}>
              {selected.severity?.toUpperCase()} | Confidence: {(selected.confidence * 100).toFixed(0)}%
            </span>
          </h2>
          <p style={{ fontSize: 18, fontWeight: "bold" }}>{SCORE_LABELS[selected.responseScore]}</p>
          <p><strong>Summary:</strong> {selected.summary}</p>
          <p><strong>Cause:</strong> {selected.likelyCause}</p>
          <p><strong>Impacted Areas:</strong> {selected.impactedAreas?.join(", ")}</p>
          <h3 style={{ fontSize: 14, marginTop: 16, borderBottom: "1px solid #FF9900", paddingBottom: 4 }}>Recommended Actions</h3>
          <ol>{selected.recommendedActions?.map((a, i) => (
            <li key={i} style={{ marginBottom: 6 }}><strong>{a.action}</strong> — {a.reason}</li>
          ))}</ol>
          {selected.escalate && (
            <p style={{ color: "#CC0000", fontWeight: "bold" }}>🚨 Escalated: {selected.escalationReason}</p>
          )}
        </section>
      )}

      {/* Incident History */}
      <section>
        <h2 style={{ fontSize: 16, borderBottom: "2px solid #FF9900", paddingBottom: 6 }}>Incident History</h2>
        {incidents.length === 0 ? <p style={{ color: "#888" }}>No incidents yet.</p> : (
          <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
            <thead><tr style={{ background: "#232F3E", color: "#fff" }}>
              {["ID", "Source", "Region", "Severity", "Status", "Created"].map((h) => (
                <th key={h} style={{ padding: "8px 10px", textAlign: "left" }}>{h}</th>
              ))}
            </tr></thead>
            <tbody>{incidents.map((inc) => {
              const card = inc.responseCard || {};
              return (
                <tr key={inc.incidentId} onClick={() => setSelected(card)} style={{ cursor: "pointer", borderBottom: "1px solid #eee" }}>
                  <td style={{ padding: 8 }}>{inc.incidentId}</td>
                  <td>{inc.input?.sourceName}</td>
                  <td>{inc.input?.region}</td>
                  <td style={{ color: SEVERITY_COLORS[card.severity] }}>{card.severity || "—"}</td>
                  <td>{card.status || "pending"}</td>
                  <td>{inc.createdAt?.slice(0, 10)}</td>
                </tr>
              );
            })}</tbody>
          </table>
        )}
      </section>
    </div>
  );
}
