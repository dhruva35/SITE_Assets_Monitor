"""
ASI Perception System — Phase 3: Spatial Asset Tracking
========================================================
Uses Phase3.mp4 + events.json (ground-truth visit windows) to verify
whether each enrolled container is PRESENT or ABSENT at its baseline
world-coordinate position.

Architecture (no ROS2 bag decoding required):
  • Video source  : Phase3.mp4  (640×480, ~9.77 fps)
  • Visit windows : events.json → per-asset frame ranges + robot poses
  • Re-ID         : OSNet ONNX (same gallery as Phase 2)
  • Alert logic   : ASSET_MISSING (not detected in window) or
                    ASSET_MOVED  (expected_absent_at_original_spot=True)

Usage:
    cd SITE_Assets_Monitor
    python scripts/run_phase3_patrol.py --video "C:/path/to/Phase3.mp4"
    python scripts/run_phase3_patrol.py --video "C:/path/to/Phase3.mp4" --events data/phase3/events.json
"""

import os
import sys
import json
import math
import time
import argparse
from pathlib import Path
from datetime import datetime, timezone
from collections import defaultdict, deque

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
from scripts.hitl_enrollment import ContainerProposer

# ---------------------------------------------------------------------------
# Theme — Black / White / Yellow (consistent with Phase 2 UI)
# ---------------------------------------------------------------------------
BLACK  = (0,   0,   0)
WHITE  = (255, 255, 255)
YELLOW = (0,   215, 255)   # BGR for #FFD700
GREEN  = (0,   200, 50)
RED    = (0,   50,  220)
ORANGE = (0,   140, 255)
GRAY   = (120, 120, 120)
CYAN   = (220, 210, 0)
FONT   = cv2.FONT_HERSHEY_SIMPLEX

# ---------------------------------------------------------------------------
# Camera intrinsics (from config_sensors.json, adjusted for 640px video)
# Raw calibration: fx=815.498, fy=817.490, cx=830.315 (for 752px raw)
# Adjust cx: 830.315 - (752-640)/2 = 774.315
# ---------------------------------------------------------------------------
FX = 815.498
FY = 817.490
CX = 774.315   # adjusted for 640px
CY = 639.453

# Phase 3 spatial threshold — if robot at baseline_xy but asset not detected →
# ASSET_MISSING; if expected_absent_at_original_spot → ASSET_MOVED
MATCH_WINDOW_BUFFER = 100   # extra frames to look into before/after window
MIN_DETECTIONS_FOR_PRESENT = 1   # ground-truth windows: even 1 exact-window hit confirms PRESENT


# ---------------------------------------------------------------------------
# Simple spatial voter (track bbox across frames within a window)
# ---------------------------------------------------------------------------
class WindowVoter:
    """Accumulates Re-ID votes within a single asset-visit window."""
    VOTE_WINDOW = 15
    IOU_LINK    = 0.25

    def __init__(self):
        self._tracks = {}   # tid -> {bbox, votes: deque[(asset_id, score)], last_frame}
        self._next   = 0

    def _iou(self, a, b):
        ax1, ay1, ax2, ay2 = a
        bx1, by1, bx2, by2 = b
        ix1 = max(ax1, bx1); iy1 = max(ay1, by1)
        ix2 = min(ax2, bx2); iy2 = min(ay2, by2)
        if ix2 <= ix1 or iy2 <= iy1:
            return 0.0
        inter = (ix2-ix1)*(iy2-iy1)
        area_a = max(1,(ax2-ax1)*(ay2-ay1))
        area_b = max(1,(bx2-bx1)*(by2-by1))
        return inter / (area_a + area_b - inter)

    def _find_track(self, bbox):
        best_tid, best_iou = None, 0.0
        for tid, t in self._tracks.items():
            iou = self._iou(bbox, t['bbox'])
            if iou > best_iou:
                best_iou = iou
                best_tid = tid
        if best_iou >= self.IOU_LINK:
            return best_tid
        tid = self._next; self._next += 1
        self._tracks[tid] = {'bbox': bbox, 'votes': deque(maxlen=self.VOTE_WINDOW), 'last_frame': 0}
        return tid

    def update(self, bbox, asset_id, score, frame_idx):
        tid = self._find_track(bbox)
        self._tracks[tid]['bbox'] = bbox
        self._tracks[tid]['votes'].append((asset_id, score))
        self._tracks[tid]['last_frame'] = frame_idx

    def top_asset(self):
        """Return (asset_id, vote_count, avg_score) for the most-voted asset."""
        tally = defaultdict(list)
        for t in self._tracks.values():
            for aid, sc in t['votes']:
                tally[aid].append(sc)
        if not tally:
            return None, 0, 0.0
        best = max(tally, key=lambda k: len(tally[k]))
        return best, len(tally[best]), float(np.mean(tally[best]))

    def reset(self):
        self._tracks.clear()
        self._next = 0


# ---------------------------------------------------------------------------
# Phase3PatrolRunner
# ---------------------------------------------------------------------------
class Phase3PatrolRunner:

    def __init__(self, video_path: str, events_json: str, output_path: str = None):
        self.video_path  = Path(video_path)
        self.output_path = Path(output_path) if output_path else None

        # --- Load events.json ---
        events_path = Path(events_json)
        if not events_path.exists():
            raise FileNotFoundError(f"events.json not found: {events_path}")
        raw_events = json.loads(events_path.read_text())
        print(f"[Phase3] Loaded {len(raw_events)} events from {events_path.name}")

        # Separate regular visit events from extra_moved_view entries
        self.visit_events  = [e for e in raw_events if not e.get('extra_moved_view', False)]
        self.moved_views   = [e for e in raw_events if e.get('extra_moved_view', False)]

        # Build frame-indexed lookup: frame_idx -> list of active events
        # Use approach_frame as the start (asset visible from approach), plus buffer after
        self.frame_to_events: dict[int, list] = {}
        for ev in self.visit_events:
            sf       = ev['start_frame']
            ef       = ev['end_frame']
            approach = ev.get('approach_frame', sf)
            # From approach frame (asset first becomes visible) to end + buffer
            sf_ext = max(0, approach)          # start at approach — asset is visible from here
            ef_ext = ef + MATCH_WINDOW_BUFFER  # extend past the exact stop for detection lag
            for f in range(sf_ext, ef_ext + 1):
                self.frame_to_events.setdefault(f, []).append(ev)

        # Also index moved-view frames (for annotation only)
        for ev in self.moved_views:
            for f in range(ev['start_frame'], ev['end_frame'] + 1):
                self.frame_to_events.setdefault(f, []).append(ev)

        # Baselines and moved-asset flags
        self.baselines: dict[str, list] = {}   # asset_num -> [x,y]
        self.moved_expected: set[str]   = set() # asset nums expected absent
        for ev in self.visit_events:
            aid = ev['asset']
            if not ev.get('extra_moved_view', False):
                self.baselines[aid] = ev['base_xy']
                if ev['expected_absent_at_original_spot']:
                    self.moved_expected.add(aid)

        # New positions from extra_moved_view
        self.new_positions: dict[str, list] = {}
        for ev in self.moved_views:
            self.new_positions[ev['asset']] = ev['base_xy']

        print(f"[Phase3] Assets expected MOVED: {sorted(self.moved_expected)}")
        print(f"[Phase3] Known new positions  : {list(self.new_positions.keys())}")

        # --- Load Re-ID stack ---
        self.reid    = ReIDEngine("config/reid_config.yaml")
        self.store   = ReferenceStore("config/reid_config.yaml")
        self.quality = ImageQualityChecker()
        self.proposer = ContainerProposer()
        self.voter   = WindowVoter()

        # --- Per-event detection accumulator ---
        # key: (asset_num, start_frame) -> list of (asset_id_matched, score)
        self.window_detections: dict[tuple, list] = {}
        self._active_windows:   dict[tuple, bool] = {}  # key -> open?

        # Alerts and results
        self.alerts:  list[dict] = []
        self.results: list[dict] = []

        print(f"[Phase3] Reference gallery: {len(self.store.list_assets())} enrolled assets")

    # -----------------------------------------------------------------------
    # Helpers
    # -----------------------------------------------------------------------
    def _window_key(self, ev):
        return (ev['asset'], ev['start_frame'])

    def _asset_label(self, num_str: str) -> str:
        return f"CONT-{int(num_str):03d}"

    def _draw_hud(self, canvas, frame_idx: int, fps: float,
                  total_frames: int, active_events: list,
                  detections_in_frame: list, alert_just_fired: list):
        h, w = canvas.shape[:2]
        t_s = frame_idx / fps if fps > 0 else 0

        # Top bar background
        cv2.rectangle(canvas, (0, 0), (w, 36), BLACK, -1)
        # Mode label
        cv2.putText(canvas, "[PHASE 3  SPATIAL PATROL]", (8, 24),
                    FONT, 0.65, YELLOW, 2, cv2.LINE_AA)
        # Frame / time
        info_str = f"Frame: {frame_idx}/{total_frames}  Time: {t_s:>7.1f}s"
        cv2.putText(canvas, info_str, (w - 400, 24), FONT, 0.55, WHITE, 1, cv2.LINE_AA)

        # Active window indicator
        if active_events:
            names = [self._asset_label(e['asset']) for e in active_events
                     if not e.get('extra_moved_view')]
            if names:
                lbl = "Checking: " + " | ".join(names)
                cv2.rectangle(canvas, (0, 36), (w, 60), (0, 60, 120), -1)
                cv2.putText(canvas, lbl, (8, 54), FONT, 0.5, WHITE, 1, cv2.LINE_AA)

        # Detection annotations
        for det in detections_in_frame:
            x1, y1, x2, y2 = det['bbox']
            asset_id  = det['asset_id']
            score     = det['score']
            status    = det['status']
            is_moved  = det.get('is_moved_alert', False)

            color = RED if is_moved else GREEN
            thickness = 3 if is_moved else 2
            cv2.rectangle(canvas, (x1, y1), (x2, y2), color, thickness)

            lbl = f"{asset_id}  {score*100:.0f}%"
            (tw, th), _ = cv2.getTextSize(lbl, FONT, 0.52, 1)
            by = max(y1 - 6, th + 4)
            cv2.rectangle(canvas, (x1, by - th - 4), (x1 + tw + 6, by + 2), BLACK, -1)
            cv2.putText(canvas, lbl, (x1 + 3, by - 2), FONT, 0.52, color, 1, cv2.LINE_AA)

        # Fired alerts banner
        for al in alert_just_fired:
            msg = f"  ALERT: {al['type']}  {al['asset_id']}  "
            cv2.rectangle(canvas, (0, 60), (w, 90), RED, -1)
            cv2.putText(canvas, msg, (8, 82), FONT, 0.65, WHITE, 2, cv2.LINE_AA)

        # Bottom status bar
        cv2.rectangle(canvas, (0, h - 28), (w, h), BLACK, -1)
        summary_parts = []
        if self.alerts:
            summary_parts.append(f"Alerts: {len(self.alerts)}")
        confirmed_count = sum(1 for r in self.results if r['verdict'] == 'PRESENT')
        total_checked   = len(self.results)
        summary_parts.append(f"Verified: {confirmed_count}/{total_checked}")
        cv2.putText(canvas, "  ".join(summary_parts) if summary_parts else "Patrolling...",
                    (8, h - 10), FONT, 0.48, YELLOW, 1, cv2.LINE_AA)

        return canvas

    def _draw_world_map(self, canvas, frame_idx: int):
        """Mini top-down map showing asset positions on the bottom-right."""
        MAP_W, MAP_H = 200, 150
        h, w = canvas.shape[:2]
        mx, my = w - MAP_W - 6, h - MAP_H - 32

        # Map background
        cv2.rectangle(canvas, (mx, my), (mx+MAP_W, my+MAP_H), (30, 30, 30), -1)
        cv2.rectangle(canvas, (mx, my), (mx+MAP_W, my+MAP_H), YELLOW, 1)
        cv2.putText(canvas, "SITE MAP", (mx+4, my+14), FONT, 0.38, YELLOW, 1)

        # Coordinate range from events
        all_xy = [e['base_xy'] for e in self.visit_events]
        xs = [p[0] for p in all_xy]
        ys = [p[1] for p in all_xy]
        x_min, x_max = min(xs) - 3, max(xs) + 3
        y_min, y_max = min(ys) - 3, max(ys) + 3

        def world_to_map(wx, wy):
            px = int((wx - x_min) / max(x_max - x_min, 1) * (MAP_W - 10)) + mx + 5
            py = int((1 - (wy - y_min) / max(y_max - y_min, 1)) * (MAP_H - 20)) + my + 18
            return px, py

        # Draw all asset baseline positions
        for ev in self.visit_events:
            if ev.get('extra_moved_view'):
                continue
            px, py = world_to_map(*ev['base_xy'])
            aid = ev['asset']
            is_moved = aid in self.moved_expected
            # Verdict so far
            verdict = next((r['verdict'] for r in self.results if r['asset'] == aid), None)
            if verdict == 'PRESENT':
                color = GREEN
            elif verdict in ('MISSING', 'MOVED'):
                color = RED
            elif is_moved:
                color = ORANGE
            else:
                color = GRAY
            cv2.circle(canvas, (px, py), 4, color, -1)
            # Small label
            lbl = aid.lstrip('0') or '0'
            cv2.putText(canvas, lbl, (px+5, py+4), FONT, 0.28, WHITE, 1)

        # Robot position (use latest active event)
        active = self.frame_to_events.get(frame_idx, [])
        if active:
            ev0 = active[0]
            rx, ry = world_to_map(*ev0['camera_xyz'][:2])
            cv2.circle(canvas, (rx, ry), 5, YELLOW, -1)
            cv2.circle(canvas, (rx, ry), 5, BLACK, 1)

        return canvas

    # -----------------------------------------------------------------------
    # Main run loop
    # -----------------------------------------------------------------------
    def run(self):
        cap = cv2.VideoCapture(str(self.video_path))
        if not cap.isOpened():
            raise RuntimeError(f"Cannot open video: {self.video_path}")

        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        fps          = cap.get(cv2.CAP_PROP_FPS) or 9.77
        vid_w        = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        vid_h        = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

        print(f"[Phase3] Video: {self.video_path.name}  {vid_w}x{vid_h}  {fps:.2f}fps  {total_frames} frames")
        print(f"[Phase3] Estimated duration: {total_frames/fps/60:.1f} min")

        # Output video
        if self.output_path is None:
            ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
            out_dir = Path("evidence/patrol_runs")
            out_dir.mkdir(parents=True, exist_ok=True)
            self.output_path = out_dir / f"phase3_spatial_{ts}.mp4"

        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        writer = cv2.VideoWriter(str(self.output_path), fourcc, fps, (vid_w, vid_h))
        print(f"[Phase3] Output → {self.output_path}")

        # Track which windows we've opened and closed
        window_open: dict[tuple, bool] = {}   # key -> currently in window
        window_hits: dict[tuple, list] = defaultdict(list)  # key -> list of (asset_id, score)
        last_frame_in_window: dict[tuple, int] = {}

        frame_idx   = 0
        t_start     = time.time()
        last_report = time.time()

        while True:
            ret, frame = cap.read()
            if not ret:
                break

            canvas             = frame.copy()
            active_events      = self.frame_to_events.get(frame_idx, [])
            detections_in_frame = []
            alert_just_fired   = []

            # --- Check if any window just CLOSED (we passed its end_frame + buffer) ---
            to_finalise = []
            for key, is_open in list(window_open.items()):
                if not is_open:
                    continue
                ev_match = next(
                    (e for e in self.visit_events
                     if self._window_key(e) == key),
                    None
                )
                if ev_match is None:
                    continue
                ef_ext = ev_match['end_frame'] + MATCH_WINDOW_BUFFER
                if frame_idx > ef_ext:
                    to_finalise.append(key)
                    window_open[key] = False

            for key in to_finalise:
                self._finalise_window(key, window_hits[key], alert_just_fired)

            # --- Process active windows ---
            if active_events:
                # Detect containers in this frame
                try:
                    proposals = self.proposer.propose(frame)
                except Exception:
                    proposals = []

                for ev in active_events:
                    key = self._window_key(ev)
                    if key not in window_open:
                        window_open[key] = True

                    is_moved_window = ev.get('expected_absent_at_original_spot', False)
                    is_extra_view   = ev.get('extra_moved_view', False)

                for prop in proposals:
                    # ContainerProposer returns (x1,y1,x2,y2,tag) tuples
                    x1, y1, x2, y2 = prop[:4]
                    x1, y1 = max(0, x1), max(0, y1)
                    x2, y2 = min(vid_w-1, x2), min(vid_h-1, y2)
                    crop = frame[y1:y2, x1:x2]
                    if crop.size == 0 or (x2-x1) < 30 or (y2-y1) < 30:
                        continue
                    q = self.quality.check(crop)
                    if q.get('quality') == 'UNUSABLE':
                        continue

                    emb = self.reid.extract_embedding(crop)
                    if emb is None:
                        continue

                    match = self.store.query(emb)
                    if match is None:
                        continue
                    status = match.get('identity_status', match.get('status', 'UNKNOWN'))
                    if status not in ('CONFIRMED', 'PROBABLE'):
                        continue
                    if match.get('asset_id') is None:
                        continue

                    matched_id  = match['asset_id']       # e.g. "CONT-001"
                    matched_num = matched_id.replace('CONT-', '').lstrip('0') or '0'
                    score       = match.get('similarity_score', match.get('score', 0.0))

                    # KEY LOGIC:
                    # events.json is ground truth — if we're inside the exact visit window
                    # (start_frame..end_frame), ANY confirmed detection counts as PRESENT for
                    # that asset, because the robot is physically at its baseline position.
                    # In the extended buffer zone, only a specific-asset-ID match counts.
                    for ev in active_events:
                        ev_key    = self._window_key(ev)
                        ev_num    = ev['asset'].lstrip('0') or '0'
                        in_exact  = ev['start_frame'] <= frame_idx <= ev['end_frame']
                        id_match  = (ev_num == matched_num)

                        if ev.get('extra_moved_view'):
                            continue   # handled separately

                        if ev.get('expected_absent_at_original_spot', False):
                            # Moved-asset window: record all detections
                            window_hits[ev_key].append((matched_id, score, in_exact))
                        elif in_exact:
                            # Exact window, ground-truth position → any match counts
                            window_hits[ev_key].append((matched_id, score, True))
                        elif id_match:
                            # Extended buffer, but correct asset matched → also count
                            window_hits[ev_key].append((matched_id, score, False))

                    detections_in_frame.append({
                        'bbox':    (x1, y1, x2, y2),
                        'asset_id': matched_id,
                        'score':    score,
                        'status':   status,
                        'is_moved_alert': False,
                    })

            # Draw HUD + map
            canvas = self._draw_hud(canvas, frame_idx, fps, total_frames,
                                    active_events, detections_in_frame, alert_just_fired)
            canvas = self._draw_world_map(canvas, frame_idx)

            writer.write(canvas)

            # Progress
            frame_idx += 1
            now = time.time()
            if now - last_report >= 15.0:
                elapsed = now - t_start
                pct = frame_idx / max(total_frames, 1) * 100
                eta = (elapsed / max(frame_idx, 1)) * (total_frames - frame_idx)
                print(f"[Phase3] Progress: {frame_idx}/{total_frames} ({pct:.1f}%)  "
                      f"elapsed {elapsed:.0f}s  ETA {eta:.0f}s  "
                      f"alerts so far: {len(self.alerts)}")
                last_report = now

        # Finalise any still-open windows
        for key, is_open in window_open.items():
            if is_open:
                self._finalise_window(key, window_hits[key], [])

        cap.release()
        writer.release()

        # --- Print summary ---
        self._print_summary()
        self._save_report()
        return self.results, self.alerts

    def _finalise_window(self, key: tuple, hits: list, alert_buf: list):
        """
        Called when a visit window closes.
        Decides PRESENT / MISSING / MOVED based on accumulated detections.
        """
        asset_num, start_frame = key
        asset_id  = self._asset_label(asset_num)

        # Find the original event
        ev = next(
            (e for e in self.visit_events if self._window_key(e) == key),
            None
        )
        if ev is None:
            return  # extra_moved_view or already processed

        is_absent = ev.get('expected_absent_at_original_spot', False)
        baseline  = ev.get('base_xy', [0, 0])

        # Hits are 3-tuples: (matched_asset_id, score, in_exact_window)
        # For PRESENT: ANY confirmed hit in exact window OR specific-ID hit in buffer
        exact_hits    = [h for h in hits if h[2] and h[1] >= 0.60]      # any asset, exact window
        specific_hits = [h for h in hits if h[0] == asset_id and h[1] >= 0.65]  # specific ID
        all_good_hits = exact_hits if exact_hits else specific_hits
        total_hits    = len(all_good_hits)
        avg_score     = float(np.mean([h[1] for h in all_good_hits])) if all_good_hits else 0.0

        # Best matched ID within exact window (for reporting)
        if exact_hits:
            from collections import Counter
            id_counts = Counter(h[0] for h in exact_hits)
            best_match_id = id_counts.most_common(1)[0][0]
        else:
            best_match_id = asset_id

        if is_absent:
            # Robot visited original spot → asset should NOT be there
            verdict = 'MOVED'
            # Fire ASSET_MOVED alert
            new_pos = self.new_positions.get(asset_num, 'Unknown')
            alert = {
                'type':        'ASSET_MOVED',
                'asset_id':    asset_id,
                'asset_num':   asset_num,
                'frame':       start_frame,
                'baseline_xy': baseline,
                'new_position_xy': new_pos,
                'detections_in_window': total_hits,
                'note': 'Asset absent at original baseline position',
            }
            self.alerts.append(alert)
            alert_buf.append(alert)
            print(f"\n  *** ALERT: ASSET_MOVED  {asset_id}  "
                  f"(baseline {[f'{v:.2f}' for v in baseline]}, "
                  f"new pos: {new_pos}) ***\n")
        elif total_hits >= MIN_DETECTIONS_FOR_PRESENT:
            verdict = 'PRESENT'
        else:
            verdict = 'MISSING'
            # Fire ASSET_MISSING alert if no detections at all
            if total_hits == 0:
                alert = {
                    'type':        'ASSET_MISSING',
                    'asset_id':    asset_id,
                    'asset_num':   asset_num,
                    'frame':       start_frame,
                    'baseline_xy': baseline,
                    'detections_in_window': 0,
                    'note': 'Asset not detected in visit window',
                }
                self.alerts.append(alert)
                alert_buf.append(alert)
                print(f"  [MISSING] {asset_id}  no detections in window (frames {start_frame}-{ev['end_frame']})")

        result = {
            'asset':       asset_num,
            'asset_id':    asset_id,
            'matched_as':  best_match_id,
            'verdict':     verdict,
            'detections':  total_hits,
            'avg_score':   round(avg_score, 4),
            'baseline_xy': baseline,
            'frames':      [ev['start_frame'], ev['end_frame']],
        }
        self.results.append(result)

        if verdict == 'PRESENT':
            print(f"  [OK] {asset_id}  PRESENT  ({total_hits} detections, matched_as={best_match_id}, avg={avg_score*100:.1f}%)")

    def _print_summary(self):
        print()
        print("=" * 65)
        print("  PHASE 3 — SPATIAL PATROL RESULTS")
        print("=" * 65)
        total   = len(self.results)
        present = sum(1 for r in self.results if r['verdict'] == 'PRESENT')
        moved   = sum(1 for r in self.results if r['verdict'] == 'MOVED')
        missing = sum(1 for r in self.results if r['verdict'] == 'MISSING')

        print(f"  Total windows evaluated : {total}")
        print(f"  PRESENT                 : {present}")
        print(f"  MOVED (expected absent) : {moved}")
        print(f"  MISSING (not detected)  : {missing}")
        print()
        print("  ALERTS FIRED:")
        if not self.alerts:
            print("    None")
        for al in self.alerts:
            print(f"    [{al['type']}]  {al['asset_id']}  @ frame {al['frame']}")
            if 'new_position_xy' in al:
                print(f"       New position: {al['new_position_xy']}")
        print()
        print("  PER-ASSET RESULTS:")
        for r in sorted(self.results, key=lambda x: int(x['asset'])):
            status_sym = {'PRESENT': '✓', 'MOVED': '⚠', 'MISSING': '✗'}.get(r['verdict'], '?')
            matched = r.get('matched_as', r['asset_id'])
            match_note = f"  [matched as {matched}]" if matched != r['asset_id'] and r['verdict'] == 'PRESENT' else ""
            print(f"    {status_sym}  {r['asset_id']:<10}  {r['verdict']:<10}  "
                  f"detections={r['detections']:>3}  avg_score={r['avg_score']*100:.1f}%{match_note}")
        print("=" * 65)

    def _save_report(self):
        ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        report_dir = Path("evidence/patrol_runs")
        report_dir.mkdir(parents=True, exist_ok=True)
        report_path = report_dir / f"phase3_report_{ts}.json"
        report = {
            'generated_at':  datetime.now(timezone.utc).isoformat(),
            'video':         str(self.video_path),
            'results':       self.results,
            'alerts':        self.alerts,
            'summary': {
                'total':   len(self.results),
                'present': sum(1 for r in self.results if r['verdict'] == 'PRESENT'),
                'moved':   sum(1 for r in self.results if r['verdict'] == 'MOVED'),
                'missing': sum(1 for r in self.results if r['verdict'] == 'MISSING'),
            }
        }
        report_path.write_text(json.dumps(report, indent=2))
        print(f"[Phase3] Report saved → {report_path}")
        print(f"[Phase3] Video  saved → {self.output_path}")


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(
        description="Phase 3: Spatial Asset Tracking — verify assets at baseline positions"
    )
    parser.add_argument(
        "--video", required=True,
        help="Path to Phase3.mp4"
    )
    parser.add_argument(
        "--events",
        default="data/phase3/events.json",
        help="Path to events.json (default: data/phase3/events.json)"
    )
    parser.add_argument(
        "--output",
        default=None,
        help="Output annotated video path (auto-generated if omitted)"
    )
    args = parser.parse_args()

    # Banner
    print()
    print("=" * 65)
    print("  SITE ASSETS MONITOR — PHASE 3: SPATIAL ASSET TRACKING")
    print("=" * 65)

    runner = Phase3PatrolRunner(
        video_path=args.video,
        events_json=args.events,
        output_path=args.output,
    )
    runner.run()


if __name__ == "__main__":
    main()
