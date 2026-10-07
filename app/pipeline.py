import csv
import logging
import os
import time
import config
from core.video import VideoStream
from core.spatial import ZoneManager
from core.detector import PersonDetector
from core.density import DensityEstimator
from core.motion import MotionEstimator, DirectionalAnalyzer
from core.signal_processing import SignalProcessor
from core.risk import LinearRiskEngine, InteractionRiskEngine, PersistenceRiskEngine
from core.state_machine import CongestionStateMachine
from core.anomaly import StatisticalAnomalyDetector

class CrowdSafetyPipeline:
    def __init__(self, video_resolution=None):
        # 1. Spatial Management (Grid or Manual)
        if config.USE_GRID and video_resolution is not None:
            w, h = video_resolution
            zones = ZoneManager.generate_grid_zones(
                w, h, 
                rows=config.GRID_SIZE[0], 
                cols=config.GRID_SIZE[1], 
                disabled_zones=config.DISABLED_ZONES
            )
            self.zone_manager = ZoneManager(zones)
        else:
            self.zone_manager = ZoneManager(config.SPATIAL_ZONES)
        
        # 2. Global AI Extractors (Heavy operations run ONCE per frame)
        self.detector = PersonDetector(config.YOLO_MODEL, config.CONFIDENCE_THRESHOLD)
        self.motion_estimator = MotionEstimator(
            fb_params=config.FARNEBACK_PARAMS,
            max_expected_motion=config.MAX_EXPECTED_MOTION
        )
        
        # 3. Per-Zone Math Engines (Lightweight filters run per zone)
        self.zone_engines = {}
        for zone_name in self.zone_manager.zones.keys():
            
            # Select Experimental Risk Model
            if config.RISK_MODEL == "Interaction":
                risk_model = InteractionRiskEngine(
                    zone_name=zone_name,
                    w_d=config.WEIGHT_DENSITY, w_c=config.WEIGHT_CONGESTION, w_t=config.WEIGHT_DURATION,
                    safe_max=config.RISK_SAFE_MAX, warn_max=config.RISK_WARN_MAX, 
                    hysteresis_buffer=config.STATE_MACHINE_BUFFER, persistence_limit=config.RISK_ALERT_PERSISTENCE
                )
            elif config.RISK_MODEL == "Persistence":
                risk_model = PersistenceRiskEngine(
                    zone_name=zone_name,
                    w_d=config.WEIGHT_DENSITY, w_c=config.WEIGHT_CONGESTION, w_t=config.WEIGHT_DURATION,
                    safe_max=config.RISK_SAFE_MAX, warn_max=config.RISK_WARN_MAX, 
                    hysteresis_buffer=config.STATE_MACHINE_BUFFER, persistence_limit=config.RISK_ALERT_PERSISTENCE
                )
            else:
                risk_model = LinearRiskEngine(
                    zone_name=zone_name,
                    w_d=config.WEIGHT_DENSITY, w_c=config.WEIGHT_CONGESTION, w_t=config.WEIGHT_DURATION,
                    safe_max=config.RISK_SAFE_MAX, warn_max=config.RISK_WARN_MAX, 
                    hysteresis_buffer=config.STATE_MACHINE_BUFFER, persistence_limit=config.RISK_ALERT_PERSISTENCE
                )
                
            self.zone_engines[zone_name] = {
                'density': DensityEstimator(config.MAX_CAPACITY_PER_ZONE),
                'signal': SignalProcessor(
                    window_size=config.MOVING_AVERAGE_WINDOW,
                    ewma_alpha=config.EWMA_ALPHA,
                    max_duration_frames=config.MAX_DURATION_FRAMES,
                    min_duration_frames=config.MIN_DURATION_FRAMES,
                    decay_rate=config.DURATION_DECAY_RATE
                ),
                'state_machine': CongestionStateMachine(
                    zone_name=zone_name,
                    t_d=config.DURATION_THRESHOLD_DENSITY,
                    t_c=config.DURATION_THRESHOLD_CONGESTION,
                    persistence_limit=config.PERSISTENCE_LIMIT_FRAMES,
                    buffer=config.STATE_MACHINE_BUFFER
                ),
                'risk': risk_model,
                'anomaly': StatisticalAnomalyDetector(
                    zone_name=zone_name, 
                    baseline_frames=config.ANOMALY_BASELINE_FRAMES
                ),
                'directional_analyzer': DirectionalAnalyzer(history_size=30)
            }
            
        self.history = []
        self.tracking_history = []

    def process_frame(self, frame, frame_number, timestamp_ms):
        """
        Runs the full multi-zone pipeline on a single frame.
        """
        if frame is None:
            return None
            
        start_time = time.perf_counter()

        # --- GLOBAL AI PASS ---
        count, boxes, ids, confidences = self.detector.detect(frame)
        flow = self.motion_estimator.update_flow(frame)
        
        # --- TRACKING TELEMETRY EXTRACTION ---
        if ids is not None and len(ids) > 0:
            for box, t_id, conf in zip(boxes, ids, confidences):
                if t_id is not None:
                    x1, y1, x2, y2 = box
                    cx, cy = (x1 + x2) / 2.0, (y1 + y2) / 2.0
                    self.tracking_history.append({
                        'track_id': int(t_id),
                        'frame_number': frame_number,
                        'timestamp_ms': timestamp_ms,
                        'bounding_box': f"[{x1:.1f}, {y1:.1f}, {x2:.1f}, {y2:.1f}]",
                        'center_x': cx,
                        'center_y': cy,
                        'confidence': float(conf)
                    })
        
        # --- PER-ZONE PROCESSING ---
        zone_results = {}
        for zone_name, engines in self.zone_engines.items():
            
            # A. Extract Zone Masks
            z_boxes, z_ids, z_confs = self.zone_manager.filter_boxes_by_zone(boxes, ids, confidences, zone_name)
            z_flow_mask = self.zone_manager.get_zone_flow_mask(frame.shape, zone_name)
            
            # B. Zone Density Estimate
            raw_count, normalized_density = engines['density'].estimate_density(z_boxes)
            
            # C. Zone Motion Estimate (with Empty Scene Fix and Crowd Masking)
            motion_stats = self.motion_estimator.estimate_zone_motion(flow, z_flow_mask, raw_count, boxes=z_boxes)
            
            # D. Zone Tracking Speed (Average speed of trajectories in this zone)
            avg_tracking_speed = self.detector.get_tracking_speeds(z_ids)
            
            # E. Zone Signal Processing (Temporal Filters)
            signal_results = engines['signal'].process(
                normalized_density, 
                motion_stats['congestion'],
                config.DURATION_THRESHOLD_DENSITY,
                config.DURATION_THRESHOLD_CONGESTION
            )
            
            # F. Zone Risk Engine (Hysteresis & Temporal Persistence)
            risk_score, risk_category = engines['risk'].evaluate(
                signal_results['fir_density'], 
                signal_results['fir_congestion'], 
                signal_results['duration_score'],
                timestamp_ms
            )
            
            # F2. Suffocation Risk (Compressive Asphyxia)
            suffocation_risk = engines['risk'].calculate_suffocation_risk(
                signal_results['fir_density'], 
                signal_results['fir_congestion'], 
                signal_results['duration_score']
            )
            
            # G. Robust Congestion State Machine
            congestion_state = engines['state_machine'].evaluate(
                signal_results['fir_density'],
                signal_results['fir_congestion']
            )
            
            # H. Experimental Anomaly Detector
            anomaly_score = 0.0
            is_calibrating = False
            if config.ENABLE_ANOMALY_DETECTION:
                feature_vector = [
                    normalized_density,
                    motion_stats['mean_magnitude'],
                    motion_stats['directional_consistency'],
                    motion_stats['congestion'],
                    signal_results['duration_score']
                ]
                anomaly_score, is_calibrating = engines['anomaly'].evaluate(feature_vector)
                
            # I. Directional Flow Analysis
            abnormal_indicators = engines['directional_analyzer'].evaluate(
                motion_stats['dominant_direction'],
                motion_stats['directional_consistency'],
                motion_stats['mean_magnitude']
            )
            
            # J. Construct Zone Record
            zone_record = {
                'timestamp': timestamp_ms,
                'frame_index_n': frame_number,
                'zone_z': zone_name,
                
                # Raw Signals
                'D_raw_z[n]': raw_count,
                'M_raw_z[n]': motion_stats['mean_magnitude'],
                'M_median_z[n]': motion_stats['median_magnitude'],
                'Dominant_Dir_z[n]': motion_stats['dominant_direction'],
                'Dir_Consistency_z[n]': motion_stats['directional_consistency'],
                'Tracked_Speed_z[n]': avg_tracking_speed,
                
                # Normalized Raw Signals (Pre-filter)
                'D_z[n]': normalized_density,
                'C_z[n]': motion_stats['congestion'],
                
                # FIR Smoothed Signals (Default)
                'D_smoothed_z[n]': signal_results['fir_density'],
                'C_smoothed_z[n]': signal_results['fir_congestion'],
                
                # IIR EWMA Smoothed Signals (Experimental)
                'D_ewma_z[n]': signal_results['ewma_density'],
                'C_ewma_z[n]': signal_results['ewma_congestion'],
                
                # Duration
                'T_z[n]': signal_results['duration_score'],
                
                # State & Risk
                'Congestion_State': congestion_state,
                'Risk_Model': config.RISK_MODEL,
                'R_z[n]': risk_score,
                'Risk_Category': risk_category,
                'Suffocation_Risk_z[n]': suffocation_risk,
                
                # Experimental Anomaly
                'Anomaly_Score_z[n]': anomaly_score,
                'Is_Calibrating': is_calibrating,
                
                # Directional Analysis
                'Abnormal_Movement_Indicators': abnormal_indicators
            }
            self.history.append(zone_record)
            
            zone_results[zone_name] = {
                'record': zone_record,
                'boxes': z_boxes,
                'ids': z_ids,
                'confidences': z_confs
            }
            
        process_time = time.perf_counter() - start_time
        fps = 1.0 / process_time if process_time > 0 else 0
            
        return {
            'fps': fps,
            'global_boxes': boxes,
            'global_ids': ids,
            'global_confidences': confidences,
            'flow': flow,
            'zones': zone_results
        }
        
    def save_to_csv(self, filename="data/output/crowd_signals.csv"):
        """Saves the flattened combined record history to a CSV file."""
        if not self.history:
            logging.warning("No data to save.")
            return
            
        os.makedirs(os.path.dirname(filename), exist_ok=True)
        keys = self.history[0].keys()
        
        with open(filename, 'w', newline='') as output_file:
            dict_writer = csv.DictWriter(output_file, fieldnames=keys)
            dict_writer.writeheader()
            dict_writer.writerows(self.history)
        logging.info(f"Saved {len(self.history)} multi-zone records to {filename}")

    def save_tracking_csv(self, filename="data/output/tracking_telemetry.csv"):
        """Saves the individual person tracking telemetry to a CSV file."""
        if not self.tracking_history:
            logging.warning("No tracking data to save.")
            return
            
        os.makedirs(os.path.dirname(filename), exist_ok=True)
        keys = self.tracking_history[0].keys()
        
        with open(filename, 'w', newline='') as output_file:
            dict_writer = csv.DictWriter(output_file, fieldnames=keys)
            dict_writer.writeheader()
            dict_writer.writerows(self.tracking_history)
        logging.info(f"Saved {len(self.tracking_history)} tracking records to {filename}")
