"""test_flisr_9stage.py — Stage 6 (EHM-CRIT-003): FLISR 9-stage orchestrator."""
from __future__ import annotations

from simulation.grid import SmartGrid


def test_flisr_9stage_emits_all_nine_stages():
    g = SmartGrid()
    g.inject_failure("P_A1")
    result = g.flisr_9stage()
    assert set(result["stages"]) == {
        "DETECT", "LOCATE", "ISOLATE", "IDENTIFY",
        "CANDIDATE_ENUMERATE", "RANK", "SWITCH",
        "VALIDATE", "REPORT",
    }


def test_flisr_9stage_records_completed_stages():
    g = SmartGrid()
    g.inject_failure("P_A1")
    result = g.flisr_9stage()
    for stage in ("DETECT", "SWITCH", "VALIDATE", "REPORT"):
        assert stage in result["stages_completed"], (
            f"Stage {stage!r} missing from completed list"
        )


def test_flisr_9stage_returns_timings():
    g = SmartGrid()
    g.inject_failure("P_A1")
    result = g.flisr_9stage()
    for stage in result["stages"]:
        assert stage in result["timings_s"]
        assert result["timings_s"][stage] >= 0.0


def test_flisr_9stage_reports_fault_target():
    g = SmartGrid()
    g.inject_failure("P_A1")
    result = g.flisr_9stage()
    assert result["fault_target"] == "P_A1"
    assert result["n_failed_nodes"] == 1


def test_flisr_9stage_legacy_return_preserved():
    """The 9-stage orchestrator returns the legacy flisr_restore() payload."""
    g = SmartGrid()
    g.inject_failure("P_A1")
    result = g.flisr_9stage()
    legacy = result["legacy"]
    assert "actions_attempted" in legacy
    assert "actions_applied" in legacy
    assert "nodes_restored" in legacy
    assert "remaining_isolated" in legacy


def test_flisr_9stage_validation_block_present():
    g = SmartGrid()
    g.inject_failure("P_A1")
    result = g.flisr_9stage()
    assert "validation" in result
    assert "dc_pf_ok" in result["validation"]
    assert "kcl_residual_max" in result["validation"]


def test_flisr_9stage_no_faults_is_safe():
    """When no node is failed, all stages still complete."""
    g = SmartGrid()
    result = g.flisr_9stage()
    assert result["n_failed_nodes"] == 0
    assert result["fault_target"] is None
    assert "SWITCH" in result["stages_completed"]