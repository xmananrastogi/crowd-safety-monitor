"""
Robust Congestion State Machine.
Implements hysteresis on explicit physical conditions (Crowd + Stall + Persistence)
to strictly determine congestion states, outputting transition logs.
"""
import logging
import os

# Initialize dedicated State Transition Logger
os.makedirs("data/logs", exist_ok=True)
logger = logging.getLogger("StateTransitions")
logger.setLevel(logging.INFO)

# Prevent duplicate handlers if module is reloaded
if not logger.handlers:
    fh = logging.FileHandler("data/logs/state_transitions.log")
    fh.setFormatter(logging.Formatter('%(asctime)s - %(message)s'))
    logger.addHandler(fh)

class CongestionStateMachine:
    def __init__(self, zone_name, t_d=75.0, t_c=50.0, persistence_limit=30, buffer=5.0):
        """
        Initializes the robust state machine for a specific zone.
        """
        self.zone_name = zone_name
        self.t_d = t_d
        self.t_c = t_c
        self.persistence_limit = persistence_limit
        self.buffer = buffer
        
        # Boolean condition memory
        self.is_crowded = False
        self.is_stalled = False
        
        # Persistence accumulator
        self.counter = 0
        
        self.current_state = "NORMAL"
        
    def evaluate(self, density, congestion):
        """
        Evaluates the current state using Schmitt Triggers on the physical conditions.
        Returns the new state.
        """
        # 1. Hysteresis on Crowd Presence Condition
        if not self.is_crowded:
            if density > (self.t_d + self.buffer):
                self.is_crowded = True
        else:
            if density < (self.t_d - self.buffer):
                self.is_crowded = False
                
        # 2. Hysteresis on Stall (Low Movement) Condition
        if not self.is_stalled:
            if congestion > (self.t_c + self.buffer):
                self.is_stalled = True
        else:
            if congestion < (self.t_c - self.buffer):
                self.is_stalled = False
                
        # 3. Persistence Accumulator
        if self.is_crowded and self.is_stalled:
            self.counter += 1
        else:
            self.counter = max(0, self.counter - 2) # Decay twice as fast to clear states quickly
            
        # 4. State Determination
        new_state = "NORMAL"
        if self.counter == 0:
            new_state = "NORMAL"
        elif 0 < self.counter < self.persistence_limit:
            new_state = "DEVELOPING"
        else:
            new_state = "PERSISTENT CONGESTION"
            
        # 5. State Transition Logging
        if new_state != self.current_state:
            logger.info(f"[{self.zone_name}] State Transition: {self.current_state} -> {new_state} | D={density:.1f}%, C={congestion:.1f}%, Counter={self.counter}")
            self.current_state = new_state
            
        return self.current_state
