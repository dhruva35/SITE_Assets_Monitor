# ROS & Navigation Team Deliverables: Technical Alignment & Confirmation Guide

**Project:** SITE Assets Monitor — Autonomous Visual Security & Spatial Tracking  
**Target Vehicle:** Autonomous Ground Vehicle (AGV / UGV)  
**Status:** Working Draft for Team Discussion & Sign-Off  
**Date:** September 2026  

---

## 1. Executive Purpose & Context

To integrate the **SITE Assets Monitor** (AI Perception & Visual Re-ID) with the mobile robot platform without unnecessary back-and-forth or integration delays, the **Perception Team** and the **ROS / Navigation Team** need to align on a clean, standardized software interface contract.

This document summarizes:
1. **The 4 Core Deliverables** needed from the Navigation team.
2. **Key Discussion Points** to confirm during our alignment meeting.
3. **The Perception Output Interface** (what our node sends back to the fleet manager).
4. **An Actionable Confirmation Checklist** for team sign-off.

> [!IMPORTANT]
> **Strict Integration Principle:**  
> The Perception team will **not** build speculative ROS2 drivers or coordinate transformation math until these 4 inputs are formally reviewed and confirmed with the Robotics/Navigation team.

---

## 2. The 4 Required Deliverables from Navigation Team

### Deliverable 1: Clean Camera Video & Depth Streams ("The Eyes")
* **What it is:** Synchronized color image, depth map, and optical camera intrinsics coming from the robot's front-facing 3D camera (e.g., Orbbec Gemini 335L / RealSense).
* **Why it's needed:** The AI uses the RGB feed to detect and recognize equipment via visual features (YOLO + OSNet Re-ID), and uses the depth feed to measure the metric distance $(X_c, Y_c, Z_c)$ in 3D camera space.

| Interface Element | Proposed Specification | Navigation Team Confirmed Spec |
| :--- | :--- | :--- |
| **Color Image Topic** | `/camera/color/image_raw` (`sensor_msgs/msg/Image`) | *(To confirm)* |
| **Color Resolution & Rate** | 1920×1080 (or 1280×720) @ 15–30 FPS | *(To confirm)* |
| **Depth Image Topic** | `/camera/depth/image_raw` (`sensor_msgs/msg/Image`) | *(To confirm)* |
| **Depth Format** | `16UC1` (16-bit unsigned integer, raw millimeters) | *(To confirm)* |
| **Camera Intrinsics** | `/camera/color/camera_info` (`sensor_msgs/msg/CameraInfo`) | *(To confirm)* |
| **Camera Optical Frame** | `camera_color_optical_frame` | *(To confirm)* |

---

### Deliverable 2: Robot Localization & TF Coordinate Tree ("The Location")
* **What it is:** The robot’s live spatial pose and the coordinate transformation tree connecting the global map to the optical camera frame.
* **Why it's needed:** When the camera detects a generator 4.2 meters ahead, our node must project that 3D vector through the robot's pose to compute the asset's exact global coordinate on the site map:
  $$\mathbf{P}_{\text{map}} = \mathbf{T}_{\text{map}\leftarrow\text{odom}} \cdot \mathbf{T}_{\text{odom}\leftarrow\text{base\_link}} \cdot \mathbf{T}_{\text{base\_link}\leftarrow\text{camera\_link}} \cdot \mathbf{P}_{\text{camera}}$$

| Interface Element | Proposed Specification | Navigation Team Confirmed Spec |
| :--- | :--- | :--- |
| **Dynamic Transforms** | `/tf` (`tf2_msgs/msg/TFMessage`) covering `map` $\rightarrow$ `odom` $\rightarrow$ `base_link` | *(To confirm)* |
| **Static Transforms** | `/tf_static` covering `base_link` $\rightarrow$ `camera_link` $\rightarrow$ `camera_color_optical_frame` | *(To confirm)* |
| **Fallback Pose Topic** | `/robot/pose` or `/amcl_pose` (`geometry_msgs/msg/PoseWithCovarianceStamped`) | *(To confirm)* |
| **Mounting Parameters** | Camera height above ground ($Z$), forward offset ($X$), and downward pitch angle | *(To confirm)* |

---

### Deliverable 3: 5-Minute Practice Test ROS2 Bag File ("The Practice Drive")
* **What it is:** A short 3- to 5-minute pre-recorded ROS2 bag file (`.mcap` preferred, or `.db3`) captured while driving the robot in the yard or facility.
* **Why it's needed:** Allows the Perception team to develop, calibrate, and verify the entire detection, Re-ID, and 3D projection pipeline offline on our development machines **without tying up the physical robot or delaying field operations**.

#### Recommended Bag Recording Scenario:
1. **Duration:** 3 to 5 minutes continuous driving.
2. **Environment:** Real facility yard, warehouse, or staging area.
3. **Targets:** 2 or 3 stationary assets (e.g., a generator, an air compressor, or a tool chest).
4. **Motion:** Robot drives at normal patrol speed (0.5 – 1.0 m/s), approaches each asset within 2–8 meters, pauses briefly (2–3 seconds), and circles past.
5. **Topics to Record:**
   - `/camera/color/image_raw` (or `/camera/color/image_raw/compressed`)
   - `/camera/depth/image_raw`
   - `/camera/color/camera_info`
   - `/tf` and `/tf_static`
   - `/odom` (optional, for velocity check)

---

### Deliverable 4: Network & ROS2 Connectivity to our Dedicated Pi
* **What it is:** A reliable Ethernet or high-speed network link connecting your navigation controller to our **dedicated Perception Raspberry Pi 5 (16GB)**.
* **Why it's needed:** Since we are running the perception AI on a dedicated, independent Raspberry Pi, we don't need to share your compute. However, our Pi still needs to subscribe to your `/tf` topics and publish our `/perception/asset_alerts` back to your fleet manager over the ROS2 network.

| Networking Requirement | Proposed Specification | Navigation Team Confirmed Spec |
| :--- | :--- | :--- |
| **Physical Connection** | Gigabit Ethernet between Navigation PC and Perception Pi | *(To confirm)* |
| **ROS2 Domain ID** | Shared `ROS_DOMAIN_ID` for DDS communication | *(To confirm)* |
| **Time Synchronization** | Chrony / NTP syncing between the two computers | *(To confirm)* |
| **Network Config** | Static IP allocation for the Perception Pi | *(To confirm)* |

---

## 3. What Perception Delivers in Return (The Output Contract)

To ensure the Navigation / Fleet Management system can easily consume asset tracking results, the Perception node publishes clean, structured alerts on a single ROS2 topic:

* **Published Topic:** `/perception/asset_alerts`
* **Message Type:** `std_msgs/msg/String` (JSON format) or custom `site_assets_msgs/msg/AssetAlert`
* **Update Frequency:** Event-driven (published whenever an asset is scanned or audited)

### Example Alert Payload:
```json
{
  "timestamp": "2026-09-28T14:30:15.120Z",
  "asset_id": "ASSET_GEN_004",
  "custom_label": "Main Generator Bay 2",
  "category": "Generator",
  "status": "MOVED",
  "baseline_position_map": {"x": 24.50, "y": 12.30, "z": 0.00},
  "current_position_map":  {"x": 28.75, "y": 14.10, "z": 0.00},
  "delta_distance_meters": 4.62,
  "confidence_score": 0.912,
  "evidence_image_path": "/var/log/assets/evidence_ASSET_GEN_004_20260928_143015.jpg"
}
```

### The 3 Core Status Rules:
1. `IN_PLACE`: Delta distance $\le 3.0$ meters (Safe, normal operational variance).
2. `MOVED`: Delta distance $> 3.0$ meters (Alert triggered, security notified with photo).
3. `MISSING`: Target asset expected at waypoint but not detected (Priority Alert).

---

## 4. Key Questions for the Upcoming Alignment Meeting

During our discussion with the ROS & Navigation team, we should walk through these 6 specific questions:

1. **Exact Topic Names:** Are the camera and depth topics published under `/camera/...` or a custom namespace (e.g., `/orbbec/...` or `/front_camera/...`)?
2. **Hardware Time Synchronization:** Are color and depth frames hardware-synchronized by the camera driver, or should our node use `message_filters::ApproximateTimeSynchronizer`?
3. **Coordinate Frame Conventions:** Does the TF tree follow standard ROS REP-103 (X-forward, Y-left, Z-up) and REP-105 (`map` $\rightarrow$ `odom` $\rightarrow$ `base_link`)?
4. **Camera Mounting Extrinsics:** Is the camera mounted fixed or on a pan-tilt head? If fixed, what is the exact height and tilt pitch angle relative to the ground plane?
5. **Rosbag Recording Schedule:** When can the navigation team record and transfer the 5-minute practice bag file?
6. **Execution Architecture:** Will the Perception node run directly onboard the robot's computer, or will it run on an edge workstation receiving compressed streams via Wi-Fi?

---

## 5. Sign-Off & Confirmation Checklist

| # | Item | Responsible Team | Target Date | Status |
| :-: | :--- | :--- | :-: | :-: |
| **1** | Camera & Depth topic names and message formats confirmed | ROS / Navigation | — | 🔲 In Discussion |
| **2** | `/tf` frame hierarchy and mounting extrinsics confirmed | ROS / Navigation | — | 🔲 In Discussion |
| **3** | Compute allocation (CPU/GPU/RAM) and OS/ROS2 distro verified | System Architect | — | 🔲 In Discussion |
| **4** | 5-Minute practice test rosbag recorded & delivered | Navigation Team | — | 🔲 Pending Bag |
| **5** | Perception node offline playback verification completed | Perception Team | — | 🔲 Pending Bag |
| **6** | Interface contract signed off; green light for node coding | Both Teams | — | 🔲 Pending Meeting |

---

*This document is ready to be printed or shared directly with the Navigation Team lead ahead of the alignment session.*
