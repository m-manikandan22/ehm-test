# Paper Experiment Summary (Stage 26)

**Seeds:** 20    **Ticks:** 80    **Faults/run:** 3    **Policies:** 4    **Ablation labels:** 6

**Runs attempted:** 80    **Valid:** 80    **Invalid:** 0    **Invalid rate:** 0.00%

**Runtime:** 35.9s (~ 0.45s / run)

## Layout

* raw/         -- per-(policy, seed) JSON
* aggregated/  -- per-policy summary CSV + JSON
* statistics/  -- paired comparison JSON + Markdown
* tables/      -- TABLE_I..IV Markdown + JSON
* figures/     -- PNG figures (or stub if matplotlib missing)
* logs/        -- per-run summary log
* manifest.json -- environment, dependencies, provenance
* summary.md    -- this file

## Manifest

* git_sha: `UNKNOWN`
* python: `3.14.3`
* platform: `Windows-11-10.0.26200-SP0`
* dependencies: `{"numpy": "2.4.2", "scipy": "1.18.0", "networkx": "3.6.1", "pandas": "2.3.3", "torch": "2.11.0+cpu", "matplotlib": "3.10.8"}`

## Honest framing

* Simulation-only (no field validation).
* Synthetic demand / weather / fault scenarios (deterministic).
* Round-trip efficiency and voltage are DC-PF proxies.
* Full results in tables/TABLE_III_baseline.md and TABLE_IV_ablation.md.
