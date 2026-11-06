"""
ASI Perception System — Image Quality Checker
Spec: PER-CAM-004

Checks if an image is usable for detection and evidence capture.
Scores: blur, brightness, visibility.
"""

import cv2
import numpy as np
import yaml


from pathlib import Path


class ImageQualityChecker:
    """
    Evaluates image quality before passing to detector or saving as evidence.
    
    Returns a quality verdict: GOOD, DEGRADED, or UNUSABLE
    along with individual scores.
    """

    def __init__(self, config_path: str = "config/evidence_config.yaml"):
        cfg_file = Path(config_path)
        if not cfg_file.exists():
            candidate = Path(__file__).resolve().parent.parent / config_path
            if candidate.exists():
                cfg_file = candidate

        with open(cfg_file, "r") as f:
            config = yaml.safe_load(f)
        
        self.min_blur_score = config.get("min_blur_score", 100.0)
        self.min_brightness = config.get("min_brightness", 40)
        self.max_brightness = config.get("max_brightness", 220)

    def check(self, image: np.ndarray) -> dict:
        """
        Evaluate image quality.

        Args:
            image: BGR image as numpy array (from cv2.imread or camera frame)

        Returns:
            dict with keys:
                - quality: "GOOD" | "DEGRADED" | "UNUSABLE"
                - blur_score: float (higher = sharper)
                - brightness: float (mean pixel brightness, 0-255)
                - issues: list of strings describing any problems
        """
        if image is None or image.size == 0:
            return {
                "quality": "UNUSABLE",
                "blur_score": 0.0,
                "brightness": 0.0,
                "issues": ["empty_or_null_image"]
            }

        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        
        # Blur detection using Laplacian variance
        blur_score = cv2.Laplacian(gray, cv2.CV_64F).var()

        # Brightness check
        brightness = float(np.mean(gray))

        # Collect issues
        issues = []
        
        if blur_score < self.min_blur_score:
            issues.append("too_blurry")
        
        if brightness < self.min_brightness:
            issues.append("too_dark")
        elif brightness > self.max_brightness:
            issues.append("overexposed")

        # Determine overall quality
        if len(issues) == 0:
            quality = "GOOD"
        elif len(issues) == 1:
            quality = "DEGRADED"
        else:
            quality = "UNUSABLE"

        return {
            "quality": quality,
            "blur_score": round(blur_score, 2),
            "brightness": round(brightness, 2),
            "issues": issues
        }

    def is_usable(self, image: np.ndarray) -> bool:
        """Quick check — is this image good enough to process?"""
        result = self.check(image)
        return result["quality"] != "UNUSABLE"

    def check_crop_quality(self, crop: np.ndarray, min_blur: float = 60.0) -> dict:
        """
        Evaluate whether an individual candidate crop is sharp enough for Re-ID.
        Filters out motion-blurred crops caused by robot movement.

        Args:
            crop: BGR crop array (numpy ndarray)
            min_blur: Minimum acceptable Laplacian variance (default: 60.0)

        Returns:
            dict with 'is_usable' (bool), 'blur_score' (float), and 'issues' (list)
        """
        if crop is None or crop.size == 0 or crop.shape[0] < 30 or crop.shape[1] < 30:
            return {
                "is_usable": False,
                "blur_score": 0.0,
                "issues": ["too_small_or_empty"]
            }

        gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
        blur_score = float(cv2.Laplacian(gray, cv2.CV_64F).var())

        issues = []
        if blur_score < min_blur:
            issues.append("crop_too_blurry")

        return {
            "is_usable": len(issues) == 0,
            "blur_score": round(blur_score, 2),
            "issues": issues
        }

