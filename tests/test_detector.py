"""
Unit Tests — YOLO Detector Wrapper
Spec: PER-DET-001 → 005

Tests for the Detector class in src/detector.py.
These run without needing a webcam or live camera feed.
"""

import sys
import os
import numpy as np
import pytest

# Make sure Python can find our src/ folder
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.detector import Detector

# ─────────────────────────────────────────────────────────────────────────────
# Fixtures
# ─────────────────────────────────────────────────────────────────────────────

CONFIG_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "config", "detection_config.yaml"
)


@pytest.fixture(scope="module")
def detector():
    """
    Create ONE Detector instance for the whole test session.
    Loading YOLO models is slow so we share it across tests.
    """
    return Detector(config_path=CONFIG_PATH)


@pytest.fixture
def blank_image():
    """A plain grey 640x640 image — no objects, but valid shape."""
    return np.full((640, 640, 3), 128, dtype=np.uint8)


@pytest.fixture
def natural_image():
    """A random noise image — simulates a real photo with texture."""
    rng = np.random.default_rng(seed=42)
    return rng.integers(60, 200, (480, 640, 3), dtype=np.uint8)


# ─────────────────────────────────────────────────────────────────────────────
# 1. Initialisation & Loading Tests
# ─────────────────────────────────────────────────────────────────────────────

class TestDetectorInit:
    """Verify the Detector loads correctly from config."""

    def test_model_is_loaded(self, detector):
        """The model should be loaded and ready after init."""
        assert detector.is_loaded is True

    def test_config_values_present(self, detector):
        """Core config values should be parsed correctly."""
        assert detector.confidence_threshold > 0
        assert detector.nms_iou_threshold > 0
        assert len(detector.input_size) == 2

    def test_invalid_config_raises(self):
        """Passing a non-existent config path should raise FileNotFoundError."""
        with pytest.raises(FileNotFoundError):
            Detector(config_path="config/this_does_not_exist.yaml")


# ─────────────────────────────────────────────────────────────────────────────
# 2. Input Validation Tests
# ─────────────────────────────────────────────────────────────────────────────

class TestDetectorInputHandling:
    """Verify the detector handles bad inputs gracefully."""

    def test_none_image_returns_empty_list(self, detector):
        """Passing None should return an empty list, not crash."""
        result = detector.detect(None)
        assert result == []

    def test_empty_array_returns_empty_list(self, detector):
        """Passing an empty numpy array should return an empty list."""
        result = detector.detect(np.array([]))
        assert result == []

    def test_valid_image_returns_list(self, detector, blank_image):
        """Any valid image should return a list (even if empty detections)."""
        result = detector.detect(blank_image)
        assert isinstance(result, list)


# ─────────────────────────────────────────────────────────────────────────────
# 3. Detection Output Format Tests
# ─────────────────────────────────────────────────────────────────────────────

class TestDetectionOutputFormat:
    """
    These tests ensure every detection dict has the right structure.
    Our entire pipeline downstream depends on this exact format.
    """

    def test_detections_are_dicts(self, detector, natural_image):
        """Every detection should be a dictionary."""
        results = detector.detect(natural_image)
        for det in results:
            assert isinstance(det, dict), "Each detection must be a dict"

    def test_required_keys_present(self, detector, natural_image):
        """Each detection must contain all 5 required keys."""
        required_keys = {
            "object_class",
            "class_id",
            "bbox_xyxy",
            "detection_confidence",
            "is_asset",
        }
        results = detector.detect(natural_image)
        for det in results:
            assert required_keys.issubset(det.keys()), (
                f"Detection missing keys. Got: {det.keys()}"
            )

    def test_bbox_has_four_coordinates(self, detector, natural_image):
        """bbox_xyxy must have exactly 4 integer coordinates."""
        results = detector.detect(natural_image)
        for det in results:
            bbox = det["bbox_xyxy"]
            assert len(bbox) == 4, "bbox_xyxy must have 4 values [x1,y1,x2,y2]"
            assert all(isinstance(c, int) for c in bbox), "All bbox coords must be ints"

    def test_bbox_is_valid(self, detector, natural_image):
        """x2 must be greater than x1, and y2 must be greater than y1."""
        results = detector.detect(natural_image)
        for det in results:
            x1, y1, x2, y2 = det["bbox_xyxy"]
            assert x2 > x1, f"Invalid bbox: x2 ({x2}) must be > x1 ({x1})"
            assert y2 > y1, f"Invalid bbox: y2 ({y2}) must be > y1 ({y1})"

    def test_confidence_is_between_0_and_1(self, detector, natural_image):
        """Confidence scores must always be between 0.0 and 1.0."""
        results = detector.detect(natural_image)
        for det in results:
            conf = det["detection_confidence"]
            assert 0.0 <= conf <= 1.0, f"Confidence {conf} is out of range [0, 1]"

    def test_object_class_is_string(self, detector, natural_image):
        """object_class must always be a non-empty string."""
        results = detector.detect(natural_image)
        for det in results:
            assert isinstance(det["object_class"], str)
            assert len(det["object_class"]) > 0

    def test_is_asset_is_boolean(self, detector, natural_image):
        """is_asset flag must always be a boolean value."""
        results = detector.detect(natural_image)
        for det in results:
            assert isinstance(det["is_asset"], bool)


# ─────────────────────────────────────────────────────────────────────────────
# 4. detect_and_draw() Tests
# ─────────────────────────────────────────────────────────────────────────────

class TestDetectAndDraw:
    """Verify the combined detect + annotate utility works correctly."""

    def test_returns_tuple_of_two(self, detector, blank_image):
        """detect_and_draw should always return a tuple of (list, ndarray)."""
        result = detector.detect_and_draw(blank_image)
        assert isinstance(result, tuple)
        assert len(result) == 2

    def test_annotated_image_is_numpy_array(self, detector, blank_image):
        """The annotated output should be a numpy array (an image)."""
        detections, annotated = detector.detect_and_draw(blank_image)
        assert isinstance(annotated, np.ndarray)

    def test_annotated_image_same_shape_as_input(self, detector, natural_image):
        """The annotated output must be the same dimensions as the input."""
        detections, annotated = detector.detect_and_draw(natural_image)
        assert annotated.shape == natural_image.shape

    def test_original_image_not_modified(self, detector, blank_image):
        """detect_and_draw must NOT modify the original image (makes a copy)."""
        original_copy = blank_image.copy()
        detector.detect_and_draw(blank_image)
        assert np.array_equal(blank_image, original_copy), (
            "detect_and_draw modified the original image — it should copy it!"
        )
