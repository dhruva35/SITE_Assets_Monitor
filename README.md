# SITE Assets Monitor — Perception & Visual Re-ID Engine

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![Tests](https://img.shields.io/badge/tests-119%20passed-brightgreen.svg)]()
[![Platform](https://img.shields.io/badge/platform-ROS2%20%7C%20Linux%20%7C%20Windows-lightgrey.svg)]()

Autonomous visual security, asset tracking, and spatial audit engine for mobile ground robots (UGVs/AGVs). Designed to operate in industrial yards, construction sites, and logistics facilities without requiring RFID tags, QR codes, or physical markers.

---

## 🏗️ System Overview

The perception system enables a patrolling robot to recognize high-value assets (generators, compressors, tool chests, equipment crates, vehicles) by visual appearance, track their positions on site coordinates, and fire automated alerts with forensic photo proof if an asset is moved (>3 meters) or missing.

### Core Modules (`src/`)

| Module | Component | Description |
| :--- | :--- | :--- |
| `image_quality.py` | Frame Quality Gate | Validates Laplacian variance (blur) and luminance (exposure) before inference. |
| `detector.py` | YOLOv8 ONNX Wrapper | Performs fast object detection with configurable confidence thresholds and class filtering. |
| `reid_engine.py` | OSNet Re-ID Engine | Extracts 512-dimensional L2-normalized visual embeddings for appearance matching. |
| `reference_store.py` | Embedding Store | Persistent gallery of asset embeddings; supports cosine similarity querying with confidence margins. |
| `asset_state_registry.py` | State Machine & Alerts | Tracks temporal movement (`STATIONARY`, `SUSPECTED`, `MOVING`), missing asset hysteresis, and displacement alerts. |
| `map_projection.py` | Ground Plane Projector | Projects 2D bounding boxes into metric ground plane coordinates using robot pose and camera intrinsics. |
| `evidence_generator.py` | Forensic Evidence Logger | Captures cropped visual proof, annotated full frames, and metadata JSON packages for incident logging. |
| `ros2_node.py` | ROS2 Integration Adapter | Standard ROS2 lifecycle/node adapter connecting the perception pipeline to robot topics. |

---

## 🤖 ROS2 Integration Interface

The perception engine operates as a ROS2 node interfacing with the robot's sensor stack and navigation system.

### Subscribed Topics
| Topic Name (Default) | Message Type | Description |
| :--- | :--- | :--- |
| `/camera/color/image_raw` | `sensor_msgs/Image` | Front RGB stream (e.g. Orbbec Gemini 335L / RealSense) |
| `/camera/color/camera_info` | `sensor_msgs/CameraInfo` | Optical intrinsics ($f_x, f_y, c_x, c_y$) |
| `/odom` or `/tf` | `nav_msgs/Odometry` / `tf2_msgs/TFMessage` | Robot base pose $(X_r, Y_r, \theta)$ in map frame |

### Published Topics
| Topic Name | Message Type | Frequency | Description |
| :--- | :--- | :--- | :--- |
| `/perception/detections` | `std_msgs/String` (JSON) | 5 Hz | Real-time detected assets, bounding boxes, Re-ID status, and map coordinates. |
| `/perception/evidence_events` | `std_msgs/String` (JSON) | Event-driven | Fired on state transitions (`ASSET_MOVED`, `ASSET_MISSING`, `NEW_ASSET`). Contains file paths to evidence crop & metadata. |

### Payload Schema (`/perception/detections`)
```json
{
  "timestamp": 1729618000.123,
  "cycle_id": 42,
  "detections_count": 2,
  "assets": [
    {
      "asset_id": "GEN-01",
      "class": "generator",
      "confidence": 0.92,
      "reid_score": 0.88,
      "state": "STATIONARY",
      "bbox": [120, 200, 350, 480],
      "site_position": {"x": 14.52, "y": 8.31},
      "alerts": []
    }
  ]
}
```

---

## 📋 Integration Next Steps (For ROS2 Navigation Team)

To complete the end-to-end integration with the robot platform:

1. **Review Deliverables Guide:** See [`docs/ROS_Navigation_Team_Deliverables_Discussion.md`](docs/ROS_Navigation_Team_Deliverables_Discussion.md) for full topic specifications and questions.
2. **Rosbag Sample:** Provide a short 3–5 minute `.mcap` or `.db3` recording with `/camera/color/image_raw`, `/camera/color/camera_info`, and `/tf` while driving past 2–3 stationary yard objects.
3. **Optical Frame Confirmation:** Confirm camera optical frame ID and mount height/tilt angle relative to `base_link`.

---

## 🚀 Getting Started

### 1. Installation

```bash
# Clone the repository
git clone https://github.com/appnetuk-maker/SITE_Assets_Monitor.git
cd SITE_Assets_Monitor

# Create and activate virtual environment
python -m venv venv
# Linux / macOS:
source venv/bin/activate
# Windows:
venv\Scripts\activate

# Install runtime dependencies
pip install -r requirements.txt
```

### 2. Run Test Suite

The perception core is verified with 119 automated unit tests covering detection, Re-ID embedding normalization, cosine matching, state transitions, missing hysteresis, and projection mathematics:

```bash
pytest -v
```

### 3. Run Standalone Perception Demo

```bash
python scripts/demo_detection.py
```

---

## 📂 Documentation

- [ROS Navigation Team Deliverables & Interface Contract](docs/ROS_Navigation_Team_Deliverables_Discussion.md)
- [System Overview & Stakeholder Guide](docs/System_Workflow_and_Integration_Deliverables.md)
- [Technical Alignment & Hardware Specifications](docs/Technical_Alignment_Document.md)
