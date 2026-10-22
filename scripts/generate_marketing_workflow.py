"""
Generate Customer-Facing Perception System Operation Workflow Visual (Marketing Edition)
Designed specifically for customers, sales, and executive presentations:
- Plain English, zero robotics jargon
- Clear 4-Step Operational Story
- Integrated 3D concept render visual
- High-contrast card-based design with ROI highlights
"""

import os
import sys
import textwrap
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from PIL import Image

import matplotlib.font_manager as fm

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PARENT_ROOT = os.path.dirname(PROJECT_ROOT)

IMAGE_RENDER_PATH = r"C:\Users\GANGARI DHRUVAVEER\.gemini\antigravity-ide\brain\7bd9be79-9b42-46e2-9b8c-b0f440068b2e\marketing_perception_workflow_1791102666102.jpg"

def create_marketing_workflow(output_path, root_output_path):
    # Set high-resolution 16:9 figure (3840x2160 equiv at 240 DPI)
    fig, ax = plt.subplots(figsize=(16, 9), dpi=240)
    fig.patch.set_facecolor('#0F172A') # Slate-900 Dark Executive Theme
    ax.set_facecolor('#0F172A')
    ax.set_xlim(0, 16)
    ax.set_ylim(0, 9)
    ax.axis('off')

    font_main = 'Segoe UI' if 'Segoe UI' in [f.name for f in fm.fontManager.ttflist] else 'DejaVu Sans'

    # 1. Header Banner
    # Badge Pill
    pill = patches.FancyBboxPatch((0.8, 8.2), 3.4, 0.42, boxstyle="round,pad=0.04",
                                  facecolor='#0369A1', edgecolor='#38BDF8', linewidth=1.2)
    ax.add_patch(pill)
    ax.text(2.5, 8.41, "HOW IT WORKS FOR YOUR FACILITY", ha='center', va='center',
            fontsize=10, weight='bold', color='#E0F2FE', fontname=font_main)

    ax.text(0.8, 7.8, "Automated 24/7 Equipment Watch & Visual Auditing",
            ha='left', va='center', fontsize=22, weight='bold', color='#FFFFFF', fontname=font_main)
    ax.text(0.8, 7.35, "How our intelligent robot tracks high-value site assets without barcodes, RFID tags, or manual clipboards.",
            ha='left', va='center', fontsize=11, color='#94A3B8', fontname=font_main)

    # 2. Left Side: The 3D Patrol Robot Visual Showcase
    def draw_card(x, y, w, h, bg_color, border_color='#334155', radius=0.08, border_w=1.2):
        box = patches.FancyBboxPatch((x, y), w, h,
                                     boxstyle=f"round,pad={radius}",
                                     facecolor=bg_color,
                                     edgecolor=border_color,
                                     linewidth=border_w)
        ax.add_patch(box)
        return box

    # Image Card Container (Left Half)
    img_card_x = 0.8
    img_card_y = 1.6
    img_card_w = 7.1
    img_card_h = 5.4
    draw_card(img_card_x, img_card_y, img_card_w, img_card_h, bg_color='#1E293B', border_color='#38BDF8', border_w=1.5)

    if os.path.exists(IMAGE_RENDER_PATH):
        render_img = Image.open(IMAGE_RENDER_PATH)
        # Position image higher up inside card so bottom has dedicated text area
        ax.imshow(render_img, extent=[img_card_x + 0.18, img_card_x + img_card_w - 0.18,
                                     img_card_y + 1.6, img_card_y + img_card_h - 0.18],
                  aspect='auto', zorder=2)
    
    # Image Caption / Tagline inside Left Card (cleanly positioned below the render)
    ax.text(img_card_x + 0.3, img_card_y + 1.15, "Live AI Scanning in Active Yards",
            fontsize=13, weight='bold', color='#FFFFFF', fontname=font_main)
    ax.text(img_card_x + 0.3, img_card_y + 0.55,
            "• Autonomous Patrol: Robot navigates scheduled routes day & night\n"
            "• Smart Ranging: 3D sensors measure asset distance up to 12 meters\n"
            "• Zero Tagging: Works directly on generators, compressors, and tools",
            fontsize=9.2, color='#CBD5E1', fontname=font_main, linespacing=1.45)

    # 3. Right Side: The 4-Step Customer Workflow
    steps = [
        {
            "num": "01",
            "title": "Smart Visual Scanning",
            "tag": "DAY & NIGHT PATROL",
            "tag_color": "#0284C7",
            "desc": "As the robot navigates the site, high-definition 3D cameras automatically spot and register machines along the path—even in harsh yard dust or direct sunlight."
        },
        {
            "num": "02",
            "title": "\"Face ID\" Machine Recognition",
            "tag": "NO RFID OR BARCODES",
            "tag_color": "#7C3AED",
            "desc": "The AI recognizes each asset by its unique visual appearance (shape, decals, paint wear, serial plates). No tags to get torn off, covered in mud, or lost."
        },
        {
            "num": "03",
            "title": "3-Meter Movement Calculation",
            "tag": "PRECISION LOCALIZATION",
            "tag_color": "#EA580C",
            "desc": "Every sighting is matched against the facility blueprint. The system calculates if the machine is still in its approved bay or if it has been relocated."
        },
        {
            "num": "04",
            "title": "Instant Proof & Automated Alerts",
            "tag": "REAL-TIME VISIBILITY",
            "tag_color": "#059669",
            "desc": "If moved > 3 meters (10 ft), operations receives an instant alert with side-by-side photo proof (Day 1 vs. Today) and the exact new map coordinates."
        }
    ]

    right_x = 8.25
    step_w = 6.95
    step_h = 1.22
    step_gap = 0.16
    start_y = 5.78

    for i, s in enumerate(steps):
        curr_y = start_y - i * (step_h + step_gap)
        draw_card(right_x, curr_y, step_w, step_h, bg_color='#1E293B', border_color='#334155', radius=0.06)

        # Number Accent Box
        num_box = patches.FancyBboxPatch((right_x + 0.18, curr_y + 0.18), 0.85, 0.86, boxstyle="round,pad=0.04",
                                         facecolor=s["tag_color"], edgecolor=s["tag_color"])
        ax.add_patch(num_box)
        ax.text(right_x + 0.605, curr_y + 0.61, s["num"], ha='center', va='center',
                fontsize=16, weight='bold', color='#FFFFFF', fontname=font_main)

        # Step Title & Badge
        ax.text(right_x + 1.25, curr_y + 0.92, s["title"],
                fontsize=12, weight='bold', color='#F8FAFC', fontname=font_main)
        
        # Pill Tag
        tag_patch = patches.FancyBboxPatch((right_x + step_w - 2.2, curr_y + 0.84), 2.0, 0.26, boxstyle="round,pad=0.03",
                                           facecolor='#0F172A', edgecolor=s["tag_color"], linewidth=1.0)
        ax.add_patch(tag_patch)
        ax.text(right_x + step_w - 1.2, curr_y + 0.97, s["tag"], ha='center', va='center',
                fontsize=7.5, weight='bold', color='#E2E8F0', fontname=font_main)

        # Description
        wrapped_desc = textwrap.fill(s["desc"], width=74)
        ax.text(right_x + 1.25, curr_y + 0.58, wrapped_desc,
                ha='left', va='top', fontsize=8.6, color='#94A3B8', fontname=font_main, linespacing=1.35)

    # 4. Bottom Value Proposition / Customer Benefits Bar
    benefit_y = 0.45
    benefit_w = 14.4
    benefit_h = 0.88
    draw_card(0.8, benefit_y, benefit_w, benefit_h, bg_color='#1E293B', border_color='#0284C7', radius=0.06, border_w=1.0)

    benefits = [
        ("100% Visual Proof", "Photo evidence attached to every single movement alert"),
        ("Zero Physical Tags", "No RFIDs, barcodes, or battery stickers to maintain"),
        ("Autonomous 24/7", "Patrols overnight & weekends without human security guards"),
        ("3-Meter Accuracy", "Distinguishes normal working tolerance from unauthorized moves")
    ]

    col_width = benefit_w / 4
    for i, (b_title, b_sub) in enumerate(benefits):
        bx = 0.8 + i * col_width
        if i > 0:
            ax.plot([bx, bx], [benefit_y + 0.15, benefit_y + benefit_h - 0.15], color='#334155', lw=1.2)
        
        ax.text(bx + col_width/2, benefit_y + 0.58, f"{b_title}", ha='center', va='center',
                fontsize=10.5, weight='bold', color='#38BDF8', fontname=font_main)
        ax.text(bx + col_width/2, benefit_y + 0.28, b_sub, ha='center', va='center',
                fontsize=8.0, color='#94A3B8', fontname=font_main)

    # Save to both project folder and root
    plt.subplots_adjust(left=0, right=1, top=1, bottom=0)
    fig.savefig(output_path, dpi=240, facecolor=fig.get_facecolor(), edgecolor='none', bbox_inches='tight', pad_inches=0.1)
    fig.savefig(root_output_path, dpi=240, facecolor=fig.get_facecolor(), edgecolor='none', bbox_inches='tight', pad_inches=0.1)
    plt.close(fig)
    print(f"Marketing visual saved to:\n  - {output_path}\n  - {root_output_path}")

if __name__ == "__main__":
    out_dir = os.path.join(PROJECT_ROOT, "evidence")
    os.makedirs(out_dir, exist_ok=True)
    out1 = os.path.join(out_dir, "Perception_System_Marketing_Workflow.png")
    out2 = os.path.join(PARENT_ROOT, "Perception_System_Marketing_Workflow.png")
    create_marketing_workflow(out1, out2)
