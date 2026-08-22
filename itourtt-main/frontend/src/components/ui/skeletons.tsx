import { Skeleton } from "@/components/ui/skeleton";
import { cn } from "@/lib/utils";

// ── Page header with title + optional action button ──────────────────────────
export function PageHeaderSkeleton({ hasButton = true }: { hasButton?: boolean }) {
  return (
    <div className="flex items-center justify-between">
      <div className="space-y-2">
        <Skeleton className="h-7 w-48" />
        <Skeleton className="h-4 w-72" />
      </div>
      {hasButton && <Skeleton className="h-9 w-32 rounded-md" />}
    </div>
  );
}

// ── Stat / KPI card ───────────────────────────────────────────────────────────
export function StatCardSkeleton() {
  return (
    <div className="rounded-xl border bg-card p-5 space-y-3">
      <div className="flex items-center justify-between">
        <Skeleton className="h-4 w-28" />
        <Skeleton className="h-8 w-8 rounded-full" />
      </div>
      <Skeleton className="h-8 w-20" />
      <Skeleton className="h-3 w-36" />
    </div>
  );
}

// ── Row of stat cards ─────────────────────────────────────────────────────────
export function StatCardRowSkeleton({ count = 4 }: { count?: number }) {
  const colsClass: Record<number, string> = {
    2: "grid-cols-2",
    3: "grid-cols-3",
    4: "grid-cols-4",
    5: "grid-cols-5",
    6: "grid-cols-6",
  };
  return (
    <div className={cn("grid gap-4", colsClass[count] ?? "grid-cols-4")}>
      {Array.from({ length: count }).map((_, i) => (
        <StatCardSkeleton key={i} />
      ))}
    </div>
  );
}

// ── Filter / toolbar row ──────────────────────────────────────────────────────
export function FilterBarSkeleton({ items = 3 }: { items?: number }) {
  return (
    <div className="flex items-center gap-3 flex-wrap">
      {Array.from({ length: items }).map((_, i) => (
        <Skeleton key={i} className={cn("h-9 rounded-md", i === 0 ? "w-40" : "w-32")} />
      ))}
      <Skeleton className="h-9 w-24 rounded-md ml-auto" />
    </div>
  );
}

// ── Data table ────────────────────────────────────────────────────────────────
export function TableSkeleton({
  rows = 8,
  columns = 5,
  className,
}: {
  rows?: number;
  columns?: number;
  className?: string;
}) {
  return (
    <div className={cn("rounded-xl border bg-card overflow-hidden", className)}>
      {/* header row */}
      <div className="border-b bg-muted/40 px-4 py-3 flex gap-4">
        {Array.from({ length: columns }).map((_, i) => (
          <Skeleton key={i} className={cn("h-4", i === 0 ? "w-40" : "flex-1")} />
        ))}
      </div>
      {/* data rows */}
      {Array.from({ length: rows }).map((_, r) => (
        <div key={r} className="flex gap-4 border-b last:border-b-0 px-4 py-3.5 items-center">
          {Array.from({ length: columns }).map((_, c) => (
            <Skeleton
              key={c}
              className={cn("h-4", c === 0 ? "w-40" : "flex-1")}
            />
          ))}
        </div>
      ))}
    </div>
  );
}

// ── Card grid (entity list pages) ─────────────────────────────────────────────
export function CardGridSkeleton({ count = 6, cols = 3 }: { count?: number; cols?: number }) {
  const colsClass: Record<number, string> = {
    2: "grid-cols-2",
    3: "grid-cols-3",
    4: "grid-cols-4",
    5: "grid-cols-5",
    6: "grid-cols-6",
  };
  return (
    <div className={cn("grid gap-4", colsClass[cols] ?? "grid-cols-3")}>
      {Array.from({ length: count }).map((_, i) => (
        <CardSkeleton key={i} />
      ))}
    </div>
  );
}

// ── Single card ───────────────────────────────────────────────────────────────
export function CardSkeleton() {
  return (
    <div className="rounded-xl border bg-card p-5 space-y-4">
      <div className="flex items-center gap-3">
        <Skeleton className="h-10 w-10 rounded-full shrink-0" />
        <div className="flex-1 space-y-2">
          <Skeleton className="h-4 w-32" />
          <Skeleton className="h-3 w-24" />
        </div>
      </div>
      <div className="space-y-2">
        <Skeleton className="h-3 w-full" />
        <Skeleton className="h-3 w-4/5" />
      </div>
      <div className="flex gap-2 pt-1">
        <Skeleton className="h-6 w-16 rounded-full" />
        <Skeleton className="h-6 w-20 rounded-full" />
      </div>
    </div>
  );
}

// ── Detail / form page ────────────────────────────────────────────────────────
export function FormSkeleton({ fields = 8 }: { fields?: number }) {
  return (
    <div className="space-y-5">
      {Array.from({ length: fields }).map((_, i) => (
        <div key={i} className="space-y-1.5">
          <Skeleton className="h-4 w-24" />
          <Skeleton className="h-9 w-full rounded-md" />
        </div>
      ))}
      <div className="flex justify-end gap-2 pt-2">
        <Skeleton className="h-9 w-20 rounded-md" />
        <Skeleton className="h-9 w-24 rounded-md" />
      </div>
    </div>
  );
}

// ── Detail view (entity detail page) ─────────────────────────────────────────
export function DetailSkeleton() {
  return (
    <div className="space-y-6">
      {/* Profile header */}
      <div className="rounded-xl border bg-card p-6 flex items-start gap-4">
        <Skeleton className="h-16 w-16 rounded-full shrink-0" />
        <div className="flex-1 space-y-2">
          <Skeleton className="h-6 w-48" />
          <Skeleton className="h-4 w-64" />
          <div className="flex gap-2 mt-2">
            <Skeleton className="h-6 w-20 rounded-full" />
            <Skeleton className="h-6 w-24 rounded-full" />
          </div>
        </div>
        <div className="flex gap-2">
          <Skeleton className="h-9 w-20 rounded-md" />
          <Skeleton className="h-9 w-9 rounded-md" />
        </div>
      </div>
      {/* Info cards */}
      <div className="grid grid-cols-2 gap-4">
        {Array.from({ length: 4 }).map((_, i) => (
          <div key={i} className="rounded-xl border bg-card p-4 space-y-3">
            <Skeleton className="h-4 w-32" />
            <div className="space-y-2">
              {Array.from({ length: 3 }).map((_, j) => (
                <div key={j} className="flex justify-between">
                  <Skeleton className="h-3.5 w-24" />
                  <Skeleton className="h-3.5 w-32" />
                </div>
              ))}
            </div>
          </div>
        ))}
      </div>
      {/* Table */}
      <TableSkeleton rows={5} columns={4} />
    </div>
  );
}

// ── Dashboard overview page ───────────────────────────────────────────────────
export function DashboardSkeleton() {
  return (
    <div className="space-y-6">
      <PageHeaderSkeleton hasButton={false} />
      <div className="grid grid-cols-4 gap-4">
        {Array.from({ length: 4 }).map((_, i) => <StatCardSkeleton key={i} />)}
      </div>
      <div className="grid grid-cols-3 gap-4">
        <div className="col-span-2 rounded-xl border bg-card p-5 space-y-3">
          <Skeleton className="h-5 w-36" />
          <Skeleton className="h-48 w-full rounded-lg" />
        </div>
        <div className="rounded-xl border bg-card p-5 space-y-3">
          <Skeleton className="h-5 w-28" />
          {Array.from({ length: 5 }).map((_, i) => (
            <div key={i} className="flex items-center gap-3 py-1">
              <Skeleton className="h-8 w-8 rounded-full shrink-0" />
              <div className="flex-1 space-y-1">
                <Skeleton className="h-3.5 w-full" />
                <Skeleton className="h-3 w-3/4" />
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

// ── List page (header + filters + table) ─────────────────────────────────────
export function ListPageSkeleton({
  filterCount = 3,
  rows = 8,
  columns = 5,
}: {
  filterCount?: number;
  rows?: number;
  columns?: number;
}) {
  return (
    <div className="space-y-5">
      <PageHeaderSkeleton />
      <FilterBarSkeleton items={filterCount} />
      <TableSkeleton rows={rows} columns={columns} />
    </div>
  );
}

// ── Reports page skeleton ─────────────────────────────────────────────────────
export function ReportsSkeleton() {
  return (
    <div className="space-y-5">
      <PageHeaderSkeleton hasButton={false} />
      {/* Tab bar */}
      <div className="flex gap-2">
        {Array.from({ length: 5 }).map((_, i) => (
          <Skeleton key={i} className="h-9 w-28 rounded-md" />
        ))}
      </div>
      <FilterBarSkeleton items={4} />
      <TableSkeleton rows={10} columns={6} />
    </div>
  );
}

// ── Finance page skeleton ─────────────────────────────────────────────────────
export function FinanceSkeleton() {
  return (
    <div className="space-y-5">
      <PageHeaderSkeleton hasButton={false} />
      <div className="grid grid-cols-3 gap-4">
        {Array.from({ length: 3 }).map((_, i) => <StatCardSkeleton key={i} />)}
      </div>
      {/* Tab bar */}
      <div className="flex gap-2">
        {Array.from({ length: 4 }).map((_, i) => (
          <Skeleton key={i} className="h-9 w-28 rounded-md" />
        ))}
      </div>
      <TableSkeleton rows={8} columns={6} />
    </div>
  );
}

// ── Dispatch page skeleton (grid-heavy) ───────────────────────────────────────
export function DispatchSkeleton() {
  return (
    <div className="space-y-4 h-full">
      <div className="flex items-center gap-3">
        <Skeleton className="h-9 w-9 rounded-md" />
        <Skeleton className="h-7 w-36" />
        <Skeleton className="h-9 w-9 rounded-md" />
        <Skeleton className="h-9 w-28 rounded-md ml-auto" />
        <Skeleton className="h-9 w-28 rounded-md" />
      </div>
      <div className="grid grid-cols-2 gap-4 flex-1">
        {["ARR", "DEP"].map((side) => (
          <div key={side} className="rounded-xl border bg-card overflow-hidden">
            <div className="border-b bg-muted/40 px-4 py-3">
              <Skeleton className="h-5 w-20" />
            </div>
            {Array.from({ length: 6 }).map((_, r) => (
              <div key={r} className="flex gap-3 border-b last:border-b-0 px-4 py-3">
                <Skeleton className="h-4 w-24" />
                <Skeleton className="h-4 flex-1" />
                <Skeleton className="h-4 w-20" />
                <Skeleton className="h-4 w-16" />
              </div>
            ))}
          </div>
        ))}
      </div>
    </div>
  );
}
