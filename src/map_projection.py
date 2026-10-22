"""
ASI Perception System — Map Projection
Spec: PER-MAP-001 → 003

Converts 2D camera pixel coordinates (bounding box centers) into estimated
site map coordinates (x, y in meters) using the robot's pose from ROS2.

CURRENT STATE: Stub implementation.
Full implementation pending Nav team ROS2 bag file + topic names.

When bag file is received, fill in:
  - Camera intrinsic matrix (from data/calibration/camera_intrinsics.yaml)
  - Robot pose subscription (from ROS2 odom/TF)
  - Ground plane assumption (flat floor or terrain model)

Integration contract:
  Caller provides: bbox_center pixel (u, v) + robot pose (x_r, y_r, heading_rad)
  Returns:         estimated site position (x_site, y_site) in meters
"""

import math
import yaml
from pathlib import Path


class MapProjector:
    """
    Converts camera-frame 2D pixel positions to site-frame 3D ground coordinates.

    For the POC, a flat ground plane assumption is used:
    - The camera is mounted at a fixed height on the robot.
    - The robot's pose (x, y, heading) is known from ROS2 odometry.
    - Pixel-to-ground transform uses the camera's vertical field of view + mounting height.

    When depth is enabled (Orbbec Femto Mega), depth value from depth frame replaces
    the ground plane assumption for exact 3D distance.

    TODO (pending Nav team bag file):
      1. Load real camera intrinsics (fx, fy, cx, cy) from calibration file.
      2. Replace mock robot pose with ROS2 odom/TF subscriber.
      3. Validate pixel-to-ground math with a tape-measure ground truth test.
    """

    # Default mounting geometry (to be confirmed with hardware team)
    DEFAULT_CAMERA_HEIGHT_M = 1.2        # Camera height above ground, meters
    DEFAULT_CAMERA_TILT_DEG = -10.0      # Camera tilt below horizontal, degrees (negative = down)
    DEFAULT_HFOV_DEG        = 68.0       # Orbbec Femto Mega horizontal FoV
    DEFAULT_VFOV_DEG        = 45.0       # Orbbec Femto Mega vertical FoV

    def __init__(self, config_path: str = "config/camera_config.yaml"):
        with open(config_path, "r") as f:
            cfg = yaml.safe_load(f)

        self.image_w = cfg.get("rgb_width",  1280)
        self.image_h = cfg.get("rgb_height", 720)

        # Camera intrinsics — loaded from calibration file if available
        calibration_file = cfg.get("calibration_file", "data/calibration/camera_intrinsics.yaml")
        self._intrinsics = self._load_intrinsics(calibration_file)

        # Mounting geometry (hardcoded defaults until hardware team confirms)
        self.camera_height_m  = self.DEFAULT_CAMERA_HEIGHT_M
        self.camera_tilt_rad  = math.radians(self.DEFAULT_CAMERA_TILT_DEG)

        print(f"[MapProjector] Initialized. Image: {self.image_w}×{self.image_h}. "
              f"Camera height: {self.camera_height_m}m. "
              f"Intrinsics: {'loaded' if self._intrinsics else 'using defaults'}.")

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def pixel_to_ground(
        self,
        pixel_uv: tuple,
        robot_pose: tuple
    ) -> tuple:
        """
        Estimate the ground-plane site coordinate of a pixel point.

        Args:
            pixel_uv:   (u, v) pixel coordinate — typically bbox center.
                        u = column (horizontal), v = row (vertical).
            robot_pose: (x_m, y_m, heading_rad) — robot position in site map
                        and heading in radians (0 = East, pi/2 = North).

        Returns:
            (x_site, y_site) estimated position in meters on the site map.
            Falls back to robot position if projection fails.

        TODO: Replace ground plane math with camera intrinsic matrix once
              calibration file is available.
        """
        robot_x, robot_y, robot_heading = robot_pose

        try:
            # --- Ground Plane Projection (Flat Floor Assumption) ---
            # Compute normalized image coordinates
            u_norm = (pixel_uv[0] - self.image_w / 2.0) / (self.image_w / 2.0)
            v_norm = (pixel_uv[1] - self.image_h / 2.0) / (self.image_h / 2.0)

            # Vertical angle from camera optical axis to this pixel.
            # v_norm > 0 means pixel is BELOW image center → camera is looking more
            # downward → depression angle INCREASES.
            v_angle_rad = v_norm * math.radians(self.DEFAULT_VFOV_DEG / 2.0)

            # Total depression angle below horizontal.
            # camera_tilt_rad is negative (tilted down), v_angle_rad is positive
            # for below-center pixels → adding them gives larger downward angle.
            total_depression = -self.camera_tilt_rad + v_angle_rad

            if total_depression <= 0:
                # Pixel is above the horizon — cannot project to ground
                return (robot_x, robot_y)

            # Ground distance along camera optical axis (flat floor)
            ground_distance_m = self.camera_height_m / math.tan(total_depression)

            # Horizontal offset (left/right)
            h_angle_rad = u_norm * math.radians(self.DEFAULT_HFOV_DEG / 2.0)
            lateral_offset_m = ground_distance_m * math.tan(h_angle_rad)

            # Transform from camera frame to site map frame using robot heading
            # Camera forward = robot forward direction
            x_site = robot_x + ground_distance_m * math.cos(robot_heading) \
                     - lateral_offset_m * math.sin(robot_heading)
            y_site = robot_y + ground_distance_m * math.sin(robot_heading) \
                     + lateral_offset_m * math.cos(robot_heading)

            return (round(x_site, 3), round(y_site, 3))

        except (ZeroDivisionError, ValueError):
            # Graceful fallback: use robot position as best estimate
            return (robot_x, robot_y)

    def compute_displacement_m(self, pos_a: tuple, pos_b: tuple) -> float:
        """
        Euclidean distance in meters between two site positions.

        Args:
            pos_a: (x, y) in meters
            pos_b: (x, y) in meters

        Returns:
            Distance in meters (float).
        """
        return math.sqrt((pos_a[0] - pos_b[0]) ** 2 + (pos_a[1] - pos_b[1]) ** 2)

    def bbox_center(self, bbox_xyxy: list) -> tuple:
        """
        Compute the (u, v) pixel center of a bounding box.

        Args:
            bbox_xyxy: [x1, y1, x2, y2] pixel coordinates from YOLO detector.

        Returns:
            (u, v) pixel center as integers.
        """
        u = int((bbox_xyxy[0] + bbox_xyxy[2]) / 2)
        v = int((bbox_xyxy[1] + bbox_xyxy[3]) / 2)
        return (u, v)

    # ------------------------------------------------------------------
    # Mock Robot Pose (Development/Standalone Use Only)
    # ------------------------------------------------------------------

    def get_mock_robot_pose(self) -> tuple:
        """
        Returns a static mock robot pose for standalone development mode.
        Replace with ROS2 odom/TF subscription in ros2_node.py.

        TODO: Remove this once ROS2 integration is complete.
        """
        return (0.0, 0.0, 0.0)  # x=0m, y=0m, heading=0rad (East)

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _load_intrinsics(calibration_file: str) -> dict | None:
        """
        Load camera intrinsic parameters from calibration YAML if it exists.
        Returns None if the file is not found (uses geometric defaults instead).
        """
        p = Path(calibration_file)
        if not p.exists():
            return None
        try:
            with open(p, "r") as f:
                return yaml.safe_load(f)
        except Exception:
            return None
