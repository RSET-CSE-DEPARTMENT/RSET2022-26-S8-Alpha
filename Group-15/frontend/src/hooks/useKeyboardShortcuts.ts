import { useEffect, useCallback } from 'react';

interface ShortcutAction {
    key: string;
    ctrl?: boolean;
    shift?: boolean;
    action: () => void;
    description?: string;
}

function isEditableTarget(e: KeyboardEvent): boolean {
    const target = e.target as HTMLElement;
    const tagName = target.tagName.toLowerCase();

    // Ignore if typing in input, textarea, select, or contenteditable
    if (['input', 'textarea', 'select'].includes(tagName)) return true;
    if (target.isContentEditable) return true;

    // Ignore if inside Monaco editor
    if (target.closest('.monaco-editor')) return true;

    return false;
}

export default function useKeyboardShortcuts(shortcuts: ShortcutAction[]) {
    const handleKeyDown = useCallback((e: KeyboardEvent) => {
        // Skip if user is typing in an editable field
        if (isEditableTarget(e)) return;

        for (const shortcut of shortcuts) {
            const ctrlMatch = shortcut.ctrl ? (e.ctrlKey || e.metaKey) : !(e.ctrlKey || e.metaKey);
            const shiftMatch = shortcut.shift ? e.shiftKey : !e.shiftKey;
            const keyMatch = e.key.toLowerCase() === shortcut.key.toLowerCase();

            if (keyMatch && ctrlMatch && shiftMatch) {
                e.preventDefault();
                e.stopPropagation();
                shortcut.action();
                return;
            }
        }
    }, [shortcuts]);

    useEffect(() => {
        window.addEventListener('keydown', handleKeyDown);
        return () => window.removeEventListener('keydown', handleKeyDown);
    }, [handleKeyDown]);
}
