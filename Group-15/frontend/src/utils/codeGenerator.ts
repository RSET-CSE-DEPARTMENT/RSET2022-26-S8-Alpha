import { Component } from '../types';

export const generateCSSFromComponents = (components: Component[]): string => {
  const baseRules: Map<string, Record<string, string>> = new Map();
  const hoverRules: Map<string, Record<string, string>> = new Map();
  const activeRules: Map<string, Record<string, string>> = new Map();
  const tabletRules: Map<string, Record<string, string>> = new Map();
  const mobileRules: Map<string, Record<string, string>> = new Map();

  const processComponent = (component: Component) => {
    if (component.className) {
      const position = component.position || { x: 0, y: 0 };
      const size = component.size || { width: 200, height: 100 };

      // Base absolute positioning injected via wrapper
      const positionStyles = {
        position: 'absolute',
        left: `${position.x}px`,
        top: `${position.y}px`,
        width: `${size.width}px`,
        height: `${size.height}px`,
      };

      baseRules.set(`.${component.className}-wrapper`, positionStyles);

      // Process base styles
      const innerBaseStyles: Record<string, string> = { ...component.styles.base };
      innerBaseStyles['width'] = '100%';
      innerBaseStyles['height'] = '100%';
      innerBaseStyles['boxSizing'] = 'border-box';
      baseRules.set(`.${component.className}`, innerBaseStyles);

      // Process hover
      if (component.styles.hover && Object.keys(component.styles.hover).length > 0) {
        hoverRules.set(`.${component.className}:hover`, { ...component.styles.hover });
      }

      // Process active
      if (component.styles.active && Object.keys(component.styles.active).length > 0) {
        activeRules.set(`.${component.className}:active`, { ...component.styles.active });
      }

      // Process tablet
      if (component.styles.tablet && Object.keys(component.styles.tablet).length > 0) {
        tabletRules.set(`.${component.className}`, { ...component.styles.tablet });
      }

      // Process mobile
      if (component.styles.mobile && Object.keys(component.styles.mobile).length > 0) {
        mobileRules.set(`.${component.className}`, { ...component.styles.mobile });
      }
    }

    if (component.children) {
      component.children.forEach(processComponent);
    }
  };

  components.forEach(processComponent);

  const formatRules = (rules: Map<string, Record<string, string>>, indent = 0): string => {
    let output = '';
    const pad = ' '.repeat(indent);
    rules.forEach((properties, selector) => {
      output += `${pad}${selector} {\n`;
      Object.entries(properties).forEach(([key, value]) => {
        if (value !== undefined) {
          const cssKey = key.replace(/([A-Z])/g, '-$1').toLowerCase();
          output += `${pad}  ${cssKey}: ${value};\n`;
        }
      });
      output += `${pad}}\n\n`;
    });
    return output;
  };

  let css = '/* === Base Styles === */\n';
  css += formatRules(baseRules);

  if (hoverRules.size > 0) {
    css += '/* === Hover Styles === */\n';
    css += formatRules(hoverRules);
  }

  if (activeRules.size > 0) {
    css += '/* === Active Styles === */\n';
    css += formatRules(activeRules);
  }

  if (tabletRules.size > 0) {
    css += '/* === Tablet Breakpoint (max-width: 768px) === */\n';
    css += `@media (max-width: 768px) {\n`;
    css += formatRules(tabletRules, 2);
    css += `}\n\n`;
  }

  if (mobileRules.size > 0) {
    css += '/* === Mobile Breakpoint (max-width: 480px) === */\n';
    css += `@media (max-width: 480px) {\n`;
    css += formatRules(mobileRules, 2);
    css += `}\n\n`;
  }

  return css;
};

/**
 * Generate clean HTML body content from components.
 * No inline styles — uses class and id attributes only.
 */
export const generateBodyHTML = (components: Component[]): string => {
  const renderComponent = (component: Component, indent: number = 2): string => {
    const pad = ' '.repeat(indent);
    const className = component.className || '';
    const customId = component.customId || '';
    const wrapperClass = className ? `${className}-wrapper` : '';
    const idAttr = customId ? ` id="${customId}"` : '';

    let innerContent = '';
    switch (component.type) {
      case 'button':
        innerContent = `${pad}  <button class="${className}"${idAttr}>${component.content}</button>`;
        break;
      case 'text':
        innerContent = `${pad}  <p class="${className}"${idAttr}>${component.content}</p>`;
        break;
      case 'heading':
        innerContent = `${pad}  <h1 class="${className}"${idAttr}>${component.content}</h1>`;
        break;
      case 'image':
        innerContent = `${pad}  <img src="${component.content}" alt="Image" class="${className}"${idAttr} />`;
        break;
      case 'input':
        innerContent = `${pad}  <input type="text" placeholder="${component.content || 'Enter text...'}" class="${className}"${idAttr} />`;
        break;
      case 'textarea':
        innerContent = `${pad}  <textarea placeholder="${component.content || 'Enter text...'}" class="${className}"${idAttr}></textarea>`;
        break;
      case 'container': {
        const children = component.children?.map(c => renderComponent(c, indent + 4)).join('\n') || '';
        innerContent = children
          ? `${pad}  <div class="${className}"${idAttr}>\n${children}\n${pad}  </div>`
          : `${pad}  <div class="${className}"${idAttr}></div>`;
        break;
      }
      case 'card': {
        const [title, desc, cta] = component.content.split('|');
        innerContent = `${pad}  <div class="${className}"${idAttr}>
${pad}    <h3>${title || 'Card Title'}</h3>
${pad}    <p>${desc || 'Card description.'}</p>
${cta ? `${pad}    <a href="#">${cta}</a>` : ''}
${pad}  </div>`;
        break;
      }
      case 'navbar': {
        const parts = component.content.split('|');
        const brand = parts[0] || 'Brand';
        const links = parts.slice(1).filter(Boolean);
        const navLinks = links.map(l => `<a href="#">${l}</a>`).join('\n        ');
        innerContent = `${pad}  <nav class="${className}"${idAttr}>
${pad}    <div class="nav-brand">${brand}</div>
${pad}    <div class="nav-links">
${pad}      ${navLinks}
${pad}    </div>
${pad}  </nav>`;
        break;
      }
      case 'footer': {
        const parts = component.content.split('|');
        const [brand, copyright, ...links] = parts;
        const footerLinks = links.filter(Boolean).map(l => `<a href="#">${l}</a>`).join('\n      ');
        innerContent = `${pad}  <footer class="${className}"${idAttr}>
${pad}    <div class="footer-brand">${brand || 'Brand'}</div>
${pad}    <div class="footer-links">${footerLinks}</div>
${pad}    <p>${copyright || '© 2024 All rights reserved.'}</p>
${pad}  </footer>`;
        break;
      }
      case 'form': {
        const [title, btnText] = component.content.split('|');
        innerContent = `${pad}  <form class="${className}"${idAttr}>
${pad}    <h3>${title || 'Contact Us'}</h3>
${pad}    <div><label>Name</label><input type="text" placeholder="Your name" /></div>
${pad}    <div><label>Email</label><input type="email" placeholder="your@email.com" /></div>
${pad}    <div><label>Message</label><textarea placeholder="Your message"></textarea></div>
${pad}    <button type="submit">${btnText || 'Send Message'}</button>
${pad}  </form>`;
        break;
      }
      case 'video':
        innerContent = `${pad}  <video controls class="${className}"${idAttr}><source src="${component.content}" type="video/mp4"></video>`;
        break;
      case 'grid': {
        const parts = component.content.split('|');
        const cells: string[] = [];
        for (let i = 0; i < parts.length; i += 2) {
          cells.push(`${pad}    <div class="grid-cell"><h4>${parts[i] || 'Feature'}</h4><p>${parts[i + 1] || ''}</p></div>`);
        }
        innerContent = `${pad}  <div class="${className}"${idAttr}>\n${cells.join('\n')}\n${pad}  </div>`;
        break;
      }
      case 'list': {
        const items = component.content.split('\n').filter(item => item.trim());
        const listItems = items.map(item => `${pad}    <li>${item}</li>`).join('\n');
        innerContent = `${pad}  <ul class="${className}"${idAttr}>\n${listItems}\n${pad}  </ul>`;
        break;
      }
      case 'badge':
        innerContent = `${pad}  <span class="${className}"${idAttr}>${component.content}</span>`;
        break;
      case 'divider':
        innerContent = `${pad}  <hr class="${className}"${idAttr} />`;
        break;
      case 'link':
        innerContent = `${pad}  <a href="#" class="${className}"${idAttr}>${component.content}</a>`;
        break;
      default:
        innerContent = '';
    }

    return `${pad}<div class="${wrapperClass}">\n${innerContent}\n${pad}</div>`;
  };

  return components.map(c => renderComponent(c)).join('\n');
};

export const generateHTMLFromComponents = (
  components: Component[],
  _canvasBg: string = '#ffffff',
  _customCSS?: string
): string => {
  const bodyHTML = generateBodyHTML(components);

  return `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>ChillBuild Project</title>
  <link rel="stylesheet" href="styles.css">
</head>
<body>
<div class="canvas-container">
${bodyHTML}
</div>
</body>
</html>`;
};

export const generateSeparateCSS = (components: Component[], canvasBg: string = '#ffffff', customCSS?: string): string => {
  const generatedCSS = customCSS || generateCSSFromComponents(components);

  return `* {
  box-sizing: border-box;
  margin: 0;
  padding: 0;
}

body {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
  margin: 0;
  padding: 0;
  overflow: auto;
}

.canvas-container {
  position: relative;
  background-color: ${canvasBg};
  min-width: 1200px;
  min-height: 800px;
}

${generatedCSS}`;
};
