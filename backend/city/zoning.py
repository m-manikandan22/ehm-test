"""
zoning.py — pure-Python zoning for the procedural city generator.

Why a separate module
---------------------
`CityGenerator` needs to decide which blocks of the road network are
"residential", "industrial", "commercial" or "critical".  The
zoning decision is what feeds population density back into load:
a residential block gets ~80 households (1 kW each), an industrial
block gets ~5 factories (50 kW each).  Getting this wrong means the
simulator's per-step power balance is meaningless.

We deliberately do **not** pull in scipy for Voronoi tessellation
(the optional dependency would break the install for non-scipy
users).  Instead we use a deterministic nearest-centroid rule on a
grid of "centroids" placed by the profile's percentages.  This is
good enough for a research simulator and keeps the implementation
dependency-free.

Public API
----------
`Zoning(road_network, profile, rng)` — returns a `dict[block -> zone]`
where block is a `Tuple[float, float]` intersection coordinate and
zone is one of `"residential" | "industrial" | "commercial" | "critical"`.
"""
from __future__ import annotations

from typing import Dict, Tuple

import numpy as np

from city.city_profile import CityProfile
from city.road_network import RoadNetwork
from utils.seeds import make_rng


ZoneName = str  # "residential" | "industrial" | "commercial" | "critical"
Block = Tuple[float, float]


class Zoning:
    """Deterministic nearest-centroid zoning over the road network."""

    def __init__(
        self,
        road_network: RoadNetwork,
        profile: CityProfile,
        seed: int = 42,
    ) -> None:
        self.road_network = road_network
        self.profile = profile
        self.seed = seed
        self._centroids: Dict[ZoneName, Tuple[float, float]] = {}
        self._zones: Dict[Block, ZoneName] = {}
        self._build()

    # ------------------------------------------------------------------

    def _build(self) -> None:
        rng = make_rng(self.seed)
        nodes = list(self.road_network.graph.nodes)
        if not nodes:
            return

        # Build centroids: pick distinct corners of the road network.
        xs = [p[0] for p in nodes]
        ys = [p[1] for p in nodes]
        min_x, min_y, max_x, max_y = min(xs), min(ys), max(xs), max(ys)

        # Industry near (max_x, min_y) — typically downwind / outskirts.
        # Commercial near the centre.  Residential on one side, critical
        # scattered but weighted to the centre.
        self._centroids = {
            "industrial": (max_x, min_y),
            "commercial": ((min_x + max_x) / 2, (min_y + max_y) / 2),
            "critical": (min_x + (max_x - min_x) * 0.4,
                         min_y + (max_y - min_y) * 0.4),
            "residential": (min_x, max_y),
        }

        # Apply the user's percentages as weights so the dominant zone
        # absorbs more blocks.
        weights = {
            "industrial": max(0.05, self.profile.industrial_pct),
            "commercial": max(0.05, self.profile.commercial_pct),
            "critical": max(0.01, self.profile.critical_infra_pct),
            "residential": 1.0 - (self.profile.industrial_pct
                                  + self.profile.commercial_pct
                                  + self.profile.critical_infra_pct),
        }
        total_w = sum(weights.values()) or 1.0

        node_array = np.asarray(nodes)
        for zone, centroid in self._centroids.items():
            self._centroids[zone] = (
                centroid[0] + float(rng.normal(0, 20)),
                centroid[1] + float(rng.normal(0, 20)),
            )

        centroids_arr = np.asarray(list(self._centroids.values()))
        centroid_names = list(self._centroids.keys())
        diffs = node_array[:, None, :] - centroids_arr[None, :, :]
        dists = np.linalg.norm(diffs, axis=2)
        nearest = np.argmin(dists, axis=1)

        # Soft-weight by `weights`: with probability proportional to the
        # weight, override the nearest-centroid assignment to the
        # dominant zone.  Keeps the algorithm dependency-free.
        for i, node in enumerate(nodes):
            chosen = centroid_names[nearest[i]]
            roll = rng.random()
            cum = 0.0
            for zone, w in weights.items():
                cum += w / total_w
                if roll <= cum:
                    chosen = zone
                    break
            self._zones[node] = chosen

    # ------------------------------------------------------------------

    def get(self, block: Block) -> ZoneName:
        return self._zones.get(block, "residential")

    def blocks_in_zone(self, zone: ZoneName) -> list:
        return [b for b, z in self._zones.items() if z == zone]

    @property
    def zones(self) -> Dict[Block, ZoneName]:
        return dict(self._zones)

    @property
    def centroids(self) -> Dict[ZoneName, Tuple[float, float]]:
        return dict(self._centroids)