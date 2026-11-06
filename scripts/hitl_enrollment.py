"""
ASI Perception System — HITL Asset Enrollment Tool  (Professional UI v2)
Phase 1: Human-in-the-Loop Baseline Asset Registration

LAYOUT (single window, no popups):
  ┌──────────────────────────────────────┬────────────────────────┐
  │                                      │  CROP PREVIEW          │
  │         VIDEO FEED                   │  Quality info          │
  │         (with bbox overlays)         │  ─────────────────     │
  │                                      │  QUICK ASSIGN          │
  │                                      │  [CONT-001] [CONT-002] │
  │                                      │  [CONT-003] [CONT-004] │
  │                                      │  ─────────────────     │
  │                                      │  > NEW ID: [input___]  │
  │                                      │  ─────────────────     │
  │                                      │  SESSION STATS         │
  ├──────────────────────────────────────┴────────────────────────┤
  │  STATUS BAR — dynamic message + keyboard shortcuts            │
  └───────────────────────────────────────────────────────────────┘

Color theme: Black / White / Yellow
  - Background : #101010  (near-black)
  - Panel bg   : #1A1A1A
  - Dividers   : #2E2E2E
  - Primary txt: #F0F0F0  (near-white)
  - Accent     : #FFD700  (gold-yellow)
  - Selected   : #FFD700  box around active candidate
  - Buttons    : #2A2A2A bg, #FFD700 border on hover, white text
  - Success    : #39FF14  (neon green for enrolled)
  - Error      : #FF4444

Controls:
  [SPACE]        : Play / Pause
  [ENTER] / [E]  : Enroll active candidate (opens inline text input if no Quick-Assign is used)
  [N]            : New ID — open inline text input
  [TAB]          : Switch to next auto-proposed candidate
  [A] / [D]      : Seek backward / forward 30 frames
  [LEFT]/[RIGHT] : Step ±5 frames
  [R]            : Reset to auto-proposals (clear manual box)
  [L]            : Print enrolled assets to console
  [Q] / [ESC]    : Quit, export training zip, print summary
"""

import os
import sys
import json
import time
import zipfile
import argparse
from pathlib import Path
from datetime import datetime, timezone

import cv2
import numpy as np

# ---------------------------------------------------------------------------
# Project root setup
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parent.parent
os.chdir(PROJECT_ROOT)
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.image_quality import ImageQualityChecker
from src.reid_engine import ReIDEngine
from src.reference_store import ReferenceStore

# ---------------------------------------------------------------------------
# UI Constants
# ---------------------------------------------------------------------------
SIDEBAR_W   = 290          # px — width of right sidebar panel
STATUS_H    = 52           # px — height of bottom status bar
PREVIEW_H   = 190          # px — crop preview box height
BTN_H       = 32           # px — height of each quick-assign button
BTN_COLS    = 2            # buttons per row
BTN_GAP     = 6            # px gap between buttons
SECTION_PAD = 10           # px padding inside sidebar sections

# Color palette (BGR)
C_BG        = (16,  16,  16)   # main background
C_PANEL     = (26,  26,  26)   # sidebar panel bg
C_DIVIDER   = (46,  46,  46)   # section divider line
C_TEXT      = (240, 240, 240)  # primary text (near-white)
C_SUBTEXT   = (160, 160, 160)  # secondary text
C_ACCENT    = (0,   215, 255)  # gold-yellow in BGR (#FFD700)
C_BTN_BG    = (40,  40,  40)   # button background
C_BTN_HOVER = (0,   215, 255)  # button border on "last clicked"
C_SUCCESS   = (20,  200,  60)  # enrollment success green
C_WARN      = (0,   140, 255)  # orange-ish warning
C_ERROR     = (68,   68, 255)  # red error
C_CAND_SEL  = (0,   215, 255)  # selected candidate box (yellow)
C_CAND_OTH  = (100, 100, 100)  # other candidates (grey)
C_MANUAL    = (200, 200, 255)  # manual override box
C_STATUS_BG = (10,  10,  10)   # status bar background

FONT      = cv2.FONT_HERSHEY_SIMPLEX
FONT_BOLD = cv2.FONT_HERSHEY_DUPLEX


# ===========================================================================
# ContainerProposer — unchanged from v1
# ===========================================================================
class ContainerProposer:
    """
    Environment-agnostic object & container candidate proposer.
    Identifies colored rectangular container structures and digital ID display boards.
    Guarantees exactly ONE non-overlapping proposal per physical container.
    """

    @staticmethod
    def propose(frame: np.ndarray) -> list:
        """
        Returns a list of candidate bounding boxes: (x1, y1, x2, y2, tag),
        ranked by visual prominence (centrality + area), with strict containment suppression.
        """
        h, w = frame.shape[:2]
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        hsv  = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        sat  = hsv[:, :, 1]
        val  = hsv[:, :, 2]

        candidates = []

        # 1. Prominent colored container faces (Blue, Green, Yellow, Orange, Red)
        mask_col = ((sat > 35) & (val > 35) & (val < 240)).astype(np.uint8) * 255
        kernel   = cv2.getStructuringElement(cv2.MORPH_RECT, (15, 25))
        closed   = cv2.morphologyEx(mask_col, cv2.MORPH_CLOSE, kernel)
        contours_col, _ = cv2.findContours(closed, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        min_area = w * h * 0.04
        for c in contours_col:
            x, y, bw, bh = cv2.boundingRect(c)
            area = bw * bh
            if bw > 75 and bh > 85 and area >= min_area and bw < int(w * 0.92):
                aspect = bw / float(bh)
                if 0.35 <= aspect <= 3.2:
                    center_dist = abs(((x + x + bw) / 2.0) - (w / 2.0))
                    score = area - (center_dist * 60)
                    candidates.append((score, (x, y, x + bw, y + bh), "Container Body", area))

        # 2. Digital ID display boards (dark rectangles with high-contrast text)
        _, thresh_black = cv2.threshold(gray, 45, 255, cv2.THRESH_BINARY_INV)
        contours_board, _ = cv2.findContours(thresh_black, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        for c in contours_board:
            bx, by, bw, bh = cv2.boundingRect(c)
            if bw > 40 and bh > 40 and (bw * bh) > 2500 and (bw / float(bh) < 2.5):
                inside_existing = False
                for _, cb, _, _ in candidates:
                    if cb[0] <= bx + 15 and cb[2] >= (bx + bw - 15) and cb[1] <= by + 15 and cb[3] >= (by + bh - 15):
                        inside_existing = True
                        break
                if not inside_existing:
                    pad_x     = int(bw * 0.60)
                    pad_y_top = int(by  * 0.35)
                    pad_y_bot = int(bh  * 1.0)
                    cx1  = max(0,          bx - pad_x)
                    cy1  = max(0,          by - pad_y_top)
                    cx2  = min(w,          bx + bw + pad_x)
                    cy2  = min(int(h*0.90), by + bh + pad_y_bot)
                    area = (cx2 - cx1) * (cy2 - cy1)
                    center_dist = abs(((cx1 + cx2) / 2.0) - (w / 2.0))
                    score = area - (center_dist * 60)
                    candidates.append((score, (cx1, cy1, cx2, cy2), f"ID Board ({bw}x{bh})", area))

        if not candidates:
            return []

        candidates.sort(key=lambda x: x[3], reverse=True)

        # Non-maximum suppression with IoMin (containment) suppression
        final_proposals = []
        for score, b, tag, area in candidates:
            keep = True
            for fs, fb, ftag, farea in final_proposals:
                ix1   = max(b[0], fb[0]); iy1 = max(b[1], fb[1])
                ix2   = min(b[2], fb[2]); iy2 = min(b[3], fb[3])
                inter = max(0, ix2 - ix1) * max(0, iy2 - iy1)
                area_b  = (b[2]  - b[0])  * (b[3]  - b[1])
                area_fb = (fb[2] - fb[0]) * (fb[3] - fb[1])
                min_a   = min(area_b, area_fb)
                iomin   = inter / float(min_a) if min_a > 0 else 0
                union   = area_b + area_fb - inter
                iou     = inter / float(union) if union > 0 else 0
                if iou > 0.35 or iomin > 0.35:
                    keep = False
                    break
            if keep:
                final_proposals.append((score, b, tag, area))

        final_proposals.sort(key=lambda x: x[0], reverse=True)
        return [(b[0], b[1], b[2], b[3], tag) for s, b, tag, a in final_proposals]


# ===========================================================================
# HITLEnrollmentTool  — full rewrite, single-window, no Tkinter
# ===========================================================================
class HITLEnrollmentTool:
    """Professional HITL Asset Enrollment Interface.
    Single OpenCV window: video feed on left, sidebar on right.
    Quick-Assign buttons, inline text input, training data export.
    Theme: Black / White / Yellow (#FFD700 accent).
    """

    def __init__(self, video_path: str, default_class: str = "container"):
        self.video_path    = Path(video_path)
        self.default_class = default_class

        if not self.video_path.exists():
            raise FileNotFoundError(f"Video not found: {self.video_path}")

        # ── Storage paths ──────────────────────────────────────────────────
        self.ref_images_dir  = PROJECT_ROOT / "data" / "reference_images"
        self.yolo_images_dir = PROJECT_ROOT / "data" / "datasets" / "containers" / "images"
        self.yolo_labels_dir = PROJECT_ROOT / "data" / "datasets" / "containers" / "labels"
        self.log_file        = PROJECT_ROOT / "data" / "enrollment_log.json"

        for d in [self.ref_images_dir, self.yolo_images_dir, self.yolo_labels_dir]:
            d.mkdir(parents=True, exist_ok=True)

        # ── Load perception modules ────────────────────────────────────────
        print("\n" + "=" * 65)
        print("  SITE ASSETS MONITOR — HITL ENROLLMENT  (v2 Professional UI)")
        print("=" * 65)
        self.quality_checker  = ImageQualityChecker()
        self.reid_engine      = ReIDEngine("config/reid_config.yaml")
        self.reference_store  = ReferenceStore("config/reid_config.yaml")

        # ── Video capture ──────────────────────────────────────────────────
        self.cap = cv2.VideoCapture(str(self.video_path))
        if not self.cap.isOpened():
            raise RuntimeError(f"Cannot open video: {self.video_path}")

        self.total_frames   = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))
        self.native_fps     = self.cap.get(cv2.CAP_PROP_FPS) or 10.0
        self.frame_w        = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        self.frame_h        = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

        print(f"  Video : {self.video_path.name}  ({self.frame_w}x{self.frame_h} @ {self.native_fps:.1f} fps)")
        print(f"  Frames: {self.total_frames}  (~{self.total_frames / self.native_fps / 60:.1f} min)")
        print(f"  Gallery (already enrolled): {self.reference_store.list_assets()}")
        print("=" * 65 + "\n")

        # ── Session state ──────────────────────────────────────────────────
        self.current_frame_idx = 0
        self.current_frame     = None
        self.is_paused         = False
        self.session_enrolled  = []          # records for this session
        self.enrolled_count    = len(self.reference_store.list_assets())

        # ── Proposal state ─────────────────────────────────────────────────
        self.proposer           = ContainerProposer()
        self.auto_candidates    = []   # list[(x1,y1,x2,y2,tag)]
        self.selected_cand_idx  = 0
        self.manual_override_bbox = None

        # ── Mouse drawing ──────────────────────────────────────────────────
        self.drawing    = False
        self.pt_start   = None
        self.pt_current = None

        # ── Status / banner ────────────────────────────────────────────────
        self.banner_text  = "▶  PLAYING — press SPACE when you see an asset"
        self.banner_color = C_ACCENT
        self.banner_until = 0.0

        # ── Quick-assign button system ─────────────────────────────────────
        self.quick_ids    = []          # ordered list of enrolled asset IDs
        self.button_rects = []          # [(x1,y1,x2,y2, asset_id), ...]
        self.last_btn_id  = None        # highlight last-clicked button

        # ── Inline text input ──────────────────────────────────────────────
        self.text_input_active  = False
        self.text_input_buffer  = ""
        self.text_input_blink   = True  # cursor blink state
        self.text_blink_timer   = time.time()

        # ── Crop preview (stored as small image for sidebar) ───────────────
        self._preview_img  = None       # np.ndarray or None
        self._preview_qual = {}

        # ── Window & mouse ─────────────────────────────────────────────────
        self.canvas_w   = self.frame_w + SIDEBAR_W
        self.canvas_h   = self.frame_h + STATUS_H
        self.win_name   = "SITE Assets Monitor — HITL Enrollment"
        cv2.namedWindow(self.win_name, cv2.WINDOW_NORMAL)
        cv2.resizeWindow(self.win_name, min(self.canvas_w, 1440), min(self.canvas_h, 860))
        cv2.setMouseCallback(self.win_name, self._on_mouse)

        # Pre-populate quick buttons from already-enrolled assets
        # list_assets() returns dicts like {'asset_id': 'CONT-001', ...}
        for entry in self.reference_store.list_assets():
            aid = entry["asset_id"] if isinstance(entry, dict) else str(entry)
            if aid not in self.quick_ids:
                self.quick_ids.append(aid)

    # ========================================================================
    # Mouse handler
    # ========================================================================
    def _on_mouse(self, event, x, y, flags, param):
        """Handle mouse events on the composite canvas."""

        # ── Sidebar button click ───────────────────────────────────────────
        if event == cv2.EVENT_LBUTTONUP:
            for bx1, by1, bx2, by2, aid in self.button_rects:
                if bx1 <= x <= bx2 and by1 <= y <= by2:
                    # Quick-assign: enroll current candidate with this existing ID
                    self._do_enroll(aid)
                    self.last_btn_id = aid
                    return

        # ── Video area mouse (manual bbox drawing) ─────────────────────────
        if x >= self.frame_w:  # cursor is in sidebar — ignore for drawing
            return

        if not self.is_paused:
            return

        if event == cv2.EVENT_LBUTTONDOWN:
            self.drawing    = True
            self.pt_start   = (x, y)
            self.pt_current = (x, y)
            self.manual_override_bbox = None

        elif event == cv2.EVENT_MOUSEMOVE:
            if self.drawing:
                self.pt_current = (x, y)

        elif event == cv2.EVENT_LBUTTONUP:
            if self.drawing:
                self.drawing = False
                x1, y1       = self.pt_start
                x2, y2       = x, y
                xmin = max(0, min(x1, x2)); xmax = min(self.frame_w, max(x1, x2))
                ymin = max(0, min(y1, y2)); ymax = min(self.frame_h, max(y1, y2))
                if (xmax - xmin) >= 30 and (ymax - ymin) >= 30:
                    self.manual_override_bbox = (xmin, ymin, xmax, ymax)
                    self._refresh_crop_preview()
                    self._set_banner("Manual box drawn — press [ENTER] to enroll, [R] to reset", C_ACCENT)
                else:
                    self.manual_override_bbox = None
                    self._update_proposals()

        elif event == cv2.EVENT_RBUTTONDOWN:
            self.manual_override_bbox = None
            self.drawing = False
            self._update_proposals()
            self._set_banner("Reset to auto-proposals", C_SUBTEXT)

    # ========================================================================
    # Proposal helpers
    # ========================================================================
    def _get_active_bbox(self):
        """Return the currently active bounding box or None."""
        if self.manual_override_bbox is not None:
            return self.manual_override_bbox
        if self.auto_candidates and self.selected_cand_idx < len(self.auto_candidates):
            c = self.auto_candidates[self.selected_cand_idx]
            return (c[0], c[1], c[2], c[3])
        return None

    def _update_proposals(self):
        """Run proposer on current frame (unless manual override is active)."""
        if self.current_frame is None or self.manual_override_bbox is not None:
            return
        self.auto_candidates = self.proposer.propose(self.current_frame)
        if self.selected_cand_idx >= len(self.auto_candidates):
            self.selected_cand_idx = 0
        self._refresh_crop_preview()

    def _refresh_crop_preview(self):
        """Update the cached crop preview image for the sidebar."""
        self._preview_img  = None
        self._preview_qual = {}
        if self.current_frame is None:
            return
        bbox = self._get_active_bbox()
        if bbox is None:
            return
        x1, y1, x2, y2 = bbox
        crop = self.current_frame[y1:y2, x1:x2].copy()
        if crop.size == 0:
            return
        # Quality
        q = self.quality_checker.check(crop)
        self._preview_qual = q
        # Resize for sidebar
        ph = PREVIEW_H
        pw = max(10, int(ph * (crop.shape[1] / max(1, crop.shape[0]))))
        self._preview_img = cv2.resize(crop, (pw, ph))

    # ========================================================================
    # Enrollment
    # ========================================================================
    def enroll_current_asset(self):
        """Called when ENTER/E is pressed. Opens inline text input or enrolls."""
        bbox = self._get_active_bbox()
        if self.current_frame is None or bbox is None:
            self._set_banner("No candidate in view — wait or draw a box manually", C_ERROR)
            return

        # Pause to hold the frame
        self.is_paused = True

        suggested = f"CONT-{self.enrolled_count + 1:03d}"
        self.text_input_buffer = suggested
        self.text_input_active = True
        self._set_banner("Type Asset ID, then press [ENTER] to confirm  |  [ESC] to cancel", C_ACCENT)

    def _quick_enroll(self, asset_id: str):
        """Enroll active candidate instantly with an existing ID (no typing)."""
        bbox = self._get_active_bbox()
        if self.current_frame is None or bbox is None:
            self._set_banner("No candidate in view — pause on an asset first", C_ERROR)
            return
        self.is_paused = True
        self._do_enroll(asset_id)

    def _do_enroll(self, asset_id: str):
        """Core enrollment: crop → embed → store → save → update buttons."""
        asset_id = asset_id.strip().upper()
        if not asset_id:
            return

        bbox = self._get_active_bbox()
        if self.current_frame is None or bbox is None:
            self._set_banner("No active candidate to enroll!", C_ERROR)
            return

        x1, y1, x2, y2 = bbox
        crop = self.current_frame[y1:y2, x1:x2].copy()

        print(f"\n[HITL] Extracting OSNet embedding for '{asset_id}'...")
        embedding = self.reid_engine.extract_embedding(crop)
        if embedding is None:
            self._set_banner(f"ERROR: Could not extract embedding for '{asset_id}'!", C_ERROR)
            return

        success = self.reference_store.add_reference(
            asset_id=asset_id,
            class_name=self.default_class,
            embedding=embedding,
            auto_save=True,
        )
        if not success:
            self._set_banner(f"ERROR: ReferenceStore rejected '{asset_id}'", C_ERROR)
            return

        # Save reference image crop
        asset_dir = self.ref_images_dir / asset_id
        asset_dir.mkdir(parents=True, exist_ok=True)
        ref_idx      = len(list(asset_dir.glob("*.jpg"))) + 1
        ref_img_path = asset_dir / f"ref_{ref_idx:03d}.jpg"
        cv2.imwrite(str(ref_img_path), crop, [cv2.IMWRITE_JPEG_QUALITY, 95])

        # Save YOLO frame + label
        sample_name     = f"frame_{self.current_frame_idx:06d}"
        frame_save_path = self.yolo_images_dir / f"{sample_name}.jpg"
        cv2.imwrite(str(frame_save_path), self.current_frame, [cv2.IMWRITE_JPEG_QUALITY, 95])

        bx_c = ((x1 + x2) / 2.0) / self.frame_w
        by_c = ((y1 + y2) / 2.0) / self.frame_h
        bw   = (x2 - x1) / self.frame_w
        bh   = (y2 - y1) / self.frame_h
        label_path = self.yolo_labels_dir / f"{sample_name}.txt"
        with open(label_path, "a") as lf:
            lf.write(f"0 {bx_c:.6f} {by_c:.6f} {bw:.6f} {bh:.6f}\n")

        # Audit log
        record = {
            "asset_id"     : asset_id,
            "class_name"   : self.default_class,
            "timestamp"    : datetime.now(timezone.utc).isoformat(),
            "frame_idx"    : self.current_frame_idx,
            "timestamp_sec": round(self.current_frame_idx / self.native_fps, 2),
            "bbox_xyxy"    : [int(x1), int(y1), int(x2), int(y2)],
            "embedding_dim": int(len(embedding)),
            "ref_image"    : str(ref_img_path.relative_to(PROJECT_ROOT)),
        }
        self.session_enrolled.append(record)
        self._append_to_log(record)

        # Update counters & quick-assign buttons
        self.enrolled_count = len(self.reference_store.list_assets())
        if asset_id not in self.quick_ids:
            self.quick_ids.append(asset_id)
        self.last_btn_id = asset_id

        # Reset manual box, re-propose
        self.manual_override_bbox = None
        self._update_proposals()

        view_num = len(list((self.ref_images_dir / asset_id).glob("*.jpg")))
        self._set_banner(
            f"✓  '{asset_id}' enrolled  (view #{view_num}, total gallery: {self.enrolled_count} assets)",
            C_SUCCESS,
        )
        print(f"[HITL] ✓  Enrolled '{asset_id}' — view #{view_num}  |  Gallery: {self.enrolled_count} assets")

    def _append_to_log(self, record: dict):
        existing = []
        if self.log_file.exists():
            try:
                with open(self.log_file, "r") as f:
                    existing = json.load(f)
            except Exception:
                existing = []
        existing.append(record)
        with open(self.log_file, "w") as f:
            json.dump(existing, f, indent=2)

    # ========================================================================
    # Banner
    # ========================================================================
    def _set_banner(self, text: str, color: tuple, duration: float = 4.5):
        self.banner_text  = text
        self.banner_color = color
        self.banner_until = time.time() + duration

    # ========================================================================
    # Seek
    # ========================================================================
    def seek_relative(self, delta: int):
        target = max(0, min(self.total_frames - 1, self.current_frame_idx + delta))
        self.cap.set(cv2.CAP_PROP_POS_FRAMES, target)
        ret, frame = self.cap.read()
        if ret:
            self.current_frame     = frame
            self.current_frame_idx = target
        self.manual_override_bbox = None
        self._update_proposals()
        sec = self.current_frame_idx / self.native_fps
        self._set_banner(f"Frame {self.current_frame_idx}  ({sec:.1f}s)", C_SUBTEXT, 2.0)

    # ========================================================================
    # Rendering
    # ========================================================================

    def _draw_video_layer(self, canvas: np.ndarray):
        """Overlay detection boxes on the video region of canvas."""
        if self.current_frame is None:
            return

        # Paste video frame into left of canvas
        vf = self.current_frame.copy()
        canvas[0:self.frame_h, 0:self.frame_w] = vf

        # In-progress manual drag
        if self.drawing and self.pt_start and self.pt_current:
            cv2.rectangle(canvas, self.pt_start, self.pt_current, C_ACCENT, 2)

        if self.manual_override_bbox is not None:
            x1, y1, x2, y2 = self.manual_override_bbox
            cv2.rectangle(canvas, (x1, y1), (x2, y2), C_MANUAL, 2)
            cv2.putText(canvas, "Manual  [ENTER to Enroll]", (x1, max(18, y1 - 8)),
                        FONT, 0.52, C_MANUAL, 1, cv2.LINE_AA)
        else:
            for idx, c in enumerate(self.auto_candidates):
                cx1, cy1, cx2, cy2, tag = c
                is_sel = (idx == self.selected_cand_idx)
                if is_sel:
                    # Semi-transparent fill
                    overlay = canvas.copy()
                    cv2.rectangle(overlay, (cx1, cy1), (cx2, cy2), C_CAND_SEL, -1)
                    cv2.addWeighted(overlay, 0.12, canvas, 0.88, 0, canvas)
                    cv2.rectangle(canvas, (cx1, cy1), (cx2, cy2), C_CAND_SEL, 2)
                    label = f">> {tag}  [ENTER to Enroll]"
                    cv2.putText(canvas, label, (cx1, max(20, cy1 - 8)),
                                FONT, 0.55, C_CAND_SEL, 2, cv2.LINE_AA)
                else:
                    cv2.rectangle(canvas, (cx1, cy1), (cx2, cy2), C_CAND_OTH, 1)
                    cv2.putText(canvas, f"[{idx+1}] {tag}", (cx1, max(16, cy1 - 5)),
                                FONT, 0.42, C_CAND_OTH, 1, cv2.LINE_AA)

        # Top-left mini info strip on video
        cv2.rectangle(canvas, (0, 0), (self.frame_w, 26), (0, 0, 0), -1)
        mode_lbl = "[ PAUSED ]" if self.is_paused else "[ PLAYING ]"
        mode_col = C_WARN if self.is_paused else C_SUCCESS
        cv2.putText(canvas, mode_lbl, (8, 18), FONT_BOLD, 0.55, mode_col, 1, cv2.LINE_AA)

        pct  = int(100 * self.current_frame_idx / max(1, self.total_frames))
        sec  = self.current_frame_idx / self.native_fps
        info = f"Frame {self.current_frame_idx}/{self.total_frames}  {sec:05.1f}s  ({pct}%)"
        cv2.putText(canvas, info, (130, 18), FONT, 0.47, C_SUBTEXT, 1, cv2.LINE_AA)

        cand_n = len(self.auto_candidates)
        cv2.putText(canvas, f"Candidates: {cand_n}", (self.frame_w - 155, 18),
                    FONT, 0.47, C_ACCENT if cand_n > 0 else C_SUBTEXT, 1, cv2.LINE_AA)

    def _draw_sidebar(self, canvas: np.ndarray):
        """Render the right sidebar: crop preview, quick-assign buttons, stats, text input."""
        sx = self.frame_w   # sidebar x offset
        sw = SIDEBAR_W
        sh = self.frame_h

        # Sidebar background
        cv2.rectangle(canvas, (sx, 0), (sx + sw, sh), C_PANEL, -1)

        y = 0  # running y cursor inside sidebar

        # ── HEADER ──────────────────────────────────────────────────────────
        cv2.rectangle(canvas, (sx, y), (sx + sw, y + 30), C_BG, -1)
        cv2.putText(canvas, "SITE ASSETS MONITOR", (sx + 8, y + 20),
                    FONT_BOLD, 0.5, C_ACCENT, 1, cv2.LINE_AA)
        y += 30

        # ── CROP PREVIEW ─────────────────────────────────────────────────────
        y = self._draw_section_header(canvas, sx, sw, y, "CROP PREVIEW")
        preview_y = y
        preview_region_h = PREVIEW_H + 50  # preview + quality lines
        cv2.rectangle(canvas, (sx, y), (sx + sw, y + preview_region_h), C_BG, -1)

        if self._preview_img is not None:
            ph, pw = self._preview_img.shape[:2]
            # Center horizontally
            px_off = sx + max(0, (sw - pw) // 2)
            py_off = y + 4
            if px_off + pw <= sx + sw and py_off + ph <= y + preview_region_h:
                canvas[py_off:py_off + ph, px_off:px_off + pw] = self._preview_img
            # Quality row
            qy  = py_off + ph + 6
            blur = self._preview_qual.get("blur_score", 0.0)
            bri  = self._preview_qual.get("brightness", 0.0)
            ok   = self._preview_qual.get("quality", "UNUSABLE") != "UNUSABLE"
            q_col = C_SUCCESS if ok else C_ERROR
            q_lbl = "Quality: OK" if ok else "Quality: LOW"
            cv2.putText(canvas, q_lbl, (sx + 8, qy + 14), FONT, 0.47, q_col, 1, cv2.LINE_AA)
            cv2.putText(canvas, f"Blur: {blur:.0f}  Bright: {bri:.0f}",
                        (sx + 8, qy + 30), FONT, 0.42, C_SUBTEXT, 1, cv2.LINE_AA)
        else:
            cv2.putText(canvas, "No candidate selected", (sx + 12, y + PREVIEW_H // 2),
                        FONT, 0.46, C_SUBTEXT, 1, cv2.LINE_AA)

        y += preview_region_h

        # ── QUICK ASSIGN ─────────────────────────────────────────────────────
        y = self._draw_section_header(canvas, sx, sw, y, "QUICK ASSIGN")
        btn_area_y = y

        self.button_rects.clear()
        if self.quick_ids:
            btn_w  = (sw - BTN_GAP * 3) // BTN_COLS
            col    = 0
            bx_start = sx + BTN_GAP
            cur_bx   = bx_start
            cur_by   = y + BTN_GAP

            for aid in self.quick_ids:
                is_last = (aid == self.last_btn_id)
                bg_col  = (60, 60, 60) if not is_last else (0, 100, 180)
                bd_col  = C_ACCENT if is_last else C_DIVIDER

                bx1 = cur_bx
                by1 = cur_by
                bx2 = cur_bx + btn_w
                by2 = cur_by + BTN_H

                cv2.rectangle(canvas, (bx1, by1), (bx2, by2), bg_col, -1)
                cv2.rectangle(canvas, (bx1, by1), (bx2, by2), bd_col, 1)

                # Truncate label if needed
                label = aid if len(aid) <= 10 else aid[:9] + "…"
                (tw, th), _ = cv2.getTextSize(label, FONT, 0.44, 1)
                tx = bx1 + max(4, (btn_w - tw) // 2)
                ty = by1 + BTN_H // 2 + th // 2
                cv2.putText(canvas, label, (tx, ty), FONT, 0.44, C_TEXT, 1, cv2.LINE_AA)

                self.button_rects.append((bx1, by1, bx2, by2, aid))

                col += 1
                if col >= BTN_COLS:
                    col = 0
                    cur_bx = bx_start
                    cur_by += BTN_H + BTN_GAP
                else:
                    cur_bx += btn_w + BTN_GAP

            # Advance y to after buttons
            rows_used = (len(self.quick_ids) + BTN_COLS - 1) // BTN_COLS
            y = btn_area_y + BTN_GAP + rows_used * (BTN_H + BTN_GAP) + BTN_GAP
        else:
            cv2.putText(canvas, "No IDs enrolled yet", (sx + 10, y + 22),
                        FONT, 0.44, C_SUBTEXT, 1, cv2.LINE_AA)
            y += 36

        # ── NEW ID TEXT INPUT ────────────────────────────────────────────────
        y = self._draw_section_header(canvas, sx, sw, y, "NEW ID")
        inp_y  = y + 4
        inp_h  = 34
        inp_x1 = sx + BTN_GAP
        inp_x2 = sx + sw - BTN_GAP

        # Blink cursor every 0.5s
        now = time.time()
        if now - self.text_blink_timer > 0.5:
            self.text_input_blink = not self.text_input_blink
            self.text_blink_timer = now

        if self.text_input_active:
            # Active input box — yellow border
            cv2.rectangle(canvas, (inp_x1, inp_y), (inp_x2, inp_y + inp_h), C_ACCENT, 1)
            cursor = "|" if self.text_input_blink else " "
            display_txt = self.text_input_buffer + cursor
            cv2.putText(canvas, display_txt, (inp_x1 + 6, inp_y + 23),
                        FONT_BOLD, 0.5, C_TEXT, 1, cv2.LINE_AA)
            cv2.putText(canvas, "[ENTER] confirm  [ESC] cancel",
                        (inp_x1, inp_y + inp_h + 14), FONT, 0.38, C_SUBTEXT, 1, cv2.LINE_AA)
            y += inp_h + 24
        else:
            # Inactive: show hint
            cv2.rectangle(canvas, (inp_x1, inp_y), (inp_x2, inp_y + inp_h), C_DIVIDER, 1)
            cv2.putText(canvas, "Press [N] or [ENTER]", (inp_x1 + 6, inp_y + 22),
                        FONT, 0.44, C_SUBTEXT, 1, cv2.LINE_AA)
            y += inp_h + 8

        # ── SESSION STATS ────────────────────────────────────────────────────
        y = self._draw_section_header(canvas, sx, sw, y, "SESSION STATS")
        all_assets_raw = self.reference_store.list_assets()
        all_assets = [
            (e["asset_id"] if isinstance(e, dict) else str(e))
            for e in all_assets_raw
        ]
        yolo_imgs  = len(list(self.yolo_images_dir.glob("*.jpg")))
        ref_imgs   = sum(len(list((self.ref_images_dir / a).glob("*.jpg")))
                         for a in all_assets if (self.ref_images_dir / a).exists())

        stats = [
            (f"Gallery total : {len(all_assets)} assets",  C_ACCENT),
            (f"This session  : {len(self.session_enrolled)} enrollments", C_TEXT),
            (f"Reference imgs: {ref_imgs}",   C_TEXT),
            (f"YOLO labels   : {yolo_imgs}",  C_TEXT),
        ]
        for line, col in stats:
            y += 2
            cv2.putText(canvas, line, (sx + 8, y + 15), FONT, 0.43, col, 1, cv2.LINE_AA)
            y += 17

    def _draw_section_header(self, canvas, sx, sw, y, title):
        """Draw a labeled section divider line. Returns new y."""
        cv2.rectangle(canvas, (sx, y), (sx + sw, y + 22), C_BG, -1)
        cv2.line(canvas, (sx + 4, y + 11), (sx + 20, y + 11), C_DIVIDER, 1)
        cv2.putText(canvas, title, (sx + 24, y + 16), FONT, 0.42, C_ACCENT, 1, cv2.LINE_AA)
        cv2.line(canvas, (sx + 24 + len(title) * 7 + 8, y + 11), (sx + sw - 4, y + 11), C_DIVIDER, 1)
        return y + 22

    def _draw_status_bar(self, canvas: np.ndarray):
        """Draw the bottom status bar across full canvas width."""
        bar_y = self.frame_h
        cv2.rectangle(canvas, (0, bar_y), (self.canvas_w, bar_y + STATUS_H), C_STATUS_BG, -1)
        cv2.line(canvas, (0, bar_y), (self.canvas_w, bar_y), C_ACCENT, 1)

        # Dynamic banner (timed) or default hint
        if time.time() < self.banner_until:
            msg = self.banner_text
            col = self.banner_color
        else:
            msg = ("▶ [SPACE] Pause  |  [ENTER/N] New ID  |  [TAB] Next candidate  |  "
                   "[A/D] Seek  |  [L] List  |  [Q] Quit & Export")
            col = C_SUBTEXT

        cv2.putText(canvas, msg, (10, bar_y + 20), FONT, 0.47, col, 1, cv2.LINE_AA)

        # Enrolled count on right of bar
        enr_str = f"Enrolled: {self.enrolled_count}"
        (tw, _), _ = cv2.getTextSize(enr_str, FONT_BOLD, 0.55, 1)
        cv2.putText(canvas, enr_str, (self.canvas_w - tw - 12, bar_y + 20),
                    FONT_BOLD, 0.55, C_ACCENT, 1, cv2.LINE_AA)

        # Second line: video name
        vname = self.video_path.name
        cv2.putText(canvas, vname, (10, bar_y + 40), FONT, 0.4, C_SUBTEXT, 1, cv2.LINE_AA)

    def _compose_frame(self) -> np.ndarray:
        """Build the final composite canvas: video + sidebar + status bar."""
        canvas = np.full((self.canvas_h, self.canvas_w, 3), C_BG, dtype=np.uint8)
        self._draw_video_layer(canvas)
        self._draw_sidebar(canvas)
        self._draw_status_bar(canvas)
        return canvas

    # ========================================================================
    # Training data export
    # ========================================================================
    def _export_training_zip(self):
        """Package data/datasets/containers/ into a zip for Kaggle upload."""
        ds_dir = PROJECT_ROOT / "data" / "datasets" / "containers"
        if not ds_dir.exists():
            print("[Export] No YOLO dataset directory found — skipping zip.")
            return

        ts       = datetime.now().strftime("%Y%m%d_%H%M%S")
        zip_path = PROJECT_ROOT / "data" / f"training_export_{ts}.zip"

        # Write dataset_info.json
        n_imgs = len(list((ds_dir / "images").glob("*.jpg")))
        n_lbl  = len(list((ds_dir / "labels").glob("*.txt")))
        info   = {
            "created"      : datetime.now(timezone.utc).isoformat(),
            "video_source" : self.video_path.name,
            "num_images"   : n_imgs,
            "num_labels"   : n_lbl,
            "classes"      : ["container"],
            "format"       : "YOLOv8",
            "enrolled_ids" : self.quick_ids,
        }
        info_path = ds_dir / "dataset_info.json"
        with open(info_path, "w") as f:
            json.dump(info, f, indent=2)

        print(f"[Export] Zipping {n_imgs} images + {n_lbl} labels → {zip_path.name} ...")
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
            for fpath in ds_dir.rglob("*"):
                if fpath.is_file():
                    zf.write(fpath, fpath.relative_to(PROJECT_ROOT / "data"))

        size_mb = zip_path.stat().st_size / 1024 / 1024
        print(f"[Export] ✓  Training zip saved: {zip_path.name}  ({size_mb:.1f} MB)")
        print(f"[Export]    Ready to upload to Kaggle / Google Colab.")

    # ========================================================================
    # Main loop
    # ========================================================================
    def run(self):
        """Main event loop."""
        print("=" * 65)
        print("  HITL ENROLLMENT READY")
        print("  Controls: SPACE=Play/Pause  ENTER/N=New ID  TAB=Next")
        print("            A/D=Seek  Q=Quit & Export  L=List assets")
        print("=" * 65 + "\n")

        # Read first frame
        ret, frame = self.cap.read()
        if not ret:
            print("[Error] Failed to read first frame.")
            return
        self.current_frame     = frame
        self.current_frame_idx = 0
        self._update_proposals()

        target_delay = max(1, int(1000 / self.native_fps))

        while True:
            # Advance frame when playing
            if not self.is_paused:
                ret, frame = self.cap.read()
                if not ret:
                    print("\n[Video] End of stream reached.")
                    self.is_paused = True
                    self._set_banner("End of video — press [Q] to quit & export", C_WARN)
                else:
                    self.current_frame     = frame
                    self.current_frame_idx += 1
                    self._update_proposals()

            # Compose and display
            canvas = self._compose_frame()
            cv2.imshow(self.win_name, canvas)

            wait = 1 if self.is_paused else target_delay
            key  = cv2.waitKey(wait) & 0xFF

            # ── Text input mode captures all keystrokes ─────────────────────
            if self.text_input_active:
                if key == 13 or key == 10:          # ENTER — confirm
                    self.text_input_active = False
                    aid = self.text_input_buffer.strip().upper()
                    if aid:
                        self._do_enroll(aid)
                    else:
                        self._set_banner("Enrollment cancelled — empty ID", C_SUBTEXT)
                    self.text_input_buffer = ""
                elif key == 27:                     # ESC — cancel
                    self.text_input_active = False
                    self.text_input_buffer = ""
                    self._set_banner("Input cancelled", C_SUBTEXT, 2.0)
                elif key == 8:                      # BACKSPACE
                    self.text_input_buffer = self.text_input_buffer[:-1]
                elif 32 <= key <= 126:              # Printable ASCII
                    self.text_input_buffer += chr(key).upper()
                continue  # skip normal key handling while input active

            # ── Normal key handling ──────────────────────────────────────────
            if key in [ord("q"), ord("Q"), 27]:     # Quit
                break

            elif key == ord(" "):                   # Play / Pause
                self.is_paused = not self.is_paused
                if self.is_paused:
                    self._set_banner("PAUSED — select a candidate, then [ENTER] or click a Quick-Assign button", C_WARN)
                else:
                    self._set_banner("PLAYING — press SPACE when you see an asset", C_ACCENT)

            elif key in [13, 10, ord("e"), ord("E")]:  # ENTER / E → open text input
                if self.quick_ids:
                    # Shortcut hint: if we already have IDs, also open input for new
                    self.enroll_current_asset()
                else:
                    self.enroll_current_asset()

            elif key in [ord("n"), ord("N")]:       # N → open text input explicitly
                self.enroll_current_asset()

            elif key == 9:                          # TAB → next candidate
                if self.auto_candidates:
                    self.selected_cand_idx = (self.selected_cand_idx + 1) % len(self.auto_candidates)
                    self.manual_override_bbox = None
                    self._refresh_crop_preview()
                    self._set_banner(f"Switched to candidate {self.selected_cand_idx + 1}/{len(self.auto_candidates)}", C_ACCENT, 2.0)

            elif key in [ord("r"), ord("R")]:       # R → reset manual box
                self.manual_override_bbox = None
                self._update_proposals()
                self._set_banner("Reset to auto-proposals", C_SUBTEXT, 2.0)

            elif key in [ord("d"), ord("D")]:       # D → forward 30 frames
                self.seek_relative(30)

            elif key in [ord("a"), ord("A")]:       # A → backward 30 frames
                self.seek_relative(-30)

            elif key == 83:                         # → arrow  (+5)
                self.seek_relative(5)

            elif key == 81:                         # ← arrow  (-5)
                self.seek_relative(-5)

            elif key in [ord("l"), ord("L")]:       # L → list assets
                assets = self.reference_store.list_assets()
                print(f"\n[Store] Gallery ({len(assets)} assets): {assets}")

        # ── Cleanup ──────────────────────────────────────────────────────────
        self.cap.release()
        cv2.destroyAllWindows()

        # Export training zip
        self._export_training_zip()

        # Session summary
        print("\n" + "=" * 65)
        print("  HITL ENROLLMENT SESSION SUMMARY")
        print("=" * 65)
        all_assets_raw = self.reference_store.list_assets()
        all_assets = [
            (e["asset_id"] if isinstance(e, dict) else str(e))
            for e in all_assets_raw
        ]
        print(f"  Gallery (total)   : {len(all_assets)} assets")
        print(f"  Enrolled (session): {len(self.session_enrolled)}")
        for item in self.session_enrolled:
            print(f"    • {item['asset_id']}  frame {item['frame_idx']}  ({item['timestamp_sec']}s)")
        print(f"  Fingerprints      : data/reference_db/*.npz")
        print(f"  Reference crops   : data/reference_images/")
        print(f"  YOLO dataset      : data/datasets/containers/")
        print(f"  Audit log         : data/enrollment_log.json")
        print("=" * 65 + "\n")


# ===========================================================================
# Entry point
# ===========================================================================
def main():
    parser = argparse.ArgumentParser(
        description="SITE Assets Monitor — HITL Enrollment Tool (Professional UI v2)"
    )
    default_vid = str(Path(r"C:\Users\GANGARI DHRUVAVEER\Downloads\Phase1.mp4"))
    parser.add_argument("--video",      "-v", default=default_vid, help="Path to Phase 1 video")
    parser.add_argument("--class-name", "-c", default="container",  help="Asset class label")
    args = parser.parse_args()

    tool = HITLEnrollmentTool(args.video, args.class_name)
    tool.run()


if __name__ == "__main__":
    main()
