"use client";

import { TableHead } from "@/components/ui/table";
import { ArrowUp, ArrowDown, ArrowUpDown } from "lucide-react";
import type { SortDir } from "@/hooks/use-sortable";

interface SortableHeaderProps {
  label: string;
  sortKey: string;
  currentKey: string | null;
  currentDir: SortDir;
  onSort: (key: string) => void;
  className?: string;
}

export function SortableHeader({
  label,
  sortKey,
  currentKey,
  currentDir,
  onSort,
  className = "",
}: SortableHeaderProps) {
  const active = currentKey === sortKey;

  return (
    <TableHead
      className={`text-white text-xs cursor-pointer select-none ${className}`}
      onClick={() => onSort(sortKey)}
    >
      <span className="inline-flex items-center gap-1">
        {label}
        {active && currentDir === "asc" ? (
          <ArrowUp className="h-3 w-3" />
        ) : active && currentDir === "desc" ? (
          <ArrowDown className="h-3 w-3" />
        ) : (
          <ArrowUpDown className="h-3 w-3 opacity-40" />
        )}
      </span>
    </TableHead>
  );
}
