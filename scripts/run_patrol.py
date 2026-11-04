"""
ASI Perception System — Autonomous Patrol & Re-ID Verification Runner
Phase 2: Live Autonomous Asset Tracking, Re-ID Matching & Evidence Capture

Runs the full perception pipeline autonomously on a test video:
  1. Auto-proposes container candidates on every frame.
  2. Extracts OSNet visual embeddings (512-D) from candidate crops.
  3. Queries the persistent ReferenceStore gallery using cosine similarity.
  4. Identifies assets (CONFIRMED / PROBABLE / UNKNOWN) with similarity scores.
  5. Updates AssetStateRegistry (STATIONARY / MOVEMENT_SUSPECTED / MOVING).
  6. Renders real-time HUD with bounding boxes, asset labels, match %, and patrol stats.
  7. Saves an annotated MP4 video to evidence/patrol_runs/.
"""

import os
import sys
import time
import argparse
from pathlib import Path
from datetime import datetime, timezone

import cv2
import numpy as np
from collections import defaultdict, deque

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
os.chdir(PROJECT_ROOT)
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.image_quality import ImageQualityChecker
from src.reid_engine import ReIDEngine
from src.reference_store import ReferenceStore
from src.asset_state_registry import AssetStateRegistry
from scripts.hitl_enrollment import ContainerProposer


class SpatialVoter:
    """
    Temporal voting buffer for Re-ID disambiguation.

    Each 'track' is a spatial region (bbox) that persists across frames via IoU matching.
    For each track we accumulate a rolling window of per-frame top-1 candidate votes
    (weighted by similarity score). The majority winner with enough votes and score
    consistency is returned as the definitive identity.

    This handles the case where OSNet margins are tiny (0.001–0.005) within the same
    color family — a container that truly is CONT-021 will vote for CONT-021 in
    most frames even when individual margins are small.
    """

    VOTE_WINDOW  = 12      # rolling window size (frames)
    MIN_VOTES    = 4       # minimum votes before voting decision takes over
    IOU_LINK     = 0.20    # IoU threshold to link a new bbox to an existing track
    LOCK_THRESH  = 0.50    # fraction of votes for majority winner to call CONFIRMED
    PROBABLE_THR = 0.35    # fraction of votes for PROBABLE
    MAX_IDLE     = 8       # frames without detection before a track is considered lost

    def __init__(self):
        # track_id → {"bbox": last bbox, "votes": deque of (asset_id, score), "color": str|None, "last_frame": int}
        self._tracks: dict = {}
        self._next_tid = 0

    # ------------------------------------------------------------------
    def update(
        self,
        bbox: tuple,
        raw_match: dict,
        color_family: str | None = None,
        frame_idx: int = 0
    ) -> dict:
        """
        Register a new per-frame match observation for the bbox region.

        Args:
            bbox:         (x1, y1, x2, y2) of the current detection.
            raw_match:    result dict from ReferenceStore.query().
            color_family: detected color family ("RED", "BLUE", etc.) — prevents
                          cross-color track merging.
            frame_idx:    current frame index for track lifecycle management.

        Returns:
            Enriched match dict with voted 'identity_status' and 'asset_id'.
        """
        # Periodic cleanup of dead tracks (> 30 frames inactive)
        if frame_idx % 20 == 0:
            dead = [t for t, tr in self._tracks.items() if frame_idx - tr["last_frame"] > 30]
            for t in dead:
                del self._tracks[t]

        tid = self._find_or_create_track(bbox, color_family, frame_idx)
        track = self._tracks[tid]

        # Record this frame's vote
        raw_id    = raw_match.get("asset_id") or "UNKNOWN"
        raw_score = raw_match.get("similarity_score", 0.0)
        track["votes"].append((raw_id, raw_score))
        track["bbox"] = bbox
        track["last_frame"] = frame_idx

        # Tally votes
        return self._tally(track, raw_match)

    # ------------------------------------------------------------------
    def _find_or_create_track(
        self,
        bbox: tuple,
        color_family: str | None = None,
        frame_idx: int = 0
    ) -> int:
        best_tid   = None
        best_iou   = 0.0

        for tid, track in self._tracks.items():
            # Don't link to stale tracks
            if (frame_idx - track["last_frame"]) > self.MAX_IDLE:
                continue
            # Don't link across different color families
            if color_family and track.get("color") and track["color"] != color_family:
                continue

            iou = self._iou(bbox, track["bbox"])
            if iou > best_iou:
                best_iou = iou
                best_tid = tid

        if best_iou >= self.IOU_LINK and best_tid is not None:
            if color_family and not self._tracks[best_tid].get("color"):
                self._tracks[best_tid]["color"] = color_family
            return best_tid

        # New track
        tid = self._next_tid
        self._next_tid += 1
        self._tracks[tid] = {
            "bbox":       bbox,
            "votes":      deque(maxlen=self.VOTE_WINDOW),
            "color":      color_family,
            "last_frame": frame_idx
        }
        return tid

    # ------------------------------------------------------------------
    def _tally(self, track: dict, raw_match: dict) -> dict:
        votes = list(track["votes"])
        n = len(votes)

        # Not enough votes yet — return raw match result (passthrough)
        if n < self.MIN_VOTES:
            return raw_match

        # Count per-ID votes and sum scores
        id_counts: dict = defaultdict(int)
        id_scores: dict = defaultdict(float)
        for vid, vscore in votes:
            id_counts[vid] += 1
            id_scores[vid] += vscore

        winner_id  = max(id_counts, key=id_counts.get)
        winner_cnt = id_counts[winner_id]
        frac       = winner_cnt / n
        avg_score  = id_scores[winner_id] / winner_cnt

        if winner_id == "UNKNOWN" or avg_score < 0.40:
            return {**raw_match, "identity_status": "UNKNOWN", "asset_id": None,
                    "voted_by": f"{winner_cnt}/{n}"}

        if frac >= self.LOCK_THRESH and avg_score >= 0.65:
            status = "CONFIRMED"
        elif frac >= self.PROBABLE_THR and avg_score >= 0.55:
            status = "PROBABLE"
        else:
            status = "AMBIGUOUS"

        return {
            **raw_match,
            "asset_id":         winner_id,
            "similarity_score": round(avg_score, 4),
            "identity_status":  status,
            "voted_by":         f"{winner_cnt}/{n}",
        }

    # ------------------------------------------------------------------
    @staticmethod
    def _iou(a: tuple, b: tuple) -> float:
        ix1 = max(a[0], b[0]); iy1 = max(a[1], b[1])
        ix2 = min(a[2], b[2]); iy2 = min(a[3], b[3])
        inter = max(0, ix2 - ix1) * max(0, iy2 - iy1)
        if inter == 0:
            return 0.0
        area_a = (a[2]-a[0]) * (a[3]-a[1])
        area_b = (b[2]-b[0]) * (b[3]-b[1])
        return inter / (area_a + area_b - inter)


class AutonomousPatrolRunner:
    """Autonomous patrol runner that validates Re-ID identification and tracking."""

    def __init__(self, video_path: str, output_path: str = None, display: bool = True, realtime: bool = True):
        self.video_path = Path(video_path)
        if not self.video_path.exists():
            raise FileNotFoundError(f"Video file not found: {self.video_path}")

        # Default output video path
        if output_path is None:
            out_dir = PROJECT_ROOT / "evidence" / "patrol_runs"
            out_dir.mkdir(parents=True, exist_ok=True)
            self.output_path = out_dir / f"patrol_verified_{datetime.now().strftime('%Y%m%d_%H%M%S')}.mp4"
        else:
            self.output_path = Path(output_path).resolve()
            self.output_path.parent.mkdir(parents=True, exist_ok=True)

        self.display = display
        self.realtime = realtime

        print("\n" + "=" * 65)
        print("  ASI PERCEPTION — AUTONOMOUS PATROL & RE-ID RUNNER")
        print("=" * 65)

        # Initialize perception modules
        self.quality_checker = ImageQualityChecker()
        self.reid_engine = ReIDEngine("config/reid_config.yaml")
        self.reference_store = ReferenceStore("config/reid_config.yaml")
        self.state_registry = AssetStateRegistry("config/movement_config.yaml")
        self.proposer = ContainerProposer()
        self.voter = SpatialVoter()   # temporal voting buffer for stable Re-ID

        # Initialize trained YOLO detector
        self.detector = None
        yolo_pt = PROJECT_ROOT / "models" / "detection" / "best.pt"
        if yolo_pt.exists():
            try:
                from ultralytics import YOLO
                self.detector = YOLO(str(yolo_pt))
                print(f"[Detector] Loaded fine-tuned YOLO from '{yolo_pt.relative_to(PROJECT_ROOT)}'")
            except Exception as e:
                print(f"[Detector] Could not load YOLO model: {e}")

        # Enrolled gallery info (extract list of asset ID strings)
        raw_assets = self.reference_store.list_assets()
        self.enrolled_assets = [item["asset_id"] for item in raw_assets]
        print(f"[Gallery] Stored Asset Fingerprints: {len(self.enrolled_assets)} unique assets")
        if self.enrolled_assets:
            preview_ids = sorted(self.enrolled_assets)[:10]
            print(f"[Gallery] Asset IDs: {', '.join(preview_ids)}...")

        # Open video capture
        self.cap = cv2.VideoCapture(str(self.video_path))
        if not self.cap.isOpened():
            raise RuntimeError(f"Could not open video stream: {self.video_path}")

        self.total_frames = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))
        self.native_fps = self.cap.get(cv2.CAP_PROP_FPS) or 10.0
        self.frame_w = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        self.frame_h = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

        # Setup video writer
        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        self.writer = cv2.VideoWriter(
            str(self.output_path),
            fourcc,
            self.native_fps,
            (self.frame_w, self.frame_h)
        )

        print(f"[Video Info] Input : {self.video_path.name} ({self.frame_w}x{self.frame_h} @ {self.native_fps:.1f} FPS, {self.total_frames} frames)")
        print(f"[Video Info] Output: {self.output_path.relative_to(PROJECT_ROOT)}")

        # Statistics
        self.stats = {
            "frames_processed": 0,
            "detections_total": 0,
            "confirmed_matches": 0,
            "probable_matches": 0,
            "ambiguous_matches": 0,
            "unknown_matches": 0,
            "matched_unique_assets": set(),
        }

        # Color palette for recognized assets
        self.color_confirmed = (0, 255, 0)     # Bright Green
        self.color_probable  = (0, 220, 255)   # Amber / Yellow
        self.color_unknown   = (150, 150, 150) # Grey

    def run(self):
        """Run the full autonomous patrol loop."""
        print("\n" + "=" * 65)
        print("  STARTING AUTONOMOUS PATROL RUN...")
        print("  Press [Q] or [ESC] in the display window to stop early.")
        print("=" * 65 + "\n")

        self.state_registry.begin_patrol_cycle()
        frame_idx = 0
        start_time = time.time()
        paused = False

        # Pacing delay: native fps interval (~100ms for 10fps), or 1ms if not realtime
        delay_ms = max(1, int(1000 / self.native_fps)) if self.realtime else 1

        if self.display:
            win_name = "ASI Autonomous Patrol — Live Re-ID & Spatial Tracking"
            cv2.namedWindow(win_name, cv2.WINDOW_NORMAL)
            cv2.resizeWindow(win_name, min(1280, self.frame_w), min(720, self.frame_h))
            print("  Controls:")
            print("    [SPACE] : Pause / Resume live playback")
            print("    [+]     : Speed up playback")
            print("    [-]     : Slow down playback")
            print("    [Q]/ESC : Exit patrol")

        while True:
            ret, frame = self.cap.read()
            if not ret:
                break

            frame_idx += 1
            display = frame.copy()

            # 1. Image Quality Check
            quality = self.quality_checker.check(frame)
            if quality["quality"] == "UNUSABLE":
                self._draw_status_bar(display, frame_idx, quality, active_dets=[])
                self.writer.write(display)
                continue

            # 2. Auto-propose container candidates (YOLO + heuristic fallback)
            candidates = self.detect_candidates(frame)
            frame_detections = []

            for cand in candidates:
                x1, y1, x2, y2, tag = cand
                crop = frame[y1:y2, x1:x2]
                if crop.size == 0 or crop.shape[0] < 30 or crop.shape[1] < 30:
                    continue

                self.stats["detections_total"] += 1

                # 3. Detect dominant color family
                color_family = self.detect_color(crop)

                # 4. Extract OSNet Re-ID embedding (512-D)
                embedding = self.reid_engine.extract_embedding(crop)
                if embedding is None:
                    continue

                # 5. Query reference store with color-consistency constraint
                raw_match = self.reference_store.query(embedding, color_filter=color_family)

                # 5b. Temporal voting — stabilise identity across frames
                match  = self.voter.update(
                    (x1, y1, x2, y2),
                    raw_match,
                    color_family=color_family,
                    frame_idx=frame_idx
                )
                status = match.get("identity_status", "UNKNOWN")
                best_id = match.get("asset_id") or "UNKNOWN"
                best_score = match.get("similarity_score", 0.0)

                # Track statistics
                if status == "CONFIRMED":
                    self.stats["confirmed_matches"] += 1
                    self.stats["matched_unique_assets"].add(best_id)
                elif status == "PROBABLE":
                    self.stats["probable_matches"] += 1
                    self.stats["matched_unique_assets"].add(best_id)
                elif status == "AMBIGUOUS":
                    self.stats["ambiguous_matches"] += 1
                    self.stats["matched_unique_assets"].add(best_id)
                else:
                    self.stats["unknown_matches"] += 1

                # 6. Update State Machine
                if best_id != "UNKNOWN" and status != "UNKNOWN":
                    center_pt = ((x1 + x2) / 2.0, (y1 + y2) / 2.0)
                    state_record = self.state_registry.update(
                        asset_id=best_id,
                        class_name="container",
                        position=center_pt,
                        identity_status=status,
                        similarity_score=best_score
                    )
                    movement_state = state_record.get("movement_state", "STATIONARY")
                else:
                    movement_state = "UNKNOWN"

                det_info = {
                    "bbox": (x1, y1, x2, y2),
                    "asset_id": best_id,
                    "status": status,
                    "score": best_score,
                    "color": color_family,
                    "state": movement_state,
                    "tag": tag,
                    "voted_by": match.get("voted_by", ""),
                }
                frame_detections.append(det_info)

                # 7. Render bounding box and label
                self._draw_asset_box(display, det_info)

            # 7. Render HUD overlay
            self._draw_status_bar(display, frame_idx, quality, frame_detections)

            # Write annotated frame
            self.writer.write(display)
            self.stats["frames_processed"] += 1

            if self.display:
                cv2.imshow(win_name, display)
                key = cv2.waitKey(delay_ms) & 0xFF
                if key in [ord("q"), ord("Q"), 27]:
                    print("\n[Patrol] Interrupted by user.")
                    break
                elif key == 32:  # SPACE
                    paused = not paused
                    while paused:
                        pause_display = display.copy()
                        cv2.rectangle(pause_display, (self.frame_w//2 - 160, self.frame_h//2 - 25),
                                      (self.frame_w//2 + 160, self.frame_h//2 + 25), (0, 0, 0), -1)
                        cv2.putText(pause_display, "PAUSED — Press SPACE to resume",
                                    (self.frame_w//2 - 150, self.frame_h//2 + 8),
                                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)
                        cv2.imshow(win_name, pause_display)
                        pk = cv2.waitKey(50) & 0xFF
                        if pk == 32:
                            paused = False
                            break
                        elif pk in [ord("q"), ord("Q"), 27]:
                            break
                    if key in [ord("q"), ord("Q"), 27]:
                        break
                elif key in [ord("+"), ord("=")]:
                    delay_ms = max(1, delay_ms - 20)
                elif key in [ord("-"), ord("_")]:
                    delay_ms = min(300, delay_ms + 20)

            if frame_idx % 100 == 0:
                elapsed = time.time() - start_time
                fps_actual = frame_idx / max(0.1, elapsed)
                matched_count = len(self.stats["matched_unique_assets"])
                print(f"  Frame {frame_idx:04d}/{self.total_frames} | {fps_actual:.1f} FPS | Active matches: {matched_count} assets")

        # Cleanup
        self.cap.release()
        self.writer.release()
        if self.display:
            cv2.destroyAllWindows()

        total_time = time.time() - start_time
        self._print_summary(total_time)

    def detect_candidates(self, frame: np.ndarray) -> list[tuple[int, int, int, int, str]]:
        """
        Propose container candidate bounding boxes using trained YOLOv8 detector
        with heuristic fallback for complete coverage.
        """
        h, w = frame.shape[:2]
        candidates = []

        # 1. Primary: Trained YOLO detector
        if self.detector is not None:
            try:
                res = self.detector.predict(frame, conf=0.25, imgsz=640, verbose=False)[0]
                for box in res.boxes:
                    xyxy = box.xyxy[0].cpu().numpy().astype(int)
                    conf = float(box.conf[0])
                    x1, y1 = max(0, int(xyxy[0])), max(0, int(xyxy[1]))
                    x2, y2 = min(w, int(xyxy[2])), min(h, int(xyxy[3]))
                    if (x2 - x1) > 40 and (y2 - y1) > 40:
                        candidates.append((x1, y1, x2, y2, f"YOLO ({conf:.2f})", (x2 - x1) * (y2 - y1)))
            except Exception:
                pass

        # 2. Secondary: Heuristic proposer fallback for any non-overlapping containers
        heur_cands = self.proposer.propose(frame)
        for hx1, hy1, hx2, hy2, htag in heur_cands:
            h_area = (hx2 - hx1) * (hy2 - hy1)
            # Check overlap with existing YOLO detections
            overlap = False
            for yx1, yy1, yx2, yy2, _, _ in candidates:
                ix1, iy1 = max(hx1, yx1), max(hy1, yy1)
                ix2, iy2 = min(hx2, yx2), min(hy2, yy2)
                inter = max(0, ix2 - ix1) * max(0, iy2 - iy1)
                min_a = min(h_area, (yx2 - yx1) * (yy2 - yy1))
                if min_a > 0 and (inter / float(min_a)) > 0.35:
                    overlap = True
                    break
            if not overlap:
                candidates.append((hx1, hy1, hx2, hy2, htag, h_area))

        return [(c[0], c[1], c[2], c[3], c[4]) for c in candidates]

    @staticmethod
    def detect_color(crop: np.ndarray) -> str | None:
        """Estimate the dominant container color family from HSV histogram."""
        hsv = cv2.cvtColor(crop, cv2.COLOR_BGR2HSV)
        sat = hsv[:, :, 1]
        val = hsv[:, :, 2]
        colored = (sat > 45) & (val > 40)
        if colored.sum() < 350:
            return None
        hues = hsv[colored, 0]
        counts, _ = np.histogram(hues, bins=[0, 15, 35, 85, 135, 180])
        red_cnt = counts[0] + counts[4]
        yellow_cnt = counts[1]
        green_cnt = counts[2]
        blue_cnt = counts[3]
        best_idx = int(np.argmax([red_cnt, yellow_cnt, green_cnt, blue_cnt]))
        return ["RED", "YELLOW", "GREEN", "BLUE"][best_idx]

    def _draw_asset_box(self, display: np.ndarray, det: dict):
        """Render polished bounding box, ID banner, match %, and state machine tag."""
        x1, y1, x2, y2 = det["bbox"]
        status = det["status"]
        asset_id = det["asset_id"]
        score_pct = int(det["score"] * 100)
        state = det["state"]
        c_fam = det.get("color")
        color_tag = f" {c_fam}" if c_fam else ""

        if status == "CONFIRMED":
            color = self.color_confirmed
            voted = det.get("voted_by", "")
            vote_str = f" v{voted}" if voted else ""
            label = f"{asset_id}{color_tag}{vote_str} [{score_pct}% CONFIRMED]"
        elif status == "PROBABLE":
            color = self.color_probable
            voted = det.get("voted_by", "")
            vote_str = f" v{voted}" if voted else ""
            label = f"{asset_id}{color_tag}{vote_str} [{score_pct}% PROBABLE]"
        elif status == "AMBIGUOUS":
            color = (0, 200, 255)
            label = f"{asset_id}{color_tag} [{score_pct}% AMBIGUOUS]"
        else:
            color = self.color_unknown
            label = f"UNKNOWN CONTAINER{color_tag} [{score_pct}%]"

        # Box outline
        cv2.rectangle(display, (x1, y1), (x2, y2), color, 2)

        # Label background
        font = cv2.FONT_HERSHEY_SIMPLEX
        font_scale = 0.55
        thickness = 1
        (lw, lh), _ = cv2.getTextSize(label, font, font_scale, thickness)

        bg_y1 = max(0, y1 - lh - 12)
        bg_y2 = y1
        cv2.rectangle(display, (x1, bg_y1), (x1 + lw + 16, bg_y2), (20, 20, 20), -1)
        cv2.rectangle(display, (x1, bg_y1), (x1 + lw + 16, bg_y2), color, 1)

        # Text
        cv2.putText(display, label, (x1 + 8, y1 - 6), font, font_scale, color, thickness, cv2.LINE_AA)

        # State badge at bottom of box
        state_badge = f"STATE: {state}"
        (sw, sh), _ = cv2.getTextSize(state_badge, font, 0.42, 1)
        cv2.rectangle(display, (x1, y2), (x1 + sw + 10, y2 + sh + 8), (20, 20, 20), -1)
        cv2.putText(display, state_badge, (x1 + 5, y2 + sh + 4), font, 0.42, (0, 255, 255), 1, cv2.LINE_AA)

    def _draw_status_bar(self, display: np.ndarray, frame_idx: int, quality: dict, active_dets: list):
        """Render top telemetry HUD and bottom audit status."""
        h, w = display.shape[:2]

        # Top bar
        cv2.rectangle(display, (0, 0), (w, 38), (15, 15, 15), -1)
        sec = frame_idx / self.native_fps

        # Mode
        cv2.putText(display, "[AUTONOMOUS PATROL]", (12, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (0, 255, 0), 2)

        # Telemetry
        time_str = f"Time: {sec:05.1f}s | Frame: {frame_idx}/{self.total_frames}"
        cv2.putText(display, time_str, (240, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (220, 220, 220), 1)

        # Matches
        matched_count = len(self.stats["matched_unique_assets"])
        match_str = f"Recognized Assets: {matched_count}/{len(self.enrolled_assets)}"
        cv2.putText(display, match_str, (560, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 0), 2)

        # Quality pill
        q_text = quality["quality"]
        q_col = (0, 255, 0) if q_text == "GOOD" else (0, 165, 255)
        cv2.putText(display, f"Cam: {q_text}", (w - 130, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.5, q_col, 1)

        # Bottom bar (Current frame active IDs)
        cv2.rectangle(display, (0, h - 30), (w, h), (15, 15, 15), -1)
        if active_dets:
            active_str = "Active Sights: " + " | ".join([f"{d['asset_id']} ({int(d['score']*100)}%)" for d in active_dets])
            cv2.putText(display, active_str, (15, h - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.48, (0, 255, 0), 1)
        else:
            cv2.putText(display, "Active Sights: Corridor scan...", (15, h - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.48, (160, 160, 160), 1)

    def _print_summary(self, total_time: float):
        """Print complete verification audit summary."""
        fps = self.stats["frames_processed"] / max(0.1, total_time)
        print("\n" + "=" * 65)
        print("  AUTONOMOUS PATROL VERIFICATION REPORT")
        print("=" * 65)
        print(f"  • Processed Frames      : {self.stats['frames_processed']} / {self.total_frames}")
        print(f"  • Total Time            : {total_time:.1f}s ({fps:.1f} FPS)")
        print(f"  • Total Container Dets  : {self.stats['detections_total']}")
        print(f"  • Confirmed Matches     : {self.stats['confirmed_matches']}")
        print(f"  • Probable Matches      : {self.stats['probable_matches']}")
        print(f"  • Ambiguous Matches     : {self.stats['ambiguous_matches']}")
        print(f"  • Unknown Detections    : {self.stats['unknown_matches']}")
        print(f"  • Unique Enrolled Assets: {len(self.enrolled_assets)}")
        print(f"  • Unique Assets Found   : {len(self.stats['matched_unique_assets'])}")
        if self.stats["matched_unique_assets"]:
            print(f"    Recognized IDs: {', '.join(sorted(self.stats['matched_unique_assets']))}")
        print(f"  • Verified Output Video : {self.output_path}")
        print("=" * 65 + "\n")


def main():
    parser = argparse.ArgumentParser(description="Autonomous Patrol & Re-ID Verification Runner")
    default_vid = r"C:\Users\GANGARI DHRUVAVEER\Downloads\WhatsApp Video 2026-10-30 at 7.55.50 PM.mp4"
    parser.add_argument("--video", "-v", default=default_vid, help="Path to test patrol video")
    parser.add_argument("--output", "-o", default=None, help="Path to save annotated video")
    parser.add_argument("--no-display", action="store_true", help="Run headless without OpenCV GUI window")
    parser.add_argument("--fast", "-f", action="store_true", help="Process at maximum GPU/CPU speed rather than real-time")
    args = parser.parse_args()

    runner = AutonomousPatrolRunner(
        video_path=args.video,
        output_path=args.output,
        display=not args.no_display,
        realtime=not args.fast
    )
    runner.run()


if __name__ == "__main__":
    main()
