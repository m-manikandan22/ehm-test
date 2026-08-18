/**
 * DigitalTwinPanel.jsx — right-side panel showing a selected asset's
 * digital twin (health, age, temperature, predicted failure, maintenance log).
 *
 * Why: a digital twin is the publication spine of the upgrade; this panel
 * surfaces it in the dashboard without touching the existing GridGraph.
 */

import { useEffect, useState } from 'react'
import { getTwin, predictTwin, getTwinsSummary } from '../services/api'

export default function DigitalTwinPanel({ assetId, onClose }) {
  const [twin, setTwin] = useState(null)
  const [prediction, setPrediction] = useState(null)
  const [summary, setSummary] = useState(null)
  const [horizon, setHorizon] = useState(24)
  const [error, setError] = useState(null)

  useEffect(() => {
    if (!assetId) return
    let mounted = true
    setError(null)
    setTwin(null)
    setPrediction(null)
    getTwin(assetId)
      .then(d => { if (mounted) setTwin(d) })
      .catch(e => { if (mounted) setError(String(e)) })
    predictTwin(assetId, horizon)
      .then(d => { if (mounted) setPrediction(d) })
      .catch(() => {})
    return () => { mounted = false }
  }, [assetId, horizon])

  useEffect(() => {
    getTwinsSummary().then(setSummary).catch(() => {})
  }, [assetId])

  if (!assetId) {
    return (
      <div className="twin-panel empty">
        <h3>Digital Twin</h3>
        <p>Click any node on the grid to inspect its twin.</p>
        {summary && (
          <div className="twin-summary">
            <div>Assets: <b>{summary.count}</b></div>
            <div>Mean health: <b>{(summary.mean_health * 100).toFixed(1)}%</b></div>
            <div>High-risk: <b>{summary.high_risk_count}</b></div>
            <div>Oldest age: <b>{summary.oldest_age_hours.toFixed(1)} h</b></div>
          </div>
        )}
      </div>
    )
  }

  return (
    <div className="twin-panel">
      <div className="twin-header">
        <h3>Digital Twin · {assetId}</h3>
        {onClose && <button onClick={onClose}>×</button>}
      </div>
      {error && <div className="twin-error">{error}</div>}
      {twin && (
        <div className="twin-body">
          <div className="twin-row">
            <span>Asset type</span><b>{twin.asset_type}</b>
          </div>
          <div className="twin-row">
            <span>Health</span>
            <b>{(twin.health * 100).toFixed(2)}%</b>
          </div>
          <div className="twin-row">
            <span>Age</span>
            <b>{twin.age_hours.toFixed(2)} h</b>
          </div>
          <div className="twin-row">
            <span>Loading</span>
            <b>{twin.loading.toFixed(3)} pu</b>
          </div>
          <div className="twin-row">
            <span>Hot-spot T</span>
            <b>{twin.temperature.toFixed(2)} K</b>
          </div>
          <div className="twin-row">
            <span>Failure probability</span>
            <b
              style={{
                color: twin.failure_probability > 0.5 ? '#e63946'
                      : twin.failure_probability > 0.2 ? '#f4a261'
                      : '#2a9d8f',
              }}
            >
              {(twin.failure_probability * 100).toFixed(2)}%
            </b>
          </div>
          <div className="twin-row">
            <span>Sensor samples</span>
            <b>{twin.sensor_history_size}</b>
          </div>
          <div className="twin-row">
            <span>Maintenance events</span>
            <b>{twin.maintenance_history_size}</b>
          </div>
        </div>
      )}
      <div className="twin-predict">
        <label>Prediction horizon: </label>
        <input
          type="number"
          min="1"
          max="168"
          value={horizon}
          onChange={(e) => setHorizon(Number(e.target.value))}
        />
        {prediction && (
          <div className="twin-prediction">
            Projected health: <b>{(prediction.projected_health * 100).toFixed(2)}%</b>
            <br/>
            Projected failure prob: <b>{(prediction.projected_failure_probability * 100).toFixed(2)}%</b>
            <br/>
            Will fail: <b>{String(prediction.will_fail)}</b>
          </div>
        )}
      </div>
    </div>
  )
}