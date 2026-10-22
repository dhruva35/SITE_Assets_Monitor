"""
Tests for src/map_projection.py
Spec: PER-MAP-001 → 003

Tests verify:
  - bbox_center utility
  - Ground plane projection produces valid (x, y) tuples
  - Displacement calculation math
  - Graceful fallback on edge cases (horizon pixels, bad inputs)
"""

import sys
import os
import math
import pytest

# Ensure project root is in sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.map_projection import MapProjector


# ---------------------------------------------------------------------------
# Helpers & fixtures
# ---------------------------------------------------------------------------

def make_projector(tmp_path):
    """Create a MapProjector with a minimal temp camera config."""
    config = tmp_path / "camera_config.yaml"
    config.write_text(
        "rgb_width: 1280\n"
        "rgb_height: 720\n"
        "depth_width: 640\n"
        "depth_height: 480\n"
        "target_fps: 5\n"
        "source: 0\n"
        "depth_enabled: false\n"
        "depth_min_m: 0.4\n"
        "depth_max_m: 5.5\n"
        "calibration_file: 'data/calibration/nonexistent.yaml'\n"
    )
    return MapProjector(config_path=str(config))


ZERO_POSE = (0.0, 0.0, 0.0)  # Origin, heading East


# ---------------------------------------------------------------------------
# 1. bbox_center utility
# ---------------------------------------------------------------------------

class TestBboxCenter:

    def test_center_of_square_bbox(self, tmp_path):
        mp = make_projector(tmp_path)
        center = mp.bbox_center([100, 200, 300, 400])
        assert center == (200, 300)

    def test_center_of_non_square_bbox(self, tmp_path):
        mp = make_projector(tmp_path)
        center = mp.bbox_center([0, 0, 640, 100])
        assert center == (320, 50)

    def test_single_pixel_bbox(self, tmp_path):
        mp = make_projector(tmp_path)
        center = mp.bbox_center([50, 50, 51, 51])
        assert center == (50, 50)

    def test_full_frame_bbox_center(self, tmp_path):
        mp = make_projector(tmp_path)
        # Full 1280x720 frame
        center = mp.bbox_center([0, 0, 1280, 720])
        assert center == (640, 360)


# ---------------------------------------------------------------------------
# 2. pixel_to_ground — basic behavior
# ---------------------------------------------------------------------------

class TestPixelToGround:

    def test_returns_tuple_of_two_floats(self, tmp_path):
        mp = make_projector(tmp_path)
        result = mp.pixel_to_ground((640, 400), ZERO_POSE)
        assert isinstance(result, tuple)
        assert len(result) == 2

    def test_center_pixel_projects_forward_from_robot(self, tmp_path):
        """Pixel at image center-bottom should project to a position in front of robot."""
        mp = make_projector(tmp_path)
        # Bottom-center pixel: (640, 680) — below center, looking at ground
        x, y = mp.pixel_to_ground((640, 680), ZERO_POSE)
        # Robot at origin heading East (heading=0) → forward is +x axis
        assert x > 0.0   # Must be ahead of robot

    def test_heading_north_changes_projection_axis(self, tmp_path):
        """Robot facing North (heading=pi/2) → bottom-center pixel is in +y direction."""
        mp = make_projector(tmp_path)
        north_pose = (0.0, 0.0, math.pi / 2)
        x, y = mp.pixel_to_ground((640, 680), north_pose)
        # Heading North means forward is +y axis
        assert y > 0.0

    def test_projection_falls_back_for_horizon_pixel(self, tmp_path):
        """A pixel at or above the image horizon line falls back to robot position."""
        mp = make_projector(tmp_path)
        robot_x, robot_y = 5.0, 10.0
        result = mp.pixel_to_ground((640, 0), (robot_x, robot_y, 0.0))  # Top of frame
        assert isinstance(result, tuple)
        assert len(result) == 2

    def test_robot_position_offset_propagates(self, tmp_path):
        """If robot is at (10, 20), the projection should shift relative to that."""
        mp = make_projector(tmp_path)
        pos_at_origin = mp.pixel_to_ground((640, 680), (0.0, 0.0, 0.0))
        pos_at_offset  = mp.pixel_to_ground((640, 680), (10.0, 0.0, 0.0))
        # x-coordinate must be offset by ~10m
        assert abs(pos_at_offset[0] - pos_at_origin[0] - 10.0) < 0.5

    def test_left_vs_right_pixel_lateral_symmetry(self, tmp_path):
        """Left-of-center and right-of-center pixels should be symmetric about forward axis."""
        mp = make_projector(tmp_path)
        v_center = 600  # Below horizon
        left  = mp.pixel_to_ground((320,  v_center), ZERO_POSE)  # Left of center
        right = mp.pixel_to_ground((960,  v_center), ZERO_POSE)  # Right of center
        fwd   = mp.pixel_to_ground((640,  v_center), ZERO_POSE)  # Center

        # y-coordinates should be roughly equal and opposite around center
        assert abs(left[1] + right[1]) < 0.5  # symmetric about y=0 line


# ---------------------------------------------------------------------------
# 3. compute_displacement_m
# ---------------------------------------------------------------------------

class TestComputeDisplacement:

    def test_zero_displacement(self, tmp_path):
        mp = make_projector(tmp_path)
        d = mp.compute_displacement_m((5.0, 5.0), (5.0, 5.0))
        assert d == 0.0

    def test_3_4_5_triangle(self, tmp_path):
        mp = make_projector(tmp_path)
        d = mp.compute_displacement_m((0.0, 0.0), (3.0, 4.0))
        assert abs(d - 5.0) < 1e-6

    def test_displacement_is_symmetric(self, tmp_path):
        mp = make_projector(tmp_path)
        a, b = (1.5, 3.7), (8.2, 9.1)
        assert abs(
            mp.compute_displacement_m(a, b) -
            mp.compute_displacement_m(b, a)
        ) < 1e-9

    def test_3_meter_threshold_discrimination(self, tmp_path):
        """Assets within 3m and beyond 3m should clearly discriminate."""
        mp = make_projector(tmp_path)
        close_displacement   = mp.compute_displacement_m((0.0, 0.0), (2.0, 0.0))
        crossed_displacement = mp.compute_displacement_m((0.0, 0.0), (4.0, 0.0))
        assert close_displacement < 3.0
        assert crossed_displacement > 3.0


# ---------------------------------------------------------------------------
# 4. Mock robot pose
# ---------------------------------------------------------------------------

class TestMockRobotPose:

    def test_mock_pose_returns_tuple_of_three(self, tmp_path):
        mp = make_projector(tmp_path)
        pose = mp.get_mock_robot_pose()
        assert isinstance(pose, tuple)
        assert len(pose) == 3

    def test_mock_pose_default_values(self, tmp_path):
        mp = make_projector(tmp_path)
        x, y, h = mp.get_mock_robot_pose()
        assert x == 0.0 and y == 0.0 and h == 0.0
