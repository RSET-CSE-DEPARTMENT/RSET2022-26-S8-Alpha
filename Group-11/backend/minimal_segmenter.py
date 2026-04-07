"""
Minimal Rep Segmentation Tool - Silent Inference
================================================
Clean function for rep segmentation without visualization or debug output.

Usage: python minimal_segmenter.py
"""

import os
import sys
import glob
import zipfile
import shutil
import random
import numpy as np
import pandas as pd

# Signal processing
from scipy.signal import savgol_filter
from scipy.ndimage import median_filter

# ONNX Runtime
import onnxruntime as ort


# ==========================================
# CONFIG
# ==========================================
ZIP_PATH = "../converted_trimmed.zip"
EXTRACT_PATH = "data/extracted"
MODEL_PATH = "dualhead_model.onnx"

# Filtering parameters (Savitzky-Golay)
SAVGOL_WINDOW_REP = 31
SAVGOL_POLYORDER_REP = 3
SAVGOL_WINDOW_PHASE = 21
SAVGOL_POLYORDER_PHASE = 2
MEDIAN_WINDOW = 5

# Segmentation parameters
SEG_WINDOW = 50
SEG_STRIDE = 10
MIN_PHASE_THRESH = 0.15
PHASE_RANGE_THRESH = 0.50


# ==========================================
# FILTERING FUNCTIONS
# ==========================================
def apply_filters(signal, window_length, polyorder, use_median=True, median_size=5):
    """Apply zero-phase smoothing filters to signal."""
    filtered = signal.copy()

    # Step 1: Optional median filter for spike removal
    if use_median and median_size > 0:
        filtered = median_filter(filtered, size=median_size)

    # Step 2: Savitzky-Golay for smooth curve fitting
    if window_length >= len(filtered):
        window_length = len(filtered) - 1
        if window_length % 2 == 0:
            window_length -= 1

    if window_length >= 3 and window_length > polyorder:
        filtered = savgol_filter(filtered, window_length, polyorder)

    return filtered


def filter_rep_prob(rep_prob):
    """Filter rep probability signal."""
    return apply_filters(
        rep_prob,
        window_length=SAVGOL_WINDOW_REP,
        polyorder=SAVGOL_POLYORDER_REP,
        use_median=(MEDIAN_WINDOW > 0),
        median_size=MEDIAN_WINDOW
    )


def filter_phase(phase):
    """Filter phase signal."""
    return apply_filters(
        phase,
        window_length=SAVGOL_WINDOW_PHASE,
        polyorder=SAVGOL_POLYORDER_PHASE,
        use_median=(MEDIAN_WINDOW > 0),
        median_size=MEDIAN_WINDOW
    )


# ==========================================
# FILE LOADING
# ==========================================
def get_val_files():
    """Extract and return validation files (80/20 split by participant)."""
    if os.path.exists(EXTRACT_PATH):
        shutil.rmtree(EXTRACT_PATH)
    os.makedirs(EXTRACT_PATH, exist_ok=True)

    with zipfile.ZipFile(ZIP_PATH, 'r') as z:
        z.extractall(EXTRACT_PATH)

    all_files = sorted(glob.glob(os.path.join(EXTRACT_PATH, "**/*.csv"), recursive=True))

    valid_files = []
    for f in all_files:
        try:
            df = pd.read_csv(f)
            if df.shape[1] < 8:
                continue
            phase = df.iloc[:, 7].values
            if np.isnan(phase).any():
                continue
            if not np.all((phase >= 0) & (phase <= 1)):
                continue
            valid_files.append(f)
        except:
            continue

    # Group by participant
    file_groups = {}
    for f in valid_files:
        fname = os.path.basename(f)
        parts = fname.split('_2class__')
        key = parts[0] if len(parts) >= 2 else fname.split('__')[0]
        file_groups.setdefault(key, []).append(f)

    # 80/20 split
    unique_ids = list(file_groups.keys())
    random.seed(42)
    random.shuffle(unique_ids)

    split_idx = int(0.8 * len(unique_ids))
    val_ids = unique_ids[split_idx:]
    val_files = [f for pid in val_ids for f in file_groups[pid]]

    return sorted(val_files)


# ==========================================
# SEGMENTATION (SILENT)
# ==========================================
def segment_reps_core(rep_prob, phase_filtered):
    """
    Silent version of segment_reps - no debug prints.

    Detect rep boundaries using phase resets + rep_prob validation.
    """
    ARRAY_LEN = len(phase_filtered)

    possible_starts = []
    segments = []
    skip_until_idx = 0

    # Sliding window
    for i in range(0, ARRAY_LEN - SEG_WINDOW + 1, SEG_STRIDE):
        # Skip if in already processed region
        if i < skip_until_idx:
            continue

        window_phase = phase_filtered[i : i + SEG_WINDOW]
        window_rep = rep_prob[i : i + SEG_WINDOW]

        max_p, min_p = window_phase.max(), window_phase.min()
        sum_diff = np.diff(window_phase).sum()

        # Possible rep start
        if min_p < MIN_PHASE_THRESH:
            possible_starts.append(i)

        # Rep end detection
        if sum_diff < 0 and min_p < MIN_PHASE_THRESH and (max_p - min_p) > PHASE_RANGE_THRESH:
            # Find index where rep_prob ≈ 0.5
            rep_end = i + np.argmin(np.abs(window_rep - 0.5))
            rep_end = min(rep_end, ARRAY_LEN - 1)

            # Find closest start before rep_end
            valid_starts = [s for s in possible_starts if s < rep_end]

            if not valid_starts:
                continue

            # Try each valid_start from latest to earliest
            valid_starts_sorted = sorted(valid_starts, reverse=True)
            segment_added = False

            for rep_start_candidate in valid_starts_sorted:
                # Validate start: find index where rep_prob ≈ 0.5 near start [0, +40]
                start_lo = max(0, rep_start_candidate)
                start_hi = min(ARRAY_LEN, rep_start_candidate + 40)
                search_range = rep_prob[start_lo:start_hi]
                search_range_phase = phase_filtered[start_lo:start_hi]

                # Filter indices to only include where phase < MIN_PHASE_THRESH
                valid_phase_mask = search_range_phase < MIN_PHASE_THRESH
                valid_indices = np.where(valid_phase_mask)[0]

                if len(valid_indices) == 0:
                    continue

                # Sort valid indices by distance from 0.5
                abs_diff = np.abs(search_range[valid_indices] - 0.5)
                sorted_valid_indices = valid_indices[np.argsort(abs_diff)]

                found_valid_start = False
                for idx_in_range in sorted_valid_indices:
                    closest_to_05_idx = start_lo + idx_in_range
                    closest_to_05_val = rep_prob[closest_to_05_idx]

                    # Ensure rep_start comes before rep_end
                    if closest_to_05_idx >= rep_end:
                        continue

                    # Check minimum gap of 20 frames
                    gap = abs(rep_end - closest_to_05_idx)
                    if gap < 20:
                        continue

                    # Found valid start
                    rep_start = closest_to_05_idx
                    found_valid_start = True
                    break

                if not found_valid_start:
                    continue

                # Check overlap with existing segments
                overlapping = False
                for seg_start, seg_end in segments:
                    if (rep_end > seg_start and rep_start < seg_end) or (rep_start == rep_end):
                        overlapping = True
                        break

                if not overlapping:
                    segments.append([rep_start, rep_end])

                    # Clean up possible_starts
                    possible_starts = [s for s in possible_starts if s > i]

                    # Skip ahead
                    skip_until_idx = rep_end

                    segment_added = True
                    break

    return segments


# ==========================================
# MAIN FUNCTION
# ==========================================
def repsegment(joint_angles):
    """
    Segment reps from 480 frames of joint angles.

    Args:
        joint_angles: numpy array (480, 6) - 6 joint angles over 480 frames

    Returns:
        segments: list of [start, end] pairs, e.g., [[10, 45], [60, 95]]
    """
    # Load ONNX model
    session = ort.InferenceSession(MODEL_PATH)
    input_name = session.get_inputs()[0].name

    # Run inference (single window, no sliding)
    window = joint_angles[np.newaxis, ...].astype(np.float32)  # (1, 480, 6)
    rep_logits, phase_pred = session.run(None, {input_name: window})

    # Softmax to get rep_prob
    rep_exp = np.exp(rep_logits - rep_logits.max(axis=-1, keepdims=True))
    rep_prob = (rep_exp[..., 1] / rep_exp.sum(axis=-1))[0]  # (480,)
    phase = phase_pred[0]  # (480,)

    # Apply filters
    rep_prob_filtered = filter_rep_prob(rep_prob)
    phase_filtered = filter_phase(phase)

    # Segment (silent)
    segments = segment_reps_core(rep_prob, phase_filtered)

    return segments


# ==========================================
# CLI
# ==========================================
def main():
    # Get validation files
    val_files = get_val_files()

    # User input
    file_num = int(input("Enter file number (0-{}): ".format(len(val_files) - 1)))
    start_idx = int(input("Enter start index: "))

    # Validate file number
    if not (0 <= file_num < len(val_files)):
        print("Invalid file number")
        return

    # Load CSV
    df = pd.read_csv(val_files[file_num])

    # Check bounds
    if start_idx + 480 > len(df):
        print(f"Error: Not enough frames (need 480 from index {start_idx}, file has {len(df)} frames)")
        return

    # Extract 480 frames
    joints = df.iloc[start_idx:start_idx+480, 1:7].values.astype(np.float32)

    # Segment
    segments = repsegment(joints)

    # Print ONLY the result
    print(segments)


if __name__ == "__main__":
    main()
