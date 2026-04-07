const express = require('express');
const router = express.Router();
const fs = require('fs').promises;
const fsSync = require('fs');
const path = require('path');
const { exec } = require('child_process');
const util = require('util');
const archiver = require('archiver');
const multer = require('multer');
const llamaService = require('../services/llamaService');
const geminiService = require('../services/geminiService');

const execPromise = util.promisify(exec);

// ============================================
// VALIDATE & FIX COMPONENT CODE
// Repairs truncated/malformed Gemini output
// ============================================
function validateAndFixComponent(code, componentName) {
  let fixed = code;

  // 0. Strip any remaining markdown fences or prose
  fixed = fixed.replace(/```[a-zA-Z]*\n?/g, '').trim();

  // 1. Ensure a function declaration exists
  if (!fixed.includes(`function ${componentName}(`)) {
    // Try to find any function declaration and rename it
    const fnMatch = fixed.match(/function\s+(\w+)\s*\(/);
    if (fnMatch) {
      fixed = fixed.replace(fnMatch[0], `function ${componentName}(`);
    } else {
      // Try arrow function patterns: const X = () => or const X = (props) =>
      const arrowMatch = fixed.match(/const\s+\w+\s*=\s*\(/);
      if (arrowMatch) {
        fixed = fixed.replace(arrowMatch[0], `function ${componentName}(`);
        // Remove the => after the params
        fixed = fixed.replace(/\)\s*=>\s*{/, ') {');
        fixed = fixed.replace(/\)\s*=>\s*\(/, ') {\n  return (');
      } else {
        // Wrap the entire code in a function
        fixed = `function ${componentName}() {\n  return (\n    <div className="p-8">\n      <p>Component loading error — please regenerate.</p>\n    </div>\n  );\n}`;
        console.warn(`⚠️ ${componentName}: No function found, using fallback`);
        return fixed;
      }
    }
  }

  // 2. Balance braces and parentheses
  let braceCount = 0;
  let parenCount = 0;
  let bracketCount = 0;
  for (const ch of fixed) {
    if (ch === '{') braceCount++;
    else if (ch === '}') braceCount--;
    else if (ch === '(') parenCount++;
    else if (ch === ')') parenCount--;
    else if (ch === '[') bracketCount++;
    else if (ch === ']') bracketCount--;
  }

  if (braceCount > 0 || parenCount > 0 || bracketCount > 0) {
    console.warn(`⚠️ ${componentName}: Unbalanced delimiters — braces:${braceCount}, parens:${parenCount}, brackets:${bracketCount}. Attempting repair.`);

    // Strategy: try simple appending of closers (works for truncated output)
    if (braceCount > 0 && braceCount <= 5 && parenCount >= 0 && parenCount <= 3 && bracketCount >= 0 && bracketCount <= 2) {
      // Remove any trailing partial JSX tags or expressions
      fixed = fixed.replace(/<[a-zA-Z][^>]*$/m, '');
      fixed = fixed.replace(/\{[^}]*$/m, '');

      // Append closers in logical nesting order
      const closers = ']'.repeat(Math.max(0, bracketCount)) +
        ')'.repeat(Math.max(0, parenCount)) +
        '}'.repeat(Math.max(0, braceCount));
      fixed += '\n' + closers;

      // Re-check balance
      let b = 0, p = 0, k = 0;
      for (const ch of fixed) {
        if (ch === '{') b++; else if (ch === '}') b--;
        if (ch === '(') p++; else if (ch === ')') p--;
        if (ch === '[') k++; else if (ch === ']') k--;
      }

      if (b === 0 && p === 0 && k === 0) {
        console.log(`✅ ${componentName}: Auto-repair succeeded`);
      } else {
        console.warn(`⚠️ ${componentName}: Auto-repair partially failed (b:${b}, p:${p}, k:${k}), using fallback`);
        fixed = createFallbackComponent(componentName);
      }
    } else {
      // Too deeply unbalanced — use fallback
      console.warn(`⚠️ ${componentName}: Too deeply unbalanced, using fallback`);
      fixed = createFallbackComponent(componentName);
    }
  }

  // 3. Check for negative balance (extra closing delimiters)
  let b2 = 0, p2 = 0, k2 = 0;
  for (const ch of fixed) {
    if (ch === '{') b2++; else if (ch === '}') b2--;
    if (ch === '(') p2++; else if (ch === ')') p2--;
    if (ch === '[') k2++; else if (ch === ']') k2--;
  }
  if (b2 !== 0 || p2 !== 0 || k2 !== 0) {
    console.warn(`⚠️ ${componentName}: Final balance check failed (b:${b2}, p:${p2}, k:${k2}), using fallback`);
    fixed = createFallbackComponent(componentName);
  }

  return fixed;
}

function createFallbackComponent(componentName) {
  return `function ${componentName}() {
  return (
    <div className="p-8 text-center">
      <h2 className="text-2xl font-bold text-red-500 mb-4">⚠️ Component Error</h2>
      <p className="text-gray-600">The ${componentName} component could not be generated correctly.</p>
      <p className="text-gray-400 text-sm mt-2">Try regenerating the page or editing with AI.</p>
    </div>
  );
}`;
}

// Multer config for image uploads
const upload = multer({
  storage: multer.diskStorage({
    destination: async (req, file, cb) => {
      const { projectName } = req.body;
      const dir = path.join(__dirname, '../../generated-projects', projectName, 'frontend', 'assets');
      await fs.mkdir(dir, { recursive: true });
      cb(null, dir);
    },
    filename: (req, file, cb) => {
      const ext = path.extname(file.originalname);
      cb(null, `upload-${Date.now()}${ext}`);
    }
  }),
  limits: { fileSize: 10 * 1024 * 1024 } // 10MB limit
});

let nextPort = 3001;

/**
 * Convert a page name (possibly hyphenated/underscored) to PascalCase.
 * e.g. 'product-details' → 'ProductDetails', 'home' → 'Home'
 */
function toPascalCase(str) {
  return str
    .split(/[-_\s]+/)
    .map(part => part.charAt(0).toUpperCase() + part.slice(1).toLowerCase())
    .join('');
}

// ============================================
// COMPONENT EXTRACTION & SPLICE HELPERS
// For surgical edits — extract one component,
// edit it, splice it back without touching the rest
// ============================================

/**
 * Extract a single component's code from the full index.html.
 * Components are delimited by "// ComponentName Component" comment markers.
 * Returns { code, startIndex, endIndex } or null if not found.
 */
function extractComponent(html, componentName) {
  // Find the component's marker comment: "// ComponentName Component"
  const markerPattern = new RegExp(
    `(// ${componentName} Component[^\\n]*\\n)`,
    'i'
  );
  const markerMatch = html.match(markerPattern);
  if (!markerMatch) {
    // Fallback: try to find "function ComponentName(" directly
    const regex = new RegExp(`function\\s+${componentName}\\s*\\(`);
    const match = html.match(regex);
    if (!match) return null;

    const fnIdx = html.indexOf(match[0]);
    if (fnIdx === -1) return null;

    // Walk backwards to find the start of the line
    let startIdx = fnIdx;
    while (startIdx > 0 && html[startIdx - 1] !== '\n') startIdx--;

    // Find the end by brace-matching the function body
    const endIdx = findFunctionEnd(html, fnIdx);
    if (endIdx === -1) return null;

    return {
      code: html.substring(startIdx, endIdx).trim(),
      startIndex: startIdx,
      endIndex: endIdx
    };
  }

  const startIdx = html.indexOf(markerMatch[0]);

  // Find the end of this component by looking for the NEXT component marker or "function App()"
  const searchFrom = startIdx + markerMatch[0].length;
  // Use \r?\n to handle Windows line endings
  const nextMarker = html.substring(searchFrom).search(/\/\/ \w+ Component\r?\n|function\s+App\s*\(/);

  let endIdx;
  if (nextMarker !== -1) {
    endIdx = searchFrom + nextMarker;
  } else {
    // Last component before App — find the function end by brace-matching
    const regex = new RegExp(`function\\s+${componentName}\\s*\\(`);
    const match = html.substring(startIdx).match(regex);
    const fnIdx = match ? startIdx + html.substring(startIdx).indexOf(match[0]) : -1;
    endIdx = fnIdx !== -1 ? findFunctionEnd(html, fnIdx) : html.length;
  }

  // Trim trailing whitespace between components
  while (endIdx > startIdx && (html[endIdx - 1] === '\n' || html[endIdx - 1] === '\r' || html[endIdx - 1] === ' ')) {
    endIdx--;
  }
  endIdx++; // include the final newline

  return {
    code: html.substring(startIdx, endIdx).trim(),
    startIndex: startIdx,
    endIndex: endIdx
  };
}

/**
 * Find the closing brace of a function starting from the 'function' keyword position.
 * Uses brace-counting to handle nested blocks.
 */
function findFunctionEnd(html, fnStart) {
  let braceDepth = 0;
  let started = false;

  for (let i = fnStart; i < html.length; i++) {
    if (html[i] === '{') {
      braceDepth++;
      started = true;
    } else if (html[i] === '}') {
      braceDepth--;
      if (started && braceDepth === 0) {
        return i + 1; // include the closing brace
      }
    }
  }
  return -1;
}

/**
 * Splice a modified component back into the full HTML,
 * replacing only the region between startIndex and endIndex.
 */
function spliceComponent(html, startIndex, endIndex, newComponentCode) {
  return html.substring(0, startIndex) + newComponentCode + html.substring(endIndex);
}

/**
 * Sanitize JSX style attributes in component code.
 * Removes HTML-style style="..." and converts to JSX style={{ }}.
 * (Same logic as in createCompleteHTML, extracted for reuse during edits)
 */
function sanitizeComponentStyles(code) {
  let clean = code;

  // Fix HTML attributes → JSX attributes
  clean = clean.replace(/\bclass=/g, 'className=');
  clean = clean.replace(/\bfor=/g, 'htmlFor=');
  clean = clean.replace(/\btabindex=/gi, 'tabIndex=');
  clean = clean.replace(/\bautocomplete=/gi, 'autoComplete=');
  clean = clean.replace(/\breadonly(?=\s|>|\/>)/gi, 'readOnly');
  clean = clean.replace(/\bmaxlength=/gi, 'maxLength=');
  clean = clean.replace(/\bminlength=/gi, 'minLength=');
  clean = clean.replace(/\bcolspan=/gi, 'colSpan=');
  clean = clean.replace(/\browspan=/gi, 'rowSpan=');
  clean = clean.replace(/\bonclick=/gi, 'onClick=');
  clean = clean.replace(/\bonchange=/gi, 'onChange=');
  clean = clean.replace(/\bonsubmit=/gi, 'onSubmit=');

  // Remove style="..." when a style={{ }} is also present on the same element
  clean = clean.replace(/\s+style="[^"]*"(\s+)/g, (match, trailing, offset, str) => {
    const lineEnd = str.indexOf('>', offset);
    const remaining = str.substring(offset, lineEnd > -1 ? lineEnd : offset + 200);
    if (remaining.includes('style={{') || remaining.includes('style ={{')) {
      return trailing;
    }
    return match;
  });

  // Convert remaining standalone HTML-style="..." to JSX style={{ }}
  clean = clean.replace(/style="([^"]*)"/g, (match, cssStr) => {
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

  return clean;
}

// ============================================
// EDIT MODE - Patch existing pages via LLM
// ============================================
router.post('/edit', async (req, res) => {
  try {
    const { projectName, prompt, targetPage } = req.body;

    if (!projectName || !prompt) {
      return res.status(400).json({ error: 'projectName and prompt are required' });
    }

    console.log('\n✏️ Starting EDIT MODE');
    console.log('Project:', projectName);
    console.log('Target page:', targetPage || '(auto-detect)');
    console.log('Edit prompt:', prompt);

    const projectPath = path.join(__dirname, '../../generated-projects', projectName);
    const frontendPath = path.join(projectPath, 'frontend');

    // Read existing index.html
    const indexPath = path.join(frontendPath, 'index.html');
    if (!(await fileExists(indexPath))) {
      return res.status(400).json({ error: 'Project not found' });
    }

    let existingHtml = await fs.readFile(indexPath, 'utf-8');

    // Try to load the plan metadata if it exists
    let planMeta = { pages: ['index'], features: [] };
    const metaPath = path.join(projectPath, 'plan.json');
    if (await fileExists(metaPath)) {
      try {
        planMeta = JSON.parse(await fs.readFile(metaPath, 'utf-8'));
      } catch (e) {
        console.warn('⚠️ Could not parse plan.json, using defaults');
      }
    }

    // Build instructions list:
    // If targetPage is explicitly provided, use it directly.
    // Otherwise, ask LLaMA to figure out what to edit.
    let editInstructions;
    if (targetPage) {
      // Direct page targeting — fast, no Llama needed
      editInstructions = [{ action: 'create_page', page: targetPage, details: prompt }];
    } else {
      const editPlan = await llamaService.analyzeEditPrompt(prompt, {
        pages: planMeta.pages || ['index'],
        features: planMeta.features || []
      });
      editInstructions = editPlan.instructions;
    }

    // Execute edits — COMPONENT-SCOPED: extract → edit → splice
    for (const instruction of editInstructions) {
      if (instruction.action !== 'create_page') continue;

      const pageName = instruction.page || 'index';
      const componentName = toPascalCase(pageName);

      console.log(`📝 Editing component: ${componentName}`);

      // STEP 1: Extract just this component's code from the full HTML
      const extracted = extractComponent(existingHtml, componentName);

      if (!extracted) {
        console.warn(`⚠️ Component "${componentName}" not found in HTML, skipping`);
        continue;
      }

      console.log(`📦 Extracted ${componentName}: ${extracted.code.length} chars (positions ${extracted.startIndex}-${extracted.endIndex})`);

      // STEP 2: Send ONLY the component code to Gemini
      let updatedCode;
      try {
        updatedCode = await geminiService.executeInstruction(
          instruction,
          planMeta,
          null,
          {
            mode: 'edit',
            existingCode: extracted.code
          }
        );
      } catch (editErr) {
        console.error(`❌ Gemini edit failed for ${componentName}:`, editErr.message);
        continue; // Keep original code, skip this component
      }

      // STEP 3: Validate and Sanitize the returned code
      let validatedCode = validateAndFixComponent(updatedCode, componentName);
      let sanitizedCode = sanitizeComponentStyles(validatedCode);

      // STEP 3b: Verify the edited code is not a fallback placeholder
      // If it is, keep the original code
      if (sanitizedCode.includes('Component Error') || sanitizedCode.includes('could not be generated')) {
        console.warn(`⚠️ ${componentName}: Edit produced invalid code, keeping original`);
        continue;
      }

      // STEP 3c: Verify brace balance of the edited code before splicing
      let b = 0, p = 0, k = 0;
      for (const ch of sanitizedCode) {
        if (ch === '{') b++; else if (ch === '}') b--;
        if (ch === '(') p++; else if (ch === ')') p--;
        if (ch === '[') k++; else if (ch === ']') k--;
      }
      if (b !== 0 || p !== 0 || k !== 0) {
        console.warn(`⚠️ ${componentName}: Edited code has unbalanced delimiters (b:${b}, p:${p}, k:${k}), keeping original`);
        continue;
      }

      // Ensure the component marker comment is preserved
      if (!sanitizedCode.startsWith('// ' + componentName)) {
        sanitizedCode = '// ' + componentName + ' Component\n' + sanitizedCode;
      }

      // STEP 4: Splice the modified component back into the full HTML
      existingHtml = spliceComponent(
        existingHtml,
        extracted.startIndex,
        extracted.endIndex,
        sanitizedCode
      );

      console.log(`✅ Spliced updated ${componentName} back into HTML`);
    }

    // Write the updated HTML
    await fs.writeFile(indexPath, existingHtml);
    console.log('💾 Saved updated index.html');

    res.json({
      success: true,
      projectName,
      previewUrl: `/api/preview/${projectName}`
    });

  } catch (error) {
    console.error('❌ Edit error:', error);
    res.status(500).json({ error: error.message });
  }
});


// ============================================
// PER-PAGE REGENERATION
// ============================================
router.post('/regenerate-page', async (req, res) => {
  try {
    const { projectName, pageName } = req.body;
    if (!projectName || !pageName) return res.status(400).json({ error: 'projectName and pageName are required' });

    const projectPath = path.join(__dirname, '../../generated-projects', projectName);

    // Load the existing plan
    const plan = JSON.parse(await fs.readFile(path.join(projectPath, 'plan.json'), 'utf8'));

    // Load all existing component files
    const componentsDir = path.join(projectPath, 'components');
    const existingFrontend = {};
    try {
      const compFiles = await fs.readdir(componentsDir);
      for (const file of compFiles) {
        if (file.endsWith('.jsx')) {
          existingFrontend[file] = await fs.readFile(path.join(componentsDir, file), 'utf8');
        }
      }
    } catch {
      // components dir doesn't exist for old projects — graceful degradation
      console.warn(`⚠️ No components/ dir for ${projectName}. Regenerating without existing pages.`);
    }

    // Regenerate just the requested page via Gemini
    const instruction = {
      step: 1, action: 'create_page', page: pageName, priority: 'high',
      details: plan.pageDescriptions?.[pageName] || `${pageName} page for ${plan.description}`
    };
    const context = { schema: null, tableName: null, columns: [], apiEndpoints: [], backendPort: null };
    console.log(`🔄 Regenerating page: ${pageName} for project: ${projectName}`);
    const code = await geminiService.executeInstruction(instruction, plan, null, context);
    const compName = toPascalCase(pageName);
    const newCode = validateAndFixComponent(code, compName);

    // Save updated component
    existingFrontend[`${pageName}.jsx`] = newCode;
    await fs.mkdir(componentsDir, { recursive: true });
    await fs.writeFile(path.join(componentsDir, `${pageName}.jsx`), newCode);

    // Rebuild the full HTML with all pages (old ones preserved, new one replaced)
    const metadata = { tableName: null, apiEndpoints: [], columns: [] };
    const newHtml = createCompleteHTML(plan, existingFrontend, null, metadata);
    await fs.writeFile(path.join(projectPath, 'frontend', 'index.html'), newHtml);

    console.log(`✅ Page "${pageName}" regenerated for ${projectName}`);
    res.json({ success: true, previewUrl: `/api/preview/${projectName}`, html: newHtml });
  } catch (err) {
    console.error('❌ Regenerate-page error:', err);
    res.status(500).json({ error: err.message });
  }
});

// ============================================
// PROJECT LISTING & DELETION (for Gallery)
// ============================================
router.get('/projects', async (req, res) => {
  try {
    const projectsRoot = path.join(__dirname, '../../generated-projects');
    let entries = [];
    try { entries = await fs.readdir(projectsRoot); } catch { return res.json({ projects: [] }); }

    const projects = (await Promise.all(
      entries.map(async (name) => {
        try {
          const planPath = path.join(projectsRoot, name, 'plan.json');
          const raw = await fs.readFile(planPath, 'utf8');
          const plan = JSON.parse(raw);
          const stat = await fs.stat(planPath);
          return {
            projectName: plan.projectName || name,
            description: plan.description || '',
            pages: plan.pages || [],
            style: plan.styleTokens?.style || 'modern',
            palette: plan.styleTokens?.palette || {},
            styleTokens: plan.styleTokens || {},
            needsDatabase: plan.needsDatabase || false,
            createdAt: stat.mtime.toISOString(),
            previewUrl: `/api/preview/${plan.projectName || name}`
          };
        } catch { return null; }
      })
    )).filter(Boolean).sort((a, b) => new Date(b.createdAt) - new Date(a.createdAt));

    res.json({ projects });
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

router.delete('/projects/:name', async (req, res) => {
  try {
    const { name } = req.params;
    if (!name || name.includes('..')) return res.status(400).json({ error: 'Invalid project name' });
    const projectPath = path.join(__dirname, '../../generated-projects', name);
    await fs.rm(projectPath, { recursive: true, force: true });
    res.json({ success: true });
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

// ============================================
// STREAMING GENERATE — Server-Sent Events
// Emits: plan → artifact (per page) → done
// ============================================
router.post('/stream-website', async (req, res) => {
  // Set SSE headers
  res.setHeader('Content-Type', 'text/event-stream');
  res.setHeader('Cache-Control', 'no-cache');
  res.setHeader('Connection', 'keep-alive');
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.flushHeaders();

  const sendEvent = (event, data) => {
    try {
      res.write(`event: ${event}\ndata: ${JSON.stringify(data)}\n\n`);
    } catch (e) { /* client disconnected */ }
  };

  const sendProgress = (message, index, total) => {
    sendEvent('progress', { message, index, total });
  };

  try {
    const { prompt, dbConfig, chatHistory } = req.body;
    if (!prompt) { sendEvent('error', { error: 'Prompt is required' }); return res.end(); }

    // ---------- STEP 1: LLAMA PLANNING ----------
    sendProgress('Analyzing your idea...', 0, 1);
    const plan = await llamaService.analyzePrompt(prompt, chatHistory || []);
    sendEvent('plan', { plan });
    console.log('✅ [SSE] Plan ready:', plan.projectName);

    const backendPort = plan.needsDatabase ? nextPort++ : null;
    const effectiveDbConfig = plan.needsDatabase
      ? (dbConfig && dbConfig.password ? dbConfig
        : { host: 'localhost', port: '5432', user: 'postgres', password: 'postgres', database: 'postgres' })
      : null;

    const generatedCode = {
      frontend: {},
      backend: {},
      database: {},
      metadata: { tableName: null, apiEndpoints: [], columns: [] }
    };

    if (plan.apiContract?.tables?.length > 0) {
      const t = plan.apiContract.tables[0];
      generatedCode.metadata.tableName = t.name;
      generatedCode.metadata.columns = t.columns.map(c => c.name);
      generatedCode.metadata.apiEndpoints = (plan.apiContract.endpoints || []).map(ep => `${ep.method} ${ep.path}`);
    }

    // Count only page instructions for UX progress display
    const pageInstructions = plan.instructions.filter(i => i.action === 'create_page');
    const seqInstructions = plan.instructions.filter(i => i.action !== 'create_page');
    const totalPageSteps = pageInstructions.length;
    let pagesDone = 0;
    const totalSteps = plan.instructions.length;

    // ---- PHASE 1: Sequential (schema + API must come before pages) ----
    for (let i = 0; i < seqInstructions.length; i++) {
      const instruction = seqInstructions[i];
      const stepLabel = instruction.action === 'create_database_schema'
        ? 'Creating database schema...'
        : 'Building API routes...';
      sendProgress(stepLabel, i + 1, totalSteps);

      const context = {
        schema: generatedCode.database['schema.sql'] || null,
        tableName: generatedCode.metadata.tableName,
        columns: generatedCode.metadata.columns,
        apiEndpoints: generatedCode.metadata.apiEndpoints,
        backendPort
      };

      const code = await geminiService.executeInstruction(instruction, plan, effectiveDbConfig, context);

      // Delay between Gemini calls to avoid rate limits
      if (i < seqInstructions.length - 1) {
        await new Promise(r => setTimeout(r, 2000));
      }

      if (instruction.action === 'create_database_schema') {
        generatedCode.database['schema.sql'] = code;
        if (!generatedCode.metadata.tableName) {
          const m = code.match(/CREATE TABLE IF NOT EXISTS (\w+)/i);
          if (m) generatedCode.metadata.tableName = m[1];
        }
        sendEvent('artifact', { type: 'schema', name: 'schema', content: code, index: i + 1, total: totalSteps });
      } else if (instruction.action === 'create_api') {
        generatedCode.backend['routes.js'] = code;
        sendEvent('artifact', { type: 'api', name: 'api', content: code, index: i + 1, total: totalSteps });
      }
    }

    // ---- PHASE 2: Pages (sequential to avoid Gemini rate limits) ----
    // Use concurrency of 1 to avoid 429 rate limit errors
    const CONCURRENCY = 1;
    let running = 0;
    const semQueue = [];
    const acquire = () => new Promise(res => {
      if (running < CONCURRENCY) { running++; res(); }
      else semQueue.push(res);
    });
    const release = () => {
      running--;
      // Stagger releases by 2s to avoid Gemini rate limits
      if (semQueue.length > 0) {
        setTimeout(() => { running++; semQueue.shift()(); }, 2000);
      }
    };

    const seqDone = seqInstructions.length;
    // Snapshot context once sequential phase is done (pages read from this)
    const pageContext = {
      schema: generatedCode.database['schema.sql'] || null,
      tableName: generatedCode.metadata.tableName,
      columns: generatedCode.metadata.columns,
      apiEndpoints: generatedCode.metadata.apiEndpoints,
      backendPort
    };

    sendProgress(`Building ${totalPageSteps} pages in parallel...`, seqDone + 1, totalSteps);

    await Promise.allSettled(pageInstructions.map(async (instruction, idx) => {
      await acquire();
      try {
        sendProgress(`Building "${instruction.page}" page...`, seqDone + idx + 1, totalSteps);
        const code = await geminiService.executeInstruction(instruction, plan, effectiveDbConfig, pageContext);
        const compName = toPascalCase(instruction.page);
        generatedCode.frontend[`${instruction.page}.jsx`] = validateAndFixComponent(code, compName);
        // Delay between page calls to avoid Gemini rate limits
        await new Promise(r => setTimeout(r, 2000));
        pagesDone++;

        // Build a snapshot of HTML with whatever pages are done so far
        const partialHtml = createCompleteHTML(plan, generatedCode.frontend, backendPort, generatedCode.metadata);
        sendEvent('artifact', {
          type: 'page',
          name: instruction.page,
          content: partialHtml,
          index: seqDone + idx + 1,
          total: totalSteps,
          pagesDone,
          totalPages: totalPageSteps
        });
        console.log(`✅ [SSE] Page artifact: ${instruction.page} (${pagesDone}/${totalPageSteps})`);
      } catch (pageErr) {
        console.error(`❌ [SSE] Page error: ${instruction.page}`, pageErr.message);
        sendEvent('progress', { message: `⚠️ "${instruction.page}" failed, skipping...`, index: seqDone + idx + 1, total: totalSteps });
      } finally {
        release();
      }
    }));

    // Safety net: generate any pages that were missed or failed
    const generatedPageNames = Object.keys(generatedCode.frontend).map(f => f.replace('.jsx', ''));
    const missingPages = plan.pages.filter(p => !generatedPageNames.includes(p));
    if (missingPages.length > 0) {
      sendProgress(`Recovering ${missingPages.length} failed page(s)...`, totalSteps, totalSteps);
      for (const pageName of missingPages) {
        try {
          const recoverInstruction = {
            step: 99, action: 'create_page', page: pageName, priority: 'high',
            details: plan.pageDescriptions?.[pageName] || `${pageName} page for ${plan.description}`
          };
          const code = await geminiService.executeInstruction(recoverInstruction, plan, effectiveDbConfig, pageContext);
          generatedCode.frontend[`${pageName}.jsx`] = validateAndFixComponent(code, toPascalCase(pageName));
          // Delay between recovery calls to avoid rate limits
          await new Promise(r => setTimeout(r, 2000));
          pagesDone++;
          const partialHtml = createCompleteHTML(plan, generatedCode.frontend, backendPort, generatedCode.metadata);
          sendEvent('artifact', {
            type: 'page', name: pageName, content: partialHtml,
            index: totalSteps, total: totalSteps, pagesDone, totalPages: totalPageSteps
          });
        } catch (recoverErr) {
          console.error(`❌ [SSE] Recovery failed for ${pageName}:`, recoverErr.message);
        }
      }
    }


    // ---------- STEP 3: ASSEMBLE & WRITE FILES ----------
    sendProgress('Assembling project files...', totalSteps, totalSteps);
    const project = await assembleProject(plan, generatedCode, effectiveDbConfig, backendPort);
    const projectPath = path.join(__dirname, '../../generated-projects', plan.projectName);
    await createProjectFiles(projectPath, project, plan, generatedCode.frontend);

    if (plan.needsDatabase && effectiveDbConfig) {
      sendProgress('Installing backend dependencies...', totalSteps, totalSteps);
      await installDependencies(projectPath);
      sendProgress('Starting project backend...', totalSteps, totalSteps);
      startBackend(projectPath, backendPort);
    }

    // Send final assembled HTML (clean/complete version from disk)
    const finalHtml = project.frontend['index.html'];
    sendEvent('done', {
      success: true,
      plan,
      project,
      projectPath,
      finalHtml,
      previewUrl: `/api/preview/${plan.projectName}`,
      backendPort,
      metadata: generatedCode.metadata
    });

    console.log('✅ [SSE] Generation complete:', plan.projectName);
    res.end();

  } catch (error) {
    console.error('❌ [SSE] Generation error:', error);
    sendEvent('error', { error: error.message });
    res.end();
  }
});

// ============================================
// GENERATE MODE - Full website generation
// ============================================
router.post('/website', async (req, res) => {
  try {
    const { prompt, dbConfig, chatHistory } = req.body;

    if (!prompt) {
      return res.status(400).json({ error: 'Prompt is required' });
    }

    console.log('\n📝 Starting Two-LLM Generation WITH API CONTRACT');
    console.log('User prompt:', prompt);

    // STEP 1: LLaMA creates plan with API contract + style tokens
    console.log('\n🦙 STEP 1: Llama Planning with API Contract...');
    const plan = await llamaService.analyzePrompt(prompt, chatHistory || []);
    console.log('✅ Plan created:', {
      project: plan.projectName,
      pages: plan.pages,
      needsDB: plan.needsDatabase,
      style: plan.styleTokens?.style,
      endpoints: plan.apiContract?.endpoints?.length || 0
    });

    const backendPort = plan.needsDatabase ? nextPort++ : null;

    // STEP 2: Gemini executes with FULL CONTEXT from API contract
    console.log('\n🤖 STEP 2: Gemini Execution WITH API CONTRACT...');

    // Use provided dbConfig or fallback defaults for backend generation
    const effectiveDbConfig = plan.needsDatabase
      ? (dbConfig && dbConfig.password
        ? dbConfig
        : { host: 'localhost', port: '5432', user: 'postgres', password: 'postgres', database: 'postgres' })
      : null;

    const generatedCode = {
      frontend: {},
      backend: {},
      database: {},
      metadata: {
        tableName: null,
        apiEndpoints: [],
        columns: []
      }
    };

    // Use API contract for metadata if available
    if (plan.apiContract && plan.apiContract.tables && plan.apiContract.tables.length > 0) {
      const primaryTable = plan.apiContract.tables[0];
      generatedCode.metadata.tableName = primaryTable.name;
      generatedCode.metadata.columns = primaryTable.columns.map(c => c.name);
      generatedCode.metadata.apiEndpoints = (plan.apiContract.endpoints || []).map(
        ep => `${ep.method} ${ep.path}`
      );
    }

    // Execute instructions IN ORDER, passing context
    for (const instruction of plan.instructions) {
      console.log(`\n📝 Step ${instruction.step}: ${instruction.action}`);

      // Build context from previous steps + API contract
      const context = {
        schema: generatedCode.database['schema.sql'] || null,
        tableName: generatedCode.metadata.tableName,
        columns: generatedCode.metadata.columns,
        apiEndpoints: generatedCode.metadata.apiEndpoints,
        backendPort: backendPort
      };

      const code = await geminiService.executeInstruction(
        instruction,
        plan,
        effectiveDbConfig,
        context
      );

      console.log(`✅ Generated ${code.length} characters`);

      // Store generated code
      if (instruction.action === 'create_database_schema') {
        generatedCode.database['schema.sql'] = code;

        // Extract table name from SQL if not from contract
        if (!generatedCode.metadata.tableName) {
          const tableMatch = code.match(/CREATE TABLE IF NOT EXISTS (\w+)/i);
          if (tableMatch) {
            generatedCode.metadata.tableName = tableMatch[1];
          }
        }

        // Cross-validate: warn if generated schema columns differ from contract
        if (plan.apiContract && plan.apiContract.tables && plan.apiContract.tables.length > 0) {
          const contractCols = plan.apiContract.tables[0].columns.map(c => c.name.toLowerCase());
          // Extract column names from the generated SQL
          const sqlColMatches = code.match(/^\s+(\w+)\s+(?:SERIAL|VARCHAR|TEXT|INTEGER|INT|DECIMAL|BOOLEAN|TIMESTAMP|DATE|BIGINT|FLOAT|DOUBLE|NUMERIC|REAL|SMALLINT|UUID|CHAR|JSON|JSONB)/gim);
          if (sqlColMatches) {
            const sqlCols = sqlColMatches.map(m => m.trim().split(/\s+/)[0].toLowerCase());
            const extraInSql = sqlCols.filter(c => !contractCols.includes(c) && c !== 'created_at' && c !== 'updated_at');
            const missingFromSql = contractCols.filter(c => !sqlCols.includes(c) && !c.includes('serial'));
            if (extraInSql.length > 0) {
              console.warn(`⚠️ Schema has extra columns not in contract: ${extraInSql.join(', ')}. Contract columns will be used for API & pages.`);
            }
            if (missingFromSql.length > 0) {
              console.warn(`⚠️ Schema is missing contract columns: ${missingFromSql.join(', ')}. Contract columns will be used for API & pages.`);
            }
          }
        }

      } else if (instruction.action === 'create_api') {
        generatedCode.backend['routes.js'] = code;

      } else if (instruction.action === 'create_page') {
        const fileName = `${instruction.page}.jsx`;
        const compName = toPascalCase(instruction.page);
        generatedCode.frontend[fileName] = validateAndFixComponent(code, compName);
        console.log(`📄 Created page: ${instruction.page}`);
      }
    }

    // ===================================================
    // SAFETY NET: Generate any pages that LLaMA forgot to
    // include in its instructions array
    // ===================================================
    const generatedPageNames = Object.keys(generatedCode.frontend).map(f => f.replace('.jsx', ''));
    const missingPages = plan.pages.filter(p => !generatedPageNames.includes(p));

    if (missingPages.length > 0) {
      console.log(`\n⚠️  SAFETY NET: Generating ${missingPages.length} missing page(s): ${missingPages.join(', ')}`);
      for (const pageName of missingPages) {
        const pageInstruction = {
          step: 99,
          action: 'create_page',
          page: pageName,
          priority: 'high',
          details: (plan.pageDescriptions && plan.pageDescriptions[pageName]) || `${pageName} page for ${plan.description}`
        };
        const context = {
          schema: generatedCode.database['schema.sql'] || null,
          tableName: generatedCode.metadata.tableName,
          columns: generatedCode.metadata.columns,
          apiEndpoints: generatedCode.metadata.apiEndpoints,
          backendPort: backendPort
        };
        console.log(`  🔧 Auto-generating missing page: ${pageName}`);
        const code = await geminiService.executeInstruction(pageInstruction, plan, effectiveDbConfig, context);
        const compName = toPascalCase(pageName);
        generatedCode.frontend[`${pageName}.jsx`] = validateAndFixComponent(code, compName);
        console.log(`  ✅ Auto-generated page: ${pageName}`);
      }
    }

    console.log('\n📦 STEP 3: Assembling project...');
    const project = await assembleProject(plan, generatedCode, effectiveDbConfig, backendPort);

    console.log('\n💾 STEP 4: Creating files...');
    const projectPath = path.join(__dirname, '../../generated-projects', plan.projectName);
    await createProjectFiles(projectPath, project, plan, generatedCode.frontend);

    if (plan.needsDatabase && effectiveDbConfig) {
      console.log('\n📦 Installing dependencies...');
      await installDependencies(projectPath);

      console.log(`\n🚀 Starting backend on port ${backendPort}...`);
      startBackend(projectPath, backendPort);
    }

    console.log('\n✅ Generation complete!');

    res.json({
      success: true,
      plan: plan,
      project: project,
      projectPath: projectPath,
      previewUrl: `/api/preview/${plan.projectName}`,
      backendPort: backendPort,
      metadata: generatedCode.metadata
    });

  } catch (error) {
    console.error('❌ Generation error:', error);
    res.status(500).json({
      success: false,
      error: error.message
    });
  }
});

// ============================================
// ASSEMBLE PROJECT
// ============================================
async function assembleProject(plan, generatedCode, dbConfig, backendPort) {
  const html = createCompleteHTML(plan, generatedCode.frontend, backendPort, generatedCode.metadata);
  const backend = plan.needsDatabase
    ? createCompleteBackend(plan, generatedCode.backend, generatedCode.database, dbConfig, backendPort)
    : null;

  return {
    projectName: plan.projectName,
    description: plan.description,
    frontend: { 'index.html': html },
    backend: backend ? { 'server.js': backend } : null,
    database: generatedCode.database
  };
}

// ============================================
// HTML TEMPLATE - Style-token-aware, multi-page
// ============================================
function createCompleteHTML(plan, pages, backendPort, metadata) {
  const styleTokens = plan.styleTokens || {};
  const palette = styleTokens.palette || {};
  const fontFamily = styleTokens.fontFamily || 'Inter';
  const isDark = styleTokens.theme === 'dark';

  const pageComponents = Object.entries(pages).map(([filename, code]) => {
    const baseName = filename.replace('.jsx', '');
    const componentName = toPascalCase(baseName);

    let cleanCode = code
      .replace(/import.*from.*['"];?\n?/g, '')
      .replace(/export default.*;?\n?/g, '')
      .replace(/export\s+{[^}]*}\s*;?\n?/g, '')
      .replace(/^'use client';?\s*$/gm, '')
      .replace(/^"use client";?\s*$/gm, '')
      .trim();

    const lowerName = baseName.toLowerCase();

    // ==========================================
    // FIX: Ensure all JSX attributes are correct
    // ==========================================
    // Convert HTML attributes to JSX
    cleanCode = cleanCode.replace(/\bclass=/g, 'className=');
    cleanCode = cleanCode.replace(/\bfor=/g, 'htmlFor=');
    cleanCode = cleanCode.replace(/\btabindex=/gi, 'tabIndex=');
    cleanCode = cleanCode.replace(/\bautocomplete=/gi, 'autoComplete=');
    cleanCode = cleanCode.replace(/\breadonly(?=\s|>|\/>)/gi, 'readOnly');
    cleanCode = cleanCode.replace(/\bmaxlength=/gi, 'maxLength=');
    cleanCode = cleanCode.replace(/\bminlength=/gi, 'minLength=');
    cleanCode = cleanCode.replace(/\bcolspan=/gi, 'colSpan=');
    cleanCode = cleanCode.replace(/\browspan=/gi, 'rowSpan=');
    cleanCode = cleanCode.replace(/\bonclick=/gi, 'onClick=');
    cleanCode = cleanCode.replace(/\bonchange=/gi, 'onChange=');
    cleanCode = cleanCode.replace(/\bonsubmit=/gi, 'onSubmit=');

    // Convert HTML-style style="..." to JSX style={{ }}
    // First remove style="..." when style={{ }} also exists on the same element
    cleanCode = cleanCode.replace(/\s+style="[^"]*"(\s+)/g, (match, trailing, offset, str) => {
      const lineEnd = str.indexOf('>', offset);
      const remaining = str.substring(offset, lineEnd > -1 ? lineEnd : offset + 200);
      if (remaining.includes('style={{') || remaining.includes('style ={{')) {
        return trailing;
      }
      return match;
    });
    // Convert remaining standalone style="..." to JSX style={{ }}
    cleanCode = cleanCode.replace(/style="([^"]*)"/g, (match, cssStr) => {
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

    // Handle arrow function components: convert to function declarations
    // Pattern 1: const Name = () => {
    cleanCode = cleanCode.replace(
      new RegExp(`const\\s+(?:${componentName}|${lowerName}|${baseName})\\s*=\\s*\\(([^)]*)\\)\\s*=>\\s*\\{`, 'g'),
      (_, params) => `function ${componentName}(${params}) {`
    );
    // Pattern 2: const Name = () => (  — implicit return
    cleanCode = cleanCode.replace(
      new RegExp(`const\\s+(?:${componentName}|${lowerName}|${baseName})\\s*=\\s*\\(([^)]*)\\)\\s*=>\\s*\\(`, 'g'),
      (_, params) => `function ${componentName}(${params}) {\n  return (`
    );

    // Handle function declarations with wrong names
    cleanCode = cleanCode
      .split('function ' + baseName + '(').join('function ' + componentName + '(')
      .split('function ' + lowerName + '(').join('function ' + componentName + '(')
      .split('function ' + baseName + ' (').join('function ' + componentName + '(')
      .split('function ' + lowerName + ' (').join('function ' + componentName + '(');

    // Last resort: rename the very first function or const arrow declaration
    if (cleanCode.indexOf('function ' + componentName + '(') === -1) {
      cleanCode = cleanCode.replace(/const\s+\w+\s*=\s*\(/, 'function ' + componentName + '(');
      if (cleanCode.indexOf('function ' + componentName + '(') === -1) {
        cleanCode = cleanCode.replace(/function\s+\w+\s*\(/, 'function ' + componentName + '(');
      }
    }

    // Fix any remaining "function X() =>" hybrids from partial conversion
    cleanCode = cleanCode.replace(
      new RegExp(`function\\s+${componentName}\\s*\\(([^)]*)\\)\\s*=>\\s*\\{`),
      `function ${componentName}($1) {`
    );
    cleanCode = cleanCode.replace(
      new RegExp(`function\\s+${componentName}\\s*\\(([^)]*)\\)\\s*=>\\s*\\(`),
      `function ${componentName}($1) {\n  return (`
    );

    // POST-CLEANUP VALIDATION: Check brace/paren balance after all transformations
    let b = 0, p = 0, k = 0;
    for (const ch of cleanCode) {
      if (ch === '{') b++; else if (ch === '}') b--;
      if (ch === '(') p++; else if (ch === ')') p--;
      if (ch === '[') k++; else if (ch === ']') k--;
    }

    if (b !== 0 || p !== 0 || k !== 0) {
      console.warn(`⚠️ ${componentName}: Post-cleanup unbalanced — braces:${b}, parens:${p}, brackets:${k}.`);
      // Try to fix by appending closers (for small imbalances)
      if (b > 0 && b <= 3 && p >= 0 && p <= 2 && k >= 0 && k <= 1) {
        cleanCode = cleanCode.trimEnd() + '\n' +
          ']'.repeat(Math.max(0, k)) +
          ')'.repeat(Math.max(0, p)) +
          '}'.repeat(Math.max(0, b));
        console.log(`✅ ${componentName}: Auto-repaired in createCompleteHTML`);
      } else {
        console.warn(`⚠️ ${componentName}: Using fallback.`);
        cleanCode = createFallbackComponent(componentName);
      }
    }

    return '// ' + componentName + ' Component\n' + cleanCode;
  }).join('\n\n');

  const apiUrl = backendPort ? `http://localhost:${backendPort}` : '';

  // Build navigation with proper page names
  const navButtons = plan.pages.map(page => {
    const displayName = page.charAt(0).toUpperCase() + page.slice(1).replace(/[-_]/g, ' ');
    return `<button 
                onClick={() => setCurrentPage('${page}')}
                className={\`px-4 py-2 rounded-lg transition-all duration-300 font-semibold \${currentPage === '${page}' ? 'active-nav' : 'inactive-nav'}\`}
              >
                ${displayName}
              </button>`;
  }).join('\n                    ');

  // Build page rendering logic
  const pageRendering = plan.pages.map(page => {
    const componentName = toPascalCase(page);
    return `if (currentPage === '${page}') {
                if (typeof ${componentName} === 'undefined') {
                  return <div className="p-8 text-center text-red-600">Error: ${componentName} component not found.</div>;
                }
                return <${componentName} setCurrentPage={setCurrentPage} />;
              }`;
  }).join('\n              ');

  // Build custom CSS based on style tokens
  const customCSS = `
    <style>
      @import url('https://fonts.googleapis.com/css2?family=${fontFamily.replace(/\s+/g, '+')}:wght@300;400;500;600;700;800;900&display=swap');
      
      :root {
        --wg-font: '${fontFamily}', sans-serif;
        --wg-primary: ${palette.primary || '#6366f1'};
        --wg-bg: ${isDark ? '#0f172a' : (palette.background || '#f8fafc')};
        --wg-text: ${isDark ? '#e2e8f0' : (palette.text || '#1e293b')};
      }
      
      * { font-family: var(--wg-font); }
      
      body {
        background-color: var(--wg-bg);
        color: var(--wg-text);
        transition: background-color 0.3s ease, color 0.3s ease;
      }
      
      /* Theme overrides — applied via postMessage from toolbar */
      [data-theme="dark"] body  { background-color: #0f172a !important; color: #e2e8f0 !important; }
      [data-theme="dark"] .page-container { background-color: #1e293b !important; }
      [data-theme="light"] body { background-color: ${palette.background || '#f8fafc'} !important; color: ${palette.text || '#1e293b'} !important; }
      [data-theme="light"] .page-container { background-color: white !important; }
      
      .nav-bar {
        background: linear-gradient(135deg, ${palette.primary || '#6366f1'}, ${palette.secondary || '#8b5cf6'});
      }
      
      .active-nav {
        background-color: white;
        color: ${palette.primary || '#6366f1'};
      }
      
      .inactive-nav {
        background-color: ${palette.primary || '#6366f1'}88;
        color: white;
      }
      
      .inactive-nav:hover {
        background-color: ${palette.primary || '#6366f1'}cc;
      }

      .page-container {
        background-color: ${isDark ? '#1e293b' : 'white'};
        min-height: calc(100vh - 80px);
      }
      
      ${styleTokens.style === 'glassmorphism' ? `
      .glass-card {
        background: rgba(255, 255, 255, 0.1);
        backdrop-filter: blur(10px);
        border: 1px solid rgba(255, 255, 255, 0.2);
        border-radius: 16px;
      }` : ''}
    </style>`;

  return `<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>${plan.description}</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <script crossorigin src="https://unpkg.com/react@18/umd/react.development.js"></script>
    <script crossorigin src="https://unpkg.com/react-dom@18/umd/react-dom.development.js"></script>
    <script crossorigin src="https://unpkg.com/@babel/standalone/babel.min.js"></script>
    ${customCSS}
</head>
<body>
    <div id="root"><p style="padding:2rem;color:#888;">Loading...</p></div>

    <!-- Global error handler: catches Babel transpilation errors -->
    <script>
      window.onerror = function(msg, url, line, col, err) {
        var root = document.getElementById('root');
        if (root) {
          var displayMsg = msg;
          var displayLine = line;
          // "Script error." at line 0 means a cross-origin error hid the details
          if (line === 0 && (msg === 'Script error.' || msg === 'Script error')) {
            displayMsg = 'Babel transpilation failed — the generated JSX may contain syntax errors.';
            displayLine = '?';
          }
          root.innerHTML = '<div style="padding:2rem;font-family:monospace;">' +
            '<h2 style="color:#ef4444;font-size:1.5rem;margin-bottom:1rem;">⚠️ Page Rendering Error</h2>' +
            '<p style="color:#f97316;margin-bottom:0.5rem;">Line ' + displayLine + ': ' + displayMsg + '</p>' +
            '<pre style="background:#1e293b;color:#e2e8f0;padding:1rem;border-radius:8px;overflow:auto;font-size:0.85rem;max-height:300px;">' +
            (err && err.stack ? err.stack : 'No stack trace available. Check the browser console (F12) for details.') + '</pre>' +
            '<p style="color:#94a3b8;margin-top:1rem;font-size:0.9rem;">Try editing with AI or regenerating the page.</p>' +
            '</div>';
        }
        return true;
      };
    </script>

    <!-- Navigation bridge: intercepts all <a> clicks and routes to SPA pages -->
    <!-- Also handles postMessages from the toolbar (navigate, theme, font) -->
    <script>
      var __wgPages = ${JSON.stringify(plan.pages)};

      // Fuzzy-match a URL path segment to the nearest page name
      function __wgMatchPage(href) {
        if (!href || href === '#' || href.startsWith('mailto') || href.startsWith('http')) return null;
        var slug = href.replace(/^\/+/, '').toLowerCase()
                       .replace(/[-_\s]/g, '').split('/').filter(Boolean).pop() || '';
        if (!slug) return null;
        return __wgPages.find(function(p) {
          var pn = p.toLowerCase().replace(/[-_\s]/g, '');
          return pn === slug || pn.startsWith(slug) || slug.startsWith(pn) || pn.includes(slug) || slug.includes(pn);
        }) || null;
      }

      // Capture-phase click interceptor — runs before React event handlers
      document.addEventListener('click', function(e) {
        var anchor = e.target.closest('a[href]');
        if (!anchor) return;
        var match = __wgMatchPage(anchor.getAttribute('href'));
        if (match && window.__wgNavigate) {
          e.preventDefault();
          e.stopPropagation();
          window.__wgNavigate(match);
        }
      }, true);

      // postMessage API — used by the toolbar chips and style toggles
      window.addEventListener('message', function(e) {
        if (!e.data) return;
        if (e.data.type === 'WG_NAVIGATE' && e.data.page && window.__wgNavigate) {
          window.__wgNavigate(e.data.page);
        }
        if (e.data.type === 'WG_SET_THEME') {
          document.documentElement.setAttribute('data-theme', e.data.theme);
        }
        if (e.data.type === 'WG_SET_FONT') {
          document.documentElement.style.setProperty('--wg-font', e.data.font + ', sans-serif');
          // Force all elements to pick up the new CSS variable
          document.body.style.fontFamily = e.data.font + ', sans-serif';
        }
      });
    </script>

    <script type="text/babel" data-type="module">
        const { useState, useEffect } = React;
        
        // API Configuration
        const API_URL = '${apiUrl}';

        // Error Boundary to catch React render errors
        class ErrorBoundary extends React.Component {
          constructor(props) {
            super(props);
            this.state = { hasError: false, error: null };
          }
          static getDerivedStateFromError(error) {
            return { hasError: true, error };
          }
          componentDidCatch(error, info) {
            console.error('React Error Boundary caught:', error, info);
          }
          render() {
            if (this.state.hasError) {
              return (
                <div style={{ padding: '2rem', fontFamily: 'monospace' }}>
                  <h2 style={{ color: '#ef4444', fontSize: '1.5rem', marginBottom: '1rem' }}>⚠️ Component Render Error</h2>
                  <p style={{ color: '#f97316' }}>{this.state.error?.message || 'Unknown error'}</p>
                  <p style={{ color: '#94a3b8', marginTop: '1rem', fontSize: '0.9rem' }}>Try editing with AI or regenerating the page.</p>
                </div>
              );
            }
            return this.props.children;
          }
        }

        ${pageComponents}

        function App() {
            const [currentPage, setCurrentPage] = useState('${plan.pages[0]}');

            // Expose navigation globally so any component or the toolbar can navigate
            React.useEffect(() => {
              window.__wgNavigate = setCurrentPage;
              // Notify parent frame of current page (used by toolbar chips)
              try { window.parent.postMessage({ type: 'WG_PAGE_CHANGED', page: currentPage }, '*'); } catch(e) {}
              return () => { window.__wgNavigate = null; };
            }, [currentPage]);

            const Navigation = () => (
                <nav className="nav-bar text-white p-4 shadow-xl">
                    <div className="container mx-auto flex justify-between items-center">
                        <h1 className="text-2xl font-bold tracking-tight">${plan.description}</h1>
                        <div className="flex gap-3">
                            ${navButtons}
                        </div>
                    </div>
                </nav>
            );

            const renderPage = () => {
              ${pageRendering}
              return <div className="p-8 text-center">Page not found</div>;
            };

            return (
                <div className="min-h-screen" style={{ backgroundColor: '${isDark ? '#0f172a' : (palette.background || '#f8fafc')}' }}>
                    <Navigation />
                    <div className="container mx-auto p-6">
                      <ErrorBoundary>
                        {renderPage()}
                      </ErrorBoundary>
                    </div>
                </div>
            );
        }

        const root = ReactDOM.createRoot(document.getElementById('root'));
        root.render(<App />);
    </script>
</body>
</html>`;
}

// ============================================
// BACKEND TEMPLATE
// ============================================
function createCompleteBackend(plan, routes, schema, dbConfig, backendPort) {
  let cleanRoutes = routes['routes.js'] || '';

  cleanRoutes = cleanRoutes
    .replace(/const express = require\(['"]express['"]\);?\n?/g, '')
    .replace(/const cors = require\(['"]cors['"]\);?\n?/g, '')
    .replace(/const { Pool } = require\(['"]pg['"]\);?\n?/g, '')
    .replace(/const pool = new Pool\([^)]*\);?\n?/g, '')
    .replace(/const app = express\(\);?\n?/g, '')
    .replace(/app\.use\(cors\(\)\);?\n?/g, '')
    .replace(/app\.use\(express\.json\(\)\);?\n?/g, '')
    .replace(/app\.listen\([^)]*\);?\n?/g, '')
    .trim();

  return `const express = require('express');
const cors = require('cors');
const { Pool } = require('pg');

console.log('🚀 Starting backend server...');

const app = express();
app.use(cors());
app.use(express.json());

// Request logging
app.use((req, res, next) => {
  console.log(\`\${req.method} \${req.path}\`, req.body || '');
  next();
});

const pool = new Pool({
  host: '${dbConfig.host}',
  port: ${dbConfig.port},
  user: '${dbConfig.user}',
  password: '${dbConfig.password}',
  database: '${dbConfig.database}'
});

// Test database connection
pool.connect((err, client, release) => {
  if (err) {
    console.error('❌ Database connection error:', err.stack);
    process.exit(1);
  } else {
    console.log('✅ Database connected successfully');
    release();
  }
});

async function initDb() {
  const client = await pool.connect();
  try {
    const schemaSQL = \`${schema['schema.sql']}\`;
    console.log('📊 Creating database tables...');
    await client.query(schemaSQL);
    console.log('✅ Database tables created successfully');
  } catch (err) {
    console.error('❌ Database initialization error:', err);
  } finally {
    client.release();
  }
}

initDb().then(() => {
  console.log('✅ Database initialization complete');
}).catch(err => {
  console.error('❌ Database initialization failed:', err);
});

// API Routes
try {
  ${cleanRoutes}
  console.log('✅ API routes loaded');
} catch (err) {
  console.error('❌ Error loading routes:', err);
}

// Health check
app.get('/api/health', (req, res) => {
  res.json({ 
    status: 'ok', 
    message: 'Server is running',
    port: ${backendPort}
  });
});

// 404 handler
app.use((req, res) => {
  console.log('404:', req.method, req.path);
  res.status(404).json({ error: 'Endpoint not found' });
});

// Error handling middleware
app.use((err, req, res, next) => {
  console.error('Server error:', err);
  res.status(500).json({ error: 'Internal server error' });
});

const PORT = ${backendPort};

app.listen(PORT, () => {
  console.log(\`🚀 Server running on http://localhost:\${PORT}\`);
  console.log(\`🚀 Health check: http://localhost:\${PORT}/api/health\`);
});

process.on('unhandledRejection', (err) => {
  console.error('❌ Unhandled rejection:', err);
});

process.on('uncaughtException', (err) => {
  console.error('❌ Uncaught exception:', err);
  process.exit(1);
});`;
}

// ============================================
// FILE CREATION
// ============================================
async function createProjectFiles(projectPath, project, plan, componentFiles = {}) {
  await fs.mkdir(projectPath, { recursive: true });
  await fs.mkdir(path.join(projectPath, 'frontend'), { recursive: true });

  // Write frontend HTML
  await fs.writeFile(
    path.join(projectPath, 'frontend', 'index.html'),
    project.frontend['index.html']
  );

  // Save individual page components — used by per-page regeneration
  if (Object.keys(componentFiles).length > 0) {
    const componentsDir = path.join(projectPath, 'components');
    await fs.mkdir(componentsDir, { recursive: true });
    for (const [filename, code] of Object.entries(componentFiles)) {
      await fs.writeFile(path.join(componentsDir, filename), code);
    }
  }

  // Save plan metadata for edit mode
  await fs.writeFile(
    path.join(projectPath, 'plan.json'),
    JSON.stringify(plan, null, 2)
  );

  // Write backend if needed
  if (plan.needsDatabase && project.backend) {
    await fs.mkdir(path.join(projectPath, 'backend'), { recursive: true });
    await fs.writeFile(
      path.join(projectPath, 'backend', 'server.js'),
      project.backend['server.js']
    );

    const packageJson = {
      name: plan.projectName,
      version: "1.0.0",
      dependencies: {
        express: "^4.18.2",
        cors: "^2.8.5",
        pg: "^8.11.3"
      }
    };
    await fs.writeFile(
      path.join(projectPath, 'backend', 'package.json'),
      JSON.stringify(packageJson, null, 2)
    );
  }
}

async function installDependencies(projectPath) {
  const backendPath = path.join(projectPath, 'backend');
  try {
    await execPromise('npm install', { cwd: backendPath });
    console.log('✅ Dependencies installed');
  } catch (error) {
    console.error('⚠️ Dependency installation error:', error.message);
  }
}

function startBackend(projectPath, port) {
  const backendPath = path.join(projectPath, 'backend');

  exec(`npx kill-port ${port}`, (err) => {
    if (err) console.log(`No existing process on port ${port}`);

    setTimeout(() => {
      const backendProcess = exec('node server.js', {
        cwd: backendPath,
        env: { ...process.env, PORT: port }
      });

      backendProcess.stdout.on('data', (data) => {
        console.log(`[Backend:${port}] ${data.toString()}`);
      });

      backendProcess.stderr.on('data', (data) => {
        console.error(`[Backend:${port} Error] ${data.toString()}`);
      });

      backendProcess.on('exit', (code) => {
        if (code !== 0) {
          console.error(`[Backend:${port}] ❌ Process exited with code ${code}`);
        }
      });
    }, 500);
  });

  console.log(`✅ Backend startup initiated on port ${port}`);
}

async function fileExists(filePath) {
  try {
    await fs.access(filePath);
    return true;
  } catch {
    return false;
  }
}

// ============================================
// GET EDITABLE TEXT CONTENT FROM PROJECT
// ============================================
router.get('/get-texts/:projectName', async (req, res) => {
  try {
    const { projectName } = req.params;
    const indexPath = path.join(__dirname, '../../generated-projects', projectName, 'frontend', 'index.html');
    if (!(await fileExists(indexPath))) {
      return res.status(404).json({ error: 'Project not found' });
    }

    const html = await fs.readFile(indexPath, 'utf-8');

    // Extract text content from JSX-like patterns in the HTML
    // Target: content between common tags like >text<
    const textItems = [];
    const seenTexts = new Set();

    // Match text inside common React/HTML tags that are likely visible headings/paragraphs/buttons
    const patterns = [
      /<h[1-6][^>]*>([^<>{}\n]{3,120})<\/h[1-6]>/gi,
      /<p[^>]*>([^<>{}\n]{5,200})<\/p>/gi,
      /<button[^>]*>([^<>{}\n]{2,80})<\/button>/gi,
      /<span[^>]*>([^<>{}\n]{3,100})<\/span>/gi,
      /<a[^>]*>([^<>{}\n]{3,80})<\/a>/gi,
      /<li[^>]*>([^<>{}\n]{3,100})<\/li>/gi,
      /<td[^>]*>([^<>{}\n]{3,100})<\/td>/gi,
      /<label[^>]*>([^<>{}\n]{3,80})<\/label>/gi,
    ];

    for (const pattern of patterns) {
      let match;
      while ((match = pattern.exec(html)) !== null) {
        const text = match[1].trim();
        // Filter out template literals, JSX expressions, and very short/long strings
        if (
          text.length >= 3 &&
          !text.includes('{') &&
          !text.includes('}') &&
          !text.includes('${') &&
          !text.startsWith('//') &&
          !seenTexts.has(text)
        ) {
          seenTexts.add(text);
          textItems.push({ original: text, type: pattern.source.match(/h[1-6]|p|button|span|a |li|td|label/)?.[0] || 'text' });
        }
      }
    }

    res.json({ texts: textItems.slice(0, 30) }); // Cap at 30 items
  } catch (error) {
    console.error('❌ Get-texts error:', error);
    res.status(500).json({ error: error.message });
  }
});

// ============================================
// EDIT TEXT CONTENT (no AI, fast string replace)
// ============================================
router.post('/edit-text', async (req, res) => {
  try {
    const { projectName, original, replacement } = req.body;
    if (!projectName || !original || replacement === undefined) {
      return res.status(400).json({ error: 'projectName, original, and replacement are required' });
    }

    const indexPath = path.join(__dirname, '../../generated-projects', projectName, 'frontend', 'index.html');
    if (!(await fileExists(indexPath))) {
      return res.status(404).json({ error: 'Project not found' });
    }

    let html = await fs.readFile(indexPath, 'utf-8');
    if (!html.includes(original)) {
      return res.status(404).json({ error: 'Text not found in project' });
    }

    // Replace all occurrences
    html = html.split(original).join(replacement);
    await fs.writeFile(indexPath, html, 'utf-8');

    console.log(`✏️ Text replaced: "${original.substring(0, 40)}..." → "${replacement.substring(0, 40)}..."`);
    res.json({ success: true });
  } catch (error) {
    console.error('❌ Edit-text error:', error);
    res.status(500).json({ error: error.message });
  }
});

// ============================================
// DOWNLOAD PROJECT AS ZIP
// ============================================
router.get('/download/:projectName', async (req, res) => {
  try {
    const { projectName } = req.params;
    const projectPath = path.join(__dirname, '../../generated-projects', projectName, 'frontend');

    if (!(await fileExists(projectPath))) {
      return res.status(404).json({ error: 'Project not found' });
    }

    res.setHeader('Content-Type', 'application/zip');
    res.setHeader('Content-Disposition', `attachment; filename="${projectName}.zip"`);

    const archive = archiver('zip', { zlib: { level: 9 } });
    archive.on('error', (err) => { throw err; });
    archive.pipe(res);
    archive.directory(projectPath, false);
    await archive.finalize();

    console.log(`✅ ZIP sent for project: ${projectName}`);
  } catch (error) {
    console.error('❌ ZIP error:', error);
    res.status(500).json({ error: error.message });
  }
});

// ============================================
// UPLOAD IMAGE TO PROJECT ASSETS
// ============================================
router.post('/upload-image', upload.single('image'), async (req, res) => {
  try {
    const { projectName } = req.body;
    if (!req.file || !projectName) {
      return res.status(400).json({ error: 'projectName and image are required' });
    }

    const relativeUrl = `./assets/${req.file.filename}`;
    console.log(`✅ Image uploaded: ${relativeUrl} for project: ${projectName}`);

    res.json({
      success: true,
      url: relativeUrl,
      filename: req.file.filename
    });
  } catch (error) {
    console.error('❌ Upload error:', error);
    res.status(500).json({ error: error.message });
  }
});

// ============================================
// RECOLOR - Fast palette swap (no AI)
// ============================================
router.post('/recolor', async (req, res) => {
  try {
    const { projectName, oldPalette, newPalette } = req.body;
    if (!projectName || !oldPalette || !newPalette) {
      return res.status(400).json({ error: 'projectName, oldPalette, and newPalette are required' });
    }

    const indexPath = path.join(__dirname, '../../generated-projects', projectName, 'frontend', 'index.html');
    if (!(await fileExists(indexPath))) {
      return res.status(404).json({ error: 'Project not found' });
    }

    let html = await fs.readFile(indexPath, 'utf-8');

    // Swap each color in the palette
    const colorKeys = ['primary', 'secondary', 'accent', 'background', 'text'];
    for (const key of colorKeys) {
      if (oldPalette[key] && newPalette[key] && oldPalette[key] !== newPalette[key]) {
        // Replace all instances (case-insensitive)
        const regex = new RegExp(oldPalette[key].replace('#', '\\#'), 'gi');
        html = html.split(oldPalette[key]).join(newPalette[key]);
        console.log(`🎨 Replaced ${key}: ${oldPalette[key]} → ${newPalette[key]}`);
      }
    }

    await fs.writeFile(indexPath, html, 'utf-8');
    console.log(`✅ Recolor complete for project: ${projectName}`);

    res.json({ success: true });
  } catch (error) {
    console.error('❌ Recolor error:', error);
    res.status(500).json({ error: error.message });
  }
});

// ============================================
// PATCH ELEMENT - Visual editor: apply style/text changes
// ============================================
router.post('/patch-element', async (req, res) => {
  try {
    const { projectName, selector, changes } = req.body;
    // changes = { text, color, backgroundColor, fontSize }

    if (!projectName || !selector || !changes) {
      return res.status(400).json({ error: 'projectName, selector, and changes are required' });
    }

    const indexPath = path.join(__dirname, '../../generated-projects', projectName, 'frontend', 'index.html');
    if (!(await fileExists(indexPath))) {
      return res.status(404).json({ error: 'Project not found' });
    }

    let html = await fs.readFile(indexPath, 'utf-8');
    let changed = false;

    // --- TEXT CHANGE ---
    // We find the element by its old text and replace only that text node
    if (changes.text !== undefined && changes.oldText !== undefined && changes.text !== changes.oldText) {
      const oldText = changes.oldText.trim();
      const newText = changes.text.trim();
      if (oldText && html.includes(oldText)) {
        html = html.split(oldText).join(newText);
        changed = true;
        console.log(`✏️ Text patched: "${oldText.substring(0, 40)}" → "${newText.substring(0, 40)}"`);
      }
    }

    // --- STYLE CHANGES (color, background-color, font-size) ---
    // We'll apply styles by adding/modifying inline style on the outer element
    // Strategy: find the element by its text content in the HTML, then inject/merge style attribute
    const styleProps = [];
    if (changes.color) styleProps.push(`color:${changes.color}`);
    if (changes.backgroundColor && changes.backgroundColor !== 'rgba(0, 0, 0, 0)' && changes.backgroundColor !== 'transparent') {
      styleProps.push(`background-color:${changes.backgroundColor}`);
    }
    if (changes.fontSize) styleProps.push(`font-size:${changes.fontSize}`);

    if (styleProps.length > 0) {
      const styleString = styleProps.join(';');
      // Target text to anchor the patch - use new text if changed, else old
      const anchorText = (changes.text || changes.oldText || '').trim();

      if (anchorText) {
        // Find the tag that directly contains this text
        // Pattern: <TAG ...>...anchorText...<\/TAG>  (single-level)
        const tagMatch = selector.split('>').pop().trim().split(':')[0]; // e.g., "h1", "p", "button"
        const tagPattern = new RegExp(
          `(<${tagMatch}(?:[^>]*?))(\\s*style="([^"]*)")?([^>]*>)((?:[^<]|\\s)*?)(${escapeRegExp(anchorText)})((?:[^<]|\\s)*?)(<\\/${tagMatch}>)`,
          'i'
        );

        if (tagPattern.test(html)) {
          html = html.replace(tagPattern, (match, openTag, styleAttr, existingStyle, closeOpen, before, text, after, closeTag) => {
            // Merge new styles with existing
            const existing = (existingStyle || '').split(';').filter(Boolean);
            const newProps = styleString.split(';').filter(Boolean);

            // Override existing properties with new ones
            const propMap = {};
            existing.forEach(p => {
              const [k, v] = p.split(':');
              if (k && v) propMap[k.trim()] = v.trim();
            });
            newProps.forEach(p => {
              const [k, v] = p.split(':');
              if (k && v) propMap[k.trim()] = v.trim();
            });

            const mergedStyle = Object.entries(propMap).map(([k, v]) => `${k}:${v}`).join(';');
            return `${openTag} style="${mergedStyle}"${closeOpen}${before}${text}${after}${closeTag}`;
          });
          changed = true;
          console.log(`🎨 Style patched on <${tagMatch}>: ${styleString}`);
        }
      }
    }

    if (changed) {
      await fs.writeFile(indexPath, html, 'utf-8');
      console.log(`✅ Element patched in project: ${projectName}`);
    }

    res.json({ success: true, changed });
  } catch (error) {
    console.error('❌ Patch-element error:', error);
    res.status(500).json({ error: error.message });
  }
});

function escapeRegExp(string) {
  return string.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}

// ============================================
// PATCH IMAGE SRC
// Replace an image's src/alt directly in the HTML
// ============================================
router.post('/patch-image-src', async (req, res) => {
  try {
    const { projectName, selector, newSrc, newAlt } = req.body;

    if (!projectName || !newSrc) {
      return res.status(400).json({ error: 'projectName and newSrc are required' });
    }

    const indexPath = path.join(__dirname, '../../generated-projects', projectName, 'frontend', 'index.html');
    if (!(await fileExists(indexPath))) {
      return res.status(404).json({ error: 'Project not found' });
    }

    let html = await fs.readFile(indexPath, 'utf-8');

    // Strategy: find <img ... src="OLD_URL" ...> and replace src + alt
    // We look for src="..." in img tags and replace the first match that seems correct
    // Using a regex that targets img tags with their src attribute
    let changed = false;

    // Replace src attribute inside any <img ...> tag
    const imgTagRegex = /<img([^>]*?)>/gi;
    html = html.replace(imgTagRegex, (match, attrs) => {
      if (changed) return match; // Only replace the first matching img
      let updated = attrs;

      // Replace src
      if (updated.includes('src=')) {
        updated = updated.replace(/src="[^"]*"/, `src="${newSrc}"`);
        updated = updated.replace(/src='[^']*'/, `src="${newSrc}"`);
      } else {
        updated = ` src="${newSrc}"` + updated;
      }

      // Replace or add alt
      if (newAlt !== undefined) {
        if (updated.includes('alt=')) {
          updated = updated.replace(/alt="[^"]*"/, `alt="${newAlt}"`);
          updated = updated.replace(/alt='[^']*'/, `alt="${newAlt}"`);
        } else {
          updated += ` alt="${newAlt}"`;
        }
      }

      if (updated !== attrs) {
        changed = true;
        console.log(`🖼️ Image src patched → ${newSrc.substring(0, 60)}`);
      }
      return `<img${updated}>`;
    });

    if (changed) {
      await fs.writeFile(indexPath, html, 'utf-8');
    }

    res.json({ success: true, changed });
  } catch (error) {
    console.error('❌ Patch-image-src error:', error);
    res.status(500).json({ error: error.message });
  }
});

module.exports = router;
