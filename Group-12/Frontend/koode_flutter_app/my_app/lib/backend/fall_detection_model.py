"""
Fall Detection ML Model
Predicts fall events based on accelerometer and gyroscope readings.

Uses a simple threshold-based approach combined with pattern recognition.
For production, consider using a trained neural network model.
"""

import numpy as np
from typing import Tuple, Dict, List


class FallDetectionModel:
    """
    Simple fall detection model based on sensor data analysis.
    
    Fall detection logic:
    - High acceleration magnitude (free fall detection)
    - Rapid change in acceleration (impact detection)
    - Unusual gyro patterns (rotation patterns during fall)
    - Combination of above factors
    """
    
    def __init__(self):
        """Initialize model with calibrated thresholds."""
        # Acceleration thresholds (in m/s²)
        self.free_fall_threshold = 2.0  # Low acceleration (near gravity)
        self.impact_threshold = 20.0     # High acceleration (impact)
        self.rapid_accel_change = 15.0   # Sudden acceleration change
        
        # Gyroscope thresholds (in deg/s)
        self.high_rotation_threshold = 200.0
        
        # Confidence weights
        self.free_fall_weight = 0.3
        self.impact_weight = 0.5
        self.gyro_weight = 0.2
        
    def calculate_acceleration_magnitude(self, 
                                        accel_x: float, 
                                        accel_y: float, 
                                        accel_z: float) -> float:
        """Calculate magnitude of acceleration vector."""
        # Remove gravity offset (9.81 m/s²)
        accel_mag = np.sqrt(accel_x**2 + accel_y**2 + accel_z**2)
        return accel_mag
    
    def calculate_gyro_magnitude(self,
                                 gyro_x: float,
                                 gyro_y: float,
                                 gyro_z: float) -> float:
        """Calculate magnitude of gyroscope vector."""
        gyro_mag = np.sqrt(gyro_x**2 + gyro_y**2 + gyro_z**2)
        return gyro_mag
    
    def detect_free_fall(self, accel_mag: float) -> Tuple[bool, float]:
        """
        Detect free fall condition (low acceleration).
        Returns (is_free_fall, confidence)
        """
        if accel_mag < self.free_fall_threshold:
            confidence = min(1.0, (self.free_fall_threshold - accel_mag) / 2.0)
            return True, confidence
        return False, 0.0
    
    def detect_impact(self, current_accel_mag: float, 
                     previous_accel_mag: float = None) -> Tuple[bool, float]:
        """
        Detect impact (high acceleration or rapid change).
        Returns (is_impact, confidence)
        """
        # Check for high acceleration
        if current_accel_mag > self.impact_threshold:
            confidence = min(1.0, (current_accel_mag - self.impact_threshold) / 20.0)
            return True, confidence
        
        # Check for rapid acceleration change
        if previous_accel_mag is not None:
            accel_change = abs(current_accel_mag - previous_accel_mag)
            if accel_change > self.rapid_accel_change:
                confidence = min(1.0, (accel_change - self.rapid_accel_change) / 15.0)
                return True, confidence
        
        return False, 0.0
    
    def detect_unusual_rotation(self, gyro_mag: float) -> Tuple[bool, float]:
        """
        Detect unusual rotation patterns (high gyro values).
        Returns (is_unusual_rotation, confidence)
        """
        if gyro_mag > self.high_rotation_threshold:
            confidence = min(1.0, (gyro_mag - self.high_rotation_threshold) / 150.0)
            return True, confidence
        return False, 0.0
    
    def predict(self,
                accel_x: float,
                accel_y: float,
                accel_z: float,
                gyro_x: float,
                gyro_y: float,
                gyro_z: float,
                previous_accel_x: float = None,
                previous_accel_y: float = None,
                previous_accel_z: float = None) -> Dict[str, float]:
        """
        Predict if a fall is occurring based on sensor readings.
        
        Args:
            accel_x, accel_y, accel_z: Current accelerometer readings (m/s²)
            gyro_x, gyro_y, gyro_z: Current gyroscope readings (deg/s)
            previous_accel_*: Previous accelerometer readings (optional)
        
        Returns:
            Dict with keys:
            - 'is_fall': Boolean indicating fall detection
            - 'confidence': Confidence score (0-1)
            - 'reasoning': List of detected patterns
        """
        reasoning = []
        scores = []
        
        # Calculate magnitudes
        current_accel_mag = self.calculate_acceleration_magnitude(accel_x, accel_y, accel_z)
        gyro_mag = self.calculate_gyro_magnitude(gyro_x, gyro_y, gyro_z)
        
        # Check for free fall
        is_free_fall, free_fall_conf = self.detect_free_fall(current_accel_mag)
        if is_free_fall:
            reasoning.append(f"Free fall detected (accel_mag: {current_accel_mag:.2f})")
            scores.append(free_fall_conf * self.free_fall_weight)
        
        # Check for impact
        prev_accel_mag = None
        if previous_accel_x is not None and previous_accel_y is not None and previous_accel_z is not None:
            prev_accel_mag = self.calculate_acceleration_magnitude(
                previous_accel_x, previous_accel_y, previous_accel_z
            )
        
        is_impact, impact_conf = self.detect_impact(current_accel_mag, prev_accel_mag)
        if is_impact:
            reasoning.append(f"Impact detected (accel_mag: {current_accel_mag:.2f})")
            scores.append(impact_conf * self.impact_weight)
        
        # Check for unusual rotation
        is_rotation, rotation_conf = self.detect_unusual_rotation(gyro_mag)
        if is_rotation:
            reasoning.append(f"High rotation detected (gyro_mag: {gyro_mag:.2f})")
            scores.append(rotation_conf * self.gyro_weight)
        
        # Calculate overall confidence
        total_confidence = sum(scores) if scores else 0.0
        is_fall = total_confidence > 0.5  # Threshold for fall detection
        
        return {
            'is_fall': is_fall,
            'confidence': min(1.0, total_confidence),
            'reasoning': reasoning,
            'accel_mag': current_accel_mag,
            'gyro_mag': gyro_mag
        }
    
    def predict_batch(self, sensor_readings: List[Dict]) -> Dict:
        """
        Predict fall from a batch of recent sensor readings.
        Useful for smoothing out noise.
        
        Args:
            sensor_readings: List of dicts with 'accelX', 'accelY', 'accelZ', 'gyroX', 'gyroY', 'gyroZ'
        
        Returns:
            Aggregated prediction across the batch
        """
        if not sensor_readings or len(sensor_readings) == 0:
            return {'is_fall': False, 'confidence': 0.0, 'reasoning': ['No data']}
        
        predictions = []
        for i, reading in enumerate(sensor_readings):
            prev_reading = sensor_readings[i-1] if i > 0 else None
            
            pred = self.predict(
                accel_x=reading['accelX'],
                accel_y=reading['accelY'],
                accel_z=reading['accelZ'],
                gyro_x=reading['gyroX'],
                gyro_y=reading['gyroY'],
                gyro_z=reading['gyroZ'],
                previous_accel_x=prev_reading['accelX'] if prev_reading else None,
                previous_accel_y=prev_reading['accelY'] if prev_reading else None,
                previous_accel_z=prev_reading['accelZ'] if prev_reading else None,
            )
            predictions.append(pred)
        
        # Aggregate predictions - if any show strong fall signal
        avg_confidence = np.mean([p['confidence'] for p in predictions])
        fall_count = sum(1 for p in predictions if p['is_fall'])
        is_fall = fall_count >= len(predictions) * 0.5  # Majority voting
        
        all_reasoning = []
        for p in predictions:
            all_reasoning.extend(p['reasoning'])
        
        return {
            'is_fall': is_fall,
            'confidence': avg_confidence,
            'reasoning': all_reasoning,
            'individual_predictions': predictions
        }
