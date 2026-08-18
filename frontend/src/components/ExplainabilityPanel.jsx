/**
 * ExplainabilityPanel.jsx — XAI panel for the advanced RL agent.
 * Shows why, alternatives, confidence, and expected benefit.
 */

import { useEffect, useState } from 'react'
import { explainDecision, getLastExplanation } from '../services/api'

export default function ExplainabilityPanel() {
  const [report, setReport] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  const fetchReport = () => {
    setLoading(true)
    setError(null)
    explainDecision(true)
      .then(r => { setReport(r); setLoading(false) })
      .catch(e => { setError(String(e)); setLoading(false) })
  }

  useEffect(() => { fetchReport() }, [])

  return (
    <div className="xai-panel">
      <div className="xai-header">
        <h3>Explainable AI</h3>
        <button onClick={fetchReport} disabled={loading}>
          {loading ? 'Running…' : 'Re-explain'}
        </button>
      </div>
      {error && <div className="xai-error">{error}</div>}
      {report && report.xai && (
        <div className="xai-body">
          <div className="xai-row">
            <span>Chosen action ID</span><b>{report.action_id}</b>
          </div>
          <div className="xai-row">
            <span>Confidence</span>
            <b>{(report.xai.confidence * 100).toFixed(2)}%</b>
          </div>
          <div className="xai-row">
            <span>Expected benefit</span>
            <b>{report.xai.expected_benefit.toFixed(3)}</b>
          </div>
          <div className="xai-section">
            <h4>Why (top features)</h4>
            <ul>
              {report.xai.why.map((w, i) => (
                <li key={i}>
                  <code>{w.feature}</code> = {w.value.toFixed(3)}
                  <span className="muted"> · importance {w.importance.toFixed(3)}</span>
                </li>
              ))}
            </ul>
          </div>
          <div className="xai-section">
            <h4>Alternatives</h4>
            <ul>
              {report.xai.alternatives.map((a, i) => (
                <li key={i}>
                  {a.action_name} · Q={a.q_value.toFixed(3)}
                </li>
              ))}
            </ul>
          </div>
          <div className="xai-section">
            <h4>Inputs that fired</h4>
            <div>{report.xai.inputs.join(', ')}</div>
          </div>
        </div>
      )}
    </div>
  )
}