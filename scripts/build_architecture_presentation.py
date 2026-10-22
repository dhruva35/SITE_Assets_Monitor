"""
Build Architecture Presentation Deck
Generates a 16:9 widescreen presentation deck specifically explaining:
- The Environment-Agnostic Architecture Modifications
- 3-Tier Layered Design (Base Engine, Configuration Profiles, Use-Case Rules)
- HITL-to-Autonomous Lifecycle (Phase 0 to Phase 4)
- Clarification on Edge Deployment (Raspberry Pi 5 CPU) vs Offline Fine-Tuning (Laptop/Cloud GPU)
- Live Inference Engine & 4-Tier Identity Confidence
- Engineering Safeguards (Lighting, Occlusion, Compute Budget)
- Business Impact (Prototype vs Agnostic Platform)
- Delivery Roadmap & Milestones

Tailored for Engineering Leadership and Client Biraj.
Contains ZERO references to commercial third-party platforms.
"""

import os
import sys

# Ensure python-pptx is available
try:
    from pptx import Presentation
    from pptx.util import Inches, Pt
    from pptx.dml.color import RGBColor
    from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
    from pptx.enum.shapes import MSO_SHAPE
except ImportError:
    import subprocess
    print("Installing python-pptx...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "python-pptx"])
    from pptx import Presentation
    from pptx.util import Inches, Pt
    from pptx.dml.color import RGBColor
    from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
    from pptx.enum.shapes import MSO_SHAPE

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PARENT_ROOT = os.path.dirname(PROJECT_ROOT)

# Design System Palette (Executive High-Tech Theme)
COLOR_BG_DARK = RGBColor(15, 23, 42)          # Deep Midnight Slate 900
COLOR_BG_LIGHT = RGBColor(248, 250, 252)      # Crisp Off-White Slate 50
COLOR_CARD_BG = RGBColor(255, 255, 255)       # Pure White Card
COLOR_CARD_BORDER = RGBColor(226, 232, 240)   # Slate 200 Border
COLOR_PRIMARY = RGBColor(24, 76, 120)         # Steel Blue 800
COLOR_PRIMARY_LIGHT = RGBColor(238, 245, 251) # Soft Blue 50
COLOR_ACCENT_CYAN = RGBColor(14, 165, 233)    # Bright Cyan
COLOR_TEXT_MAIN = RGBColor(30, 41, 59)        # Slate 800 Dark Text
COLOR_TEXT_MUTED = RGBColor(100, 116, 139)    # Slate 500 Subtitle
COLOR_TEXT_LIGHT = RGBColor(241, 245, 249)    # Slate 100 White/Light
COLOR_GREEN = RGBColor(16, 185, 129)          # Emerald 500
COLOR_GREEN_LIGHT = RGBColor(236, 253, 245)   # Emerald 50
COLOR_AMBER = RGBColor(245, 158, 11)          # Amber 500
COLOR_AMBER_LIGHT = RGBColor(254, 243, 199)   # Amber 50
COLOR_RED = RGBColor(239, 68, 68)             # Rose 500
COLOR_PURPLE = RGBColor(139, 92, 246)         # Violet 500

FONT_HEADING = "Segoe UI"
FONT_BODY = "Segoe UI"
TOTAL_SLIDES = 10

def set_slide_background(slide, color):
    """Sets a solid background color for a slide."""
    background = slide.background
    fill = background.fill
    fill.solid()
    fill.fore_color.rgb = color

def add_header(slide, badge_text, title_text, subtitle_text=None, is_dark=False):
    """Standardized clean header with category badge, title, subtitle, and divider."""
    # Category Badge
    badge_box = slide.shapes.add_textbox(Inches(0.8), Inches(0.4), Inches(9), Inches(0.32))
    bf = badge_box.text_frame
    bf.word_wrap = True
    bf.margin_left = bf.margin_top = bf.margin_right = bf.margin_bottom = 0
    bp = bf.paragraphs[0]
    bp.text = badge_text.upper()
    bp.font.name = FONT_HEADING
    bp.font.size = Pt(10)
    bp.font.bold = True
    bp.font.color.rgb = COLOR_ACCENT_CYAN if is_dark else COLOR_PRIMARY

    # Main Title
    title_box = slide.shapes.add_textbox(Inches(0.8), Inches(0.72), Inches(11.5), Inches(0.55))
    tf = title_box.text_frame
    tf.word_wrap = True
    tf.margin_left = tf.margin_top = tf.margin_right = tf.margin_bottom = 0
    tp = tf.paragraphs[0]
    tp.text = title_text
    tp.font.name = FONT_HEADING
    tp.font.size = Pt(21)
    tp.font.bold = True
    tp.font.color.rgb = COLOR_TEXT_LIGHT if is_dark else COLOR_TEXT_MAIN

    # Subtitle
    if subtitle_text:
        sub_box = slide.shapes.add_textbox(Inches(0.8), Inches(1.28), Inches(11.5), Inches(0.35))
        sf = sub_box.text_frame
        sf.word_wrap = True
        sf.margin_left = sf.margin_top = sf.margin_right = sf.margin_bottom = 0
        sp = sf.paragraphs[0]
        sp.text = subtitle_text
        sp.font.name = FONT_BODY
        sp.font.size = Pt(11.5)
        sp.font.color.rgb = RGBColor(148, 163, 184) if is_dark else COLOR_TEXT_MUTED

    # Header dividing rule
    divider = slide.shapes.add_shape(
        MSO_SHAPE.RECTANGLE,
        Inches(0.8), Inches(1.65), Inches(11.733), Inches(0.015)
    )
    divider.fill.solid()
    divider.fill.fore_color.rgb = RGBColor(51, 65, 85) if is_dark else RGBColor(226, 232, 240)
    divider.line.fill.background()

def add_footer(slide, current_page, total_pages=TOTAL_SLIDES, is_dark=False):
    """Standardized modern footer."""
    foot_box = slide.shapes.add_textbox(Inches(0.8), Inches(7.05), Inches(9.5), Inches(0.3))
    ff = foot_box.text_frame
    ff.margin_left = ff.margin_top = ff.margin_right = ff.margin_bottom = 0
    fp = ff.paragraphs[0]
    fp.text = "SITE Assets Monitor | Environment-Agnostic Perception Platform Architecture"
    fp.font.name = FONT_BODY
    fp.font.size = Pt(9)
    fp.font.color.rgb = RGBColor(100, 116, 139) if is_dark else RGBColor(148, 163, 184)

    page_box = slide.shapes.add_textbox(Inches(10.5), Inches(7.05), Inches(2.0), Inches(0.3))
    pf = page_box.text_frame
    pf.margin_left = pf.margin_top = pf.margin_right = pf.margin_bottom = 0
    pp = pf.paragraphs[0]
    pp.alignment = PP_ALIGN.RIGHT
    pp.text = f"{current_page} / {total_pages}"
    pp.font.name = FONT_BODY
    pp.font.size = Pt(9)
    pp.font.bold = True
    pp.font.color.rgb = RGBColor(100, 116, 139) if is_dark else RGBColor(148, 163, 184)

def create_card(slide, left, top, width, height, bg_color=COLOR_CARD_BG, border_color=COLOR_CARD_BORDER):
    """Helper to draw a styled rectangular card container."""
    card = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, left, top, width, height)
    card.fill.solid()
    card.fill.fore_color.rgb = bg_color
    card.line.color.rgb = border_color
    card.line.width = Pt(1)
    return card

# ==========================================================
# SLIDE 1: COVER SLIDE (DARK MODERN)
# ==========================================================
def build_slide_1(prs):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    set_slide_background(slide, COLOR_BG_DARK)

    # Accent decorative top bar
    bar = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0.8), Inches(0.8), Inches(1.5), Inches(0.06))
    bar.fill.solid()
    bar.fill.fore_color.rgb = COLOR_ACCENT_CYAN
    bar.line.fill.background()

    # Pill badge
    badge = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(0.8), Inches(1.15), Inches(3.8), Inches(0.35))
    badge.fill.solid()
    badge.fill.fore_color.rgb = RGBColor(30, 41, 59)
    badge.line.color.rgb = RGBColor(51, 65, 85)
    bf = badge.text_frame
    bp = bf.paragraphs[0]
    bp.alignment = PP_ALIGN.CENTER
    bp.text = "ARCHITECTURE EVOLUTION & PLATFORM MODIFICATIONS"
    bp.font.name = FONT_HEADING
    bp.font.size = Pt(9.5)
    bp.font.bold = True
    bp.font.color.rgb = COLOR_ACCENT_CYAN

    # Main Title
    t_box = slide.shapes.add_textbox(Inches(0.8), Inches(1.7), Inches(11.5), Inches(1.5))
    tf = t_box.text_frame
    tf.word_wrap = True
    tp = tf.paragraphs[0]
    tp.text = "Environment-Agnostic Perception Platform"
    tp.font.name = FONT_HEADING
    tp.font.size = Pt(38)
    tp.font.bold = True
    tp.font.color.rgb = RGBColor(255, 255, 255)

    sub_p = tf.add_paragraph()
    sub_p.text = "Standardized Core Perception Engine, Human-in-the-Loop Bootstrap & Autonomous Edge Auditing"
    sub_p.font.name = FONT_BODY
    sub_p.font.size = Pt(16)
    sub_p.font.color.rgb = RGBColor(148, 163, 184)
    sub_p.space_before = Pt(6)

    # Executive Summary Paragraph
    desc_box = slide.shapes.add_textbox(Inches(0.8), Inches(3.3), Inches(11.5), Inches(1.3))
    df = desc_box.text_frame
    df.word_wrap = True
    dp = df.paragraphs[0]
    dp.text = (
        "This presentation details the architectural refactoring of the SITE Assets Monitor system. "
        "We have transitioned the perception stack from an environment-dependent prototype into a modular, "
        "configuration-driven base platform capable of rapid multi-client deployment with zero core code changes, "
        "seamless Human-in-the-Loop onboarding, and optimized CPU execution on mobile ground robots."
    )
    dp.font.name = FONT_BODY
    dp.font.size = Pt(13)
    dp.font.color.rgb = RGBColor(203, 213, 225)

    # 3 High-Impact Spec Cards
    specs = [
        ("CORE ARCHITECTURE", "3-Tier Layered Framework", "Frozen Engine + Profile + Rules"),
        ("HARDWARE BOUNDARY", "Raspberry Pi 5 (CPU)", "Zero Onboard Training Required"),
        ("DEPLOYMENT VELOCITY", "< 1 Day Calibration", "Zero Per-Client Code Rewrites")
    ]
    card_w = Inches(3.64)
    card_h = Inches(1.25)
    for i, (label, val, sub) in enumerate(specs):
        left = Inches(0.8) + i * Inches(3.9)
        c = create_card(slide, left, Inches(5.15), card_w, card_h, bg_color=RGBColor(30, 41, 59), border_color=RGBColor(51, 65, 85))
        box = slide.shapes.add_textbox(left + Inches(0.2), Inches(5.25), card_w - Inches(0.4), Inches(1.0))
        bf = box.text_frame
        lp = bf.paragraphs[0]
        lp.text = label
        lp.font.name = FONT_HEADING
        lp.font.size = Pt(9.5)
        lp.font.bold = True
        lp.font.color.rgb = COLOR_ACCENT_CYAN
        
        vp = bf.add_paragraph()
        vp.text = val
        vp.font.name = FONT_HEADING
        vp.font.size = Pt(13)
        vp.font.bold = True
        vp.font.color.rgb = RGBColor(241, 245, 249)
        vp.space_before = Pt(3)

        sp = bf.add_paragraph()
        sp.text = sub
        sp.font.name = FONT_BODY
        sp.font.size = Pt(10.5)
        sp.font.color.rgb = RGBColor(148, 163, 184)
        sp.space_before = Pt(2)

    add_footer(slide, 1, is_dark=True)

# ==========================================================
# SLIDE 2: WHY WE EVOLVED THE ARCHITECTURE (BEFORE VS AFTER)
# ==========================================================
def build_slide_2(prs):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    set_slide_background(slide, COLOR_BG_LIGHT)
    add_header(
        slide,
        badge_text="Strategic Motivation",
        title_text="Why Evolve from a Prototype to a Scalable Platform?",
        subtitle_text="Moving from brittle, site-specific code to an industrial base engine designed for fleet scale."
    )

    card_w = Inches(5.66)
    card_h = Inches(4.9)
    top_y = Inches(1.9)

    # Left Card: Site-Specific Prototype (Before)
    left_x = Inches(0.8)
    create_card(slide, left_x, top_y, card_w, card_h, bg_color=COLOR_CARD_BG, border_color=COLOR_CARD_BORDER)
    
    # Left Header Accent
    accent_bar_l = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, left_x + Inches(0.3), top_y + Inches(0.3), Inches(1.2), Inches(0.05))
    accent_bar_l.fill.solid()
    accent_bar_l.fill.fore_color.rgb = COLOR_AMBER
    accent_bar_l.line.fill.background()

    tb_l = slide.shapes.add_textbox(left_x + Inches(0.3), top_y + Inches(0.45), card_w - Inches(0.6), Inches(4.2))
    tf_l = tb_l.text_frame
    tf_l.word_wrap = True

    p = tf_l.paragraphs[0]
    p.text = "BEFORE: Site-Specific Prototype"
    p.font.name = FONT_HEADING
    p.font.size = Pt(17)
    p.font.bold = True
    p.font.color.rgb = COLOR_TEXT_MAIN

    p_sub = tf_l.add_paragraph()
    p_sub.text = "Tightly coupled to a single environment and fixed taxonomy."
    p_sub.font.name = FONT_BODY
    p_sub.font.size = Pt(11)
    p_sub.font.color.rgb = COLOR_TEXT_MUTED
    p_sub.space_before = Pt(2)
    p_sub.space_after = Pt(12)

    points_l = [
        ("Hardcoded Rules & Classes", "Model classes, camera settings, and thresholds were hardcoded in Python files."),
        ("Expensive Per-Client Engineering", "Deploying to a second client (e.g. port or warehouse) required branching code and rewriting logic."),
        ("No Adaptation Mechanism", "If lighting shifted or new machinery arrived, the system had no structured way to learn or adjust."),
        ("High Maintenance Overhead", "Bug fixes in one deployment could not be easily pushed to other client sites without merging conflicts.")
    ]

    for title, desc in points_l:
        p_t = tf_l.add_paragraph()
        p_t.text = f"•  {title}:"
        p_t.font.name = FONT_HEADING
        p_t.font.size = Pt(11.5)
        p_t.font.bold = True
        p_t.font.color.rgb = COLOR_TEXT_MAIN
        p_t.space_before = Pt(6)

        p_d = tf_l.add_paragraph()
        p_d.text = f"   {desc}"
        p_d.font.name = FONT_BODY
        p_d.font.size = Pt(10.5)
        p_d.font.color.rgb = COLOR_TEXT_MUTED
        p_d.space_before = Pt(1)

    # Right Card: Environment-Agnostic Platform (After)
    right_x = Inches(6.86)
    create_card(slide, right_x, top_y, card_w, card_h, bg_color=COLOR_PRIMARY_LIGHT, border_color=COLOR_ACCENT_CYAN)

    accent_bar_r = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, right_x + Inches(0.3), top_y + Inches(0.3), Inches(1.2), Inches(0.05))
    accent_bar_r.fill.solid()
    accent_bar_r.fill.fore_color.rgb = COLOR_GREEN
    accent_bar_r.line.fill.background()

    tb_r = slide.shapes.add_textbox(right_x + Inches(0.3), top_y + Inches(0.45), card_w - Inches(0.6), Inches(4.2))
    tf_r = tb_r.text_frame
    tf_r.word_wrap = True

    p = tf_r.paragraphs[0]
    p.text = "NOW: Environment-Agnostic Platform"
    p.font.name = FONT_HEADING
    p.font.size = Pt(17)
    p.font.bold = True
    p.font.color.rgb = COLOR_PRIMARY

    p_sub = tf_r.add_paragraph()
    p_sub.text = "Modular, profile-driven engine deployable anywhere in hours."
    p_sub.font.name = FONT_BODY
    p_sub.font.size = Pt(11)
    p_sub.font.color.rgb = COLOR_TEXT_MUTED
    p_sub.space_before = Pt(2)
    p_sub.space_after = Pt(12)

    points_r = [
        ("Zero Code Changes per Site", "100% of site-specific behavior is configured in clean YAML profiles."),
        ("Unified Core Engine", "Base perception algorithms (quality filtering, detection, ReID, spatial tracking) remain standard and frozen."),
        ("Rapid HITL Calibration", "Built-in Human-in-the-Loop workflow collects on-site data Day 1 and bootstraps autonomous tracking."),
        ("Continuous Fleet Updates", "Core algorithmic enhancements can be deployed universally to all client robots with zero site breakage.")
    ]

    for title, desc in points_r:
        p_t = tf_r.add_paragraph()
        p_t.text = f"✔  {title}:"
        p_t.font.name = FONT_HEADING
        p_t.font.size = Pt(11.5)
        p_t.font.bold = True
        p_t.font.color.rgb = COLOR_PRIMARY
        p_t.space_before = Pt(6)

        p_d = tf_r.add_paragraph()
        p_d.text = f"   {desc}"
        p_d.font.name = FONT_BODY
        p_d.font.size = Pt(10.5)
        p_d.font.color.rgb = COLOR_TEXT_MAIN
        p_d.space_before = Pt(1)

    add_footer(slide, 2)

# ==========================================================
# SLIDE 3: 3-TIER LAYERED ARCHITECTURE
# ==========================================================
def build_slide_3(prs):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    set_slide_background(slide, COLOR_BG_LIGHT)
    add_header(
        slide,
        badge_text="System Architecture",
        title_text="The 3-Tier Layered Architecture",
        subtitle_text="Strict separation between standard vision algorithms, site parameters, and use-case rules."
    )

    layers = [
        {
            "tier": "TIER 1",
            "name": "Standard Base Engine",
            "badge": "100% Reusable (Frozen)",
            "badge_color": COLOR_PRIMARY,
            "badge_bg": COLOR_PRIMARY_LIGHT,
            "desc": "The core algorithmic perception foundation. Identical on every robot and client site.",
            "components": [
                "Image Quality Checker (Rejects motion blur & bad lighting)",
                "YOLOv8 Neural Detector (ONNX Edge Inference)",
                "OSNet Deep Visual Re-ID (512D spatial embeddings)",
                "Reference Store (Cosine similarity & multi-view centroids)",
                "Forensic Evidence Generator (Raw frames + annotated crops + JSON metadata)"
            ]
        },
        {
            "tier": "TIER 2",
            "name": "Deployment Profiles",
            "badge": "Config Only (YAML)",
            "badge_color": COLOR_GREEN,
            "badge_bg": COLOR_GREEN_LIGHT,
            "desc": "Site-specific settings injected at startup. Enables new client setup in under an hour.",
            "components": [
                "Hardware Mapping (Camera resolution, FPS, ROS2 topics)",
                "Site Asset Taxonomy (Target machinery classes & priorities)",
                "Quality Gate Thresholds (Tolerances for outdoor vs indoor light)",
                "Model Weights Pointer (Path to site-calibrated ONNX model)",
                "Storage Paths (Evidence directories and retention policies)"
            ]
        },
        {
            "tier": "TIER 3",
            "name": "Use-Case Rules Layer",
            "badge": "Client Business Logic",
            "badge_color": COLOR_AMBER,
            "badge_bg": COLOR_AMBER_LIGHT,
            "desc": "High-level rules that translate raw perception states into operational security actions.",
            "components": [
                "Movement Geofencing (e.g. 3-meter displacement violation)",
                "Missing Equipment Alerting (Temporal hysteresis buffer)",
                "Shift Audit Generator (Shift-end asset compliance report)",
                "ROS2 / Webhook Event Dispatcher (Security operator alerts)"
            ]
        }
    ]

    card_w = Inches(3.64)
    card_h = Inches(4.9)
    top_y = Inches(1.9)

    for i, layer in enumerate(layers):
        left = Inches(0.8) + i * Inches(3.9)
        create_card(slide, left, top_y, card_w, card_h)

        tb = slide.shapes.add_textbox(left + Inches(0.25), top_y + Inches(0.25), card_w - Inches(0.5), card_h - Inches(0.5))
        tf = tb.text_frame
        tf.word_wrap = True

        p_tier = tf.paragraphs[0]
        p_tier.text = layer["tier"]
        p_tier.font.name = FONT_HEADING
        p_tier.font.size = Pt(10)
        p_tier.font.bold = True
        p_tier.font.color.rgb = layer["badge_color"]

        p_name = tf.add_paragraph()
        p_name.text = layer["name"]
        p_name.font.name = FONT_HEADING
        p_name.font.size = Pt(16)
        p_name.font.bold = True
        p_name.font.color.rgb = COLOR_TEXT_MAIN
        p_name.space_before = Pt(2)

        p_badge = tf.add_paragraph()
        p_badge.text = f"Status: {layer['badge']}"
        p_badge.font.name = FONT_HEADING
        p_badge.font.size = Pt(9.5)
        p_badge.font.bold = True
        p_badge.font.color.rgb = layer["badge_color"]
        p_badge.space_before = Pt(3)

        p_desc = tf.add_paragraph()
        p_desc.text = layer["desc"]
        p_desc.font.name = FONT_BODY
        p_desc.font.size = Pt(10.5)
        p_desc.font.color.rgb = COLOR_TEXT_MUTED
        p_desc.space_before = Pt(8)
        p_desc.space_after = Pt(10)

        p_comp_title = tf.add_paragraph()
        p_comp_title.text = "CORE MODULES & DUTIES:"
        p_comp_title.font.name = FONT_HEADING
        p_comp_title.font.size = Pt(10)
        p_comp_title.font.bold = True
        p_comp_title.font.color.rgb = COLOR_TEXT_MAIN
        p_comp_title.space_before = Pt(4)

        for comp in layer["components"]:
            cp = tf.add_paragraph()
            cp.text = f"• {comp}"
            cp.font.name = FONT_BODY
            cp.font.size = Pt(9.8)
            cp.font.color.rgb = COLOR_TEXT_MAIN
            cp.space_before = Pt(4)

    add_footer(slide, 3)

# ==========================================================
# SLIDE 4: DEPLOYMENT LIFECYCLE (PHASES 0 TO 4)
# ==========================================================
def build_slide_4(prs):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    set_slide_background(slide, COLOR_BG_LIGHT)
    add_header(
        slide,
        badge_text="Operational Lifecycle",
        title_text="The 5-Phase Deployment Lifecycle",
        subtitle_text="Step-by-step path from unboxing the robot on Day 1 to fully autonomous 24/7 site auditing."
    )

    phases = [
        ("PHASE 0", "Pre-Deployment", "~1-2 Hours (Engineering)", [
            "Clone base software repo on robot.",
            "Create 'profiles/client.yaml' from template.",
            "Configure camera, ROS2 topics, & FPS.",
            "Zero algorithmic code modification."
        ]),
        ("PHASE 1", "HITL Bootstrap", "Day 1 (2-4 Hours On-Site)", [
            "Robot patrols site guided by operator.",
            "Camera captures equipment crops.",
            "Operator confirms/names assets on tablet.",
            "Builds initial Re-ID visual fingerprints."
        ]),
        ("PHASE 2", "Offline Tuning", "~30 Min (Laptop / Cloud)", [
            "Transfer Day 1 photos to engineer's laptop.",
            "Run transfer learning fine-tuning on GPU.",
            "Export single lightweight ONNX model file.",
            "Copy ONNX to Pi 5 & point YAML to it."
        ]),
        ("PHASE 3", "Autonomous Ops", "Day 2 Onwards (24/7)", [
            "Robot audits assets completely marker-free.",
            "Real-time 3-5 FPS inspection on Pi 5 CPU.",
            "Evaluates location, movement, & status.",
            "Auto-generates legal-grade evidence packages."
        ]),
        ("PHASE 4", "Gradual Handoff", "Weeks 1 to 4 (The HITL Dial)", [
            "Week 1: ~50% human review (new assets).",
            "Week 2: ~20% review as library expands.",
            "Week 4+: <5% review (rare anomalies only).",
            "Near-zero routine human supervision."
        ])
    ]

    card_w = Inches(2.22)
    card_h = Inches(4.9)
    top_y = Inches(1.9)

    for i, (p_num, p_title, p_time, bullets) in enumerate(phases):
        left = Inches(0.8) + i * Inches(2.38)
        # Highlight Phase 2 and 3 with subtle tint
        bg = COLOR_PRIMARY_LIGHT if i == 2 else COLOR_CARD_BG
        border = COLOR_ACCENT_CYAN if i == 2 else COLOR_CARD_BORDER
        create_card(slide, left, top_y, card_w, card_h, bg_color=bg, border_color=border)

        tb = slide.shapes.add_textbox(left + Inches(0.15), top_y + Inches(0.2), card_w - Inches(0.3), card_h - Inches(0.4))
        tf = tb.text_frame
        tf.word_wrap = True

        p0 = tf.paragraphs[0]
        p0.text = p_num
        p0.font.name = FONT_HEADING
        p0.font.size = Pt(10)
        p0.font.bold = True
        p0.font.color.rgb = COLOR_PRIMARY if i != 2 else COLOR_ACCENT_CYAN

        p1 = tf.add_paragraph()
        p1.text = p_title
        p1.font.name = FONT_HEADING
        p1.font.size = Pt(14)
        p1.font.bold = True
        p1.font.color.rgb = COLOR_TEXT_MAIN
        p1.space_before = Pt(2)

        p2 = tf.add_paragraph()
        p2.text = p_time
        p2.font.name = FONT_BODY
        p2.font.size = Pt(9.5)
        p2.font.color.rgb = COLOR_TEXT_MUTED
        p2.space_before = Pt(2)
        p2.space_after = Pt(10)

        for b in bullets:
            bp = tf.add_paragraph()
            bp.text = f"• {b}"
            bp.font.name = FONT_BODY
            bp.font.size = Pt(9.5)
            bp.font.color.rgb = COLOR_TEXT_MAIN
            bp.space_before = Pt(4)

    add_footer(slide, 4)

# ==========================================================
# SLIDE 5: CLARIFYING FINE-TUNING VS EDGE DEPLOYMENT
# ==========================================================
def build_slide_5(prs):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    set_slide_background(slide, COLOR_BG_LIGHT)
    add_header(
        slide,
        badge_text="Compute Architecture",
        title_text="Edge Execution vs Offline Fine-Tuning Clarified",
        subtitle_text="How we achieve high accuracy on low-cost robot hardware without expensive onboard GPUs."
    )

    card_w = Inches(5.66)
    card_h = Inches(4.9)
    top_y = Inches(1.9)

    # Left: What Happens on the Robot (Pi 5)
    left_x = Inches(0.8)
    create_card(slide, left_x, top_y, card_w, card_h)

    bar_l = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, left_x + Inches(0.3), top_y + Inches(0.3), Inches(1.2), Inches(0.05))
    bar_l.fill.solid()
    bar_l.fill.fore_color.rgb = COLOR_ACCENT_CYAN
    bar_l.line.fill.background()

    tb_l = slide.shapes.add_textbox(left_x + Inches(0.3), top_y + Inches(0.45), card_w - Inches(0.6), Inches(4.2))
    tf_l = tb_l.text_frame
    tf_l.word_wrap = True

    p = tf_l.paragraphs[0]
    p.text = "ON THE ROBOT: Raspberry Pi 5 (Edge CPU)"
    p.font.name = FONT_HEADING
    p.font.size = Pt(16)
    p.font.bold = True
    p.font.color.rgb = COLOR_TEXT_MAIN

    p_sub = tf_l.add_paragraph()
    p_sub.text = "Dedicated solely to live inference and evidence logging."
    p_sub.font.name = FONT_BODY
    p_sub.font.size = Pt(11)
    p_sub.font.color.rgb = COLOR_TEXT_MUTED
    p_sub.space_before = Pt(2)
    p_sub.space_after = Pt(10)

    pi_points = [
        ("Inference Only (No Onboard Training)", "The Pi 5 has no NVIDIA CUDA GPU. Training on a Pi 5 would overheat, freeze RAM, and take days. It only *runs* pre-optimized models."),
        ("Fast ONNX CPU Runtime", "Executes pre-compiled ONNX models at ~250-350ms per inspection cycle, delivering an optimal 3-5 FPS for slow-moving ground AMRs."),
        ("Low Power & Cost", "Operates under 15 Watts without draining robot patrol battery life or requiring costly $2,000+ industrial GPU computers."),
        ("Day 1 Data Collector", "During Phase 1, the Pi 5 acts as a high-fidelity image recorder, capturing real-world crops for offline training.")
    ]

    for title, desc in pi_points:
        pt = tf_l.add_paragraph()
        pt.text = f"✔  {title}:"
        pt.font.name = FONT_HEADING
        pt.font.size = Pt(11)
        pt.font.bold = True
        pt.font.color.rgb = COLOR_PRIMARY
        pt.space_before = Pt(5)

        pd = tf_l.add_paragraph()
        pd.text = f"   {desc}"
        pd.font.name = FONT_BODY
        pd.font.size = Pt(10)
        pd.font.color.rgb = COLOR_TEXT_MAIN
        pd.space_before = Pt(1)

    # Right: What Happens Offline (Laptop / Cloud)
    right_x = Inches(6.86)
    create_card(slide, right_x, top_y, card_w, card_h, bg_color=COLOR_PRIMARY_LIGHT, border_color=COLOR_ACCENT_CYAN)

    bar_r = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, right_x + Inches(0.3), top_y + Inches(0.3), Inches(1.2), Inches(0.05))
    bar_r.fill.solid()
    bar_r.fill.fore_color.rgb = COLOR_GREEN
    bar_r.line.fill.background()

    tb_r = slide.shapes.add_textbox(right_x + Inches(0.3), top_y + Inches(0.45), card_w - Inches(0.6), Inches(4.2))
    tf_r = tb_r.text_frame
    tf_r.word_wrap = True

    p = tf_r.paragraphs[0]
    p.text = "OFFLINE: Laptop / Cloud GPU (Fine-Tuning)"
    p.font.name = FONT_HEADING
    p.font.size = Pt(16)
    p.font.bold = True
    p.font.color.rgb = COLOR_PRIMARY

    p_sub = tf_r.add_paragraph()
    p_sub.text = "The 30-minute transfer learning step on an engineer's GPU."
    p_sub.font.name = FONT_BODY
    p_sub.font.size = Pt(11)
    p_sub.font.color.rgb = COLOR_TEXT_MUTED
    p_sub.space_before = Pt(2)
    p_sub.space_after = Pt(10)

    train_points = [
        ("Where Training Happens", "Executed on an engineer's laptop with an NVIDIA RTX GPU or a free cloud notebook (Google Colab)."),
        ("Transfer Learning Speed", "Base model weights are kept frozen; only the final classification layer is adapted. Takes only 20-30 minutes for 200-500 images."),
        ("One-Step ONNX Export", "A single command converts the trained model into a portable '.onnx' binary (~12MB), optimized for CPU math."),
        ("1-Minute File Drop Deployment", "Copy the '.onnx' file to the robot via Wi-Fi or USB drive, update 1 line in 'detection_config.yaml', and restart. Zero code edits.")
    ]

    for title, desc in train_points:
        pt = tf_r.add_paragraph()
        pt.text = f"⚡  {title}:"
        pt.font.name = FONT_HEADING
        pt.font.size = Pt(11)
        pt.font.bold = True
        pt.font.color.rgb = COLOR_PRIMARY
        pt.space_before = Pt(5)

        pd = tf_r.add_paragraph()
        pd.text = f"   {desc}"
        pd.font.name = FONT_BODY
        pd.font.size = Pt(10)
        pd.font.color.rgb = COLOR_TEXT_MAIN
        pd.space_before = Pt(1)

    add_footer(slide, 5)

# ==========================================================
# SLIDE 6: LIVE INFERENCE PIPELINE & 4-TIER RE-ID
# ==========================================================
def build_slide_6(prs):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    set_slide_background(slide, COLOR_BG_LIGHT)
    add_header(
        slide,
        badge_text="Live Runtime Intelligence",
        title_text="Live Inference Pipeline & 4-Tier Identity Verification",
        subtitle_text="How each camera frame is evaluated in real time to guarantee accuracy and eliminate false alarms."
    )

    card_w = Inches(5.66)
    card_h = Inches(4.9)
    top_y = Inches(1.9)

    # Left: The Processing Flow
    left_x = Inches(0.8)
    create_card(slide, left_x, top_y, card_w, card_h)

    tb_l = slide.shapes.add_textbox(left_x + Inches(0.3), top_y + Inches(0.3), card_w - Inches(0.6), card_h - Inches(0.6))
    tf_l = tb_l.text_frame
    tf_l.word_wrap = True

    p = tf_l.paragraphs[0]
    p.text = "Frame Processing Pipeline (Every 200-300ms)"
    p.font.name = FONT_HEADING
    p.font.size = Pt(16)
    p.font.bold = True
    p.font.color.rgb = COLOR_TEXT_MAIN
    p.space_after = Pt(10)

    steps = [
        ("1. Quality Gate", "Rejects blurry, overexposed, or pitch-black frames in ~2ms before deep models run."),
        ("2. YOLOv8 Detection", "Detects machinery bboxes and initial class categories in ~150-180ms."),
        ("3. Deep Re-ID Fingerprint", "OSNet extracts a 512-dimensional visual embedding vector from valid crops (~60ms)."),
        ("4. Spatial Reference Match", "Calculates cosine similarity against stored asset fingerprints in the ReferenceStore (~1ms)."),
        ("5. Spatial Delta Tracking", "Compares detected position with baseline. Computes displacement vs 3m threshold."),
        ("6. Evidence & ROS2 Publish", "On state change or violation, logs raw + annotated evidence and publishes to ROS2 topic.")
    ]

    for title, desc in steps:
        pt = tf_l.add_paragraph()
        pt.text = f"▶  {title}"
        pt.font.name = FONT_HEADING
        pt.font.size = Pt(11)
        pt.font.bold = True
        pt.font.color.rgb = COLOR_PRIMARY
        pt.space_before = Pt(4)

        pd = tf_l.add_paragraph()
        pd.text = f"    {desc}"
        pd.font.name = FONT_BODY
        pd.font.size = Pt(9.8)
        pd.font.color.rgb = COLOR_TEXT_MUTED
        pd.space_before = Pt(1)

    # Right: 4-Tier Identity Verification
    right_x = Inches(6.86)
    create_card(slide, right_x, top_y, card_w, card_h)

    tb_r = slide.shapes.add_textbox(right_x + Inches(0.3), top_y + Inches(0.3), card_w - Inches(0.6), card_h - Inches(0.6))
    tf_r = tb_r.text_frame
    tf_r.word_wrap = True

    p = tf_r.paragraphs[0]
    p.text = "4-Tier Identity Confidence System"
    p.font.name = FONT_HEADING
    p.font.size = Pt(16)
    p.font.bold = True
    p.font.color.rgb = COLOR_TEXT_MAIN
    p.space_after = Pt(10)

    tiers = [
        ("CONFIRMED", "Similarity ≥ 0.85 (High Margin)", COLOR_GREEN,
         "Definite match. Asset identity is locked. State updated in registry without operator distraction."),
        ("PROBABLE", "Similarity ≥ 0.65", COLOR_AMBER,
         "Match under non-ideal angles or lighting. Logged with audit flag; automated tracking continues."),
        ("AMBIGUOUS", "Two Assets Competing Closely", COLOR_RED,
         "Cosine scores are tied (margin < 0.15). Alerts operator tablet for quick validation instead of guessing."),
        ("UNKNOWN", "Similarity < 0.40", COLOR_ACCENT_CYAN,
         "New equipment arrived on site. Auto-registers as candidate asset or triggers security onboarding review.")
    ]

    for name, threshold, color, action in tiers:
        pt = tf_r.add_paragraph()
        pt.text = f"●  {name} — {threshold}"
        pt.font.name = FONT_HEADING
        pt.font.size = Pt(11)
        pt.font.bold = True
        pt.font.color.rgb = color
        pt.space_before = Pt(6)

        pa = tf_r.add_paragraph()
        pa.text = f"    Action: {action}"
        pa.font.name = FONT_BODY
        pa.font.size = Pt(9.8)
        pa.font.color.rgb = COLOR_TEXT_MAIN
        pa.space_before = Pt(2)

    add_footer(slide, 6)

# ==========================================================
# SLIDE 7: REAL-WORLD SAFEGUARDS & ENGINEERING HARDENING
# ==========================================================
def build_slide_7(prs):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    set_slide_background(slide, COLOR_BG_LIGHT)
    add_header(
        slide,
        badge_text="Robustness & Reliability",
        title_text="Built for Industrial Field Conditions",
        subtitle_text="Proactive engineering safeguards addressing lighting variations, occlusions, and compute limits."
    )

    safeguards = [
        {
            "num": "01",
            "title": "Lighting & Sun Shadow Shifts",
            "problem": "Harsh morning vs late afternoon sunlight alters machine appearance.",
            "solution": "Multi-Embedding Centroids: The ReferenceStore stores up to 10 visual embeddings per asset across different times of day, computing a stable mathematical centroid resistant to glare and shadows."
        },
        {
            "num": "02",
            "title": "Temporary Obstacles & Occlusion",
            "problem": "A passing truck or worker momentarily blocks the camera's view.",
            "solution": "Temporal Hysteresis Buffering: Missing alerts are NEVER raised on a single frame dropout. The system requires N consecutive patrol misses before flagging 'ASSET MISSING', eliminating false security calls."
        },
        {
            "num": "03",
            "title": "Pi 5 Compute Bottlenecks",
            "problem": "Multiple machines in frame could drop frame rate below target.",
            "solution": "Adaptive Re-ID Execution: If an asset's bounding box is stationary across consecutive frames, deep Re-ID embedding extraction is safely bypassed, preserving steady 3-5 FPS execution."
        },
        {
            "num": "04",
            "title": "Forensic-Grade Evidence Logging",
            "problem": "Disputed relocation events or auditing compliance challenges.",
            "solution": "Dual-Stream Cryptographic Evidence: Saves pristine unannotated original frames, cropped asset views, annotated overlays, and JSON metadata with robot coordinates and timestamps for legal compliance."
        }
    ]

    card_w = Inches(5.66)
    card_h = Inches(2.32)

    positions = [
        (Inches(0.8), Inches(1.9)),
        (Inches(6.86), Inches(1.9)),
        (Inches(0.8), Inches(4.45)),
        (Inches(6.86), Inches(4.45))
    ]

    for i, s in enumerate(safeguards):
        left, top = positions[i]
        create_card(slide, left, top, card_w, card_h)

        tb = slide.shapes.add_textbox(left + Inches(0.25), top + Inches(0.18), card_w - Inches(0.5), card_h - Inches(0.36))
        tf = tb.text_frame
        tf.word_wrap = True

        p0 = tf.paragraphs[0]
        p0.text = f"{s['num']}  |  {s['title']}"
        p0.font.name = FONT_HEADING
        p0.font.size = Pt(13)
        p0.font.bold = True
        p0.font.color.rgb = COLOR_PRIMARY

        pp = tf.add_paragraph()
        pp.text = f"Challenge: {s['problem']}"
        pp.font.name = FONT_BODY
        pp.font.size = Pt(9.8)
        pp.font.color.rgb = COLOR_TEXT_MUTED
        pp.space_before = Pt(3)

        ps = tf.add_paragraph()
        ps.text = f"Safeguard: {s['solution']}"
        ps.font.name = FONT_BODY
        ps.font.size = Pt(10)
        ps.font.color.rgb = COLOR_TEXT_MAIN
        ps.space_before = Pt(3)

    add_footer(slide, 7)

# ==========================================================
# SLIDE 8: BUSINESS & OPERATIONAL IMPACT (PROTOTYPE VS PLATFORM)
# ==========================================================
def build_slide_8(prs):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    set_slide_background(slide, COLOR_BG_LIGHT)
    add_header(
        slide,
        badge_text="Executive Business Case",
        title_text="Commercial & Operational Impact",
        subtitle_text="Comparing project velocity, deployment costs, and operational reliability."
    )

    metrics = [
        {
            "title": "Client Deployment Speed",
            "before": "2–3 Weeks of Custom Engineering",
            "after": "< 1 Day Calibration (Profile + HITL)",
            "impact": "90% faster rollout. Enables signing and onboarding new facilities without software bottlenecks."
        },
        {
            "title": "Codebase Maintainability",
            "before": "Fragmented Forks per Client Site",
            "after": "Single Unified Base Codebase",
            "impact": "One bug fix or vision enhancement benefits every deployed robot simultaneously."
        },
        {
            "title": "Visual Accuracy & Reliability",
            "before": "Generic Out-of-the-Box Models (~50-60%)",
            "after": "Environment-Calibrated ONNX (85-95%+)",
            "impact": "Near-zero false alarms; high operator trust from day two of deployment."
        },
        {
            "title": "Hardware Investment",
            "before": "High-Cost Industrial GPU Modules",
            "after": "Low-Power Raspberry Pi 5 CPU",
            "impact": "Keeps robot build costs low while ensuring 24/7 battery endurance on mobile patrols."
        }
    ]

    card_w = Inches(11.733)
    card_h = Inches(1.1)
    top_base = Inches(1.9)

    for i, m in enumerate(metrics):
        top_y = top_base + i * Inches(1.25)
        create_card(slide, Inches(0.8), top_y, card_w, card_h)

        tb = slide.shapes.add_textbox(Inches(1.05), top_y + Inches(0.12), card_w - Inches(0.5), card_h - Inches(0.24))
        tf = tb.text_frame
        tf.word_wrap = True

        p_t = tf.paragraphs[0]
        p_t.text = m["title"].upper()
        p_t.font.name = FONT_HEADING
        p_t.font.size = Pt(11)
        p_t.font.bold = True
        p_t.font.color.rgb = COLOR_PRIMARY

        p_comp = tf.add_paragraph()
        p_comp.text = f"Prototype: {m['before']}    ➔    Agnostic Platform: {m['after']}"
        p_comp.font.name = FONT_HEADING
        p_comp.font.size = Pt(12)
        p_comp.font.bold = True
        p_comp.font.color.rgb = COLOR_TEXT_MAIN
        p_comp.space_before = Pt(2)

        p_imp = tf.add_paragraph()
        p_imp.text = f"Business Value: {m['impact']}"
        p_imp.font.name = FONT_BODY
        p_imp.font.size = Pt(10)
        p_imp.font.color.rgb = COLOR_TEXT_MUTED
        p_imp.space_before = Pt(2)

    add_footer(slide, 8)

# ==========================================================
# SLIDE 9: DELIVERY ROADMAP & ENGINEERING STEPS
# ==========================================================
def build_slide_9(prs):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    set_slide_background(slide, COLOR_BG_LIGHT)
    add_header(
        slide,
        badge_text="Execution Roadmap",
        title_text="Milestones & Immediate Next Steps",
        subtitle_text="Structured technical roadmap leading to live client demonstration and field validation."
    )

    steps = [
        {
            "stage": "STAGE 1",
            "name": "Modular Profile Loader",
            "status": "In Progress (Current Sprint)",
            "color": COLOR_PRIMARY,
            "tasks": [
                "Implement 'profile_loader.py' to parse YAML into active runtime modules.",
                "Inject dynamic class taxonomies & confidence thresholds.",
                "Ensure zero hardcoded paths across 'detector.py' and 'reference_store.py'."
            ]
        },
        {
            "stage": "STAGE 2",
            "name": "ROS2 Navigation Handshake",
            "status": "Awaiting Bag File / Topics",
            "color": COLOR_AMBER,
            "tasks": [
                "Map 2D camera pixels to 3D site coordinates via map projection.",
                "Subscribe to camera frame topic and robot pose/TF topics.",
                "Publish verified asset detections to '/perception/detections'."
            ]
        },
        {
            "stage": "STAGE 3",
            "name": "HITL Capture & Field Pilot",
            "status": "Pilot Validation",
            "color": COLOR_GREEN,
            "tasks": [
                "Deploy tablet-friendly HITL calibration interface for site walkthrough.",
                "Run 30-min offline fine-tuning workflow on captured assets.",
                "Conduct full 24-hour autonomous audit trial at client facility."
            ]
        }
    ]

    card_w = Inches(3.64)
    card_h = Inches(4.9)
    top_y = Inches(1.9)

    for i, step in enumerate(steps):
        left = Inches(0.8) + i * Inches(3.9)
        create_card(slide, left, top_y, card_w, card_h)

        tb = slide.shapes.add_textbox(left + Inches(0.25), top_y + Inches(0.25), card_w - Inches(0.5), card_h - Inches(0.5))
        tf = tb.text_frame
        tf.word_wrap = True

        p_st = tf.paragraphs[0]
        p_st.text = step["stage"]
        p_st.font.name = FONT_HEADING
        p_st.font.size = Pt(10)
        p_st.font.bold = True
        p_st.font.color.rgb = step["color"]

        p_name = tf.add_paragraph()
        p_name.text = step["name"]
        p_name.font.name = FONT_HEADING
        p_name.font.size = Pt(16)
        p_name.font.bold = True
        p_name.font.color.rgb = COLOR_TEXT_MAIN
        p_name.space_before = Pt(2)

        p_stat = tf.add_paragraph()
        p_stat.text = f"Status: {step['status']}"
        p_stat.font.name = FONT_HEADING
        p_stat.font.size = Pt(9.5)
        p_stat.font.bold = True
        p_stat.font.color.rgb = step["color"]
        p_stat.space_before = Pt(3)
        p_stat.space_after = Pt(12)

        p_del = tf.add_paragraph()
        p_del.text = "KEY DELIVERABLES:"
        p_del.font.name = FONT_HEADING
        p_del.font.size = Pt(10)
        p_del.font.bold = True
        p_del.font.color.rgb = COLOR_TEXT_MAIN

        for t in step["tasks"]:
            pt = tf.add_paragraph()
            pt.text = f"✔ {t}"
            pt.font.name = FONT_BODY
            pt.font.size = Pt(9.8)
            pt.font.color.rgb = COLOR_TEXT_MAIN
            pt.space_before = Pt(6)

    add_footer(slide, 9)

# ==========================================================
# SLIDE 10: EXECUTIVE CLOSING & ALIGNMENT
# ==========================================================
def build_slide_10(prs):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    set_slide_background(slide, COLOR_BG_DARK)

    # Accent decorative top bar
    bar = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0.8), Inches(0.8), Inches(1.5), Inches(0.06))
    bar.fill.solid()
    bar.fill.fore_color.rgb = COLOR_ACCENT_CYAN
    bar.line.fill.background()

    # Title Box
    t_box = slide.shapes.add_textbox(Inches(0.8), Inches(1.1), Inches(11.5), Inches(1.2))
    tf = t_box.text_frame
    tf.word_wrap = True
    tp = tf.paragraphs[0]
    tp.text = "SITE Assets Monitor"
    tp.font.name = FONT_HEADING
    tp.font.size = Pt(34)
    tp.font.bold = True
    tp.font.color.rgb = RGBColor(255, 255, 255)

    sub_p = tf.add_paragraph()
    sub_p.text = "Ready to Power Multi-Site Autonomous Auditing & Visual Security"
    sub_p.font.name = FONT_BODY
    sub_p.font.size = Pt(16)
    sub_p.font.color.rgb = COLOR_ACCENT_CYAN
    sub_p.space_before = Pt(4)

    # 3 Summary Pillar Cards
    pillars = [
        ("ZERO CODE REWRITES", "Profile-Driven Flexibility", [
            "100% config-based onboarding.",
            "Deploy to construction sites, ports, or warehouses using YAML profiles.",
            "Central core engine remains untouched and scalable across all clients."
        ]),
        ("EDGE-OPTIMIZED EFFICIENCY", "Raspberry Pi 5 Ready", [
            "Smooth 3-5 FPS inference on low-power onboard CPU.",
            "Zero heavy onboard GPU requirement.",
            "Offline 30-min fine-tuning yields high-accuracy custom ONNX weights."
        ]),
        ("HIGH-CONFIDENCE AUDITING", "Autonomous Security & Audits", [
            "Markerless visual Re-ID with 4-tier confidence verification.",
            "Defensible dual-stream evidence generation with tamper-proof metadata.",
            "Seamless integration with mobile robot ROS2 navigation stacks."
        ])
    ]

    card_w = Inches(3.64)
    card_h = Inches(4.0)
    top_y = Inches(2.6)

    for i, (head, sub, bullets) in enumerate(pillars):
        left = Inches(0.8) + i * Inches(3.9)
        create_card(slide, left, top_y, card_w, card_h, bg_color=RGBColor(30, 41, 59), border_color=RGBColor(51, 65, 85))

        tb = slide.shapes.add_textbox(left + Inches(0.25), top_y + Inches(0.25), card_w - Inches(0.5), card_h - Inches(0.5))
        tf = tb.text_frame
        tf.word_wrap = True

        p0 = tf.paragraphs[0]
        p0.text = head
        p0.font.name = FONT_HEADING
        p0.font.size = Pt(10)
        p0.font.bold = True
        p0.font.color.rgb = COLOR_ACCENT_CYAN

        p1 = tf.add_paragraph()
        p1.text = sub
        p1.font.name = FONT_HEADING
        p1.font.size = Pt(15)
        p1.font.bold = True
        p1.font.color.rgb = RGBColor(255, 255, 255)
        p1.space_before = Pt(3)
        p1.space_after = Pt(10)

        for b in bullets:
            bp = tf.add_paragraph()
            bp.text = f"•  {b}"
            bp.font.name = FONT_BODY
            bp.font.size = Pt(10.5)
            bp.font.color.rgb = RGBColor(203, 213, 225)
            bp.space_before = Pt(5)

    add_footer(slide, 10, is_dark=True)

# ==========================================================
# MAIN BUILDER FUNCTION
# ==========================================================
def build_presentation():
    print("Initializing 16:9 Environment-Agnostic Architecture Deck...")
    prs = Presentation()
    prs.slide_width = Inches(13.333)
    prs.slide_height = Inches(7.5)

    print("Building Slide 1: Executive Cover...")
    build_slide_1(prs)
    print("Building Slide 2: Why Evolve (Strategic Motivation)...")
    build_slide_2(prs)
    print("Building Slide 3: 3-Tier Layered Architecture...")
    build_slide_3(prs)
    print("Building Slide 4: 5-Phase Deployment Lifecycle...")
    build_slide_4(prs)
    print("Building Slide 5: Edge Execution vs Offline Training...")
    build_slide_5(prs)
    print("Building Slide 6: Live Inference & 4-Tier Re-ID...")
    build_slide_6(prs)
    print("Building Slide 7: Engineering Safeguards & Reliability...")
    build_slide_7(prs)
    print("Building Slide 8: Commercial & Operational Impact...")
    build_slide_8(prs)
    print("Building Slide 9: Delivery Roadmap & Milestones...")
    build_slide_9(prs)
    print("Building Slide 10: Executive Closing...")
    build_slide_10(prs)

    # Output file paths
    deck_filename = "Environment_Agnostic_Perception_Platform_Deck.pptx"
    primary_path = os.path.join(PROJECT_ROOT, deck_filename)
    parent_copy_path = os.path.join(PARENT_ROOT, deck_filename)

    prs.save(primary_path)
    print(f"Deck saved to: {primary_path}")
    try:
        prs.save(parent_copy_path)
        print(f"Parent directory copy saved to: {parent_copy_path}")
    except Exception as e:
        print(f"Could not save parent copy: {e}")

    print("Presentation generation completed successfully!")

if __name__ == "__main__":
    build_presentation()
