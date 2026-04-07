"""
Standalone Posture Data Processor
Receives batched frame data via WebSocket, stores in memory, and generates debug files.
This is completely independent from main.py and can be deleted without affecting main.py.
"""

import json
import os
from datetime import datetime
from typing import Dict, List, Optional, Any
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn
import numpy as np
from scipy import interpolate
import inference


# ============================================================================
# INCREMENTAL STREAMING FILTERS
# ============================================================================

class StreamingEMA:
    """Exponential Moving Average - O(1) per update, no history storage"""
    def __init__(self, alpha: float = 0.3):
        self.alpha = alpha
        self.ema = None
    
    def update(self, new_value: float) -> float:
        if new_value is None:
            return self.ema if self.ema is not None else None
        
        if self.ema is None:
            self.ema = new_value
        else:
            self.ema = self.alpha * new_value + (1 - self.alpha) * self.ema
        return self.ema
    
    def reset(self):
        self.ema = None


class StreamingKalman:
    """Kalman Filter - O(1) per update, optimal for noisy sensor data"""
    def __init__(self, process_noise: float = 0.01, measurement_noise: float = 0.1):
        self.estimate = None
        self.error_estimate = 1.0
        self.Q = process_noise
        self.R = measurement_noise
    
    def update(self, measurement: float) -> float:
        if measurement is None:
            return self.estimate
        
        if self.estimate is None:
            self.estimate = measurement
            return self.estimate
        
        # Prediction step
        predicted_estimate = self.estimate
        predicted_error = self.error_estimate + self.Q
        
        # Update step
        kalman_gain = predicted_error / (predicted_error + self.R)
        self.estimate = predicted_estimate + kalman_gain * (measurement - predicted_estimate)
        self.error_estimate = (1 - kalman_gain) * predicted_error
        
        return self.estimate
    
    def reset(self):
        self.estimate = None
        self.error_estimate = 1.0


class StreamingDoubleEMA:
    """Double Exponential Smoothing (Holt's method) - Handles trends"""
    def __init__(self, alpha: float = 0.3, beta: float = 0.1):
        self.alpha = alpha
        self.beta = beta
        self.level = None
        self.trend = 0
    
    def update(self, new_value: float) -> float:
        if new_value is None:
            return self.level if self.level is not None else None
        
        if self.level is None:
            self.level = new_value
            return self.level
        
        prev_level = self.level
        self.level = self.alpha * new_value + (1 - self.alpha) * (self.level + self.trend)
        self.trend = self.beta * (self.level - prev_level) + (1 - self.beta) * self.trend
        
        return self.level + self.trend
    
    def reset(self):
        self.level = None
        self.trend = 0


class RollingWindowFilter:
    """Rolling window filter (Gaussian/Savitzky-Golay) - O(window_size) per update"""
    def __init__(self, window_size: int = 7, filter_mode: str = 'gaussian', sigma: float = 1.5):
        self.window_size = window_size
        self.filter_mode = filter_mode
        self.sigma = sigma
        self.buffer = []
        
        # Precompute coefficients
        if filter_mode == 'gaussian':
            self._compute_gaussian_kernel()
        elif filter_mode == 'savgol':
            self._compute_savgol_coefficients()
    
    def _compute_gaussian_kernel(self):
        """Precompute Gaussian kernel weights"""
        import math
        half_window = self.window_size // 2
        kernel = []
        kernel_sum = 0
        
        for i in range(-half_window, half_window + 1):
            weight = math.exp(-(i * i) / (2 * self.sigma * self.sigma))
            kernel.append(weight)
            kernel_sum += weight
        
        self.kernel = [k / kernel_sum for k in kernel]
    
    def _compute_savgol_coefficients(self):
        """Precompute Savitzky-Golay coefficients"""
        coefficients = {
            5: [-3, 12, 17, 12, -3],
            7: [-2, 3, 6, 7, 6, 3, -2],
            9: [-21, 14, 39, 54, 59, 54, 39, 14, -21]
        }
        
        if self.window_size == 5:
            self.kernel = [c / 35 for c in coefficients[5]]
        elif self.window_size == 7:
            self.kernel = [c / 21 for c in coefficients[7]]
        elif self.window_size == 9:
            self.kernel = [c / 231 for c in coefficients[9]]
        else:
            self.kernel = [c / 21 for c in coefficients[7]]
    
    def update(self, new_value: float) -> float:
        if new_value is None:
            if len(self.buffer) > 0:
                return self.buffer[-1]
            return None
        
        # Add to buffer
        self.buffer.append(new_value)
        
        # Keep only window_size elements
        if len(self.buffer) > self.window_size:
            self.buffer.pop(0)
        
        # Not enough data yet - return raw value
        if len(self.buffer) < self.window_size:
            return new_value
        
        # Apply convolution
        filtered_value = sum(self.buffer[i] * self.kernel[i] for i in range(self.window_size))
        return filtered_value
    
    def reset(self):
        self.buffer.clear()


class IncrementalHybridFilter:
    """
    Hybrid incremental filter combining multiple stages:
    Stage 1: Kalman (removes sensor noise)
    Stage 2: Rolling Gaussian (smooths movement)
    
    Memory: ~10 floats per joint
    Computation: O(window_size) per update (constant for fixed window)
    """
    def __init__(self):
        self.kalman = StreamingKalman(process_noise=0.01, measurement_noise=0.1)
        self.gaussian = RollingWindowFilter(window_size=7, filter_mode='gaussian', sigma=1.5)
    
    def update(self, raw_angle: float) -> float:
        if raw_angle is None:
            return None
        
        # Stage 1: Kalman removes sensor noise
        kalman_filtered = self.kalman.update(raw_angle)
        
        # Stage 2: Gaussian smooths movement
        final_filtered = self.gaussian.update(kalman_filtered)
        
        return final_filtered
    
    def reset(self):
        self.kalman.reset()
        self.gaussian.reset()

def create_incremental_filter(filter_type: str, config: Dict):
    """Factory function to create appropriate incremental filter"""
    if filter_type == 'ema':
        return StreamingEMA(alpha=config['ema_alpha'])
    elif filter_type == 'double_ema':
        return StreamingDoubleEMA(
            alpha=config['double_ema_alpha'],
            beta=config['double_ema_beta']
        )
    elif filter_type == 'kalman':
        return StreamingKalman(
            process_noise=config['kalman_process_noise'],
            measurement_noise=config['kalman_measurement_noise']
        )
    elif filter_type == 'savgol':
        return RollingWindowFilter(
            window_size=config['savgol_window_size'],
            filter_mode='savgol'
        )
    elif filter_type == 'gaussian':
        return RollingWindowFilter(
            window_size=config['gaussian_window_size'],
            filter_mode='gaussian',
            sigma=config['gaussian_sigma']
        )
    elif filter_type == 'hybrid':
        return IncrementalHybridFilter()
    else:
        # Default to hybrid
        return IncrementalHybridFilter()


# ============================================================================
# CONFIGURATION
# ============================================================================

# Smoothing configuration (matching main.py SMOOTHING_CONFIG)
SMOOTHING_CONFIG = {
    'filter_type': 'gaussian',      # Options: 'savgol', 'ema', 'double_ema', 'gaussian', 'kalman', 'hybrid'
    'savgol_window_size': 7,        # 5, 7, or 9
    'ema_alpha': 0.3,               # 0.1-0.5
    'double_ema_alpha': 0.3,
    'double_ema_beta': 0.1,
    'gaussian_window_size': 7,
    'gaussian_sigma': 1.5,
    'kalman_process_noise': 0.01,
    'kalman_measurement_noise': 0.1
}


# ============================================================================
# DATA STORAGE CLASS
# ============================================================================

class JointDataStore:
    """Stores angle data points for a single joint (either trainer or user)"""
    
    def __init__(self, joint_name: str):
        self.joint_name = joint_name
        self.timestamps: List[float] = []
        self.angles: List[float] = []              # Raw angles (with confidence filtering)
        self.angles_smoothed: List[float] = []     # Incrementally filtered angles
        self.confidences: List[float] = []
        self.interpolated_60fps: List[float] = []  # Auto-interpolated 60 FPS data
        self.interpolated_filtered: List[float] = []  # Filtered interpolated data
        self.last_interpolated_index: int = 0      # Track which raw data index we last interpolated up to
        self.last_interpolated_timestamp: float = 0.0  # Last 60 FPS timestamp we generated
        
        # Cumulative average tracking (batch-based for efficiency)
        self.cumulative_average: Optional[float] = None  # Running average of all raw angles from start
        self.raw_angles_count: int = 0                  # Count of raw angles used in cumulative average
        self.batch_buffer: List[float] = []             # Temporary buffer for current batch angles
        self.statistics_reset_index: int = 0            # Index in interpolated_filtered where statistics were last reset
        
        # Cumulative standard deviation tracking
        self.cumulative_sum_of_squares: float = 0.0     # Running sum of squared values for std dev calculation
        
        # Cumulative stats for interpolated_filtered data (from statistics_reset_index onward)
        self.interp_cumulative_average: Optional[float] = None  # Running mean of interpolated_filtered values
        self.interp_count: int = 0                              # Count of interpolated_filtered values tracked
        self.interp_sum_of_squares: float = 0.0                # Running sum of x² for interpolated_filtered
        
        # Create incremental filter instance (maintains state, no reprocessing)
        self.filter = create_incremental_filter(
            SMOOTHING_CONFIG['filter_type'],
            SMOOTHING_CONFIG
        )
        
        # Create separate filter for interpolated data
        self.interpolated_filter = create_incremental_filter(
            SMOOTHING_CONFIG['filter_type'],
            SMOOTHING_CONFIG
        )
    
    def add_data_point(self, timestamp: float, angle: float, confidence: float):
        """Add a new data point and apply incremental filter"""
        self.timestamps.append(timestamp)
        self.angles.append(angle)
        self.confidences.append(confidence)
        
        # Apply filter incrementally (O(1) or O(window_size), no reprocessing)
        smoothed = self.filter.update(angle)
        self.angles_smoothed.append(smoothed)
        
        # Add to batch buffer for cumulative average calculation
        self.batch_buffer.append(angle)
        
        # Auto-interpolate after adding data
        self._update_interpolation()
    
    def _update_interpolation(self):
        """Internal method to update 60 FPS interpolation incrementally"""
        if len(self.timestamps) < 2:
            self.interpolated_60fps = []
            self.last_interpolated_index = 0
            self.last_interpolated_timestamp = 0.0
            return
        
        fps = 60
        frame_duration = 1.0 / fps  # 0.016666... seconds per frame
        current_data_count = len(self.timestamps)
        
        # First time interpolation - do full interpolation
        if self.last_interpolated_index == 0:
            timestamps = np.array(self.timestamps)
            angles = np.array(self.angles_smoothed)
            
            first_timestamp = timestamps[0]
            last_timestamp = timestamps[-1]
            
            # Align start time to nearest 60 FPS frame boundary at or before first timestamp
            whole_second = int(np.floor(first_timestamp))
            offset_within_second = first_timestamp - whole_second
            frame_index_within_second = int(np.floor(offset_within_second / frame_duration))
            aligned_start_time = whole_second + (frame_index_within_second * frame_duration)
            
            # Generate timestamps at exactly 60 FPS from aligned start
            duration = last_timestamp - aligned_start_time
            num_frames = int(np.floor(duration / frame_duration)) + 1
            
            interpolated_timestamps = np.array([
                aligned_start_time + (i * frame_duration) 
                for i in range(num_frames)
            ])
            
            interpolated_timestamps = interpolated_timestamps[interpolated_timestamps <= last_timestamp]
            
            if len(interpolated_timestamps) == 0:
                return
            
            # Perform linear interpolation
            interpolator = interpolate.interp1d(
                timestamps, 
                angles, 
                kind='linear',
                fill_value='extrapolate'
            )
            interpolated_values = interpolator(interpolated_timestamps)
            
            # Store interpolated values and apply filter to each
            self.interpolated_60fps = []
            self.interpolated_filtered = []
            for value in interpolated_values.tolist():
                self.interpolated_60fps.append(value)
                # Apply filter to interpolated value and round to integer
                filtered_value = self.interpolated_filter.update(value)
                # Clamp to [0, 180] range
                clamped_value = max(0, min(180, round(filtered_value)))
                self.interpolated_filtered.append(clamped_value)
                # Update cumulative interp stats if at or after reset index
                if len(self.interpolated_filtered) - 1 >= self.statistics_reset_index:
                    self._update_interp_cumulative_stats(clamped_value)
            
            self.last_interpolated_index = current_data_count - 1
            self.last_interpolated_timestamp = interpolated_timestamps[-1]
            return
        
        # Incremental interpolation - only process new data
        # Use 2 boundary points from previous data for smooth interpolation
        boundary_points = 2
        start_idx = max(0, self.last_interpolated_index - boundary_points + 1)
        
        # Check if we have new data
        if current_data_count <= self.last_interpolated_index:
            return  # No new data
        
        # Get slice of data including boundary points and new data
        timestamps_slice = np.array(self.timestamps[start_idx:])
        angles_slice = np.array(self.angles_smoothed[start_idx:])
        
        if len(timestamps_slice) < 2:
            return
        
        last_timestamp = timestamps_slice[-1]
        
        # Calculate next 60 FPS timestamp after last interpolated point
        next_start_time = self.last_interpolated_timestamp + frame_duration
        
        # Check if we have enough new data for at least one frame
        if last_timestamp < next_start_time:
            return
        
        # Generate new 60 FPS timestamps from next_start_time to last_timestamp
        duration = last_timestamp - next_start_time
        num_new_frames = int(np.floor(duration / frame_duration)) + 1
        
        new_interpolated_timestamps = np.array([
            next_start_time + (i * frame_duration)
            for i in range(num_new_frames)
        ])
        
        new_interpolated_timestamps = new_interpolated_timestamps[new_interpolated_timestamps <= last_timestamp]
        
        if len(new_interpolated_timestamps) == 0:
            return
        
        # Interpolate only the new timestamps using the slice (includes boundary points)
        interpolator = interpolate.interp1d(
            timestamps_slice,
            angles_slice,
            kind='linear',
            fill_value='extrapolate'
        )
        new_interpolated_values = interpolator(new_interpolated_timestamps)
        
        # Append only the new interpolated values and apply filter to each
        new_values_list = new_interpolated_values.tolist()
        for value in new_values_list:
            self.interpolated_60fps.append(value)
            # Apply filter to interpolated value and round to integer
            filtered_value = self.interpolated_filter.update(value)
            # Clamp to [0, 180] range
            clamped_value = max(0, min(180, round(filtered_value)))
            self.interpolated_filtered.append(clamped_value)
            # Update cumulative interp stats if at or after reset index
            if len(self.interpolated_filtered) - 1 >= self.statistics_reset_index:
                self._update_interp_cumulative_stats(clamped_value)
        
        self.last_interpolated_index = current_data_count - 1
        self.last_interpolated_timestamp = new_interpolated_timestamps[-1]
    
    def finalize_batch(self):
        """
        Finalize the current batch by updating cumulative average.
        This should be called after a batch of data points has been added.
        Uses weighted average formula to efficiently update the cumulative average.
        """
        if len(self.batch_buffer) == 0:
            return  # No new data in this batch
        
        # Calculate average and sum of squares of current batch
        batch_avg = sum(self.batch_buffer) / len(self.batch_buffer)
        batch_count = len(self.batch_buffer)
        batch_sum_of_squares = sum(x * x for x in self.batch_buffer)
        
        # Update cumulative average using weighted formula
        if self.cumulative_average is None:
            # First batch
            self.cumulative_average = batch_avg
            self.raw_angles_count = batch_count
            self.cumulative_sum_of_squares = batch_sum_of_squares
        else:
            # Weighted average: new_avg = (old_avg * old_count + batch_avg * batch_count) / (old_count + batch_count)
            self.cumulative_average = (
                (self.cumulative_average * self.raw_angles_count) + (batch_avg * batch_count)
            ) / (self.raw_angles_count + batch_count)
            self.raw_angles_count += batch_count
            self.cumulative_sum_of_squares += batch_sum_of_squares
        
        # Clear the batch buffer
        self.batch_buffer.clear()
    
    def get_cumulative_average(self) -> Optional[float]:
        """Get the cumulative average of all raw angles from start (rounded to integer)"""
        if self.cumulative_average is not None:
            return round(self.cumulative_average)
        return None
    
    def get_cumulative_average_precise(self) -> Optional[float]:
        """Get the precise cumulative average (not rounded)"""
        return self.cumulative_average
    
    def get_cumulative_std_dev(self) -> Optional[float]:
        """Get the cumulative standard deviation of all raw angles from start (rounded to 2 decimal places)"""
        if self.cumulative_average is not None and self.raw_angles_count > 0:
            # Calculate variance: var = (sum(x^2) / n) - mean^2
            mean_of_squares = self.cumulative_sum_of_squares / self.raw_angles_count
            variance = mean_of_squares - (self.cumulative_average ** 2)
            # Handle floating point errors that might make variance slightly negative
            variance = max(0, variance)
            std_dev = variance ** 0.5
            return round(std_dev, 2)
        return None
    
    def get_cumulative_std_dev_precise(self) -> Optional[float]:
        """Get the precise cumulative standard deviation (not rounded)"""
        if self.cumulative_average is not None and self.raw_angles_count > 0:
            mean_of_squares = self.cumulative_sum_of_squares / self.raw_angles_count
            variance = mean_of_squares - (self.cumulative_average ** 2)
            variance = max(0, variance)
            return variance ** 0.5
        return None
    
    def _update_interp_cumulative_stats(self, value: float):
        """Incrementally update cumulative stats for interpolated_filtered data (O(1))"""
        self.interp_sum_of_squares += value * value
        self.interp_count += 1
        if self.interp_cumulative_average is None:
            self.interp_cumulative_average = float(value)
        else:
            # Welford-style incremental mean update
            self.interp_cumulative_average += (value - self.interp_cumulative_average) / self.interp_count
    
    def get_interp_cumulative_average(self) -> Optional[float]:
        """Get cumulative average of interpolated_filtered values (rounded to integer)"""
        if self.interp_cumulative_average is not None:
            return round(self.interp_cumulative_average)
        return None
    
    def get_interp_cumulative_average_precise(self) -> Optional[float]:
        """Get precise cumulative average of interpolated_filtered values (not rounded)"""
        return self.interp_cumulative_average
    
    def get_interp_cumulative_std_dev(self) -> Optional[float]:
        """Get cumulative std dev of interpolated_filtered values (rounded to 2 decimal places)"""
        if self.interp_cumulative_average is not None and self.interp_count > 0:
            mean_of_squares = self.interp_sum_of_squares / self.interp_count
            variance = max(0, mean_of_squares - (self.interp_cumulative_average ** 2))
            return round(variance ** 0.5, 2)
        return None
    
    def get_interp_cumulative_std_dev_precise(self) -> Optional[float]:
        """Get precise cumulative std dev of interpolated_filtered values (not rounded)"""
        if self.interp_cumulative_average is not None and self.interp_count > 0:
            mean_of_squares = self.interp_sum_of_squares / self.interp_count
            variance = max(0, mean_of_squares - (self.interp_cumulative_average ** 2))
            return variance ** 0.5
        return None
    
    def get_window_average(self, window_size: int) -> Optional[float]:
        """
        Calculate average of the last N filtered interpolated angle data points.
        Uses the filtered_interpolated array for smoother results.
        Only includes data from after the last statistics reset.
        
        Args:
            window_size: Number of points to average (e.g., 120 for last 120 interpolated points)
        
        Returns:
            Average of last window_size points, or None if not enough data (requires minimum 2 points)
        """
        # Only use data from after the last reset point
        valid_data = self.interpolated_filtered[self.statistics_reset_index:]
        
        # Require at least 2 points for meaningful average
        if len(valid_data) < 2:
            return None
        
        if len(valid_data) < window_size:
            # Use all available data if less than window size
            window_size = len(valid_data)
        
        # Get last window_size points from valid data
        last_angles = valid_data[-window_size:]
        return sum(last_angles) / len(last_angles)
    
    def get_window_average_rounded(self, window_size: int) -> Optional[int]:
        """Get window average rounded to integer"""
        avg = self.get_window_average(window_size)
        if avg is not None:
            return round(avg)
        return None
    
    def get_window_average_count(self, window_size: int) -> int:
        """Get the actual number of elements used in window average calculation"""
        # Only use data from after the last reset point
        valid_data = self.interpolated_filtered[self.statistics_reset_index:]
        
        if len(valid_data) == 0:
            return 0
        
        # Return the actual number of elements used (min of requested window_size and available data)
        return min(len(valid_data), window_size)
    
    def get_window_std_dev(self, window_size: int) -> Optional[float]:
        """Get the standard deviation of the last N filtered interpolated angle data points (rounded to 2 decimal places)"""
        # Only use data from after the last reset point
        valid_data = self.interpolated_filtered[self.statistics_reset_index:]
        
        # Require at least 2 points for meaningful std dev
        if len(valid_data) < 2:
            return None
        
        # Use actual window size (min of requested and available)
        actual_window_size = min(len(valid_data), window_size)
        window_data = valid_data[-actual_window_size:]
        
        # Calculate mean
        mean = sum(window_data) / len(window_data)
        
        # Calculate variance
        variance = sum((x - mean) ** 2 for x in window_data) / len(window_data)
        
        # Return standard deviation
        std_dev = variance ** 0.5
        return round(std_dev, 2)
    
    def get_window_std_dev_precise(self, window_size: int) -> Optional[float]:
        """Get the precise standard deviation of the last N points (not rounded)"""
        valid_data = self.interpolated_filtered[self.statistics_reset_index:]
        
        # Require at least 2 points for meaningful std dev
        if len(valid_data) < 2:
            return None
        
        actual_window_size = min(len(valid_data), window_size)
        window_data = valid_data[-actual_window_size:]
        
        mean = sum(window_data) / len(window_data)
        variance = sum((x - mean) ** 2 for x in window_data) / len(window_data)
        return variance ** 0.5
    
    def clear_average_values(self):
        """Clear only average values, marking current position as reset point"""
        # Clear cumulative average tracking
        self.cumulative_average = None
        self.raw_angles_count = 0
        self.batch_buffer.clear()
        self.cumulative_sum_of_squares = 0.0
        
        # Clear cumulative interpolated_filtered stats
        self.interp_cumulative_average = None
        self.interp_count = 0
        self.interp_sum_of_squares = 0.0
        
        # Mark the current position in interpolated data as reset point
        # Window averages will only use frames from this index onwards
        self.statistics_reset_index = len(self.interpolated_filtered)
    
    def clear_interpolated_cumulative_stats(self):
        """Clear only the cumulative statistics for interpolated_filtered data"""
        # Clear cumulative interpolated_filtered stats only
        self.interp_cumulative_average = None
        self.interp_count = 0
        self.interp_sum_of_squares = 0.0
        
        # Mark the current position in interpolated data as reset point
        # This affects window-based calculations that use interpolated_filtered data
        self.statistics_reset_index = len(self.interpolated_filtered)
    
    def clear_all_data(self):
        """Clear all data including raw, smoothed, interpolated, and averages"""
        self.timestamps.clear()
        self.angles.clear()
        self.angles_smoothed.clear()
        self.confidences.clear()
        self.interpolated_60fps.clear()
        self.interpolated_filtered.clear()
        self.cumulative_average = None
        self.raw_angles_count = 0
        self.batch_buffer.clear()
        self.cumulative_sum_of_squares = 0.0
        self.interp_cumulative_average = None
        self.interp_count = 0
        self.interp_sum_of_squares = 0.0
        self.statistics_reset_index = 0
        self.last_interpolated_index = 0
        self.last_interpolated_timestamp = 0.0
        self.filter.reset()
        self.interpolated_filter.reset()

# ============================================================================
# JOINT CONFIGURATION
# ============================================================================

# 15 joint names
JOINT_NAMES = [
    "Left Shoulder",
    "Left Elbow",
    "Left Wrist",
    "Right Shoulder",
    "Right Elbow",
    "Right Wrist",
    "Left Hip",
    "Left Knee",
    "Left Ankle",
    "Right Hip",
    "Right Knee",
    "Right Ankle",
    "Left Spine",
    "Right Spine",
    "Neck"
]

# Mapping from frontend short keys to full joint names
JOINT_KEY_MAPPING = {
    'ls': 'Left Shoulder',
    'le': 'Left Elbow',
    'lw': 'Left Wrist',
    'rs': 'Right Shoulder',
    're': 'Right Elbow',
    'rw': 'Right Wrist',
    'lh': 'Left Hip',
    'lk': 'Left Knee',
    'la': 'Left Ankle',
    'rh': 'Right Hip',
    'rk': 'Right Knee',
    'ra': 'Right Ankle',
    'lsp': 'Left Spine',
    'rsp': 'Right Spine',
    'n': 'Neck'
}

# Initialize storage for all 30 joint stores (15 trainer + 15 user)
trainer_stores: Dict[str, JointDataStore] = {
    joint_name: JointDataStore(f"Trainer_{joint_name}")
    for joint_name in JOINT_NAMES
}

user_stores: Dict[str, JointDataStore] = {
    joint_name: JointDataStore(f"User_{joint_name}")
    for joint_name in JOINT_NAMES
}

# Confidence threshold (matching main.py line 1023)
CONFIDENCE_THRESHOLD = 40

# Track last valid angles for confidence filtering
last_valid_trainer_angles: Dict[str, float] = {}  # {joint_name: last_valid_angle}
last_valid_user_angles: Dict[str, float] = {}     # {joint_name: last_valid_angle}

# Track pause state for statistics reset
pause_flag = False  # True when video is paused, False when playing

# Track exercise change gestures (Thumb_Up -> Thumb_Down within 3 seconds)
thumbs_up_timestamp = None  # Timestamp of LAST (latest) Thumb_Up detected
EXERCISE_CHANGE_WINDOW = 3.0  # seconds - window to detect Thumb_Down after Thumb_Up
exercise_change_count = 0  # Counter for number of exercise changes

# Feedback algorithm state
feedback_batch_count = 0    # increments each batch; resets on exercise change, pause, or after feedback sent
feedback_check_flag = False # True after first mismatch; cleared on positive feedback or exercise change
feedback_complete = False   # True after positive feedback; stops all checking until exercise change

# ============================================================================
# MODEL PRE-LOADING
# ============================================================================

MODEL_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "base_model.pt")
rep_model, rep_device = inference.load_model(MODEL_PATH)
print(f"[MODEL] base_model.pt loaded on {rep_device}")

# Track already-detected reps per exercise (list of [start_index, end_index])
# These use absolute exercise-timeline indices (not window-relative)
trainer_found_reps: List[List[int]] = []
user_found_reps: List[List[int]] = []

# Store last inference results for the /reps visualization endpoint
last_trainer_inference: Optional[dict] = None
last_user_inference: Optional[dict] = None
last_rep_joint_names: List[str] = []
last_rep_framecount: int = 0


# ============================================================================
# REP SEGMENTATION FUNCTIONS
# ============================================================================

def get_exercise_frame_count(stores_dict: dict) -> int:
    """
    Get the number of interpolated_filtered frames for the CURRENT exercise only.
    Uses statistics_reset_index as the boundary — this is moved forward on
    exercise change, pause, and resume via clear_average_values().
    
    Returns the frame count from the first joint that has data.
    """
    for store in stores_dict.values():
        total = len(store.interpolated_filtered)
        if total > 0:
            return total - store.statistics_reset_index
    return 0


def get_top_6_joints(stores_dict: dict) -> list:
    """
    Get the top 6 joints by std dev from the trainer's sorted list.
    Primary joints come first, then fill with next-highest std-dev joints to reach 6.
    
    Returns list of up to 6 joint names.
    """
    result = calculate_primary_joints(stores_dict)
    all_sorted = result["all_joints_sorted"]
    
    # Take first 6 joint names from the sorted list (primary joints naturally first)
    joint_names = [j["joint_name"] for j in all_sorted[:6]]
    return joint_names


def repsegment(stores_dict: dict, joint_names: list, framecount: int) -> tuple:
    """
    Run the rep segmentation model on interpolated_filtered data.
    
    Args:
        stores_dict: trainer_stores or user_stores
        joint_names: list of up to 6 joint names (from get_top_6_joints)
        framecount: number of frames in the current exercise
    
    Returns:
        tuple of (reps, full_result):
          reps: list of [start_index, end_index, [6 array slices]]
          full_result: full inference dict from predict_with_model
    """
    arrays = []
    
    for jname in joint_names:
        store = stores_dict.get(jname)
        if store is None:
            # Joint not found — use zeros
            arrays.append(np.zeros(min(framecount, 480), dtype="float32"))
            continue
        
        # Extract only current exercise data (from statistics_reset_index onward)
        exercise_data = store.interpolated_filtered[store.statistics_reset_index:]
        
        if framecount > 480:
            # Take last 480 frames
            data_slice = exercise_data[-480:]
        else:
            # Take last framecount frames
            data_slice = exercise_data[-framecount:] if framecount > 0 else []
        
        arrays.append(np.array(data_slice, dtype="float32"))
    
    # Pad to 6 arrays if fewer joints provided
    while len(arrays) < 6:
        target_len = min(framecount, 480) if framecount > 0 else 1
        arrays.append(np.zeros(target_len, dtype="float32"))
    
    # Run model
    result = inference.predict_with_model(arrays, rep_model, rep_device)
    reps = result["reps"]
    
    # Offset indices to absolute exercise-timeline positions
    # Model returns indices relative to the 480-frame window (0-479).
    # When framecount > 480, the window starts at (framecount - 480),
    # so we add that offset to get the true exercise-timeline index.
    if framecount > 480:
        offset = framecount - 480
        for rep in reps:
            rep[0] += offset  # start_index
            rep[1] += offset  # end_index
    
    return reps, result


def is_overlapping_rep(new_start: int, new_end: int, found_reps: list) -> bool:
    """
    Check if a new rep overlaps with any already-found rep.
    
    Overlap condition:
      - new_start falls within an existing rep (start >= existing_start AND start <= existing_end)
      - OR new_end falls within an existing rep (end >= existing_start AND end <= existing_end)
    
    Returns True if overlapping (i.e. duplicate), False if new.
    """
    for existing in found_reps:
        ex_start, ex_end = existing[0], existing[1]
        if (new_start >= ex_start and new_start <= ex_end) or \
           (new_end >= ex_start and new_end <= ex_end):
            return True
    return False


def feedbacksystem(user_reps: list, trainer_reps: list, joint_names: list):
    """
    Placeholder for future rep analysis and feedback.
    
    Args:
        user_reps: list of [start, end, [6 array slices]] for user
        trainer_reps: list of [start, end, [6 array slices]] for trainer
        joint_names: list of joint names used
    """
    # Future: compare user reps against trainer reps using repcomparison.py
    pass


def run_rep_segmentation():
    """
    Run rep segmentation for both trainer and user.
    Called on every batch after feedback_complete is True.
    Uses the trainer's top 6 std-dev joints for both.
    Filters out already-detected reps using overlap checking.
    """
    global trainer_found_reps, user_found_reps
    global last_trainer_inference, last_user_inference, last_rep_joint_names, last_rep_framecount
    
    # Get the top 6 joints from trainer (trainer defines the exercise)
    joint_names = get_top_6_joints(trainer_stores)
    
    if len(joint_names) == 0:
        return  # No joints with data yet
    
    # Get frame count for current exercise
    framecount = get_exercise_frame_count(trainer_stores)
    
    if framecount < 60:
        return  # Less than ~1 second of data, not enough for segmentation
    
    # Run rep segmentation on both trainer and user
    trainer_reps, trainer_inf = repsegment(trainer_stores, joint_names, framecount)
    user_reps, user_inf = repsegment(user_stores, joint_names, framecount)
    
    # Store inference results for visualization endpoint
    last_trainer_inference = trainer_inf
    last_user_inference = user_inf
    last_rep_joint_names = joint_names
    last_rep_framecount = framecount
    
    # Filter out overlapping (already-detected) reps for trainer
    new_trainer_reps = []
    for rep in trainer_reps:
        if not is_overlapping_rep(rep[0], rep[1], trainer_found_reps):
            new_trainer_reps.append(rep)
            trainer_found_reps.append([rep[0], rep[1]])
    
    # Filter out overlapping (already-detected) reps for user
    new_user_reps = []
    for rep in user_reps:
        if not is_overlapping_rep(rep[0], rep[1], user_found_reps):
            new_user_reps.append(rep)
            user_found_reps.append([rep[0], rep[1]])
    
    # Print compact rep count line whenever a new rep is detected
    if new_trainer_reps or new_user_reps:
        print(f"user rep {len(user_found_reps)}\ttrainer rep {len(trainer_found_reps)}")
    
    # Send only new (non-overlapping) reps to feedback system
    if new_trainer_reps or new_user_reps:
        feedbacksystem(new_user_reps, new_trainer_reps, joint_names)


# ============================================================================
# DATA PROCESSING
# ============================================================================

def process_batch(batch_data: Dict) -> Dict:
    """
    Process a batch of frames and store the data
    Returns statistics about what was processed
    """
    frames = batch_data.get('frames', [])
    frame_count = batch_data.get('frameCount', len(frames))
    batch_timestamp = batch_data.get('batchTimestamp', datetime.now().timestamp())
    
    stats = {
        'batch_timestamp': batch_timestamp,
        'frame_count': frame_count,
        'frames_processed': 0,
        'trainer_joints_found': set(),
        'user_joints_found': set(),
        'sample_values': {},
        'exercise_change_detected': False
    }
    
    # Process each frame
    for frame in frames:
        frame_timestamp = frame.get('t', datetime.now().timestamp()) / 1000.0  # Convert ms to seconds
        stats['frames_processed'] += 1
        
        # === EXERCISE CHANGE DETECTION via Gesture Sequence ===
        gesture = frame.get('gest')
        
        global thumbs_up_timestamp, exercise_change_count, feedback_batch_count, feedback_check_flag, feedback_complete
        
        if gesture == "Thumb_Up":
            # Store the LAST (latest) Thumb_Up timestamp
            thumbs_up_timestamp = frame_timestamp
            print(f"[GESTURE] Thumb_Up detected at {frame_timestamp}, waiting for Thumb_Down within 3 seconds")
        
        elif gesture == "Thumb_Down" and thumbs_up_timestamp is not None:
            # Check if Thumb_Down is within 3 seconds of the last Thumb_Up
            elapsed = frame_timestamp - thumbs_up_timestamp
            
            if elapsed <= EXERCISE_CHANGE_WINDOW:
                # EXERCISE CHANGE DETECTED - Reset all statistics
                print("\n" + "="*80)
                print(f"🔄 EXERCISE CHANGE DETECTED!")
                print(f"   Gesture Sequence: Thumb_Up → Thumb_Down ({elapsed:.2f}s)")
                print(f"   Action: Resetting all statistics")
                print(f"   New Exercise Session: #{exercise_change_count + 1}")
                print("="*80 + "\n")
                
                for store in trainer_stores.values():
                    store.clear_average_values()
                for store in user_stores.values():
                    store.clear_average_values()
                
                exercise_change_count += 1
                thumbs_up_timestamp = None
                stats['exercise_change_detected'] = True
                stats['exercise_change_number'] = exercise_change_count
                _reset_feedback_state()
                # Clear found reps for new exercise
                trainer_found_reps.clear()
                user_found_reps.clear()
                # Clear inference results for visualization
                global last_trainer_inference, last_user_inference, last_rep_joint_names, last_rep_framecount
                last_trainer_inference = None
                last_user_inference = None
                last_rep_joint_names = []
                last_rep_framecount = 0
            else:
                # Thumb_Down came too late, reset waiting state
                thumbs_up_timestamp = None
        
        # Check if Thumb_Up gesture sequence expired
        if thumbs_up_timestamp is not None and (frame_timestamp - thumbs_up_timestamp) > EXERCISE_CHANGE_WINDOW:
            thumbs_up_timestamp = None
        
        # Extract isPlaying from frame and detect pause state transitions
        is_playing = frame.get('isPlaying', True)
        
        global pause_flag
        
        if not is_playing and not pause_flag:
            # Video just paused - clear average values
            pause_flag = True
            print("[PAUSE] Video paused - clearing average values")
            for store in trainer_stores.values():
                store.clear_average_values()
            for store in user_stores.values():
                store.clear_average_values()
            thumbs_up_timestamp = None  # Reset gesture state
            _reset_feedback_state()
            stats['statistics_reset_at_frame'] = stats['frames_processed']
        
        elif is_playing and pause_flag:
            # Video just resumed - clear average values IMMEDIATELY before processing this frame
            pause_flag = False
            print("[RESUME] Video resumed - clearing average values only")
            for store in trainer_stores.values():
                store.clear_average_values()
            for store in user_stores.values():
                store.clear_average_values()
            thumbs_up_timestamp = None  # Reset gesture state
            _reset_feedback_state()
            stats['statistics_reset_at_frame'] = stats['frames_processed']
        
        # Skip joint data processing entirely while video is paused
        if not is_playing:
            continue

        # Process each joint key in the frame
        for key, value in frame.items():
            if key in ('t', 'gest', 'isPlaying'):  # Skip timestamp, gesture, and isPlaying
                continue
            
            # Determine if this is trainer or user data
            if key.startswith('tr_'):
                prefix = 'tr_'
                is_trainer = True
                stores_dict = trainer_stores
            elif key.startswith('u_'):
                prefix = 'u_'
                is_trainer = False
                stores_dict = user_stores
            else:
                continue
            
            # Extract the joint key (e.g., 'ls' from 'tr_ls' or 'u_ls')
            joint_key = key[len(prefix):]
            
            # Map to full joint name
            joint_name = JOINT_KEY_MAPPING.get(joint_key)
            if not joint_name:
                print(f"[WARNING] Unknown joint key: {joint_key}")
                continue
            
            # Extract angle and confidence from [angle, confidence] array
            if isinstance(value, list) and len(value) >= 2:
                angle = value[0]
                confidence = value[1]
                
                # Apply confidence threshold filtering (matching main.py logic)
                angle_to_store = angle
                
                if is_trainer:
                    # Trainer data
                    if confidence >= CONFIDENCE_THRESHOLD:
                        # Good confidence - use actual angle
                        angle_to_store = angle
                        last_valid_trainer_angles[joint_name] = angle
                    else:
                        # Low confidence
                        if joint_name in last_valid_trainer_angles:
                            # Use previous valid angle
                            angle_to_store = last_valid_trainer_angles[joint_name]
                        else:
                            # First frame with low confidence - store anyway as baseline
                            angle_to_store = angle
                            last_valid_trainer_angles[joint_name] = angle
                else:
                    # User data
                    if confidence >= CONFIDENCE_THRESHOLD:
                        # Good confidence - use actual angle
                        angle_to_store = angle
                        last_valid_user_angles[joint_name] = angle
                    else:
                        # Low confidence
                        if joint_name in last_valid_user_angles:
                            # Use previous valid angle
                            angle_to_store = last_valid_user_angles[joint_name]
                        else:
                            # First frame with low confidence - store anyway as baseline
                            angle_to_store = angle
                            last_valid_user_angles[joint_name] = angle
                
                # Store the data (filtered angle with original confidence)
                if joint_name in stores_dict:
                    stores_dict[joint_name].add_data_point(frame_timestamp, angle_to_store, confidence)
                    
                    # Track which joints were found
                    if is_trainer:
                        stats['trainer_joints_found'].add(joint_name)
                    else:
                        stats['user_joints_found'].add(joint_name)
                    
                    # Store sample values for the first frame
                    if stats['frames_processed'] == 1:
                        if joint_name not in stats['sample_values']:
                            stats['sample_values'][joint_name] = {}
                        
                        if is_trainer:
                            stats['sample_values'][joint_name]['trainer'] = {
                                'angle': angle,
                                'confidence': confidence
                            }
                        else:
                            stats['sample_values'][joint_name]['user'] = {
                                'angle': angle,
                                'confidence': confidence
                            }
    
    # Convert sets to lists for JSON serialization
    stats['trainer_joints_found'] = sorted(list(stats['trainer_joints_found']))
    stats['user_joints_found'] = sorted(list(stats['user_joints_found']))
    
    # Finalize batch: Update cumulative averages for all joints
    for store in trainer_stores.values():
        store.finalize_batch()
    for store in user_stores.values():
        store.finalize_batch()
    
    return stats


# ============================================================================
# FEEDBACK MANAGER
# ============================================================================

class FeedbackManager:
    """
    Manages feedback messages for the frontend.
    Sends text messages via WebSocket.
    """
    
    def __init__(self):
        self.websocket = None
        
    def set_websocket(self, websocket):
        """Set the active WebSocket connection for sending messages"""
        self.websocket = websocket
        
    def clear_websocket(self):
        """Clear the WebSocket connection when client disconnects"""
        self.websocket = None
        
    async def clear_frontend_message_section(self):
        """
        Send command to clear all feedback messages on the frontend
        """
        if self.websocket:
            try:
                await self.websocket.send_json({
                    "type": "feedback_clear",
                    "message": "clear_all"
                })
                print("[FEEDBACK] Cleared frontend message section")
            except Exception as e:
                print(f"[FEEDBACK ERROR] Failed to clear messages: {e}")
    
    async def send_message(self, message: str):
        """
        Send a text message to the frontend
        
        Args:
            message: Text message to send
        """
        if not self.websocket:
            print("[FEEDBACK] No active WebSocket connection")
            return
            
        try:
            await self.websocket.send_json({
                "type": "feedback",
                "message": message,
                "timestamp": datetime.now().isoformat()
            })
            print(f"[FEEDBACK] Sent message: {message[:50]}...")
            
        except Exception as e:
            print(f"[FEEDBACK ERROR] Failed to send message: {e}")


# Global feedback manager instance
feedback_manager = FeedbackManager()


# ============================================================================
# FASTAPI APPLICATION
# ============================================================================

app = FastAPI(title="Posture Data Processor", version="1.0.0")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for development
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Store active WebSocket connections for plot updates
plot_websocket_connections = []

async def broadcast_update():
    """Broadcast update notification to all connected plot viewers"""
    for connection in plot_websocket_connections[:]:
        try:
            await connection.send_json({"type": "data_updated"})
        except Exception as e:
            print(f"[BROADCAST ERROR] Failed to send: {e}")
            plot_websocket_connections.remove(connection)

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """
    WebSocket endpoint to receive batched frame data from frontend
    Expected format: {frames: [...], frameCount: N, batchTimestamp: T}
    """
    await websocket.accept()
    print("\n[WEBSOCKET] Client connected to /ws")
    print("[WEBSOCKET] Waiting for data...")
    
    # Set the websocket for feedback manager
    feedback_manager.set_websocket(websocket)
    
    try:
        while True:
            # Receive data from client
            data = await websocket.receive_text()
            
            try:
                # Parse JSON data
                batch_data = json.loads(data)
                
                # Process the batch and get statistics
                stats = process_batch(batch_data)

                # Run primary-angle feedback check (only while video is playing)
                if not pause_flag:
                    await run_feedback_check()

                # Run rep segmentation on every batch after primary joints are corrected
                if feedback_complete:
                    run_rep_segmentation()

                # Broadcast update to all connected plot viewers
                await broadcast_update()
                
            except json.JSONDecodeError as e:
                print(f"[ERROR] Failed to parse JSON: {e}")
                await websocket.send_json({
                    "status": "error",
                    "message": f"Invalid JSON: {str(e)}"
                })
            except Exception as e:
                print(f"[ERROR] Error processing batch: {e}")
                import traceback
                traceback.print_exc()
                await websocket.send_json({
                    "status": "error",
                    "message": f"Processing error: {str(e)}"
                })
    
    except WebSocketDisconnect:
        print("[WEBSOCKET] Client disconnected")
        feedback_manager.clear_websocket()
    except Exception as e:
        print(f"[WEBSOCKET ERROR] {e}")
        import traceback
        traceback.print_exc()
        feedback_manager.clear_websocket()

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Posture Data Processor is running",
        "websocket_endpoint": "/ws",
        "plot_endpoint": "/plot",
        "reps_endpoint": "/reps",
        "status": "active"
    }

@app.get("/plot", response_class=HTMLResponse)
async def get_plot_page():
    """HTML page with uPlot charts showing all stored data"""
    
    # Get active filter info for display
    filter_descriptions = {
        'savgol': 'Savitzky-Golay - Preserves peaks and valleys',
        'ema': 'Exponential Moving Average - Fast response, minimal lag',
        'double_ema': 'Double EMA - Handles trends well',
        'gaussian': 'Gaussian - Heavy noise reduction, smooth curves',
        'kalman': 'Kalman - Optimal for noisy sensor data',
        'hybrid': 'Hybrid - Best overall (Kalman + Savitzky-Golay + EMA)'
    }
    filter_type = SMOOTHING_CONFIG['filter_type']
    filter_desc = filter_descriptions.get(filter_type, 'Unknown filter')
    
    html_content = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Posture Data - Live Plot</title>
        <script src="https://unpkg.com/uplot@1.6.24/dist/uPlot.iife.min.js"></script>
        <link rel="stylesheet" href="https://unpkg.com/uplot@1.6.24/dist/uPlot.min.css">
        <style>
            body {
                font-family: Arial, sans-serif;
                margin: 20px;
                background-color: #f5f5f5;
            }
            h1 {
                color: #333;
                text-align: center;
            }
            .container {
                max-width: 1600px;
                margin: 0 auto;
            }
            .charts-grid {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(400px, 1fr));
                gap: 15px;
                margin-bottom: 20px;
            }
            .chart-container {
                background: white;
                border-radius: 8px;
                padding: 15px;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            }
            .chart-container h3 {
                margin-top: 0;
                margin-bottom: 10px;
                color: #555;
                font-size: 14px;
            }
            .u-legend {
                font-size: 11px;
            }
            .info-box {
                background: #e3f2fd;
                border-left: 4px solid #2196f3;
                padding: 15px;
                margin-bottom: 20px;
                border-radius: 4px;
                font-size: 14px;
            }
            .refresh-button {
                display: block;
                margin: 20px auto;
                padding: 10px 30px;
                background: #2196f3;
                color: white;
                border: none;
                border-radius: 5px;
                font-size: 16px;
                cursor: pointer;
            }
            .refresh-button:hover {
                background: #1976d2;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>Posture Data - Live Plot (Raw Data)</h1>
            
            <div class="info-box">
                <strong>Data Source:</strong> Stored in Python JointDataStore objects<br>
                <strong>Visualization:</strong> Raw (confidence-filtered) + Smoothed angles<br>
                <strong>Active Filter:</strong> <code>" + filter_type.upper() + "</code> - " + filter_desc + "<br>
                <strong>Confidence Threshold:</strong> ≥40%<br>
                <strong>Time Window:</strong> Last 10 seconds of data<br>
                <strong>Updates:</strong> Real-time via WebSocket (updates as data arrives)
            </div>
            
            <button class="refresh-button" onclick="loadData()">Manual Refresh</button>
            
            <div class="charts-grid" id="charts-container"></div>
        </div>

        <script>
            // Joint mapping
            const joints = {
                'Left Shoulder': 'Left Shoulder',
                'Left Elbow': 'Left Elbow',
                'Left Wrist': 'Left Wrist',
                'Right Shoulder': 'Right Shoulder',
                'Right Elbow': 'Right Elbow',
                'Right Wrist': 'Right Wrist',
                'Left Hip': 'Left Hip',
                'Left Knee': 'Left Knee',
                'Left Ankle': 'Left Ankle',
                'Right Hip': 'Right Hip',
                'Right Knee': 'Right Knee',
                'Right Ankle': 'Right Ankle',
                'Left Spine': 'Left Spine',
                'Right Spine': 'Right Spine',
                'Neck': 'Neck'
            };
            
            const charts = {};
            const chartsContainer = document.getElementById('charts-container');
            
            // Create a chart for each joint
            Object.keys(joints).forEach(jointName => {
                // Create container
                const container = document.createElement('div');
                container.className = 'chart-container';
                container.innerHTML = `<h3>${jointName} (Count: <span id="count-${jointName.replace(/\\s/g, '-')}">0</span>)</h3>`;
                chartsContainer.appendChild(container);
                
                // uPlot options
                const opts = {
                    width: 400,
                    height: 200,
                    scales: {
                        x: {
                            time: true
                        },
                        y: {
                            range: [0, 180]
                        }
                    },
                    series: [
                        {
                            label: "Time",
                            value: (u, v) => {
                                if (v == null) return "-";
                                const date = new Date(v * 1000);
                                const minutes = String(date.getMinutes()).padStart(2, '0');
                                const seconds = String(date.getSeconds()).padStart(2, '0');
                                const milliseconds = String(date.getMilliseconds()).padStart(3, '0');
                                return `${minutes}:${seconds}.${milliseconds}`;
                            }
                        },
                        {
                            label: "User Raw",
                            stroke: "#2196F3",
                            width: 1.5,
                            points: { show: false }
                        },
                        {
                            label: "Trainer Raw",
                            stroke: "#4CAF50",
                            width: 1.5,
                            points: { show: false }
                        },
                        {
                            label: "User Smoothed",
                            stroke: "#FF6B6B",
                            width: 2.5,
                            points: { show: false },
                            
                        },
                        {
                            label: "Trainer Smoothed",
                            stroke: "#FFA500",
                            width: 2.5,
                            points: { show: false },
                            
                        }
                    ],
                    axes: [
                        {
                            stroke: "#64748b",
                            grid: { stroke: "#e2e8f0", width: 1 }
                        },
                        {
                            stroke: "#64748b",
                            grid: { stroke: "#e2e8f0", width: 1 },
                            label: "Angle (°)"
                        }
                    ],
                    legend: {
                        show: true
                    }
                };
                
                // Create chart with initial empty data (5 series)
                const data = [
                    [0],
                    [0],
                    [0],
                    [0],
                    [0]
                ];
                
                charts[jointName] = new uPlot(opts, data, container);
            });
            
            // Function to load data from the API
            async function loadData() {
                try {
                    const response = await fetch('/api/plot-data');
                    const data = await response.json();
                    
                    // Update each chart with stored data
                    Object.keys(joints).forEach(jointName => {
                        const trainerStore = data.trainer_stores[jointName];
                        const userStore = data.user_stores[jointName];
                        
                        // Get timestamps and angles
                        const trainerTimestamps = trainerStore.timestamps || [];
                        const trainerAngles = trainerStore.angles || [];
                        const trainerAnglesSmoothed = trainerStore.angles_smoothed || [];
                        const userTimestamps = userStore.timestamps || [];
                        const userAngles = userStore.angles || [];
                        const userAnglesSmoothed = userStore.angles_smoothed || [];
                        
                        // Combine timestamps (union of both)
                        const allTimestamps = [...new Set([...trainerTimestamps, ...userTimestamps])].sort();
                        
                        // If no data, use dummy data
                        if (allTimestamps.length === 0) {
                            charts[jointName].setData([[0], [null], [null], [null], [null]]);
                            const countElement = document.getElementById(`count-$\{jointName.replace(/\\s/g, '-')}`);
                            if (countElement) {
                                countElement.textContent = '0';
                            }
                            return;
                        }
                        
                        // Prepare data for uPlot - map to combined timeline
                        const userAnglesAligned = allTimestamps.map(t => {
                            const idx = userTimestamps.indexOf(t);
                            return idx >= 0 ? userAngles[idx] : null;
                        });
                        const trainerAnglesAligned = allTimestamps.map(t => {
                            const idx = trainerTimestamps.indexOf(t);
                            return idx >= 0 ? trainerAngles[idx] : null;
                        });
                        const userAnglesSmoothedAligned = allTimestamps.map(t => {
                            const idx = userTimestamps.indexOf(t);
                            return idx >= 0 ? userAnglesSmoothed[idx] : null;
                        });
                        const trainerAnglesSmoothedAligned = allTimestamps.map(t => {
                            const idx = trainerTimestamps.indexOf(t);
                            return idx >= 0 ? trainerAnglesSmoothed[idx] : null;
                        });
                        
                        // Update chart with 5 series
                        const chartData = [
                            allTimestamps,
                            userAnglesAligned,
                            trainerAnglesAligned,
                            userAnglesSmoothedAligned,
                            trainerAnglesSmoothedAligned
                        ];
                        
                        charts[jointName].setData(chartData);
                        
                        // Update count
                        const totalCount = trainerStore.count + userStore.count;
                        const countElement = document.getElementById(`count-$\{jointName.replace(/\\s/g, '-')}`);
                        if (countElement) {
                            countElement.textContent = totalCount;
                        }
                    });
                    
                    console.log('Charts updated successfully');
                } catch (error) {
                    console.error('Error loading data:', error);
                }
            }
            
            // Connect to WebSocket for real-time updates
            let plotWs = null;
            
            function connectPlotWebSocket() {
                plotWs = new WebSocket('ws://127.0.0.1:8000/ws/plot-updates');
                
                plotWs.onopen = () => {
                    console.log('[PLOT WS] Connected to plot updates');
                };
                
                plotWs.onmessage = (event) => {
                    const data = JSON.parse(event.data);
                    if (data.type === 'data_updated') {
                        console.log('[PLOT WS] Data updated, refreshing charts...');
                        loadData();
                    }
                };
                
                plotWs.onerror = (error) => {
                    console.error('[PLOT WS] Error:', error);
                };
                
                plotWs.onclose = () => {
                    console.log('[PLOT WS] Disconnected, reconnecting in 2 seconds...');
                    setTimeout(connectPlotWebSocket, 2000);
                };
            }
            
            // Load data initially
            loadData();
            
            // Connect to WebSocket for real-time updates
            connectPlotWebSocket();
        </script>
    </body>
    </html>
    """
    
    return HTMLResponse(content=html_content)

@app.get("/api/plot-data")
async def get_plot_data():
    """Get last 10 seconds of stored data for plotting"""
    import time
    current_time = time.time()
    ten_seconds_ago = current_time - 5
    
    def filter_last_10_seconds(store):
        """Filter data to only include last 10 seconds"""
        if len(store.timestamps) == 0:
            return {
                "timestamps": [],
                "angles": [],
                "confidences": [],
                "count": 0
            }
        
        # Find indices where timestamp >= ten_seconds_ago
        filtered_indices = [i for i, t in enumerate(store.timestamps) if t >= ten_seconds_ago]
        
        if not filtered_indices:
            return {
                "timestamps": [],
                "angles": [],
                "confidences": [],
                "count": 0
            }
        
        return {
            "timestamps": [store.timestamps[i] for i in filtered_indices],
            "angles": [store.angles[i] for i in filtered_indices],
            "angles_smoothed": [store.angles_smoothed[i] for i in filtered_indices],
            "confidences": [store.confidences[i] for i in filtered_indices],
            "count": len(filtered_indices)
        }
    
    return {
        "timestamp": datetime.now().isoformat(),
        "trainer_stores": {
            joint_name: filter_last_10_seconds(store)
            for joint_name, store in trainer_stores.items()
        },
        "user_stores": {
            joint_name: filter_last_10_seconds(store)
            for joint_name, store in user_stores.items()
        }
    }

@app.get("/statistics")
async def get_statistics():
    """Get cumulative statistics (average & std dev) for all joints (calculated from raw data)"""
    return {
        "timestamp": datetime.now().isoformat(),
        "trainer_statistics": {
            joint_name: {
                "joint_name": joint_name,
                "cumulative_average": store.get_cumulative_average(),
                "cumulative_average_precise": store.get_cumulative_average_precise(),
                "cumulative_std_dev": store.get_cumulative_std_dev(),
                "cumulative_std_dev_precise": store.get_cumulative_std_dev_precise(),
                "total_data_points": store.raw_angles_count
            }
            for joint_name, store in trainer_stores.items()
        },
        "user_statistics": {
            joint_name: {
                "joint_name": joint_name,
                "cumulative_average": store.get_cumulative_average(),
                "cumulative_average_precise": store.get_cumulative_average_precise(),
                "cumulative_std_dev": store.get_cumulative_std_dev(),
                "cumulative_std_dev_precise": store.get_cumulative_std_dev_precise(),
                "total_data_points": store.raw_angles_count
            }
            for joint_name, store in user_stores.items()
        }
    }

@app.get("/last-stats")
async def get_last_stats(window_size: int = 120):
    """
    Get window statistics (average & std dev) for all joints (calculated from filtered interpolated data)
    
    Args:
        window_size: Number of interpolated points to average (default: 120)
    """
    return {
        "timestamp": datetime.now().isoformat(),
        "window_size": window_size,
        "trainer_last_average": {
            joint_name: {
                "joint_name": joint_name,
                "window_average": store.get_window_average_rounded(window_size),
                "window_average_precise": store.get_window_average(window_size),
                "window_std_dev": store.get_window_std_dev(window_size),
                "window_std_dev_precise": store.get_window_std_dev_precise(window_size),
                "elements_used": store.get_window_average_count(window_size),
                "available_data_points": len(store.interpolated_filtered)
            }
            for joint_name, store in trainer_stores.items()
        },
        "user_last_average": {
            joint_name: {
                "joint_name": joint_name,
                "window_average": store.get_window_average_rounded(window_size),
                "window_average_precise": store.get_window_average(window_size),
                "window_std_dev": store.get_window_std_dev(window_size),
                "window_std_dev_precise": store.get_window_std_dev_precise(window_size),
                "elements_used": store.get_window_average_count(window_size),
                "available_data_points": len(store.interpolated_filtered)
            }
            for joint_name, store in user_stores.items()
        }
    }

def calculate_primary_joints(stores_dict: dict) -> dict:
    """
    Calculate primary joints based on standard deviation analysis.
    
    Algorithm:
    1. Get std dev for all joints (excluding Left Wrist and Right Wrist)
    2. Sort by std dev in descending order
    3. Calculate differences between consecutive std devs
    4. Find the maximum difference
    5. All joints above (before) that max difference are considered primary
    
    Returns:
        dict with 'primary_joints' list and 'all_joints_sorted' list with details
    """
    # Joints to ignore in primary joint analysis
    ignored_joints = {"Left Wrist", "Right Wrist", "Neck"}
    
    # Collect std dev for all joints
    joint_std_devs = []
    for joint_name, store in stores_dict.items():
        # Skip ignored joints
        if joint_name in ignored_joints:
            continue
            
        std_dev = store.get_cumulative_std_dev_precise()
        if std_dev is not None:
            joint_std_devs.append({
                "joint_name": joint_name,
                "std_dev": std_dev,
                "cumulative_average": store.get_cumulative_average_precise(),
                "data_points": store.raw_angles_count
            })
    
    # Sort by std dev descending
    joint_std_devs.sort(key=lambda x: x["std_dev"], reverse=True)

    # If the highest std dev is below threshold, no meaningful movement detected
    MIN_STD_DEV = 5.0
    if not joint_std_devs or joint_std_devs[0]["std_dev"] < MIN_STD_DEV:
        return {
            "primary_joints": [],
            "primary_count": 0,
            "total_joints": len(joint_std_devs),
            "all_joints_sorted": joint_std_devs,
            "max_difference": None,
            "all_differences": []
        }

    # Calculate differences between consecutive std devs
    differences = []
    for i in range(len(joint_std_devs) - 1):
        diff = joint_std_devs[i]["std_dev"] - joint_std_devs[i + 1]["std_dev"]
        differences.append({
            "index": i,
            "diff": diff,
            "from_joint": joint_std_devs[i]["joint_name"],
            "to_joint": joint_std_devs[i + 1]["joint_name"],
            "from_std_dev": joint_std_devs[i]["std_dev"],
            "to_std_dev": joint_std_devs[i + 1]["std_dev"]
        })
    
    # Find maximum difference
    primary_joints = []
    max_diff_info = None
    
    if differences:
        max_diff_info = max(differences, key=lambda x: x["diff"])
        cutoff_index = max_diff_info["index"]
        
        # All joints up to and including the cutoff_index are primary
        primary_joints = [joint["joint_name"] for joint in joint_std_devs[:cutoff_index + 1]]
    
    return {
        "primary_joints": primary_joints,
        "primary_count": len(primary_joints),
        "total_joints": len(joint_std_devs),
        "all_joints_sorted": joint_std_devs,
        "max_difference": max_diff_info,
        "all_differences": differences
    }

def calculate_primary_joints_interpolated(stores_dict: dict) -> dict:
    """
    Calculate primary joints based on cumulative standard deviation of
    interpolated_filtered data (60 FPS, Kalman+Gaussian smoothed).
    
    Identical algorithm to calculate_primary_joints but driven by
    interp_cumulative_std_dev instead of raw-angle cumulative_std_dev.
    """
    ignored_joints = {"Left Wrist", "Right Wrist", "Neck"}
    
    joint_std_devs = []
    for joint_name, store in stores_dict.items():
        if joint_name in ignored_joints:
            continue
        
        std_dev = store.get_interp_cumulative_std_dev_precise()
        if std_dev is not None:
            joint_std_devs.append({
                "joint_name": joint_name,
                "std_dev": std_dev,
                "cumulative_average": store.get_interp_cumulative_average_precise(),
                "data_points": store.interp_count
            })
    
    joint_std_devs.sort(key=lambda x: x["std_dev"], reverse=True)

    # If the highest std dev is below threshold, no meaningful movement detected
    MIN_STD_DEV = 5.0
    if not joint_std_devs or joint_std_devs[0]["std_dev"] < MIN_STD_DEV:
        return {
            "primary_joints": [],
            "primary_count": 0,
            "total_joints": len(joint_std_devs),
            "all_joints_sorted": joint_std_devs,
            "max_difference": None,
            "all_differences": []
        }

    differences = []
    for i in range(len(joint_std_devs) - 1):
        diff = joint_std_devs[i]["std_dev"] - joint_std_devs[i + 1]["std_dev"]
        differences.append({
            "index": i,
            "diff": diff,
            "from_joint": joint_std_devs[i]["joint_name"],
            "to_joint": joint_std_devs[i + 1]["joint_name"],
            "from_std_dev": joint_std_devs[i]["std_dev"],
            "to_std_dev": joint_std_devs[i + 1]["std_dev"]
        })
    
    primary_joints = []
    max_diff_info = None
    
    if differences:
        max_diff_info = max(differences, key=lambda x: x["diff"])
        cutoff_index = max_diff_info["index"]
        primary_joints = [joint["joint_name"] for joint in joint_std_devs[:cutoff_index + 1]]
    
    return {
        "primary_joints": primary_joints,
        "primary_count": len(primary_joints),
        "total_joints": len(joint_std_devs),
        "all_joints_sorted": joint_std_devs,
        "max_difference": max_diff_info,
        "all_differences": differences
    }


# ============================================================================
# FEEDBACK ALGORITHM
# ============================================================================

def checkprimaryangles() -> dict:
    """
    Compare trainer primary joints (raw cumulative) vs user primary joints
    (interpolated cumulative).

    Returns:
        {
            'is_same': 1 (match) or 0 (mismatch),
            'feedback': str,
            'trainer_primary': List[str],
            'user_primary':    List[str]
        }
    """
    trainer_result = calculate_primary_joints(trainer_stores)
    user_result    = calculate_primary_joints_interpolated(user_stores)

    trainer_primary = trainer_result["primary_joints"]
    user_primary    = user_result["primary_joints"]

    # --- Debug print: all joints sorted by std dev ---
    print("\n" + "="*60)
    print("[PRIMARY ANGLES DEBUG]")
    print(f"{'TRAINER (raw cumulative)':^68}")
    print(f"  {'Joint':<22} {'Std Dev':>10}  {'N Values':>10}")
    print(f"  {'-'*22} {'-'*10}  {'-'*10}")
    for j in trainer_result["all_joints_sorted"]:
        marker = " <--" if j["joint_name"] in trainer_primary else ""
        print(f"  {j['joint_name']:<22} {j['std_dev']:>10.4f}  {j['data_points']:>10}{marker}")
    print(f"\n{'USER (interpolated cumulative)':^68}")
    print(f"  {'Joint':<22} {'Std Dev':>10}  {'N Values':>10}")
    print(f"  {'-'*22} {'-'*10}  {'-'*10}")
    for j in user_result["all_joints_sorted"]:
        marker = " <--" if j["joint_name"] in user_primary else ""
        print(f"  {j['joint_name']:<22} {j['std_dev']:>10.4f}  {j['data_points']:>10}{marker}")
    print(f"\n  Trainer primary: {trainer_primary}")
    print(f"  User primary:    {user_primary}")
    print("="*60 + "\n")
    # -------------------------------------------------

    # Not enough data yet — treat as match to avoid false negatives at startup
    

    # Build std-dev lookup dicts keyed by joint name for fast access
    trainer_std_map = {j["joint_name"]: j["std_dev"] for j in trainer_result["all_joints_sorted"]}
    user_std_map    = {j["joint_name"]: j["std_dev"] for j in user_result["all_joints_sorted"]}

    STD_TOLERANCE = 0.40   # ±40 %

    trainer_set = set(trainer_primary)
    user_set    = set(user_primary)

    if trainer_set == user_set:
        # Sets match — now check if each user std dev is within ±40 % of trainer's
        out_of_range = []
        for joint in sorted(trainer_set):
            t_std = trainer_std_map.get(joint)
            u_std = user_std_map.get(joint)
            if t_std is None or u_std is None or t_std == 0:
                continue
            lower = t_std * (1 - STD_TOLERANCE)
            upper = t_std * (1 + STD_TOLERANCE)
            if u_std < lower:
                out_of_range.append(f"More movement needed in {joint} "
                                    f"(you: {u_std:.1f}°, target: {t_std:.1f}°)")
            elif u_std > upper:
                out_of_range.append(f"Reduce movement in {joint} "
                                    f"(you: {u_std:.1f}°, target: {t_std:.1f}°)")

        if not out_of_range:
            return {
                "is_same": 1,
                "feedback": "Great form! Movement range matches the trainer.",
                "trainer_primary": trainer_primary,
                "user_primary": user_primary
            }
        else:
            return {
                "is_same": 0,
                "feedback": " | ".join(out_of_range),
                "trainer_primary": trainer_primary,
                "user_primary": user_primary
            }

    else:
        missing = sorted(trainer_set - user_set)   # trainer uses, user doesn't
        extra   = sorted(user_set - trainer_set)    # user uses, trainer doesn't
        parts   = []

        for joint in missing:
            parts.append(f"Focus more on {joint}")

        for joint in extra:
            t_std = trainer_std_map.get(joint)
            u_std = user_std_map.get(joint)
            if t_std is not None and u_std is not None and u_std > t_std:
                parts.append(f"Reduce movement in {joint} "
                             f"(you: {u_std:.1f}°, trainer: {t_std:.1f}°)")
            else:
                parts.append(f"Unnecessary movement detected in {joint}")

        feedback_str = " | ".join(parts) if parts else "Adjust your form to match the trainer."
        return {
            "is_same": 0,
            "feedback": feedback_str,
            "trainer_primary": trainer_primary,
            "user_primary": user_primary
        }


def _reset_user_primary_angles() -> None:
    """
    Reset only the interpolated cumulative stats for all user stores.
    Raw cumulative data is intentionally preserved.
    """
    for store in user_stores.values():
        store.clear_interpolated_cumulative_stats()


async def run_feedback_check() -> None:
    """
    Called after every processed batch.
    Implements the 5-batch primary-angle feedback loop:
      - Every 5 batches: compare primary joints.
      - On first mismatch: send negative feedback, set checkflag, start 1-batch-per-check window.
      - During check window (checkflag=True): silent on mismatch until count reaches 5,
        then send negative feedback and reset count.
      - Any match during check window or at the 5-batch gate: send positive feedback,
        clear all flags, stop checking until next exercise change.
    """
    global feedback_batch_count, feedback_check_flag, feedback_complete

    # Once positive feedback has been given, stop until next exercise
    if feedback_complete:
        return

    feedback_batch_count += 1

    if feedback_batch_count < 5 and not feedback_check_flag:
        return  # Still in the initial 5-batch wait window

    result = checkprimaryangles()

    if result["is_same"] == 1:
        # Positive — stop checking entirely
        await feedback_manager.send_message(result["feedback"])
        feedback_batch_count = 0
        feedback_check_flag  = False
        feedback_complete    = True

    else:
        # Negative
        if feedback_check_flag:
            # Already in the 1-sec check window
            if feedback_batch_count >= 5:
                # End of check window — send negative, restart window
                await feedback_manager.send_message(result["feedback"])
                feedback_batch_count = 0
                _reset_user_primary_angles()
                # feedback_check_flag stays True
            # else: silent (count 1-4)
        else:
            # First mismatch at the 5-batch gate
            await feedback_manager.send_message(result["feedback"])
            feedback_batch_count = 0
            feedback_check_flag  = True
            _reset_user_primary_angles()


def _reset_feedback_state() -> None:
    """Reset all feedback algorithm state (called on exercise change / pause / resume)."""
    global feedback_batch_count, feedback_check_flag, feedback_complete
    feedback_batch_count = 0
    feedback_check_flag  = False
    feedback_complete    = False


@app.get("/primary-joints")
async def get_primary_joints():
    """
    Analyze and return primary joints for both trainer and user based on standard deviation.
    Primary joints are those with significantly higher std dev (indicating actual movement).
    """
    trainer_analysis = calculate_primary_joints(trainer_stores)
    user_analysis = calculate_primary_joints(user_stores)
    
    return {
        "timestamp": datetime.now().isoformat(),
        "trainer": trainer_analysis,
        "user": user_analysis,
        "summary": {
            "trainer_primary_count": trainer_analysis["primary_count"],
            "trainer_total_joints": trainer_analysis["total_joints"],
            "user_primary_count": user_analysis["primary_count"],
            "user_total_joints": user_analysis["total_joints"]
        }
    }

@app.get("/primary-joints-interpolated")
async def get_primary_joints_interpolated():
    """
    Analyze and return primary joints for both trainer and user based on the
    cumulative standard deviation of interpolated_filtered (60 FPS smoothed) data.
    """
    trainer_analysis = calculate_primary_joints_interpolated(trainer_stores)
    user_analysis = calculate_primary_joints_interpolated(user_stores)
    
    return {
        "timestamp": datetime.now().isoformat(),
        "trainer": trainer_analysis,
        "user": user_analysis,
        "summary": {
            "trainer_primary_count": trainer_analysis["primary_count"],
            "trainer_total_joints": trainer_analysis["total_joints"],
            "user_primary_count": user_analysis["primary_count"],
            "user_total_joints": user_analysis["total_joints"]
        }
    }

@app.get("/exercise-info")
async def get_exercise_info():
    """Get current exercise change tracking information"""
    import time
    
    time_remaining = None
    if thumbs_up_timestamp is not None:
        current_time = time.time()
        elapsed = current_time - thumbs_up_timestamp
        if elapsed <= EXERCISE_CHANGE_WINDOW:
            time_remaining = EXERCISE_CHANGE_WINDOW - elapsed
    
    return {
        "timestamp": datetime.now().isoformat(),
        "exercise_change_count": exercise_change_count,
        "thumbs_up_waiting": thumbs_up_timestamp is not None,
        "time_remaining": round(time_remaining, 2) if time_remaining is not None else None,
        "exercise_change_window": EXERCISE_CHANGE_WINDOW
    }

@app.api_route("/clear-all", methods=["GET", "POST"])
async def clear_all_data_endpoint():
    """
    Clear ALL data (raw angles, smoothed, interpolated, cumulative stats, filters)
    for every trainer and user joint store. Use this for a full reset between sessions.
    """
    global thumbs_up_timestamp, exercise_change_count
    global last_valid_trainer_angles, last_valid_user_angles
    for store in trainer_stores.values():
        store.clear_all_data()
    for store in user_stores.values():
        store.clear_all_data()
    # Clear confidence-fallback caches so no stale angles re-seed the stores
    last_valid_trainer_angles.clear()
    last_valid_user_angles.clear()
    thumbs_up_timestamp = None
    exercise_change_count = 0
    # Do NOT reset pause_flag — leave the state machine intact.
    # Resetting to False while paused would allow a mixed-isPlaying batch
    # to slip through the `if not is_playing: continue` guard on the same cycle.
    return {
        "status": "success",
        "message": "All joint data cleared",
        "timestamp": datetime.now().isoformat()
    }

@app.api_route("/clear-stats", methods=["GET", "POST"])
async def clear_stats_endpoint():
    """
    Clear only cumulative statistics (raw + interpolated averages and std devs)
    for every trainer and user joint store, without discarding the underlying
    angle or interpolated data. Marks the current interpolated position as the
    new reset point so window averages also start fresh from here.
    """
    for store in trainer_stores.values():
        store.clear_average_values()
    for store in user_stores.values():
        store.clear_average_values()
    return {
        "status": "success",
        "message": "Cumulative statistics cleared",
        "timestamp": datetime.now().isoformat()
    }

class FeedbackMessage(BaseModel):
    """Request model for sending feedback messages"""
    message: str

@app.post("/send")
async def send_feedback_message(feedback: FeedbackMessage):
    """
    Send a feedback message to the connected frontend client
    
    Request body:
        {"message": "Your feedback text here"}
    """
    await feedback_manager.send_message(feedback.message)
    return {
        "status": "success",
        "message": "Feedback sent",
        "timestamp": datetime.now().isoformat()
    }

@app.post("/clear")
async def clear_feedback_messages():
    """
    Clear all feedback messages on the frontend
    """
    await feedback_manager.clear_frontend_message_section()
    return {
        "status": "success",
        "message": "Feedback messages cleared",
        "timestamp": datetime.now().isoformat()
    }

@app.get("/live-primary-joints", response_class=HTMLResponse)
async def get_live_primary_joints():
    """HTML page showing live primary joints analysis with auto-refresh"""
    
    html_content = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Live Primary Joints Analysis</title>
    </head>
    <body>
        <h1>Live Primary Joints Analysis</h1>
        <p id="updateStatus">Loading...</p>
        
        <h2>Trainer Primary Joints</h2>
        <p id="trainerSummary">Loading...</p>
        <table id="trainerTable" border="1">
            <thead>
                <tr>
                    <th>Rank</th>
                    <th>Joint Name</th>
                    <th>Std Dev</th>
                    <th>Cumulative Avg</th>
                    <th>Data Points</th>
                    <th>Is Primary</th>
                </tr>
            </thead>
            <tbody id="trainerBody">
                <tr><td colspan="6">Loading...</td></tr>
            </tbody>
        </table>
        
        <h2>User Primary Joints</h2>
        <p id="userSummary">Loading...</p>
        <table id="userTable" border="1">
            <thead>
                <tr>
                    <th>Rank</th>
                    <th>Joint Name</th>
                    <th>Std Dev</th>
                    <th>Cumulative Avg</th>
                    <th>Data Points</th>
                    <th>Is Primary</th>
                </tr>
            </thead>
            <tbody id="userBody">
                <tr><td colspan="6">Loading...</td></tr>
            </tbody>
        </table>
        
        <h2>Max Difference Analysis</h2>
        <h3>Trainer</h3>
        <table id="trainerMaxDiff" border="1">
            <thead>
                <tr>
                    <th>From Joint</th>
                    <th>From Std Dev</th>
                    <th>To Joint</th>
                    <th>To Std Dev</th>
                    <th>Difference</th>
                </tr>
            </thead>
            <tbody id="trainerMaxDiffBody">
                <tr><td colspan="5">Loading...</td></tr>
            </tbody>
        </table>
        
        <h3>User</h3>
        <table id="userMaxDiff" border="1">
            <thead>
                <tr>
                    <th>From Joint</th>
                    <th>From Std Dev</th>
                    <th>To Joint</th>
                    <th>To Std Dev</th>
                    <th>Difference</th>
                </tr>
            </thead>
            <tbody id="userMaxDiffBody">
                <tr><td colspan="5">Loading...</td></tr>
            </tbody>
        </table>

        <script>
            let updateCount = 0;
            
            function formatValue(val) {
                if (val === null || val === undefined) return '—';
                if (typeof val === 'number') return val.toFixed(2);
                return val;
            }
            
            async function updatePrimaryJoints() {
                try {
                    const response = await fetch('/primary-joints');
                    const data = await response.json();
                    
                    // Update trainer summary
                    document.getElementById('trainerSummary').textContent = 
                        `Primary Joints: ${data.trainer.primary_count} / ${data.trainer.total_joints}`;
                    
                    // Update user summary
                    document.getElementById('userSummary').textContent = 
                        `Primary Joints: ${data.user.primary_count} / ${data.user.total_joints}`;
                    
                    // Update trainer table
                    let trainerHtml = '';
                    data.trainer.all_joints_sorted.forEach((joint, index) => {
                        const isPrimary = data.trainer.primary_joints.includes(joint.joint_name);
                        trainerHtml += `
                            <tr>
                                <td>${index + 1}</td>
                                <td>${joint.joint_name}</td>
                                <td>${formatValue(joint.std_dev)}</td>
                                <td>${formatValue(joint.cumulative_average)}</td>
                                <td>${joint.data_points}</td>
                                <td>${isPrimary ? '✓ PRIMARY' : ''}</td>
                            </tr>
                        `;
                    });
                    document.getElementById('trainerBody').innerHTML = trainerHtml;
                    
                    // Update user table
                    let userHtml = '';
                    data.user.all_joints_sorted.forEach((joint, index) => {
                        const isPrimary = data.user.primary_joints.includes(joint.joint_name);
                        userHtml += `
                            <tr>
                                <td>${index + 1}</td>
                                <td>${joint.joint_name}</td>
                                <td>${formatValue(joint.std_dev)}</td>
                                <td>${formatValue(joint.cumulative_average)}</td>
                                <td>${joint.data_points}</td>
                                <td>${isPrimary ? '✓ PRIMARY' : ''}</td>
                            </tr>
                        `;
                    });
                    document.getElementById('userBody').innerHTML = userHtml;
                    
                    // Update trainer max difference
                    if (data.trainer.max_difference) {
                        const md = data.trainer.max_difference;
                        document.getElementById('trainerMaxDiffBody').innerHTML = `
                            <tr>
                                <td>${md.from_joint}</td>
                                <td>${formatValue(md.from_std_dev)}</td>
                                <td>${md.to_joint}</td>
                                <td>${formatValue(md.to_std_dev)}</td>
                                <td>${formatValue(md.diff)}</td>
                            </tr>
                        `;
                    } else {
                        document.getElementById('trainerMaxDiffBody').innerHTML = 
                            '<tr><td colspan="5">No difference data</td></tr>';
                    }
                    
                    // Update user max difference
                    if (data.user.max_difference) {
                        const md = data.user.max_difference;
                        document.getElementById('userMaxDiffBody').innerHTML = `
                            <tr>
                                <td>${md.from_joint}</td>
                                <td>${formatValue(md.from_std_dev)}</td>
                                <td>${md.to_joint}</td>
                                <td>${formatValue(md.to_std_dev)}</td>
                                <td>${formatValue(md.diff)}</td>
                            </tr>
                        `;
                    } else {
                        document.getElementById('userMaxDiffBody').innerHTML = 
                            '<tr><td colspan="5">No difference data</td></tr>';
                    }
                    
                    updateCount++;
                    document.getElementById('updateStatus').textContent = 
                        `Last updated: ${new Date().toLocaleTimeString()} (Update #${updateCount})`;
                    
                } catch (error) {
                    document.getElementById('updateStatus').textContent = 
                        `Error: ${error.message}`;
                }
            }
            
            // Initial update
            updatePrimaryJoints();
            
            // Update every 1 second
            setInterval(updatePrimaryJoints, 1000);
        </script>
    </body>
    </html>
    """
    
    return HTMLResponse(content=html_content)

@app.get("/live-statistics", response_class=HTMLResponse)
async def get_live_statistics(window_size: int = 120):
    """HTML page showing live statistics table that updates every 500ms"""
    
    html_content = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Live Statistics - Posture Analysis</title>
    </head>
    <body>
        <h1>Live Statistics Monitor</h1>
        <p>Window Size: {window_size} frames | Auto-refresh: 500ms</p>
        <p id="updateStatus">Connecting...</p>
        
        <table id="statsTable" border="1">
            <thead>
                <tr>
                    <th>Joint Name</th>
                    <th>Role</th>
                    <th>Cumulative Avg</th>
                    <th>Cumulative Std Dev</th>
                    <th>Window Avg (Last {window_size})</th>
                    <th>Window Std Dev</th>
                    <th>Data Points (Total/Window)</th>
                </tr>
            </thead>
            <tbody id="statsBody">
                <tr><td colspan="7">Loading data...</td></tr>
            </tbody>
        </table>

        <script>
            const WINDOW_SIZE = {window_size};
            let updateCount = 0;
            
            function formatValue(value, decimals = 1) {{
                if (value === null || value === undefined) {{
                    return '—';
                }}
                return value.toFixed(decimals);
            }}
            
            function formatValueWithPrecise(value, preciseValue) {{
                if (value === null || value === undefined) {{
                    return '—';
                }}
                let text = value;
                if (preciseValue !== null && preciseValue !== undefined) {{
                    text += ` (${{preciseValue.toFixed(4)}})`;
                }}
                return text;
            }}
            
            async function updateStatistics() {{
                try {{
                    // Fetch both endpoints in parallel
                    const [cumulativeRes, windowRes] = await Promise.all([
                        fetch('/statistics'),
                        fetch(`/last-stats?window_size=${{WINDOW_SIZE}}`)
                    ]);
                    
                    const cumulativeData = await cumulativeRes.json();
                    const windowData = await windowRes.json();
                    
                    // Build table rows
                    let html = '';
                    
                    // Process trainer data
                    const trainerStats = cumulativeData.trainer_statistics;
                    const trainerWindow = windowData.trainer_last_average;
                    
                    Object.keys(trainerStats).forEach(jointName => {{
                        const cumStats = trainerStats[jointName];
                        const winStats = trainerWindow[jointName];
                        
                        html += `
                            <tr>
                                <td>${{jointName}}</td>
                                <td>TRAINER</td>
                                <td>${{formatValueWithPrecise(cumStats.cumulative_average, cumStats.cumulative_average_precise)}}</td>
                                <td>${{formatValueWithPrecise(cumStats.cumulative_std_dev, cumStats.cumulative_std_dev_precise)}}</td>
                                <td>${{formatValueWithPrecise(winStats.window_average, winStats.window_average_precise)}}</td>
                                <td>${{formatValueWithPrecise(winStats.window_std_dev, winStats.window_std_dev_precise)}}</td>
                                <td>${{cumStats.total_data_points}} / ${{winStats.elements_used}}</td>
                            </tr>
                        `;
                    }});
                    
                    // Process user data
                    const userStats = cumulativeData.user_statistics;
                    const userWindow = windowData.user_last_average;
                    
                    Object.keys(userStats).forEach(jointName => {{
                        const cumStats = userStats[jointName];
                        const winStats = userWindow[jointName];
                        
                        html += `
                            <tr>
                                <td>${{jointName}}</td>
                                <td>USER</td>
                                <td>${{formatValueWithPrecise(cumStats.cumulative_average, cumStats.cumulative_average_precise)}}</td>
                                <td>${{formatValueWithPrecise(cumStats.cumulative_std_dev, cumStats.cumulative_std_dev_precise)}}</td>
                                <td>${{formatValueWithPrecise(winStats.window_average, winStats.window_average_precise)}}</td>
                                <td>${{formatValueWithPrecise(winStats.window_std_dev, winStats.window_std_dev_precise)}}</td>
                                <td>${{cumStats.total_data_points}} / ${{winStats.elements_used}}</td>
                            </tr>
                        `;
                    }});
                    
                    document.getElementById('statsBody').innerHTML = html;
                    
                    updateCount++;
                    document.getElementById('updateStatus').textContent = 
                        `Live | Updates: ${{updateCount}} | Last: ${{new Date().toLocaleTimeString()}}`;
                    
                }} catch (error) {{
                    console.error('Error fetching statistics:', error);
                    document.getElementById('updateStatus').textContent = 'Connection Error';
                }}
            }}
            
            // Initial update
            updateStatistics();
            
            // Update every 500ms
            setInterval(updateStatistics, 500);
        </script>
    </body>
    </html>
    """
    
    return HTMLResponse(content=html_content)

@app.get("/interpolated-plot", response_class=HTMLResponse)
async def get_interpolated_plot_page():
    """HTML page with uPlot charts showing 60 FPS interpolated data for all 15 joints"""
    
    html_content = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>60 FPS Interpolated Data - Live Plot</title>
        <script src="https://unpkg.com/uplot@1.6.24/dist/uPlot.iife.min.js"></script>
        <link rel="stylesheet" href="https://unpkg.com/uplot@1.6.24/dist/uPlot.min.css">
        <style>
            body {
                font-family: Arial, sans-serif;
                margin: 20px;
                background-color: #f5f5f5;
            }
            h1 {
                color: #333;
                text-align: center;
            }
            .container {
                max-width: 1600px;
                margin: 0 auto;
            }
            .charts-grid {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(400px, 1fr));
                gap: 15px;
                margin-bottom: 20px;
            }
            .chart-container {
                background: white;
                border-radius: 8px;
                padding: 15px;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            }
            .chart-container h3 {
                margin-top: 0;
                margin-bottom: 10px;
                color: #555;
                font-size: 14px;
            }
            .u-legend {
                font-size: 11px;
            }
            .info-box {
                background: #d1f2eb;
                border-left: 4px solid #00C853;
                padding: 15px;
                margin-bottom: 20px;
                border-radius: 4px;
                font-size: 14px;
            }
            .warning-box {
                background: #fff3cd;
                border-left: 4px solid #ffc107;
                padding: 10px 15px;
                margin-bottom: 20px;
                border-radius: 4px;
                font-size: 13px;
            }
            .refresh-button {
                display: block;
                margin: 20px auto;
                padding: 10px 30px;
                background: #00C853;
                color: white;
                border: none;
                border-radius: 5px;
                font-size: 16px;
                cursor: pointer;
            }
            .refresh-button:hover {
                background: #00A844;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>📊 60 FPS Interpolated Data - Live Plot</h1>
            
            <div class="info-box">
                <strong>Data Type:</strong> 60 FPS Interpolated (Second-Boundary Aligned) + Filtered<br>
                <strong>Interpolation:</strong> Linear interpolation with incremental updates<br>
                <strong>Filtering:</strong> Same filter applied to interpolated data for smoothness<br>
                <strong>FPS:</strong> Exactly 60 frames per second (0.0167s intervals)<br>
                <strong>Alignment:</strong> Indices 0-59 = 1st second, 60-119 = 2nd second, etc.<br>
                <strong>Display:</strong> Last 5 seconds (300 frames) shown for both raw interpolated and filtered<br>
                <strong>Updates:</strong> Real-time via WebSocket (auto-updates as batches arrive)
            </div>
            
            <div class="warning-box">
                ⚠️ <strong>Note:</strong> X-axis shows frame indices (not timestamps). Each point is exactly 1/60th of a second apart. Lighter colors show filtered data for smoother visualization.
            </div>
            
            <button class="refresh-button" onclick="loadData()">🔄 Manual Refresh</button>
            
            <div class="charts-grid" id="charts-container"></div>
        </div>

        <script>
            // Joint names
            const joints = [
                'Left Shoulder',
                'Left Elbow',
                'Left Wrist',
                'Right Shoulder',
                'Right Elbow',
                'Right Wrist',
                'Left Hip',
                'Left Knee',
                'Left Ankle',
                'Right Hip',
                'Right Knee',
                'Right Ankle',
                'Left Spine',
                'Right Spine',
                'Neck'
            ];
            
            const charts = {};
            const chartsContainer = document.getElementById('charts-container');
            
            // Create a chart for each joint
            joints.forEach(jointName => {
                // Create container
                const container = document.createElement('div');
                container.className = 'chart-container';
                container.innerHTML = `<h3>${jointName} (<span id="count-${jointName.replace(/\\s/g, '-')}">0</span> frames @ 60fps)</h3>`;
                chartsContainer.appendChild(container);
                
                // uPlot options
                const opts = {
                    width: 400,
                    height: 200,
                    scales: {
                        x: {
                            time: false
                        },
                        y: {
                            range: [0, 180]
                        }
                    },
                    series: [
                        {
                            label: "Frame Index",
                            value: (u, v) => v != null ? `Frame ${v}` : "-"
                        },
                        {
                            label: "User (60fps)",
                            stroke: "#FF1744",
                            width: 1.5,
                            points: { show: false }
                        },
                        {
                            label: "User Filtered",
                            stroke: "#FF8A80",
                            width: 2,
                            points: { show: false }
                        },
                        {
                            label: "Trainer (60fps)",
                            stroke: "#00C853",
                            width: 1.5,
                            points: { show: false }
                        },
                        {
                            label: "Trainer Filtered",
                            stroke: "#69F0AE",
                            width: 2,
                            points: { show: false }
                        }
                    ],
                    axes: [
                        {
                            stroke: "#64748b",
                            grid: { stroke: "#e2e8f0", width: 1 },
                            label: "Frame Index"
                        },
                        {
                            stroke: "#64748b",
                            grid: { stroke: "#e2e8f0", width: 1 },
                            label: "Angle (°)"
                        }
                    ],
                    legend: {
                        show: true
                    }
                };
                
                // Create chart with initial empty data
                const data = [
                    [0],
                    [0],
                    [0],
                    [0],
                    [0]
                ];
                
                charts[jointName] = new uPlot(opts, data, container);
            });
            
            // Function to load data from the API
            async function loadData() {
                try {
                    const response = await fetch('/api/interpolated-data');
                    const data = await response.json();
                    
                    // Update each chart with interpolated data
                    joints.forEach(jointName => {
                        const trainerData = data.trainer[jointName]?.interpolated || [];
                        const trainerFiltered = data.trainer[jointName]?.filtered || [];
                        const userData = data.user[jointName]?.interpolated || [];
                        const userFiltered = data.user[jointName]?.filtered || [];
                        
                        // Use the longest array length for frame indices
                        const maxLength = Math.max(
                            trainerData.length, 
                            trainerFiltered.length,
                            userData.length,
                            userFiltered.length
                        );
                        
                        if (maxLength === 0) {
                            charts[jointName].setData([[0], [null], [null], [null], [null]]);
                            const countElement = document.getElementById(`count-${jointName.replace(/\\s/g, '-')}`);
                            if (countElement) {
                                countElement.textContent = '0';
                            }
                            return;
                        }
                        
                        // Create frame indices (0, 1, 2, 3, ...)
                        const frameIndices = Array.from({length: maxLength}, (_, i) => i);
                        
                        // Pad shorter arrays with nulls
                        const userDataPadded = [...userData];
                        const userFilteredPadded = [...userFiltered];
                        const trainerDataPadded = [...trainerData];
                        const trainerFilteredPadded = [...trainerFiltered];
                        
                        while (userDataPadded.length < maxLength) userDataPadded.push(null);
                        while (userFilteredPadded.length < maxLength) userFilteredPadded.push(null);
                        while (trainerDataPadded.length < maxLength) trainerDataPadded.push(null);
                        while (trainerFilteredPadded.length < maxLength) trainerFilteredPadded.push(null);
                        
                        // Update chart
                        const chartData = [
                            frameIndices,
                            userDataPadded,
                            userFilteredPadded,
                            trainerDataPadded,
                            trainerFilteredPadded
                        ];
                        
                        charts[jointName].setData(chartData);
                        
                        // Update count
                        const countElement = document.getElementById(`count-${jointName.replace(/\\s/g, '-')}`);
                        if (countElement) {
                            const userCount = userData.length;
                            const trainerCount = trainerData.length;
                            countElement.innerHTML = `U:${userCount} / T:${trainerCount}`;
                        }
                    });
                    
                    console.log('Interpolated charts updated successfully');
                } catch (error) {
                    console.error('Error loading interpolated data:', error);
                }
            }
            
            // Connect to WebSocket for real-time updates
            let plotWs = null;
            
            function connectPlotWebSocket() {
                plotWs = new WebSocket('ws://127.0.0.1:8000/ws/plot-updates');
                
                plotWs.onopen = () => {
                    console.log('[INTERPOLATED PLOT WS] Connected');
                };
                
                plotWs.onmessage = (event) => {
                    const data = JSON.parse(event.data);
                    if (data.type === 'data_updated') {
                        loadData();
                    }
                };
                
                plotWs.onerror = (error) => {
                    console.error('[INTERPOLATED PLOT WS] Error:', error);
                };
                
                plotWs.onclose = () => {
                    console.log('[INTERPOLATED PLOT WS] Disconnected, reconnecting in 2 seconds...');
                    setTimeout(connectPlotWebSocket, 2000);
                };
            }
            
            // Load data initially
            loadData();
            
            // Connect to WebSocket for real-time updates
            connectPlotWebSocket();
        </script>
    </body>
    </html>
    """
    
    return HTMLResponse(content=html_content)

@app.get("/api/interpolated-data")
async def get_interpolated_data():
    """Get 60 FPS interpolated data for all joints (last 5 seconds = 300 points)"""
    return {
        "timestamp": datetime.now().isoformat(),
        "trainer": {
            joint_name: {
                "interpolated": store.interpolated_60fps[-300:] if len(store.interpolated_60fps) > 0 else [],
                "filtered": store.interpolated_filtered[-300:] if len(store.interpolated_filtered) > 0 else []
            }
            for joint_name, store in trainer_stores.items()
        },
        "user": {
            joint_name: {
                "interpolated": store.interpolated_60fps[-300:] if len(store.interpolated_60fps) > 0 else [],
                "filtered": store.interpolated_filtered[-300:] if len(store.interpolated_filtered) > 0 else []
            }
            for joint_name, store in user_stores.items()
        }
    }

@app.get("/ifil/{role}/{joint_name}")
async def get_interpolated_filtered_angle(role: str, joint_name: str):
    """Get filtered interpolated data array for a specific joint and role"""
    if role.lower() not in ['trainer', 'user']:
        return {"error": "Role must be 'trainer' or 'user'"}
    
    stores = trainer_stores if role.lower() == "trainer" else user_stores
    
    if joint_name not in stores:
        return {
            "error": f"Joint '{joint_name}' not found for role '{role}'",
            "available_joints": list(stores.keys())
        }
    
    store = stores[joint_name]
    return store.interpolated_filtered if len(store.interpolated_filtered) > 0 else []


# ============================================================================
# REP VISUALIZATION ENDPOINTS
# ============================================================================

@app.get("/api/rep-data")
async def get_rep_data():
    """JSON endpoint returning last inference results for rep visualization"""
    def _serialize_inference(inf_dict):
        if inf_dict is None:
            return None
        return {
            "original_arrays": [arr.tolist() if hasattr(arr, 'tolist') else list(arr) for arr in inf_dict["original_arrays"]],
            "labels_final": inf_dict["labels_final"].tolist() if hasattr(inf_dict["labels_final"], 'tolist') else list(inf_dict["labels_final"]),
            "conf_phase1": inf_dict["conf_phase1"].tolist() if hasattr(inf_dict["conf_phase1"], 'tolist') else list(inf_dict["conf_phase1"]),
            "conf_phase2": inf_dict["conf_phase2"].tolist() if hasattr(inf_dict["conf_phase2"], 'tolist') else list(inf_dict["conf_phase2"]),
        }

    return {
        "joint_names": last_rep_joint_names,
        "frame_count": last_rep_framecount,
        "offset": max(0, last_rep_framecount - 480) if last_rep_framecount > 0 else 0,
        "trainer": {
            "inference": _serialize_inference(last_trainer_inference),
            "found_reps": [[r[0], r[1]] for r in trainer_found_reps],
            "rep_count": len(trainer_found_reps),
        },
        "user": {
            "inference": _serialize_inference(last_user_inference),
            "found_reps": [[r[0], r[1]] for r in user_found_reps],
            "rep_count": len(user_found_reps),
        },
    }


@app.get("/reps", response_class=HTMLResponse)
async def get_reps_page():
    """HTML page with uPlot charts showing identified reps with colored regions"""
    html_content = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Rep Segmentation - Live View</title>
        <script src="https://unpkg.com/uplot@1.6.24/dist/uPlot.iife.min.js"></script>
        <link rel="stylesheet" href="https://unpkg.com/uplot@1.6.24/dist/uPlot.min.css">
        <style>
            * { box-sizing: border-box; margin: 0; padding: 0; }
            body {
                font-family: 'Segoe UI', Arial, sans-serif;
                background: #0f172a;
                color: #e2e8f0;
                padding: 20px;
            }
            .container { max-width: 1800px; margin: 0 auto; }
            h1 {
                text-align: center;
                font-size: 24px;
                margin-bottom: 16px;
                color: #f8fafc;
            }

            /* Rep counter banner */
            .rep-banner {
                display: flex;
                justify-content: center;
                gap: 40px;
                margin-bottom: 20px;
            }
            .rep-count-box {
                background: #1e293b;
                border: 1px solid #334155;
                border-radius: 12px;
                padding: 16px 32px;
                text-align: center;
                min-width: 180px;
            }
            .rep-count-box .label {
                font-size: 13px;
                text-transform: uppercase;
                letter-spacing: 1px;
                color: #94a3b8;
                margin-bottom: 6px;
            }
            .rep-count-box .count {
                font-size: 42px;
                font-weight: 700;
            }
            .rep-count-box.trainer .count { color: #4ade80; }
            .rep-count-box.user .count { color: #60a5fa; }

            /* Info box */
            .info-box {
                background: #1e293b;
                border-left: 4px solid #6366f1;
                padding: 14px 18px;
                margin-bottom: 20px;
                border-radius: 4px;
                font-size: 13px;
                line-height: 1.7;
                color: #cbd5e1;
            }
            .info-box code { color: #a5b4fc; }

            /* Legend */
            .legend-bar {
                display: flex;
                justify-content: center;
                gap: 28px;
                margin-bottom: 18px;
                font-size: 13px;
            }
            .legend-item {
                display: flex;
                align-items: center;
                gap: 6px;
            }
            .legend-swatch {
                width: 18px;
                height: 14px;
                border-radius: 3px;
                display: inline-block;
            }

            .refresh-button {
                display: block;
                margin: 0 auto 20px;
                padding: 10px 30px;
                background: #6366f1;
                color: white;
                border: none;
                border-radius: 6px;
                font-size: 15px;
                cursor: pointer;
                transition: background .15s;
            }
            .refresh-button:hover { background: #4f46e5; }

            /* No-data message */
            .no-data {
                text-align: center;
                padding: 60px 20px;
                color: #64748b;
                font-size: 16px;
            }

            /* Charts */
            .joint-section {
                margin-bottom: 24px;
            }
            .joint-title {
                font-size: 15px;
                font-weight: 600;
                color: #e2e8f0;
                margin-bottom: 8px;
                padding-left: 4px;
            }
            .chart-row {
                display: grid;
                grid-template-columns: 1fr 1fr;
                gap: 12px;
            }
            .chart-card {
                background: #1e293b;
                border-radius: 8px;
                padding: 12px;
                border: 1px solid #334155;
            }
            .chart-card h4 {
                font-size: 12px;
                color: #94a3b8;
                margin-bottom: 6px;
                text-transform: uppercase;
                letter-spacing: .5px;
            }
            .u-legend { font-size: 11px !important; color: #94a3b8 !important; }
            .u-legend .u-series th { color: #94a3b8 !important; }

            @media (max-width: 900px) {
                .chart-row { grid-template-columns: 1fr; }
            }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>Rep Segmentation &mdash; Live View</h1>

            <div class="rep-banner">
                <div class="rep-count-box trainer">
                    <div class="label">Trainer Reps</div>
                    <div class="count" id="trainer-rep-count">0</div>
                </div>
                <div class="rep-count-box user">
                    <div class="label">User Reps</div>
                    <div class="count" id="user-rep-count">0</div>
                </div>
            </div>

            <div class="legend-bar">
                <div class="legend-item"><span class="legend-swatch" style="background:rgba(74,222,128,.35)"></span> Phase 1 (concentric)</div>
                <div class="legend-item"><span class="legend-swatch" style="background:rgba(251,146,60,.35)"></span> Phase 2 (eccentric)</div>
                <div class="legend-item"><span class="legend-swatch" style="background:transparent;border:1.5px dashed #a78bfa"></span> Rep boundaries</div>
            </div>

            <div class="info-box">
                <strong>Model:</strong> UNet-BiLSTM &middot; 6 top-std-dev joints &middot; 480-frame window @ 60 FPS<br>
                <strong>Labels:</strong> <code>0</code> rest &middot; <code>1</code> phase 1 &middot; <code>2</code> phase 2<br>
                <strong>Updates:</strong> Real-time via WebSocket (auto-refreshes when new data arrives)
            </div>

            <button class="refresh-button" onclick="loadData()">Manual Refresh</button>

            <div id="charts-container">
                <div class="no-data" id="no-data-msg">Waiting for rep segmentation data&hellip;</div>
            </div>
        </div>

        <script>
        (function() {
            const PHASE1_COLOR = 'rgba(74, 222, 128, 0.18)';
            const PHASE2_COLOR = 'rgba(251, 146, 60, 0.18)';
            const REP_BORDER   = '#a78bfa';

            let currentJoints = [];
            let charts = {};  // key: "joint|role" => uPlot instance

            function destroyAllCharts() {
                Object.values(charts).forEach(u => u.destroy());
                charts = {};
            }

            function makeDrawHook(labelsRef, repsRef) {
                // labelsRef and repsRef are objects with a .v property we update
                return function(u) {
                    const ctx = u.ctx;
                    const labels = labelsRef.v;
                    const reps = repsRef.v;
                    if (!labels || labels.length === 0) return;

                    const xScale = u.scales.x;
                    const yScale = u.scales.y;
                    const left   = u.bbox.left;
                    const top    = u.bbox.top;
                    const width  = u.bbox.width;
                    const height = u.bbox.height;

                    // Draw phase bands from labels array
                    let i = 0;
                    while (i < labels.length) {
                        const lbl = labels[i];
                        if (lbl === 1 || lbl === 2) {
                            const start = i;
                            while (i < labels.length && labels[i] === lbl) i++;
                            const end = i - 1;

                            const x0 = u.valToPos(start, 'x', true);
                            const x1 = u.valToPos(end, 'x', true);

                            ctx.save();
                            ctx.fillStyle = lbl === 1 ? PHASE1_COLOR : PHASE2_COLOR;
                            ctx.fillRect(x0, top, x1 - x0, height);
                            ctx.restore();
                        } else {
                            i++;
                        }
                    }

                    // Draw rep boundary lines
                    if (reps && reps.length > 0) {
                        ctx.save();
                        ctx.strokeStyle = REP_BORDER;
                        ctx.lineWidth = 1.5;
                        ctx.setLineDash([4, 4]);

                        for (const rep of reps) {
                            // rep indices are absolute; labels are 0-479 window
                            // The API already provides found_reps in absolute indices
                            // but label indices match the window, so we don't need offset here
                            // We draw from the 'found_reps' mapped to the 480 window
                            const sx = u.valToPos(rep[0], 'x', true);
                            const ex = u.valToPos(rep[1], 'x', true);

                            ctx.beginPath();
                            ctx.moveTo(sx, top);
                            ctx.lineTo(sx, top + height);
                            ctx.stroke();

                            ctx.beginPath();
                            ctx.moveTo(ex, top);
                            ctx.lineTo(ex, top + height);
                            ctx.stroke();
                        }
                        ctx.restore();
                    }
                };
            }

            function createChart(container, role, jointIdx, labelsRef, repsRef) {
                const color = role === 'trainer' ? '#4ade80' : '#60a5fa';
                const opts = {
                    width: container.clientWidth - 24,
                    height: 200,
                    scales: {
                        x: { time: false },
                        y: { range: [0, 180] }
                    },
                    series: [
                        { label: 'Frame', value: (u, v) => v != null ? v : '-' },
                        {
                            label: 'Angle',
                            stroke: color,
                            width: 1.8,
                            points: { show: false }
                        }
                    ],
                    axes: [
                        { stroke: '#475569', grid: { stroke: '#1e293b', width: 1 }, ticks: { stroke: '#334155' }, font: '11px sans-serif', labelFont: '11px sans-serif' },
                        { stroke: '#475569', grid: { stroke: '#1e293b', width: 1 }, ticks: { stroke: '#334155' }, label: 'Angle (deg)', font: '11px sans-serif', labelFont: '12px sans-serif', labelGap: 8 }
                    ],
                    hooks: {
                        draw: [makeDrawHook(labelsRef, repsRef)]
                    },
                    legend: { show: false },
                    cursor: { show: true, drag: { x: false, y: false } }
                };

                const data = [[0], [null]];
                return new uPlot(opts, data, container);
            }

            function buildCharts(jointNames) {
                destroyAllCharts();
                const container = document.getElementById('charts-container');
                container.innerHTML = '';
                if (!jointNames || jointNames.length === 0) {
                    container.innerHTML = '<div class="no-data">No active joints detected yet.</div>';
                    return;
                }

                jointNames.forEach((jname, jIdx) => {
                    const section = document.createElement('div');
                    section.className = 'joint-section';
                    section.innerHTML = '<div class="joint-title">' + jname + ' (#' + (jIdx + 1) + ')</div>';

                    const row = document.createElement('div');
                    row.className = 'chart-row';

                    ['trainer', 'user'].forEach(role => {
                        const card = document.createElement('div');
                        card.className = 'chart-card';
                        card.innerHTML = '<h4>' + role + '</h4>';
                        const wrap = document.createElement('div');
                        wrap.id = 'chart-' + role + '-' + jIdx;
                        card.appendChild(wrap);
                        row.appendChild(card);
                    });

                    section.appendChild(row);
                    container.appendChild(section);
                });

                // Create uPlot instances after DOM is ready
                requestAnimationFrame(() => {
                    jointNames.forEach((jname, jIdx) => {
                        ['trainer', 'user'].forEach(role => {
                            const wrap = document.getElementById('chart-' + role + '-' + jIdx);
                            if (!wrap) return;
                            const labelsRef = { v: [] };
                            const repsRef = { v: [] };
                            const key = jname + '|' + role;
                            const u = createChart(wrap, role, jIdx, labelsRef, repsRef);
                            charts[key] = u;
                            u._labelsRef = labelsRef;
                            u._repsRef = repsRef;
                        });
                    });
                });
            }

            function arraysEqual(a, b) {
                if (a.length !== b.length) return false;
                for (let i = 0; i < a.length; i++) { if (a[i] !== b[i]) return false; }
                return true;
            }

            async function loadData() {
                try {
                    const resp = await fetch('/api/rep-data');
                    const d = await resp.json();

                    const jointNames = d.joint_names || [];
                    const offset = d.offset || 0;

                    // Update rep counters
                    document.getElementById('trainer-rep-count').textContent = d.trainer.rep_count;
                    document.getElementById('user-rep-count').textContent = d.user.rep_count;

                    // Rebuild charts if joints changed
                    if (!arraysEqual(currentJoints, jointNames)) {
                        currentJoints = jointNames;
                        buildCharts(jointNames);
                        // Allow DOM to settle before updating data
                        await new Promise(r => setTimeout(r, 80));
                    }

                    if (jointNames.length === 0) return;

                    // Update each chart
                    ['trainer', 'user'].forEach(role => {
                        const inf = d[role].inference;
                        if (!inf) return;
                        const labels = inf.labels_final;
                        const foundReps = d[role].found_reps;

                        // Map found_reps from absolute indices to window-relative indices
                        const windowReps = foundReps.map(r => [r[0] - offset, r[1] - offset])
                                                     .filter(r => r[1] >= 0 && r[0] < 480);

                        jointNames.forEach((jname, jIdx) => {
                            const key = jname + '|' + role;
                            const u = charts[key];
                            if (!u) return;

                            const arr = inf.original_arrays[jIdx] || [];
                            const frames = arr.map((_, i) => i);

                            u._labelsRef.v = labels;
                            u._repsRef.v = windowReps;

                            u.setData([frames, arr]);
                        });
                    });
                } catch (err) {
                    console.error('Error loading rep data:', err);
                }
            }

            // WebSocket real-time updates
            function connectWS() {
                const ws = new WebSocket('ws://' + location.host + '/ws/plot-updates');
                ws.onopen = () => console.log('[REP WS] Connected');
                ws.onmessage = (e) => {
                    const msg = JSON.parse(e.data);
                    if (msg.type === 'data_updated') loadData();
                };
                ws.onclose = () => { console.log('[REP WS] Disconnected, reconnecting...'); setTimeout(connectWS, 2000); };
                ws.onerror = () => {};
            }

            // Initial load + WS
            loadData();
            connectWS();

            // Resize handler
            window.addEventListener('resize', () => {
                Object.entries(charts).forEach(([key, u]) => {
                    const wrap = u.root.parentNode;
                    if (wrap) u.setSize({ width: wrap.clientWidth - 24, height: 200 });
                });
            });
        })();
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)


@app.websocket("/ws/plot-updates")
async def plot_updates_websocket(websocket: WebSocket):
    """WebSocket endpoint for real-time plot updates"""
    await websocket.accept()
    plot_websocket_connections.append(websocket)
    print("[PLOT WS] Plot viewer connected")
    
    try:
        while True:
            # Keep connection alive and wait for disconnect
            await websocket.receive_text()
    except WebSocketDisconnect:
        plot_websocket_connections.remove(websocket)
        print("[PLOT WS] Plot viewer disconnected")
    except Exception as e:
        if websocket in plot_websocket_connections:
            plot_websocket_connections.remove(websocket)
        print(f"[PLOT WS ERROR] {e}")

# ============================================================================
# MAIN ENTRY POINT
# ============================================================================

if __name__ == "__main__":
    print("\n" + "="*80)
    print("POSTURE DATA PROCESSOR - STANDALONE APPLICATION")
    print("="*80)
    print(f"Initialized {len(trainer_stores)} trainer joint stores")
    print(f"Initialized {len(user_stores)} user joint stores")
    print("="*80 + "\n")
    
    # Run the FastAPI app on port 8000
    uvicorn.run(
        app,
        host="127.0.0.1",
        port=8000,
        log_level="info"
    )
