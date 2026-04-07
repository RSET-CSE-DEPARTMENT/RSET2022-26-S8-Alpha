import { useState, useRef, useEffect, useCallback } from 'react';
import AIChat from './AIChat';
import Builder from './Builder';
import ArtifactPanel, { StreamLogEntry, ArtifactProgress } from './ArtifactPanel';
import ProjectGallery from './ProjectGallery';
import { DBConfig, webgenService, GenerateResult, SelectedElement } from '../services/webgenService';
import {
  ArrowRight, Code, Eye, Download, ExternalLink, Github, Palette,
  Image, Monitor, Tablet, Smartphone, RefreshCw, X, Check, Loader,
  MousePointer, Plus, Save, FolderOpen
} from 'lucide-react';

interface AIBuilderModeProps {
  dbConfig: DBConfig | null;
}

export default function AIBuilderMode({ dbConfig }: AIBuilderModeProps) {
  const [showCanvas, setShowCanvas] = useState(false);
  const [projectName, setProjectName] = useState('');
  const [previewUrl, setPreviewUrl] = useState('');
  const [previewKey, setPreviewKey] = useState(0);
  const [artifactHtml, setArtifactHtml] = useState<string | null>(null); // live streaming HTML

  // Viewport
  const [viewport, setViewport] = useState<'desktop' | 'tablet' | 'mobile'>('desktop');
  const viewportWidths = { desktop: '100%', tablet: '768px', mobile: '375px' };

  // Recolor
  const [showRecolor, setShowRecolor] = useState(false);
  const [palette, setPalette] = useState({ primary: '#6366f1', secondary: '#8b5cf6', accent: '#f59e0b', background: '#f8fafc', text: '#1e293b' });
  const [origPalette, setOrigPalette] = useState(palette);
  const [recoloring, setRecoloring] = useState(false);

  // Image upload
  const [showUpload, setShowUpload] = useState(false);
  const [uploading, setUploading] = useState(false);
  const fileRef = useRef<HTMLInputElement>(null);

  // Export
  const [exporting, setExporting] = useState(false);

  // Gallery
  const [showGallery, setShowGallery] = useState(false);
  const [loadedProject, setLoadedProject] = useState<{ name: string; previewUrl: string } | null>(null);

  // Streaming / Artifact Panel state
  const [isStreaming, setIsStreaming] = useState(false);
  const [artifacts, setArtifacts] = useState<Record<string, string>>({}); // pageName -> html
  const [streamLog, setStreamLog] = useState<StreamLogEntry[]>([]);
  const [streamProgress, setStreamProgress] = useState<ArtifactProgress>({ current: 0, total: 0, message: '' });
  type StreamPlan = { projectName?: string; pages?: string[]; styleTokens?: { style?: string; palette?: Record<string, string> } } | null;
  const [streamPlan, setStreamPlan] = useState<StreamPlan>(null);

  // Visual Editor
  const [editMode, setEditMode] = useState(false);
  const [selectedElement, setSelectedElement] = useState<SelectedElement | null>(null);
  const [editText, setEditText] = useState('');
  const [editColor, setEditColor] = useState('#000000');
  const [editBgColor, setEditBgColor] = useState('#ffffff');
  const [editFontSize, setEditFontSize] = useState('16px');
  const [saving, setSaving] = useState(false);

  // Status
  const [statusMsg, setStatusMsg] = useState('');

  // Listen for postMessage from the preview iframe (visual editor)
  useEffect(() => {
    const handler = (e: MessageEvent) => {
      if (e.data?.type === 'WG_SELECT') {
        const el: SelectedElement = e.data;
        setSelectedElement(el);
        setEditText(el.text || '');
        setEditColor(el.styles?.color || '#000000');
        setEditBgColor(el.styles?.backgroundColor || '#ffffff');
        setEditFontSize(el.styles?.fontSize || '16px');
      }
    };
    window.addEventListener('message', handler);
    return () => window.removeEventListener('message', handler);
  }, []);

  const handleWebsiteGenerated = (name: string, url: string, result?: GenerateResult) => {
    setProjectName(name);
    setPreviewUrl(url);
    setPreviewKey(k => k + 1);
    setArtifactHtml(null);
    setIsStreaming(false); // generation finished
    if (result?.plan?.styleTokens?.palette) {
      const p = result.plan.styleTokens.palette as Record<string, string>;
      const pal = { primary: p.primary || '#6366f1', secondary: p.secondary || '#8b5cf6', accent: p.accent || '#f59e0b', background: p.background || '#f8fafc', text: p.text || '#1e293b' };
      setPalette(pal);
      setOrigPalette(pal);
    }
  };

  // Open a previously generated project from the gallery
  const handleOpenFromGallery = (name: string, url: string, _pages: string[]) => {
    setProjectName(name);
    setPreviewUrl(url);
    setPreviewKey(k => k + 1);
    setArtifactHtml(null);
    setIsStreaming(false);
    setArtifacts({});
    setStreamLog([]);
    setStreamPlan(null);
    setStreamProgress({ current: 0, total: 0, message: '' });
    setEditMode(false);
    setSelectedElement(null);
    setShowRecolor(false);
    setShowUpload(false);
    setStatusMsg('');
    // Signal AIChat to enter edit mode for this project
    setLoadedProject({ name, previewUrl: url });
  };

  // Handles every streaming event from AIChat — feeds ArtifactPanel
  const handleStreamEvent = useCallback((type: string, data: Record<string, unknown>) => {
    if (type === 'plan') {
      const plan = data.plan as StreamPlan;
      setStreamPlan(plan);
      setIsStreaming(true);
      if (!previewUrl) setPreviewUrl('streaming');
      const total = (plan?.pages?.length || 0) + 2; // +2 for plan + assemble steps
      setStreamProgress({ current: 1, total, message: `🧠 Plan ready: ${plan?.pages?.length || 0} pages` });
      setStreamLog(prev => [...prev, { message: `Plan ready — ${plan?.pages?.length || 0} pages, ${plan?.styleTokens?.style || 'modern'} style`, done: true }]);
    } else if (type === 'progress') {
      const msg = data.message as string;
      setStreamProgress(prev => ({ ...prev, current: Math.min(prev.current + 1, prev.total), message: msg }));
      setStreamLog(prev => {
        // Mark previous non-done entries done, then add new pending one
        const updated = prev.map((e, i) => i === prev.length - 1 && !e.done ? { ...e, done: true } : e);
        return [...updated, { message: msg, done: false }];
      });
    } else if (type === 'artifact' && data.type === 'page') {
      const pageName = data.name as string;
      const html = data.content as string;
      const pagesDone = data.pagesDone as number;
      const totalPages = data.totalPages as number;
      setArtifacts(prev => ({ ...prev, [pageName]: html }));
      setStreamProgress(prev => ({ ...prev, current: pagesDone + 1, total: totalPages + 2, message: `🎨 Built “${pageName}” (${pagesDone}/${totalPages})` }));
      setStreamLog(prev => {
        const updated = prev.map((e, i) => i === prev.length - 1 && !e.done ? { ...e, done: true } : e);
        return [...updated, { message: `Page “${pageName}” built successfully`, done: true }];
      });
      // Keep iframe srcdoc updated with latest page
      setArtifactHtml(html);
    } else if (type === 'done') {
      setStreamProgress(prev => ({ ...prev, current: prev.total, message: '✅ All done!' }));
      setStreamLog(prev => prev.map(e => ({ ...e, done: true })));
    }
  }, [previewUrl]);

  const refreshPreview = () => setPreviewKey(k => k + 1);

  const handleDownload = () => {
    if (!projectName) return;
    window.open(webgenService.getDownloadUrl(projectName), '_blank');
  };

  const handleExport = async () => {
    if (!projectName) return;
    setExporting(true);
    setStatusMsg('');
    const res = await webgenService.exportToGitHub(projectName);
    setExporting(false);
    if (res.success && res.repoUrl) {
      window.open(res.repoUrl, '_blank');
      showStatus('✅ Exported to GitHub!');
    } else {
      showStatus(`❌ ${res.error}`);
    }
  };

  const handleRecolor = async () => {
    if (!projectName) return;
    setRecoloring(true);
    const res = await webgenService.recolor(projectName, origPalette, palette);
    setRecoloring(false);
    if (res.success) {
      setOrigPalette({ ...palette });
      refreshPreview();
      showStatus('✅ Colors updated!');
    } else {
      showStatus(`❌ ${res.error}`);
    }
  };

  const handleImageUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file || !projectName) return;
    setUploading(true);
    const res = await webgenService.uploadImage(projectName, file);
    setUploading(false);
    setShowUpload(false);
    if (res.success && res.url) {
      showStatus(`✅ Image uploaded! URL: ${res.url}`, 5000);
    } else {
      showStatus(`❌ ${res.error}`);
    }
  };

  const toggleEditMode = () => {
    setEditMode(prev => {
      if (prev) {
        setSelectedElement(null);
        // Tell iframe to deselect
        const iframe = document.querySelector('iframe');
        iframe?.contentWindow?.postMessage({ type: 'WG_DESELECT' }, '*');
      }
      return !prev;
    });
    setPreviewKey(k => k + 1);
  };

  const handleSaveEdit = async () => {
    if (!selectedElement || !projectName) return;
    setSaving(true);
    const changes: Record<string, string> = {};
    if (editText !== selectedElement.text) {
      changes.text = editText;
      changes.oldText = selectedElement.text;
    }
    if (editColor !== selectedElement.styles?.color) changes.color = editColor;
    if (editBgColor !== selectedElement.styles?.backgroundColor) changes.backgroundColor = editBgColor;
    if (editFontSize !== selectedElement.styles?.fontSize) changes.fontSize = editFontSize;

    if (Object.keys(changes).length === 0) {
      showStatus('No changes to save');
      setSaving(false);
      return;
    }

    const res = await webgenService.patchElement(projectName, selectedElement.selector, changes);
    setSaving(false);
    if (res.success) {
      showStatus('✅ Element updated!');
      refreshPreview();
      setSelectedElement(null);
    } else {
      showStatus(`❌ ${res.error}`);
    }
  };

  const handleNewProject = useCallback(() => {
    setProjectName('');
    setPreviewUrl('');
    setPreviewKey(0);
    setArtifactHtml(null);
    setIsStreaming(false);
    setArtifacts({});
    setStreamLog([]);
    setStreamPlan(null);
    setStreamProgress({ current: 0, total: 0, message: '' });
    setEditMode(false);
    setSelectedElement(null);
    setShowRecolor(false);
    setShowUpload(false);
    setStatusMsg('');
    setLoadedProject(null);
  }, []);

  const showStatus = (msg: string, timeout = 3000) => {
    setStatusMsg(msg);
    setTimeout(() => setStatusMsg(''), timeout);
  };

  if (showCanvas) return <Builder />;

  const iframeSrc = previewUrl && previewUrl !== 'streaming'
    ? (editMode ? `${previewUrl}?editMode=1` : previewUrl)
    : '';
  const iframeSrcdoc = artifactHtml ?? undefined;

  const btn = (active = false): React.CSSProperties => ({
    padding: '0.35rem 0.55rem', borderRadius: '6px', fontSize: '0.78rem',
    border: active ? '1px solid #667eea' : '1px solid rgba(255,255,255,0.12)',
    background: active ? 'rgba(102,126,234,0.2)' : 'transparent',
    color: active ? '#a5b4fc' : '#94a3b8',
    cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '0.25rem',
    textDecoration: 'none', whiteSpace: 'nowrap' as const,
  });

  const inputStyle: React.CSSProperties = {
    width: '100%', padding: '0.4rem 0.5rem', borderRadius: '6px',
    background: '#1e293b', color: '#e2e8f0', border: '1px solid rgba(255,255,255,0.12)',
    fontSize: '0.82rem', outline: 'none',
  };

  return (
    <div style={{ display: 'flex', height: '100vh', background: '#0f172a' }}>
      {/* Left: AI Chat */}
      <div style={{
        width: previewUrl ? '380px' : '100%', minWidth: '340px',
        borderRight: previewUrl ? '1px solid rgba(255,255,255,0.1)' : 'none',
        transition: 'width 0.3s ease', display: 'flex', flexDirection: 'column',
      }}>
          <AIChat
        dbConfig={dbConfig}
        onWebsiteGenerated={handleWebsiteGenerated}
        onStreamEvent={handleStreamEvent}
        onArtifactHtml={(html) => {
          setArtifactHtml(html);
          if (!previewUrl) setPreviewUrl('streaming');
        }}
        onOpenGallery={() => setShowGallery(true)}
        loadedProject={loadedProject}
      />
      </div>

      {/* Right: Preview + Toolbar */}
      {previewUrl && (
        <div style={{ flex: 1, display: 'flex', flexDirection: 'column', background: '#0f172a' }}>
          {/* Toolbar */}
          <div style={{
            display: 'flex', alignItems: 'center', justifyContent: 'space-between',
            padding: '0.45rem 0.75rem', background: 'rgba(255,255,255,0.03)',
            borderBottom: '1px solid rgba(255,255,255,0.08)', flexWrap: 'wrap', gap: '0.4rem',
          }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
              <Eye size={14} style={{ color: '#94a3b8' }} />
              <span style={{ color: '#e2e8f0', fontSize: '0.8rem', fontWeight: 500, maxWidth: '120px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                {projectName}
              </span>
              <div style={{ display: 'flex', gap: '0.15rem', marginLeft: '0.25rem' }}>
                <button onClick={() => setViewport('desktop')} style={btn(viewport === 'desktop')} title="Desktop"><Monitor size={13} /></button>
                <button onClick={() => setViewport('tablet')} style={btn(viewport === 'tablet')} title="Tablet"><Tablet size={13} /></button>
                <button onClick={() => setViewport('mobile')} style={btn(viewport === 'mobile')} title="Mobile"><Smartphone size={13} /></button>
              </div>
            </div>
            <div style={{ display: 'flex', gap: '0.25rem', alignItems: 'center' }}>
              <button onClick={toggleEditMode} style={btn(editMode)} title="Visual Edit Mode">
                <MousePointer size={13} /> {editMode ? 'Exit Edit' : 'Edit'}
              </button>
              <button onClick={refreshPreview} style={btn()} title="Refresh"><RefreshCw size={13} /></button>
              <a href={previewUrl} target="_blank" rel="noopener noreferrer" style={btn()} title="Open in new tab"><ExternalLink size={13} /></a>
              <button onClick={() => { setShowRecolor(!showRecolor); setShowUpload(false); }} style={btn(showRecolor)} title="Recolor"><Palette size={13} /></button>
              <button onClick={() => { setShowUpload(!showUpload); setShowRecolor(false); }} style={btn(showUpload)} title="Upload Image"><Image size={13} /></button>
              <button onClick={handleDownload} style={btn()} title="Download ZIP"><Download size={13} /></button>
              <button onClick={handleExport} disabled={exporting} style={btn()} title="Export to GitHub">
                {exporting ? <Loader size={13} style={{ animation: 'spin 1s linear infinite' }} /> : <Github size={13} />}
              </button>
              <button onClick={handleNewProject} style={btn()} title="New Project"><Plus size={13} /></button>
              <button onClick={() => setShowGallery(true)} style={btn()} title="Past Projects"><FolderOpen size={13} /> Projects</button>
              <button onClick={() => setShowCanvas(true)} style={{
                ...btn(), background: 'linear-gradient(135deg, #667eea, #764ba2)',
                color: 'white', border: 'none', fontWeight: 600,
              }} title="Canvas Editor">
                <Code size={13} /> Canvas <ArrowRight size={11} />
              </button>
            </div>
          </div>

          {/* Status */}
          {statusMsg && (
            <div style={{
              padding: '0.4rem 0.75rem', fontSize: '0.82rem',
              background: statusMsg.startsWith('✅') ? 'rgba(16,185,129,0.15)' : 'rgba(239,68,68,0.15)',
              color: statusMsg.startsWith('✅') ? '#6ee7b7' : '#fca5a5',
              borderBottom: '1px solid rgba(255,255,255,0.05)',
            }}>
              {statusMsg}
            </div>
          )}

          {/* Recolor panel */}
          {showRecolor && (
            <div style={{
              display: 'flex', alignItems: 'center', gap: '0.5rem', padding: '0.5rem 0.75rem',
              background: 'rgba(255,255,255,0.03)', borderBottom: '1px solid rgba(255,255,255,0.08)',
              flexWrap: 'wrap',
            }}>
              {Object.entries(palette).map(([key, val]) => (
                <label key={key} style={{ display: 'flex', alignItems: 'center', gap: '0.25rem', fontSize: '0.75rem', color: '#94a3b8' }}>
                  {key}
                  <input type="color" value={val}
                    onChange={e => setPalette(p => ({ ...p, [key]: e.target.value }))}
                    style={{ width: '24px', height: '24px', border: 'none', cursor: 'pointer', background: 'transparent' }}
                  />
                </label>
              ))}
              <button onClick={handleRecolor} disabled={recoloring} style={{ ...btn(), background: '#667eea', color: 'white', border: 'none' }}>
                {recoloring ? <Loader size={12} style={{ animation: 'spin 1s linear infinite' }} /> : <Check size={12} />} Apply
              </button>
              <button onClick={() => setShowRecolor(false)} style={btn()}><X size={12} /></button>
            </div>
          )}

          {/* Upload panel */}
          {showUpload && (
            <div style={{
              display: 'flex', alignItems: 'center', gap: '0.5rem', padding: '0.5rem 0.75rem',
              background: 'rgba(255,255,255,0.03)', borderBottom: '1px solid rgba(255,255,255,0.08)',
            }}>
              <input ref={fileRef} type="file" accept="image/*" onChange={handleImageUpload}
                style={{ fontSize: '0.8rem', color: '#94a3b8' }} />
              {uploading && <Loader size={14} style={{ color: '#94a3b8', animation: 'spin 1s linear infinite' }} />}
              <button onClick={() => setShowUpload(false)} style={btn()}><X size={12} /></button>
            </div>
          )}

          {/* Main content area: ArtifactPanel during streaming, iframe after */}
          <div style={{ flex: 1, display: 'flex', overflow: 'hidden' }}>
            {/* During generation: show ArtifactPanel */}
            {isStreaming ? (
              <div style={{ flex: 1, padding: '1rem', overflow: 'hidden' }}>
                <ArtifactPanel
                  plan={streamPlan}
                  artifacts={artifacts}
                  streamLog={streamLog}
                  progress={streamProgress}
                />
              </div>
            ) : (
              <>
                {/* Post-generation: live preview iframe */}
                <div style={{
                  flex: 1, display: 'flex', justifyContent: 'center',
                  background: viewport === 'desktop' ? '#fff' : '#1e293b',
                  overflow: 'auto', padding: viewport === 'desktop' ? 0 : '1rem',
                }}>
                  <iframe
                    key={iframeSrcdoc ? `srcdoc-${previewKey}` : `src-${previewKey}`}
                    {...(iframeSrcdoc ? { srcDoc: iframeSrcdoc } : { src: iframeSrc })}
                    title="Website Preview"
                    sandbox="allow-scripts allow-same-origin allow-forms"
                    style={{
                      width: viewportWidths[viewport], maxWidth: '100%',
                      height: viewport === 'desktop' ? '100%' : '90vh',
                      border: viewport === 'desktop' ? 'none' : '2px solid rgba(255,255,255,0.1)',
                      borderRadius: viewport === 'desktop' ? 0 : '12px',
                      background: '#fff',
                      boxShadow: viewport === 'desktop' ? 'none' : '0 20px 60px rgba(0,0,0,0.5)',
                    }}
                  />
                </div>

                {/* Visual Editor panel */}
                {editMode && selectedElement && (
              <div style={{
                width: '280px', borderLeft: '1px solid rgba(255,255,255,0.1)',
                background: '#0f172a', padding: '1rem', overflowY: 'auto',
                display: 'flex', flexDirection: 'column', gap: '0.75rem',
              }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <h3 style={{ color: '#e2e8f0', fontSize: '0.9rem', fontWeight: 600, margin: 0 }}>
                    Edit &lt;{selectedElement.tag.toLowerCase()}&gt;
                  </h3>
                  <button onClick={() => setSelectedElement(null)} style={btn()}><X size={12} /></button>
                </div>

                {/* Text */}
                <div>
                  <label style={{ fontSize: '0.75rem', color: '#94a3b8', display: 'block', marginBottom: '0.25rem' }}>Text Content</label>
                  <textarea
                    value={editText}
                    onChange={e => setEditText(e.target.value)}
                    rows={3}
                    style={{ ...inputStyle, resize: 'vertical', fontFamily: 'inherit' }}
                  />
                </div>

                {/* Color */}
                <div>
                  <label style={{ fontSize: '0.75rem', color: '#94a3b8', display: 'block', marginBottom: '0.25rem' }}>Text Color</label>
                  <div style={{ display: 'flex', gap: '0.4rem', alignItems: 'center' }}>
                    <input type="color" value={editColor}
                      onChange={e => setEditColor(e.target.value)}
                      style={{ width: '32px', height: '32px', border: 'none', cursor: 'pointer', background: 'transparent' }}
                    />
                    <input type="text" value={editColor} onChange={e => setEditColor(e.target.value)} style={inputStyle} />
                  </div>
                </div>

                {/* Background Color */}
                <div>
                  <label style={{ fontSize: '0.75rem', color: '#94a3b8', display: 'block', marginBottom: '0.25rem' }}>Background</label>
                  <div style={{ display: 'flex', gap: '0.4rem', alignItems: 'center' }}>
                    <input type="color" value={editBgColor}
                      onChange={e => setEditBgColor(e.target.value)}
                      style={{ width: '32px', height: '32px', border: 'none', cursor: 'pointer', background: 'transparent' }}
                    />
                    <input type="text" value={editBgColor} onChange={e => setEditBgColor(e.target.value)} style={inputStyle} />
                  </div>
                </div>

                {/* Font Size */}
                <div>
                  <label style={{ fontSize: '0.75rem', color: '#94a3b8', display: 'block', marginBottom: '0.25rem' }}>Font Size</label>
                  <div style={{ display: 'flex', gap: '0.4rem', alignItems: 'center' }}>
                    <input type="range" min="8" max="72"
                      value={parseInt(editFontSize) || 16}
                      onChange={e => setEditFontSize(e.target.value + 'px')}
                      style={{ flex: 1, accentColor: '#667eea' }}
                    />
                    <input type="text" value={editFontSize} onChange={e => setEditFontSize(e.target.value)}
                      style={{ ...inputStyle, width: '60px', textAlign: 'center' }}
                    />
                  </div>
                </div>

                {/* Save button */}
                <button onClick={handleSaveEdit} disabled={saving} style={{
                  display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '0.4rem',
                  padding: '0.6rem', borderRadius: '8px', border: 'none', cursor: 'pointer',
                  background: 'linear-gradient(135deg, #667eea, #764ba2)',
                  color: 'white', fontWeight: 600, fontSize: '0.85rem', marginTop: '0.25rem',
                  opacity: saving ? 0.6 : 1,
                }}>
                  {saving ? <Loader size={14} style={{ animation: 'spin 1s linear infinite' }} /> : <Save size={14} />}
                  {saving ? 'Saving...' : 'Apply Changes'}
                </button>

                {/* Element info */}
                <div style={{ marginTop: 'auto', padding: '0.5rem', borderRadius: '6px', background: 'rgba(255,255,255,0.03)', border: '1px solid rgba(255,255,255,0.06)' }}>
                  <p style={{ fontSize: '0.7rem', color: '#64748b', margin: 0, wordBreak: 'break-all' }}>
                    {selectedElement.selector}
                  </p>
                </div>
              </div>
            )}

            {/* Edit mode hint when no element selected */}
            {editMode && !selectedElement && (
              <div style={{
                width: '280px', borderLeft: '1px solid rgba(255,255,255,0.1)',
                background: '#0f172a', display: 'flex', flexDirection: 'column',
                alignItems: 'center', justifyContent: 'center', padding: '2rem', gap: '0.75rem',
              }}>
                <MousePointer size={32} style={{ color: '#667eea', opacity: 0.6 }} />
                <p style={{ color: '#94a3b8', fontSize: '0.85rem', textAlign: 'center', lineHeight: 1.5 }}>
                  Click any element in the preview to edit its text, color, and font size.
                </p>
              </div>
            )}
              </>
            )}
          </div>
        </div>
      )}

      {/* CSS animation for Loader spin */}
      <style>{`
        @keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
      `}</style>

      {/* Project Gallery overlay */}
      {showGallery && (
        <ProjectGallery
          onOpen={handleOpenFromGallery}
          onClose={() => setShowGallery(false)}
        />
      )}
    </div>
  );
}
