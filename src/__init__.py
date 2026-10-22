"""
ASI Perception System — Source Package
Environment-Agnostic Perception Platform for Mobile Ground Robots

Modules:
    image_quality        — Frame quality gate (blur / brightness checks)
    detector             — YOLOv8 ONNX object detection wrapper
    reid_engine          — OSNet ONNX visual Re-ID & embedding extraction
    reference_store      — Persistent asset fingerprint store (cosine similarity)
    asset_state_registry — Temporal movement state machine & alert generation
    map_projection       — 2D pixel → site map coordinate projection
    evidence_generator   — Forensic evidence package capture (frames + JSON)
    ros2_node            — ROS2 integration node (stub — pending Nav team topics)
"""

from .image_quality        import ImageQualityChecker
from .detector             import Detector
from .reid_engine          import ReIDEngine
from .reference_store      import ReferenceStore
from .asset_state_registry import AssetStateRegistry
from .map_projection       import MapProjector
from .evidence_generator   import EvidenceGenerator

__all__ = [
    "ImageQualityChecker",
    "Detector",
    "ReIDEngine",
    "ReferenceStore",
    "AssetStateRegistry",
    "MapProjector",
    "EvidenceGenerator",
]
