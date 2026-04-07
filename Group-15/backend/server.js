require('dotenv').config();

const token = process.env.GITHUB_TOKEN;
if (!token) {
  console.warn("⚠️  GITHUB_TOKEN is not set — GitHub export will be disabled. Add it to your .env file to enable exports.");
}


const express = require('express');
const exportRoutes = require("./routes/export");
const cors = require('cors');
const dotenv = require('dotenv');
const path = require('path');
const fs = require('fs');
const generateRoutes = require('./routes/generate');
const previewRoutes = require('./routes/preview');
const chatRoutes = require('./routes/chat');

dotenv.config();

const app = express();
const PORT = process.env.PORT || 5000;

app.use(cors());
app.use(express.json({ limit: '50mb' }));
app.use(express.urlencoded({ extended: true, limit: '50mb' }));

// Routes
app.use('/api/generate', generateRoutes);
app.use('/api/preview', previewRoutes);
app.use("/api/export", exportRoutes);
app.use('/api/chat', chatRoutes);

// Serve generated project files for preview
app.use('/preview-files', express.static(path.join(__dirname, 'generated-projects'), {
  setHeaders: (res, filepath) => {
    if (filepath.endsWith('.html')) {
      res.setHeader('Content-Type', 'text/html');
    } else if (filepath.endsWith('.js')) {
      res.setHeader('Content-Type', 'application/javascript');
    }
  }
}));

app.get('/api/health', (req, res) => {
  res.json({
    status: 'OK',
    message: 'Two-LLM Generator API is running',
    llm1: 'Llama (Local)',
    llm2: 'Gemini (Cloud)'
  });
});

app.listen(PORT, () => {
  console.log(`🚀 Server running on http://localhost:${PORT}`);
  console.log(`🤖 LLM1: Llama (Planning)`);
  console.log(`🤖 LLM2: Gemini (Execution)`);
});

// After existing routes, add this:
app.get('/api/check-databases', async (req, res) => {
  const { Pool } = require('pg');
  const dbConfig = {
    host: 'localhost',
    port: 5432,
    user: 'postgres',
    password: process.env.DB_PASSWORD || 'your_password',
    database: 'generated_apps'
  };

  const pool = new Pool(dbConfig);

  try {
    const result = await pool.query(`
      SELECT table_name 
      FROM information_schema.tables 
      WHERE table_schema = 'public'
    `);

    res.json({
      success: true,
      tables: result.rows.map(r => r.table_name)
    });
  } catch (error) {
    res.json({
      success: false,
      error: error.message
    });
  } finally {
    await pool.end();
  }
});