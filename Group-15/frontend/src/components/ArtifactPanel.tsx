import { useState, useEffect, useRef } from 'react';
import { Code2, Monitor, Sparkles, CheckCircle2, Loader2, Globe } from 'lucide-react';

export interface StreamLogEntry {
  message: string;
  done: boolean;
}

export interface ArtifactProgress {
  current: number;
  total: number;
  message: string;
}

interface ArtifactPanelProps {
  plan: { projectName?: string; pages?: string[]; styleTokens?: { style?: string; palette?: Record<string, string> } } | null;
  artifacts: Record<string, string>; // { [pageName]: fullHtml }
  streamLog: StreamLogEntry[];
  progress: ArtifactProgress;
}

export default function ArtifactPanel({ plan, artifacts, streamLog, progress }: ArtifactPanelProps) {
  const [activeTab, setActiveTab] = useState<string | null>(null);
  const [viewMode, setViewMode] = useState<'preview' | 'code'>('preview');
  const codeRef = useRef<HTMLDivElement>(null);

  // Auto-select the latest completed page
  useEffect(() => {
    const pageKeys = Object.keys(artifacts);
    if (pageKeys.length > 0) {
      setActiveTab(pageKeys[pageKeys.length - 1]);
    }
  }, [artifacts]);

  // Scroll code to bottom as content streams in
  useEffect(() => {
    if (codeRef.current) {
      codeRef.current.scrollTop = codeRef.current.scrollHeight;
    }
  }, [artifacts, activeTab]);

  const pageArtifacts = Object.keys(artifacts);
  const activeHtml = activeTab ? artifacts[activeTab] : null;
  const percent = progress.total > 0 ? Math.round((progress.current / progress.total) * 100) : 0;
  const palette = plan?.styleTokens?.palette || {};

  // Styles
  const s = {
    root: {
      display: 'flex', flexDirection: 'column' as const, height: '100%',
      background: 'rgba(15, 23, 42, 0.85)',
      borderRadius: '16px',
      border: '1px solid rgba(255,255,255,0.08)',
      overflow: 'hidden',
      boxShadow: '0 25px 60px rgba(0,0,0,0.5)',
    },
    header: {
      display: 'flex', alignItems: 'center', gap: '0.75rem',
      padding: '0.85rem 1.1rem',
      background: 'rgba(0,0,0,0.3)',
      borderBottom: '1px solid rgba(255,255,255,0.08)',
      flexShrink: 0,
    },
    headerTitle: { color: '#f1f5f9', fontSize: '0.85rem', fontWeight: 600, margin: 0, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' as const },
    headerSub: { color: 'rgba(167,139,250,0.7)', fontSize: '0.74rem', margin: 0, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' as const },
    progressBar: { height: '3px', background: 'rgba(255,255,255,0.05)', flexShrink: 0 },
    progressFill: {
      height: '100%',
      background: 'linear-gradient(90deg, #8b5cf6, #6366f1)',
      transition: 'width 0.5s ease',
      width: `${percent}%`,
    },
    logArea: {
      padding: '0.6rem 1rem', borderBottom: '1px solid rgba(255,255,255,0.05)',
      flexShrink: 0, maxHeight: '100px', overflowY: 'auto' as const,
      background: 'rgba(0,0,0,0.2)', display: 'flex', flexDirection: 'column' as const, gap: '0.3rem',
    },
    tabBar: {
      display: 'flex', alignItems: 'center', gap: '0.3rem',
      padding: '0.5rem 0.75rem', borderBottom: '1px solid rgba(255,255,255,0.08)',
      background: 'rgba(0,0,0,0.1)', overflowX: 'auto' as const, flexShrink: 0,
    },
    content: { flex: 1, overflow: 'hidden', display: 'flex', flexDirection: 'column' as const },
    toggleBar: {
      display: 'flex', alignItems: 'center', padding: '0.4rem 0.75rem',
      borderBottom: '1px solid rgba(255,255,255,0.05)',
      background: 'rgba(0,0,0,0.2)', flexShrink: 0, gap: '0.25rem',
    },
  };

  const tabBtn = (active: boolean): React.CSSProperties => ({
    display: 'flex', alignItems: 'center', gap: '0.35rem',
    padding: '0.3rem 0.65rem', borderRadius: '8px',
    fontSize: '0.73rem', fontWeight: 600, cursor: 'pointer',
    whiteSpace: 'nowrap' as const, border: 'none',
    background: active ? '#7c3aed' : 'rgba(255,255,255,0.05)',
    color: active ? 'white' : 'rgba(167,139,250,0.6)',
    boxShadow: active ? '0 4px 12px rgba(124,58,237,0.35)' : 'none',
    transition: 'all 0.15s ease',
  });

  const toggleBtn = (active: boolean): React.CSSProperties => ({
    display: 'flex', alignItems: 'center', gap: '0.3rem',
    padding: '0.25rem 0.6rem', borderRadius: '6px',
    fontSize: '0.72rem', fontWeight: 600, cursor: 'pointer', border: 'none',
    background: active ? '#7c3aed' : 'transparent',
    color: active ? 'white' : 'rgba(167,139,250,0.6)',
    transition: 'all 0.15s ease',
  });

  return (
    <div style={s.root}>
      {/* Header */}
      <div style={s.header}>
        <Sparkles size={18} style={{ color: '#a78bfa', flexShrink: 0, animation: 'pulse 2s ease-in-out infinite' }} />
        <div style={{ flex: 1, minWidth: 0 }}>
          <p style={s.headerTitle}>{plan?.projectName || 'Generating…'}</p>
          <p style={s.headerSub}>{progress.message || 'Starting up…'}</p>
        </div>
        <span style={{ color: '#a78bfa', fontSize: '0.8rem', fontWeight: 700, flexShrink: 0, fontFamily: 'monospace' }}>
          {percent}%
        </span>
      </div>

      {/* Progress bar */}
      <div style={s.progressBar}>
        <div style={s.progressFill} />
      </div>

      {/* Step log */}
      <div style={s.logArea}>
        {streamLog.length === 0 && (
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', color: 'rgba(167,139,250,0.45)', fontSize: '0.75rem' }}>
            <Loader2 size={12} style={{ animation: 'spin 1s linear infinite' }} />
            <span>Waiting for AI planning…</span>
          </div>
        )}
        {streamLog.map((entry, i) => (
          <div key={i} style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', fontSize: '0.75rem' }}>
            {entry.done
              ? <CheckCircle2 size={12} style={{ color: '#34d399', flexShrink: 0 }} />
              : <Loader2 size={12} style={{ color: '#a78bfa', flexShrink: 0, animation: 'spin 1s linear infinite' }} />
            }
            <span style={{ color: entry.done ? 'rgba(52,211,153,0.8)' : 'rgba(241,245,249,0.75)' }}>{entry.message}</span>
          </div>
        ))}
      </div>

      {/* Page artifact tabs */}
      {pageArtifacts.length > 0 && (
        <div style={s.tabBar}>
          {pageArtifacts.map(name => (
            <button key={name} onClick={() => setActiveTab(name)} style={tabBtn(activeTab === name)}>
              <Globe size={11} />
              {name.charAt(0).toUpperCase() + name.slice(1).replace(/-/g, ' ')}
            </button>
          ))}
        </div>
      )}

      {/* Main content area */}
      <div style={s.content}>
        {pageArtifacts.length === 0 ? (
          /* Empty state — waiting for first page */
          <div style={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', gap: '1rem', padding: '2rem', textAlign: 'center' }}>
            <div style={{ position: 'relative', width: '72px', height: '72px' }}>
              <div style={{
                position: 'absolute', inset: 0, borderRadius: '16px',
                background: 'rgba(124,58,237,0.2)',
                animation: 'ping 2s ease-in-out infinite',
              }} />
              <div style={{ position: 'absolute', inset: 0, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                <Sparkles size={36} style={{ color: '#a78bfa' }} />
              </div>
            </div>
            <div>
              <p style={{ color: '#f1f5f9', fontWeight: 600, fontSize: '1rem', margin: '0 0 0.4rem' }}>Building your website</p>
              <p style={{ color: 'rgba(167,139,250,0.55)', fontSize: '0.82rem', margin: 0 }}>
                {plan
                  ? `Crafting ${plan.pages?.length || 0} pages with ${plan.styleTokens?.style || 'modern'} style`
                  : 'Analyzing your idea with AI…'}
              </p>
            </div>
            {/* Palette swatches */}
            {Object.keys(palette).length > 0 && (
              <div style={{ display: 'flex', gap: '0.4rem', marginTop: '0.25rem' }}>
                {Object.entries(palette).map(([key, color]) => (
                  <div key={key} title={`${key}: ${color}`} style={{
                    width: '16px', height: '16px', borderRadius: '50%',
                    background: color, border: '1px solid rgba(255,255,255,0.2)',
                    boxShadow: `0 0 8px ${color}55`,
                  }} />
                ))}
              </div>
            )}
          </div>
        ) : (
          <>
            {/* Preview / Code toggle */}
            {activeHtml && (
              <div style={s.toggleBar}>
                <div style={{ display: 'flex', background: 'rgba(0,0,0,0.3)', borderRadius: '8px', padding: '2px', gap: '2px' }}>
                  <button onClick={() => setViewMode('preview')} style={toggleBtn(viewMode === 'preview')}>
                    <Monitor size={12} /> Preview
                  </button>
                  <button onClick={() => setViewMode('code')} style={toggleBtn(viewMode === 'code')}>
                    <Code2 size={12} /> Code
                  </button>
                </div>
                <span style={{ marginLeft: 'auto', fontSize: '0.68rem', color: 'rgba(167,139,250,0.35)', fontFamily: 'monospace' }}>
                  {activeTab && `${(activeHtml.length / 1024).toFixed(1)} KB`}
                </span>
              </div>
            )}

            {/* Content pane */}
            <div style={{ flex: 1, overflow: 'hidden' }}>
              {viewMode === 'preview' && activeHtml ? (
                <iframe
                  key={`${activeTab}-${activeHtml.length}`}
                  srcDoc={activeHtml}
                  style={{ width: '100%', height: '100%', border: 'none', background: '#fff' }}
                  title={`Preview: ${activeTab}`}
                  sandbox="allow-scripts allow-same-origin"
                />
              ) : viewMode === 'code' && activeHtml ? (
                <div
                  ref={codeRef}
                  style={{
                    width: '100%', height: '100%', overflowY: 'auto',
                    padding: '1rem', fontSize: '0.72rem', color: 'rgba(52,211,153,0.85)',
                    lineHeight: 1.6, fontFamily: "'Fira Code', 'Cascadia Code', Consolas, monospace",
                    background: '#0d1117', whiteSpace: 'pre-wrap', wordBreak: 'break-all',
                    boxSizing: 'border-box',
                  }}
                >
                  {activeHtml}
                  <span style={{ display: 'inline-block', width: '8px', height: '14px', background: '#34d399', marginLeft: '2px', animation: 'pulse 1s ease-in-out infinite', verticalAlign: 'middle' }} />
                </div>
              ) : (
                <div style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100%' }}>
                  <Loader2 size={24} style={{ color: '#a78bfa', animation: 'spin 1s linear infinite' }} />
                </div>
              )}
            </div>
          </>
        )}
      </div>

      <style>{`
        @keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
        @keyframes pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.4; } }
        @keyframes ping { 0% { transform: scale(1); opacity: 0.6; } 100% { transform: scale(1.6); opacity: 0; } }
      `}</style>
    </div>
  );
}
