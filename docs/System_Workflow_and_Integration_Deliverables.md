# SITE Assets Monitor: System Overview & Project Deliverables Guide
*(A Non-Technical Guide for Stakeholders & Operations Teams)*

---

## 1. What is the SITE Assets Monitor?

The **SITE Assets Monitor** is an intelligent visual security and tracking system designed for industrial work sites, yards, and warehouses. It turns a patrolling mobile robot into an **automated site auditor** that keeps 24/7 watch over high-value equipment (such as generators, air compressors, tool chests, equipment crates, and pallets).

### Why this is different from traditional tracking:
* **No RFID tags or barcode stickers needed:** Physical tags get scratched, covered in mud, or torn off. Our system uses smart cameras to recognize equipment by its actual visual appearance—just like a human guard would.
* **No manual clipboard counting:** Workers no longer have to spend hours walking the yard to locate equipment.
* **Instant alerts with photographic proof:** If an asset is moved more than **3 meters (10 feet)** from where it belongs, the system immediately flags it and provides photo evidence of the movement.

---

## 2. How the System Works: The Two Operating Phases

The system operates in two simple steps: **Day 1 Setup** and **Daily Routine Patrols**.

```
+----------------------------------------------------------------------------------------------------+
|                                      HOW THE SYSTEM WORKS                                          |
+----------------------------------------------------------------------------------------------------+
|                                                                                                    |
|  STEP 1: THE INITIAL WALKTHROUGH (One-Time Setup)                                                  |
|  A human guides the robot once through the yard.                                                   |
|  -> The robot takes photos of every machine.                                                       |
|  -> It creates a unique "Digital Fingerprint" for each item.                                       |
|  -> It records its exact "home location" on the site blueprint.                                    |
|                                                                                                    |
|                                     ▼                                                              |
|                                                                                                    |
|  STEP 2: AUTONOMOUS PATROL (Daily Ongoing Watch)                                                   |
|  The robot drives around on its own regular schedule.                                              |
|  -> It spots equipment along its patrol path.                                                      |
|  -> It verifies: "Is this the exact same machine?"                                                 |
|  -> It measures: "Has it moved from where it belongs?"                                             |
|                                                                                                    |
|       🟢 Within 3 meters (10 ft)  ==> [ NORMAL / IN PLACE ]                                        |
|       🟡 Moved > 3 meters (10 ft) ==> [ WARNING / MOVED ] (Alert sent with photo)                  |
|       🔴 Not found in area        ==> [ CRITICAL / MISSING ] (Alert sent)                          |
|                                                                                                    |
+----------------------------------------------------------------------------------------------------+
```

---

### Phase 1: Human Walkthrough (One-Time Setup)
**Analogy:** *"Taking the Initial Inventory & Registering Equipment"*

Before the robot can watch over the site by itself, it needs to learn what equipment exists and where each item normally stays.

1. **The Walkthrough:**  
   An operator guides the robot (using a handheld joystick or remote lead) through the site's work bays, aisles, and storage zones.
2. **Camera Recognition:**  
   As the robot passes machinery, its smart 3D camera spots each asset and identifies what it is (e.g., "Industrial Generator #3").
3. **Creating a "Digital Fingerprint" (Automatic):**  
   The system automatically scans the machine's unique appearance—its shape, color patterns, logos, surface scratches, and equipment tags. This acts like a **Face ID for machines**.
4. **Naming the Equipment (Human-Assigned via UI):**  
   While the robot automatically generates the fingerprint, the human operator uses a simple tablet screen to type in the custom name or ID for the machine (e.g., "Main Welding Unit Alpha" or "Asset #774-B"). The system links this custom name to the new digital fingerprint.
5. **Locking in the Home Location:**  
   The robot notes the exact location on the site blueprint (e.g., *Bay 4, 12 meters from the north wall*) and saves it into the Master Site Inventory database.
6. **Outcome:** A complete, verified digital catalog of all site assets is locked in. This only needs to be done once during initial site commissioning.

---

### Phase 2: Autonomous Patrol (Ongoing Monitoring)
**Analogy:** *"The Automated Security Guard on Duty"*

Once the catalog is built, the robot takes over completely and patrols autonomously on scheduled shifts (e.g., every 2 hours, or overnight).

1. **Self-Driving Patrol:**  
   The robot navigates along its pre-planned patrol routes without needing human intervention.
2. **Live Scanning:**  
   As it drives, the smart camera continuously watches the surroundings and spots equipment up to 10–12 meters (30–40 feet) away.
3. **Identity Verification:**  
   When the robot sees an asset, it compares its live visual fingerprint with the Master Catalog to verify: *"Yes, this is Generator #3, not a different unit."*
4. **The 3-Meter Movement Check:**  
   The robot calculates where the machine is currently sitting compared to where it was registered:

| Status Indicator | What it Means | System Action | What You See |
| :---: | :--- | :--- | :--- |
| 🟢 **IN PLACE** | The asset is in its expected zone (moved **less than 3 meters**). | Logged as safe; no alert needed. Normal daily working tolerance. | Green checkmark on dashboard. |
| 🟡 **MOVED / DISPLACED** | The asset has moved **more than 3 meters (10 ft)** from its spot. | System triggers a displacement alert with before-and-after photo proof. | Yellow alert on phone/computer with photos & new map pin. |
| 🔴 **MISSING** | The robot checked the entire area, but the asset was nowhere to be found. | System triggers a missing equipment alert with the last-known timestamp. | Red priority alert: "Asset Missing from Bay 2". |

---

## 3. What Value & Deliverables You (The Client) Receive

As the site owner and client, here is what this system delivers to your day-to-day operations:

1. **Automated Equipment Audits:**  
   No manual headcounts. You get a real-time summary of all assets, their current statuses, and when they were last seen.
2. **Instant Displacement & Theft Alerts:**  
   Get notified immediately if high-value tools or machinery are moved outside their approved work zones.
3. **Photographic Evidence Package:**  
   Every alert comes with visual documentation:
   - A high-resolution photo of the asset when first registered.
   - A photo showing where and how it is sitting now.
   - An overlay showing how many meters it was moved.
4. **Site Map Visualization:**  
   A clean visual map of your facility showing live colored pins for every piece of equipment (Green = In Place, Yellow = Relocated, Red = Missing).

---

## 4. What We Need from the Robot & Navigation Team

To make this system work seamlessly with your robot vehicle, our AI perception software needs four simple items from the robotics/navigation team. 

Here is what is needed in **plain, simple terms**:

### 1. "The Eyes" — Clean Camera Video Feeds
* **What it is:** Live video and 3D depth feeds coming from the mounted Orbbec 3D camera.
* **Why it's needed:** The AI software uses the color video to recognize what the machine is, and the 3D depth to measure exactly how far away it is standing.

### 2. "The Location" — The Robot's Position on the Map
* **What it is:** The robot's live coordinates on the facility map (like a live indoor GPS position).
* **Why it's needed:** So the system can say: *"The robot is standing at Point A, the generator is 4 meters ahead of the robot, therefore the generator is at Point B on the site map."*

### 3. "A 5-Minute Practice Video" — A Sample Test Recording
* **What it is:** A short 3- to 5-minute pre-recorded test drive of the robot driving past 2 or 3 stationary pieces of equipment.
* **Why it's needed:** This lets our software team test, calibrate, and verify everything on our computers before we test on your actual physical robot, saving hours of on-site setup time.

### 4. "Network & Communication Bridge" — Ethernet & ROS2 Connection
* **What it is:** A standard Gigabit Ethernet connection and network configuration linking our dedicated Raspberry Pi 5 (16GB) perception unit to the robot's navigation computer.
* **Why it's needed:** Our AI perception software runs entirely on its own dedicated hardware (Raspberry Pi 5 16GB), putting **zero CPU or memory load** on your navigation computer. We simply need an Ethernet link, matching network subnet, shared `ROS_DOMAIN_ID`, and clock synchronization so the two systems can seamlessly communicate.

---

## 5. Project Roadmap: Step-by-Step Delivery

| Milestone | What Happens | Timeframe | Outcome for You |
| :--- | :--- | :--- | :--- |
| **Phase A: Setup & Test Drive** | The robotics team provides network access and a 5-minute practice recording. Our team verifies camera calibration. | Week 1 | We confirm the robot's camera, maps, and network talk to our AI software cleanly. |
| **Phase B: Software Tuning** | We run our recognition software on your site's specific equipment models. | Week 2 | The AI reliably identifies your machinery types with 90%+ accuracy. |
| **Phase C: Walkthrough Test** | One initial walkthrough is conducted on your actual site to catalog baseline equipment. | Week 3 | Your site's Master Asset Inventory is created. |
| **Phase D: Autonomous Go-Live** | The robot is turned on for scheduled autonomous patrols with live movement alerts enabled. | Week 4 | Full autonomous operation, daily reports, and real-time alerts active. |

---

## 6. Technical Appendix (For Robotics & Software Engineers)

*(Note: This section contains technical interface details intended for the robot engineering team.)*

If you forward this document to your robot integration team, here are the exact ROS2 topic connections and message formats they will look for:

* **Camera Feeds:**
  - Color Image: `/camera/color/image_raw` (`sensor_msgs/msg/Image`) at 15–30 Hz
  - Depth Image: `/camera/depth/image_raw` (`sensor_msgs/msg/Image`, 16-bit millimeter `16UC1`)
  - Calibration: `/camera/color/camera_info` (`sensor_msgs/msg/CameraInfo`)
* **Robot Localization & TF:**
  - Coordinate frames: `/tf` and `/tf_static` covering `map` $\rightarrow$ `odom` $\rightarrow$ `base_link` $\rightarrow$ `camera_link`
  - Fallback Pose: `/robot/pose` (`geometry_msgs/msg/PoseWithCovarianceStamped`)
* **Sample Test Recording:**
  - Format: ROS2 bag file (`.mcap` or `.db3`), 3–5 minutes duration with stationary targets.
* **Alert Output Topic:**
  - Topic: `/perception/asset_alerts`
  - Format: Standard JSON string containing `asset_id`, `status` (`IN_PLACE`, `DISPLACED`, `MISSING`), `baseline_position`, `current_position`, `delta_distance_meters`, and `evidence_image_path`.
* **Hardware & Network Architecture:**
  - **Dedicated Unit:** Dedicated Raspberry Pi 5 (16GB LPDDR4X, Broadcom BCM2712 quad-core @ 2.4GHz) solely allocated to perception. Zero CPU/memory burden on the robot navigation controller.
  - **Network Interconnect:** Gigabit Ethernet switch connection with static IP assignment on the robot subnet.
  - **DDS Discovery & Time Sync:** Shared `ROS_DOMAIN_ID` and Chrony/NTP time synchronization (<10ms offset) for reliable `/tf` transform lookups.
