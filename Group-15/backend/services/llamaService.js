const axios = require('axios');

// ============================================
// LLM PROVIDER CONFIG
// Supports Groq (cloud) or Ollama (local) 
// ============================================
const GROQ_API_KEY = process.env.GROK_API || '';
const GROQ_MODEL = process.env.GROQ_MODEL || 'llama-3.3-70b-versatile';
const GROQ_URL = 'https://api.groq.com/openai/v1/chat/completions';

// Fallback to Ollama if no Groq key
const LLAMA_URL = process.env.LLAMA_URL || 'http://localhost:11434/api/generate';
const LLAMA_MODEL = process.env.LLAMA_MODEL || 'llama3.2:latest';

const USE_GROQ = GROQ_API_KEY.length > 0;

console.log(`🤖 LLM1 (Planning): ${USE_GROQ ? `Groq Cloud (${GROQ_MODEL})` : `Ollama Local (${LLAMA_MODEL})`}`);

// Unified LLM call — uses Groq if key exists, otherwise Ollama
async function callLLM(prompt, temperature = 0.3) {
  if (USE_GROQ) {
    // Groq Cloud API (OpenAI-compatible)
    const response = await axios.post(GROQ_URL, {
      model: GROQ_MODEL,
      messages: [{ role: 'user', content: prompt }],
      temperature: temperature,
      max_tokens: 4096
    }, {
      headers: {
        'Authorization': `Bearer ${GROQ_API_KEY}`,
        'Content-Type': 'application/json'
      }
    });
    return response.data.choices[0].message.content;
  } else {
    // Ollama Local API
    const wrappedPrompt = LLAMA_MODEL.toLowerCase().includes('qwen3')
      ? `/no_think\n${prompt}` : prompt;
    const response = await axios.post(LLAMA_URL, {
      model: LLAMA_MODEL,
      prompt: wrappedPrompt,
      stream: false,
      options: { temperature }
    });
    return response.data.response;
  }
}

// ============================================
// DYNAMIC FORM - Requirement Gathering
// ============================================
async function generateQuestionnaire(userMessage) {
  console.log('🦙 Llama analyzing initial idea to build a questionnaire...');

  const systemPrompt = `You are a senior product manager and web architect. A client gave you a brief project idea.
Your job is to ask the RIGHT questions for THIS specific project — not a generic form.

Client Idea: "${userMessage}"

STEP 1 — Classify the project type:
Think about what kind of website this is. Examples of project types:
- Restaurant / Food service (needs: menu items, cuisine type, reservation system, ambiance)
- E-commerce store (needs: product categories, payment flow, shipping rules, return policy)
- Portfolio / Personal brand (needs: skills showcase, case studies, contact form, bio tone)
- SaaS / Startup (needs: pricing tiers, feature highlights, onboarding flow, dashboard)
- Blog / News site (needs: content categories, author profiles, comment system, newsletter)
- Booking / Appointment system (needs: service types, calendar UI, staff profiles, locations)
- NGO / Non-profit (needs: mission, donation flow, volunteers, events)
- Educational platform (needs: course types, student roles, quiz/assessment, certification)
... and so on. Identify the type and generate questions for THAT type.

STEP 2 — Generate 5 to 7 questions SPECIFICALLY for this project type.
CRITICAL RULES:
- Questions MUST be specific to the idea: "${userMessage}"
- Do NOT paste generic default questions. For a restaurant, ask about cuisine and seating capacity. For an e-commerce site, ask about product categories and payment methods. For a portfolio, ask about the person's profession and skills.
- Use "single_select" or "multi_select" for anything that has known answer options.
- Use "text" ONLY for open-ended things like brand name, tagline, or special requirements.
- Each question must have a unique "id" like "q_cuisine_type", "q_payment_methods", "q_design_vibe" etc.

RETURN STRICT JSON ONLY. No markdown, no explanation. Use this structure:
{
  "questions": [
    {
      "id": "unique_snake_case_id",
      "label": "A very specific, direct question relevant to this project",
      "type": "single_select" | "multi_select" | "text",
      "options": ["Option A", "Option B", "Option C"]
    }
  ]
}

IMPORTANT: The "options" field MUST be included for single_select and multi_select types. Leave it out ONLY for type "text".

Return ONLY the raw JSON object. No intro, no trailing text.`;

  try {
    const rawResponse = await callLLM(systemPrompt, 0.7);

    let jsonStr = rawResponse.trim();
    jsonStr = jsonStr.replace(/```json/g, '').replace(/```/g, '');

    const jsonStart = jsonStr.indexOf('{');
    const jsonEnd = jsonStr.lastIndexOf('}');
    if (jsonStart !== -1 && jsonEnd !== -1) {
      jsonStr = jsonStr.substring(jsonStart, jsonEnd + 1);
    }

    const compiled = JSON.parse(jsonStr);

    // Ensure we always have questions
    if (!compiled.questions || compiled.questions.length === 0) {
      throw new Error("Empty questions array returned from LLaMA");
    }

    return compiled.questions;

  } catch (err) {
    console.error('❌ Llama Questionnaire Error:', err.message);
    // Fallback questionnaire
    return [
      {
        id: "fallback_style",
        label: "What visual style do you prefer?",
        type: "single_select",
        options: ["Modern & Clean", "Dark Mode", "Playful & Bold", "Corporate"]
      },
      {
        id: "fallback_pages",
        label: "Which pages do you need?",
        type: "multi_select",
        options: ["Home", "About", "Services", "Contact", "Dashboard"]
      },
      {
        id: "fallback_audience",
        label: "Who is the primary target audience?",
        type: "text"
      },
      {
        id: "fallback_features",
        label: "Select essential features:",
        type: "multi_select",
        options: ["User Login/Auth", "Database Storage", "Online Payments", "Image Gallery"]
      },
      {
        id: "fallback_data",
        label: "What specific content or data will this site display?",
        type: "text"
      }
    ];
  }
}

// ============================================
// EDIT ANALYSIS - Multi-page aware
// ============================================
async function analyzeEditPrompt(userPrompt, projectContext = {}) {
  const pages = projectContext.pages || ['index'];
  const features = projectContext.features || [];

  const systemPrompt = `You are editing an EXISTING multi-page web project.

Existing pages: ${pages.join(', ')}
Existing features: ${features.join(', ')}

Your task:
- Decide WHICH page(s) need to be modified based on the user request
- Describe WHAT changes to make on each page

Allowed actions:
- create_page (meaning EDIT/UPDATE an existing page)

Rules:
- ONLY reference pages that already exist: ${pages.join(', ')}
- Prefer minimal, surgical changes
- You may edit MULTIPLE pages if the request affects more than one
- Be very specific about what to change (colors, layout, content, functionality)

Return JSON ONLY:
{
  "instructions": [
    {
      "action": "create_page",
      "page": "<page_name>",
      "details": "Specific description of what to change on this page"
    }
  ]
}

User request: "${userPrompt}"`;

  const rawResponse = await callLLM(systemPrompt, 0.2);

  let text = rawResponse
    .replace(/```json|```/g, '')
    .trim();

  const jsonStart = text.indexOf('{');
  const jsonEnd = text.lastIndexOf('}');
  if (jsonStart !== -1 && jsonEnd !== -1) {
    text = text.substring(jsonStart, jsonEnd + 1);
  }

  try {
    const parsed = JSON.parse(text);
    if (!parsed.instructions || parsed.instructions.length === 0) {
      throw new Error('No instructions found');
    }
    return parsed;
  } catch (parseErr) {
    console.warn('⚠️ LLaMA edit JSON parse failed, using fallback. Raw:', text.substring(0, 200));
    // Fallback: apply the edit to all existing pages
    return {
      instructions: pages.map(page => ({
        action: 'create_page',
        page: page,
        details: userPrompt
      }))
    };
  }
}




async function analyzePrompt(userPrompt, chatHistory = []) {
  console.log('🦙 Llama analyzing prompt with API contract...');

  // Build context from chat history if available
  const chatContext = chatHistory.length > 0
    ? `\nThe following conversation happened before this request:\n${chatHistory.map(m => `${m.role}: ${m.content}`).join('\n')}\n`
    : '';

  const systemPrompt = `You are a web application architect. Analyze the request and create a DETAILED execution plan with an API contract.
${chatContext}
CRITICAL: You can ONLY use these 3 actions:
1. "create_database_schema" - for database tables
2. "create_page" - for frontend pages  
3. "create_api" - for backend API routes

Your response MUST be valid JSON with this EXACT structure:
{
  "projectName": "short-kebab-name",
  "description": "Brief one-line description",
  "needsDatabase": true/false,
  "databaseType": "postgresql" or "none",
  "pages": ["landing", "about", "contact", "dashboard"],
  "features": ["list of features"],
  "styleTokens": {
    "theme": "dark" or "light",
    "palette": {
      "primary": "#hex",
      "secondary": "#hex",
      "accent": "#hex",
      "background": "#hex",
      "text": "#hex"
    },
    "style": "modern" or "minimal" or "bold" or "glassmorphism" or "corporate" or "playful" or "luxury",
    "fontFamily": "Inter" or "Poppins" or "Playfair Display" or "Space Grotesk",
    "borderRadius": "rounded-lg" or "rounded-xl" or "rounded-2xl" or "rounded-none",
    "animations": true/false
  },
  "apiContract": {
    "tables": [
      {
        "name": "table_name",
        "columns": [
          { "name": "id", "type": "SERIAL PRIMARY KEY" },
          { "name": "column_name", "type": "VARCHAR(255)", "default": null }
        ]
      }
    ],
    "endpoints": [
      { "method": "GET", "path": "/api/table_name", "description": "Get all items" },
      { "method": "GET", "path": "/api/table_name/:id", "description": "Get single item" },
      { "method": "POST", "path": "/api/table_name", "description": "Create item" },
      { "method": "PUT", "path": "/api/table_name/:id", "description": "Update item" },
      { "method": "DELETE", "path": "/api/table_name/:id", "description": "Delete item" }
    ]
  },
  "pageDescriptions": {
    "landing": "Hero section with gradient background, feature highlights grid, call-to-action buttons",
    "about": "Company story, team cards with photos, mission statement",
    "contact": "Contact form with validation, embedded map placeholder, social links",
    "dashboard": "Data table with search/filter, stats cards at top, action buttons"
  },
  "imageKeywords": {
    "landing": "restaurant,fine-dining,interior",
    "about": "chef,kitchen,team",
    "menu": "food,dish,cuisine,gourmet",
    "contact": "restaurant-exterior,location"
  },
  "instructions": [
    {
      "step": 1,
      "action": "create_database_schema",
      "priority": "high",
      "details": "Create database tables as defined in apiContract.tables"
    },
    {
      "step": 2,
      "action": "create_page",
      "page": "landing",
      "priority": "high",
      "details": "Landing page with hero section, featured items grid, and CTA buttons"
    },
    {
      "step": 3,
      "action": "create_page",
      "page": "menu",
      "priority": "high",
      "details": "Full menu listing with categories, dish cards, prices and images"
    },
    {
      "step": 4,
      "action": "create_page",
      "page": "reservations",
      "priority": "high",
      "details": "Reservation form with date picker, party size, and special requests"
    },
    {
      "step": 5,
      "action": "create_api",
      "priority": "high",
      "details": "REST API endpoints as defined in apiContract.endpoints"
    }
  ]
}

IMPORTANT RULES:
- action MUST be EXACTLY: "create_database_schema", "create_page", or "create_api"
- If needsDatabase is true, ALWAYS include create_database_schema as step 1 and create_api LAST
- ⭐ CRITICAL: You MUST include one "create_page" instruction for EVERY page listed in the "pages" array. If pages has 4 items, you need 4 create_page instructions. NEVER combine pages or skip any.
- create_page actions MUST have a "page" field that EXACTLY matches a page name in the pages array
- pages array must list all pages you intend to build
- apiContract MUST define exact table names, columns, and endpoints that frontend and backend BOTH use
- styleTokens MUST match the project's vibe (e.g., luxury car site = dark theme, gold accent)
- pageDescriptions MUST describe UNIQUE layouts for each page - NO two pages should look the same
- Pages should be DIVERSE: landing pages, dashboards, galleries, forms, about sections
- Choose APPROPRIATE pages for the project type (restaurant needs Menu/Reservations, portfolio needs Projects/Contact)
- imageKeywords MUST contain comma-separated search terms for EACH page
- imageKeywords should be specific and descriptive, NOT generic

⭐⭐ DATABASE RULE — THIS IS EXTREMELY IMPORTANT:
- If the app manages, lists, creates, edits, deletes, tracks, stores, or displays ANY kind of data items, then needsDatabase MUST be true.
- Examples that ALWAYS need needsDatabase=true: library (books), todo/task app, store/shop (products/items), inventory, booking system, restaurant (menu items/reservations), blog (posts), CRM (contacts), school (students/courses), hospital (patients), gym (members), event manager, recipe app, note-taking app, job board, real estate (listings), supermarket (items), hotel (rooms/bookings).
- If the user's idea involves ANY of these patterns, you MUST set needsDatabase to true, include apiContract with proper tables/columns/endpoints, and include create_database_schema + create_api instructions.
- ONLY set needsDatabase=false for purely static/informational sites like portfolios, landing pages, or company brochures with NO data management.

User request: "${userPrompt}"

Return ONLY the JSON object, nothing else.`;

  try {
    const rawResponse = await callLLM(systemPrompt, 0.3);

    let llamaResponse = rawResponse;

    llamaResponse = llamaResponse.trim();
    llamaResponse = llamaResponse.replace(/```json/g, '').replace(/```/g, '');

    const jsonStart = llamaResponse.indexOf('{');
    const jsonEnd = llamaResponse.lastIndexOf('}');

    if (jsonStart !== -1 && jsonEnd !== -1) {
      llamaResponse = llamaResponse.substring(jsonStart, jsonEnd + 1);
    }

    const plan = JSON.parse(llamaResponse);

    // Validate actions
    for (const instruction of plan.instructions) {
      const validActions = ['create_database_schema', 'create_page', 'create_api'];
      if (!validActions.includes(instruction.action)) {
        console.warn(`⚠️ Invalid action "${instruction.action}", replacing with "create_page"`);
        instruction.action = 'create_page';
        if (!instruction.page) {
          instruction.page = 'home';
        }
      }
    }

    // Ensure styleTokens exist with defaults
    if (!plan.styleTokens) {
      plan.styleTokens = {
        theme: 'light',
        palette: { primary: '#6366f1', secondary: '#8b5cf6', accent: '#f59e0b', background: '#f8fafc', text: '#1e293b' },
        style: 'modern',
        fontFamily: 'Inter',
        borderRadius: 'rounded-xl',
        animations: true
      };
    }

    // Ensure apiContract exists
    if (!plan.apiContract) {
      plan.apiContract = { tables: [], endpoints: [] };
    }

    // Ensure pageDescriptions exist
    if (!plan.pageDescriptions) {
      plan.pageDescriptions = {};
      for (const page of plan.pages) {
        plan.pageDescriptions[page] = `${page.charAt(0).toUpperCase() + page.slice(1)} page`;
      }
    }

    // Ensure imageKeywords exist with smart defaults
    if (!plan.imageKeywords) {
      plan.imageKeywords = {};
      const projectWords = plan.description.toLowerCase().replace(/[^a-z\s]/g, '').split(/\s+/).slice(0, 3).join(',');
      for (const page of plan.pages) {
        plan.imageKeywords[page] = `${projectWords},${page}`;
      }
    }

    console.log('✅ Llama analysis complete');
    console.log('📋 Plan:', {
      project: plan.projectName,
      needsDB: plan.needsDatabase,
      pages: plan.pages,
      style: plan.styleTokens?.style,
      endpoints: plan.apiContract?.endpoints?.length || 0,
      instructions: plan.instructions.length
    });

    return plan;

  } catch (error) {
    console.error('❌ Llama error:', error.message);
    console.log('⚠️ Using fallback plan');
    return createFallbackPlan(userPrompt);
  }
}

function createFallbackPlan(userPrompt) {
  const needsDB = userPrompt.toLowerCase().includes('database') ||
    userPrompt.toLowerCase().includes('store') ||
    userPrompt.toLowerCase().includes('save') ||
    userPrompt.toLowerCase().includes('crud') ||
    userPrompt.toLowerCase().includes('todo') ||
    userPrompt.toLowerCase().includes('blog') ||
    userPrompt.toLowerCase().includes('notes');

  const projectName = userPrompt
    .toLowerCase()
    .replace(/create|build|make|a|an|the/gi, '')
    .trim()
    .replace(/\s+/g, '-')
    .substring(0, 30) || 'generated-app';

  const instructions = [];
  let step = 1;

  if (needsDB) {
    instructions.push({
      step: step++,
      action: 'create_database_schema',
      priority: 'high',
      details: `Create database schema for ${userPrompt}`
    });
  }

  instructions.push({
    step: step++,
    action: 'create_page',
    page: 'home',
    priority: 'high',
    details: 'Main landing page with hero section and feature highlights'
  });

  instructions.push({
    step: step++,
    action: 'create_page',
    page: 'about',
    priority: 'medium',
    details: 'About page with project information'
  });

  if (needsDB) {
    instructions.push({
      step: step++,
      action: 'create_api',
      priority: 'high',
      details: 'REST API endpoints for CRUD operations'
    });
  }

  return {
    projectName: projectName,
    description: userPrompt,
    needsDatabase: needsDB,
    databaseType: needsDB ? 'postgresql' : 'none',
    pages: ['home', 'about'],
    features: ['Responsive design', 'Modern UI'],
    styleTokens: {
      theme: 'light',
      palette: { primary: '#6366f1', secondary: '#8b5cf6', accent: '#f59e0b', background: '#f8fafc', text: '#1e293b' },
      style: 'modern',
      fontFamily: 'Inter',
      borderRadius: 'rounded-xl',
      animations: true
    },
    apiContract: needsDB ? {
      tables: [{
        name: 'items',
        columns: [
          { name: 'id', type: 'SERIAL PRIMARY KEY' },
          { name: 'name', type: 'VARCHAR(255)' },
          { name: 'description', type: 'TEXT' }
        ]
      }],
      endpoints: [
        { method: 'GET', path: '/api/items', description: 'Get all items' },
        { method: 'POST', path: '/api/items', description: 'Create item' }
      ]
    } : { tables: [], endpoints: [] },
    pageDescriptions: {
      home: 'Landing page with hero section and feature grid',
      about: 'About page with project information'
    },
    instructions: instructions
  };
}

module.exports = {
  analyzePrompt,
  analyzeEditPrompt,
  generateQuestionnaire
};
