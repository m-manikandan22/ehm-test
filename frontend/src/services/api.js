/**
 * api.js — Axios service layer for the Smart Grid backend API.
 * Uses Vite proxy to connect to backend (http://localhost:8000)
 */

import axios from 'axios'

// Use '/api' to route through Vite proxy (defined in vite.config.js)
const BASE_URL = '/api'

const api = axios.create({
  baseURL: BASE_URL,
  timeout: 10000,
  headers: { 'Content-Type': 'application/json' },
})

// ── Grid operations ───────────────────────────────────────────────────

/** Get current grid state without stepping the simulation. */
export const getState = () => api.get('/state').then(r => r.data)

/**
 * Advance 1 timestep: runs grid physics, LSTM forecast, DQN decision.
 * Returns { grid, ai: { predicted_load, decision, action_result, reward } }
 */
export const simulate = () => api.post('/simulate').then(r => r.data)

/** Reset grid to initial state. */
export const resetGrid = () => api.post('/reset').then(r => r.data)

// ── User Grid Construction (CAD Modes) ──────────────────────────────────

export const addNode = (type, position) => api.post('/add_node', { type, position }).then(r => r.data)
export const addEdge = (u, v) => api.post('/connect', { source: u, target: v }).then(r => r.data)
export const cutEdge = (u, v) => api.post('/cut_edge', { source: u, target: v }).then(r => r.data)
export const failNodeAPI = (node_id) => api.post('/fail_node', { node_id }).then(r => r.data)
export const restoreNodeAPI = (node_id) => api.post('/restore_node', { node_id }).then(r => r.data)
export const moveNodeAPI = (node_id, x, y) => api.put(`/nodes/${node_id}/move`, { x, y }).then(r => r.data)
export const addHouseAPI = (node_id) => api.post('/command/add_house', { node_id }).then(r => r.data)
export const deleteNodeAPI = (node_id) => api.delete(`/nodes/${node_id}`).then(r => r.data)

export const getAISuggestions = () => api.get('/ai/suggestions').then(r => r.data)
export const getSuggestParent = (x, y) => api.post('/ai/suggest_parent', { x, y }).then(r => r.data)
export const randomFaultAPI = () => api.post('/random_fault').then(r => r.data)

// ── Events ────────────────────────────────────────────────────────────

/**
 * Trigger a grid event.
 * @param {string} type - 'failure' | 'storm' | 'clear_storm' | 'demand' | 'generation' | 'restore'
 * @param {string|null} nodeId - required for 'failure' and 'restore'
 * @param {number|null} amount - optional for 'demand' and 'generation'
 */
export const triggerEvent = (type, nodeId = null, amount = null) =>
  api.post('/event', { type, node_id: nodeId, amount }).then(r => r.data)

// ── Prediction ────────────────────────────────────────────────────────

/** Get LSTM prediction for a specific node. */
export const predict = (nodeId = 'S0') =>
  api.get('/predict', { params: { node_id: nodeId } }).then(r => r.data)

// ── Manual action ─────────────────────────────────────────────────────

/** Force a specific RL action by ID (0–4). */
export const forceAction = (actionId) =>
  api.post('/action', { action_id: actionId }).then(r => r.data)

// ── Utility ───────────────────────────────────────────────────────────

/** Health check. */
export const healthCheck = () =>
  api.get('/health').then(r => r.data).catch(() => null)

// ── M2: Digital Twin / Weather / Smart Faults / Microgrid ────────────

export const getTwinsSummary = () => api.get('/twins/summary').then(r => r.data)
export const getTwin = (assetId) => api.get(`/twins/${assetId}`).then(r => r.data)
export const predictTwin = (assetId, horizonSteps = 24) =>
  api.post(`/twins/${assetId}/predict`, null, { params: { horizon_steps: horizonSteps } })
    .then(r => r.data)
export const syncTwins = () => api.post('/twins/sync').then(r => r.data)

export const getWeather = () => api.get('/weather').then(r => r.data)
export const stepWeather = () => api.post('/weather/step').then(r => r.data)
export const setWeather = (state) =>
  api.post('/weather/set', { state }).then(r => r.data)

export const getFaultCatalog = () => api.get('/fault/catalog').then(r => r.data)
export const injectSmartFault = ({ apply = false, max_events = 5, state = null } = {}) =>
  api.post('/fault/inject_smart', { apply, max_events, state }).then(r => r.data)

export const formMicrogrid = (faultedNodes = []) =>
  api.post('/microgrid/form', { faulted_nodes: faultedNodes }).then(r => r.data)
export const listMicrogrids = () => api.get('/microgrid/list').then(r => r.data)
export const reconnectMicrogrid = () => api.post('/microgrid/reconnect').then(r => r.data)

// ── M3: Advanced RL + XAI ────────────────────────────────────────────

export const explainDecision = (includeXai = true) =>
  api.post('/explain/decision', { include_xai: includeXai }).then(r => r.data)
export const getLastExplanation = () => api.get('/explain/last').then(r => r.data)

// ── M4: IEEE 1366 Metrics + Self-Improvement ─────────────────────────

export const getFullMetrics = () => api.get('/metrics/full').then(r => r.data)
export const computeIEEE1366 = (payload) =>
  api.post('/metrics/ieee1366', payload).then(r => r.data)
export const computeForecastMetrics = (actual, predicted) =>
  api.post('/metrics/forecast', { actual, predicted }).then(r => r.data)
export const runImprovement = (steps = 50) =>
  api.post('/improvement/run', { steps }).then(r => r.data)
export const getImprovementHistory = () => api.get('/improvement/history').then(r => r.data)

// ── M1: Procedural City + AI Planner ─────────────────────────────────

export const getCityProfile = () => api.get('/city/profile').then(r => r.data)
export const setCityProfile = (profile) =>
  api.post('/city/profile', profile).then(r => r.data)
export const generateCity = (profile = null) =>
  api.post('/city/generate', profile || {}).then(r => r.data)
export const getCityReport = () => api.get('/city/report').then(r => r.data)
export const getCityLayout = () => api.get('/city/layout').then(r => r.data)
export const runPlanner = () => api.post('/planner/run').then(r => r.data)
