import { useState, useRef, useCallback, useEffect } from 'react';
import { Editor } from '@monaco-editor/react';
import { Copy, Check, Plus, FileCode } from 'lucide-react';
import { Component } from '../types';
import PanelHeader from './PanelHeader';

interface CSSEditorProps {
  css: string;
  onChange: (css: string) => void;
  selectedComponent: Component | null;
  onCreateClass: () => void;
  onClose?: () => void;
}

export default function CSSEditor({ css, onChange, selectedComponent, onCreateClass, onClose }: CSSEditorProps) {
  const [copied, setCopied] = useState(false);
  const [localValue, setLocalValue] = useState(css);
  const [highlightedLine, setHighlightedLine] = useState<number | null>(null);
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Sync incoming CSS
  const prevCssRef = useRef(css);
  useEffect(() => {
    if (css !== prevCssRef.current) {
      setLocalValue(css);
      prevCssRef.current = css;
    }
  }, [css]);

  useEffect(() => {
    if (selectedComponent?.className) {
      const lines = localValue.split('\n');
      const lineIndex = lines.findIndex(line => line.includes(`.${selectedComponent.className}`));
      if (lineIndex !== -1) {
        setHighlightedLine(lineIndex + 1);
      }
    } else {
      setHighlightedLine(null);
    }
  }, [selectedComponent, localValue]);

  const handleEditorChange = useCallback((value: string | undefined) => {
    const v = value || '';
    setLocalValue(v);

    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => {
      onChange(v);
      prevCssRef.current = v;
    }, 400);
  }, [onChange]);

  const handleCopy = async () => {
    await navigator.clipboard.writeText(localValue);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleEditorDidMount = (editor: any) => {
    if (highlightedLine) {
      editor.revealLineInCenter(highlightedLine);
      editor.setPosition({ lineNumber: highlightedLine, column: 1 });
    }
  };

  return (
    <div className="editor-panel css-editor-panel">
      <PanelHeader
        title="CSS"
        icon={<FileCode size={16} />}
        onClose={onClose}
        actions={
          <>
            <button className="panel-header-btn" onClick={onCreateClass} title="Create new CSS class">
              <Plus size={14} />
            </button>
            <button className="panel-header-btn copy-btn" onClick={handleCopy} title="Copy CSS">
              {copied ? <Check size={14} /> : <Copy size={14} />}
            </button>
          </>
        }
      />
      {selectedComponent && (
        <div className="css-editor-context">
          <span className="css-context-badge">.{selectedComponent.className}</span>
        </div>
      )}
      <div className="editor-body">
        <Editor
          height="100%"
          defaultLanguage="css"
          value={localValue}
          theme="vs-dark"
          onChange={handleEditorChange}
          onMount={handleEditorDidMount}
          options={{
            readOnly: false,
            minimap: { enabled: false },
            fontSize: 13,
            lineNumbers: 'on',
            scrollBeyondLastLine: false,
            automaticLayout: true,
            tabSize: 2,
            wordWrap: 'on',
            formatOnPaste: true,
            formatOnType: true,
            suggest: {
              showProperties: true,
              showKeywords: true,
              showSnippets: true,
            },
            quickSuggestions: {
              other: true,
              comments: false,
              strings: true,
            },
          }}
        />
      </div>
    </div>
  );
}
