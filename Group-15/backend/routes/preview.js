const express = require('express');
const router = express.Router();
const path = require('path');
const fs = require('fs');

// The overlay script is injected into the iframe HTML when ?editMode=1
// It highlights hovered elements and sends postMessage to the parent (our React app)
const EDITOR_OVERLAY_SCRIPT = `
<script id="__webgen_editor__">
(function() {
  // Don't run twice
  if (window.__webgenEditorActive) return;
  window.__webgenEditorActive = true;

  var highlighted = null;
  var highlightBox = null;

  // Create the highlight border overlay div
  function createHighlightBox() {
    var box = document.createElement('div');
    box.id = '__wg_highlight__';
    box.style.cssText = [
      'position:fixed',
      'pointer-events:none',
      'z-index:999999',
      'border:2px solid #a855f7',
      'border-radius:4px',
      'background:rgba(168,85,247,0.08)',
      'box-shadow:0 0 0 1px rgba(168,85,247,0.3),0 0 12px rgba(168,85,247,0.25)',
      'transition:all 0.08s ease',
      'display:none'
    ].join(';');
    document.body.appendChild(box);
    return box;
  }

  // Build a simple CSS path selector for an element
  function getSelector(el) {
    var path = [];
    var current = el;
    while (current && current !== document.body) {
      var tag = current.tagName.toLowerCase();
      var siblings = Array.from(current.parentElement ? current.parentElement.children : []);
      var sameTagSiblings = siblings.filter(function(s){ return s.tagName === current.tagName; });
      var idx = sameTagSiblings.indexOf(current);
      path.unshift(tag + (sameTagSiblings.length > 1 ? ':nth-of-type(' + (idx + 1) + ')' : ''));
      current = current.parentElement;
    }
    return path.join(' > ');
  }

  // Parse inline styles into an object
  function parseStyles(el) {
    var cs = window.getComputedStyle(el);
    return {
      color: cs.color || '',
      backgroundColor: cs.backgroundColor || '',
      fontSize: cs.fontSize || '',
      fontWeight: cs.fontWeight || '',
      textAlign: cs.textAlign || ''
    };
  }

  // Check if element is a meaningful, editable UI element
  var EDITABLE_TAGS = ['H1','H2','H3','H4','H5','H6','P','BUTTON','A','SPAN','LI','LABEL','TD','TH','DIV','SECTION','ARTICLE','HEADER','FOOTER','NAV','IMG'];
  var SKIP_TAGS = ['HTML','BODY','SCRIPT','STYLE','META','HEAD','svg','path','g'];

  function isEditable(el) {
    if (!el || !el.tagName) return false;
    if (SKIP_TAGS.indexOf(el.tagName) !== -1) return false;
    if (el.id === '__wg_highlight__') return false;
    return true;
  }

  function showHighlight(el) {
    if (!highlightBox) highlightBox = createHighlightBox();
    var rect = el.getBoundingClientRect();
    highlightBox.style.display = 'block';
    highlightBox.style.top = rect.top + 'px';
    highlightBox.style.left = rect.left + 'px';
    highlightBox.style.width = rect.width + 'px';
    highlightBox.style.height = rect.height + 'px';
  }

  function hideHighlight() {
    if (highlightBox) highlightBox.style.display = 'none';
  }

  document.addEventListener('mouseover', function(e) {
    var el = e.target;
    if (!isEditable(el)) return;
    highlighted = el;
    showHighlight(el);
  }, true);

  document.addEventListener('mouseleave', function() {
    hideHighlight();
    highlighted = null;
  }, true);

  document.addEventListener('click', function(e) {
    var el = e.target;
    if (!isEditable(el)) return;
    e.preventDefault();
    e.stopPropagation();

    var textContent = '';
    // Only get direct text, not from children
    var childNodes = Array.from(el.childNodes);
    childNodes.forEach(function(node) {
      if (node.nodeType === Node.TEXT_NODE) {
        textContent += node.textContent;
      }
    });
    textContent = textContent.trim() || el.innerText && el.innerText.trim() || '';

    window.parent.postMessage({
      type: 'WG_SELECT',
      tag: el.tagName,
      text: textContent,
      src: el.tagName === 'IMG' ? el.src : null,
      alt: el.tagName === 'IMG' ? (el.alt || '') : null,
      styles: parseStyles(el),
      selector: getSelector(el),
      outerHTML: el.outerHTML.substring(0, 300)
    }, '*');
  }, true);

  // Listen for deselect from parent
  window.addEventListener('message', function(e) {
    if (e.data && e.data.type === 'WG_DESELECT') {
      hideHighlight();
    }
  });
})();
</script>
`;

router.get('/:projectName', (req, res) => {
  const projectName = req.params.projectName;
  const htmlPath = path.join(__dirname, '../../generated-projects', projectName, 'frontend', 'index.html');

  if (!fs.existsSync(htmlPath)) {
    return res.status(404).send('Project not found');
  }

  const editMode = req.query.editMode === '1';

  if (!editMode) {
    return res.sendFile(htmlPath);
  }

  // Edit mode: inject overlay script before </body>
  try {
    let html = fs.readFileSync(htmlPath, 'utf-8');
    if (html.includes('</body>')) {
      html = html.replace('</body>', EDITOR_OVERLAY_SCRIPT + '\n</body>');
    } else {
      html += EDITOR_OVERLAY_SCRIPT;
    }
    res.setHeader('Content-Type', 'text/html; charset=utf-8');
    res.send(html);
  } catch (err) {
    console.error('Preview inject error:', err);
    res.sendFile(htmlPath);
  }
});

router.post('/save-code/:projectName', (req, res) => {
  const projectName = req.params.projectName;
  const htmlPath = path.join(__dirname, '../../generated-projects', projectName, 'frontend', 'index.html');

  if (!fs.existsSync(htmlPath)) {
    return res.status(404).json({ error: 'Project not found' });
  }

  const { html } = req.body;
  if (typeof html !== 'string') {
    return res.status(400).json({ error: '"html" field required in request body' });
  }

  try {
    fs.writeFileSync(htmlPath, html, 'utf-8');
    res.json({ success: true });
  } catch (err) {
    console.error('Save code error:', err);
    res.status(500).json({ error: err.message });
  }
});

module.exports = router;
