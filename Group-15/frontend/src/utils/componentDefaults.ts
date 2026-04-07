import { Component } from '../types';

export const componentDefaults: Record<Component['type'], Partial<Component>> = {
  button: {
    type: 'button',
    content: 'Get Started',
    styles: {
      base: {
        display: 'inline-flex',
        alignItems: 'center',
        justifyContent: 'center',
        background: 'linear-gradient(135deg, #6366f1 0%, #4f46e5 100%)',
        color: '#ffffff',
        padding: '12px 28px',
        borderRadius: '10px',
        border: 'none',
        fontSize: '15px',
        fontWeight: '600',
        letterSpacing: '0.02em',
        cursor: 'pointer',
        boxShadow: '0 4px 15px -3px rgba(99, 102, 241, 0.5)',
        transition: 'all 0.2s cubic-bezier(0.4, 0, 0.2, 1)',
        fontFamily: 'Inter, system-ui, sans-serif',
      },
      hover: {
        transform: 'translateY(-2px)',
        boxShadow: '0 8px 20px -3px rgba(99, 102, 241, 0.6)',
      },
      active: {
        transform: 'translateY(0px)',
      }
    },
  },
  text: {
    type: 'text',
    content: 'This is a beautifully styled text block. Use it to convey your message clearly and elegantly.',
    styles: {
      base: {
        fontSize: '16px',
        color: '#4b5563',
        lineHeight: '1.7',
        fontWeight: '400',
        fontFamily: 'Inter, system-ui, sans-serif',
      }
    },
  },
  heading: {
    type: 'heading',
    content: 'Building the Future',
    styles: {
      base: {
        fontSize: '48px',
        fontWeight: '800',
        color: '#111827',
        lineHeight: '1.1',
        letterSpacing: '-0.02em',
        marginBottom: '16px',
        fontFamily: 'Inter, system-ui, sans-serif',
      }
    },
  },
  image: {
    type: 'image',
    content: 'https://images.unsplash.com/photo-1618005182384-a83a8bd57fbe?q=80&w=2400&auto=format&fit=crop',
    styles: {
      base: {
        width: '100%',
        height: '100%',
        borderRadius: '16px',
        objectFit: 'cover',
        boxShadow: '0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04)',
      }
    },
  },
  input: {
    type: 'input',
    content: 'Enter your email...',
    styles: {
      base: {
        width: '100%',
        padding: '12px 16px',
        fontSize: '15px',
        color: '#111827',
        backgroundColor: '#f9fafb',
        border: '1.5px solid #e5e7eb',
        borderRadius: '10px',
        transition: 'all 0.2s ease',
        outline: 'none',
        fontFamily: 'Inter, system-ui, sans-serif',
      },
      hover: {
        borderColor: '#6366f1',
        boxShadow: '0 0 0 3px rgba(99, 102, 241, 0.1)',
      }
    },
  },
  container: {
    type: 'container',
    content: '',
    styles: {
      base: {
        display: 'flex',
        flexDirection: 'column',
        gap: '24px',
        padding: '48px 24px',
        backgroundColor: 'transparent',
        width: '100%',
        maxWidth: '1200px',
        margin: '0 auto',
      }
    },
    children: [],
  },
  card: {
    type: 'card',
    content: 'Premium Feature|Unlock advanced capabilities that take your product to the next level.|Learn More →',
    styles: {
      base: {
        display: 'flex',
        flexDirection: 'column',
        backgroundColor: '#ffffff',
        padding: '32px',
        borderRadius: '20px',
        boxShadow: '0 4px 24px -4px rgba(0,0,0,0.08), 0 1px 4px -1px rgba(0,0,0,0.04)',
        border: '1px solid rgba(229, 231, 235, 0.7)',
        transition: 'transform 0.2s ease, box-shadow 0.2s ease',
        gap: '12px',
        fontFamily: 'Inter, system-ui, sans-serif',
      },
      hover: {
        transform: 'translateY(-4px)',
        boxShadow: '0 12px 32px -4px rgba(0,0,0,0.12)',
      }
    },
  },
  navbar: {
    type: 'navbar',
    content: 'MyBrand|Home|About|Features|Pricing|Contact',
    styles: {
      base: {
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        padding: '16px 40px',
        backgroundColor: 'rgba(255, 255, 255, 0.9)',
        backdropFilter: 'blur(16px)',
        borderBottom: '1px solid rgba(229, 231, 235, 0.5)',
        width: '100%',
        position: 'sticky',
        top: '0',
        zIndex: '50',
        fontFamily: 'Inter, system-ui, sans-serif',
      }
    },
    children: [],
  },
  footer: {
    type: 'footer',
    content: 'MyBrand|© 2024 MyBrand. All rights reserved.|Privacy Policy|Terms of Service|About Us|Contact',
    styles: {
      base: {
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        padding: '64px 24px 32px',
        backgroundColor: '#0f172a',
        color: '#94a3b8',
        width: '100%',
        fontSize: '14px',
        gap: '24px',
        fontFamily: 'Inter, system-ui, sans-serif',
      }
    },
  },
  form: {
    type: 'form',
    content: 'Get in Touch|Send Message',
    styles: {
      base: {
        display: 'flex',
        flexDirection: 'column',
        gap: '16px',
        padding: '40px',
        backgroundColor: '#ffffff',
        borderRadius: '24px',
        boxShadow: '0 20px 25px -5px rgba(0, 0, 0, 0.08)',
        border: '1px solid rgba(229, 231, 235, 0.5)',
        width: '100%',
        maxWidth: '480px',
        fontFamily: 'Inter, system-ui, sans-serif',
      }
    },
    children: [],
  },
  video: {
    type: 'video',
    content: 'https://www.w3schools.com/html/mov_bbb.mp4',
    styles: {
      base: {
        width: '100%',
        height: '100%',
        borderRadius: '16px',
        boxShadow: '0 20px 25px -5px rgba(0, 0, 0, 0.1)',
        objectFit: 'cover',
      }
    },
  },
  grid: {
    type: 'grid',
    content: 'Feature One|Powerful Tools|Feature Two|Smart Analytics|Feature Three|Easy Integration',
    styles: {
      base: {
        display: 'grid',
        gridTemplateColumns: 'repeat(3, 1fr)',
        gap: '24px',
        width: '100%',
      }
    },
    children: [],
  },
  list: {
    type: 'list',
    content: 'Unlimited projects and workspaces\nAdvanced analytics dashboard\nPriority customer support 24/7\nCustom domain & branding\nTeam collaboration tools',
    styles: {
      base: {
        display: 'flex',
        flexDirection: 'column',
        gap: '10px',
        color: '#374151',
        fontSize: '15px',
        lineHeight: '1.6',
        listStyleType: 'none',
        padding: '0',
        fontFamily: 'Inter, system-ui, sans-serif',
      }
    },
  },
  badge: {
    type: 'badge',
    content: '✨ New Feature',
    styles: {
      base: {
        display: 'inline-flex',
        alignItems: 'center',
        gap: '4px',
        padding: '5px 12px',
        backgroundColor: '#eff6ff',
        color: '#2563eb',
        fontSize: '12px',
        fontWeight: '600',
        letterSpacing: '0.02em',
        borderRadius: '9999px',
        border: '1px solid #bfdbfe',
        fontFamily: 'Inter, system-ui, sans-serif',
      }
    },
  },
  divider: {
    type: 'divider',
    content: '',
    styles: {
      base: {
        width: '100%',
        height: '1px',
        backgroundColor: '#e5e7eb',
        margin: '32px 0',
        border: 'none',
        display: 'block',
      }
    },
  },
  link: {
    type: 'link',
    content: 'Learn more →',
    styles: {
      base: {
        color: '#6366f1',
        textDecoration: 'none',
        fontSize: '15px',
        fontWeight: '500',
        transition: 'color 0.2s ease',
        fontFamily: 'Inter, system-ui, sans-serif',
      },
      hover: {
        color: '#4f46e5',
        textDecoration: 'underline',
      }
    },
  },
  textarea: {
    type: 'textarea',
    content: 'Tell us about yourself...',
    styles: {
      base: {
        width: '100%',
        padding: '16px',
        fontSize: '15px',
        color: '#111827',
        backgroundColor: '#f9fafb',
        border: '1.5px solid #e5e7eb',
        borderRadius: '12px',
        minHeight: '120px',
        resize: 'vertical',
        transition: 'all 0.2s ease',
        outline: 'none',
        fontFamily: 'Inter, system-ui, sans-serif',
        lineHeight: '1.6',
      },
      hover: {
        borderColor: '#6366f1',
        boxShadow: '0 0 0 3px rgba(99, 102, 241, 0.1)',
      }
    },
  },
};

let componentCounters: Record<string, number> = {};

export const createComponent = (type: Component['type']): Component => {
  if (!componentCounters[type]) {
    componentCounters[type] = 0;
  }
  componentCounters[type]++;

  const className = `cb-${type}-${componentCounters[type]}`;
  const customId = `${type}-${componentCounters[type]}`;

  // Smarter default sizes per type
  const sizeMap: Partial<Record<Component['type'], { width: number; height: number }>> = {
    navbar: { width: 1100, height: 64 },
    footer: { width: 1100, height: 220 },
    heading: { width: 500, height: 70 },
    text: { width: 400, height: 80 },
    button: { width: 160, height: 48 },
    card: { width: 300, height: 260 },
    container: { width: 600, height: 200 },
    form: { width: 400, height: 380 },
    grid: { width: 700, height: 220 },
    image: { width: 300, height: 200 },
    video: { width: 480, height: 270 },
    input: { width: 280, height: 48 },
    textarea: { width: 300, height: 120 },
    list: { width: 320, height: 180 },
    badge: { width: 130, height: 36 },
    divider: { width: 400, height: 24 },
    link: { width: 140, height: 36 },
  };

  const size = sizeMap[type] || { width: 200, height: 100 };

  return {
    id: `${type}-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
    className,
    customId,
    position: { x: 50, y: 50 },
    size,
    ...componentDefaults[type],
  } as Component;
};

export const resetComponentCounters = () => {
  componentCounters = {};
};
