const { GoogleGenerativeAI } = require('@google/generative-ai');

// SECURITY WARNING: Never hardcode your API key here! It will be leaked to GitHub.
// Always use the .env file.
const genAI = new GoogleGenerativeAI(process.env.GEMINI_API_KEY);

// ============================================
// DESIGN RANDOMIZATION ENGINE
// Ensures every generated website looks unique
// ============================================
const LAYOUT_PATTERNS = [
  {
    name: 'Split Hero',
    hero: 'Two-column split layout: text on left, large image on right. Full-viewport height hero.',
    cards: 'Horizontal scroll carousel of cards',
    cta: 'Floating sticky CTA bar at bottom'
  },
  {
    name: 'Centered Minimal',
    hero: 'Centered text hero with large background image behind, dark overlay, text centered vertically.',
    cards: 'Masonry grid layout (3 columns, varying heights)',
    cta: 'Large rounded pill button centered below content'
  },
  {
    name: 'Asymmetric Bold',
    hero: 'Asymmetric layout with oversized heading text taking 60% width, image bleeding off edge.',
    cards: 'Alternating left-right zigzag sections',
    cta: 'Full-width gradient banner with CTA'
  },
  {
    name: 'Magazine',
    hero: 'Full-bleed image background with overlaid gradient and text at bottom-left.',
    cards: 'Newspaper-style grid: one large featured + smaller tiles',
    cta: 'Inline CTA embedded within content flow'
  },
  {
    name: 'Dashboard-Style',
    hero: 'Compact header bar with stats/metrics row below it. No traditional hero.',
    cards: 'Data grid with sortable columns or stat cards in a 4-column row',
    cta: 'Top-right action button in the header'
  },
  {
    name: 'Parallax Scroll',
    hero: 'Full-screen image with parallax-style layered text/overlay using fixed background.',
    cards: 'Vertical timeline or stacked full-width sections with alternating backgrounds',
    cta: 'Animated scroll-triggered CTA'
  },
  {
    name: 'Card-First',
    hero: 'No traditional hero — starts immediately with a prominent feature card grid.',
    cards: 'Rounded, elevated cards with hover-lift effects in a responsive grid',
    cta: 'Each card has its own CTA button'
  }
];

const EXTRA_DESIGN_MODIFIERS = [
  'Add subtle CSS animations (fade-in on scroll, slide-up on load) using Tailwind animate classes',
  'Use a diagonal or curved SVG divider between sections',
  'Add a floating badge or ribbon element for emphasis',
  'Use an icon set (emoji or Unicode symbols) alongside headings for visual interest',
  'Include a decorative background pattern using CSS gradients (subtle dots or lines)',
  'Add a testimonials/quote section with large decorative quotation marks',
  'Use numbered steps or a visual timeline for process sections',
  'Add micro-interactions: button scale on hover, card tilt, underline slide on links'
];

function getRandomDesignVariation() {
  const layout = LAYOUT_PATTERNS[Math.floor(Math.random() * LAYOUT_PATTERNS.length)];
  // Pick 2 random modifiers
  const shuffled = [...EXTRA_DESIGN_MODIFIERS].sort(() => 0.5 - Math.random());
  const modifiers = shuffled.slice(0, 2);

  return { layout, modifiers };
}

// ============================================
// UNSPLASH IMAGE HELPER
// ============================================
function getImageUrls(pageKeywords, count = 4) {
  if (!pageKeywords) return '';

  const keywords = pageKeywords.split(',').map(k => k.trim());
  const urls = [];

  for (let i = 0; i < count; i++) {
    const seed = Math.floor(Math.random() * 900) + 100;
    const w = i === 0 ? 1200 : 800;
    const h = i === 0 ? 600 : 500;
    // Use loremflickr for keyword-relevant images (always works, no API key needed)
    const keyword = keywords[i % keywords.length].replace(/\s+/g, ',');
    urls.push(`https://loremflickr.com/${w}/${h}/${keyword}?lock=${seed}`);
  }

  return `
REAL IMAGES — use these exact URLs in <img> tags (they return real photos):
${urls.map((url, i) => `  Image ${i + 1}: ${url}`).join('\n')}
RULES for images:
- Use these URLs DIRECTLY as src attributes: <img src="${urls[0]}" ... />
- Use className="w-full h-64 object-cover rounded-xl" for a responsive image card
- The first URL is wider (good for hero/banner), others are more square (good for cards)
- DO NOT use colored div placeholders — these URLs return real photos
- Add alt text describing what the image shows`;
}


// ============================================
// MAIN EXECUTION
// ============================================
// MAIN EXECUTION - with auto-retry on rate limits
// ============================================
const sleep = (ms) => new Promise(resolve => setTimeout(resolve, ms));

// ============================================
// CODE CLEANING & VALIDATION HELPERS
// Makes generated code reliable regardless of model
// ============================================

/**
 * Comprehensive cleaning of LLM-generated code.
 * Strips markdown wrappers, stray prose, fixes common syntax issues.
 */
function cleanGeneratedCode(rawCode, action) {
  let code = rawCode;

  // 1. Strip markdown code fences (```jsx, ```javascript, ```html, ```sql, etc.)
  code = code.replace(/```[a-zA-Z]*\n?/g, '').trim();

  // 2. Remove stray prose before/after the actual code
  if (action === 'create_page') {
    // Remove any text before the function declaration
    const fnStart = code.search(/^\s*(function\s|const\s)/m);
    if (fnStart > 0) {
      const before = code.substring(0, fnStart);
      if (!before.includes('{') && !before.includes('<') && !before.includes('return')) {
        console.log(`🧹 Stripped ${fnStart} chars of prose before function`);
        code = code.substring(fnStart);
      }
    }

    // Remove any text after the last closing brace of the function
    const lastBrace = code.lastIndexOf('}');
    if (lastBrace !== -1 && lastBrace < code.length - 1) {
      const after = code.substring(lastBrace + 1).trim();
      if (after && !after.startsWith('//') && !after.startsWith('/*') && after.length < 500) {
        code = code.substring(0, lastBrace + 1);
      }
    }
  }

  // 3. Strip SQL-specific wrappers
  if (action === 'create_database_schema') {
    code = code.replace(/```sql/g, '').replace(/```/g, '').trim();
  }

  // 4. Remove orphan import/export lines
  code = code.replace(/^import\s+.*from\s+['"].*['"];?\s*$/gm, '');
  code = code.replace(/^'use client';?\s*$/gm, '');
  code = code.replace(/^"use client";?\s*$/gm, '');
  // Preserve "export default function" instead of deleting the whole line
  code = code.replace(/^export\s+default\s+function/gm, 'function');
  // Then remove standalone regular exports like "export default Home;"
  code = code.replace(/^export\s+default\s+.*$/gm, '');
  code = code.replace(/^export\s+\{[^}]*\}\s*;?\s*$/gm, '');

  // 5. Remove React/hook imports (they are globals in our setup)
  code = code.replace(/^\s*const\s*\{[^}]*\}\s*=\s*React\s*;?\s*$/gm, '');
  code = code.replace(/^\s*const\s+React\s*=\s*require\([^)]*\)\s*;?\s*$/gm, '');

  // 6. Fix common JSX attribute errors inline
  code = code.replace(/\bclass=/g, 'className=');
  code = code.replace(/\bfor=/g, 'htmlFor=');
  code = code.replace(/\btabindex=/gi, 'tabIndex=');
  code = code.replace(/\bautocomplete=/gi, 'autoComplete=');
  code = code.replace(/\breadonly(?=\s|>|\/>)/gi, 'readOnly');
  code = code.replace(/\bmaxlength=/gi, 'maxLength=');
  code = code.replace(/\bminlength=/gi, 'minLength=');
  code = code.replace(/\bcellpadding=/gi, 'cellPadding=');
  code = code.replace(/\bcellspacing=/gi, 'cellSpacing=');
  code = code.replace(/\bcolspan=/gi, 'colSpan=');
  code = code.replace(/\browspan=/gi, 'rowSpan=');
  code = code.replace(/\benctype=/gi, 'encType=');
  code = code.replace(/\bnovalidate(?=\s|>|\/>)/gi, 'noValidate');
  code = code.replace(/\bplaceholder=/gi, 'placeholder=');
  code = code.replace(/\bcontenteditable=/gi, 'contentEditable=');
  code = code.replace(/\bcrossorigin=/gi, 'crossOrigin=');
  code = code.replace(/\bdatetime=/gi, 'dateTime=');

  // 7. Convert HTML-style style="..." to JSX style={{ }}
  code = code.replace(/style="([^"]*)"/g, (match, cssStr) => {
    try {
      const parts = cssStr.split(';').filter(s => s.trim());
      if (parts.length === 0) return match;
      const jsxParts = parts.map(part => {
        const colonIdx = part.indexOf(':');
        if (colonIdx === -1) return null;
        const prop = part.substring(0, colonIdx).trim();
        const val = part.substring(colonIdx + 1).trim();
        if (!prop || !val) return null;
        const camelProp = prop.replace(/-([a-z])/g, (_, c) => c.toUpperCase());
        return `${camelProp}: '${val}'`;
      }).filter(Boolean);
      if (jsxParts.length === 0) return match;
      return `style={{ ${jsxParts.join(', ')} }}`;
    } catch {
      return match;
    }
  });

  // 8. Convert HTML event handlers to React equivalents
  code = code.replace(/\bonclick=/gi, 'onClick=');
  code = code.replace(/\bonchange=/gi, 'onChange=');
  code = code.replace(/\bonsubmit=/gi, 'onSubmit=');
  code = code.replace(/\bonkeydown=/gi, 'onKeyDown=');
  code = code.replace(/\bonkeyup=/gi, 'onKeyUp=');
  code = code.replace(/\bonmouseover=/gi, 'onMouseOver=');
  code = code.replace(/\bonmouseout=/gi, 'onMouseOut=');
  code = code.replace(/\bonfocus=/gi, 'onFocus=');
  code = code.replace(/\bonblur=/gi, 'onBlur=');
  code = code.replace(/\boninput=/gi, 'onInput=');

  return code.trim();
}

/**
 * Validate JSX code for common fatal errors.
 * Returns array of issue descriptions (empty = valid).
 */
function validateJSX(code) {
  const issues = [];

  // 1. Check brace/paren/bracket balance
  let braces = 0, parens = 0, brackets = 0;
  for (const ch of code) {
    if (ch === '{') braces++;
    else if (ch === '}') braces--;
    else if (ch === '(') parens++;
    else if (ch === ')') parens--;
    else if (ch === '[') brackets++;
    else if (ch === ']') brackets--;
  }
  if (braces !== 0) issues.push(`unbalanced_braces:${braces}`);
  if (parens !== 0) issues.push(`unbalanced_parens:${parens}`);
  if (brackets !== 0) issues.push(`unbalanced_brackets:${brackets}`);

  // 2. Check for HTML attributes that should be JSX
  if (/\bclass="/i.test(code)) issues.push('html_class_attribute');
  if (/\bfor="/i.test(code) && /\<label/i.test(code)) issues.push('html_for_attribute');
  if (/\bonchange="/i.test(code)) issues.push('html_onchange_attribute');
  if (/\bonclick="/i.test(code)) issues.push('html_onclick_attribute');

  // 3. Check for markdown remnants
  if (code.includes('```')) issues.push('markdown_fence_remnant');

  // 4. Check for missing return statement
  if (code.includes('function ') && !code.includes('return')) {
    issues.push('missing_return');
  }

  // 5. Check for HTML-style style attributes
  // Match style="..." but not style={{ (which is JSX)
  const styleStringMatches = code.match(/style="[^"]+"/g);
  if (styleStringMatches && styleStringMatches.length > 0) {
    issues.push('html_style_string');
  }

  return issues;
}

/**
 * Auto-fix common JSX issues that can be repaired programmatically.
 */
function autoFixJSX(code, issues) {
  let fixed = code;

  for (const issue of issues) {
    switch (issue) {
      case 'html_class_attribute':
        fixed = fixed.replace(/\bclass="/g, 'className="');
        console.log('🔧 Fixed: class → className');
        break;

      case 'html_for_attribute':
        fixed = fixed.replace(/\bfor="/g, 'htmlFor="');
        console.log('🔧 Fixed: for → htmlFor');
        break;

      case 'html_onclick_attribute':
        fixed = fixed.replace(/\bonclick="([^"]*)"/gi, 'onClick={() => { $1 }}');
        console.log('🔧 Fixed: onclick → onClick');
        break;

      case 'html_onchange_attribute':
        fixed = fixed.replace(/\bonchange="([^"]*)"/gi, 'onChange={() => { $1 }}');
        console.log('🔧 Fixed: onchange → onChange');
        break;

      case 'markdown_fence_remnant':
        fixed = fixed.replace(/```[a-zA-Z]*\n?/g, '');
        console.log('🔧 Fixed: removed markdown fences');
        break;

      case 'html_style_string':
        fixed = fixed.replace(/style="([^"]*)"/g, (match, cssStr) => {
          try {
            const parts = cssStr.split(';').filter(s => s.trim());
            const jsxParts = parts.map(part => {
              const colonIdx = part.indexOf(':');
              if (colonIdx === -1) return null;
              const prop = part.substring(0, colonIdx).trim();
              const val = part.substring(colonIdx + 1).trim();
              if (!prop || !val) return null;
              const camelProp = prop.replace(/-([a-z])/g, (_, c) => c.toUpperCase());
              return `${camelProp}: '${val}'`;
            }).filter(Boolean);
            if (jsxParts.length === 0) return match;
            return `style={{ ${jsxParts.join(', ')} }}`;
          } catch {
            return match;
          }
        });
        console.log('🔧 Fixed: style="..." → style={{ }}');
        break;

      default:
        // Handle unbalanced delimiters — try to repair
        if (issue.startsWith('unbalanced_braces:')) {
          const count = parseInt(issue.split(':')[1]);
          if (count > 0 && count <= 3) {
            // Missing closing braces — add them
            fixed = fixed.trimEnd() + '\n' + '}'.repeat(count);
            console.log(`🔧 Fixed: added ${count} missing closing brace(s)`);
          }
        }
        if (issue.startsWith('unbalanced_parens:')) {
          const count = parseInt(issue.split(':')[1]);
          if (count > 0 && count <= 3) {
            fixed = fixed.trimEnd() + ')'.repeat(count);
            console.log(`🔧 Fixed: added ${count} missing closing paren(s)`);
          }
        }
        if (issue.startsWith('unbalanced_brackets:')) {
          const count = parseInt(issue.split(':')[1]);
          if (count > 0 && count <= 3) {
            fixed = fixed.trimEnd() + ']'.repeat(count);
            console.log(`🔧 Fixed: added ${count} missing closing bracket(s)`);
          }
        }
        break;
    }
  }

  return fixed;
}

async function executeInstruction(instruction, plan, dbConfig, context = {}) {
  console.log(`🤖 Gemini executing: ${instruction.action}`);

  const model = genAI.getGenerativeModel({
    model: process.env.GEMINI_MODEL || 'gemini-2.5-flash',
    generationConfig: {
      maxOutputTokens: 65536,
    }
  });

  let prompt = '';

  switch (instruction.action) {
    case 'create_database_schema':
      prompt = createSchemaPrompt(instruction, plan);
      break;
    case 'create_page':
      prompt = createPagePrompt(instruction, plan, context);
      break;
    case 'create_api':
      prompt = createApiPrompt(instruction, plan, dbConfig, context);
      break;
    default:
      console.warn(`⚠️ Unknown action: ${instruction.action}`);
      instruction.action = 'create_page';
      instruction.page = instruction.page || 'home';
      prompt = createPagePrompt(instruction, plan, context);
      break;
  }

  // Retry loop — handles 429 rate limit errors automatically
  const MAX_RETRIES = 3;
  let lastCode = ''; // Track last cleaned code for fallback
  for (let attempt = 1; attempt <= MAX_RETRIES; attempt++) {
    try {
      const result = await model.generateContent(prompt);
      const response = await result.response;
      let code = response.text();

      // ========== COMPREHENSIVE CODE CLEANING ==========
      code = cleanGeneratedCode(code, instruction.action);
      lastCode = code; // Save for fallback

      // ========== VALIDATION (for page code only) ==========
      if (instruction.action === 'create_page') {
        const issues = validateJSX(code);
        if (issues.length > 0) {
          console.warn(`⚠️ Validation issues in ${instruction.page || 'page'}:`, issues);

          // Auto-fix what we can
          code = autoFixJSX(code, issues);
          lastCode = code; // Save the auto-fixed version

          // Re-validate after auto-fix
          const remainingIssues = validateJSX(code);
          if (remainingIssues.length > 0 && attempt < MAX_RETRIES) {
            console.log(`🔄 Code still has issues after auto-fix, retrying (attempt ${attempt})...`);
            // Retry with a more explicit prompt
            throw new Error(`CODE_QUALITY_RETRY: ${remainingIssues.join(', ')}`);
          }
        }
      }

      console.log(`✅ Gemini completed: ${instruction.action}`);
      return code;

    } catch (err) {
      const is429 = err.message && (err.message.includes('429') || err.message.includes('Too Many Requests'));
      const isNetworkError = err.message && (
        err.message.includes('fetch failed') ||
        err.message.includes('ECONNRESET') ||
        err.message.includes('ETIMEDOUT') ||
        err.message.includes('ENOTFOUND') ||
        err.message.includes('socket hang up') ||
        err.message.includes('network')
      );

      if (is429 && attempt < MAX_RETRIES) {
        // Extract retry delay from the error message (the API tells us exactly how long to wait)
        const retryMatch = err.message.match(/retryDelay['":\s]+['"]?([\d.]+)s['"]?/);
        const waitSeconds = retryMatch ? Math.ceil(parseFloat(retryMatch[1])) + 5 : attempt * 30;

        console.log(`⏳ Rate limited (attempt ${attempt}/${MAX_RETRIES}). Waiting ${waitSeconds}s before retry...`);
        await sleep(waitSeconds * 1000);
        continue;
      }

      if (isNetworkError && attempt < MAX_RETRIES) {
        const waitSeconds = attempt * 5; // 5s, 10s, 15s...
        console.log(`🌐 Network error (attempt ${attempt}/${MAX_RETRIES}): ${err.message}. Retrying in ${waitSeconds}s...`);
        await sleep(waitSeconds * 1000);
        continue;
      }

      // Code quality retry — short delay, then retry
      const isCodeQualityRetry = err.message && err.message.startsWith('CODE_QUALITY_RETRY:');
      if (isCodeQualityRetry && attempt < MAX_RETRIES) {
        console.log(`🔄 Code quality retry (attempt ${attempt}/${MAX_RETRIES}). Retrying in 5s...`);
        await sleep(5000);
        continue;
      }

      // Not a retryable error, or out of retries — rethrow
      if (isCodeQualityRetry) {
        // Don't crash on code quality issues — return the best code we have
        console.warn(`⚠️ Code quality issues persist after retries, returning best effort`);
        return lastCode || '';
      }
      throw err;
    }
  }
}


// ============================================
// SCHEMA PROMPT - Uses API Contract
// ============================================
function createSchemaPrompt(instruction, plan) {
  const contract = plan.apiContract;

  if (contract && contract.tables && contract.tables.length > 0) {
    const tableDefinitions = contract.tables.map(table => {
      const cols = table.columns.map(col => {
        let def = `  ${col.name} ${col.type}`;
        if (col.default !== undefined && col.default !== null) {
          def += ` DEFAULT ${col.default}`;
        }
        return def;
      }).join(',\n');
      return `CREATE TABLE IF NOT EXISTS ${table.name} (\n${cols}\n);`;
    }).join('\n\n');

    return `Generate the following PostgreSQL schema EXACTLY as specified:

${tableDefinitions}

Add a "created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP" column to each table if not already present.

RULES:
- Use the EXACT table names and column names shown above
- Do NOT rename or add extra tables
- Do NOT add ANY extra columns beyond what is specified above and the created_at column
- Do NOT add foreign keys unless specified
- Return ONLY the SQL CREATE TABLE statement(s), nothing else`;
  }

  return `You are creating a PostgreSQL database schema for: "${plan.description}"

Analyze what this project needs and create an appropriate schema.

CRITICAL TYPE RULES:
- Use VARCHAR(255) for: names, titles, categories, status, priority, short text
- Use TEXT for: descriptions, content, long text
- Use INTEGER ONLY for: counts, quantities, numeric IDs
- Use DECIMAL(10,2) ONLY for: money, prices
- Use BOOLEAN for: true/false flags
- Use TIMESTAMP for: dates and times

Requirements:
- Table name should match the project context
- 5-7 columns total including id and created_at
- NO foreign keys or complex relationships
- Use proper data types

Return ONLY the SQL CREATE TABLE statement(s).`;
}

// ============================================
// API PROMPT - Uses API Contract endpoints
// ============================================
function createApiPrompt(instruction, plan, dbConfig, context) {
  const contract = plan.apiContract;

  if (contract && contract.endpoints && contract.endpoints.length > 0 && contract.tables && contract.tables.length > 0) {
    const table = contract.tables[0];
    const tableName = table.name;
    const insertColumns = table.columns
      .filter(col => !['id', 'created_at', 'updated_at'].includes(col.name.toLowerCase()) && !col.type.includes('SERIAL'))
      .map(col => col.name);

    const endpointList = contract.endpoints.map(ep => `- ${ep.method} ${ep.path} : ${ep.description}`).join('\n');

    return `Create REST API route handlers for: "${plan.description}"

DATABASE TABLE: ${tableName}
INSERTABLE COLUMNS: ${insertColumns.join(', ')}
ALL TABLE COLUMNS: ${table.columns.map(c => `${c.name} (${c.type})`).join(', ')}

ENDPOINTS TO IMPLEMENT:
${endpointList}

IMPORTANT:
- Use EXACT endpoint paths as listed above
- Use EXACT table name: ${tableName}
- Use EXACT column names: ${insertColumns.join(', ')}
- Do NOT invent, rename, or add any columns that are not listed above
- Variable "pool" is already available (PostgreSQL connection pool)
- Variable "app" is already available (Express app)
- DO NOT add: require(), const pool, const app, app.listen(), or any imports
- Return ONLY route handlers (app.get, app.post, app.put, app.delete)
- Include proper error handling with try/catch
- Use parameterized queries ($1, $2, etc.) to prevent SQL injection
- Return JSON responses`;
  }

  const tableName = context.tableName || 'items';
  const columns = context.columns || ['title'];
  const insertColumns = columns.filter(col => !['id', 'created_at', 'updated_at'].includes(col.toLowerCase()));

  return `Create CRUD REST API route handlers for table "${tableName}" with columns: ${insertColumns.join(', ')}

- GET /api/${tableName} - Get all
- GET /api/${tableName}/:id - Get one
- POST /api/${tableName} - Create
- PUT /api/${tableName}/:id - Update  
- DELETE /api/${tableName}/:id - Delete

DO NOT add require, pool, app, or listen. Return ONLY route handlers.`;
}

// ============================================
// PAGE PROMPT - Dynamic, style-token-aware
// With Unsplash images & design randomization
// ============================================
function toPascalCase(str) {
  return str.split(/[-_\s]+/).map(p => p.charAt(0).toUpperCase() + p.slice(1).toLowerCase()).join('');
}

function createPagePrompt(instruction, plan, context) {
  const pageName = instruction.page;
  const componentName = toPascalCase(pageName);
  const styleTokens = plan.styleTokens || {};
  const palette = styleTokens.palette || {};
  const pageDescription = (plan.pageDescriptions && plan.pageDescriptions[pageName]) || instruction.details || `${componentName} page`;

  // === EDIT MODE ===
  if (context?.mode === 'edit') {
    return `You are making a SURGICAL EDIT to a single React component function.

STRICT OUTPUT RULES:
1. Return ONLY the complete JavaScript function. Nothing before it, nothing after it.
2. The FIRST line of your response MUST be: function ${componentName}(
3. The LAST line of your response MUST be a single closing brace: }
4. DO NOT include any markdown fences (no \`\`\`), no explanations, no commentary.
5. DO NOT rename the function — it MUST remain: function ${componentName}(...)
6. DO NOT add imports or exports — they are handled externally
7. DO NOT return HTML boilerplate, <html>, <head>, or <script> tags

JSX SYNTAX RULES:
- Use className= NOT class=
- Use htmlFor= NOT for=
- Use tabIndex= NOT tabindex=
- For inline styles, ALWAYS use JSX object syntax: style={{ color: 'red', fontSize: '18px' }}
- NEVER use HTML-string style="color: red" syntax
- All event handlers use camelCase: onClick, onChange, onSubmit (not onclick, onchange)
- Self-close tags without children: <img />, <input />, <br />

EDITING RULES:
- Keep all existing functionality intact unless explicitly asked to change it
- DO NOT remove existing state variables, useEffect hooks, or API calls unless asked
- You MAY: add/modify JSX elements, change styles, add new state, add new sections

CURRENT COMPONENT CODE:
<<<
${context.existingCode}
>>>

REQUESTED CHANGE:
${instruction.details}

Begin your response with: function ${componentName}(`;
  }

  // === GENERATE MODE ===

  // 1. Get random design variation for uniqueness
  const designVariation = getRandomDesignVariation();
  console.log(`🎨 Design variation for ${pageName}: ${designVariation.layout.name}`);

  // 2. Get image URLs for the page
  const imageKeywords = plan.imageKeywords && plan.imageKeywords[pageName];
  const imageSection = getImageUrls(imageKeywords || `${plan.description},${pageName}`);

  // 3. Build the API info string for pages that need data
  const contract = plan.apiContract || {};
  const endpoints = contract.endpoints || [];
  const tables = contract.tables || [];
  const primaryTable = tables.length > 0 ? tables[0] : null;
  const tableName = primaryTable ? primaryTable.name : 'items';
  const columnDetails = primaryTable
    ? primaryTable.columns
      .filter(c => !['id', 'created_at', 'updated_at'].includes(c.name.toLowerCase()) && !c.type.includes('SERIAL'))
      .map(c => `  - ${c.name} (${c.type})`).join('\n')
    : '';
  const allColumnNames = primaryTable
    ? primaryTable.columns
      .filter(c => !['id', 'created_at', 'updated_at'].includes(c.name.toLowerCase()) && !c.type.includes('SERIAL'))
      .map(c => c.name)
    : [];

  // Build a concrete CRUD example using the ACTUAL table/column names
  const crudExample = (endpoints.length > 0 && allColumnNames.length > 0) ? `

⚠️⚠️⚠️ COPY THIS EXACT PATTERN FOR CRUD (adapt UI only, keep data logic identical):

function ${componentName}() {
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [showForm, setShowForm] = useState(false);
  const [editId, setEditId] = useState(null);
  const [formData, setFormData] = useState({ ${allColumnNames.map(c => `${c}: ''`).join(', ')} });

  const fetchItems = () => {
    fetch(API_URL + '/api/${tableName}')
      .then(r => r.json())
      .then(data => { setItems(Array.isArray(data) ? data : []); setLoading(false); })
      .catch(err => { setError(err.message); setLoading(false); });
  };

  useEffect(() => { fetchItems(); }, []);

  const handleSubmit = (e) => {
    e.preventDefault();
    const url = editId ? API_URL + '/api/${tableName}/' + editId : API_URL + '/api/${tableName}';
    const method = editId ? 'PUT' : 'POST';
    fetch(url, {
      method,
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(formData)
    })
    .then(r => r.json())
    .then(() => {
      setFormData({ ${allColumnNames.map(c => `${c}: ''`).join(', ')} });
      setEditId(null);
      setShowForm(false);
      fetchItems();
    })
    .catch(err => setError(err.message));
  };

  const handleEdit = (item) => {
    setFormData({ ${allColumnNames.map(c => `${c}: item.${c} || ''`).join(', ')} });
    setEditId(item.id);
    setShowForm(true);
  };

  const handleDelete = (id) => {
    if (!confirm('Delete this item?')) return;
    fetch(API_URL + '/api/${tableName}/' + id, { method: 'DELETE' })
      .then(() => fetchItems())
      .catch(err => setError(err.message));
  };

  if (loading) return <div className="p-8 text-center"><p>Loading...</p></div>;
  if (error) return <div className="p-8 text-center text-red-500"><p>Error: {error}</p></div>;

  return (
    <div className="p-6">
      {/* ... your beautiful UI here, using items.map() to render data ... */}
      {/* ... form with inputs for: ${allColumnNames.join(', ')} ... */}
      {/* ... edit/delete buttons that call handleEdit(item) and handleDelete(item.id) ... */}
    </div>
  );
}

⚠️ The above is the DATA PATTERN. You MUST use this exact fetch/state logic but design your own beautiful UI around it.
` : '';

  const apiInfo = endpoints.length > 0
    ? `\n⭐⭐ CRITICAL — DATA MUST COME FROM THE API — NO HARDCODED DATA:
DATABASE TABLE: ${tableName}
TABLE COLUMNS (use EXACTLY these field names in state, forms, and fetch request/response bodies):
${columnDetails}

AVAILABLE API ENDPOINTS (API_URL is already defined globally as e.g. "http://localhost:3001"):
${endpoints.map(ep => `- ${ep.method} ${ep.path} : ${ep.description}`).join('\n')}

CRUD RULES (FOLLOW EXACTLY):
1. ALL data displayed MUST be fetched from the API using fetch(API_URL + '/api/${tableName}').
2. Use useState([]) for data arrays and useEffect with fetch to load data on mount.
3. NEVER create hardcoded/static arrays of items. The data MUST come from the database.
4. For CREATE: POST to API_URL + '/api/${tableName}' with JSON body containing { ${allColumnNames.join(', ')} }.
5. For UPDATE: PUT to API_URL + '/api/${tableName}/' + id with JSON body.
6. For DELETE: DELETE to API_URL + '/api/${tableName}/' + id.
7. After every CREATE/UPDATE/DELETE, re-fetch the data to refresh the list.
8. Include 'Content-Type': 'application/json' header in POST and PUT requests.
9. Show a loading state while fetching and an error state if fetch fails.
10. FIELD NAMES in useState objects, form inputs, and request bodies MUST EXACTLY match: ${allColumnNames.join(', ')}.
11. Do NOT invent, rename, or add fields that are not listed above.
${crudExample}`
    : '\nThis page does NOT need to fetch data from an API. Use static/hardcoded content.\n';

  // 4. Style guide with randomization built in
  const styleGuide = `
DESIGN SYSTEM (follow strictly):
- Theme: ${styleTokens.theme || 'light'}
- Visual Style: ${styleTokens.style || 'modern'}
- Font: "${styleTokens.fontFamily || 'Inter'}" (loaded via Google Fonts in the HTML head)
- Primary Color: ${palette.primary || '#6366f1'}
- Secondary Color: ${palette.secondary || '#8b5cf6'}  
- Accent Color: ${palette.accent || '#f59e0b'}
- Background: ${palette.background || '#f8fafc'}
- Text Color: ${palette.text || '#1e293b'}
- Border Radius: ${styleTokens.borderRadius || 'rounded-xl'}
- Animations: ${styleTokens.animations !== false ? 'YES - use Tailwind transitions, hover effects, and subtle animations' : 'minimal'}

🎨 UNIQUE LAYOUT DIRECTIVE (FOLLOW THIS EXACTLY — this makes YOUR design unique):
- Layout Pattern: "${designVariation.layout.name}"
- Hero Section: ${designVariation.layout.hero}
- Card/Content Layout: ${designVariation.layout.cards}
- CTA Placement: ${designVariation.layout.cta}
- Extra Effect 1: ${designVariation.modifiers[0]}
- Extra Effect 2: ${designVariation.modifiers[1]}

DESIGN EXCELLENCE RULES:
- Use gradients (e.g., bg-gradient-to-r, bg-gradient-to-br) with the palette colors via inline styles
- Use shadows (shadow-lg, shadow-xl) for depth
- Add hover effects on interactive elements (hover:scale-105, hover:shadow-xl)
- Use spacing generously (p-8, gap-6, space-y-6)
- Make headings bold and large (text-3xl, text-4xl, font-extrabold)
- Use the accent color for CTAs and highlights
- Create visual hierarchy with font sizes and weights
- ${styleTokens.style === 'glassmorphism' ? 'Use backdrop-blur-lg, bg-white/10, border border-white/20 for glass effects' : ''}
- ${styleTokens.style === 'luxury' ? 'Use serif fonts for headings, gold/warm tones, generous whitespace, elegant imagery placeholders' : ''}
- ${styleTokens.style === 'bold' ? 'Use large typography, bright saturated colors, strong contrasts, chunky buttons' : ''}
- ${styleTokens.style === 'minimal' ? 'Use lots of whitespace, thin borders, subtle colors, clean lines' : ''}
- ${styleTokens.theme === 'dark' ? 'All backgrounds should be dark (bg-gray-900, bg-gray-800). Text should be light (text-white, text-gray-200).' : ''}
`;

  return `Create a React component for the "${pageName}" page of: "${plan.description}"

Component name: function ${componentName}()
Page purpose: ${pageDescription}
${imageSection}
${apiInfo}
${styleGuide}

STRICT OUTPUT FORMAT:
1. Your response MUST start with EXACTLY: function ${componentName}() {
2. Your response MUST end with EXACTLY: } (the closing brace of the function)
3. DO NOT include any text before or after the function
4. DO NOT include markdown fences (no \`\`\`jsx or \`\`\`)
5. DO NOT include import or export statements
6. DO NOT include comments like "Here is the code" or explanations

JSX SYNTAX RULES (CRITICAL — violations cause runtime crashes):
- Use className= NOT class=
- Use htmlFor= NOT for= (on label elements)
- Use tabIndex= NOT tabindex=
- Use autoComplete= NOT autocomplete=
- Self-close tags: <img />, <input />, <br />, <hr />
- For inline styles, ALWAYS use JSX object syntax: style={{ color: 'red', fontSize: '18px' }}
- NEVER use HTML-string style="..." — this BREAKS the app
- NEVER put two style attributes on the same element
- All event handlers use camelCase: onClick, onChange, onSubmit

COMPLETENESS RULE:
- Every { MUST have a matching }
- Every ( MUST have a matching )
- Every [ MUST have a matching ]
- Every <tag> MUST have a matching </tag> or be self-closed
- If the component is getting long, SIMPLIFY the UI — do NOT truncate
- Count your braces before finishing. The function must be syntactically valid JavaScript.

OTHER RULES:
- Use React hooks: useState, useEffect are already available as globals
- Use Tailwind CSS classes for ALL styling
- Make the component RESPONSIVE (mobile-first, use md: and lg: breakpoints)
- Make this page look UNIQUE and SPECIFIC to its purpose
- Use the REAL image URLs provided above in <img> tags
- FORMS MUST MATCH THE WEBSITE PURPOSE: generate fields logically for "${plan.description}"

Begin your output NOW with: function ${componentName}() {`;
}

module.exports = {
  executeInstruction
};