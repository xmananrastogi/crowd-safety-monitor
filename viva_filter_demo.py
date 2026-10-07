"""
Viva Demonstration: Moving Average Low-Pass Filter
Shows the effect of different window sizes (N) on a noisy discrete-time signal.
"""
import os
import numpy as np
import matplotlib.pyplot as plt
from collections import deque

def apply_moving_average(signal, window_size):
    """
    Applies the LTI causal filter: S[n] = (1/N) * sum_{k=0}^{N-1} M[n-k]
    """
    filtered_signal = []
    buffer = deque(maxlen=window_size)
    
    for x in signal:
        buffer.append(x)
        filtered_signal.append(np.mean(buffer))
        
    return np.array(filtered_signal)

def run_viva_demo():
    # 1. Generate a mock base signal (e.g., crowd moving steadily)
    # We use 200 discrete time steps (frames)
    n = np.arange(0, 200) 
    true_motion = np.ones_like(n) * 40.0 
    
    # Introduce a short-term fluctuation (e.g., a momentary burst of movement)
    true_motion[80:90] = 75.0
    
    # 2. Add high-frequency noise 
    # This represents camera jitter, YOLO flickering, or optical flow miscalculations
    np.random.seed(42) # For reproducibility, no artificial manipulation
    noise = np.random.normal(0, 15, size=len(n))
    raw_signal_M = true_motion + noise
    
    # Ensure realistic non-negative values
    raw_signal_M = np.clip(raw_signal_M, 0, 100)
    
    # 3. Apply Moving Average Filters with multiple window sizes N
    window_sizes = [5, 15, 30]
    
    plt.figure(figsize=(12, 8))
    
    # Plot the raw, noisy discrete-time signal M[n]
    plt.plot(n, raw_signal_M, label="Raw Signal $M[n]$ (Noisy)", color='gray', alpha=0.5, linestyle='--')
    
    # Plot filtered signals S[n] for each window size
    colors = ['blue', 'orange', 'red']
    for N, color in zip(window_sizes, colors):
        filtered_S = apply_moving_average(raw_signal_M, N)
        plt.plot(n, filtered_S, label=f"Filtered $S[n]$ (N={N})", color=color, linewidth=2.5)
        
    plt.title("Viva Demonstration: Moving Average Filter Response")
    plt.xlabel("Discrete Time Step / Frame Index ($n$)")
    plt.ylabel("Motion Signal Amplitude")
    plt.grid(True, linestyle=':', alpha=0.7)
    plt.legend(loc='upper right')
    
    # Save the plot for the academic presentation
    os.makedirs("data/output", exist_ok=True)
    save_path = "data/output/viva_filter_demo.png"
    plt.savefig(save_path, dpi=300, bbox_inches='tight')
    print(f"Saved Viva demonstration plot to {save_path}")
    
    # Display the plot
    plt.show()

if __name__ == "__main__":
    run_viva_demo()
