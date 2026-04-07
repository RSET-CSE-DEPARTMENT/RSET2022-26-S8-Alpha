import { useState } from 'react';
import { Layers, ChevronRight, ChevronDown, Eye, EyeOff, Lock, Unlock, Trash2, ArrowUp, ArrowDown } from 'lucide-react';
import { Component } from '../types';

interface LayersPanelProps {
    components: Component[];
    selectedId: string | null;
    onSelect: (id: string | null) => void;
    onUpdate: (components: Component[]) => void;
}

interface LayerItemProps {
    component: Component;
    level: number;
    selectedId: string | null;
    onSelect: (id: string | null) => void;
    onUpdateComponent: (id: string, updates: Partial<Component>) => void;
    onDeleteComponent: (id: string) => void;
    onMoveComponent: (id: string, direction: 'up' | 'down') => void;
}

function LayerItem({ component, level, selectedId, onSelect, onUpdateComponent, onDeleteComponent, onMoveComponent }: LayerItemProps) {
    const [expanded, setExpanded] = useState(true);
    const isSelected = selectedId === component.id;
    const hasChildren = component.children && component.children.length > 0;

    // Custom states for visibility and locking (stored in properties for now, or just local if not in Component type yet)
    // We'll store them in component.styles for simplicity without modifying the Component type further
    const isHidden = component.styles?.base?.display === 'none';
    const isLocked = component.styles?.base?.pointerEvents === 'none';

    const handleToggleVisibility = (e: React.MouseEvent) => {
        e.stopPropagation();
        onUpdateComponent(component.id, {
            styles: {
                ...component.styles,
                base: {
                    ...component.styles.base,
                    display: isHidden ? '' : 'none'
                }
            }
        });
    };

    const handleToggleLock = (e: React.MouseEvent) => {
        e.stopPropagation();
        onUpdateComponent(component.id, {
            styles: {
                ...component.styles,
                base: {
                    ...component.styles.base,
                    pointerEvents: isLocked ? '' : 'none'
                }
            }
        });
    };

    return (
        <div className="layer-item-wrapper">
            <div
                className={`layer-item ${isSelected ? 'selected' : ''} ${isHidden ? 'hidden-layer' : ''}`}
                style={{ paddingLeft: `${level * 12 + 8}px` }}
                onClick={() => onSelect(component.id)}
            >
                <div className="layer-item-main">
                    {hasChildren ? (
                        <button
                            className="layer-expand-btn"
                            onClick={(e) => {
                                e.stopPropagation();
                                setExpanded(!expanded);
                            }}
                        >
                            {expanded ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
                        </button>
                    ) : (
                        <span className="layer-expand-placeholder" />
                    )}

                    <span className="layer-type">{component.type}</span>
                    {component.className && <span className="layer-class">.{component.className}</span>}
                    {component.customId && <span className="layer-id">#{component.customId}</span>}

                    {/* Show content preview for text elements */}
                    {['text', 'heading', 'button', 'link'].includes(component.type) && component.content && (
                        <span className="layer-content-preview">"{component.content.substring(0, 15)}{component.content.length > 15 ? '...' : ''}"</span>
                    )}
                </div>

                <div className="layer-actions">
                    <button className="layer-action-btn" onClick={(e) => { e.stopPropagation(); onMoveComponent(component.id, 'up'); }} title="Move Up">
                        <ArrowUp size={12} />
                    </button>
                    <button className="layer-action-btn" onClick={(e) => { e.stopPropagation(); onMoveComponent(component.id, 'down'); }} title="Move Down">
                        <ArrowDown size={12} />
                    </button>
                    <button className="layer-action-btn" onClick={handleToggleLock} title={isLocked ? "Unlock" : "Lock"}>
                        {isLocked ? <Lock size={12} /> : <Unlock size={12} />}
                    </button>
                    <button className="layer-action-btn" onClick={handleToggleVisibility} title={isHidden ? "Show" : "Hide"}>
                        {isHidden ? <EyeOff size={12} /> : <Eye size={12} />}
                    </button>
                    <button className="layer-action-btn delete" onClick={(e) => { e.stopPropagation(); onDeleteComponent(component.id); }} title="Delete">
                        <Trash2 size={12} />
                    </button>
                </div>
            </div>

            {hasChildren && expanded && (
                <div className="layer-children">
                    {component.children!.map(child => (
                        <LayerItem
                            key={child.id}
                            component={child}
                            level={level + 1}
                            selectedId={selectedId}
                            onSelect={onSelect}
                            onUpdateComponent={onUpdateComponent}
                            onDeleteComponent={onDeleteComponent}
                            onMoveComponent={onMoveComponent}
                        />
                    ))}
                </div>
            )}
        </div>
    );
}

export default function LayersPanel({ components, selectedId, onSelect, onUpdate }: LayersPanelProps) {

    // Helper to update a component deeply in the tree
    const updateComponentDeep = (nodes: Component[], id: string, updates: Partial<Component>): Component[] => {
        return nodes.map(node => {
            if (node.id === id) {
                return { ...node, ...updates };
            }
            if (node.children) {
                return { ...node, children: updateComponentDeep(node.children, id, updates) };
            }
            return node;
        });
    };

    const deleteComponentDeep = (nodes: Component[], id: string): Component[] => {
        return nodes.filter(node => {
            if (node.id === id) return false;
            if (node.children) {
                node.children = deleteComponentDeep(node.children, id);
            }
            return true;
        });
    };

    const moveComponentDeep = (nodes: Component[], id: string, direction: 'up' | 'down'): Component[] => {
        const idx = nodes.findIndex(n => n.id === id);
        if (idx !== -1) {
            if (direction === 'up' && idx > 0) {
                const result = [...nodes];
                [result[idx], result[idx - 1]] = [result[idx - 1], result[idx]];
                return result;
            }
            if (direction === 'down' && idx < nodes.length - 1) {
                const result = [...nodes];
                [result[idx], result[idx + 1]] = [result[idx + 1], result[idx]];
                return result;
            }
            return nodes;
        }

        // Not found at this level, check children
        return nodes.map(node => {
            if (node.children) {
                return { ...node, children: moveComponentDeep(node.children, id, direction) };
            }
            return node;
        });
    };

    const handleUpdate = (id: string, updates: Partial<Component>) => {
        onUpdate(updateComponentDeep(components, id, updates));
    };

    const handleDelete = (id: string) => {
        if (selectedId === id) onSelect(null);
        onUpdate(deleteComponentDeep(components, id));
    };

    const handleMove = (id: string, direction: 'up' | 'down') => {
        onUpdate(moveComponentDeep(components, id, direction));
    };

    return (
        <div className="layers-panel">
            {components.length === 0 ? (
                <div className="layers-empty">
                    <Layers size={24} />
                    <p>No layers yet</p>
                    <span>Add components to the canvas to see them here.</span>
                </div>
            ) : (
                <div className="layers-tree">
                    {components.map(component => (
                        <LayerItem
                            key={component.id}
                            component={component}
                            level={0}
                            selectedId={selectedId}
                            onSelect={onSelect}
                            onUpdateComponent={handleUpdate}
                            onDeleteComponent={handleDelete}
                            onMoveComponent={handleMove}
                        />
                    ))}
                </div>
            )}
        </div>
    );
}
