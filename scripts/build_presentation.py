"""
Simple, modern PowerPoint presentation generator for Dhruvaveer's client meeting.
Presents:
1. Completed developments (Detection, Re-ID, Quality Gating, Evidence Logger, 77 Tests)
2. System Design Flow (Visual Diagram of Phase 1 vs Phase 2)
3. Operational Breakdown (Phase 1 Human Walkthrough vs Phase 2 Autonomous Patrol)
4. Verified Live Demo Outputs
5. Hardware assessment & confirmation (Orbbec Gemini 2 XL PoE)
6. What is missing & what is needed (Site data, ROS2 topic specs, milestone sign-off)
7. Next Steps & Roadmap
"""

import os
import shutil
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN
from pptx.enum.shapes import MSO_SHAPE

def create_full_presentation(output_path):
    prs = Presentation()
    prs.slide_width = Inches(13.333)
    prs.slide_height = Inches(7.5)

    # Modern, crisp color palette
    C_BG = RGBColor(248, 250, 252)        # Slate 50
    C_CARD = RGBColor(255, 255, 255)      # Pure White
    C_BORDER = RGBColor(226, 232, 240)    # Slate 200
    C_TEXT_MAIN = RGBColor(15, 23, 42)    # Slate 900
    C_TEXT_MUTED = RGBColor(71, 85, 105)  # Slate 600
    C_PRIMARY = RGBColor(37, 99, 235)     # Blue 600
    C_PRIMARY_LIGHT = RGBColor(239, 246, 255) # Blue 50
    C_GREEN = RGBColor(16, 185, 129)      # Emerald 500
    C_GREEN_LIGHT = RGBColor(236, 253, 245) # Emerald 50
    C_AMBER = RGBColor(217, 119, 6)       # Amber 600
    C_AMBER_LIGHT = RGBColor(254, 243, 199) # Amber 50
    C_PURPLE = RGBColor(124, 58, 237)     # Violet 600
    C_PURPLE_LIGHT = RGBColor(245, 243, 255) # Violet 50

    blank_layout = prs.slide_layouts[6]

    def set_bg(slide, color=C_BG):
        bg = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, Inches(13.333), Inches(7.5))
        bg.fill.solid()
        bg.fill.fore_color.rgb = color
        bg.line.fill.background()
        return bg

    def add_header(slide, title, subtitle=None, category="MILESTONE UPDATE"):
        pill = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(0.9), Inches(0.45), Inches(2.6), Inches(0.32))
        pill.fill.solid()
        pill.fill.fore_color.rgb = C_PRIMARY_LIGHT
        pill.line.color.rgb = C_PRIMARY
        pill.line.width = Pt(1)
        p_pill = pill.text_frame.paragraphs[0]
        p_pill.text = category
        p_pill.font.size = Pt(9.5)
        p_pill.font.bold = True
        p_pill.font.color.rgb = C_PRIMARY
        p_pill.font.name = "Segoe UI"
        p_pill.alignment = PP_ALIGN.CENTER

        tb = slide.shapes.add_textbox(Inches(0.9), Inches(0.85), Inches(11.5), Inches(0.9))
        tf = tb.text_frame
        tf.word_wrap = True
        tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0

        p = tf.paragraphs[0]
        p.text = title
        p.font.size = Pt(23)
        p.font.bold = True
        p.font.color.rgb = C_TEXT_MAIN
        p.font.name = "Segoe UI"

        if subtitle:
            p_sub = tf.add_paragraph()
            p_sub.text = subtitle
            p_sub.font.size = Pt(11.5)
            p_sub.font.color.rgb = C_TEXT_MUTED
            p_sub.font.name = "Segoe UI"
            p_sub.space_before = Pt(3)

    def make_card(slide, left, top, width, height, bg_color=C_CARD, border_color=C_BORDER):
        card = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, left, top, width, height)
        card.fill.solid()
        card.fill.fore_color.rgb = bg_color
        card.line.color.rgb = border_color
        card.line.width = Pt(1.5)
        return card

    slides_with_notes = []

    # =========================================================
    # SLIDE 1: TITLE SLIDE
    # =========================================================
    s1 = prs.slides.add_slide(blank_layout)
    set_bg(s1, RGBColor(241, 245, 249))

    make_card(s1, Inches(1.5), Inches(1.3), Inches(10.333), Inches(4.9), bg_color=C_CARD)

    # Accent top strip on card
    strip = s1.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(1.5), Inches(1.3), Inches(10.333), Inches(0.12))
    strip.fill.solid()
    strip.fill.fore_color.rgb = C_PRIMARY
    strip.line.fill.background()

    # Pill badge
    pill1 = s1.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(2.0), Inches(1.75), Inches(2.6), Inches(0.35))
    pill1.fill.solid()
    pill1.fill.fore_color.rgb = C_GREEN_LIGHT
    pill1.line.color.rgb = C_GREEN
    pill1.line.width = Pt(1)
    p_p1 = pill1.text_frame.paragraphs[0]
    p_p1.text = "MILESTONE 1 : 50% COMPLETE"
    p_p1.font.size = Pt(10)
    p_p1.font.bold = True
    p_p1.font.color.rgb = C_GREEN
    p_p1.alignment = PP_ALIGN.CENTER

    tb_title = s1.shapes.add_textbox(Inches(2.0), Inches(2.25), Inches(9.3), Inches(1.8))
    tf_t = tb_title.text_frame
    tf_t.word_wrap = True

    p = tf_t.paragraphs[0]
    p.text = "SITE Assets Monitor"
    p.font.size = Pt(36)
    p.font.bold = True
    p.font.color.rgb = C_TEXT_MAIN
    p.font.name = "Segoe UI"

    p_sub = tf_t.add_paragraph()
    p_sub.text = "Core AI Perception & Equipment Re-ID System — Progress Update"
    p_sub.font.size = Pt(16)
    p_sub.font.color.rgb = C_PRIMARY
    p_sub.font.name = "Segoe UI"
    p_sub.space_before = Pt(6)

    div = s1.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(2.0), Inches(4.1), Inches(9.3), Inches(0.02))
    div.fill.solid()
    div.fill.fore_color.rgb = C_BORDER
    div.line.fill.background()

    tb_info = s1.shapes.add_textbox(Inches(2.0), Inches(4.3), Inches(9.3), Inches(1.5))
    tf_info = tb_info.text_frame
    tf_info.word_wrap = True

    p_info = tf_info.paragraphs[0]
    p_info.text = "Author / Engineer: Dhruvaveer (AI Perception Specialist)"
    p_info.font.size = Pt(13)
    p_info.font.bold = True
    p_info.font.color.rgb = C_TEXT_MAIN
    p_info.font.name = "Segoe UI"

    p_agenda = tf_info.add_paragraph()
    p_agenda.text = "Agenda: 1. Core Engine Built  •  2. System Design Flow (Phase 1 vs 2)  •  3. Orbbec Camera  •  4. Next Steps"
    p_agenda.font.size = Pt(11.5)
    p_agenda.font.color.rgb = C_TEXT_MUTED
    p_agenda.font.name = "Segoe UI"
    p_agenda.space_before = Pt(4)

    slides_with_notes.append((s1, (
        "Hi team. Today I want to give you a clear, concise update on the SITE Assets Monitor perception system. "
        "We have reached our 50% milestone: the core AI perception engine—including object detection, quality gating, "
        "and vehicle re-identification—is fully built, tested with 77 passing unit tests, and verified end-to-end. "
        "Today I will also walk through our two-phase operational design—showing exactly how the human walkthrough enrollment works "
        "versus ongoing autonomous robot monitoring, followed by our camera validation and next steps."
    )))

    # =========================================================
    # SLIDE 2: CURRENT UPDATES & DEVELOPMENTS (WHAT'S BUILT)
    # =========================================================
    s2 = prs.slides.add_slide(blank_layout)
    set_bg(s2)
    add_header(s2, "Current Developments: Core AI Engine Complete", 
               "Full end-to-end perception pipeline built, tested, and passing 77 automated test suites.",
               "DEVELOPMENT PROGRESS")

    modules = [
        ("1. Image Quality Gating", "Pre-Filter Guard",
         "Automatically evaluates brightness, blurriness, and solar glare. Drops unviable frames early so corrupted images never pollute the database or trigger false positives.",
         C_PRIMARY, C_PRIMARY_LIGHT),
        ("2. Heavy Equipment Detection", "YOLOv8 Detection Engine",
         "Accurately localizes site machinery (trucks, excavators, cranes, loaders) with tight bounding boxes, high confidence scoring, and configurable detection thresholds.",
         C_GREEN, C_GREEN_LIGHT),
        ("3. Equipment Re-ID (Identity)", "OSNet Deep Feature Matcher",
         "Moves beyond simple detection to identify specific units (e.g. 'Truck #04' vs 'Truck #02'). Extracts deep visual feature embeddings and compares them using cosine similarity.",
         C_PURPLE, C_PURPLE_LIGHT),
        ("4. Reference Store & Evidence", "Audit Database & Logger",
         "Stores enrolled equipment signatures, clusters unknown vehicles, and automatically captures timestamped crop photos + JSON metadata logs for complete accountability.",
         C_AMBER, C_AMBER_LIGHT)
    ]

    card_w = Inches(2.7)
    card_gap = Inches(0.24)
    start_x = Inches(0.9)

    for i, (m_tag, m_title, m_desc, col, bg_light) in enumerate(modules):
        x = start_x + i * (card_w + card_gap)
        make_card(s2, x, Inches(1.9), card_w, Inches(4.3))

        tag_rect = s2.shapes.add_shape(MSO_SHAPE.RECTANGLE, x, Inches(1.9), card_w, Inches(0.08))
        tag_rect.fill.solid()
        tag_rect.fill.fore_color.rgb = col
        tag_rect.line.fill.background()

        tb = s2.shapes.add_textbox(x + Inches(0.2), Inches(2.1), card_w - Inches(0.4), Inches(3.9))
        tf = tb.text_frame
        tf.word_wrap = True

        p1 = tf.paragraphs[0]
        p1.text = m_tag
        p1.font.size = Pt(11)
        p1.font.bold = True
        p1.font.color.rgb = col
        p1.font.name = "Segoe UI"

        p2 = tf.add_paragraph()
        p2.text = m_title
        p2.font.size = Pt(14)
        p2.font.bold = True
        p2.font.color.rgb = C_TEXT_MAIN
        p2.font.name = "Segoe UI"
        p2.space_before = Pt(4)

        p3 = tf.add_paragraph()
        p3.text = m_desc
        p3.font.size = Pt(10.5)
        p3.font.color.rgb = C_TEXT_MUTED
        p3.font.name = "Segoe UI"
        p3.space_before = Pt(10)

    banner = make_card(s2, Inches(0.9), Inches(6.35), Inches(11.533), Inches(0.65), bg_color=C_GREEN_LIGHT, border_color=C_GREEN)
    tb_b = s2.shapes.add_textbox(Inches(1.1), Inches(6.42), Inches(11.1), Inches(0.5))
    tf_b = tb_b.text_frame
    p_b = tf_b.paragraphs[0]
    p_b.text = "✓ Quality & Stability Verified: 77 Unit Tests Passing (100% test pass rate across Quality, Detection, Re-ID, and Reference Store)"
    p_b.font.size = Pt(11.5)
    p_b.font.bold = True
    p_b.font.color.rgb = C_GREEN
    p_b.font.name = "Segoe UI"

    slides_with_notes.append((s2, (
        "Here is what is completely built and functional right now: First, an image quality gating filter that rejects blurry or glare-blinded images. "
        "Second, a custom YOLOv8 detector for construction machinery. "
        "Third, our Re-ID engine using OSNet—this allows the system to recognize specific assets, like distinguishing Truck #04 from Truck #02. "
        "Fourth, a persistent reference store that logs cropped photos, timestamps, and metadata. "
        "Most importantly, the entire codebase has 77 automated unit tests, and all 77 are passing cleanly."
    )))

    # =========================================================
    # SLIDE 3: SYSTEM DESIGN FLOW (VISUAL DIAGRAM)
    # =========================================================
    s3 = prs.slides.add_slide(blank_layout)
    set_bg(s3)
    add_header(s3, "System Design Flow: Operational Architecture",
               "Visual end-to-end pipeline: Phase 1 Enrollment creates Ground Truth; Phase 2 Autonomous Patrol verifies it.",
               "SYSTEM ARCHITECTURE")

    flow_img_path = os.path.abspath("evidence/system_design_flow.png")
    if not os.path.exists(flow_img_path):
        flow_img_path = os.path.abspath("../system_design_flow.png")
    
    make_card(s3, Inches(0.9), Inches(1.85), Inches(11.533), Inches(5.2))
    
    if os.path.exists(flow_img_path):
        s3.shapes.add_picture(flow_img_path, Inches(1.0), Inches(1.95), width=Inches(11.333))

    slides_with_notes.append((s3, (
        "This diagram illustrates the full system operational workflow. "
        "At the top is Phase 1: Human Walkthrough, which is a one-time onboarding setup where a human guides the robot to capture and lock the site's ground truth database. "
        "At the bottom is Phase 2: Autonomous Patrol, where the robot drives ongoing patrol routes, detects equipment in real time, "
        "matches visual fingerprints against the locked database, and compares current real-world positions with stored positions to trigger instant movement alerts."
    )))

    # =========================================================
    # SLIDE 4: PHASE 1 VS PHASE 2 COMPARATIVE BREAKDOWN
    # =========================================================
    s4 = prs.slides.add_slide(blank_layout)
    set_bg(s4)
    add_header(s4, "Operational Phases: Setup vs. Autonomous Patrol",
               "Clear separation between one-time baseline enrollment and continuous automated site monitoring.",
               "OPERATIONAL BREAKDOWN")

    # Left: Phase 1 Card
    make_card(s4, Inches(0.9), Inches(1.85), Inches(5.6), Inches(5.15))
    strip_p1 = s4.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0.9), Inches(1.85), Inches(5.6), Inches(0.1))
    strip_p1.fill.solid()
    strip_p1.fill.fore_color.rgb = C_PRIMARY
    strip_p1.line.fill.background()

    tb_p1 = s4.shapes.add_textbox(Inches(1.2), Inches(2.1), Inches(5.0), Inches(4.7))
    tf_p1 = tb_p1.text_frame
    tf_p1.word_wrap = True

    p_p1_t = tf_p1.paragraphs[0]
    p_p1_t.text = "PHASE 1: Human Walkthrough"
    p_p1_t.font.size = Pt(16)
    p_p1_t.font.bold = True
    p_p1_t.font.color.rgb = C_PRIMARY
    p_p1_t.font.name = "Segoe UI"

    p_p1_sub = tf_p1.add_paragraph()
    p_p1_sub.text = "One-Time Setup & Baseline Enrollment"
    p_p1_sub.font.size = Pt(11.5)
    p_p1_sub.font.color.rgb = C_TEXT_MUTED
    p_p1_sub.font.name = "Segoe UI"
    p_p1_sub.space_before = Pt(2)

    p1_details = [
        ("When It Happens", "Day 1 site deployment, or when new contractor machinery arrives."),
        ("Human Operator Role", "Guides the robot or carries camera past all parked machinery."),
        ("Multi-Modal Capture", "Orbbec camera records RGB image while robot SLAM/GPS logs precise (X,Y) coordinates."),
        ("Fingerprint Extraction", "YOLOv8 detects asset; OSNet extracts invariant 512D Re-ID embedding."),
        ("Database Lock", "Stored as Ground Truth: [Asset ID, Class, Stored Pose, Embedding, Crop Photo]. No false alerts possible.")
    ]
    for tag, desc in p1_details:
        p = tf_p1.add_paragraph()
        p.text = f"• {tag}: "
        p.font.size = Pt(10.5)
        p.font.bold = True
        p.font.color.rgb = C_TEXT_MAIN
        p.font.name = "Segoe UI"
        p.space_before = Pt(8)

        run = p.add_run()
        run.text = desc
        run.font.bold = False
        run.font.color.rgb = C_TEXT_MUTED

    # Right: Phase 2 Card
    make_card(s4, Inches(6.8), Inches(1.85), Inches(5.633), Inches(5.15))
    strip_p2 = s4.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(6.8), Inches(1.85), Inches(5.633), Inches(0.1))
    strip_p2.fill.solid()
    strip_p2.fill.fore_color.rgb = C_GREEN
    strip_p2.line.fill.background()

    tb_p2 = s4.shapes.add_textbox(Inches(7.1), Inches(2.1), Inches(5.0), Inches(4.7))
    tf_p2 = tb_p2.text_frame
    tf_p2.word_wrap = True

    p_p2_t = tf_p2.paragraphs[0]
    p_p2_t.text = "PHASE 2: Autonomous Patrol"
    p_p2_t.font.size = Pt(16)
    p_p2_t.font.bold = True
    p_p2_t.font.color.rgb = C_GREEN
    p_p2_t.font.name = "Segoe UI"

    p_p2_sub = tf_p2.add_paragraph()
    p_p2_sub.text = "Continuous Ongoing Monitoring & Verification"
    p_p2_sub.font.size = Pt(11.5)
    p_p2_sub.font.color.rgb = C_TEXT_MUTED
    p_p2_sub.font.name = "Segoe UI"
    p_p2_sub.space_before = Pt(2)

    p2_details = [
        ("When It Happens", "Continuous daily/hourly autonomous patrol missions without human intervention."),
        ("Real-Time Re-ID Matching", "Robot scans equipment; compares live 512D embedding against the locked Phase 1 database."),
        ("Spatial Verification", "Computes live equipment coordinates using depth stream + robot pose. Compares against registered location."),
        ("Outcome A : In Place", "Distance Delta ≤ 3.0m → 'ASSET IN PLACE'. Logged cleanly with timestamp."),
        ("Outcome B : Relocation Alert", "Distance Delta > 3.0m → 'ALERT: ASSET MOVED'. Dispatches old vs new coordinates + crop evidence to dashboard.")
    ]
    for tag, desc in p2_details:
        p = tf_p2.add_paragraph()
        p.text = f"• {tag}: "
        p.font.size = Pt(10.5)
        p.font.bold = True
        p.font.color.rgb = C_TEXT_MAIN
        p.font.name = "Segoe UI"
        p.space_before = Pt(8)

        run = p.add_run()
        run.text = desc
        run.font.bold = False
        run.font.color.rgb = C_TEXT_MUTED

    slides_with_notes.append((s4, (
        "To make the operational design crystal clear: In Phase 1, an operator walks the robot through the site just once. "
        "The system spots each excavator, crane, or truck, records its GPS coordinates, generates a 512-dimensional fingerprint, "
        "and locks this into the reference database as Ground Truth. "
        "In Phase 2, the robot patrols autonomously. Every time it spots equipment, it identifies who it is using Re-ID, "
        "calculates where the machine is, and compares that to the Phase 1 baseline. "
        "If it is within 3 meters, it logs 'In Place'. If it has moved past 3 meters, it immediately raises an alert with the new coordinates and evidence photos."
    )))

    # =========================================================
    # SLIDE 5: VISUAL PROOF & DEMO PIPELINE
    # =========================================================
    s5 = prs.slides.add_slide(blank_layout)
    set_bg(s5)
    add_header(s5, "Pipeline Architecture & Live Verification",
               "Visual proof of equipment identification, audit cropping, and end-to-end execution.",
               "VERIFIED DEMO")

    demo_img_path = os.path.abspath("evidence/demo_output.jpg")
    crop_img_path = os.path.abspath("evidence/2026-09-06/crop_20260906_162218_602_Truck_DEMO.jpg")

    make_card(s5, Inches(0.9), Inches(1.85), Inches(5.6), Inches(5.15))
    tb_flow = s5.shapes.add_textbox(Inches(1.1), Inches(2.05), Inches(5.2), Inches(4.7))
    tf_flow = tb_flow.text_frame
    tf_flow.word_wrap = True

    p_f1 = tf_flow.paragraphs[0]
    p_f1.text = "End-to-End Processing Flow"
    p_f1.font.size = Pt(15)
    p_f1.font.bold = True
    p_f1.font.color.rgb = C_PRIMARY
    p_f1.font.name = "Segoe UI"

    flow_steps = [
        ("Raw Video / Camera Frame", "Ingested via ROS2 topic (e.g. /camera/color/image_raw)."),
        ("Quality Guard", "Evaluates sharpness, exposure, glare. Drops bad frames in <3ms."),
        ("YOLOv8 Detection", "Generates bbox, class label ('Truck'), and detection confidence (99%)."),
        ("OSNet Feature Extractor", "Extracts 512-dim visual embedding vector from vehicle crop."),
        ("Reference Matcher", "Computes cosine distance against known gallery: matches known asset or flags 'UNKNOWN'."),
        ("Evidence & Audit Logger", "Saves full image, cropped asset, timestamp, and JSON audit log.")
    ]

    for title, desc in flow_steps:
        p = tf_flow.add_paragraph()
        p.text = f"• {title}: "
        p.font.size = Pt(10.5)
        p.font.bold = True
        p.font.color.rgb = C_TEXT_MAIN
        p.font.name = "Segoe UI"
        p.space_before = Pt(6)

        run = p.add_run()
        run.text = desc
        run.font.bold = False
        run.font.color.rgb = C_TEXT_MUTED

    make_card(s5, Inches(6.8), Inches(1.85), Inches(5.633), Inches(5.15))
    tb_img_t = s5.shapes.add_textbox(Inches(7.0), Inches(2.0), Inches(5.2), Inches(0.35))
    p_it = tb_img_t.text_frame.paragraphs[0]
    p_it.text = "Actual Demo Output: Detection & Cropped Evidence"
    p_it.font.size = Pt(13)
    p_it.font.bold = True
    p_it.font.color.rgb = C_GREEN
    p_it.font.name = "Segoe UI"

    if os.path.exists(demo_img_path):
        s5.shapes.add_picture(demo_img_path, Inches(7.0), Inches(2.4), width=Inches(3.3))

    if os.path.exists(crop_img_path):
        s5.shapes.add_picture(crop_img_path, Inches(10.5), Inches(2.4), width=Inches(1.75))

    tb_live_desc = s5.shapes.add_textbox(Inches(7.0), Inches(5.0), Inches(5.2), Inches(1.8))
    tf_ld = tb_live_desc.text_frame
    tf_ld.word_wrap = True

    p_ld1 = tf_ld.paragraphs[0]
    p_ld1.text = "Demo Execution (`scripts/demo_reid.py`):"
    p_ld1.font.size = Pt(11)
    p_ld1.font.bold = True
    p_ld1.font.color.rgb = C_TEXT_MAIN
    p_ld1.font.name = "Segoe UI"

    demo_bullets = [
        "Tested with single and multi-vehicle frames.",
        "Accurate bounding boxes generated at 99% & 93% confidence.",
        "Zero memory leaks, self-contained reference database.",
        "Ready to accept live camera streaming."
    ]
    for b in demo_bullets:
        p = tf_ld.add_paragraph()
        p.text = "✔ " + b
        p.font.size = Pt(10)
        p.font.color.rgb = C_TEXT_MUTED
        p.font.name = "Segoe UI"
        p.space_before = Pt(3)

    slides_with_notes.append((s5, (
        "Here is the visual proof from our test suite. On the left is the exact step-by-step pipeline from raw frame intake to audit logging. "
        "On the right is the actual output from our test run: our YOLOv8 model detects the vehicle with 99% confidence, "
        "and our Re-ID pipeline crops the vehicle and compares its visual signature against the site database. "
        "The system has been verified using scripts/demo_reid.py and is ready for live stream integration."
    )))

    # =========================================================
    # SLIDE 6: HARDWARE CONFIRMATION (ORBBEC GEMINI 2 XL POE)
    # =========================================================
    s6 = prs.slides.add_slide(blank_layout)
    set_bg(s6)
    add_header(s6, "Hardware Assessment: Orbbec Gemini 2 XL PoE",
               "Technical validation for sunny outdoor environments & robot integration.",
               "HARDWARE VALIDATION")

    make_card(s6, Inches(0.9), Inches(1.85), Inches(5.6), Inches(5.15))
    tb_hw1 = s6.shapes.add_textbox(Inches(1.2), Inches(2.05), Inches(5.0), Inches(4.7))
    tf_hw1 = tb_hw1.text_frame
    tf_hw1.word_wrap = True

    p_h1 = tf_hw1.paragraphs[0]
    p_h1.text = "Why It's a Strong Fit for the Robot"
    p_h1.font.size = Pt(15)
    p_h1.font.bold = True
    p_h1.font.color.rgb = C_PRIMARY
    p_h1.font.name = "Segoe UI"

    strengths = [
        ("Outdoor Sunlight Resilience", "Unlike standard structured-light cameras that get blinded by the sun, the Gemini 2 XL uses active stereo depth, making it stable under outdoor solar IR."),
        ("PoE (Power over Ethernet)", "Single ruggedized Ethernet cable supplies both power and data. Prevents loose USB connectors or ribbon-cable failures on a vibrating robot chassis."),
        ("Extended Range", "Offers reliable depth from 0.2m up to 5m+, perfect for large construction equipment patrol."),
        ("Official ROS2 SDK", "Official Orbbec ROS2 driver publishes standard sensor_msgs/Image topics out-of-the-box.")
    ]
    for title, desc in strengths:
        p = tf_hw1.add_paragraph()
        p.text = f"• {title}: "
        p.font.size = Pt(10.5)
        p.font.bold = True
        p.font.color.rgb = C_TEXT_MAIN
        p.font.name = "Segoe UI"
        p.space_before = Pt(8)

        run = p.add_run()
        run.text = desc
        run.font.bold = False
        run.font.color.rgb = C_TEXT_MUTED

    make_card(s6, Inches(6.8), Inches(1.85), Inches(5.633), Inches(5.15))
    tb_hw2 = s6.shapes.add_textbox(Inches(7.1), Inches(2.05), Inches(5.0), Inches(4.7))
    tf_hw2 = tb_hw2.text_frame
    tf_hw2.word_wrap = True

    p_h2 = tf_hw2.paragraphs[0]
    p_h2.text = "Perception Integration Compatibility"
    p_h2.font.size = Pt(15)
    p_h2.font.bold = True
    p_h2.font.color.rgb = C_GREEN
    p_h2.font.name = "Segoe UI"

    compat = [
        ("100% Pipeline Compatible", "Our YOLOv8 + OSNet pipeline takes standard RGB frames. We subscribe directly to `/camera/color/image_raw` with zero pipeline rework."),
        ("Depth-Enhanced Spatial Bounding", "The aligned depth stream will allow us to filter out background objects and measure exact real-world distance to detected machinery."),
        ("Network Topology", "PoE allows placing the camera anywhere on the chassis while routing cleanly into the onboard compute switch."),
        ("Decision Item", "Approved from AI perception standpoint. Ready to integrate once hardware is ordered / delivered.")
    ]
    for title, desc in compat:
        p = tf_hw2.add_paragraph()
        p.text = f"• {title}: "
        p.font.size = Pt(10.5)
        p.font.bold = True
        p.font.color.rgb = C_TEXT_MAIN
        p.font.name = "Segoe UI"
        p.space_before = Pt(8)

        run = p.add_run()
        run.text = desc
        run.font.bold = False
        run.font.color.rgb = C_TEXT_MUTED

    slides_with_notes.append((s6, (
        "Regarding the camera proposed by the team lead: I reviewed the Orbbec Gemini 2 XL PoE datasheet thoroughly. "
        "It is an excellent choice for three reasons: First, it handles harsh outdoor sunlight much better than indoor depth cameras. "
        "Second, PoE eliminates loose USB cable disconnects on a moving robot. "
        "Third, it is 100% compatible with our perception software—we subscribe directly to its ROS2 RGB image stream, "
        "and we can use its depth channel to compute real-world distance to equipment. "
        "From the AI side, this gets a clear green light."
    )))

    # =========================================================
    # SLIDE 7: WHAT IS MISSING & WHAT I NEED (THE ASKS)
    # =========================================================
    s7 = prs.slides.add_slide(blank_layout)
    set_bg(s7)
    add_header(s7, "Current Needs & Confirmations (The Asks)",
               "Key inputs required from the robotics team to proceed smoothly into Phase 2.",
               "ACTION ITEMS")

    items_need = [
        ("1. Real Site Photos / Rosbag", "Data for Calibration",
         "A small sample of real site footage (or 10-15 phone photos of your actual equipment on site). This allows us to tune cosine similarity thresholds and calibrate detection for actual dust, shadows, and lighting.",
         C_AMBER, C_AMBER_LIGHT),
        ("2. ROS2 Topic Specifications", "Interface Alignment",
         "Confirm your robot's ROS2 naming conventions (e.g. `/camera/color/image_raw`, `/patrol/robot_pose`) and preferred alert topic schema so our ROS2 wrapper publishes exactly what navigation expects.",
         C_PRIMARY, C_PRIMARY_LIGHT),
        ("3. Milestone 1 Sign-Off", "Progress Confirmation",
         "Formal review and sign-off for the completed Core Perception Engine (detection, Re-ID, reference store, and 77 passing unit tests) to release the Milestone 1 deliverable.",
         C_GREEN, C_GREEN_LIGHT)
    ]

    card_w7 = Inches(3.6)
    card_gap7 = Inches(0.36)
    start_x7 = Inches(0.9)

    for i, (tag, title, desc, col, bg_l) in enumerate(items_need):
        x = start_x7 + i * (card_w7 + card_gap7)
        make_card(s7, x, Inches(1.85), card_w7, Inches(5.15))

        tb = s7.shapes.add_textbox(x + Inches(0.25), Inches(2.1), card_w7 - Inches(0.5), Inches(4.5))
        tf = tb.text_frame
        tf.word_wrap = True

        p1 = tf.paragraphs[0]
        p1.text = tag
        p1.font.size = Pt(12)
        p1.font.bold = True
        p1.font.color.rgb = col
        p1.font.name = "Segoe UI"

        p2 = tf.add_paragraph()
        p2.text = title
        p2.font.size = Pt(16)
        p2.font.bold = True
        p2.font.color.rgb = C_TEXT_MAIN
        p2.font.name = "Segoe UI"
        p2.space_before = Pt(6)

        p3 = tf.add_paragraph()
        p3.text = desc
        p3.font.size = Pt(11)
        p3.font.color.rgb = C_TEXT_MUTED
        p3.font.name = "Segoe UI"
        p3.space_before = Pt(14)

        p4 = tf.add_paragraph()
        p4.text = "Status: Pending Team Input"
        p4.font.size = Pt(10)
        p4.font.bold = True
        p4.font.color.rgb = col
        p4.font.name = "Segoe UI"
        p4.space_before = Pt(20)

    slides_with_notes.append((s7, (
        "To keep our momentum going, here are the 3 key things I need from the team: "
        "First, sample site photos or a short rosbag recording so I can calibrate our Re-ID similarity thresholds against actual site lighting and dust. "
        "Second, confirmation of the ROS2 topic names and alert message formats your navigation system expects. "
        "Third, sign-off on Milestone 1, which confirms the core perception engine meets your expectations."
    )))

    # =========================================================
    # SLIDE 8: NEXT STEPS & ROADMAP
    # =========================================================
    s8 = prs.slides.add_slide(blank_layout)
    set_bg(s8)
    add_header(s8, "Next Steps & Phase 2 Roadmap",
               "Target deliverables for the upcoming development cycle.",
               "ROADMAP")

    make_card(s8, Inches(0.9), Inches(1.85), Inches(5.6), Inches(5.15))
    tb_nx1 = s8.shapes.add_textbox(Inches(1.2), Inches(2.05), Inches(5.0), Inches(4.7))
    tf_nx1 = tb_nx1.text_frame
    tf_nx1.word_wrap = True

    p_n1 = tf_nx1.paragraphs[0]
    p_n1.text = "Upcoming Engineering Tasks (Week 2)"
    p_n1.font.size = Pt(15)
    p_n1.font.bold = True
    p_n1.font.color.rgb = C_PRIMARY
    p_n1.font.name = "Segoe UI"

    tasks = [
        ("ROS2 Node Wrapper", "Package the perception engine into `site_asset_monitor_node` with standard ROS2 publishers and subscribers."),
        ("Movement & Dwell Tracking", "Integrate temporal tracking to identify whether equipment is moving or stationary across patrol passes."),
        ("ONNX Runtime Optimization", "Export OSNet and YOLO to ONNX with INT8/FP16 quantization for low-latency inference on the robot compute."),
        ("Live Orbbec Stream Testing", "Validate image intake directly with the Orbbec ROS2 driver as soon as hardware is available.")
    ]
    for title, desc in tasks:
        p = tf_nx1.add_paragraph()
        p.text = f"• {title}: "
        p.font.size = Pt(10.5)
        p.font.bold = True
        p.font.color.rgb = C_TEXT_MAIN
        p.font.name = "Segoe UI"
        p.space_before = Pt(8)

        run = p.add_run()
        run.text = desc
        run.font.bold = False
        run.font.color.rgb = C_TEXT_MUTED

    make_card(s8, Inches(6.8), Inches(1.85), Inches(5.633), Inches(5.15))
    tb_nx2 = s8.shapes.add_textbox(Inches(7.1), Inches(2.05), Inches(5.0), Inches(4.7))
    tf_nx2 = tb_nx2.text_frame
    tf_nx2.word_wrap = True

    p_n2 = tf_nx2.paragraphs[0]
    p_n2.text = "Summary & Open Discussion"
    p_n2.font.size = Pt(15)
    p_n2.font.bold = True
    p_n2.font.color.rgb = C_GREEN
    p_n2.font.name = "Segoe UI"

    sum_points = [
        "Milestone 1 is ready, verified, and backed by 77 automated tests.",
        "System operation flow (Phase 1 Enrollment vs Phase 2 Patrol) is clearly defined.",
        "Camera choice (Orbbec Gemini 2 XL PoE) is validated and ready for integration.",
        "Clear path forward for ROS2 packaging and robot deployment.",
        "Questions & Feedback: Let's discuss data availability, timeline, and next milestones."
    ]
    for pt in sum_points:
        p = tf_nx2.add_paragraph()
        p.text = "✔ " + pt
        p.font.size = Pt(11)
        p.font.color.rgb = C_TEXT_MAIN
        p.font.name = "Segoe UI"
        p.space_before = Pt(12)

    slides_with_notes.append((s8, (
        "To summarize: Our next immediate step is wrapping the perception engine into a ROS2 node, "
        "adding movement and dwell time tracking, and optimizing our models for low latency. "
        "Everything is on schedule, the foundation is rock solid, and I'm ready to answer any questions or discuss your feedback. Thank you!"
    )))

    for slide, note in slides_with_notes:
        slide.notes_slide.notes_text_frame.text = note

    prs.save(output_path)
    print(f"Presentation saved successfully to: {output_path}")

if __name__ == "__main__":
    out_dir = r"c:\Users\GANGARI DHRUVAVEER\Downloads\prozect"
    
    # Save to both standard names so whichever file the user opens is updated
    f1 = os.path.join(out_dir, "Site_Assets_Monitor_Presentation.pptx")
    f2 = os.path.join(out_dir, "Site_Assets_Monitor_Milestone_Update.pptx")
    
    create_full_presentation(f1)
    shutil.copy(f1, f2)
    
    # Also sync into SITE_Assets_Monitor subdirectory
    sub_dir = os.path.join(out_dir, "SITE_Assets_Monitor")
    shutil.copy(f1, os.path.join(sub_dir, "Site_Assets_Monitor_Presentation.pptx"))
    shutil.copy(f1, os.path.join(sub_dir, "Site_Assets_Monitor_Milestone_Update.pptx"))
    print("All PPTX files updated successfully!")
