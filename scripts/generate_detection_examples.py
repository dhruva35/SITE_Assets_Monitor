"""
Generate Detection Example Images
Runs the custom YOLO ONNX model on a diverse sample of site images
from the validation dataset and saves the best annotated outputs for
client presentation.

Usage:
    python scripts/generate_detection_examples.py
"""

import os
import sys
import random
import shutil

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

import cv2
import numpy as np

# ── Config ────────────────────────────────────────────────────────────────────
VAL_IMAGES_DIR = os.path.join(
    PROJECT_ROOT, "data", "datasets", "construction-equipment", "valid", "images"
)
MODEL_PATH = os.path.join(PROJECT_ROOT, "models", "detection", "yolo_best.onnx")
OUTPUT_DIR = os.path.join(PROJECT_ROOT, "evidence", "detection_examples")

CONF_THRESHOLD  = 0.40   # Lower to catch more classes
NUM_SAMPLES     = 40     # How many images to run inference on
MIN_DETECTIONS  = 1      # Minimum detections to keep an image
TOP_N_SAVE      = 12     # How many final images to save
# ─────────────────────────────────────────────────────────────────────────────


def draw_detections(frame, results, class_names):
    """Draw bounding boxes with labels on frame."""
    # Color palette — one per class (BGR)
    palette = [
        (0,   200, 255), (50,  255, 100), (255, 100, 50 ),
        (255, 50,  200), (100, 50,  255), (50,  255, 200),
        (200, 255, 50 ), (0,   150, 255), (255, 200, 0  ),
        (0,   255, 150), (200, 0,   255), (255, 80,  80 ),
        (80,  255, 255), (255, 160, 0  ), (0,   80,  255),
        (180, 255, 180), (255, 0,   130),
    ]

    annotated = frame.copy()
    boxes  = results[0].boxes
    h, w   = annotated.shape[:2]

    for box in boxes:
        cls_idx  = int(box.cls[0])
        conf     = float(box.conf[0])
        label    = class_names.get(cls_idx, f"class_{cls_idx}")
        color    = palette[cls_idx % len(palette)]
        x1,y1,x2,y2 = [int(v) for v in box.xyxy[0].tolist()]

        # Box
        cv2.rectangle(annotated, (x1, y1), (x2, y2), color, 3)

        # Label background
        text     = f"{label}  {conf:.2f}"
        font     = cv2.FONT_HERSHEY_SIMPLEX
        scale    = max(0.55, min(0.85, w / 1920))
        thick    = 2
        (tw, th), _ = cv2.getTextSize(text, font, scale, thick)
        lx, ly   = x1, max(y1 - 10, th + 8)
        cv2.rectangle(annotated, (lx - 2, ly - th - 6), (lx + tw + 4, ly + 2), color, -1)
        cv2.putText(annotated,   text, (lx, ly - 2), font, scale, (0, 0, 0), thick, cv2.LINE_AA)

    # System watermark
    watermark = "ASI Perception  |  Detection Demo"
    cv2.rectangle(annotated, (0, 0), (len(watermark) * 13 + 10, 36), (20, 20, 20), -1)
    cv2.putText(annotated, watermark, (6, 24),
                cv2.FONT_HERSHEY_SIMPLEX, 0.65, (0, 220, 255), 2, cv2.LINE_AA)

    return annotated


def run():
    from ultralytics import YOLO

    print("=" * 62)
    print("  ASI Perception — Batch Detection Example Generator")
    print("=" * 62)

    # ── Load model ────────────────────────────────────────────────
    print(f"\n[1] Loading model: {MODEL_PATH}")
    model = YOLO(MODEL_PATH, task="detect")

    class_names = {
        0: "Dump Truck",    1: "Excavator",        2: "Motor Grader",
        3: "Roller",        4: "Crane Manipulator", 5: "Gazelle",
        6: "Forklift",      7: "Bucket Loader",     8: "Mixer",
        9: "Tanker",       10: "Bulldozer",        11: "Cleaning Equip",
       12: "Truck",        13: "Trailer",          14: "Forklift (tall)",
       15: "Bucket Loader (Std)", 16: "Auto Crane",
    }
    print(f"    ✓ Model loaded  |  {len(class_names)} classes")

    # ── Collect images ─────────────────────────────────────────────
    all_images = sorted([
        f for f in os.listdir(VAL_IMAGES_DIR)
        if f.lower().endswith((".jpg", ".jpeg", ".png"))
    ])
    print(f"\n[2] Found {len(all_images)} validation images")

    # Sample evenly across the sorted list to get temporal diversity
    step    = max(1, len(all_images) // NUM_SAMPLES)
    sampled = [all_images[i] for i in range(0, len(all_images), step)][:NUM_SAMPLES]
    print(f"    Sampling {len(sampled)} images for inference...")

    # ── Run inference ──────────────────────────────────────────────
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    results_list = []  # (num_dets, confidence_sum, annotated_frame, filename)

    for idx, fname in enumerate(sampled, 1):
        img_path = os.path.join(VAL_IMAGES_DIR, fname)
        frame    = cv2.imread(img_path)
        if frame is None:
            continue

        results  = model(frame, conf=CONF_THRESHOLD, verbose=False)
        boxes    = results[0].boxes
        num_dets = len(boxes)

        if num_dets < MIN_DETECTIONS:
            continue

        conf_sum  = sum(float(b.conf[0]) for b in boxes)
        annotated = draw_detections(frame, results, class_names)

        results_list.append((num_dets, conf_sum, annotated, fname))
        print(f"    [{idx:02d}/{len(sampled)}] {fname[-40:]:40s}  →  {num_dets} detection(s)")

    # ── Pick the TOP_N_SAVE best frames ───────────────────────────
    # Sort by (num_dets DESC, conf_sum DESC)
    results_list.sort(key=lambda x: (x[0], x[1]), reverse=True)
    top_results = results_list[:TOP_N_SAVE]

    print(f"\n[3] Saving top {len(top_results)} annotated images to:\n    {OUTPUT_DIR}\n")

    saved_paths = []
    for rank, (num_dets, conf_sum, annotated, fname) in enumerate(top_results, 1):
        out_name = f"detection_example_{rank:02d}_{fname}"
        out_path = os.path.join(OUTPUT_DIR, out_name)
        cv2.imwrite(out_path, annotated, [cv2.IMWRITE_JPEG_QUALITY, 92])
        saved_paths.append(out_path)
        avg_conf = conf_sum / num_dets if num_dets else 0
        print(f"    ✓ [{rank:02d}]  {num_dets} det(s)  avg_conf={avg_conf:.2f}  →  {out_name}")

    print("\n" + "=" * 62)
    print(f"  Done! {len(saved_paths)} detection examples saved.")
    print(f"  Folder: {OUTPUT_DIR}")
    print("=" * 62)


if __name__ == "__main__":
    run()
