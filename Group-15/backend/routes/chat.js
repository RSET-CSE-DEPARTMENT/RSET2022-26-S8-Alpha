const express = require('express');
const router = express.Router();
const llamaService = require('../services/llamaService');

// Interactive requirement gathering via dynamic form
router.post('/questionnaire', async (req, res) => {
    try {
        const { idea } = req.body;

        if (!idea) {
            return res.status(400).json({ error: 'idea is required' });
        }

        console.log('\n📝 Generating questionnaire for:', idea);

        // Returns a strict JSON array of form fields
        const questions = await llamaService.generateQuestionnaire(idea);

        console.log('🤖 Generated questions:', questions.length);

        res.json({
            success: true,
            questions: questions
        });

    } catch (error) {
        console.error('❌ Questionnaire error:', error);
        res.status(500).json({ error: error.message });
    }
});

module.exports = router;
