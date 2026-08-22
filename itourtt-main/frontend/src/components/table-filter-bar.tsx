"use client";

import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Search } from "lucide-react";

interface StatusOption {
  value: string;
  label: string;
}

interface TableFilterBarProps {
  search: string;
  onSearchChange: (value: string) => void;
  placeholder?: string;
  statusOptions?: StatusOption[];
  statusValue?: string;
  onStatusChange?: (value: string) => void;
  statusPlaceholder?: string;
}

export function TableFilterBar({
  search,
  onSearchChange,
  placeholder = "Search...",
  statusOptions,
  statusValue,
  onStatusChange,
  statusPlaceholder = "All",
}: TableFilterBarProps) {
  return (
    <div className="flex flex-wrap items-center gap-3">
      <div className="relative flex-1 min-w-[200px] max-w-sm">
        <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
        <Input
          value={search}
          onChange={(e) => onSearchChange(e.target.value)}
          placeholder={placeholder}
          className="pl-9"
        />
      </div>
      {statusOptions && onStatusChange && (
        <Select value={statusValue ?? "ALL"} onValueChange={onStatusChange}>
          <SelectTrigger className="w-44">
            <SelectValue placeholder={statusPlaceholder} />
          </SelectTrigger>
          <SelectContent>
            {statusOptions.map((opt) => (
              <SelectItem key={opt.value} value={opt.value}>
                {opt.label}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      )}
    </div>
  );
}
