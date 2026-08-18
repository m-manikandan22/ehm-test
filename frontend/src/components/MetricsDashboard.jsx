/**
 * MetricsDashboard.jsx — IEEE 1366 + grid KPI dashboard.
 */

import { useEffect, useState } from 'react'
import {
  getFullMetrics,
  getImprovementHistory,
  runImprovement,
} from '../services/api'

export default function MetricsDashboard() {
  const [metrics, setMetrics] = useState(null)
  const [history, setHistory] = useState(null)
  const [running, setRunning] = useState(false)
  const [error, setError] = useState(null)

  const refresh = () => {
    getFullMetrics().then(setMetrics).catch(e => setError(String(e)))
    getImprovementHistory().then(setHistory).catch(() => {})
  }

  useEffect(() => { refresh() }, [])

  const handleRunImprovement = async () => {
    setRunning(true)
    setError(null)
    try {
      await runImprovement(20)
      refresh()
    } catch (e) {
      setError(String(e))
    } finally {
      setRunning(false)
    }
  }

  return (
    <div className="metrics-dashboard">
      <div className="metrics-header">
        <h3>Industry-Grade Metrics</h3>
        <button onClick={refresh}>Refresh</button>
        <button onClick={handleRunImprovement} disabled={running}>
          {running ? 'Running…' : 'Run Improvement'}
        </button>
      </div>
      {error && <div className="metrics-error">{error}</div>}
      {metrics && (
        <div className="metrics-grid">
          <Card label="Voltage stability" value={(metrics.voltage_stability * 100).toFixed(1) + '%'} />
          <Card label="Frequency stability" value={(metrics.frequency_stability * 100).toFixed(1) + '%'} />
          <Card label="Renewable penetration" value={metrics.renewable_penetration_pct.toFixed(1) + '%'} />
          <Card label="Battery utilisation" value={metrics.battery_utilisation_pct.toFixed(1) + '%'} />
          <Card label="Reliability index" value={(metrics.system_reliability_index * 100).toFixed(1) + '%'} />
          <Card label="Nodes" value={metrics.n_nodes} />
          <Card label="Failed" value={metrics.n_failed} />
        </div>
      )}
      {history && history.history && history.history.length > 0 && (
        <div className="improvement-history">
          <h4>Self-improvement history ({history.count})</h4>
          <table>
            <thead>
              <tr>
                <th>#</th>
                <th>Proposed</th>
                <th>Applied</th>
                <th>Δ critical avail.</th>
              </tr>
            </thead>
            <tbody>
              {history.history.map((h, i) => (
                <tr key={i}>
                  <td>{i + 1}</td>
                  <td>{h.actions_proposed}</td>
                  <td>{h.actions_applied}</td>
                  <td>
                    {h.delta && h.delta.critical_load_availability !== undefined
                      ? h.delta.critical_load_availability.toFixed(4)
                      : '—'}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}

function Card({ label, value }) {
  return (
    <div className="metrics-card">
      <div className="metrics-card-label">{label}</div>
      <div className="metrics-card-value">{value}</div>
    </div>
  )
}