"""
Quick Verification Script — Run this to test that your setup works.

This script:
1. Loads the detector with a pretrained YOLOv8n model
2. Runs the image quality checker
3. Runs detection on a test image (or your webcam)
4. Saves annotated output + evidence package

Usage:
    python scripts/verify_setup.py                    # Use webcam
    python scripts/verify_setup.py --image path.jpg   # Use an image file
"""

import sys
import os
import argparse

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.detector import Detector
from src.image_quality import ImageQualityChecker
from src.evidence_generator import EvidenceGenerator
import cv2


def main():
    parser = argparse.ArgumentParser(description="Verify ASI Perception setup")
    parser.add_argument("--image", type=str, default=None, help="Path to test image")
    args = parser.parse_args()

    print("=" * 60)
    print("  ASI Perception System — Setup Verification")
    print("=" * 60)

    # 1. Load modules
    print("\n[1/4] Loading Image Quality Checker...")
    quality_checker = ImageQualityChecker()
    print("  ✓ Image Quality Checker loaded")

    print("\n[2/4] Loading Detector...")
    detector = Detector()
    if detector.is_loaded:
        print("  ✓ Detector loaded successfully")
    else:
        print("  ✗ Detector failed to load. Check ultralytics installation.")
        return

    print("\n[3/4] Loading Evidence Generator...")
    evidence_gen = EvidenceGenerator()
    print("  ✓ Evidence Generator loaded")

    # 2. Get test image
    print("\n[4/4] Getting test image...")
    if args.image:
        frame = cv2.imread(args.image)
        if frame is None:
            print(f"  ✗ Could not read image: {args.image}")
            return
        print(f"  ✓ Loaded image: {args.image} ({frame.shape[1]}x{frame.shape[0]})")
    else:
        print("  Capturing from webcam (press any key to continue)...")
        cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            print("  ✗ Could not open webcam. Try: python scripts/verify_setup.py --image path.jpg")
            return
        ret, frame = cap.read()
        cap.release()
        if not ret:
            print("  ✗ Could not capture frame from webcam.")
            return
        print(f"  ✓ Captured webcam frame ({frame.shape[1]}x{frame.shape[0]})")

    # 3. Check image quality
    print("\n" + "-" * 60)
    print("Image Quality Check:")
    quality = quality_checker.check(frame)
    print(f"  Quality:    {quality['quality']}")
    print(f"  Blur Score: {quality['blur_score']} (higher = sharper)")
    print(f"  Brightness: {quality['brightness']} (0-255)")
    if quality['issues']:
        print(f"  Issues:     {', '.join(quality['issues'])}")

    # 4. Run detection
    print("\n" + "-" * 60)
    print("Detection Results:")
    detections, annotated = detector.detect_and_draw(frame)
    print(f"  Total detections: {len(detections)}")
    for i, det in enumerate(detections):
        print(f"  [{i+1}] {det['object_class']} — confidence: {det['detection_confidence']:.2f} — bbox: {det['bbox_xyxy']}")

    # 5. Save evidence for first detection (if any)
    if detections:
        print("\n" + "-" * 60)
        print("Evidence Capture:")
        evidence = evidence_gen.capture(
            frame=frame,
            detection=detections[0],
            annotated_frame=annotated,
            model_version="setup-verification"
        )
        print(f"  Evidence saved:")
        for ref in evidence["evidence_refs"]:
            print(f"    → {ref}")

    # 6. Save annotated output
    output_path = "evidence/verification_output.jpg"
    os.makedirs("evidence", exist_ok=True)
    cv2.imwrite(output_path, annotated)
    print(f"\n  Annotated image saved to: {output_path}")

    print("\n" + "=" * 60)
    print("  ✅ SETUP VERIFICATION COMPLETE")
    print("  All modules loaded and working correctly.")
    print("=" * 60)


if __name__ == "__main__":
    main()
