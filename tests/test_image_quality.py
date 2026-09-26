"""
Unit Tests — Image Quality Checker
"""

import sys
import os
import numpy as np
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.image_quality import ImageQualityChecker


class TestImageQualityChecker:
    """Tests for image quality assessment."""

    def setup_method(self):
        """Create checker with default config."""
        self.checker = ImageQualityChecker()

    def test_null_image_returns_unusable(self):
        """Null image should be UNUSABLE."""
        result = self.checker.check(None)
        assert result["quality"] == "UNUSABLE"
        assert "empty_or_null_image" in result["issues"]

    def test_empty_image_returns_unusable(self):
        """Empty array should be UNUSABLE."""
        empty = np.array([])
        result = self.checker.check(empty)
        assert result["quality"] == "UNUSABLE"

    def test_good_image(self):
        """A normal, sharp, well-lit image should be GOOD."""
        # Create a synthetic image with texture (not uniform — has edges for blur detection)
        img = np.random.randint(80, 180, (480, 640, 3), dtype=np.uint8)
        result = self.checker.check(img)
        assert result["quality"] == "GOOD"
        assert len(result["issues"]) == 0
        assert result["blur_score"] > 0
        assert 40 < result["brightness"] < 220

    def test_dark_image(self):
        """A very dark image should be flagged."""
        dark = np.full((480, 640, 3), 10, dtype=np.uint8)
        result = self.checker.check(dark)
        assert "too_dark" in result["issues"]

    def test_overexposed_image(self):
        """A very bright image should be flagged."""
        bright = np.full((480, 640, 3), 250, dtype=np.uint8)
        result = self.checker.check(bright)
        assert "overexposed" in result["issues"]

    def test_blurry_image(self):
        """A completely uniform (blurry) image should be flagged."""
        # Uniform color = zero Laplacian variance = maximum blur
        blurry = np.full((480, 640, 3), 128, dtype=np.uint8)
        result = self.checker.check(blurry)
        assert "too_blurry" in result["issues"]

    def test_is_usable_good_image(self):
        """is_usable should return True for good images."""
        img = np.random.randint(80, 180, (480, 640, 3), dtype=np.uint8)
        assert self.checker.is_usable(img) is True

    def test_is_usable_null_image(self):
        """is_usable should return False for null images."""
        assert self.checker.is_usable(None) is False
