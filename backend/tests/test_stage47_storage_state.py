"""
test_stage47_storage_state.py — Stage 47 Storage State Repair Unit Tests

These tests verify that the storage observation repair correctly exposes
grid-scale storage SOC (STORAGE_BAT, STORAGE_SC) without masking by
house storage SOC.
"""

import pytest
import sys
from pathlib import Path

# Add backend to path
BACKEND = Path(__file__).parent.parent / "backend"
sys.path.insert(0, str(BACKEND))

from simulation.grid import SmartGrid
from experiments.runner import _storage_level
from models.rl_agent import EXTENDED_STATE_DIM, build_extended_state


class TestGridStorageNodesExist:
    """Verify the grid storage nodes exist and have correct types."""

    def test_storage_bat_exists(self):
        grid = SmartGrid(seed=0)
        assert "STORAGE_BAT" in grid.nodes
        node = grid.nodes["STORAGE_BAT"]
        assert node.node_type == "battery"
        assert hasattr(node, "battery_level")
        assert hasattr(node, "battery_capacity")

    def test_storage_sc_exists(self):
        grid = SmartGrid(seed=0)
        assert "STORAGE_SC" in grid.nodes
        node = grid.nodes["STORAGE_SC"]
        assert node.node_type == "supercap"
        assert hasattr(node, "supercap_level")
        assert hasattr(node, "supercap_capacity")

    def test_house_storage_exists(self):
        grid = SmartGrid(seed=0)
        house_nodes = [n for n in grid.nodes.values() if n.node_type == "house"]
        assert len(house_nodes) >= 10  # At least 10 houses
        for house in house_nodes:
            assert hasattr(house, "battery_level")
            assert hasattr(house, "supercap_level")


class TestStorageLevelFunction:
    """Test the corrected _storage_level() function."""

    def test_grid_battery_soc_changes_feature_73(self):
        """Changing STORAGE_BAT battery_level changes the returned value."""
        grid = SmartGrid(seed=0)
        # Default is 0.75
        assert _storage_level(grid, "battery") == 0.75
        
        # Change to 0.80
        grid.nodes["STORAGE_BAT"].battery_level = 0.80
        assert _storage_level(grid, "battery") == 0.80
        
        # Change to 0.20
        grid.nodes["STORAGE_BAT"].battery_level = 0.20
        assert _storage_level(grid, "battery") == 0.20
        
        # Change to 0.0
        grid.nodes["STORAGE_BAT"].battery_level = 0.0
        assert _storage_level(grid, "battery") == 0.0

    def test_house_battery_soc_does_not_mask_grid(self):
        """House battery SOC at 1.0 should NOT mask grid battery SOC."""
        grid = SmartGrid(seed=0)
        grid.nodes["STORAGE_BAT"].battery_level = 0.50
        
        # Set all houses to SOC=1.0 (default, but explicit)
        for n in grid.nodes.values():
            if n.node_type == "house":
                n.battery_level = 1.0
        
        # Feature should be 0.50 (grid), NOT 1.0 (house)
        assert _storage_level(grid, "battery") == 0.50

    def test_grid_supercap_soc_changes_feature_74(self):
        """Changing STORAGE_SC supercap_level changes the returned value."""
        grid = SmartGrid(seed=0)
        # Default is 1.0
        assert _storage_level(grid, "supercap") == 1.0
        
        # Change to 0.80
        grid.nodes["STORAGE_SC"].supercap_level = 0.80
        assert _storage_level(grid, "supercap") == 0.80
        
        # Change to 0.20
        grid.nodes["STORAGE_SC"].supercap_level = 0.20
        assert _storage_level(grid, "supercap") == 0.20
        
        # Change to 0.0
        grid.nodes["STORAGE_SC"].supercap_level = 0.0
        assert _storage_level(grid, "supercap") == 0.0

    def test_house_supercap_soc_does_not_mask_grid(self):
        """House supercap SOC at 1.0 should NOT mask grid supercap SOC."""
        grid = SmartGrid(seed=0)
        grid.nodes["STORAGE_SC"].supercap_level = 0.50
        
        # Set all houses to SOC=1.0
        for n in grid.nodes.values():
            if n.node_type == "house":
                n.supercap_level = 1.0
        
        # Feature should be 0.50 (grid), NOT 1.0 (house)
        assert _storage_level(grid, "supercap") == 0.50

    def test_battery_soc_specific_values(self):
        """Test specific battery SOC values from Stage-46.3 audit."""
        test_values = [0.80, 0.60, 0.40, 0.20, 0.10, 0.05, 0.00]
        
        for soc in test_values:
            grid = SmartGrid(seed=0)
            grid.nodes["STORAGE_BAT"].battery_level = soc
            # Set houses to 1.0 to verify no masking
            for n in grid.nodes.values():
                if n.node_type == "house":
                    n.battery_level = 1.0
            
            result = _storage_level(grid, "battery")
            assert result == soc, f"Expected {soc}, got {result}"

    def test_supercap_soc_specific_values(self):
        """Test specific supercap SOC values from Stage-46.3 audit."""
        test_values = [0.80, 0.60, 0.40, 0.20, 0.10, 0.05, 0.00]
        
        for soc in test_values:
            grid = SmartGrid(seed=0)
            grid.nodes["STORAGE_SC"].supercap_level = soc
            # Set houses to 1.0 to verify no masking
            for n in grid.nodes.values():
                if n.node_type == "house":
                    n.supercap_level = 1.0
            
            result = _storage_level(grid, "supercap")
            assert result == soc, f"Expected {soc}, got {result}"

    def test_failed_storage_bat_returns_zero(self):
        """Failed STORAGE_BAT should return 0.0."""
        grid = SmartGrid(seed=0)
        grid.nodes["STORAGE_BAT"].battery_level = 0.80
        grid.nodes["STORAGE_BAT"].failed = True
        assert _storage_level(grid, "battery") == 0.0

    def test_isolated_storage_bat_returns_zero(self):
        """Isolated STORAGE_BAT should return 0.0."""
        grid = SmartGrid(seed=0)
        grid.nodes["STORAGE_BAT"].battery_level = 0.80
        grid.nodes["STORAGE_BAT"].isolated = True
        assert _storage_level(grid, "battery") == 0.0

    def test_failed_storage_sc_returns_zero(self):
        """Failed STORAGE_SC should return 0.0."""
        grid = SmartGrid(seed=0)
        grid.nodes["STORAGE_SC"].supercap_level = 0.80
        grid.nodes["STORAGE_SC"].failed = True
        assert _storage_level(grid, "supercap") == 0.0

    def test_isolated_storage_sc_returns_zero(self):
        """Isolated STORAGE_SC should return 0.0."""
        grid = SmartGrid(seed=0)
        grid.nodes["STORAGE_SC"].supercap_level = 0.80
        grid.nodes["STORAGE_SC"].isolated = True
        assert _storage_level(grid, "supercap") == 0.0

    def test_unknown_kind_returns_zero(self):
        """Unknown storage kind should return 0.0."""
        grid = SmartGrid(seed=0)
        assert _storage_level(grid, "unknown") == 0.0
        assert _storage_level(grid, "") == 0.0


class TestExtendedStateConstruction:
    """Test that build_extended_state produces correct 78-dim vector."""

    def test_state_dimension_is_78(self):
        """Extended state must be 78 dimensions."""
        grid = SmartGrid(seed=0)
        legacy_state = grid.get_rl_state()
        assert len(legacy_state) == 72
        
        ext_state = build_extended_state(
            legacy_state,
            predicted_load=0.5,
            battery_soc=0.75,
            supercap_soc=1.0,
            twin_max_risk=0.0,
            twin_mean_risk=0.0,
            twin_high_frac=0.0,
        )
        assert len(ext_state) == 78
        assert EXTENDED_STATE_DIM == 78

    def test_feature_73_is_battery_soc(self):
        """Feature 73 (index 73) should equal battery_soc parameter."""
        grid = SmartGrid(seed=0)
        legacy_state = grid.get_rl_state()
        
        for soc in [0.0, 0.25, 0.50, 0.75, 1.0]:
            ext_state = build_extended_state(
                legacy_state,
                predicted_load=0.5,
                battery_soc=soc,
                supercap_soc=1.0,
                twin_max_risk=0.0,
                twin_mean_risk=0.0,
                twin_high_frac=0.0,
            )
            assert ext_state[73] == soc

    def test_feature_74_is_supercap_soc(self):
        """Feature 74 (index 74) should equal supercap_soc parameter."""
        grid = SmartGrid(seed=0)
        legacy_state = grid.get_rl_state()
        
        for soc in [0.0, 0.25, 0.50, 0.75, 1.0]:
            ext_state = build_extended_state(
                legacy_state,
                predicted_load=0.5,
                battery_soc=0.75,
                supercap_soc=soc,
                twin_max_risk=0.0,
                twin_mean_risk=0.0,
                twin_high_frac=0.0,
            )
            assert ext_state[74] == soc

    def test_end_to_end_grid_to_feature(self):
        """Full pipeline: grid -> _storage_level -> build_extended_state -> feature 73/74."""
        grid = SmartGrid(seed=0)
        
        # Test battery
        grid.nodes["STORAGE_BAT"].battery_level = 0.60
        for n in grid.nodes.values():
            if n.node_type == "house":
                n.battery_level = 1.0  # Should not mask
        
        legacy_state = grid.get_rl_state()
        battery_soc = _storage_level(grid, "battery")
        ext_state = build_extended_state(
            legacy_state,
            predicted_load=0.5,
            battery_soc=battery_soc,
            supercap_soc=1.0,
            twin_max_risk=0.0,
            twin_mean_risk=0.0,
            twin_high_frac=0.0,
        )
        assert ext_state[73] == 0.60
        
        # Test supercap
        grid.nodes["STORAGE_SC"].supercap_level = 0.40
        for n in grid.nodes.values():
            if n.node_type == "house":
                n.supercap_level = 1.0  # Should not mask
        
        supercap_soc = _storage_level(grid, "supercap")
        ext_state = build_extended_state(
            legacy_state,
            predicted_load=0.5,
            battery_soc=0.60,
            supercap_soc=supercap_soc,
            twin_max_risk=0.0,
            twin_mean_risk=0.0,
            twin_high_frac=0.0,
        )
        assert ext_state[74] == 0.40


class TestStage44CheckpointUnchanged:
    """Verify Stage-44 checkpoint is byte-identical."""

    def test_checkpoint_hash_unchanged(self):
        import hashlib
        ckpt_path = Path(r"C:\Users\ELCOT\Music\EHM-paper\backend\experiments\checkpoints\dqn_stage44.pt")
        with open(ckpt_path, "rb") as f:
            sha256 = hashlib.sha256(f.read()).hexdigest()
        expected = "eb7bbed22a18f13dbe607b908caf7905ec0fd9b9c14f2a80a75c628bac594493"
        assert sha256 == expected


if __name__ == "__main__":
    pytest.main([__file__, "-v"])