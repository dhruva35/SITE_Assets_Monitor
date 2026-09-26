"""
ASI Perception System — YOLO Detection Wrapper
Spec: PER-DET-001 → 005

Wraps the YOLO model (Ultralytics) into a clean API.
Input: image frame
Output: list of detections with class, bbox, confidence
"""

import cv2
import numpy as np
import yaml
from pathlib import Path


class Detector:
    """
    YOLO-based object detector for construction site assets.
    
    Wraps Ultralytics YOLO model and provides a clean API
    that the rest of the pipeline consumes.
    """

    def __init__(self, config_path: str = "config/detection_config.yaml"):
        with open(config_path, "r") as f:
            self.config = yaml.safe_load(f)
        
        self.confidence_threshold = self.config.get("confidence_threshold", 0.5)
        self.nms_iou_threshold = self.config.get("nms_iou_threshold", 0.45)
        self.input_size = tuple(self.config.get("input_size", [640, 640]))
        self.classes = self.config.get("classes", {})
        self.asset_classes = self.config.get("asset_classes", [])
        self.context_classes = self.config.get("context_classes", [])

        self.model = None
        self._load_model()

    def _load_model(self):
        """Load the YOLO model."""
        model_path = self.config.get("model_path", "")
        model_format = self.config.get("model_format", "pytorch")

        if not Path(model_path).exists():
            # During development, use a pretrained model as placeholder
            print(f"[Detector] Model not found at {model_path}. Loading pretrained YOLOv8n...")
            try:
                from ultralytics import YOLO
                self.model = YOLO("yolov8n.pt")
                print("[Detector] Pretrained YOLOv8n loaded successfully.")
            except ImportError:
                print("[Detector] ERROR: ultralytics not installed. Run: pip install ultralytics")
                self.model = None
        else:
            from ultralytics import YOLO
            self.model = YOLO(model_path)
            print(f"[Detector] Model loaded from {model_path}")

    def detect(self, image: np.ndarray) -> list:
        """
        Run detection on a single image frame.

        Args:
            image: BGR image as numpy array

        Returns:
            List of detection dicts, each containing:
                - object_class: str (e.g., "excavator")
                - class_id: int
                - bbox_xyxy: [x1, y1, x2, y2] in pixels
                - detection_confidence: float (0-1)
                - is_asset: bool (True if asset class, False if context class like person/vehicle)
        """
        if self.model is None:
            print("[Detector] No model loaded. Returning empty detections.")
            return []

        if image is None or image.size == 0:
            return []

        # Run inference
        results = self.model(
            image,
            conf=self.confidence_threshold,
            iou=self.nms_iou_threshold,
            imgsz=self.input_size[0],
            verbose=False
        )

        detections = []

        for result in results:
            if result.boxes is None:
                continue

            for box in result.boxes:
                class_id = int(box.cls[0])
                confidence = float(box.conf[0])
                bbox = box.xyxy[0].tolist()  # [x1, y1, x2, y2]
                bbox = [int(coord) for coord in bbox]

                # Map class_id to class name
                # For pretrained YOLO, class names come from COCO
                # For our custom model, they come from config
                if hasattr(result, 'names') and class_id in result.names:
                    class_name = result.names[class_id]
                elif class_id in self.classes:
                    class_name = self.classes[class_id]
                else:
                    class_name = f"class_{class_id}"

                # Determine if this is an asset or context detection
                is_asset = class_name in self.asset_classes

                detections.append({
                    "object_class": class_name,
                    "class_id": class_id,
                    "bbox_xyxy": bbox,
                    "detection_confidence": round(confidence, 4),
                    "is_asset": is_asset,
                })

        return detections

    def detect_and_draw(self, image: np.ndarray) -> tuple:
        """
        Run detection and draw bounding boxes on a copy of the image.
        Useful for development/debugging.

        Args:
            image: BGR image

        Returns:
            (detections, annotated_image)
        """
        detections = self.detect(image)
        annotated = image.copy()

        for det in detections:
            x1, y1, x2, y2 = det["bbox_xyxy"]
            label = f"{det['object_class']} {det['detection_confidence']:.2f}"

            # Green for assets, blue for context (persons/vehicles)
            color = (0, 255, 0) if det["is_asset"] else (255, 165, 0)

            cv2.rectangle(annotated, (x1, y1), (x2, y2), color, 2)
            
            # Label background
            (label_w, label_h), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)
            cv2.rectangle(annotated, (x1, y1 - label_h - 8), (x1 + label_w + 4, y1), color, -1)
            cv2.putText(annotated, label, (x1 + 2, y1 - 4),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 1)

        return detections, annotated

    @property
    def is_loaded(self) -> bool:
        """Check if the model is loaded and ready."""
        return self.model is not None
