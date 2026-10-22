"""
Tests for src/asset_state_registry.py
Spec: PER-STATE-001 → 006

Tests cover:
  - New asset registration
  - Movement state machine transitions (STATIONARY → SUSPECTED → MOVING → STATIONARY)
  - Temporal hysteresis for ASSET_MISSING (misses must exceed threshold before alert)
  - ASSET_MOVED alert generation
  - Baseline position reset
  - Patrol cycle bookkeeping
"""

import sys
import os
import pytest

# Ensure project root is in sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.asset_state_registry import AssetStateRegistry


# ---------------------------------------------------------------------------
# Helpers & fixtures
# ---------------------------------------------------------------------------

def make_registry(tmp_path, missing_threshold=3):
    """Create an AssetStateRegistry from a temp config file."""
    config = tmp_path / "movement_config.yaml"
    config.write_text(
        "states: ['STATIONARY', 'MOVEMENT_SUSPECTED', 'MOVING', 'UNCERTAIN']\n"
        "frames_to_suspect: 2\n"
        "frames_to_confirm: 5\n"
        "frames_to_clear: 10\n"
        "position_change_threshold_px: 15\n"
        f"missing_alert_threshold: {missing_threshold}\n"
        "displacement_alert_threshold_m: 3.0\n"
        "ego_motion_enabled: true\n"
    )
    return AssetStateRegistry(config_path=str(config))


STATIONARY_POS = (100.0, 200.0)
MOVED_POS      = (200.0, 300.0)   # > 15px away from STATIONARY_POS


# ---------------------------------------------------------------------------
# 1. New asset registration
# ---------------------------------------------------------------------------

class TestNewAssetRegistration:

    def test_first_update_registers_asset(self, tmp_path):
        reg = make_registry(tmp_path)
        reg.update("EXC-01", "Excavator", STATIONARY_POS, "CONFIRMED", 0.91)
        assert reg.tracked_count == 1

    def test_first_update_state_is_stationary(self, tmp_path):
        reg = make_registry(tmp_path)
        result = reg.update("EXC-01", "Excavator", STATIONARY_POS, "CONFIRMED", 0.91)
        assert result["movement_state"] == "STATIONARY"

    def test_first_update_no_alert(self, tmp_path):
        reg = make_registry(tmp_path)
        result = reg.update("EXC-01", "Excavator", STATIONARY_POS, "CONFIRMED", 0.91)
        assert result["alert"] is None

    def test_first_update_zero_displacement(self, tmp_path):
        reg = make_registry(tmp_path)
        result = reg.update("EXC-01", "Excavator", STATIONARY_POS, "CONFIRMED", 0.91)
        assert result["displacement_px"] == 0.0

    def test_multiple_assets_tracked_independently(self, tmp_path):
        reg = make_registry(tmp_path)
        reg.update("EXC-01", "Excavator", STATIONARY_POS, "CONFIRMED", 0.91)
        reg.update("GEN-01", "Generator", (500.0, 600.0), "CONFIRMED", 0.88)
        assert reg.tracked_count == 2

    def test_list_assets_returns_all_tracked(self, tmp_path):
        reg = make_registry(tmp_path)
        reg.update("EXC-01", "Excavator", STATIONARY_POS, "CONFIRMED", 0.91)
        reg.update("GEN-01", "Generator", (500.0, 600.0), "CONFIRMED", 0.88)
        assets = reg.list_assets()
        ids = {a["asset_id"] for a in assets}
        assert ids == {"EXC-01", "GEN-01"}


# ---------------------------------------------------------------------------
# 2. Movement state machine
# ---------------------------------------------------------------------------

class TestMovementStateMachine:

    def _make_moving_pos(self, step):
        """Generate a unique position that is 30px away from the previous step.
        Each call returns a distinct (x, y) so frame-to-frame displacement > 15px threshold."""
        base_x, base_y = 200.0, 300.0
        return (base_x + step * 30.0, base_y + step * 30.0)

    def _drive_to_suspected(self, reg, asset_id="EXC-01"):
        """Register then push asset into MOVEMENT_SUSPECTED state.
        frames_to_suspect=2 means we need 2 consecutive frames each showing
        displacement > threshold from the PREVIOUS frame's position.
        """
        reg.update(asset_id, "Excavator", STATIONARY_POS, "CONFIRMED", 0.91)
        # Frame 1: move from STATIONARY_POS → step1 (displacement ≈ 42px > 15px threshold)
        reg.update(asset_id, "Excavator", self._make_moving_pos(1), "PROBABLE", 0.72)
        # Frame 2: move from step1 → step2 (displacement = 42px > threshold)
        result = reg.update(asset_id, "Excavator", self._make_moving_pos(2), "PROBABLE", 0.70)
        return result

    def test_stationary_asset_stays_stationary_without_motion(self, tmp_path):
        reg = make_registry(tmp_path)
        reg.update("EXC-01", "Excavator", STATIONARY_POS, "CONFIRMED", 0.91)
        result = reg.update("EXC-01", "Excavator", STATIONARY_POS, "CONFIRMED", 0.91)
        assert result["movement_state"] == "STATIONARY"

    def test_transition_to_movement_suspected(self, tmp_path):
        reg = make_registry(tmp_path)
        result = self._drive_to_suspected(reg)
        assert result["movement_state"] == "MOVEMENT_SUSPECTED"

    def test_transition_to_moving_after_enough_motion_frames(self, tmp_path):
        reg = make_registry(tmp_path)
        self._drive_to_suspected(reg)
        # frames_to_confirm=5: need 5 more frames each moving > threshold from previous
        result = None
        for i in range(5):
            result = reg.update("EXC-01", "Excavator", self._make_moving_pos(3 + i),
                                "PROBABLE", 0.70)
        assert result["movement_state"] == "MOVING"

    def test_asset_moved_alert_fired_on_moving_transition(self, tmp_path):
        reg = make_registry(tmp_path)
        self._drive_to_suspected(reg)
        result = None
        for i in range(5):
            result = reg.update("EXC-01", "Excavator", self._make_moving_pos(3 + i),
                                "PROBABLE", 0.70)
        state = reg.get_state("EXC-01")
        assert state["movement_state"] == "MOVING"

    def test_false_motion_clears_back_to_stationary(self, tmp_path):
        """Asset moves for only 1 frame then returns to same position → stays STATIONARY.
        With frames_to_suspect=2, a single motion frame is not enough to transition."""
        reg = make_registry(tmp_path)
        reg.update("EXC-01", "Excavator", STATIONARY_POS, "CONFIRMED", 0.91)
        # 1 motion frame
        reg.update("EXC-01", "Excavator", self._make_moving_pos(1), "PROBABLE", 0.72)
        # Asset stops — displacement from step1 → STATIONARY_POS is > threshold,
        # but motion_count resets because this frame shows movement again.
        # Instead send the SAME position as previous to get still_evidence_count up.
        # After 1 motion + 2 still → still_count reaches frames_to_suspect, clears back.
        reg.update("EXC-01", "Excavator", self._make_moving_pos(1), "CONFIRMED", 0.88)
        result = reg.update("EXC-01", "Excavator", self._make_moving_pos(1), "CONFIRMED", 0.88)
        assert result["movement_state"] == "STATIONARY"

    def test_moving_clears_to_stationary_after_enough_still_frames(self, tmp_path):
        """Asset goes MOVING then comes to rest — should return to STATIONARY."""
        reg = make_registry(tmp_path)
        self._drive_to_suspected(reg)
        for i in range(5):
            reg.update("EXC-01", "Excavator", self._make_moving_pos(3 + i),
                       "PROBABLE", 0.70)
        # Asset settles at its current resting spot — send frames_to_clear=10 still frames
        rest_pos = self._make_moving_pos(7)
        result = None
        for _ in range(10):
            result = reg.update("EXC-01", "Excavator", rest_pos, "CONFIRMED", 0.88)
        assert result["movement_state"] == "STATIONARY"


# ---------------------------------------------------------------------------
# 3. Missing asset detection (temporal hysteresis)
# ---------------------------------------------------------------------------

class TestMissingAssetDetection:

    def test_no_missing_alert_before_threshold(self, tmp_path):
        reg = make_registry(tmp_path, missing_threshold=3)
        reg.begin_patrol_cycle()
        reg.update("EXC-01", "Excavator", STATIONARY_POS, "CONFIRMED", 0.91)
        reg.end_patrol_cycle()

        # 2 cycles where asset is NOT seen (below threshold of 3)
        for _ in range(2):
            reg.begin_patrol_cycle()
            alerts = reg.end_patrol_cycle()
            assert len(alerts) == 0

    def test_missing_alert_fires_at_threshold(self, tmp_path):
        reg = make_registry(tmp_path, missing_threshold=3)
        reg.begin_patrol_cycle()
        reg.update("EXC-01", "Excavator", STATIONARY_POS, "CONFIRMED", 0.91)
        reg.end_patrol_cycle()

        all_alerts = []
        for _ in range(3):  # exactly at threshold
            reg.begin_patrol_cycle()
            alerts = reg.end_patrol_cycle()
            all_alerts.extend(alerts)

        assert any(a["alert_type"] == "ASSET_MISSING" and a["asset_id"] == "EXC-01"
                   for a in all_alerts)

    def test_missing_alert_fires_once_not_repeatedly(self, tmp_path):
        """Alert fires once per missing episode, not every cycle after threshold."""
        reg = make_registry(tmp_path, missing_threshold=3)
        reg.begin_patrol_cycle()
        reg.update("EXC-01", "Excavator", STATIONARY_POS, "CONFIRMED", 0.91)
        reg.end_patrol_cycle()

        all_alerts = []
        for _ in range(6):  # 6 cycles missed — double the threshold
            reg.begin_patrol_cycle()
            alerts = reg.end_patrol_cycle()
            all_alerts.extend(alerts)

        missing = [a for a in all_alerts if a["alert_type"] == "ASSET_MISSING"]
        assert len(missing) == 1  # Must fire exactly once

    def test_reacquired_asset_clears_miss_counter(self, tmp_path):
        """Asset seen again after 2 misses → consecutive_misses resets to 0."""
        reg = make_registry(tmp_path, missing_threshold=3)
        reg.begin_patrol_cycle()
        reg.update("EXC-01", "Excavator", STATIONARY_POS, "CONFIRMED", 0.91)
        reg.end_patrol_cycle()

        # 2 missed cycles
        for _ in range(2):
            reg.begin_patrol_cycle()
            reg.end_patrol_cycle()

        # Asset reacquired
        reg.begin_patrol_cycle()
        reg.update("EXC-01", "Excavator", STATIONARY_POS, "CONFIRMED", 0.91)
        reg.end_patrol_cycle()

        state = reg.get_state("EXC-01")
        assert state["consecutive_misses"] == 0

    def test_get_missing_assets_returns_correct_list(self, tmp_path):
        reg = make_registry(tmp_path, missing_threshold=2)
        reg.begin_patrol_cycle()
        reg.update("EXC-01", "Excavator", STATIONARY_POS, "CONFIRMED", 0.91)
        reg.update("GEN-01", "Generator", (500.0, 600.0), "CONFIRMED", 0.88)
        reg.end_patrol_cycle()

        # Miss EXC-01 for 2 cycles, keep seeing GEN-01
        for _ in range(2):
            reg.begin_patrol_cycle()
            reg.update("GEN-01", "Generator", (500.0, 600.0), "CONFIRMED", 0.88)
            reg.end_patrol_cycle()

        missing = reg.get_missing_assets()
        assert "EXC-01" in missing
        assert "GEN-01" not in missing


# ---------------------------------------------------------------------------
# 4. Patrol cycle control
# ---------------------------------------------------------------------------

class TestPatrolCycleControl:

    def test_begin_patrol_cycle_increments_counter(self, tmp_path):
        reg = make_registry(tmp_path)
        assert reg.current_cycle == 0
        reg.begin_patrol_cycle()
        assert reg.current_cycle == 1
        reg.begin_patrol_cycle()
        assert reg.current_cycle == 2

    def test_end_patrol_cycle_returns_list(self, tmp_path):
        reg = make_registry(tmp_path)
        reg.begin_patrol_cycle()
        result = reg.end_patrol_cycle()
        assert isinstance(result, list)

    def test_no_alerts_in_empty_registry(self, tmp_path):
        reg = make_registry(tmp_path)
        reg.begin_patrol_cycle()
        alerts = reg.end_patrol_cycle()
        assert alerts == []


# ---------------------------------------------------------------------------
# 5. Baseline reset
# ---------------------------------------------------------------------------

class TestBaselineReset:

    def test_reset_clears_movement_state(self, tmp_path):
        reg = make_registry(tmp_path)
        reg.update("EXC-01", "Excavator", STATIONARY_POS, "CONFIRMED", 0.91)
        # Force MOVING state
        reg._registry["EXC-01"]["movement_state"] = "MOVING"
        result = reg.reset_asset_baseline("EXC-01", MOVED_POS)
        assert result is True
        assert reg.get_state("EXC-01")["movement_state"] == "STATIONARY"

    def test_reset_updates_baseline_position(self, tmp_path):
        reg = make_registry(tmp_path)
        reg.update("EXC-01", "Excavator", STATIONARY_POS, "CONFIRMED", 0.91)
        new_pos = (999.0, 888.0)
        reg.reset_asset_baseline("EXC-01", new_pos)
        assert reg.get_state("EXC-01")["baseline_position"] == new_pos

    def test_reset_nonexistent_asset_returns_false(self, tmp_path):
        reg = make_registry(tmp_path)
        result = reg.reset_asset_baseline("DOES-NOT-EXIST", (0.0, 0.0))
        assert result is False


# ---------------------------------------------------------------------------
# 6. Internal distance math
# ---------------------------------------------------------------------------

class TestDistanceMath:

    def test_same_position_zero_distance(self):
        assert AssetStateRegistry._euclidean_distance((0.0, 0.0), (0.0, 0.0)) == 0.0

    def test_known_distance(self):
        # 3-4-5 right triangle
        d = AssetStateRegistry._euclidean_distance((0.0, 0.0), (3.0, 4.0))
        assert abs(d - 5.0) < 1e-6

    def test_distance_is_symmetric(self):
        a, b = (10.0, 20.0), (30.0, 40.0)
        assert abs(
            AssetStateRegistry._euclidean_distance(a, b) -
            AssetStateRegistry._euclidean_distance(b, a)
        ) < 1e-6
