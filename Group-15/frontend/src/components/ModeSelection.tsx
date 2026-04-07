import { Sparkles, MousePointer, ArrowLeft } from 'lucide-react';

interface ModeSelectionProps {
  onSelectMode: (mode: 'ai' | 'scratch') => void;
  onBack: () => void;
}

export default function ModeSelection({ onSelectMode, onBack }: ModeSelectionProps) {
  return (
    <div className="mode-selection">
      <button className="back-button" onClick={onBack}>
        <ArrowLeft size={20} />
        Back
      </button>

      <div className="mode-container">
        <h1 className="mode-title">Choose Your Starting Mode</h1>
        <p className="mode-subtitle">
          How would you like to begin building your website?
        </p>

        <div className="mode-cards">
          <div className="mode-card" onClick={() => onSelectMode('ai')}>
            <div className="mode-icon ai-mode">
              <Sparkles size={48} />
            </div>
            <h2>Start with AI</h2>
            <p>
              Describe your vision to AI and get a complete design generated instantly.
              Then customize it further using drag-and-drop components.
            </p>
            <button className="mode-button ai-button">
              <Sparkles size={20} />
              Start with AI
            </button>
          </div>

          <div className="mode-card" onClick={() => onSelectMode('scratch')}>
            <div className="mode-icon scratch-mode">
              <MousePointer size={48} />
            </div>
            <h2>Start from Scratch</h2>
            <p>
              Begin with a blank canvas and build your website from the ground up.
              Drag and drop components to create your custom design.
            </p>
            <button className="mode-button scratch-button">
              <MousePointer size={20} />
              Start from Scratch
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
