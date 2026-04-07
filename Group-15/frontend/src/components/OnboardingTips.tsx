import { useState, useEffect } from 'react';
import { X, Lightbulb } from 'lucide-react';
import { OnboardingTip } from '../types';

interface OnboardingTipsProps {
  trigger: OnboardingTip['trigger'];
  onDismiss: (trigger: OnboardingTip['trigger']) => void;
  shown: boolean;
}

const tipContent: Record<OnboardingTip['trigger'], { title: string; message: string }> = {
  'first-component': {
    title: 'Welcome to ChillBuild!',
    message: 'You just added your first component! You can drag it around the canvas, resize it, and customize its properties in the right panel. Try selecting it to see what you can change.',
  },
  'first-css-edit': {
    title: 'CSS Editing',
    message: 'You\'re now editing CSS directly! This gives you full control over styling. Each component has a unique class name that you can style. Changes appear instantly on the canvas.',
  },
  'first-class-create': {
    title: 'Creating Custom Classes',
    message: 'You can create custom CSS classes and apply them to multiple components. This helps maintain consistent styling across your design. Use descriptive names like "primary-button" or "hero-text".',
  },
  'first-export': {
    title: 'Exporting Your Design',
    message: 'When you export, you\'ll get clean HTML with a separate CSS file. This is production-ready code that follows best practices and can be deployed anywhere.',
  },
};

export default function OnboardingTips({ trigger, onDismiss, shown }: OnboardingTipsProps) {
  const [isVisible, setIsVisible] = useState(false);

  useEffect(() => {
    if (!shown) {
      const timer = setTimeout(() => setIsVisible(true), 500);
      return () => clearTimeout(timer);
    }
  }, [shown]);

  if (shown || !isVisible) return null;

  const content = tipContent[trigger];

  const handleDismiss = () => {
    setIsVisible(false);
    setTimeout(() => onDismiss(trigger), 300);
  };

  return (
    <div
      style={{
        position: 'fixed',
        bottom: '24px',
        right: '24px',
        maxWidth: '400px',
        background: 'linear-gradient(135deg, #2563eb 0%, #1d4ed8 100%)',
        color: 'white',
        padding: '20px',
        borderRadius: '12px',
        boxShadow: '0 8px 24px rgba(0, 0, 0, 0.2)',
        zIndex: 10000,
        animation: 'slideIn 0.3s ease-out',
      }}
    >
      <div style={{ display: 'flex', alignItems: 'flex-start', gap: '12px' }}>
        <div
          style={{
            width: '40px',
            height: '40px',
            borderRadius: '50%',
            background: 'rgba(255, 255, 255, 0.2)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            flexShrink: 0,
          }}
        >
          <Lightbulb size={20} />
        </div>
        <div style={{ flex: 1 }}>
          <h3 style={{ fontSize: '16px', fontWeight: '700', marginBottom: '8px' }}>
            {content.title}
          </h3>
          <p style={{ fontSize: '14px', lineHeight: '1.6', opacity: 0.95 }}>
            {content.message}
          </p>
        </div>
        <button
          onClick={handleDismiss}
          style={{
            background: 'transparent',
            border: 'none',
            color: 'white',
            cursor: 'pointer',
            padding: '4px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            borderRadius: '4px',
            transition: 'background 0.2s',
          }}
          onMouseEnter={(e) => (e.currentTarget.style.background = 'rgba(255, 255, 255, 0.2)')}
          onMouseLeave={(e) => (e.currentTarget.style.background = 'transparent')}
        >
          <X size={18} />
        </button>
      </div>
      <style>
        {`
          @keyframes slideIn {
            from {
              transform: translateY(20px);
              opacity: 0;
            }
            to {
              transform: translateY(0);
              opacity: 1;
            }
          }
        `}
      </style>
    </div>
  );
}
