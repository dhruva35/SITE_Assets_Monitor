"""
Generate SITE Assets Monitor Phase 1 & Phase 2 Presentation Deck
Produces: presentation/SITE_Assets_Monitor_Phase1_Phase2_Presentation.pptx
Theme: Modern Dark Mode with Black/White/Yellow (#FFD700) branding
Includes User's 5 Verified Detection Keyframe Snapshots
"""

import os
from pathlib import Path
import pptx
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN
from pptx.enum.shapes import MSO_SHAPE

PROJECT_ROOT = Path(__file__).resolve().parent.parent
OUTPUT_DIR = PROJECT_ROOT / "presentation"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
PPTX_PATH = OUTPUT_DIR / "SITE_Assets_Monitor_Phase1_Phase2_Presentation.pptx"
IMG_DIR = OUTPUT_DIR / "images"

# ── Color Palette (Black, White, Yellow #FFD700) ──────────────────────────
C_BG          = RGBColor(15, 17, 23)      # Deep Black/Charcoal Background
C_CARD_BG     = RGBColor(26, 29, 38)      # Card / Panel Background
C_CARD_BORDER = RGBColor(45, 50, 65)      # Card subtle border
C_ACCENT      = RGBColor(255, 215, 0)     # Gold-Yellow Accent (#FFD700)
C_ACCENT_MUT  = RGBColor(190, 160, 20)     # Muted Gold
C_TEXT_WHITE  = RGBColor(245, 245, 250)    # Primary Crisp White
C_TEXT_MUTED  = RGBColor(170, 175, 190)    # Secondary Slate/Gray Text
C_GREEN       = RGBColor(46, 213, 115)    # Success / Confirmed Green
C_BLUE        = RGBColor(84, 160, 255)    # Informational Blue

FONT_TITLE = "Segoe UI"
FONT_BODY  = "Segoe UI"


def create_deck():
    prs = pptx.Presentation()
    prs.slide_width = Inches(13.333)
    prs.slide_height = Inches(7.5)
    blank_layout = prs.slide_layouts[6]

    def set_slide_background(slide):
        bg = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, prs.slide_width, prs.slide_height)
        bg.fill.solid()
        bg.fill.fore_color.rgb = C_BG
        bg.line.color.rgb = C_BG
        return bg

    def add_header(slide, title_text, category_text="SITE ASSETS MONITOR"):
        cat_box = slide.shapes.add_textbox(Inches(0.8), Inches(0.42), Inches(11.7), Inches(0.32))
        tf_cat = cat_box.text_frame
        tf_cat.word_wrap = True
        tf_cat.margin_left = tf_cat.margin_top = tf_cat.margin_right = tf_cat.margin_bottom = 0
        p_cat = tf_cat.paragraphs[0]
        p_cat.text = category_text.upper()
        p_cat.font.name = FONT_TITLE
        p_cat.font.size = Pt(11)
        p_cat.font.bold = True
        p_cat.font.color.rgb = C_ACCENT

        title_box = slide.shapes.add_textbox(Inches(0.8), Inches(0.72), Inches(11.7), Inches(0.65))
        tf = title_box.text_frame
        tf.word_wrap = True
        tf.margin_left = tf.margin_top = tf.margin_right = tf.margin_bottom = 0
        p = tf.paragraphs[0]
        p.text = title_text
        p.font.name = FONT_TITLE
        p.font.size = Pt(23)
        p.font.bold = True
        p.font.color.rgb = C_TEXT_WHITE

        bar = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0.8), Inches(1.42), Inches(1.5), Inches(0.04))
        bar.fill.solid()
        bar.fill.fore_color.rgb = C_ACCENT
        bar.line.color.rgb = C_ACCENT

    def add_card(slide, left, top, width, height, title=None, border_color=C_CARD_BORDER, bg_color=C_CARD_BG):
        card = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, left, top, width, height)
        card.fill.solid()
        card.fill.fore_color.rgb = bg_color
        card.line.color.rgb = border_color
        card.line.width = Pt(1.2)

        if title:
            tbox = slide.shapes.add_textbox(left + Inches(0.2), top + Inches(0.18), width - Inches(0.4), Inches(0.38))
            tf = tbox.text_frame
            tf.word_wrap = True
            tf.margin_left = tf.margin_top = tf.margin_right = tf.margin_bottom = 0
            p = tf.paragraphs[0]
            p.text = title
            p.font.name = FONT_TITLE
            p.font.size = Pt(13)
            p.font.bold = True
            p.font.color.rgb = C_ACCENT
        return card

    # =========================================================================
    # SLIDE 1: Title Slide
    # =========================================================================
    slide1 = prs.slides.add_slide(blank_layout)
    set_slide_background(slide1)

    top_bar = slide1.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, prs.slide_width, Inches(0.12))
    top_bar.fill.solid()
    top_bar.fill.fore_color.rgb = C_ACCENT
    top_bar.line.color.rgb = C_ACCENT

    badge = slide1.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(1.0), Inches(1.8), Inches(3.2), Inches(0.45))
    badge.fill.solid()
    badge.fill.fore_color.rgb = RGBColor(35, 30, 15)
    badge.line.color.rgb = C_ACCENT
    badge.line.width = Pt(1.5)
    tf_b = badge.text_frame
    p_b = tf_b.paragraphs[0]
    p_b.text = "AUTONOMOUS SECURITY & PERCEPTION"
    p_b.font.name = FONT_TITLE
    p_b.font.size = Pt(10)
    p_b.font.bold = True
    p_b.font.color.rgb = C_ACCENT
    p_b.alignment = PP_ALIGN.CENTER

    t_box = slide1.shapes.add_textbox(Inches(1.0), Inches(2.5), Inches(11.3), Inches(1.5))
    tf1 = t_box.text_frame
    tf1.word_wrap = True
    p1 = tf1.paragraphs[0]
    p1.text = "SITE Assets Monitor"
    p1.font.name = FONT_TITLE
    p1.font.size = Pt(44)
    p1.font.bold = True
    p1.font.color.rgb = C_TEXT_WHITE

    p2 = tf1.add_paragraph()
    p2.text = "Phase 1 & Phase 2 Technical Milestone Presentation"
    p2.font.name = FONT_TITLE
    p2.font.size = Pt(22)
    p2.font.bold = True
    p2.font.color.rgb = C_ACCENT

    desc_box = slide1.shapes.add_textbox(Inches(1.0), Inches(4.3), Inches(11.0), Inches(1.2))
    tf_desc = desc_box.text_frame
    tf_desc.word_wrap = True
    p3 = tf_desc.paragraphs[0]
    p3.text = "Environment-Agnostic HITL Asset Enrollment (Phase 1) & Autonomous High-Recall Multi-Asset Re-ID Patrol (Phase 2) on a Mobile Robot Platform (UGV)."
    p3.font.name = FONT_BODY
    p3.font.size = Pt(15)
    p3.font.color.rgb = C_TEXT_MUTED

    meta_w = Inches(3.5)
    meta_h = Inches(1.0)
    meta_top = Inches(5.8)

    c1 = add_card(slide1, Inches(1.0), meta_top, meta_w, meta_h)
    tb1 = slide1.shapes.add_textbox(Inches(1.15), meta_top + Inches(0.18), meta_w - Inches(0.3), Inches(0.7))
    tf_c1 = tb1.text_frame
    p_c1_1 = tf_c1.paragraphs[0]
    p_c1_1.text = "PHASE 1 DELIVERABLE"
    p_c1_1.font.size = Pt(9.5)
    p_c1_1.font.bold = True
    p_c1_1.font.color.rgb = C_ACCENT
    p_c1_2 = tf_c1.add_paragraph()
    p_c1_2.text = "HITL Operator Enrollment UI (v2)\nZero Pre-Training Day-1 Setup"
    p_c1_2.font.size = Pt(11)
    p_c1_2.font.color.rgb = C_TEXT_WHITE

    c2 = add_card(slide1, Inches(4.85), meta_top, meta_w, meta_h)
    tb2 = slide1.shapes.add_textbox(Inches(5.0), meta_top + Inches(0.18), meta_w - Inches(0.3), Inches(0.7))
    tf_c2 = tb2.text_frame
    p_c2_1 = tf_c2.paragraphs[0]
    p_c2_1.text = "PHASE 2 DELIVERABLE"
    p_c2_1.font.size = Pt(9.5)
    p_c2_1.font.bold = True
    p_c2_1.font.color.rgb = C_ACCENT
    p_c2_2 = tf_c2.add_paragraph()
    p_c2_2.text = "Autonomous Re-ID Patrol Verification\n100% Asset Recall (24/24 Containers)"
    p_c2_2.font.size = Pt(11)
    p_c2_2.font.color.rgb = C_TEXT_WHITE

    c3 = add_card(slide1, Inches(8.7), meta_top, meta_w, meta_h)
    tb3 = slide1.shapes.add_textbox(Inches(8.85), meta_top + Inches(0.18), meta_w - Inches(0.3), Inches(0.7))
    tf_c3 = tb3.text_frame
    p_c3_1 = tf_c3.paragraphs[0]
    p_c3_1.text = "TEST SUITE STATUS"
    p_c3_1.font.size = Pt(9.5)
    p_c3_1.font.bold = True
    p_c3_1.font.color.rgb = C_GREEN
    p_c3_2 = tf_c3.add_paragraph()
    p_c3_2.text = "119 / 119 Unit Tests Passing\nClean Architecture & CI Verified"
    p_c3_2.font.size = Pt(11)
    p_c3_2.font.color.rgb = C_TEXT_WHITE

    # =========================================================================
    # SLIDE 2: Executive Summary & The Problem
    # =========================================================================
    slide2 = prs.slides.add_slide(blank_layout)
    set_slide_background(slide2)
    add_header(slide2, "Executive Summary: The Industrial Challenge & Our Solution", "CONTEXT & OBJECTIVES")

    add_card(slide2, Inches(0.8), Inches(1.8), Inches(5.6), Inches(5.0), "THE INDUSTRIAL PROBLEM")
    t_chal = slide2.shapes.add_textbox(Inches(1.05), Inches(2.4), Inches(5.1), Inches(4.2))
    tf_chal = t_chal.text_frame
    tf_chal.word_wrap = True

    items_chal = [
        ("No Pre-Trained Models on Day-1", "Every construction, logistics, or industrial yard has unique asset types, customized containers, and lighting conditions. Off-the-shelf detectors fail without extensive retraining."),
        ("Manual Inventory is Slow & Flawed", "Human audit walkthroughs take hours, introduce logging errors, and fail to track unexpected asset displacements or theft in real time."),
        ("Harsh Mobile Robot Dynamics", "UGV/AGV motion introduces camera vibration, heavy motion blur, steep perspective angles, and partial occlusions that confuse typical vision models.")
    ]
    for i, (head, body) in enumerate(items_chal):
        p_h = tf_chal.paragraphs[0] if i == 0 else tf_chal.add_paragraph()
        p_h.text = f"•  {head}"
        p_h.font.size = Pt(13)
        p_h.font.bold = True
        p_h.font.color.rgb = RGBColor(255, 100, 100)
        p_b = tf_chal.add_paragraph()
        p_b.text = f"   {body}\n"
        p_b.font.size = Pt(11)
        p_b.font.color.rgb = C_TEXT_MUTED

    add_card(slide2, Inches(6.8), Inches(1.8), Inches(5.7), Inches(5.0), "OUR TWO-PHASE SOLUTION")
    t_sol = slide2.shapes.add_textbox(Inches(7.05), Inches(2.4), Inches(5.2), Inches(4.2))
    tf_sol = t_sol.text_frame
    tf_sol.word_wrap = True

    items_sol = [
        ("Phase 1: Environment-Agnostic HITL", "Human-In-The-Loop walkthrough on Day 1. The operator uses an intelligent auto-proposal UI with Quick-Assign buttons to tag containers. Generates 512-D OSNet visual fingerprints instantly."),
        ("Phase 2: Autonomous Re-ID Patrol", "Full autonomous patrol replay. Multi-layer filtering (crop-level blur rejection + frame motion gating + spatial voting) verifies known assets with 100% recall across 24 containers."),
        ("Dual-Output Advantage", "While enrolling assets, the tool automatically saves full frames and normalized YOLO labels (ready-to-train Kaggle/Colab dataset zip).")
    ]
    for i, (head, body) in enumerate(items_sol):
        p_h = tf_sol.paragraphs[0] if i == 0 else tf_sol.add_paragraph()
        p_h.text = f"✓  {head}"
        p_h.font.size = Pt(13)
        p_h.font.bold = True
        p_h.font.color.rgb = C_ACCENT
        p_b = tf_sol.add_paragraph()
        p_b.text = f"   {body}\n"
        p_b.font.size = Pt(11)
        p_b.font.color.rgb = C_TEXT_WHITE

    # =========================================================================
    # SLIDE 3: End-to-End System Architecture
    # =========================================================================
    slide3 = prs.slides.add_slide(blank_layout)
    set_slide_background(slide3)
    add_header(slide3, "End-to-End System Architecture: Phase 1 to Phase 3", "SYSTEM PIPELINE")

    col_w = Inches(3.7)
    col_h = Inches(5.1)
    col_top = Inches(1.8)

    # Col 1: Phase 1
    add_card(slide3, Inches(0.8), col_top, col_w, col_h, "PHASE 1: HITL ENROLLMENT")
    t_c1 = slide3.shapes.add_textbox(Inches(1.0), col_top + Inches(0.65), col_w - Inches(0.4), col_h - Inches(0.8))
    tf1 = t_c1.text_frame; tf1.word_wrap = True
    p = tf1.paragraphs[0]
    p.text = "Day-1 Baseline Walkthrough"
    p.font.size = Pt(12); p.font.bold = True; p.font.color.rgb = C_TEXT_WHITE

    p_body1 = [
        ("Container Candidate Proposer", "Heuristic color-face & digital ID board detector spots containers automatically."),
        ("Crop Quality Checker", "Laplacian variance filter rejects blurry or dark frames before fingerprinting."),
        ("OSNet Feature Extractor", "Extracts 512-D L2-normalized deep metric vector."),
        ("Reference Store (.npz)", "Multi-view embeddings saved into gallery (data/reference_db/)."),
        ("Bonus: YOLO Training Data", "Auto-saves bounding boxes for offline Kaggle/Colab fine-tuning.")
    ]
    for h, b in p_body1:
        ph = tf1.add_paragraph(); ph.text = f"• {h}: "; ph.font.size = Pt(10.5); ph.font.bold = True; ph.font.color.rgb = C_ACCENT
        pb = tf1.add_paragraph(); pb.text = f"  {b}"; pb.font.size = Pt(9.5); pb.font.color.rgb = C_TEXT_MUTED

    # Col 2: Phase 2
    add_card(slide3, Inches(4.8), col_top, col_w, col_h, "PHASE 2: AUTONOMOUS PATROL")
    t_c2 = slide3.shapes.add_textbox(Inches(5.0), col_top + Inches(0.65), col_w - Inches(0.4), col_h - Inches(0.8))
    tf2 = t_c2.text_frame; tf2.word_wrap = True
    p = tf2.paragraphs[0]
    p.text = "Live Verification on Patrol"
    p.font.size = Pt(12); p.font.bold = True; p.font.color.rgb = C_TEXT_WHITE

    p_body2 = [
        ("Motion Differencing", "Checks frame-level movement (absdiff); gates false heuristic proposals while moving."),
        ("Crop-Level Blur Gate", "Evaluates Laplacian variance on each candidate; discards blurry motion transients."),
        ("Color-Constrained Re-ID", "Cosine distance matching strictly restricted to matching color families."),
        ("Spatial-Temporal Voter", "Confidence-squared weighted vote buffer eliminates single-frame false alarms."),
        ("Live Verification HUD", "Real-time CONFIRMED / PROBABLE / UNKNOWN status badges on video feed.")
    ]
    for h, b in p_body2:
        ph = tf2.add_paragraph(); ph.text = f"• {h}: "; ph.font.size = Pt(10.5); ph.font.bold = True; ph.font.color.rgb = C_ACCENT
        pb = tf2.add_paragraph(); pb.text = f"  {b}"; pb.font.size = Pt(9.5); pb.font.color.rgb = C_TEXT_MUTED

    # Col 3: Phase 3
    add_card(slide3, Inches(8.8), col_top, col_w, col_h, "PHASE 3: SPATIAL TRACKING")
    t_c3 = slide3.shapes.add_textbox(Inches(9.0), col_top + Inches(0.65), col_w - Inches(0.4), col_h - Inches(0.8))
    tf3 = t_c3.text_frame; tf3.word_wrap = True
    p = tf3.paragraphs[0]
    p.text = "Global Map & Alerts"
    p.font.size = Pt(12); p.font.bold = True; p.font.color.rgb = C_TEXT_WHITE

    p_body3 = [
        ("Robot Pose Synchronization", "Synchronizes camera timestamp with localized robot pose (odom/tf bag)."),
        ("Ray Casting & Ground Projection", "Projects bottom-center bbox ray onto ground plane (Z=0) via camera intrinsics."),
        ("Map Coordinate Registration", "Maps visual detections into 2D world coordinates (X, Y) on site map."),
        ("Displacement Thresholding", "Compares patrol coordinates vs. Phase 1 baseline positions."),
        ("ASSET_MOVED Alert Engine", "Triggers high-priority security alert if an asset moves > 1.5m.")
    ]
    for h, b in p_body3:
        ph = tf3.add_paragraph(); ph.text = f"• {h}: "; ph.font.size = Pt(10.5); ph.font.bold = True; ph.font.color.rgb = C_ACCENT
        pb = tf3.add_paragraph(); pb.text = f"  {b}"; pb.font.size = Pt(9.5); pb.font.color.rgb = C_TEXT_MUTED

    # =========================================================================
    # SLIDE 4: Phase 1 Deep-Dive: HITL Enrollment Engine
    # =========================================================================
    slide4 = prs.slides.add_slide(blank_layout)
    set_slide_background(slide4)
    add_header(slide4, "Phase 1 Deep-Dive: Baseline Asset Registration & OSNet Fingerprinting", "PHASE 1 IMPLEMENTATION")

    gw = Inches(5.6)
    gh = Inches(2.4)

    add_card(slide4, Inches(0.8), Inches(1.8), gw, gh, "1. HEURISTIC CANDIDATE PROPOSER")
    tb = slide4.shapes.add_textbox(Inches(1.0), Inches(2.35), gw - Inches(0.4), gh - Inches(0.65))
    tf = tb.text_frame; tf.word_wrap = True
    p = tf.paragraphs[0]
    p.text = "• Dual-Detector Logic: Simultaneously spots colored container faces (HSV saturation/value thresholding) and digital ID display boards (high-contrast dark rectangles).\n• Strict Containment Suppression: IoMin and IoU suppression ensures exactly ONE proposal per physical container without duplicate overlaps.\n• Zero Pre-Training: Works out of the box on any new site with zero custom weights."
    p.font.size = Pt(11); p.font.color.rgb = C_TEXT_WHITE

    add_card(slide4, Inches(6.9), Inches(1.8), gw, gh, "2. EMBEDDED CROP QUALITY GATING")
    tb = slide4.shapes.add_textbox(Inches(7.1), Inches(2.35), gw - Inches(0.4), gh - Inches(0.65))
    tf = tb.text_frame; tf.word_wrap = True
    p = tf.paragraphs[0]
    p.text = "• Blur Variance: Computes Laplacian variance on candidate crops (threshold: min_blur = 45.0) to prevent corrupting gallery with motion-blurred frames.\n• Brightness & Contrast: Flags underexposed (<40) or overexposed (>235) crops.\n• Real-Time HUD Feedback: Displays 'QUALITY: OK' or 'QUALITY: LOW' directly in sidebar crop preview before enrollment."
    p.font.size = Pt(11); p.font.color.rgb = C_TEXT_WHITE

    add_card(slide4, Inches(0.8), Inches(4.45), gw, gh, "3. OSNET 512-D DEEP METRIC EMBEDDING")
    tb = slide4.shapes.add_textbox(Inches(1.0), Inches(5.0), gw - Inches(0.4), gh - Inches(0.65))
    tf = tb.text_frame; tf.word_wrap = True
    p = tf.paragraphs[0]
    p.text = "• Omni-Scale Architecture: OSNet extracts features across multiple spatial scales (global container body + localized ID digits).\n• 512-D L2-Normalized Vectors: Generates compact, ultra-fast cosine similarity vectors.\n• Multi-View Gallery: Stores 5–8 diverse viewpoints per container (front, angled, side) in data/reference_db/{asset_id}.npz for robust all-angle matching."
    p.font.size = Pt(11); p.font.color.rgb = C_TEXT_WHITE

    add_card(slide4, Inches(6.9), Inches(4.45), gw, gh, "4. AUTOMATIC DATASET PACKAGING")
    tb = slide4.shapes.add_textbox(Inches(7.1), Inches(5.0), gw - Inches(0.4), gh - Inches(0.65))
    tf = tb.text_frame; tf.word_wrap = True
    p = tf.paragraphs[0]
    p.text = "• Instant YOLO Labels: Every confirmed enrollment writes a normalized YOLO bbox (0 x_c y_c w h) and saves the raw frame into data/datasets/containers/.\n• Automated Cloud Packaging: When operator quits, the tool automatically packages all images & labels into a ready-to-upload .zip file for Kaggle/Colab training.\n• Complete Audit Log: Full JSON audit trail recorded in data/enrollment_log.json."
    p.font.size = Pt(11); p.font.color.rgb = C_TEXT_WHITE

    # =========================================================================
    # SLIDE 5: Phase 1 UI Overhaul: Professional Operator Tool (v2)
    # =========================================================================
    slide5 = prs.slides.add_slide(blank_layout)
    set_slide_background(slide5)
    add_header(slide5, "Phase 1 UI Redesign: Professional Black, White & Yellow Operator Experience", "OPERATOR INTERFACE v2")

    add_card(slide5, Inches(0.8), Inches(1.8), Inches(6.2), Inches(5.0), "NEW OPERATOR CAPABILITIES")
    t_feat = slide5.shapes.add_textbox(Inches(1.05), Inches(2.4), Inches(5.7), Inches(4.2))
    tf_feat = t_feat.text_frame; tf_feat.word_wrap = True

    ui_highlights = [
        ("Single-Window Canvas", "Eliminated clunky Tkinter popups and multi-window desync. Video feed on left, live sidebar on right, status bar at bottom."),
        ("Quick-Assign Buttons (Core UX Innovation)", "When an ID (e.g. CONT-001) is enrolled for the first time, a clickable button appears in the sidebar. For additional angles of the same asset, the operator simply clicks the button once — no retyping needed!"),
        ("Inline Text Input in HUD", "Operator presses [N] or [ENTER] to type a new ID directly inside the OpenCV sidebar. Fully keyboard driven with [ENTER] confirm and [ESC] cancel."),
        ("Live Crop Preview & Quality Feedback", "Shows a 240px zoom preview of the highlighted container with real-time blur and brightness metrics before saving."),
        ("Corporate Black/White/Yellow Theme", "Modern industrial theme matching defense/security monitoring consoles.")
    ]
    for i, (head, body) in enumerate(ui_highlights):
        p_h = tf_feat.paragraphs[0] if i == 0 else tf_feat.add_paragraph()
        p_h.text = f"★  {head}"
        p_h.font.size = Pt(12.5); p_h.font.bold = True; p_h.font.color.rgb = C_ACCENT
        p_b = tf_feat.add_paragraph(); p_b.text = f"    {body}\n"; p_b.font.size = Pt(10.5); p_b.font.color.rgb = C_TEXT_WHITE

    add_card(slide5, Inches(7.3), Inches(1.8), Inches(5.2), Inches(5.0), "UI COMPOSITE SCHEMATIC")
    t_sch = slide5.shapes.add_textbox(Inches(7.55), Inches(2.4), Inches(4.7), Inches(4.2))
    tf_sch = t_sch.text_frame; tf_sch.word_wrap = True
    p = tf_sch.paragraphs[0]
    p.text = (
        "┌─────────────────────────┬──────────────┐\n"
        "│                         │ CROP PREVIEW │\n"
        "│                         │ Quality: OK  │\n"
        "│       VIDEO FEED        ├──────────────┤\n"
        "│                         │ QUICK ASSIGN │\n"
        "│  [Selected Container]   │ [CONT-001]   │\n"
        "│   Yellow Bounding Box   │ [CONT-002]   │\n"
        "│                         ├──────────────┤\n"
        "│                         │ > NEW ID [_] │\n"
        "│                         ├──────────────┤\n"
        "│                         │ STATS PANEL  │\n"
        "├─────────────────────────┴──────────────┤\n"
        "│ STATUS: SPACE:Pause | ENTER:Enroll | Q:Export  │\n"
        "└────────────────────────────────────────┘\n\n"
        "• Instant keyboard navigation (A/D to seek, TAB to switch)\n"
        "• Click-to-assign reduces enrollment time by over 70%\n"
        "• 100% pure OpenCV rendering — zero OS dialog bugs"
    )
    p.font.name = "Consolas"; p.font.size = Pt(10); p.font.color.rgb = C_TEXT_MUTED

    # =========================================================================
    # SLIDE 6: Phase 2 Deep-Dive: Autonomous Patrol & Real-Time Re-ID
    # =========================================================================
    slide6 = prs.slides.add_slide(blank_layout)
    set_slide_background(slide6)
    add_header(slide6, "Phase 2 Deep-Dive: Autonomous Multi-Asset Re-ID & Anti-False-Alarm Pipeline", "PHASE 2 HARDENING")

    cw = Inches(5.6)
    ch = Inches(2.4)

    add_card(slide6, Inches(0.8), Inches(1.8), cw, ch, "FILTER 1: FRAME MOTION DIFFERENCING")
    tb = slide6.shapes.add_textbox(Inches(1.0), Inches(2.35), cw - Inches(0.4), ch - Inches(0.65))
    tf = tb.text_frame; tf.word_wrap = True
    p = tf.paragraphs[0]
    p.text = "• Problem: Robot movement causes camera shake and background streaks, generating hallucinated false container proposals.\n• Mechanism: Uses cv2.absdiff on consecutive frames (motion threshold = 6.0).\n• Adaptive Gating: When robot is moving, heuristic proposals are paused (only trained YOLO runs). Full candidate proposals resume when the robot slows or stops."
    p.font.size = Pt(11); p.font.color.rgb = C_TEXT_WHITE

    add_card(slide6, Inches(6.9), Inches(1.8), cw, ch, "FILTER 2: CROP-LEVEL BLUR REJECTION")
    tb = slide6.shapes.add_textbox(Inches(7.1), Inches(2.35), cw - Inches(0.4), ch - Inches(0.65))
    tf = tb.text_frame; tf.word_wrap = True
    p = tf.paragraphs[0]
    p.text = "• Problem: Even in a static scene, rapid panning blurs container faces, corrupting Re-ID cosine similarity.\n• Mechanism: Evaluates Laplacian variance directly on each candidate bounding box crop.\n• Quality Gate: Any crop with variance < 45.0 is discarded BEFORE reaching OSNet, guaranteeing only crisp visual fingerprints enter the matching pipeline."
    p.font.size = Pt(11); p.font.color.rgb = C_TEXT_WHITE

    add_card(slide6, Inches(0.8), Inches(4.45), cw, ch, "FILTER 3: COLOR-CONSTRAINED COSINE MATCHING")
    tb = slide6.shapes.add_textbox(Inches(1.0), Inches(5.0), cw - Inches(0.4), ch - Inches(0.65))
    tf = tb.text_frame; tf.word_wrap = True
    p = tf.paragraphs[0]
    p.text = "• Problem: Different containers with similar geometric shapes can produce borderline cosine similarity scores.\n• Mechanism: Classifies candidate crops into strict HSV color families (Red, Blue, Green, Yellow).\n• Cross-Color Suppression: Gallery queries are strictly constrained to candidate's own color group, eliminating 100% of cross-color identity confusion."
    p.font.size = Pt(11); p.font.color.rgb = C_TEXT_WHITE

    add_card(slide6, Inches(6.9), Inches(4.45), cw, ch, "FILTER 4: SPATIAL-TEMPORAL VOTING BUFFER")
    tb = slide6.shapes.add_textbox(Inches(7.1), Inches(5.0), cw - Inches(0.4), ch - Inches(0.65))
    tf = tb.text_frame; tf.word_wrap = True
    p = tf.paragraphs[0]
    p.text = "• Confidence-Squared Weighting: Votes are weighted by w = max(0.05, score^2) so high-confidence views dominate over marginal views.\n• Fast-Track Override: If a pristine match arrives (score >= 0.72) and previous history was weak, the buffer clears instantly to track the true asset.\n• Multi-Frame Consensus: Requires minimum 3 consistent spatial votes before locking ID."
    p.font.size = Pt(11); p.font.color.rgb = C_TEXT_WHITE

    # =========================================================================
    # SLIDE 7: Phase 2 Benchmark Verification Results
    # =========================================================================
    slide7 = prs.slides.add_slide(blank_layout)
    set_slide_background(slide7)
    add_header(slide7, "Phase 2 Verification: 100% Asset Recall Across 15,173 Patrol Frames", "BENCHMARK PERFORMANCE")

    m_w = Inches(2.7)
    m_h = Inches(1.5)
    m_top = Inches(1.8)

    add_card(slide7, Inches(0.8), m_top, m_w, m_h, bg_color=RGBColor(20, 35, 25), border_color=C_GREEN)
    tb = slide7.shapes.add_textbox(Inches(0.95), m_top + Inches(0.15), m_w - Inches(0.3), Inches(1.2))
    tf = tb.text_frame; tf.word_wrap = True
    p = tf.paragraphs[0]; p.text = "24 / 24"; p.font.size = Pt(32); p.font.bold = True; p.font.color.rgb = C_GREEN
    p2 = tf.add_paragraph(); p2.text = "100% ASSET RECALL\nAll enrolled assets found"; p2.font.size = Pt(10.5); p2.font.color.rgb = C_TEXT_WHITE

    add_card(slide7, Inches(3.8), m_top, m_w, m_h)
    tb = slide7.shapes.add_textbox(Inches(3.95), m_top + Inches(0.15), m_w - Inches(0.3), Inches(1.2))
    tf = tb.text_frame; tf.word_wrap = True
    p = tf.paragraphs[0]; p.text = "23,150"; p.font.size = Pt(32); p.font.bold = True; p.font.color.rgb = C_ACCENT
    p2 = tf.add_paragraph(); p2.text = "TOTAL DETECTIONS\nOver 15,173 video frames"; p2.font.size = Pt(10.5); p2.font.color.rgb = C_TEXT_WHITE

    add_card(slide7, Inches(6.8), m_top, m_w, m_h)
    tb = slide7.shapes.add_textbox(Inches(6.95), m_top + Inches(0.15), m_w - Inches(0.3), Inches(1.2))
    tf = tb.text_frame; tf.word_wrap = True
    p = tf.paragraphs[0]; p.text = "84.3%"; p.font.size = Pt(32); p.font.bold = True; p.font.color.rgb = C_ACCENT
    p2 = tf.add_paragraph(); p2.text = "CONFIRMED ACCURACY\n19,508 high-certainty hits"; p2.font.size = Pt(10.5); p2.font.color.rgb = C_TEXT_WHITE

    add_card(slide7, Inches(9.8), m_top, m_w, m_h)
    tb = slide7.shapes.add_textbox(Inches(9.95), m_top + Inches(0.15), m_w - Inches(0.3), Inches(1.2))
    tf = tb.text_frame; tf.word_wrap = True
    p = tf.paragraphs[0]; p.text = "96.2%"; p.font.size = Pt(32); p.font.bold = True; p.font.color.rgb = C_TEXT_WHITE
    p2 = tf.add_paragraph(); p2.text = "VERIFIED PATROL RATE\nConfirmed + Probable total"; p2.font.size = Pt(10.5); p2.font.color.rgb = C_TEXT_WHITE

    add_card(slide7, Inches(0.8), Inches(3.6), Inches(11.7), Inches(3.2), "FULL PHASE 2 PATROL REPLAY AUDIT BREAKDOWN")
    t_tbl = slide7.shapes.add_textbox(Inches(1.05), Inches(4.2), Inches(11.2), Inches(2.5))
    tf_tbl = t_tbl.text_frame; tf_tbl.word_wrap = True

    breakdown_text = (
        "• Video Processed: Phase2.mp4 (640×480 @ 9.8 FPS, 15,173 frames total, ~26 minutes continuous robot patrol)\n"
        "• Detection Breakdown:\n"
        "   - CONFIRMED Matches : 19,508 (84.3%) — Strict cosine similarity >= 0.60 with consensus voting\n"
        "   - PROBABLE Matches  : 2,750 (11.9%) — Secondary views / oblique angles with similarity >= 0.45\n"
        "   - AMBIGUOUS Matches : 71 (0.3%) — Flagged for human review when two candidates tie\n"
        "   - UNKNOWN Objects   : 818 (3.5%) — Suppressed transients, rejected blur frames, background clutter\n"
        "• Evidence Outputs Generated:\n"
        "   - Full Verified Output Video : evidence/patrol_runs/patrol_verified_20261106_124607.mp4\n"
        "   - Verified Image Snapshots   : 922 keyframe images saved in evidence/patrol_runs/snapshots_.../ (every 30 frames)\n"
        "• Stability & Performance: Ran end-to-end without a single crash, frame skip, or memory leak."
    )
    p = tf_tbl.paragraphs[0]; p.text = breakdown_text; p.font.size = Pt(11.5); p.font.color.rgb = C_TEXT_WHITE

    # =========================================================================
    # SLIDE 8: Visual Detection Evidence — Single Asset Progression (Images 1-4)
    # =========================================================================
    slide8 = prs.slides.add_slide(blank_layout)
    set_slide_background(slide8)
    add_header(slide8, "Visual Detection Evidence: High-Certainty Re-ID & Multi-Angle Tracking", "VISUAL EVIDENCE — KEYFRAMES")

    # 4 Columns for Images 1-4
    col_w4 = Inches(2.72)
    col_gap4 = Inches(0.24)
    card_top4 = Inches(1.8)
    card_h4 = Inches(5.1)

    user_slots_s8 = [
        ("CONT-001 (Angled)", "97% CONFIRMED", "patrol_frame_00333_CONT-001_angled.jpg",
         "Frame 333 (034.1s)",
         "• Initial angled approach detection.\n• Active Sights locked at 97% confidence.\n• State correctly recognized as STATIONARY."),

        ("CONT-001 (Direct Lock)", "97% CONFIRMED", "patrol_frame_00363_CONT-001_confirmed.jpg",
         "Frame 363 (037.2s)",
         "• Head-on confirmed hit (v10/12 votes).\n• Demonstrates headlight glare tolerance.\n• Solid Green Bounding Box lock."),

        ("CONT-002 (Row Depth)", "82% TRACKING", "patrol_frame_00891_CONT-002_perspective.jpg",
         "Frame 891 (091.2s)",
         "• Long-range perspective corridor view.\n• Locks CONT-002 in foreground while seeing CONT-003/004 lined up behind.\n• Zero occlusion cross-talk."),

        ("CONT-002 (Direct Lock)", "96% CONFIRMED", "patrol_frame_00921_CONT-002_confirmed.jpg",
         "Frame 921 (094.3s)",
         "• Full container face match (v9/12 votes).\n• Blue color family constrained search.\n• Strict IoU suppression eliminates false border proposals.")
    ]

    for i, (title, badge_txt, img_fname, frame_tag, desc) in enumerate(user_slots_s8):
        x = Inches(0.8) + i * (col_w4 + col_gap4)
        add_card(slide8, x, card_top4, col_w4, card_h4, title)

        # Embed Image
        img_p = IMG_DIR / img_fname
        img_w = Inches(2.46)
        img_h = Inches(1.845)
        img_top = card_top4 + Inches(0.65)
        if img_p.exists():
            slide8.shapes.add_picture(str(img_p), x + Inches(0.13), img_top, width=img_w, height=img_h)

        # Caption text
        cap_box = slide8.shapes.add_textbox(x + Inches(0.13), card_top4 + Inches(2.55), col_w4 - Inches(0.26), Inches(2.3))
        tf_cap = cap_box.text_frame; tf_cap.word_wrap = True

        p_b = tf_cap.paragraphs[0]; p_b.text = badge_txt; p_b.font.size = Pt(10.5); p_b.font.bold = True
        p_b.font.color.rgb = C_GREEN if "CONFIRMED" in badge_txt else C_ACCENT

        p_ft = tf_cap.add_paragraph(); p_ft.text = frame_tag; p_ft.font.size = Pt(10); p_ft.font.bold = True; p_ft.font.color.rgb = C_TEXT_WHITE

        p_d = tf_cap.add_paragraph(); p_d.text = desc; p_d.font.size = Pt(9.2); p_d.font.color.rgb = C_TEXT_MUTED

    # =========================================================================
    # SLIDE 9: Visual Detection Evidence — Dual Corridor Tracking (Image 5)
    # =========================================================================
    slide9 = prs.slides.add_slide(blank_layout)
    set_slide_background(slide9)
    add_header(slide9, "Visual Detection Evidence: Dual-Corridor Simultaneous Multi-Asset Tracking", "VISUAL EVIDENCE — DUAL TRACKING")

    # Left: Large High-Res Picture (Image 5)
    img5_card = add_card(slide9, Inches(0.8), Inches(1.8), Inches(6.4), Inches(5.0), "SIMULTANEOUS DUAL RECOGNITION (FRAME 1330)")
    img5_p = IMG_DIR / "patrol_frame_01330_dual_CONT-006_CONT-024.jpg"
    if img5_p.exists():
        slide9.shapes.add_picture(str(img5_p), Inches(1.0), Inches(2.4), width=Inches(6.0), height=Inches(4.2))

    # Right: Technical Analysis Cards
    add_card(slide9, Inches(7.5), Inches(1.8), Inches(5.0), Inches(5.0), "MULTI-OBJECT RE-ID ENGINEERING ANALYSIS")
    tb_dual = slide9.shapes.add_textbox(Inches(7.75), Inches(2.4), Inches(4.5), Inches(4.2))
    tf_dual = tb_dual.text_frame; tf_dual.word_wrap = True

    dual_points = [
        ("Simultaneous Multi-Asset Lock",
         "At Frame 1330 (136.1s), the UGV navigates the central roadway. The pipeline detects and locks two distinct containers simultaneously:\n"
         "  • Left: CONT-006 (RED) at 69% CONFIRMED (12/12 consensus votes)\n"
         "  • Right: CONT-024 (YELLOW) at 66% CONFIRMED (12/12 consensus votes)"),

        ("Color-Constrained Segregation",
         "The left candidate is classified as RED and matched only against RED references. The right candidate is classified as YELLOW and matched only against YELLOW references. Zero identity cross-talk across the roadway."),

        ("Spatial Consensus Independence",
         "The SpatialVoter maintains independent temporal tracking tubes. Even though both containers appear concurrently in the field of view, each maintains its own 12-frame consensus buffer."),

        ("Extreme Perspective Tolerance",
         "Notice both containers are at steep oblique angles relative to the camera axis. Our multi-view OSNet gallery matches side and 3/4 profiles with high stability.")
    ]

    for i, (head, body) in enumerate(dual_points):
        ph = tf_dual.paragraphs[0] if i == 0 else tf_dual.add_paragraph()
        ph.text = f"★  {head}"
        ph.font.size = Pt(12); ph.font.bold = True; ph.font.color.rgb = C_ACCENT
        pb = tf_dual.add_paragraph()
        pb.text = f"{body}\n"
        pb.font.size = Pt(10); pb.font.color.rgb = C_TEXT_WHITE

    # =========================================================================
    # SLIDE 10: Transition to Phase 3: Spatial Map Tracking & Displacement
    # =========================================================================
    slide10 = prs.slides.add_slide(blank_layout)
    set_slide_background(slide10)
    add_header(slide10, "Looking Ahead to Phase 3: Spatial Map Tracking & Displacement Alerts", "PHASE 3 ROADMAP")

    col3_w = Inches(3.7)
    col3_h = Inches(5.0)

    add_card(slide10, Inches(0.8), Inches(1.8), col3_w, col3_h, "1. GROUND RAY-CASTING")
    tb = slide10.shapes.add_textbox(Inches(1.0), Inches(2.4), col3_w - Inches(0.4), col3_h - Inches(0.7))
    tf = tb.text_frame; tf.word_wrap = True
    p = tf.paragraphs[0]
    p.text = (
        "• Camera Geometry: Uses pinhole camera intrinsic matrix (fx, fy, cx, cy) and extrinsic pitch angle.\n\n"
        "• Bounding Box Ground Point: Casts a 3D ray through the bottom-center pixel (x_c, y2) of the container bounding box.\n\n"
        "• Ground Plane Intersection: Intersects ray with the floor plane (Z = 0) to compute metric container position relative to robot: [X_rob, Y_rob]."
    )
    p.font.size = Pt(11); p.font.color.rgb = C_TEXT_WHITE

    add_card(slide10, Inches(4.8), Inches(1.8), col3_w, col3_h, "2. GLOBAL MAP PROJECTION")
    tb = slide10.shapes.add_textbox(Inches(5.0), Inches(2.4), col3_w - Inches(0.4), col3_h - Inches(0.7))
    tf = tb.text_frame; tf.word_wrap = True
    p = tf.paragraphs[0]
    p.text = (
        "• Robot Pose Synchronization: Queries robot position & orientation (x_r, y_r, yaw) from synchronized odometry/TF bag topics.\n\n"
        "• 2D Rigid Transform: Converts local container coordinates into global site map coordinates:\n"
        "  X_map = x_r + X_rob*cos(yaw) - Y_rob*sin(yaw)\n"
        "  Y_map = y_r + X_rob*sin(yaw) + Y_rob*cos(yaw)\n\n"
        "• Spatial Footprint: Plots container location on the 2D occupancy grid map."
    )
    p.font.size = Pt(11); p.font.color.rgb = C_TEXT_WHITE

    add_card(slide10, Inches(8.8), Inches(1.8), col3_w, col3_h, "3. ASSET_MOVED ALERT ENGINE")
    tb = slide10.shapes.add_textbox(Inches(9.0), Inches(2.4), col3_w - Inches(0.4), col3_h - Inches(0.7))
    tf = tb.text_frame; tf.word_wrap = True
    p = tf.paragraphs[0]
    p.text = (
        "• Baseline Position Register: Recorded during Phase 1 walkthrough (X_0, Y_0).\n\n"
        "• Real-Time Euclidean Delta: During Phase 3 patrol, monitors:\n"
        "  Δd = sqrt((X_t - X_0)^2 + (Y_t - Y_0)^2)\n\n"
        "• Automated Alert Generation:\n"
        "  - If Δd > 1.5m: Triggers ASSET_MOVED alert\n"
        "  - Saves side-by-side evidence image\n"
        "  - Generates JSON security audit dispatch."
    )
    p.font.size = Pt(11); p.font.color.rgb = C_TEXT_WHITE

    # =========================================================================
    # SLIDE 11: Deliverables Summary & Live Demo Agenda
    # =========================================================================
    slide11 = prs.slides.add_slide(blank_layout)
    set_slide_background(slide11)
    add_header(slide11, "Deliverables Summary & Live Demonstration Agenda", "CONCLUSION & DEMO FLOW")

    add_card(slide11, Inches(0.8), Inches(1.8), Inches(6.0), Inches(5.0), "DELIVERABLES COMPLETED")
    t_del = slide11.shapes.add_textbox(Inches(1.05), Inches(2.4), Inches(5.5), Inches(4.2))
    tf_del = t_del.text_frame; tf_del.word_wrap = True

    deliv_items = [
        ("Phase 1 HITL Enrollment Tool (v2)", "scripts/hitl_enrollment.py — Full single-window UI with Quick-Assign buttons, inline text input, and auto Kaggle/Colab training zip export."),
        ("Calibrated Reference Store", "data/reference_db/*.npz — 139 multi-view embeddings for 24 containers (CONT-001 to CONT-024)."),
        ("Hardened Autonomous Patrol Runner", "scripts/run_patrol.py — 4-layer anti-false-alarm pipeline, 100% recall (24/24), 84.3% confirmed detections."),
        ("Full Verification Artifacts", "Verified output video (15,173 frames) + 922 labeled keyframe snapshots in evidence/patrol_runs/."),
        ("100% Unit Test Pass Rate", "119 / 119 unit tests passing across all perception modules.")
    ]
    for i, (head, body) in enumerate(deliv_items):
        p_h = tf_del.paragraphs[0] if i == 0 else tf_del.add_paragraph()
        p_h.text = f"✓  {head}"
        p_h.font.size = Pt(12); p_h.font.bold = True; p_h.font.color.rgb = C_ACCENT
        p_b = tf_del.add_paragraph()
        p_b.text = f"    {body}\n"; p_b.font.size = Pt(10); p_b.font.color.rgb = C_TEXT_MUTED

    add_card(slide11, Inches(7.1), Inches(1.8), Inches(5.4), Inches(5.0), "MEETING DEMONSTRATION FLOW")
    t_demo = slide11.shapes.add_textbox(Inches(7.35), Inches(2.4), Inches(4.9), Inches(4.2))
    tf_demo = t_demo.text_frame; tf_demo.word_wrap = True

    demo_steps = [
        ("Step 1: Introduction (2 min)", "Present the industrial challenge & the two-phase approach on Slide 2."),
        ("Step 2: Live Phase 1 Demo (5 min)", "Launch hitl_enrollment.py on Phase 1 video. Show the clean Black/White/Yellow UI, auto-proposals, pause, click Quick-Assign button, and show auto-exported training zip."),
        ("Step 3: Live Phase 2 Demo (6 min)", "Play verified patrol video patrol_verified_20261106_124607.mp4. Point out real-time CONFIRMED badges, 24/24 container recall, and motion-blur rejection."),
        ("Step 4: Visual Detections Walkthrough (3 min)", "Walk through Slides 8 & 9 showing your verified keyframes (CONT-001, CONT-002, and dual CONT-006/024)."),
        ("Step 5: Phase 3 Roadmap & Q&A (4 min)", "Explain map projection & displacement alert engine. Take client questions.")
    ]
    for i, (step, desc) in enumerate(demo_steps):
        p_s = tf_demo.paragraphs[0] if i == 0 else tf_demo.add_paragraph()
        p_s.text = f"{step}"
        p_s.font.size = Pt(11.5); p_s.font.bold = True; p_s.font.color.rgb = C_TEXT_WHITE
        p_d = tf_demo.add_paragraph()
        p_d.text = f"  {desc}\n"; p_d.font.size = Pt(9.5); p_d.font.color.rgb = C_TEXT_MUTED

    try:
        prs.save(str(PPTX_PATH))
        print(f"Presentation successfully updated with user images at: {PPTX_PATH}")
    except PermissionError:
        alt_path = OUTPUT_DIR / "SITE_Assets_Monitor_Phase1_Phase2_Final.pptx"
        prs.save(str(alt_path))
        print(f"[Notice] {PPTX_PATH.name} was open in PowerPoint. Saved updated deck to: {alt_path}")


if __name__ == "__main__":
    create_deck()
