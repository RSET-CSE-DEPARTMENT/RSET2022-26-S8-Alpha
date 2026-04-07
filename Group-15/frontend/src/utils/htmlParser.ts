import { Component } from '../types';

/**
 * Parse HTML body content back into Component array.
 * Extracts className, customId, and maps elements to the correct component types.
 */
export const parseHTMLToComponents = (html: string, existingComponents: Component[] = []): Component[] => {
  const parser = new DOMParser();
  const doc = parser.parseFromString(html, 'text/html');
  const components: Component[] = [];

  let componentIdCounter = 0;

  // Build a flat map of className -> ID from existing components to maintain stability
  const idMap = new Map<string, string>();
  const flattenIds = (comps: Component[]) => {
    comps.forEach(c => {
      if (c.className) idMap.set(c.className, c.id);
      if (c.children) flattenIds(c.children);
    });
  };
  flattenIds(existingComponents);

  const parseElement = (element: Element): Component | null => {
    componentIdCounter++;

    const tagName = element.tagName.toLowerCase();

    // Skip wrapper divs that contain a single child — descend into the actual element
    if (tagName === 'div' && element.children.length === 1) {
      const wrapperClass = element.getAttribute('class') || '';
      if (wrapperClass.endsWith('-wrapper')) {
        const inner = element.children[0];
        const comp = parseElement(inner);
        if (comp) {
          // Extract position/size from the wrapper class if available in CSS
          comp.className = comp.className || wrapperClass.replace('-wrapper', '');
        }
        return comp;
      }
    }

    const className = element.getAttribute('class') || undefined;
    const customId = element.getAttribute('id') || undefined;

    // Use existing ID if className matches, otherwise generate a new one
    const id = (className && idMap.get(className)) || `parsed-${Date.now()}-${componentIdCounter}`;

    // Build styles from inline style attribute (if any)
    const styles: Record<string, string> = {};
    const inlineStyle = element.getAttribute('style');
    if (inlineStyle) {
      inlineStyle.split(';').forEach((style) => {
        const [key, value] = style.split(':').map((s) => s.trim());
        if (key && value) {
          const camelKey = key.replace(/-([a-z])/g, (g) => g[1].toUpperCase());
          styles[camelKey] = value;
        }
      });
    }

    let type: Component['type'] = 'container';
    let content = '';

    switch (tagName) {
      case 'button':
        type = 'button';
        content = element.textContent || 'Button';
        break;
      case 'p':
        type = 'text';
        content = element.textContent || '';
        break;
      case 'h1':
      case 'h2':
      case 'h3':
      case 'h4':
      case 'h5':
      case 'h6':
        type = 'heading';
        content = element.textContent || '';
        break;
      case 'img':
        type = 'image';
        content = element.getAttribute('src') || '';
        break;
      case 'input':
        type = 'input';
        content = element.getAttribute('placeholder') || '';
        break;
      case 'textarea':
        type = 'textarea';
        content = element.getAttribute('placeholder') || '';
        break;
      case 'nav':
        type = 'navbar';
        content = '';
        break;
      case 'footer':
        type = 'footer';
        content = element.textContent || '';
        break;
      case 'form':
        type = 'form';
        content = '';
        break;
      case 'video':
        type = 'video';
        const source = element.querySelector('source');
        content = source?.getAttribute('src') || '';
        break;
      case 'ul':
      case 'ol':
        type = 'list';
        const items = Array.from(element.querySelectorAll('li'));
        content = items.map(li => li.textContent || '').join('\n');
        break;
      case 'a':
        type = 'link';
        content = element.textContent || '';
        break;
      case 'span':
        type = 'badge';
        content = element.textContent || '';
        break;
      case 'hr':
        type = 'divider';
        content = '';
        break;
      case 'div':
      case 'section':
      case 'article':
      case 'main':
      case 'aside':
      case 'header':
        // Check if it's a card (heuristic: div with text content and no children)
        if (tagName === 'div' && element.children.length === 0 && element.textContent?.trim()) {
          type = 'card';
          content = element.textContent || '';
        } else {
          type = 'container';
          content = '';
        }
        break;
      default:
        return null;
    }

    const component: Component = {
      id,
      type,
      content,
      className,
      customId,
      styles: { base: styles },
      position: { x: 0, y: 0 },
      size: { width: 200, height: 100 },
    };

    // Parse children for container-like types
    if (['container', 'navbar', 'form', 'grid'].includes(type)) {
      const children: Component[] = [];
      Array.from(element.children).forEach((child) => {
        const childComponent = parseElement(child);
        if (childComponent) {
          children.push(childComponent);
        }
      });
      if (children.length > 0) {
        component.children = children;
      }
    }

    return component;
  };

  // Try to find the canvas-container div first
  const canvasContainer = doc.querySelector('.canvas-container');
  const rootElement = canvasContainer || doc.body;

  Array.from(rootElement.children).forEach((element) => {
    const component = parseElement(element);
    if (component) {
      components.push(component);
    }
  });

  return components;
};
