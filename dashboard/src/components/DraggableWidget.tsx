'use client';

import React, { useState, useRef, useCallback } from 'react';
import { useDraggable, useDroppable } from '@dnd-kit/core';
import { CSS } from '@dnd-kit/utilities';
import { GripVertical, X, Settings } from 'lucide-react';
import { DashboardWidget } from './DashboardLayoutProvider';

interface DraggableWidgetProps {
  widget: DashboardWidget;
  children: React.ReactNode;
  isEditMode: boolean;
  onRemove?: (widgetId: string) => void;
  onConfigure?: (widgetId: string) => void;
  onResize?: (widgetId: string, newPosition: { x: number; y: number; w: number; h: number }) => void;
}

export function DraggableWidget({
  widget,
  children,
  isEditMode,
  onRemove,
  onConfigure,
  onResize
}: DraggableWidgetProps) {
  const [isResizing, setIsResizing] = useState(false);
  const resizeStartRef = useRef<{ x: number; y: number; w: number; h: number } | null>(null);
  const widgetRef = useRef<HTMLDivElement>(null);

  const {
    attributes,
    listeners,
    setNodeRef: setDraggableRef,
    transform,
    isDragging,
  } = useDraggable({
    id: widget.id,
    disabled: !isEditMode || isResizing,
  });

  const {
    setNodeRef: setDroppableRef,
    isOver,
  } = useDroppable({
    id: widget.id,
    disabled: !isEditMode || isResizing,
  });

  const style = {
    transform: CSS.Translate.toString(transform),
    opacity: isDragging ? 0.5 : 1,
  };

  // Combine refs for both draggable and droppable
  const setRefs = (element: HTMLElement | null) => {
    setDraggableRef(element);
    setDroppableRef(element);
  };

  // Resize handlers
  const handleResizeStart = useCallback((e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsResizing(true);
    resizeStartRef.current = {
      x: e.clientX,
      y: e.clientY,
      w: widget.position.w,
      h: widget.position.h,
    };
  }, [widget.position]);

  const handleResizeMove = useCallback((e: MouseEvent) => {
    if (!isResizing || !resizeStartRef.current || !onResize) return;

    const deltaX = e.clientX - resizeStartRef.current.x;
    const deltaY = e.clientY - resizeStartRef.current.y;

    // Calculate new dimensions (assuming 1 unit = 50px for grid)
    const gridSize = 50;
    const newW = Math.max(1, Math.min(12, resizeStartRef.current.w + Math.round(deltaX / gridSize)));
    const newH = Math.max(1, Math.min(6, resizeStartRef.current.h + Math.round(deltaY / gridSize)));

    if (newW !== widget.position.w || newH !== widget.position.h) {
      onResize(widget.id, {
        ...widget.position,
        w: newW,
        h: newH,
      });
    }
  }, [isResizing, onResize, widget.id, widget.position]);

  const handleResizeEnd = useCallback(() => {
    setIsResizing(false);
    resizeStartRef.current = null;
  }, []);

  // Add global mouse event listeners for resizing
  React.useEffect(() => {
    if (isResizing) {
      document.addEventListener('mousemove', handleResizeMove);
      document.addEventListener('mouseup', handleResizeEnd);
      return () => {
        document.removeEventListener('mousemove', handleResizeMove);
        document.removeEventListener('mouseup', handleResizeEnd);
      };
    }
  }, [isResizing, handleResizeMove, handleResizeEnd]);

  return (
    <div
      ref={setRefs}
      style={style}
      className={`relative enterprise-card enterprise-card-hover overflow-hidden transition-all duration-200 ${
        isEditMode ? 'hover:border-primary/50 cursor-move ring-1 ring-primary/10' : ''
      } ${isDragging ? 'z-50 shadow-2xl scale-105' : ''} ${
        isOver && isEditMode ? 'border-primary bg-primary/5 ring-2 ring-primary/20' : ''
      }`}
    >
      {/* Edit mode overlay */}
      {isEditMode && (
        <div className="absolute top-2 right-2 flex items-center gap-1 z-10">
          <button
            onClick={() => onConfigure?.(widget.id)}
            className="p-1 rounded-lg bg-surface-2 hover:bg-surface-3 transition-colors"
            title="Configure widget"
          >
            <Settings className="w-3 h-3 text-muted-foreground" />
          </button>
          <button
            onClick={() => onRemove?.(widget.id)}
            className="p-1 rounded-lg bg-red-500/20 hover:bg-red-500/30 transition-colors"
            title="Remove widget"
          >
            <X className="w-3 h-3 text-red-400" />
          </button>
        </div>
      )}

      {/* Drag handle */}
      {isEditMode && (
        <div
          {...listeners}
          {...attributes}
          className="absolute top-2 left-2 p-1 rounded-lg bg-surface-2 hover:bg-surface-3 cursor-move transition-colors z-10"
          title="Drag to move"
        >
          <GripVertical className="w-3 h-3 text-muted-foreground" />
        </div>
      )}

      {/* Resize handle */}
      {isEditMode && (
        <div
          onMouseDown={handleResizeStart}
          className="absolute bottom-2 right-2 w-3 h-3 cursor-se-resize z-10"
          title="Drag to resize"
        >
          <div className="w-full h-full bg-vanguard-400 rounded-sm opacity-60 hover:opacity-100 transition-opacity" />
        </div>
      )}

      {/* Widget content */}
      <div className={`${isEditMode ? 'pt-10' : ''}`}>
        {children}
      </div>
    </div>
  );
}