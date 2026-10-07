"""
Handles the mathematical normalization of crowd presence into a discrete-time signal.
"""
class DensityEstimator:
    def __init__(self, max_capacity=100):
        """
        Initializes the Density Estimator.
        Args:
            max_capacity (int): The estimated maximum number of people that can fit 
                                safely in the monitored zone (100% density).
        """
        self.max_capacity = max_capacity
        
    def estimate_density(self, boxes):
        """
        Calculates the normalized crowd density estimate from bounding boxes.
        IMPORTANT: This is not physical density (people/m^2) unless camera 
        calibration is provided.
        
        Args:
            boxes (list): List of YOLO bounding boxes pre-filtered by ZoneManager.
            
        Returns:
            raw_count (int): Number of people in the zone.
            normalized_density (float): 0-100 value based on max_capacity.
        """
        if boxes is None or len(boxes) == 0:
            return 0, 0.0
            
        raw_count = len(boxes)
        
        if self.max_capacity <= 0:
            normalized_density = 0.0
        else:
            normalized_density = (raw_count / self.max_capacity) * 100.0
            
        # Cap at 100%
        normalized_density = min(normalized_density, 100.0)
        return raw_count, normalized_density
