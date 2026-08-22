"use client";

import { useCallback, useEffect, useState } from "react";
import {
  Briefcase,
  TrendingUp,
  TrendingDown,
  AlertTriangle,
  CheckCircle2,
  UserCheck,
  EyeOff,
  XCircle,
  PlaneLanding,
  PlaneTakeoff,
  Bus,
  CalendarDays,
  Map,
  ArrowRightLeft,
  Repeat,
  X,
} from "lucide-react";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { useRouter } from "next/navigation";
import api from "@/lib/api";
import { useT } from "@/lib/i18n";
import { localDateStr, formatDate } from "@/lib/utils";
import { useServiceTypeLabel } from "@/lib/service-types";

interface JobSummary {
  id: string;
  internalRef: string;
  serviceType: string;
  status: string;
  paxCount: number;
  agent: { legalName: string } | null;
  customer: { legalName: string } | null;
  assignment: {
    vehicle: { plateNumber: string; vehicleType: { name: string } } | null;
    driver: { name: string } | null;
    rep: { name: string } | null;
  } | null;
}

interface DashboardStats {
  todayJobs: number;
  activeJobs: number;
  unassignedJobs: number;
  assignmentRate: number;
  completionRate: number;
  noShowJobs: number;
  cancelledJobs: number;
  byServiceType: Record<string, number>;
  byStatus: Record<string, number>;
  jobs: JobSummary[];
}

function StatCard({
  label,
  value,
  icon: Icon,
  trend,
  trendUp,
  trendColor,
  iconColor,
  iconBg,
}: {
  label: string;
  value: number | string;
  icon: React.ElementType;
  trend?: string;
  /** true = green TrendingUp, false = red TrendingDown, undefined = no trend row */
  trendUp?: boolean;
  trendColor?: string;
  iconColor: string;
  iconBg: string;
}) {
  const TrendIcon = trendUp === false ? TrendingDown : TrendingUp;
  const defaultTrendColor =
    trendUp === false
      ? "text-red-500 dark:text-red-400"
      : "text-emerald-600 dark:text-emerald-400";

  return (
    <Card className="border-border bg-card p-5">
      <div className="flex items-start justify-between">
        <div>
          <p className={`text-sm font-medium ${iconColor}`}>{label}</p>
          <p className="mt-1 text-2xl font-semibold text-foreground">{value}</p>
          {trend && (
            <p className={`mt-1 flex items-center text-xs ${trendColor || defaultTrendColor}`}>
              <TrendIcon className="mr-1 h-3 w-3" />
              {trend}
            </p>
          )}
        </div>
        <div className={`flex h-10 w-10 items-center justify-center rounded-lg ${iconBg}`}>
          <Icon className={`h-5 w-5 ${iconColor}`} />
        </div>
      </div>
    </Card>
  );
}

const STATUS_BADGE: Record<string, string> = {
  PENDING: "bg-amber-100 text-amber-800 dark:bg-amber-900/30 dark:text-amber-300",
  ASSIGNED: "bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-300",
  IN_PROGRESS: "bg-indigo-100 text-indigo-800 dark:bg-indigo-900/30 dark:text-indigo-300",
  COMPLETED: "bg-emerald-100 text-emerald-800 dark:bg-emerald-900/30 dark:text-emerald-300",
  NO_SHOW: "bg-orange-100 text-orange-800 dark:bg-orange-900/30 dark:text-orange-300",
  CANCELLED: "bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-300",
};

export default function DashboardPage() {
  const t = useT();
  const router = useRouter();
  const [selectedDate, setSelectedDate] = useState(() => localDateStr(new Date()));
  const [stats, setStats] = useState<DashboardStats>({
    todayJobs: 0,
    activeJobs: 0,
    unassignedJobs: 0,
    assignmentRate: 0,
    completionRate: 0,
    noShowJobs: 0,
    cancelledJobs: 0,
    byServiceType: {},
    byStatus: {},
    jobs: [],
  });
  const [loading, setLoading] = useState(true);
  const [modalFilter, setModalFilter] = useState<{ type: "status" | "serviceType"; key: string; label: string } | null>(null);

  const fetchStats = useCallback(async (date: string) => {
    setLoading(true);
    try {
      const res = await api.get(`/reports/daily-dispatch?date=${date}`);
      const report = res.data?.data ?? res.data;

      const byStatus = report.byStatus || {};
      const byServiceType = report.byServiceType || {};
      setStats({
        todayJobs: report.totalJobs || 0,
        activeJobs: report.activeJobs || 0,
        unassignedJobs: report.unassignedCount || 0,
        assignmentRate: report.assignmentRate || 0,
        completionRate: report.completionRate || 0,
        noShowJobs: byStatus.NO_SHOW || 0,
        cancelledJobs: byStatus.CANCELLED || 0,
        byServiceType,
        byStatus,
        jobs: report.jobs || [],
      });
    } catch {
      // silently fail – dashboard still renders with zeros
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchStats(selectedDate);
  }, [selectedDate, fetchStats]);

  const serviceTypeLabel = useServiceTypeLabel();

  // Labels come from the shared service-type source, not a second copy.
  const serviceTypeRows = [
    { key: "ARR", label: serviceTypeLabel("ARR"), icon: PlaneLanding, color: "text-blue-500", bg: "bg-blue-500/10" },
    { key: "DEP", label: serviceTypeLabel("DEP"), icon: PlaneTakeoff, color: "text-violet-500", bg: "bg-violet-500/10" },
    { key: "DAY_TOUR", label: serviceTypeLabel("DAY_TOUR"), icon: Map, color: "text-amber-500", bg: "bg-amber-500/10" },
    { key: "ONE_WAY_TRANSFER", label: serviceTypeLabel("ONE_WAY_TRANSFER"), icon: ArrowRightLeft, color: "text-emerald-500", bg: "bg-emerald-500/10" },
    { key: "RETURN", label: serviceTypeLabel("RETURN"), icon: Repeat, color: "text-cyan-500", bg: "bg-cyan-500/10" },
  ];

  const statusRows = [
    { key: "PENDING", label: t("dashHome.statusPending"), color: "text-amber-500", bg: "bg-amber-500" },
    { key: "ASSIGNED", label: t("dashHome.statusAssigned"), color: "text-blue-500", bg: "bg-blue-500" },
    { key: "IN_PROGRESS", label: t("dashHome.statusInProgress"), color: "text-indigo-500", bg: "bg-indigo-500" },
    { key: "COMPLETED", label: t("dashHome.statusCompleted"), color: "text-emerald-500", bg: "bg-emerald-500" },
    { key: "NO_SHOW", label: t("dashHome.noShow"), color: "text-orange-500", bg: "bg-orange-500" },
    { key: "CANCELLED", label: t("dashHome.cancelled"), color: "text-red-500", bg: "bg-red-500" },
  ];

  const modalJobs = modalFilter
    ? stats.jobs.filter((j) =>
        modalFilter.type === "status"
          ? j.status === modalFilter.key
          : j.serviceType === modalFilter.key
      )
    : [];

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-foreground">{t("dashHome.title")}</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            {t("dashHome.overview")}
          </p>
        </div>
        <div className="flex items-center gap-2">
          <CalendarDays className="h-4 w-4 text-muted-foreground" />
          <input
            type="date"
            value={selectedDate}
            onChange={(e) => setSelectedDate(e.target.value)}
            className="h-9 rounded-md border border-border bg-card px-3 text-sm text-foreground outline-none focus:ring-2 focus:ring-ring"
          />
        </div>
      </div>

      {loading ? (
        <div className="space-y-4">
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {[...Array(3)].map((_, i) => (
              <Card key={i} className="h-28 animate-pulse border-border bg-card" />
            ))}
          </div>
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {[...Array(3)].map((_, i) => (
              <Card key={i} className="h-28 animate-pulse border-border bg-card" />
            ))}
          </div>
        </div>
      ) : (
        <div className="space-y-4">
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
            <StatCard
              label={t("dashHome.todayJobs")}
              value={stats.todayJobs}
              icon={Briefcase}
              iconColor="text-blue-500"
              iconBg="bg-blue-500/10"
              trend="+12% vs yesterday"
              trendUp={true}
            />
            <StatCard
              label={t("dashHome.unassignedJobs")}
              value={stats.unassignedJobs}
              icon={AlertTriangle}
              iconColor="text-amber-500"
              iconBg="bg-amber-500/10"
              trend={stats.unassignedJobs > 0 ? t("dashHome.needsAttention") : "+0% vs yesterday"}
              trendColor={stats.unassignedJobs > 0 ? "text-amber-600 dark:text-amber-400" : undefined}
              trendUp={stats.unassignedJobs === 0 ? true : undefined}
            />
            <StatCard
              label={t("dashHome.assignmentRate")}
              value={`${stats.assignmentRate}%`}
              icon={UserCheck}
              iconColor="text-indigo-500"
              iconBg="bg-indigo-500/10"
              trend="+5% vs yesterday"
              trendUp={true}
            />
          </div>
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
            <StatCard
              label={t("dashHome.completionRate")}
              value={`${stats.completionRate}%`}
              icon={CheckCircle2}
              iconColor="text-emerald-500"
              iconBg="bg-emerald-500/10"
              trend="+8% vs yesterday"
              trendUp={true}
            />
            <StatCard
              label={t("dashHome.noShow")}
              value={stats.noShowJobs}
              icon={EyeOff}
              iconColor="text-orange-500"
              iconBg="bg-orange-500/10"
              trend="-4% vs yesterday"
              trendUp={false}
            />
            <StatCard
              label={t("dashHome.cancelled")}
              value={stats.cancelledJobs}
              icon={XCircle}
              iconColor="text-red-500"
              iconBg="bg-red-500/10"
              trend="-2% vs yesterday"
              trendUp={false}
            />
          </div>
        </div>
      )}

      {/* Interactive Stats */}
      {!loading && (
        <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
          {/* Jobs by Service Type */}
          <Card className="border-border bg-card p-5">
            <h3 className="mb-4 text-sm font-medium text-muted-foreground">
              {t("dashHome.byServiceType")}
            </h3>
            <div className="space-y-3">
              {serviceTypeRows.map(({ key, label, icon: SIcon, color, bg }) => {
                const count = stats.byServiceType[key] || 0;
                const pct = stats.todayJobs > 0 ? Math.round((count / stats.todayJobs) * 100) : 0;
                return (
                  <button
                    key={key}
                    onClick={() => setModalFilter({ type: "serviceType", key, label })}
                    className="flex w-full items-center gap-3 rounded-lg p-2 text-left transition-colors hover:bg-accent"
                  >
                    <div className={`flex h-9 w-9 shrink-0 items-center justify-center rounded-lg ${bg}`}>
                      <SIcon className={`h-4 w-4 ${color}`} />
                    </div>
                    <div className="min-w-0 flex-1">
                      <div className="flex items-center justify-between">
                        <span className="text-sm font-medium text-foreground">{label}</span>
                        <span className="text-sm font-semibold text-foreground">{count}</span>
                      </div>
                      <div className="mt-1 h-3 w-full overflow-hidden rounded-full bg-muted">
                        <div
                          className={`h-full rounded-full transition-all ${color.replace("text-", "bg-")}`}
                          style={{ width: `${pct}%` }}
                        />
                      </div>
                    </div>
                    <span className="shrink-0 text-xs text-muted-foreground">{pct}%</span>
                  </button>
                );
              })}
            </div>
          </Card>

          {/* Jobs by Status */}
          <Card className="border-border bg-card p-5">
            <h3 className="mb-4 text-sm font-medium text-muted-foreground">
              {t("dashHome.byStatus")}
            </h3>
            <div className="space-y-3">
              {statusRows.map(({ key, label, color, bg }) => {
                const count = stats.byStatus[key] || 0;
                // percentage over active jobs for COMPLETED/IN_PROGRESS/ASSIGNED/PENDING/NO_SHOW;
                // CANCELLED is shown as % of total
                const base = key === "CANCELLED" ? stats.todayJobs : (stats.activeJobs || stats.todayJobs);
                const pct = base > 0 ? Math.round((count / base) * 100) : 0;
                return (
                  <button
                    key={key}
                    onClick={() => setModalFilter({ type: "status", key, label })}
                    className="flex w-full items-center gap-3 rounded-lg p-2 text-left transition-colors hover:bg-accent"
                  >
                    <div className={`h-2.5 w-2.5 shrink-0 rounded-full ${bg}`} />
                    <div className="min-w-0 flex-1">
                      <div className="flex items-center justify-between">
                        <span className="text-sm font-medium text-foreground">{label}</span>
                        <span className="text-sm font-semibold text-foreground">{count}</span>
                      </div>
                      <div className="mt-1 h-3 w-full overflow-hidden rounded-full bg-muted">
                        <div
                          className={`h-full rounded-full transition-all ${bg}`}
                          style={{ width: `${pct}%` }}
                        />
                      </div>
                    </div>
                    <span className="shrink-0 text-xs text-muted-foreground">{pct}%</span>
                  </button>
                );
              })}
            </div>
          </Card>
        </div>
      )}

      {/* Jobs drill-down modal */}
      <Dialog open={!!modalFilter} onOpenChange={(open) => { if (!open) setModalFilter(null); }}>
        <DialogContent className="!w-[95vw] !max-w-[95vw] sm:!max-w-[95vw] max-h-[85vh] flex flex-col gap-0 p-0 border-2 border-white [&>button]:text-red-500 [&>button]:hover:text-red-600 [&>button]:opacity-100">
          <DialogHeader className="px-6 pt-6 pb-4 border-b border-border">
            <DialogTitle className="flex items-center gap-2">
              {modalFilter?.label} — {formatDate(selectedDate)}
              <span className="ml-auto text-sm font-normal text-muted-foreground">
                {modalJobs.length} job{modalJobs.length !== 1 ? "s" : ""}
              </span>
            </DialogTitle>
          </DialogHeader>
          <div className="overflow-auto flex-1 px-6 py-4">
            {modalJobs.length === 0 ? (
              <p className="py-8 text-center text-sm text-muted-foreground">No jobs for this selection.</p>
            ) : (
              <Table>
                <TableHeader>
                  <TableRow className="border-border">
                    <TableHead>Ref</TableHead>
                    <TableHead>Type</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead>Pax</TableHead>
                    <TableHead>Agent</TableHead>
                    <TableHead>Vehicle</TableHead>
                    <TableHead>Driver</TableHead>
                    <TableHead>Rep</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {modalJobs.map((j) => (
                    <TableRow
                      key={j.id}
                      className="border-border cursor-pointer hover:bg-accent"
                      onClick={() => {
                        setModalFilter(null);
                        router.push(`/dashboard/traffic-jobs?search=${j.internalRef}`);
                      }}
                    >
                      <TableCell className="font-mono text-xs font-medium">{j.internalRef}</TableCell>
                      <TableCell className="text-xs">{j.serviceType}</TableCell>
                      <TableCell>
                        <span className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ${STATUS_BADGE[j.status] || ""}`}>
                          {j.status}
                        </span>
                      </TableCell>
                      <TableCell className="text-xs">{j.paxCount}</TableCell>
                      <TableCell className="text-xs">{j.agent?.legalName ?? j.customer?.legalName ?? "—"}</TableCell>
                      <TableCell className="text-xs">{j.assignment?.vehicle?.plateNumber ?? "—"}</TableCell>
                      <TableCell className="text-xs">{j.assignment?.driver?.name ?? "—"}</TableCell>
                      <TableCell className="text-xs">{j.assignment?.rep?.name ?? "—"}</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            )}
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}
