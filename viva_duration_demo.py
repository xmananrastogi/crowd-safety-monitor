"""
Viva Demonstration: Congestion Duration Tracking
Demonstrates the algorithmic state tracking for abnormal crowd conditions.
"""
import os
import numpy as np
import matplotlib.pyplot as plt
from core.signal_processing import SignalProcessor

def run_duration_demo():
    # 1. Experimental Configuration
    MAX_CAPACITY = 100
    MAX_DUR_FRAMES = 100
    MIN_DUR_FRAMES = 15
    DECAY_RATE = 2
    
    # Initialize the Signal Processor
    sp = SignalProcessor(window_size=1, # Bypass LPF for this specific duration demo
                         max_capacity=MAX_CAPACITY,
                         max_duration_frames=MAX_DUR_FRAMES,
                         min_duration_frames=MIN_DUR_FRAMES,
                         decay_rate=DECAY_RATE)
                         
    THRESH_D = 50.0 # Density threshold
    THRESH_C = 50.0 # Congestion threshold

    # 2. Generate discrete time steps
    n = np.arange(0, 300)
    
    # Generate mock smoothed signals
    density = np.zeros_like(n)
    congestion = np.zeros_like(n)
    
    # Scenario A: Short, harmless spike (Fails MIN_DUR_FRAMES)
    density[20:30] = 60.0
    congestion[20:30] = 60.0
    
    # Scenario B: Single variable exceeds threshold (Should NOT trigger)
    density[60:100] = 80.0
    congestion[60:100] = 40.0 # Congestion is low
    
    # Scenario C: Prolonged abnormal condition (Should trigger and grow)
    density[150:240] = 90.0
    congestion[150:240] = 80.0
    
    # 3. Process the signals through the tracking algorithm
    for i in range(len(n)):
        sp.process(density[i], congestion[i], THRESH_D, THRESH_C)
        
    T_signal = np.array(sp.T_signal)
    
    # 4. Plot the demonstration
    plt.figure(figsize=(12, 10))
    
    # Plot 1: Smoothed Inputs
    plt.subplot(2, 1, 1)
    plt.plot(n, density, label="Smoothed Density $D[n]$", color='blue')
    plt.plot(n, congestion, label="Smoothed Congestion $C[n]$", color='orange')
    plt.axhline(y=THRESH_D, color='r', linestyle='--', label="Experimental Threshold (50%)")
    plt.title("Filtered Inputs (Density & Congestion)")
    plt.ylabel("Percentage (%)")
    plt.legend()
    plt.grid(True, linestyle=':', alpha=0.7)
    
    # Plot 2: Duration Output
    plt.subplot(2, 1, 2)
    plt.plot(n, T_signal, label="Normalized Duration $T[n]$", color='purple', linewidth=3)
    plt.title(f"Abnormal Congestion Duration Tracking\n(Min Frames={MIN_DUR_FRAMES}, Max Frames={MAX_DUR_FRAMES}, Decay={DECAY_RATE}x)")
    plt.xlabel("Discrete Time Step / Frame Index ($n$)")
    plt.ylabel("Risk Duration Score (%)")
    
    # Annotate Scenario A
    plt.annotate("Short Spike\n(Ignored)", xy=(25, 5), xytext=(25, 40),
                 arrowprops=dict(facecolor='black', shrink=0.05), ha='center')
                 
    # Annotate Scenario B
    plt.annotate("Only Density High\n(No Trigger)", xy=(80, 5), xytext=(80, 40),
                 arrowprops=dict(facecolor='black', shrink=0.05), ha='center')
                 
    # Annotate Scenario C
    plt.annotate("Prolonged Episode\n(T[n] scales up)", xy=(200, 50), xytext=(150, 80),
                 arrowprops=dict(facecolor='black', shrink=0.05), ha='center')
    
    plt.legend()
    plt.grid(True, linestyle=':', alpha=0.7)
    
    plt.tight_layout()
    
    os.makedirs("data/output", exist_ok=True)
    save_path = "data/output/viva_duration_demo.png"
    plt.savefig(save_path, dpi=300, bbox_inches='tight')
    print(f"Saved Viva duration demonstration plot to {save_path}")
    plt.show()

if __name__ == "__main__":
    run_duration_demo()
