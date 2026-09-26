"""
ASI Perception System — Image Quality Checker
Spec: PER-CAM-004

Checks if an image is usable for detection and evidence capture.
Scores: blur, brightness, visibility.
"""

import cv2
import numpy as np
import yaml


class ImageQualityChecker:
    """
    Evaluates image quality before passing to detector or saving as evidence.
    
    Returns a quality verdict: GOOD, DEGRADED, or UNUSABLE
    along with individual scores.
    """

    def __init__(self, config_path: str = "config/evidence_config.yaml"):
        with open(config_path, "r") as f:
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
