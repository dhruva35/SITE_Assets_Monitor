"""
Quick Demo — Test YOLOv8n Pretrained Detection

Run this to see the detector working right now with the pretrained COCO model.
This proves your pipeline works end-to-end before you train a custom model.

Usage:
    python scripts/demo_detection.py                     # Use webcam
    python scripts/demo_detection.py --image photo.jpg   # Use an image
    python scripts/demo_detection.py --video video.mp4   # Use a video file
"""

import sys
import os
import argparse
import time

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

import cv2
import numpy as np
from src.image_quality import ImageQualityChecker
from src.evidence_generator import EvidenceGenerator


def run_demo(source, save_output=True):
    """Run detection demo on image, video, or webcam."""
    from ultralytics import YOLO

    print("=" * 60)
    print("  ASI Perception — Detection Demo (Pretrained YOLOv8n)")
    print("=" * 60)

    # Load model
    print("\n[1] Loading custom trained ONNX model...")
    model_path = os.path.join(PROJECT_ROOT, "models", "detection", "yolo_best.onnx")
    model = YOLO(model_path, task="detect")
    print("    ✓ Model loaded")

    # Load quality checker
    quality_checker = ImageQualityChecker()
    evidence_gen = EvidenceGenerator()

    # Determine source type
    if source is None or source == "0":
        source = 0
        print("\n[2] Opening webcam...")
    elif os.path.isfile(source):
        ext = os.path.splitext(source)[1].lower()
        if ext in ['.jpg', '.jpeg', '.png', '.bmp', '.webp']:
            print(f"\n[2] Loading image: {source}")
            return run_on_image(source, model, quality_checker, evidence_gen)
        else:
            print(f"\n[2] Opening video: {source}")
    else:
        print(f"\n[2] Opening source: {source}")

    # Video / webcam mode
    cap = cv2.VideoCapture(source)
    if not cap.isOpened():
        print(f"    ✗ Could not open source: {source}")
        return

    frame_count = 0
    fps_times = []

    print("    Press 'q' to quit, 's' to save current frame as evidence\n")

    while True:
        ret, frame = cap.read()
        if not ret:
            # Loop the video infinitely back to frame 0
            cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
            continue

        frame_count += 1
        start_time = time.time()

        # Quality check
        quality = quality_checker.check(frame)

        # Run detection
        results = model(frame, conf=0.5, verbose=False)
        annotated = results[0].plot()

        # Calculate FPS
        elapsed = time.time() - start_time
        fps_times.append(elapsed)
        if len(fps_times) > 30:
            fps_times.pop(0)
        avg_fps = 1.0 / (sum(fps_times) / len(fps_times))

        # Draw info overlay
        info_text = f"FPS: {avg_fps:.1f} | Quality: {quality['quality']} | Detections: {len(results[0].boxes)}"
        cv2.putText(annotated, info_text, (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)

        # Show
        cv2.imshow("ASI Perception Demo", annotated)

        key = cv2.waitKey(1) & 0xFF
        if key == ord('q'):
            break
        elif key == ord('s'):
            # Save evidence for all detections in current frame
            print(f"\n    [Evidence] Saving frame {frame_count}...")
            for box in results[0].boxes:
                det = {
                    "object_class": results[0].names[int(box.cls[0])],
                    "bbox_xyxy": [int(x) for x in box.xyxy[0].tolist()],
                    "detection_confidence": float(box.conf[0]),
                    "asset_id": "DEMO",
                }
                ev = evidence_gen.capture(frame, det, annotated, "yolov8n-pretrained")
                print(f"    Saved: {ev['evidence_refs'][0]}")

    cap.release()
    cv2.destroyAllWindows()
    print(f"\n    Total frames processed: {frame_count}")
    print(f"    Average FPS: {avg_fps:.1f}")


def run_on_image(image_path, model, quality_checker, evidence_gen):
    """Run detection on a single image."""
    frame = cv2.imread(image_path)
    if frame is None:
        print(f"    ✗ Could not read image: {image_path}")
        return

    # Quality check
    quality = quality_checker.check(frame)
    print(f"\n[3] Image Quality: {quality['quality']}")
    print(f"    Blur Score:  {quality['blur_score']}")
    print(f"    Brightness:  {quality['brightness']}")

    # Detect
    print("\n[4] Running detection...")
    start = time.time()
    results = model(frame, conf=0.5, verbose=False)
    elapsed = time.time() - start

    annotated = results[0].plot()
    detections = results[0].boxes

    print(f"    Inference time: {elapsed * 1000:.0f}ms")
    print(f"    Detections: {len(detections)}")

    for i, box in enumerate(detections):
        cls = results[0].names[int(box.cls[0])]
        conf = float(box.conf[0])
        bbox = [int(x) for x in box.xyxy[0].tolist()]
        print(f"    [{i+1}] {cls} — {conf:.2f} — bbox: {bbox}")

        # Save evidence
        det = {
            "object_class": cls,
            "bbox_xyxy": bbox,
            "detection_confidence": conf,
            "asset_id": "DEMO",
        }
        ev = evidence_gen.capture(frame, det, annotated, "yolov8n-pretrained")

    # Save annotated output
    output_path = os.path.join("evidence", "demo_output.jpg")
    os.makedirs("evidence", exist_ok=True)
    cv2.imwrite(output_path, annotated)
    print(f"\n[5] Annotated image saved to: {output_path}")

    # Show image
    cv2.imshow("ASI Perception Demo", annotated)
    print("    Press any key to close...")
    cv2.waitKey(0)
    cv2.destroyAllWindows()


def main():
    parser = argparse.ArgumentParser(description="ASI Perception Detection Demo")
    parser.add_argument("--image", type=str, help="Path to test image")
    parser.add_argument("--video", type=str, help="Path to test video")
    parser.add_argument("--webcam", action="store_true", help="Use webcam")
    args = parser.parse_args()

    if args.image:
        source = args.image
    elif args.video:
        source = args.video
    else:
        source = "0"

    run_demo(source)


if __name__ == "__main__":
    main()
