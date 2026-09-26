"""
ASI Perception System — Evidence Generator
Spec: PER-CAP-001 → 004, PER-EVD-001 → 004

Captures and saves evidence packages:
- Full frame snapshot (unannotated original)
- Asset crop (padded bounding box)
- Annotated preview (with bounding boxes drawn)
- Metadata JSON
"""

import cv2
import json
import numpy as np
import yaml
from datetime import datetime, timezone
from pathlib import Path


class EvidenceGenerator:
    """
    Captures evidence for asset observations.

    Every evidence package includes the ORIGINAL unannotated image
    (the legal evidence) plus annotated versions for operator convenience.
    """

    def __init__(self, config_path: str = "config/evidence_config.yaml"):
        with open(config_path, "r") as f:
            config = yaml.safe_load(f)

        self.evidence_dir = Path(config.get("evidence_dir", "evidence/"))
        self.jpeg_quality = config.get("jpeg_quality", 95)
        self.crop_padding_ratio = config.get("crop_padding_ratio", 0.1)
        self.capture_full_frame = config.get("capture_full_frame", True)
        self.capture_asset_crop = config.get("capture_asset_crop", True)
        self.capture_annotated = config.get("capture_annotated_preview", True)

        # Create evidence directory
        self.evidence_dir.mkdir(parents=True, exist_ok=True)

    def capture(self, frame: np.ndarray, detection: dict,
                annotated_frame: np.ndarray = None,
                model_version: str = "unknown") -> dict:
        """
        Capture a full evidence package for one detection.

        Args:
            frame: Original BGR image (unannotated)
            detection: Detection dict from Detector
            annotated_frame: Optional annotated version of the frame
            model_version: Current model version string

        Returns:
            dict with evidence file paths and metadata
        """
        timestamp = datetime.now(timezone.utc)
        ts_str = timestamp.strftime("%Y%m%d_%H%M%S_%f")[:-3]  # ms precision
        asset_id = detection.get("asset_id", "UNKNOWN")
        object_class = detection.get("object_class", "unknown")

        # Create subdirectory for this date
        date_dir = self.evidence_dir / timestamp.strftime("%Y-%m-%d")
        date_dir.mkdir(parents=True, exist_ok=True)

        evidence_refs = []
        file_prefix = f"{ts_str}_{object_class}_{asset_id}"

        # 1. Full frame snapshot (original, unannotated)
        if self.capture_full_frame:
            full_path = date_dir / f"full_{file_prefix}.jpg"
            cv2.imwrite(
                str(full_path), frame,
                [cv2.IMWRITE_JPEG_QUALITY, self.jpeg_quality]
            )
            evidence_refs.append(str(full_path))

        # 2. Asset crop (padded bounding box)
        if self.capture_asset_crop and "bbox_xyxy" in detection:
            crop = self._extract_padded_crop(frame, detection["bbox_xyxy"])
            if crop is not None and crop.size > 0:
                crop_path = date_dir / f"crop_{file_prefix}.jpg"
                cv2.imwrite(
                    str(crop_path), crop,
                    [cv2.IMWRITE_JPEG_QUALITY, self.jpeg_quality]
                )
                evidence_refs.append(str(crop_path))

        # 3. Annotated preview
        if self.capture_annotated and annotated_frame is not None:
            ann_path = date_dir / f"annotated_{file_prefix}.jpg"
            cv2.imwrite(
                str(ann_path), annotated_frame,
                [cv2.IMWRITE_JPEG_QUALITY, self.jpeg_quality]
            )
            evidence_refs.append(str(ann_path))

        # 4. Metadata JSON
        metadata = {
            "timestamp": timestamp.isoformat(),
            "asset_id": asset_id,
            "object_class": object_class,
            "detection_confidence": detection.get("detection_confidence"),
            "identity_status": detection.get("identity_status", "N/A"),
            "identity_confidence": detection.get("identity_confidence", None),
            "movement_state": detection.get("movement_state", "N/A"),
            "bbox_xyxy": detection.get("bbox_xyxy"),
            "model_version": model_version,
            "evidence_files": [str(p) for p in evidence_refs],
        }

        meta_path = date_dir / f"meta_{file_prefix}.json"
        with open(meta_path, "w") as f:
            json.dump(metadata, f, indent=2)
        
        evidence_refs.append(str(meta_path))

        return {
            "evidence_refs": evidence_refs,
            "metadata": metadata,
        }

    def _extract_padded_crop(self, image: np.ndarray, bbox: list) -> np.ndarray:
        """
        Extract a crop from the image with padding around the bbox.
        
        Args:
            image: BGR image
            bbox: [x1, y1, x2, y2]

        Returns:
            Cropped image with padding
        """
        h, w = image.shape[:2]
        x1, y1, x2, y2 = bbox

        # Add padding
        pad_w = int((x2 - x1) * self.crop_padding_ratio)
        pad_h = int((y2 - y1) * self.crop_padding_ratio)

        x1 = max(0, x1 - pad_w)
        y1 = max(0, y1 - pad_h)
        x2 = min(w, x2 + pad_w)
        y2 = min(h, y2 + pad_h)

        crop = image[y1:y2, x1:x2]
        return crop
