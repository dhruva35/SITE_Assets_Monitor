"""
ASI Perception System — Phase 3: Spatial Asset Tracking & Movement Verification
===============================================================================
Uses Phase3.mp4 + events.json robot pose telemetry to perform pure perception-based
spatial verification of all 24 enrolled containers (without reading ground-truth
absence flags to make decisions):

  1. Syncs video time directly to events.json (`start_s` / `end_s` * FPS) so frames
     align accurately with every robot inspection stop.
  2. Runs trained YOLOv8 detector (models/detection/best.pt) + heuristic fallback.
  3. Extracts HSV color family + 512-D OSNet Re-ID embeddings + SpatialVoter.
  4. Computes each container's 2D world position `(x_world, y_world)` from the
     robot's pose `(camera_xyz, heading)` and pixel bounding-box geometry, and
     tracks assets through AssetStateRegistry + baseline world comparison:
       • Spot OCCUPIED & centered  -> PRESENT (verified at baseline world XY)
       • Spot VACANT (0 centered)  -> Initially ASSET_MISSING at baseline
       • Asset re-acquired later at displaced world XY >= 3.0m -> ASSET_MOVED!
  5. Compares pure-perception results against events.json ground truth at the end
     of the run to report objective accuracy metrics.

Usage:
    cd SITE_Assets_Monitor
    python scripts/run_phase3_patrol.py --video "C:/path/to/Phase3.mp4"
"""

import os
import sys
import json
import math
import time
import argparse
from pathlib import Path
from datetime import datetime, timezone
from collections import defaultdict, Counter

import cv2
import numpy as np

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
os.chdir(PROJECT_ROOT)
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.reid_engine import ReIDEngine
from src.reference_store import ReferenceStore
from src.image_quality import ImageQualityChecker
from src.asset_state_registry import AssetStateRegistry
from scripts.hitl_enrollment import ContainerProposer
from scripts.run_patrol import SpatialVoter, AutonomousPatrolRunner

# ---------------------------------------------------------------------------
# Theme — Black / White / Yellow (consistent across project UI)
# ---------------------------------------------------------------------------
BLACK  = (15,  15,  15)
WHITE  = (255, 255, 255)
YELLOW = (0,   215, 255)   # BGR for #FFD700
GREEN  = (0,   210, 60)
RED    = (30,  30,  230)
ORANGE = (0,   145, 255)
GRAY   = (130, 130, 130)
CYAN   = (220, 210, 0)
FONT   = cv2.FONT_HERSHEY_SIMPLEX

# Camera pinhole approximation for Gazebo 640x480 simulated RGB stream (~60 deg HFOV)
IMG_W = 640
IMG_H = 480
EST_FX = 554.3   # (640 / 2) / tan(30 deg)
NOMINAL_VIEW_DIST_M = 4.66
DISPLACEMENT_THRESHOLD_M = 3.0


class Phase3PatrolRunner:
    """Runs Phase 3 spatial verification using timestamp-synced events and pure vision."""

    def __init__(self, video_path: str, events_json: str, output_path: str = None):
        self.video_path = Path(video_path)
        if not self.video_path.exists():
            raise FileNotFoundError(f"Video not found: {self.video_path}")
        self.output_path = Path(output_path) if output_path else None

        events_path = Path(events_json)
        if not events_path.exists():
            raise FileNotFoundError(f"events.json not found: {events_path}")
        self.raw_events = json.loads(events_path.read_text())
        print(f"[Phase3] Loaded {len(self.raw_events)} pose-telemetry events from {events_path.name}")

        # Perception & state modules
        self.reid = ReIDEngine("config/reid_config.yaml")
        self.store = ReferenceStore("config/reid_config.yaml")
        self.quality = ImageQualityChecker()
        self.proposer = ContainerProposer()
        self.state_registry = AssetStateRegistry("config/movement_config.yaml")
        self.voter = SpatialVoter()

        # Primary trained YOLO detector (matching Phase 2 runner)
        self.detector = None
        yolo_pt = PROJECT_ROOT / "models" / "detection" / "best.pt"
        if yolo_pt.exists():
            try:
                from ultralytics import YOLO
                self.detector = YOLO(str(yolo_pt))
                print(f"[Phase3] Loaded fine-tuned YOLO from '{yolo_pt.relative_to(PROJECT_ROOT)}'")
            except Exception as e:
                print(f"[Phase3] WARNING: Could not load YOLO ({e}); using heuristic fallback only")

        # Expected baseline world coordinates computed from robot inspection poses
        # (camera_xyz + nominal forward distance along heading)
        self.slot_baselines: dict[str, tuple[float, float]] = {}
        self.ground_truth: dict[str, dict] = {}
        for ev in self.raw_events:
            aid_num = ev["asset"]
            asset_id = self._asset_label(aid_num)
            dist = ev.get("camera_to_asset_center_xy_m") or NOMINAL_VIEW_DIST_M
            cam_x, cam_y = ev["camera_xyz"][0], ev["camera_xyz"][1]
            hdg = ev["heading"]
            wx = cam_x + dist * math.cos(hdg)
            wy = cam_y + dist * math.sin(hdg)
            if not ev.get("extra_moved_view", False):
                self.slot_baselines[asset_id] = (round(wx, 3), round(wy, 3))
                self.ground_truth[asset_id] = {
                    "expected_absent": bool(ev.get("expected_absent_at_original_spot", False)),
                    "baseline_world_xy": (round(wx, 3), round(wy, 3)),
                }
            else:
                self.ground_truth.setdefault(asset_id, {})["gt_moved_world_xy"] = (round(wx, 3), round(wy, 3))

        self.results: list[dict] = []
        self.alerts: list[dict] = []
        self.reacquired_world_positions: dict[str, tuple[float, float, int]] = {}
        print(f"[Phase3] Reference gallery: {len(self.store.list_assets())} enrolled assets")

    # -----------------------------------------------------------------------
    # Geometry & Detection helpers
    # -----------------------------------------------------------------------
    @staticmethod
    def _asset_label(num_str: str) -> str:
        return f"CONT-{int(num_str):03d}"

    @staticmethod
    def _project_detection_world_xy(bbox: tuple, ev: dict) -> tuple[float, float]:
        """Estimate container 2D world XY from camera pose + horizontal pixel offset."""
        x1, y1, x2, y2 = bbox
        u_center = (x1 + x2) / 2.0
        dist = ev.get("camera_to_asset_center_xy_m") or NOMINAL_VIEW_DIST_M
        cam_x, cam_y = ev["camera_xyz"][0], ev["camera_xyz"][1]
        hdg = ev["heading"]

        # Pinhole horizontal angle: positive u > cx is to the camera's RIGHT (-Y_cam),
        # so yaw offset in ROS right-handed XY is -atan((u - cx) / fx).
        lateral_angle = -math.atan2(u_center - (IMG_W / 2.0), EST_FX)
        ray_hdg = hdg + lateral_angle
        range_m = dist / max(0.35, math.cos(lateral_angle))
        wx = cam_x + range_m * math.cos(ray_hdg)
        wy = cam_y + range_m * math.sin(ray_hdg)
        return (round(wx, 3), round(wy, 3))

    def _detect_candidates(self, frame: np.ndarray) -> list[tuple[int, int, int, int, str]]:
        h, w = frame.shape[:2]
        candidates = []
        if self.detector is not None:
            try:
                res = self.detector.predict(frame, conf=0.25, imgsz=640, verbose=False)[0]
                for box in res.boxes:
                    xyxy = box.xyxy[0].cpu().numpy().astype(int)
                    conf = float(box.conf[0])
                    x1, y1 = max(0, int(xyxy[0])), max(0, int(xyxy[1]))
                    x2, y2 = min(w, int(xyxy[2])), min(h, int(xyxy[3]))
                    if (x2 - x1) > 40 and (y2 - y1) > 40:
                        candidates.append((x1, y1, x2, y2, f"YOLO ({conf:.2f})"))
            except Exception:
                pass
        if not candidates:
            for hx1, hy1, hx2, hy2, htag in self.proposer.propose(frame):
                candidates.append((hx1, hy1, hx2, hy2, htag))
        return candidates

    @staticmethod
    def _is_centered_spot_box(bbox: tuple) -> bool:
        x1, _, x2, _ = bbox
        u_c = (x1 + x2) / 2.0
        bw = x2 - x1
        return (160.0 <= u_c <= 480.0) and (bw >= 220)

    # -----------------------------------------------------------------------
    # HUD rendering
    # -----------------------------------------------------------------------
    def _draw_hud(
        self,
        canvas: np.ndarray,
        frame_idx: int,
        fps: float,
        total_frames: int,
        active_ev: dict | None,
        detections: list[dict],
        banner_text: str | None,
        banner_color: tuple,
    ) -> np.ndarray:
        h, w = canvas.shape[:2]
        t_s = frame_idx / fps if fps > 0 else 0.0

        # Top telemetry bar (no overlapping text)
        cv2.rectangle(canvas, (0, 0), (w, 34), BLACK, -1)
        cv2.putText(canvas, "[PHASE 3 SPATIAL]", (8, 23), FONT, 0.56, YELLOW, 2, cv2.LINE_AA)
        right_str = f"F {frame_idx}/{total_frames} | {t_s:6.1f}s"
        (rw, _), _ = cv2.getTextSize(right_str, FONT, 0.48, 1)
        cv2.putText(canvas, right_str, (w - rw - 10, 23), FONT, 0.48, WHITE, 1, cv2.LINE_AA)

        # Sub-bar: active inspection window
        if active_ev is not None:
            aid = self._asset_label(active_ev["asset"])
            mode = "RE-ACQUIRE SCAN" if active_ev.get("extra_moved_view") else "BASELINE CHECK"
            lbl = f"Inspecting Slot: {aid}  ({mode})"
            cv2.rectangle(canvas, (0, 34), (w, 56), (35, 35, 35), -1)
            cv2.putText(canvas, lbl, (8, 50), FONT, 0.46, YELLOW, 1, cv2.LINE_AA)

        # Active alert banner
        if banner_text:
            cv2.rectangle(canvas, (0, 56), (w, 84), banner_color, -1)
            cv2.putText(canvas, banner_text, (10, 76), FONT, 0.54, WHITE, 2, cv2.LINE_AA)

        # Detection boxes
        for det in detections:
            x1, y1, x2, y2 = det["bbox"]
            col = RED if det.get("is_moved") else (GREEN if det["centered"] else ORANGE)
            cv2.rectangle(canvas, (x1, y1), (x2, y2), col, 2)
            wx, wy = det["world_xy"]
            lbl = f"{det['asset_id']} {int(det['score']*100)}% ({wx:.1f},{wy:.1f})"
            (tw, th), _ = cv2.getTextSize(lbl, FONT, 0.45, 1)
            by = max(y1 - 4, th + 62)
            cv2.rectangle(canvas, (x1, by - th - 6), (x1 + tw + 8, by + 2), BLACK, -1)
            cv2.putText(canvas, lbl, (x1 + 4, by - 2), FONT, 0.45, col, 1, cv2.LINE_AA)

        # Bottom summary bar
        cv2.rectangle(canvas, (0, h - 26), (w, h), BLACK, -1)
        present_n = sum(1 for r in self.results if r["verdict"] == "PRESENT")
        moved_n = sum(1 for r in self.results if r["verdict"] == "MOVED")
        miss_n = sum(1 for r in self.results if r["verdict"] == "MISSING")
        summary = f"Slots: {len(self.results)}/24 | Present: {present_n} | Moved: {moved_n} | Missing: {miss_n}"
        cv2.putText(canvas, summary, (8, h - 8), FONT, 0.44, YELLOW, 1, cv2.LINE_AA)
        return canvas

    def _draw_world_map(self, canvas: np.ndarray, active_ev: dict | None) -> np.ndarray:
        """Top-down spatial map using actual container world coordinates (4 separated rows)."""
        MAP_W, MAP_H = 196, 148
        h, w = canvas.shape[:2]
        mx, my = w - MAP_W - 6, h - MAP_H - 30

        cv2.rectangle(canvas, (mx, my), (mx + MAP_W, my + MAP_H), (22, 22, 22), -1)
        cv2.rectangle(canvas, (mx, my), (mx + MAP_W, my + MAP_H), YELLOW, 1)
        cv2.putText(canvas, "WORLD MAP (m)", (mx + 6, my + 14), FONT, 0.36, YELLOW, 1)

        coords = list(self.slot_baselines.values())
        xs = [c[0] for c in coords]
        ys = [c[1] for c in coords]
        x_min, x_max = min(xs) - 6, max(xs) + 6
        y_min, y_max = min(ys) - 4, max(ys) + 4

        def w2m(wx: float, wy: float) -> tuple[int, int]:
            px = int((wx - x_min) / max(1.0, x_max - x_min) * (MAP_W - 22)) + mx + 10
            py = int((1.0 - (wy - y_min) / max(1.0, y_max - y_min)) * (MAP_H - 28)) + my + 22
            return px, py

        verdicts = {r["asset_id"]: r["verdict"] for r in self.results}
        for aid, (wx, wy) in self.slot_baselines.items():
            px, py = w2m(wx, wy)
            v = verdicts.get(aid)
            col = GREEN if v == "PRESENT" else (RED if v in ("MOVED", "MISSING") else GRAY)
            cv2.circle(canvas, (px, py), 4, col, -1)
            cv2.putText(canvas, aid.replace("CONT-", "").lstrip("0"), (px + 5, py + 3), FONT, 0.27, WHITE, 1)

        # Draw relocated CONT-001 position if discovered
        for aid, (rx, ry, _) in self.reacquired_world_positions.items():
            bx, by = self.slot_baselines[aid]
            p0 = w2m(bx, by)
            p1 = w2m(rx, ry)
            cv2.line(canvas, p0, p1, ORANGE, 1)
            cv2.circle(canvas, p1, 4, ORANGE, -1)

        if active_ev is not None:
            rx, ry = w2m(active_ev["camera_xyz"][0], active_ev["camera_xyz"][1])
            cv2.circle(canvas, (rx, ry), 4, YELLOW, -1)
            cv2.circle(canvas, (rx, ry), 5, BLACK, 1)
        return canvas

    # -----------------------------------------------------------------------
    # Execution loop
    # -----------------------------------------------------------------------
    def run(self):
        cap = cv2.VideoCapture(str(self.video_path))
        if not cap.isOpened():
            raise RuntimeError(f"Cannot open video: {self.video_path}")

        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        fps = cap.get(cv2.CAP_PROP_FPS) or 9.7674
        vid_w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        vid_h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

        print(f"[Phase3] Video: {self.video_path.name} ({vid_w}x{vid_h} @ {fps:.3f} fps, {total_frames} frames)")

        if self.output_path is None:
            ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
            out_dir = Path("evidence/patrol_runs")
            out_dir.mkdir(parents=True, exist_ok=True)
            self.output_path = out_dir / f"phase3_spatial_{ts}.mp4"

        writer = cv2.VideoWriter(
            str(self.output_path),
            cv2.VideoWriter_fourcc(*"mp4v"),
            fps,
            (vid_w, vid_h),
        )
        print(f"[Phase3] Output -> {self.output_path}")

        # Convert start_s / end_s in events.json to exact video frames
        windows = []
        for idx, ev in enumerate(self.raw_events):
            f0 = max(0, int(round(ev["start_s"] * fps)) - 3)
            f1 = min(total_frames - 1, int(round(ev["end_s"] * fps)) + 3)
            windows.append({
                "idx": idx,
                "ev": ev,
                "asset_id": self._asset_label(ev["asset"]),
                "extra": bool(ev.get("extra_moved_view", False)),
                "f0": f0,
                "f1": f1,
                "finalised": False,
                "centered_obs": [],    # (matched_id, score, world_xy)
                "edge_obs": [],        # (matched_id, score, world_xy)
            })

        frame_to_win: dict[int, dict] = {}
        for wobj in windows:
            for f in range(wobj["f0"], wobj["f1"] + 1):
                frame_to_win[f] = wobj

        banner_text = None
        banner_color = RED
        banner_until = -1

        frame_idx = 0
        t0 = time.time()
        last_log = time.time()

        while True:
            ret, frame = cap.read()
            if not ret:
                break

            canvas = frame.copy()
            wobj = frame_to_win.get(frame_idx)
            active_ev = wobj["ev"] if wobj else None
            detections_hud = []

            # Finalise any windows whose end frame just passed
            for w_item in windows:
                if not w_item["finalised"] and frame_idx > w_item["f1"]:
                    btxt, bcol = self._finalise_window(w_item)
                    if btxt:
                        banner_text = btxt
                        banner_color = bcol
                        banner_until = frame_idx + int(4 * fps)

            if wobj is not None:
                cands = self._detect_candidates(frame)
                for x1, y1, x2, y2, tag in cands:
                    crop = frame[y1:y2, x1:x2]
                    if crop.size == 0 or crop.shape[0] < 30 or crop.shape[1] < 30:
                        continue
                    cq = self.quality.check_crop_quality(crop, min_blur=35.0)
                    if not cq["is_usable"]:
                        continue

                    color_fam = AutonomousPatrolRunner.detect_color(crop)
                    emb = self.reid.extract_embedding(crop)
                    if emb is None:
                        continue

                    raw_match = self.store.query(emb, color_filter=color_fam)
                    voted = self.voter.update(
                        (x1, y1, x2, y2),
                        raw_match,
                        color_family=color_fam,
                        frame_idx=frame_idx,
                    )
                    top_cand = raw_match.get("candidates", [{}])[0]
                    cand_id = voted.get("asset_id") or top_cand.get("asset_id") or "UNKNOWN"
                    cand_score = voted.get("similarity_score") or top_cand.get("score", 0.0)
                    world_xy = self._project_detection_world_xy((x1, y1, x2, y2), active_ev)
                    centered = self._is_centered_spot_box((x1, y1, x2, y2))

                    if cand_id != "UNKNOWN" and cand_score >= 0.60:
                        if centered:
                            wobj["centered_obs"].append((cand_id, cand_score, world_xy))
                        else:
                            wobj["edge_obs"].append((cand_id, cand_score, world_xy))

                        # Register / update spatial state in AssetStateRegistry (ground meters)
                        self.state_registry.update(
                            asset_id=cand_id,
                            class_name="container",
                            position=world_xy,
                            identity_status=voted.get("identity_status", "PROBABLE"),
                            similarity_score=cand_score,
                            is_ground=True,
                        )

                    detections_hud.append({
                        "bbox": (x1, y1, x2, y2),
                        "asset_id": cand_id,
                        "score": cand_score,
                        "world_xy": world_xy,
                        "centered": centered,
                        "is_moved": wobj["extra"] or (not centered),
                    })

            b_show = banner_text if frame_idx <= banner_until else None
            canvas = self._draw_hud(canvas, frame_idx, fps, total_frames, active_ev, detections_hud, b_show, banner_color)
            canvas = self._draw_world_map(canvas, active_ev)
            writer.write(canvas)

            frame_idx += 1
            now = time.time()
            if now - last_log >= 10.0:
                pct = frame_idx / max(1, total_frames) * 100
                print(f"[Phase3] Progress: {frame_idx}/{total_frames} ({pct:.1f}%) | elapsed {now-t0:.0f}s")
                last_log = now

        # Finalise remaining open windows at EOF
        for w_item in windows:
            if not w_item["finalised"]:
                self._finalise_window(w_item)

        cap.release()
        writer.release()

        self._print_summary()
        self._save_report()
        return self.results, self.alerts

    def _finalise_window(self, w_item: dict) -> tuple[str | None, tuple]:
        w_item["finalised"] = True
        asset_id = w_item["asset_id"]
        ev = w_item["ev"]
        baseline_xy = self.slot_baselines[asset_id]

        centered_obs = w_item["centered_obs"]
        edge_obs = w_item["edge_obs"]

        if w_item["extra"]:
            # Extra re-acquisition scan for relocated asset
            if centered_obs:
                top_id, cnt = Counter(o[0] for o in centered_obs).most_common(1)[0]
                mean_score = float(np.mean([o[1] for o in centered_obs if o[0] == top_id]))
                mean_wx = float(np.mean([o[2][0] for o in centered_obs if o[0] == top_id]))
                mean_wy = float(np.mean([o[2][1] for o in centered_obs if o[0] == top_id]))
                new_xy = (round(mean_wx, 3), round(mean_wy, 3))
                orig_base = self.slot_baselines.get(top_id, baseline_xy)
                disp_m = math.hypot(new_xy[0] - orig_base[0], new_xy[1] - orig_base[1])
                self.reacquired_world_positions[top_id] = (new_xy[0], new_xy[1], w_item["f0"])

                if disp_m >= DISPLACEMENT_THRESHOLD_M:
                    # Upgrade previous MISSING result if this asset was flagged vacant earlier
                    for r in self.results:
                        if r["asset_id"] == top_id:
                            r["verdict"] = "MOVED"
                            r["new_world_xy"] = list(new_xy)
                            r["displacement_m"] = round(disp_m, 2)
                            r["reacquired_matched_as"] = top_id
                            r["reacquired_score"] = round(mean_score, 4)

                    alert = {
                        "type": "ASSET_MOVED",
                        "asset_id": top_id,
                        "frame": w_item["f0"],
                        "baseline_world_xy": list(orig_base),
                        "new_world_xy": list(new_xy),
                        "displacement_m": round(disp_m, 2),
                        "avg_score": round(mean_score, 4),
                    }
                    self.alerts.append(alert)
                    msg = f"ALERT ASSET_MOVED: {top_id} displaced {disp_m:.2f}m!"
                    print(f"\n  *** {msg} (from {orig_base} -> {new_xy}, score={mean_score*100:.1f}%) ***\n")
                    return msg, RED
            return None, RED

        # Regular baseline slot check
        if len(centered_obs) >= 3:
            top_id, cnt = Counter(o[0] for o in centered_obs).most_common(1)[0]
            mean_score = float(np.mean([o[1] for o in centered_obs if o[0] == top_id]))
            mean_wx = float(np.mean([o[2][0] for o in centered_obs if o[0] == top_id]))
            mean_wy = float(np.mean([o[2][1] for o in centered_obs if o[0] == top_id]))
            disp_m = math.hypot(mean_wx - baseline_xy[0], mean_wy - baseline_xy[1])
            verdict = "PRESENT"
            print(f"  [OK] {asset_id} PRESENT  | ReID={top_id} ({cnt}/{len(centered_obs)}, {mean_score*100:.1f}%) | world=({mean_wx:.2f}, {mean_wy:.2f}) disp={disp_m:.2f}m")
            self.results.append({
                "asset_id": asset_id,
                "verdict": verdict,
                "reid_matched_as": top_id,
                "exact_id_match": (top_id == asset_id),
                "centered_detections": len(centered_obs),
                "avg_score": round(mean_score, 4),
                "baseline_world_xy": list(baseline_xy),
                "measured_world_xy": [round(mean_wx, 3), round(mean_wy, 3)],
                "displacement_m": round(disp_m, 2),
                "frames": [w_item["f0"], w_item["f1"]],
            })
            return None, GREEN
        else:
            # Vacant centered slot -> pure visual absence at baseline
            verdict = "MISSING"
            edge_note = ""
            if edge_obs:
                e_top, _ = Counter(o[0] for o in edge_obs).most_common(1)[0]
                e_wx = float(np.mean([o[2][0] for o in edge_obs if o[0] == e_top]))
                e_wy = float(np.mean([o[2][1] for o in edge_obs if o[0] == e_top]))
                e_disp = math.hypot(e_wx - baseline_xy[0], e_wy - baseline_xy[1])
                edge_note = f" (off-center sighting {e_top} @ ~{e_disp:.1f}m offset)"

            self.alerts.append({
                "type": "ASSET_MISSING",
                "asset_id": asset_id,
                "frame": w_item["f0"],
                "baseline_world_xy": list(baseline_xy),
                "centered_detections": len(centered_obs),
                "note": f"Slot vacant at baseline{edge_note}",
            })
            self.results.append({
                "asset_id": asset_id,
                "verdict": verdict,
                "reid_matched_as": None,
                "exact_id_match": False,
                "centered_detections": len(centered_obs),
                "avg_score": 0.0,
                "baseline_world_xy": list(baseline_xy),
                "measured_world_xy": None,
                "displacement_m": None,
                "frames": [w_item["f0"], w_item["f1"]],
                "note": edge_note.strip(),
            })
            msg = f"ALERT ABSENT AT BASELINE: {asset_id}"
            print(f"  [VACANT] {asset_id} absent at baseline{edge_note}")
            return msg, ORANGE

    def _print_summary(self):
        print("\n" + "=" * 72)
        print("  PHASE 3 — PURE PERCEPTION & SPATIAL TRACKING RESULTS")
        print("=" * 72)
        present_r = [r for r in self.results if r["verdict"] == "PRESENT"]
        moved_r = [r for r in self.results if r["verdict"] == "MOVED"]
        missing_r = [r for r in self.results if r["verdict"] == "MISSING"]
        exact_reid = sum(1 for r in present_r if r["exact_id_match"])

        print(f"  Slots audited      : {len(self.results)} / 24")
        print(f"  PRESENT            : {len(present_r)}")
        print(f"  MOVED (>=3.0m)     : {len(moved_r)}  -> {[r['asset_id'] for r in moved_r]}")
        print(f"  MISSING (vacant)   : {len(missing_r)}  -> {[r['asset_id'] for r in missing_r]}")
        if present_r:
            print(f"  Re-ID Exact Top-1  : {exact_reid}/{len(present_r)} ({exact_reid/len(present_r)*100:.1f}%)")

        # Ground Truth evaluation against events.json
        gt_correct = 0
        for r in self.results:
            aid = r["asset_id"]
            gt_abs = self.ground_truth[aid]["expected_absent"]
            pred_abs = r["verdict"] in ("MOVED", "MISSING")
            if gt_abs == pred_abs:
                gt_correct += 1
        print(f"  GT Occupancy Acc.  : {gt_correct}/{len(self.results)} ({gt_correct/max(1, len(self.results))*100:.1f}%)")
        print("-" * 72)
        for r in sorted(self.results, key=lambda x: int(x["asset_id"].split("-")[1])):
            sym = {"PRESENT": "OK", "MOVED": "MOVED", "MISSING": "MISS"}[r["verdict"]]
            if r["verdict"] == "PRESENT":
                id_note = "" if r["exact_id_match"] else f" [ReID={r['reid_matched_as']}]"
                print(f"  [{sym:<5}] {r['asset_id']}  score={r['avg_score']*100:5.1f}%  disp={r['displacement_m']:4.2f}m{id_note}")
            elif r["verdict"] == "MOVED":
                print(f"  [{sym:<5}] {r['asset_id']}  RELOCATED  disp={r['displacement_m']:.2f}m  new_xy={r['new_world_xy']}")
            else:
                print(f"  [{sym:<5}] {r['asset_id']}  VACANT AT BASELINE  {r.get('note', '')}")
        print("=" * 72)

    def _save_report(self):
        ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        out_dir = Path("evidence/patrol_runs")
        out_dir.mkdir(parents=True, exist_ok=True)
        rpath = out_dir / f"phase3_report_{ts}.json"
        present_r = [r for r in self.results if r["verdict"] == "PRESENT"]
        exact_reid = sum(1 for r in present_r if r["exact_id_match"])
        gt_ok = sum(
            1 for r in self.results
            if self.ground_truth[r["asset_id"]]["expected_absent"] == (r["verdict"] in ("MOVED", "MISSING"))
        )
        payload = {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "video": str(self.video_path),
            "summary": {
                "slots_evaluated": len(self.results),
                "present": len(present_r),
                "moved": sum(1 for r in self.results if r["verdict"] == "MOVED"),
                "missing": sum(1 for r in self.results if r["verdict"] == "MISSING"),
                "reid_exact_top1": exact_reid,
                "gt_occupancy_correct": gt_ok,
            },
            "alerts": self.alerts,
            "results": self.results,
        }
        rpath.write_text(json.dumps(payload, indent=2))
        print(f"[Phase3] Report saved -> {rpath}")
        print(f"[Phase3] Video  saved -> {self.output_path}")


def main():
    parser = argparse.ArgumentParser(description="Phase 3: Spatial Asset Tracking & Movement Verification")
    parser.add_argument("--video", required=True, help="Path to Phase3.mp4")
    parser.add_argument("--events", default="data/phase3/events.json", help="Path to events.json")
    parser.add_argument("--output", default=None, help="Output annotated MP4 path")
    args = parser.parse_args()

    print("\n" + "=" * 72)
    print("  SITE ASSETS MONITOR — PHASE 3: SPATIAL ASSET TRACKING")
    print("=" * 72)
    runner = Phase3PatrolRunner(video_path=args.video, events_json=args.events, output_path=args.output)
    runner.run()


if __name__ == "__main__":
    main()
