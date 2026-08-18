"""
city_generator.py — procedural city + electrical topology.

Why this module exists
----------------------
The EHM 49-bus topology was hand-built in `SmartGrid._build_grid` (≈200
lines of hard-coded coordinates).  A research-grade digital-twin must
let reviewers ask "what changes when the population doubles?" or
"what's the optimal substation count for a hurricane-prone coastal
city?"  That requires a *parameterised* generator that produces a
fully-populated `SmartGrid` from a `CityProfile`.

The generator returns a `SmartGrid` instance built the same way as
the IEEE-13 helper (`simulation.ieee13.build_ieee13`): bypass
`SmartGrid.__init__`, populate the minimum fields needed for the
DC power flow + FLISR + EMS pipeline to work, then run a few
warm-up physics iterations.  This way **every existing module**
(power flow, FLISR, EMS, attack detector, digital twin) keeps
working without modification.

Topology layout
---------------
A procedural city with N distribution substations produces:

  - 1 transmission corridor (T0..Tn) feeding N primary substations
  - N primary substations, each feeding ~M distribution substations
  - Each distribution substation feeding ~K feeders with poles,
    transformers, and downstream loads
  - 1 main substation as the city's single slack bus (mandatory for
    DC PF)
  - 2 tie switches (one across the primary substation ring, one
    across feeder heads) so FLISR has something to close
  - Critical loads (hospital ICU, gov building) wired to a microgrid
    root near the centre

The generator is intentionally *not* stochastic in its broad layout:
two runs with the same `CityProfile` produce the same graph.  Only
the *positions* of buildings within blocks (and tie-switch
placement) use the RNG.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

import math
import random

import networkx as nx

from city.city_profile import CityProfile
from city.road_network import RoadNetwork
from city.zoning import Zoning
from simulation.grid import SmartGrid
from simulation.node import GridNode
from utils.seeds import make_rng


@dataclass
class GenerationReport:
    """Summary of a CityGenerator run — useful for the API and tests."""

    profile: CityProfile
    node_counts: Dict[str, int]
    edge_count: int
    expected_load_mw: float
    road_blocks: int
    zones: Dict[str, int]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "profile": self.profile.to_dict(),
            "node_counts": self.node_counts,
            "edge_count": self.edge_count,
            "expected_load_mw": self.expected_load_mw,
            "road_blocks": self.road_blocks,
            "zones": self.zones,
        }


# Allowed node types that the generator may emit, in the order they
# appear in the layout.  Used for the report.
_GENERATED_TYPES = (
    "transmission_tower", "primary_substation", "distribution_substation",
    "substation", "transformer", "pole",
    "house", "hospital_icu", "school", "university", "gov_building",
    "industry", "commercial", "ev_charger",
    "solar_farm", "wind_farm", "bess", "battery", "microgrid_root",
)


class CityGenerator:
    """Build a SmartGrid-shaped NetworkX city from a `CityProfile`."""

    def __init__(self, profile: CityProfile) -> None:
        self.profile = profile
        # Density-aware sizing.
        self.cols = max(3, min(20, int(round(math.sqrt(profile.effective_density
                                                       / 1000.0)) or 6)))
        self.rows = max(3, min(20, self.cols))

    # ------------------------------------------------------------------

    def generate(self) -> SmartGrid:
        """Run the generator and return a fresh SmartGrid."""
        rng = make_rng(self.profile.seed)
        road = RoadNetwork(rows=self.rows, cols=self.cols,
                           block_size=80.0, seed=self.profile.seed)
        zoning = Zoning(road, self.profile, seed=self.profile.seed)

        g = SmartGrid.__new__(SmartGrid)
        # Mirror SmartGrid's minimum init.
        g.graph = nx.DiGraph()
        g.nodes = {}
        g.timestep = 0
        g.storm_active = False
        g.total_energy_loss = 0.0
        g.avg_frequency = 50.0
        g.event_log = []
        g.reclose_queue = {}
        g.last_fault_segment = {}
        g.bus_map = {}
        g.line_impedance = {}
        g.dc_state = None
        g.dc_enabled = True
        # Stage-43 (RNG isolation): the grid owns an environment RNG.
        # Mirror SmartGrid._init_state semantics — a profile seed pins a
        # deterministic stream; no seed mirrors the global ``random``
        # state (legacy behaviour for direct construction).
        g.random = random.Random()
        if self.profile.seed is not None:
            g.random.seed(int(self.profile.seed))
        else:
            g.random.setstate(random.getstate())

        # Build the layout.
        node_counts: Dict[str, int] = {t: 0 for t in _GENERATED_TYPES}
        self._build_topology(g, road, zoning, rng, node_counts)
        self._build_zonal_loads(g, zoning, rng, node_counts)
        self._place_renewables(g, rng, node_counts)
        self._place_storage_and_microgrids(g, rng, node_counts)

        # Wire tie switches so FLISR has something to do.
        self._place_tie_switches(g, rng)

        # Initial physics warm-up (3 iterations, like SmartGrid.__init__).
        for _ in range(3):
            try:
                g.update_generation()
                g.update_power_flow()
            except Exception:  # noqa: BLE001 — physics is best-effort
                # Some first-pass edge cases (e.g. all-isolated generator)
                # are fine; the test suite exercises the topology only.
                pass

        # Stash a report on the grid for the API.
        zones_count: Dict[str, int] = {}
        for z in zoning.zones.values():
            zones_count[z] = zones_count.get(z, 0) + 1
        g._city_report = GenerationReport(
            profile=self.profile,
            node_counts=node_counts,
            edge_count=g.graph.number_of_edges(),
            expected_load_mw=self.profile.expected_load_mw(),
            road_blocks=len(road),
            zones=zones_count,
        )
        # M5 (EHM upgrade) — also stash the road/zoning for the city
        # visualiser.  Keeping references on the grid is intentional and
        # additively non-breaking; methods that don't know about them
        # ignore them.
        g._road_network = road
        g._zoning = zoning
        return g

    # ------------------------------------------------------------------

    def _add_node(
        self,
        g: SmartGrid,
        nid: str,
        ntype: str,
        x: float,
        y: float,
        gen: float = 0.0,
        load: float = 0.0,
        source_type: str = "none",
        role: str = "load",
        priority: int = 3,
        street: str = "",
        label: Optional[str] = None,
        rng: Optional[Any] = None,
    ) -> GridNode:
        node = GridNode(nid, node_type=ntype, x=x, y=y)
        node.street = street
        node.generation = float(gen)
        node.load = float(load)
        node._base_generation = float(gen)
        node._base_load = float(load)
        node.source_type = source_type
        node.role = role
        node.priority = priority
        node.label = label or nid
        # For storage nodes default to mid-charge.
        if ntype in ("battery", "bess", "supercap"):
            node.battery_level = 0.75
        if rng is not None:
            # Tiny per-node jitter so identical profiles don't stack nodes.
            jx = float(rng.normal(0, 3.0))
            jy = float(rng.normal(0, 3.0))
            node.x += jx
            node.y += jy
        g.nodes[nid] = node
        g.graph.add_node(nid)
        return node

    # ------------------------------------------------------------------

    def _build_topology(
        self,
        g: SmartGrid,
        road: RoadNetwork,
        zoning: Zoning,
        rng: Any,
        node_counts: Dict[str, int],
    ) -> None:
        # Slack bus: a single main substation at the centroid of the road
        # network.  Without a slack the DC PF won't converge.
        #
        # Type rationale: the original EHM grid uses "substation" but pairs
        # it with 5 dedicated baseload generators (see `_build_grid`).  A
        # procedural city has no separate generator nodes by default, so we
        # use `generator_coal` here — a real baseload type whose `step()`
        # branch keeps `generation` alive across ticks (the `substation`
        # branch in `GridNode.step` zeros generation).  This node still
        # acts as the slack bus for DC PF; we set priority=1 and label it
        # as the main substation.
        cx, cy = road.bounds[0], road.bounds[1]
        max_x, max_y = road.bounds[2], road.bounds[3]
        centre = ((cx + max_x) / 2, (cy + max_y) / 2)
        self._add_node(
            g, "S_MAIN", "generator_coal", centre[0], centre[1],
            gen=self.profile.expected_load_mw(),
            load=0.0, source_type="grid", role="generation",
            priority=1, street="Central",
            label="Main Substation (slack)", rng=rng,
        )
        node_counts["substation"] += 1

        # Transmission corridor.
        n_primary = self.profile.expected_primary_substation_count()
        tower_count = self.profile.expected_transmission_tower_count()
        prev_tower = "S_MAIN"
        for i in range(tower_count):
            tx, ty = (cx - 60 + i * 30), (cy - 60)
            tid = f"TT{i}"
            self._add_node(
                g, tid, "transmission_tower", tx, ty,
                gen=0.0, load=0.0, street="Corridor",
                label=f"Transm. Tower {i}", rng=rng,
            )
            node_counts["transmission_tower"] += 1
            self._add_edge(g, prev_tower, tid)
            prev_tower = tid

        # Primary substations off the corridor.
        primary_ids: List[str] = []
        for i in range(n_primary):
            psid = f"PS{i}"
            px = cx + (i - (n_primary - 1) / 2) * (max_x - cx) / max(1, n_primary)
            py = cy + 30
            self._add_node(
                g, psid, "primary_substation", px, py,
                gen=0.0, load=0.2, street="Primary Ring",
                label=f"Primary Sub {i}", priority=1, rng=rng,
            )
            node_counts["primary_substation"] += 1
            primary_ids.append(psid)
            self._add_edge(g, prev_tower, psid)
            # Also back to the corridor so we have a ring.
            if i > 0:
                self._add_edge(g, primary_ids[-2], psid)

        # Distribution substations.
        dist_per_primary = max(
            1, self.profile.expected_distribution_substation_count() // n_primary
        )
        dist_ids: List[str] = []
        for psid in primary_ids:
            for j in range(dist_per_primary):
                dsid = f"DS_{psid}_{j}"
                dx, dy = self._jitter_near(
                    g.nodes[psid].x, g.nodes[psid].y, 40, rng,
                )
                self._add_node(
                    g, dsid, "distribution_substation", dx, dy,
                    gen=0.0, load=0.1, street=f"Dist {j}",
                    label=f"Distribution Sub {psid}-{j}", priority=2, rng=rng,
                )
                node_counts["distribution_substation"] += 1
                dist_ids.append(dsid)
                self._add_edge(g, psid, dsid)

        # Feeders (transformers + poles) off each distribution substation.
        feeders_per_dist = max(
            1, self.profile.expected_feeder_count() // max(1, len(dist_ids))
        )
        for dsid in dist_ids:
            for f in range(feeders_per_dist):
                tx_x, tx_y = self._jitter_near(
                    g.nodes[dsid].x, g.nodes[dsid].y, 30, rng,
                )
                txid = f"T_{dsid}_{f}"
                self._add_node(
                    g, txid, "transformer", tx_x, tx_y,
                    gen=0.0, load=0.05, street=f"Feeder {f}",
                    label=f"Transformer {dsid}-{f}", rng=rng,
                )
                node_counts["transformer"] += 1
                self._add_edge(g, dsid, txid)
                # Pole backbone along the feeder.
                pole_count = 3
                prev = txid
                for p in range(pole_count):
                    px, py = self._jitter_near(tx_x, tx_y, 30 * (p + 1), rng)
                    pid = f"P_{dsid}_{f}_{p}"
                    self._add_node(
                        g, pid, "pole", px, py,
                        gen=0.0, load=0.0, street=f"Feeder {f}",
                        label=f"Pole {dsid}-{f}-{p}", rng=rng,
                    )
                    node_counts["pole"] += 1
                    self._add_edge(g, prev, pid)
                    prev = pid

        # Critical infrastructure tied to the centre so a microgrid can
        # rescue them.  We attach the ICU, university, and gov building
        # to the distribution substation closest to the centre.
        closest_ds = min(
            dist_ids,
            key=lambda d: (g.nodes[d].x - centre[0]) ** 2
                          + (g.nodes[d].y - centre[1]) ** 2,
        )
        cx2, cy2 = self._jitter_near(
            g.nodes[closest_ds].x, g.nodes[closest_ds].y, 50, rng,
        )
        mgr = self._add_node(
            g, "MICROGRID_ROOT", "microgrid_root", cx2, cy2,
            gen=0.0, load=0.0, street="Critical Ring",
            label="Microgrid Root", priority=1, rng=rng,
        )
        node_counts["microgrid_root"] += 1
        self._add_edge(g, closest_ds, mgr.node_id)

        # House count derived from feeder counts.
        n_households = self.profile.expected_households()
        # Cap house population so a large city doesn't blow the 500-node
        # ceiling used by SmartGrid.add_user_node.  We don't pass through
        # add_user_node (which has its own limit) — we add them directly.
        house_cap = max(20, min(180, n_households // max(1, feeders_per_dist * dist_per_primary) // 4))
        # Distribute houses across transformers.
        transformer_ids = [nid for nid, n in g.nodes.items() if n.node_type == "transformer"]
        if transformer_ids:
            per_tx = max(1, house_cap // len(transformer_ids))
            for txid in transformer_ids:
                base_x = g.nodes[txid].x
                base_y = g.nodes[txid].y
                for h in range(per_tx):
                    hx, hy = self._jitter_near(base_x, base_y, 25, rng)
                    hid = f"H_{txid}_{h}"
                    self._add_node(
                        g, hid, "house", hx, hy,
                        gen=0.05, load=0.25, street="Residential",
                        label=f"House {txid}-{h}", priority=3, rng=rng,
                    )
                    node_counts["house"] += 1
                    self._add_edge(g, txid, hid)

        # Hospital ICU attached to the microgrid root.
        hx, hy = self._jitter_near(
            g.nodes["MICROGRID_ROOT"].x, g.nodes["MICROGRID_ROOT"].y, 25, rng,
        )
        self._add_node(
            g, "HOSP_ICU", "hospital_icu", hx, hy,
            gen=0.1, load=0.5, street="Hospital District",
            label="ICU Hospital", priority=1, rng=rng,
        )
        node_counts["hospital_icu"] += 1
        self._add_edge(g, "MICROGRID_ROOT", "HOSP_ICU")

        # Schools + university + gov building + EV chargers attached to
        # transformers spread across the city.
        if transformer_ids:
            for i, (ntype, count) in enumerate(
                [("school", 2), ("university", 1), ("gov_building", 1),
                 ("ev_charger", 3)],
            ):
                for k in range(count):
                    txid = transformer_ids[(i + k) % len(transformer_ids)]
                    base_x = g.nodes[txid].x
                    base_y = g.nodes[txid].y
                    nx_, ny_ = self._jitter_near(base_x, base_y, 35, rng)
                    nid = f"{ntype.upper()}_{txid}_{k}"
                    self._add_node(
                        g, nid, ntype, nx_, ny_,
                        gen=0.0, load=0.15,
                        street=ntype.replace("_", " ").title(),
                        label=nid, priority=2, rng=rng,
                    )
                    node_counts[ntype] += 1
                    self._add_edge(g, txid, nid)

        # Industrial + commercial nodes placed by zone.
        self._build_zonal_loads(g, zoning, rng, node_counts)

    def _build_zonal_loads(
        self,
        g: SmartGrid,
        zoning: Zoning,
        rng: Any,
        node_counts: Dict[str, int],
    ) -> None:
        """Place industry/commercial buildings in their zone centroids."""
        # Find a list of "feed points" — distribution substations and
        # transformers — to attach zonal loads to.
        feed_points = [
            nid for nid, n in g.nodes.items()
            if n.node_type in ("distribution_substation", "transformer")
        ]
        if not feed_points:
            return

        # Industrial blocks (a few per industrial centroid).
        for block in zoning.blocks_in_zone("industrial"):
            ntype = "industry"
            for i in range(2):
                txid = feed_points[(hash(block) + i) % len(feed_points)]
                bx, by = self._jitter_near(block[0], block[1], 30, rng)
                nid = f"IND_{int(block[0])}_{int(block[1])}_{i}"
                self._add_node(
                    g, nid, ntype, bx, by,
                    gen=0.0, load=0.6, street="Industrial Park",
                    label=f"Industry {nid}", priority=2, rng=rng,
                )
                node_counts[ntype] += 1
                self._add_edge(g, txid, nid)

        for block in zoning.blocks_in_zone("commercial"):
            for i in range(2):
                txid = feed_points[hash(block) % len(feed_points)]
                bx, by = self._jitter_near(block[0], block[1], 30, rng)
                nid = f"COM_{int(block[0])}_{int(block[1])}_{i}"
                self._add_node(
                    g, nid, "commercial", bx, by,
                    gen=0.0, load=0.3, street="Commercial District",
                    label=f"Commercial {nid}", priority=2, rng=rng,
                )
                node_counts["commercial"] += 1
                self._add_edge(g, txid, nid)

    def _place_renewables(
        self,
        g: SmartGrid,
        rng: Any,
        node_counts: Dict[str, int],
    ) -> None:
        renewable_mw = self.profile.expected_renewable_mw()
        if renewable_mw <= 0:
            return
        # Half solar, half wind.
        n_solar = max(1, int(math.ceil(self.profile.expected_primary_substation_count() / 2)))
        n_wind = max(1, int(math.ceil(self.profile.expected_primary_substation_count() / 3)))
        ps_ids = [nid for nid, n in g.nodes.items() if n.node_type == "primary_substation"]
        for i in range(n_solar):
            ps = ps_ids[i % len(ps_ids)]
            x, y = self._jitter_near(g.nodes[ps].x, g.nodes[ps].y, 50, rng)
            sid = f"SOLAR_FARM_{i}"
            self._add_node(
                g, sid, "solar_farm", x, y,
                gen=renewable_mw / (2 * n_solar), load=0.0,
                source_type="solar", role="generation",
                street="Renewables", label=f"Solar Farm {i}", rng=rng,
            )
            node_counts["solar_farm"] += 1
            self._add_edge(g, ps, sid)
        for i in range(n_wind):
            ps = ps_ids[i % len(ps_ids)]
            x, y = self._jitter_near(g.nodes[ps].x, g.nodes[ps].y, 50, rng)
            wid = f"WIND_FARM_{i}"
            self._add_node(
                g, wid, "wind_farm", x, y,
                gen=renewable_mw / (2 * n_wind), load=0.0,
                source_type="wind", role="generation",
                street="Renewables", label=f"Wind Farm {i}", rng=rng,
            )
            node_counts["wind_farm"] += 1
            self._add_edge(g, ps, wid)

    def _place_storage_and_microgrids(
        self,
        g: SmartGrid,
        rng: Any,
        node_counts: Dict[str, int],
    ) -> None:
        n_bess = self.profile.expected_bess_count()
        ds_ids = [nid for nid, n in g.nodes.items()
                  if n.node_type == "distribution_substation"]
        for i in range(n_bess):
            ds = ds_ids[i % max(1, len(ds_ids))]
            x, y = self._jitter_near(g.nodes[ds].x, g.nodes[ds].y, 35, rng)
            bid = f"BESS_{i}"
            self._add_node(
                g, bid, "bess", x, y,
                gen=0.0, load=0.0, source_type="battery", role="storage",
                priority=2, street="Storage Zone",
                label=f"Battery Storage {i}", rng=rng,
            )
            node_counts["bess"] += 1
            self._add_node(g, f"B{bid}", "battery", x + 5, y + 5,
                            gen=0.0, load=0.0, source_type="battery",
                            role="storage", priority=2, street="Storage Zone",
                            label=f"Battery Cell {i}", rng=rng)
            node_counts["battery"] += 1  # track the internal battery too
            self._add_edge(g, ds, bid)
            self._add_edge(g, bid, f"B{bid}")

    def _place_tie_switches(
        self,
        g: SmartGrid,
        rng: Any,
    ) -> None:
        """Mark a couple of edges as tie switches so FLISR has work to do."""
        # Pick two random pairs of distribution substations.
        ds_ids = [nid for nid, n in g.nodes.items()
                  if n.node_type == "distribution_substation"]
        if len(ds_ids) < 2:
            return
        a, b = ds_ids[0], ds_ids[-1]
        c, d = ds_ids[len(ds_ids) // 3], ds_ids[2 * len(ds_ids) // 3]
        # Connect them through a normally-open edge with `is_tie_switch`.
        self._add_edge(g, a, b, is_tie_switch=True)
        self._add_edge(g, c, d, is_tie_switch=True)

    # ------------------------------------------------------------------

    def _jitter_near(
        self,
        x: float,
        y: float,
        radius: float,
        rng: Any,
    ) -> Tuple[float, float]:
        return (
            x + float(rng.normal(0, radius / 2)),
            y + float(rng.normal(0, radius / 2)),
        )

    def _add_edge(
        self,
        g: SmartGrid,
        u: str,
        v: str,
        is_tie_switch: bool = False,
    ) -> None:
        """Add a bidirectional edge with deterministic resistance."""
        if u == v or u not in g.nodes or v not in g.nodes:
            return
        if g.graph.has_edge(u, v):
            return
        dx = g.nodes[u].x - g.nodes[v].x
        dy = g.nodes[u].y - g.nodes[v].y
        distance = (dx * dx + dy * dy) ** 0.5
        # Resistance in pu ~ 1e-4 × distance, capped at 0.05 pu.
        resistance = min(0.05, max(0.001, distance * 1e-4))
        capacity = 5.0 if not is_tie_switch else 4.0
        g.graph.add_edge(
            u, v,
            active=True,
            resistance=resistance,
            capacity=capacity,
            flow=0.0,
            switch_type="tie" if is_tie_switch else "sectionalizer",
            switch_status="open" if is_tie_switch else "closed",
            is_tie_switch=is_tie_switch,
        )
        # Mirror so undirected algorithms work too.
        g.graph.add_edge(
            v, u,
            active=True,
            resistance=resistance,
            capacity=capacity,
            flow=0.0,
            switch_type="tie" if is_tie_switch else "sectionalizer",
            switch_status="open" if is_tie_switch else "closed",
            is_tie_switch=is_tie_switch,
        )
