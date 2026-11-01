"""
ASI Perception System — Phase 3: ROS2 Bag Patrol & Spatial Movement Tracking Runner
Processes synchronized camera and localized pose bags to track assets in global map coordinates.

Pipeline:
  1. Synchronizes compressed camera images with robot odometry/poses (PoseStamped).
  2. Extracts Re-ID visual fingerprints (512-D) and identifies assets via ReferenceStore.
  3. Projects bounding box ground-contact points to 2D site coordinates (x_site, y_site) in meters.
  4. Tracks spatial movement using AssetStateRegistry (ego-motion compensated).
  5. Triggers ASSET_MOVED alerts when ground displacement >= 3.0m.
  6. Renders live HUD overlay with robot pose, site positions, match %, and state machine tags.
  7. Saves verified annotated MP4 video to evidence/patrol_runs/.
"""

import os
import sys
import math
import time
import bisect
import struct
import sqlite3
import argparse
from pathlib import Path
from datetime import datetime

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
from src.map_projection import MapProjector
from scripts.hitl_enrollment import ContainerProposer
from scripts.run_patrol import SpatialVoter


class ROS2BagPatrolRunner:
    """Processes ROS2 db3 bags for camera frames and localized poses."""

    def __init__(
        self,
        camera_bag: str,
        pose_bag: str,
        output_path: str = None,
        display: bool = False,
        max_frames: int = None
    ):
        self.camera_bag = Path(camera_bag)
        self.pose_bag = Path(pose_bag)
        self.display = display
        self.max_frames = max_frames

        if not self.camera_bag.exists():
            raise FileNotFoundError(f"Camera bag not found: {self.camera_bag}")
        if not self.pose_bag.exists():
            raise FileNotFoundError(f"Pose bag not found: {self.pose_bag}")

        out_dir = PROJECT_ROOT / "evidence" / "patrol_runs"
        out_dir.mkdir(parents=True, exist_ok=True)
        if output_path is None:
            self.output_path = out_dir / f"bag_patrol_verified_{datetime.now().strftime('%Y%m%d_%H%M%S')}.mp4"
        else:
            self.output_path = Path(output_path)
            self.output_path.parent.mkdir(parents=True, exist_ok=True)

        print("\n" + "=" * 65)
        print("  ASI PERCEPTION — PHASE 3: ROS2 BAG SPATIAL PATROL RUNNER")
        print("=" * 65)

        # Initialize perception modules
        self.quality_checker = ImageQualityChecker()
        self.reid_engine = ReIDEngine("config/reid_config.yaml")
        self.reference_store = ReferenceStore("config/reid_config.yaml")
        self.state_registry = AssetStateRegistry("config/movement_config.yaml")
        self.proposer = ContainerProposer()
        self.voter = SpatialVoter()

        # Enrolled gallery info
        raw_assets = self.reference_store.list_assets()
        self.enrolled_assets = [item["asset_id"] for item in raw_assets]
        print(f"[Gallery] Stored Asset Fingerprints: {len(self.enrolled_assets)} unique assets")

        # Load robot poses from pose_bag
        print("[Pose Bag] Loading localized poses from /benchmark/localized_pose...")
        self.pose_timestamps, self.poses = self._load_poses(self.pose_bag)
        print(f"[Pose Bag] Loaded {len(self.poses)} poses spanning {(self.pose_timestamps[-1] - self.pose_timestamps[0])/1e9:.1f}s.")

        # Inspect camera bag
        self.cam_conn = sqlite3.connect(str(self.camera_bag))
        self.cam_cursor = self.cam_conn.cursor()
        self.cam_cursor.execute("SELECT count(*) FROM messages WHERE topic_id = 1")
        self.total_frames = self.cam_cursor.fetchone()[0]
        if self.max_frames:
            self.total_frames = min(self.total_frames, self.max_frames)
        print(f"[Camera Bag] Total frames available: {self.total_frames}")

        # Setup video writer
        self.frame_w, self.frame_h = 640, 480
        self.fps = 5.0
        self.map_projector = MapProjector(image_w=self.frame_w, image_h=self.frame_h)

        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        self.writer = cv2.VideoWriter(
            str(self.output_path),
            fourcc,
            self.fps,
            (self.frame_w, self.frame_h)
        )
        print(f"[Video Output] Saving to: {self.output_path.relative_to(PROJECT_ROOT)}")

        # Statistics
        self.stats = {
            "frames_processed": 0,
            "detections_total": 0,
            "confirmed_matches": 0,
            "probable_matches": 0,
            "ambiguous_matches": 0,
            "unknown_matches": 0,
            "matched_unique_assets": set(),
            "movement_alerts": [],
        }

    def _load_poses(self, pose_bag_path: Path):
        """Extract timestamps and (x, y, yaw) from PoseStamped messages."""
        conn = sqlite3.connect(str(pose_bag_path))
        c = conn.cursor()
        c.execute("SELECT timestamp, data FROM messages WHERE topic_id = 1 ORDER BY timestamp")
        timestamps = []
        poses = []
        for ts, blob in c.fetchall():
            # CDR PoseStamped unpack: blob[20:76] contains x, y, z, qx, qy, qz, qw
            x, y, z, qx, qy, qz, qw = struct.unpack("<ddddddd", blob[20:76])
            # Yaw from quaternion
            yaw = math.atan2(2.0 * (qw * qz + qx * qy), 1.0 - 2.0 * (qy * qy + qz * qz))
            timestamps.append(ts)
            poses.append((x, y, yaw))
        conn.close()
        return timestamps, poses

    def _get_robot_pose(self, cam_ts: int) -> tuple:
        """Find the closest localized robot pose for a given camera timestamp."""
        if not self.pose_timestamps:
            return (0.0, 0.0, 0.0)
        idx = bisect.bisect_left(self.pose_timestamps, cam_ts)
        if idx == 0:
            return self.poses[0]
        if idx >= len(self.pose_timestamps):
            return self.poses[-1]
        before = self.pose_timestamps[idx - 1]
        after = self.pose_timestamps[idx]
        if (cam_ts - before) <= (after - cam_ts):
            return self.poses[idx - 1]
        return self.poses[idx]

    def run(self):
        """Execute the Phase 3 patrol tracking cycle."""
        print("\n" + "=" * 65)
        print("  STARTING PHASE 3 BAG REPLAY & SPATIAL PATROL...")
        print("=" * 65 + "\n")

        self.state_registry.begin_patrol_cycle()
        query = "SELECT timestamp, data FROM messages WHERE topic_id = 1 ORDER BY timestamp"
        if self.max_frames:
            query += f" LIMIT {self.max_frames}"

        self.cam_cursor.execute(query)

        frame_idx = 0
        start_time = time.time()

        if self.display:
            win_name = "ASI Phase 3 — Spatial Movement Tracking"
            cv2.namedWindow(win_name, cv2.WINDOW_NORMAL)
            cv2.resizeWindow(win_name, self.frame_w, self.frame_h)

        while True:
            row = self.cam_cursor.fetchone()
            if not row:
                break

            cam_ts, blob = row
            frame_idx += 1

            # Decode JPEG
            jpeg_start = blob.find(b"\xff\xd8\xff")
            if jpeg_start == -1:
                continue
            frame = cv2.imdecode(np.frombuffer(blob[jpeg_start:], dtype=np.uint8), cv2.IMREAD_COLOR)
            if frame is None:
                continue

            display = frame.copy()
            robot_x, robot_y, robot_yaw = self._get_robot_pose(cam_ts)

            # 1. Quality Check
            quality = self.quality_checker.check(frame)
            if quality["quality"] == "UNUSABLE":
                self._draw_status_bar(display, frame_idx, quality, (robot_x, robot_y, robot_yaw), [])
                self.writer.write(display)
                continue

            # 2. Object Proposal
            candidates = self.proposer.propose(frame)
            frame_detections = []

            for cand in candidates:
                x1, y1, x2, y2, tag = cand
                crop = frame[y1:y2, x1:x2]
                if crop.size == 0 or crop.shape[0] < 25 or crop.shape[1] < 25:
                    continue

                self.stats["detections_total"] += 1

                # 3. Detect Color & Extract Re-ID Embedding
                color_family = self.detect_color(crop)
                embedding = self.reid_engine.extract_embedding(crop)
                if embedding is None:
                    continue

                # 4. Query Gallery with Color Consistency Constraint & Temporal Voting
                raw_match = self.reference_store.query(embedding, color_filter=color_family)
                match = self.voter.update(
                    (x1, y1, x2, y2),
                    raw_match,
                    color_family=color_family,
                    frame_idx=frame_idx
                )
                status = match.get("identity_status", "UNKNOWN")
                best_id = match.get("asset_id") or "UNKNOWN"
                best_score = match.get("similarity_score", 0.0)

                # Stats
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

                # 5. Map Projection: Project ground contact point (bottom-center)
                u_ground = int((x1 + x2) / 2)
                v_ground = int(y2)
                site_pos = self.map_projector.pixel_to_ground(
                    (u_ground, v_ground),
                    (robot_x, robot_y, robot_yaw)
                )

                # 6. Update State Registry (in ground meters, ego-motion compensated!)
                movement_state = "UNKNOWN"
                if best_id != "UNKNOWN" and status != "UNKNOWN":
                    state_record = self.state_registry.update(
                        asset_id=best_id,
                        class_name="container",
                        position=site_pos,
                        identity_status=status,
                        similarity_score=best_score,
                        is_ground=True  # Ground coordinates in meters
                    )
                    movement_state = state_record.get("movement_state", "STATIONARY")
                    if state_record.get("alert"):
                        self.stats["movement_alerts"].append(state_record["alert"])

                det_info = {
                    "bbox": (x1, y1, x2, y2),
                    "asset_id": best_id,
                    "status": status,
                    "score": best_score,
                    "state": movement_state,
                    "site_pos": site_pos,
                }
                frame_detections.append(det_info)
                self._draw_asset_box(display, det_info)

            # 7. Render HUD
            self._draw_status_bar(display, frame_idx, quality, (robot_x, robot_y, robot_yaw), frame_detections)

            self.writer.write(display)
            self.stats["frames_processed"] += 1

            if self.display:
                cv2.imshow(win_name, display)
                key = cv2.waitKey(int(1000 / self.fps)) & 0xFF
                if key in [ord("q"), ord("Q"), 27]:
                    print("\n[Patrol] Interrupted by user.")
                    break
                elif key == 32:  # SPACE
                    paused = True
                    while paused:
                        pause_display = display.copy()
                        cv2.rectangle(pause_display, (self.frame_w//2 - 160, self.frame_h//2 - 25),
                                      (self.frame_w//2 + 160, self.frame_h//2 + 25), (0, 0, 0), -1)
                        cv2.putText(pause_display, "PAUSED — Press SPACE to resume",
                                    (self.frame_w//2 - 150, self.frame_h//2 + 8),
                                    cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 255, 255), 2)
                        cv2.imshow(win_name, pause_display)
                        pk = cv2.waitKey(50) & 0xFF
                        if pk == 32:
                            paused = False
                            break
                        elif pk in [ord("q"), ord("Q"), 27]:
                            break
                    if key in [ord("q"), ord("Q"), 27]:
                        break

            if frame_idx % 100 == 0:
                elapsed = time.time() - start_time
                fps_actual = frame_idx / max(0.1, elapsed)
                matched_cnt = len(self.stats["matched_unique_assets"])
                print(f"  Frame {frame_idx:04d}/{self.total_frames} | {fps_actual:.1f} FPS | Assets found: {matched_cnt} | Alerts: {len(self.stats['movement_alerts'])}")

        # Cleanup
        self.cam_conn.close()
        self.writer.release()
        if self.display:
            cv2.destroyAllWindows()

        total_time = time.time() - start_time
        self._print_summary(total_time)

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
        x1, y1, x2, y2 = det["bbox"]
        status = det["status"]
        asset_id = det["asset_id"]
        score_pct = int(det["score"] * 100)
        state = det["state"]
        sx, sy = det["site_pos"]

        if status == "CONFIRMED":
            color = (0, 255, 0)
            label = f"{asset_id} [{score_pct}% CONFIRMED]"
        elif status == "PROBABLE":
            color = (0, 220, 255)
            label = f"{asset_id} [{score_pct}% PROBABLE]"
        elif status == "AMBIGUOUS":
            color = (0, 200, 255)
            label = f"{asset_id} [{score_pct}% AMB]"
        else:
            color = (150, 150, 150)
            label = f"UNKNOWN CONTAINER [{score_pct}%]"

        # Box
        cv2.rectangle(display, (x1, y1), (x2, y2), color, 2)

        # Label Banner
        font = cv2.FONT_HERSHEY_SIMPLEX
        (lw, lh), _ = cv2.getTextSize(label, font, 0.45, 1)
        bg_y1 = max(0, y1 - lh - 8)
        cv2.rectangle(display, (x1, bg_y1), (x1 + lw + 10, y1), (20, 20, 20), -1)
        cv2.rectangle(display, (x1, bg_y1), (x1 + lw + 10, y1), color, 1)
        cv2.putText(display, label, (x1 + 5, y1 - 4), font, 0.45, color, 1, cv2.LINE_AA)

        # Ground Position & State badge at bottom
        pos_badge = f"{state} | ({sx:.1f}m, {sy:.1f}m)"
        (pw, ph), _ = cv2.getTextSize(pos_badge, font, 0.38, 1)
        cv2.rectangle(display, (x1, y2), (x1 + pw + 8, y2 + ph + 6), (20, 20, 20), -1)
        cv2.putText(display, pos_badge, (x1 + 4, y2 + ph + 3), font, 0.38, (0, 255, 255), 1, cv2.LINE_AA)

    def _draw_status_bar(self, display: np.ndarray, frame_idx: int, quality: dict, pose: tuple, active_dets: list):
        h, w = display.shape[:2]
        rx, ry, ryaw = pose

        # Top bar
        cv2.rectangle(display, (0, 0), (w, 32), (15, 15, 15), -1)
        cv2.putText(display, "[PHASE 3 SPATIAL PATROL]", (10, 22), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 255, 0), 2)

        # Robot Pose Telemetry
        pose_str = f"Robot: ({rx:.1f}m, {ry:.1f}m, {math.degrees(ryaw):.0f}deg)"
        cv2.putText(display, pose_str, (215, 22), cv2.FONT_HERSHEY_SIMPLEX, 0.42, (200, 200, 255), 1)

        # Assets Count
        matched_cnt = len(self.stats["matched_unique_assets"])
        stat_str = f"Assets: {matched_cnt}/{len(self.enrolled_assets)}"
        cv2.putText(display, stat_str, (430, 22), cv2.FONT_HERSHEY_SIMPLEX, 0.48, (255, 255, 0), 1)

        # Quality
        q_col = (0, 255, 0) if quality["quality"] == "GOOD" else (0, 165, 255)
        cv2.putText(display, quality["quality"], (w - 75, 22), cv2.FONT_HERSHEY_SIMPLEX, 0.42, q_col, 1)

        # Bottom bar
        cv2.rectangle(display, (0, h - 24), (w, h), (15, 15, 15), -1)
        if active_dets:
            act_text = "Sight: " + " | ".join([f"{d['asset_id']} @ ({d['site_pos'][0]:.1f},{d['site_pos'][1]:.1f}m)" for d in active_dets[:3]])
            cv2.putText(display, act_text, (10, h - 7), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 255, 0), 1)
        else:
            cv2.putText(display, "Scanning site perimeter...", (10, h - 7), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (160, 160, 160), 1)

    def _print_summary(self, total_time: float):
        fps = self.stats["frames_processed"] / max(0.1, total_time)
        print("\n" + "=" * 65)
        print("  PHASE 3 ROS2 BAG SPATIAL PATROL REPORT")
        print("=" * 65)
        print(f"  • Processed Frames      : {self.stats['frames_processed']} / {self.total_frames}")
        print(f"  • Total Time            : {total_time:.1f}s ({fps:.1f} FPS)")
        print(f"  • Total Detections      : {self.stats['detections_total']}")
        print(f"  • Confirmed Matches     : {self.stats['confirmed_matches']}")
        print(f"  • Probable Matches      : {self.stats['probable_matches']}")
        print(f"  • Ambiguous Matches     : {self.stats['ambiguous_matches']}")
        print(f"  • Unknown Detections    : {self.stats['unknown_matches']}")
        print(f"  • Unique Assets Found   : {len(self.stats['matched_unique_assets'])} / {len(self.enrolled_assets)}")
        if self.stats["matched_unique_assets"]:
            print(f"    Recognized IDs: {', '.join(sorted(self.stats['matched_unique_assets']))}")
        print(f"  • Movement Alerts (>=3m): {len(self.stats['movement_alerts'])}")
        for alert in self.stats["movement_alerts"]:
            print(f"    [ALERT] {alert['asset_id']} moved {alert.get('baseline_displacement', 0.0):.2f}m")
        print(f"  • Verified Output Video : {self.output_path}")
        print("=" * 65 + "\n")


def main():
    parser = argparse.ArgumentParser(description="Phase 3: ROS2 Bag Spatial Patrol Runner")
    default_cam = r"c:\Users\GANGARI DHRUVAVEER\Downloads\prozect\camera_bag\camera_bag\camera_bag_0.db3"
    default_pose = r"c:\Users\GANGARI DHRUVAVEER\Downloads\prozect\pose_bag\pose_bag\pose_bag_0.db3"
    parser.add_argument("--camera", "-c", default=default_cam, help="Path to camera_bag_0.db3")
    parser.add_argument("--pose", "-p", default=default_pose, help="Path to pose_bag_0.db3")
    parser.add_argument("--output", "-o", default=None, help="Output MP4 path")
    parser.add_argument("--frames", "-n", type=int, default=None, help="Max frames to process (optional)")
    parser.add_argument("--display", action="store_true", help="Display OpenCV window")
    args = parser.parse_args()

    runner = ROS2BagPatrolRunner(
        camera_bag=args.camera,
        pose_bag=args.pose,
        output_path=args.output,
        display=args.display,
        max_frames=args.frames
    )
    runner.run()


if __name__ == "__main__":
    main()

