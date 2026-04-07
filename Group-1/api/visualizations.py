import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import cv2
from matplotlib.patches import Rectangle
from matplotlib.colors import LinearSegmentedColormap
from matplotlib.cm import ScalarMappable
from matplotlib.colors import Normalize

# Professional color schemes
CNN_COLORMAP = plt.cm.jet  # For heatmaps
VIT_CMAP = plt.cm.RdYlGn   # Red-Yellow-Green for patches
SHAP_COLOR = '#1f77b4'      # Professional blue for SHAP

def create_cnn_visualization(image_np, cam, model_name, pred_name, confidence, true_label):
    """
    Professional CNN Grad-CAM visualization:
    - Single heatmap image with proper colorbar
    - Clean, professional design
    """
    # Create figure
    fig, ax = plt.subplots(1, 1, figsize=(12, 10))
    
    # Create overlay
    heatmap_colored = cv2.applyColorMap(np.uint8(255 * cam), cv2.COLORMAP_JET)
    heatmap_colored = cv2.cvtColor(heatmap_colored, cv2.COLOR_BGR2RGB) / 255.0
    
    # Blend with original image (60% heatmap, 40% original)
    overlay = heatmap_colored * 0.6 + image_np * 0.4
    
    # Display the overlay
    ax.imshow(overlay)
    
    # Title with prediction
    title_color = '#2ecc71' if pred_name.lower() == 'real' else '#e74c3c'
    ax.set_title(f'EfficientNet (CNN) Grad-CAM\nPrediction: {pred_name.upper()}  |  Confidence: {confidence:.1f}%', 
                 fontsize=16, fontweight='bold', pad=20, color=title_color)
    ax.axis('off')
    
    # Add colorbar with professional styling
    sm = ScalarMappable(cmap=plt.cm.jet, norm=Normalize(vmin=0, vmax=1))
    sm.set_array([])
    cbar = plt.colorbar(sm, ax=ax, fraction=0.046, pad=0.04, shrink=0.7)
    cbar.set_label('Feature Importance (Gradient Weight)', fontsize=12, fontweight='bold')
    cbar.ax.tick_params(labelsize=10)
    
    # Add professional legend at bottom
    legend_text = (
        "🔴 Red regions: High influence on the model's decision\n"
        "🔵 Blue regions: Low influence on the model's decision\n"
        "The model focuses on these highlighted areas to determine if the image is FAKE or REAL"
    )
    
    fig.text(0.5, 0.02, legend_text, ha='center', fontsize=11,
             bbox=dict(boxstyle='round,pad=0.5', facecolor='#f8f9fa', 
                      alpha=0.9, edgecolor='#dee2e6', linewidth=1))
    
    plt.tight_layout()
    return fig


def create_vit_visualization(image_np, patch_importance, patch_features, grid_size, patch_size, 
                             model_name, pred_name, confidence, true_label):
    """
    Professional ViT patch visualization:
    - Shows patch importance with colored borders
    - Clear gradient of importance
    - Professional design
    """
    fig, axes = plt.subplots(1, 2, figsize=(18, 8))
    
    # LEFT: Original image with patch grid
    ax1 = axes[0]
    ax1.imshow(image_np)
    
    # Draw professional patch grid
    for i in range(grid_size + 1):
        ax1.axhline(i * patch_size, color='white', linewidth=0.8, alpha=0.5)
        ax1.axvline(i * patch_size, color='white', linewidth=0.8, alpha=0.5)
    
    ax1.set_title('Original Image with Patch Grid', fontsize=15, fontweight='bold', pad=15)
    ax1.axis('off')
    
    # Add patch count with professional styling
    ax1.text(5, 25, f'{grid_size}×{grid_size} patches', color='white', fontsize=12,
             bbox=dict(boxstyle='round', facecolor='#2c3e50', alpha=0.8, edgecolor='none'))
    
    # RIGHT: Patch importance with colored borders
    ax2 = axes[1]
    ax2.imshow(image_np)
    
    # Find top patches for highlighting
    flat_importance = patch_importance.flatten()
    sorted_indices = np.argsort(flat_importance)[::-1]
    
    # Highlight patches based on importance percentile
    # Top 10% - Red, Next 15% - Orange, Next 25% - Yellow, Rest - Light Green
    total_patches = grid_size * grid_size
    red_threshold = int(total_patches * 0.10)      # Top 10%
    orange_threshold = int(total_patches * 0.25)   # Next 15%
    yellow_threshold = int(total_patches * 0.50)   # Next 25%
    
    highlighted_count = 0
    for rank, idx in enumerate(sorted_indices):
        if rank >= yellow_threshold:
            break
            
        i = idx // grid_size
        j = idx % grid_size
        importance = patch_importance[i, j]
        
        # Determine color based on importance rank
        if rank < red_threshold:
            color = '#e74c3c'  # Red
            linewidth = 3
            alpha = 1.0
            label = 'Critical patches'
        elif rank < orange_threshold:
            color = '#e67e22'  # Orange
            linewidth = 2.5
            alpha = 0.9
            label = 'High importance'
        elif rank < yellow_threshold:
            color = '#f1c40f'  # Yellow
            linewidth = 2
            alpha = 0.8
            label = 'Moderate importance'
        else:
            continue
        
        x1 = j * patch_size
        y1 = i * patch_size
        
        rect = Rectangle((x1, y1), patch_size, patch_size,
                        linewidth=linewidth, edgecolor=color, 
                        facecolor='none', alpha=alpha)
        ax2.add_patch(rect)
        highlighted_count += 1
        
        # Add importance score for critical patches
        if rank < red_threshold:
            ax2.text(x1 + patch_size/2, y1 + patch_size/2, f'{importance:.2f}',
                    ha='center', va='center', fontsize=8, color='white',
                    bbox=dict(boxstyle='round', facecolor='#2c3e50', alpha=0.7, edgecolor='none'))
    
    ax2.set_title(f'Patch Importance Analysis\n({highlighted_count} important patches highlighted)', 
                  fontsize=15, fontweight='bold', pad=15)
    ax2.axis('off')
    
    # Add professional legend
    legend_elements = [
        Rectangle((0,0), 1, 1, facecolor='none', edgecolor='#e74c3c', linewidth=3, label='Critical patches (Top 10%)'),
        Rectangle((0,0), 1, 1, facecolor='none', edgecolor='#e67e22', linewidth=2.5, label='High importance (Top 25%)'),
        Rectangle((0,0), 1, 1, facecolor='none', edgecolor='#f1c40f', linewidth=2, label='Moderate importance (Top 50%)')
    ]
    
    fig.legend(handles=legend_elements, loc='lower center', bbox_to_anchor=(0.5, 0.02),
              ncol=3, fontsize=10, frameon=True, fancybox=True, shadow=True)
    
    # Main title
    title_color = '#2ecc71' if pred_name.lower() == 'real' else '#e74c3c'
    fig.suptitle(f'Vision Transformer (ViT) Analysis: How the model sees the image\n'
                 f'Prediction: {pred_name.upper()}  |  Confidence: {confidence:.1f}%', 
                 fontsize=16, fontweight='bold', y=1.02, color=title_color)
    
    plt.tight_layout(rect=[0, 0.05, 1, 0.95])
    return fig


def create_shap_plot(shap_values, feature_names, feature_values, model_name, prediction, output_type="cnn"):
    """
    Professional SHAP plot with consistent styling
    """
    # Calculate feature importance (mean absolute SHAP value)
    mean_shap = np.abs(shap_values).mean(axis=0)
    
    # Get top 10 features
    top_n = 10
    sorted_idx = np.argsort(mean_shap)[::-1][:top_n]
    sorted_features = [feature_names[i] for i in sorted_idx]
    sorted_shap = mean_shap[sorted_idx]
    
    # Create readable names
    readable_names = []
    for feat in sorted_features:
        # Convert to readable format
        name = feat.replace('_', ' ').title()
        if 'Cnn' in name:
            name = name.replace('Cnn', 'CNN')
        elif 'Vit' in name:
            name = name.replace('Vit', 'ViT')
        
        # Shorten if needed
        if len(name) > 25:
            name = name[:22] + '...'
        readable_names.append(name)
    
    # Create figure with professional layout
    fig, ax = plt.subplots(figsize=(14, 8))
    
    # Use consistent professional blue for both models
    color = SHAP_COLOR
    
    # Create horizontal bar plot
    y_pos = np.arange(len(sorted_features))
    bars = ax.barh(y_pos, sorted_shap, color=color, edgecolor='white', alpha=0.9, height=0.7)
    
    # Customize plot
    ax.set_yticks(y_pos)
    ax.set_yticklabels(readable_names, fontsize=12)
    ax.set_xlabel('Mean |SHAP Value| (Feature Importance)', fontsize=13, fontweight='bold')
    ax.tick_params(axis='x', labelsize=11)
    
    # Add grid for readability
    ax.xaxis.grid(True, linestyle='--', alpha=0.3, linewidth=0.5)
    ax.set_axisbelow(True)
    ax.invert_yaxis()
    
    # Add title with prediction
    title_color = '#2ecc71' if prediction.lower() == 'real' else '#e74c3c'
    model_title = "EfficientNet (CNN)" if output_type == "cnn" else "Vision Transformer (ViT)"
    ax.set_title(f'{model_title} Feature Importance Analysis\nWhy the model predicted: {prediction.upper()}', 
                 fontsize=16, fontweight='bold', pad=20, color=title_color)
    
    # Add value labels on bars
    for i, (bar, val) in enumerate(zip(bars, sorted_shap)):
        width = bar.get_width()
        ax.text(width + 0.001, i, f'{val:.3f}', va='center', fontsize=10, fontweight='bold')
    
    # Add professional explanation at bottom
    explanation = (
        "Higher SHAP value = More influence on the model's decision\n"
        "These are the visual features that most strongly influenced the prediction"
    )
    fig.text(0.5, 0.02, explanation, ha='center', fontsize=10, style='italic',
             bbox=dict(boxstyle='round', facecolor='#f8f9fa', alpha=0.9, edgecolor='#dee2e6'))
    
    plt.tight_layout(rect=[0, 0.05, 1, 0.95])
    return fig