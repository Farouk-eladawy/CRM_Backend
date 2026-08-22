"use client";

import { useState, useCallback } from "react";
import { toast } from "sonner";
import { Lock, LockOpen, Loader2, Search, ChevronLeft, ChevronRight } from "lucide-react";
import { PageHeader } from "@/components/page-header";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import api from "@/lib/api";
import { useT } from "@/lib/i18n";
import { usePermission } from "@/hooks/use-permission";
import { localDateStr } from "@/lib/utils";
import { useColumnPreferences } from "@/hooks/useColumnPreferences";
import { ColumnVisibilityControl } from "@/components/ui/column-visibility-control";
import { type ColumnDef } from "@/components/ui/draggable-table-header";

const JOB_LOCKS_COL_DEFS: ColumnDef[] = [
  { key: "lock", label: "Lock" },
  { key: "ref", label: "Ref" },
  { key: "entity", label: "Entity" },
  { key: "route", label: "Route" },
  { key: "date", label: "Date" },
  { key: "status", label: "Status" },
  { key: "provider", label: "Provider" },
];

const PAGE_SIZE = 50;

type LockTab = "dispatcher" | "driver" | "rep" | "supplier" | "edit" | "b2c" | "online";

interface JobLockItem {
  id: string;
  internalRef: string;
  jobDate: string;
  serviceType: string;
  status: string;
  clientName: string | null;
  isUnlocked: boolean;
  agent?: { legalName: string } | null;
  customer?: { legalName: string } | null;
  fromZone?: { name: string } | null;
  toZone?: { name: string } | null;
  assignment?: {
    driver?: { id: string; name: string } | null;
    rep?: { id: string; name: string } | null;
    vehicle?: {
      id: string;
      plateNumber: string;
      supplier?: { id: string; legalName: string } | null;
    } | null;
  } | null;
}

interface PagedResult {
  data: JobLockItem[];
  total: number;
  page: number;
  limit: number;
}

function getDefaultDateRange() {
  const to = new Date();
  const from = new Date();
  from.setDate(from.getDate() - 7);
  return {
    dateFrom: localDateStr(from),
    dateTo: localDateStr(to),
  };
}

function getEntityName(job: JobLockItem, tab: LockTab): string {
  if (!job.assignment) return "-";
  switch (tab) {
    case "dispatcher":
      return job.agent?.legalName || job.customer?.legalName || "-";
    case "driver":
      return job.assignment.driver?.name || "-";
    case "rep":
      return job.assignment.rep?.name || "-";
    case "supplier":
      return job.assignment.vehicle?.supplier?.legalName || "-";
    case "edit":
      return job.agent?.legalName || job.customer?.legalName || "-";
    case "b2c":
    case "online":
      return job.clientName || "-";
    default:
      return "-";
  }
}

export default function JobLocksPage() {
  const t = useT();
  const canLockDispatcher = usePermission("job-locks.dispatcher");
  const canLockDriver = usePermission("job-locks.driver");
  const canLockRep = usePermission("job-locks.rep");
  const canLockSupplier = usePermission("job-locks.supplier");
  const canLockEdit = usePermission("job-locks.edit");
  const canLockB2C = usePermission("job-locks.b2c");
  const canLockOnline = usePermission("job-locks.online");
  const lockPermissions: Record<LockTab, boolean> = {
    dispatcher: canLockDispatcher,
    driver: canLockDriver,
    rep: canLockRep,
    supplier: canLockSupplier,
    edit: canLockEdit,
    b2c: canLockB2C,
    online: canLockOnline,
  };
  const defaults = getDefaultDateRange();
  const [activeTab, setActiveTab] = useState<LockTab>("dispatcher");
  const [dateFrom, setDateFrom] = useState(defaults.dateFrom);
  const [dateTo, setDateTo] = useState(defaults.dateTo);
  const [search, setSearch] = useState("");
  const [jobs, setJobs] = useState<JobLockItem[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(false);
  const [toggling, setToggling] = useState<string | null>(null);

  const fetchJobs = useCallback(
    async (tab: LockTab, from: string, to: string, searchStr: string, pageNum: number) => {
      setLoading(true);
      try {
        const params = new URLSearchParams({
          dateFrom: from,
          dateTo: to,
          page: String(pageNum),
          limit: String(PAGE_SIZE),
        });
        if (searchStr) params.set("search", searchStr);
        const res = await api.get(`/job-locks/${tab}?${params.toString()}`);
        const result: PagedResult = res.data.data;
        setJobs(result.data);
        setTotal(result.total);
        setPage(result.page);
      } catch {
        toast.error(t("jobLocks.toggleFailed"));
      } finally {
        setLoading(false);
      }
    },
    [t],
  );

  const handleSearch = () => {
    setPage(1);
    fetchJobs(activeTab, dateFrom, dateTo, search, 1);
  };

  const handleTabChange = (tab: string) => {
    const lockTab = tab as LockTab;
    setActiveTab(lockTab);
    setJobs([]);
    setTotal(0);
    setPage(1);
    fetchJobs(lockTab, dateFrom, dateTo, search, 1);
  };

  const handlePageChange = (newPage: number) => {
    fetchJobs(activeTab, dateFrom, dateTo, search, newPage);
  };

  const handleToggleLock = async (job: JobLockItem) => {
    setToggling(job.id);
    try {
      const action = job.isUnlocked ? "lock" : "unlock";
      await api.post(`/job-locks/${activeTab}/${job.id}/${action}`);
      toast.success(
        job.isUnlocked ? t("jobLocks.lockSuccess") : t("jobLocks.unlockSuccess"),
      );
      setJobs((prev) =>
        prev.map((j) =>
          j.id === job.id ? { ...j, isUnlocked: !j.isUnlocked } : j,
        ),
      );
    } catch {
      toast.error(t("jobLocks.toggleFailed"));
    } finally {
      setToggling(null);
    }
  };

  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE));

  return (
    <div className="space-y-6">
      <PageHeader
        title={t("jobLocks.title")}
        description={t("jobLocks.description")}
      />

      <Card className="p-6">
        <Tabs
          defaultValue="dispatcher"
          value={activeTab}
          onValueChange={handleTabChange}
        >
          <TabsList className="mb-4">
            <TabsTrigger value="dispatcher">
              {t("jobLocks.tabs.dispatcher")}
            </TabsTrigger>
            <TabsTrigger value="driver">
              {t("jobLocks.tabs.driver")}
            </TabsTrigger>
            <TabsTrigger value="rep">{t("jobLocks.tabs.rep")}</TabsTrigger>
            <TabsTrigger value="supplier">
              {t("jobLocks.tabs.supplier")}
            </TabsTrigger>
            <TabsTrigger value="edit">
              {t("jobLocks.tabs.edit")}
            </TabsTrigger>
            <TabsTrigger value="b2c">
              {t("jobLocks.tabs.b2c")}
            </TabsTrigger>
            <TabsTrigger value="online">
              {t("jobLocks.tabs.online")}
            </TabsTrigger>
          </TabsList>

          {/* Filters */}
          <div className="mb-4 flex flex-wrap items-end gap-3">
            <div>
              <label className="mb-1 block text-xs font-medium text-muted-foreground">
                {t("jobLocks.filters.dateFrom")}
              </label>
              <Input
                type="date"
                value={dateFrom}
                onChange={(e) => setDateFrom(e.target.value)}
                className="w-40"
              />
            </div>
            <div>
              <label className="mb-1 block text-xs font-medium text-muted-foreground">
                {t("jobLocks.filters.dateTo")}
              </label>
              <Input
                type="date"
                value={dateTo}
                onChange={(e) => setDateTo(e.target.value)}
                className="w-40"
              />
            </div>
            <div>
              <label className="mb-1 block text-xs font-medium text-muted-foreground">
                &nbsp;
              </label>
              <div className="relative">
                <Search className="absolute left-2.5 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                <Input
                  placeholder={t("jobLocks.filters.search")}
                  value={search}
                  onChange={(e) => setSearch(e.target.value)}
                  onKeyDown={(e) => e.key === "Enter" && handleSearch()}
                  className="w-56 pl-8"
                />
              </div>
            </div>
            <Button onClick={handleSearch} disabled={loading}>
              {loading ? (
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              ) : (
                <Search className="mr-2 h-4 w-4" />
              )}
              {t("common.search")}
            </Button>
          </div>

          {/* Table content (same for all tabs) */}
          {(["dispatcher", "driver", "rep", "supplier", "edit", "b2c", "online"] as LockTab[]).map((tab) => (
            <TabsContent key={tab} value={tab}>
              <JobLocksTable
                jobs={jobs}
                tab={tab}
                loading={loading}
                toggling={toggling}
                onToggleLock={handleToggleLock}
                canToggle={lockPermissions[tab]}
                t={t}
              />
              {/* Pagination */}
              {!loading && total > 0 && (
                <div className="mt-4 flex items-center justify-between text-sm text-muted-foreground">
                  <span>
                    Showing {(page - 1) * PAGE_SIZE + 1}–{Math.min(page * PAGE_SIZE, total)} of {total} jobs
                  </span>
                  <div className="flex items-center gap-2">
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => handlePageChange(page - 1)}
                      disabled={page <= 1}
                    >
                      <ChevronLeft className="h-4 w-4" />
                    </Button>
                    <span className="tabular-nums">
                      {page} / {totalPages}
                    </span>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => handlePageChange(page + 1)}
                      disabled={page >= totalPages}
                    >
                      <ChevronRight className="h-4 w-4" />
                    </Button>
                  </div>
                </div>
              )}
            </TabsContent>
          ))}
        </Tabs>
      </Card>
    </div>
  );
}

function JobLocksTable({
  jobs,
  tab,
  loading,
  toggling,
  onToggleLock,
  canToggle,
  t,
}: {
  jobs: JobLockItem[];
  tab: LockTab;
  loading: boolean;
  toggling: string | null;
  onToggleLock: (job: JobLockItem) => void;
  canToggle: boolean;
  t: (key: string) => string;
}) {
  const { visibility: jlColVis, saveVisibility: saveJlColVis } = useColumnPreferences("job_locks", JOB_LOCKS_COL_DEFS.map((c) => c.key));
  const isVis = (key: string) => jlColVis[key] !== false;

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
      </div>
    );
  }

  if (jobs.length === 0) {
    return (
      <div className="py-12 text-center text-sm text-muted-foreground">
        {t("jobLocks.noJobs")}
      </div>
    );
  }

  return (
    <>
      <div className="flex justify-end mb-2">
        <ColumnVisibilityControl columns={JOB_LOCKS_COL_DEFS} visibility={jlColVis} onSave={saveJlColVis} />
      </div>
      <div className="rounded-md border">
        <Table>
          <TableHeader>
            <TableRow>
              {isVis("lock") && <TableHead className="w-16">{t("jobLocks.table.lock")}</TableHead>}
              {isVis("ref") && <TableHead>{t("jobLocks.table.ref")}</TableHead>}
              {isVis("entity") && <TableHead>{t("jobLocks.table.entity")}</TableHead>}
              {isVis("route") && <TableHead>{t("jobLocks.table.route")}</TableHead>}
              {isVis("date") && <TableHead>{t("jobLocks.table.date")}</TableHead>}
              {isVis("status") && <TableHead>{t("jobLocks.table.status")}</TableHead>}
              {isVis("provider") && <TableHead>{t("jobLocks.table.provider")}</TableHead>}
            </TableRow>
          </TableHeader>
          <TableBody>
            {jobs.map((job) => {
              const isToggling = toggling === job.id;
              const route = [
                job.fromZone?.name,
                job.toZone?.name,
              ]
                .filter(Boolean)
                .join(" → ");
              const provider =
                job.agent?.legalName || job.customer?.legalName || "-";

              return (
                <TableRow key={job.id}>
                  {isVis("lock") && (
                    <TableCell>
                      {canToggle ? (
                        <button onClick={() => onToggleLock(job)} disabled={isToggling} className="flex h-8 w-8 items-center justify-center rounded-md transition-colors hover:bg-muted" title={job.isUnlocked ? t("jobLocks.lock") : t("jobLocks.unlock")}>
                          {isToggling ? <Loader2 className="h-4 w-4 animate-spin" /> : job.isUnlocked ? <LockOpen className="h-4 w-4 text-green-500" /> : <Lock className="h-4 w-4 text-amber-500" />}
                        </button>
                      ) : (
                        <div className="flex h-8 w-8 items-center justify-center">
                          {job.isUnlocked ? <LockOpen className="h-4 w-4 text-green-500/50" /> : <Lock className="h-4 w-4 text-amber-500/50" />}
                        </div>
                      )}
                    </TableCell>
                  )}
                  {isVis("ref") && <TableCell className="font-mono text-xs">{job.internalRef}</TableCell>}
                  {isVis("entity") && <TableCell>{getEntityName(job, tab)}</TableCell>}
                  {isVis("route") && <TableCell className="text-sm">{route || "-"}</TableCell>}
                  {isVis("date") && <TableCell className="text-sm">{new Date(job.jobDate).toLocaleDateString()}</TableCell>}
                  {isVis("status") && (
                    <TableCell>
                      <Badge variant={job.isUnlocked ? "default" : "secondary"} className={job.isUnlocked ? "bg-green-500/10 text-green-500 border-green-500/20" : "bg-amber-500/10 text-amber-500 border-amber-500/20"}>
                        {job.isUnlocked ? t("jobLocks.unlocked") : t("jobLocks.locked")}
                      </Badge>
                    </TableCell>
                  )}
                  {isVis("provider") && <TableCell className="text-sm">{provider}</TableCell>}
                </TableRow>
              );
            })}
          </TableBody>
        </Table>
      </div>
    </>
  );
}
