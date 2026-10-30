import os
import sys
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE

def build_presentation(output_pptx_paths):
    prs = Presentation()
    # 16:9 Widescreen standard
    prs.slide_width = Inches(13.333)
    prs.slide_height = Inches(7.5)
    
    # -------------------------------------------------------------
    # PALETTE (Palantir / Modern Engineering Dark Theme)
    # -------------------------------------------------------------
    BG_DARK = RGBColor(11, 15, 25)         # Ultra deep slate
    CARD_BG = RGBColor(23, 32, 51)         # Card surface
    CARD_BORDER = RGBColor(51, 65, 85)     # Slate border
    ACCENT_CYAN = RGBColor(56, 189, 248)   # Bright Sky / Cyan
    ACCENT_BLUE = RGBColor(96, 165, 250)   # Blue
    TEXT_WHITE = RGBColor(248, 250, 252)   # Pure white
    TEXT_MUTED = RGBColor(148, 163, 184)   # Slate 400
    TEXT_BODY = RGBColor(226, 232, 240)    # Slate 200
    GREEN_SUCCESS = RGBColor(52, 211, 153) # Emerald
    AMBER_WARN = RGBColor(251, 191, 36)    # Amber
    ROSE_CRIT = RGBColor(244, 63, 94)      # Critical Rose
    
    # Local asset paths (Freshly captured live screenshots)
    ASSET_DIR = os.path.abspath("assets/slides")
    img_dashboard = os.path.join(ASSET_DIR, "main_dashboard_live.png")
    img_tracking = os.path.join(ASSET_DIR, "dense_tracking_overlay.png")
    img_report = os.path.join(ASSET_DIR, "report_page_screenshot.png")
    img_alerts = os.path.join(ASSET_DIR, "incident_alerts_snapshots.png")
    img_zones = os.path.join(ASSET_DIR, "spatial_zones_grid.png")
    img_telemetry = os.path.join(ASSET_DIR, "telemetry_gauges.png")
    img_modal = os.path.join(ASSET_DIR, "add_feed_modal.png")

    blank_layout = prs.slide_layouts[6] # Blank slide layout

    # Helper: Set slide solid background
    def apply_background(slide):
        bg = slide.background
        fill = bg.fill
        fill.solid()
        fill.fore_color.rgb = BG_DARK

    # Helper: Add header banner
    def add_header(slide, title_text, category_text="CROWD SAFETY MONITOR • OPERATIONS PLATFORM"):
        # Category pill
        cat_box = slide.shapes.add_textbox(Inches(0.8), Inches(0.4), Inches(11.5), Inches(0.35))
        tf_cat = cat_box.text_frame
        tf_cat.word_wrap = True
        p_cat = tf_cat.paragraphs[0]
        p_cat.text = category_text.upper()
        p_cat.font.size = Pt(11)
        p_cat.font.bold = True
        p_cat.font.color.rgb = ACCENT_CYAN

        # Title
        t_box = slide.shapes.add_textbox(Inches(0.8), Inches(0.75), Inches(11.5), Inches(0.7))
        tf_t = t_box.text_frame
        tf_t.word_wrap = True
        p_t = tf_t.paragraphs[0]
        p_t.text = title_text
        p_t.font.size = Pt(28)
        p_t.font.bold = True
        p_t.font.color.rgb = TEXT_WHITE

    # Helper: Add card container
    def add_card(slide, left, top, width, height, fill_color=CARD_BG, border_color=CARD_BORDER):
        shape = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, left, top, width, height)
        shape.fill.solid()
        shape.fill.fore_color.rgb = fill_color
        shape.line.color.rgb = border_color
        shape.line.width = Pt(1.2)
        return shape

    # -------------------------------------------------------------
    # SLIDE 1: TITLE & COVER SLIDE
    # -------------------------------------------------------------
    s1 = prs.slides.add_slide(blank_layout)
    apply_background(s1)
    
    # Backdrop card
    add_card(s1, Inches(0.8), Inches(0.8), Inches(11.733), Inches(5.9), fill_color=RGBColor(15, 23, 42), border_color=RGBColor(30, 41, 59))
    
    # Badge
    badge_box = s1.shapes.add_textbox(Inches(1.2), Inches(1.2), Inches(6.0), Inches(0.4))
    tf_b = badge_box.text_frame
    p_b = tf_b.paragraphs[0]
    p_b.text = "● VIVA FINAL PROJECT REVIEW & EVALUATION"
    p_b.font.size = Pt(12)
    p_b.font.bold = True
    p_b.font.color.rgb = GREEN_SUCCESS

    # Big Title
    title_box = s1.shapes.add_textbox(Inches(1.2), Inches(1.7), Inches(11.0), Inches(1.8))
    tf_main = title_box.text_frame
    tf_main.word_wrap = True
    p_m1 = tf_main.paragraphs[0]
    p_m1.text = "CROWD SAFETY MONITOR"
    p_m1.font.size = Pt(44)
    p_m1.font.bold = True
    p_m1.font.color.rgb = TEXT_WHITE

    p_m2 = tf_main.add_paragraph()
    p_m2.text = "Real-Time Spatio-Temporal Intelligence & Stampede Prevention Platform"
    p_m2.font.size = Pt(22)
    p_m2.font.bold = True
    p_m2.font.color.rgb = ACCENT_CYAN
    p_m2.space_before = Pt(8)

    # Sub-description
    desc_box = s1.shapes.add_textbox(Inches(1.2), Inches(3.6), Inches(10.8), Inches(1.0))
    tf_desc = desc_box.text_frame
    tf_desc.word_wrap = True
    p_d = tf_desc.paragraphs[0]
    p_d.text = ("An autonomous, edge-accelerated computer vision platform engineered to predict crowd turbulence, "
                "velocity lock, and compressive asphyxia risk in high-density gatherings before disaster occurs.")
    p_d.font.size = Pt(15)
    p_d.font.color.rgb = TEXT_MUTED

    # Highlight Pill Grid at bottom
    chips = [
        ("PERCEPTION", "YOLOv8s + Centroid Tracking"),
        ("HARDWARE", "Apple Silicon MPS GPU (20+ FPS)"),
        ("SPATIAL GRID", "4x4 Matrix (16 Discrete Zones)"),
        ("PHYSICS", "Farnebäck Optical Flow"),
        ("PHYSIOLOGY", "Compressive Asphyxia Model"),
        ("DELIVERY", "FastAPI + 10Hz WebSocket HUD")
    ]
    for i, (tag, val) in enumerate(chips):
        col = i % 3
        row = i // 3
        c_left = Inches(1.2 + col * 3.65)
        c_top = Inches(4.7 + row * 0.9)
        add_card(s1, c_left, c_top, Inches(3.45), Inches(0.75), fill_color=RGBColor(24, 34, 53), border_color=RGBColor(59, 130, 246))
        c_box = s1.shapes.add_textbox(c_left + Inches(0.1), c_top + Inches(0.05), Inches(3.25), Inches(0.65))
        tf_c = c_box.text_frame
        p_c1 = tf_c.paragraphs[0]
        p_c1.text = tag
        p_c1.font.size = Pt(9)
        p_c1.font.bold = True
        p_c1.font.color.rgb = ACCENT_CYAN
        p_c2 = tf_c.add_paragraph()
        p_c2.text = val
        p_c2.font.size = Pt(12)
        p_c2.font.bold = True
        p_c2.font.color.rgb = TEXT_WHITE

    # -------------------------------------------------------------
    # SLIDE 2: THE CRITICAL PROBLEM & MOTIVATION
    # -------------------------------------------------------------
    s2 = prs.slides.add_slide(blank_layout)
    apply_background(s2)
    add_header(s2, "The Critical Problem: Why Stampedes Turn Fatal")

    # 3 Column Cards
    col_w = Inches(3.7)
    gap = Inches(0.3)
    
    # Card 1: Disasters
    add_card(s2, Inches(0.8), Inches(1.6), col_w, Inches(5.2))
    b1 = s2.shapes.add_textbox(Inches(1.0), Inches(1.8), Inches(3.3), Inches(4.8))
    tf1 = b1.text_frame
    tf1.word_wrap = True
    p = tf1.paragraphs[0]
    p.text = "HISTORICAL TRAGEDIES"
    p.font.size = Pt(13)
    p.font.bold = True
    p.font.color.rgb = ROSE_CRIT
    
    pts1 = [
        "Itaewon Halloween (2022): 159 deaths in a 4-meter narrow alley due to crowd collapse.",
        "Kumbh Mela & Mina Stampedes: Overcrowded bottlenecks causing systemic panic cascades.",
        "Astroworld Festival (2021): 10 deaths from progressive compressive crowd surge.",
        "Critical Takeaway: Disasters are not caused by wild running, but by silent physical crowd crushing."
    ]
    for pt in pts1:
        p = tf1.add_paragraph()
        p.text = "• " + pt
        p.font.size = Pt(13)
        p.font.color.rgb = TEXT_BODY
        p.space_before = Pt(10)

    # Card 2: Failure Modes
    add_card(s2, Inches(0.8) + col_w + gap, Inches(1.6), col_w, Inches(5.2))
    b2 = s2.shapes.add_textbox(Inches(1.0) + col_w + gap, Inches(1.8), Inches(3.3), Inches(4.8))
    tf2 = b2.text_frame
    tf2.word_wrap = True
    p = tf2.paragraphs[0]
    p.text = "CONVENTIONAL CCTV FLAWS"
    p.font.size = Pt(13)
    p.font.bold = True
    p.font.color.rgb = AMBER_WARN

    pts2 = [
        "100% Reactive Surveillance: Human operators only spot crowds after injuries have occurred.",
        "Global Headcount Bias: A venue at 50% capacity can still have a lethal 150% crush at one exit gate.",
        "False Stampede Detection: Stationary dense groups are mistakenly flagged as stampedes by naive algorithms.",
        "Fatigue & Blind Spots: Guard attention drops by >70% after 20 minutes of multi-camera monitoring."
    ]
    for pt in pts2:
        p = tf2.add_paragraph()
        p.text = "• " + pt
        p.font.size = Pt(13)
        p.font.color.rgb = TEXT_BODY
        p.space_before = Pt(10)

    # Card 3: Physiological Reality
    add_card(s2, Inches(0.8) + (col_w + gap) * 2, Inches(1.6), col_w, Inches(5.2))
    b3 = s2.shapes.add_textbox(Inches(1.0) + (col_w + gap) * 2, Inches(1.8), Inches(3.3), Inches(4.8))
    tf3 = b3.text_frame
    tf3.word_wrap = True
    p = tf3.paragraphs[0]
    p.text = "THE INVISIBLE KILLER"
    p.font.size = Pt(13)
    p.font.bold = True
    p.font.color.rgb = ACCENT_CYAN

    pts3 = [
        "Compressive Asphyxia: Chest compression above 4,000 N prevents lung expansion while standing upright.",
        "Velocity Lock: When people pack tightly, walking speed drops to near 0 px/frame under intense force.",
        "Turbulence / Wave Transmission: Shockwaves propagate through dense human bodies like fluid.",
        "Our Goal: Detect the precursors (density + kinetic lock + duration) 3 to 5 minutes prior to collapse."
    ]
    for pt in pts3:
        p = tf3.add_paragraph()
        p.text = "• " + pt
        p.font.size = Pt(13)
        p.font.color.rgb = TEXT_BODY
        p.space_before = Pt(10)

    # -------------------------------------------------------------
    # SLIDE 3: OUR PROPOSED SOLUTION & INNOVATION
    # -------------------------------------------------------------
    s3 = prs.slides.add_slide(blank_layout)
    apply_background(s3)
    add_header(s3, "The Proposed Solution: Autonomous Crowd Safety Monitor")

    # Left: Core Pillars
    left_w = Inches(6.0)
    add_card(s3, Inches(0.8), Inches(1.6), left_w, Inches(5.2))
    b_sol = s3.shapes.add_textbox(Inches(1.0), Inches(1.8), Inches(5.6), Inches(4.8))
    tf_sol = b_sol.text_frame
    tf_sol.word_wrap = True
    p = tf_sol.paragraphs[0]
    p.text = "ARCHITECTURAL CAPABILITIES & INNOVATION"
    p.font.size = Pt(14)
    p.font.bold = True
    p.font.color.rgb = ACCENT_CYAN

    sol_pts = [
        ("Sub-Second Inference on Edge", "Runs YOLOv8s natively accelerated by Apple Silicon MPS (GPU), achieving 20+ FPS continuous tracking."),
        ("Physical Velocity Lock Modeling", "Calibrated velocity decay distinguishes peaceful walking crowds from locked, immobilized crushing crowds."),
        ("16-Zone Discrete Spatial Matrix", "Divides physical scenes into a 4x4 spatial grid, computing discrete densities and isolating exact choke points."),
        ("Farnebäck Dense Optical Flow", "Calculates dense motion vectors to spot sudden directional reversals, panic turbulence, and shockwaves."),
        ("Automated Forensics & Incident Dossier", "Auto-captures annotated JPEGs upon critical triggers and generates comprehensive 1-click audit PDFs.")
    ]
    for title, desc in sol_pts:
        p = tf_sol.add_paragraph()
        p.text = "✔ " + title
        p.font.size = Pt(13)
        p.font.bold = True
        p.font.color.rgb = GREEN_SUCCESS
        p.space_before = Pt(8)
        p_sub = tf_sol.add_paragraph()
        p_sub.text = desc
        p_sub.font.size = Pt(11)
        p_sub.font.color.rgb = TEXT_BODY

    # Right: Feature Snapshot Card (Dynamic Stream Ingestion)
    right_w = Inches(5.4)
    add_card(s3, Inches(7.1), Inches(1.6), right_w, Inches(5.2))
    if os.path.exists(img_modal):
        s3.shapes.add_picture(img_modal, Inches(7.3), Inches(1.8), width=Inches(5.0))
    t_caption = s3.shapes.add_textbox(Inches(7.3), Inches(6.0), Inches(5.0), Inches(0.6))
    p_cap = t_caption.text_frame.paragraphs[0]
    p_cap.text = "Dynamic Stream Connector: Connect live RTSP IP cameras, video streams, or hardware devices on the fly."
    p_cap.font.size = Pt(10)
    p_cap.font.color.rgb = TEXT_MUTED

    # -------------------------------------------------------------
    # SLIDE 4: SYSTEM ARCHITECTURE & DATA PIPELINE
    # -------------------------------------------------------------
    s4 = prs.slides.add_slide(blank_layout)
    apply_background(s4)
    add_header(s4, "End-to-End System Architecture & Data Pipeline")

    steps = [
        ("1. INGESTION", "Multi-Source Feeds", "RTSP / CCTV Streams\n4K Video Files\nHardware Webcams\nFastAPI Uploads", ACCENT_BLUE),
        ("2. DETECTION", "YOLOv8s + MPS GPU", "Native PyTorch MPS\n25ms Inference Time\nBounding Boxes\nCentroid Tracking", ACCENT_CYAN),
        ("3. MOTION", "Optical Flow Engine", "Farnebäck Dense Flow\n0.5x Grayscale Downsample\nVelocity Vectors\nDirectional Variance", GREEN_SUCCESS),
        ("4. ANALYTICS", "Spatio-Temporal Matrix", "4x4 Grid Partitioning\nLocal Headcount (D_z)\nKinetic Congestion (C_z)\nAsphyxia Load (S_z)", AMBER_WARN),
        ("5. TELEMETRY", "FastAPI + WebSocket", "10Hz JSON Push\nMJPEG Video Stream\nZero-Lag Web HUD\nSynthesized Web Audio", ROSE_CRIT)
    ]
    card_w = Inches(2.2)
    step_gap = Inches(0.18)
    for idx, (step_tag, title, desc, col) in enumerate(steps):
        s_left = Inches(0.8 + idx * (2.2 + 0.18))
        add_card(s4, s_left, Inches(1.6), card_w, Inches(4.3), fill_color=RGBColor(18, 26, 43), border_color=col)
        
        box = s4.shapes.add_textbox(s_left + Inches(0.1), Inches(1.8), card_w - Inches(0.2), Inches(3.9))
        tf = box.text_frame
        tf.word_wrap = True
        
        p = tf.paragraphs[0]
        p.text = step_tag
        p.font.size = Pt(11)
        p.font.bold = True
        p.font.color.rgb = col
        
        p2 = tf.add_paragraph()
        p2.text = title
        p2.font.size = Pt(14)
        p2.font.bold = True
        p2.font.color.rgb = TEXT_WHITE
        p2.space_before = Pt(4)
        
        p3 = tf.add_paragraph()
        p3.text = desc
        p3.font.size = Pt(11)
        p3.font.color.rgb = TEXT_MUTED
        p3.space_before = Pt(12)

    # Bottom summary banner
    add_card(s4, Inches(0.8), Inches(6.1), Inches(11.733), Inches(0.8), fill_color=RGBColor(24, 34, 53), border_color=RGBColor(59, 130, 246))
    bot_box = s4.shapes.add_textbox(Inches(1.0), Inches(6.2), Inches(11.3), Inches(0.6))
    p_bot = bot_box.text_frame.paragraphs[0]
    p_bot.text = "⚡ Real-Time Guarantee: Decoupled daemon worker threads process OpenCV frames asynchronously from the FastAPI ASGI event loop."
    p_bot.font.size = Pt(12)
    p_bot.font.bold = True
    p_bot.font.color.rgb = TEXT_WHITE

    # -------------------------------------------------------------
    # SLIDE 5: MATHEMATICAL FORMULATION
    # -------------------------------------------------------------
    s5 = prs.slides.add_slide(blank_layout)
    apply_background(s5)
    add_header(s5, "Mathematical Formulation: Physics-Based Risk Modeling")

    math_cards = [
        ("1. SPATIAL DENSITY (D_z)", 
         "D_z[t] = min( 100 , ( N_z[t] / Capacity_max ) * 100 )",
         "Measures localized spatial packing per zone z. Unlike global headcounts, this captures localized dangerous clustering in narrow choke points.",
         ACCENT_CYAN),
        ("2. KINETIC CONGESTION (C_z)",
         "C_z[t] = max( 0 , 100 * ( 1.0 - ( v_avg[t] / v_expected ) ) )",
         "Calibrated velocity decay. Free-flowing crowds maintain high v_avg (low congestion). Immobilized crowds approaching 0 px/frame trigger high congestion.",
         GREEN_SUCCESS),
        ("3. TURBULENCE / PANIC (T_z)",
         "T_z[t] = min( 100 , std_dev( theta_vectors ) * 50 )",
         "Measures directional entropy from Farnebäck optical flow. Uniform laminar flow has low variance; counter-directional panic surges yield high turbulence.",
         AMBER_WARN),
        ("4. COMPRESSIVE ASPHYXIA (S_z)",
         "S_z[t] = min( 100 , (D_z / 100)^2 * (C_z / 100) * log2( 1 + t_stagnant ) )",
         "Models physiological crush hazard. Non-linear amplification occurs when maximum density and zero velocity persist over prolonged time intervals.",
         ROSE_CRIT)
    ]
    for idx, (m_title, formula, explanation, color) in enumerate(math_cards):
        col = idx % 2
        row = idx // 2
        m_left = Inches(0.8 + col * 5.95)
        m_top = Inches(1.6 + row * 2.5)
        add_card(s5, m_left, m_top, Inches(5.75), Inches(2.3), fill_color=RGBColor(20, 29, 47), border_color=color)
        
        m_box = s5.shapes.add_textbox(m_left + Inches(0.15), m_top + Inches(0.1), Inches(5.45), Inches(2.1))
        tf_m = m_box.text_frame
        tf_m.word_wrap = True
        
        p = tf_m.paragraphs[0]
        p.text = m_title
        p.font.size = Pt(13)
        p.font.bold = True
        p.font.color.rgb = color
        
        p_eq = tf_m.add_paragraph()
        p_eq.text = formula
        p_eq.font.size = Pt(12)
        p_eq.font.bold = True
        p_eq.font.color.rgb = TEXT_WHITE
        p_eq.space_before = Pt(4)
        
        p_exp = tf_m.add_paragraph()
        p_exp.text = explanation
        p_exp.font.size = Pt(10)
        p_exp.font.color.rgb = TEXT_MUTED
        p_exp.space_before = Pt(4)

    # Formula composite at bottom
    add_card(s5, Inches(0.8), Inches(6.55), Inches(11.733), Inches(0.65), fill_color=RGBColor(24, 34, 53), border_color=RGBColor(96, 165, 250))
    b_comp = s5.shapes.add_textbox(Inches(1.0), Inches(6.6), Inches(11.3), Inches(0.55))
    p_comp = b_comp.text_frame.paragraphs[0]
    p_comp.text = "COMPOSITE RISK INDEX:   R_z[t] = 0.35 · D_z[t] + 0.30 · C_z[t] + 0.20 · T_z[t] + 0.15 · S_z[t]"
    p_comp.font.size = Pt(13)
    p_comp.font.bold = True
    p_comp.font.color.rgb = ACCENT_CYAN

    # -------------------------------------------------------------
    # SLIDE 6: LIVE OPERATIONS DASHBOARD
    # -------------------------------------------------------------
    s6 = prs.slides.add_slide(blank_layout)
    apply_background(s6)
    add_header(s6, "Operations Center: Real-Time Intelligence Dashboard")

    # Left: Large Screenshot of live dashboard
    if os.path.exists(img_dashboard):
        s6.shapes.add_picture(img_dashboard, Inches(0.8), Inches(1.6), width=Inches(8.0))

    # Right: Annotated Features
    add_card(s6, Inches(9.0), Inches(1.6), Inches(3.533), Inches(5.2))
    b_feat = s6.shapes.add_textbox(Inches(9.15), Inches(1.8), Inches(3.2), Inches(4.8))
    tf_f = b_feat.text_frame
    tf_f.word_wrap = True
    p = tf_f.paragraphs[0]
    p.text = "OPERATIONAL CONTROLS"
    p.font.size = Pt(13)
    p.font.bold = True
    p.font.color.rgb = ACCENT_CYAN

    feats = [
        ("Multi-Camera Switcher", "1-click toggling between CAM-01 (Mall 40p), CAM-02 (Queue 20p), CAM-03 (Shibuya), and local webcam."),
        ("Dynamic Overlays", "Instant keyboard shortcuts: [F] for Optical Flow vectors, [H] for Density Heatmaps."),
        ("Circular Risk Gauge", "Dynamic SVG gauge displaying real-time risk index (0-100) with Safe/Warning/Critical color coding."),
        ("Acoustic Alert Chimes", "Web Audio API dual-tone synthesizer with Sound ON/Muted controls ([M] hotkey)."),
        ("4x4 Zone Matrix", "Real-time 16-cell spatial density monitor identifying the peak active bottleneck.")
    ]
    for tit, dsc in feats:
        p = tf_f.add_paragraph()
        p.text = "▸ " + tit
        p.font.size = Pt(11)
        p.font.bold = True
        p.font.color.rgb = TEXT_WHITE
        p.space_before = Pt(6)
        p_sub = tf_f.add_paragraph()
        p_sub.text = dsc
        p_sub.font.size = Pt(9.5)
        p_sub.font.color.rgb = TEXT_MUTED

    # -------------------------------------------------------------
    # SLIDE 7: HIGH-DENSITY CROWD PERCEPTION
    # -------------------------------------------------------------
    s7 = prs.slides.add_slide(blank_layout)
    apply_background(s7)
    add_header(s7, "Perception Engine: Dense Crowd Detection & Tracking")

    # Left: Screenshot of dense crowd tracking
    if os.path.exists(img_tracking):
        s7.shapes.add_picture(img_tracking, Inches(0.8), Inches(1.6), width=Inches(7.8))

    # Right: Technical Cards
    add_card(s7, Inches(8.8), Inches(1.6), Inches(3.733), Inches(5.2))
    b_trk = s7.shapes.add_textbox(Inches(8.95), Inches(1.8), Inches(3.4), Inches(4.8))
    tf_trk = b_trk.text_frame
    tf_trk.word_wrap = True
    p = tf_trk.paragraphs[0]
    p.text = "TRACKING SPECIFICATIONS"
    p.font.size = Pt(13)
    p.font.bold = True
    p.font.color.rgb = GREEN_SUCCESS

    trk_specs = [
        ("High-Headcount Concurrency", "Successfully tracks 35–40 concurrent individuals in dense concourses without dropped detections."),
        ("Centroid Trajectory Tracing", "Maintains unique tracking IDs (#13, #73, #114) and renders persistent trajectory tails displaying pedestrian paths."),
        ("Occlusion Handling", "Euclidean distance matching with velocity momentum projection prevents identity swapping in tightly packed crowds."),
        ("Sub-Pixel Motion Estimation", "Vector tails illustrate exact velocity magnitude and direction vectors in real time.")
    ]
    for tit, dsc in trk_specs:
        p = tf_trk.add_paragraph()
        p.text = "✔ " + tit
        p.font.size = Pt(11)
        p.font.bold = True
        p.font.color.rgb = TEXT_WHITE
        p.space_before = Pt(8)
        p_sub = tf_trk.add_paragraph()
        p_sub.text = dsc
        p_sub.font.size = Pt(10)
        p_sub.font.color.rgb = TEXT_MUTED

    # -------------------------------------------------------------
    # SLIDE 8: 4x4 SPATIAL ZONE MATRIX
    # -------------------------------------------------------------
    s8 = prs.slides.add_slide(blank_layout)
    apply_background(s8)
    add_header(s8, "Spatial Intelligence: 4x4 Zone Matrix & Bottleneck Isolation")

    # Left: Explanation & Why Spatial Matters
    add_card(s8, Inches(0.8), Inches(1.6), Inches(6.0), Inches(5.2))
    b_zone = s8.shapes.add_textbox(Inches(1.0), Inches(1.8), Inches(5.6), Inches(4.8))
    tf_z = b_zone.text_frame
    tf_z.word_wrap = True
    p = tf_z.paragraphs[0]
    p.text = "WHY GLOBAL HEADCOUNTS FAIL"
    p.font.size = Pt(14)
    p.font.bold = True
    p.font.color.rgb = AMBER_WARN

    z_pts = [
        ("Localized Choke Points", "Stampedes happen at bottlenecks (doors, stairs, turnstiles). A global count hides localized life-threatening densities."),
        ("16 Discrete Micro-Sectors", "The scene is partitioned into a 4x4 matrix (Z0_0 to Z3_3), monitoring micro-density and speed independently."),
        ("Peak Zone Isolation", "System automatically flags the highest-risk zone (e.g. PEAK: Z0_1) for direct security dispatch."),
        ("Granular Telemetry Stream", "Every 100ms, all 16 zones broadcast local headcounts, speeds, and densities over WebSockets.")
    ]
    for tit, dsc in z_pts:
        p = tf_z.add_paragraph()
        p.text = "• " + tit
        p.font.size = Pt(12)
        p.font.bold = True
        p.font.color.rgb = TEXT_WHITE
        p.space_before = Pt(8)
        p_sub = tf_z.add_paragraph()
        p_sub.text = dsc
        p_sub.font.size = Pt(10.5)
        p_sub.font.color.rgb = TEXT_MUTED

    # Right: Zone Grid Graphic
    if os.path.exists(img_zones):
        s8.shapes.add_picture(img_zones, Inches(7.1), Inches(1.6), width=Inches(5.4))
    t_zcap = s8.shapes.add_textbox(Inches(7.1), Inches(6.0), Inches(5.4), Inches(0.6))
    p_zcap = t_zcap.text_frame.paragraphs[0]
    p_zcap.text = "Live 4x4 zone overlay segmenting physical space into discrete risk zones."
    p_zcap.font.size = Pt(10)
    p_zcap.font.color.rgb = TEXT_MUTED

    # -------------------------------------------------------------
    # SLIDE 9: INCIDENT ALERTS & FORENSIC SNAPSHOTS
    # -------------------------------------------------------------
    s9 = prs.slides.add_slide(blank_layout)
    apply_background(s9)
    add_header(s9, "Incident Forensics: Automated Snapshots & Alert Logs")

    # Left: Alerts screenshot
    if os.path.exists(img_alerts):
        s9.shapes.add_picture(img_alerts, Inches(0.8), Inches(1.6), width=Inches(7.8))

    # Right: Forensics Capabilities
    add_card(s9, Inches(8.8), Inches(1.6), Inches(3.733), Inches(5.2))
    b_alt = s9.shapes.add_textbox(Inches(8.95), Inches(1.8), Inches(3.4), Inches(4.8))
    tf_alt = b_alt.text_frame
    tf_alt.word_wrap = True
    p = tf_alt.paragraphs[0]
    p.text = "CRITICAL RESPONSE AUDITING"
    p.font.size = Pt(13)
    p.font.bold = True
    p.font.color.rgb = ROSE_CRIT

    alt_pts = [
        ("Auto-Captured Evidence", "When composite risk exceeds threshold (70.0), system automatically freezes and archives high-res annotated JPEGs to disk."),
        ("Multi-Tier Risk Badging", "Visual notifications display exact zone coordinates, timestamp, and severity level (Warning vs High Risk)."),
        ("Dual-Tone Acoustic Alert", "Web Audio API triggers urgent harmonic alarm frequencies to grab operator attention instantly."),
        ("Immutable Audit Log", "All incidents are timestamped and indexed in disk manifests for official post-event investigations.")
    ]
    for tit, dsc in alt_pts:
        p = tf_alt.add_paragraph()
        p.text = "▸ " + tit
        p.font.size = Pt(11)
        p.font.bold = True
        p.font.color.rgb = TEXT_WHITE
        p.space_before = Pt(8)
        p_sub = tf_alt.add_paragraph()
        p_sub.text = dsc
        p_sub.font.size = Pt(10)
        p_sub.font.color.rgb = TEXT_MUTED

    # -------------------------------------------------------------
    # SLIDE 10: EXECUTIVE AUDIT REPORT & ANALYTICS
    # -------------------------------------------------------------
    s10 = prs.slides.add_slide(blank_layout)
    apply_background(s10)
    add_header(s10, "Post-Incident Dossier: Official Executive Safety Report")

    # Left: Report Screenshot
    if os.path.exists(img_report):
        s10.shapes.add_picture(img_report, Inches(0.8), Inches(1.6), width=Inches(7.8))

    # Right: Audit Report Features
    add_card(s10, Inches(8.8), Inches(1.6), Inches(3.733), Inches(5.2))
    b_rep = s10.shapes.add_textbox(Inches(8.95), Inches(1.8), Inches(3.4), Inches(4.8))
    tf_rep = b_rep.text_frame
    tf_rep.word_wrap = True
    p = tf_rep.paragraphs[0]
    p.text = "AUDIT DOSSIER CAPABILITIES"
    p.font.size = Pt(13)
    p.font.bold = True
    p.font.color.rgb = ACCENT_CYAN

    rep_pts = [
        ("1-Click PDF Generation", "Generates comprehensive, court-admissible PDF safety audits via headless Chrome printing."),
        ("Risk Trajectory Curves", "Plots time-series curves of composite hazard score R_z[t] against warning (40) and critical (70) thresholds."),
        ("Concurrent Headcount Trajectory", "Visualizes influx surges, peak person volumes, and evacuation curve decay."),
        ("Session Summary Telemetry", "Documents Peak Risk, Peak Headcount, Average Density, and Monitored Frame counts.")
    ]
    for tit, dsc in rep_pts:
        p = tf_rep.add_paragraph()
        p.text = "✔ " + tit
        p.font.size = Pt(11)
        p.font.bold = True
        p.font.color.rgb = TEXT_WHITE
        p.space_before = Pt(8)
        p_sub = tf_rep.add_paragraph()
        p_sub.text = dsc
        p_sub.font.size = Pt(10)
        p_sub.font.color.rgb = TEXT_MUTED

    # -------------------------------------------------------------
    # SLIDE 11: HARDWARE ACCELERATION & BENCHMARKS
    # -------------------------------------------------------------
    s11 = prs.slides.add_slide(blank_layout)
    apply_background(s11)
    add_header(s11, "Engineering Rigor: Apple Silicon MPS GPU Benchmarks")

    # 3 Benchmark Metric Cards
    bm_cards = [
        ("YOLOv8s INFERENCE", "113.5 ms", "25.0 ms", "4.5x FASTER", "CPU vs Apple MPS GPU", ACCENT_CYAN),
        ("FARNEBÄCK OPTICAL FLOW", "102.9 ms", "27.3 ms", "3.8x FASTER", "1080p Full vs 0.5x Downsampled", GREEN_SUCCESS),
        ("END-TO-END THROUGHPUT", "4.8 FPS", "20.0 FPS", "4.2x BOOST", "Unoptimized vs Edge GPU", AMBER_WARN)
    ]
    bm_w = Inches(3.7)
    for idx, (title, before, after, speedup, comp, color) in enumerate(bm_cards):
        c_left = Inches(0.8 + idx * (3.7 + 0.3))
        add_card(s11, c_left, Inches(1.6), bm_w, Inches(4.0), fill_color=RGBColor(20, 29, 47), border_color=color)
        
        box = s11.shapes.add_textbox(c_left + Inches(0.15), Inches(1.8), bm_w - Inches(0.3), Inches(3.6))
        tf = box.text_frame
        tf.word_wrap = True
        
        p = tf.paragraphs[0]
        p.text = title
        p.font.size = Pt(12)
        p.font.bold = True
        p.font.color.rgb = color
        
        p2 = tf.add_paragraph()
        p2.text = speedup
        p2.font.size = Pt(28)
        p2.font.bold = True
        p2.font.color.rgb = TEXT_WHITE
        p2.space_before = Pt(8)
        
        p3 = tf.add_paragraph()
        p3.text = f"Before: {before}  ➔  Optimized: {after}"
        p3.font.size = Pt(12)
        p3.font.color.rgb = color
        p3.space_before = Pt(4)
        
        p4 = tf.add_paragraph()
        p4.text = comp
        p4.font.size = Pt(11)
        p4.font.color.rgb = TEXT_MUTED
        p4.space_before = Pt(12)

    # Bottom Architecture optimization notes
    add_card(s11, Inches(0.8), Inches(5.8), Inches(11.733), Inches(1.1), fill_color=RGBColor(24, 34, 53), border_color=RGBColor(59, 130, 246))
    bot_bm = s11.shapes.add_textbox(Inches(1.0), Inches(5.9), Inches(11.3), Inches(0.9))
    tf_bb = bot_bm.text_frame
    tf_bb.word_wrap = True
    p1 = tf_bb.paragraphs[0]
    p1.text = "ADDITIONAL ENGINEERING OPTIMIZATIONS:"
    p1.font.size = Pt(11)
    p1.font.bold = True
    p1.font.color.rgb = ACCENT_CYAN
    p2 = tf_bb.add_paragraph()
    p2.text = "• Zero Memory Leaks: Replaced unbounded tracking history lists with collections.deque(maxlen=2000) ring buffers.\n• Frame Dropping Prevention: VideoStream runs in decoupled background thread with OpenCV non-blocking reads."
    p2.font.size = Pt(10.5)
    p2.font.color.rgb = TEXT_BODY

    # -------------------------------------------------------------
    # SLIDE 12: EXPERIMENTAL VALIDATION & TEST SCENARIOS
    # -------------------------------------------------------------
    s12 = prs.slides.add_slide(blank_layout)
    apply_background(s12)
    add_header(s12, "Experimental Validation: Real-World Test Scenarios")

    scenarios = [
        ("SCENARIO 1: HIGH-DENSITY CONCOURSE", 
         "CAM-01: Commercial Mall Concourse",
         "Headcount: 38 Persons\nSpeed: 1.4 px/frame (Free walking)\nSpatial Density: 10.0%\nResulting Risk: 9.6 (SAFE)\nKey Outcome: Zero false alarms despite dense crowds.",
         GREEN_SUCCESS),
        ("SCENARIO 2: BOTTLENECK QUEUE CHOKING",
         "CAM-02: Temple Entrance Queue",
         "Headcount: 18 Persons\nSpeed: 0.2 px/frame (Kinetic Lock)\nSpatial Density: 48.5% (High localized)\nResulting Risk: 64.2 (WARNING)\nKey Outcome: Correctly flags impending crush.",
         AMBER_WARN),
        ("SCENARIO 3: PEDESTRIAN CROSSWALK FLOW",
         "CAM-03: Multi-Lane Crosswalk Intersection",
         "Headcount: 21 Persons\nSpeed: 1.2 px/frame (Free walking)\nSpatial Density: 6.8%\nResulting Risk: 8.0 (SAFE)\nKey Outcome: Correctly detects all street-level crossing pedestrians without false alarms.",
         ACCENT_CYAN)
    ]
    sc_w = Inches(3.7)
    for idx, (title, sub, details, color) in enumerate(scenarios):
        sc_left = Inches(0.8 + idx * (3.7 + 0.3))
        add_card(s12, sc_left, Inches(1.6), sc_w, Inches(5.2), fill_color=RGBColor(20, 29, 47), border_color=color)
        
        box = s12.shapes.add_textbox(sc_left + Inches(0.15), Inches(1.8), sc_w - Inches(0.3), Inches(4.8))
        tf = box.text_frame
        tf.word_wrap = True
        
        p = tf.paragraphs[0]
        p.text = title
        p.font.size = Pt(11)
        p.font.bold = True
        p.font.color.rgb = color
        
        p_s = tf.add_paragraph()
        p_s.text = sub
        p_s.font.size = Pt(13)
        p_s.font.bold = True
        p_s.font.color.rgb = TEXT_WHITE
        p_s.space_before = Pt(4)
        
        p_d = tf.add_paragraph()
        p_d.text = details
        p_d.font.size = Pt(11)
        p_d.font.color.rgb = TEXT_BODY
        p_d.space_before = Pt(12)

    # -------------------------------------------------------------
    # SLIDE 13: COMPARATIVE ANALYSIS VS STATE OF THE ART
    # -------------------------------------------------------------
    s13 = prs.slides.add_slide(blank_layout)
    apply_background(s13)
    add_header(s13, "Competitive Analysis: Comparison with Existing Solutions")

    # Table of comparison
    tbl_shape = s13.shapes.add_table(6, 4, Inches(0.8), Inches(1.6), Inches(11.733), Inches(5.2))
    tbl = tbl_shape.table
    tbl.columns[0].width = Inches(3.0)
    tbl.columns[1].width = Inches(2.8)
    tbl.columns[2].width = Inches(2.8)
    tbl.columns[3].width = Inches(3.133)

    headers = ["FEATURE CAPABILITY", "TRADITIONAL CCTV", "BASIC AI DETECTION", "OUR SYSTEM (CSM)"]
    for col_idx, h_text in enumerate(headers):
        cell = tbl.cell(0, col_idx)
        cell.fill.solid()
        cell.fill.fore_color.rgb = RGBColor(30, 41, 59)
        p = cell.text_frame.paragraphs[0]
        p.text = h_text
        p.font.size = Pt(12)
        p.font.bold = True
        p.font.color.rgb = ACCENT_CYAN if col_idx == 3 else TEXT_WHITE
        p.alignment = PP_ALIGN.CENTER

    row_data = [
        ("Real-Time Frame Rate", "25-30 FPS (Passive)", "5-10 FPS (CPU bound)", "20+ FPS (MPS GPU Edge)"),
        ("Spatial Granularity", "None (Single screen)", "Global bounding boxes", "4x4 Matrix (16 Discrete Zones)"),
        ("Immobilization / Velocity Lock", "Not measured", "Flagged as 'stationary'", "Velocity Decay Curve (Physical Lock)"),
        ("Compressive Asphyxia Model", "Unsupported", "Unsupported", "Non-linear time-pressure integration"),
        ("Forensics & Reporting", "Manual review", "Alert timestamp only", "Automated JPEGs + 1-Click PDF Dossier")
    ]
    for row_idx, r_vals in enumerate(row_data, start=1):
        for col_idx, val in enumerate(r_vals):
            cell = tbl.cell(row_idx, col_idx)
            cell.fill.solid()
            cell.fill.fore_color.rgb = RGBColor(22, 31, 50) if row_idx % 2 == 0 else RGBColor(18, 25, 42)
            p = cell.text_frame.paragraphs[0]
            p.text = val
            p.font.size = Pt(11)
            if col_idx == 3:
                p.font.bold = True
                p.font.color.rgb = GREEN_SUCCESS
            elif col_idx == 0:
                p.font.bold = True
                p.font.color.rgb = TEXT_WHITE
            else:
                p.font.color.rgb = TEXT_MUTED

    # -------------------------------------------------------------
    # SLIDE 14: CONCLUSION & VIVA DEFENSE SUMMARY
    # -------------------------------------------------------------
    s14 = prs.slides.add_slide(blank_layout)
    apply_background(s14)
    add_header(s14, "Conclusion & Project Defense Summary")

    # Left: Project Achievements
    add_card(s14, Inches(0.8), Inches(1.6), Inches(6.0), Inches(5.2))
    b_conc = s14.shapes.add_textbox(Inches(1.0), Inches(1.8), Inches(5.6), Inches(4.8))
    tf_c = b_conc.text_frame
    tf_c.word_wrap = True
    p = tf_c.paragraphs[0]
    p.text = "CORE DELIVERABLES & ACHIEVEMENTS"
    p.font.size = Pt(14)
    p.font.bold = True
    p.font.color.rgb = GREEN_SUCCESS

    achievements = [
        "100% Production-Ready: Completed end-to-end integration across Computer Vision, Telemetry, and Interactive Web HUD.",
        "Zero API Dependencies: Entirely self-contained pipeline runs offline on edge hardware without external cloud latency.",
        "Acoustic & Forensic Evidence: Dual-tone synthesized audio alerts coupled with automatic high-res snapshot capture.",
        "Academic & Mathematical Rigor: Physics-calibrated velocity decay curves and time-integrated asphyxia hazard modeling."
    ]
    for a in achievements:
        p = tf_c.add_paragraph()
        p.text = "✔ " + a
        p.font.size = Pt(12)
        p.font.color.rgb = TEXT_BODY
        p.space_before = Pt(10)

    # Right: Future Scope & Viva Invitation
    add_card(s14, Inches(7.1), Inches(1.6), Inches(5.4), Inches(5.2))
    b_fut = s14.shapes.add_textbox(Inches(7.3), Inches(1.8), Inches(5.0), Inches(4.8))
    tf_fut = b_fut.text_frame
    tf_fut.word_wrap = True
    p = tf_fut.paragraphs[0]
    p.text = "FUTURE ROADMAP & DEMONSTRATION"
    p.font.size = Pt(14)
    p.font.bold = True
    p.font.color.rgb = ACCENT_CYAN

    future_pts = [
        ("Multi-Camera Re-Identification (ReID)", "Tracking pedestrian flow across adjacent cameras and corridors."),
        ("3D LiDAR Point Cloud Fusion", "Volumetric density estimation invariant to extreme lighting and smoke."),
        ("Drone Aerial Surveillance Integration", "Rapid-deployment edge monitoring for open-air religious and sporting festivals."),
        ("Live Demonstration Ready", "System is actively streaming live at localhost:8080 with multi-camera controls.")
    ]
    for tit, dsc in future_pts:
        p = tf_fut.add_paragraph()
        p.text = "▸ " + tit
        p.font.size = Pt(12)
        p.font.bold = True
        p.font.color.rgb = TEXT_WHITE
        p.space_before = Pt(8)
        p_sub = tf_fut.add_paragraph()
        p_sub.text = dsc
        p_sub.font.size = Pt(10.5)
        p_sub.font.color.rgb = TEXT_MUTED

    # Save to all requested file targets
    for p_path in output_pptx_paths:
        prs.save(p_path)
        print(f"Presentation saved successfully to: {p_path}")

if __name__ == "__main__":
    target_files = [
        "Crowd_Safety_Monitor_Final_Review.pptx",
        "Crowd_Safety_Monitor_Review2_Extended.pptx",
        "Crowd_Safety_Monitor_Review2.pptx"
    ]
    build_presentation(target_files)
