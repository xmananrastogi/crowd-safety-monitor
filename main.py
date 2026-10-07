"""
Main Entry Point for the Crowd Safety Monitoring Pipeline.
Offline CLI processor that processes a video end-to-end.

Usage:
    python main.py --input data/sample_video.mp4 --output data/output
"""
import os
import argparse
import logging
import cv2
import pandas as pd
import matplotlib.pyplot as plt

import config
from core.video import VideoStream
from app.pipeline import CrowdSafetyPipeline

def setup_logging():
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(levelname)s] %(message)s',
        handlers=[logging.StreamHandler()]
    )

def plot_results(history, output_dir):
    """Generates the required plots from the CSV telemetry."""
    if not history:
        logging.warning("No history found to plot.")
        return
        
    df = pd.DataFrame(history)
    # Get the max risk zone per frame to represent the overall scene
    idx = df.groupby('frame_index_n')['R_z[n]'].idxmax()
    df = df.loc[idx].sort_values('frame_index_n').reset_index(drop=True)
    n = df['frame_index_n']
    
    # Create a 6-subplot figure
    fig, axes = plt.subplots(6, 1, figsize=(14, 24), sharex=True)
    
    # 1. Density Plot
    axes[0].plot(n, df['D_z[n]'], label='Raw Density ($D[n]$)', color='blue', alpha=0.3, linestyle='--')
    axes[0].plot(n, df['D_smoothed_z[n]'], label='Filtered Density', color='blue', linewidth=2)
    axes[0].set_title('Spatial Crowd Density')
    axes[0].set_ylabel('Density (%)')
    axes[0].legend()
    axes[0].grid(True, linestyle=':', alpha=0.6)
    
    # 2. Motion Plot
    axes[1].plot(n, df['M_raw_z[n]'], label='Raw Motion Magnitude ($M_{raw}[n]$)', color='green')
    axes[1].set_title('Temporal Crowd Motion (Optical Flow Magnitude)')
    axes[1].set_ylabel('Motion Magnitude')
    axes[1].legend()
    axes[1].grid(True, linestyle=':', alpha=0.6)
    
    # 3. Filtered Congestion Plot
    axes[2].plot(n, df['C_z[n]'], label='Raw Congestion', color='orange', alpha=0.3, linestyle='--')
    axes[2].plot(n, df['C_smoothed_z[n]'], label='Filtered Congestion ($C[n]$)', color='orange', linewidth=2)
    axes[2].set_title('Congestion Signal (Low Motion = High Congestion)')
    axes[2].set_ylabel('Congestion (%)')
    axes[2].legend()
    axes[2].grid(True, linestyle=':', alpha=0.6)
    
    # 4. Congestion Duration Plot
    axes[3].plot(n, df['T_z[n]'], label='Normalized Duration ($T[n]$)', color='purple', linewidth=2)
    axes[3].set_title('Abnormal Congestion Duration Tracking')
    axes[3].set_ylabel('Duration Score (%)')
    axes[3].legend()
    axes[3].grid(True, linestyle=':', alpha=0.6)
    
    # 5. Suffocation Risk Plot
    axes[4].plot(n, df.get('Suffocation_Risk_z[n]', [0]*len(n)), label='Suffocation Risk', color='red', linewidth=2)
    axes[4].set_title('Compressive Asphyxia (Suffocation) Risk')
    axes[4].set_ylabel('Risk (%)')
    axes[4].legend()
    axes[4].grid(True, linestyle=':', alpha=0.6)
    
    # 6. Risk Score Plot
    axes[5].plot(n, df['R_z[n]'], label='Total Risk ($R[n]$)', color='black', linewidth=2.5)
    axes[5].axhline(y=config.RISK_SAFE_MAX, color='green', linestyle='--', label='Safe Threshold')
    axes[5].axhline(y=config.RISK_WARN_MAX, color='orange', linestyle='--', label='Warning Threshold')
    axes[5].set_title('Overall Crowd Safety Risk Index')
    axes[5].set_xlabel('Discrete Time Step / Frame Index ($n$)')
    axes[5].set_ylabel('Risk Score (0-100)')
    axes[5].set_ylim(0, 105)
    axes[5].legend()
    axes[5].grid(True, linestyle=':', alpha=0.6)
    
    plt.tight_layout()
    plot_path = os.path.join(output_dir, 'pipeline_plots.png')
    plt.savefig(plot_path, dpi=300, bbox_inches='tight')
    logging.info(f"Saved pipeline plots to {plot_path}")
    plt.close()

def print_summary_statistics(history):
    """Calculates and prints final summary statistics."""
    if not history:
        return
        
    df = pd.DataFrame(history)
    idx = df.groupby('frame_index_n')['R_z[n]'].idxmax()
    df = df.loc[idx].sort_values('frame_index_n').reset_index(drop=True)
    
    logging.info("\n=============================================")
    logging.info("          FINAL SUMMARY STATISTICS           ")
    logging.info("=============================================")
    logging.info(f"Total Frames Processed: {len(df)}")
    
    # Averages & Maximums
    logging.info(f"Average Person Count:   {df['D_raw_z[n]'].mean():.1f} people/frame")
    logging.info(f"Maximum Density:        {df['D_z[n]'].max():.1f}%")
    logging.info(f"Average Motion:         {df['M_raw_z[n]'].mean():.2f}")
    logging.info(f"Maximum Duration:       {df['T_z[n]'].max():.1f}%")
    if 'Suffocation_Risk_z[n]' in df.columns:
        logging.info(f"Max Suffocation Risk:   {df['Suffocation_Risk_z[n]'].max():.1f}%")
    
    # Risk Metrics
    logging.info("--- Risk Metrics ---")
    logging.info(f"Maximum Risk Score:     {df['R_z[n]'].max():.1f}")
    logging.info(f"Average Risk Score:     {df['R_z[n]'].mean():.1f}")
    
    # States
    safe_frames = len(df[df['Risk_Category'] == 'Safe'])
    warn_frames = len(df[df['Risk_Category'] == 'Warning'])
    high_frames = len(df[df['Risk_Category'] == 'High Risk'])
    total = len(df)
    
    logging.info(f"Time in Safe State:     {safe_frames} frames ({(safe_frames/total)*100:.1f}%)")
    logging.info(f"Time in Warning State:  {warn_frames} frames ({(warn_frames/total)*100:.1f}%)")
    logging.info(f"Time in High Risk State:{high_frames} frames ({(high_frames/total)*100:.1f}%)")
    logging.info("=============================================\n")

def main():
    setup_logging()
    
    parser = argparse.ArgumentParser(description="End-to-End Crowd Safety Pipeline (CLI)")
    parser.add_argument('--input', type=str, required=True, help="Path to input video file")
    parser.add_argument('--output_dir', type=str, default="data/output", help="Directory to save outputs")
    args = parser.parse_args()
    
    input_path = args.input
    output_dir = args.output_dir
    os.makedirs(output_dir, exist_ok=True)
    
    if not os.path.exists(input_path):
        logging.error(f"Input video not found: {input_path}")
        return
        
    logging.info(f"Initializing pipeline for video: {input_path}")
    
    # 1. Initialize Reused Modules
    video_stream = VideoStream(input_path)
    pipeline = CrowdSafetyPipeline()
    
    # Setup VideoWriter
    first_data = video_stream.read_frame()
    if first_data is None:
        logging.error("Failed to read first frame.")
        return
        
    frame_h, frame_w = first_data['frame'].shape[:2]
    fps = video_stream.get_fps()
    
    output_video_path = os.path.join(output_dir, "annotated_output.mp4")
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    video_writer = cv2.VideoWriter(output_video_path, fourcc, fps, (frame_w, frame_h))
    
    # Re-initialize stream to process first frame again properly
    video_stream.release()
    video_stream = VideoStream(input_path)
    
    logging.info("Starting processing loop... (This may take a while depending on video length)")
    
    try:
        while True:
            data = video_stream.read_frame()
            if data is None:
                break # EOF
                
            frame = data['frame']
            
            # 2. Run the End-to-End Pipeline
            results = pipeline.process_frame(frame, data['frame_number'], data['timestamp_ms'])
            if results is None:
                continue
                
            # 3. Create Annotated Video Frame
            annotated_frame = pipeline.detector.draw_boxes(frame, results['boxes'], results['confidences'])
            annotated_frame = pipeline.motion_estimator.draw_flow_arrows(annotated_frame, results['flow'])
            
            # Draw Risk Status overlay
            risk = results['risk_score']
            category = results['risk_category']
            if category == 'High Risk':
                color = (0, 0, 255) # Red (BGR)
            elif category == 'Warning':
                color = (0, 165, 255) # Orange
            else:
                color = (0, 255, 0) # Green
                
            cv2.putText(annotated_frame, f"Risk: {risk:.1f} ({category})", (20, 50), 
                        cv2.FONT_HERSHEY_SIMPLEX, 1.2, color, 3)
                        
            video_writer.write(annotated_frame)
            
            # Progress tracking
            if data['frame_number'] % 30 == 0:
                logging.info(f"Processed {data['frame_number']} frames. Current Risk: {risk:.1f} ({category})")
                
    except Exception as e:
        logging.error(f"Error during processing: {e}")
        
    finally:
        # Cleanup
        video_stream.release()
        video_writer.release()
        logging.info(f"Saved annotated video to: {output_video_path}")
        
        # 4. Save CSV Telemetry
        csv_path = os.path.join(output_dir, "crowd_signals.csv")
        pipeline.save_to_csv(csv_path)
        
        # 5. Generate Plots
        plot_results(pipeline.history, output_dir)
        
        # 6. Final Summary Statistics
        print_summary_statistics(pipeline.history)

if __name__ == "__main__":
    main()
