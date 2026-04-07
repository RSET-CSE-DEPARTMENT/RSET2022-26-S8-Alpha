import { useEffect, useRef, ReactNode } from 'react';

export interface ContextMenuItem {
    label: string;
    icon?: ReactNode;
    shortcut?: string;
    onClick: () => void;
    disabled?: boolean;
    divider?: boolean;
}

interface ContextMenuProps {
    x: number;
    y: number;
    isOpen: boolean;
    items: ContextMenuItem[];
    onClose: () => void;
}

export default function ContextMenu({ x, y, isOpen, items, onClose }: ContextMenuProps) {
    const menuRef = useRef<HTMLDivElement>(null);

    useEffect(() => {
        if (!isOpen) return;

        const handleClickOutside = (e: MouseEvent) => {
            if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
                onClose();
            }
        };

        const handleEscape = (e: KeyboardEvent) => {
            if (e.key === 'Escape') onClose();
        };

        const handleScroll = () => onClose();

        document.addEventListener('mousedown', handleClickOutside);
        document.addEventListener('keydown', handleEscape);
        window.addEventListener('scroll', handleScroll, true);

        return () => {
            document.removeEventListener('mousedown', handleClickOutside);
            document.removeEventListener('keydown', handleEscape);
            window.removeEventListener('scroll', handleScroll, true);
        };
    }, [isOpen, onClose]);

    // Adjust position to keep menu on screen
    useEffect(() => {
        if (!isOpen || !menuRef.current) return;
        const rect = menuRef.current.getBoundingClientRect();
        const vw = window.innerWidth;
        const vh = window.innerHeight;

        if (rect.right > vw) {
            menuRef.current.style.left = `${x - rect.width}px`;
        }
        if (rect.bottom > vh) {
            menuRef.current.style.top = `${y - rect.height}px`;
        }
    }, [isOpen, x, y]);

    if (!isOpen) return null;

    return (
        <div
            ref={menuRef}
            className="context-menu"
            style={{ left: x, top: y }}
        >
            {items.map((item, index) => {
                if (item.divider) {
                    return <div key={index} className="context-menu-divider" />;
                }

                return (
                    <button
                        key={index}
                        className={`context-menu-item ${item.disabled ? 'disabled' : ''}`}
                        onClick={() => {
                            if (!item.disabled) {
                                item.onClick();
                                onClose();
                            }
                        }}
                        disabled={item.disabled}
                    >
                        <span className="context-menu-item-left">
                            {item.icon && <span className="context-menu-icon">{item.icon}</span>}
                            <span>{item.label}</span>
                        </span>
                        {item.shortcut && (
                            <span className="context-menu-shortcut">{item.shortcut}</span>
                        )}
                    </button>
                );
            })}
        </div>
    );
}
