"""
ASI Perception System — Re-Identification Engine
Spec: PER-REID-001 → 005

Loads the OSNet ONNX backbone and extracts 512-dimensional
embedding fingerprints from cropped asset images.

Input:  BGR crop (numpy array)
Output: 512D normalized numpy embedding vector
"""

import cv2
import numpy as np
import yaml
from pathlib import Path


class ReIDEngine:
    """
    Feature extraction engine for visual asset re-identification.

    Takes a cropped image of a detected asset and converts it into
    a 512-dimensional embedding vector (a numerical "fingerprint").
    Similar assets will produce similar embeddings; different assets
    will produce dissimilar embeddings.
    """

    # Minimum crop size to be considered valid for embedding extraction
    MIN_CROP_H = 50
    MIN_CROP_W = 50

    # ImageNet normalisation constants (OSNet was trained with these)
    IMAGENET_MEAN = np.array([0.485, 0.456, 0.406], dtype=np.float32)
    IMAGENET_STD  = np.array([0.229, 0.224, 0.225], dtype=np.float32)

    def __init__(self, config_path: str = "config/reid_config.yaml"):
        with open(config_path, "r") as f:
            self.config = yaml.safe_load(f)

        self.model_path     = self.config.get("model_path", "models/reid/reid_backbone_best.onnx")
        self.embedding_dim  = self.config.get("embedding_dim", 512)
        self.input_h        = 256
        self.input_w        = 256

        self.session = None
        self._load_model()

    # ------------------------------------------------------------------
    # Model Loading
    # ------------------------------------------------------------------

    def _load_model(self):
        """Load the OSNet ONNX model via ONNX Runtime."""
        model_path = Path(self.model_path)

        if not model_path.exists():
            print(
                f"[ReIDEngine] WARNING: Model not found at '{self.model_path}'. "
                "Embedding extraction will be unavailable until the model is placed there."
            )
            self.session = None
            return

        try:
            import onnxruntime as ort
            self.session = ort.InferenceSession(
                str(model_path),
                providers=["CPUExecutionProvider"]
            )
            self.input_name  = self.session.get_inputs()[0].name
            self.output_name = self.session.get_outputs()[0].name
            print(f"[ReIDEngine] OSNet loaded from '{self.model_path}'")
        except Exception as e:
            print(f"[ReIDEngine] ERROR loading model: {e}")
            self.session = None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def extract_embedding(self, crop: np.ndarray) -> np.ndarray | None:
        """
        Extract a 512-dimensional embedding from a single asset crop.

        Args:
            crop: BGR numpy image (H x W x 3). The crop should contain
                  a single detected asset, as output by crop_detections().

        Returns:
            512D float32 numpy array (L2-normalised), or None if the crop
            is invalid / the model is not loaded.
        """
        if self.session is None:
            return None

        if not self.is_valid_crop(crop):
            return None

        tensor = self._preprocess(crop)
        outputs = self.session.run([self.output_name], {self.input_name: tensor})
        embedding = outputs[0][0]                    # shape: (512,)
        embedding = self._l2_normalize(embedding)
        return embedding.astype(np.float32)

    def crop_detections(self, frame: np.ndarray, detections: list) -> list:
        """
        Cut asset crops out of a full camera frame using YOLO bounding boxes.

        Only crops where is_asset=True are extracted, matching the
        detector.py output convention.

        Args:
            frame:      Full BGR camera frame (H x W x 3).
            detections: List of detection dicts from detector.detect().

        Returns:
            List of dicts:
                {
                    "detection":  original detection dict,
                    "crop":       BGR numpy crop (or None if invalid bbox),
                    "valid":      bool - True if crop passes size filter
                }
        """
        h, w = frame.shape[:2]
        results = []

        for det in detections:
            if not det.get("is_asset", False):
                # Skip context detections (persons, generic vehicles)
                continue

            x1, y1, x2, y2 = det["bbox_xyxy"]

            # Clamp to frame boundaries
            x1 = max(0, x1)
            y1 = max(0, y1)
            x2 = min(w, x2)
            y2 = min(h, y2)

            if x2 <= x1 or y2 <= y1:
                results.append({"detection": det, "crop": None, "valid": False})
                continue

            crop = frame[y1:y2, x1:x2].copy()
            valid = self.is_valid_crop(crop)
            results.append({"detection": det, "crop": crop, "valid": valid})

        return results

    def is_valid_crop(self, crop: np.ndarray | None) -> bool:
        """
        Check whether a crop is large enough and non-empty for embedding extraction.

        Crops that are too small produce noisy, unreliable embeddings that
        can corrupt the reference database.

        Args:
            crop: BGR numpy image or None.

        Returns:
            True if the crop passes the minimum size filter.
        """
        if crop is None:
            return False
        if crop.size == 0:
            return False
        h, w = crop.shape[:2]
        return h >= self.MIN_CROP_H and w >= self.MIN_CROP_W

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _preprocess(self, crop: np.ndarray) -> np.ndarray:
        """
        Resize and normalise a BGR crop into a model-ready float32 tensor.

        Steps:
          1. Resize to 256x256 (square - handles wide vehicles and tall cranes)
          2. BGR -> RGB
          3. Normalise with ImageNet mean/std
          4. HWC -> CHW -> NCHW (add batch dimension)

        Returns:
            float32 numpy array with shape (1, 3, 256, 256)
        """
        img = cv2.resize(crop, (self.input_w, self.input_h))
        img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        img = img.astype(np.float32) / 255.0
        img = (img - self.IMAGENET_MEAN) / self.IMAGENET_STD
        img = img.transpose(2, 0, 1)       # HWC -> CHW
        img = np.expand_dims(img, axis=0)  # CHW -> NCHW
        return img

    @staticmethod
    def _l2_normalize(vector: np.ndarray) -> np.ndarray:
        """
        L2-normalise a vector so its length equals 1.0.
        Required for cosine similarity to work correctly.
        """
        norm = np.linalg.norm(vector)
        if norm < 1e-8:
            return vector
        return vector / norm

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def is_loaded(self) -> bool:
        """True if the ONNX model is loaded and ready."""
        return self.session is not None
