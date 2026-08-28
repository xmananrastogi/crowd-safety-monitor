"""
Streamlit dashboard for Crowd Safety Monitoring.
Run this using: streamlit run main.py
"""
import streamlit as st
import cv2
import numpy as np
import time
import pandas as pd

import config
from core.video import VideoStream
from app.pipeline import CrowdSafetyPipeline

st.set_page_config(page_title="Crowd Safety Monitor", layout="wide")

st.title("Vision-Based Crowd Safety Monitoring")
st.markdown("Monitoring Spatial Density, Temporal Congestion, and Duration to estimate Risk.")

# Sidebar for config tuning
st.sidebar.header("Signal & System Configuration")
st.sidebar.markdown("Tune the weights for the Risk Equation: $R[n] = w_1D[n] + w_2C[n] + w_3T[n]$")

w_d = st.sidebar.slider("Density Weight (w1)", 0.0, 1.0, config.WEIGHT_DENSITY)
w_c = st.sidebar.slider("Congestion Weight (w2)", 0.0, 1.0, config.WEIGHT_CONGESTION)
w_t = st.sidebar.slider("Duration Weight (w3)", 0.0, 1.0, config.WEIGHT_DURATION)

# Normalize weights so they sum to 1.0 (optional but good practice)
total_w = w_d + w_c + w_t
if total_w > 0:
    w_d, w_c, w_t = w_d/total_w, w_c/total_w, w_t/total_w

# Initialize pipeline in session state so it persists across reruns
if 'pipeline' not in st.session_state:
    st.session_state.pipeline = CrowdSafetyPipeline()

if 'video_stream' not in st.session_state:
    st.session_state.video_stream = None

col1, col2 = st.columns([2, 1])

with col1:
    st.subheader("Live CCTV Feed")
    video_placeholder = st.empty()

with col2:
    st.subheader("Real-Time Signals")
    risk_metric = st.empty()
    density_metric = st.empty()
    congestion_metric = st.empty()
    
    st.subheader("Signal Plot")
    chart_placeholder = st.line_chart(pd.DataFrame(columns=["Density", "Congestion", "Risk"]))

# Start/Stop controls
start_btn = st.sidebar.button("Start Monitoring")
stop_btn = st.sidebar.button("Stop")

if start_btn:
    # We use a placeholder video (or webcam)
    st.session_state.video_stream = VideoStream(config.VIDEO_SOURCE)
    
    history = []
    
    while True:
        frame = st.session_state.video_stream.read_frame()
        if frame is None:
            st.warning("Video stream ended or cannot be read.")
            break
            
        # Process the frame
        # Temporarily override weights with UI values
        st.session_state.pipeline.signal_processor.calculate_risk = lambda d, c, t, wd, wc, wt: min((wd*d) + (wc*c) + (wt*t), 100.0)
        
        results = st.session_state.pipeline.process_frame(frame)
        
        # Draw bounding boxes
        display_frame = frame.copy()
        for box in results['boxes']:
            x1, y1, x2, y2 = map(int, box)
            cv2.rectangle(display_frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
            
        # Add overlay text
        cv2.putText(display_frame, f"Risk: {results['risk_category']}", (20, 40), 
                    cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255) if results['risk_score'] > 60 else (0, 255, 0), 2)
            
        # Convert BGR to RGB for Streamlit
        display_frame = cv2.cvtColor(display_frame, cv2.COLOR_BGR2RGB)
        video_placeholder.image(display_frame, channels="RGB", use_container_width=True)
        
        # Update metrics
        risk_color = "red" if results['risk_score'] > 60 else "orange" if results['risk_score'] > 30 else "green"
        risk_metric.markdown(f"### Risk Score: <span style='color:{risk_color}'>{results['risk_score']:.1f}% ({results['risk_category']})</span>", unsafe_allow_html=True)
        density_metric.write(f"**Smoothed Density:** {results['density']:.1f}%")
        congestion_metric.write(f"**Smoothed Congestion:** {results['congestion']:.1f}%")
        
        # Update Chart
        history.append({
            "Density": results['density'],
            "Congestion": results['congestion'],
            "Risk": results['risk_score']
        })
        if len(history) > 100:
            history.pop(0)
            
        chart_placeholder.line_chart(pd.DataFrame(history))

        if stop_btn:
            break

if stop_btn and st.session_state.video_stream is not None:
    st.session_state.video_stream.release()
    st.session_state.video_stream = None
    st.sidebar.success("Stopped monitoring.")
