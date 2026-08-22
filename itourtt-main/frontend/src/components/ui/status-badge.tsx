"use client";

import React from "react";

// ─── Status → color mapping ──────────────────────────────────────────────────
// Each entry: [bgClass, textClass, dotClass]
const STATUS_MAP: Record<string, [string, string, string]> = {
  PENDING:     ["bg-amber-500/30",   "text-amber-600 dark:text-amber-400",   "bg-amber-500"],
  ASSIGNED:    ["bg-blue-500/30",    "text-blue-600 dark:text-blue-400",     "bg-blue-500"],
  IN_PROGRESS: ["bg-purple-500/30",  "text-purple-600 dark:text-purple-400", "bg-purple-500"],
  IN_PLACE:    ["bg-teal-500/30",    "text-teal-600 dark:text-teal-400",     "bg-teal-500"],
  COMPLETED:   ["bg-emerald-500/30", "text-emerald-600 dark:text-emerald-400","bg-emerald-500"],
  CANCELLED:   ["bg-red-500/30",     "text-red-600 dark:text-red-400",       "bg-red-500"],
  NO_SHOW:     ["bg-orange-500/30",  "text-orange-600 dark:text-orange-400", "bg-orange-500"],
  DRAFT:       ["bg-zinc-500/30",    "text-zinc-600 dark:text-zinc-400",     "bg-zinc-500"],
  POSTED:      ["bg-sky-500/30",     "text-sky-600 dark:text-sky-400",       "bg-sky-500"],
  PAID:        ["bg-emerald-500/30", "text-emerald-600 dark:text-emerald-400","bg-emerald-500"],
  CONFIRMED:   ["bg-green-500/30",   "text-green-600 dark:text-green-400",   "bg-green-500"],
  CONVERTED:   ["bg-blue-500/30",    "text-blue-600 dark:text-blue-400",     "bg-blue-500"],
  COLLECTED:   ["bg-blue-500/30",    "text-blue-600 dark:text-blue-400",     "bg-blue-500"],
  LIQUIDATED:  ["bg-emerald-500/30", "text-emerald-600 dark:text-emerald-400","bg-emerald-500"],
  NEW:         ["bg-emerald-500/30", "text-emerald-600 dark:text-emerald-400","bg-emerald-500"],
  UPDATED:     ["bg-sky-500/30",     "text-sky-600 dark:text-sky-400",       "bg-sky-500"],
  REFUNDED:    ["bg-zinc-500/30",    "text-zinc-600 dark:text-zinc-400",     "bg-zinc-500"],
  FAILED:      ["bg-red-500/30",     "text-red-600 dark:text-red-400",       "bg-red-500"],
  ACTIVE:      ["bg-emerald-500/30", "text-emerald-600 dark:text-emerald-400","bg-emerald-500"],
  INACTIVE:    ["bg-zinc-500/30",    "text-zinc-600 dark:text-zinc-400",     "bg-zinc-500"],
};

const FALLBACK: [string, string, string] = [
  "bg-zinc-500/30",
  "text-zinc-600 dark:text-zinc-400",
  "bg-zinc-500",
];

interface StatusBadgeProps {
  status: string;
  /** Override the display label; defaults to status with underscores replaced by spaces */
  label?: string;
  className?: string;
}

export function StatusBadge({ status, label, className = "" }: StatusBadgeProps) {
  const [bg, text, dot] = STATUS_MAP[status] ?? FALLBACK;
  const displayLabel = label ?? status.replace(/_/g, " ");

  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full px-2 py-0.5 text-xs font-medium ${bg} ${text} ${className}`}
    >
      <span className={`h-1.5 w-1.5 shrink-0 rounded-full ${dot}`} aria-hidden="true" />
      {displayLabel}
    </span>
  );
}
