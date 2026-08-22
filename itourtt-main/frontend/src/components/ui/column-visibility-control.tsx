'use client';
import React, { useState, useEffect, useRef } from 'react';
import { SlidersHorizontal } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Checkbox } from '@/components/ui/checkbox';
import { Label } from '@/components/ui/label';
import type { ColumnDef } from '@/components/ui/draggable-table-header';

interface ColumnVisibilityControlProps {
  columns: ColumnDef[];
  visibility: Record<string, boolean>;
  onSave: (vis: Record<string, boolean>) => void;
}

export function ColumnVisibilityControl({
  columns,
  visibility,
  onSave,
}: ColumnVisibilityControlProps) {
  const [open, setOpen] = useState(false);
  const [local, setLocal] = useState<Record<string, boolean>>(visibility);
  const panelRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (open) setLocal(visibility);
  }, [open, visibility]);

  useEffect(() => {
    if (!open) return;
    function handleClick(e: MouseEvent) {
      if (panelRef.current && !panelRef.current.contains(e.target as Node)) {
        setOpen(false);
      }
    }
    document.addEventListener('mousedown', handleClick);
    return () => document.removeEventListener('mousedown', handleClick);
  }, [open]);

  function toggle(key: string) {
    setLocal((prev) => ({ ...prev, [key]: !prev[key] }));
  }

  function handleSave() {
    onSave(local);
    setOpen(false);
  }

  const displayLabel = (col: ColumnDef) =>
    col.title ?? (typeof col.label === 'string' ? col.label : col.key);

  return (
    <div className="relative inline-block" ref={panelRef}>
      <Button
        variant="outline"
        size="sm"
        className="gap-1.5 h-8 text-xs"
        onClick={() => setOpen((v) => !v)}
      >
        <SlidersHorizontal className="h-3.5 w-3.5" />
        Columns
      </Button>

      {open && (
        <div className="absolute right-0 top-full mt-1 z-50 bg-background border border-border rounded-md shadow-lg p-3 min-w-52">
          <p className="text-xs font-medium text-muted-foreground mb-2">Toggle columns</p>
          <div className="grid grid-cols-2 gap-x-6 gap-y-2 mb-3 max-h-72 overflow-y-auto pr-1">
            {columns.map((col) => (
              <div key={col.key} className="flex items-center gap-2">
                <Checkbox
                  id={`vis-${col.key}`}
                  checked={local[col.key] !== false}
                  onCheckedChange={() => toggle(col.key)}
                />
                <Label
                  htmlFor={`vis-${col.key}`}
                  className="text-xs cursor-pointer font-normal truncate"
                >
                  {displayLabel(col)}
                </Label>
              </div>
            ))}
          </div>
          <Button size="sm" className="w-full h-7 text-xs" onClick={handleSave}>
            Save
          </Button>
        </div>
      )}
    </div>
  );
}
