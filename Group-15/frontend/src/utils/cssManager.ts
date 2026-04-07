import { Component } from '../types';

export class CSSManager {
  private rules: Map<string, Record<string, string>> = new Map();
  private mediaRules: Map<string, Map<string, Record<string, string>>> = new Map();
  private classCounter: Map<string, number> = new Map();

  generateClassName(type: string): string {
    const count = this.classCounter.get(type) || 0;
    this.classCounter.set(type, count + 1);
    return `cb-${type}-${count + 1}`;
  }

  generateId(type: string): string {
    const count = this.classCounter.get(`${type}-id`) || 0;
    this.classCounter.set(`${type}-id`, count + 1);
    return `${type}-${count + 1}`;
  }

  addRule(selector: string, properties: Record<string, string>, mediaQuery?: string): void {
    if (mediaQuery) {
      if (!this.mediaRules.has(mediaQuery)) {
        this.mediaRules.set(mediaQuery, new Map());
      }
      this.mediaRules.get(mediaQuery)!.set(selector, properties);
    } else {
      this.rules.set(selector, properties);
    }
  }

  updateRule(selector: string, properties: Record<string, string>, mediaQuery?: string): void {
    if (mediaQuery) {
      if (!this.mediaRules.has(mediaQuery)) {
        this.mediaRules.set(mediaQuery, new Map());
      }
      const existing = this.mediaRules.get(mediaQuery)!.get(selector) || {};
      this.mediaRules.get(mediaQuery)!.set(selector, { ...existing, ...properties });
    } else {
      const existing = this.rules.get(selector) || {};
      this.rules.set(selector, { ...existing, ...properties });
    }
  }

  deleteRule(selector: string, mediaQuery?: string): void {
    if (mediaQuery) {
      this.mediaRules.get(mediaQuery)?.delete(selector);
    } else {
      this.rules.delete(selector);
    }
  }

  getRule(selector: string, mediaQuery?: string): Record<string, string> | undefined {
    if (mediaQuery) {
      return this.mediaRules.get(mediaQuery)?.get(selector);
    }
    return this.rules.get(selector);
  }

  renameSelector(oldSelector: string, newSelector: string): void {
    const properties = this.rules.get(oldSelector);
    if (properties) {
      this.rules.delete(oldSelector);
      this.rules.set(newSelector, properties);
    }
    this.mediaRules.forEach((map) => {
      const p = map.get(oldSelector);
      if (p) {
        map.delete(oldSelector);
        map.set(newSelector, p);
      }
    });
  }

  generateCSS(): string {
    let css = '';
    this.rules.forEach((properties, selector) => {
      css += `${selector} {\n`;
      Object.entries(properties).forEach(([key, value]) => {
        const cssKey = key.replace(/([A-Z])/g, '-$1').toLowerCase();
        css += `  ${cssKey}: ${value};\n`;
      });
      css += '}\n\n';
    });
    this.mediaRules.forEach((rulesMap, mediaQuery) => {
      css += `${mediaQuery} {\n`;
      rulesMap.forEach((properties, selector) => {
        css += `  ${selector} {\n`;
        Object.entries(properties).forEach(([key, value]) => {
          const cssKey = key.replace(/([A-Z])/g, '-$1').toLowerCase();
          css += `    ${cssKey}: ${value};\n`;
        });
        css += `  }\n`;
      });
      css += '}\n\n';
    });
    return css;
  }

  parseCSS(cssText: string): void {
    this.rules.clear();
    this.mediaRules.clear();

    // A simple parser for nested media queries
    let currentMedia: string | null = null;
    let blockStart = 0;
    let inMedia = false;
    let braceCount = 0;

    for (let i = 0; i < cssText.length; i++) {
      if (cssText[i] === '{') {
        if (braceCount === 0) {
          const beforeBrace = cssText.substring(blockStart, i).trim();
          if (beforeBrace.startsWith('@media')) {
            inMedia = true;
            currentMedia = beforeBrace;
            blockStart = i + 1;
            braceCount++;
            continue;
          }
        }
        braceCount++;
      } else if (cssText[i] === '}') {
        braceCount--;
        if (braceCount === 0) {
          if (inMedia) {
            const innerCSS = cssText.substring(blockStart, i);
            this.parseRules(innerCSS, currentMedia!);
            inMedia = false;
            currentMedia = null;
          } else {
            const ruleText = cssText.substring(blockStart, i + 1);
            this.parseRules(ruleText);
          }
          blockStart = i + 1;
        }
      }
    }

    // Catch-all if CSS was flat without @media or unbalanced
    if (blockStart < cssText.length && !inMedia) {
      this.parseRules(cssText.substring(blockStart));
    }
  }

  private parseRules(cssChunk: string, mediaQuery?: string) {
    const ruleRegex = /([^{]+)\{([^}]+)\}/g;
    let match;
    while ((match = ruleRegex.exec(cssChunk)) !== null) {
      const selectors = match[1].split(',').map(s => s.trim());
      const propertiesText = match[2].trim();

      const properties: Record<string, string> = {};
      const individualRules = propertiesText.split(';').map(r => r.trim()).filter(Boolean);

      for (const rule of individualRules) {
        const firstColonIndex = rule.indexOf(':');
        if (firstColonIndex !== -1) {
          const key = rule.substring(0, firstColonIndex).trim();
          const value = rule.substring(firstColonIndex + 1).trim();
          const camelKey = key.replace(/-([a-z])/g, (g) => g[1].toUpperCase());
          properties[camelKey] = value;
        }
      }

      for (const selector of selectors) {
        if (selector) {
          this.addRule(selector, properties, mediaQuery);
        }
      }
    }
  }

  componentToCSS(component: Component): void {
    if (component.className) {
      const cleanStyles: Record<string, string> = {};
      Object.entries(component.styles.base).forEach(([key, value]) => {
        if (value !== undefined) {
          cleanStyles[key] = value;
        }
      });
      this.addRule(`.${component.className}`, cleanStyles);
    }
    if (component.customId) {
      this.addRule(`#${component.customId}`, {});
    }
    if (component.children) {
      component.children.forEach(child => this.componentToCSS(child));
    }
  }

  getAllSelectors(mediaQuery?: string): string[] {
    if (mediaQuery) {
      return Array.from(this.mediaRules.get(mediaQuery)?.keys() || []);
    }
    return Array.from(this.rules.keys());
  }
}

export const stylesToCSS = (styles: Record<string, string>): string => {
  return Object.entries(styles)
    .map(([key, value]) => {
      const cssKey = key.replace(/([A-Z])/g, '-$1').toLowerCase();
      return `  ${cssKey}: ${value};`;
    })
    .join('\n');
};

/**
 * Apply CSS string back to matching components by className.
 * Parses the CSS and updates component.styles for components whose
 * .className matches a CSS selector.
 */
export const applyCSSToComponents = (cssText: string, components: Component[]): Component[] => {
  const manager = new CSSManager();

  // Remove comments before parsing to prevent regex mess-ups
  const noCommentsCss = cssText.replace(/\/\*[\s\S]*?\*\//g, '');
  manager.parseCSS(noCommentsCss);

  const applyToComponent = (comp: Component): Component => {
    const updated = { ...comp };
    updated.styles = { ...comp.styles };

    if (comp.className) {
      // Base rule
      const rule = manager.getRule(`.${comp.className}`);
      updated.styles.base = rule ? { ...rule } : { ...comp.styles.base };

      // Hover rule
      const hoverRule = manager.getRule(`.${comp.className}:hover`);
      if (hoverRule) updated.styles.hover = { ...hoverRule };

      // Active rule
      const activeRule = manager.getRule(`.${comp.className}:active`);
      if (activeRule) updated.styles.active = { ...activeRule };

      // Tablet rule
      const tabletRule = manager.getRule(`.${comp.className}`, '@media (max-width: 768px)');
      if (tabletRule) updated.styles.tablet = { ...tabletRule };

      // Mobile rule
      const mobileRule = manager.getRule(`.${comp.className}`, '@media (max-width: 480px)');
      if (mobileRule) updated.styles.mobile = { ...mobileRule };

      // Also check wrapper rule for position/size (which should be base level)
      const wrapperRule = manager.getRule(`.${comp.className}-wrapper`);
      if (wrapperRule) {
        if (wrapperRule.left) {
          const x = parseFloat(wrapperRule.left);
          if (!isNaN(x)) updated.position = { ...(updated.position || { x: 0, y: 0 }), x };
        }
        if (wrapperRule.top) {
          const y = parseFloat(wrapperRule.top);
          if (!isNaN(y)) updated.position = { ...(updated.position || { x: 0, y: 0 }), y };
        }
        if (wrapperRule.width) {
          const w = parseFloat(wrapperRule.width);
          if (!isNaN(w)) updated.size = { ...(updated.size || { width: 200, height: 100 }), width: w };
        }
        if (wrapperRule.height) {
          const h = parseFloat(wrapperRule.height);
          if (!isNaN(h)) updated.size = { ...(updated.size || { width: 200, height: 100 }), height: h };
        }
      }
    }

    if (comp.children) {
      updated.children = comp.children.map(applyToComponent);
    }

    return updated;
  };

  return components.map(applyToComponent);
};

/**
 * Merge user-edited CSS with generated CSS.
 * User CSS rules take precedence for matching selectors.
 */
export const mergeCSS = (generatedCSS: string, userCSS: string): string => {
  const genManager = new CSSManager();
  genManager.parseCSS(generatedCSS);

  const userManager = new CSSManager();
  userManager.parseCSS(userCSS);

  // User rules override generated rules (Base)
  userManager.getAllSelectors().forEach(selector => {
    const userRule = userManager.getRule(selector);
    if (userRule) {
      genManager.addRule(selector, userRule);
    }
  });

  // Override Media Queries
  // For tablet
  userManager.getAllSelectors('@media (max-width: 768px)').forEach(selector => {
    const userRule = userManager.getRule(selector, '@media (max-width: 768px)');
    if (userRule) genManager.addRule(selector, userRule, '@media (max-width: 768px)');
  });

  // For mobile
  userManager.getAllSelectors('@media (max-width: 480px)').forEach(selector => {
    const userRule = userManager.getRule(selector, '@media (max-width: 480px)');
    if (userRule) genManager.addRule(selector, userRule, '@media (max-width: 480px)');
  });


  return genManager.generateCSS();
};
