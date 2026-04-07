import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
import os

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))


# ── Model definition ──────────────────────────────────────────────────────────

class ConvBlock(nn.Module):
    def __init__(self, in_ch, out_ch, kernel=3, stride=1):
        super().__init__()
        self.block = nn.Sequential(
            nn.Conv1d(in_ch, out_ch, kernel, stride=stride,
                      padding=kernel // 2, bias=False),
            nn.BatchNorm1d(out_ch),
            nn.ReLU(inplace=True)
        )
    def forward(self, x): return self.block(x)


class UNetBiLSTM(nn.Module):
    def __init__(self, n_joints=6, n_classes=3):
        super().__init__()
        self.enc1 = nn.Sequential(ConvBlock(n_joints, 32, 5, 2), ConvBlock(32, 32))
        self.enc2 = nn.Sequential(ConvBlock(32, 64, 3, 2),       ConvBlock(64, 64))
        self.enc3 = nn.Sequential(ConvBlock(64, 128, 3, 2),      ConvBlock(128, 128))
        self.lstm      = nn.LSTM(128, 128, batch_first=True, bidirectional=True)
        self.lstm_norm = nn.LayerNorm(256)
        self.lstm_drop = nn.Dropout(0.2)
        self.e3_proj = nn.Conv1d(128, 256, 1)
        self.dec3    = nn.Sequential(ConvBlock(512, 128, 3), ConvBlock(128, 64, 3))
        self.up3     = nn.Upsample(scale_factor=2, mode='linear', align_corners=False)
        self.e2_proj = nn.Conv1d(64, 64, 1)
        self.dec2    = nn.Sequential(ConvBlock(128, 64, 3))
        self.up2     = nn.Upsample(scale_factor=2, mode='linear', align_corners=False)
        self.e1_proj = nn.Conv1d(32, 64, 1)
        self.dec1    = nn.Sequential(ConvBlock(128, 64, 3))
        self.up1     = nn.Upsample(scale_factor=2, mode='linear', align_corners=False)
        self.output  = nn.Conv1d(64, n_classes, 1)

    def forward(self, x):
        e1 = self.enc1(x)
        e2 = self.enc2(e1)
        e3 = self.enc3(e2)
        b, _ = self.lstm(e3.permute(0, 2, 1))
        b = self.lstm_norm(b)
        b = self.lstm_drop(b).permute(0, 2, 1)
        d3 = torch.cat([b, self.e3_proj(e3)], dim=1)
        d3 = self.up3(self.dec3(d3))
        d2 = torch.cat([d3, self.e2_proj(e2)], dim=1)
        d2 = self.up2(self.dec2(d2))
        d1 = torch.cat([d2, self.e1_proj(e1)], dim=1)
        d1 = self.up1(self.dec1(d1))
        return self.output(d1).permute(0, 2, 1)   # (1, 480, 3)


# ── Z-score normalisation ─────────────────────────────────────────────────────

def zscore_normalise(raw: np.ndarray) -> np.ndarray:
    mu  = raw.mean(axis=0, keepdims=True)
    std = raw.std(axis=0,  keepdims=True) + 1e-6
    return (raw - mu) / std


# ── Post-processing (state machine) ──────────────────────────────────────────

def apply_threshold(labels: np.ndarray, conf_phase1: np.ndarray,
                    conf_phase2: np.ndarray, threshold: float = 0.45) -> np.ndarray:
    """Step 1 only: zero out low-confidence 1s and 2s."""
    labels = labels.copy()
    labels[(labels == 1) & (conf_phase1 < threshold)] = 0
    labels[(labels == 2) & (conf_phase2 < threshold)] = 0
    return labels


def apply_state_machine(labels: np.ndarray) -> np.ndarray:
    """
    Step 2: enforce transition rules:
      0 -> next must be 0 or 1
      1 -> next must be 1 or 2
      2 -> next can be 0, 1, 2
    When broken, zero out whichever side is 1 or 2.
    Repeat until stable.
    """
    labels = labels.copy()
    valid_next = {0: {0, 1}, 1: {1, 2}, 2: {0, 1, 2}}
    changed = True
    while changed:
        changed = False
        for i in range(1, len(labels)):
            if labels[i] not in valid_next[labels[i - 1]]:
                if labels[i] in (1, 2):
                    labels[i] = 0
                else:
                    labels[i - 1] = 0
                changed = True
    return labels


# ── Rep detection ─────────────────────────────────────────────────────────────

def find_reps(labels: np.ndarray, original_arrays: list) -> tuple:
    """
    A rep is any 1111->2222 block.

    Returns
    -------
    labels_after_rep_filter : np.ndarray  — labels with invalid reps zeroed out
    reps : list of [start, end, [arr1..arr6]]
    """
    labels = labels.copy()
    reps = []
    i = 0
    n = len(labels)

    while i < n:
        if labels[i] == 1:
            start = i
            while i < n and labels[i] == 1:
                i += 1
            if i < n and labels[i] == 2:
                phase2_start = i
                while i < n and labels[i] == 2:
                    i += 1
                end = i - 1

                slices = [np.array(arr)[start:end + 1].tolist()
                          for arr in original_arrays]
                reps.append([start, end, slices])
            # if no 2-run follows, already zeroed by state machine
        else:
            i += 1

    return labels, reps


# ── Main inference function ───────────────────────────────────────────────────

def predict(
    arrays: list,
    model_path: str = "base_model.pt",
    device: str = None
) -> dict:
    """
    Returns a dict with all intermediate arrays for plotting plus final reps.

    Keys
    ----
    original_arrays   : list of 6 np.ndarray (raw input, padded to 480)
    conf_rest         : (480,) confidence for class 0
    conf_phase1       : (480,) confidence for class 1
    conf_phase2       : (480,) confidence for class 2
    labels_raw        : (480,) argmax labels before any post-processing
    labels_threshold  : (480,) after 0.45 confidence threshold
    labels_statemachine:(480,) after state machine rule enforcement
    labels_final      : (480,) after state machine (same as reps source)
    reps              : list of [start, end, [arr1..arr6]]
    """

    WINDOW = 480

    # ── 1. Validate / auto-fill to 6 arrays ──────────────────────────────
    if len(arrays) == 1:
        arrays = arrays + [np.zeros_like(arrays[0]) for _ in range(5)]
    elif len(arrays) != 6:
        raise ValueError(f"Expected 1 or 6 arrays, got {len(arrays)}")

    original_arrays = [np.array(a, dtype="float32").flatten() for a in arrays]

    # ── 2. Pad / truncate to 480 ──────────────────────────────────────────
    processed = []
    for arr in arrays:
        arr = np.array(arr, dtype="float32").flatten()
        n   = len(arr)
        if n < WINDOW:
            padded = np.zeros(WINDOW, dtype="float32")
            padded[WINDOW - n:] = arr
            arr = padded
        elif n > WINDOW:
            arr = arr[-WINDOW:]
        processed.append(arr)

    # ── 3. Stack -> (480, 6), normalise ──────────────────────────────────
    features = np.stack(processed, axis=1)
    features = zscore_normalise(features)

    # ── 4. Load model ─────────────────────────────────────────────────────
    if device is None:
        device = "cuda" if torch.cuda.is_available() else "cpu"
    dev = torch.device(device)

    model = UNetBiLSTM(n_joints=6, n_classes=3).to(dev)
    model.load_state_dict(torch.load(model_path, map_location=dev))
    model.eval()

    # ── 5. Build tensor (1, 6, 480) ──────────────────────────────────────
    x = torch.tensor(features, dtype=torch.float32)
    x = x.permute(1, 0).unsqueeze(0).to(dev)

    # ── 6. Inference ──────────────────────────────────────────────────────
    with torch.no_grad():
        logits = model(x)
        probs  = F.softmax(logits, dim=-1)
        labels_raw = probs.argmax(dim=-1)

    probs      = probs.squeeze(0).cpu().numpy()
    labels_raw = labels_raw.squeeze(0).cpu().numpy().astype(np.int32)

    conf_rest   = probs[:, 0]
    conf_phase1 = probs[:, 1]
    conf_phase2 = probs[:, 2]

    # ── 7. Post-processing stages ─────────────────────────────────────────
    labels_threshold   = apply_threshold(labels_raw, conf_phase1, conf_phase2, threshold=0.45)
    labels_statemachine = apply_state_machine(labels_threshold)
    labels_final, reps = find_reps(labels_statemachine, original_arrays)

    return {
        "original_arrays"    : processed,          # padded to 480 for aligned plotting
        "conf_rest"          : conf_rest,
        "conf_phase1"        : conf_phase1,
        "conf_phase2"        : conf_phase2,
        "labels_raw"         : labels_raw,
        "labels_threshold"   : labels_threshold,
        "labels_statemachine": labels_statemachine,
        "labels_final"       : labels_final,
        "reps"               : reps,
    }


# ── Pre-load model (for use in posture_processor) ────────────────────────────

def load_model(model_path: str = "base_model.pt", device: str = None):
    """
    Load the UNetBiLSTM model once and return (model, device_str).
    Call this at startup so the model is warm in memory.
    """
    if device is None:
        device = "cuda" if torch.cuda.is_available() else "cpu"
    dev = torch.device(device)
    model = UNetBiLSTM(n_joints=6, n_classes=3).to(dev)
    model.load_state_dict(torch.load(model_path, map_location=dev))
    model.eval()
    return model, device


def predict_with_model(
    arrays: list,
    model,
    device: str
) -> dict:
    """
    Same as predict() but uses a pre-loaded model instead of loading from disk.
    Input arrays should be interpolated_filtered data (not confidence).
    Rep slices in the output will be from the same interpolated_filtered data.

    Parameters
    ----------
    arrays : list of array-like — 1 or 6 joint angle arrays
    model  : pre-loaded UNetBiLSTM model
    device : device string ('cpu' or 'cuda')

    Returns
    -------
    dict with same keys as predict()
    """
    WINDOW = 480

    # ── 1. Validate / auto-fill to 6 arrays ──────────────────────────────
    if len(arrays) == 1:
        arrays = arrays + [np.zeros_like(arrays[0]) for _ in range(5)]
    elif len(arrays) != 6:
        raise ValueError(f"Expected 1 or 6 arrays, got {len(arrays)}")

    original_arrays = [np.array(a, dtype="float32").flatten() for a in arrays]

    # ── 2. Pad / truncate to 480 ──────────────────────────────────────────
    processed = []
    for arr in arrays:
        arr = np.array(arr, dtype="float32").flatten()
        n   = len(arr)
        if n < WINDOW:
            padded = np.zeros(WINDOW, dtype="float32")
            padded[WINDOW - n:] = arr
            arr = padded
        elif n > WINDOW:
            arr = arr[-WINDOW:]
        processed.append(arr)

    # ── 3. Stack -> (480, 6), normalise ──────────────────────────────────
    features = np.stack(processed, axis=1)
    features = zscore_normalise(features)

    # ── 4. Build tensor (1, 6, 480) ──────────────────────────────────────
    dev = torch.device(device)
    x = torch.tensor(features, dtype=torch.float32)
    x = x.permute(1, 0).unsqueeze(0).to(dev)

    # ── 5. Inference ──────────────────────────────────────────────────────
    with torch.no_grad():
        logits = model(x)
        probs  = F.softmax(logits, dim=-1)
        labels_raw = probs.argmax(dim=-1)

    probs      = probs.squeeze(0).cpu().numpy()
    labels_raw = labels_raw.squeeze(0).cpu().numpy().astype(np.int32)

    conf_rest   = probs[:, 0]
    conf_phase1 = probs[:, 1]
    conf_phase2 = probs[:, 2]

    # ── 6. Post-processing stages ─────────────────────────────────────────
    labels_threshold    = apply_threshold(labels_raw, conf_phase1, conf_phase2, threshold=0.45)
    labels_statemachine = apply_state_machine(labels_threshold)
    labels_final, reps  = find_reps(labels_statemachine, original_arrays)

    return {
        "original_arrays"    : processed,
        "conf_rest"          : conf_rest,
        "conf_phase1"        : conf_phase1,
        "conf_phase2"        : conf_phase2,
        "labels_raw"         : labels_raw,
        "labels_threshold"   : labels_threshold,
        "labels_statemachine": labels_statemachine,
        "labels_final"       : labels_final,
        "reps"               : reps,
    }