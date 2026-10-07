import os
import sys
import pandas as pd
import numpy as np

# Ensure root is in path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import config
from core.video import VideoStream
from app.pipeline import CrowdSafetyPipeline

# 1. Scenario Configuration Map (using placeholder paths)
SCENARIOS = {
    "1_LowDensityNormal": {"video": "data/test_videos/1_low_density.mp4", "gt": "data/test_gt/1_gt.csv"},
    "2_HighDensityNormal": {"video": "data/test_videos/2_high_density_normal.mp4", "gt": "data/test_gt/2_gt.csv"},
    "3_HighDensitySlow": {"video": "data/test_videos/3_high_density_slow.mp4", "gt": "data/test_gt/3_gt.csv"},
    "4_HighDensityStationary": {"video": "data/test_videos/4_stationary.mp4", "gt": "data/test_gt/4_gt.csv"},
    "5_ShortCongestion": {"video": "data/test_videos/5_short_congestion.mp4", "gt": "data/test_gt/5_gt.csv"},
    "6_ProlongedCongestion": {"video": "data/test_videos/6_prolonged_congestion.mp4", "gt": "data/test_gt/6_gt.csv"},
    "7_EmptyScene": {"video": "data/test_videos/7_empty.mp4", "gt": "data/test_gt/7_gt.csv"},
    "8_SuddenMovement": {"video": "data/test_videos/8_sudden_move.mp4", "gt": "data/test_gt/8_gt.csv"},
    "9_DirectionReversal": {"video": "data/test_videos/9_reversal.mp4", "gt": "data/test_gt/9_gt.csv"},
    "10_LocalizedCongestion": {"video": "data/test_videos/10_local_congestion.mp4", "gt": "data/test_gt/10_gt.csv"},
}

def calculate_classification_metrics(pred_labels, true_labels):
    tp = np.sum((pred_labels == 1) & (true_labels == 1))
    fp = np.sum((pred_labels == 1) & (true_labels == 0))
    tn = np.sum((pred_labels == 0) & (true_labels == 0))
    fn = np.sum((pred_labels == 0) & (true_labels == 1))
    
    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0
    
    return {
        'Precision': round(precision, 3),
        'Recall': round(recall, 3),
        'F1_Score': round(f1, 3),
        'TP': tp, 'FP': fp, 'TN': tn, 'FN': fn
    }

def run_experiment():
    results = []
    
    for scenario_name, paths in SCENARIOS.items():
        video_path = paths['video']
        gt_path = paths['gt']
        
        print(f"--- Running Scenario: {scenario_name} ---")
        
        if not os.path.exists(video_path):
            print(f"  [SKIPPED] Video file not found: {video_path}")
            # Add a placeholder result so the table still has all rows
            results.append({
                'Scenario': scenario_name,
                'Status': 'Missing Video',
                'Max Density': 'N/A', 'Avg Density': 'N/A', 'Min Movement': 'N/A',
                'Avg Movement': 'N/A', 'Max Congestion': 'N/A', 'Max Duration': 'N/A',
                'Max Risk': 'N/A', 'Time Safe': 'N/A', 'Time Warning': 'N/A',
                'Time High Risk': 'N/A', 'Num Alerts': 'N/A',
                'Precision': 'N/A', 'Recall': 'N/A', 'F1_Score': 'N/A',
                'TP': 'N/A', 'FP': 'N/A', 'TN': 'N/A', 'FN': 'N/A'
            })
            continue
            
        video_stream = VideoStream(video_path)
        pipeline = CrowdSafetyPipeline(video_resolution=(video_stream.width, video_stream.height))
        
        frame_count = 0
        while True:
            data = video_stream.read_frame()
            if data is None:
                break
                
            results_frame = pipeline.process_frame(data['frame'], data['frame_number'], data['timestamp_ms'])
            if results_frame:
                frame_count += 1
                
        video_stream.release()
        
        if not pipeline.history:
            print(f"  [SKIPPED] No data processed for: {scenario_name}")
            continue
            
        # Aggregate Metrics from History
        df = pd.DataFrame(pipeline.history)
        
        # Aggregate globally across all zones per frame
        frame_maxes = df.groupby('frame_index_n').agg({
            'D_smoothed_z[n]': 'max',
            'M_raw_z[n]': 'min', # min movement across zones
            'C_smoothed_z[n]': 'max',
            'T_z[n]': 'max',
            'R_z[n]': 'max'
        }).reset_index()
        
        frame_means = df.groupby('frame_index_n').agg({
            'D_smoothed_z[n]': 'mean',
            'M_raw_z[n]': 'mean'
        }).reset_index()
        
        max_density = frame_maxes['D_smoothed_z[n]'].max()
        avg_density = frame_means['D_smoothed_z[n]'].mean()
        min_movement = frame_maxes['M_raw_z[n]'].min()
        avg_movement = frame_means['M_raw_z[n]'].mean()
        max_congestion = frame_maxes['C_smoothed_z[n]'].max()
        max_duration = frame_maxes['T_z[n]'].max()
        max_risk = frame_maxes['R_z[n]'].max()
        
        # States (Safe, Warning, High Risk)
        cat_map = {"Safe": 0, "Warning": 1, "High Risk": 2}
        df['Cat_Num'] = df['Risk_Category'].map(cat_map).fillna(0)
        frame_cats = df.groupby('frame_index_n')['Cat_Num'].max().reset_index()
        
        time_safe = (frame_cats['Cat_Num'] == 0).sum()
        time_warning = (frame_cats['Cat_Num'] == 1).sum()
        time_high = (frame_cats['Cat_Num'] == 2).sum()
        
        # Number of Alerts (Transitions into High Risk)
        cat_diff = frame_cats['Cat_Num'].diff()
        num_alerts = (cat_diff > 0)[frame_cats['Cat_Num'] == 2].sum()
        
        scenario_result = {
            'Scenario': scenario_name,
            'Status': 'Success',
            'Frames': frame_count,
            'Max Density': round(max_density, 2),
            'Avg Density': round(avg_density, 2),
            'Min Movement': round(min_movement, 2),
            'Avg Movement': round(avg_movement, 2),
            'Max Congestion': round(max_congestion, 2),
            'Max Duration': round(max_duration, 2),
            'Max Risk': round(max_risk, 2),
            'Time Safe': int(time_safe),
            'Time Warning': int(time_warning),
            'Time High Risk': int(time_high),
            'Num Alerts': int(num_alerts)
        }
        
        # Ground Truth Evaluation
        if os.path.exists(gt_path):
            gt_df = pd.read_csv(gt_path)
            merged = pd.merge(frame_cats, gt_df, left_on='frame_index_n', right_on='frame_index', how='inner')
            
            if not merged.empty:
                preds = (merged['Cat_Num'] == 2).astype(int).values
                truths = merged['is_dangerous'].astype(int).values
                metrics = calculate_classification_metrics(preds, truths)
                scenario_result.update(metrics)
            else:
                scenario_result.update({'Precision': 'N/A', 'Recall': 'N/A', 'F1_Score': 'N/A'})
        else:
            scenario_result.update({
                'Precision': 'N/A', 'Recall': 'N/A', 'F1_Score': 'N/A',
                'TP': 'N/A', 'FP': 'N/A', 'TN': 'N/A', 'FN': 'N/A'
            })
            
        results.append(scenario_result)
        print(f"  -> Finished {scenario_name}. Max Risk: {max_risk:.1f}")

    # Export
    out_dir = "data/output"
    os.makedirs(out_dir, exist_ok=True)
    
    res_df = pd.DataFrame(results)
    
    # Save CSV
    csv_path = os.path.join(out_dir, "experiment_results.csv")
    res_df.to_csv(csv_path, index=False)
    print(f"\nSaved raw results to {csv_path}")
    
    # Save Markdown Table
    md_path = os.path.join(out_dir, "experiment_results.md")
    with open(md_path, 'w') as f:
        f.write("# Academic Experiment Results\n\n")
        f.write("Comparison table across 10 crowd scenarios.\n\n")
        f.write(res_df.to_markdown(index=False))
    print(f"Saved Markdown table to {md_path}")
    
if __name__ == "__main__":
    run_experiment()
