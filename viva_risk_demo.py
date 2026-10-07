"""
Viva Demonstration: Crowd Safety Risk Index
Demonstrates the calculation and visualization of the proposed Risk Equation.
R[n] = 0.45D[n] + 0.35C[n] + 0.20T[n]
"""
import os
import numpy as np
import matplotlib.pyplot as plt
from core.risk import RiskEvaluator

def run_risk_demo():
    # Initialize the Risk Evaluator with initial proposed weights
    # IMPORTANT: These are experimental, non-validated parameters.
    evaluator = RiskEvaluator(w_d=0.45, w_c=0.35, w_t=0.20)
    
    # Generate 300 discrete time steps
    n = np.arange(0, 300)
    
    # Create mock scenarios for D[n], C[n], and T[n]
    D_n = np.zeros_like(n, dtype=float)
    C_n = np.zeros_like(n, dtype=float)
    T_n = np.zeros_like(n, dtype=float)
    
    # Phase 1: Safe (Low density, moving freely)
    D_n[0:50] = 30.0
    C_n[0:50] = 20.0
    
    # Phase 2: Density increases, but crowd keeps moving
    D_n[50:150] = np.linspace(30, 90, 100)
    C_n[50:150] = 25.0
    
    # Phase 3: Sudden stop (Congestion spikes)
    D_n[150:200] = 95.0
    C_n[150:200] = np.linspace(25, 90, 50)
    
    # Phase 4: Sustained congestion (Duration builds up)
    D_n[200:300] = 95.0
    C_n[200:300] = 90.0
    T_n[200:300] = np.linspace(0, 100, 100)
    
    # Process through the evaluator
    for i in range(len(n)):
        evaluator.evaluate(D_n[i], C_n[i], T_n[i])
        
    R_signal = np.array(evaluator.R_signal)
    contrib_D = np.array(evaluator.contributions['D'])
    contrib_C = np.array(evaluator.contributions['C'])
    contrib_T = np.array(evaluator.contributions['T'])
    
    # Plotting
    plt.figure(figsize=(12, 7))
    
    # Stacked Area Chart to show which component contributed to the score
    plt.stackplot(n, contrib_D, contrib_C, contrib_T, 
                  labels=['Density ($0.45 \cdot D[n]$)', 
                          'Congestion ($0.35 \cdot C[n]$)', 
                          'Duration ($0.20 \cdot T[n]$)'],
                  colors=['#4c72b0', '#dd8452', '#c44e52'],
                  alpha=0.8)
                  
    # Plot the total risk line
    plt.plot(n, R_signal, color='black', linewidth=2.5, label="Total Risk $R[n]$")
    
    # Plot Threshold Lines
    plt.axhline(y=30, color='green', linestyle='--', linewidth=2, label='Safe Threshold (30)')
    plt.axhline(y=60, color='red', linestyle='--', linewidth=2, label='Warning Threshold (60)')
    
    # Annotate phases
    bbox_style = dict(facecolor='white', alpha=0.9, edgecolor='black', boxstyle='round,pad=0.5')
    plt.text(25, 85, 'Phase 1:\nSafe', ha='center', va='center', bbox=bbox_style)
    plt.text(100, 85, 'Phase 2:\nDensity Rises', ha='center', va='center', bbox=bbox_style)
    plt.text(175, 85, 'Phase 3:\nMotion Stops', ha='center', va='center', bbox=bbox_style)
    plt.text(250, 85, 'Phase 4:\nDuration Builds', ha='center', va='center', bbox=bbox_style)
    
    plt.title("Viva Demonstration: Crowd Safety Risk Index $R[n]$\n(Note: Weights & Thresholds are Configurable Experimental Parameters)")
    plt.xlabel("Discrete Time Step / Frame Index ($n$)")
    plt.ylabel("Risk Score (0-100)")
    plt.ylim(0, 105)
    plt.grid(True, linestyle=':', alpha=0.5)
    
    plt.legend(loc='lower right', framealpha=0.9)
    plt.tight_layout()
    
    os.makedirs("data/output", exist_ok=True)
    save_path = "data/output/viva_risk_demo.png"
    plt.savefig(save_path, dpi=300, bbox_inches='tight')
    print(f"Saved Viva Risk demonstration plot to {save_path}")
    plt.show()

if __name__ == "__main__":
    run_risk_demo()
