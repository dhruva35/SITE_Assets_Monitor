"""
Batch Video Annotation Script
Reads all raw MP4 videos from the client's records folder, runs the 
YOLOv8 custom ONNX model, and saves annotated MP4 files.
"""

import os
import sys
import cv2

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

# ── Config ────────────────────────────────────────────────────────────────────
INPUT_DIR = r"C:\Users\GANGARI DHRUVAVEER\Downloads\site_records"
OUTPUT_DIR = os.path.join(PROJECT_ROOT, "evidence", "video_examples")
MODEL_PATH = os.path.join(PROJECT_ROOT, "models", "detection", "yolo_best.onnx")

CONF_THRESHOLD = 0.40
# ─────────────────────────────────────────────────────────────────────────────

def draw_detections(frame, results, class_names):
    palette = [
        (0, 200, 255), (50, 255, 100), (255, 100, 50),
        (255, 50, 200), (100, 50, 255), (50, 255, 200),
        (200, 255, 50), (0, 150, 255), (255, 200, 0),
        (0, 255, 150), (200, 0, 255), (255, 80, 80),
        (80, 255, 255), (255, 160, 0), (0, 80, 255),
        (180, 255, 180), (255, 0, 130),
    ]

    annotated = frame.copy()
    boxes = results[0].boxes
    h, w = annotated.shape[:2]

    for box in boxes:
        cls_idx = int(box.cls[0])
        conf = float(box.conf[0])
        label = class_names.get(cls_idx, f"class_{cls_idx}")
        color = palette[cls_idx % len(palette)]
        x1, y1, x2, y2 = [int(v) for v in box.xyxy[0].tolist()]

        cv2.rectangle(annotated, (x1, y1), (x2, y2), color, 3)

        text = f"{label} {conf:.2f}"
        font = cv2.FONT_HERSHEY_SIMPLEX
        scale = max(0.55, min(0.85, w / 1920))
        (tw, th), _ = cv2.getTextSize(text, font, scale, 2)
        lx, ly = x1, max(y1 - 10, th + 8)
        cv2.rectangle(annotated, (lx - 2, ly - th - 6), (lx + tw + 4, ly + 2), color, -1)
        cv2.putText(annotated, text, (lx, ly - 2), font, scale, (0, 0, 0), 2, cv2.LINE_AA)

    watermark = "ASI Perception | Live Detection"
    cv2.rectangle(annotated, (0, 0), (len(watermark) * 14 + 10, 36), (20, 20, 20), -1)
    cv2.putText(annotated, watermark, (6, 24), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 220, 255), 2, cv2.LINE_AA)

    return annotated

def run():
    from ultralytics import YOLO

    print(f"Loading Model: {MODEL_PATH}")
    model = YOLO(MODEL_PATH, task="detect")
    
    class_names = {
        0: "Dump Truck", 1: "Excavator", 2: "Motor Grader", 3: "Roller", 4: "Crane Manipulator", 5: "Gazelle",
        6: "Forklift", 7: "Bucket Loader", 8: "Mixer", 9: "Tanker", 10: "Bulldozer", 11: "Cleaning Equip",
        12: "Truck", 13: "Trailer", 14: "Forklift (tall)", 15: "Bucket Loader (Std)", 16: "Auto Crane",
    }

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    video_files = [f for f in os.listdir(INPUT_DIR) if f.endswith('.mp4')]
    print(f"Found {len(video_files)} videos in {INPUT_DIR}")

    for vid_name in video_files:
        in_path = os.path.join(INPUT_DIR, vid_name)
        out_name = vid_name.replace(".mp4", "_annotated.mp4")
        out_path = os.path.join(OUTPUT_DIR, out_name)

        cap = cv2.VideoCapture(in_path)
        if not cap.isOpened():
            print(f"Failed to open {vid_name}")
            continue

        w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        fps = int(cap.get(cv2.CAP_PROP_FPS))
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

        # Use mp4v codec for standard mp4 saving
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        out = cv2.VideoWriter(out_path, fourcc, fps, (w, h))

        print(f"\nProcessing {vid_name} ({total_frames} frames)...")
        
        frame_idx = 0
        while True:
            ret, frame = cap.read()
            if not ret:
                break
                
            results = model(frame, conf=CONF_THRESHOLD, verbose=False)
            annotated = draw_detections(frame, results, class_names)
            out.write(annotated)
            
            frame_idx += 1
            if frame_idx % 30 == 0:
                print(f"  -> Processed {frame_idx}/{total_frames} frames")

        cap.release()
        out.release()
        print(f"✓ Saved {out_name} to {OUTPUT_DIR}")

if __name__ == "__main__":
    run()
