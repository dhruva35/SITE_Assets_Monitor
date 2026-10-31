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


class AutonomousPatrolRunner:
    """Autonomous patrol runner that validates Re-ID identification and tracking."""

    def __init__(self, video_path: str, output_path: str = None, display: bool = True):
        self.video_path = Path(video_path)
        if not self.video_path.exists():
            raise FileNotFoundError(f"Video file not found: {self.video_path}")

        # Default output video path
        if output_path is None:
            out_dir = PROJECT_ROOT / "evidence" / "patrol_runs"
            out_dir.mkdir(parents=True, exist_ok=True)
            self.output_path = out_dir / f"patrol_verified_{datetime.now().strftime('%Y%m%d_%H%M%S')}.mp4"
        else:
            self.output_path = Path(output_path)
            self.output_path.parent.mkdir(parents=True, exist_ok=True)

        self.display = display

        print("\n" + "=" * 65)
        print("  ASI PERCEPTION — AUTONOMOUS PATROL & RE-ID RUNNER")
        print("=" * 65)

        # Initialize perception modules
        self.quality_checker = ImageQualityChecker()
        self.reid_engine = ReIDEngine("config/reid_config.yaml")
        self.reference_store = ReferenceStore("config/reid_config.yaml")
        self.state_registry = AssetStateRegistry("config/movement_config.yaml")
        self.proposer = ContainerProposer()

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

        if self.display:
            win_name = "ASI Autonomous Patrol — Live Re-ID & Spatial Tracking"
            cv2.namedWindow(win_name, cv2.WINDOW_NORMAL)
            cv2.resizeWindow(win_name, min(1280, self.frame_w), min(720, self.frame_h))

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

            # 2. Auto-propose container candidates
            candidates = self.proposer.propose(frame)
            frame_detections = []

            for cand in candidates:
                x1, y1, x2, y2, tag = cand
                crop = frame[y1:y2, x1:x2]
                if crop.size == 0 or crop.shape[0] < 30 or crop.shape[1] < 30:
                    continue

                self.stats["detections_total"] += 1

                # 3. Extract OSNet Re-ID embedding (512-D)
                embedding = self.reid_engine.extract_embedding(crop)
                if embedding is None:
                    continue

                # 4. Query reference store
                match = self.reference_store.query(embedding)
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

                # 5. Update State Machine
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
                    "state": movement_state,
                    "tag": tag
                }
                frame_detections.append(det_info)

                # 6. Render bounding box and label
                self._draw_asset_box(display, det_info)

            # 7. Render HUD overlay
            self._draw_status_bar(display, frame_idx, quality, frame_detections)

            # Write annotated frame
            self.writer.write(display)
            self.stats["frames_processed"] += 1

            if self.display:
                cv2.imshow(win_name, display)
                key = cv2.waitKey(1) & 0xFF
                if key in [ord("q"), ord("Q"), 27]:
                    print("\n[Patrol] Interrupted by user.")
                    break

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

    def _draw_asset_box(self, display: np.ndarray, det: dict):
        """Render polished bounding box, ID banner, match %, and state machine tag."""
        x1, y1, x2, y2 = det["bbox"]
        status = det["status"]
        asset_id = det["asset_id"]
        score_pct = int(det["score"] * 100)
        state = det["state"]

        if status == "CONFIRMED":
            color = self.color_confirmed
            label = f"{asset_id} [{score_pct}% CONFIRMED]"
        elif status == "PROBABLE":
            color = self.color_probable
            label = f"{asset_id} [{score_pct}% PROBABLE]"
        elif status == "AMBIGUOUS":
            color = (0, 200, 255)
            label = f"{asset_id} [{score_pct}% AMBIGUOUS]"
        else:
            color = self.color_unknown
            label = f"UNKNOWN [{score_pct}%]"

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
    args = parser.parse_args()

    runner = AutonomousPatrolRunner(
        video_path=args.video,
        output_path=args.output,
        display=not args.no_display
    )
    runner.run()


if __name__ == "__main__":
    main()
