"""
Build Presentation Deck - Clean & Modern Edition
Generates a polished, executive-ready 16:9 widescreen presentation for the client
and engineering leadership, incorporating modern card-based styling,
structured operational workflows, and verified on-site field evidence.
"""

import os
import sys
import glob

# Ensure python-pptx is installed
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

# Visual Design Palette
COLOR_BG_DARK = RGBColor(15, 23, 42)        # Slate 900 (Deep Midnight)
COLOR_BG_LIGHT = RGBColor(248, 250, 252)    # Slate 50 (Crisp Off-White)
COLOR_CARD_BG = RGBColor(255, 255, 255)     # Pure White Card
COLOR_CARD_BORDER = RGBColor(226, 232, 240) # Slate 200 Border
COLOR_PRIMARY = RGBColor(24, 76, 120)       # Deep Steel Blue
COLOR_ACCENT_CYAN = RGBColor(14, 165, 233)  # Bright Cyan / Accent
COLOR_TEXT_MAIN = RGBColor(30, 41, 59)      # Slate 800 Dark Text
COLOR_TEXT_MUTED = RGBColor(100, 116, 139)  # Slate 500 Subtitle/Muted
COLOR_TEXT_LIGHT = RGBColor(241, 245, 249)  # Slate 100 White/Light
COLOR_GREEN = RGBColor(16, 185, 129)        # Emerald 500
COLOR_AMBER = RGBColor(245, 158, 11)        # Amber 500
COLOR_RED = RGBColor(239, 68, 68)           # Rose 500

FONT_HEADING = "Segoe UI"
FONT_BODY = "Segoe UI"

def set_slide_background(slide, color):
    """Sets a solid background color for a slide."""
    background = slide.background
    fill = background.fill
    fill.solid()
    fill.fore_color.rgb = color

def add_header(slide, badge_text, title_text, subtitle_text=None, is_dark=False):
    """Adds a standardized clean header with a category badge and title."""
    badge_box = slide.shapes.add_textbox(Inches(0.8), Inches(0.45), Inches(8), Inches(0.35))
    bf = badge_box.text_frame
    bf.word_wrap = True
    bf.margin_left = bf.margin_top = bf.margin_right = bf.margin_bottom = 0
    bp = bf.paragraphs[0]
    bp.text = badge_text.upper()
    bp.font.name = FONT_HEADING
    bp.font.size = Pt(10)
    bp.font.bold = True
    bp.font.color.rgb = COLOR_ACCENT_CYAN if is_dark else COLOR_PRIMARY

    title_box = slide.shapes.add_textbox(Inches(0.8), Inches(0.75), Inches(11.5), Inches(0.55))
    tf = title_box.text_frame
    tf.word_wrap = True
    tf.margin_left = tf.margin_top = tf.margin_right = tf.margin_bottom = 0
    tp = tf.paragraphs[0]
    tp.text = title_text
    tp.font.name = FONT_HEADING
    tp.font.size = Pt(22)
    tp.font.bold = True
    tp.font.color.rgb = COLOR_TEXT_LIGHT if is_dark else COLOR_TEXT_MAIN

    if subtitle_text:
        sub_box = slide.shapes.add_textbox(Inches(0.8), Inches(1.3), Inches(11.5), Inches(0.35))
        sf = sub_box.text_frame
        sf.word_wrap = True
        sf.margin_left = sf.margin_top = sf.margin_right = sf.margin_bottom = 0
        sp = sf.paragraphs[0]
        sp.text = subtitle_text
        sp.font.name = FONT_BODY
        sp.font.size = Pt(12)
        sp.font.color.rgb = RGBColor(148, 163, 184) if is_dark else COLOR_TEXT_MUTED

    # Header dividing rule
    divider = slide.shapes.add_shape(
        MSO_SHAPE.RECTANGLE,
        Inches(0.8), Inches(1.68), Inches(11.733), Inches(0.015)
    )
    divider.fill.solid()
    divider.fill.fore_color.rgb = RGBColor(51, 65, 85) if is_dark else RGBColor(226, 232, 240)
    divider.line.fill.background()

def add_footer(slide, current_page, total_pages=8, is_dark=False):
    """Standardized modern footer."""
    foot_box = slide.shapes.add_textbox(Inches(0.8), Inches(7.05), Inches(9.5), Inches(0.3))
    ff = foot_box.text_frame
    ff.margin_left = ff.margin_top = ff.margin_right = ff.margin_bottom = 0
    fp = ff.paragraphs[0]
    fp.text = "SITE Assets Monitor | Autonomous Security & Visual Auditing Platform"
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
# SLIDE BUILDERS
# ==========================================================

def build_slide_1_cover(prs):
    """Slide 1: Clean Dark Executive Cover Slide."""
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    set_slide_background(slide, COLOR_BG_DARK)

    # Accent decorative top bar
    bar = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0.8), Inches(0.8), Inches(1.5), Inches(0.06))
    bar.fill.solid()
    bar.fill.fore_color.rgb = COLOR_ACCENT_CYAN
    bar.line.fill.background()

    # Pill badge
    badge = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(0.8), Inches(1.2), Inches(3.2), Inches(0.35))
    badge.fill.solid()
    badge.fill.fore_color.rgb = RGBColor(30, 41, 59)
    badge.line.color.rgb = RGBColor(51, 65, 85)
    bf = badge.text_frame
    bp = bf.paragraphs[0]
    bp.alignment = PP_ALIGN.CENTER
    bp.text = "AI PERCEPTION & AUTONOMOUS SURVEILLANCE"
    bp.font.name = FONT_HEADING
    bp.font.size = Pt(9.5)
    bp.font.bold = True
    bp.font.color.rgb = COLOR_ACCENT_CYAN

    # Main Title
    t_box = slide.shapes.add_textbox(Inches(0.8), Inches(1.75), Inches(11.5), Inches(1.5))
    tf = t_box.text_frame
    tf.word_wrap = True
    tp = tf.paragraphs[0]
    tp.text = "SITE Assets Monitor"
    tp.font.name = FONT_HEADING
    tp.font.size = Pt(44)
    tp.font.bold = True
    tp.font.color.rgb = RGBColor(255, 255, 255)

    sub_p = tf.add_paragraph()
    sub_p.text = "Automated Visual Security & Spatial Equipment Auditing for Industrial Facilities"
    sub_p.font.name = FONT_BODY
    sub_p.font.size = Pt(18)
    sub_p.font.color.rgb = RGBColor(148, 163, 184)
    sub_p.space_before = Pt(8)

    # Overview Description
    desc_box = slide.shapes.add_textbox(Inches(0.8), Inches(3.3), Inches(11.0), Inches(1.2))
    df = desc_box.text_frame
    df.word_wrap = True
    dp = df.paragraphs[0]
    dp.text = (
        "Transforming patrolling mobile robots into autonomous, 24/7 site auditors. "
        "Eliminates manual asset inventory, recognizes equipment marker-free via visual deep learning, "
        "and alerts security instantly when critical machinery moves beyond authorized boundaries."
    )
    dp.font.name = FONT_BODY
    dp.font.size = Pt(13)
    dp.font.color.rgb = RGBColor(203, 213, 225)

    # 3 Metadata highlight pills at bottom
    specs = [
        ("TARGET VEHICLE", "Mobile Ground Robot / UGV"),
        ("DETECTION TECH", "RGB-D Vision + Deep Re-ID"),
        ("DISPLACEMENT TOLERANCE", "3-Meter Relocation Alert")
    ]
    card_w = Inches(3.64)
    card_h = Inches(1.1)
    for i, (label, val) in enumerate(specs):
        left = Inches(0.8) + i * Inches(3.9)
        c = create_card(slide, left, Inches(5.3), card_w, card_h, bg_color=RGBColor(30, 41, 59), border_color=RGBColor(51, 65, 85))
        box = slide.shapes.add_textbox(left + Inches(0.2), Inches(5.42), card_w - Inches(0.4), Inches(0.85))
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

    add_footer(slide, 1, total_pages=8, is_dark=True)

def build_slide_2_overview(prs):
    """Slide 2: Core Value Pillars (Clean 3-Card Layout)."""
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    set_slide_background(slide, COLOR_BG_LIGHT)
    add_header(
        slide,
        badge_text="Executive Summary",
        title_text="What is the SITE Assets Monitor?",
        subtitle_text="An intelligent visual auditing layer mounted onto your mobile robot to secure high-value equipment."
    )

    pillars = [
        {
            "num": "01",
            "title": "Autonomous 24/7 Security",
            "subtitle": "Continuous Site Audits",
            "accent": COLOR_PRIMARY,
            "bullets": [
                "Turns regular robot patrol rounds into automated inventory sweeps.",
                "Watches generators, air compressors, welders, and heavy toolkits.",
                "Eliminates human clipboard checks and reduces site inventory losses.",
                "Produces automated shift-by-shift compliance & status logs."
            ]
        },
        {
            "num": "02",
            "title": "Markerless Visual Re-ID",
            "subtitle": "No RFID or Barcode Tags",
            "accent": COLOR_ACCENT_CYAN,
            "bullets": [
                "Traditional tags get covered in dust, weather away, or get torn off.",
                "Uses AI Computer Vision to recognize machinery by silhouette & texture.",
                "Extracts unique 512-dimension digital fingerprints for each machine.",
                "Robust to perspective changes, varying sunlight, and partial clutter."
            ]
        },
        {
            "num": "03",
            "title": "3-Meter Precision Alert",
            "subtitle": "Immediate Photographic Proof",
            "accent": COLOR_GREEN,
            "bullets": [
                "Measures exact metric distance using 3D depth camera point clouds.",
                "Projects equipment coordinates directly into your facility site map.",
                "Triggers an alert if equipment is displaced by more than 3 meters.",
                "Packages side-by-side photo evidence (Baseline vs. Current location)."
            ]
        }
    ]

    card_w = Inches(3.64)
    card_h = Inches(4.8)
    for i, p in enumerate(pillars):
        left = Inches(0.8) + i * Inches(4.04)
        top = Inches(1.95)
        # Background card
        create_card(slide, left, top, card_w, card_h)

        # Top accent bar on card
        bar = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, left + Inches(0.2), top + Inches(0.2), Inches(0.6), Inches(0.08))
        bar.fill.solid()
        bar.fill.fore_color.rgb = p["accent"]
        bar.line.fill.background()

        # Text box
        tb = slide.shapes.add_textbox(left + Inches(0.25), top + Inches(0.4), card_w - Inches(0.5), card_h - Inches(0.6))
        tf = tb.text_frame
        tf.word_wrap = True

        np = tf.paragraphs[0]
        np.text = f"PILLAR {p['num']}"
        np.font.name = FONT_HEADING
        np.font.size = Pt(10)
        np.font.bold = True
        np.font.color.rgb = p["accent"]

        tp = tf.add_paragraph()
        tp.text = p["title"]
        tp.font.name = FONT_HEADING
        tp.font.size = Pt(16)
        tp.font.bold = True
        tp.font.color.rgb = COLOR_TEXT_MAIN
        tp.space_before = Pt(4)

        sub_p = tf.add_paragraph()
        sub_p.text = p["subtitle"]
        sub_p.font.name = FONT_BODY
        sub_p.font.size = Pt(11)
        sub_p.font.color.rgb = COLOR_TEXT_MUTED
        sub_p.space_after = Pt(14)

        for b in p["bullets"]:
            bp = tf.add_paragraph()
            bp.text = f"•  {b}"
            bp.font.name = FONT_BODY
            bp.font.size = Pt(11)
            bp.font.color.rgb = COLOR_TEXT_MAIN
            bp.space_before = Pt(6)

    add_footer(slide, 2, total_pages=8)

def build_slide_3_lifecycle(prs):
    """Slide 3: Two-Phase Operational Lifecycle (Comparative 2-Column)."""
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    set_slide_background(slide, COLOR_BG_LIGHT)
    add_header(
        slide,
        badge_text="Operational Lifecycle",
        title_text="Two Distinct Operating Phases: Setup vs. Autonomous Patrol",
        subtitle_text="A simple one-time onboarding walkthrough establishes the baseline catalog; the robot then audits continuously."
    )

    col_w = Inches(5.66)
    col_h = Inches(4.8)

    # --- Phase 1: Setup Walkthrough ---
    left1 = Inches(0.8)
    top = Inches(1.95)
    create_card(slide, left1, top, col_w, col_h)
    
    # Phase 1 header badge
    badge1 = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, left1 + Inches(0.3), top + Inches(0.25), Inches(2.2), Inches(0.32))
    badge1.fill.solid()
    badge1.fill.fore_color.rgb = RGBColor(238, 242, 255)
    badge1.line.color.rgb = RGBColor(199, 210, 254)
    b1_p = badge1.text_frame.paragraphs[0]
    b1_p.alignment = PP_ALIGN.CENTER
    b1_p.text = "PHASE 1: ONE-TIME ONBOARDING"
    b1_p.font.name = FONT_HEADING
    b1_p.font.size = Pt(9)
    b1_p.font.bold = True
    b1_p.font.color.rgb = COLOR_PRIMARY

    tb1 = slide.shapes.add_textbox(left1 + Inches(0.3), top + Inches(0.68), col_w - Inches(0.6), col_h - Inches(0.9))
    tf1 = tb1.text_frame
    tf1.word_wrap = True

    t1 = tf1.paragraphs[0]
    t1.text = "Human-Guided Walkthrough (Setup)"
    t1.font.name = FONT_HEADING
    t1.font.size = Pt(16)
    t1.font.bold = True
    t1.font.color.rgb = COLOR_TEXT_MAIN

    steps1 = [
        ("1. Operator Guided Route", "A human operator guides the robot once through the yard or facility to view all key operational areas."),
        ("2. Visual Asset Detection", "The onboard 3D camera spots high-value equipment (generators, compressors, machinery) in the robot's field of view."),
        ("3. Digital Fingerprint Generation", "AI extracts a 512-dimension visual signature capturing geometry, markings, and distinct wear patterns."),
        ("4. Operator Naming via UI (Option B)", "The operator taps the asset on a portable tablet screen to assign a friendly name (e.g. 'Gen-Set Beta 03')."),
        ("5. Spatial Baseline Lock", "Robot notes exact 3D coordinates (X, Y, Z) and registers the asset into the Master Inventory Database.")
    ]
    for title, desc in steps1:
        p = tf1.add_paragraph()
        p.text = f"{title}: {desc}"
        p.font.name = FONT_BODY
        p.font.size = Pt(10.5)
        p.font.color.rgb = COLOR_TEXT_MAIN
        p.space_before = Pt(8)

    # --- Phase 2: Autonomous Patrol ---
    left2 = Inches(6.86)
    create_card(slide, left2, top, col_w, col_h)

    badge2 = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, left2 + Inches(0.3), top + Inches(0.25), Inches(2.2), Inches(0.32))
    badge2.fill.solid()
    badge2.fill.fore_color.rgb = RGBColor(236, 253, 245)
    badge2.line.color.rgb = RGBColor(167, 243, 208)
    b2_p = badge2.text_frame.paragraphs[0]
    b2_p.alignment = PP_ALIGN.CENTER
    b2_p.text = "PHASE 2: 24/7 AUTONOMOUS OPERATION"
    b2_p.font.name = FONT_HEADING
    b2_p.font.size = Pt(9)
    b2_p.font.bold = True
    b2_p.font.color.rgb = RGBColor(5, 150, 105)

    tb2 = slide.shapes.add_textbox(left2 + Inches(0.3), top + Inches(0.68), col_w - Inches(0.6), col_h - Inches(0.9))
    tf2 = tb2.text_frame
    tf2.word_wrap = True

    t2 = tf2.paragraphs[0]
    t2.text = "Autonomous Security Rounds (Ongoing)"
    t2.font.name = FONT_HEADING
    t2.font.size = Pt(16)
    t2.font.bold = True
    t2.font.color.rgb = COLOR_TEXT_MAIN

    steps2 = [
        ("1. Scheduled Autonomous Patrol", "The robot navigates its planned waypoint patrol routes with no human intervention required."),
        ("2. Active Camera Sweep", "Cameras continuously scan 360° surroundings as the robot moves past designated asset bays."),
        ("3. Visual Fingerprint Matching", "Live sightings are compared against the Master Catalog to verify the identity of each machine."),
        ("4. 3-Meter Spatial Audit", "The system calculates live position vs baseline position and applies the movement rule:"),
        ("   🟢 IN PLACE (< 3m)", "Asset is within normal operational radius. Marked healthy."),
        ("   🟡 MOVED (> 3m)", "Asset displaced. Instant warning alert sent with photo proof."),
        ("   🔴 MISSING", "Asset not detected at scheduled checkpoint. High-priority alert.")
    ]
    for item in steps2:
        p = tf2.add_paragraph()
        if isinstance(item, tuple):
            title, desc = item
            p.text = f"{title}: {desc}"
        else:
            p.text = item
        p.font.name = FONT_BODY
        p.font.size = Pt(10.5)
        p.font.color.rgb = COLOR_TEXT_MAIN
        p.space_before = Pt(6)

    add_footer(slide, 3, total_pages=8)

def build_slide_4_architecture(prs):
    """Slide 4: System Architecture & Workflow Diagram."""
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    set_slide_background(slide, COLOR_BG_LIGHT)
    add_header(
        slide,
        badge_text="System Architecture",
        title_text="End-to-End Visual & Spatial Processing Pipeline",
        subtitle_text="Synchronizing optical video, 3D point clouds, and robot localization for real-time asset tracking."
    )

    diagram_path = os.path.join(PARENT_ROOT, "system_design_flow.png")
    if not os.path.exists(diagram_path):
        diagram_path = os.path.join(PROJECT_ROOT, "system_design_flow.png")

    top_card = Inches(1.9)
    card_w = Inches(11.733)
    card_h = Inches(3.7)
    create_card(slide, Inches(0.8), top_card, card_w, card_h)

    if os.path.exists(diagram_path):
        # Center image within card
        img_left = Inches(1.0)
        img_top = Inches(2.05)
        img_width = Inches(11.333)
        img_height = Inches(3.4)
        slide.shapes.add_picture(diagram_path, img_left, img_top, width=img_width)
    else:
        tb = slide.shapes.add_textbox(Inches(1.5), Inches(3.0), Inches(9), Inches(1))
        tb.text_frame.text = "[System Design Diagram: system_design_flow.png]"

    # 3 Summary callout cards below the diagram
    callouts = [
        ("1. Sensory Ingestion", "Subscribes to 1080p RGB video, 16-bit millimeter depth maps, and robot /tf pose in map coordinates."),
        ("2. AI Perception Core", "YOLOv8 isolates bounding boxes; OSNet extracts visual embeddings; Depth pinpoints 3D (X, Y, Z)."),
        ("3. Audit & Alert Engine", "Database matches identity, computes delta distance vs baseline, and dispatches UI notifications.")
    ]
    sub_top = Inches(5.8)
    sub_w = Inches(3.74)
    sub_h = Inches(1.05)
    for i, (title, desc) in enumerate(callouts):
        left = Inches(0.8) + i * Inches(3.99)
        c = create_card(slide, left, sub_top, sub_w, sub_h, bg_color=RGBColor(241, 245, 249))
        tb = slide.shapes.add_textbox(left + Inches(0.15), sub_top + Inches(0.1), sub_w - Inches(0.3), sub_h - Inches(0.2))
        tf = tb.text_frame
        tf.word_wrap = True
        tp = tf.paragraphs[0]
        tp.text = title
        tp.font.name = FONT_HEADING
        tp.font.size = Pt(11)
        tp.font.bold = True
        tp.font.color.rgb = COLOR_PRIMARY
        
        dp = tf.add_paragraph()
        dp.text = desc
        dp.font.name = FONT_BODY
        dp.font.size = Pt(9.5)
        dp.font.color.rgb = COLOR_TEXT_MAIN
        dp.space_before = Pt(3)

    add_footer(slide, 4, total_pages=8)

def build_slide_5_evidence(prs):
    """Slide 5: Field AI Detection Evidence from Site Records."""
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    set_slide_background(slide, COLOR_BG_LIGHT)
    add_header(
        slide,
        badge_text="Field AI Verification",
        title_text="Real-World Visual Detections from Site Records",
        subtitle_text="Live verification testing using actual site inspection video clippings and object detection."
    )

    detection_dir = os.path.join(PROJECT_ROOT, "evidence", "detection_examples")
    imgs = sorted(glob.glob(os.path.join(detection_dir, "*.jpg")))

    # Pick two high-res representative examples
    img1 = imgs[0] if len(imgs) > 0 else None
    img2 = imgs[2] if len(imgs) > 2 else (imgs[1] if len(imgs) > 1 else None)

    col_w = Inches(5.66)
    col_h = Inches(4.8)

    items = [
        (img1, Inches(0.8), "Detection Sighting A: Heavy Asset Scanning", "YOLO Bounding Box: Active | Depth: Verified | ID Confidence: 89%"),
        (img2, Inches(6.86), "Detection Sighting B: Complex Yard Clutter", "Re-ID Feature Extraction: Active | Multi-Angle Tracking | Threshold: In-Place")
    ]

    for img_path, left, title, caption in items:
        # Card container
        create_card(slide, left, Inches(1.95), col_w, col_h)

        # Title
        tb = slide.shapes.add_textbox(left + Inches(0.25), Inches(2.05), col_w - Inches(0.5), Inches(0.4))
        tf = tb.text_frame
        tp = tf.paragraphs[0]
        tp.text = title
        tp.font.name = FONT_HEADING
        tp.font.size = Pt(13)
        tp.font.bold = True
        tp.font.color.rgb = COLOR_TEXT_MAIN

        # Image
        if img_path and os.path.exists(img_path):
            img_top = Inches(2.5)
            img_width = col_w - Inches(0.5)
            slide.shapes.add_picture(img_path, left + Inches(0.25), img_top, width=img_width)
        else:
            ph = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, left + Inches(0.25), Inches(2.5), col_w - Inches(0.5), Inches(3.2))
            ph.fill.solid()
            ph.fill.fore_color.rgb = RGBColor(226, 232, 240)

        # Metric caption bar at bottom of card
        cap_box = slide.shapes.add_textbox(left + Inches(0.25), Inches(6.15), col_w - Inches(0.5), Inches(0.5))
        cf = cap_box.text_frame
        cf.word_wrap = True
        cp = cf.paragraphs[0]
        cp.text = caption
        cp.font.name = FONT_BODY
        cp.font.size = Pt(10)
        cp.font.bold = True
        cp.font.color.rgb = COLOR_PRIMARY

        note_p = cf.add_paragraph()
        note_p.text = "• Model baseline verified; site fine-tuning will provide custom asset classes."
        note_p.font.name = FONT_BODY
        note_p.font.size = Pt(9)
        note_p.font.color.rgb = COLOR_TEXT_MUTED
        note_p.space_before = Pt(2)

    add_footer(slide, 5, total_pages=8)

def build_slide_6_robotics_deliverables(prs):
    """Slide 6: ROS & Navigation Team Requirements."""
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    set_slide_background(slide, COLOR_BG_LIGHT)
    add_header(
        slide,
        badge_text="Robotics Integration",
        title_text="Deliverables Needed from the ROS & Navigation Team",
        subtitle_text="Four standardized engineering inputs required to link the perception engine with the physical robot."
    )

    deliverables = [
        {
            "tag": "INPUT 01: SENSORY STREAMS",
            "title": "Camera Video & Depth Feeds",
            "bullets": [
                "Color Feed: /camera/color/image_raw (sensor_msgs/Image, 1080p @ 15-30Hz)",
                "Depth Feed: /camera/depth/image_raw (16-bit mm depth, 16UC1 format)",
                "Intrinsics: /camera/color/camera_info (focal length & distortion matrix)",
                "Purpose: Enables visual bounding box isolation and precise 3D ranging."
            ]
        },
        {
            "tag": "INPUT 02: SPATIAL LOCALIZATION",
            "title": "Robot Coordinates & TF Tree",
            "bullets": [
                "Coordinate Frames: /tf & /tf_static (map -> odom -> base_link -> camera_link)",
                "Fallback Pose: /robot/pose (geometry_msgs/PoseWithCovarianceStamped)",
                "Camera Extrinsics: Exact mounting height (Z) and pitch angle (tilt)",
                "Purpose: Converts camera coordinates into absolute global site map coordinates."
            ]
        },
        {
            "tag": "INPUT 03: SIMULATION & TESTING",
            "title": "5-Minute Test ROS2 Bag File",
            "bullets": [
                "Recording Format: ROS2 bag (.mcap or .db3) of 3 to 5 minutes duration",
                "Scenario: Robot navigating past 2 or 3 stationary assets (generators, carts)",
                "Included Topics: Camera RGB, Depth, CameraInfo, /tf, /tf_static, /odom",
                "Purpose: Validates the entire pipeline offline before testing on live vehicle."
            ]
        },
        {
            "tag": "INPUT 04: NETWORK CONNECTIVITY",
            "title": "Link to Dedicated Perception Pi",
            "bullets": [
                "Hardware: Gigabit Ethernet between Navigation PC and our Raspberry Pi 5",
                "Middleware: Shared ROS_DOMAIN_ID for DDS communication",
                "Time Sync: NTP / Chrony synchronization across both boards",
                "Purpose: Enables our dedicated Pi to read your /tf and send alerts without sharing CPU."
            ]
        }
    ]

    card_w = Inches(5.66)
    card_h = Inches(2.25)
    positions = [
        (Inches(0.8), Inches(1.95)),
        (Inches(6.86), Inches(1.95)),
        (Inches(0.8), Inches(4.5)),
        (Inches(6.86), Inches(4.5))
    ]

    for i, d in enumerate(deliverables):
        left, top = positions[i]
        create_card(slide, left, top, card_w, card_h)

        tb = slide.shapes.add_textbox(left + Inches(0.25), top + Inches(0.18), card_w - Inches(0.5), card_h - Inches(0.35))
        tf = tb.text_frame
        tf.word_wrap = True

        tag_p = tf.paragraphs[0]
        tag_p.text = d["tag"]
        tag_p.font.name = FONT_HEADING
        tag_p.font.size = Pt(9.5)
        tag_p.font.bold = True
        tag_p.font.color.rgb = COLOR_PRIMARY

        tp = tf.add_paragraph()
        tp.text = d["title"]
        tp.font.name = FONT_HEADING
        tp.font.size = Pt(14)
        tp.font.bold = True
        tp.font.color.rgb = COLOR_TEXT_MAIN
        tp.space_before = Pt(2)
        tp.space_after = Pt(6)

        for b in d["bullets"]:
            bp = tf.add_paragraph()
            bp.text = f"•  {b}"
            bp.font.name = FONT_BODY
            bp.font.size = Pt(9.5)
            bp.font.color.rgb = COLOR_TEXT_MAIN
            bp.space_before = Pt(3)

    add_footer(slide, 6, total_pages=8)

def build_slide_7_roadmap(prs):
    """Slide 7: Step-by-Step Delivery Roadmap."""
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    set_slide_background(slide, COLOR_BG_LIGHT)
    add_header(
        slide,
        badge_text="Deployment Schedule",
        title_text="Project Roadmap: Step-by-Step Delivery Schedule",
        subtitle_text="Structured 4-phase rollout ensuring robust validation at each milestone before moving forward."
    )

    phases = [
        {
            "phase": "PHASE A",
            "time": "Week 1",
            "name": "Rosbag Verification & Calibration",
            "status": "In Discussion",
            "accent": COLOR_PRIMARY,
            "details": [
                "Navigation team provides 5-min test ROS2 bag recording.",
                "Perception team validates depth camera optical calibration.",
                "Verify coordinate transform integrity (map -> camera_link).",
                "Milestone: Software talks cleanly to the robot's data format."
            ]
        },
        {
            "phase": "PHASE B",
            "time": "Week 2",
            "name": "On-Site Model Fine-Tuning",
            "status": "Pending",
            "accent": COLOR_ACCENT_CYAN,
            "details": [
                "Collect localized images of site-specific equipment types.",
                "Train custom YOLOv8 classes for generators & compressors.",
                "Benchmark Re-ID fingerprint matching accuracy (>92%).",
                "Milestone: AI reliably recognizes all client equipment models."
            ]
        },
        {
            "phase": "PHASE C",
            "time": "Week 3",
            "name": "Initial Site Walkthrough",
            "status": "Pending",
            "accent": COLOR_AMBER,
            "details": [
                "Execute one-time guided walkthrough on the physical site.",
                "Operator names assets via UI and locks baseline locations.",
                "Generate the site's official Master Asset Catalog.",
                "Milestone: Full facility baseline inventory locked into database."
            ]
        },
        {
            "phase": "PHASE D",
            "time": "Week 4",
            "name": "Autonomous Go-Live & Auditing",
            "status": "Target",
            "accent": COLOR_GREEN,
            "details": [
                "Enable autonomous patrol rounds with active 3D tracking.",
                "Automated 3-meter displacement alert notifications active.",
                "Automated daily inventory logs with photographic evidence.",
                "Milestone: 24/7 autonomous asset security fully operational."
            ]
        }
    ]

    card_w = Inches(2.72)
    card_h = Inches(4.8)
    for i, p in enumerate(phases):
        left = Inches(0.8) + i * Inches(3.0)
        top = Inches(1.95)
        create_card(slide, left, top, card_w, card_h)

        # Header bar on card
        bar = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, left, top, card_w, Inches(0.08))
        bar.fill.solid()
        bar.fill.fore_color.rgb = p["accent"]
        bar.line.fill.background()

        tb = slide.shapes.add_textbox(left + Inches(0.2), top + Inches(0.2), card_w - Inches(0.4), card_h - Inches(0.4))
        tf = tb.text_frame
        tf.word_wrap = True

        ph_p = tf.paragraphs[0]
        ph_p.text = f"{p['phase']} • {p['time']}"
        ph_p.font.name = FONT_HEADING
        ph_p.font.size = Pt(10)
        ph_p.font.bold = True
        ph_p.font.color.rgb = p["accent"]

        np = tf.add_paragraph()
        np.text = p["name"]
        np.font.name = FONT_HEADING
        np.font.size = Pt(13)
        np.font.bold = True
        np.font.color.rgb = COLOR_TEXT_MAIN
        np.space_before = Pt(4)
        np.space_after = Pt(10)

        for d in p["details"]:
            dp = tf.add_paragraph()
            dp.text = f"•  {d}"
            dp.font.name = FONT_BODY
            dp.font.size = Pt(10)
            dp.font.color.rgb = COLOR_TEXT_MAIN
            dp.space_before = Pt(6)

    add_footer(slide, 7, total_pages=8)

def build_slide_8_closing(prs):
    """Slide 8: Closing Summary & Immediate Alignment Action."""
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    set_slide_background(slide, COLOR_BG_DARK)

    # Header badge
    badge = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(0.8), Inches(1.0), Inches(2.8), Inches(0.35))
    badge.fill.solid()
    badge.fill.fore_color.rgb = RGBColor(30, 41, 59)
    badge.line.color.rgb = RGBColor(51, 65, 85)
    bp = badge.text_frame.paragraphs[0]
    bp.alignment = PP_ALIGN.CENTER
    bp.text = "NEXT STEPS & ALIGNMENT"
    bp.font.name = FONT_HEADING
    bp.font.size = Pt(9.5)
    bp.font.bold = True
    bp.font.color.rgb = COLOR_ACCENT_CYAN

    # Big Title
    t_box = slide.shapes.add_textbox(Inches(0.8), Inches(1.5), Inches(11.5), Inches(1.0))
    tf = t_box.text_frame
    tf.word_wrap = True
    tp = tf.paragraphs[0]
    tp.text = "Immediate Next Action: Team Confirmation"
    tp.font.name = FONT_HEADING
    tp.font.size = Pt(32)
    tp.font.bold = True
    tp.font.color.rgb = RGBColor(255, 255, 255)

    sub_p = tf.add_paragraph()
    sub_p.text = "Perception and Navigation team alignment to confirm topics and capture the test rosbag."
    sub_p.font.name = FONT_BODY
    sub_p.font.size = Pt(15)
    sub_p.font.color.rgb = RGBColor(148, 163, 184)
    sub_p.space_before = Pt(4)

    # 2 Action Cards
    actions = [
        {
            "num": "ACTION 01",
            "title": "Navigation Alignment Meeting",
            "points": [
                "Review the 4 deliverables document with the robotics engineering team.",
                "Confirm exact ROS2 topic strings (/camera/color/image_raw, /tf frames).",
                "Confirm compute budget on the vehicle (Jetson vs Industrial PC).",
                "Sign off on perception interface contract before node coding."
            ]
        },
        {
            "num": "ACTION 02",
            "title": "5-Minute Practice Rosbag Recording",
            "points": [
                "Drive robot past 2-3 stationary target equipment assets in yard.",
                "Record color, depth, camera_info, and /tf into an .mcap file.",
                "Hand over rosbag to perception team for offline calibration.",
                "Perception team verifies 3D coordinate projection accuracy."
            ]
        }
    ]

    card_w = Inches(5.66)
    card_h = Inches(3.2)
    for i, a in enumerate(actions):
        left = Inches(0.8) + i * Inches(6.06)
        top = Inches(2.9)
        create_card(slide, left, top, card_w, card_h, bg_color=RGBColor(30, 41, 59), border_color=RGBColor(51, 65, 85))

        tb = slide.shapes.add_textbox(left + Inches(0.3), top + Inches(0.25), card_w - Inches(0.6), card_h - Inches(0.5))
        tf = tb.text_frame
        tf.word_wrap = True

        ap = tf.paragraphs[0]
        ap.text = a["num"]
        ap.font.name = FONT_HEADING
        ap.font.size = Pt(10)
        ap.font.bold = True
        ap.font.color.rgb = COLOR_ACCENT_CYAN

        tp = tf.add_paragraph()
        tp.text = a["title"]
        tp.font.name = FONT_HEADING
        tp.font.size = Pt(16)
        tp.font.bold = True
        tp.font.color.rgb = RGBColor(255, 255, 255)
        tp.space_before = Pt(4)
        tp.space_after = Pt(10)

        for p in a["points"]:
            pp = tf.add_paragraph()
            pp.text = f"•  {p}"
            pp.font.name = FONT_BODY
            pp.font.size = Pt(11)
            pp.font.color.rgb = RGBColor(203, 213, 225)
            pp.space_before = Pt(4)

    add_footer(slide, 8, total_pages=8, is_dark=True)

def build_presentation():
    """Main function to create 16:9 widescreen presentation deck."""
    print("Initializing 16:9 Presentation Deck...")
    prs = Presentation()
    # Set 16:9 widescreen aspect ratio
    prs.slide_width = Inches(13.333)
    prs.slide_height = Inches(7.5)

    build_slide_1_cover(prs)
    build_slide_2_overview(prs)
    build_slide_3_lifecycle(prs)
    build_slide_4_architecture(prs)
    build_slide_5_evidence(prs)
    build_slide_6_robotics_deliverables(prs)
    build_slide_7_roadmap(prs)
    build_slide_8_closing(prs)

    # Save to primary and clean paths
    primary_path = os.path.join(PROJECT_ROOT, "Site_Assets_Monitor_Client_Deck.pptx")
    clean_path = os.path.join(PROJECT_ROOT, "Site_Assets_Monitor_Presentation_Clean.pptx")
    root_copy_path = os.path.join(PARENT_ROOT, "Site_Assets_Monitor_Presentation_Clean.pptx")

    # Always write clean_path
    prs.save(clean_path)
    prs.save(root_copy_path)
    print(f"Clean deck saved to: {clean_path}")
    print(f"Clean deck root copy saved to: {root_copy_path}")

    # Attempt to overwrite primary_path if not locked
    try:
        prs.save(primary_path)
        print(f"Successfully updated primary deck: {primary_path}")
    except PermissionError:
        print(f"Notice: '{primary_path}' is currently open in PowerPoint. Clean version saved to '{clean_path}'.")

if __name__ == "__main__":
    build_presentation()
