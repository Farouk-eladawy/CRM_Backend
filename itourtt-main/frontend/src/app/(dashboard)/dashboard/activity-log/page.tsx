"use client";

import { useEffect, useState, useCallback, useRef } from "react";
import {
  ClipboardList,
  Loader2,
  Download,
  Search,
  X,
  Play,
} from "lucide-react";
import { toast } from "sonner";
import { PageHeader } from "@/components/page-header";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { useSortable } from "@/hooks/use-sortable";
import { SortableHeader } from "@/components/sortable-header";
import api from "@/lib/api";
import { useT } from "@/lib/i18n";
import { usePermission } from "@/hooks/use-permission";
import { localDateStr } from "@/lib/utils";
import { useColumnPreferences } from "@/hooks/useColumnPreferences";
import { ColumnVisibilityControl } from "@/components/ui/column-visibility-control";
import { type ColumnDef } from "@/components/ui/draggable-table-header";

const ACTIVITY_COL_DEFS: ColumnDef[] = [
  { key: "dateTime", label: "Date/Time" },
  { key: "user", label: "User" },
  { key: "action", label: "Action" },
  { key: "entity", label: "Window" },
  { key: "summary", label: "Summary" },
];

// Friendly screen/window name for a raw audit `entity` value. Mirrors the
// backend WINDOW_LABELS; sub-resources use dot notation (e.g. "Agent.PriceList").
const WINDOW_LABELS: Record<string, string> = {
  TrafficJob: "Traffic Jobs",
  Agent: "Agents",
  Customer: "Customers",
  Supplier: "Suppliers",
  Driver: "Drivers",
  Rep: "Reps",
  Vehicle: "Vehicles",
  VehicleType: "Vehicle Types",
  Location: "Locations",
  Dispatch: "Dispatch Console",
  Finance: "Finance",
  Invoice: "Invoices",
  JobLock: "Job Locks",
  Permission: "Permissions",
  Settings: "Settings",
  Report: "Reports",
  Whatsapp: "WhatsApp",
  ActivityLog: "Activity Log",
  User: "Users",
};

function windowLabel(entity: string): string {
  return entity
    .split(".")
    .map((p) => WINDOW_LABELS[p] ?? p.replace(/([a-z0-9])([A-Z])/g, "$1 $2"))
    .join(" › ");
}

// ─── Types ──────────────────────────────────────────────────────
interface ActivityLog {
  id: string;
  userId: string;
  userName: string;
  action: string;
  entity: string;
  entityId: string | null;
  summary: string;
  ipAddress: string | null;
  createdAt: string;
}

interface ActivityLogDetail extends ActivityLog {
  details: Record<string, unknown> | null;
  previousData?: Record<string, unknown> | null;
  window?: string;
  entityRef?: string | null;
  createdFields?: { label: string; value: string }[];
  deletedFields?: { label: string; value: string }[];
  changes?: { label: string; oldValue: string; newValue: string }[];
}

interface User {
  id: string;
  name: string;
  email: string;
}

// ─── Main Page ──────────────────────────────────────────────────
export default function ActivityLogPage() {
  const t = useT();
  const canExport = usePermission("activity-logs.export");

  // State
  const [logs, setLogs] = useState<ActivityLog[]>([]);
  const [loading, setLoading] = useState(false);
  const [generated, setGenerated] = useState(false);
  const [totalPages, setTotalPages] = useState(1);
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);

  // Filters
  const [userFilter, setUserFilter] = useState("ALL");
  const [actionFilter, setActionFilter] = useState("ALL");
  const [entityFilter, setEntityFilter] = useState("ALL");
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");
  const [search, setSearch] = useState("");

  // Dropdown data
  const [users, setUsers] = useState<User[]>([]);
  const [entities, setEntities] = useState<string[]>([]);

  // Detail modal
  const [selectedLog, setSelectedLog] = useState<ActivityLogDetail | null>(null);
  const [detailOpen, setDetailOpen] = useState(false);
  const [detailLoading, setDetailLoading] = useState(false);

  // Export loading
  const [exporting, setExporting] = useState(false);

  const { sortedData, sortKey, sortDir, onSort } = useSortable(logs);
  const { visibility: actColVis, saveVisibility: saveActColVis } = useColumnPreferences("activity_log", ACTIVITY_COL_DEFS.map((c) => c.key));
  const isVis = (key: string) => actColVis[key] !== false;

  // Track current page for pagination re-fetch
  const pageRef = useRef(page);
  pageRef.current = page;

  // ─── Build query params ─────────────────────────────────────
  const buildParams = useCallback((pageNum?: number) => {
    const params: Record<string, string> = { page: String(pageNum ?? page), limit: "30" };
    if (userFilter !== "ALL") params.userId = userFilter;
    if (actionFilter !== "ALL") params.action = actionFilter;
    if (entityFilter !== "ALL") params.entity = entityFilter;
    if (dateFrom) params.dateFrom = dateFrom;
    if (dateTo) params.dateTo = dateTo;
    if (search.trim()) params.search = search.trim();
    return new URLSearchParams(params).toString();
  }, [page, userFilter, actionFilter, entityFilter, dateFrom, dateTo, search]);

  // ─── Fetch logs (only called on Generate or pagination) ─────
  const fetchLogs = useCallback(async (pageNum?: number) => {
    setLoading(true);
    try {
      const qs = buildParams(pageNum);
      const { data } = await api.get(`/activity-logs?${qs}`);
      setLogs(Array.isArray(data.data) ? data.data : []);
      setTotal(data.meta?.total ?? 0);
      setTotalPages(data.meta?.totalPages ?? 1);
      setGenerated(true);
    } catch {
      toast.error("Failed to load activity logs");
    } finally {
      setLoading(false);
    }
  }, [buildParams]);

  // ─── Fetch dropdown data ─────────────────────────────────────
  useEffect(() => {
    async function loadDropdowns() {
      try {
        const [usersRes, entitiesRes] = await Promise.all([
          api.get("/users?limit=100"),
          api.get("/activity-logs/entities"),
        ]);
        setUsers(
          Array.isArray(usersRes.data?.data)
            ? usersRes.data.data
            : Array.isArray(usersRes.data)
              ? usersRes.data
              : [],
        );
        setEntities(Array.isArray(entitiesRes.data) ? entitiesRes.data : []);
      } catch {
        // Silently fail — dropdowns just won't have values
      }
    }
    loadDropdowns();
  }, []);

  // ─── Re-fetch on page change (only if already generated) ────
  useEffect(() => {
    if (generated) {
      fetchLogs(page);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [page]);

  // ─── Generate handler ──────────────────────────────────────
  function handleGenerate() {
    setPage(1);
    fetchLogs(1);
  }

  // ─── Open detail ─────────────────────────────────────────────
  async function openDetail(id: string) {
    setDetailLoading(true);
    setDetailOpen(true);
    try {
      const { data } = await api.get(`/activity-logs/${id}`);
      setSelectedLog(data);
    } catch {
      toast.error("Failed to load log details");
      setDetailOpen(false);
    } finally {
      setDetailLoading(false);
    }
  }

  // ─── Export ──────────────────────────────────────────────────
  async function handleExport() {
    setExporting(true);
    try {
      const params: Record<string, string> = {};
      if (userFilter !== "ALL") params.userId = userFilter;
      if (actionFilter !== "ALL") params.action = actionFilter;
      if (entityFilter !== "ALL") params.entity = entityFilter;
      if (dateFrom) params.dateFrom = dateFrom;
      if (dateTo) params.dateTo = dateTo;
      if (search.trim()) params.search = search.trim();
      const qs = new URLSearchParams(params).toString();

      const { data } = await api.get(`/activity-logs/export?${qs}`, {
        responseType: "blob",
      });
      const url = window.URL.createObjectURL(new Blob([data]));
      const a = document.createElement("a");
      a.href = url;
      a.download = `activity_log_${localDateStr(new Date())}.xlsx`;
      a.click();
      window.URL.revokeObjectURL(url);
      toast.success(t("common.exportSuccess"));
    } catch {
      toast.error(t("common.exportFailed"));
    } finally {
      setExporting(false);
    }
  }

  // ─── Clear filters ───────────────────────────────────────────
  function clearFilters() {
    setUserFilter("ALL");
    setActionFilter("ALL");
    setEntityFilter("ALL");
    setDateFrom("");
    setDateTo("");
    setSearch("");
  }

  const hasFilters =
    userFilter !== "ALL" ||
    actionFilter !== "ALL" ||
    entityFilter !== "ALL" ||
    dateFrom !== "" ||
    dateTo !== "" ||
    search.trim() !== "";

  // ─── Action badge ────────────────────────────────────────────
  function actionBadge(action: string) {
    switch (action) {
      case "CREATE":
        return (
          <Badge className="bg-emerald-500/20 text-emerald-600 dark:text-emerald-400">
            {t("activityLog.created")}
          </Badge>
        );
      case "UPDATE":
        return (
          <Badge className="bg-blue-500/20 text-blue-600 dark:text-blue-400">
            {t("activityLog.updated")}
          </Badge>
        );
      case "DELETE":
        return (
          <Badge className="bg-red-500/20 text-red-600 dark:text-red-400">
            {t("activityLog.deleted")}
          </Badge>
        );
      default:
        return <Badge variant="secondary">{action}</Badge>;
    }
  }

  function formatDateTime(iso: string) {
    const d = new Date(iso);
    const dd = String(d.getDate()).padStart(2, "0");
    const mm = String(d.getMonth() + 1).padStart(2, "0");
    const yy = d.getFullYear();
    const hh = String(d.getHours()).padStart(2, "0");
    const mn = String(d.getMinutes()).padStart(2, "0");
    const ss = String(d.getSeconds()).padStart(2, "0");
    return `${dd}/${mm}/${yy} ${hh}:${mn}:${ss}`;
  }

  // ─── Render ──────────────────────────────────────────────────
  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <PageHeader
          title={t("activityLog.title")}
          description={t("activityLog.description")}
        />
        {canExport && (
          <Button
            size="sm"
            variant="outline"
            className="gap-1.5"
            onClick={handleExport}
            disabled={exporting || !generated}
          >
            {exporting ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <Download className="h-4 w-4" />
            )}
            {t("activityLog.export")}
          </Button>
        )}
      </div>

      {/* ─── Filters ─────────────────────────────────────────── */}
      <div className="flex flex-wrap items-end gap-3">
        {/* Search */}
        <div className="relative w-52">
          <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
          <Input
            placeholder={t("common.search") + "..."}
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="pl-8 border-border bg-muted/50 text-foreground placeholder:text-muted-foreground/50 h-9"
          />
        </div>

        {/* User */}
        <Select value={userFilter} onValueChange={setUserFilter}>
          <SelectTrigger className="w-44 border-border bg-muted/50 text-foreground h-9">
            <SelectValue placeholder={t("activityLog.allUsers")} />
          </SelectTrigger>
          <SelectContent className="border-border bg-popover text-popover-foreground">
            <SelectItem value="ALL">{t("activityLog.allUsers")}</SelectItem>
            {users.map((u) => (
              <SelectItem key={u.id} value={u.id}>
                {u.name}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>

        {/* Action */}
        <Select value={actionFilter} onValueChange={setActionFilter}>
          <SelectTrigger className="w-36 border-border bg-muted/50 text-foreground h-9">
            <SelectValue placeholder={t("activityLog.allActions")} />
          </SelectTrigger>
          <SelectContent className="border-border bg-popover text-popover-foreground">
            <SelectItem value="ALL">{t("activityLog.allActions")}</SelectItem>
            <SelectItem value="CREATE">{t("activityLog.created")}</SelectItem>
            <SelectItem value="UPDATE">{t("activityLog.updated")}</SelectItem>
            <SelectItem value="DELETE">{t("activityLog.deleted")}</SelectItem>
          </SelectContent>
        </Select>

        {/* Entity */}
        <Select value={entityFilter} onValueChange={setEntityFilter}>
          <SelectTrigger className="w-40 border-border bg-muted/50 text-foreground h-9">
            <SelectValue placeholder={t("activityLog.allEntities")} />
          </SelectTrigger>
          <SelectContent className="border-border bg-popover text-popover-foreground">
            <SelectItem value="ALL">{t("activityLog.allEntities")}</SelectItem>
            {entities.map((e) => (
              <SelectItem key={e} value={e}>
                {windowLabel(e)}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>

        {/* Date From */}
        <div className="flex items-center gap-1.5">
          <span className="text-xs text-muted-foreground">{t("activityLog.from")}</span>
          <Input
            type="date"
            value={dateFrom}
            onChange={(e) => setDateFrom(e.target.value)}
            className="w-36 border-border bg-muted/50 text-foreground h-9"
          />
        </div>

        {/* Date To */}
        <div className="flex items-center gap-1.5">
          <span className="text-xs text-muted-foreground">{t("activityLog.to")}</span>
          <Input
            type="date"
            value={dateTo}
            onChange={(e) => setDateTo(e.target.value)}
            className="w-36 border-border bg-muted/50 text-foreground h-9"
          />
        </div>

        {/* Generate */}
        <Button
          size="sm"
          className="h-9 gap-1.5"
          onClick={handleGenerate}
          disabled={loading}
        >
          {loading ? (
            <Loader2 className="h-4 w-4 animate-spin" />
          ) : (
            <Play className="h-4 w-4" />
          )}
          {t("activityLog.generate")}
        </Button>

        {/* Clear */}
        {hasFilters && (
          <Button
            variant="ghost"
            size="sm"
            className="h-9 gap-1 text-muted-foreground"
            onClick={clearFilters}
          >
            <X className="h-3.5 w-3.5" />
            Clear
          </Button>
        )}
      </div>

      {/* ─── Table ───────────────────────────────────────────── */}
      {!generated && !loading ? (
        <div className="flex flex-col items-center justify-center py-16 text-muted-foreground">
          <ClipboardList className="mb-2 h-8 w-8" />
          <p className="text-sm">{t("activityLog.generateHint")}</p>
        </div>
      ) : loading ? (
        <div className="flex items-center justify-center py-16">
          <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
        </div>
      ) : logs.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-16 text-muted-foreground">
          <ClipboardList className="mb-2 h-8 w-8" />
          <p className="text-sm">{t("activityLog.noLogs")}</p>
        </div>
      ) : (
        <>
          <div className="overflow-x-auto [overflow-y:clip]">
            <div className="flex justify-end mb-2">
              <ColumnVisibilityControl columns={ACTIVITY_COL_DEFS} visibility={actColVis} onSave={saveActColVis} />
            </div>
            <Table>
              <TableHeader>
                <TableRow className="border-border bg-muted">
                  {isVis("dateTime") && <SortableHeader label={t("activityLog.dateTime")} sortKey="createdAt" currentKey={sortKey} currentDir={sortDir} onSort={onSort} />}
                  {isVis("user") && <SortableHeader label={t("activityLog.user")} sortKey="userName" currentKey={sortKey} currentDir={sortDir} onSort={onSort} />}
                  {isVis("action") && <SortableHeader label={t("activityLog.action")} sortKey="action" currentKey={sortKey} currentDir={sortDir} onSort={onSort} />}
                  {isVis("entity") && <SortableHeader label={t("activityLog.entity")} sortKey="entity" currentKey={sortKey} currentDir={sortDir} onSort={onSort} />}
                  {isVis("summary") && <TableHead className="text-muted-foreground text-xs">{t("activityLog.summary")}</TableHead>}
                </TableRow>
              </TableHeader>
              <TableBody>
                {sortedData.map((log, idx) => (
                  <TableRow
                    key={log.id}
                    className={`border-border cursor-pointer transition-colors hover:bg-accent/50 ${
                      idx % 2 === 0
                        ? "bg-gray-100/25 dark:bg-gray-800/25"
                        : "bg-gray-200/50 dark:bg-gray-700/50"
                    }`}
                    onClick={() => openDetail(log.id)}
                  >
                    {isVis("dateTime") && <TableCell className="text-muted-foreground text-xs whitespace-nowrap">{formatDateTime(log.createdAt)}</TableCell>}
                    {isVis("user") && <TableCell className="font-medium text-foreground whitespace-nowrap">{log.userName}</TableCell>}
                    {isVis("action") && <TableCell>{actionBadge(log.action)}</TableCell>}
                    {isVis("entity") && <TableCell><Badge variant="secondary" className="bg-secondary text-muted-foreground">{windowLabel(log.entity)}</Badge></TableCell>}
                    {isVis("summary") && <TableCell className="text-muted-foreground max-w-xs truncate">{log.summary}</TableCell>}
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>

          {/* Pagination */}
          <div className="flex items-center justify-between text-sm text-muted-foreground">
            <span>
              {total} record{total !== 1 ? "s" : ""}
            </span>
            <div className="flex items-center gap-2">
              <Button
                variant="outline"
                size="sm"
                disabled={page <= 1}
                onClick={() => setPage((p) => Math.max(1, p - 1))}
              >
                Previous
              </Button>
              <span>
                Page {page} of {totalPages}
              </span>
              <Button
                variant="outline"
                size="sm"
                disabled={page >= totalPages}
                onClick={() => setPage((p) => p + 1)}
              >
                Next
              </Button>
            </div>
          </div>
        </>
      )}

      {/* ─── Detail Modal ────────────────────────────────────── */}
      <Dialog open={detailOpen} onOpenChange={setDetailOpen}>
        <DialogContent className="border-border bg-popover text-popover-foreground sm:max-w-lg flex max-h-[90vh] flex-col overflow-hidden">
          <DialogHeader className="shrink-0">
            <DialogTitle>{t("activityLog.details")}</DialogTitle>
          </DialogHeader>

          {detailLoading ? (
            <div className="flex items-center justify-center py-8">
              <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
            </div>
          ) : selectedLog ? (
            <div className="-mr-2 min-h-0 flex-1 space-y-3 overflow-y-auto pr-2">
              <div className="grid grid-cols-1 gap-3 text-sm sm:grid-cols-2">
                <div>
                  <span className="text-muted-foreground text-xs">
                    {t("activityLog.dateTime")}
                  </span>
                  <p className="text-foreground">
                    {formatDateTime(selectedLog.createdAt)}
                  </p>
                </div>
                <div>
                  <span className="text-muted-foreground text-xs">
                    {t("activityLog.user")}
                  </span>
                  <p className="text-foreground">{selectedLog.userName}</p>
                </div>
                <div>
                  <span className="text-muted-foreground text-xs">
                    {t("activityLog.action")}
                  </span>
                  <div className="mt-0.5">{actionBadge(selectedLog.action)}</div>
                </div>
                <div>
                  <span className="text-muted-foreground text-xs">
                    {t("activityLog.entity")}
                  </span>
                  <p className="text-foreground">
                    {selectedLog.window ?? windowLabel(selectedLog.entity)}
                  </p>
                </div>
                {(selectedLog.entityRef || selectedLog.entityId) && (
                  <div className="col-span-2">
                    <span className="text-muted-foreground text-xs">
                      {t("activityLog.entityId")}
                    </span>
                    {selectedLog.entityRef ? (
                      <p className="text-foreground">
                        {selectedLog.entityRef}
                        {selectedLog.entityId && (
                          <span className="ml-2 font-mono text-[10px] text-muted-foreground">
                            {selectedLog.entityId}
                          </span>
                        )}
                      </p>
                    ) : (
                      <p className="text-foreground font-mono text-xs">
                        {selectedLog.entityId}
                      </p>
                    )}
                  </div>
                )}
                <div className="col-span-2">
                  <span className="text-muted-foreground text-xs">
                    {t("activityLog.summary")}
                  </span>
                  <p className="text-foreground">{selectedLog.summary}</p>
                </div>
                {selectedLog.ipAddress && (
                  <div className="col-span-2">
                    <span className="text-muted-foreground text-xs">
                      {t("activityLog.ipAddress")}
                    </span>
                    <p className="text-foreground font-mono text-xs">
                      {selectedLog.ipAddress}
                    </p>
                  </div>
                )}
              </div>

              {/* CREATE → readable list of what was created */}
              {selectedLog.createdFields && selectedLog.createdFields.length > 0 && (
                <div>
                  <span className="text-muted-foreground text-xs">
                    {t("activityLog.whatCreated")}
                  </span>
                  <div className="mt-1 overflow-hidden rounded-md border border-border">
                    <table className="w-full text-sm">
                      <tbody>
                        {selectedLog.createdFields.map((f, i) => (
                          <tr key={i} className="border-b border-border last:border-0">
                            <td className="w-2/5 bg-muted/40 px-3 py-1.5 align-top font-medium text-foreground">
                              {f.label}
                            </td>
                            <td className="px-3 py-1.5 align-top text-foreground break-words">
                              {f.value}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}

              {/* DELETE → readable list of what was removed */}
              {selectedLog.deletedFields && selectedLog.deletedFields.length > 0 && (
                <div>
                  <span className="text-muted-foreground text-xs">
                    {t("activityLog.whatDeleted")}
                  </span>
                  <div className="mt-1 overflow-hidden rounded-md border border-border">
                    <table className="w-full text-sm">
                      <tbody>
                        {selectedLog.deletedFields.map((f, i) => (
                          <tr key={i} className="border-b border-border last:border-0">
                            <td className="w-2/5 bg-muted/40 px-3 py-1.5 align-top font-medium text-foreground">
                              {f.label}
                            </td>
                            <td className="px-3 py-1.5 align-top text-foreground break-words line-through opacity-70">
                              {f.value}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}

              {/* UPDATE → old (left) vs new (right) comparison */}
              {selectedLog.action === "UPDATE" && selectedLog.changes && (
                <div>
                  <span className="text-muted-foreground text-xs">
                    {t("activityLog.whatChanged")}
                  </span>
                  {selectedLog.changes.length === 0 ? (
                    <p className="mt-1 text-sm text-muted-foreground">
                      {t("activityLog.noChanges")}
                    </p>
                  ) : (
                    <div className="mt-1 overflow-hidden rounded-md border border-border">
                      <table className="w-full text-sm">
                        <thead>
                          <tr className="bg-muted text-xs text-muted-foreground">
                            <th className="px-3 py-1.5 text-left font-medium">
                              {t("activityLog.fieldCol")}
                            </th>
                            <th className="px-3 py-1.5 text-left font-medium">
                              {t("activityLog.previousCol")}
                            </th>
                            <th className="px-3 py-1.5 text-left font-medium">
                              {t("activityLog.newCol")}
                            </th>
                          </tr>
                        </thead>
                        <tbody>
                          {selectedLog.changes.map((c, i) => (
                            <tr key={i} className="border-t border-border align-top">
                              <td className="px-3 py-1.5 font-medium text-foreground">
                                {c.label}
                              </td>
                              <td className="px-3 py-1.5 text-muted-foreground break-words line-through opacity-70">
                                {c.oldValue}
                              </td>
                              <td className="px-3 py-1.5 break-words font-medium text-emerald-600 dark:text-emerald-400">
                                {c.newValue}
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  )}
                </div>
              )}

              {/* Raw payload kept behind a collapsible for technical review */}
              {((selectedLog.details &&
                Object.keys(selectedLog.details).length > 0) ||
                (selectedLog.previousData &&
                  Object.keys(selectedLog.previousData).length > 0)) && (
                <details className="group">
                  <summary className="cursor-pointer text-muted-foreground text-xs hover:text-foreground">
                    {t("activityLog.technicalDetails")}
                  </summary>
                  <pre className="mt-1 max-h-60 overflow-auto rounded-md border border-border bg-muted/50 p-3 text-xs text-foreground">
                    {JSON.stringify(
                      {
                        ...(selectedLog.previousData
                          ? { previous: selectedLog.previousData }
                          : {}),
                        ...(selectedLog.details
                          ? { submitted: selectedLog.details }
                          : {}),
                      },
                      null,
                      2,
                    )}
                  </pre>
                </details>
              )}
            </div>
          ) : null}
        </DialogContent>
      </Dialog>
    </div>
  );
}
