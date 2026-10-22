"""
ASI Perception System — ROS2 Integration Node
Spec: PER-ROS-001 → 005

Bridges the perception pipeline to the ROS2 navigation stack.

CURRENT STATE: Structural stub with full TODO annotations.
Full implementation pending Nav team ROS2 bag file and topic names.

Integration contract with Navigation team:
  SUBSCRIBES TO:
    - Camera RGB topic         → topic name TBD (e.g., /camera/color/image_raw)
    - Camera info topic        → topic name TBD (e.g., /camera/color/camera_info)
    - Robot odometry / TF      → topic name TBD (e.g., /odom or /tf)

  PUBLISHES TO:
    - /perception/detections   → JSON string (asset_id, class, position, identity_status, alerts)
    - /perception/evidence_events → JSON string (evidence file paths on state-change events)

When the Nav team provides the bag file and topic names:
  1. Fill in TOPIC_* constants below.
  2. Replace mock_robot_pose with TF/odom subscriber.
  3. Test against bag file with: ros2 bag play <bag_file>
"""

# ==========================================================================
# TODO: Fill these in once Nav team provides bag file + topic names
# ==========================================================================
TOPIC_CAMERA_RGB    = "/camera/color/image_raw"    # TODO: confirm with Nav team
TOPIC_CAMERA_INFO   = "/camera/color/camera_info"  # TODO: confirm with Nav team
TOPIC_ODOM          = "/odom"                      # TODO: confirm with Nav team (or /tf)
TOPIC_DETECTIONS    = "/perception/detections"     # outbound — this side owns this
TOPIC_EVIDENCE      = "/perception/evidence_events" # outbound — this side owns this
# ==========================================================================

import sys
import json
from pathlib import Path

# Add project root to path (for running as standalone ROS2 node)
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.image_quality    import ImageQualityChecker
from src.detector         import Detector
from src.reid_engine      import ReIDEngine
from src.reference_store  import ReferenceStore
from src.asset_state_registry import AssetStateRegistry
from src.map_projection   import MapProjector
from src.evidence_generator   import EvidenceGenerator


def run_standalone():
    """
    Standalone (non-ROS2) perception pipeline runner.
    Uses webcam or video file as input instead of ROS2 camera topic.
    Used for development and testing without a running ROS2 environment.
    """
    import cv2
    import yaml

    print("[ros2_node] Running in STANDALONE mode (no ROS2 required).")
    print("[ros2_node] For ROS2 mode, implement the ROS2Node class below.")

    with open("config/camera_config.yaml") as f:
        cam_cfg = yaml.safe_load(f)

    source = cam_cfg.get("source", 0)
    target_fps = cam_cfg.get("target_fps", 5)

    # Initialize pipeline
    quality_checker = ImageQualityChecker()
    detector        = Detector()
    reid_engine     = ReIDEngine()
    ref_store       = ReferenceStore()
    state_registry  = AssetStateRegistry()
    map_projector   = MapProjector()
    evidence_gen    = EvidenceGenerator()

    cap = cv2.VideoCapture(source)
    if not cap.isOpened():
        print(f"[ros2_node] ERROR: Cannot open camera source: {source}")
        return

    frame_interval_ms = int(1000 / target_fps)
    print(f"[ros2_node] Pipeline running at target {target_fps} FPS. Press 'q' to stop.")

    # Begin patrol cycle (in ROS2 mode this would be event-driven per camera topic message)
    state_registry.begin_patrol_cycle()
    cycle_frame_count = 0
    frames_per_cycle = 10  # Treat every 10 frames as one "patrol cycle"

    while True:
        ret, frame = cap.read()
        if not ret:
            print("[ros2_node] Frame read failed. Stopping.")
            break

        cycle_frame_count += 1

        # ----------------------------------------------------------------
        # Step 1: Image Quality Gate
        # ----------------------------------------------------------------
        quality_result = quality_checker.check(frame)
        if quality_result["quality"] == "UNUSABLE":
            continue

        # ----------------------------------------------------------------
        # Step 2: YOLO Detection
        # ----------------------------------------------------------------
        detections, annotated_frame = detector.detect_and_draw(frame)

        # ----------------------------------------------------------------
        # Step 3: Per-detection Re-ID + State Update
        # ----------------------------------------------------------------
        crop_results = reid_engine.crop_detections(frame, detections)

        mock_robot_pose = map_projector.get_mock_robot_pose()  # TODO: replace with ROS2 odom

        for crop_info in crop_results:
            det = crop_info["detection"]

            # Extract Re-ID embedding
            embedding = None
            if crop_info["valid"]:
                embedding = reid_engine.extract_embedding(crop_info["crop"])

            identity_status = "UNKNOWN"
            similarity_score = 0.0
            asset_id = None

            if embedding is not None:
                match_result = ref_store.query(embedding, class_filter=det["object_class"])
                identity_status  = match_result["identity_status"]
                similarity_score = match_result["similarity_score"]
                asset_id         = match_result["asset_id"]

            if asset_id is None:
                # Auto-generate candidate ID for unknown assets
                asset_id = f"UNKNOWN_{det['object_class'].replace(' ', '_').upper()}_0"

            # ----------------------------------------------------------------
            # Step 4: Map Projection — pixel bbox center → site coordinate
            # ----------------------------------------------------------------
            bbox_center = map_projector.bbox_center(det["bbox_xyxy"])
            site_position = map_projector.pixel_to_ground(bbox_center, mock_robot_pose)

            # ----------------------------------------------------------------
            # Step 5: State Registry Update
            # ----------------------------------------------------------------
            state_update = state_registry.update(
                asset_id        = asset_id,
                class_name      = det["object_class"],
                position        = site_position,
                identity_status = identity_status,
                similarity_score = similarity_score
            )

            # Attach identity and state info to detection dict for evidence
            det["asset_id"]        = asset_id
            det["identity_status"] = identity_status
            det["identity_confidence"] = similarity_score
            det["movement_state"]  = state_update["movement_state"]

            # ----------------------------------------------------------------
            # Step 6: Evidence Capture (on alerts or state changes)
            # ----------------------------------------------------------------
            if state_update["alert"] is not None:
                evidence_result = evidence_gen.capture(
                    frame            = frame,
                    detection        = det,
                    annotated_frame  = annotated_frame,
                    model_version    = "standalone_dev"
                )
                alert = state_update["alert"]
                print(f"[ros2_node] {alert['alert_type']}: {asset_id} | "
                      f"Evidence: {evidence_result['evidence_refs'][0]}")

            # ----------------------------------------------------------------
            # Step 7: Publish to ROS2
            # TODO: Replace print with rclpy publisher once ROS2 is integrated
            # ----------------------------------------------------------------
            publish_payload = {
                "asset_id":         asset_id,
                "class_name":       det["object_class"],
                "identity_status":  identity_status,
                "similarity_score": round(similarity_score, 4),
                "movement_state":   state_update["movement_state"],
                "site_position":    site_position,
                "alert":            state_update["alert"],
            }
            # TODO: self.detection_publisher.publish(json.dumps(publish_payload))
            # For now — print to stdout for development visibility
            # print(f"[PUBLISH] {json.dumps(publish_payload)}")

        # ----------------------------------------------------------------
        # Patrol cycle bookkeeping — advance every N frames
        # ----------------------------------------------------------------
        if cycle_frame_count >= frames_per_cycle:
            missing_alerts = state_registry.end_patrol_cycle()
            for alert in missing_alerts:
                print(f"[ros2_node] {alert['alert_type']}: {alert['asset_id']} "
                      f"not seen for {state_registry.get_state(alert['asset_id'])['consecutive_misses']} cycles.")
            state_registry.begin_patrol_cycle()
            cycle_frame_count = 0

        # Display (standalone dev mode only)
        cv2.imshow("SITE Assets Monitor — Standalone Dev", annotated_frame)
        key = cv2.waitKey(frame_interval_ms) & 0xFF
        if key == ord("q"):
            print("[ros2_node] Quit requested.")
            break

    cap.release()
    cv2.destroyAllWindows()
    print("[ros2_node] Pipeline stopped.")


# ==========================================================================
# ROS2 NODE CLASS — To be implemented once bag file + topics are known
# ==========================================================================
class ROS2PerceptionNode:
    """
    Full ROS2 integration node.

    TODO: Implement this class once the Nav team provides:
      1. ROS2 bag file (for testing)
      2. Camera topic name (e.g., /camera/color/image_raw)
      3. Camera info topic name
      4. Odometry/TF topic name and frame names

    Implementation steps (when ready):
      1. Import rclpy and rclpy.node
      2. Subscribe to camera topic → callback runs the full pipeline below
      3. Subscribe to odom/TF → update robot pose variable used by MapProjector
      4. Create publishers for TOPIC_DETECTIONS and TOPIC_EVIDENCE
      5. Implement camera_callback() that runs the same pipeline as run_standalone()
         but reads frames from ROS2 messages instead of cv2.VideoCapture

    Skeleton:
        import rclpy
        from rclpy.node import Node
        from sensor_msgs.msg import Image, CameraInfo
        from nav_msgs.msg import Odometry
        from std_msgs.msg import String
        from cv_bridge import CvBridge

        class ROS2PerceptionNode(Node):
            def __init__(self):
                super().__init__('site_assets_monitor')
                # Subscribers
                self.create_subscription(Image, TOPIC_CAMERA_RGB, self.camera_callback, 10)
                self.create_subscription(Odometry, TOPIC_ODOM, self.odom_callback, 10)
                # Publishers
                self.detection_pub = self.create_publisher(String, TOPIC_DETECTIONS, 10)
                self.evidence_pub  = self.create_publisher(String, TOPIC_EVIDENCE, 10)
                # Pipeline modules (same as standalone)
                self.bridge = CvBridge()
                ...

            def odom_callback(self, msg):
                # Extract (x, y, heading) from msg.pose.pose
                ...

            def camera_callback(self, msg):
                frame = self.bridge.imgmsg_to_cv2(msg, 'bgr8')
                # Run full pipeline (same as run_standalone loop body)
                ...
    """
    pass  # Implement when Nav team bag file + topic names are received


# ==========================================================================
# Entry Point
# ==========================================================================
if __name__ == "__main__":
    run_standalone()
