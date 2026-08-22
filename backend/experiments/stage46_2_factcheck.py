"""Quick fact-check for Stage 46.2 before writing the full audit."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from utils.seeds import set_global_seed
from simulation.grid import SmartGrid

set_global_seed(0)
g = SmartGrid(seed=0)

for nid in ("STORAGE_BAT", "STORAGE_SC"):
    n = g.nodes[nid]
    print(f"{nid}: node_type={n.node_type!r} battery_level={n.battery_level} "
          f"battery_capacity={n.battery_capacity} supercap_level={n.supercap_level} "
          f"supercap_capacity={n.supercap_capacity} "
          f"discharge_rate={getattr(n,'discharge_rate',None)} "
          f"role={n.role} source_type={n.source_type} priority={n.priority}")

print("G0 exists:", "G0" in g.nodes)
print("node insertion order (first 8):", list(g.nodes.keys())[:8])
print("gen node types:", [(nid, n.node_type) for nid, n in g.nodes.items() if str(n.node_type).startswith('generator')])

# house count + a sample house
houses = [nid for nid, n in g.nodes.items() if n.node_type == "house"]
print("num houses:", len(houses), "sample:", houses[:3])
h = g.nodes[houses[0]]
print("house sample: battery_level=", h.battery_level, "battery_capacity=", h.battery_capacity,
      "supercap_level=", h.supercap_level, "supercap_capacity=", h.supercap_capacity)
print("'storage_bat' in 'battery':", "storage_bat" in "battery")
print("'storage_sc' in 'supercap':", "storage_sc" in "supercap")
print("'battery' in 'storage_bat':", "battery" in "storage_bat")
print("'supercap' in 'storage_sc':", "supercap" in "storage_sc")

# action 0 target check
from experiments.runner import _dispatch_action
before = {nid: n.generation for nid, n in g.nodes.items()}
_dispatch_action(g, 0)
after = {nid: n.generation for nid, n in g.nodes.items()}
changed = [(nid, before[nid], after[nid]) for nid in g.nodes if before[nid] != after[nid]]
print("action 0 changed nodes:", changed[:6])