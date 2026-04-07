import { CheckCircle, RefreshCw, Globe, Palette, Database } from 'lucide-react';
import { GenerateResult } from '../services/webgenService';

interface PlanReviewCardProps {
  plan: GenerateResult['plan'];
  onApprove: () => void;
  onRestart: () => void;
}

export default function PlanReviewCard({ plan, onApprove, onRestart }: PlanReviewCardProps) {
  const palette = (plan?.styleTokens?.palette ?? {}) as Record<string, string>;
  const style = ((plan?.styleTokens as Record<string, unknown>)?.style ?? 'modern') as string;

  const card: React.CSSProperties = {
    background: 'rgba(255,255,255,0.05)',
    border: '1px solid rgba(255,255,255,0.12)',
    borderRadius: '14px',
    padding: '1.1rem',
    display: 'flex',
    flexDirection: 'column',
    gap: '0.85rem',
  };

  const tag = (label: string, color = '#667eea'): React.CSSProperties => ({
    display: 'inline-block', padding: '0.2rem 0.6rem', borderRadius: '999px',
    fontSize: '0.72rem', fontWeight: 600,
    background: `${color}25`, color, border: `1px solid ${color}50`,
  });

  return (
    <div style={card}>
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
        <div>
          <p style={{ color: '#a5b4fc', fontSize: '0.72rem', fontWeight: 600, margin: 0, letterSpacing: '0.05em', textTransform: 'uppercase' }}>
            AI Generated Plan
          </p>
          <h3 style={{ color: '#e2e8f0', fontSize: '1rem', fontWeight: 700, margin: '0.2rem 0 0' }}>
            {plan?.projectName ?? 'Your Website'}
          </h3>
          <p style={{ color: '#94a3b8', fontSize: '0.8rem', margin: '0.15rem 0 0' }}>
            {plan?.description}
          </p>
        </div>
        <span style={tag(plan?.needsDatabase ? '#f59e0b' : '#6ee7b7', plan?.needsDatabase ? '#f59e0b' : '#10b981')}>
          {plan?.needsDatabase ? <><Database size={10} style={{ display:'inline', marginRight:3 }} />With DB</> : 'Static'}
        </span>
      </div>

      {/* Style + palette */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem', flexWrap: 'wrap' }}>
        <Palette size={13} style={{ color: '#94a3b8' }} />
        <span style={tag(style === 'dark' ? '#8b5cf6' : '#3b82f6')}>{style}</span>
        {Object.entries(palette).slice(0, 5).map(([key, val]) => (
          <span key={key} title={`${key}: ${val}`} style={{
            width: 18, height: 18, borderRadius: '50%',
            background: val, border: '2px solid rgba(255,255,255,0.2)',
            display: 'inline-block', flexShrink: 0,
          }} />
        ))}
      </div>

      {/* Pages */}
      <div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', marginBottom: '0.4rem' }}>
          <Globe size={13} style={{ color: '#94a3b8' }} />
          <span style={{ color: '#94a3b8', fontSize: '0.75rem' }}>{plan?.pages?.length ?? 0} pages</span>
        </div>
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.35rem' }}>
          {plan?.pages?.map(page => (
            <span key={page} style={{
              padding: '0.2rem 0.55rem', borderRadius: '6px', fontSize: '0.75rem',
              background: 'rgba(255,255,255,0.07)', color: '#cbd5e1',
              border: '1px solid rgba(255,255,255,0.08)',
            }}>
              {page}
            </span>
          ))}
        </div>
      </div>

      {/* Actions */}
      <div style={{ display: 'flex', gap: '0.5rem', marginTop: '0.1rem' }}>
        <button
          onClick={onApprove}
          style={{
            flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '0.4rem',
            padding: '0.6rem', borderRadius: '8px', border: 'none', cursor: 'pointer',
            background: 'linear-gradient(135deg, #667eea, #764ba2)',
            color: 'white', fontWeight: 700, fontSize: '0.85rem',
          }}
        >
          <CheckCircle size={15} /> Looks Good — Build It!
        </button>
        <button
          onClick={onRestart}
          style={{
            display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '0.4rem',
            padding: '0.6rem 0.9rem', borderRadius: '8px', cursor: 'pointer',
            background: 'transparent', border: '1px solid rgba(255,255,255,0.15)',
            color: '#94a3b8', fontSize: '0.85rem',
          }}
        >
          <RefreshCw size={14} />
        </button>
      </div>
    </div>
  );
}
