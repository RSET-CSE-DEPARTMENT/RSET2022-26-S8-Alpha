// Check if already injected to prevent duplicate execution
if (window.imageGuardInjected) {
  console.log("ImageGuard already injected, skipping");
} else {
  window.imageGuardInjected = true;
  
  console.log("ImageGuard content script loaded with improved overlay display");

  let isEnabled = true;
  let hoverTimeout = null;
  let analyzedImages = new Map(); // Store results to avoid re-analysis
  let lastHoveredImage = null;
  let lastClickedImage = null;

  // Initialize
  chrome.storage.local.get(['detectionEnabled'], (data) => {
    if (data.detectionEnabled !== undefined) {
      isEnabled = data.detectionEnabled;
    }
    console.log(`ImageGuard initialized: ${isEnabled ? 'ENABLED' : 'DISABLED'}`);
  });

  // Function to check if image is an XAI visualization
  function isXaiImage(src) {
    if (!src) return true;
    const xaiKeywords = [
      'cnn_explanation', 'vit_explanation', 'cnn_feature_analysis', 'vit_feature_analysis',
      'gradcam', 'xai', 'explanation', 'analysis', 'heatmap', 'patch', 'shap',
      'xai_outputs', 'cnn_gradcam', 'vit_gradcam'
    ];
    const url = src.toLowerCase();
    return xaiKeywords.some(keyword => url.includes(keyword));
  }

  // Create beautiful overlay - IMPROVED VERSION
  function createOverlay(img, text, color, confidence = null) {
    // Remove existing overlay for this image
    const existingOverlay = img.parentElement?.querySelector('.imageguard-overlay');
    if (existingOverlay) existingOverlay.remove();
    
    // Also check for any orphaned overlays with same image src
    document.querySelectorAll('.imageguard-overlay').forEach(overlay => {
      if (overlay.dataset.imageSrc === img.src) {
        overlay.remove();
      }
    });
    
    // Ensure parent is positioned
    let parent = img.parentElement;
    let positionedParent = null;
    
    // Find a positioned parent or make the closest relative container positioned
    while (parent && parent !== document.body) {
      const position = getComputedStyle(parent).position;
      if (position === 'relative' || position === 'absolute' || position === 'fixed') {
        positionedParent = parent;
        break;
      }
      parent = parent.parentElement;
    }
    
    if (!positionedParent) {
      // Make the image's parent relatively positioned
      const imgParent = img.parentElement;
      if (imgParent && getComputedStyle(imgParent).position === 'static') {
        imgParent.style.position = 'relative';
      }
      positionedParent = imgParent;
    }
    
    // Create overlay container
    const overlay = document.createElement('div');
    overlay.className = 'imageguard-overlay';
    overlay.dataset.imageSrc = img.src;
    overlay.style.cssText = `
      position: absolute !important;
      bottom: 8px !important;
      left: 8px !important;
      top: auto !important;
      right: auto !important;
      z-index: 999999 !important;
      pointer-events: auto !important;
      display: block !important;
      visibility: visible !important;
      opacity: 1 !important;
    `;
    
    // Create badge
    const badge = document.createElement('div');
    
    // Determine icon and color based on verdict
    let icon = '';
    let bgColor = color;
    let badgeText = text;
    
    if (text.includes('FAKE')) {
      icon = '🔴 ';
      bgColor = '#dc3545';
    } else if (text.includes('REAL')) {
      icon = '🟢 ';
      bgColor = '#28a745';
    } else if (text.includes('ANALYZING')) {
      icon = '⏳ ';
      bgColor = '#ff9800';
    } else if (text.includes('ERROR')) {
      icon = '⚠️ ';
      bgColor = '#6c757d';
    } else {
      icon = '🛡️ ';
    }
    
    badge.innerHTML = `${icon}${badgeText}`;
    badge.style.cssText = `
      background: ${bgColor} !important;
      color: white !important;
      padding: 6px 12px !important;
      border-radius: 20px !important;
      font-size: 11px !important;
      font-weight: 600 !important;
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif !important;
      cursor: pointer !important;
      box-shadow: 0 2px 8px rgba(0,0,0,0.25) !important;
      backdrop-filter: blur(2px) !important;
      letter-spacing: 0.3px !important;
      border: 1px solid rgba(255,255,255,0.2) !important;
      transition: all 0.2s ease !important;
      white-space: nowrap !important;
      display: inline-flex !important;
      align-items: center !important;
      gap: 4px !important;
      line-height: 1 !important;
      z-index: 999999 !important;
      pointer-events: auto !important;
    `;
    
    // Add hover effects
    badge.onmouseenter = () => {
      badge.style.transform = 'translateY(-1px)';
      badge.style.boxShadow = '0 4px 12px rgba(0,0,0,0.3)';
    };
    
    badge.onmouseleave = () => {
      badge.style.transform = 'translateY(0)';
      badge.style.boxShadow = '0 2px 8px rgba(0,0,0,0.25)';
    };
    
    // Add click handler
    badge.onclick = (e) => {
      e.stopPropagation();
      e.preventDefault();
      
      // Add click animation
      badge.style.transform = 'scale(0.95)';
      setTimeout(() => {
        badge.style.transform = '';
      }, 150);
      
      // Store the clicked image
      lastClickedImage = img.src;
      chrome.storage.local.set({
        clickedImage: {
          src: img.src,
          verdict: img.dataset.verdict,
          confidence: img.dataset.confidence,
          timestamp: Date.now()
        },
        pendingImageUrl: img.src,
        autoAnalyzePending: true
      });
      
      // Open extension popup
      chrome.runtime.sendMessage({ action: "openPopup" }, (response) => {
        if (chrome.runtime.lastError) {
          console.log("Please click the extension icon to see results");
          // Show a temporary tooltip
          const tooltip = document.createElement('div');
          tooltip.textContent = 'Click the ImageGuard icon in toolbar';
          tooltip.style.cssText = `
            position: fixed;
            bottom: 20px;
            right: 20px;
            background: #1a56db;
            color: white;
            padding: 8px 16px;
            border-radius: 8px;
            font-size: 12px;
            z-index: 1000000;
            animation: fadeOut 3s ease forwards;
          `;
          document.body.appendChild(tooltip);
          setTimeout(() => tooltip.remove(), 3000);
        }
      });
    };
    
    overlay.appendChild(badge);
    
    // Try multiple attachment strategies
    try {
      // Strategy 1: Attach to positioned parent
      if (positionedParent && positionedParent !== img.parentElement) {
        positionedParent.style.position = 'relative';
        positionedParent.appendChild(overlay);
      } 
      // Strategy 2: Attach to image's parent
      else if (img.parentElement) {
        if (getComputedStyle(img.parentElement).position === 'static') {
          img.parentElement.style.position = 'relative';
        }
        img.parentElement.appendChild(overlay);
      }
      // Strategy 3: Attach after image
      else {
        img.insertAdjacentElement('afterend', overlay);
      }
    } catch(e) {
      // Final fallback
      document.body.appendChild(overlay);
      const rect = img.getBoundingClientRect();
      overlay.style.position = 'fixed';
      overlay.style.bottom = (window.innerHeight - rect.top + 5) + 'px';
      overlay.style.left = (rect.left + 5) + 'px';
    }
    
    // Add outline to image
    img.style.outline = `2px solid ${bgColor}`;
    img.style.outlineOffset = '2px';
    img.style.transition = 'outline 0.2s ease';
    img.style.cursor = 'pointer';
    
    return overlay;
  }

  // Show analyzing state
  function showAnalyzing(img) {
    if (!img || img.dataset.imageguard === 'true') return;
    
    // Remove existing overlay
    const existing = img.parentElement?.querySelector('.imageguard-overlay');
    if (existing) existing.remove();
    
    createOverlay(img, 'ANALYZING...', '#ff9800');
    img.style.outline = '2px solid #ff9800';
    img.style.outlineOffset = '2px';
    img.style.cursor = 'wait';
    img.dataset.analyzing = 'true';
  }

  // Show error state
  function showError(img) {
    if (!img) return;
    delete img.dataset.analyzing;
    createOverlay(img, 'ERROR', '#6c757d');
    img.style.outline = '2px solid #6c757d';
    img.style.cursor = 'not-allowed';
  }

  // Show result state
  function showResult(img, verdict, confidence) {
    if (!img) return;
    
    const isFake = verdict === 'FAKE';
    const color = isFake ? '#dc3545' : '#28a745';
    const percentage = Math.round(confidence);
    const text = `${isFake ? 'FAKE' : 'REAL'} ${percentage}%`;
    
    delete img.dataset.analyzing;
    img.dataset.imageguard = 'true';
    img.dataset.verdict = verdict;
    img.dataset.confidence = confidence;
    
    createOverlay(img, text, color, confidence);
    img.style.outline = `2px solid ${color}`;
    img.style.cursor = 'pointer';
    
    // Store in cache
    analyzedImages.set(img.src, { verdict, confidence, timestamp: Date.now() });
  }

  // Mouseover handler
  document.addEventListener('mouseover', (e) => {
    if (!isEnabled) return;
    
    let img = e.target;
    // Traverse up to find img if needed (for Amazon's nested structure)
    while (img && img.tagName !== 'IMG' && img !== document.body) {
      img = img.parentElement;
    }
    
    if (img && img.tagName === 'IMG' && img.src && img.src.startsWith('http')) {
      // Skip if already analyzed or analyzing
      if (img.dataset.imageguard === 'true') return;
      if (img.dataset.analyzing === 'true') return;
      
      // Skip XAI images
      if (isXaiImage(img.src)) return;
      
      // Skip very small images
      if (img.width < 50 || img.height < 50) return;
      
      // Skip data URLs
      if (img.src.startsWith('data:')) return;
      
      // Check cache
      const cached = analyzedImages.get(img.src);
      if (cached && (Date.now() - cached.timestamp) < 300000) { // 5 minutes cache
        showResult(img, cached.verdict, cached.confidence);
        return;
      }
      
      // Track hovered image
      lastHoveredImage = img.src;
      
      // Clear previous timeout
      if (hoverTimeout) clearTimeout(hoverTimeout);
      
      // Set timeout for hover (800ms delay)
      hoverTimeout = setTimeout(() => {
        // Show analyzing state
        showAnalyzing(img);
        
        // Send to background for analysis
        chrome.runtime.sendMessage({
          action: "analyzeImage",
          imageUrl: img.src
        }, (response) => {
          if (chrome.runtime.lastError) {
            console.error("Runtime error:", chrome.runtime.lastError);
            showError(img);
          }
        });
      }, 800);
    }
  });

  // Mouseout handler
  document.addEventListener('mouseout', (e) => {
    let img = e.target;
    while (img && img.tagName !== 'IMG' && img !== document.body) {
      img = img.parentElement;
    }
    
    if (img && img.tagName === 'IMG') {
      if (hoverTimeout) {
        clearTimeout(hoverTimeout);
        hoverTimeout = null;
      }
      
      // Don't remove outline if analyzed
      if (!img.dataset.imageguard && !img.dataset.analyzing) {
        img.style.outline = '';
        img.style.cursor = '';
      }
    }
  });

  // Listen for messages from background
  chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
    console.log("📨 Content received:", message.action);
    
    if (message.action === "updateImage") {
      console.log("Updating image:", message.verdict, message.confidence);
      
      // Find all matching images
      const imgs = document.querySelectorAll('img');
      let updated = false;
      
      imgs.forEach(img => {
        // Try different matching strategies
        const imgSrc = img.src;
        const messageSrc = message.imageUrl;
        
        if (imgSrc === messageSrc || 
            imgSrc === decodeURIComponent(messageSrc) || 
            decodeURIComponent(imgSrc) === messageSrc ||
            imgSrc.includes(messageSrc.split('/').pop()) ||
            messageSrc.includes(imgSrc.split('/').pop())) {
          
          showResult(img, message.verdict, message.confidence);
          updated = true;
        }
      });
      
      if (!updated) {
        console.log("Image not found on page, will apply when visible");
        // Store for later when image appears
        chrome.storage.local.set({
          pendingImageUpdate: {
            imageUrl: message.imageUrl,
            verdict: message.verdict,
            confidence: message.confidence,
            timestamp: Date.now()
          }
        });
      }
      
      sendResponse({ success: updated });
    }
    
    else if (message.action === "showError") {
      const imgs = document.querySelectorAll('img');
      imgs.forEach(img => {
        if (img.src === message.imageUrl || img.src.includes(message.imageUrl.split('/').pop())) {
          showError(img);
        }
      });
      sendResponse({ success: true });
    }
    
    else if (message.action === "toggleDetection") {
      isEnabled = message.enabled !== false;
      
      if (!isEnabled) {
        // Clean up
        document.querySelectorAll('.imageguard-overlay').forEach(el => el.remove());
        document.querySelectorAll('img').forEach(img => {
          img.style.outline = '';
          img.style.cursor = '';
          delete img.dataset.imageguard;
          delete img.dataset.analyzing;
        });
        analyzedImages.clear();
        console.log("ImageGuard disabled");
      } else {
        console.log("ImageGuard enabled");
      }
      
      chrome.storage.local.set({ detectionEnabled: isEnabled });
      sendResponse({ success: true, enabled: isEnabled });
    }
    
    else if (message.action === "clearOverlays") {
      document.querySelectorAll('.imageguard-overlay').forEach(el => el.remove());
      document.querySelectorAll('img').forEach(img => {
        img.style.outline = '';
        img.style.cursor = '';
        delete img.dataset.imageguard;
        delete img.dataset.analyzing;
      });
      analyzedImages.clear();
      sendResponse({ success: true });
    }
    
    else if (message.action === "getSelectedImageForMismatch") {
      const imageSrc = lastClickedImage || lastHoveredImage;
      if (imageSrc) {
        sendResponse({ imageSrc: imageSrc });
      } else {
        sendResponse({ imageSrc: null });
      }
    }
    
    else if (message.action === "ping") {
      sendResponse({ alive: true, version: '2.0' });
    }
    
    return true;
  });

  // Handle dynamically added images
  const observer = new MutationObserver((mutations) => {
    if (!isEnabled) return;
    
    mutations.forEach((mutation) => {
      mutation.addedNodes.forEach((node) => {
        // Check for images
        if (node.tagName === 'IMG') {
          addImageListeners(node);
        }
        // Check for containers with images
        if (node.querySelectorAll) {
          node.querySelectorAll('img').forEach(img => addImageListeners(img));
        }
      });
    });
  });
  
  function addImageListeners(img) {
    if (!img.src || !img.src.startsWith('http')) return;
    if (img.dataset.imageguard === 'true') return;
    if (isXaiImage(img.src)) return;
    if (analyzedImages.has(img.src)) return;
    
    // Remove existing listener flag
    if (!img.dataset.imageguardListener) {
      img.addEventListener('mouseover', handleImageHover);
      img.addEventListener('mouseout', handleImageOut);
      img.dataset.imageguardListener = 'true';
    }
  }
  
  function handleImageHover(e) {
    if (!isEnabled) return;
    const img = e.target;
    
    if (img.dataset.imageguard === 'true') return;
    if (img.dataset.analyzing === 'true') return;
    if (isXaiImage(img.src)) return;
    if (img.width < 50 || img.height < 50) return;
    
    // Check cache
    const cached = analyzedImages.get(img.src);
    if (cached && (Date.now() - cached.timestamp) < 300000) {
      showResult(img, cached.verdict, cached.confidence);
      return;
    }
    
    lastHoveredImage = img.src;
    
    if (img.hoverTimeout) clearTimeout(img.hoverTimeout);
    
    img.hoverTimeout = setTimeout(() => {
      showAnalyzing(img);
      chrome.runtime.sendMessage({
        action: "analyzeImage",
        imageUrl: img.src
      });
    }, 800);
  }
  
  function handleImageOut(e) {
    const img = e.target;
    if (img.hoverTimeout) {
      clearTimeout(img.hoverTimeout);
      img.hoverTimeout = null;
    }
    
    if (!img.dataset.imageguard && !img.dataset.analyzing) {
      img.style.outline = '';
      img.style.cursor = '';
    }
  }
  
  // Start observing
  observer.observe(document.body, {
    childList: true,
    subtree: true
  });
  
  // Add CSS animations
  const style = document.createElement('style');
  style.textContent = `
    @keyframes imageguardFadeIn {
      from {
        opacity: 0;
        transform: translateY(5px);
      }
      to {
        opacity: 1;
        transform: translateY(0);
      }
    }
    
    .imageguard-overlay {
      animation: imageguardFadeIn 0.2s ease-out !important;
    }
    
    @keyframes fadeOut {
      0% { opacity: 1; }
      70% { opacity: 1; }
      100% { opacity: 0; visibility: hidden; }
    }
  `;
  document.head.appendChild(style);
  
  // Initial scan
  window.addEventListener('load', () => {
    console.log("ImageGuard ready on", window.location.hostname);
    document.querySelectorAll('img[src^="http"]').forEach(img => addImageListeners(img));
    
    // Check for pending updates
    chrome.storage.local.get(['pendingImageUpdate'], (storage) => {
      if (storage.pendingImageUpdate && (Date.now() - storage.pendingImageUpdate.timestamp) < 30000) {
        const update = storage.pendingImageUpdate;
        const imgs = document.querySelectorAll('img');
        imgs.forEach(img => {
          if (img.src === update.imageUrl || img.src.includes(update.imageUrl.split('/').pop())) {
            showResult(img, update.verdict, update.confidence);
            chrome.storage.local.remove(['pendingImageUpdate']);
          }
        });
      }
    });
  });
  
  console.log("✅ ImageGuard content script ready with improved overlay display");
}