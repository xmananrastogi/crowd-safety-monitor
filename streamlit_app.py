"""
Streamlit dashboard for the Crowd Safety Monitoring system.
Contains both the CCTV Monitor and the Academic Signals Analysis Report.
Upgraded for Multi-Zone Architecture 2.0.
"""
import streamlit as st
import cv2
import pandas as pd
import time
from datetime import datetime
import tempfile
import os

import config
from core.video import VideoStream
from app.pipeline import CrowdSafetyPipeline

st.set_page_config(page_title="Crowd Safety CCTV v2", layout="wide", initial_sidebar_state="expanded")

st.title("🛡️ Crowd Safety Monitoring System (Multi-Zone)")

# --- SIDEBAR CONFIGURATION ---
st.sidebar.header("⚙️ Configuration")

st.sidebar.markdown("### 📹 Video Source")
upload_option = st.sidebar.radio("Input Type", ["Default Test Video", "Upload CCTV Video", "Live Webcam"], label_visibility="collapsed")
uploaded_file = None
if upload_option == "Upload CCTV Video":
    uploaded_file = st.sidebar.file_uploader("Upload Video (.mp4, .avi, .mov)", type=["mp4", "avi", "mov"])
    
st.sidebar.markdown("### 🧮 Risk Model")
risk_model_ui = st.sidebar.selectbox("Experimental Risk Model", ["Linear", "Interaction", "Persistence"], index=["Linear", "Interaction", "Persistence"].index(config.RISK_MODEL), label_visibility="collapsed")
st.sidebar.markdown("---")
w_d = st.sidebar.number_input("Density Weight ($w_1$)", 0.0, 1.0, config.WEIGHT_DENSITY, 0.05)
w_c = st.sidebar.number_input("Congestion Weight ($w_2$)", 0.0, 1.0, config.WEIGHT_CONGESTION, 0.05)
w_t = st.sidebar.number_input("Duration Weight ($w_3$)", 0.0, 1.0, config.WEIGHT_DURATION, 0.05)

if abs((w_d + w_c + w_t) - 1.0) > 1e-5:
    st.sidebar.error("Weights must sum exactly to 1.0!")

filter_window = st.sidebar.slider("Moving-Average Window ($N$)", 1, 60, config.MOVING_AVERAGE_WINDOW)
ewma_alpha = st.sidebar.slider("EWMA Alpha ($\\alpha$)", 0.01, 1.0, config.EWMA_ALPHA, 0.01)
thresh_d = st.sidebar.slider("Density Threshold ($\tau_D$)", 0.0, 100.0, config.DURATION_THRESHOLD_DENSITY)
thresh_c = st.sidebar.slider("Congestion Threshold ($\tau_C$)", 0.0, 100.0, config.DURATION_THRESHOLD_CONGESTION)
persistence_limit = st.sidebar.slider("State Machine Persistence (frames)", 10, 300, config.PERSISTENCE_LIMIT_FRAMES)
risk_alert_persistence = st.sidebar.slider("Risk Alert Persistence (frames)", 1, 60, config.RISK_ALERT_PERSISTENCE)

st.sidebar.markdown("### Spatial Zones (Grid)")
grid_rows = st.sidebar.number_input("Grid Rows", 1, 10, config.GRID_SIZE[0])
grid_cols = st.sidebar.number_input("Grid Columns", 1, 10, config.GRID_SIZE[1])
disabled_zones_str = st.sidebar.text_input("Disabled Zones (comma-separated)", ", ".join(config.DISABLED_ZONES))

st.sidebar.markdown("### Rendering")
visualize_hsv = st.sidebar.checkbox("Show Dense Flow HSV Heatmap", value=False)

st.sidebar.markdown("### Experimental Modules")
enable_anomaly = st.sidebar.checkbox("Enable Statistical Anomaly Detector", value=config.ENABLE_ANOMALY_DETECTION)
st.sidebar.info("💡 **Anomaly Limitations**: The Z-score anomaly detector mathematically assumes the first 10 seconds of video perfectly represent a 'Safe/Normal' baseline. If the video starts already congested, the baseline will be corrupted.")

start_btn = st.sidebar.button("▶️ Start CCTV Feed", type="primary")
stop_btn = st.sidebar.button("⏹️ Stop Feed")

tab_cctv, tab_analysis = st.tabs(["📷 CCTV Monitor", "📚 Signals & Systems Analysis"])

with tab_cctv:
    col_vid, col_panel = st.columns([7, 3])

    with col_vid:
        st.markdown("### 📷 CAMERA 01: MAIN CONCOURSE")
        video_placeholder = st.empty()

    with col_panel:
        st.markdown("### 📡 SAFETY TELEMETRY")
        ui_zone_selector = st.empty() # Placeholder for zone selection dropdown
        telemetry_container = st.empty()
        st.markdown("---")
        st.markdown("### 📈 SIGNAL HISTORY")
        chart_placeholder = st.empty()

if start_btn and abs((w_d + w_c + w_t) - 1.0) <= 1e-5:
    # 1. Update config
    config.RISK_MODEL = risk_model_ui
    config.WEIGHT_DENSITY = w_d
    config.WEIGHT_CONGESTION = w_c
    config.WEIGHT_DURATION = w_t
    config.MOVING_AVERAGE_WINDOW = filter_window
    config.EWMA_ALPHA = ewma_alpha
    config.DURATION_THRESHOLD_DENSITY = thresh_d
    config.DURATION_THRESHOLD_CONGESTION = thresh_c
    config.PERSISTENCE_LIMIT_FRAMES = persistence_limit
    config.RISK_ALERT_PERSISTENCE = risk_alert_persistence
    config.ENABLE_ANOMALY_DETECTION = enable_anomaly
    
    config.USE_GRID = True
    config.GRID_SIZE = (grid_rows, grid_cols)
    config.DISABLED_ZONES = [z.strip() for z in disabled_zones_str.split(",") if z.strip()]
    
    active_video_path = config.VIDEO_SOURCE
    if upload_option == "Live Webcam":
        active_video_path = 0
    elif upload_option == "Upload CCTV Video" and uploaded_file is not None:
        tfile = tempfile.NamedTemporaryFile(delete=False, suffix='.mp4')
        tfile.write(uploaded_file.read())
        active_video_path = tfile.name
        
    video_stream = VideoStream(active_video_path)
    
    pipeline = CrowdSafetyPipeline(video_resolution=(video_stream.width, video_stream.height))
    st.session_state['pipeline_history'] = pipeline.history
    
    # Store the selected zone for the UI dropdown
    active_zone = list(pipeline.zone_manager.zones.keys())[0] if pipeline.zone_manager.zones else "Global"
    
    try:
        while True:
            if stop_btn:
                break
                
            data = video_stream.read_frame()
            if data is None:
                break
                
            results = pipeline.process_frame(data['frame'], data['frame_number'], data['timestamp_ms'])
            if results is None:
                continue
                
            fps = results['fps']
            zones_data = results['zones']
            
            # Since Streamlit's selectbox inside a tight while loop blocks execution, 
            # we will just cycle through zones or show the highest risk zone automatically.
            # Let's find the zone with the highest risk to display in the telemetry panel.
            highest_risk_zone_name = max(zones_data.keys(), key=lambda z: zones_data[z]['record']['R_z[n]'])
            rec = zones_data[highest_risk_zone_name]['record']
            
            risk = rec['R_z[n]']
            cat = rec['Risk_Category']
            congestion_state = rec.get('Congestion_State', 'NORMAL')
            
            # --- 1. Compact Telemetry Panel ---
            if cat == "High Risk":
                color_hex = "#ff4b4b"
            elif cat == "Warning":
                color_hex = "#ffa500"
            else:
                color_hex = "#00cc66"
                
            # State color coding
            if congestion_state == "PERSISTENT CONGESTION":
                state_color = "#ff4b4b"
            elif congestion_state == "DEVELOPING":
                state_color = "#ffa500"
            else:
                state_color = "#00cc66"
                
            telemetry_html = f"""
            <div style="background: linear-gradient(145deg, #111827, #1f2937); padding: 25px; border-radius: 16px; border: 1px solid {color_hex}40; box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.37); color: #eee; font-family: 'Inter', sans-serif;">
                <h4 style="margin: 0; color: #9ca3af; text-align: center; text-transform: uppercase; letter-spacing: 1px; font-size: 0.85em;">Selected Zone: <span style="color: #fff;">{highest_risk_zone_name}</span></h4>
                <div style="text-align: center; margin: 20px 0;">
                    <div style="font-size: 0.85em; color: #9ca3af; text-transform: uppercase; letter-spacing: 2px;">Overall Risk Level</div>
                    <h1 style="margin: 5px 0; color: {color_hex}; font-size: 4.5em; text-shadow: 0 0 20px {color_hex}60; line-height: 1;">{risk:.1f}</h1>
                    <h3 style="margin: 0; color: {color_hex}; letter-spacing: 3px; text-transform: uppercase; font-size: 1.2em;">{cat}</h3>
                    <div style="margin-top: 12px; display: inline-block; padding: 6px 16px; border-radius: 20px; background-color: {state_color}15; color: {state_color}; border: 1px solid {state_color}40; font-size: 0.8em; font-weight: bold; letter-spacing: 1px;">STATE: {congestion_state}</div>
                </div>
                
                <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 15px; margin-top: 30px;">
                    <div style="background: rgba(255,255,255,0.03); padding: 15px; border-radius: 12px; border-left: 4px solid #3b82f6;">
                        <div style="font-size: 0.75em; color: #9ca3af; text-transform: uppercase;">Density $D_z[n]$</div>
                        <div style="font-size: 1.6em; font-weight: bold; color: #fff; margin-top: 5px;">{rec['D_smoothed_z[n]']:.1f}%</div>
                        <div style="font-size: 0.75em; color: #6b7280; margin-top: 2px;">Count: {rec['D_raw_z[n]']}</div>
                    </div>
                    <div style="background: rgba(255,255,255,0.03); padding: 15px; border-radius: 12px; border-left: 4px solid #f59e0b;">
                        <div style="font-size: 0.75em; color: #9ca3af; text-transform: uppercase;">Congestion $C_z[n]$</div>
                        <div style="font-size: 1.6em; font-weight: bold; color: #fff; margin-top: 5px;">{rec['C_smoothed_z[n]']:.1f}%</div>
                        <div style="font-size: 0.75em; color: #6b7280; margin-top: 2px;">Motion: {rec['M_raw_z[n]']:.2f}</div>
                    </div>
                    <div style="background: rgba(255,255,255,0.03); padding: 15px; border-radius: 12px; border-left: 4px solid #8b5cf6;">
                        <div style="font-size: 0.75em; color: #9ca3af; text-transform: uppercase;">Duration $T_z[n]$</div>
                        <div style="font-size: 1.6em; font-weight: bold; color: #fff; margin-top: 5px;">{rec['T_z[n]']:.1f}%</div>
                        <div style="font-size: 0.75em; color: #6b7280; margin-top: 2px;">Threshold Exceeded</div>
                    </div>
                    <div style="background: rgba(239,68,68,0.08); padding: 15px; border-radius: 12px; border-left: 4px solid #ef4444;">
                        <div style="font-size: 0.75em; color: #ef4444; text-transform: uppercase; font-weight: bold;">⚠️ Suffocation Risk</div>
                        <div style="font-size: 1.6em; font-weight: bold; color: #ef4444; margin-top: 5px; text-shadow: 0 0 10px rgba(239, 68, 68, 0.4);">{rec.get('Suffocation_Risk_z[n]', 0.0):.1f}%</div>
                        <div style="font-size: 0.75em; color: #ef4444; opacity: 0.7; margin-top: 2px;">Compressive Asphyxia</div>
                    </div>
                </div>
                
                <div style="margin-top: 25px; border-top: 1px solid rgba(255,255,255,0.1); padding-top: 15px;">
                    <div style="display: flex; justify-content: space-between; font-size: 0.85em; margin-bottom: 10px; background: rgba(0,0,0,0.2); padding: 8px 12px; border-radius: 6px;">
                        <span style="color: #9ca3af;">Average Speed</span> 
                        <span style="color: #fff; font-weight: bold;">{rec.get('Tracked_Speed_z[n]', 0.0):.2f} px/f</span>
                    </div>
                    <div style="display: flex; justify-content: space-between; font-size: 0.85em; margin-bottom: 10px; background: rgba(0,0,0,0.2); padding: 8px 12px; border-radius: 6px;">
                        <span style="color: #9ca3af;">Dominant Flow</span> 
                        <span style="color: #fff; font-weight: bold;">{rec.get('Dominant_Dir_z[n]', 0.0):.0f}° <span style="color: #6b7280; font-weight: normal;">(Cons: {rec.get('Dir_Consistency_z[n]', 0.0):.2f})</span></span>
                    </div>
                    <div style="display: flex; justify-content: space-between; font-size: 0.85em; background: rgba(234, 179, 8, 0.08); padding: 8px 12px; border-radius: 6px;">
                        <span style="color: #9ca3af;">Anomalies</span> 
                        <span style="color: #eab308; font-weight: bold;">{rec.get('Abnormal_Movement_Indicators', 'None')}</span>
                    </div>
                </div>
                
                <p style="text-align: center; color: #4b5563; margin-top: 25px; font-size: 0.75em; text-transform: uppercase; letter-spacing: 1px;">Engine: {config.RISK_MODEL} &nbsp;•&nbsp; FPS: {fps:.1f}</p>
            </div>
            """
            telemetry_container.markdown(telemetry_html, unsafe_allow_html=True)
            
            # --- 2. Annotated Video Feed ---
            frame = data['frame']
            
            # Draw the spatial zones
            frame = pipeline.zone_manager.draw_zones(frame)
            
            # Draw YOLO boxes with IDs
            frame = pipeline.detector.draw_boxes(frame, results['global_boxes'], results['global_ids'], results['global_confidences'])
            
            # Draw Flow
            if visualize_hsv:
                frame = pipeline.motion_estimator.draw_flow_hsv(frame, results['flow'])
            else:
                frame = pipeline.motion_estimator.draw_flow_arrows(frame, results['flow'])
            
            current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            cv2.putText(frame, f"CAM01 REC | {current_time} | {fps:.1f} FPS", (20, 30), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
                        
            video_placeholder.image(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB), use_container_width=True)
            
            # --- 3. Live Charts ---
            df = pd.DataFrame(pipeline.history).tail(200) # Contains records for ALL zones
            
            with chart_placeholder.container():
                # Pivot to plot Risk Score per Zone
                if not df.empty:
                    risk_pivot = df.pivot(index='frame_index_n', columns='zone_z', values='R_z[n]')
                    st.line_chart(risk_pivot)
            
            time.sleep(0.01)
            
    except Exception as e:
        st.error(f"Error during processing: {e}")
    finally:
        video_stream.release()

# ==========================================
# TAB 2: SIGNALS & SYSTEMS ACADEMIC ANALYSIS
# ==========================================
with tab_analysis:
    st.header("Signals & Systems Mathematical Analysis (Zone-Based)")
    
    if 'pipeline_history' not in st.session_state or len(st.session_state['pipeline_history']) == 0:
        st.info("⚠️ Please run the CCTV feed first.")
    else:
        df_all = pd.DataFrame(st.session_state['pipeline_history'])
        
        # Select a zone to analyze
        zones = df_all['zone_z'].unique()
        selected_zone = st.selectbox("Select Zone for Analysis", zones)
        
        df = df_all[df_all['zone_z'] == selected_zone].set_index('frame_index_n')
        
        group_delay = (config.MOVING_AVERAGE_WINDOW - 1) / 2.0
        st.markdown(f"**Filter Information:** FIR Window ($N$) = {config.MOVING_AVERAGE_WINDOW}, IIR EWMA ($\\alpha$) = {config.EWMA_ALPHA}")
        st.markdown(f"**FIR Group Delay:** $\\tau_g = \\frac{{N-1}}{{2}} = {group_delay}$ frames.")
        
        # 1. Raw Density
        st.subheader(f"Raw Count $D_{{raw, z}}[n]$ for {selected_zone}")
        st.line_chart(df['D_raw_z[n]'], height=250)
        
        # 2. Normalized Density (Comparative Filter Analysis)
        st.subheader("Density Signal $D_z[n]$ (Raw vs FIR vs EWMA)")
        st.line_chart(df[['D_z[n]', 'D_smoothed_z[n]', 'D_ewma_z[n]']], height=250)
        
        # 3. Raw Motion
        st.subheader("Raw Optical-Flow/Motion Signal $M_z[n]$")
        st.line_chart(df['M_raw_z[n]'], height=250)
        
        # 4. Congestion Signal (Comparative Filter Analysis)
        st.subheader("Congestion Signal $C_z[n]$ (Raw vs FIR vs EWMA)")
        st.line_chart(df[['C_z[n]', 'C_smoothed_z[n]', 'C_ewma_z[n]']], height=250)
        
        # 5. Duration Tracker
        st.subheader("Congestion-Duration Signal $T_z[n]$")
        st.line_chart(df['T_z[n]'], height=250)
        
        # 7. Final Risk
        st.subheader("Final Risk Signal $R_z[n]$")
        st.line_chart(df['R_z[n]'], height=250)
        
        # 8. Tracked Speed
        if 'Tracked_Speed_z[n]' in df.columns:
            st.subheader("Average Tracked Speed (pixels/frame)")
            st.line_chart(df['Tracked_Speed_z[n]'], height=250)
            
        # 9. Directional Consistency & Dominant Direction
        if 'Dir_Consistency_z[n]' in df.columns:
            st.subheader("Directional Consistency (0.0 to 1.0)")
            st.line_chart(df['Dir_Consistency_z[n]'], height=250)
            
        if 'Dominant_Dir_z[n]' in df.columns:
            st.subheader("Dominant Movement Direction (Degrees)")
            st.line_chart(df['Dominant_Dir_z[n]'], height=250)
            
        # 10. Experimental Anomaly
        if 'Anomaly_Score_z[n]' in df.columns:
            st.subheader("Statistical Anomaly Score (Z-Score derived)")
            st.line_chart(df['Anomaly_Score_z[n]'], height=250)
            
        # 11. Suffocation Risk
        if 'Suffocation_Risk_z[n]' in df.columns:
            st.subheader("⚠️ Compressive Asphyxia (Suffocation) Risk (%)")
            st.line_chart(df['Suffocation_Risk_z[n]'], height=250)
