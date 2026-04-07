import { Component } from '../types';

export type AIProvider = 'gemini' | 'openai' | 'anthropic' | 'custom';

export interface AIConfig {
  provider: AIProvider;
  apiKey: string;
  model?: string;
  customEndpoint?: string;
}

export interface AIResponse {
  components: Component[];
  error?: string;
}

export const defaultPrompts = [
  {
    title: 'Landing Page',
    description: 'Modern landing page with hero section',
    prompt: 'Create a modern landing page with a hero section featuring a heading "Welcome to Our Platform", a subtitle, and a call-to-action button. Add a features section with 3 cards showcasing key features.',
  },
  {
    title: 'Portfolio',
    description: 'Portfolio website layout',
    prompt: 'Create a portfolio website with a header containing my name, a hero section with my photo and bio, a projects section with 3 project cards, and a contact section with a form.',
  },
  {
    title: 'Product Page',
    description: 'E-commerce product showcase',
    prompt: 'Create a product page with a large product image, product title, price, description, and an "Add to Cart" button. Include customer reviews section below.',
  },
  {
    title: 'Contact Form',
    description: 'Simple contact form',
    prompt: 'Create a centered contact form with fields for name, email, message, and a submit button. Use a clean, modern design with proper spacing.',
  },
  {
    title: 'Pricing Page',
    description: 'Pricing tiers layout',
    prompt: 'Create a pricing page with 3 pricing tiers (Basic, Pro, Enterprise). Each tier should have a card with the plan name, price, features list, and a signup button.',
  },
  {
    title: 'Blog Layout',
    description: 'Blog post grid',
    prompt: 'Create a blog layout with a header, and a grid of 6 blog post cards. Each card should have an image, title, excerpt, and read more button.',
  },
];

export class AIService {
  private config: AIConfig;

  constructor(config: AIConfig) {
    this.config = config;
  }

  async generateComponents(prompt: string): Promise<AIResponse> {
    try {
      switch (this.config.provider) {
        case 'gemini':
          return await this.generateWithGemini(prompt);
        case 'openai':
          return await this.generateWithOpenAI(prompt);
        case 'anthropic':
          return await this.generateWithAnthropic(prompt);
        case 'custom':
          return await this.generateWithCustom(prompt);
        default:
          throw new Error('Unsupported AI provider');
      }
    } catch (error) {
      return {
        components: [],
        error: error instanceof Error ? error.message : 'Failed to generate components',
      };
    }
  }

  private async generateWithGemini(prompt: string): Promise<AIResponse> {
    const systemPrompt = `You are a web design expert. Generate a JSON array of website components based on the user's request.

Each component must follow this TypeScript interface:
{
  id: string;
  type: 'button' | 'text' | 'image' | 'container' | 'heading' | 'input' | 'card';
  content: string;
  styles: {
    [key: string]: string; // CSS properties in camelCase
  };
  children?: Component[]; // Only for container type
}

Rules:
1. Return ONLY a valid JSON array, no markdown or explanations
2. Use realistic content (no Lorem Ipsum)
3. Use images from Pexels (https://images.pexels.com/photos/...)
4. Make designs modern, clean, and responsive
5. Use proper color combinations and spacing
6. For containers, nest children components inside

Example:
[
  {
    "id": "heading-1",
    "type": "heading",
    "content": "Welcome to Our Site",
    "styles": {
      "fontSize": "48px",
      "fontWeight": "700",
      "color": "#1a1a1a",
      "textAlign": "center",
      "marginBottom": "16px"
    }
  }
]`;

    const fullPrompt = `${systemPrompt}\n\nUser request: ${prompt}\n\nGenerate the components:`;

    const response = await fetch(
      `https://generativelanguage.googleapis.com/v1beta/models/${this.config.model || 'gemini-pro'}:generateContent?key=${this.config.apiKey}`,
      {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          contents: [{ parts: [{ text: fullPrompt }] }],
          generationConfig: {
            temperature: 0.7,
            maxOutputTokens: 8000,
          },
        }),
      }
    );

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.error?.message || 'Gemini API request failed');
    }

    const data = await response.json();
    const text = data.candidates[0]?.content?.parts[0]?.text || '';
    const components = this.parseComponents(text);

    return { components };
  }

  private async generateWithOpenAI(prompt: string): Promise<AIResponse> {
    const systemPrompt = `You are a web design expert. Generate a JSON array of website components based on the user's request.

Each component must follow this structure with proper TypeScript typing. Return ONLY a valid JSON array without markdown formatting.
Use realistic content, modern designs, and Pexels images.`;

    const response = await fetch('https://api.openai.com/v1/chat/completions', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${this.config.apiKey}`,
      },
      body: JSON.stringify({
        model: this.config.model || 'gpt-4o',
        messages: [
          { role: 'system', content: systemPrompt },
          { role: 'user', content: prompt },
        ],
        temperature: 0.7,
        max_tokens: 4000,
      }),
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.error?.message || 'OpenAI API request failed');
    }

    const data = await response.json();
    const text = data.choices[0]?.message?.content || '';
    const components = this.parseComponents(text);

    return { components };
  }

  private async generateWithAnthropic(prompt: string): Promise<AIResponse> {
    const systemPrompt = `You are a web design expert. Generate a JSON array of website components based on the user's request.
    Return ONLY valid JSON without markdown formatting.`;

    const response = await fetch('https://api.anthropic.com/v1/messages', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'x-api-key': this.config.apiKey,
        'anthropic-version': '2023-06-01',
      },
      body: JSON.stringify({
        model: this.config.model || 'claude-3-5-sonnet-20241022',
        max_tokens: 4000,
        system: systemPrompt,
        messages: [{ role: 'user', content: prompt }],
      }),
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.error?.message || 'Anthropic API request failed');
    }

    const data = await response.json();
    const text = data.content[0]?.text || '';
    const components = this.parseComponents(text);

    return { components };
  }

  private async generateWithCustom(prompt: string): Promise<AIResponse> {
    if (!this.config.customEndpoint) {
      throw new Error('Custom endpoint not configured');
    }

    const response = await fetch(this.config.customEndpoint, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${this.config.apiKey}`,
      },
      body: JSON.stringify({ prompt }),
    });

    if (!response.ok) {
      throw new Error('Custom API request failed');
    }

    const data = await response.json();
    const components = Array.isArray(data.components) ? data.components : this.parseComponents(data.content || '');

    return { components };
  }

  private parseComponents(text: string): Component[] {
    try {
      let cleaned = text.trim();

      if (cleaned.startsWith('```json')) {
        cleaned = cleaned.replace(/^```json\n?/, '').replace(/```$/, '').trim();
      } else if (cleaned.startsWith('```')) {
        cleaned = cleaned.replace(/^```\n?/, '').replace(/```$/, '').trim();
      }

      const parsed = JSON.parse(cleaned);
      return Array.isArray(parsed) ? parsed : [];
    } catch (error) {
      console.error('Failed to parse components:', error);
      return [];
    }
  }
}
