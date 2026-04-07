import { createContext, useContext, useState, useCallback, ReactNode } from 'react';
import { PanelConfig, PanelId, LayoutPreset, WorkspaceState, Breakpoint } from '../types';

const defaultPanels: PanelConfig[] = [
    { id: 'components', title: 'Components', visible: true, width: 220, minWidth: 180, collapsed: false },
    { id: 'layers', title: 'Layers', visible: false, width: 220, minWidth: 180, collapsed: false },
    { id: 'canvas', title: 'Canvas', visible: true, width: 0, minWidth: 400, collapsed: false }, // flex: 1
    { id: 'properties', title: 'Properties', visible: true, width: 280, minWidth: 220, collapsed: false },
    { id: 'html-editor', title: 'HTML', visible: false, width: 400, minWidth: 250, collapsed: false },
    { id: 'css-editor', title: 'CSS', visible: false, width: 400, minWidth: 250, collapsed: false },
];

const presetConfigs: Record<LayoutPreset, Partial<Record<PanelId, { visible: boolean; collapsed: boolean }>>> = {
    design: {
        'components': { visible: true, collapsed: false },
        'layers': { visible: false, collapsed: false },
        'canvas': { visible: true, collapsed: false },
        'properties': { visible: true, collapsed: false },
        'html-editor': { visible: false, collapsed: false },
        'css-editor': { visible: false, collapsed: false },
    },
    code: {
        'components': { visible: false, collapsed: false },
        'layers': { visible: false, collapsed: false },
        'canvas': { visible: true, collapsed: false },
        'properties': { visible: false, collapsed: false },
        'html-editor': { visible: true, collapsed: false },
        'css-editor': { visible: true, collapsed: false },
    },
    preview: {
        'components': { visible: false, collapsed: true },
        'layers': { visible: false, collapsed: true },
        'canvas': { visible: true, collapsed: false },
        'properties': { visible: false, collapsed: true },
        'html-editor': { visible: false, collapsed: true },
        'css-editor': { visible: false, collapsed: true },
    },
};

interface WorkspaceContextType {
    state: WorkspaceState;
    togglePanel: (id: PanelId) => void;
    collapsePanel: (id: PanelId) => void;
    setPanelWidth: (id: PanelId, width: number) => void;
    setPreset: (preset: LayoutPreset) => void;
    toggleFocusMode: () => void;
    isPanelVisible: (id: PanelId) => boolean;
    setActiveBreakpoint: (breakpoint: Breakpoint) => void;
}

const WorkspaceContext = createContext<WorkspaceContextType | null>(null);

export function useWorkspace() {
    const ctx = useContext(WorkspaceContext);
    if (!ctx) throw new Error('useWorkspace must be used inside WorkspaceProvider');
    return ctx;
}

interface WorkspaceProviderProps {
    children: ReactNode;
}

export default function WorkspaceProvider({ children }: WorkspaceProviderProps) {
    const [state, setState] = useState<WorkspaceState>({
        panels: defaultPanels,
        activePreset: 'design',
        focusMode: false,
        activeBreakpoint: 'desktop',
    });

    const togglePanel = useCallback((id: PanelId) => {
        setState(prev => ({
            ...prev,
            panels: prev.panels.map(p =>
                p.id === id ? { ...p, visible: !p.visible } : p
            ),
        }));
    }, []);

    const collapsePanel = useCallback((id: PanelId) => {
        setState(prev => ({
            ...prev,
            panels: prev.panels.map(p =>
                p.id === id ? { ...p, collapsed: !p.collapsed } : p
            ),
        }));
    }, []);

    const setPanelWidth = useCallback((id: PanelId, width: number) => {
        setState(prev => ({
            ...prev,
            panels: prev.panels.map(p =>
                p.id === id ? { ...p, width: Math.max(p.minWidth, width) } : p
            ),
        }));
    }, []);

    const setPreset = useCallback((preset: LayoutPreset) => {
        setState(prev => {
            const config = presetConfigs[preset];
            return {
                ...prev,
                activePreset: preset,
                focusMode: false,
                panels: prev.panels.map(p => {
                    const override = config[p.id];
                    return override ? { ...p, ...override } : p;
                }),
            };
        });
    }, []);

    const toggleFocusMode = useCallback(() => {
        setState(prev => ({
            ...prev,
            focusMode: !prev.focusMode,
        }));
    }, []);

    const setActiveBreakpoint = useCallback((breakpoint: Breakpoint) => {
        setState(prev => ({
            ...prev,
            activeBreakpoint: breakpoint,
        }));
    }, []);

    const isPanelVisible = useCallback((id: PanelId) => {
        if (state.focusMode) return id === 'canvas';
        const panel = state.panels.find(p => p.id === id);
        return panel ? panel.visible && !panel.collapsed : false;
    }, [state.focusMode, state.panels]);

    return (
        <WorkspaceContext.Provider value={{ state, togglePanel, collapsePanel, setPanelWidth, setPreset, toggleFocusMode, isPanelVisible, setActiveBreakpoint }}>
            {children}
        </WorkspaceContext.Provider>
    );
}
