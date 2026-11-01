"""
ASI Perception System — Environment-Agnostic HITL Asset Enrollment Tool
Phase 1: Human-in-the-Loop Baseline Asset Registration (Auto-Proposal Mode)

Features:
  1. AUTOMATIC OBJECT PROPOSAL: Automatically detects container bodies and digital
     ID boards in real time. Highlights candidates with bounding boxes without
     requiring manual drawing.
  2. INSTANT OPERATOR CONFIRMATION: Operator simply presses [ENTER] to confirm
     and name the auto-detected asset (e.g., "CONT-007").
  3. CROP QUALITY INSPECTION: Continuously checks Laplacian variance (blur) and
     brightness before enrollment.
  4. LIVE OSNet EMBEDDING: Extracts 512-D L2-normalized visual fingerprint on the spot.
  5. PERSISTENT RE-ID GALLERY: Saves to data/reference_db/{asset_id}.npz.
  6. VISUAL PROOF REPOSITORY: Saves clean reference crops in data/reference_images/{asset_id}/.
  7. AUTO-GENERATED YOLO DATASET: Automatically saves full frames and normalized
     bounding box labels (0 x_c y_c w h) into data/datasets/containers/ for future training.
  8. AUDIT LOG: Full JSON audit trail written to data/enrollment_log.json.
  9. MANUAL OVERRIDE: Click + Drag is always available if the operator wishes to draw/adjust a box.

Controls:
  [SPACE]       : Play / Pause
  [ENTER] / [E] : Enroll currently highlighted candidate container
  [TAB]         : Switch to next candidate on screen (when multiple are detected)
  [A] / [D]     : Seek backward / forward 30 frames (~3 sec)
  [LEFT]/[RIGHT]: Fine step backward / forward 5 frames
  [Click+Drag]  : Manual box override (drag on screen to draw custom box)
  [R]           : Reset selection back to auto-detected candidates
  [L]           : List enrolled assets in console
  [Q] / [ESC]   : Finish session & print summary
"""

import os
import sys
import json
import time
import argparse
from pathlib import Path
from datetime import datetime, timezone
import tkinter as tk
from tkinter import simpledialog

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


class ContainerProposer:
    """
    Environment-agnostic object & container candidate proposer.
    Identifies colored rectangular container structures and digital ID display boards.
    Guarantees exactly ONE non-overlapping proposal per physical container.
    """

    @staticmethod
    def propose(frame: np.ndarray) -> list[tuple[int, int, int, int, str]]:
        """
        Returns a list of candidate bounding boxes: (x1, y1, x2, y2, tag),
        ranked by visual prominence (centrality + area), with strict containment suppression.
        """
        h, w = frame.shape[:2]
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        sat = hsv[:, :, 1]
        val = hsv[:, :, 2]

        candidates = []

        # 1. Prominent colored container faces (Blue, Green, Yellow, Orange, Red)
        mask_col = ((sat > 35) & (val > 35) & (val < 240)).astype(np.uint8) * 255
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (15, 25))
        closed = cv2.morphologyEx(mask_col, cv2.MORPH_CLOSE, kernel)
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
                # Check if this board is already inside an existing container candidate
                inside_existing = False
                for _, cb, _, _ in candidates:
                    if cb[0] <= bx + 15 and cb[2] >= (bx + bw - 15) and cb[1] <= by + 15 and cb[3] >= (by + bh - 15):
                        inside_existing = True
                        break
                if not inside_existing:
                    # Expand around board to encompass the container body
                    pad_x = int(bw * 0.60)
                    pad_y_top = int(by * 0.35)
                    pad_y_bot = int(bh * 1.0)
                    cx1 = max(0, bx - pad_x)
                    cy1 = max(0, by - pad_y_top)
                    cx2 = min(w, bx + bw + pad_x)
                    cy2 = min(int(h * 0.90), by + bh + pad_y_bot)
                    area = (cx2 - cx1) * (cy2 - cy1)
                    center_dist = abs(((cx1 + cx2) / 2.0) - (w / 2.0))
                    score = area - (center_dist * 60)
                    candidates.append((score, (cx1, cy1, cx2, cy2), f"ID Board ({bw}x{bh})", area))

        if not candidates:
            return []

        # Sort by area descending so full container bodies take precedence over partial slivers
        candidates.sort(key=lambda x: x[3], reverse=True)

        # Non-maximum suppression with IoMin (containment) suppression
        final_proposals = []
        for score, b, tag, area in candidates:
            keep = True
            for fs, fb, ftag, farea in final_proposals:
                ix1 = max(b[0], fb[0])
                iy1 = max(b[1], fb[1])
                ix2 = min(b[2], fb[2])
                iy2 = min(b[3], fb[3])
                inter = max(0, ix2 - ix1) * max(0, iy2 - iy1)
                area_b = (b[2] - b[0]) * (b[3] - b[1])
                area_fb = (fb[2] - fb[0]) * (fb[3] - fb[1])
                min_a = min(area_b, area_fb)
                iomin = inter / float(min_a) if min_a > 0 else 0
                union = area_b + area_fb - inter
                iou = inter / float(union) if union > 0 else 0
                # Suppress if either IoU > 0.35 OR one box is contained in the other (IoMin > 0.35)
                if iou > 0.35 or iomin > 0.35:
                    keep = False
                    break
            if keep:
                final_proposals.append((score, b, tag, area))

        # Re-sort final proposals by visual prominence (score) for operator convenience
        final_proposals.sort(key=lambda x: x[0], reverse=True)
        return [(b[0], b[1], b[2], b[3], tag) for s, b, tag, a in final_proposals]


class HITLEnrollmentTool:
    """Environment-Agnostic HITL Asset Enrollment Interface."""

    def __init__(self, video_path: str, default_class: str = "container"):
        self.video_path = Path(video_path)
        if not self.video_path.exists():
            raise FileNotFoundError(f"Video file not found: {self.video_path}")

        self.default_class = default_class

        # Storage paths
        self.ref_images_dir = PROJECT_ROOT / "data" / "reference_images"
        self.yolo_images_dir = PROJECT_ROOT / "data" / "datasets" / "containers" / "images"
        self.yolo_labels_dir = PROJECT_ROOT / "data" / "datasets" / "containers" / "labels"
        self.log_file = PROJECT_ROOT / "data" / "enrollment_log.json"

        for d in [self.ref_images_dir, self.yolo_images_dir, self.yolo_labels_dir]:
            d.mkdir(parents=True, exist_ok=True)

        print("\n" + "=" * 65)
        print("  ASI PERCEPTION — HITL ENROLLMENT (AUTO-PROPOSAL MODE)")
        print("=" * 65)
        self.quality_checker = ImageQualityChecker()
        self.reid_engine = ReIDEngine("config/reid_config.yaml")
        self.reference_store = ReferenceStore("config/reid_config.yaml")

        self.cap = cv2.VideoCapture(str(self.video_path))
        if not self.cap.isOpened():
            raise RuntimeError(f"Could not open video stream: {self.video_path}")

        self.total_frames = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))
        self.native_fps = self.cap.get(cv2.CAP_PROP_FPS) or 10.0
        self.frame_w = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        self.frame_h = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

        print(f"[Video Info] File: {self.video_path.name}")
        print(f"[Video Info] Resolution: {self.frame_w}x{self.frame_h} @ {self.native_fps:.1f} FPS")
        print(f"[Video Info] Total Frames: {self.total_frames} (~{self.total_frames / self.native_fps / 60:.1f} min)")
        print(f"[Store Info] Already enrolled assets: {self.reference_store.list_assets()}")

        # Session state
        self.current_frame_idx = 0
        self.current_frame = None
        self.is_paused = False  # Start playing smoothly
        self.enrolled_count = len(self.reference_store.list_assets())
        self.session_enrolled = []

        # Auto-proposal & candidate selection
        self.proposer = ContainerProposer()
        self.auto_candidates = []  # List of (x1, y1, x2, y2, tag)
        self.selected_cand_idx = 0
        self.manual_override_bbox = None

        # Mouse selection state (manual override)
        self.drawing = False
        self.pt_start = None
        self.pt_current = None

        # Feedback banner
        self.banner_text = "AUTO-PROPOSAL ACTIVE — Press [ENTER] to Enroll highlighted asset"
        self.banner_color = (0, 255, 0)
        self.banner_timer = 0.0

        # Windows
        self.main_window = "HITL Asset Enrollment — SITE Assets Monitor"
        self.crop_window = "Candidate Crop Preview"
        cv2.namedWindow(self.main_window, cv2.WINDOW_NORMAL)
        cv2.resizeWindow(self.main_window, min(1280, self.frame_w), min(720, self.frame_h))
        cv2.setMouseCallback(self.main_window, self._on_mouse)

        # Tkinter root for input dialogs (hidden)
        self.tk_root = tk.Tk()
        self.tk_root.withdraw()

    # ------------------------------------------------------------------
    # Candidate Management
    # ------------------------------------------------------------------

    def _get_active_bbox(self) -> tuple[int, int, int, int] | None:
        """Returns the currently active bounding box (manual override or auto-candidate)."""
        if self.manual_override_bbox is not None:
            return self.manual_override_bbox
        if self.auto_candidates and self.selected_cand_idx < len(self.auto_candidates):
            c = self.auto_candidates[self.selected_cand_idx]
            return (c[0], c[1], c[2], c[3])
        return None

    def _update_proposals(self):
        """Run auto-detector on current frame if manual override is not active."""
        if self.current_frame is None or self.manual_override_bbox is not None:
            return
        self.auto_candidates = self.proposer.propose(self.current_frame)
        if self.selected_cand_idx >= len(self.auto_candidates):
            self.selected_cand_idx = 0
        self._update_crop_preview()

    # ------------------------------------------------------------------
    # Mouse Handler (Manual Override)
    # ------------------------------------------------------------------

    def _on_mouse(self, event, x, y, flags, param):
        """Allow operator to manually drag-and-drop a box if desired."""
        if not self.is_paused:
            return

        if event == cv2.EVENT_LBUTTONDOWN:
            self.drawing = True
            self.pt_start = (x, y)
            self.pt_current = (x, y)
            self.manual_override_bbox = None

        elif event == cv2.EVENT_MOUSEMOVE:
            if self.drawing:
                self.pt_current = (x, y)

        elif event == cv2.EVENT_LBUTTONUP:
            if self.drawing:
                self.drawing = False
                x1, y1 = self.pt_start
                x2, y2 = x, y
                xmin, xmax = max(0, min(x1, x2)), min(self.frame_w, max(x1, x2))
                ymin, ymax = max(0, min(y1, y2)), min(self.frame_h, max(y1, y2))

                if (xmax - xmin) >= 30 and (ymax - ymin) >= 30:
                    self.manual_override_bbox = (xmin, ymin, xmax, ymax)
                    self._update_crop_preview()
                    self._set_banner("Manual box selected! Press [ENTER] to Enroll, or [R] to Reset.", (0, 255, 255))
                else:
                    self.manual_override_bbox = None
                    self._update_proposals()

        elif event == cv2.EVENT_RBUTTONDOWN:
            self.manual_override_bbox = None
            self.drawing = False
            self._update_proposals()
            self._set_banner("Reset to auto-proposals.", (200, 200, 200))

    # ------------------------------------------------------------------
    # Crop Preview
    # ------------------------------------------------------------------

    def _update_crop_preview(self):
        """Show preview window of the selected candidate crop with quality score."""
        if self.current_frame is None:
            return

        bbox = self._get_active_bbox()
        if bbox is None:
            try:
                cv2.destroyWindow(self.crop_window)
            except Exception:
                pass
            return

        x1, y1, x2, y2 = bbox
        crop = self.current_frame[y1:y2, x1:x2].copy()
        if crop.size == 0:
            return

        # Quality check
        quality = self.quality_checker.check(crop)
        blur_var = quality.get("blur_score", 0.0)
        brightness = quality.get("brightness", 0.0)
        usable = quality.get("quality") != "UNUSABLE"

        # Scale preview
        preview_h = 240
        aspect = crop.shape[1] / max(1, crop.shape[0])
        preview_w = int(preview_h * aspect)
        crop_resized = cv2.resize(crop, (preview_w, preview_h))

        # Annotate quality info on preview
        status_color = (0, 255, 0) if usable else (0, 0, 255)
        status_txt = "QUALITY: OK" if usable else "WARNING: LOW QUALITY"
        cv2.putText(crop_resized, status_txt, (10, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.6, status_color, 2)
        cv2.putText(crop_resized, f"Blur: {blur_var:.1f} | Brightness: {brightness:.1f}", (10, 50),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255, 255, 255), 1)

        cv2.imshow(self.crop_window, crop_resized)

    # ------------------------------------------------------------------
    # Enrollment Logic
    # ------------------------------------------------------------------

    def enroll_current_asset(self):
        """Enroll the currently highlighted container candidate."""
        bbox = self._get_active_bbox()
        if self.current_frame is None or bbox is None:
            self._set_banner("No container candidate in view. Wait until one appears or draw box!", (0, 0, 255))
            return

        # Pause automatically during enrollment
        self.is_paused = True

        x1, y1, x2, y2 = bbox
        crop = self.current_frame[y1:y2, x1:x2].copy()

        suggested_id = f"CONT-{self.enrolled_count + 1:03d}"

        # Bring dialog to front
        self.tk_root.lift()
        self.tk_root.attributes("-topmost", True)

        asset_id = simpledialog.askstring(
            "Enroll Asset",
            f"Container Candidate ({x2 - x1}x{y2 - y1} px).\n\nEnter Asset ID (e.g., CONT-007, CONT-002):",
            initialvalue=suggested_id,
            parent=self.tk_root
        )

        if not asset_id:
            print(f"\n[HITL] Enter Asset ID (or press Enter for '{suggested_id}'): ", end="", flush=True)
            try:
                cli_id = input().strip()
                asset_id = cli_id if cli_id else suggested_id
            except Exception:
                asset_id = suggested_id

        asset_id = asset_id.strip().upper()
        if not asset_id:
            self._set_banner("Enrollment cancelled.", (200, 200, 200))
            return

        # 1. Extract 512-D visual embedding
        print(f"\n[HITL] Extracting OSNet visual fingerprint for '{asset_id}'...")
        embedding = self.reid_engine.extract_embedding(crop)
        if embedding is None:
            self._set_banner(f"ERROR: Could not extract embedding for '{asset_id}'!", (0, 0, 255))
            return

        # 2. Add to Reference Store
        success = self.reference_store.add_reference(
            asset_id=asset_id,
            class_name=self.default_class,
            embedding=embedding,
            auto_save=True
        )

        if not success:
            self._set_banner(f"ERROR: Failed to save '{asset_id}' to ReferenceStore!", (0, 0, 255))
            return

        # 3. Save reference image crop
        asset_ref_dir = self.ref_images_dir / asset_id
        asset_ref_dir.mkdir(parents=True, exist_ok=True)
        ref_idx = len(list(asset_ref_dir.glob("*.jpg"))) + 1
        ref_img_path = asset_ref_dir / f"ref_{ref_idx:03d}.jpg"
        cv2.imwrite(str(ref_img_path), crop, [cv2.IMWRITE_JPEG_QUALITY, 95])

        # 4. Save frame and YOLO label for detector fine-tuning
        sample_name = f"frame_{self.current_frame_idx:06d}"
        frame_save_path = self.yolo_images_dir / f"{sample_name}.jpg"
        cv2.imwrite(str(frame_save_path), self.current_frame, [cv2.IMWRITE_JPEG_QUALITY, 95])

        bx_center = ((x1 + x2) / 2.0) / self.frame_w
        by_center = ((y1 + y2) / 2.0) / self.frame_h
        bw = (x2 - x1) / self.frame_w
        bh = (y2 - y1) / self.frame_h

        label_save_path = self.yolo_labels_dir / f"{sample_name}.txt"
        with open(label_save_path, "a") as lf:
            lf.write(f"0 {bx_center:.6f} {by_center:.6f} {bw:.6f} {bh:.6f}\n")

        # 5. Log to session log
        record = {
            "asset_id": asset_id,
            "class_name": self.default_class,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "frame_idx": self.current_frame_idx,
            "timestamp_sec": round(self.current_frame_idx / self.native_fps, 2),
            "bbox_xyxy": [int(x1), int(y1), int(x2), int(y2)],
            "embedding_dim": int(len(embedding)),
            "ref_image": str(ref_img_path.relative_to(PROJECT_ROOT)),
            "yolo_image": str(frame_save_path.relative_to(PROJECT_ROOT)),
        }
        self.session_enrolled.append(record)
        self._append_to_log(record)

        self.enrolled_count = len(self.reference_store.list_assets())
        self._set_banner(f"SUCCESS: Enrolled '{asset_id}'! (Total: {self.enrolled_count}) - Press [SPACE] to resume", (0, 255, 0))
        print(f"[HITL] SUCCESS: Enrolled '{asset_id}' at frame {self.current_frame_idx} (Total enrolled: {self.enrolled_count})")

        # Clear manual override and re-propose
        self.manual_override_bbox = None
        self._update_proposals()

    def _append_to_log(self, record: dict):
        """Append record to enrollment_log.json."""
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

    def _set_banner(self, text: str, color: tuple):
        """Set message banner on the video overlay."""
        self.banner_text = text
        self.banner_color = color
        self.banner_timer = time.time() + 4.0

    # ------------------------------------------------------------------
    # Frame Navigation
    # ------------------------------------------------------------------

    def seek_relative(self, delta_frames: int):
        """Jump forward or backward by a number of frames."""
        target = max(0, min(self.total_frames - 1, self.current_frame_idx + delta_frames))
        self.cap.set(cv2.CAP_PROP_POS_FRAMES, target)
        self.current_frame_idx = target
        ret, frame = self.cap.read()
        if ret:
            self.current_frame = frame
        self.manual_override_bbox = None
        self._update_proposals()
        sec = self.current_frame_idx / self.native_fps
        self._set_banner(f"Jumped to frame {self.current_frame_idx} ({sec:.1f}s)", (0, 200, 255))

    # ------------------------------------------------------------------
    # Rendering HUD
    # ------------------------------------------------------------------

    def _draw_hud(self, display_img: np.ndarray) -> np.ndarray:
        """Render candidate boxes, active selection, and status HUD."""
        h, w = display_img.shape[:2]

        # 1. Render all auto-detected candidates
        active_bbox = self._get_active_bbox()

        if self.manual_override_bbox is not None:
            # Render manual box in Cyan
            mx1, my1, mx2, my2 = self.manual_override_bbox
            cv2.rectangle(display_img, (mx1, my1), (mx2, my2), (255, 255, 0), 2)
            cv2.putText(display_img, "Manual Selection [Press ENTER to Enroll]", (mx1, max(22, my1 - 8)),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.58, (255, 255, 0), 2)
        else:
            # Render auto proposals
            for idx, c in enumerate(self.auto_candidates):
                cx1, cy1, cx2, cy2, tag = c
                is_selected = (idx == self.selected_cand_idx)

                if is_selected:
                    # Highlight primary candidate with Neon Green + translucent overlay
                    overlay = display_img.copy()
                    cv2.rectangle(overlay, (cx1, cy1), (cx2, cy2), (0, 255, 0), -1)
                    cv2.addWeighted(overlay, 0.20, display_img, 0.80, 0, display_img)
                    cv2.rectangle(display_img, (cx1, cy1), (cx2, cy2), (0, 255, 0), 3)

                    label = f">> Candidate {idx + 1}: {tag} [Press ENTER to Enroll]"
                    cv2.putText(display_img, label, (cx1, max(25, cy1 - 10)),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.62, (0, 255, 0), 2)
                else:
                    # Secondary candidate in dashed/thinner amber
                    cv2.rectangle(display_img, (cx1, cy1), (cx2, cy2), (0, 165, 255), 1)
                    label = f"[{idx + 1}] {tag} (Press TAB)"
                    cv2.putText(display_img, label, (cx1, max(20, cy1 - 6)),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 165, 255), 1)

        # 2. Render in-progress mouse drag if active
        if self.drawing and self.pt_start and self.pt_current:
            cv2.rectangle(display_img, self.pt_start, self.pt_current, (0, 255, 255), 2)

        # 3. Top Info Bar
        cv2.rectangle(display_img, (0, 0), (w, 42), (20, 20, 20), -1)
        mode_str = "[PAUSED]" if self.is_paused else "[PLAYING]"
        mode_col = (0, 165, 255) if self.is_paused else (0, 255, 0)
        cv2.putText(display_img, mode_str, (12, 28), cv2.FONT_HERSHEY_SIMPLEX, 0.7, mode_col, 2)

        sec = self.current_frame_idx / self.native_fps
        time_str = f"Frame: {self.current_frame_idx}/{self.total_frames} ({sec:05.1f}s)"
        cv2.putText(display_img, time_str, (135, 28), cv2.FONT_HERSHEY_SIMPLEX, 0.52, (220, 220, 220), 1)

        enrolled_str = f"Enrolled: {self.enrolled_count} assets"
        cv2.putText(display_img, enrolled_str, (455, 28), cv2.FONT_HERSHEY_SIMPLEX, 0.58, (255, 255, 0), 2)

        cands_count = len(self.auto_candidates)
        cand_str = f"Spotted: {cands_count}" if cands_count > 0 else "Spotted: none"
        cand_col = (0, 255, 0) if cands_count > 0 else (140, 140, 140)
        cv2.putText(display_img, cand_str, (670, 28), cv2.FONT_HERSHEY_SIMPLEX, 0.52, cand_col, 1)

        # Shortcuts hint
        shortcuts = "[ENTER] Enroll | [SPACE] Pause | [TAB] Next | [Q] Quit"
        cv2.putText(display_img, shortcuts, (w - 480, 28),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.44, (180, 180, 180), 1)

        # 4. Bottom Banner (Dynamic status message)
        cv2.rectangle(display_img, (0, h - 38), (w, h), (15, 15, 15), -1)
        cv2.putText(display_img, self.banner_text, (15, h - 14),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.52, self.banner_color, 1)

        return display_img

    # ------------------------------------------------------------------
    # Main Event Loop
    # ------------------------------------------------------------------

    def run(self):
        """Run the automated HITL enrollment loop."""
        print("\n" + "=" * 65)
        print("  HITL ASSET ENROLLMENT (AUTO-PROPOSAL MODE) READY")
        print("=" * 65)
        print("  • The AI automatically detects and puts green boxes on containers!")
        print("  • Press [ENTER] to confirm & enroll the highlighted container")
        print("  • Press [TAB] to switch candidate if multiple containers are seen")
        print("  • Press [SPACE] to Play or Pause")
        print("  • Press [A] or [D] to seek -/+ 3 seconds")
        print("  • Press [Q] to finish and save summary")
        print("=" * 65 + "\n")

        ret, frame = self.cap.read()
        if not ret:
            print("[Error] Failed to read initial frame from video.")
            return
        self.current_frame = frame
        self.current_frame_idx = 0
        self._update_proposals()

        target_delay = int(1000 / self.native_fps)

        while True:
            if not self.is_paused:
                ret, frame = self.cap.read()
                if not ret:
                    print("\n[Video Complete] Reached end of video stream.")
                    self.is_paused = True
                    self._set_banner("End of video reached. Press [Q] to quit.", (0, 165, 255))
                else:
                    self.current_frame = frame
                    self.current_frame_idx += 1
                    # Update auto-proposals every frame while playing
                    self._update_proposals()

            display = self.current_frame.copy()
            display = self._draw_hud(display)
            cv2.imshow(self.main_window, display)

            key = cv2.waitKey(1 if self.is_paused else target_delay) & 0xFF

            if key in [ord("q"), ord("Q"), 27]:  # Q or ESC
                break

            elif key == ord(" "):  # Spacebar toggle pause
                self.is_paused = not self.is_paused
                if self.is_paused:
                    self._set_banner("PAUSED — Press [ENTER] to enroll, [TAB] to switch, or [SPACE] to Play", (0, 165, 255))
                else:
                    self._set_banner("PLAYING — Press [ENTER] anytime a container is highlighted to enroll!", (0, 255, 0))

            elif key in [13, 10, ord("e"), ord("E")]:  # ENTER or E -> Enroll active candidate
                self.enroll_current_asset()

            elif key == 9:  # TAB -> Cycle through candidates
                if self.auto_candidates:
                    self.selected_cand_idx = (self.selected_cand_idx + 1) % len(self.auto_candidates)
                    self.manual_override_bbox = None
                    self._update_crop_preview()
                    self._set_banner(f"Switched to candidate {self.selected_cand_idx + 1}/{len(self.auto_candidates)}", (0, 255, 255))

            elif key in [ord("r"), ord("R")]:  # Reset to auto proposals
                self.manual_override_bbox = None
                self._update_proposals()
                self._set_banner("Reset to auto-proposals.", (200, 200, 200))

            elif key in [ord("d"), ord("D")]:  # Forward 30 frames
                self.seek_relative(30)

            elif key in [ord("a"), ord("A")]:  # Backward 30 frames
                self.seek_relative(-30)

            elif key == 83:  # Right arrow
                self.seek_relative(5)

            elif key == 81:  # Left arrow
                self.seek_relative(-5)

            elif key in [ord("l"), ord("L")]:  # List assets
                enrolled = self.reference_store.list_assets()
                print(f"\n[Store] Currently enrolled assets ({len(enrolled)}): {enrolled}")

        # Cleanup
        self.cap.release()
        cv2.destroyAllWindows()
        self.tk_root.destroy()

        # Print final session report
        print("\n" + "=" * 65)
        print("  HITL ENROLLMENT SESSION SUMMARY")
        print("=" * 65)
        all_assets = self.reference_store.list_assets()
        print(f"  • Total Assets in Gallery : {len(all_assets)}")
        print(f"  • Enrolled This Session   : {len(self.session_enrolled)}")
        if self.session_enrolled:
            for item in self.session_enrolled:
                print(f"    - {item['asset_id']} ({item['class_name']}) at frame {item['frame_idx']} ({item['timestamp_sec']}s)")
        print(f"  • Fingerprints Saved To   : data/reference_db/*.npz")
        print(f"  • Visual Proof Crops In   : data/reference_images/")
        print(f"  • YOLO Training Data In   : data/datasets/containers/")
        print(f"  • Session Audit Log In    : data/enrollment_log.json")
        print("=" * 65 + "\n")


def main():
    parser = argparse.ArgumentParser(description="HITL Asset Enrollment Tool (Auto-Proposal Mode)")
    default_vid = r"C:\Users\GANGARI DHRUVAVEER\Downloads\WhatsApp Video 2026-10-29 at 10.44.12 AM (1).mp4"
    parser.add_argument("--video", "-v", default=default_vid, help="Path to video file")
    parser.add_argument("--class-name", "-c", default="container", help="Default asset class name")
    args = parser.parse_args()

    tool = HITLEnrollmentTool(args.video, args.class_name)
    tool.run()


if __name__ == "__main__":
    main()
