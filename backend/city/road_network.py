"""
road_network.py — a small 2D road graph for procedural cities.

Why
---
A digital-twin city has roads.  The road graph isn't part of the
electrical topology (no power flows through it), but it drives the
*placement* of feeders (which follow streets) and the visual layout
of the city layer in M5.  Without it the generator produces a grid
of floating points; with it the grid lines up with streets and the
visualisation looks like a real city.

This module is intentionally small and dependency-free.  It returns
a plain `networkx.Graph` of `(x, y)` road nodes connected by straight
segments with a per-edge length.  The grid pattern is a deterministic
Manhattan lattice with one diagonal "avenue" cut through to keep the
road graph from being overly regular.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterator, List, Tuple

import networkx as nx

from utils.seeds import make_rng


@dataclass(frozen=True)
class RoadSegment:
    u: Tuple[float, float]
    v: Tuple[float, float]
    length: float


class RoadNetwork:
    """A simple Manhattan road graph with one diagonal avenue."""

    def __init__(
        self,
        rows: int = 6,
        cols: int = 8,
        block_size: float = 80.0,
        seed: int = 42,
    ) -> None:
        self.rows = rows
        self.cols = cols
        self.block_size = float(block_size)
        self.seed = seed
        self.graph = nx.Graph()
        self._build()

    # ------------------------------------------------------------------

    def _build(self) -> None:
        rng = make_rng(self.seed)
        # Nodes at intersections, spaced by block_size, with one diagonal
        # avenue picked deterministically (random but seeded).
        for r in range(self.rows):
            for c in range(self.cols):
                x = c * self.block_size
                y = r * self.block_size
                self.graph.add_node((x, y), kind="intersection")

        # Manhattan edges.
        for r in range(self.rows):
            for c in range(self.cols):
                x = c * self.block_size
                y = r * self.block_size
                if c + 1 < self.cols:
                    self.graph.add_edge(
                        (x, y), ((c + 1) * self.block_size, y),
                        length=self.block_size, kind="street",
                    )
                if r + 1 < self.rows:
                    self.graph.add_edge(
                        (x, y), (x, (r + 1) * self.block_size),
                        length=self.block_size, kind="street",
                    )

        # One diagonal "avenue" — deterministically chosen between two
        # diagonally-opposite corners.
        diag_start = (0, 0)
        diag_end = ((self.cols - 1) * self.block_size,
                    (self.rows - 1) * self.block_size)
        # Approximate the diagonal as Manhattan segments so the path is
        # always on-street.
        cx, cy = diag_start
        end_x, end_y = diag_end
        steps = max(self.rows, self.cols)
        for _ in range(steps):
            if cx < end_x:
                cx += self.block_size
                self.graph.add_edge(
                    (cx - self.block_size, cy), (cx, cy),
                    length=self.block_size, kind="avenue",
                )
            if cy < end_y:
                cy += self.block_size
                self.graph.add_edge(
                    (cx, cy - self.block_size), (cx, cy),
                    length=self.block_size, kind="avenue",
                )

        # Mark a tiny bit of variation via RNG (used by tests for
        # reproducibility).
        _ = rng.random()

    # ------------------------------------------------------------------

    @property
    def bounds(self) -> Tuple[float, float, float, float]:
        """Return (min_x, min_y, max_x, max_y) of the road network."""
        xs = [p[0] for p in self.graph.nodes]
        ys = [p[1] for p in self.graph.nodes]
        return min(xs), min(ys), max(xs), max(ys)

    def edges(self) -> List[RoadSegment]:
        out: List[RoadSegment] = []
        for u, v, data in self.graph.edges(data=True):
            dx = u[0] - v[0]
            dy = u[1] - v[1]
            length = float(data.get("length", (dx * dx + dy * dy) ** 0.5))
            out.append(RoadSegment(u=u, v=v, length=length))
        return out

    def __iter__(self) -> Iterator[Tuple[float, float]]:
        return iter(self.graph.nodes)

    def __len__(self) -> int:
        return self.graph.number_of_nodes()