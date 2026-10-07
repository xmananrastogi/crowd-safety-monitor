"""
Experimental Parameter-Tuning Module
Sweeps through various configurations to evaluate the sensitivity of the Crowd Safety Pipeline.
"""
import os
import itertools
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from unittest.mock import MagicMock

# Ensure we can import from the parent directory
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import config
from app.pipeline import CrowdSafetyPipeline

class ParameterTuner:
    def __init__(self, output_dir="data/output/tuning"):
        self.output_dir = output_dir
        os.makedirs(self.output_dir, exist_ok=True)
        
        # Generates a synthetic crowd event (Normal -> Stampede/Stall -> Dispersal)
        self.synthetic_data = self._generate_synthetic_scenario()
        
    def _generate_synthetic_scenario(self):
        """Generates 300 discrete frames."""
        density = np.zeros(300)
        motion = np.zeros(300)
        
        # 0-100: Safe
        density[0:100] = 30.0
        motion[0:100] = 3.0
        
        # 100-200: Stampede/Stall Condition
        density[100:200] = 95.0
        motion[100:200] = 0.5
        
        # 200-300: Dispersal
        density[200:300] = 40.0
        motion[200:300] = 4.0
        
        # Add high-frequency noise to simulate real-world CV jitter
        np.random.seed(42)
        density += np.random.normal(0, 10, 300)
        motion += np.random.normal(0, 1, 300)
        
        density = np.clip(density, 0.0, 100.0)
        motion = np.clip(motion, 0.0, 5.0)
        
        return list(zip(density, motion))
        
    def run_sweep(self, sweep_params):
        """
        Executes a Cartesian product sweep of the given parameters.
        Returns the observational metrics and the full risk trajectories.
        """
        keys = list(sweep_params.keys())
        values = list(sweep_params.values())
        combinations = list(itertools.product(*values))
        
        results = []
        histories = {}
        
        print(f"Executing {len(combinations)} parameter configurations...\n")
        
        for idx, combo in enumerate(combinations):
            # 1. Override global config safely
            config_label = []
            for i, key in enumerate(keys):
                setattr(config, key, combo[i])
                config_label.append(f"{key}={combo[i]}")
            
            label = " | ".join(config_label)
            
            # 2. Instantiate pipeline and mock CV layers
            pipeline = CrowdSafetyPipeline()
            pipeline.detector.detect = MagicMock()
            pipeline.density_estimator.estimate_density = MagicMock()
            pipeline.motion_estimator.estimate_motion = MagicMock()
            
            dummy_frame = np.zeros((10, 10, 3), dtype=np.uint8)
            
            for f_idx, (mock_d, mock_m) in enumerate(self.synthetic_data):
                mock_c = (1.0 - (mock_m / 5.0)) * 100.0
                
                pipeline.detector.detect.return_value = (int(mock_d), [], [])
                pipeline.density_estimator.estimate_density.return_value = (int(mock_d), mock_d)
                pipeline.motion_estimator.estimate_motion.return_value = (mock_m, mock_c, None)
                
                pipeline.process_frame(dummy_frame, f_idx, f_idx*33)
                
            # 3. Compute Observational Metrics
            df = pd.DataFrame(pipeline.history)
            
            high_risk_frames = len(df[df['risk_category'] == 'High Risk'])
            is_high = (df['risk_category'] == 'High Risk').astype(int)
            alert_starts = (is_high.diff() == 1).sum()
            
            results.append({
                'Config': label,
                'Max Risk': df['risk_score'].max(),
                'Alerts Count': alert_starts,
                'Total Alert Duration (frames)': high_risk_frames
            })
            
            histories[label] = df['risk_score'].values
            
        return pd.DataFrame(results), histories

    def plot_window_sweep(self):
        """Generates plots showing how the moving-average window affects smoothing."""
        print("=== Experiment 1: Filter Window Sweep ===")
        sweep = {'MOVING_AVERAGE_WINDOW': [1, 15, 45]}
        df_results, histories = self.run_sweep(sweep)
        
        for idx, row in df_results.iterrows():
            print(f"Config: {row['Config']}")
            print(f"  -> Number of Alerts: {row['Alerts Count']}")
            print(f"  -> Duration of Alerts: {row['Total Alert Duration (frames)']} frames\n")
        
        plt.figure(figsize=(12, 6))
        colors = ['red', 'green', 'blue']
        for (label, risk_signal), color in zip(histories.items(), colors):
            N = label.split('=')[1]
            plt.plot(risk_signal, label=f"N = {N}", color=color, linewidth=2, alpha=0.8)
            
        plt.title("Parameter Sweep: Moving-Average Window ($N$) vs Risk Signal ($R[n]$)")
        plt.xlabel("Frame Index")
        plt.ylabel("Risk Score")
        plt.grid(True, linestyle=':', alpha=0.6)
        plt.legend(title="Window Size")
        plt.axhline(60, color='black', linestyle='--', label='High Risk Threshold')
        
        plot_path = os.path.join(self.output_dir, "sweep_window.png")
        plt.savefig(plot_path, dpi=300, bbox_inches='tight')
        print(f"-> Saved filter plot to {plot_path}\n")

    def plot_weight_sweep(self):
        """Generates plots showing how risk weights bias the system's sensitivity."""
        print("=== Experiment 2: Risk Equation Weights Sweep ===")
        # (w_d, w_c, w_t)
        weights = [
            (0.80, 0.10, 0.10), # Density Biased
            (0.10, 0.80, 0.10), # Congestion Biased
            (0.33, 0.33, 0.34)  # Balanced
        ]
        labels = ["Density-Biased", "Congestion-Biased", "Balanced"]
        
        plt.figure(figsize=(12, 6))
        colors = ['purple', 'orange', 'teal']
        
        for weight_set, name, color in zip(weights, labels, colors):
            config.WEIGHT_DENSITY = weight_set[0]
            config.WEIGHT_CONGESTION = weight_set[1]
            config.WEIGHT_DURATION = weight_set[2]
            
            pipeline = CrowdSafetyPipeline()
            pipeline.detector.detect = MagicMock()
            pipeline.density_estimator.estimate_density = MagicMock()
            pipeline.motion_estimator.estimate_motion = MagicMock()
            
            dummy_frame = np.zeros((10, 10, 3), dtype=np.uint8)
            for f_idx, (mock_d, mock_m) in enumerate(self.synthetic_data):
                mock_c = (1.0 - (mock_m / 5.0)) * 100.0
                pipeline.detector.detect.return_value = (int(mock_d), [], [])
                pipeline.density_estimator.estimate_density.return_value = (int(mock_d), mock_d)
                pipeline.motion_estimator.estimate_motion.return_value = (mock_m, mock_c, None)
                pipeline.process_frame(dummy_frame, f_idx, f_idx*33)
                
            df = pd.DataFrame(pipeline.history)
            
            # Observational Metrics
            high_risk_frames = len(df[df['risk_category'] == 'High Risk'])
            is_high = (df['risk_category'] == 'High Risk').astype(int)
            alert_starts = (is_high.diff() == 1).sum()
            
            print(f"Config: {name} {weight_set}")
            print(f"  -> Number of Alerts: {alert_starts}")
            print(f"  -> Duration of Alerts: {high_risk_frames} frames\n")
            
            plt.plot(df['risk_score'].values, label=f"{name} {weight_set}", color=color, linewidth=2)
            
        plt.title("Parameter Sweep: Equation Weights vs Risk Signal ($R[n]$)")
        plt.xlabel("Frame Index")
        plt.ylabel("Risk Score")
        plt.grid(True, linestyle=':', alpha=0.6)
        plt.legend()
        plt.axhline(60, color='black', linestyle='--', label='High Risk Threshold')
        
        plot_path = os.path.join(self.output_dir, "sweep_weights.png")
        plt.savefig(plot_path, dpi=300, bbox_inches='tight')
        print(f"-> Saved weights plot to {plot_path}\n")

if __name__ == "__main__":
    print("======================================================")
    print("   CROWD SAFETY MONITOR: PARAMETER TUNING MODULE      ")
    print("======================================================\n")
    print("NOTE: False-Positive/False-Negative metrics are intentionally")
    print("excluded as no ground-truth labeled stampede dataset is provided.")
    print("We report strict observational metrics only.\n")
    
    tuner = ParameterTuner()
    tuner.plot_window_sweep()
    tuner.plot_weight_sweep()
