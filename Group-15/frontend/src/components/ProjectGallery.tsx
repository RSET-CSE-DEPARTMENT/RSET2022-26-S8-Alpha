import { useState, useEffect } from 'react';
import { X, ExternalLink, Trash2, Clock, Globe, Database, Loader } from 'lucide-react';
import { webgenService, ProjectMeta } from '../services/webgenService';

interface ProjectGalleryProps {
  onOpen: (projectName: string, previewUrl: string, pages: string[]) => void;
  onClose: () => void;
}

export default function ProjectGallery({ onOpen, onClose }: ProjectGalleryProps) {
  const [projects, setProjects] = useState<ProjectMeta[]>([]);
  const [loading, setLoading] = useState(true);
  const [deleting, setDeleting] = useState<string | null>(null);
  const [error, setError] = useState('');

  useEffect(() => {
    (async () => {
      setLoading(true);
      const result = await webgenService.listProjects();
      if (result.error) setError(result.error);
      setProjects(result.projects);
      setLoading(false);
    })();
  }, []);

  const handleDelete = async (name: string) => {
    setDeleting(name);
    await webgenService.deleteProject(name);
    setProjects(prev => prev.filter(p => p.projectName !== name));
    setDeleting(null);
  };

  const formatDate = (iso: string) => {
    const d = new Date(iso);
    const now = new Date();
    const diffH = Math.round((now.getTime() - d.getTime()) / 3600000);
    if (diffH < 1) return 'just now';
    if (diffH < 24) return `${diffH}h ago`;
    return d.toLocaleDateString();
  };

  const overlay: React.CSSProperties = {
    position: 'fixed', inset: 0, zIndex: 50,
    background: 'rgba(0,0,0,0.6)', backdropFilter: 'blur(4px)',
    display: 'flex', justifyContent: 'flex-end',
  };

  const panel: React.CSSProperties = {
    width: '380px', height: '100%',
    background: '#0f172a', borderLeft: '1px solid rgba(255,255,255,0.1)',
    display: 'flex', flexDirection: 'column',
    animation: 'slideIn 0.2s ease',
  };

  return (
    <>
      <style>{`
        @keyframes slideIn { from { transform: translateX(100%); } to { transform: translateX(0); } }
      `}</style>
      <div style={overlay} onClick={e => { if (e.target === e.currentTarget) onClose(); }}>
        <div style={panel}>
          {/* Header */}
          <div style={{
            display: 'flex', alignItems: 'center', justifyContent: 'space-between',
            padding: '1rem 1.1rem', borderBottom: '1px solid rgba(255,255,255,0.08)',
          }}>
            <div>
              <h2 style={{ color: '#e2e8f0', fontSize: '1rem', fontWeight: 700, margin: 0 }}>Past Projects</h2>
              <p style={{ color: '#64748b', fontSize: '0.75rem', margin: '0.15rem 0 0' }}>
                {projects.length} project{projects.length !== 1 ? 's' : ''} generated
              </p>
            </div>
            <button onClick={onClose} style={{
              background: 'transparent', border: 'none', cursor: 'pointer',
              color: '#64748b', padding: '0.3rem',
            }}>
              <X size={18} />
            </button>
          </div>

          {/* Content */}
          <div style={{ flex: 1, overflowY: 'auto', padding: '0.75rem' }}>
            {loading && (
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', padding: '3rem', color: '#64748b', gap: '0.5rem' }}>
                <Loader size={16} style={{ animation: 'spin 1s linear infinite' }} /> Loading...
              </div>
            )}
            {error && !loading && (
              <p style={{ color: '#f87171', fontSize: '0.85rem', padding: '1rem', textAlign: 'center' }}>{error}</p>
            )}
            {!loading && projects.length === 0 && !error && (
              <div style={{ textAlign: 'center', padding: '3rem 1rem', color: '#64748b' }}>
                <Globe size={32} style={{ margin: '0 auto 0.75rem', opacity: 0.4 }} />
                <p style={{ fontSize: '0.9rem' }}>No projects yet.</p>
                <p style={{ fontSize: '0.8rem', marginTop: '0.25rem' }}>Generate a website to see it here.</p>
              </div>
            )}
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.6rem' }}>
              {projects.map(p => (
                <div key={p.projectName} style={{
                  background: 'rgba(255,255,255,0.04)',
                  border: '1px solid rgba(255,255,255,0.08)',
                  borderRadius: '10px', padding: '0.85rem',
                  display: 'flex', flexDirection: 'column', gap: '0.5rem',
                }}>
                  {/* Project header */}
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                    <div style={{ flex: 1, minWidth: 0 }}>
                      <p style={{ color: '#e2e8f0', fontWeight: 600, fontSize: '0.88rem', margin: 0, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                        {p.projectName}
                      </p>
                      <p style={{ color: '#64748b', fontSize: '0.75rem', margin: '0.15rem 0 0', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                        {p.description}
                      </p>
                    </div>
                    <button
                      onClick={() => handleDelete(p.projectName)}
                      disabled={deleting === p.projectName}
                      style={{
                        background: 'transparent', border: 'none', cursor: 'pointer',
                        color: deleting === p.projectName ? '#334155' : '#ef4444',
                        padding: '0.2rem', flexShrink: 0, marginLeft: '0.5rem',
                        opacity: deleting === p.projectName ? 0.5 : 1,
                      }}
                    >
                      {deleting === p.projectName
                        ? <Loader size={14} style={{ animation: 'spin 1s linear infinite' }} />
                        : <Trash2 size={14} />
                      }
                    </button>
                  </div>

                  {/* Meta row */}
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem', flexWrap: 'wrap' }}>
                    <span style={{ display: 'flex', alignItems: 'center', gap: '0.2rem', color: '#64748b', fontSize: '0.72rem' }}>
                      <Globe size={11} /> {p.pages.length} page{p.pages.length !== 1 ? 's' : ''}
                    </span>
                    {p.needsDatabase && (
                      <span style={{ display: 'flex', alignItems: 'center', gap: '0.2rem', color: '#f59e0b', fontSize: '0.72rem' }}>
                        <Database size={11} /> DB
                      </span>
                    )}
                    <span style={{ display: 'flex', alignItems: 'center', gap: '0.2rem', color: '#64748b', fontSize: '0.72rem', marginLeft: 'auto' }}>
                      <Clock size={11} /> {formatDate(p.createdAt)}
                    </span>
                  </div>

                  {/* Palette swatches */}
                  {Object.keys(p.palette).length > 0 && (
                    <div style={{ display: 'flex', gap: '0.25rem' }}>
                      {Object.values(p.palette).slice(0, 5).map((color, i) => (
                        <span key={i} style={{
                          width: 14, height: 14, borderRadius: '50%',
                          background: color as string, border: '1px solid rgba(255,255,255,0.15)',
                        }} />
                      ))}
                    </div>
                  )}

                  {/* Open button */}
                  <button
                    onClick={() => { onOpen(p.projectName, p.previewUrl, p.pages); onClose(); }}
                    style={{
                      display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '0.35rem',
                      padding: '0.45rem', borderRadius: '7px', border: 'none', cursor: 'pointer',
                      background: 'linear-gradient(135deg, #667eea, #764ba2)',
                      color: 'white', fontWeight: 600, fontSize: '0.8rem',
                    }}
                  >
                    <ExternalLink size={13} /> Open in Preview
                  </button>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
      <style>{`@keyframes spin { from{transform:rotate(0deg);} to{transform:rotate(360deg);} }`}</style>
    </>
  );
}
