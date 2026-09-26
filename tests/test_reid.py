"""
Tests for src/reid_engine.py
Spec: PER-REID-001 → 005

These tests cover the ReIDEngine without requiring the actual ONNX model
to be present. The model-dependent tests are gated with a check and
skipped cleanly if the model file is missing.
"""

import numpy as np
import pytest
import cv2
from pathlib import Path
from unittest.mock import MagicMock, patch
from src.reid_engine import ReIDEngine


# ---------------------------------------------------------------------------
# Helpers & fixtures
# ---------------------------------------------------------------------------

def make_engine_no_model(tmp_path):
    """Create a ReIDEngine pointing at a config with a missing model file."""
    config = tmp_path / "reid_config.yaml"
    config.write_text(
        "model_path: 'models/reid/__nonexistent__.onnx'\n"
        "embedding_dim: 512\n"
        "thresholds:\n"
        "  t_high: 0.85\n"
        "  t_low: 0.65\n"
        "  t_margin: 0.15\n"
        "  t_min: 0.40\n"
        "max_references_per_asset: 10\n"
        "embedding_aggregation: mean\n"
        "max_candidates: 5\n"
    )
    return ReIDEngine(config_path=str(config))


def make_rgb_crop(h=100, w=200):
    """Return a valid BGR crop filled with random pixels."""
    return np.random.randint(0, 256, (h, w, 3), dtype=np.uint8)


def make_fake_embedding(seed=42):
    """Return a reproducible L2-normalised 512D vector."""
    rng = np.random.default_rng(seed)
    v = rng.random(512).astype(np.float32)
    return v / np.linalg.norm(v)


# ---------------------------------------------------------------------------
# 1. Model loading
# ---------------------------------------------------------------------------

class TestModelLoading:

    def test_missing_model_does_not_crash(self, tmp_path):
        """Engine initialises cleanly even when the ONNX file is absent."""
        engine = make_engine_no_model(tmp_path)
        assert engine.is_loaded is False

    def test_is_loaded_false_without_model(self, tmp_path):
        engine = make_engine_no_model(tmp_path)
        assert engine.is_loaded is False

    def test_extract_embedding_returns_none_without_model(self, tmp_path):
        engine = make_engine_no_model(tmp_path)
        crop = make_rgb_crop()
        result = engine.extract_embedding(crop)
        assert result is None


# ---------------------------------------------------------------------------
# 2. Preprocessing
# ---------------------------------------------------------------------------

class TestPreprocessing:

    def test_preprocess_output_shape(self, tmp_path):
        """_preprocess must return (1, 3, 256, 256) regardless of crop size."""
        engine = make_engine_no_model(tmp_path)
        for (h, w) in [(64, 64), (100, 200), (480, 640)]:
            crop = make_rgb_crop(h, w)
            tensor = engine._preprocess(crop)
            assert tensor.shape == (1, 3, 256, 256), f"Failed for crop {h}x{w}"

    def test_preprocess_output_dtype(self, tmp_path):
        engine = make_engine_no_model(tmp_path)
        crop = make_rgb_crop()
        tensor = engine._preprocess(crop)
        assert tensor.dtype == np.float32

    def test_preprocess_values_in_reasonable_range(self, tmp_path):
        """After ImageNet normalisation values should be roughly in [-3, 3]."""
        engine = make_engine_no_model(tmp_path)
        crop = make_rgb_crop()
        tensor = engine._preprocess(crop)
        assert tensor.min() > -5.0 and tensor.max() < 5.0


# ---------------------------------------------------------------------------
# 3. L2 Normalisation
# ---------------------------------------------------------------------------

class TestL2Normalisation:

    def test_normalised_vector_has_unit_length(self):
        v = np.random.random(512).astype(np.float32)
        normalised = ReIDEngine._l2_normalize(v)
        assert abs(np.linalg.norm(normalised) - 1.0) < 1e-6

    def test_zero_vector_returned_unchanged(self):
        v = np.zeros(512, dtype=np.float32)
        result = ReIDEngine._l2_normalize(v)
        assert np.allclose(result, v)

    def test_already_normalised_vector_unchanged(self):
        v = make_fake_embedding()
        result = ReIDEngine._l2_normalize(v)
        assert abs(np.linalg.norm(result) - 1.0) < 1e-6


# ---------------------------------------------------------------------------
# 4. Crop validation
# ---------------------------------------------------------------------------

class TestCropValidation:

    def test_valid_large_crop(self, tmp_path):
        engine = make_engine_no_model(tmp_path)
        crop = make_rgb_crop(100, 150)
        assert engine.is_valid_crop(crop) is True

    def test_crop_exactly_at_minimum(self, tmp_path):
        engine = make_engine_no_model(tmp_path)
        crop = make_rgb_crop(50, 50)
        assert engine.is_valid_crop(crop) is True

    def test_tiny_crop_rejected_height(self, tmp_path):
        engine = make_engine_no_model(tmp_path)
        crop = make_rgb_crop(h=30, w=200)  # height too small
        assert engine.is_valid_crop(crop) is False

    def test_tiny_crop_rejected_width(self, tmp_path):
        engine = make_engine_no_model(tmp_path)
        crop = make_rgb_crop(h=200, w=30)  # width too small
        assert engine.is_valid_crop(crop) is False

    def test_none_crop_rejected(self, tmp_path):
        engine = make_engine_no_model(tmp_path)
        assert engine.is_valid_crop(None) is False

    def test_empty_array_rejected(self, tmp_path):
        engine = make_engine_no_model(tmp_path)
        assert engine.is_valid_crop(np.array([])) is False


# ---------------------------------------------------------------------------
# 5. crop_detections
# ---------------------------------------------------------------------------

class TestCropDetections:

    def _make_detections(self):
        return [
            {
                "object_class": "Excavator",
                "class_id": 1,
                "bbox_xyxy": [50, 50, 300, 250],
                "detection_confidence": 0.91,
                "is_asset": True,
            },
            {
                "object_class": "Truck",
                "class_id": 12,
                "bbox_xyxy": [10, 10, 100, 80],
                "detection_confidence": 0.70,
                "is_asset": False,   # context class — should be skipped
            }
        ]

    def test_only_asset_crops_are_returned(self, tmp_path):
        engine = make_engine_no_model(tmp_path)
        frame = make_rgb_crop(480, 640)
        dets = self._make_detections()
        results = engine.crop_detections(frame, dets)
        # Only the Excavator (is_asset=True) should appear
        assert len(results) == 1
        assert results[0]["detection"]["object_class"] == "Excavator"

    def test_valid_crop_is_correct_size(self, tmp_path):
        engine = make_engine_no_model(tmp_path)
        frame = make_rgb_crop(480, 640)
        dets = self._make_detections()
        results = engine.crop_detections(frame, dets)
        crop = results[0]["crop"]
        assert crop is not None
        assert crop.shape[0] == 200  # y2 - y1 = 250 - 50
        assert crop.shape[1] == 250  # x2 - x1 = 300 - 50

    def test_out_of_bounds_bbox_clamped(self, tmp_path):
        engine = make_engine_no_model(tmp_path)
        frame = make_rgb_crop(100, 100)
        dets = [{
            "object_class": "Excavator",
            "class_id": 1,
            "bbox_xyxy": [-10, -10, 200, 200],  # outside frame bounds
            "detection_confidence": 0.8,
            "is_asset": True,
        }]
        results = engine.crop_detections(frame, dets)
        assert results[0]["crop"] is not None
        assert results[0]["crop"].shape == (100, 100, 3)

    def test_empty_detections_returns_empty_list(self, tmp_path):
        engine = make_engine_no_model(tmp_path)
        frame = make_rgb_crop()
        results = engine.crop_detections(frame, [])
        assert results == []


# ---------------------------------------------------------------------------
# 6. Mocked end-to-end (model present, stubbed ONNX runtime)
# ---------------------------------------------------------------------------

class TestExtractEmbeddingMocked:

    def _make_engine_with_mock_session(self, tmp_path):
        """Inject a fake ONNX session that returns a deterministic embedding."""
        engine = make_engine_no_model(tmp_path)
        mock_session = MagicMock()
        fake_output = make_fake_embedding(seed=7).reshape(1, 512)
        mock_session.run.return_value = [fake_output]
        mock_session.get_inputs.return_value = [MagicMock(name="input")]
        mock_session.get_outputs.return_value = [MagicMock(name="output")]
        engine.session = mock_session
        engine.input_name = "input"
        engine.output_name = "output"
        return engine

    def test_extract_embedding_returns_512d_array(self, tmp_path):
        engine = self._make_engine_with_mock_session(tmp_path)
        crop = make_rgb_crop()
        emb = engine.extract_embedding(crop)
        assert emb is not None
        assert emb.shape == (512,)

    def test_extract_embedding_is_normalised(self, tmp_path):
        engine = self._make_engine_with_mock_session(tmp_path)
        crop = make_rgb_crop()
        emb = engine.extract_embedding(crop)
        assert abs(np.linalg.norm(emb) - 1.0) < 1e-5

    def test_extract_embedding_is_float32(self, tmp_path):
        engine = self._make_engine_with_mock_session(tmp_path)
        crop = make_rgb_crop()
        emb = engine.extract_embedding(crop)
        assert emb.dtype == np.float32

    def test_same_crop_same_embedding(self, tmp_path):
        """The same mock always returns the same vector — deterministic."""
        engine = self._make_engine_with_mock_session(tmp_path)
        crop = make_rgb_crop()
        emb1 = engine.extract_embedding(crop)
        emb2 = engine.extract_embedding(crop)
        assert np.allclose(emb1, emb2)

    def test_tiny_crop_returns_none_even_with_model(self, tmp_path):
        engine = self._make_engine_with_mock_session(tmp_path)
        tiny_crop = make_rgb_crop(h=20, w=20)
        result = engine.extract_embedding(tiny_crop)
        assert result is None
