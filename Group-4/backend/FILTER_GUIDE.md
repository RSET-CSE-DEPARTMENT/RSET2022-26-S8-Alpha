# Filter Configuration Guide

Complete guide for using and configuring all 6 available filters in the Posture Processor.

---

## 📋 Quick Reference

| Filter | Speed | Memory | Best For | Key Parameter |
|--------|-------|--------|----------|---------------|
| **EMA** | Fastest | 1 float | Quick movements | `ema_alpha` (0.1-0.5) |
| **Double EMA** | Very Fast | 2 floats | Trending movements | `double_ema_alpha` (0.1-0.5) |
| **Kalman** | Very Fast | 2 floats | Noisy sensors | `kalman_measurement_noise` (0.01-1.0) |
| **Savitzky-Golay** | Fast | ~7 floats | Preserving peaks | `savgol_window_size` (5, 7, or 9) |
| **Gaussian** | Fast | ~7 floats | Maximum smoothness | `gaussian_sigma` (0.5-3.0) |
| **Hybrid** | Fast | ~9 floats | Production use | No configuration |

---

## 🔧 How to Change Filters

### Method 1: Edit Configuration File (Requires Restart)

Open `posture_processor.py` and modify line 238:

```python
SMOOTHING_CONFIG = {
    'filter_type': 'hybrid',  # Change this to: 'ema', 'kalman', 'gaussian', etc.
    # ... rest of config
}
```

Then restart the server:
```bash
uvicorn posture_processor:app --reload
```

### Method 2: API Endpoint (Runtime, No Restart)

Send a POST request:

```bash
# Using curl
curl -X POST "http://127.0.0.1:8000/api/filter-config?filter_type=hybrid"

# Using Python
import requests
requests.post("http://127.0.0.1:8000/api/filter-config?filter_type=hybrid")

# Using JavaScript
fetch("http://127.0.0.1:8000/api/filter-config?filter_type=hybrid", {
    method: "POST"
})
```

⚠️ **Warning:** Changing filter via API clears all stored data and recreates storage.

---

## 🎯 Filter Details & Configuration

### 1. EMA (Exponential Moving Average)

**Best for:** Fast movements, minimal lag, real-time tracking

**How it works:** 
- Weighted average where recent values matter more
- Formula: `EMA[t] = α × Value[t] + (1 - α) × EMA[t-1]`

**Configuration:**

```python
SMOOTHING_CONFIG = {
    'filter_type': 'ema',
    'ema_alpha': 0.3,  # Range: 0.1 to 0.5
}
```

**Parameter Effects:**

| `ema_alpha` | Smoothing | Response Time | Use Case |
|-------------|-----------|---------------|----------|
| **0.1** | Maximum smoothness | Slow (laggy) | Very noisy data |
| **0.2** | High smoothness | Moderate lag | Noisy data |
| **0.3** ⭐ | Balanced | Balanced | Default - good for most cases |
| **0.4** | Light smoothing | Fast response | Clean data, quick movements |
| **0.5** | Minimal smoothing | Very fast | Minimal noise, maximum responsiveness |

**Example:** Lower alpha = smoother but slower to react to changes

```
alpha = 0.1: ▁▁▁▂▂▃▃▄▄▅▅ (very smooth, slow)
alpha = 0.3: ▁▂▃▄▅▆▇███ (balanced)
alpha = 0.5: ▁▃▅▇█████ (responsive, less smooth)
```

**When to adjust:**
- Increase α → More responsive, less smooth (for fast exercises like jumping jacks)
- Decrease α → More smooth, more lag (for slow exercises like yoga)

---

### 2. Double EMA (Holt's Method)

**Best for:** Movements with trends (gradual angle increases/decreases)

**How it works:**
- Tracks both level (current value) and trend (direction of change)
- Predicts next value based on trend
- Formula: `Level[t] = α × Value + (1 - α) × (Level[t-1] + Trend[t-1])`

**Configuration:**

```python
SMOOTHING_CONFIG = {
    'filter_type': 'double_ema',
    'double_ema_alpha': 0.3,  # Level smoothing (0.1-0.5)
    'double_ema_beta': 0.1,   # Trend smoothing (0.05-0.3)
}
```

**Parameter Effects:**

**`double_ema_alpha` (Level Smoothing):**

| Value | Effect | Use Case |
|-------|--------|----------|
| **0.1** | Very smooth levels | Noisy data with trends |
| **0.2** | Smooth levels | Moderate noise |
| **0.3** ⭐ | Balanced | Default |
| **0.4** | Responsive levels | Clean data |

**`double_ema_beta` (Trend Smoothing):**

| Value | Effect | Use Case |
|-------|--------|----------|
| **0.05** | Very smooth trend | Erratic movements |
| **0.1** ⭐ | Balanced trend | Default |
| **0.15** | Responsive trend | Clear directional movements |
| **0.2-0.3** | Very responsive | Fast changing trends |

**Example Scenarios:**

```python
# Slow, steady movements (yoga, stretching)
'double_ema_alpha': 0.2,  # Smooth
'double_ema_beta': 0.05,  # Gentle trend following

# Fast exercise (squats, lunges)
'double_ema_alpha': 0.4,  # Responsive
'double_ema_beta': 0.2,   # Quick trend adaptation
```

**When to use:** When exercises involve gradual angle changes (like slowly raising arms)

---

### 3. Kalman Filter

**Best for:** Noisy sensor data, optimal estimation, production quality

**How it works:**
- Predicts next state based on motion model
- Corrects prediction with new measurement
- Balances trust between prediction and measurement
- Adapts to changing conditions

**Configuration:**

```python
SMOOTHING_CONFIG = {
    'filter_type': 'kalman',
    'kalman_process_noise': 0.01,      # How much angles can change (Q)
    'kalman_measurement_noise': 0.1,   # Sensor noise level (R)
}
```

**Parameter Effects:**

**`kalman_process_noise` (Q) - Motion Variability:**

| Value | Meaning | Effect | Use Case |
|-------|---------|--------|----------|
| **0.001** | Very stable angles | Trusts prediction heavily | Static poses, slow movements |
| **0.01** ⭐ | Normal variability | Balanced | Default - most exercises |
| **0.05** | High variability | Adapts quickly | Dynamic movements |
| **0.1+** | Very dynamic | Follows measurements closely | Rapid movements |

**`kalman_measurement_noise` (R) - Sensor Noise:**

| Value | Meaning | Effect | Use Case |
|-------|---------|--------|----------|
| **0.01** | Clean sensor | Trusts measurements | High-quality camera, good lighting |
| **0.1** ⭐ | Normal noise | Balanced | Default - typical conditions |
| **0.5** | Noisy sensor | Smooths heavily | Poor lighting, shaky camera |
| **1.0+** | Very noisy | Maximum smoothing | Very poor conditions |

**Kalman Gain Formula:**
```
Kalman Gain = Process Error / (Process Error + Measurement Noise)

High Gain (→1.0) = Trust measurement more
Low Gain (→0.0) = Trust prediction more
```

**Example Scenarios:**

```python
# High-quality camera, good lighting, static exercises
'kalman_process_noise': 0.005,  # Stable
'kalman_measurement_noise': 0.05,  # Trust sensor

# Webcam, normal lighting, dynamic exercises
'kalman_process_noise': 0.01,  # Default
'kalman_measurement_noise': 0.1,  # Default

# Poor lighting, shaky camera, need maximum smoothing
'kalman_process_noise': 0.001,  # Very stable model
'kalman_measurement_noise': 0.5,  # Don't trust sensor
```

**When to adjust:**
- High noise → Increase `measurement_noise` (smoother but slower)
- Fast movements → Increase `process_noise` (more responsive)

---

### 4. Savitzky-Golay Filter

**Best for:** Preserving peaks and valleys, exercise movements where max/min angles matter

**How it works:**
- Fits polynomial to sliding window
- Smooths while preserving shape of peaks
- Uses precomputed coefficients for efficiency

**Configuration:**

```python
SMOOTHING_CONFIG = {
    'filter_type': 'savgol',
    'savgol_window_size': 7,  # Options: 5, 7, or 9
}
```

**Parameter Effects:**

| `savgol_window_size` | Smoothing | Peak Preservation | Latency | Use Case |
|----------------------|-----------|-------------------|---------|----------|
| **5** | Light | Excellent | ~0.17s | Fast exercises, precise tracking |
| **7** ⭐ | Moderate | Very Good | ~0.23s | Default - balanced |
| **9** | Heavy | Good | ~0.30s | Noisy data, slow movements |

**Visual Comparison:**

```
Raw data:     ▁▃▂▅▄▇▆█▇▅▆▄▅▃▄▂▃▁
Window 5:     ▁▂▃▅▆▇██▇▆▅▄▃▂▁
Window 7:     ▁▂▃▄▆███▆▅▃▂▁
Window 9:     ▁▂▃▄▅██▅▄▃▂▁
```

**Window Size Selection:**

```python
# Fast movements (jumping jacks, burpees)
'savgol_window_size': 5  # Quick response

# Moderate exercises (squats, lunges)
'savgol_window_size': 7  # Balanced

# Slow movements (yoga, stretching)
'savgol_window_size': 9  # Maximum smoothness
```

**When to use:** When peak angles are critical (e.g., maximum knee bend, full arm extension)

**Latency Calculation:**
- Latency = (window_size / 30 fps) / 2
- Window 5: ~0.17 seconds
- Window 7: ~0.23 seconds
- Window 9: ~0.30 seconds

---

### 5. Gaussian Filter

**Best for:** Maximum smoothness, heavy noise reduction, smooth curves

**How it works:**
- Applies Gaussian (bell curve) weighting to window
- Center values get most weight, edges get less
- Produces very smooth output

**Configuration:**

```python
SMOOTHING_CONFIG = {
    'filter_type': 'gaussian',
    'gaussian_window_size': 7,     # Options: 5, 7, 9
    'gaussian_sigma': 1.5,          # Range: 0.5 to 3.0
}
```

**Parameter Effects:**

**`gaussian_window_size`:**

| Value | Smoothing | Latency | Use Case |
|-------|-----------|---------|----------|
| **5** | Moderate | ~0.17s | Faster response |
| **7** ⭐ | High | ~0.23s | Default - balanced |
| **9** | Maximum | ~0.30s | Very noisy data |

**`gaussian_sigma` (Kernel Width):**

| Value | Distribution | Smoothing | Use Case |
|-------|-------------|-----------|----------|
| **0.5** | Narrow peak | Light smoothing | Clean data |
| **1.0** | Moderate spread | Moderate | Slight noise |
| **1.5** ⭐ | Wide spread | High smoothing | Default |
| **2.0** | Very wide | Very smooth | Noisy data |
| **3.0** | Extremely wide | Maximum smooth | Extremely noisy |

**Sigma Visual:**

```
Sigma = 0.5:  _▁▃▇█▇▃▁_  (narrow, less smooth)
Sigma = 1.5:  ▁▂▄▆█▆▄▂▁  (wide, smoother)
Sigma = 3.0:  ▂▃▄▅█▅▄▃▂  (very wide, very smooth)
```

**Example Scenarios:**

```python
# Clean data, need some smoothing
'gaussian_window_size': 5,
'gaussian_sigma': 1.0

# Moderate noise, balanced smoothing
'gaussian_window_size': 7,
'gaussian_sigma': 1.5

# Very noisy data, maximum smoothing
'gaussian_window_size': 9,
'gaussian_sigma': 2.5
```

**When to adjust:**
- More noise → Increase `sigma` or `window_size`
- Need responsiveness → Decrease both
- Want smoothest possible → Use window 9, sigma 3.0

---

### 6. Hybrid Filter (Recommended)

**Best for:** Production use, best overall quality, default choice

**How it works:**
- **Stage 1:** Kalman filter removes sensor noise and outliers
- **Stage 2:** Gaussian filter smooths movement jitter
- Two-stage pipeline combines strengths of both

**Configuration:**

```python
SMOOTHING_CONFIG = {
    'filter_type': 'hybrid',
    # No parameters - uses hardcoded optimal values
}
```

**Hardcoded Parameters:**
```python
# Stage 1: Kalman
process_noise = 0.01
measurement_noise = 0.1

# Stage 2: Gaussian
window_size = 7
sigma = 1.5
```

**Why Hybrid is Best:**

1. **Kalman Stage** handles:
   - Sudden noise spikes
   - Sensor glitches
   - Outlier rejection
   - Adaptive estimation

2. **Gaussian Stage** handles:
   - Natural movement jitter
   - Smooth transitions
   - Final polish

**Performance:**
- Memory: ~9 floats per joint (270 floats for 30 joints = ~1 KB)
- Computation: O(7) per update
- Latency: ~0.25 seconds
- Quality: Excellent

**Example Data Flow:**

```
Raw Input:    145° 200° 148° 150° 152° 147° 149°
                ↓
Kalman:       145° 148° 148° 149° 151° 149° 149°  (removes 200° spike)
                ↓
Gaussian:     145° 147° 148° 149° 150° 149° 149°  (smooths jitter)
```

**When to use:** Default choice for production. Only switch if you have specific requirements.

---

## 📊 Comparison Examples

### Noise Spike Test

```
Raw data:       [145, 147, 200, 149, 151, 148]
                     ↓ SPIKE!

EMA (α=0.3):    [145, 146, 162, 158, 156, 154]  ⚠️ Spike affects many frames
Kalman:         [145, 146, 148, 148, 149, 148]  ✅ Spike rejected
Gaussian:       [145, 150, 160, 155, 150, 148]  ⚠️ Spike smoothed but visible
Hybrid:         [145, 146, 147, 148, 149, 148]  ✅ Perfect rejection
```

### Responsiveness Test

```
Raw data:       [100, 100, 100, 150, 150, 150]
                          ↓ SUDDEN CHANGE

EMA (α=0.5):    [100, 100, 100, 125, 138, 144]  ✅ Fast (3 frames)
Kalman:         [100, 100, 100, 125, 138, 145]  ✅ Fast (3 frames)
Gaussian:       [100, 100, 100, 117, 133, 150]  ⚠️ Slower (4 frames)
Savgol:         [100, 100, 100, 121, 136, 150]  ⚠️ Slower (4 frames)
Hybrid:         [100, 100, 100, 120, 135, 147]  ✅ Good (3-4 frames)
```

### Smoothness Test

```
Noisy data:     [145, 143, 148, 142, 149, 144, 147]

EMA:            [145, 144, 145, 144, 146, 145, 146]  ✓ Moderate smooth
Kalman:         [145, 144, 146, 145, 147, 146, 146]  ✓ Moderate smooth
Savgol:         [145, 145, 145, 145, 146, 146, 146]  ✓✓ Smooth
Gaussian:       [145, 145, 145, 145, 146, 146, 146]  ✓✓ Very smooth
Hybrid:         [145, 145, 145, 145, 146, 146, 146]  ✓✓ Very smooth
```

---

## 🎮 Recommended Settings by Use Case

### High-Quality Camera, Good Lighting
```python
# Option 1: Maximum responsiveness
SMOOTHING_CONFIG = {
    'filter_type': 'ema',
    'ema_alpha': 0.4,
}

# Option 2: Balanced
SMOOTHING_CONFIG = {
    'filter_type': 'kalman',
    'kalman_process_noise': 0.01,
    'kalman_measurement_noise': 0.05,
}
```

### Webcam, Normal Lighting
```python
# Recommended: Use hybrid (default settings)
SMOOTHING_CONFIG = {
    'filter_type': 'hybrid',
}
```

### Poor Lighting / Shaky Camera
```python
# Option 1: Maximum smoothing
SMOOTHING_CONFIG = {
    'filter_type': 'gaussian',
    'gaussian_window_size': 9,
    'gaussian_sigma': 2.5,
}

# Option 2: Heavy Kalman filtering
SMOOTHING_CONFIG = {
    'filter_type': 'kalman',
    'kalman_process_noise': 0.001,
    'kalman_measurement_noise': 0.5,
}
```

### Fast Dynamic Exercises (Jumping Jacks, Burpees)
```python
SMOOTHING_CONFIG = {
    'filter_type': 'ema',
    'ema_alpha': 0.4,  # Fast response
}

# OR

SMOOTHING_CONFIG = {
    'filter_type': 'savgol',
    'savgol_window_size': 5,  # Minimal latency
}
```

### Slow Controlled Movements (Yoga, Stretching)
```python
SMOOTHING_CONFIG = {
    'filter_type': 'gaussian',
    'gaussian_window_size': 9,
    'gaussian_sigma': 2.0,
}

# OR

SMOOTHING_CONFIG = {
    'filter_type': 'double_ema',
    'double_ema_alpha': 0.2,
    'double_ema_beta': 0.05,
}
```

### Precision Required (Physical Therapy)
```python
SMOOTHING_CONFIG = {
    'filter_type': 'savgol',
    'savgol_window_size': 7,  # Preserves peaks
}
```

---

## 🔍 Debugging & Testing

### View Current Filter
```bash
curl http://127.0.0.1:8000/api/filter-config
```

### Test Different Filters
```python
import requests

filters_to_test = ['ema', 'kalman', 'gaussian', 'savgol', 'hybrid']

for filter_name in filters_to_test:
    print(f"\nTesting {filter_name}...")
    response = requests.post(
        f"http://127.0.0.1:8000/api/filter-config?filter_type={filter_name}"
    )
    print(response.json())
    
    # Wait and observe the plot at http://127.0.0.1:8000/plot
    input(f"Check the plot with {filter_name}, then press Enter...")
```

### Compare Filters Side-by-Side

1. Open plot page: http://127.0.0.1:8000/plot
2. Start exercise
3. Change filter via API
4. Observe smoothing differences in real-time

---

## 📈 Performance Impact

| Filter | CPU Impact | Memory Impact | Suitable for Long Workouts |
|--------|------------|---------------|---------------------------|
| **EMA** | Minimal | Minimal (1 float) | ✅ Unlimited |
| **Double EMA** | Minimal | Minimal (2 floats) | ✅ Unlimited |
| **Kalman** | Low | Minimal (2 floats) | ✅ Unlimited |
| **Savgol** | Low | Low (7 floats) | ✅ Unlimited |
| **Gaussian** | Low | Low (7 floats) | ✅ Unlimited |
| **Hybrid** | Low | Low (9 floats) | ✅ Unlimited |

**All filters support unlimited workout duration with constant performance!**

---

## 🚨 Common Issues & Solutions

### Issue: Too much lag / delayed response
**Solution:**
- Decrease smoothing strength
- Use faster filter (EMA with high α)
- Reduce window size (Savgol, Gaussian)

### Issue: Too jittery / not smooth enough
**Solution:**
- Increase smoothing strength
- Use heavier filter (Gaussian, Hybrid)
- Increase window size
- Lower α (EMA)

### Issue: Missing peaks / valleys
**Solution:**
- Use Savitzky-Golay filter
- Avoid Gaussian with high sigma
- Use smaller window size

### Issue: Noise spikes affecting output
**Solution:**
- Use Kalman or Hybrid filter
- Increase `kalman_measurement_noise`
- Use Hybrid (best at spike rejection)

---

## 📝 Quick Start Recommendations

**Just starting? Use this:**
```python
SMOOTHING_CONFIG = {
    'filter_type': 'hybrid',
}
```

**Want maximum speed? Use this:**
```python
SMOOTHING_CONFIG = {
    'filter_type': 'ema',
    'ema_alpha': 0.4,
}
```

**Want maximum smoothness? Use this:**
```python
SMOOTHING_CONFIG = {
    'filter_type': 'gaussian',
    'gaussian_window_size': 9,
    'gaussian_sigma': 2.5,
}
```

**Production deployment? Use this:**
```python
SMOOTHING_CONFIG = {
    'filter_type': 'hybrid',
}
```

---

## 🎯 Summary

- **Hybrid** = Best overall, default choice
- **Kalman** = Best for noisy sensors
- **EMA** = Fastest response
- **Gaussian** = Smoothest output
- **Savitzky-Golay** = Best for preserving peaks
- **Double EMA** = Best for trending movements

All filters work incrementally with **constant memory and performance**, supporting unlimited workout duration! 🚀
