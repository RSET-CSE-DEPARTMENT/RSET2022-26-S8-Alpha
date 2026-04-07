import { ReactNode } from 'react';
import { ChevronLeft, ChevronRight, X } from 'lucide-react';

interface PanelHeaderProps {
    title: string;
    collapsed?: boolean;
    onCollapse?: () => void;
    onClose?: () => void;
    actions?: ReactNode;
    icon?: ReactNode;
}

export default function PanelHeader({
    title,
    collapsed,
    onCollapse,
    onClose,
    actions,
    icon,
}: PanelHeaderProps) {
    return (
        <div className="panel-header">
            <div className="panel-header-left">
                {icon && <span className="panel-header-icon">{icon}</span>}
                <h3 className="panel-header-title">{title}</h3>
            </div>
            <div className="panel-header-actions">
                {actions}
                {onCollapse && (
                    <button
                        className="panel-header-btn"
                        onClick={onCollapse}
                        title={collapsed ? 'Expand' : 'Collapse'}
                    >
                        {collapsed ? <ChevronRight size={14} /> : <ChevronLeft size={14} />}
                    </button>
                )}
                {onClose && (
                    <button
                        className="panel-header-btn"
                        onClick={onClose}
                        title="Hide panel"
                    >
                        <X size={14} />
                    </button>
                )}
            </div>
        </div>
    );
}
