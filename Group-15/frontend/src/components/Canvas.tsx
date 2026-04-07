import { useRef, useState, useCallback } from 'react';
import { ZoomIn, ZoomOut, Grid3x3, Palette, Maximize2, MousePointer2, Copy, Trash2, ChevronUp, ChevronDown, Image as ImageIcon, Film, X } from 'lucide-react';
import { Component, CanvasBgMedia } from '../types';
import { createComponent } from '../utils/componentDefaults';
import { useWorkspace } from './WorkspaceProvider';

interface CanvasProps {
  components: Component[];
  onComponentsChange: (components: Component[]) => void;
  selectedComponentId: string | null;
  onSelectComponent: (id: string | null) => void;
  canvasBg?: string;
  onCanvasBgChange?: (bg: string) => void;
  bgMedia?: CanvasBgMedia;
  onBgMediaChange?: (media: CanvasBgMedia | undefined) => void;
  onContextMenu?: (e: React.MouseEvent, componentId: string | null) => void;
  onSwitchPage?: (pageId: string) => void;
  onDuplicate?: () => void;
  onDelete?: () => void;
}

export default function Canvas({
  components,
  onComponentsChange,
  selectedComponentId,
  onSelectComponent,
  canvasBg: canvasBgProp,
  onCanvasBgChange,
  bgMedia,
  onBgMediaChange,
  onContextMenu,
  onSwitchPage,
  onDuplicate,
  onDelete,
}: CanvasProps) {
  const canvasRef = useRef<HTMLDivElement>(null);
  const { state: workspaceState } = useWorkspace();
  const { activeBreakpoint } = workspaceState;

  const canvasWidth = activeBreakpoint === 'mobile' ? 375 : activeBreakpoint === 'tablet' ? 768 : 1200;
  const canvasHeight = Math.max(800, activeBreakpoint === 'mobile' ? 667 : activeBreakpoint === 'tablet' ? 1024 : 800);

  const [draggedComponent, setDraggedComponent] = useState<string | null>(null);
  const [dragOffset, setDragOffset] = useState({ x: 0, y: 0 });
  const [resizing, setResizing] = useState<{ id: string; direction: string } | null>(null);
  const [resizeStart, setResizeStart] = useState({ x: 0, y: 0, width: 0, height: 0, left: 0, top: 0 });
  const [zoom, setZoom] = useState(100);
  const [showGrid, setShowGrid] = useState(true);
  // Inline editing
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editingValue, setEditingValue] = useState('');

  const canvasBg = canvasBgProp || '#ffffff';
  const setCanvasBg = (bg: string) => { if (onCanvasBgChange) onCanvasBgChange(bg); };

  // Background media popover
  const [showBgPicker, setShowBgPicker] = useState(false);
  const [bgTab, setBgTab] = useState<'color' | 'image' | 'video'>('color');
  const [bgUrlInput, setBgUrlInput] = useState(bgMedia?.url || '');
  const [bgOverlayOpacity, setBgOverlayOpacity] = useState(bgMedia?.overlayOpacity ?? 0.3);
  const [bgOverlayColor, setBgOverlayColor] = useState(bgMedia?.overlayColor ?? '#000000');
  const [bgSize, setBgSize] = useState<'cover' | 'contain' | 'auto'>(bgMedia?.size ?? 'cover');
  const bgImageInputRef = useRef<HTMLInputElement>(null);
  const bgVideoInputRef = useRef<HTMLInputElement>(null);

  const applyBgMedia = (type: 'image' | 'video', url: string) => {
    if (!url.trim()) return;
    const media: CanvasBgMedia = {
      type,
      url: url.trim(),
      size: bgSize,
      position: 'center center',
      overlayOpacity: bgOverlayOpacity,
      overlayColor: bgOverlayColor,
    };
    onBgMediaChange?.(media);
    setBgUrlInput(url.trim());
  };

  const removeBgMedia = () => {
    onBgMediaChange?.(undefined);
    setBgUrlInput('');
  };

  const handleBgImageUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      const reader = new FileReader();
      reader.onload = ev => applyBgMedia('image', ev.target?.result as string);
      reader.readAsDataURL(file);
    }
  };

  const handleBgVideoUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      const url = URL.createObjectURL(file);
      applyBgMedia('video', url);
    }
  };

  const GRID_SIZE = 16;
  const SNAP_THRESHOLD = 8;

  const snapToGrid = (value: number): number => {
    if (!showGrid) return value;
    const rounded = Math.round(value / GRID_SIZE) * GRID_SIZE;
    return Math.abs(rounded - value) < SNAP_THRESHOLD ? rounded : value;
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    const componentType = e.dataTransfer.getData('componentType') as Component['type'];
    const assetUrl = e.dataTransfer.getData('assetUrl');

    if (componentType && canvasRef.current) {
      const rect = canvasRef.current.getBoundingClientRect();
      const x = snapToGrid((e.clientX - rect.left) / (zoom / 100));
      const y = snapToGrid((e.clientY - rect.top) / (zoom / 100));

      const newComponent = createComponent(componentType);
      newComponent.position = { x, y };

      if (assetUrl) {
        newComponent.content = assetUrl;
      }

      onComponentsChange([...components, newComponent]);
    }
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    e.dataTransfer.dropEffect = 'copy';
  };

  const handleComponentMouseDown = (e: React.MouseEvent, component: Component) => {
    if (editingId === component.id) return;
    e.stopPropagation();
    onSelectComponent(component.id);

    if (component.position) {
      setDraggedComponent(component.id);
      setDragOffset({
        x: e.clientX - (component.position.x * zoom / 100),
        y: e.clientY - (component.position.y * zoom / 100),
      });
    }
  };

  const handleDoubleClick = (e: React.MouseEvent, component: Component) => {
    e.stopPropagation();
    const editableTypes = ['text', 'heading', 'button', 'link', 'badge', 'card', 'footer', 'navbar'];
    if (editableTypes.includes(component.type)) {
      setEditingId(component.id);
      setEditingValue(component.content);
    }
  };

  const commitEdit = useCallback((id: string, value: string) => {
    onComponentsChange(
      components.map(c => c.id === id ? { ...c, content: value } : c)
    );
    setEditingId(null);
  }, [components, onComponentsChange]);

  const handleMouseMove = (e: React.MouseEvent) => {
    if (draggedComponent && canvasRef.current) {
      const rect = canvasRef.current.getBoundingClientRect();
      const rawX = ((e.clientX - rect.left) / (zoom / 100)) - (dragOffset.x / (zoom / 100));
      const rawY = ((e.clientY - rect.top) / (zoom / 100)) - (dragOffset.y / (zoom / 100));
      const component = components.find((c) => c.id === draggedComponent);
      if (!component?.size) return;

      let newX = snapToGrid(rawX);
      let newY = snapToGrid(rawY);
      newX = Math.max(0, Math.min(newX, canvasWidth - component.size.width));
      newY = Math.max(0, Math.min(newY, canvasHeight - component.size.height));

      onComponentsChange(components.map(c =>
        c.id === draggedComponent ? { ...c, position: { x: newX, y: newY } } : c
      ));
    }

    if (resizing && canvasRef.current) {
      const rect = canvasRef.current.getBoundingClientRect();
      const mouseX = (e.clientX - rect.left) / (zoom / 100);
      const mouseY = (e.clientY - rect.top) / (zoom / 100);
      const startMouseX = resizeStart.x / (zoom / 100);
      const startMouseY = resizeStart.y / (zoom / 100);
      const deltaX = mouseX - startMouseX;
      const deltaY = mouseY - startMouseY;

      onComponentsChange(components.map(c => {
        if (c.id !== resizing.id) return c;
        const dir = resizing.direction;
        let newW = resizeStart.width;
        let newH = resizeStart.height;
        let newLeft = resizeStart.left;
        let newTop = resizeStart.top;

        if (dir.includes('e')) newW = Math.max(50, resizeStart.width + deltaX);
        if (dir.includes('s')) newH = Math.max(30, resizeStart.height + deltaY);
        if (dir.includes('w')) {
          const d = Math.min(deltaX, resizeStart.width - 50);
          newW = resizeStart.width - d;
          newLeft = resizeStart.left + d;
        }
        if (dir.includes('n')) {
          const d = Math.min(deltaY, resizeStart.height - 30);
          newH = resizeStart.height - d;
          newTop = resizeStart.top + d;
        }
        return { ...c, size: { width: newW, height: newH }, position: { x: newLeft, y: newTop } };
      }));
    }
  };

  const handleMouseUp = () => {
    setDraggedComponent(null);
    setResizing(null);
  };

  const handleResizeMouseDown = (e: React.MouseEvent, componentId: string, direction: string) => {
    e.stopPropagation();
    e.preventDefault();
    const component = components.find(c => c.id === componentId);
    if (component?.size && component.position && canvasRef.current) {
      const rect = canvasRef.current.getBoundingClientRect();
      setResizing({ id: componentId, direction });
      setResizeStart({
        x: e.clientX - rect.left,
        y: e.clientY - rect.top,
        width: component.size.width,
        height: component.size.height,
        left: component.position.x,
        top: component.position.y,
      });
    }
  };

  const moveComponentLayer = (componentId: string, direction: 'up' | 'down') => {
    const index = components.findIndex(c => c.id === componentId);
    if (index === -1) return;
    const next = [...components];
    if (direction === 'up' && index < components.length - 1)
      [next[index], next[index + 1]] = [next[index + 1], next[index]];
    else if (direction === 'down' && index > 0)
      [next[index], next[index - 1]] = [next[index - 1], next[index]];
    onComponentsChange(next);
  };

  // ─── Rich component renderers ────────────────────────────────────────────────

  const renderNavbar = (component: Component, style: React.CSSProperties, onClick: React.MouseEventHandler) => {
    const parts = component.content.split('|');
    const brand = parts[0] || 'Brand';
    const links = parts.slice(1).filter(Boolean);
    return (
      <nav style={style} onClick={onClick}>
        <div style={{ fontWeight: '800', fontSize: '20px', color: '#111827', letterSpacing: '-0.02em', fontFamily: 'Inter, system-ui, sans-serif' }}>
          {brand}
        </div>
        <div style={{ display: 'flex', gap: '32px', alignItems: 'center' }}>
          {links.map((link, i) => (
            <a key={i} href="#" style={{ fontSize: '14px', fontWeight: '500', color: i === 0 ? '#6366f1' : '#6b7280', textDecoration: 'none', transition: 'color 0.2s ease', fontFamily: 'Inter, system-ui, sans-serif' }}
              onClick={e => e.preventDefault()}>
              {link}
            </a>
          ))}
          <button style={{ background: 'linear-gradient(135deg, #6366f1, #4f46e5)', color: '#fff', border: 'none', borderRadius: '8px', padding: '8px 18px', fontSize: '14px', fontWeight: '600', cursor: 'pointer', fontFamily: 'Inter, system-ui, sans-serif' }}>
            Sign Up
          </button>
        </div>
      </nav>
    );
  };

  const renderCard = (component: Component, style: React.CSSProperties, onClick: React.MouseEventHandler) => {
    const parts = component.content.split('|');
    const title = parts[0] || 'Card Title';
    const desc = parts[1] || 'A short description of the feature or content.';
    const cta = parts[2] || 'Learn More →';
    return (
      <div style={style} onClick={onClick}>
        <div style={{ width: '44px', height: '44px', borderRadius: '12px', background: 'linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%)', display: 'flex', alignItems: 'center', justifyContent: 'center', marginBottom: '4px', flexShrink: 0 }}>
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
            <polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2" />
          </svg>
        </div>
        <h3 style={{ margin: '8px 0 6px', fontSize: '18px', fontWeight: '700', color: '#111827', fontFamily: 'Inter, system-ui, sans-serif', letterSpacing: '-0.01em' }}>{title}</h3>
        <p style={{ margin: '0 0 16px', fontSize: '14px', color: '#6b7280', lineHeight: '1.6', fontFamily: 'Inter, system-ui, sans-serif', flex: 1 }}>{desc}</p>
        <a href="#" style={{ fontSize: '14px', fontWeight: '600', color: '#6366f1', textDecoration: 'none', fontFamily: 'Inter, system-ui, sans-serif', display: 'flex', alignItems: 'center', gap: '4px' }}
          onClick={e => e.preventDefault()}>
          {cta}
        </a>
      </div>
    );
  };

  const renderFooter = (component: Component, style: React.CSSProperties, onClick: React.MouseEventHandler) => {
    const parts = component.content.split('|');
    const brand = parts[0] || 'Brand';
    const copyright = parts[1] || '© 2024 Brand. All rights reserved.';
    const links = parts.slice(2).filter(Boolean);
    return (
      <footer style={style} onClick={onClick}>
        <div style={{ fontWeight: '800', fontSize: '22px', color: '#f1f5f9', letterSpacing: '-0.02em', fontFamily: 'Inter, system-ui, sans-serif' }}>{brand}</div>
        <div style={{ display: 'flex', gap: '24px', flexWrap: 'wrap', justifyContent: 'center' }}>
          {links.map((link, i) => (
            <a key={i} href="#" style={{ color: '#94a3b8', textDecoration: 'none', fontSize: '14px', fontFamily: 'Inter, system-ui, sans-serif', transition: 'color 0.2s' }}
              onClick={e => e.preventDefault()}>
              {link}
            </a>
          ))}
        </div>
        <div style={{ borderTop: '1px solid rgba(255,255,255,0.08)', paddingTop: '24px', width: '100%', textAlign: 'center', color: '#64748b', fontSize: '13px', fontFamily: 'Inter, system-ui, sans-serif' }}>
          {copyright}
        </div>
      </footer>
    );
  };

  const renderForm = (component: Component, style: React.CSSProperties, onClick: React.MouseEventHandler) => {
    const parts = component.content.split('|');
    const title = parts[0] || 'Get in Touch';
    const btnText = parts[1] || 'Send Message';
    const inputStyle: React.CSSProperties = { width: '100%', padding: '10px 14px', borderRadius: '8px', border: '1.5px solid #e5e7eb', fontSize: '14px', color: '#111827', backgroundColor: '#f9fafb', outline: 'none', fontFamily: 'Inter, system-ui, sans-serif', boxSizing: 'border-box' };
    const labelStyle: React.CSSProperties = { fontSize: '13px', fontWeight: '600', color: '#374151', marginBottom: '5px', display: 'block', fontFamily: 'Inter, system-ui, sans-serif' };
    return (
      <form style={style} onClick={onClick} onSubmit={e => e.preventDefault()}>
        <h3 style={{ margin: '0 0 4px', fontSize: '20px', fontWeight: '700', color: '#111827', fontFamily: 'Inter, system-ui, sans-serif', letterSpacing: '-0.01em' }}>{title}</h3>
        <p style={{ margin: '0 0 8px', fontSize: '13px', color: '#9ca3af', fontFamily: 'Inter, system-ui, sans-serif' }}>Fill in the form below and we'll get back to you.</p>
        <div>
          <label style={labelStyle}>Full Name</label>
          <input type="text" placeholder="John Doe" style={inputStyle} readOnly />
        </div>
        <div>
          <label style={labelStyle}>Email Address</label>
          <input type="email" placeholder="john@example.com" style={inputStyle} readOnly />
        </div>
        <div>
          <label style={labelStyle}>Message</label>
          <textarea placeholder="How can we help you?" style={{ ...inputStyle, minHeight: '80px', resize: 'none' }} readOnly />
        </div>
        <button style={{ background: 'linear-gradient(135deg, #6366f1, #4f46e5)', color: '#fff', border: 'none', borderRadius: '10px', padding: '12px', fontSize: '14px', fontWeight: '600', cursor: 'pointer', fontFamily: 'Inter, system-ui, sans-serif', width: '100%' }}>
          {btnText}
        </button>
      </form>
    );
  };

  const renderGrid = (component: Component, style: React.CSSProperties, onClick: React.MouseEventHandler) => {
    const parts = component.content.split('|');
    const cells: { title: string; desc: string }[] = [];
    for (let i = 0; i < parts.length; i += 2) {
      cells.push({ title: parts[i] || `Feature`, desc: parts[i + 1] || 'Description here.' });
    }
    const icons = ['⚡', '📊', '🔗'];
    return (
      <div style={style} onClick={onClick}>
        {cells.map((cell, idx) => (
          <div key={idx} style={{ background: '#fff', borderRadius: '16px', padding: '24px', border: '1px solid rgba(229,231,235,0.8)', boxShadow: '0 2px 12px -2px rgba(0,0,0,0.06)', display: 'flex', flexDirection: 'column', gap: '8px' }}>
            <span style={{ fontSize: '24px' }}>{icons[idx % icons.length]}</span>
            <div style={{ fontSize: '15px', fontWeight: '700', color: '#111827', fontFamily: 'Inter, system-ui, sans-serif' }}>{cell.title}</div>
            <div style={{ fontSize: '13px', color: '#6b7280', lineHeight: '1.5', fontFamily: 'Inter, system-ui, sans-serif' }}>{cell.desc}</div>
          </div>
        ))}
      </div>
    );
  };

  const renderList = (component: Component, style: React.CSSProperties, onClick: React.MouseEventHandler) => {
    const items = component.content.split('\n').filter(item => item.trim());
    return (
      <ul style={{ ...style, padding: '0', margin: '0' }} onClick={onClick}>
        {items.map((item, index) => (
          <li key={index} style={{ display: 'flex', alignItems: 'flex-start', gap: '10px', padding: '4px 0' }}>
            <span style={{ width: '20px', height: '20px', borderRadius: '50%', background: 'linear-gradient(135deg, #6366f1, #8b5cf6)', display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0, marginTop: '1px' }}>
              <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round">
                <polyline points="20 6 9 17 4 12" />
              </svg>
            </span>
            <span style={{ fontFamily: 'Inter, system-ui, sans-serif', fontSize: (style.fontSize as string) || '15px', color: (style.color as string) || '#374151', lineHeight: '1.6' }}>{item}</span>
          </li>
        ))}
      </ul>
    );
  };

  // ─── Main render function ────────────────────────────────────────────────────

  const renderComponent = (component: Component) => {
    const isSelected = component.id === selectedComponentId;
    const isDragging = draggedComponent === component.id;
    const isEditing = editingId === component.id;

    const position = component.position || { x: 0, y: 0 };
    const size = component.size || { width: 200, height: 100 };

    const wrapperStyle: React.CSSProperties = {
      position: 'absolute',
      left: `${position.x}px`,
      top: `${position.y}px`,
      width: `${size.width}px`,
      height: `${size.height}px`,
      userSelect: 'none',
      cursor: isDragging ? 'grabbing' : 'grab',
    };

    const mergedStyles = {
      ...component.styles.base,
      ...(activeBreakpoint === 'tablet' || activeBreakpoint === 'mobile' ? component.styles.tablet : {}),
      ...(activeBreakpoint === 'mobile' ? component.styles.mobile : {}),
    } as React.CSSProperties;

    const componentStyle: React.CSSProperties = {
      ...mergedStyles,
      width: '100%',
      height: '100%',
      boxSizing: 'border-box',
    };

    const handleClick = (e: React.MouseEvent) => {
      e.stopPropagation();
      if (workspaceState.activePreset === 'preview' && component.navigation?.type === 'page') {
        if (onSwitchPage) onSwitchPage(component.navigation.targetPageId);
        return;
      }
      onSelectComponent(component.id);
    };

    let content: React.ReactNode;

    if (isEditing) {
      // Inline editing overlay
      const isMultiline = ['card', 'footer', 'navbar', 'form'].includes(component.type);
      if (isMultiline) {
        content = (
          <textarea
            autoFocus
            value={editingValue}
            onChange={e => setEditingValue(e.target.value)}
            onBlur={() => commitEdit(component.id, editingValue)}
            onKeyDown={e => { if (e.key === 'Escape') { setEditingId(null); } }}
            style={{ position: 'absolute', inset: 0, width: '100%', height: '100%', border: '2px solid #6366f1', borderRadius: '4px', padding: '8px', fontSize: '13px', resize: 'none', background: 'rgba(255,255,255,0.97)', zIndex: 10, fontFamily: 'Inter, monospace', color: '#111827', boxSizing: 'border-box' }}
            placeholder="Use | to separate parts (e.g. Brand|Home|About)"
          />
        );
      } else {
        content = (
          <input
            autoFocus
            type="text"
            value={editingValue}
            onChange={e => setEditingValue(e.target.value)}
            onBlur={() => commitEdit(component.id, editingValue)}
            onKeyDown={e => { if (e.key === 'Enter') commitEdit(component.id, editingValue); if (e.key === 'Escape') setEditingId(null); }}
            style={{ position: 'absolute', inset: 0, width: '100%', height: '100%', border: '2px solid #6366f1', borderRadius: '4px', padding: '0 8px', fontSize: '14px', background: 'rgba(255,255,255,0.97)', zIndex: 10, fontFamily: 'Inter, system-ui', color: '#111827', boxSizing: 'border-box' }}
          />
        );
      }
    } else {
      switch (component.type) {
        case 'button':
          content = <button style={{ ...componentStyle, cursor: 'inherit' }} onClick={handleClick}>{component.content}</button>;
          break;
        case 'text':
          content = <p style={{ ...componentStyle, margin: 0 }} onClick={handleClick}>{component.content}</p>;
          break;
        case 'heading':
          content = <h1 style={{ ...componentStyle, margin: 0 }} onClick={handleClick}>{component.content}</h1>;
          break;
        case 'image':
          content = <img style={componentStyle} src={component.content} alt="Component" onClick={handleClick} />;
          break;
        case 'input':
          content = (
            <input style={{ ...componentStyle, cursor: 'inherit' }} type="text" placeholder={component.content || 'Enter text...'} onClick={handleClick} readOnly />
          );
          break;
        case 'textarea':
          content = (
            <textarea style={{ ...componentStyle, cursor: 'inherit', resize: 'none' }} placeholder={component.content || 'Enter text...'} onClick={handleClick} readOnly />
          );
          break;
        case 'navbar':
          content = renderNavbar(component, componentStyle, handleClick);
          break;
        case 'card':
          content = renderCard(component, componentStyle, handleClick);
          break;
        case 'footer':
          content = renderFooter(component, componentStyle, handleClick);
          break;
        case 'form':
          content = renderForm(component, componentStyle, handleClick);
          break;
        case 'grid':
          content = renderGrid(component, componentStyle, handleClick);
          break;
        case 'list':
          content = renderList(component, componentStyle, handleClick);
          break;
        case 'container':
          content = (
            <div style={componentStyle} onClick={handleClick}>
              {component.children?.map(renderComponent)}
            </div>
          );
          break;
        case 'video':
          content = (
            <video style={componentStyle} controls onClick={handleClick}>
              <source src={component.content} type="video/mp4" />
            </video>
          );
          break;
        case 'badge':
          content = <span style={{ ...componentStyle, height: 'auto', display: 'inline-flex', alignItems: 'center' }} onClick={handleClick}>{component.content}</span>;
          break;
        case 'divider':
          content = <hr style={{ ...componentStyle, height: '1px' }} onClick={handleClick} />;
          break;
        case 'link':
          content = <a href="#" style={componentStyle} onClick={e => { e.preventDefault(); handleClick(e); }}>{component.content}</a>;
          break;
        default:
          content = <div style={componentStyle} onClick={handleClick}>{component.content}</div>;
      }
    }

    const inPreview = workspaceState.activePreset === 'preview';

    return (
      <div
        key={component.id}
        className={`canvas-component ${isSelected ? 'selected' : ''} ${isDragging ? 'dragging' : ''}`}
        style={wrapperStyle}
        onMouseDown={inPreview ? undefined : (e) => handleComponentMouseDown(e, component)}
        onDoubleClick={inPreview ? undefined : (e) => handleDoubleClick(e, component)}
        onContextMenu={(e) => {
          e.preventDefault();
          e.stopPropagation();
          onContextMenu?.(e, component.id);
        }}
      >
        {content}

        {/* Component type label */}
        {!inPreview && !isEditing && (
          <div className="component-label">
            {component.type.charAt(0).toUpperCase() + component.type.slice(1)}
          </div>
        )}

        {/* Selection overlay + handles */}
        {isSelected && !inPreview && !isEditing && (
          <>
            <div className="selection-outline" />

            {/* Size readout */}
            <div className="component-info">
              {Math.round(size.width)} × {Math.round(size.height)}
            </div>

            {/* Floating quick-action bar */}
            <div className="component-floating-bar">
              <button className="floating-action-btn" title="Bring forward" onClick={e => { e.stopPropagation(); moveComponentLayer(component.id, 'up'); }}>
                <ChevronUp size={12} />
              </button>
              <button className="floating-action-btn" title="Send backward" onClick={e => { e.stopPropagation(); moveComponentLayer(component.id, 'down'); }}>
                <ChevronDown size={12} />
              </button>
              <div className="floating-bar-divider" />
              {onDuplicate && (
                <button className="floating-action-btn" title="Duplicate (Ctrl+D)" onClick={e => { e.stopPropagation(); onDuplicate(); }}>
                  <Copy size={12} />
                </button>
              )}
              {onDelete && (
                <button className="floating-action-btn floating-delete" title="Delete (Del)" onClick={e => { e.stopPropagation(); onDelete(); }}>
                  <Trash2 size={12} />
                </button>
              )}
            </div>

            {/* 8-direction resize handles */}
            {(['nw', 'n', 'ne', 'e', 'se', 's', 'sw', 'w'] as const).map(dir => (
              <div
                key={dir}
                className={`resize-handle resize-${dir}`}
                onMouseDown={(e) => handleResizeMouseDown(e, component.id, dir)}
              />
            ))}
          </>
        )}

        {/* Editing hint */}
        {isSelected && !inPreview && !isEditing && ['text', 'heading', 'button', 'link', 'badge', 'card', 'footer', 'navbar', 'form'].includes(component.type) && (
          <div className="double-click-hint">Double-click to edit</div>
        )}
      </div>
    );
  };

  return (
    <div className="canvas-wrapper">
      <div className="canvas-toolbar">
        <div className="toolbar-section">
          <button
            className={`toolbar-btn ${showGrid ? 'active' : ''}`}
            onClick={() => setShowGrid(!showGrid)}
            title="Toggle grid snapping"
          >
            <Grid3x3 size={16} />
            <span>Grid</span>
          </button>

          {/* Background Media Picker */}
          <div style={{ position: 'relative' }}>
            <button
              className={`toolbar-btn ${bgMedia?.type && bgMedia.type !== 'none' ? 'active' : ''}`}
              onClick={() => setShowBgPicker(p => !p)}
              title="Canvas background"
            >
              {bgMedia?.type === 'video' ? <Film size={16} /> : bgMedia?.type === 'image' ? <ImageIcon size={16} /> : <Palette size={16} />}
              <span>Background</span>
              {!bgMedia?.type || bgMedia.type === 'none' ? (
                <div style={{ width: '14px', height: '14px', borderRadius: '3px', backgroundColor: canvasBg, border: '1.5px solid rgba(0,0,0,0.15)', flexShrink: 0 }} />
              ) : (
                <span style={{ fontSize: '10px', background: '#6366f1', color: '#fff', borderRadius: '4px', padding: '1px 5px', fontWeight: 700 }}>
                  {bgMedia.type === 'video' ? 'VID' : 'IMG'}
                </span>
              )}
            </button>

            {/* Popover */}
            {showBgPicker && (
              <div className="bg-media-popover">
                <div className="bg-media-header">
                  <span>Background</span>
                  <button onClick={() => setShowBgPicker(false)}><X size={14} /></button>
                </div>

                {/* Tabs */}
                <div className="bg-media-tabs">
                  {(['color', 'image', 'video'] as const).map(t => (
                    <button key={t} className={`bg-media-tab ${bgTab === t ? 'active' : ''}`} onClick={() => setBgTab(t)}>
                      {t === 'color' ? <Palette size={12} /> : t === 'image' ? <ImageIcon size={12} /> : <Film size={12} />}
                      {t.charAt(0).toUpperCase() + t.slice(1)}
                    </button>
                  ))}
                </div>

                {/* Color tab */}
                {bgTab === 'color' && (
                  <div className="bg-media-body">
                    <label className="bg-media-label">Background Color</label>
                    <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
                      <input type="color" value={canvasBg} onChange={e => setCanvasBg(e.target.value)}
                        style={{ width: '36px', height: '36px', border: '1.5px solid #e5e7eb', borderRadius: '8px', cursor: 'pointer', padding: '2px' }} />
                      <input type="text" value={canvasBg} onChange={e => setCanvasBg(e.target.value)}
                        style={{ flex: 1, padding: '7px 10px', border: '1.5px solid #e5e7eb', borderRadius: '8px', fontSize: '12px', fontFamily: 'Inter, monospace' }} />
                    </div>
                    {bgMedia?.type && bgMedia.type !== 'none' && (
                      <button className="bg-remove-btn" onClick={removeBgMedia}>Remove media background</button>
                    )}
                  </div>
                )}

                {/* Image tab */}
                {bgTab === 'image' && (
                  <div className="bg-media-body">
                    <input type="file" accept="image/*" ref={bgImageInputRef} style={{ display: 'none' }} onChange={handleBgImageUpload} />
                    <button className="bg-upload-btn" onClick={() => bgImageInputRef.current?.click()}>
                      <ImageIcon size={14} /> Upload Image
                    </button>
                    <div className="bg-media-divider">or paste URL</div>
                    <input
                      type="url"
                      placeholder="https://example.com/image.jpg"
                      value={bgUrlInput}
                      onChange={e => setBgUrlInput(e.target.value)}
                      className="bg-url-input"
                    />
                    <button className="bg-apply-btn" onClick={() => applyBgMedia('image', bgUrlInput)}>Apply Image</button>
                    <label className="bg-media-label" style={{ marginTop: '8px' }}>Fit</label>
                    <div style={{ display: 'flex', gap: '4px' }}>
                      {(['cover', 'contain', 'auto'] as const).map(s => (
                        <button key={s} className={`bg-size-btn ${bgSize === s ? 'active' : ''}`} onClick={() => setBgSize(s)}>{s}</button>
                      ))}
                    </div>
                    <label className="bg-media-label" style={{ marginTop: '8px' }}>Overlay opacity</label>
                    <input type="range" min={0} max={1} step={0.05} value={bgOverlayOpacity}
                      onChange={e => setBgOverlayOpacity(+e.target.value)} className="prop-range" />
                    {bgMedia?.type === 'image' && <button className="bg-remove-btn" onClick={removeBgMedia}>Remove</button>}
                  </div>
                )}

                {/* Video tab */}
                {bgTab === 'video' && (
                  <div className="bg-media-body">
                    <input type="file" accept="video/*" ref={bgVideoInputRef} style={{ display: 'none' }} onChange={handleBgVideoUpload} />
                    <button className="bg-upload-btn" onClick={() => bgVideoInputRef.current?.click()}>
                      <Film size={14} /> Upload Video
                    </button>
                    <div className="bg-media-divider">or paste URL</div>
                    <input
                      type="url"
                      placeholder="https://example.com/video.mp4"
                      value={bgUrlInput}
                      onChange={e => setBgUrlInput(e.target.value)}
                      className="bg-url-input"
                    />
                    <button className="bg-apply-btn" onClick={() => applyBgMedia('video', bgUrlInput)}>Apply Video</button>
                    <label className="bg-media-label" style={{ marginTop: '8px' }}>Overlay tint</label>
                    <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
                      <input type="color" value={bgOverlayColor} onChange={e => setBgOverlayColor(e.target.value)}
                        style={{ width: '30px', height: '30px', border: '1.5px solid #e5e7eb', borderRadius: '6px', cursor: 'pointer', padding: '2px' }} />
                      <input type="range" min={0} max={0.9} step={0.05} value={bgOverlayOpacity}
                        onChange={e => setBgOverlayOpacity(+e.target.value)} className="prop-range" style={{ flex: 1 }} />
                      <span style={{ fontSize: '11px', fontWeight: 700, color: '#6366f1', minWidth: '32px' }}>{Math.round(bgOverlayOpacity * 100)}%</span>
                    </div>
                    <p style={{ fontSize: '11px', color: '#9ca3af', lineHeight: 1.4, marginTop: '6px' }}>Video plays silently and loops automatically in the background.</p>
                    {bgMedia?.type === 'video' && <button className="bg-remove-btn" onClick={removeBgMedia}>Remove</button>}
                  </div>
                )}
              </div>
            )}
          </div>
        </div>

        <div className="toolbar-section">
          <span className="canvas-breakpoint-label">
            <MousePointer2 size={14} />
            {activeBreakpoint === 'desktop' ? '1200px' : activeBreakpoint === 'tablet' ? '768px' : '375px'}
          </span>
        </div>

        <div className="toolbar-section">
          <button className="toolbar-btn" onClick={() => setZoom(Math.max(25, zoom - 25))} disabled={zoom <= 25} title="Zoom out">
            <ZoomOut size={16} />
          </button>
          <span className="zoom-label">{zoom}%</span>
          <button className="toolbar-btn" onClick={() => setZoom(Math.min(200, zoom + 25))} disabled={zoom >= 200} title="Zoom in">
            <ZoomIn size={16} />
          </button>
          <button className="toolbar-btn" onClick={() => setZoom(100)} title="Reset zoom">
            <Maximize2 size={16} />
          </button>
        </div>

        <div className="toolbar-section">
          <button
            className="toolbar-btn toolbar-btn-danger"
            onClick={() => { onComponentsChange([]); onSelectComponent(null); }}
            disabled={components.length === 0}
            title="Clear canvas"
          >
            Clear All
          </button>
        </div>
      </div>

      <div className="canvas-viewport">
        <div
          className="canvas-container"
          style={{ transform: `scale(${zoom / 100})`, transformOrigin: 'top left' }}
        >
          <div
            ref={canvasRef}
            className={`canvas ${showGrid ? 'show-grid' : ''}`}
            onDrop={handleDrop}
            onDragOver={handleDragOver}
            onMouseMove={handleMouseMove}
            onMouseUp={handleMouseUp}
            onMouseLeave={handleMouseUp}
            onClick={() => { onSelectComponent(null); if (editingId) setEditingId(null); if (showBgPicker) setShowBgPicker(false); }}
            onContextMenu={(e) => { e.preventDefault(); onContextMenu?.(e, null); }}
            style={{
              backgroundColor: canvasBg,
              backgroundImage: bgMedia?.type === 'image' ? `url(${bgMedia.url})` : undefined,
              backgroundSize: bgMedia?.type === 'image' ? (bgMedia.size || 'cover') : undefined,
              backgroundPosition: bgMedia?.type === 'image' ? (bgMedia.position || 'center center') : undefined,
              backgroundRepeat: 'no-repeat',
              minWidth: `${canvasWidth}px`,
              minHeight: `${canvasHeight}px`,
              margin: '0 auto',
              width: `${canvasWidth}px`,
              overflow: 'visible',
              position: 'relative',
              boxShadow: activeBreakpoint !== 'desktop'
                ? '0 0 0 1px #e5e7eb, 0 10px 40px -5px rgba(0,0,0,0.15)'
                : 'none',
              borderRadius: activeBreakpoint !== 'desktop' ? '16px' : '0',
              transition: 'all 0.3s cubic-bezier(0.4, 0, 0.2, 1)',
            }}
          >
            {/* Video background */}
            {bgMedia?.type === 'video' && bgMedia.url && (
              <>
                <video
                  key={bgMedia.url}
                  autoPlay muted loop playsInline
                  style={{
                    position: 'absolute', inset: 0, width: '100%', height: '100%',
                    objectFit: 'cover', zIndex: 0, pointerEvents: 'none',
                    borderRadius: activeBreakpoint !== 'desktop' ? '16px' : '0',
                  }}
                >
                  <source src={bgMedia.url} type="video/mp4" />
                </video>
                {/* Overlay tint */}
                {(bgMedia.overlayOpacity ?? 0) > 0 && (
                  <div style={{
                    position: 'absolute', inset: 0, zIndex: 1, pointerEvents: 'none',
                    backgroundColor: bgMedia.overlayColor || '#000000',
                    opacity: bgMedia.overlayOpacity,
                    borderRadius: activeBreakpoint !== 'desktop' ? '16px' : '0',
                  }} />
                )}
              </>
            )}
            {/* Image overlay tint */}
            {bgMedia?.type === 'image' && (bgMedia.overlayOpacity ?? 0) > 0 && (
              <div style={{
                position: 'absolute', inset: 0, zIndex: 1, pointerEvents: 'none',
                backgroundColor: bgMedia.overlayColor || '#000000',
                opacity: bgMedia.overlayOpacity,
                borderRadius: activeBreakpoint !== 'desktop' ? '16px' : '0',
              }} />
            )}
            {components.length === 0 ? (
              <div className="canvas-empty">
                <div className="canvas-empty-icon">
                  <svg width="48" height="48" viewBox="0 0 48 48" fill="none">
                    <rect x="2" y="2" width="44" height="44" rx="12" stroke="#d1d5db" strokeWidth="2" strokeDasharray="6 4" />
                    <path d="M24 16v16M16 24h16" stroke="#9ca3af" strokeWidth="2.5" strokeLinecap="round" />
                  </svg>
                </div>
                <p className="canvas-empty-title">Drop your first component here</p>
                <p className="canvas-empty-sub">Drag from the library on the left, or use <strong>AI</strong> to generate a layout</p>
              </div>
            ) : (
              components.map(renderComponent)
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
