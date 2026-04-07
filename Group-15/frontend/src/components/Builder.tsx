import { useState, useRef, useEffect, useCallback, useMemo } from 'react';
import { Sparkles, FolderOpen, Download, Layout, Code2, Eye, Maximize, PanelLeft, PanelRight, Undo2, Redo2, Copy, Clipboard, Trash2, CopyPlus, ChevronUp, ChevronDown, Layers, Monitor, Tablet, Smartphone } from 'lucide-react';
import WorkspaceProvider, { useWorkspace } from './WorkspaceProvider';
import ResizablePanel from './ResizablePanel';
import ComponentLibrary from './ComponentLibrary';
import Canvas from './Canvas';
import PropertiesPanel from './PropertiesPanel';
import CSSEditor from './CSSEditor';
import HTMLEditor from './HTMLEditor';
import PageTabs from './PageTabs';
import AIModal from './AIModal';
import ContextMenu, { ContextMenuItem } from './ContextMenu';
import Tooltip from './Tooltip';
import OnboardingTips from './OnboardingTips';
import LayersPanel from './LayersPanel';
import { Component, Page, OnboardingTip, LayoutPreset, CanvasBgMedia } from '../types';
import { generateCSSFromComponents, generateBodyHTML } from '../utils/codeGenerator';
import { parseHTMLToComponents } from '../utils/htmlParser';
import { applyCSSToComponents } from '../utils/cssManager';
import { AIService, AIConfig } from '../services/aiService';
import useHistory from '../hooks/useHistory';
import useKeyboardShortcuts from '../hooks/useKeyboardShortcuts';

interface BuilderProps {
  initialComponents?: Component[];
}

// Helper to create a default page
const createPage = (name: string, components: Component[] = []): Page => ({
  id: `page-${Date.now()}-${Math.random().toString(36).substr(2, 6)}`,
  name,
  components,
  cssCode: generateCSSFromComponents(components),
  canvasBg: '#ffffff',
});

// Deep-clone a component with a new unique ID
const cloneComponent = (comp: Component, offsetX = 20, offsetY = 20): Component => ({
  ...comp,
  id: `${comp.type}-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
  className: comp.className ? `${comp.className}-copy` : undefined,
  customId: comp.customId ? `${comp.customId}-copy` : undefined,
  position: comp.position
    ? { x: comp.position.x + offsetX, y: comp.position.y + offsetY }
    : undefined,
  children: comp.children?.map(c => cloneComponent(c, 0, 0)),
});

function BuilderInner({ initialComponents = [] }: BuilderProps) {
  const { state: workspaceState, setPreset, toggleFocusMode, togglePanel, isPanelVisible, setActiveBreakpoint } = useWorkspace();
  const { activeBreakpoint, activePreset, focusMode } = workspaceState;

  // Multi-page state
  const [pages, setPages] = useState<Page[]>([createPage('index', initialComponents)]);
  const [activePageId, setActivePageId] = useState(pages[0].id);
  const activePage = pages.find(p => p.id === activePageId) || pages[0];

  // === Component state WITH UNDO/REDO ===
  const {
    state: components,
    setState: setComponents,
    undo,
    redo,
    canUndo,
    canRedo,
    reset: resetHistory,
  } = useHistory<Component[]>(activePage.components);

  const [selectedComponentId, setSelectedComponentId] = useState<string | null>(null);
  const [customCSS, setCustomCSS] = useState(activePage.cssCode);
  const [htmlCode, setHtmlCode] = useState('');
  const [canvasBg, setCanvasBg] = useState(activePage.canvasBg);
  const [bgMedia, setBgMedia] = useState<CanvasBgMedia | undefined>(activePage.bgMedia);

  // UI state
  const [isAIModalOpen, setIsAIModalOpen] = useState(false);
  const [isGenerating, setIsGenerating] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Clipboard for copy/paste
  const clipboardRef = useRef<Component | null>(null);

  // Context menu state
  const [contextMenu, setContextMenu] = useState<{
    x: number;
    y: number;
    componentId: string | null;
  } | null>(null);

  // Sync flags to prevent circular updates
  const syncSourceRef = useRef<'canvas' | 'html' | 'css' | null>(null);

  const [onboardingTips, setOnboardingTips] = useState<Record<OnboardingTip['trigger'], boolean>>({
    'first-component': false,
    'first-css-edit': false,
    'first-class-create': false,
    'first-export': false,
  });

  const selectedComponent = components.find((c) => c.id === selectedComponentId) || null;

  // === SYNC: Generate HTML/CSS when components change (from canvas) ===
  useEffect(() => {
    if (syncSourceRef.current === 'html' || syncSourceRef.current === 'css') {
      syncSourceRef.current = null;
      return;
    }
    const html = generateBodyHTML(components);
    const css = generateCSSFromComponents(components);
    setHtmlCode(html);
    setCustomCSS(css);
  }, [components]);

  // === Save active page state whenever it changes ===
  useEffect(() => {
    setPages(prev => prev.map(p =>
      p.id === activePageId
        ? { ...p, components, cssCode: customCSS, canvasBg, bgMedia }
        : p
    ));
  }, [components, customCSS, canvasBg, activePageId]);

  // === Page switching ===
  const handleSwitchPage = useCallback((pageId: string) => {
    const page = pages.find(p => p.id === pageId);
    if (page) {
      setActivePageId(pageId);
      resetHistory(page.components);
      setCustomCSS(page.cssCode);
      setCanvasBg(page.canvasBg);
      setBgMedia(page.bgMedia);
      setSelectedComponentId(null);
      syncSourceRef.current = null;
    }
  }, [pages, resetHistory]);

  const handleAddPage = useCallback(() => {
    const newPage = createPage(`page-${pages.length + 1}`);
    setPages(prev => [...prev, newPage]);
    handleSwitchPage(newPage.id);
  }, [pages.length, handleSwitchPage]);

  const handleDeletePage = useCallback((pageId: string) => {
    if (pages.length <= 1) return;
    setPages(prev => {
      const next = prev.filter(p => p.id !== pageId);
      if (pageId === activePageId) {
        const switchTo = next[0];
        setActivePageId(switchTo.id);
        resetHistory(switchTo.components);
        setCustomCSS(switchTo.cssCode);
        setCanvasBg(switchTo.canvasBg);
        setBgMedia(switchTo.bgMedia);
        setSelectedComponentId(null);
      }
      return next;
    });
  }, [pages.length, activePageId, resetHistory]);

  const handleRenamePage = useCallback((pageId: string, name: string) => {
    setPages(prev => prev.map(p => p.id === pageId ? { ...p, name } : p));
  }, []);

  // === Component handlers ===
  const handleAddComponent = (component: Component) => {
    setComponents(prev => [...prev, component]);
    syncSourceRef.current = 'canvas';
  };

  const handleUpdateComponent = (updatedComponent: Component) => {
    syncSourceRef.current = 'canvas';
    setComponents(prev =>
      prev.map((c) => (c.id === updatedComponent.id ? updatedComponent : c))
    );
  };

  const handleDeleteComponent = useCallback(() => {
    if (selectedComponentId) {
      syncSourceRef.current = 'canvas';
      setComponents(prev => prev.filter((c) => c.id !== selectedComponentId));
      setSelectedComponentId(null);
    }
  }, [selectedComponentId, setComponents]);

  // === Copy / Paste / Duplicate ===
  const handleCopy = useCallback(() => {
    if (selectedComponent) {
      clipboardRef.current = selectedComponent;
    }
  }, [selectedComponent]);

  const handlePaste = useCallback(() => {
    if (clipboardRef.current) {
      const pasted = cloneComponent(clipboardRef.current);
      syncSourceRef.current = 'canvas';
      setComponents(prev => [...prev, pasted]);
      setSelectedComponentId(pasted.id);
    }
  }, [setComponents]);

  const handleDuplicate = useCallback(() => {
    if (selectedComponent) {
      const duplicated = cloneComponent(selectedComponent);
      syncSourceRef.current = 'canvas';
      setComponents(prev => [...prev, duplicated]);
      setSelectedComponentId(duplicated.id);
    }
  }, [selectedComponent, setComponents]);

  // === Nudge (arrow keys) ===
  const handleNudge = useCallback((dx: number, dy: number) => {
    if (!selectedComponentId) return;
    syncSourceRef.current = 'canvas';
    setComponents(prev =>
      prev.map(c =>
        c.id === selectedComponentId && c.position
          ? { ...c, position: { x: c.position.x + dx, y: c.position.y + dy } }
          : c
      )
    );
  }, [selectedComponentId, setComponents]);

  // === Layer ordering ===
  const handleBringForward = useCallback(() => {
    if (!selectedComponentId) return;
    setComponents(prev => {
      const idx = prev.findIndex(c => c.id === selectedComponentId);
      if (idx === -1 || idx >= prev.length - 1) return prev;
      const next = [...prev];
      [next[idx], next[idx + 1]] = [next[idx + 1], next[idx]];
      return next;
    });
  }, [selectedComponentId, setComponents]);

  const handleSendBackward = useCallback(() => {
    if (!selectedComponentId) return;
    setComponents(prev => {
      const idx = prev.findIndex(c => c.id === selectedComponentId);
      if (idx <= 0) return prev;
      const next = [...prev];
      [next[idx], next[idx - 1]] = [next[idx - 1], next[idx]];
      return next;
    });
  }, [selectedComponentId, setComponents]);

  // === Select all ===
  const handleSelectAll = useCallback(() => {
    // Select the first component if any (multi-select not supported yet)
    if (components.length > 0) {
      setSelectedComponentId(components[0].id);
    }
  }, [components]);

  // === Deselect ===
  const handleDeselect = useCallback(() => {
    setSelectedComponentId(null);
    setContextMenu(null);
  }, []);

  // === Keyboard shortcuts ===
  const shortcuts = useMemo(() => [
    { key: 'z', ctrl: true, action: undo, description: 'Undo' },
    { key: 'y', ctrl: true, action: redo, description: 'Redo' },
    { key: 'z', ctrl: true, shift: true, action: redo, description: 'Redo' },
    { key: 'Delete', action: handleDeleteComponent, description: 'Delete' },
    { key: 'Backspace', action: handleDeleteComponent, description: 'Delete' },
    { key: 'c', ctrl: true, action: handleCopy, description: 'Copy' },
    { key: 'v', ctrl: true, action: handlePaste, description: 'Paste' },
    { key: 'd', ctrl: true, action: handleDuplicate, description: 'Duplicate' },
    { key: 'a', ctrl: true, action: handleSelectAll, description: 'Select All' },
    { key: 'Escape', action: handleDeselect, description: 'Deselect' },
    { key: 'ArrowUp', action: () => handleNudge(0, -5), description: 'Nudge up' },
    { key: 'ArrowDown', action: () => handleNudge(0, 5), description: 'Nudge down' },
    { key: 'ArrowLeft', action: () => handleNudge(-5, 0), description: 'Nudge left' },
    { key: 'ArrowRight', action: () => handleNudge(5, 0), description: 'Nudge right' },
    { key: 'ArrowUp', shift: true, action: () => handleNudge(0, -1), description: 'Nudge up 1px' },
    { key: 'ArrowDown', shift: true, action: () => handleNudge(0, 1), description: 'Nudge down 1px' },
    { key: 'ArrowLeft', shift: true, action: () => handleNudge(-1, 0), description: 'Nudge left 1px' },
    { key: 'ArrowRight', shift: true, action: () => handleNudge(1, 0), description: 'Nudge right 1px' },
  ], [undo, redo, handleDeleteComponent, handleCopy, handlePaste, handleDuplicate, handleSelectAll, handleDeselect, handleNudge]);

  useKeyboardShortcuts(shortcuts);

  // === Context menu ===
  const handleContextMenu = useCallback((e: React.MouseEvent, componentId: string | null) => {
    e.preventDefault();
    setContextMenu({ x: e.clientX, y: e.clientY, componentId });
    if (componentId) {
      setSelectedComponentId(componentId);
    }
  }, []);

  const contextMenuItems: ContextMenuItem[] = useMemo(() => [
    {
      label: 'Copy',
      icon: <Copy size={14} />,
      shortcut: 'Ctrl+C',
      onClick: handleCopy,
      disabled: !selectedComponent,
    },
    {
      label: 'Paste',
      icon: <Clipboard size={14} />,
      shortcut: 'Ctrl+V',
      onClick: handlePaste,
      disabled: !clipboardRef.current,
    },
    {
      label: 'Duplicate',
      icon: <CopyPlus size={14} />,
      shortcut: 'Ctrl+D',
      onClick: handleDuplicate,
      disabled: !selectedComponent,
    },
    { label: '', onClick: () => { }, divider: true },
    {
      label: 'Bring Forward',
      icon: <ChevronUp size={14} />,
      onClick: handleBringForward,
      disabled: !selectedComponent,
    },
    {
      label: 'Send Backward',
      icon: <ChevronDown size={14} />,
      onClick: handleSendBackward,
      disabled: !selectedComponent,
    },
    { label: '', onClick: () => { }, divider: true },
    {
      label: 'Delete',
      icon: <Trash2 size={14} />,
      shortcut: 'Del',
      onClick: handleDeleteComponent,
      disabled: !selectedComponent,
    },
  ], [selectedComponent, handleCopy, handlePaste, handleDuplicate, handleBringForward, handleSendBackward, handleDeleteComponent]);

  // === HTML Editor → Canvas sync ===
  const handleHTMLChange = useCallback((newHtml: string) => {
    syncSourceRef.current = 'html';
    setHtmlCode(newHtml);
    try {
      const wrapperHtml = `<div class="canvas-container">${newHtml}</div>`;
      const parsed = parseHTMLToComponents(wrapperHtml, components);
      if (parsed.length > 0) {
        const withStyles = applyCSSToComponents(customCSS, parsed);
        setComponents(withStyles);
      }
    } catch {
      // Parsing may fail while user is typing; ignore silently
    }
  }, [customCSS, setComponents]);

  // === CSS Editor → Canvas sync ===
  const handleCSSChange = useCallback((newCSS: string) => {
    syncSourceRef.current = 'css';
    setCustomCSS(newCSS);
    try {
      const updated = applyCSSToComponents(newCSS, components);
      setComponents(updated);
    } catch {
      // Parse error while typing; ignore
    }
  }, [components, setComponents]);

  const handleCreateClass = () => {
    const className = prompt('Enter new class name (without dot):');
    if (className) {
      const newRule = `.${className} {\n  \n}\n\n`;
      setCustomCSS(prev => prev + newRule);
    }
  };

  // === AI ===
  const handleAIGenerate = async (prompt: string, config: AIConfig) => {
    setIsGenerating(true);
    setError(null);
    try {
      const aiService = new AIService(config);
      const response = await aiService.generateComponents(prompt);
      if (response.error) {
        setError(response.error);
      } else if (response.components.length > 0) {
        syncSourceRef.current = 'canvas';
        setComponents(response.components);
        setIsAIModalOpen(false);
      } else {
        setError('No components generated. Try a different prompt.');
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to generate components');
    } finally {
      setIsGenerating(false);
    }
  };

  // === Export / Save / Load ===
  const handleExport = () => {
    const exportData: Record<string, string> = {};
    pages.forEach(page => {
      const savePage = page.id === activePageId
        ? { ...page, components, cssCode: customCSS, canvasBg }
        : page;
      const html = `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>${savePage.name} - ChillBuild</title>
  <link rel="stylesheet" href="${savePage.name}.css">
</head>
<body>
<div class="canvas-container" style="background-color: ${savePage.canvasBg}; position: relative; min-width: 1200px; min-height: 800px;">
${generateBodyHTML(savePage.components)}
</div>
</body>
</html>`;
      exportData[`${savePage.name}.html`] = html;
      exportData[`${savePage.name}.css`] = savePage.cssCode;
    });

    const blob = new Blob([JSON.stringify(exportData, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `chillbuild-export-${Date.now()}.json`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  const handleSaveProject = () => {
    const project = {
      name: 'ChillBuild Project',
      pages: pages.map(p => p.id === activePageId
        ? { ...p, components, cssCode: customCSS, canvasBg }
        : p
      ),
      activePageId,
      onboardingTips,
      savedAt: new Date().toISOString(),
    };

    const blob = new Blob([JSON.stringify(project, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `chillbuild-project-${Date.now()}.json`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  const handleLoadProject = () => {
    fileInputRef.current?.click();
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      const reader = new FileReader();
      reader.onload = (event) => {
        try {
          const content = event.target?.result as string;
          const project = JSON.parse(content);

          if (project.pages) {
            setPages(project.pages);
            const firstPage = project.pages[0];
            setActivePageId(project.activePageId || firstPage.id);
            const active = project.pages.find((p: Page) => p.id === project.activePageId) || firstPage;
            resetHistory(active.components);
            setCustomCSS(active.cssCode);
            setCanvasBg(active.canvasBg);
          } else if (project.components) {
            const migrated = createPage('index', project.components);
            migrated.cssCode = project.customCSS || generateCSSFromComponents(project.components);
            migrated.canvasBg = project.canvasBg || '#ffffff';
            setPages([migrated]);
            setActivePageId(migrated.id);
            resetHistory(migrated.components);
            setCustomCSS(migrated.cssCode);
            setCanvasBg(migrated.canvasBg);
          } else {
            setError('Invalid project file');
            return;
          }

          if (project.onboardingTips) setOnboardingTips(project.onboardingTips);
          setError(null);
          setSelectedComponentId(null);
        } catch {
          setError('Failed to load project file');
        }
      };
      reader.readAsText(file);
    }
  };

  const dismissTip = (trigger: OnboardingTip['trigger']) => {
    setOnboardingTips({ ...onboardingTips, [trigger]: true });
  };

  const presetButtons: { preset: LayoutPreset; icon: typeof Layout; label: string }[] = [
    { preset: 'design', icon: Layout, label: 'Design' },
    { preset: 'code', icon: Code2, label: 'Code' },
    { preset: 'preview', icon: Eye, label: 'Preview' },
  ];

  return (
    <div className={`builder ${focusMode ? 'focus-mode' : ''}`}>
      {/* Header */}
      <header className="builder-header">
        <div className="builder-logo">
          <Sparkles size={24} />
          <h1>CHILLBUILD</h1>
        </div>

        <div className="builder-presets">
          {presetButtons.map(({ preset, icon: Icon, label }) => (
            <button
              key={preset}
              className={`preset-btn ${activePreset === preset ? 'active' : ''}`}
              onClick={() => setPreset(preset)}
              title={`${label} Mode`}
            >
              <Icon size={16} />
              <span>{label}</span>
            </button>
          ))}
          <div className="preset-divider" />
          <Tooltip content="Toggle focus mode — full canvas view">
            <button
              className={`preset-btn ${focusMode ? 'active' : ''}`}
              onClick={toggleFocusMode}
            >
              <Maximize size={16} />
            </button>
          </Tooltip>
        </div>

        {/* Breakpoint Switcher */}
        <div className="builder-breakpoints" style={{ display: 'flex', gap: '4px', background: '#f3f4f6', padding: '4px', borderRadius: '6px' }}>
          <Tooltip content="Desktop (Base)">
            <button
              className={`action-btn ${activeBreakpoint === 'desktop' ? 'active' : ''}`}
              onClick={() => setActiveBreakpoint('desktop')}
              style={{ background: activeBreakpoint === 'desktop' ? '#ffffff' : 'transparent', boxShadow: activeBreakpoint === 'desktop' ? '0 1px 2px rgba(0,0,0,0.1)' : 'none' }}
            >
              <Monitor size={16} />
            </button>
          </Tooltip>
          <Tooltip content="Tablet (< 768px)">
            <button
              className={`action-btn ${activeBreakpoint === 'tablet' ? 'active' : ''}`}
              onClick={() => setActiveBreakpoint('tablet')}
              style={{ background: activeBreakpoint === 'tablet' ? '#ffffff' : 'transparent', boxShadow: activeBreakpoint === 'tablet' ? '0 1px 2px rgba(0,0,0,0.1)' : 'none' }}
            >
              <Tablet size={16} />
            </button>
          </Tooltip>
          <Tooltip content="Mobile (< 480px)">
            <button
              className={`action-btn ${activeBreakpoint === 'mobile' ? 'active' : ''}`}
              onClick={() => setActiveBreakpoint('mobile')}
              style={{ background: activeBreakpoint === 'mobile' ? '#ffffff' : 'transparent', boxShadow: activeBreakpoint === 'mobile' ? '0 1px 2px rgba(0,0,0,0.1)' : 'none' }}
            >
              <Smartphone size={16} />
            </button>
          </Tooltip>
        </div>

        {/* Undo / Redo */}
        <div className="builder-history">
          <Tooltip content="Undo (Ctrl+Z)">
            <button
              className={`history-btn ${!canUndo ? 'disabled' : ''}`}
              onClick={undo}
              disabled={!canUndo}
            >
              <Undo2 size={18} />
            </button>
          </Tooltip>
          <Tooltip content="Redo (Ctrl+Y)">
            <button
              className={`history-btn ${!canRedo ? 'disabled' : ''}`}
              onClick={redo}
              disabled={!canRedo}
            >
              <Redo2 size={18} />
            </button>
          </Tooltip>
        </div>

        <div className="builder-actions">
          <input
            ref={fileInputRef}
            type="file"
            accept=".json"
            onChange={handleFileChange}
            style={{ display: 'none' }}
          />
          <Tooltip content="Toggle Components Panel">
            <button
              className={`action-btn ${isPanelVisible('components') ? 'active' : ''}`}
              onClick={() => togglePanel('components')}
            >
              <PanelLeft size={18} />
            </button>
          </Tooltip>
          <Tooltip content="Toggle Layers Panel">
            <button
              className={`action-btn ${isPanelVisible('layers') ? 'active' : ''}`}
              onClick={() => togglePanel('layers')}
            >
              <Layers size={18} />
            </button>
          </Tooltip>
          <Tooltip content="Toggle Properties Panel">
            <button
              className={`action-btn ${isPanelVisible('properties') ? 'active' : ''}`}
              onClick={() => togglePanel('properties')}
            >
              <PanelRight size={18} />
            </button>
          </Tooltip>
          <Tooltip content="Save project">
            <button className="action-btn" onClick={handleSaveProject}>
              <FolderOpen size={18} />
              Save
            </button>
          </Tooltip>
          <Tooltip content="Load project">
            <button className="action-btn" onClick={handleLoadProject}>
              <FolderOpen size={18} />
              Load
            </button>
          </Tooltip>
          <Tooltip content="Export as HTML/CSS">
            <button className="action-btn" onClick={handleExport}>
              <Download size={18} />
              Export
            </button>
          </Tooltip>
          <Tooltip content="Generate with AI">
            <button className="action-btn ai-btn" onClick={() => setIsAIModalOpen(true)}>
              <Sparkles size={18} />
              AI
            </button>
          </Tooltip>
        </div>
      </header>

      {/* Page Tabs */}
      <PageTabs
        pages={pages}
        activePageId={activePageId}
        onSwitchPage={handleSwitchPage}
        onAddPage={handleAddPage}
        onDeletePage={handleDeletePage}
        onRenamePage={handleRenamePage}
      />

      {error && (
        <div className="error-banner">
          <p>{error}</p>
          <button onClick={() => setError(null)}>×</button>
        </div>
      )}

      {/* Workspace */}
      <div className="builder-workspace">
        {/* Left: Components Panel */}
        {isPanelVisible('components') && (
          <ResizablePanel
            defaultWidth={220}
            minWidth={180}
            maxWidth={350}
            direction="right"
            className="panel-components"
          >
            <ComponentLibrary onAddComponent={handleAddComponent} />
          </ResizablePanel>
        )}

        {/* Left: Layers Panel */}
        {isPanelVisible('layers') && (
          <ResizablePanel
            defaultWidth={220}
            minWidth={180}
            maxWidth={350}
            direction="right"
            className="panel-components"
          >
            <div className="panel-header">
              <h3>Layers</h3>
            </div>
            <LayersPanel
              components={components}
              selectedId={selectedComponentId}
              onSelect={setSelectedComponentId}
              onUpdate={(newComponents) => {
                syncSourceRef.current = 'canvas';
                setComponents(newComponents);
              }}
            />
          </ResizablePanel>
        )}

        {/* Center: Canvas (always visible) */}
        <main className="builder-main">
          <Canvas
            components={components}
            onComponentsChange={(newComponents) => {
              syncSourceRef.current = 'canvas';
              setComponents(newComponents);
            }}
            selectedComponentId={selectedComponentId}
            onSelectComponent={setSelectedComponentId}
            canvasBg={canvasBg}
            onCanvasBgChange={setCanvasBg}
            bgMedia={bgMedia}
            onBgMediaChange={setBgMedia}
            onContextMenu={handleContextMenu}
            onSwitchPage={handleSwitchPage}
            onDuplicate={handleDuplicate}
            onDelete={handleDeleteComponent}
          />
        </main>

        {/* Right side: Editors + Properties */}
        <div className="builder-right-panels">
          {isPanelVisible('html-editor') && (
            <ResizablePanel
              defaultWidth={400}
              minWidth={250}
              maxWidth={700}
              direction="left"
              className="panel-editor"
            >
              <HTMLEditor
                html={htmlCode}
                onChange={handleHTMLChange}
                onClose={() => togglePanel('html-editor')}
              />
            </ResizablePanel>
          )}

          {isPanelVisible('css-editor') && (
            <ResizablePanel
              defaultWidth={400}
              minWidth={250}
              maxWidth={700}
              direction="left"
              className="panel-editor"
            >
              <CSSEditor
                css={customCSS}
                onChange={handleCSSChange}
                selectedComponent={selectedComponent}
                onCreateClass={handleCreateClass}
                onClose={() => togglePanel('css-editor')}
              />
            </ResizablePanel>
          )}

          {isPanelVisible('properties') && (
            <ResizablePanel
              defaultWidth={280}
              minWidth={220}
              maxWidth={450}
              direction="left"
              className="panel-properties"
            >
              <PropertiesPanel
                component={selectedComponent}
                pages={pages}
                onUpdateComponent={handleUpdateComponent}
                onDeleteComponent={handleDeleteComponent}
              />
            </ResizablePanel>
          )}
        </div>
      </div>

      {/* Context Menu */}
      {contextMenu && (
        <ContextMenu
          x={contextMenu.x}
          y={contextMenu.y}
          isOpen={true}
          items={contextMenuItems}
          onClose={() => setContextMenu(null)}
        />
      )}

      {/* AI Modal */}
      <AIModal
        isOpen={isAIModalOpen}
        onClose={() => setIsAIModalOpen(false)}
        onGenerate={handleAIGenerate}
        isGenerating={isGenerating}
      />

      {/* Onboarding */}
      {components.length === 1 && (
        <OnboardingTips
          trigger="first-component"
          onDismiss={dismissTip}
          shown={onboardingTips['first-component']}
        />
      )}
    </div>
  );
}

export default function Builder(props: BuilderProps) {
  return (
    <WorkspaceProvider>
      <BuilderInner {...props} />
    </WorkspaceProvider>
  );
}
