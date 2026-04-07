import { useState } from 'react';
import { Component, Page } from '../types';
import { Trash2, Upload, ExternalLink, Type, Layout, Sliders, Code } from 'lucide-react';
import { useWorkspace } from './WorkspaceProvider';

interface PropertiesPanelProps {
  component: Component | null;
  pages: Page[];
  onUpdateComponent: (component: Component) => void;
  onDeleteComponent: () => void;
}

type PropTab = 'content' | 'design' | 'advanced';

const GOOGLE_FONTS = [
  'Inter', 'Roboto', 'Open Sans', 'Lato', 'Montserrat', 'Poppins',
  'Nunito', 'Raleway', 'Playfair Display', 'Merriweather', 'Source Code Pro',
  'DM Sans', 'Outfit', 'Figtree', 'Plus Jakarta Sans', 'system-ui',
];

const SHADOW_PRESETS = [
  { label: 'None', value: 'none' },
  { label: 'XS', value: '0 1px 2px rgba(0,0,0,0.08)' },
  { label: 'SM', value: '0 2px 8px rgba(0,0,0,0.10)' },
  { label: 'MD', value: '0 4px 16px rgba(0,0,0,0.12)' },
  { label: 'LG', value: '0 8px 32px rgba(0,0,0,0.14)' },
  { label: 'XL', value: '0 16px 48px rgba(0,0,0,0.18)' },
  { label: 'Indigo', value: '0 8px 24px -4px rgba(99,102,241,0.4)' },
  { label: 'Rose', value: '0 8px 24px -4px rgba(244,63,94,0.4)' },
];

// Simple slider helper
function PropSlider({ label, value, onChange, min, max, step = 1, unit = 'px' }: {
  label: string; value: string; onChange: (v: string) => void;
  min: number; max: number; step?: number; unit?: string;
}) {
  const numVal = parseFloat(value) || min;
  return (
    <div className="prop-slider-group">
      <div className="prop-slider-header">
        <span className="prop-slider-label">{label}</span>
        <span className="prop-slider-value">{numVal}{unit}</span>
      </div>
      <input
        type="range" min={min} max={max} step={step} value={numVal}
        onChange={e => onChange(`${e.target.value}${unit}`)}
        className="prop-range"
      />
    </div>
  );
}

// Color input helper
function ColorProp({ label, value, onChange, placeholder = '#000000' }: {
  label: string; value: string; onChange: (v: string) => void; placeholder?: string;
}) {
  return (
    <div className="property-group">
      <label>{label}</label>
      <div className="color-input">
        <input type="color" value={value.startsWith('#') || value.startsWith('rgb') ? (value.startsWith('#') ? value : '#000000') : '#000000'}
          onChange={e => onChange(e.target.value)} />
        <input type="text" value={value} onChange={e => onChange(e.target.value)} placeholder={placeholder} />
      </div>
    </div>
  );
}

// Spacing (4-side) editor
function SpacingEditor({ label, value, onChange }: { label: string; value: string; onChange: (v: string) => void }) {
  // Parse shorthand into 4 values
  const parts = value.replace(/px/g, '').trim().split(/\s+/).map(Number);
  const [top, right, bottom, left] = parts.length === 4 ? parts : parts.length === 2 ? [parts[0], parts[1], parts[0], parts[1]] : parts.length === 1 ? [parts[0], parts[0], parts[0], parts[0]] : [0, 0, 0, 0];

  const update = (t: number, r: number, b: number, l: number) => {
    if (t === r && t === b && t === l) onChange(`${t}px`);
    else if (t === b && r === l) onChange(`${t}px ${r}px`);
    else onChange(`${t}px ${r}px ${b}px ${l}px`);
  };

  return (
    <div className="property-group">
      <label>{label}</label>
      <div className="spacing-editor">
        <div className="spacing-row">
          <input type="number" value={top} min={0} max={200} onChange={e => update(+e.target.value, right, bottom, left)}
            className="spacing-input" title="Top" />
        </div>
        <div className="spacing-middle">
          <input type="number" value={left} min={0} max={200} onChange={e => update(top, right, bottom, +e.target.value)}
            className="spacing-input" title="Left" />
          <div className="spacing-center">{label.charAt(0)}</div>
          <input type="number" value={right} min={0} max={200} onChange={e => update(top, +e.target.value, bottom, left)}
            className="spacing-input" title="Right" />
        </div>
        <div className="spacing-row">
          <input type="number" value={bottom} min={0} max={200} onChange={e => update(top, right, +e.target.value, left)}
            className="spacing-input" title="Bottom" />
        </div>
      </div>
    </div>
  );
}

// Border radius — individual corners
function BorderRadiusEditor({ value, onChange }: { value: string; onChange: (v: string) => void }) {
  const parts = value.replace(/px/g, '').trim().split(/\s+/).map(Number);
  const [tl, tr, br, bl] = parts.length === 4 ? parts : [parts[0] || 0, parts[0] || 0, parts[0] || 0, parts[0] || 0];
  const update = (a: number, b: number, c: number, d: number) => {
    if (a === b && a === c && a === d) onChange(`${a}px`);
    else onChange(`${a}px ${b}px ${c}px ${d}px`);
  };
  return (
    <div className="property-group">
      <label>Border Radius</label>
      <div className="corner-editor">
        <div className="corner-row">
          <div className="corner-input-wrap tl">
            <span className="corner-symbol">⌜</span>
            <input type="number" value={tl} min={0} max={100} onChange={e => update(+e.target.value, tr, br, bl)} className="corner-input" />
          </div>
          <div className="corner-input-wrap tr">
            <span className="corner-symbol">⌝</span>
            <input type="number" value={tr} min={0} max={100} onChange={e => update(tl, +e.target.value, br, bl)} className="corner-input" />
          </div>
        </div>
        <div className="corner-row">
          <div className="corner-input-wrap bl">
            <span className="corner-symbol">⌞</span>
            <input type="number" value={bl} min={0} max={100} onChange={e => update(tl, tr, br, +e.target.value)} className="corner-input" />
          </div>
          <div className="corner-input-wrap br">
            <span className="corner-symbol">⌟</span>
            <input type="number" value={br} min={0} max={100} onChange={e => update(tl, tr, +e.target.value, bl)} className="corner-input" />
          </div>
        </div>
      </div>
    </div>
  );
}

export default function PropertiesPanel({
  component,
  pages,
  onUpdateComponent,
  onDeleteComponent,
}: PropertiesPanelProps) {
  const { state: workspaceState } = useWorkspace();
  const { activeBreakpoint } = workspaceState;
  const [activeTab, setActiveTab] = useState<PropTab>('content');
  const [pseudoState, setPseudoState] = useState<'base' | 'hover' | 'active'>('base');
  const [bgMode, setBgMode] = useState<'solid' | 'gradient' | 'none'>('solid');
  const [gradientAngle, setGradientAngle] = useState('135');
  const [gradientFrom, setGradientFrom] = useState('#6366f1');
  const [gradientTo, setGradientTo] = useState('#8b5cf6');

  if (!component) {
    return (
      <div className="properties-panel">
        <div className="properties-header">
          <h3>Properties</h3>
        </div>
        <div className="properties-empty">
          <div className="properties-empty-icon">
            <Sliders size={32} strokeWidth={1.5} />
          </div>
          <p>Select a component to edit</p>
          <span>Click any element on the canvas to start editing its properties</span>
        </div>
      </div>
    );
  }

  const activeStyleKey = activeBreakpoint === 'desktop' ? pseudoState : activeBreakpoint;
  const currentStyles = (component.styles[activeStyleKey as keyof typeof component.styles] as Record<string, string>) || {};

  const handleContentChange = (content: string) => onUpdateComponent({ ...component, content });

  const handleStyleChange = (key: string, value: string) => {
    onUpdateComponent({
      ...component,
      styles: {
        ...component.styles,
        [activeStyleKey]: { ...currentStyles, [key]: value },
      },
    });
  };

  const handleMultiStyleChange = (changes: Record<string, string>) => {
    onUpdateComponent({
      ...component,
      styles: {
        ...component.styles,
        [activeStyleKey]: { ...currentStyles, ...changes },
      },
    });
  };

  const handleImageUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      const reader = new FileReader();
      reader.onload = (event) => handleContentChange(event.target?.result as string);
      reader.readAsDataURL(file);
    }
  };

  const applyGradient = () => {
    handleStyleChange('background', `linear-gradient(${gradientAngle}deg, ${gradientFrom}, ${gradientTo})`);
  };

  // ── CONTENT TAB ──────────────────────────────────────────────────────────────
  const renderContentTab = () => {
    switch (component.type) {
      case 'button':
        return (
          <>
            <div className="property-group">
              <label>Button Text</label>
              <input type="text" value={component.content} onChange={e => handleContentChange(e.target.value)} placeholder="Button text" />
            </div>
            <div className="property-group">
              <label>Navigate to Page</label>
              <select value={component.navigation?.targetPageId || ''}
                onChange={e => onUpdateComponent({ ...component, navigation: e.target.value ? { type: 'page', targetPageId: e.target.value } : undefined })}>
                <option value="">None</option>
                {pages.map(p => <option key={p.id} value={p.id}>{p.name}</option>)}
              </select>
            </div>
          </>
        );
      case 'text':
      case 'heading':
        return (
          <div className="property-group">
            <label>Content</label>
            <textarea value={component.content} onChange={e => handleContentChange(e.target.value)} rows={4} placeholder="Enter text" />
          </div>
        );
      case 'image':
        return (
          <>
            <div className="property-group">
              <label>Image</label>
              <input type="file" accept="image/*" onChange={handleImageUpload} style={{ display: 'none' }} id="image-upload" />
              <label htmlFor="image-upload" className="upload-label">
                <Upload size={14} /> Upload Image
              </label>
              {component.content && <img src={component.content} alt="Preview" style={{ width: '100%', borderRadius: '8px', marginTop: '8px', maxHeight: '120px', objectFit: 'cover' }} />}
              <input type="url" value={component.content.startsWith('data:') ? '' : component.content}
                onChange={e => handleContentChange(e.target.value)} placeholder="Or paste image URL" style={{ marginTop: '8px' }} />
            </div>
            <div className="property-group">
              <label>Object Fit</label>
              <select value={currentStyles.objectFit || 'cover'} onChange={e => handleStyleChange('objectFit', e.target.value)}>
                {['cover', 'contain', 'fill', 'none', 'scale-down'].map(v => <option key={v} value={v}>{v.charAt(0).toUpperCase() + v.slice(1)}</option>)}
              </select>
            </div>
          </>
        );
      case 'input':
      case 'textarea':
        return (
          <div className="property-group">
            <label>Placeholder Text</label>
            <input type="text" value={component.content} onChange={e => handleContentChange(e.target.value)} placeholder="Placeholder text" />
          </div>
        );
      case 'navbar':
        return (
          <div className="property-group">
            <label>Navbar Content <span className="prop-hint">(Brand|Link1|Link2|…)</span></label>
            <input type="text" value={component.content} onChange={e => handleContentChange(e.target.value)} placeholder="Brand|Home|About|Contact" />
          </div>
        );
      case 'footer':
        return (
          <div className="property-group">
            <label>Footer Content <span className="prop-hint">(Brand|Copyright|Link1|…)</span></label>
            <input type="text" value={component.content} onChange={e => handleContentChange(e.target.value)} placeholder="MyBrand|© 2024 All rights reserved.|Privacy" />
          </div>
        );
      case 'card':
        return (
          <div className="property-group">
            <label>Card Content <span className="prop-hint">(Title|Description|CTA)</span></label>
            <input type="text" value={component.content} onChange={e => handleContentChange(e.target.value)} placeholder="Title|Description|Learn More" />
          </div>
        );
      case 'form':
        return (
          <div className="property-group">
            <label>Form Content <span className="prop-hint">(Title|Button Text)</span></label>
            <input type="text" value={component.content} onChange={e => handleContentChange(e.target.value)} placeholder="Get in Touch|Send Message" />
          </div>
        );
      case 'grid':
        return (
          <div className="property-group">
            <label>Grid Cells <span className="prop-hint">(Title|Desc|Title|Desc|…)</span></label>
            <textarea value={component.content} onChange={e => handleContentChange(e.target.value)} rows={3} placeholder="Feature 1|Description|Feature 2|Description" />
          </div>
        );
      case 'list':
        return (
          <div className="property-group">
            <label>List Items <span className="prop-hint">(one per line)</span></label>
            <textarea value={component.content} onChange={e => handleContentChange(e.target.value)} rows={5} placeholder="Item 1&#10;Item 2&#10;Item 3" />
          </div>
        );
      case 'video':
        return (
          <div className="property-group">
            <label>Video URL</label>
            <input type="url" value={component.content} onChange={e => handleContentChange(e.target.value)} placeholder="https://..." />
          </div>
        );
      default:
        return (
          <div className="property-group">
            <label>Content</label>
            <textarea value={component.content} onChange={e => handleContentChange(e.target.value)} rows={3} placeholder="Enter content" />
          </div>
        );
    }
  };

  // ── DESIGN TAB ───────────────────────────────────────────────────────────────
  const renderDesignTab = () => (
    <>
      {/* State selector */}
      {activeBreakpoint === 'desktop' ? (
        <div className="design-section">
          <div className="design-section-title">State</div>
          <div className="state-toggle">
            {(['base', 'hover', 'active'] as const).map(s => (
              <button key={s} className={`state-btn ${pseudoState === s ? 'active' : ''}`} onClick={() => setPseudoState(s)}>
                {s === 'base' ? 'Normal' : s.charAt(0).toUpperCase() + s.slice(1)}
              </button>
            ))}
          </div>
        </div>
      ) : (
        <div className="design-section">
          <div className="design-section-title" style={{ color: '#6366f1' }}>Editing: {activeBreakpoint}</div>
        </div>
      )}

      {/* Typography */}
      <div className="design-section">
        <div className="design-section-title">
          <Type size={12} /> Typography
        </div>
        <div className="property-group">
          <label>Font Family</label>
          <select value={currentStyles.fontFamily?.split(',')[0]?.trim() || 'Inter'}
            onChange={e => handleStyleChange('fontFamily', `${e.target.value}, system-ui, sans-serif`)}>
            {GOOGLE_FONTS.map(f => <option key={f} value={f}>{f}</option>)}
          </select>
        </div>
        <div className="prop-row-2">
          <PropSlider label="Size" value={currentStyles.fontSize || '16px'} onChange={v => handleStyleChange('fontSize', v)} min={8} max={120} />
          <div className="property-group">
            <label>Weight</label>
            <select value={currentStyles.fontWeight || '400'} onChange={e => handleStyleChange('fontWeight', e.target.value)}>
              {[['300', 'Light'], ['400', 'Regular'], ['500', 'Medium'], ['600', 'Semibold'], ['700', 'Bold'], ['800', 'ExtraBold'], ['900', 'Black']].map(([v, l]) =>
                <option key={v} value={v}>{l}</option>)}
            </select>
          </div>
        </div>
        <div className="prop-row-2">
          <div className="property-group">
            <label>Align</label>
            <div className="align-buttons">
              {[['left', '←'], ['center', '↔'], ['right', '→'], ['justify', '↕']].map(([v, icon]) => (
                <button key={v} className={`align-btn ${currentStyles.textAlign === v ? 'active' : ''}`}
                  onClick={() => handleStyleChange('textAlign', v)} title={v}>{icon}</button>
              ))}
            </div>
          </div>
          <div className="property-group">
            <label>Style</label>
            <div className="align-buttons">
              <button className={`align-btn ${currentStyles.fontStyle === 'italic' ? 'active' : ''}`}
                onClick={() => handleStyleChange('fontStyle', currentStyles.fontStyle === 'italic' ? 'normal' : 'italic')}><em>I</em></button>
              <button className={`align-btn ${currentStyles.textDecoration === 'underline' ? 'active' : ''}`}
                onClick={() => handleStyleChange('textDecoration', currentStyles.textDecoration === 'underline' ? 'none' : 'underline')}><u>U</u></button>
              <button className={`align-btn ${currentStyles.textTransform === 'uppercase' ? 'active' : ''}`}
                onClick={() => handleStyleChange('textTransform', currentStyles.textTransform === 'uppercase' ? 'none' : 'uppercase')}>TT</button>
            </div>
          </div>
        </div>
        <div className="prop-row-2">
          <PropSlider label="Line Height" value={currentStyles.lineHeight || '1.5'} onChange={v => handleStyleChange('lineHeight', v)} min={1} max={3} step={0.1} unit="" />
          <PropSlider label="Letter Sp." value={currentStyles.letterSpacing || '0px'} onChange={v => handleStyleChange('letterSpacing', v)} min={-2} max={10} step={0.5} />
        </div>
        <ColorProp label="Text Color" value={currentStyles.color || '#111827'} onChange={v => handleStyleChange('color', v)} />
      </div>

      {/* Background */}
      <div className="design-section">
        <div className="design-section-title">Background</div>
        <div className="property-group">
          <div className="bg-mode-toggle">
            {(['solid', 'gradient', 'none'] as const).map(m => (
              <button key={m} className={`bg-mode-btn ${bgMode === m ? 'active' : ''}`} onClick={() => {
                setBgMode(m);
                if (m === 'none') handleStyleChange('background', 'transparent');
              }}>{m.charAt(0).toUpperCase() + m.slice(1)}</button>
            ))}
          </div>
        </div>
        {bgMode === 'solid' && (
          <ColorProp label="Color" value={currentStyles.backgroundColor || currentStyles.background || '#ffffff'}
            onChange={v => handleMultiStyleChange({ backgroundColor: v, background: v })} />
        )}
        {bgMode === 'gradient' && (
          <div className="gradient-builder">
            <div className="prop-row-2">
              <div className="property-group">
                <label>From</label>
                <div className="color-input">
                  <input type="color" value={gradientFrom} onChange={e => setGradientFrom(e.target.value)} />
                  <input type="text" value={gradientFrom} onChange={e => setGradientFrom(e.target.value)} />
                </div>
              </div>
              <div className="property-group">
                <label>To</label>
                <div className="color-input">
                  <input type="color" value={gradientTo} onChange={e => setGradientTo(e.target.value)} />
                  <input type="text" value={gradientTo} onChange={e => setGradientTo(e.target.value)} />
                </div>
              </div>
            </div>
            <PropSlider label="Angle" value={`${gradientAngle}deg`} onChange={v => setGradientAngle(v.replace('deg', ''))} min={0} max={360} unit="°" />
            <button className="apply-gradient-btn" onClick={applyGradient}>
              Apply Gradient
            </button>
            <div className="gradient-preview" style={{ background: `linear-gradient(${gradientAngle}deg, ${gradientFrom}, ${gradientTo})` }} />
          </div>
        )}
      </div>

      {/* Box Model */}
      <div className="design-section">
        <div className="design-section-title"><Layout size={12} /> Box Model</div>
        <SpacingEditor label="Padding" value={currentStyles.padding || '0px'} onChange={v => handleStyleChange('padding', v)} />
        <SpacingEditor label="Margin" value={currentStyles.margin || '0px'} onChange={v => handleStyleChange('margin', v)} />
        <BorderRadiusEditor value={currentStyles.borderRadius || '0px'} onChange={v => handleStyleChange('borderRadius', v)} />
        <div className="prop-row-2">
          <div className="property-group">
            <label>Border Style</label>
            <select value={currentStyles.borderStyle || 'none'} onChange={e => handleStyleChange('borderStyle', e.target.value)}>
              {['none', 'solid', 'dashed', 'dotted', 'double', 'groove'].map(v => <option key={v} value={v}>{v}</option>)}
            </select>
          </div>
          <PropSlider label="B. Width" value={currentStyles.borderWidth || '1px'} onChange={v => handleStyleChange('borderWidth', v)} min={0} max={12} />
        </div>
        {currentStyles.borderStyle && currentStyles.borderStyle !== 'none' && (
          <ColorProp label="Border Color" value={currentStyles.borderColor || '#e5e7eb'} onChange={v => handleStyleChange('borderColor', v)} />
        )}
      </div>

      {/* Size */}
      <div className="design-section">
        <div className="design-section-title">Size &amp; Layout</div>
        <div className="prop-row-2">
          <div className="property-group">
            <label>Width</label>
            <input type="text" value={currentStyles.width || '100%'} onChange={e => handleStyleChange('width', e.target.value)} placeholder="100%" />
          </div>
          <div className="property-group">
            <label>Height</label>
            <input type="text" value={currentStyles.height || 'auto'} onChange={e => handleStyleChange('height', e.target.value)} placeholder="auto" />
          </div>
        </div>
        <div className="prop-row-2">
          <div className="property-group">
            <label>Overflow</label>
            <select value={currentStyles.overflow || 'visible'} onChange={e => handleStyleChange('overflow', e.target.value)}>
              {['visible', 'hidden', 'scroll', 'auto', 'clip'].map(v => <option key={v} value={v}>{v}</option>)}
            </select>
          </div>
          <div className="property-group">
            <label>Z-Index</label>
            <input type="number" value={(currentStyles.zIndex || '0').toString()} onChange={e => handleStyleChange('zIndex', e.target.value)} />
          </div>
        </div>
        <div className="property-group">
          <label>Display</label>
          <select value={currentStyles.display || 'block'} onChange={e => handleStyleChange('display', e.target.value)}>
            {[['block', 'Block'], ['flex', 'Flex'], ['grid', 'Grid'], ['inline-flex', 'Inline Flex'], ['inline-block', 'Inline Block'], ['none', 'None']].map(([v, l]) =>
              <option key={v} value={v}>{l}</option>)}
          </select>
        </div>
        {(currentStyles.display === 'flex' || currentStyles.display === 'inline-flex') && (
          <>
            <div className="prop-row-2">
              <div className="property-group">
                <label>Direction</label>
                <select value={currentStyles.flexDirection || 'row'} onChange={e => handleStyleChange('flexDirection', e.target.value)}>
                  <option value="row">Row →</option>
                  <option value="column">Column ↓</option>
                  <option value="row-reverse">Row ←</option>
                  <option value="column-reverse">Col ↑</option>
                </select>
              </div>
              <div className="property-group">
                <label>Flex Wrap</label>
                <select value={currentStyles.flexWrap || 'nowrap'} onChange={e => handleStyleChange('flexWrap', e.target.value)}>
                  <option value="nowrap">No Wrap</option>
                  <option value="wrap">Wrap</option>
                  <option value="wrap-reverse">Reverse</option>
                </select>
              </div>
            </div>
            <div className="prop-row-2">
              <div className="property-group">
                <label>Justify</label>
                <select value={currentStyles.justifyContent || 'flex-start'} onChange={e => handleStyleChange('justifyContent', e.target.value)}>
                  {['flex-start', 'center', 'flex-end', 'space-between', 'space-around', 'space-evenly'].map(v => <option key={v} value={v}>{v.replace('flex-', '')}</option>)}
                </select>
              </div>
              <div className="property-group">
                <label>Align</label>
                <select value={currentStyles.alignItems || 'stretch'} onChange={e => handleStyleChange('alignItems', e.target.value)}>
                  {['stretch', 'flex-start', 'center', 'flex-end', 'baseline'].map(v => <option key={v} value={v}>{v.replace('flex-', '')}</option>)}
                </select>
              </div>
            </div>
            <PropSlider label="Gap" value={currentStyles.gap || '0px'} onChange={v => handleStyleChange('gap', v)} min={0} max={80} />
          </>
        )}
      </div>

      {/* Effects */}
      <div className="design-section">
        <div className="design-section-title"><Sliders size={12} /> Effects</div>
        <PropSlider label="Opacity" value={currentStyles.opacity || '1'} onChange={v => handleStyleChange('opacity', v)} min={0} max={1} step={0.05} unit="" />
        <div className="property-group">
          <label>Box Shadow</label>
          <div className="shadow-presets">
            {SHADOW_PRESETS.map(s => (
              <button key={s.label}
                className={`shadow-preset-btn ${currentStyles.boxShadow === s.value ? 'active' : ''}`}
                onClick={() => handleStyleChange('boxShadow', s.value)}
                title={s.value}
              >{s.label}</button>
            ))}
          </div>
          <input type="text" value={currentStyles.boxShadow || ''} onChange={e => handleStyleChange('boxShadow', e.target.value)} placeholder="0 4px 16px rgba(0,0,0,0.1)" style={{ marginTop: '6px' }} />
        </div>
        <PropSlider label="Blur (filter)" value={currentStyles.filter ? (currentStyles.filter.match(/blur\(([^)]+)\)/)?.[1] || '0px') : '0px'}
          onChange={v => { const other = (currentStyles.filter || '').replace(/blur\([^)]*\)/g, '').trim(); handleStyleChange('filter', `blur(${v}) ${other}`.trim()); }}
          min={0} max={20} />
        <div className="property-group">
          <label>Transform</label>
          <input type="text" value={currentStyles.transform || ''} onChange={e => handleStyleChange('transform', e.target.value)} placeholder="rotate(0deg) scale(1)" />
        </div>
        <div className="property-group">
          <label>Transition</label>
          <input type="text" value={currentStyles.transition || ''} onChange={e => handleStyleChange('transition', e.target.value)} placeholder="all 0.2s ease" />
        </div>
      </div>
    </>
  );

  // ── ADVANCED TAB ─────────────────────────────────────────────────────────────
  const renderAdvancedTab = () => (
    <>
      <div className="design-section">
        <div className="design-section-title"><Code size={12} /> Identity</div>
        <div className="property-group">
          <label>Element ID</label>
          <input type="text" value={component.customId || ''} onChange={e => onUpdateComponent({ ...component, customId: e.target.value })} placeholder="my-element" />
        </div>
        <div className="property-group">
          <label>CSS Class</label>
          <input type="text" value={component.className || ''} onChange={e => onUpdateComponent({ ...component, className: e.target.value })} placeholder="my-class" />
        </div>
      </div>
      <div className="design-section">
        <div className="design-section-title">Navigation</div>
        <div className="property-group">
          <label><ExternalLink size={12} style={{ display: 'inline', marginRight: '4px' }} />Navigate to Page (on click)</label>
          <select value={component.navigation?.targetPageId || ''}
            onChange={e => onUpdateComponent({ ...component, navigation: e.target.value ? { type: 'page', targetPageId: e.target.value } : undefined })}>
            <option value="">None</option>
            {pages.map(p => <option key={p.id} value={p.id}>{p.name}</option>)}
          </select>
        </div>
      </div>
      <div className="design-section">
        <div className="design-section-title">Raw CSS Override</div>
        <div className="property-group">
          <label>Custom properties <span className="prop-hint">(key: value; format)</span></label>
          <textarea
            rows={6}
            placeholder="e.g., animation: pulse 1s infinite;"
            style={{ fontFamily: 'Source Code Pro, monospace', fontSize: '12px' }}
          />
        </div>
      </div>
    </>
  );

  const tabs = [
    { id: 'content' as const, label: 'Content', icon: Type },
    { id: 'design' as const, label: 'Design', icon: Sliders },
    { id: 'advanced' as const, label: 'Advanced', icon: Code },
  ];

  return (
    <div className="properties-panel">
      <div className="properties-header">
        <div className="properties-component-badge">
          <span className="component-type-dot" />
          <h3>{component.type.charAt(0).toUpperCase() + component.type.slice(1)}</h3>
        </div>
        <button className="delete-btn" onClick={onDeleteComponent} title="Delete component">
          <Trash2 size={16} />
        </button>
      </div>

      <div className="properties-tabs">
        {tabs.map(({ id, label, icon: Icon }) => (
          <button key={id} className={`prop-tab-btn ${activeTab === id ? 'active' : ''}`} onClick={() => setActiveTab(id)}>
            <Icon size={13} />
            <span>{label}</span>
          </button>
        ))}
      </div>

      <div className="properties-content">
        {activeTab === 'content' && renderContentTab()}
        {activeTab === 'design' && renderDesignTab()}
        {activeTab === 'advanced' && renderAdvancedTab()}
      </div>
    </div>
  );
}
