"""
Modular Risk Evaluation Engines.
Implements the base RiskEngine with shared Hysteresis, Temporal Persistence, and Alert Logging.
"""
import os
import csv
import numpy as np
from abc import ABC, abstractmethod
from datetime import datetime
import config

class RiskEngine(ABC):
    def __init__(self, zone_name, w_d=0.45, w_c=0.35, w_t=0.20, safe_max=30, warn_max=60, hysteresis_buffer=5.0, persistence_limit=5):
        if not np.isclose(w_d + w_c + w_t, 1.0, atol=1e-5):
            raise ValueError("Risk weights must sum exactly to 1.0")
            
        self.zone_name = zone_name
        self.w_d = w_d
        self.w_c = w_c
        self.w_t = w_t
        self.safe_max = safe_max
        self.warn_max = warn_max
        self.buffer = hysteresis_buffer
        self.persistence_limit = persistence_limit
        
        # State memory
        self.current_state = "Safe"
        
        # Temporal Persistence Tracking
        self.target_state = "Safe"
        self.persistence_counter = 0
        self.target_reason = ""
        
        # Alert CSV Setup
        self.alert_file = "data/logs/alerts.csv"
        os.makedirs("data/logs", exist_ok=True)
        if not os.path.exists(self.alert_file):
            with open(self.alert_file, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(["Timestamp", "Zone", "RiskScore", "PreviousState", "NewState", "Reason", "Density", "Congestion", "Duration"])

    def log_alert(self, timestamp_ms, risk_score, new_state, reason, D_n, C_n, T_n):
        """Logs an official state transition alert to the CSV."""
        dt_str = datetime.fromtimestamp(timestamp_ms / 1000.0).strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
        with open(self.alert_file, 'a', newline='') as f:
            writer = csv.writer(f)
            writer.writerow([dt_str, self.zone_name, f"{risk_score:.2f}", self.current_state, new_state, reason, f"{D_n:.2f}", f"{C_n:.2f}", f"{T_n:.2f}"])

    @abstractmethod
    def calculate_raw_risk(self, D_n, C_n, T_n):
        """
        Mathematical definition of risk. Must return a float between 0.0 and 100.0.
        """
        pass
        
    def evaluate(self, D_n, C_n, T_n, timestamp_ms):
        """
        Calculates Risk Index R[n] and applies a Schmitt Trigger AND Temporal Persistence
        before allowing a state transition.
        """
        # Ensure inputs are capped to prevent mathematical overflow
        D_n, C_n, T_n = np.clip([D_n, C_n, T_n], 0.0, 100.0)
        
        # Subclass Math
        raw_risk = self.calculate_raw_risk(D_n, C_n, T_n)
        risk_score = float(np.clip(raw_risk, 0.0, 100.0))
        
        # 1. Evaluate Schmitt Trigger bounds to find Target State
        new_target_state = self.current_state
        reason = ""
        
        if self.current_state == "Safe":
            if risk_score > (self.safe_max + self.buffer):
                new_target_state = "Warning"
                reason = f"Risk crossed Warning threshold ({self.safe_max + self.buffer})"
                
        elif self.current_state == "Warning":
            if risk_score < (self.safe_max - self.buffer):
                new_target_state = "Safe"
                reason = f"Risk fell below Safe threshold ({self.safe_max - self.buffer})"
            elif risk_score > (self.warn_max + self.buffer):
                new_target_state = "High Risk"
                reason = f"Risk crossed High Risk threshold ({self.warn_max + self.buffer})"
                
        elif self.current_state == "High Risk":
            if risk_score < (self.warn_max - self.buffer):
                new_target_state = "Warning"
                reason = f"Risk fell below Warning threshold ({self.warn_max - self.buffer})"
                
        # 2. Evaluate Temporal Persistence
        if new_target_state == self.current_state:
            # Condition normalized, reset counter
            self.persistence_counter = 0
            self.target_state = self.current_state
            self.target_reason = ""
        else:
            if new_target_state == self.target_state:
                # Target state condition persists
                self.persistence_counter += 1
            else:
                # New target state emerged
                self.target_state = new_target_state
                self.target_reason = reason
                self.persistence_counter = 1
                
            # 3. Escalate State if Persistence Limit Reached
            if self.persistence_counter >= self.persistence_limit:
                self.log_alert(timestamp_ms, risk_score, self.target_state, self.target_reason, D_n, C_n, T_n)
                self.current_state = self.target_state
                self.persistence_counter = 0
                
        return risk_score, self.current_state

    def calculate_suffocation_risk(self, D_n, C_n, T_n):
        """
        Calculates Compressive Asphyxia (Suffocation) Risk (0-100%).
        Models danger of high-density crushes where lack of movement prevents breathing.
        Requires both extremely high density and congestion to trigger.
        """
        if D_n < config.SUFFOCATION_MIN_DENSITY or C_n < config.SUFFOCATION_MIN_CONGESTION:
            return 0.0
            
        # Normalize how far above the threshold we are (0.0 to 1.0 scale for the danger zone)
        d_range = 100.0 - config.SUFFOCATION_MIN_DENSITY
        c_range = 100.0 - config.SUFFOCATION_MIN_CONGESTION
        
        d_factor = (D_n - config.SUFFOCATION_MIN_DENSITY) / d_range if d_range > 0 else 0
        c_factor = (C_n - config.SUFFOCATION_MIN_CONGESTION) / c_range if c_range > 0 else 0
        
        # Exponential curve: risk skyrockets when both approach 100%
        crush_base = (d_factor * c_factor) ** 1.5
        
        # Duration acts as a harsh multiplier (the longer they are crushed, the worse it gets)
        # 0% duration = 1x multiplier, 100% duration = 2.5x multiplier
        t_factor = 1.0 + (1.5 * (T_n / 100.0))
        
        risk = crush_base * 100.0 * t_factor
        return min(risk, 100.0)

class LinearRiskEngine(RiskEngine):
    """
    MODEL 1: Baseline Linear Model.
    R = wD*D + wC*C + wT*T
    """
    def calculate_raw_risk(self, D_n, C_n, T_n):
        return (self.w_d * D_n) + (self.w_c * C_n) + (self.w_t * T_n)

class InteractionRiskEngine(RiskEngine):
    """
    MODEL 2: Interaction Model.
    Danger requires BOTH high density and low movement simultaneously.
    If scene is empty (D=0), base risk is 0 regardless of C.
    """
    def calculate_raw_risk(self, D_n, C_n, T_n):
        base_spatial_risk = (D_n * C_n) / 100.0
        
        # Combine base interaction with temporal weight
        w_base = self.w_d + self.w_c
        return (w_base * base_spatial_risk) + (self.w_t * T_n)

class PersistenceRiskEngine(RiskEngine):
    """
    MODEL 3: Persistence-Aware Model.
    Duration acts as a progressive multiplier closing the gap to 100%, 
    rather than a flat additive score. 
    If scene is empty (S=0), duration does not artificially create risk.
    """
    def calculate_raw_risk(self, D_n, C_n, T_n):
        # Normalize spatial weights to 1.0 sum for base spatial calculation
        total_spatial_weight = self.w_d + self.w_c
        
        if total_spatial_weight == 0:
            return 0.0
            
        w_d_norm = self.w_d / total_spatial_weight
        w_c_norm = self.w_c / total_spatial_weight
        
        # Base linear spatial risk (0 to 100)
        base_S = (w_d_norm * D_n) + (w_c_norm * C_n)
        
        # Progressively increase towards 100 as T approaches 100
        return base_S + ((T_n / 100.0) * (100.0 - base_S))
