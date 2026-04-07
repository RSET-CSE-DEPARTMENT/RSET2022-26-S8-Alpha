console.log("ImageGuard popup loaded - Professional unified interface v1.5");

// ================== UTILITY FUNCTIONS ==================

function updateStatus(text, isError = false, isWarning = false) {
  const statusText = document.getElementById("statusText");
  const statusDot = document.getElementById("statusDot");
  statusText.textContent = text;
  if (isError) {
    statusDot.className = "status-dot error";
  } else if (isWarning) {
    statusDot.className = "status-dot warning";
  } else {
    statusDot.className = "status-dot";
  }
}

function addCacheBust(url) {
  if (!url) return url;
  const separator = url.includes('?') ? '&' : '?';
  return url + separator + 't=' + Date.now();
}

function showLoading(text = "Processing...") {
  const loadingDiv = document.getElementById("loading");
  const loadingText = document.getElementById("loadingText");
  loadingText.textContent = text;
  loadingDiv.classList.remove("hidden");
  document.getElementById("result").classList.add("hidden");
  document.getElementById("xaiSection").classList.add("hidden");
  document.getElementById("feedbackSection").classList.add("hidden");
  document.getElementById("error").classList.add("hidden");
  updateStatus(text);
}

function hideLoading() {
  document.getElementById("loading").classList.add("hidden");
}

function showError(msg) {
  hideLoading();
  document.getElementById("result").classList.add("hidden");
  document.getElementById("xaiSection").classList.add("hidden");
  document.getElementById("feedbackSection").classList.add("hidden");
  const errorDiv = document.getElementById("error");
  document.getElementById("errorMsg").textContent = msg;
  errorDiv.classList.remove("hidden");
  updateStatus(msg, true);
}

function clearResults() {
  hideLoading();
  document.getElementById("result").classList.add("hidden");
  document.getElementById("xaiSection").classList.add("hidden");
  document.getElementById("feedbackSection").classList.add("hidden");
  document.getElementById("error").classList.add("hidden");
  document.getElementById("original").src = "";
  document.getElementById("verdict").textContent = "-";
  document.getElementById("confidenceFill").style.width = "0%";
  document.getElementById("effPred").textContent = "-";
  document.getElementById("vitPred").textContent = "-";
  document.getElementById("finalPred").textContent = "-";
  document.getElementById("xaiGrid").classList.add("hidden");
  document.getElementById("xaiLoading").classList.add("hidden");
  document.getElementById("wrongFeedback").classList.add("hidden");
  document.getElementById("feedbackSuccess").classList.add("hidden");
  updateStatus("System ready");
  
  window.currentResult = null;
  window.currentImageBase64 = null;
  window.currentImageForMismatch = null;
  window.feedbackSubmitted = false;
  window.xaiGenerating = false;
}

function showResult(data) {
  console.log("Showing result:", data);
  hideLoading();
  document.getElementById("error").classList.add("hidden");
  document.getElementById("result").classList.remove("hidden");
  document.getElementById("xaiSection").classList.remove("hidden");
  document.getElementById("feedbackSection").classList.remove("hidden");
  
  window.currentResult = data;
  
  // Store the image URL for mismatch detection
  if (data.imageUrl) {
    window.currentImageForMismatch = data.imageUrl;
    updateMismatchImagePreview();
    // Fetch as base64 for feedback
    fetchImageAsBase64(data.imageUrl);
  }
  
  const verdict = data.verdict || "UNKNOWN";
  const confidence = data.confidence || 0;
  const isFake = verdict === "FAKE";
  
  const verdictEl = document.getElementById("verdict");
  verdictEl.textContent = `${verdict} - ${Math.round(confidence)}%`;
  verdictEl.className = `verdict-value ${isFake ? "fake" : "real"}`;
  
  const confidenceFill = document.getElementById("confidenceFill");
  confidenceFill.style.width = `${confidence}%`;
  confidenceFill.className = `confidence-fill ${isFake ? "fake" : "real"}`;
  
  if (data.imageUrl) {
    document.getElementById("original").src = addCacheBust(data.imageUrl);
  }
  
  // Update the three column grid
  const effValue = document.getElementById("effPred");
  effValue.textContent = `${data.efficientnet_prediction || "N/A"} (${Math.round(data.efficientnet_confidence || 0)}%)`;
  effValue.className = `grid-value ${(data.efficientnet_prediction || "").toLowerCase() === "fake" ? "fake" : "real"}`;
  
  const vitValue = document.getElementById("vitPred");
  vitValue.textContent = `${data.vit_prediction || "N/A"} (${Math.round(data.vit_confidence || 0)}%)`;
  vitValue.className = `grid-value ${(data.vit_prediction || "").toLowerCase() === "fake" ? "fake" : "real"}`;
  
  const finalValue = document.getElementById("finalPred");
  finalValue.textContent = `${verdict} (${Math.round(confidence)}%)`;
  finalValue.className = `grid-value ${isFake ? "fake" : "real"}`;
  
  const generateBtn = document.getElementById("generateXaiBtn");
  generateBtn.disabled = false;
  generateBtn.textContent = "Generate Explanations";
  generateBtn.className = isFake ? "btn-danger btn-full" : "btn-success btn-full";
  
  document.getElementById("xaiGrid").classList.add("hidden");
  document.getElementById("xaiLoading").classList.add("hidden");
  document.getElementById("wrongFeedback").classList.add("hidden");
  document.getElementById("feedbackSuccess").classList.add("hidden");
  window.feedbackSubmitted = false;
  
  updateStatus(`Analysis complete: ${verdict} (${Math.round(confidence)}% confidence)`);
}

function fetchImageAsBase64(imageUrl) {
  fetch(imageUrl)
    .then(response => response.blob())
    .then(blob => {
      const reader = new FileReader();
      reader.onloadend = () => { window.currentImageBase64 = reader.result; };
      reader.readAsDataURL(blob);
    })
    .catch(err => console.error("Failed to fetch image:", err));
}

// ================== XAI FUNCTIONS ==================

function showXaiModal(imageSrc, title) {
  const modal = document.createElement('div');
  modal.style.cssText = `
    position: fixed; top: 0; left: 0; width: 100%; height: 100%;
    background: rgba(0,0,0,0.85); display: flex; justify-content: center;
    align-items: center; z-index: 10001; cursor: pointer;
  `;
  const content = document.createElement('div');
  content.style.cssText = `
    background: white; border-radius: 12px; max-width: 90%; max-height: 90%;
    overflow: auto; cursor: default;
  `;
  const header = document.createElement('div');
  header.style.cssText = `
    padding: 12px 16px; background: #1a56db; color: white;
    font-weight: 600; display: flex; justify-content: space-between;
    align-items: center;
  `;
  header.innerHTML = `<span>${title}</span><span style="cursor:pointer; font-size:20px;">&times;</span>`;
  const img = document.createElement('img');
  img.src = imageSrc;
  img.style.cssText = "max-width:100%; max-height:70vh; display:block; margin:16px;";
  content.appendChild(header);
  content.appendChild(img);
  modal.appendChild(content);
  document.body.appendChild(modal);
  
  const close = () => modal.remove();
  header.querySelector('span:last-child').onclick = close;
  modal.onclick = (e) => { if (e.target === modal) close(); };
}

function showXAI(xaiData, predictions, confidenceScores) {
  document.getElementById("xaiLoading").classList.add("hidden");
  const generateBtn = document.getElementById("generateXaiBtn");
  generateBtn.disabled = false;
  generateBtn.textContent = "Regenerate Explanations";
  window.xaiGenerating = false;
  
  const xaiGrid = document.getElementById("xaiGrid");
  xaiGrid.classList.remove("hidden");
  
  const baseUrl = "http://127.0.0.1:8000";
  
  const xaiMap = [
    { img: document.getElementById("cnn_gradcam"), url: xaiData?.cnn_gradcam?.url, title: "CNN Grad-CAM" },
    { img: document.getElementById("vit_gradcam"), url: xaiData?.vit_gradcam?.url, title: "ViT Grad-CAM" },
    { img: document.getElementById("cnn_features"), url: xaiData?.cnn_features?.url, title: "CNN Feature Analysis" },
    { img: document.getElementById("vit_features"), url: xaiData?.vit_features?.url, title: "ViT Feature Analysis" }
  ];
  
  xaiMap.forEach(({ img, url, title }) => {
    if (img && url) {
      const fullUrl = url.startsWith('http') ? url : baseUrl + url;
      img.src = addCacheBust(fullUrl);
      img.parentElement.onclick = () => showXaiModal(addCacheBust(fullUrl), title);
    }
  });
  
  updateStatus("Explanations generated successfully");
}

// ================== PRODUCT TYPE FUNCTIONS ==================

function detectProductTypeFromDescription(description) {
  if (!description) return null;
  const lowerDesc = description.toLowerCase();
  
  const shoeKeywords = ['shoe', 'shoes', 'sneaker', 'sneakers', 'boot', 'boots', 'footwear', 'running', 'basketball', 'tennis', 'soccer', 'football', 'hiking', 'athletic', 'sports', 'trainer', 'trainers'];
  const watchKeywords = ['watch', 'watches', 'wristwatch', 'timepiece', 'chronograph', 'smartwatch', 'smart watch', 'apple watch', 'samsung watch', 'digital watch', 'analog watch'];
  
  for (const keyword of watchKeywords) {
    if (lowerDesc.includes(keyword)) return 'watch';
  }
  for (const keyword of shoeKeywords) {
    if (lowerDesc.includes(keyword)) return 'shoe';
  }
  return null;
}

function formatProductTypeForDisplay(productType) {
  if (!productType) return "Unknown";
  const lowerType = productType.toLowerCase();
  if (lowerType === 'shoe' || lowerType.includes('shoe') || lowerType.includes('sneaker') || lowerType.includes('boot')) {
    return 'Shoe / Footwear';
  } else if (lowerType === 'watch' || lowerType.includes('watch')) {
    return 'Watch / Timepiece';
  }
  return productType.charAt(0).toUpperCase() + productType.slice(1);
}

function getMatchExplanation(score) {
  if (score >= 0.8) return { rating: 'Excellent Match', description: 'The product matches the description very well.', color: '#059669' };
  if (score >= 0.6) return { rating: 'Good Match', description: 'The product generally matches the description.', color: '#3b82f6' };
  if (score >= 0.4) return { rating: 'Moderate Match', description: 'Some elements match, but there are differences.', color: '#d97706' };
  if (score >= 0.2) return { rating: 'Poor Match', description: 'The product shows significant differences.', color: '#ea580c' };
  return { rating: 'Very Poor Match', description: 'The product does not match the description at all.', color: '#dc2626' };
}

// ================== MISMATCH FUNCTIONS ==================

function updateMismatchImagePreview() {
  let imageSrc = null;
  let imageInfo = '';
  
  if (window.currentImageForMismatch) {
    imageSrc = window.currentImageForMismatch;
    imageInfo = 'Selected image for analysis';
  }
  
  const preview = document.getElementById("mismatchImagePreview");
  if (imageSrc) {
    document.getElementById("mismatchImage").src = addCacheBust(imageSrc);
    document.getElementById("mismatchImageInfo").textContent = imageInfo;
    preview.classList.remove("hidden");
  } else {
    preview.classList.add("hidden");
  }
}

function showMismatchResult(result, imageUrl, description) {
  console.log("Showing mismatch result:", result);
  document.getElementById("mismatchLoading").classList.add("hidden");
  document.getElementById("mismatchResult").classList.remove("hidden");
  
  const risk = result.risk_score || 0;
  const verdict = result.verdict || "UNKNOWN";
  const isHighRisk = risk >= 60;
  
  const verdictEl = document.getElementById("mismatchVerdict");
  verdictEl.textContent = verdict;
  verdictEl.className = `verdict-value ${isHighRisk ? "fake" : "real"}`;
  
  const riskFill = document.getElementById("riskFill");
  riskFill.style.width = `${risk}%`;
  riskFill.className = `confidence-fill ${isHighRisk ? "fake" : "real"}`;
  document.getElementById("riskScore").textContent = risk;
  
  const matchScore = result.match_score || 0.5;
  const matchInfo = getMatchExplanation(matchScore);
  document.getElementById("matchValue").textContent = matchScore.toFixed(2);
  document.getElementById("matchLabel").textContent = matchInfo.rating;
  document.getElementById("matchDescription").textContent = matchInfo.description;
  
  if (result.image_features) {
    document.getElementById("imageProductType").textContent = formatProductTypeForDisplay(result.image_features.product_type);
    if (result.image_features.color_analysis?.colors?.length > 0) {
      document.getElementById("imageColors").textContent = result.image_features.color_analysis.colors.map(c => `${c.name} (${c.percentage}%)`).join(', ');
    }
  }
  if (result.text_features) {
    document.getElementById("textProductType").textContent = formatProductTypeForDisplay(result.text_features.product_type);
    document.getElementById("textColor").textContent = result.text_features.color || "Not specified";
  }
  
  let itemsHtml = '';
  if (result.mismatches?.length) {
    result.mismatches.forEach(m => { itemsHtml += `<div class="mismatch-item error"><span>✗</span><span>${m}</span></div>`; });
  }
  if (result.warnings?.length) {
    result.warnings.forEach(w => { itemsHtml += `<div class="mismatch-item warning"><span>⚠</span><span>${w}</span></div>`; });
  }
  if (!itemsHtml) {
    itemsHtml = `<div class="mismatch-item success"><span>✓</span><span>No issues detected</span></div>`;
  }
  document.getElementById("mismatchItems").innerHTML = itemsHtml;
  
  updateAnalysisGrids(result);
  updateStatus("Mismatch analysis complete");
}

function updateAnalysisGrids(result) {
  // Color Analysis
  if (result.image_features?.color_analysis?.colors?.length) {
    let html = '';
    result.image_features.color_analysis.colors.forEach(c => {
      let swatchColor = '#808080';
      if (c.rgb && c.rgb.length === 3) swatchColor = `rgb(${c.rgb[0]}, ${c.rgb[1]}, ${c.rgb[2]})`;
      html += `<div class="color-item"><div class="color-swatch" style="background:${swatchColor};"></div><span>${c.name}</span><span style="margin-left:auto;">${c.percentage}%</span></div>`;
    });
    document.getElementById("colorAnalysisContent").innerHTML = html;
  } else {
    document.getElementById("colorAnalysisContent").innerHTML = '<span style="color:var(--text-secondary);">No color data available</span>';
  }
  
  // Quality Analysis
  if (result.image_features?.quality_metrics) {
    const q = result.image_features.quality_metrics;
    let fillClass = 'fair';
    if (q.quality_rating === 'Excellent') fillClass = 'excellent';
    else if (q.quality_rating === 'Good') fillClass = 'good';
    else if (q.quality_rating === 'Poor' || q.quality_rating === 'Very Poor') fillClass = 'poor';
    
    document.getElementById("qualityAnalysisContent").innerHTML = `
      <div class="quality-meter"><div class="quality-fill ${fillClass}" style="width:${q.quality_score}%"></div></div>
      <div style="display:flex; justify-content:space-between; font-size:11px;">
        <span>${q.quality_rating || 'Unknown'}</span>
        <span>${Math.round(q.quality_score || 0)}%</span>
      </div>
      <div style="font-size:10px; margin-top:6px;">${q.quality_description || ''}</div>
    `;
  } else {
    document.getElementById("qualityAnalysisContent").innerHTML = '<span style="color:var(--text-secondary);">No quality data available</span>';
  }
  
  // Background Analysis
  if (result.image_features?.background_analysis) {
    const bg = result.image_features.background_analysis;
    document.getElementById("backgroundAnalysisContent").innerHTML = `
      <div class="bg-item"><span>Type</span><span>${bg.background_type || 'Unknown'}</span></div>
      <div class="bg-item"><span>Product Photo</span><span>${bg.is_product_photo ? 'Yes' : 'No'}</span></div>
      <div class="bg-item"><span>Centered</span><span>${bg.product_centered_score || 0}%</span></div>
      <div style="font-size:10px; margin-top:6px;">${bg.assessment || ''}</div>
    `;
  } else {
    document.getElementById("backgroundAnalysisContent").innerHTML = '<span style="color:var(--text-secondary);">No background data available</span>';
  }
  
  // Product Details
  if (result.text_features) {
    const tf = result.text_features;
    let html = '';
    if (tf.brand) html += `<div class="bg-item"><span>Brand</span><span>${tf.brand}</span></div>`;
    if (tf.condition) html += `<div class="bg-item"><span>Condition</span><span>${tf.condition}</span></div>`;
    if (tf.size) html += `<div class="bg-item"><span>Size</span><span>${tf.size}</span></div>`;
    if (tf.price || tf.has_price) html += `<div class="bg-item"><span>Price</span><span>${tf.price || 'Mentioned'}</span></div>`;
    if (!html) html = '<span style="color:var(--text-secondary);">No product details extracted</span>';
    document.getElementById("productDetailsContent").innerHTML = html;
  } else {
    document.getElementById("productDetailsContent").innerHTML = '<span style="color:var(--text-secondary);">No product details extracted</span>';
  }
}

async function autoExtractProductDetails() {
  const mismatchLoading = document.getElementById("mismatchLoading");
  const mismatchLoadingText = document.getElementById("mismatchLoadingText");
  mismatchLoading.classList.remove("hidden");
  mismatchLoadingText.textContent = "Extracting product details from page...";
  
  try {
    const tabs = await chrome.tabs.query({ active: true, currentWindow: true });
    const results = await chrome.scripting.executeScript({
      target: { tabId: tabs[0].id },
      func: () => {
        function cleanText(text) {
          if (!text) return '';
          const noise = [/was removed from Shopping Cart\.?/gi, /Only \d+ left in stock\./gi, /Add to Cart/gi, /Buy Now/gi, /\d+ bought in past month/gi, /\d+ customer reviews?/gi, /\|/g, /•/g];
          let cleaned = text;
          noise.forEach(p => { cleaned = cleaned.replace(p, ' '); });
          return cleaned.replace(/\s+/g, ' ').trim();
        }
        
        const titleSelectors = ['#productTitle', '[class*="product-title"]', 'h1[class*="title"]', '[itemprop="name"]', 'h1'];
        let title = '';
        for (const sel of titleSelectors) {
          const el = document.querySelector(sel);
          if (el && el.textContent.trim()) { title = cleanText(el.textContent.trim()); break; }
        }
        if (!title) title = cleanText(document.title.replace(/\s*[|-]\s*Amazon.*$/i, ''));
        
        const priceSelectors = ['.a-price .a-offscreen', '[class*="price"]', '[itemprop="price"]', '.price', '.a-price-whole'];
        let price = '';
        for (const sel of priceSelectors) {
          const el = document.querySelector(sel);
          if (el) { price = cleanText(el.textContent.trim()); if (price) break; }
        }
        
        const brandSelectors = ['[class*="brand"]', '[itemprop="brand"]', '.brand', '#bylineInfo'];
        let brand = '';
        for (const sel of brandSelectors) {
          const el = document.querySelector(sel);
          if (el) { brand = cleanText(el.textContent.trim()).replace('Brand: ', '').replace('Visit the ', ''); if (brand && brand.length < 50) break; }
        }
        
        const colorSelectors = ['[class*="color"]', '#variation_color_name', '.selection', '[data-csa-c-color]', '[class*="swatch"]'];
        let color = '';
        for (const sel of colorSelectors) {
          const el = document.querySelector(sel);
          if (el) { color = cleanText(el.textContent.trim()).replace(/Color:?/i, ''); if (color && !color.match(/color/i) && color.length < 30) break; }
        }
        
        const sizeSelectors = ['[class*="size"]', '#variation_size_name', '.a-dropdown-prompt', '[data-csa-c-size]'];
        let size = '';
        for (const sel of sizeSelectors) {
          const el = document.querySelector(sel);
          if (el) { size = cleanText(el.textContent.trim()).replace(/Size:?/i, ''); if (size && /[\d]/.test(size)) break; }
        }
        
        const parts = [];
        if (title) parts.push(title);
        if (brand) parts.push(brand);
        if (color) parts.push(`Color: ${color}`);
        if (size) parts.push(`Size: ${size}`);
        if (price) parts.push(`Price: ${price}`);
        
        const mainImage = document.querySelector('#landingImage, #imgBlkFront, .a-dynamic-image, img[data-old-hires], .imgTagWrapper img')?.src || null;
        
        return { description: parts.join(' ') || title, mainImage, title, brand, color, size, price };
      }
    });
    
    if (results?.[0]?.result) {
      const pageDetails = results[0].result;
      if (pageDetails.description && pageDetails.description.length > 10) {
        document.getElementById("descriptionInput").value = pageDetails.description;
        updateStatus("Product details extracted successfully");
      }
      if (pageDetails.mainImage) {
        window.currentImageForMismatch = pageDetails.mainImage;
        updateMismatchImagePreview();
      }
    } else {
      updateStatus("Could not extract product details", false, true);
    }
  } catch (err) {
    console.error("Auto-extract error:", err);
    updateStatus("Extraction failed", true);
  } finally {
    mismatchLoading.classList.add("hidden");
  }
}

// ================== EVENT HANDLERS ==================

document.getElementById("testBtn").addEventListener("click", async () => {
  showLoading("Testing API connection...");
  try {
    const response = await fetch("http://127.0.0.1:8000/health");
    if (response.ok) {
      updateStatus("API connected");
      // Check if we have a stored result from image hover
      chrome.storage.local.get(['lastResult', 'pendingImageUrl'], (data) => {
        if (data.lastResult) {
          setTimeout(() => showResult(data.lastResult), 300);
        } else if (data.pendingImageUrl) {
          // Analyze the pending image
          analyzeImageFromUrl(data.pendingImageUrl);
        } else {
          hideLoading();
          updateStatus("System ready - Click on an image badge to analyze");
        }
      });
    } else {
      showError(`API Error: ${response.status}`);
    }
  } catch (err) {
    showError("Cannot connect to API. Make sure it's running on port 8000");
  }
});

async function analyzeImageFromUrl(imageUrl) {
  showLoading("Analyzing image...");
  try {
    const response = await fetch(imageUrl);
    const blob = await response.blob();
    const reader = new FileReader();
    reader.onloadend = () => {
      chrome.runtime.sendMessage({
        action: "analyzeImage",
        imageUrl: imageUrl,
        imageBase64: reader.result
      }, (resp) => {
        if (resp?.success && resp.result) {
          showResult(resp.result);
          chrome.storage.local.set({ lastResult: resp.result, pendingImageUrl: null });
        } else {
          showError(resp?.error || "Analysis failed");
        }
      });
    };
    reader.readAsDataURL(blob);
  } catch (err) {
    showError("Failed to load image: " + err.message);
  }
}

document.getElementById("clearBtn").addEventListener("click", clearResults);

document.getElementById("generateXaiBtn").addEventListener("click", async () => {
  if (!window.currentResult || !window.currentResult.imageUrl) {
    showError("No image to analyze");
    return;
  }
  if (window.xaiGenerating) return;
  
  window.xaiGenerating = true;
  const generateBtn = document.getElementById("generateXaiBtn");
  generateBtn.disabled = true;
  generateBtn.textContent = "Generating...";
  document.getElementById("xaiLoading").classList.remove("hidden");
  document.getElementById("xaiGrid").classList.add("hidden");
  updateStatus("Generating explanations...");
  
  try {
    chrome.storage.local.get(['lastXAIResult'], (storage) => {
      if (storage.lastXAIResult && storage.lastXAIResult.imageUrl === window.currentResult.imageUrl) {
        showXAI(storage.lastXAIResult.xai, storage.lastXAIResult.predictions, storage.lastXAIResult.confidence_scores);
        window.xaiGenerating = false;
        return;
      }
    });
    
    const response = await fetch(window.currentResult.imageUrl);
    const blob = await response.blob();
    const reader = new FileReader();
    reader.onloadend = () => {
      chrome.runtime.sendMessage({
        action: "generateXAI",
        imageUrl: window.currentResult.imageUrl,
        imageBase64: reader.result
      }, (resp) => {
        if (resp?.success && resp.result) {
          chrome.storage.local.set({ 
            lastXAIResult: { 
              imageUrl: window.currentResult.imageUrl, 
              xai: resp.result.xai_visualizations, 
              predictions: resp.result.predictions, 
              confidence_scores: resp.result.confidence_scores, 
              timestamp: Date.now() 
            } 
          });
          showXAI(resp.result.xai_visualizations, resp.result.predictions, resp.result.confidence_scores);
        } else {
          showError("Failed to generate explanations");
          window.xaiGenerating = false;
          generateBtn.disabled = false;
          generateBtn.textContent = "Generate Explanations";
          document.getElementById("xaiLoading").classList.add("hidden");
        }
      });
    };
    reader.readAsDataURL(blob);
  } catch (err) {
    showError("Failed to generate explanations: " + err.message);
    window.xaiGenerating = false;
    generateBtn.disabled = false;
    generateBtn.textContent = "Generate Explanations";
    document.getElementById("xaiLoading").classList.add("hidden");
  }
});

// Feedback handlers
document.getElementById("correctBtn").addEventListener("click", () => {
  if (window.feedbackSubmitted) { showError("Feedback already submitted"); return; }
  if (!window.currentResult) { showError("No image to provide feedback for"); return; }
  
  chrome.runtime.sendMessage({
    action: "submitFeedback",
    feedback: { 
      imageUrl: window.currentResult.imageUrl, 
      imageBase64: window.currentImageBase64, 
      predictedLabel: window.currentResult.verdict, 
      trueLabel: window.currentResult.verdict, 
      confidence: window.currentResult.confidence 
    }
  }, (response) => {
    if (response?.success) {
      window.feedbackSubmitted = true;
      const successDiv = document.getElementById("feedbackSuccess");
      successDiv.textContent = "Thank you for confirming!";
      successDiv.classList.remove("hidden");
      setTimeout(() => successDiv.classList.add("hidden"), 3000);
      updateStatus("Feedback recorded");
    } else {
      showError("Failed to submit feedback");
    }
  });
});

document.getElementById("wrongBtn").addEventListener("click", () => {
  if (window.feedbackSubmitted) { showError("Feedback already submitted"); return; }
  if (!window.currentResult) { showError("No image to provide feedback for"); return; }
  document.getElementById("wrongFeedback").classList.remove("hidden");
  document.getElementById("realBtn").classList.remove("active");
  document.getElementById("fakeBtn").classList.remove("active");
});

document.getElementById("realBtn").addEventListener("click", () => {
  document.getElementById("realBtn").classList.add("active");
  document.getElementById("fakeBtn").classList.remove("active");
});

document.getElementById("fakeBtn").addEventListener("click", () => {
  document.getElementById("fakeBtn").classList.add("active");
  document.getElementById("realBtn").classList.remove("active");
});

document.getElementById("submitFeedbackBtn").addEventListener("click", () => {
  const realActive = document.getElementById("realBtn").classList.contains("active");
  const fakeActive = document.getElementById("fakeBtn").classList.contains("active");
  const trueLabel = realActive ? "REAL" : fakeActive ? "FAKE" : null;
  
  if (!trueLabel) { showError("Please select the correct label"); return; }
  
  chrome.runtime.sendMessage({
    action: "submitFeedback",
    feedback: { 
      imageUrl: window.currentResult.imageUrl, 
      imageBase64: window.currentImageBase64, 
      predictedLabel: window.currentResult.verdict, 
      trueLabel: trueLabel, 
      confidence: window.currentResult.confidence 
    }
  }, (response) => {
    if (response?.success) {
      window.feedbackSubmitted = true;
      const successDiv = document.getElementById("feedbackSuccess");
      successDiv.textContent = "Thank you for your feedback!";
      successDiv.classList.remove("hidden");
      document.getElementById("wrongFeedback").classList.add("hidden");
      setTimeout(() => successDiv.classList.add("hidden"), 3000);
      updateStatus("Feedback recorded");
    } else {
      showError("Failed to submit feedback");
    }
  });
});

// Mismatch handlers
document.getElementById("analyzeMismatchBtn").addEventListener("click", async () => {
  const description = document.getElementById("descriptionInput").value.trim();
  if (!description || description.length < 3) {
    showError("Please enter a product description");
    return;
  }
  if (!window.currentImageForMismatch) {
    showError("No image selected. Click on an image badge first or extract from page.");
    return;
  }
  
  const mismatchLoading = document.getElementById("mismatchLoading");
  const mismatchLoadingText = document.getElementById("mismatchLoadingText");
  mismatchLoading.classList.remove("hidden");
  mismatchLoadingText.textContent = "Analyzing mismatch...";
  document.getElementById("mismatchResult").classList.add("hidden");
  
  try {
    const response = await fetch(window.currentImageForMismatch);
    const blob = await response.blob();
    const reader = new FileReader();
    reader.onloadend = () => {
      chrome.runtime.sendMessage({
        action: "detectMismatch",
        imageUrl: window.currentImageForMismatch,
        description: description,
        imageBase64: reader.result
      }, (resp) => {
        mismatchLoading.classList.add("hidden");
        if (resp?.success) {
          showMismatchResult(resp.result, window.currentImageForMismatch, description);
        } else {
          showError(resp?.error || "Mismatch detection failed");
        }
      });
    };
    reader.readAsDataURL(blob);
  } catch (err) {
    mismatchLoading.classList.add("hidden");
    showError("Failed to load image: " + err.message);
  }
});

document.getElementById("clearMismatchBtn").addEventListener("click", () => {
  document.getElementById("descriptionInput").value = "";
  document.getElementById("mismatchResult").classList.add("hidden");
  document.getElementById("mismatchImagePreview").classList.add("hidden");
  window.currentImageForMismatch = null;
  updateStatus("Ready");
});

document.getElementById("autoExtractBtn").addEventListener("click", autoExtractProductDetails);

// Storage listeners
chrome.storage.onChanged.addListener((changes, namespace) => {
  if (namespace === 'local') {
    if (changes.lastResult?.newValue) {
      showResult(changes.lastResult.newValue);
    }
    if (changes.lastXAIResult?.newValue && window.currentResult?.imageUrl === changes.lastXAIResult.newValue.imageUrl) {
      showXAI(changes.lastXAIResult.newValue.xai, changes.lastXAIResult.newValue.predictions, changes.lastXAIResult.newValue.confidence_scores);
    }
    if (changes.lastMismatchResult?.newValue) {
      showMismatchResult(changes.lastMismatchResult.newValue, changes.lastMismatchResult.newValue.imageUrl, changes.lastMismatchResult.newValue.description);
    }
    if (changes.pendingImageUrl?.newValue) {
      window.currentImageForMismatch = changes.pendingImageUrl.newValue;
      updateMismatchImagePreview();
      // Auto-analyze if API is connected
      chrome.storage.local.get(['lastResult'], (data) => {
        if (!data.lastResult && changes.pendingImageUrl.newValue) {
          analyzeImageFromUrl(changes.pendingImageUrl.newValue);
        }
      });
    }
  }
});

// Message listener
chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (message.action === "showResult") {
    showResult(message);
  } else if (message.action === "showError") {
    showError(message.error);
  } else if (message.action === "xaiGenerated" && window.currentResult?.imageUrl === message.imageUrl) {
    setTimeout(() => showXAI(message.xai, message.predictions, message.confidence_scores), 300);
  } else if (message.action === "mismatchResult") {
    showMismatchResult(message.result, message.result.imageUrl, message.result.description);
  } else if (message.action === "imageSelected") {
    window.currentImageForMismatch = message.imageUrl;
    updateMismatchImagePreview();
    if (message.autoAnalyze) {
      analyzeImageFromUrl(message.imageUrl);
    }
  }
  return true;
});

// Initialize
document.addEventListener("DOMContentLoaded", () => {
  clearResults();
  updateMismatchImagePreview();
  
  // Check for pending image from hover
  chrome.storage.local.get(['lastResult', 'pendingImageUrl', 'autoAnalyzePending'], (storage) => {
    if (storage.lastResult) {
      showResult(storage.lastResult);
    } else if (storage.pendingImageUrl && storage.autoAnalyzePending) {
      window.currentImageForMismatch = storage.pendingImageUrl;
      updateMismatchImagePreview();
      analyzeImageFromUrl(storage.pendingImageUrl);
      chrome.storage.local.remove(['autoAnalyzePending']);
    }
  });
  
  // Auto-test connection on load
  setTimeout(() => document.getElementById("testBtn").click(), 300);
});