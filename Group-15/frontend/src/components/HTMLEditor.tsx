import { useState, useRef, useCallback, useEffect } from 'react';
import { Editor } from '@monaco-editor/react';
import { Copy, Check, Code2 } from 'lucide-react';
import PanelHeader from './PanelHeader';

interface HTMLEditorProps {
    html: string;
    onChange: (html: string) => void;
    onClose?: () => void;
}

export default function HTMLEditor({ html, onChange, onClose }: HTMLEditorProps) {
    const [copied, setCopied] = useState(false);
    const [localValue, setLocalValue] = useState(html);
    const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);

    // Sync incoming HTML to local state (only when it changes externally)
    const prevHtmlRef = useRef(html);
    useEffect(() => {
        if (html !== prevHtmlRef.current) {
            setLocalValue(html);
            prevHtmlRef.current = html;
        }
    }, [html]);

    const handleEditorChange = useCallback((value: string | undefined) => {
        const v = value || '';
        setLocalValue(v);

        // Debounce sync back to parent
        if (debounceRef.current) clearTimeout(debounceRef.current);
        debounceRef.current = setTimeout(() => {
            onChange(v);
            prevHtmlRef.current = v;
        }, 400);
    }, [onChange]);

    const handleCopy = async () => {
        await navigator.clipboard.writeText(localValue);
        setCopied(true);
        setTimeout(() => setCopied(false), 2000);
    };

    return (
        <div className="editor-panel html-editor-panel">
            <PanelHeader
                title="HTML"
                icon={<Code2 size={16} />}
                onClose={onClose}
                actions={
                    <button className="panel-header-btn copy-btn" onClick={handleCopy} title="Copy HTML">
                        {copied ? <Check size={14} /> : <Copy size={14} />}
                    </button>
                }
            />
            <div className="editor-body">
                <Editor
                    height="100%"
                    defaultLanguage="html"
                    value={localValue}
                    theme="vs-dark"
                    onChange={handleEditorChange}
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
                    }}
                />
            </div>
        </div>
    );
}
