/**
 * CityCanvas.jsx — base layer that paints the procedural city
 * (roads, zone polygons, building markers) BEHIND the GridGraph.
 *
 * Additive: doesn't replace the existing GridGraph; only adds context.
 *
 * The data comes from `GET /city/layout` which is wired through
 * `backend/city/layout.py`.  When the grid wasn't produced by
 * ``CityGenerator`` (legacy CAD-built grid), the endpoint returns
 * ``{has_layout: false}`` and we fall back to a procedural grid backdrop.
 */

import { useEffect, useState } from 'react'
import { getCityLayout, getCityReport } from '../services/api'

const ZONE_COLORS = {
  residential: '#a8dadc',
  industrial: '#e9c46a',
  commercial: '#f4a261',
  critical: '#e63946',
  unknown: '#cccccc',
}

const BUILDING_PRIORITY_COLORS = {
  0: '#222',      // nuclear / gov
  1: '#e63946',   // hospital
  2: '#f4a261',   // critical
  3: '#457b9d',   // normal load
  4: '#a8dadc',   // residential
}

export default function CityCanvas({ width = 900, height = 600 }) {
  const [layout, setLayout] = useState(null)
  const [report, setReport] = useState(null)
  const [view, setView] = useState({ minX: 0, minY: 0, maxX: 0, maxY: 0 })

  useEffect(() => {
    getCityLayout()
      .then((d) => {
        setLayout(d)
        if (d?.has_layout && d.bounds) {
          setView({
            minX: d.bounds.min_x,
            minY: d.bounds.min_y,
            maxX: d.bounds.max_x,
            maxY: d.bounds.max_y,
          })
        }
      })
      .catch(() => {})
    getCityReport().then(setReport).catch(() => {})
  }, [])

  if (!layout || !layout.has_layout) {
    return (
      <svg width={width} height={height} className="city-canvas">
        <LegacyBackdrop width={width} height={height} report={report} />
      </svg>
    )
  }

  const dx = view.maxX - view.minX || 1
  const dy = view.maxY - view.minY || 1
  const pad = 20
  const sx = (x) => pad + ((x - view.minX) / dx) * (width - 2 * pad)
  const sy = (y) => pad + ((y - view.minY) / dy) * (height - 2 * pad)

  return (
    <svg width={width} height={height} className="city-canvas">
      {/* 1) Zone polygons (filled blocks) */}
      {(layout.zones || []).map((z, i) => {
        const pts = z.polygon.map(([x, y]) => `${sx(x)},${sy(y)}`).join(' ')
        return (
          <polygon
            key={`zone-${i}`}
            points={pts}
            fill={ZONE_COLORS[z.zone] || ZONE_COLORS.unknown}
            fillOpacity={0.18}
            stroke={ZONE_COLORS[z.zone] || ZONE_COLORS.unknown}
            strokeOpacity={0.4}
            strokeWidth={1}
          />
        )
      })}

      {/* 2) Road network (street + avenue segments) */}
      {(layout.roads || []).map((r, i) => {
        const x1 = sx(r.u[0])
        const y1 = sy(r.u[1])
        const x2 = sx(r.v[0])
        const y2 = sy(r.v[1])
        const w = r.kind === 'avenue' ? 3.5 : 1.6
        const stroke = r.kind === 'avenue' ? '#8d99ae' : '#bcc4d1'
        return (
          <line
            key={`road-${i}`}
            x1={x1}
            y1={y1}
            x2={x2}
            y2={y2}
            stroke={stroke}
            strokeWidth={w}
            strokeLinecap="round"
          />
        )
      })}

      {/* 3) Building markers (small dots coloured by priority) */}
      {(layout.buildings || []).map((b) => (
        <circle
          key={`bld-${b.id}`}
          cx={sx(b.x)}
          cy={sy(b.y)}
          r={b.priority <= 1 ? 4 : 2.5}
          fill={BUILDING_PRIORITY_COLORS[b.priority] || '#999'}
          fillOpacity={0.85}
          stroke="#fff"
          strokeWidth={0.5}
        >
          <title>{`${b.label} (${b.node_type})`}</title>
        </circle>
      ))}
    </svg>
  )
}

function LegacyBackdrop({ width, height, report }) {
  // Fallback for grids without a city report — paint a grid backdrop
  // proportional to the population.
  if (!report) {
    return (
      <text x={20} y={30} fill="#888">
        No city profile loaded
      </text>
    )
  }
  const cols = Math.ceil(Math.sqrt(report.road_blocks || 1))
  const cellW = width / Math.max(1, cols)
  const cellH = height / Math.max(1, cols)
  const cells = []
  for (let i = 0; i < cols; i++) {
    for (let j = 0; j < cols; j++) {
      const zoneKeys = Object.keys(report.zones || {})
      const z = zoneKeys[(i * cols + j) % Math.max(1, zoneKeys.length)]
      cells.push(
        <rect
          key={`${i}-${j}`}
          x={i * cellW}
          y={j * cellH}
          width={cellW}
          height={cellH}
          fill={ZONE_COLORS[z] || '#cccccc'}
          fillOpacity={0.25}
          stroke="#888"
          strokeOpacity={0.2}
        />
      )
    }
  }
  return <g>{cells}</g>
}
