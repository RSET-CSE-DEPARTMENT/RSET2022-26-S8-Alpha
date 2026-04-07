import { Editor } from '@monaco-editor/react';
import { Copy, Check } from 'lucide-react';
import { useState } from 'react';

interface CodePanelProps {
  code: string;
  onChange: (code: string) => void;
}

export default function CodePanel({ code, onChange }: CodePanelProps) {
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    await navigator.clipboard.writeText(code);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="code-panel">
      <div className="code-header">
        <h3>Code</h3>
        <button className="copy-btn" onClick={handleCopy}>
          {copied ? <Check size={18} /> : <Copy size={18} />}
          {copied ? 'Copied!' : 'Copy'}
        </button>
      </div>
      <Editor
        height="calc(100% - 50px)"
        defaultLanguage="html"
        value={code}
        theme="vs-dark"
        onChange={(value) => onChange(value || '')}
        options={{
          readOnly: false,
          minimap: { enabled: false },
          fontSize: 13,
          lineNumbers: 'on',
          scrollBeyondLastLine: false,
          automaticLayout: true,
          tabSize: 2,
          wordWrap: 'on',
        }}
      />
    </div>
  );
}
