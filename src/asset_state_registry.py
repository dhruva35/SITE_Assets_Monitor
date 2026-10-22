"""
ASI Perception System — Asset State Registry
Spec: PER-STATE-001 → 006

Tracks the real-time operational state of each known asset across patrol cycles.
Bridges the Re-ID layer (who is this?) and the alerting layer (has it moved or gone missing?).

State machine per asset:
    STATIONARY → MOVEMENT_SUSPECTED → MOVING → STATIONARY
                                              ↘ UNCERTAIN

Missing detection logic uses temporal hysteresis from movement_config.yaml
to avoid false "ASSET_MISSING" alerts caused by temporary occlusion.
"""

import yaml
from datetime import datetime, timezone
from pathlib import Path


class AssetStateRegistry:
    """
    Maintains real-time operational state for every known tracked asset.

    Each asset entry holds:
      - movement_state:      Current kinematic state (STATIONARY / SUSPECTED / MOVING / UNCERTAIN)
      - last_seen_cycle:     Patrol cycle index when this asset was last confirmed
      - last_position:       (x, y) tuple — site coordinate of last confirmed sighting
      - consecutive_misses:  How many consecutive patrol cycles this asset was absent
      - alert_flags:         Active unacknowledged alerts for this asset

    The registry does NOT interact with the camera or models directly.
    It receives structured results from the Re-ID and map projection layers.
    """

    # Valid movement states (mirrors movement_config.yaml states list)
    STATE_STATIONARY = "STATIONARY"
    STATE_SUSPECTED   = "MOVEMENT_SUSPECTED"
    STATE_MOVING      = "MOVING"
    STATE_UNCERTAIN   = "UNCERTAIN"

    def __init__(self, config_path: str = "config/movement_config.yaml"):
        with open(config_path, "r") as f:
            cfg = yaml.safe_load(f)

        # Hysteresis thresholds (frames/cycles before state transitions)
        self.frames_to_suspect  = cfg.get("frames_to_suspect",  2)
        self.frames_to_confirm  = cfg.get("frames_to_confirm",  5)
        self.frames_to_clear    = cfg.get("frames_to_clear",   10)

        # Position change threshold in pixels (used if map projection unavailable)
        self.pos_threshold_px = cfg.get("position_change_threshold_px", 15)

        # How many consecutive patrol misses before ASSET_MISSING alert fires
        self.missing_threshold = cfg.get("missing_alert_threshold", 3)

        # Internal state store: {asset_id: state_dict}
        self._registry: dict = {}

        # Current patrol cycle counter (incremented by caller each patrol sweep)
        self._current_cycle: int = 0

        print("[AssetStateRegistry] Initialized. Ready to track assets.")

    # ------------------------------------------------------------------
    # Patrol Cycle Control
    # ------------------------------------------------------------------

    def begin_patrol_cycle(self):
        """
        Call this at the START of each robot patrol sweep.
        Increments the internal cycle counter.
        After processing all detections in a sweep, call end_patrol_cycle().
        """
        self._current_cycle += 1

    def end_patrol_cycle(self) -> list:
        """
        Call this at the END of each patrol sweep (after all frame detections processed).
        Checks for assets that were NOT seen this cycle and increments their miss counters.

        Returns:
            List of alert dicts for assets that exceeded the missing threshold.
        """
        alerts = []
        for asset_id, state in self._registry.items():
            if state["last_seen_cycle"] < self._current_cycle:
                state["consecutive_misses"] += 1
                if state["consecutive_misses"] >= self.missing_threshold:
                    # Only fire alert once per missing episode (not every cycle after)
                    if not state["alert_flags"].get("missing_alerted"):
                        alert = self._make_alert("ASSET_MISSING", asset_id, state)
                        alerts.append(alert)
                        state["alert_flags"]["missing_alerted"] = True
                        print(f"[AssetStateRegistry] ALERT: {asset_id} MISSING for "
                              f"{state['consecutive_misses']} consecutive patrol cycles.")
        return alerts

    # ------------------------------------------------------------------
    # Core Update
    # ------------------------------------------------------------------

    def update(
        self,
        asset_id: str,
        class_name: str,
        position: tuple,
        identity_status: str,
        similarity_score: float = 0.0
    ) -> dict:
        """
        Register a detection observation for an asset in the current patrol cycle.

        Args:
            asset_id:         Asset identifier (e.g., "EXC-01"). Must match ReferenceStore ID.
            class_name:       Asset class label (e.g., "Excavator").
            position:         (x, y) tuple. Site map coordinates from MapProjector,
                              or pixel bbox center if map projection unavailable.
            identity_status:  One of "CONFIRMED" / "PROBABLE" / "AMBIGUOUS" / "UNKNOWN"
                              from ReferenceStore.query().
            similarity_score: ReID cosine similarity score (0.0–1.0).

        Returns:
            State update result dict:
            {
                "asset_id":         str,
                "movement_state":   str,
                "alert":            dict | None  (ASSET_MOVED alert, or None)
                "displacement_px":  float,
                "consecutive_misses": int
            }
        """
        now = datetime.now(timezone.utc)

        if asset_id not in self._registry:
            # First sighting — register with baseline position
            self._registry[asset_id] = {
                "class_name":           class_name,
                "movement_state":       self.STATE_STATIONARY,
                "last_seen_cycle":      self._current_cycle,
                "last_seen_time":       now.isoformat(),
                "last_position":        position,
                "baseline_position":    position,  # The "home" position from HITL
                "motion_evidence_count": 0,        # Consecutive frames with motion
                "still_evidence_count": 0,         # Consecutive frames without motion
                "consecutive_misses":   0,
                "alert_flags":          {},
                "observation_count":    1,
                "last_identity_status": identity_status,
                "last_similarity":      similarity_score,
            }
            print(f"[AssetStateRegistry] Registered new asset: {asset_id} ({class_name}) "
                  f"at position {position}.")
            return {
                "asset_id":           asset_id,
                "movement_state":     self.STATE_STATIONARY,
                "alert":              None,
                "displacement_px":    0.0,
                "consecutive_misses": 0
            }

        # Existing asset — update state
        state = self._registry[asset_id]
        prev_position  = state["last_position"]
        prev_mv_state  = state["movement_state"]

        # Compute displacements BEFORE updating last_position
        displacement          = self._euclidean_distance(position, prev_position)
        baseline_displacement = self._euclidean_distance(position, state["baseline_position"])

        # Update metadata
        state["last_seen_cycle"]      = self._current_cycle
        state["last_seen_time"]       = now.isoformat()
        state["last_position"]        = position   # updated for next call
        state["consecutive_misses"]   = 0
        state["last_identity_status"] = identity_status
        state["last_similarity"]      = similarity_score
        state["observation_count"]   += 1

        # Clear missing alert flag if asset is back
        if state["alert_flags"].get("missing_alerted"):
            state["alert_flags"]["missing_alerted"] = False
            print(f"[AssetStateRegistry] {asset_id} reacquired after missing episode.")

        # --- Movement State Machine ---
        motion_detected = displacement > self.pos_threshold_px
        alert = None

        if motion_detected:
            state["motion_evidence_count"] += 1
            state["still_evidence_count"]   = 0
        else:
            state["still_evidence_count"]  += 1
            state["motion_evidence_count"]  = 0

        # State transitions
        new_mv_state = prev_mv_state

        if prev_mv_state == self.STATE_STATIONARY:
            if state["motion_evidence_count"] >= self.frames_to_suspect:
                new_mv_state = self.STATE_SUSPECTED

        elif prev_mv_state == self.STATE_SUSPECTED:
            if state["motion_evidence_count"] >= self.frames_to_confirm:
                new_mv_state = self.STATE_MOVING
                # Fire ASSET_MOVED alert
                alert = self._make_alert("ASSET_MOVED", asset_id, state,
                                         extra={"baseline_displacement": baseline_displacement,
                                                "displacement_px": displacement})
                print(f"[AssetStateRegistry] ALERT: {asset_id} MOVED. "
                      f"Baseline displacement: {baseline_displacement:.1f}px.")
            elif state["still_evidence_count"] >= self.frames_to_suspect:
                # Didn't sustain motion — false alarm, revert to STATIONARY
                new_mv_state = self.STATE_STATIONARY

        elif prev_mv_state == self.STATE_MOVING:
            if state["still_evidence_count"] >= self.frames_to_clear:
                new_mv_state = self.STATE_STATIONARY
                # Update baseline position to new resting location
                state["baseline_position"] = position
                print(f"[AssetStateRegistry] {asset_id} settled at new position {position}. "
                      f"Baseline updated.")

        state["movement_state"] = new_mv_state

        return {
            "asset_id":           asset_id,
            "movement_state":     new_mv_state,
            "alert":              alert,
            "displacement_px":    round(displacement, 2),
            "consecutive_misses": 0
        }

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------

    def get_state(self, asset_id: str) -> dict | None:
        """Return the full state dict for an asset, or None if not registered."""
        return self._registry.get(asset_id)

    def list_assets(self) -> list:
        """Return a summary list of all tracked assets and their current states."""
        return [
            {
                "asset_id":         aid,
                "class_name":       s["class_name"],
                "movement_state":   s["movement_state"],
                "last_seen_cycle":  s["last_seen_cycle"],
                "consecutive_misses": s["consecutive_misses"],
                "last_position":    s["last_position"],
            }
            for aid, s in self._registry.items()
        ]

    def get_missing_assets(self) -> list:
        """Return list of asset_ids that are currently flagged as missing."""
        return [
            aid for aid, s in self._registry.items()
            if s["consecutive_misses"] >= self.missing_threshold
        ]

    def reset_asset_baseline(self, asset_id: str, new_position: tuple) -> bool:
        """
        Manually reset an asset's baseline position (e.g., after an approved relocation).
        Returns True if the asset existed.
        """
        if asset_id not in self._registry:
            return False
        self._registry[asset_id]["baseline_position"] = new_position
        self._registry[asset_id]["movement_state"]    = self.STATE_STATIONARY
        self._registry[asset_id]["motion_evidence_count"] = 0
        self._registry[asset_id]["still_evidence_count"]  = 0
        print(f"[AssetStateRegistry] Baseline reset for {asset_id} → {new_position}.")
        return True

    @property
    def current_cycle(self) -> int:
        """Current patrol cycle index."""
        return self._current_cycle

    @property
    def tracked_count(self) -> int:
        """Number of assets currently being tracked."""
        return len(self._registry)

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _euclidean_distance(pos_a: tuple, pos_b: tuple) -> float:
        """Euclidean distance between two (x, y) positions."""
        return float(((pos_a[0] - pos_b[0]) ** 2 + (pos_a[1] - pos_b[1]) ** 2) ** 0.5)

    @staticmethod
    def _make_alert(alert_type: str, asset_id: str, state: dict, extra: dict = None) -> dict:
        """Construct a structured alert dict."""
        return {
            "alert_type":     alert_type,       # "ASSET_MOVED" | "ASSET_MISSING"
            "asset_id":       asset_id,
            "class_name":     state["class_name"],
            "timestamp":      datetime.now(timezone.utc).isoformat(),
            "last_position":  state["last_position"],
            "movement_state": state["movement_state"],
            **(extra or {})
        }
