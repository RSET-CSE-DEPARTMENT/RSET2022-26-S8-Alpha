import { useState } from 'react';
import { Plus, X, FileText } from 'lucide-react';
import { Page } from '../types';

interface PageTabsProps {
    pages: Page[];
    activePageId: string;
    onSwitchPage: (pageId: string) => void;
    onAddPage: () => void;
    onDeletePage: (pageId: string) => void;
    onRenamePage: (pageId: string, name: string) => void;
}

export default function PageTabs({
    pages,
    activePageId,
    onSwitchPage,
    onAddPage,
    onDeletePage,
    onRenamePage,
}: PageTabsProps) {
    const [editingId, setEditingId] = useState<string | null>(null);
    const [editName, setEditName] = useState('');

    const startRename = (page: Page) => {
        setEditingId(page.id);
        setEditName(page.name);
    };

    const commitRename = () => {
        if (editingId && editName.trim()) {
            onRenamePage(editingId, editName.trim());
        }
        setEditingId(null);
    };

    const handleKeyDown = (e: React.KeyboardEvent) => {
        if (e.key === 'Enter') commitRename();
        if (e.key === 'Escape') setEditingId(null);
    };

    return (
        <div className="page-tabs">
            <div className="page-tabs-scroll">
                {pages.map(page => (
                    <div
                        key={page.id}
                        className={`page-tab ${page.id === activePageId ? 'active' : ''}`}
                        onClick={() => onSwitchPage(page.id)}
                        onDoubleClick={() => startRename(page)}
                    >
                        <FileText size={14} />
                        {editingId === page.id ? (
                            <input
                                className="page-tab-rename"
                                value={editName}
                                onChange={e => setEditName(e.target.value)}
                                onBlur={commitRename}
                                onKeyDown={handleKeyDown}
                                autoFocus
                                onClick={e => e.stopPropagation()}
                            />
                        ) : (
                            <span className="page-tab-name">{page.name}</span>
                        )}
                        {pages.length > 1 && (
                            <button
                                className="page-tab-close"
                                onClick={e => {
                                    e.stopPropagation();
                                    onDeletePage(page.id);
                                }}
                                title="Delete page"
                            >
                                <X size={12} />
                            </button>
                        )}
                    </div>
                ))}
            </div>
            <button className="page-tab-add" onClick={onAddPage} title="Add new page">
                <Plus size={16} />
            </button>
        </div>
    );
}
