import numpy as np
import cv2
from scipy import fftpack
from scipy.ndimage import gaussian_filter

def extract_human_friendly_features(image_np):
    """Extract features that normal people understand when looking at fake vs real products"""
    features = {}
    
    img_uint8 = (image_np * 255).astype(np.uint8)
    gray = cv2.cvtColor(img_uint8, cv2.COLOR_RGB2GRAY)
    hsv = cv2.cvtColor(img_uint8, cv2.COLOR_RGB2HSV) / 255.0
    
    # ===== 1. VISUAL QUALITY FEATURES =====
    
    # Sharpness
    sobel_x = cv2.Sobel(gray, cv2.CV_64F, 1, 0, ksize=3)
    sobel_y = cv2.Sobel(gray, cv2.CV_64F, 0, 1, ksize=3)
    gradient = np.sqrt(sobel_x**2 + sobel_y**2)
    features['Image_Sharpness'] = np.mean(gradient) / 1000
    
    # Blurriness
    laplacian = cv2.Laplacian(gray, cv2.CV_64F)
    features['Blurriness'] = 1.0 - min(np.var(laplacian) / 10000, 1.0)
    
    # ===== 2. COLOR FEATURES =====
    
    # Color richness
    features['Color_Richness'] = np.mean(hsv[:, :, 1])
    
    # Color consistency
    color_diff = np.std(image_np, axis=(0, 1)).mean()
    features['Color_Consistency'] = 1.0 - min(color_diff * 3, 1.0)
    
    # Print quality
    edges = cv2.Canny(gray, 50, 150)
    edge_colors = []
    edge_positions = np.column_stack(np.where(edges > 0))
    
    if len(edge_positions) > 0:
        for i in range(min(100, len(edge_positions))):
            y, x = edge_positions[i]
            if y < image_np.shape[0] and x < image_np.shape[1]:
                edge_colors.append(np.std(image_np[y, x]))
        
        if edge_colors:
            features['Print_Sharpness'] = 1.0 - np.mean(edge_colors)
        else:
            features['Print_Sharpness'] = 0.5
    else:
        features['Print_Sharpness'] = 0.5
    
    # ===== 3. TEXTURE FEATURES =====
    
    # Texture detail
    blurred = gaussian_filter(gray, sigma=2)
    details = np.abs(gray - blurred)
    features['Texture_Detail'] = min(np.mean(details) / 100, 1.0)
    
    # Surface smoothness
    features['Surface_Smoothness'] = 1.0 - features['Texture_Detail']
    
    # Pattern regularity
    fft = np.abs(fftpack.fft2(gray))
    fft_shifted = fftpack.fftshift(fft)
    center = fft_shifted.shape[0] // 2
    
    quarter = center // 2
    center_strength = np.mean(fft_shifted[max(0, center-quarter):min(fft_shifted.shape[0], center+quarter), 
                                          max(0, center-quarter):min(fft_shifted.shape[1], center+quarter)])
    total_strength = np.mean(fft_shifted)
    features['Repeating_Patterns'] = min(center_strength / (total_strength + 1e-8), 1.0)
    
    # ===== 4. LIGHTING FEATURES =====
    
    # Lighting quality
    brightness_std = np.std(gray)
    features['Lighting_Quality'] = 1.0 - min(brightness_std / 100, 1.0)
    
    # Shadow softness
    shadow_threshold = np.percentile(gray, 30)
    shadow_mask = gray < shadow_threshold
    if np.any(shadow_mask):
        shadow_edges = cv2.Canny((gray * 255).astype(np.uint8), 50, 150)
        shadow_edge_values = shadow_edges[shadow_mask]
        if len(shadow_edge_values) > 0:
            features['Shadow_Softness'] = 1.0 - min(np.mean(shadow_edge_values) / 255.0, 1.0)
        else:
            features['Shadow_Softness'] = 0.7
    else:
        features['Shadow_Softness'] = 0.7
    
    # ===== 5. DETAIL FEATURES =====
    
    # Edge crispness
    edge_intensity = np.mean(edges) / 255.0
    features['Edge_Crispness'] = min(edge_intensity, 1.0)
    
    # Detail complexity
    contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if contours:
        features['Detail_Complexity'] = min(len(contours) / 50, 1.0)
    else:
        features['Detail_Complexity'] = 0.3
    
    # ===== 6. COMPOSITION FEATURES =====
    
    # Product centering
    height, width = gray.shape
    center_region = gray[height//3:2*height//3, width//3:2*width//3]
    border_regions = []
    
    if height // 4 > 0:
        border_regions.append(gray[:height//4, :].flatten())
    if height // 4 > 0:
        border_regions.append(gray[-height//4:, :].flatten())
    if width // 4 > 0:
        border_regions.append(gray[:, :width//4].flatten())
    if width // 4 > 0:
        border_regions.append(gray[:, -width//4:].flatten())
    
    if border_regions:
        border_region = np.concatenate(border_regions)
        if len(border_region) > 0:
            center_brightness = np.mean(center_region) / 255.0
            border_brightness = np.mean(border_region) / 255.0
            features['Product_Centering'] = min(max(center_brightness - border_brightness + 0.5, 0), 1)
        else:
            features['Product_Centering'] = 0.5
    else:
        features['Product_Centering'] = 0.5
    
    # Background simplicity
    bg_complexity = 0
    if height // 8 > 0:
        bg_complexity += np.std(gray[:height//8, :]) if height//8 > 0 else 0
        bg_complexity += np.std(gray[-height//8:, :]) if height//8 > 0 else 0
    if width // 8 > 0:
        bg_complexity += np.std(gray[:, :width//8]) if width//8 > 0 else 0
        bg_complexity += np.std(gray[:, -width//8:]) if width//8 > 0 else 0
    
    features['Background_Simplicity'] = 1.0 - min(bg_complexity / 400, 1.0)
    
    # ===== 7. PRODUCT INDICATORS =====
    
    # Logo/Text presence
    high_contrast = np.std(image_np, axis=2) > 0.3
    features['Logo_Text_Presence'] = min(np.mean(high_contrast), 1.0)
    
    # Surface shine
    highlights = gray > 200
    features['Surface_Shine'] = min(np.mean(highlights), 1.0)
    
    # ===== 8. NOISE FEATURES =====
    
    # Compression artifacts
    noise = gray - gaussian_filter(gray, sigma=1)
    features['Compression_Artifacts'] = min(np.std(noise) / 50, 1.0)
    
    # Color noise
    color_noise = 0
    for i in range(3):
        channel_filtered = gaussian_filter(image_np[:, :, i], sigma=1)
        color_noise += np.std(image_np[:, :, i] - channel_filtered)
    color_noise /= 3
    features['Color_Noise'] = min(color_noise * 5, 1.0)
    
    return features


def extract_cnn_specific_features(image_np):
    """
    Extract features that CNN (EfficientNet) focuses on:
    - Local patterns, textures, edges, details
    - High-frequency information
    """
    features = {}
    
    img_uint8 = (image_np * 255).astype(np.uint8)
    gray = cv2.cvtColor(img_uint8, cv2.COLOR_RGB2GRAY)
    
    # ===== LOCAL TEXTURE FEATURES (CNN STRENGTH) =====
    
    # 1. Edge density in different orientations
    sobel_x = cv2.Sobel(gray, cv2.CV_64F, 1, 0, ksize=3)
    sobel_y = cv2.Sobel(gray, cv2.CV_64F, 0, 1, ksize=3)
    
    features['Horizontal_Edges'] = np.mean(np.abs(sobel_x)) / 100
    features['Vertical_Edges'] = np.mean(np.abs(sobel_y)) / 100
    features['Diagonal_Edges'] = np.mean(np.abs(sobel_x + sobel_y)) / 100
    
    # 2. Local Binary Pattern (texture descriptor)
    from skimage.feature import local_binary_pattern
    try:
        lbp = local_binary_pattern(gray, 8, 1, method='uniform')
        features['Local_Texture_Variance'] = np.std(lbp) / 20
    except:
        features['Local_Texture_Variance'] = 0.5
    
    # 3. Gabor filter responses (texture at different scales)
    gabor_kernel_size = 21
    gabor_sigma = 3.0
    gabor_theta = 0
    gabor_lambda = 10.0
    gabor_gamma = 0.5
    
    kernel = cv2.getGaborKernel((gabor_kernel_size, gabor_kernel_size), gabor_sigma, gabor_theta, gabor_lambda, gabor_gamma, 0)
    gabor_response = cv2.filter2D(gray, cv2.CV_64F, kernel)
    features['Gabor_Texture'] = np.std(gabor_response) / 100
    
    # 4. Local variance (texture strength in small windows)
    local_var = cv2.blur(gray.astype(np.float32)**2, (5,5)) - cv2.blur(gray.astype(np.float32), (5,5))**2
    features['Local_Variance'] = np.mean(local_var) / 1000
    
    # 5. Gradient magnitude (edge strength)
    gradient_magnitude = np.sqrt(sobel_x**2 + sobel_y**2)
    features['Gradient_Strength'] = np.mean(gradient_magnitude) / 100
    
    # 6. Laplacian (second derivative - detail detection)
    laplacian = cv2.Laplacian(gray, cv2.CV_64F)
    features['Detail_Density'] = np.std(laplacian) / 100
    
    # 7. Harris corner response (corner detection)
    corners = cv2.cornerHarris(gray.astype(np.float32), 2, 3, 0.04)
    features['Corner_Density'] = np.sum(corners > 0.01 * corners.max()) / (gray.shape[0] * gray.shape[1])
    
    # 8. High-frequency energy (from FFT)
    fft = np.abs(fftpack.fft2(gray))
    fft_shifted = fftpack.fftshift(fft)
    center = fft_shifted.shape[0] // 2
    
    # High frequency (away from center)
    high_freq = fft_shifted.copy()
    high_freq[center-20:center+20, center-20:center+20] = 0
    features['High_Freq_Energy'] = np.mean(high_freq) / (np.mean(fft) + 1e-8)
    
    # 9. Local contrast (std dev in patches)
    patch_size = 16
    h_patches = gray.shape[0] // patch_size
    w_patches = gray.shape[1] // patch_size
    patch_stds = []
    for i in range(h_patches):
        for j in range(w_patches):
            patch = gray[i*patch_size:(i+1)*patch_size, j*patch_size:(j+1)*patch_size]
            patch_stds.append(np.std(patch))
    features['Local_Contrast'] = np.mean(patch_stds) / 100
    
    # 10. Edge consistency (how well edges connect)
    edges = cv2.Canny(gray, 50, 150)
    kernel = np.ones((3,3), np.uint8)
    dilated = cv2.dilate(edges, kernel, iterations=1)
    edge_connectivity = np.sum(dilated > 0) / (np.sum(edges > 0) + 1)
    features['Edge_Connectivity'] = min(edge_connectivity / 5, 1.0)
    
    return features


def extract_vit_specific_features(image_np):
    """
    Extract features that ViT (Vision Transformer) focuses on:
    - Global patterns, composition, relationships between parts
    - Low-frequency information, overall structure
    """
    features = {}
    
    img_uint8 = (image_np * 255).astype(np.uint8)
    gray = cv2.cvtColor(img_uint8, cv2.COLOR_RGB2GRAY)
    hsv = cv2.cvtColor(img_uint8, cv2.COLOR_RGB2HSV)
    
    # ===== GLOBAL COMPOSITION FEATURES (ViT STRENGTH) =====
    
    # 1. Symmetry score
    height, width = gray.shape
    left_half = gray[:, :width//2]
    right_half = np.fliplr(gray[:, width//2:])
    
    if left_half.shape == right_half.shape:
        symmetry = 1.0 - np.mean(np.abs(left_half.astype(float) - right_half.astype(float)) / 255.0)
    else:
        min_width = min(left_half.shape[1], right_half.shape[1])
        symmetry = 1.0 - np.mean(np.abs(left_half[:, :min_width].astype(float) - right_half[:, :min_width].astype(float)) / 255.0)
    features['Global_Symmetry'] = symmetry
    
    # 2. Low-frequency energy (global structure)
    fft = np.abs(fftpack.fft2(gray))
    fft_shifted = fftpack.fftshift(fft)
    center = fft_shifted.shape[0] // 2
    
    # Low frequency (center region)
    low_freq = fft_shifted[center-30:center+30, center-30:center+30]
    features['Low_Freq_Energy'] = np.mean(low_freq) / (np.mean(fft) + 1e-8)
    
    # 3. Color harmony (relationships between colors)
    # Quantize colors
    pixels = img_uint8.reshape(-1, 3)
    from sklearn.cluster import KMeans
    kmeans = KMeans(n_clusters=5, n_init=5, random_state=42)
    labels = kmeans.fit_predict(pixels)
    from collections import Counter
    counts = Counter(labels)
    # Color harmony score based on distribution
    color_distribution = np.array(list(counts.values())) / len(labels)
    features['Color_Harmony'] = 1.0 - np.std(color_distribution) * 2
    
    # 4. Spatial relationship (center vs edges)
    center_region = gray[height//4:3*height//4, width//4:3*width//4]
    edge_regions = np.concatenate([
        gray[:height//4, :].flatten(),
        gray[-height//4:, :].flatten(),
        gray[:, :width//4].flatten(),
        gray[:, -width//4:].flatten()
    ])
    
    center_mean = np.mean(center_region)
    edge_mean = np.mean(edge_regions)
    features['Center_Edge_Contrast'] = abs(center_mean - edge_mean) / 255.0
    
    # 5. Global contrast
    features['Global_Contrast'] = np.std(gray) / 100
    
    # 6. Entropy (information content)
    hist = cv2.calcHist([gray], [0], None, [256], [0, 256]).flatten()
    hist = hist / hist.sum()
    entropy = -np.sum(hist * np.log2(hist + 1e-10))
    features['Image_Entropy'] = min(entropy / 8, 1.0)
    
    # 7. Pattern repetition (global)
    # Use autocorrelation
    fft_mag = np.abs(fftpack.fft2(gray))
    autocorr = np.real(fftpack.ifft2(fft_mag**2))
    autocorr_norm = autocorr / autocorr[0, 0]
    features['Pattern_Repetition'] = np.std(autocorr_norm[10:50, 10:50])
    
    # 8. Background-foreground separation
    _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    foreground_ratio = np.sum(binary > 0) / binary.size
    features['Foreground_Ratio'] = foreground_ratio
    
    # 9. Depth perception (variance in different regions)
    top_region = gray[:height//3, :]
    middle_region = gray[height//3:2*height//3, :]
    bottom_region = gray[2*height//3:, :]
    
    top_var = np.var(top_region)
    middle_var = np.var(middle_region)
    bottom_var = np.var(bottom_region)
    
    features['Vertical_Variation'] = np.std([top_var, middle_var, bottom_var]) / 1000
    
    # 10. Overall quality score
    features['Overall_Quality'] = (np.mean(gray) / 255.0 + np.std(gray) / 100) / 2
    
    # 11. Saturation variance (colorfulness)
    saturation = hsv[:, :, 1]
    features['Saturation_Variance'] = np.std(saturation) / 100
    
    # 12. Value variance (brightness distribution)
    value = hsv[:, :, 2]
    features['Brightness_Variance'] = np.std(value) / 100
    
    return features