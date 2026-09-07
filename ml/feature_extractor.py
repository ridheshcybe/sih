import numpy as np
import pandas as pd
from typing import Dict, List, Any, Tuple

class FeatureExtractor:
    """
    Extracts a fixed-length feature vector from a window of telemetry data 
    and the current digital twin state for ML model input.
    """

    def __init__(self, sensor_names: List[str]):
        """
        Initializes the FeatureExtractor.
        :param sensor_names: List of all monitored sensor names.
        """
        self.sensor_names = sensor_names
        # Placeholder for the known expected physical relationships (for residuals)
        self.physics_model_params = {
            "cht": lambda rpm, egt: rpm * 0.1 + egt * 0.01, # Mock function
            "oil_pressure": lambda rpm, cht: rpm * 0.005
        }
