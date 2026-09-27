"""
Generates a crisp, publication-quality System Design Flow diagram image
showing Phase 1 (Human Walkthrough / One-Time Setup) vs Phase 2 (Autonomous Patrol / Ongoing).
"""

import os
import matplotlib.pyplot as plt
import matplotlib.patches as patches

def draw_system_flow_diagram(output_path):
    # Set high DPI figure with modern 16:9 ratio
    fig, ax = plt.subplots(figsize=(16, 9), dpi=300)
    fig.patch.set_facecolor('#F8FAFC')
    ax.set_facecolor('#F8FAFC')
    ax.set_xlim(0, 16)
    ax.set_ylim(0, 9)
    ax.axis('off')

    # Fonts and styling
    font_main = 'DejaVu Sans'
    
    # Title Header Banner
    ax.text(8.0, 8.45, "SITE ASSETS MONITOR — SYSTEM OPERATION WORKFLOW", 
            ha='center', va='center', fontsize=20, weight='bold', color='#0F172A', fontname=font_main)
    ax.text(8.0, 8.1, "Two-Phase Architecture: One-Time Ground Truth Enrollment vs. Continuous Autonomous Monitoring", 
            ha='center', va='center', fontsize=11, color='#64748B', fontname=font_main)

    def draw_card(x, y, w, h, bg_color, border_color, radius=0.08, border_w=1.5):
        box = patches.FancyBboxPatch((x, y), w, h,
                                     boxstyle=f"round,pad={radius}",
                                     facecolor=bg_color,
                                     edgecolor=border_color,
                                     linewidth=border_w)
        ax.add_patch(box)
        return box

    def draw_arrow(x1, y1, x2, y2, color='#2563EB', text=None, text_offset=(0, 0.15)):
        ax.annotate('', xy=(x2, y2), xytext=(x1, y1),
                    arrowprops=dict(arrowstyle="-|>", color=color, lw=2.2, mutation_scale=15))
        if text:
            ax.text((x1 + x2)/2 + text_offset[0], (y1 + y2)/2 + text_offset[1], text,
                    ha='center', va='center', fontsize=9, weight='bold', color=color, fontname=font_main)

    # =========================================================================
    # PHASE 1 CONTAINER (TOP HALF)
    # =========================================================================
    draw_card(0.6, 4.3, 14.8, 3.4, bg_color='#FFFFFF', border_color='#CBD5E1', radius=0.1)
    
    # Phase 1 Header Pill
    p1_pill = patches.FancyBboxPatch((0.9, 7.25), 5.2, 0.45, boxstyle="round,pad=0.05",
                                     facecolor='#EFF6FF', edgecolor='#2563EB', linewidth=1.2)
    ax.add_patch(p1_pill)
    ax.text(3.5, 7.47, "PHASE 1 : HUMAN WALKTHROUGH (ONE-TIME SETUP)", 
            ha='center', va='center', fontsize=11, weight='bold', color='#2563EB', fontname=font_main)
    
    ax.text(14.8, 7.47, "Goal: Establish Site Baseline & Ground Truth Database", 
            ha='right', va='center', fontsize=10, weight='semibold', color='#64748B', fontname=font_main)

    # Phase 1 Steps (4 Columns)
    p1_steps = [
        ("Step 1: Site Walkthrough", "#2563EB", 
         ["• Human operator guides robot", "  around the construction site", "• Orbbec Camera captures frames", "• Robot SLAM/GPS logs coordinates"],
         1.0, 4.6, 3.1, 2.4),
        ("Step 2: AI Detection & Crop", "#0D9488", 
         ["• Image Quality Filter checks blur/glare", "• YOLOv8 detects heavy machinery", "• Tight bounding boxes generated", "• High-res crops cut for Re-ID"],
         4.6, 4.6, 3.1, 2.4),
        ("Step 3: Signature Extraction", "#7C3AED", 
         ["• OSNet Deep Feature Extractor", "• Extracts 512D visual embedding", "• Invariant to slight angle changes", "• Human labels ID (e.g. EXC-024)"],
         8.2, 4.6, 3.1, 2.4),
        ("Step 4: Ground Truth DB", "#059669", 
         ["• Database Locked as Ground Truth", "• asset_id: 'EXC-024' (Excavator)", "• reference_pose: (X: 34.2, Y: 12.7)", "• 512D signature vector + crop photo"],
         11.8, 4.6, 3.2, 2.4)
    ]

    for title, col, bullets, bx, by, bw, bh in p1_steps:
        draw_card(bx, by, bw, bh, bg_color='#F8FAFC', border_color='#E2E8F0', border_w=1.2)
        # Header bar
        hbar = patches.FancyBboxPatch((bx, by + bh - 0.45), bw, 0.45, boxstyle="round,pad=0.03",
                                      facecolor=col, edgecolor=col, linewidth=1)
        ax.add_patch(hbar)
        ax.text(bx + bw/2, by + bh - 0.22, title, ha='center', va='center', 
                fontsize=10.5, weight='bold', color='#FFFFFF', fontname=font_main)
        
        # Bullets
        ty = by + bh - 0.75
        for b in bullets:
            ax.text(bx + 0.15, ty, b, ha='left', va='center', 
                    fontsize=9.2, color='#334155', fontname=font_main)
            ty -= 0.38

    # Connect Phase 1 Steps with arrows
    draw_arrow(4.1, 5.8, 4.6, 5.8, color='#2563EB')
    draw_arrow(7.7, 5.8, 8.2, 5.8, color='#2563EB')
    draw_arrow(11.3, 5.8, 11.8, 5.8, color='#2563EB')

    # =========================================================================
    # PHASE 2 CONTAINER (BOTTOM HALF)
    # =========================================================================
    draw_card(0.6, 0.45, 14.8, 3.55, bg_color='#FFFFFF', border_color='#CBD5E1', radius=0.1)
    
    # Phase 2 Header Pill
    p2_pill = patches.FancyBboxPatch((0.9, 3.48), 5.4, 0.45, boxstyle="round,pad=0.05",
                                     facecolor='#ECFDF5', edgecolor='#059669', linewidth=1.2)
    ax.add_patch(p2_pill)
    ax.text(3.6, 3.7, "PHASE 2 : AUTONOMOUS PATROL (ONGOING MONITORING)", 
            ha='center', va='center', fontsize=11, weight='bold', color='#059669', fontname=font_main)
    
    ax.text(14.8, 3.7, "Goal: Continuous Identity Verification & Relocation Detection", 
            ha='right', va='center', fontsize=10, weight='semibold', color='#64748B', fontname=font_main)

    # Phase 2 Steps (4 Blocks)
    # Block A: Robot Patrol Intake
    draw_card(1.0, 0.75, 2.9, 2.5, bg_color='#F8FAFC', border_color='#E2E8F0', border_w=1.2)
    hbar = patches.FancyBboxPatch((1.0, 2.8), 2.9, 0.45, boxstyle="round,pad=0.03",
                                  facecolor='#0284C7', edgecolor='#0284C7', linewidth=1)
    ax.add_patch(hbar)
    ax.text(2.45, 3.02, "1. Autonomous Patrol", ha='center', va='center', 
            fontsize=10.5, weight='bold', color='#FFFFFF', fontname=font_main)
    b_text1 = [
        "• Robot drives patrol waypoint",
        "• Orbbec RGB + Depth stream",
        "• ROS2 /robot/pose stream",
        "• Quality Gating (<3ms filter)"
    ]
    ty = 2.5
    for b in b_text1:
        ax.text(1.15, ty, b, ha='left', va='center', fontsize=9.2, color='#334155', fontname=font_main)
        ty -= 0.38

    # Block B: Identification Engine
    draw_card(4.3, 0.75, 3.1, 2.5, bg_color='#F8FAFC', border_color='#E2E8F0', border_w=1.2)
    hbar = patches.FancyBboxPatch((4.3, 2.8), 3.1, 0.45, boxstyle="round,pad=0.03",
                                  facecolor='#7C3AED', edgecolor='#7C3AED', linewidth=1)
    ax.add_patch(hbar)
    ax.text(5.85, 3.02, "2. Real-Time Re-ID", ha='center', va='center', 
            fontsize=10.5, weight='bold', color='#FFFFFF', fontname=font_main)
    b_text2 = [
        "• YOLOv8 spots equipment",
        "• OSNet extracts live 512D vector",
        "• Cosine similarity against DB",
        "• Match >= 0.85 -> ID Confirmed",
        "• Match < 0.65 -> Flag UNKNOWN"
    ]
    ty = 2.5
    for b in b_text2:
        ax.text(4.45, ty, b, ha='left', va='center', fontsize=9.0, color='#334155', fontname=font_main)
        ty -= 0.38

    # Block C: Pose & Movement Comparator
    draw_card(7.8, 0.75, 3.1, 2.5, bg_color='#F8FAFC', border_color='#E2E8F0', border_w=1.2)
    hbar = patches.FancyBboxPatch((7.8, 2.8), 3.1, 0.45, boxstyle="round,pad=0.03",
                                  facecolor='#EA580C', edgecolor='#EA580C', linewidth=1)
    ax.add_patch(hbar)
    ax.text(9.35, 3.02, "3. Spatial Verification", ha='center', va='center', 
            fontsize=10.5, weight='bold', color='#FFFFFF', fontname=font_main)
    b_text3 = [
        "• Compute asset real-world (X,Y)",
        "  using depth + robot pose",
        "• Compare with Phase 1 baseline",
        "• Distance Δ = |Current - Stored|",
        "• Configurable tolerance: ~3.0m"
    ]
    ty = 2.5
    for b in b_text3:
        ax.text(7.95, ty, b, ha='left', va='center', fontsize=9.0, color='#334155', fontname=font_main)
        ty -= 0.38

    # Block D: Automated Outcomes (Branching)
    draw_card(11.3, 0.75, 3.8, 2.5, bg_color='#F8FAFC', border_color='#E2E8F0', border_w=1.2)
    hbar = patches.FancyBboxPatch((11.3, 2.8), 3.8, 0.45, boxstyle="round,pad=0.03",
                                  facecolor='#0F172A', edgecolor='#0F172A', linewidth=1)
    ax.add_patch(hbar)
    ax.text(13.2, 3.02, "4. Status & Audit Alerts", ha='center', va='center', 
            fontsize=10.5, weight='bold', color='#FFFFFF', fontname=font_main)

    # Sub-card 1: In Place
    draw_card(11.45, 1.95, 3.5, 0.72, bg_color='#ECFDF5', border_color='#10B981', border_w=1.0)
    ax.text(11.6, 2.45, "IN PLACE (Delta <= 3m)", fontsize=9.2, weight='bold', color='#065F46', fontname=font_main)
    ax.text(11.6, 2.15, "Normal logging; timestamp & position verified.", fontsize=8.0, color='#047857', fontname=font_main)

    # Sub-card 2: Moved
    draw_card(11.45, 1.15, 3.5, 0.72, bg_color='#FEF2F2', border_color='#EF4444', border_w=1.0)
    ax.text(11.6, 1.65, "ALERT: ASSET MOVED (Delta > 3m)", fontsize=9.2, weight='bold', color='#991B1B', fontname=font_main)
    ax.text(11.6, 1.35, "Relocation alert + evidence crop + new GPS.", fontsize=8.0, color='#B91C1C', fontname=font_main)

    # Sub-card 3: Unknown
    draw_card(11.45, 0.82, 3.5, 0.28, bg_color='#FFFBEB', border_color='#F59E0B', border_w=1.0)
    ax.text(11.6, 0.96, "UNKNOWN ASSET -- Added to inspection queue", fontsize=8.0, weight='bold', color='#92400E', fontname=font_main)

    # Connect Phase 2 Steps
    draw_arrow(3.9, 2.0, 4.3, 2.0, color='#0284C7')
    draw_arrow(7.4, 2.0, 7.8, 2.0, color='#7C3AED')
    draw_arrow(10.9, 2.0, 11.3, 2.0, color='#EA580C')

    # Inter-phase dashed connection: Ground truth DB feeds live matching
    ax.annotate('', xy=(6.5, 3.3), xytext=(12.8, 4.6),
                arrowprops=dict(arrowstyle="-|>", color='#059669', lw=2.0, linestyle='dashed', 
                                connectionstyle="arc3,rad=0.12", mutation_scale=15))
    ax.text(9.5, 4.05, "Ground Truth DB Feeds Reference Embeddings & Expected Poses", 
            ha='center', va='center', fontsize=9.2, weight='bold', color='#059669', 
            bbox=dict(boxstyle='round,pad=0.25', facecolor='#ECFDF5', edgecolor='#059669', lw=1.2),
            fontname=font_main)

    plt.tight_layout()
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    plt.savefig(output_path, dpi=300, facecolor=fig.get_facecolor(), edgecolor='none', bbox_inches='tight')
    plt.close()
    print(f"System flow diagram successfully generated at: {output_path}")

if __name__ == "__main__":
    out_img = r"c:\Users\GANGARI DHRUVAVEER\Downloads\prozect\SITE_Assets_Monitor\evidence\system_design_flow.png"
    draw_system_flow_diagram(out_img)
