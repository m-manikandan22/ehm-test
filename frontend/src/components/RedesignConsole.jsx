/**
 * RedesignConsole.jsx — UI for the self-improvement loop.
 * Run sim → see metrics → apply redesign → compare before/after.
 */

import { useState } from 'react'
import { runImprovement } from '../services/api'

export default function RedesignConsole() {
  const [steps, setSteps] = useState(50)
  const [result, setResult] = useState(null)
  const [running, setRunning] = useState(false)
  const [error, setError] = useState(null)

  const handleRun = async () => {
    setRunning(true)
    setError(null)
    try {
      const r = await runImprovement(steps)
      setResult(r)
    } catch (e) {
      setError(String(e))
    } finally {
      setRunning(false)
    }
  }

  return (
    <div className="redesign-console">
      <h3>Self-Improvement Loop</h3>
      <div className="redesign-row">
        <label>Steps per evaluation: </label>
        <input
          type="number"
          min="1"
          max="500"
          value={steps}
          onChange={(e) => setSteps(Number(e.target.value))}
        />
        <button onClick={handleRun} disabled={running}>
          {running ? 'Running…' : 'Run improvement'}
        </button>
      </div>
      {error && <div className="redesign-error">{error}</div>}
      {result && (
        <div className="redesign-result">
          <div className="redesign-summary">
            <div>Actions proposed: <b>{result.report.actions_proposed}</b></div>
            <div>Actions applied: <b>{result.report.actions_applied}</b></div>
          </div>
          <div className="redesign-deltas">
            <h4>Before → After deltas</h4>
            <ul>
              {Object.entries(result.report.delta || {}).map(([k, v]) => (
                <li key={k}>
                  <code>{k}</code>: {Number(v).toFixed(4)}
                </li>
              ))}
            </ul>
          </div>
          {result.report.notes && result.report.notes.length > 0 && (
            <div className="redesign-notes">
              <h4>Notes</h4>
              <ul>{result.report.notes.map((n, i) => <li key={i}>{n}</li>)}</ul>
            </div>
          )}
        </div>
      )}
    </div>
  )
}