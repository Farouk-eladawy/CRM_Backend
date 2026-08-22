'use client';
import React, { useEffect, useState } from 'react';
import {
  DndContext,
  closestCenter,
  KeyboardSensor,
  PointerSensor,
  useSensor,
  useSensors,
  type DragEndEvent,
} from '@dnd-kit/core';
import {
  arrayMove,
  SortableContext,
  sortableKeyboardCoordinates,
  horizontalListSortingStrategy,
  useSortable,
} from '@dnd-kit/sortable';
import { CSS } from '@dnd-kit/utilities';
import { GripHorizontal } from 'lucide-react';
import { TableHead, TableHeader, TableRow } from '@/components/ui/table';

export interface ColumnDef {
  key: string;
  label: React.ReactNode;
  title?: string; // plain text label for the column visibility panel
  className?: string;
}

interface DraggableTableHeaderProps {
  columns: ColumnDef[];
  columnOrder: string[];
  onReorder: (newOrder: string[]) => void;
  rowClassName?: string;
  prefixCells?: React.ReactNode;
  visibility?: Record<string, boolean>;
}

function SortableTableHead({ col }: { col: ColumnDef }) {
  const {
    attributes,
    listeners,
    setNodeRef,
    transform,
    transition,
    isDragging,
  } = useSortable({ id: col.key });

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
    opacity: isDragging ? 0.5 : 1,
    cursor: 'grab',
  };

  return (
    <TableHead
      ref={setNodeRef}
      style={style}
      className={`select-none ${col.className ?? ''}`}
    >
      <div className="flex items-center gap-1 group">
        <GripHorizontal
          className="h-3 w-3 text-muted-foreground/40 group-hover:text-muted-foreground transition-colors shrink-0"
          {...attributes}
          {...listeners}
        />
        {col.label}
      </div>
    </TableHead>
  );
}

export function DraggableTableHeader({
  columns,
  columnOrder,
  onReorder,
  rowClassName,
  prefixCells,
  visibility,
}: DraggableTableHeaderProps) {
  const [mounted, setMounted] = useState(false);
  useEffect(() => { setMounted(true); }, []);

  const sensors = useSensors(
    useSensor(PointerSensor),
    useSensor(KeyboardSensor, {
      coordinateGetter: sortableKeyboardCoordinates,
    }),
  );

  const orderedColumns = columnOrder
    .map((key) => columns.find((c) => c.key === key))
    .filter(Boolean) as ColumnDef[];

  const visibleColumns = visibility
    ? orderedColumns.filter((col) => visibility[col.key] !== false)
    : orderedColumns;

  function handleDragEnd(event: DragEndEvent) {
    const { active, over } = event;
    if (over && active.id !== over.id) {
      const oldIndex = columnOrder.indexOf(active.id as string);
      const newIndex = columnOrder.indexOf(over.id as string);
      onReorder(arrayMove(columnOrder, oldIndex, newIndex));
    }
  }

  return (
    <DndContext
      sensors={sensors}
      collisionDetection={closestCenter}
      onDragEnd={handleDragEnd}
      accessibility={mounted ? { container: document.body } : undefined}
    >
      <TableHeader>
        <SortableContext
          items={columnOrder}
          strategy={horizontalListSortingStrategy}
        >
          <TableRow className={rowClassName}>
            {prefixCells}
            {visibleColumns.map((col) => (
              <SortableTableHead key={col.key} col={col} />
            ))}
          </TableRow>
        </SortableContext>
      </TableHeader>
    </DndContext>
  );
}
