// Background service worker
console.log("ImageGuard background service worker started with enhanced extraction");

let activeRequests = new Map();
let selectedText = '';
let selectedImage = null;

// ================== ENHANCED PRODUCT TYPE DETECTION ==================

function detectProductTypeFromText(text) {
  if (!text) return null;
  
  const lowerText = text.toLowerCase();
  
  const shoeKeywords = [
    'running shoes', 'running shoe', 'jogging shoes', 'athletic shoes',
    'basketball shoes', 'tennis shoes', 'football shoes', 'soccer shoes',
    'hiking shoes', 'walking shoes', 'work boots', 'safety boots',
    'winter boots', 'snow boots', 'rain boots', 'dress shoes',
    'casual shoes', 'sports shoes', 'gym shoes', 'training shoes',
    'canvas shoes', 'oxfords', 'loafers', 'high heels', 'stilettos',
    'air max', 'air force', 'jordans', 'yeezy', 'ultraboost',
    'converse', 'vans', 'timberlands', 'sneaker', 'sneakers',
    'boot', 'boots', 'sandals', 'shoe', 'shoes', 'footwear'
  ];
  
  const watchKeywords = [
    'smart watch', 'smartwatch', 'apple watch', 'samsung galaxy watch',
    'digital watch', 'analog watch', 'diver watch', 'diving watch',
    'pilot watch', 'dress watch', 'sports watch', 'luxury watch',
    'automatic watch', 'mechanical watch', 'quartz watch',
    'chronograph watch', 'fitness tracker', 'rolex', 'omega',
    'tag heuer', 'seiko', 'citizen', 'casio', 'fossil', 'timex',
    'wristwatch', 'wrist watch', 'timepiece', 'watch', 'watches'
  ];
  
  for (const keyword of shoeKeywords) {
    if (lowerText.includes(keyword)) return 'shoe';
  }
  
  for (const keyword of watchKeywords) {
    if (lowerText.includes(keyword)) return 'watch';
  }
  
  return null;
}

// ================== ADVANCED TEXT CLEANING ==================

function cleanEcommerceText(text) {
  if (!text) return '';
  
  const noisePatterns = [
    /was removed from Shopping Cart\.?/gi,
    /was already removed from Shopping Cart\.?/gi,
    /Moved to Saved for later/gi,
    /Delete Failed\. Try again/gi,
    /Update failed\. Try again/gi,
    /We couldn’t save this item for later; try again/gi,
    /Quantity is \d+Updating quantity\d+\d+ Qty: Update\./gi,
    /Only \d+ left in stock\./gi,
    /\.{2,}/g,
    /See All.*?$/gim,
    /Cashback \([^)]+\):.*?(?=\n|$)/gim,
    /Get \d+% back.*?(?=\n|$)/gim,
    /EMI options? available/gi,
    /Free Shipping/gi,
    /Delivery by/gi,
    /Ships to/gi,
    /Add to Cart/gi,
    /Buy Now/gi,
    /In stock/gi,
    /Out of stock/gi,
    /Usually dispatched/gi,
    /Temporarily out of stock/gi,
    /New \(\d+\)/gi,
    /Used \(\d+\)/gi,
    /Refurbished \(\d+\)/gi,
    /\d+ bought in past month/gi,
    /\d+ sold in past month/gi,
    /\d+ customer reviews?/gi,
    /\d+ answered questions?/gi,
    /See more/gi,
    /Show more/gi,
    /Read more/gi,
    /\|/g,
    /•/g,
    /›/g,
    /★/g,
    /☆/g,
    /✓/g,
    /✗/g,
    /✔/g,
    /®/g,
    /™/g,
    /©/g
  ];
  
  let cleaned = text;
  for (const pattern of noisePatterns) {
    cleaned = cleaned.replace(pattern, ' ');
  }
  
  cleaned = cleaned.replace(/\s+/g, ' ').trim();
  
  if (cleaned.length > 1500) {
    cleaned = cleaned.substring(0, 1500) + '...';
  }
  
  return cleaned;
}

// ================== ACCURATE COLOR DETECTION ==================

// Comprehensive color mapping with RGB values for accurate detection
const ACCURATE_COLOR_MAP = {
  'Red': {
    rgb: [255, 0, 0],
    variants: ['red', 'crimson', 'scarlet', 'ruby', 'cherry', 'wine', 'burgundy', 'maroon', 'candy red', 'tomato', 'vermilion', 'carmine', 'rouge', 'claret', 'cardinal'],
    range: { hue: [0, 10, 350, 360], sat: [50, 100], val: [50, 100] }
  },
  'Orange': {
    rgb: [255, 165, 0],
    variants: ['orange', 'tangerine', 'coral', 'peach', 'apricot', 'rust', 'burnt orange', 'pumpkin', 'mandarin', 'amber', 'saffron', 'ginger', 'sunset', 'flame'],
    range: { hue: [11, 30], sat: [50, 100], val: [50, 100] }
  },
  'Yellow': {
    rgb: [255, 255, 0],
    variants: ['yellow', 'gold', 'mustard', 'lemon', 'honey', 'sunflower', 'canary', 'amber', 'flax', 'butter', 'daffodil', 'banana'],
    range: { hue: [31, 60], sat: [50, 100], val: [50, 100] }
  },
  'Green': {
    rgb: [0, 255, 0],
    variants: ['green', 'emerald', 'forest green', 'olive', 'mint', 'sage', 'khaki', 'army green', 'lime', 'chartreuse', 'sea green', 'teal', 'jade', 'viridian', 'pine'],
    range: { hue: [61, 140], sat: [50, 100], val: [50, 100] }
  },
  'Blue': {
    rgb: [0, 0, 255],
    variants: ['blue', 'navy', 'royal blue', 'sky blue', 'denim', 'indigo', 'cobalt', 'sapphire', 'teal', 'turquoise', 'midnight blue', 'azure', 'cerulean', 'aqua', 'cyan'],
    range: { hue: [141, 260], sat: [50, 100], val: [50, 100] }
  },
  'Purple': {
    rgb: [128, 0, 128],
    variants: ['purple', 'violet', 'lavender', 'plum', 'lilac', 'mauve', 'orchid', 'magenta', 'amethyst', 'eggplant', 'grape', 'heather'],
    range: { hue: [261, 320], sat: [50, 100], val: [50, 100] }
  },
  'Pink': {
    rgb: [255, 192, 203],
    variants: ['pink', 'rose', 'fuchsia', 'hot pink', 'salmon', 'coral', 'blush', 'magenta', 'bubblegum', 'cotton candy', 'peony', 'cherry blossom'],
    range: { hue: [321, 349], sat: [40, 100], val: [60, 100] }
  },
  'Brown': {
    rgb: [139, 69, 19],
    variants: ['brown', 'tan', 'beige', 'khaki', 'camel', 'chocolate', 'espresso', 'chestnut', 'cognac', 'coffee', 'caramel', 'taupe', 'saddle', 'mahogany', 'walnut'],
    range: { hue: [10, 30], sat: [40, 80], val: [30, 60] }
  },
  'Gray': {
    rgb: [128, 128, 128],
    variants: ['gray', 'grey', 'charcoal', 'slate', 'silver', 'platinum', 'smoke', 'anthracite', 'pewter', 'ash', 'dove'],
    range: { hue: [0, 360], sat: [0, 15], val: [30, 80] }
  },
  'Black': {
    rgb: [0, 0, 0],
    variants: ['black', 'ebony', 'onyx', 'jet black', 'midnight', 'obsidian', 'coal', 'ink', 'raven', 'pitch black'],
    range: { hue: [0, 360], sat: [0, 30], val: [0, 25] }
  },
  'White': {
    rgb: [255, 255, 255],
    variants: ['white', 'snow', 'ivory', 'cream', 'off-white', 'pearl', 'chalk', 'pure white', 'alabaster', 'eggshell', 'vanilla'],
    range: { hue: [0, 360], sat: [0, 20], val: [85, 100] }
  },
  'Cyan': {
    rgb: [0, 255, 255],
    variants: ['cyan', 'aqua', 'turquoise', 'teal', 'ice blue', 'electric blue'],
    range: { hue: [141, 200], sat: [60, 100], val: [60, 100] }
  },
  'Magenta': {
    rgb: [255, 0, 255],
    variants: ['magenta', 'fuchsia', 'hot pink', 'neon pink'],
    range: { hue: [321, 340], sat: [70, 100], val: [70, 100] }
  }
};

function rgbToHsv(r, g, b) {
  r /= 255;
  g /= 255;
  b /= 255;
  
  const max = Math.max(r, g, b);
  const min = Math.min(r, g, b);
  const diff = max - min;
  
  let h = 0;
  const v = max;
  const s = max === 0 ? 0 : diff / max;
  
  if (diff !== 0) {
    if (max === r) {
      h = 60 * (((g - b) / diff) % 6);
    } else if (max === g) {
      h = 60 * (((b - r) / diff) + 2);
    } else {
      h = 60 * (((r - g) / diff) + 4);
    }
  }
  
  if (h < 0) h += 360;
  
  return { h: Math.round(h), s: Math.round(s * 100), v: Math.round(v * 100) };
}

function getColorNameFromRgb(r, g, b) {
  const hsv = rgbToHsv(r, g, b);
  
  let bestMatch = 'Gray';
  let bestScore = 0;
  
  for (const [colorName, colorData] of Object.entries(ACCURATE_COLOR_MAP)) {
    let score = 0;
    const range = colorData.range;
    
    // Hue matching
    if (range.hue[0] <= range.hue[1]) {
      if (hsv.h >= range.hue[0] && hsv.h <= range.hue[1]) {
        score += 50;
      }
    } else {
      // Wrap around for red (0-10 and 350-360)
      if (hsv.h >= range.hue[0] || hsv.h <= range.hue[1]) {
        score += 50;
      }
    }
    
    // Saturation matching
    if (hsv.s >= range.sat[0] && hsv.s <= range.sat[1]) {
      score += 30;
    } else if (Math.abs(hsv.s - range.sat[0]) < 20) {
      score += 15;
    }
    
    // Value/Brightness matching
    if (hsv.v >= range.val[0] && hsv.v <= range.val[1]) {
      score += 20;
    } else if (Math.abs(hsv.v - range.val[0]) < 15) {
      score += 10;
    }
    
    // Special handling for grayscale
    if (colorName === 'Gray' && hsv.s < 20) {
      score += 40;
    }
    if (colorName === 'Black' && hsv.v < 25) {
      score += 40;
    }
    if (colorName === 'White' && hsv.v > 85 && hsv.s < 20) {
      score += 40;
    }
    
    if (score > bestScore) {
      bestScore = score;
      bestMatch = colorName;
    }
  }
  
  return bestMatch;
}

// Advanced color extraction from image data
function extractAccurateColors(imageData, maxColors = 5) {
  const pixels = [];
  const step = 5; // Sample every 5th pixel for performance
  
  // Collect sampled pixels
  for (let i = 0; i < imageData.data.length; i += 4 * step) {
    const r = imageData.data[i];
    const g = imageData.data[i + 1];
    const b = imageData.data[i + 2];
    const a = imageData.data[i + 3];
    
    // Skip transparent or very dark/light background pixels
    if (a < 128) continue;
    
    pixels.push({ r, g, b });
  }
  
  if (pixels.length === 0) return [];
  
  // Cluster similar colors using simple quantization
  const colorMap = new Map();
  
  for (const pixel of pixels) {
    // Quantize colors to reduce variation
    const quantizedR = Math.round(pixel.r / 25) * 25;
    const quantizedG = Math.round(pixel.g / 25) * 25;
    const quantizedB = Math.round(pixel.b / 25) * 25;
    const key = `${quantizedR},${quantizedG},${quantizedB}`;
    
    if (colorMap.has(key)) {
      colorMap.set(key, colorMap.get(key) + 1);
    } else {
      colorMap.set(key, 1);
    }
  }
  
  // Convert to array and sort by frequency
  const sortedColors = Array.from(colorMap.entries())
    .map(([key, count]) => {
      const [r, g, b] = key.split(',').map(Number);
      return { r, g, b, count };
    })
    .sort((a, b) => b.count - a.count);
  
  // Get top colors and map to names
  const topColors = [];
  const totalPixels = pixels.length;
  
  for (let i = 0; i < Math.min(maxColors, sortedColors.length); i++) {
    const color = sortedColors[i];
    const percentage = (color.count / totalPixels) * 100;
    
    // Only include colors that make up at least 3% of the image
    if (percentage >= 3) {
      const colorName = getColorNameFromRgb(color.r, color.g, color.b);
      
      // Merge duplicate color names
      const existing = topColors.find(c => c.name === colorName);
      if (existing) {
        existing.percentage += percentage;
      } else {
        topColors.push({
          name: colorName,
          percentage: Math.round(percentage * 10) / 10,
          rgb: [color.r, color.g, color.b]
        });
      }
    }
  }
  
  // Sort by percentage descending
  topColors.sort((a, b) => b.percentage - a.percentage);
  
  return topColors;
}

// ================== ADVANCED PRODUCT EXTRACTION ==================

function extractProductFeaturesFromText(text) {
  const features = {
    product_type: null,
    color: null,
    brand: null,
    size: null,
    condition: null,
    has_price: false,
    price: null
  };
  
  if (!text) return features;
  
  const lowerText = text.toLowerCase();
  
  features.product_type = detectProductTypeFromText(text);
  
  // Brand detection
  const brandMap = {
    'Nike': ['nike', 'air jordan', 'air max', 'jordan', 'jordans', 'nike air'],
    'Adidas': ['adidas', 'originals', 'yeezy', 'ultraboost', 'boost', 'adidas originals'],
    'Puma': ['puma', 'puma suede'],
    'Converse': ['converse', 'all star', 'chuck taylor', 'converse chuck'],
    'Vans': ['vans', 'old skool', 'vans old skool'],
    'New Balance': ['new balance', 'nb', 'newbalance'],
    'Under Armour': ['under armour', 'under armor', 'ua'],
    'Skechers': ['skechers', 'skecher'],
    'Reebok': ['reebok', 'reebok classic'],
    'Timberland': ['timberland', 'timberlands', 'timberland pro'],
    'Dr. Martens': ['dr. martens', 'doc martens', 'drmartens'],
    'ASICS': ['asics', 'asics gel'],
    'Rolex': ['rolex', 'rolex submariner'],
    'Omega': ['omega', 'omega seamaster'],
    'Tag Heuer': ['tag heuer', 'tag', 'tagheuer'],
    'Seiko': ['seiko', 'seiko 5'],
    'Citizen': ['citizen', 'eco-drive'],
    'Casio': ['casio', 'g-shock', 'baby-g', 'casio edifice'],
    'Fossil': ['fossil', 'fossil gen'],
    'Timex': ['timex', 'timex expedition'],
    'Apple': ['apple watch', 'apple', 'i watch'],
    'Samsung': ['samsung galaxy watch', 'galaxy watch', 'samsung watch'],
    'Fitbit': ['fitbit', 'fitbit sense'],
    'Garmin': ['garmin', 'garmin fenix']
  };
  
  for (const [brand, keywords] of Object.entries(brandMap)) {
    for (const keyword of keywords) {
      if (lowerText.includes(keyword)) {
        features.brand = brand;
        break;
      }
    }
    if (features.brand) break;
  }
  
  // Size detection
  const sizePatterns = [
    /size[:\s]*([\d.]+(?:-\d+)?(?:\s*(?:US|UK|EU|CM))?)/i,
    /size\s*([\d.]+)\s*(?:US|UK|EU)?/i,
    /([\d.]+)\s*(?:US|UK|EU)\s*size/i,
    /([\d.]+)\s*(?:men|women|unisex|kids)/i,
    /shoe\s*size[:\s]*([\d.]+)/i,
    /([\d.]+)\s*mm\b/i,
    /size[:\s]*([SMLXL\s]+)/i,
    /size[:\s]*(\d+(?:\.\d+)?(?:\s*[-\/]\s*\d+(?:\.\d+)?)?)/
  ];
  
  for (const pattern of sizePatterns) {
    const match = text.match(pattern);
    if (match && match[1]) {
      features.size = match[1].trim();
      break;
    }
  }
  
  // Price detection
  const pricePatterns = [
    /[$₹€£]\s*([\d,]+(?:\.\d{2})?)/,
    /([\d,]+(?:\.\d{2})?)\s*(?:USD|EUR|GBP|INR)/i,
    /price[:\s]*[$₹€£]\s*([\d,]+(?:\.\d{2})?)/i,
    /MRP[:\s]*[$₹€£]\s*([\d,]+(?:\.\d{2})?)/i,
    /₹\s*([\d,]+(?:\.\d{2})?)/,
    /\$\s*([\d,]+(?:\.\d{2})?)/
  ];
  
  for (const pattern of pricePatterns) {
    const match = text.match(pattern);
    if (match) {
      features.has_price = true;
      features.price = match[0].trim();
      break;
    }
  }
  
  // Condition detection
  const conditionKeywords = {
    'New': ['new', 'brand new', 'unused', 'never worn', 'with tags', 'in box', 'sealed', 'authentic'],
    'Like New': ['like new', 'mint condition', 'excellent condition', 'as new', 'barely used'],
    'Used': ['used', 'pre-owned', 'second hand', 'worn', 'preloved', 'vintage', 'good condition'],
    'Good': ['good condition', 'fair condition', 'gently used', 'well maintained'],
    'Poor': ['poor condition', 'needs repair', 'worn out', 'damaged', 'defective']
  };
  
  for (const [condition, keywords] of Object.entries(conditionKeywords)) {
    for (const keyword of keywords) {
      if (lowerText.includes(keyword)) {
        features.condition = condition;
        break;
      }
    }
    if (features.condition) break;
  }
  
  return features;
}

// ================== ADVANCED PAGE EXTRACTION ==================

async function extractProductDetailsFromPage(tabId) {
  return new Promise((resolve, reject) => {
    chrome.scripting.executeScript({
      target: { tabId: tabId },
      func: () => {
        
        function superClean(text) {
          if (!text) return '';
          
          let cleaned = String(text);
          cleaned = cleaned.replace(/<[^>]*>/g, ' ');
          cleaned = cleaned.replace(/https?:\/\/[^\s]+\.(jpg|jpeg|png|gif|webp|svg)/gi, '');
          cleaned = cleaned.replace(/[\u{1F300}-\u{1F9FF}]/gu, '');
          cleaned = cleaned.replace(/[^\w\s\-:,.₹$€£()%/]/g, ' ');
          
          const noisePatterns = [
            /with \d+ percent savings/i, /-\d+% ₹[\d,]+/, /M\.R\.P\.?:?\s*₹[\d,]+/i,
            /deal price:?\s*₹[\d,]+/i, /you save:?\s*₹[\d,]+/i, /inclusive of all taxes/i,
            /free delivery/i, /free shipping/i, /cash on delivery/i, /emi available/i,
            /bank offer/i, /exchange offer/i, /no cost emi/i, /buy now/i, /add to cart/i,
            /only \d+ left in stock/i, /usually dispatched in/i, /sold by/i, /fulfilled by/i,
            /amazon's choice/i, /best seller/i, /\d+ bought in past month/i,
            /\d+ customer reviews/i, /visit the .*? store/i, /\|\s*/g, /•\s*/g, /›\s*/g,
            /★\s*/g, /☆\s*/g, /✓\s*/g, /✔\s*/g, /®/g, /™/g, /\s{2,}/g
          ];
          
          for (const pattern of noisePatterns) {
            cleaned = cleaned.replace(pattern, ' ');
          }
          
          cleaned = cleaned.replace(/\s+/g, ' ').trim();
          if (cleaned.length < 5 || /^[\d\s,.%₹]+$/.test(cleaned)) return '';
          if (cleaned.length > 300) cleaned = cleaned.substring(0, 300);
          
          return cleaned;
        }
        
        function extractCleanTitle() {
          const selectors = ['#productTitle', '#title', 'span#productTitle', '.a-size-large.product-title-word-break', 'h1#title', '[itemprop="name"]'];
          for (const selector of selectors) {
            try {
              const el = document.querySelector(selector);
              if (el) {
                let text = '';
                for (const node of el.childNodes) {
                  if (node.nodeType === Node.TEXT_NODE) text += node.textContent;
                }
                if (!text.trim()) text = el.textContent;
                text = superClean(text);
                if (text && text.length > 10 && text.length < 200) return text;
              }
            } catch(e) {}
          }
          let pageTitle = document.title;
          pageTitle = pageTitle.replace(/\s*[|\-•]\s*(Amazon|Flipkart|eBay|Myntra|Ajio|Walmart|Target).*$/i, '');
          return superClean(pageTitle) || '';
        }
        
        function extractCleanPrice() {
          const priceSelectors = ['.a-price .a-offscreen', '#priceblock_ourprice', '#priceblock_dealprice', '[itemprop="price"]', '.priceBlockBuyingPriceString'];
          for (const selector of priceSelectors) {
            try {
              const el = document.querySelector(selector);
              if (el) {
                const priceMatch = el.textContent.match(/[₹$€£]\s*([\d,]+(?:\.\d{2})?)/);
                if (priceMatch) return priceMatch[0];
              }
            } catch(e) {}
          }
          return '';
        }
        
        function extractCleanBrand() {
          const brandSelectors = ['#bylineInfo', '#brand', '[itemprop="brand"]', '.a-brand'];
          for (const selector of brandSelectors) {
            try {
              const el = document.querySelector(selector);
              if (el) {
                let text = el.textContent;
                text = text.replace(/Brand:?|Visit the|Store/gi, '');
                text = superClean(text);
                if (text && text.length > 1 && text.length < 30 && !text.match(/color|size|price/i)) return text;
              }
            } catch(e) {}
          }
          return '';
        }
        
        function extractCleanColor() {
          const colorSelectors = ['#variation_color_name', '.selection', '[data-csa-c-color]'];
          const colorNames = ['Black', 'White', 'Red', 'Blue', 'Green', 'Yellow', 'Purple', 'Pink', 'Orange', 'Brown', 'Gray', 'Navy', 'Teal', 'Olive'];
          for (const selector of colorSelectors) {
            try {
              const el = document.querySelector(selector);
              if (el) {
                let text = el.textContent;
                text = superClean(text);
                for (const color of colorNames) {
                  if (text.toLowerCase() === color.toLowerCase() || text.toLowerCase().includes(color.toLowerCase())) return color;
                }
              }
            } catch(e) {}
          }
          return '';
        }
        
        function extractCleanSize() {
          const sizeSelectors = ['#variation_size_name', '.a-dropdown-prompt', '[data-csa-c-size]'];
          for (const selector of sizeSelectors) {
            try {
              const el = document.querySelector(selector);
              if (el) {
                let text = el.textContent;
                text = superClean(text);
                const sizeMatch = text.match(/(\d+(?:\.\d+)?)/);
                if (sizeMatch && sizeMatch[1] > 0 && sizeMatch[1] < 20) return sizeMatch[1];
              }
            } catch(e) {}
          }
          return '';
        }
        
        function extractMainImage() {
          const imageSelectors = ['#landingImage', '#imgBlkFront', '.a-dynamic-image', 'img[data-old-hires]', '.imgTagWrapper img'];
          for (const selector of imageSelectors) {
            try {
              const el = document.querySelector(selector);
              if (el && el.src && el.src.startsWith('http') && !el.src.includes('icon') && !el.src.includes('logo')) return el.src;
            } catch(e) {}
          }
          return null;
        }
        
        const title = extractCleanTitle();
        const brand = extractCleanBrand();
        const color = extractCleanColor();
        const size = extractCleanSize();
        const price = extractCleanPrice();
        const mainImage = extractMainImage();
        
        const parts = [];
        if (title && title.length > 5) parts.push(title);
        if (brand && brand.length > 1) parts.push(`Brand: ${brand}`);
        if (color && color.length > 1) parts.push(`Color: ${color}`);
        if (size && size.length > 0) parts.push(`Size: ${size}`);
        if (price && price.length > 2) parts.push(`Price: ${price}`);
        
        let structuredDescription = parts.join(' | ');
        structuredDescription = structuredDescription.replace(/<[^>]*>/g, '');
        structuredDescription = structuredDescription.replace(/\s+/g, ' ').trim();
        
        if (structuredDescription.length < 10 || structuredDescription.includes('Main content')) {
          structuredDescription = title;
        }
        
        return {
          title: title,
          brand: brand,
          color: color,
          size: size,
          price: price,
          mainImage: mainImage,
          structuredDescription: structuredDescription,
          cleanedText: structuredDescription,
          success: true
        };
      }
    }, (results) => {
      if (chrome.runtime.lastError) {
        reject(new Error(chrome.runtime.lastError.message));
        return;
      }
      if (results && results[0] && results[0].result) {
        resolve(results[0].result);
      } else {
        reject(new Error("Failed to extract page data"));
      }
    });
  });
}

// ================== CREATE CONTEXT MENUS ==================

chrome.runtime.onInstalled.addListener(() => {
  console.log("Creating context menus...");
  
  chrome.contextMenus.create({
    id: "checkMismatch",
    title: "Check Mismatch with ImageGuard",
    contexts: ["selection"]
  });
  
  chrome.contextMenus.create({
    id: "analyzeImage",
    title: "Analyze Image with ImageGuard",
    contexts: ["image"]
  });
});

chrome.contextMenus.onClicked.addListener((info, tab) => {
  console.log("Context menu clicked:", info.menuItemId);
  
  if (info.menuItemId === "checkMismatch") {
    selectedText = cleanEcommerceText(info.selectionText);
    console.log("Text selected for mismatch:", selectedText.substring(0, 50) + "...");
    
    const productType = detectProductTypeFromText(selectedText);
    console.log("Detected product type from selection:", productType);
    
    chrome.tabs.sendMessage(tab.id, {
      action: "getSelectedImageForMismatch"
    }, (response) => {
      if (chrome.runtime.lastError) {
        console.log("Content script not ready:", chrome.runtime.lastError);
        return;
      }
      
      if (response && response.imageSrc) {
        selectedImage = response.imageSrc;
        console.log("Got selected image:", selectedImage);
        
        chrome.storage.local.set({
          mismatchData: {
            text: selectedText,
            imageUrl: selectedImage,
            detectedProductType: productType,
            timestamp: Date.now()
          }
        }, () => {
          chrome.action.openPopup();
        });
      } else {
        chrome.storage.local.set({
          mismatchData: {
            text: selectedText,
            imageUrl: null,
            detectedProductType: productType,
            timestamp: Date.now()
          }
        }, () => {
          chrome.action.openPopup();
        });
      }
    });
  } else if (info.menuItemId === "analyzeImage") {
    if (info.srcUrl) {
      console.log("Analyzing image from context menu:", info.srcUrl);
      
      chrome.storage.local.set({
        clickedImage: {
          src: info.srcUrl,
          timestamp: Date.now()
        }
      }, () => {
        chrome.action.openPopup();
      });
    }
  }
});

// ================== TAB UPDATE HANDLER ==================

chrome.tabs.onUpdated.addListener((tabId, changeInfo, tab) => {
  if (changeInfo.status === 'complete' && tab.url && tab.url.startsWith('http')) {
    chrome.tabs.sendMessage(tabId, { action: "ping" }, (response) => {
      if (chrome.runtime.lastError) {
        chrome.scripting.executeScript({
          target: { tabId: tabId },
          files: ['content.js']
        }).catch(err => console.log("Error injecting content script:", err.message));
      } else {
        console.log("Content script already active in tab", tabId);
      }
    });
  }
});

// ================== MESSAGE HANDLERS ==================

chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  console.log("Background received:", request.action);

  if (request.action === "analyzeImage") {
    const imageUrl = request.imageUrl;
    const requestKey = `${sender.tab.id}_${imageUrl}`;
    
    if (activeRequests.has(requestKey)) {
      return true;
    }
    
    activeRequests.set(requestKey, true);
    
    console.log("Fast analyzing image:", imageUrl);
    
    chrome.storage.local.set({ 
      analyzing: true,
      currentImage: imageUrl,
      currentTabId: sender.tab.id
    });
    
    processImageFast(imageUrl, sender.tab.id)
      .then(result => {
        console.log("Fast analysis complete:", result.verdict);
        result.needs_explanation = true;
        
        chrome.tabs.sendMessage(sender.tab.id, {
          action: "updateImage",
          imageUrl: imageUrl,
          verdict: result.verdict,
          confidence: result.confidence,
          needsExplanation: result.needs_explanation
        }).catch(err => console.log("Content script not ready:", err.message));
        
        const storedResult = {
          ...result,
          imageUrl: imageUrl,
          timestamp: Date.now(),
          hasXAI: false
        };
        
        chrome.storage.local.set({
          lastResult: storedResult,
          analyzing: false
        });
        
        chrome.storage.local.set({
          lastAnalyzedImage: {
            src: imageUrl,
            verdict: result.verdict,
            confidence: result.confidence,
            timestamp: Date.now()
          }
        });
      })
      .catch(error => {
        console.error("Analysis failed:", error);
        
        chrome.tabs.sendMessage(sender.tab.id, {
          action: "showError",
          imageUrl: imageUrl,
          error: error.message
        }).catch(err => console.log("Content script not ready:", err.message));
        
        chrome.storage.local.set({
          lastError: error.message,
          analyzing: false
        });
      })
      .finally(() => {
        activeRequests.delete(requestKey);
      });
    
    return true;
  }
  
  else if (request.action === "generateXAI") {
    const imageUrl = request.imageUrl;
    const imageBase64 = request.imageBase64;
    
    console.log("Generating XAI for:", imageUrl);
    
    generateXAI(imageUrl, imageBase64)
      .then(result => {
        console.log("XAI generated with textual explanations");
        
        chrome.storage.local.get(['lastResult'], (data) => {
          if (data.lastResult && data.lastResult.imageUrl === imageUrl) {
            const updatedResult = {
              ...data.lastResult,
              xai_visualizations: result.xai_visualizations,
              predictions: result.predictions,
              confidence_scores: result.confidence_scores,
              hasXAI: true
            };
            
            chrome.storage.local.set({ lastResult: updatedResult });
            
            try {
              chrome.runtime.sendMessage({
                action: "xaiGenerated",
                imageUrl: imageUrl,
                xai: result.xai_visualizations,
                predictions: result.predictions,
                confidence_scores: result.confidence_scores
              });
            } catch (err) {
              console.log("Popup not open");
            }
            
            chrome.storage.local.set({
              lastXAIResult: {
                imageUrl: imageUrl,
                xai: result.xai_visualizations,
                predictions: result.predictions,
                confidence_scores: result.confidence_scores,
                timestamp: Date.now()
              }
            });
          }
        });
        
        sendResponse({ success: true, result: result });
      })
      .catch(error => {
        console.error("XAI generation failed:", error);
        sendResponse({ success: false, error: error.message });
      });
    
    return true;
  }
  
  else if (request.action === "detectMismatch") {
    const imageUrl = request.imageUrl;
    const description = request.description;
    const imageBase64 = request.imageBase64;
    
    console.log("Starting enhanced mismatch detection...");
    
    const cleanedDescription = cleanEcommerceText(description);
    const textFeatures = extractProductFeaturesFromText(cleanedDescription);
    console.log("Extracted text features:", textFeatures);
    
    detectMismatch(imageUrl, cleanedDescription, imageBase64)
      .then(result => {
        console.log("Mismatch detection complete:", result.verdict);
        
        if (!result.text_features && textFeatures.product_type) {
          result.text_features = textFeatures;
        }
        
        chrome.storage.local.set({
          lastMismatchResult: {
            ...result,
            imageUrl: imageUrl,
            description: cleanedDescription,
            textFeatures: textFeatures,
            timestamp: Date.now()
          }
        });
        
        try {
          chrome.runtime.sendMessage({
            action: "mismatchResult",
            result: result
          });
        } catch (err) {
          console.log("Popup not open");
        }
        
        sendResponse({ success: true, result: result });
      })
      .catch(error => {
        console.error("Mismatch detection failed:", error);
        sendResponse({ success: false, error: error.message });
      });
    
    return true;
  }
  
  else if (request.action === "extractProductDetails") {
    const tabId = request.tabId;
    
    console.log("Extracting product details from page...");
    
    extractProductDetailsFromPage(tabId)
      .then(result => {
        console.log("Extraction complete:", result);
        
        const cleanedText = cleanEcommerceText(result.structuredDescription || result.title || '');
        
        sendResponse({ 
          success: true, 
          result: {
            ...result,
            cleanedText: cleanedText
          }
        });
      })
      .catch(error => {
        console.error("Extraction failed:", error);
        sendResponse({ success: false, error: error.message });
      });
    
    return true;
  }
  
  else if (request.action === "submitFeedback") {
    const feedback = request.feedback;
    
    submitFeedback(feedback)
      .then(result => {
        console.log("Feedback submitted");
        sendResponse({ success: true, result: result });
      })
      .catch(error => {
        console.error("Feedback submission failed:", error);
        sendResponse({ success: false, error: error.message });
      });
    
    return true;
  }
  
  else if (request.action === "checkAPI") {
    fetch("http://127.0.0.1:8000/health", { 
      method: "GET",
      mode: "cors",
      headers: { 'Accept': 'application/json' }
    })
      .then(response => {
        if (response.ok) {
          return response.json().then(data => sendResponse({ running: true, data: data }));
        }
        sendResponse({ running: false, error: `Status: ${response.status}` });
      })
      .catch(error => {
        console.error("API check error:", error);
        sendResponse({ running: false, error: error.message });
      });
    return true;
  }
  
  else if (request.action === "getLastResult") {
    chrome.storage.local.get(['lastResult'], (data) => {
      sendResponse({ result: data.lastResult });
    });
    return true;
  }
  
  else if (request.action === "openPopup") {
    chrome.action.openPopup().then(() => {
      console.log("Popup opened");
      sendResponse({ success: true });
    }).catch(error => {
      console.error("Failed to open popup:", error);
      sendResponse({ success: false, error: error.message });
    });
    return true;
  }
  
  else if (request.action === "clearStorage") {
    chrome.storage.local.clear(() => {
      console.log("Storage cleared");
      sendResponse({ success: true });
    });
    return true;
  }
  
  return false;
});

// ================== API HELPER FUNCTIONS ==================

async function processImageFast(imageUrl, tabId) {
  try {
    console.log("Fetching image from URL:", imageUrl);
    
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 15000);
    
    const response = await fetch(imageUrl, {
      signal: controller.signal,
      headers: { 'Accept': 'image/*' }
    });
    
    clearTimeout(timeoutId);
    
    if (!response.ok) {
      throw new Error(`Failed to fetch image: ${response.status} ${response.statusText}`);
    }
    
    const blob = await response.blob();
    if (blob.size > 10 * 1024 * 1024) {
      throw new Error("Image too large (max 10MB)");
    }
    
    const base64 = await blobToBase64(blob);
    
    console.log("Sending to API for analysis...");
    
    const apiController = new AbortController();
    const apiTimeoutId = setTimeout(() => apiController.abort(), 30000);
    
    const base64Data = base64.split(',')[1];
    
    const apiResponse = await fetch("http://127.0.0.1:8000/detect-base64", {
      method: "POST",
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'application/json'
      },
      body: JSON.stringify({
        image_base64: base64Data,
        image_url: imageUrl
      }),
      signal: apiController.signal
    });
    
    clearTimeout(apiTimeoutId);
    
    if (!apiResponse.ok) {
      const errorText = await apiResponse.text();
      throw new Error(`API error: ${apiResponse.status} - ${errorText}`);
    }
    
    const data = await apiResponse.json();
    
    if (data.status === "error") {
      throw new Error(data.error || "API returned error");
    }
    
    console.log("API response received:", data.verdict, data.confidence);
    return data;
    
  } catch (error) {
    if (error.name === 'AbortError') {
      throw new Error("Request timed out. Please try again.");
    }
    throw error;
  }
}

async function generateXAI(imageUrl, imageBase64) {
  try {
    console.log("Generating XAI for:", imageUrl);
    
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 60000);
    
    const base64Data = imageBase64.split(',')[1];
    
    const apiResponse = await fetch("http://127.0.0.1:8000/generate-xai", {
      method: "POST",
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'application/json'
      },
      body: JSON.stringify({
        image_base64: base64Data,
        image_url: imageUrl
      }),
      signal: controller.signal
    });
    
    clearTimeout(timeoutId);
    
    if (!apiResponse.ok) {
      const errorText = await apiResponse.text();
      throw new Error(`XAI API error: ${apiResponse.status} - ${errorText}`);
    }
    
    const data = await apiResponse.json();
    
    if (data.status === "error") {
      throw new Error(data.error || "XAI API returned error");
    }
    
    console.log("XAI data received");
    return data;
    
  } catch (error) {
    if (error.name === 'AbortError') {
      throw new Error("XAI generation timed out after 60 seconds.");
    }
    console.error("XAI generation failed:", error);
    throw error;
  }
}

async function detectMismatch(imageUrl, description, imageBase64) {
  try {
    console.log("Starting enhanced mismatch detection...");
    
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 60000);
    
    const base64Data = imageBase64.split(',')[1];
    
    const apiResponse = await fetch("http://127.0.0.1:8000/detect-mismatch", {
      method: "POST",
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'application/json'
      },
      body: JSON.stringify({
        image_base64: base64Data,
        description: description,
        image_url: imageUrl
      }),
      signal: controller.signal
    });
    
    clearTimeout(timeoutId);
    
    if (!apiResponse.ok) {
      const errorText = await apiResponse.text();
      throw new Error(`Mismatch API error: ${apiResponse.status} - ${errorText}`);
    }
    
    const data = await apiResponse.json();
    
    if (data.status === "error") {
      throw new Error(data.error || "Mismatch API returned error");
    }
    
    console.log("Mismatch detection complete:", data.verdict);
    return data;
    
  } catch (error) {
    if (error.name === 'AbortError') {
      throw new Error("Mismatch detection timed out after 60 seconds.");
    }
    console.error("Mismatch detection failed:", error);
    throw error;
  }
}

async function submitFeedback(feedback) {
  try {
    console.log("Submitting feedback...");
    
    const { imageUrl, predictedLabel, trueLabel, confidence, imageBase64 } = feedback;
    
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 15000);
    
    const base64Data = imageBase64 ? imageBase64.split(',')[1] : '';
    
    try {
      const apiResponse = await fetch("http://127.0.0.1:8000/submit-feedback", {
        method: "POST",
        headers: {
          'Content-Type': 'application/json',
          'Accept': 'application/json'
        },
        body: JSON.stringify({
          image_base64: base64Data,
          image_url: imageUrl,
          predicted_label: predictedLabel,
          true_label: trueLabel,
          confidence: confidence,
          feedback: "User corrected prediction"
        }),
        signal: controller.signal
      });
      
      clearTimeout(timeoutId);
      
      if (apiResponse.ok) {
        const data = await apiResponse.json();
        console.log("Feedback submitted to API");
        return data;
      }
    } catch (apiError) {
      console.log("Feedback API not available, storing locally");
    }
    
    const feedbackData = {
      imageUrl: imageUrl,
      predictedLabel: predictedLabel,
      trueLabel: trueLabel,
      confidence: confidence,
      timestamp: Date.now()
    };
    
    chrome.storage.local.get(['userFeedback'], (result) => {
      const feedbacks = result.userFeedback || [];
      feedbacks.push(feedbackData);
      chrome.storage.local.set({ userFeedback: feedbacks });
    });
    
    return {
      status: "success",
      message: "Feedback recorded (stored locally)"
    };
    
  } catch (error) {
    if (error.name === 'AbortError') {
      throw new Error("Feedback submission timed out");
    }
    console.error("Feedback submission failed:", error);
    throw error;
  }
}

function blobToBase64(blob) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onloadend = () => resolve(reader.result);
    reader.onerror = reject;
    reader.readAsDataURL(blob);
  });
}

// ================== CLEANUP INTERVAL ==================

setInterval(() => {
  chrome.storage.local.get(['lastResult', 'lastXAIResult', 'lastMismatchResult', 'mismatchData'], (data) => {
    const now = Date.now();
    const thirtyMinutes = 30 * 60 * 1000;
    
    if (data.lastResult && now - data.lastResult.timestamp > thirtyMinutes) {
      chrome.storage.local.remove(['lastResult', 'lastError', 'lastAnalyzedImage']);
      console.log("Cleaned old result data");
    }
    if (data.lastXAIResult && now - data.lastXAIResult.timestamp > thirtyMinutes) {
      chrome.storage.local.remove(['lastXAIResult']);
      console.log("Cleaned old XAI data");
    }
    if (data.lastMismatchResult && now - data.lastMismatchResult.timestamp > thirtyMinutes) {
      chrome.storage.local.remove(['lastMismatchResult']);
      console.log("Cleaned old mismatch data");
    }
    if (data.mismatchData && now - data.mismatchData.timestamp > thirtyMinutes) {
      chrome.storage.local.remove(['mismatchData']);
      console.log("Cleaned old mismatch data");
    }
  });
}, 60000);

// ================== INITIALIZATION ==================

chrome.action.setBadgeText({ text: "ON" });
chrome.action.setBadgeBackgroundColor({ color: '#28a745' });

chrome.runtime.onInstalled.addListener((details) => {
  if (details.reason === 'install') {
    console.log("ImageGuard extension installed");
    chrome.storage.local.set({
      detectionEnabled: true,
      firstRun: true
    });
  }
});

chrome.tabs.onRemoved.addListener((tabId, removeInfo) => {
  for (const [key, value] of activeRequests.entries()) {
    if (key.startsWith(`${tabId}_`)) {
      activeRequests.delete(key);
    }
  }
});

console.log("Background service worker ready with enhanced extraction and accurate color analysis");