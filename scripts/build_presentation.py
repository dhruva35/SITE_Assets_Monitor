"""
Simple, non-complex PowerPoint presentation generator.
Focuses strictly on what Dhruva is building: The AI Vision System.
Clean, easy-to-read, 6 slides, human-friendly language.
"""

import os
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN
from pptx.enum.shapes import MSO_SHAPE

def create_simple_presentation(output_path):
    prs = Presentation()
    prs.slide_width = Inches(13.333)
    prs.slide_height = Inches(7.5)

    # Clean, modern, friendly color palette
    C_BG = RGBColor(248, 250, 252)        # Crisp Light Background #F8FAFC
    C_CARD = RGBColor(255, 255, 255)     # Pure White Card #FFFFFF
    C_BORDER = RGBColor(226, 232, 240)   # Light Border #E2E8F0
    C_TEXT_MAIN = RGBColor(15, 23, 42)   # Dark Slate #0F172A
    C_TEXT_MUTED = RGBColor(71, 85, 105) # Slate 600 #475569
    C_PRIMARY = RGBColor(37, 99, 235)    # Royal Blue #2563EB
    C_GREEN = RGBColor(16, 185, 129)     # Emerald Green #10B981
    C_AMBER = RGBColor(217, 119, 6)      # Amber #D97706

    blank_layout = prs.slide_layouts[6]

    def set_bg(slide, color=C_BG):
        bg = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, Inches(13.333), Inches(7.5))
        bg.fill.solid()
        bg.fill.fore_color.rgb = color
        bg.line.fill.background()
        return bg

    def add_header(slide, title, subtitle=None):
        # Blue accent dot / tag
        dot = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0.9), Inches(0.6), Inches(0.6), Inches(0.06))
        dot.fill.solid()
        dot.fill.fore_color.rgb = C_PRIMARY
        dot.line.fill.background()

        tb = slide.shapes.add_textbox(Inches(0.9), Inches(0.8), Inches(11.5), Inches(0.8))
        tf = tb.text_frame
        tf.word_wrap = True
        tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0

        p = tf.paragraphs[0]
        p.text = title
        p.font.size = Pt(26)
        p.font.bold = True
        p.font.color.rgb = C_TEXT_MAIN
        p.font.name = "Segoe UI"

        if subtitle:
            p_sub = tf.add_paragraph()
            p_sub.text = subtitle
            p_sub.font.size = Pt(13)
            p_sub.font.color.rgb = C_TEXT_MUTED
            p_sub.font.name = "Segoe UI"
            p_sub.space_before = Pt(4)

    def make_card(slide, left, top, width, height, bg_color=C_CARD, border_color=C_BORDER):
        card = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, left, top, width, height)
        card.fill.solid()
        card.fill.fore_color.rgb = bg_color
        card.line.color.rgb = border_color
        card.line.width = Pt(1.5)
        return card

    slides_with_notes = []

    # =========================================================
    # SLIDE 1: SIMPLE TITLE SLIDE
    # =========================================================
    s1 = prs.slides.add_slide(blank_layout)
    set_bg(s1, RGBColor(241, 245, 249))

    # Center card
    center_card = make_card(s1, Inches(1.5), Inches(1.5), Inches(10.333), Inches(4.5), bg_color=C_CARD)

    # Accent top strip on card
    strip = s1.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(1.5), Inches(1.5), Inches(10.333), Inches(0.1))
    strip.fill.solid()
    strip.fill.fore_color.rgb = C_PRIMARY
    strip.line.fill.background()

    tb_title = s1.shapes.add_textbox(Inches(2.0), Inches(2.2), Inches(9.3), Inches(2.0))
    tf_t = tb_title.text_frame
    tf_t.word_wrap = True

    p = tf_t.paragraphs[0]
    p.text = "Site Asset Vision System"
    p.font.size = Pt(36)
    p.font.bold = True
    p.font.color.rgb = C_TEXT_MAIN
    p.font.name = "Segoe UI"

    p_sub = tf_t.add_paragraph()
    p_sub.text = "AI Perception & Equipment Monitoring — Progress Update"
    p_sub.font.size = Pt(16)
    p_sub.font.color.rgb = C_PRIMARY
    p_sub.font.name = "Segoe UI"
    p_sub.space_before = Pt(6)

    # Divider line
    div = s1.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(2.0), Inches(3.8), Inches(9.3), Inches(0.02))
    div.fill.solid()
    div.fill.fore_color.rgb = C_BORDER
    div.line.fill.background()

    tb_info = s1.shapes.add_textbox(Inches(2.0), Inches(4.1), Inches(9.3), Inches(1.2))
    tf_info = tb_info.text_frame
    tf_info.word_wrap = True

    p_info = tf_info.paragraphs[0]
    p_info.text = "Prepared by: Dhruvaveer (AI Perception Engineer)"
    p_info.font.size = Pt(13)
    p_info.font.bold = True
    p_info.font.color.rgb = C_TEXT_MAIN
    p_info.font.name = "Segoe UI"

    p_stat = tf_info.add_paragraph()
    p_stat.text = "Status: Week 1 Core Vision System Complete & Tested  •  Ready for Re-ID"
    p_stat.font.size = Pt(12)
    p_stat.font.color.rgb = C_GREEN
    p_stat.font.name = "Segoe UI"
    p_stat.space_before = Pt(4)

    slides_with_notes.append((s1, (
        "Hi Biraj. Today I will give you a quick, simple update on the AI vision system I'm building for our site patrol robot. "
        "I'll show you what it does, what I've built and tested so far, the camera we chose, and the next steps."
    )))

    # =========================================================
    # SLIDE 2: WHAT THE SYSTEM DOES (SIMPLE 3 STEPS)
    # =========================================================
    s2 = prs.slides.add_slide(blank_layout)
    set_bg(s2)
    add_header(s2, "How the Vision System Works", "Three simple steps the camera performs as the vehicle drives around the site.")

    steps = [
        ("STEP 1: CHECK IMAGE", "Make Sure It's Clear",
         "The system checks each camera picture first. If the lens is blocked, too dark, or blurred from a bump, it skips it instead of making a wrong guess.", C_PRIMARY),
        ("STEP 2: DETECT", "Spot Site Equipment",
         "The AI scans the image and spots construction machinery like trucks, excavators, and cranes, drawing boxes around them with high accuracy.", C_GREEN),
        ("STEP 3: SAVE PROOF", "Record Time & Photos",
         "Whenever equipment is spotted, the system automatically saves a clean photo of the machine along with the time and location details.", C_AMBER)
    ]

    card_w = Inches(3.6)
    card_gap = Inches(0.36)
    start_x = Inches(0.9)

    for i, (tag, title, desc, col) in enumerate(steps):
        x = start_x + i * (card_w + card_gap)
        make_card(s2, x, Inches(2.1), card_w, Inches(4.5))

        # Top tag
        tb = s2.shapes.add_textbox(x + Inches(0.3), Inches(2.4), card_w - Inches(0.6), Inches(3.8))
        tf = tb.text_frame
        tf.word_wrap = True

        p1 = tf.paragraphs[0]
        p1.text = tag
        p1.font.size = Pt(11)
        p1.font.bold = True
        p1.font.color.rgb = col
        p1.font.name = "Segoe UI"

        p2 = tf.add_paragraph()
        p2.text = title
        p2.font.size = Pt(18)
        p2.font.bold = True
        p2.font.color.rgb = C_TEXT_MAIN
        p2.font.name = "Segoe UI"
        p2.space_before = Pt(6)

        p3 = tf.add_paragraph()
        p3.text = desc
        p3.font.size = Pt(12)
        p3.font.color.rgb = C_TEXT_MUTED
        p3.font.name = "Segoe UI"
        p3.space_before = Pt(14)

    slides_with_notes.append((s2, (
        "In simple terms, here is what my software does: First, it checks if the picture is good quality so we don't make mistakes in bad lighting. "
        "Second, it spots the construction machines. Third, it automatically saves a cropped photo and timestamp as proof. "
        "Everything runs directly on the vehicle's Raspberry Pi."
    )))

    # =========================================================
    # SLIDE 3: WHAT I HAVE BUILT SO FAR
    # =========================================================
    s3 = prs.slides.add_slide(blank_layout)
    set_bg(s3)
    add_header(s3, "What I Have Built So Far", "The foundation is fully built, configured, and verified.")

    items = [
        ("Image Quality Filter", "Rejects blurry or dark photos automatically so bad images don't produce false readings."),
        ("Custom AI Equipment Detector", "Trained specifically on heavy construction machinery (trucks, excavators, cranes, loaders)."),
        ("Automatic Evidence Logger", "Cuts out close-up photos of detected equipment and creates organized audit records."),
        ("Easy Configuration Settings", "All settings (camera settings, detection thresholds) are kept in simple files for easy adjustment."),
        ("25 Automated Tests Passing", "100% of my automated tests pass cleanly, proving the code is stable and reliable.")
    ]

    left_x = Inches(0.9)
    top_y = Inches(2.1)

    for i, (title, desc) in enumerate(items):
        y = top_y + i * Inches(0.92)
        make_card(s3, left_x, y, Inches(11.533), Inches(0.78))

        # Checkmark icon
        tb_chk = s3.shapes.add_textbox(left_x + Inches(0.2), y + Inches(0.18), Inches(0.5), Inches(0.4))
        p_chk = tb_chk.text_frame.paragraphs[0]
        p_chk.text = "✓"
        p_chk.font.size = Pt(16)
        p_chk.font.bold = True
        p_chk.font.color.rgb = C_GREEN

        tb = s3.shapes.add_textbox(left_x + Inches(0.75), y + Inches(0.12), Inches(10.5), Inches(0.55))
        tf = tb.text_frame
        tf.word_wrap = True

        p1 = tf.paragraphs[0]
        p1.text = title + " — "
        p1.font.size = Pt(13)
        p1.font.bold = True
        p1.font.color.rgb = C_TEXT_MAIN
        p1.font.name = "Segoe UI"

        run = p1.add_run()
        run.text = desc
        run.font.bold = False
        run.font.color.rgb = C_TEXT_MUTED

    slides_with_notes.append((s3, (
        "Here is what I've completed: I built the image quality filter, trained the custom detection AI for construction machinery, "
        "and built the evidence logger that cuts out close-up photos of detected assets. "
        "I also wrote 25 automated tests and all 25 are passing, meaning everything is working properly."
    )))

    # =========================================================
    # SLIDE 4: LIVE RESULTS & VISUAL PROOF
    # =========================================================
    s4 = prs.slides.add_slide(blank_layout)
    set_bg(s4)
    add_header(s4, "Live Test Results", "The custom AI detector accurately spotting equipment and saving evidence.")

    demo_img_path = os.path.abspath("evidence/demo_output.jpg")
    crop_img_path = os.path.abspath("evidence/2026-09-06/crop_20260906_162218_602_Truck_DEMO.jpg")

    # Left: Detection Image Card
    make_card(s4, Inches(0.9), Inches(2.1), Inches(7.5), Inches(4.7))
    tb_img_t = s4.shapes.add_textbox(Inches(1.1), Inches(2.25), Inches(7.0), Inches(0.35))
    p_it = tb_img_t.text_frame.paragraphs[0]
    p_it.text = "AI Detection: Spotting Truck (99% & 93% Confidence)"
    p_it.font.size = Pt(12)
    p_it.font.bold = True
    p_it.font.color.rgb = C_PRIMARY
    p_it.font.name = "Segoe UI"

    if os.path.exists(demo_img_path):
        s4.shapes.add_picture(demo_img_path, Inches(1.1), Inches(2.65), width=Inches(7.1))

    # Right: Close-up evidence crop
    make_card(s4, Inches(8.7), Inches(2.1), Inches(3.733), Inches(4.7))
    tb_cr_t = s4.shapes.add_textbox(Inches(8.95), Inches(2.25), Inches(3.2), Inches(0.35))
    p_ct = tb_cr_t.text_frame.paragraphs[0]
    p_ct.text = "Saved Evidence Photo"
    p_ct.font.size = Pt(12)
    p_ct.font.bold = True
    p_ct.font.color.rgb = C_GREEN
    p_ct.font.name = "Segoe UI"

    if os.path.exists(crop_img_path):
        s4.shapes.add_picture(crop_img_path, Inches(8.95), Inches(2.65), width=Inches(3.2))

    tb_cr_desc = s4.shapes.add_textbox(Inches(8.95), Inches(4.7), Inches(3.2), Inches(1.9))
    tf_cd = tb_cr_desc.text_frame
    tf_cd.word_wrap = True

    p_cd1 = tf_cd.paragraphs[0]
    p_cd1.text = "What was recorded:"
    p_cd1.font.size = Pt(11)
    p_cd1.font.bold = True
    p_cd1.font.color.rgb = C_TEXT_MAIN
    p_cd1.font.name = "Segoe UI"

    details = [
        "• Equipment: Construction Truck",
        "• AI Confidence: 99%",
        "• Quality Status: PASS",
        "• Automatically saved for audit"
    ]
    for d in details:
        p_d = tf_cd.add_paragraph()
        p_d.text = d
        p_d.font.size = Pt(10.5)
        p_d.font.color.rgb = C_TEXT_MUTED
        p_d.font.name = "Segoe UI"
        p_d.space_before = Pt(3)

    slides_with_notes.append((s4, (
        "Here is the actual visual proof from our tests. On the left, you can see the AI accurately identifying the truck with 99% confidence. "
        "On the right is what the system automatically generates: a clean, cropped photo of the equipment saved along with its date, time, and confidence score."
    )))

    # =========================================================
    # SLIDE 5: CAMERA HARDWARE SELECTED
    # =========================================================
    s5 = prs.slides.add_slide(blank_layout)
    set_bg(s5)
    add_header(s5, "Selected Camera Hardware", "Recommended for optimal site vision and easy integration with the Raspberry Pi 5.")

    # 2 Cards: The Camera & Why It Fits
    make_card(s5, Inches(0.9), Inches(2.1), Inches(5.6), Inches(4.7))
    tb_cam = s5.shapes.add_textbox(Inches(1.2), Inches(2.4), Inches(5.0), Inches(4.2))
    tf_cam = tb_cam.text_frame
    tf_cam.word_wrap = True

    p_c1 = tf_cam.paragraphs[0]
    p_c1.text = "Raspberry Pi Camera Module 3 (Wide)"
    p_c1.font.size = Pt(18)
    p_c1.font.bold = True
    p_c1.font.color.rgb = C_PRIMARY
    p_c1.font.name = "Segoe UI"

    cam_bullets = [
        "120° Wide-Angle Lens: Captures big construction machines without needing to pan or tilt the camera.",
        "Autofocus: Keeps pictures sharp whether equipment is near or far.",
        "HDR (High Dynamic Range): Handles harsh outdoor sunlight and dark shadows without blinding the camera.",
        "Native Support: Connects directly to the Raspberry Pi 5 with zero software issues."
    ]
    for b in cam_bullets:
        p_b = tf_cam.add_paragraph()
        p_b.text = "• " + b
        p_b.font.size = Pt(11.5)
        p_b.font.color.rgb = C_TEXT_MUTED
        p_b.font.name = "Segoe UI"
        p_b.space_before = Pt(10)

    # Card 2: Cable & Scope
    make_card(s5, Inches(6.8), Inches(2.1), Inches(5.6), Inches(4.7))
    tb_cab = s5.shapes.add_textbox(Inches(7.1), Inches(2.4), Inches(5.0), Inches(4.2))
    tf_cab = tb_cab.text_frame
    tf_cab.word_wrap = True

    p_cb1 = tf_cab.paragraphs[0]
    p_cb1.text = "Cable & Physical Setup"
    p_cb1.font.size = Pt(18)
    p_cb1.font.bold = True
    p_cb1.font.color.rgb = C_TEXT_MAIN
    p_cb1.font.name = "Segoe UI"

    cab_bullets = [
        "500mm Cable: Identified the official 500mm camera ribbon cable so your team has plenty of length to route it neatly through the vehicle chassis.",
        "Clear Focus: My focus is making sure the AI software and camera perform reliably.",
        "Ready to Test: Once your team has the Pi 5 and camera mounted, my software is ready to run on it immediately."
    ]
    for b in cab_bullets:
        p_b = tf_cab.add_paragraph()
        p_b.text = "• " + b
        p_b.font.size = Pt(11.5)
        p_b.font.color.rgb = C_TEXT_MUTED
        p_b.font.name = "Segoe UI"
        p_b.space_before = Pt(12)

    slides_with_notes.append((s5, (
        "Regarding hardware: I recommended the Raspberry Pi Camera Module 3 Wide. "
        "Its 120-degree lens captures large equipment easily, autofocus keeps it sharp, and HDR handles strong sunlight. "
        "I also shared the link for the 500mm cable so your mechanical team has enough length to route it inside the vehicle enclosure."
    )))

    # =========================================================
    # SLIDE 6: NEXT STEPS & QUICK QUESTIONS FOR BIRAJ
    # =========================================================
    s6 = prs.slides.add_slide(blank_layout)
    set_bg(s6)
    add_header(s6, "Next Steps & Discussion", "What comes next and 2 quick questions for today's meeting.")

    # Left: What comes next
    make_card(s6, Inches(0.9), Inches(2.1), Inches(5.6), Inches(4.7))
    tb_nxt = s6.shapes.add_textbox(Inches(1.2), Inches(2.4), Inches(5.0), Inches(4.2))
    tf_nxt = tb_nxt.text_frame
    tf_nxt.word_wrap = True

    p_nx1 = tf_nxt.paragraphs[0]
    p_nx1.text = "Next: Vehicle Recognition (Re-ID)"
    p_nx1.font.size = Pt(18)
    p_nx1.font.bold = True
    p_nx1.font.color.rgb = C_PRIMARY
    p_nx1.font.name = "Segoe UI"

    nxt_points = [
        "Goal: Moving from 'That is a Truck' to 'That is Truck #04'.",
        "Vehicle ID Match: The system will match spotted vehicles against a reference list of registered equipment on your site.",
        "Safe & Honest: If a machine looks unfamiliar or new, the system will flag it as 'Unknown' rather than making a wrong guess."
    ]
    for p_text in nxt_points:
        p_b = tf_nxt.add_paragraph()
        p_b.text = "• " + p_text
        p_b.font.size = Pt(12)
        p_b.font.color.rgb = C_TEXT_MUTED
        p_b.font.name = "Segoe UI"
        p_b.space_before = Pt(12)

    # Right: Quick questions for Biraj
    make_card(s6, Inches(6.8), Inches(2.1), Inches(5.6), Inches(4.7))
    tb_q = s6.shapes.add_textbox(Inches(7.1), Inches(2.4), Inches(5.0), Inches(4.2))
    tf_q = tb_q.text_frame
    tf_q.word_wrap = True

    p_q1 = tf_q.paragraphs[0]
    p_q1.text = "Quick Questions for Biraj"
    p_q1.font.size = Pt(18)
    p_q1.font.bold = True
    p_q1.font.color.rgb = C_AMBER
    p_q1.font.name = "Segoe UI"

    q_points = [
        "1. Equipment Checklist: Can you confirm the main types of equipment currently on your site? (e.g., excavators, dump trucks, cranes, loaders).",
        "2. Sample Photos: Do you have a few photos of your site's actual machines? Even quick phone photos will help us tune the system to your real site environment."
    ]
    for q_text in q_points:
        p_b = tf_q.add_paragraph()
        p_b.text = q_text
        p_b.font.size = Pt(12)
        p_b.font.color.rgb = C_TEXT_MAIN
        p_b.font.name = "Segoe UI"
        p_b.space_before = Pt(16)

    slides_with_notes.append((s6, (
        "Looking forward: Our next step is vehicle re-identification—teaching the system to recognize specific assets like 'Truck #04' instead of just 'a truck'. "
        "To help with that, two quick questions for you, Biraj: Can you confirm the equipment types on your site, and do you have any sample photos of your vehicles? "
        "Thank you, and I'd love to hear your feedback!"
    )))

    # Add notes to all slides
    for slide, note in slides_with_notes:
        slide.notes_slide.notes_text_frame.text = note

    prs.save(output_path)
    print(f"Simple presentation saved successfully to: {output_path}")

if __name__ == "__main__":
    out_dir = r"c:\Users\GANGARI DHRUVAVEER\Downloads\prozect"
    out_file = os.path.join(out_dir, "Site_Assets_Monitor_Presentation.pptx")
    create_simple_presentation(out_file)
