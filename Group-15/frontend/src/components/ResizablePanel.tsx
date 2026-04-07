import { useState, useRef, useCallback, ReactNode, useEffect } from 'react';

interface ResizablePanelProps {
    children: ReactNode;
    defaultWidth: number;
    minWidth: number;
    maxWidth?: number;
    direction: 'left' | 'right';
    onResize?: (width: number) => void;
    className?: string;
    collapsed?: boolean;
}

export default function ResizablePanel({
    children,
    defaultWidth,
    minWidth,
    maxWidth = 800,
    direction,
    onResize,
    className = '',
    collapsed = false,
}: ResizablePanelProps) {
    const [width, setWidth] = useState(defaultWidth);
    const [isDragging, setIsDragging] = useState(false);
    const panelRef = useRef<HTMLDivElement>(null);
    const startXRef = useRef(0);
    const startWidthRef = useRef(0);

    const handleMouseDown = useCallback((e: React.MouseEvent) => {
        e.preventDefault();
        setIsDragging(true);
        startXRef.current = e.clientX;
        startWidthRef.current = width;
    }, [width]);

    useEffect(() => {
        if (!isDragging) return;

        const handleMouseMove = (e: MouseEvent) => {
            const delta = direction === 'right'
                ? e.clientX - startXRef.current
                : startXRef.current - e.clientX;

            const newWidth = Math.max(minWidth, Math.min(maxWidth, startWidthRef.current + delta));
            setWidth(newWidth);
            onResize?.(newWidth);
        };

        const handleMouseUp = () => {
            setIsDragging(false);
        };

        document.addEventListener('mousemove', handleMouseMove);
        document.addEventListener('mouseup', handleMouseUp);
        document.body.style.cursor = 'col-resize';
        document.body.style.userSelect = 'none';

        return () => {
            document.removeEventListener('mousemove', handleMouseMove);
            document.removeEventListener('mouseup', handleMouseUp);
            document.body.style.cursor = '';
            document.body.style.userSelect = '';
        };
    }, [isDragging, direction, minWidth, maxWidth, onResize]);

    if (collapsed) {
        return null;
    }

    return (
        <div
            ref={panelRef}
            className={`resizable-panel ${className} ${isDragging ? 'is-resizing' : ''}`}
            style={{ width: `${width}px`, minWidth: `${minWidth}px` }}
        >
            {children}
            <div
                className={`resize-handle-bar resize-${direction}`}
                onMouseDown={handleMouseDown}
            >
                <div className="resize-handle-indicator" />
            </div>
        </div>
    );
}
