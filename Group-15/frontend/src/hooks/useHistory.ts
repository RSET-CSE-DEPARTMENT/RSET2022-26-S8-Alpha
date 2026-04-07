import { useState, useRef, useCallback } from 'react';

interface HistoryState<T> {
    past: T[];
    present: T;
    future: T[];
}

interface UseHistoryReturn<T> {
    state: T;
    setState: (newState: T | ((prev: T) => T)) => void;
    undo: () => void;
    redo: () => void;
    canUndo: boolean;
    canRedo: boolean;
    reset: (newState: T) => void;
}

export default function useHistory<T>(
    initialState: T,
    maxSize: number = 50
): UseHistoryReturn<T> {
    const [history, setHistory] = useState<HistoryState<T>>({
        past: [],
        present: initialState,
        future: [],
    });

    // Track whether we're in an undo/redo to avoid pushing to history
    const isUndoRedoRef = useRef(false);

    const setState = useCallback((newState: T | ((prev: T) => T)) => {
        setHistory(prev => {
            const resolved = typeof newState === 'function'
                ? (newState as (prev: T) => T)(prev.present)
                : newState;

            // Don't push to history if it's identical (shallow compare)
            if (resolved === prev.present) return prev;

            const newPast = [...prev.past, prev.present];
            // Trim history to maxSize
            if (newPast.length > maxSize) {
                newPast.shift();
            }

            return {
                past: newPast,
                present: resolved,
                future: [], // Clear future on new action
            };
        });
    }, [maxSize]);

    const undo = useCallback(() => {
        setHistory(prev => {
            if (prev.past.length === 0) return prev;

            const newPast = [...prev.past];
            const previous = newPast.pop()!;

            isUndoRedoRef.current = true;

            return {
                past: newPast,
                present: previous,
                future: [prev.present, ...prev.future],
            };
        });
    }, []);

    const redo = useCallback(() => {
        setHistory(prev => {
            if (prev.future.length === 0) return prev;

            const newFuture = [...prev.future];
            const next = newFuture.shift()!;

            isUndoRedoRef.current = true;

            return {
                past: [...prev.past, prev.present],
                present: next,
                future: newFuture,
            };
        });
    }, []);

    const reset = useCallback((newState: T) => {
        setHistory({
            past: [],
            present: newState,
            future: [],
        });
    }, []);

    return {
        state: history.present,
        setState,
        undo,
        redo,
        canUndo: history.past.length > 0,
        canRedo: history.future.length > 0,
        reset,
    };
}
