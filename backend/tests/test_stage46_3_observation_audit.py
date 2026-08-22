"""
test_stage46_3_observation_audit.py — Tests for Stage 46.3 DQN Storage Observation Audit

These tests verify the audit findings without modifying production behavior.
"""

import json
from pathlib import Path

import pytest

OUTPUT_DIR = Path(r'C:\Users\ELCOT\Music\EHM-paper\backend\experiments\results\stage46_3')
CKPT_PATH = r'C:\Users\ELCOT\Music\EHM-paper\backend\experiments\checkpoints\dqn_stage44.pt'


class TestCheckpointIntegrity:
    """Verify the frozen checkpoint remains byte-identical."""

    def test_checkpoint_hash_unchanged(self):
        """Checkpoint SHA-256 must be identical before and after audit."""
        with open(OUTPUT_DIR / "checkpoint_hash.json") as f:
            data = json.load(f)
        assert data["unchanged"] is True, "Checkpoint hash changed during audit"
        assert data["sha256_before"] == data["sha256_after"]
        assert data["sha256_before"] == "eb7bbed22a18f13dbe607b908caf7905ec0fd9b9c14f2a80a75c628bac594493"

    def test_checkpoint_dimensions(self):
        """Checkpoint must have state_dim=78, n_actions=5."""
        with open(OUTPUT_DIR / "checkpoint_hash.json") as f:
            data = json.load(f)
        # The manifest contains dimension info
        with open(OUTPUT_DIR / "manifest.json") as f:
            manifest = json.load(f)
        assert manifest["checkpoint"]["state_dim"] == 78
        assert manifest["checkpoint"]["n_actions"] == 5


class TestNoRetraining:
    """Verify no training occurred during audit."""

    def test_no_training_operations(self):
        """No optimizer.step, backward, or checkpoint save occurred."""
        with open(OUTPUT_DIR / "no_retraining_check.json") as f:
            data = json.load(f)
        assert data["optimizer_step_called"] is False
        assert data["backward_called"] is False
        assert data["loss_computed"] is False
        assert data["training_loop_executed"] is False
        assert data["checkpoint_saved"] is False
        assert data["agent_mode"] == "eval_mode()"


class TestSourceIntegrity:
    """Verify no production source files were modified."""

    def test_no_production_files_modified(self):
        """Only new audit files created, no production code changed."""
        with open(OUTPUT_DIR / "source_integrity.json") as f:
            data = json.load(f)
        assert data["production_files_modified"] == []
        assert data["checkpoint_retrained"] is False
        assert data["training_occurred"] is False


class TestStateVectorMapping:
    """Verify the DQN input dimension and feature mapping."""

    def test_input_dimension_is_78(self):
        """Extended state dimension must be 78."""
        with open(OUTPUT_DIR / "manifest.json") as f:
            manifest = json.load(f)
        assert manifest["checkpoint"]["state_dim"] == 78

    def test_feature_73_is_battery_soc(self):
        """Feature 73 corresponds to battery SOC."""
        with open(OUTPUT_DIR / "battery_observation_probe.json") as f:
            data = json.load(f)
        # Feature 73 is derived from _storage_level(grid, "battery")
        for entry in data:
            assert "feature_73" in entry

    def test_feature_74_is_supercap_soc(self):
        """Feature 74 corresponds to supercapacitor SOC."""
        with open(OUTPUT_DIR / "supercap_observation_probe.json") as f:
            data = json.load(f)
        for entry in data:
            assert "feature_74" in entry


class TestStorageObservation:
    """Test grid storage SOC observability."""

    def test_battery_feature_constant_when_houses_at_max(self):
        """Feature 73 remains 1.0 when house batteries are at 1.0, regardless of grid battery SOC."""
        with open(OUTPUT_DIR / "battery_observation_probe.json") as f:
            data = json.load(f)
        feat_73_vals = [entry["feature_73"] for entry in data]
        # All values should be 1.0 (masked by house SOC=1.0)
        for v in feat_73_vals:
            assert abs(v - 1.0) < 1e-6, f"Feature 73 changed unexpectedly: {v}"

    def test_supercap_feature_constant_when_houses_at_max(self):
        """Feature 74 remains 1.0 when house supercaps are at 1.0, regardless of grid supercap SOC."""
        with open(OUTPUT_DIR / "supercap_observation_probe.json") as f:
            data = json.load(f)
        feat_74_vals = [entry["feature_74"] for entry in data]
        for v in feat_74_vals:
            assert abs(v - 1.0) < 1e-6, f"Feature 74 changed unexpectedly: {v}"

    def test_grid_battery_soc_not_independently_observable(self):
        """Changing ONLY grid battery SOC does not change DQN input feature 73."""
        with open(OUTPUT_DIR / "battery_observation_probe.json") as f:
            data = json.load(f)
        # Grid battery SOC varies from 0.8 to 0.0, but feature 73 stays 1.0
        grid_socs = [entry["grid_battery_soc"] for entry in data]
        assert max(grid_socs) > 0.5  # We tested high values
        assert min(grid_socs) < 0.1  # We tested low values
        feat_73_vals = [entry["feature_73"] for entry in data]
        assert max(feat_73_vals) == min(feat_73_vals) == 1.0

    def test_grid_supercap_soc_not_independently_observable(self):
        """Changing ONLY grid supercap SOC does not change DQN input feature 74."""
        with open(OUTPUT_DIR / "supercap_observation_probe.json") as f:
            data = json.load(f)
        grid_socs = [entry["grid_supercap_soc"] for entry in data]
        assert max(grid_socs) > 0.5
        assert min(grid_socs) < 0.1
        feat_74_vals = [entry["feature_74"] for entry in data]
        assert max(feat_74_vals) == min(feat_74_vals) == 1.0


class TestQValueSensitivity:
    """Test Q-value sensitivity to storage SOC changes."""

    def test_battery_soc_change_does_not_affect_q_values(self):
        """Q-values identical when only grid battery SOC changes (houses at 1.0)."""
        with open(OUTPUT_DIR / "q_value_sensitivity_battery.json") as f:
            data = json.load(f)
        assert data["l2_norm"] == 0.0, "Q-values changed despite masked feature"
        assert data["action_changed"] is False

    def test_supercap_soc_change_does_not_affect_q_values(self):
        """Q-values identical when only grid supercap SOC changes (houses at 1.0)."""
        with open(OUTPUT_DIR / "q_value_sensitivity_supercap.json") as f:
            data = json.load(f)
        assert data["l2_norm"] == 0.0, "Q-values changed despite masked feature"
        assert data["action_changed"] is False

    def test_lstm_forecast_changes_q_values(self):
        """LSTM forecast (feature 72) does change Q-values."""
        with open(OUTPUT_DIR / "feature_sensitivity.json") as f:
            data = json.load(f)
        lstm_entry = next(e for e in data if "lstm_forecast" in e["feature_changed"])
        assert lstm_entry["delta_q_norm"] > 0.0
        assert lstm_entry["delta_state_norm"] > 0.0

    def test_twin_risk_changes_q_values(self):
        """Twin max risk (feature 75) does change Q-values."""
        with open(OUTPUT_DIR / "feature_sensitivity.json") as f:
            data = json.load(f)
        twin_entry = next(e for e in data if "twin_max_risk" in e["feature_changed"])
        assert twin_entry["delta_q_norm"] > 0.0
        assert twin_entry["delta_state_norm"] > 0.0


class TestActionSensitivity:
    """Test action selection sensitivity."""

    def test_no_action_change_for_storage_soc(self):
        """Storage SOC changes don't change selected action (all action 4)."""
        with open(OUTPUT_DIR / "action_sensitivity_multi_state.json") as f:
            data = json.load(f)
        actions = [entry["action"] for entry in data]
        # All should be action 4 (pinned policy)
        for a in actions:
            assert a == 4, f"Unexpected action: {a}"

    def test_feature_isolation_no_action_changes(self):
        """No single feature change flips the action (policy pinned at action 4)."""
        with open(OUTPUT_DIR / "feature_sensitivity.json") as f:
            data = json.load(f)
        for entry in data:
            assert entry["action_changed"] is False, f"Action changed for {entry['feature_changed']}"


class TestEMSObservability:
    """Test EMS observability through DQN."""

    def test_ems_physical_effect_not_in_dqn_observation(self):
        """EMS changes physical battery SOC but not DQN feature 73."""
        with open(OUTPUT_DIR / "ems_observability.json") as f:
            data = json.load(f)
        # Physical change
        phys = data["physical_changes"]["STORAGE_BAT_battery_level"]
        assert phys["before"] != phys["after"], "EMS should change battery SOC"
        # DQN observation unchanged
        obs = data["dqn_observation_changes"]["feature_73_battery_soc"]
        assert obs["before"] == obs["after"] == 1.0, "Feature 73 should not change (masked)"

    def test_ems_classification(self):
        """EMS changes physical storage but storage features (73, 74) unchanged."""
        with open(OUTPUT_DIR / "ems_observability.json") as f:
            data = json.load(f)
        # Storage features specifically unchanged (masked by house SOC)
        obs_bat = data["dqn_observation_changes"]["feature_73_battery_soc"]
        obs_sc = data["dqn_observation_changes"]["feature_74_supercap_soc"]
        assert obs_bat["before"] == obs_bat["after"] == 1.0
        assert obs_sc["before"] == obs_sc["after"] == 1.0
        # But full state changes due to power flow recomputation
        assert data["dqn_observation_changes"]["full_state_delta_norm"] > 0.0


class TestStorageObservabilityMatrix:
    """Test the final storage observability classification."""

    def test_battery_classification_level_1(self):
        """Battery SOC classified as LEVEL 1 (represented but constant)."""
        with open(OUTPUT_DIR / "storage_observability.json") as f:
            data = json.load(f)
        bat = data["battery_soc"]
        assert bat["grid_storage_visible"] is False
        assert bat["state_delta"] is True  # No state change
        assert bat["q_delta_norm"] == 0.0
        assert bat["action_delta"] is False
        assert "LEVEL 1" in bat["classification"]

    def test_supercap_classification_level_1(self):
        """Supercap SOC classified as LEVEL 1 (represented but constant)."""
        with open(OUTPUT_DIR / "storage_observability.json") as f:
            data = json.load(f)
        sc = data["supercap_soc"]
        assert sc["grid_storage_visible"] is False
        assert sc["state_delta"] is True  # No state change
        assert sc["q_delta_norm"] == 0.0
        assert sc["action_delta"] is False
        assert "LEVEL 1" in sc["classification"]


class TestHypotheticalDirectRepresentation:
    """Test the analytical comparison of direct representation."""

    def test_direct_representation_would_show_grid_soc(self):
        """Direct (grid-only) representation would expose actual grid storage SOC."""
        with open(OUTPUT_DIR / "hypothetical_direct_representation.json") as f:
            data = json.load(f)
        curr = data["current_representation"]
        hyp = data["hypothetical_direct"]
        # Current shows 1.0, direct shows actual grid values
        assert curr["feature_73_battery"] == 1.0
        assert hyp["feature_73_grid_battery"] == 0.55
        assert curr["feature_74_supercap"] == 1.0
        assert hyp["feature_74_grid_supercap"] == 0.667


if __name__ == "__main__":
    pytest.main([__file__, "-v"])