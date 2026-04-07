import { useState } from 'react';
import { X, Sparkles, Loader } from 'lucide-react';
import { AIConfig, AIProvider, defaultPrompts } from '../services/aiService';

interface AIModalProps {
  isOpen: boolean;
  onClose: () => void;
  onGenerate: (prompt: string, config: AIConfig) => void;
  isGenerating: boolean;
}

export default function AIModal({ isOpen, onClose, onGenerate, isGenerating }: AIModalProps) {
  const [prompt, setPrompt] = useState('');
  const [provider, setProvider] = useState<AIProvider>('gemini');
  const [apiKey, setApiKey] = useState('');
  const [model, setModel] = useState('');
  const [customEndpoint, setCustomEndpoint] = useState('');
  const [showConfig, setShowConfig] = useState(true);

  if (!isOpen) return null;

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (prompt.trim() && apiKey.trim()) {
      const config: AIConfig = {
        provider,
        apiKey,
        model: model || undefined,
        customEndpoint: customEndpoint || undefined,
      };
      onGenerate(prompt, config);
    }
  };

  const handlePromptSelect = (selectedPrompt: string) => {
    setPrompt(selectedPrompt);
  };

  const getDefaultModel = () => {
    switch (provider) {
      case 'gemini':
        return 'gemini-pro';
      case 'openai':
        return 'gpt-4o';
      case 'anthropic':
        return 'claude-3-5-sonnet-20241022';
      default:
        return '';
    }
  };

  return (
    <div className="modal-overlay">
      <div className="modal-content ai-modal">
        <div className="modal-header">
          <div className="modal-title">
            <Sparkles size={24} />
            <h2>AI Website Generator</h2>
          </div>
          <button className="close-btn" onClick={onClose} disabled={isGenerating}>
            <X size={24} />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="modal-body">
          <div className="prompt-ideas">
            <h3>Prompt Ideas</h3>
            <div className="prompt-grid">
              {defaultPrompts.map((item) => (
                <button
                  key={item.title}
                  type="button"
                  className="prompt-card"
                  onClick={() => handlePromptSelect(item.prompt)}
                  disabled={isGenerating}
                >
                  <h4>{item.title}</h4>
                  <p>{item.description}</p>
                </button>
              ))}
            </div>
          </div>

          <div className="form-section">
            <label htmlFor="prompt">Your Prompt</label>
            <textarea
              id="prompt"
              value={prompt}
              onChange={(e) => setPrompt(e.target.value)}
              placeholder="Describe the website you want to create..."
              rows={4}
              disabled={isGenerating}
              required
            />
          </div>

          <button
            type="button"
            className="config-toggle-btn"
            onClick={() => setShowConfig(!showConfig)}
          >
            {showConfig ? 'Hide' : 'Show'} API Configuration
          </button>

          {showConfig && (
            <div className="config-section">
              <div className="form-section">
                <label htmlFor="provider">AI Provider</label>
                <select
                  id="provider"
                  value={provider}
                  onChange={(e) => setProvider(e.target.value as AIProvider)}
                  disabled={isGenerating}
                >
                  <option value="gemini">Google Gemini</option>
                  <option value="openai">OpenAI (GPT-4)</option>
                  <option value="anthropic">Anthropic (Claude)</option>
                  <option value="custom">Custom Endpoint</option>
                </select>
              </div>

              <div className="form-section">
                <label htmlFor="apiKey">API Key *</label>
                <input
                  type="password"
                  id="apiKey"
                  value={apiKey}
                  onChange={(e) => setApiKey(e.target.value)}
                  placeholder="Enter your API key"
                  disabled={isGenerating}
                  required
                />
              </div>

              <div className="form-section">
                <label htmlFor="model">Model (optional)</label>
                <input
                  type="text"
                  id="model"
                  value={model}
                  onChange={(e) => setModel(e.target.value)}
                  placeholder={`Default: ${getDefaultModel()}`}
                  disabled={isGenerating}
                />
              </div>

              {provider === 'custom' && (
                <div className="form-section">
                  <label htmlFor="endpoint">Custom Endpoint *</label>
                  <input
                    type="url"
                    id="endpoint"
                    value={customEndpoint}
                    onChange={(e) => setCustomEndpoint(e.target.value)}
                    placeholder="https://your-api-endpoint.com"
                    disabled={isGenerating}
                    required
                  />
                </div>
              )}
            </div>
          )}

          <button
            type="submit"
            className="generate-btn"
            disabled={isGenerating || !prompt.trim() || !apiKey.trim()}
          >
            {isGenerating ? (
              <>
                <Loader size={20} className="spinner" />
                Generating...
              </>
            ) : (
              <>
                <Sparkles size={20} />
                Generate Website
              </>
            )}
          </button>
        </form>
      </div>
    </div>
  );
}
