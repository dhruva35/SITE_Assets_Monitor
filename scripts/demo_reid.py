"""
ASI Perception System — End-to-End Re-Identification Demo
Week 2 Deliverable

This script proves the full Re-ID pipeline works end-to-end:

  Camera Frame
      │
      ▼
  Image Quality Check  (image_quality.py)
      │
      ▼
  YOLOv8 Detection     (detector.py)
      │
      ▼
  Crop + Embed         (reid_engine.py  ← OSNet ONNX)
      │
      ▼
  Database Match       (reference_store.py)
      │
      ▼
  Identity Status      CONFIRMED / PROBABLE / AMBIGUOUS / UNKNOWN

No real site data is needed: we use our Kaggle validation images as
stand-in assets. Two images of the same type will produce a high
similarity score; two different types will produce a low score.

Usage:
    python scripts/demo_reid.py
    python scripts/demo_reid.py --images 10
"""

import sys
import os
import argparse
import random
import cv2
import numpy as np
from pathlib import Path

# ---------------------------------------------------------------------------
# Path setup — allow running from project root
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.image_quality import ImageQualityChecker
from src.detector import Detector
from src.reid_engine import ReIDEngine
from src.reference_store import ReferenceStore


# ---------------------------------------------------------------------------
# ANSI colours for terminal output
# ---------------------------------------------------------------------------
class C:
    RESET  = "\033[0m"
    BOLD   = "\033[1m"
    GREEN  = "\033[92m"
    YELLOW = "\033[93m"
    RED    = "\033[91m"
    CYAN   = "\033[96m"
    GREY   = "\033[90m"
    BLUE   = "\033[94m"

def status_color(status: str) -> str:
    return {
        "CONFIRMED":  C.GREEN,
        "PROBABLE":   C.YELLOW,
        "AMBIGUOUS":  C.YELLOW,
        "UNKNOWN":    C.GREY,
        "UNUSABLE":   C.RED,
    }.get(status, C.RESET)


# ---------------------------------------------------------------------------
# Main demo
# ---------------------------------------------------------------------------

def run_demo(num_images: int = 8):
    print(f"\n{C.BOLD}{C.CYAN}{'='*60}{C.RESET}")
    print(f"{C.BOLD}{C.CYAN}  ASI Perception System — Re-ID Pipeline Demo{C.RESET}")
    print(f"{C.BOLD}{C.CYAN}{'='*60}{C.RESET}\n")

    # ----- 1. Load all components -----
    print(f"{C.BOLD}[1/4] Loading pipeline components...{C.RESET}")
    quality = ImageQualityChecker()
    detector = Detector(config_path="config/detection_config.yaml")
    reid = ReIDEngine(config_path="config/reid_config.yaml")
    store = ReferenceStore(config_path="config/reid_config.yaml")

    if not reid.is_loaded:
        print(f"{C.RED}ERROR: OSNet model not found at '{reid.model_path}'.{C.RESET}")
        print("Please place 'reid_backbone_best.onnx' in models/reid/ and re-run.")
        sys.exit(1)

    print(f"  {C.GREEN}✓{C.RESET} Image quality checker ready")
    print(f"  {C.GREEN}✓{C.RESET} YOLOv8 detector ready  (model: {detector.model is not None})")
    print(f"  {C.GREEN}✓{C.RESET} OSNet Re-ID engine ready")
    print(f"  {C.GREEN}✓{C.RESET} Reference store ready   ({store.asset_count} existing assets)\n")

    # ----- 2. Select images from the validation set -----
    val_dir = Path("data/datasets/construction-equipment/valid/images")
    if not val_dir.exists():
        print(f"{C.RED}ERROR: Validation image folder not found: {val_dir}{C.RESET}")
        sys.exit(1)

    all_images = sorted(val_dir.glob("*.jpg")) + sorted(val_dir.glob("*.png"))
    if len(all_images) < num_images:
        print(f"{C.YELLOW}Only {len(all_images)} images available. Using all.{C.RESET}")
        num_images = len(all_images)

    # Pick images randomly, ensuring we have at least two from which to build
    # references and test queries
    random.seed(42)
    selected = random.sample(all_images, min(num_images * 3, len(all_images)))

    print(f"{C.BOLD}[2/4] Building reference database from first {num_images} detectable images...{C.RESET}")

    registered = []   # list of (asset_id, class_name, ref_image_path)
    ref_count  = 0

    for img_path in selected:
        if ref_count >= num_images:
            break

        frame = cv2.imread(str(img_path))
        if frame is None:
            continue

        # Quality gate
        if not quality.is_usable(frame):
            continue

        # Detect assets
        detections = detector.detect(frame)
        asset_dets = [d for d in detections if d["is_asset"]]
        if not asset_dets:
            continue

        # Take the highest-confidence detection as our reference crop
        best_det = max(asset_dets, key=lambda d: d["detection_confidence"])
        crops = reid.crop_detections(frame, [best_det])
        if not crops or not crops[0]["valid"]:
            continue

        crop = crops[0]["crop"]
        embedding = reid.extract_embedding(crop)
        if embedding is None:
            continue

        # Register this as a known asset using the filename as a stand-in ID
        asset_id   = f"{best_det['object_class'].upper().replace(' ', '_')}-{ref_count+1:03d}"
        class_name = best_det["object_class"]
        store.add_reference(asset_id, class_name, embedding, auto_save=False)
        registered.append((asset_id, class_name, img_path))
        ref_count += 1

        print(f"  {C.GREEN}✓{C.RESET} Registered {C.BOLD}{asset_id}{C.RESET} "
              f"({class_name}, conf={best_det['detection_confidence']:.2f}) "
              f"← {img_path.name}")

    if not registered:
        print(f"{C.RED}No assets could be registered. Try increasing --images.{C.RESET}")
        sys.exit(1)

    print(f"\n  {C.CYAN}Total registered: {store.asset_count} asset(s){C.RESET}\n")

    # ----- 3. Run query phase -----
    print(f"{C.BOLD}[3/4] Running Re-ID queries on fresh images...{C.RESET}\n")
    print(f"  {'Image':<42} {'Detected Class':<22} {'Matched ID':<26} {'Score':>6}  {'Status'}")
    print(f"  {'-'*42} {'-'*22} {'-'*26} {'-'*6}  {'-'*12}")

    # Pick the remaining images (not used for registration) as query images
    used_paths = {r[2] for r in registered}
    query_images = [p for p in selected if p not in used_paths][:num_images]

    results_summary = {"CONFIRMED": 0, "PROBABLE": 0, "AMBIGUOUS": 0, "UNKNOWN": 0, "NO_DETECTION": 0}

    for img_path in query_images:
        frame = cv2.imread(str(img_path))
        if frame is None:
            continue

        if not quality.is_usable(frame):
            print(f"  {img_path.name:<42} {C.RED}UNUSABLE (quality){C.RESET}")
            continue

        detections = detector.detect(frame)
        asset_dets = [d for d in detections if d["is_asset"]]

        if not asset_dets:
            print(f"  {img_path.name:<42} {'No asset detected':<22}")
            results_summary["NO_DETECTION"] += 1
            continue

        best_det = max(asset_dets, key=lambda d: d["detection_confidence"])
        crops = reid.crop_detections(frame, [best_det])

        if not crops or not crops[0]["valid"]:
            print(f"  {img_path.name:<42} {best_det['object_class']:<22} {'Crop too small'}")
            continue

        embedding = reid.extract_embedding(crops[0]["crop"])
        if embedding is None:
            continue

        result = store.query(embedding, class_filter=best_det["object_class"])
        status = result["identity_status"]
        col = status_color(status)
        asset_id = result["asset_id"] or "—"
        score = result["similarity_score"]

        print(f"  {img_path.name:<42} {best_det['object_class']:<22} "
              f"{asset_id:<26} {score:>6.3f}  {col}{C.BOLD}{status}{C.RESET}")

        results_summary[status] = results_summary.get(status, 0) + 1

    # ----- 4. Summary -----
    print(f"\n{C.BOLD}[4/4] Results Summary{C.RESET}")
    print(f"  {C.GREEN}CONFIRMED  : {results_summary['CONFIRMED']}{C.RESET}")
    print(f"  {C.YELLOW}PROBABLE   : {results_summary['PROBABLE']}{C.RESET}")
    print(f"  {C.YELLOW}AMBIGUOUS  : {results_summary['AMBIGUOUS']}{C.RESET}")
    print(f"  {C.GREY}UNKNOWN    : {results_summary['UNKNOWN']}{C.RESET}")
    print(f"  {C.GREY}NO ASSET   : {results_summary['NO_DETECTION']}{C.RESET}")

    total_decided = results_summary["CONFIRMED"] + results_summary["PROBABLE"]
    total_queries = sum(results_summary.values())
    if total_queries > 0:
        rate = total_decided / total_queries * 100
        print(f"\n  {C.BOLD}Positive ID rate (CONFIRMED + PROBABLE): {rate:.0f}%{C.RESET}")

    print(f"\n{C.BOLD}{C.CYAN}{'='*60}{C.RESET}")
    print(f"{C.BOLD}{C.GREEN}  Pipeline test complete.{C.RESET}")
    print(f"{C.BOLD}{C.CYAN}{'='*60}{C.RESET}\n")

    # Clean up temp references from this demo run (don't pollute real DB)
    print(f"{C.GREY}  Cleaning up demo references from store...{C.RESET}")
    for asset_id, _, _ in registered:
        store.remove_asset(asset_id)
    print(f"{C.GREY}  Done. Real database is unchanged.{C.RESET}\n")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="ASI Re-ID Pipeline Demo — tests the full detection → fingerprint → match chain."
    )
    parser.add_argument(
        "--images", type=int, default=8,
        help="Number of images to register as references (default: 8)"
    )
    args = parser.parse_args()
    run_demo(num_images=args.images)
