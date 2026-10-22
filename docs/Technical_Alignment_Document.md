# SITE Assets Monitor — Perception System: Technical Alignment Document

**Prepared for:** Navigation / ROS2 Team Lead  
**Prepared by:** Dhruva (Perception Team)  
**Date:** October 2026  
**Purpose:** Validate the perception layer's internal design against the proposed architecture and confirm the ROS2 integration handshake points.

---

## 1. Executive Summary

The perception system has been built as a **fully standalone, ROS2-agnostic Python library**. It does not depend on ROS2 to run. It is designed to plug into a ROS2 node as a thin adapter — meaning the Nav team's bag files and topic names are the **only missing connector** before live end-to-end testing can begin.

All internal modules are operational and unit-tested in isolation.

---

## 2. Architecture Alignment Map

The table below maps every layer of the proposed POC architecture to its current implementation status.

| Layer (from Proposed Arch) | Proposed Component | Our Implementation | Status |
|---|---|---|---|
| **Camera Input** | RGB-D Camera (Orbbec Femto Mega) | `config/camera_config.yaml` — source configurable (webcam / video / RTSP / ROS topic) | ✅ Config-ready, pluggable |
| **Image Pre-processing** | Quality gating before inference | `ImageQualityChecker` — blur (Laplacian variance), brightness, overexposure check | ✅ Built & tested |
| **Object Detection** | YOLO-based Detection Node | `Detector` class — YOLOv8 / ONNX, 17-class construction taxonomy, config-driven thresholds | ✅ Built & tested |
| **Re-Identification** | Appearance Embedding | `ReIDEngine` — OSNet ONNX backbone, 512D L2-normalised embedding per asset crop | ✅ Built & tested |
| **Asset Identity Store** | DB / Unordered Map (as per TL) | `ReferenceStore` — in-memory Python dict + `.npz` file persistence, cosine similarity matching | ✅ Built (simplified as TL directed — no heavy DB) |
| **Identity Decision** | Confidence Thresholding | `ReferenceStore.query()` — 4-tier status: CONFIRMED / PROBABLE / AMBIGUOUS / UNKNOWN | ✅ Built & tested |
| **Evidence Logging** | Asset photo + metadata capture | `EvidenceGenerator` — full frame, cropped asset, annotated frame, metadata JSON per detection event | ✅ Built & tested |
| **ROS2 Wrapper / Node** | Perception Node subscribing to camera + TF | Skeleton config ready (`camera_config.yaml` has ROS topic placeholder). **Awaiting: topic names + bag file** | ⏳ Pending Nav team data |
| **Map Coordinate Projection** | TF-based 2D→3D projection | Ground plane projection math (in progress — being validated with mock robot poses) | 🔄 In progress |
| **Navigation Interface** | Output to Nav/Mapping stack | Will publish on agreed ROS2 topics. Interface to be confirmed with Nav team | ⏳ Pending alignment |

---

## 3. Module-by-Module Technical Breakdown

### 3.1 — Image Quality Checker (`src/image_quality.py`)

**Role in Architecture:** Pre-processing gate — prevents bad frames from reaching the detector.

**What it does:**
- Measures **sharpness** using Laplacian variance. A blurry moving-robot frame is rejected before it wastes inference time.
- Measures **brightness** — catches frames that are too dark (night / shadow) or overexposed (direct sunlight glare).
- Returns a 3-tier verdict: `GOOD` / `DEGRADED` / `UNUSABLE`

**ROS2 Connection Point:** Will gate the raw frame received from `/camera/color/image_raw` before passing it downstream.

---

### 3.2 — Detector (`src/detector.py`)

**Role in Architecture:** The primary perception engine — Layer 2 in the proposed stack.

**What it does:**
- Loads a **YOLOv8 model** (ONNX format for deployment on Raspberry Pi 5 / CPU)
- Runs inference on a single BGR frame
- Returns structured detections:
  ```python
  {
    "object_class":          "Excavator",
    "class_id":              1,
    "bbox_xyxy":             [412, 230, 680, 510],  # pixel bounding box
    "detection_confidence":  0.87,
    "is_asset":              True    # True = trackable site asset
  }
  ```
- Handles two detection categories:
  - **Asset classes** (17 equipment types: excavators, dump trucks, cranes, etc.) — tracked with ReID
  - **Context classes** (trucks, gazelles) — detected but not ID-tracked

**ROS2 Connection Point:** This module takes a `numpy BGR image` in. Once the ROS2 node is built, the node will call `cv_bridge.imgmsg_to_cv2()` to convert the `/camera/color/image_raw` message into this exact format.

---

### 3.3 — ReID Engine (`src/reid_engine.py`)

**Role in Architecture:** Visual fingerprinting — assigns a persistent identity to each detected asset.

**What it does:**
- Takes the **bounding box crop** from the Detector output
- Runs it through **OSNet ONNX** (a lightweight re-identification neural network)
- Outputs a **512-dimensional embedding vector** — a numerical "visual fingerprint" unique to each physical machine
- The embedding is L2-normalised so that cosine distance is simple and reliable

**Why OSNet?** It was trained specifically for the re-identification task (originally on person re-ID datasets but the architecture generalises well to rigid objects). The ONNX export means it runs on the Pi 5 CPU with no GPU required.

**ROS2 Connection Point:** Purely internal — no ROS2 interface needed. This module is called by the perception node after every detection.

---

### 3.4 — Reference Store (`src/reference_store.py`)

**Role in Architecture:** Replaces the proposed database layer with a **lightweight Python dictionary + `.npz` file persistence** — exactly as the team lead directed.

**What it does:**
- Stores known asset fingerprints: `{asset_id → list of 512D embeddings}`
- Matches incoming embeddings via **cosine similarity** against all known assets
- Returns a 4-tier match status:
  - `CONFIRMED` — score ≥ 0.85 AND clear margin from second candidate
  - `PROBABLE` — score ≥ 0.65 with good margin
  - `AMBIGUOUS` — score is OK but two candidates look too similar
  - `UNKNOWN` — score below minimum threshold (0.40) — treat as new asset
- Supports multiple reference embeddings per asset (up to 10) for better robustness when the machine is seen from different angles

**Storage:** Each asset saves as a `.npz` file in `data/reference_db/`. No database server required. Survives robot restarts.

**ROS2 Connection Point:** None. Fully internal persistence layer.

---

### 3.5 — Evidence Generator (`src/evidence_generator.py`)

**Role in Architecture:** Audit & logging layer — creates the evidence package that the client (and the operator dashboard, when built) will consume.

**What it saves per detection event:**
1. `full_TIMESTAMP_CLASS_ID.jpg` — Original unannotated frame (legal-grade evidence)
2. `crop_TIMESTAMP_CLASS_ID.jpg` — Padded crop of the detected asset
3. `annotated_TIMESTAMP_CLASS_ID.jpg` — Frame with bounding boxes drawn
4. `meta_TIMESTAMP_CLASS_ID.json` — Full metadata record:
   ```json
   {
     "timestamp": "2026-10-11T06:30:00Z",
     "asset_id": "EXC-024",
     "object_class": "Excavator",
     "detection_confidence": 0.87,
     "identity_status": "CONFIRMED",
     "movement_state": "STATIONARY",
     "bbox_xyxy": [412, 230, 680, 510],
     "model_version": "yolo_v1.0_site_A"
   }
   ```

**ROS2 Connection Point:** The `movement_state` field will be enriched by map-coordinate data once the TF pipeline is integrated.

---

## 4. ROS2 Integration — The Handshake Points

This is the precise list of what is needed from the Navigation team to complete integration.

### 4.1 What We Need From Nav Team

| Item | Why We Need It | Current Placeholder |
|---|---|---|
| **ROS2 bag file** | To replay real sensor data and test the full pipeline end-to-end | Video file (`.mp4`) used as substitute for development |
| **Camera topic name** | e.g., `/camera/color/image_raw` or `/amr/front_cam/image` | `/camera/color/image_raw` (default) in `camera_config.yaml` |
| **`camera_info` topic name** | For reading camera intrinsic calibration (focal length, distortion) — required for 3D projection | `/camera/color/camera_info` (default) |
| **TF frame names** | `map_frame` and `camera_frame` names used in the robot's TF tree — for converting pixel coords to map coords | `map` and `camera_link` (defaults) |
| **Odometry / Pose topic** | Robot position + heading on the map — required for projecting detections to world coordinates | `/odom` (default) |

### 4.2 What We Provide to the Nav Stack (Our Outputs)

Once integrated, the Perception Node will **publish** the following on ROS2 topics (topic names to be agreed):

| Output | ROS2 Message Type | Content |
|---|---|---|
| Detected assets | `std_msgs/String` (JSON) | Asset ID, class, bounding box, confidence, identity status |
| Asset map positions | `geometry_msgs/PoseArray` or custom msg | World (X, Y) position of each confirmed asset |
| Event flags | `std_msgs/Bool` or custom | `ASSET_MOVED` alert when an asset has shifted more than threshold |

---

## 5. What is NOT Being Built (Simplified POC Scope)

As directed by the team lead, the following are intentionally out of scope for the POC:

| Removed from Scope | Reason | Replacement |
|---|---|---|
| Multi-Object Tracking (SORT/DeepSORT) | Not needed immediately for stationary-asset monitoring | ReID engine handles cross-frame identity |
| SQL / PostgreSQL / SQLite Database | Overkill for POC | Python dict + `.npz` file persistence (`ReferenceStore`) |
| Operator Web Dashboard | Can be added later as a separate service | Evidence JSON files + folder structure serve as audit log |
| Depth-based 3D Localization | Requires Orbbec SDK integration | Ground-plane projection using camera geometry (simpler, adequate for POC) |

---

## 6. Open Questions for Team Lead

1. **Topic names:** Can you confirm the exact ROS2 topic names from the robot's camera driver so we can update `camera_config.yaml`?
2. **TF frame names:** What are the `map_frame` and `camera_frame` identifiers in your TF tree?
3. **Output interface:** Should the perception node publish on `sensor_msgs/Image` (annotated), or just structured data messages? Or both?
4. **Bag file:** When can we expect the test bag for end-to-end validation? (Not blocking — we are developing with mock data in parallel.)

---

## 7. Summary of Build Status

```
SITE Assets Monitor — Perception Layer
├── src/
│   ├── image_quality.py     ✅ Complete — Image gating (blur, brightness)
│   ├── detector.py          ✅ Complete — YOLOv8 ONNX inference + 17-class taxonomy
│   ├── reid_engine.py       ✅ Complete — OSNet ONNX 512D visual fingerprinting
│   ├── reference_store.py   ✅ Complete — In-memory dict + .npz persistence + cosine matching
│   └── evidence_generator.py ✅ Complete — Full evidence package capture (frame + crop + JSON)
│
├── config/
│   ├── detection_config.yaml  ✅ 17-class taxonomy configured
│   ├── reid_config.yaml       ✅ Similarity thresholds calibrated
│   ├── camera_config.yaml     ✅ ROS topic placeholders ready (⏳ awaiting actual names)
│   └── evidence_config.yaml   ✅ Evidence capture settings
│
└── Pending:
    ├── ros2_node.py           ⏳ Thin adapter — awaiting bag + topic names from Nav team
    └── map_projection.py      🔄 In progress — ground-plane 2D→3D coordinate math
```

---

*This document is intended for technical review by the Navigation team lead. All modules are available for code inspection. A visual system diagram accompanies this document.*
