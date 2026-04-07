export interface Component {
  id: string;
  type: 'button' | 'text' | 'image' | 'container' | 'heading' | 'input' | 'card' | 'navbar' | 'footer' | 'form' | 'video' | 'grid' | 'list' | 'badge' | 'divider' | 'link' | 'textarea';
  content: string;
  className?: string;
  customId?: string;
  position?: {
    x: number;
    y: number;
  };
  size?: {
    width: number;
    height: number;
  };
  styles: {
    base: Record<string, string>;
    hover?: Record<string, string>;
    active?: Record<string, string>;
    tablet?: Record<string, string>;
    mobile?: Record<string, string>;
  };
  children?: Component[];
  navigation?: ComponentNavigation;
}

export interface ComponentNavigation {
  type: 'page';
  targetPageId: string;
}

export interface CSSRule {
  selector: string;
  properties: Record<string, string>;
}

export interface OnboardingTip {
  id: string;
  title: string;
  message: string;
  trigger: 'first-component' | 'first-css-edit' | 'first-class-create' | 'first-export';
  shown: boolean;
}

// === NEW: Multi-page support ===

export interface CanvasBgMedia {
  /** 'image' | 'video' | 'none' */
  type: 'image' | 'video' | 'none';
  url: string;
  /** background-size: cover | contain | auto */
  size?: 'cover' | 'contain' | 'auto';
  /** background-position string e.g. 'center center' */
  position?: string;
  /** 0–1 overlay tint opacity */
  overlayOpacity?: number;
  /** hex color for the overlay */
  overlayColor?: string;
}

export interface Page {
  id: string;
  name: string;
  components: Component[];
  cssCode: string;
  canvasBg: string;
  bgMedia?: CanvasBgMedia;
}

// === NEW: Workspace panel system ===

export type PanelId = 'components' | 'canvas' | 'properties' | 'html-editor' | 'css-editor' | 'layers';

export interface PanelConfig {
  id: PanelId;
  title: string;
  visible: boolean;
  width: number;       // percentage or pixels
  minWidth: number;
  collapsed: boolean;
}

export type LayoutPreset = 'design' | 'code' | 'preview';

export type Breakpoint = 'desktop' | 'tablet' | 'mobile';

export interface WorkspaceState {
  panels: PanelConfig[];
  activePreset: LayoutPreset;
  focusMode: boolean;
  activeBreakpoint: Breakpoint;
}
