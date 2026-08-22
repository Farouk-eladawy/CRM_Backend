"use client";

import { useEffect, useState, useCallback } from "react";
import { useRouter } from "next/navigation";
import { toast } from "sonner";
import {
  Loader2,
  Search,
  Filter,
  Plus,
  Printer,
  MapPin,
  ExternalLink,
  Image,
  PlaneLanding,
  ChevronUp,
  ChevronDown,
  AlertTriangle,
} from "lucide-react";
import { PageHeader } from "@/components/page-header";
import { EmptyState } from "@/components/ui/empty-state";
import { Skeleton } from "@/components/ui/skeleton";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "@/components/ui/dialog";
import { Label } from "@/components/ui/label";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import api from "@/lib/api";
import { useT, useLocaleId } from "@/lib/i18n";
import { formatDate , localDateStr } from "@/lib/utils";
import { SortableHeader } from "@/components/sortable-header";
import { useSortable } from "@/hooks/use-sortable";
import { usePermission } from "@/hooks/use-permission";
import { StatusBadge } from "@/components/ui/status-badge";
import { useColumnPreferences } from "@/hooks/useColumnPreferences";
import { DraggableTableHeader, type ColumnDef } from "@/components/ui/draggable-table-header";
import { ColumnVisibilityControl } from "@/components/ui/column-visibility-control";
import { useServiceTypeLabel } from "@/lib/service-types";

interface TrafficJob {
  id: string;
  internalRef: string;
  agentRef: string | null;
  customerJobId: string | null;
  bookingChannel: "ONLINE" | "B2B" | "B2C";
  serviceType: string;
  jobDate: string;
  createdAt: string;
  status: string;
  bookingStatus: string;
  adultCount: number;
  childCount: number;
  paxCount: number;
  clientName: string | null;
  clientMobile: string | null;
  pickUpTime: string | null;
  notes: string | null;
  jobExtras?: { name: string; qty: number }[];
  printSign: boolean;
  transferPrice: number | null;
  transferPriceCurrency: string;
  collectionRequired: boolean;
  collectionAmount: number | null;
  collectionCurrency: string;
  requestedVehicleType?: { name: string } | null;
  custRepName: string | null;
  custRepMobile: string | null;
  agent?: { legalName: string } | null;
  customer?: { legalName: string } | null;
  originAirport?: { name: string; code: string } | null;
  originZone?: { name: string } | null;
  originHotel?: { name: string } | null;
  destinationAirport?: { name: string; code: string } | null;
  destinationZone?: { name: string } | null;
  destinationHotel?: { name: string } | null;
  fromZone?: { name: string } | null;
  toZone?: { name: string } | null;
  flight?: { flightNo: string; carrier?: string; terminal?: string; arrivalTime?: string; departureTime?: string } | null;
  createdBy?: { id: string; name: string } | null;
  assignment?: {
    vehicle?: { plateNumber: string };
    driver?: { name: string };
    rep?: { name: string };
    driverStatus?: string;
    repStatus?: string;
  } | null;
  noShowEvidence?: {
    id: string;
    imageUrls: string[];
    gpsLatitude: number | string;
    gpsLongitude: number | string;
    gpsMapLink: string;
    submittedBy: string;
    createdAt: string;
  }[];
}


export default function TrafficJobsPage() {
  const t = useT();
  const locale = useLocaleId();
  const router = useRouter();
  const canPrintSigns = usePermission("dispatch.exportButton") || usePermission("traffic-jobs.online.createJob");
  const canFlightDelay = usePermission("reports.flightDelay");
  const [jobs, setJobs] = useState<TrafficJob[]>([]);
  const [loading, setLoading] = useState(true);
  const [filterStatus, setFilterStatus] = useState<string>("ALL");
  const [search, setSearch] = useState("");
  const [generatingSigns, setGeneratingSigns] = useState(false);
  const [signModalOpen, setSignModalOpen] = useState(false);
  const [signDate, setSignDate] = useState(localDateStr(new Date()));
  const [evidenceJob, setEvidenceJob] = useState<TrafficJob | null>(null);
  const [evidenceBlobUrls, setEvidenceBlobUrls] = useState<Map<string, string>>(new Map());
  const [evidenceLoading, setEvidenceLoading] = useState(false);
  const [flightDelayModalOpen, setFlightDelayModalOpen] = useState(false);
  const [flightDelayModalRef, setFlightDelayModalRef] = useState("");
  const [flightDelayEvents, setFlightDelayEvents] = useState<Array<{
    oldArrivalDate: string | null;
    oldArrivalTime: string | null;
    newArrivalDate: string;
    newArrivalTime: string;
    reportedBy: string;
    currentRepName: string | null;
    reportedAt: string;
  }>>([]);
  const [flightDelayModalLoading, setFlightDelayModalLoading] = useState(false);
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [total, setTotal] = useState(0);
  const limit = 100;

  const serviceTypeLabel = useServiceTypeLabel();

  const fetchJobs = useCallback(async () => {
    try {
      const params: Record<string, string> = { page: String(page), limit: String(limit) };
      if (filterStatus !== "ALL") params.status = filterStatus;
      const { data } = await api.get("/traffic-jobs", { params });
      if (Array.isArray(data)) {
        setJobs(data);
        setTotalPages(1);
        setTotal(data.length);
      } else {
        setJobs(data.data || []);
        setTotalPages(data.meta?.totalPages || 1);
        setTotal(data.meta?.total || 0);
      }
    } catch {
      toast.error(t("jobs.failedLoad"));
    } finally {
      setLoading(false);
    }
  }, [filterStatus, page]);

  useEffect(() => {
    fetchJobs();
  }, [fetchJobs]);

  const isDriveId = (url: string) => /^[A-Za-z0-9_-]{20,}$/.test(url);

  const openEvidenceDialog = async (job: TrafficJob) => {
    setEvidenceJob(job);
    const allUrls = (job.noShowEvidence ?? []).flatMap((ev) => ev.imageUrls ?? []);
    const driveIds = allUrls.filter(isDriveId);
    if (driveIds.length === 0) return;
    setEvidenceLoading(true);
    const map = new Map<string, string>();
    await Promise.all(
      driveIds.map(async (fileId) => {
        try {
          const res = await api.get(`/export/odoo/evidence-file/${fileId}`, { responseType: "blob" });
          map.set(fileId, URL.createObjectURL(res.data));
        } catch {
          // leave missing — broken img is better than crashing
        }
      })
    );
    setEvidenceBlobUrls(map);
    setEvidenceLoading(false);
  };

  const handlePrintSigns = async () => {
    if (!signDate) {
      toast.error(t("jobs.selectDateForSigns"));
      return;
    }
    setGeneratingSigns(true);
    try {
      const res = await api.get(`/export/odoo/client-signs?date=${signDate}`, {
        responseType: "blob",
      });
      const blob = new Blob([res.data], { type: "application/pdf" });
      const url = URL.createObjectURL(blob);
      window.open(url, "_blank");
      setSignModalOpen(false);
    } catch (err: any) {
      if (err.response?.status === 404) {
        toast.error(t("jobs.noSignJobs"));
      } else {
        toast.error(t("jobs.failedLoad"));
      }
    } finally {
      setGeneratingSigns(false);
    }
  };

  const openFlightDelayModal = async (job: TrafficJob) => {
    setFlightDelayModalRef(job.internalRef);
    setFlightDelayEvents([]);
    setFlightDelayModalOpen(true);
    setFlightDelayModalLoading(true);
    try {
      const { data } = await api.get(`/reports/flight-delay/${job.id}`);
      const result = data.data || data;
      setFlightDelayEvents(result.events || []);
    } catch {
      toast.error("Failed to load flight delay data");
    } finally {
      setFlightDelayModalLoading(false);
    }
  };

  const filtered = jobs.filter((j) => {
    if (search) {
      const q = search.toLowerCase();
      const match =
        j.internalRef?.toLowerCase().includes(q) ||
        j.agentRef?.toLowerCase().includes(q) ||
        j.agent?.legalName?.toLowerCase().includes(q) ||
        j.customer?.legalName?.toLowerCase().includes(q) ||
        j.clientName?.toLowerCase().includes(q);
      if (!match) return false;
    }
    return true;
  });

  const { sortedData, sortKey, sortDir, onSort } = useSortable(filtered);

  // ── Draggable column order ──
  const DEFAULT_COLS = [
    "createdAt", "internalRef", "bookingChannel", "serviceType", "jobDate", "pickUpTime",
    "agentCustomer", "clientName", "clientNumber", "adults", "children",
    "origin", "destination", "flightNo", "terminal", "arrivalTime", "departureTime", "carrier",
    "extras", "printSign", "notes", "status", "bookingStatus",
    "driverStatus", "repStatus", "vehicleType", "transferPrice", "collection",
    "assignment", "custRep", "userLog",
    ...(canFlightDelay ? ["flightDelay"] : []),
  ];
  const { columns: columnOrder, reorder, visibility, saveVisibility } = useColumnPreferences("traffic_jobs_all", DEFAULT_COLS);

  const sortBtn = (label: string, key: string) => (
    <button onClick={() => onSort(key)} className="flex items-center gap-0.5 text-xs font-medium text-muted-foreground hover:text-foreground">
      {label}
      {sortKey === key && (sortDir === "asc" ? <ChevronUp className="h-3 w-3" /> : <ChevronDown className="h-3 w-3" />)}
    </button>
  );
  const th = (label: string) => <span className="text-xs font-medium text-muted-foreground">{label}</span>;

  const columnDefs: ColumnDef[] = [
    { key: "createdAt",      label: sortBtn(t("jobs.bookingDate"), "createdAt") },
    { key: "internalRef",    label: sortBtn(t("dispatch.ref"), "internalRef") },
    { key: "bookingChannel", label: sortBtn(t("jobs.channel"), "bookingChannel") },
    { key: "serviceType",    label: sortBtn(t("jobs.type"), "serviceType") },
    { key: "jobDate",        label: sortBtn(t("jobs.serviceDate"), "jobDate") },
    { key: "pickUpTime",     label: sortBtn(t("jobs.pickUpTime"), "pickUpTime") },
    { key: "agentCustomer",  label: th(t("jobs.agentCustomer")) },
    { key: "clientName",     label: sortBtn(t("jobs.clientName"), "clientName") },
    { key: "clientNumber",   label: th(t("jobs.clientNumber")) },
    { key: "adults",         label: sortBtn(t("jobs.ad"), "adultCount") },
    { key: "children",       label: sortBtn(t("jobs.chd"), "childCount") },
    { key: "origin",         label: th(t("jobs.origin")) },
    { key: "destination",    label: th(t("jobs.destination")) },
    { key: "flightNo",       label: th(t("jobs.flightNumber")) },
    { key: "terminal",       label: th(t("jobs.terminal")) },
    { key: "arrivalTime",    label: th(t("jobs.arrivalTime")) },
    { key: "departureTime",  label: th(t("jobs.departureTime")) },
    { key: "carrier",        label: th(t("jobs.carrier")) },
    { key: "extras",         label: th(t("jobs.extras")) },
    { key: "printSign",      label: th(t("jobs.printSign")) },
    { key: "notes",          label: th(t("jobs.notes")) },
    { key: "status",         label: sortBtn(t("common.status"), "status") },
    { key: "bookingStatus",  label: sortBtn("Bkg Status", "bookingStatus") },
    { key: "driverStatus",   label: th("Driver Status") },
    { key: "repStatus",      label: th("Rep Status") },
    { key: "vehicleType",    label: th("Veh. Type") },
    { key: "transferPrice",  label: th("Transfer Price") },
    { key: "collection",     label: th("Collection") },
    { key: "assignment",     label: th(t("jobs.assignment")) },
    { key: "custRep",        label: th("Cust. Rep") },
    { key: "userLog",        label: th(t("jobs.userLog")) },
    ...(canFlightDelay ? [{ key: "flightDelay", label: th("Flight Delay") }] : []),
  ];

  const renderCell = (key: string, job: TrafficJob): React.ReactNode => {
    switch (key) {
      case "createdAt":
        return <TableCell key={key} className="text-muted-foreground text-xs whitespace-nowrap">{formatDate(job.createdAt)}</TableCell>;
      case "internalRef":
        return (
          <TableCell key={key} className="text-foreground font-mono text-xs whitespace-nowrap">
            {job.internalRef}
            {job.agentRef && <span className="ml-1 text-muted-foreground">({job.agentRef})</span>}
            {job.customerJobId && <span className="ml-1 text-muted-foreground">#{job.customerJobId}</span>}
          </TableCell>
        );
      case "bookingChannel":
        return (
          <TableCell key={key}>
            <Badge variant="outline" className={
              job.bookingChannel === "B2C"
                ? "bg-purple-500/10 text-purple-600 border-purple-500/30 text-xs"
                : job.bookingChannel === "ONLINE"
                  ? "bg-blue-500/10 text-blue-600 border-blue-500/30 text-xs"
                  : "bg-amber-500/10 text-amber-600 border-amber-500/30 text-xs"
            }>
              {job.bookingChannel === "B2C" ? "B2C Website" : job.bookingChannel}
            </Badge>
          </TableCell>
        );
      case "serviceType":
        return (
          <TableCell key={key}>
            <Badge variant="outline" className="border-border text-muted-foreground text-xs">
              {serviceTypeLabel(job.serviceType)}
            </Badge>
          </TableCell>
        );
      case "jobDate":
        return <TableCell key={key} className="text-muted-foreground text-xs whitespace-nowrap">{formatDate(job.jobDate)}</TableCell>;
      case "pickUpTime":
        return (
          <TableCell key={key} className="text-muted-foreground text-xs whitespace-nowrap">
            {job.pickUpTime ? new Date(job.pickUpTime).toLocaleTimeString(locale, { timeZone: "Africa/Cairo", hour: "2-digit", minute: "2-digit", hour12: false }) : "\u2014"}
          </TableCell>
        );
      case "agentCustomer":
        return (
          <TableCell key={key} className="text-muted-foreground text-xs whitespace-nowrap">
            {job.bookingChannel === "B2B" ? (job.customer?.legalName || "\u2014") : job.bookingChannel === "B2C" ? (job.agentRef || "\u2014") : (job.agent?.legalName || "\u2014")}
          </TableCell>
        );
      case "clientName":
        return <TableCell key={key} className="text-muted-foreground text-xs whitespace-nowrap">{job.clientName || "\u2014"}</TableCell>;
      case "clientNumber":
        return <TableCell key={key} className="text-muted-foreground text-xs whitespace-nowrap">{job.clientMobile || "\u2014"}</TableCell>;
      case "adults":
        return <TableCell key={key} className="text-muted-foreground text-xs">{job.adultCount}</TableCell>;
      case "children":
        return <TableCell key={key} className="text-muted-foreground text-xs">{job.childCount}</TableCell>;
      case "origin":
        return (
          <TableCell key={key} className="text-muted-foreground text-xs whitespace-nowrap">
            {job.originAirport?.code || job.originAirport?.name || job.originHotel?.name || job.originZone?.name || job.fromZone?.name || "\u2014"}
          </TableCell>
        );
      case "destination":
        return (
          <TableCell key={key} className="text-muted-foreground text-xs whitespace-nowrap">
            {job.destinationAirport?.code || job.destinationAirport?.name || job.destinationHotel?.name || job.destinationZone?.name || job.toZone?.name || "\u2014"}
          </TableCell>
        );
      case "flightNo":
        return <TableCell key={key} className="text-muted-foreground text-xs whitespace-nowrap">{job.flight?.flightNo || "\u2014"}</TableCell>;
      case "terminal":
        return <TableCell key={key} className="text-muted-foreground text-xs">{job.flight?.terminal || "\u2014"}</TableCell>;
      case "arrivalTime":
        return (
          <TableCell key={key} className="text-muted-foreground text-xs whitespace-nowrap">
            {job.flight?.arrivalTime ? new Date(job.flight.arrivalTime).toLocaleTimeString(locale, { timeZone: "Africa/Cairo", hour: "2-digit", minute: "2-digit", hour12: false }) : "\u2014"}
          </TableCell>
        );
      case "departureTime":
        return (
          <TableCell key={key} className="text-muted-foreground text-xs whitespace-nowrap">
            {job.flight?.departureTime ? new Date(job.flight.departureTime).toLocaleTimeString(locale, { timeZone: "Africa/Cairo", hour: "2-digit", minute: "2-digit", hour12: false }) : "\u2014"}
          </TableCell>
        );
      case "carrier":
        return <TableCell key={key} className="text-muted-foreground text-xs whitespace-nowrap">{job.flight?.carrier || "\u2014"}</TableCell>;
      case "extras":
        return (
          <TableCell key={key} className="text-muted-foreground text-xs whitespace-nowrap">
            {(job.jobExtras || [])
              .filter((e) => e.qty > 0)
              .map((e) => `${e.name} \u00d7${e.qty}`)
              .join(", ") || "\u2014"}
          </TableCell>
        );
      case "printSign":
        return (
          <TableCell key={key} className="text-muted-foreground text-xs text-center">
            {job.printSign ? <span className="text-emerald-500">✓</span> : "\u2014"}
          </TableCell>
        );
      case "notes":
        return (
          <TableCell key={key} className="text-muted-foreground text-xs max-w-[150px] truncate" title={job.notes || ""}>
            {job.notes || "\u2014"}
          </TableCell>
        );
      case "status":
        return (
          <TableCell key={key}>
            {job.status === "NO_SHOW" ? (
              <span data-no-show="true" className="cursor-pointer hover:underline inline-flex items-center gap-1" title="Click to view no-show evidence" onClick={() => openEvidenceDialog(job)}>
                <StatusBadge status={job.status} />
                {(job.noShowEvidence?.length ?? 0) > 0 && <Image className="h-3 w-3 opacity-70" />}
              </span>
            ) : (
              <StatusBadge status={job.status} />
            )}
          </TableCell>
        );
      case "bookingStatus":
        return <TableCell key={key}>{job.bookingStatus ? <StatusBadge status={job.bookingStatus} /> : "\u2014"}</TableCell>;
      case "driverStatus":
        return (
          <TableCell key={key}>
            {job.assignment?.driverStatus ? (
              <span
                data-no-show={job.assignment.driverStatus === "NO_SHOW" ? "true" : undefined}
                className={job.assignment.driverStatus === "NO_SHOW" ? "cursor-pointer hover:underline" : ""}
                onClick={job.assignment.driverStatus === "NO_SHOW" ? () => setEvidenceJob(job) : undefined}
              >
                <StatusBadge status={job.assignment.driverStatus} />
              </span>
            ) : "\u2014"}
          </TableCell>
        );
      case "repStatus":
        return (
          <TableCell key={key}>
            {job.assignment?.repStatus ? (
              <span
                data-no-show={job.assignment.repStatus === "NO_SHOW" ? "true" : undefined}
                className={job.assignment.repStatus === "NO_SHOW" ? "cursor-pointer hover:underline" : ""}
                onClick={job.assignment.repStatus === "NO_SHOW" ? () => openEvidenceDialog(job) : undefined}
              >
                <StatusBadge status={job.assignment.repStatus} />
              </span>
            ) : "\u2014"}
          </TableCell>
        );
      case "vehicleType":
        return <TableCell key={key} className="text-muted-foreground text-xs whitespace-nowrap">{job.requestedVehicleType?.name || "\u2014"}</TableCell>;
      case "transferPrice":
        return (
          <TableCell key={key} className="text-muted-foreground text-xs whitespace-nowrap font-mono font-medium">
            {job.transferPrice ? `${job.transferPrice} ${job.transferPriceCurrency}` : "\u2014"}
          </TableCell>
        );
      case "collection":
        return (
          <TableCell key={key} className="text-muted-foreground text-xs whitespace-nowrap font-mono font-medium">
            {job.collectionRequired && job.collectionAmount ? `${job.collectionAmount} ${job.collectionCurrency}` : "\u2014"}
          </TableCell>
        );
      case "assignment":
        return (
          <TableCell key={key} className="text-xs text-muted-foreground whitespace-nowrap">
            {job.assignment ? (
              <span>
                {job.assignment.vehicle?.plateNumber || "\u2014"}
                {job.assignment.driver && ` / ${job.assignment.driver.name}`}
                {job.assignment.rep && ` / ${job.assignment.rep.name}`}
              </span>
            ) : t("dispatch.unassigned")}
          </TableCell>
        );
      case "custRep":
        return (
          <TableCell key={key} className="text-xs text-muted-foreground whitespace-nowrap">
            {job.custRepName ? `${job.custRepName}${job.custRepMobile ? ` (${job.custRepMobile})` : ""}` : "\u2014"}
          </TableCell>
        );
      case "userLog":
        return <TableCell key={key} className="text-xs text-muted-foreground whitespace-nowrap">{job.createdBy?.name || "\u2014"}</TableCell>;
      case "flightDelay":
        return (
          <TableCell key={key}>
            <button
              data-no-show="true"
              onClick={() => openFlightDelayModal(job)}
              className="flex items-center gap-1 text-xs text-amber-600 dark:text-amber-400 hover:underline whitespace-nowrap"
            >
              <AlertTriangle className="h-3 w-3" />
              Flight Delay
            </button>
          </TableCell>
        );
      default:
        return <TableCell key={key} />;
    }
  };

  return (
    <div className="space-y-6 animate-in fade-in duration-300">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold text-foreground">{t("jobs.title")}</h1>
          <p className="mt-1 text-sm text-muted-foreground">{t("jobs.description")}</p>
        </div>
        <div className="flex items-center gap-2">
          {canPrintSigns && (
            <Button
              size="sm"
              variant="outline"
              className="gap-1.5 border-border"
              onClick={() => setSignModalOpen(true)}
            >
              <Printer className="h-4 w-4" />
              {t("jobs.printSigns")}
            </Button>
          )}
          <Button
            size="sm"
            className="gap-1.5"
            onClick={() => router.push("/dashboard/traffic-jobs/online")}
          >
            <Plus className="h-4 w-4" />
            {t("jobs.newOnlineJob")}
          </Button>
          <Button
            size="sm"
            variant="outline"
            className="gap-1.5 border-border"
            onClick={() => router.push("/dashboard/traffic-jobs/b2b")}
          >
            <Plus className="h-4 w-4" />
            {t("jobs.newB2BJob")}
          </Button>
        </div>
      </div>

      {/* Filters */}
      <div className="flex items-center gap-3">
        <div className="relative flex-1 max-w-sm">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground/60" />
          <Input
            placeholder={t("jobs.searchPlaceholder")}
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="border-border bg-card pl-9 text-foreground placeholder:text-muted-foreground"
          />
        </div>
        <div className="flex items-center gap-2">
          <Filter className="h-4 w-4 text-muted-foreground" />
          <Select value={filterStatus} onValueChange={(v) => { setFilterStatus(v); setPage(1); }}>
            <SelectTrigger className="w-36 border-border bg-card text-foreground">
              <SelectValue />
            </SelectTrigger>
            <SelectContent className="border-border bg-popover text-foreground">
              <SelectItem value="ALL">{t("jobs.allStatus")}</SelectItem>
              <SelectItem value="PENDING">{t("jobs.pending")}</SelectItem>
              <SelectItem value="ASSIGNED">{t("jobs.assigned")}</SelectItem>
              <SelectItem value="IN_PROGRESS">{t("jobs.inProgress")}</SelectItem>
              <SelectItem value="COMPLETED">{t("jobs.completed")}</SelectItem>
              <SelectItem value="CANCELLED">{t("jobs.cancelled")}</SelectItem>
              <SelectItem value="NO_SHOW">{t("jobs.noShow")}</SelectItem>
            </SelectContent>
          </Select>
        </div>
        <div className="ml-auto">
          <ColumnVisibilityControl
            columns={columnDefs}
            visibility={visibility}
            onSave={saveVisibility}
          />
        </div>
      </div>

      {/* Table */}
      <div>
        {loading ? (
          <div className="overflow-x-auto [overflow-y:clip]">
            <table className="w-full text-sm">
              <tbody>
                {Array.from({ length: 9 }).map((_, i) => (
                  <tr key={i} className={`border-b border-border ${i % 2 === 0 ? "bg-gray-100/25 dark:bg-gray-800/25" : "bg-gray-200/50 dark:bg-gray-700/50"}`}>
                    <td className="px-3 py-2.5"><Skeleton className="h-3 w-20" /></td>
                    <td className="px-3 py-2.5"><Skeleton className="h-3 w-24" /></td>
                    <td className="px-3 py-2.5"><Skeleton className="h-5 w-14 rounded-full" /></td>
                    <td className="px-3 py-2.5"><Skeleton className="h-5 w-12 rounded-full" /></td>
                    <td className="px-3 py-2.5"><Skeleton className="h-3 w-20" /></td>
                    <td className="px-3 py-2.5"><Skeleton className="h-3 w-12" /></td>
                    <td className="px-3 py-2.5"><Skeleton className="h-3 w-28" /></td>
                    <td className="px-3 py-2.5"><Skeleton className="h-3 w-24" /></td>
                    <td className="px-3 py-2.5"><Skeleton className="h-3 w-20" /></td>
                    <td className="px-3 py-2.5"><Skeleton className="h-3 w-6" /></td>
                    <td className="px-3 py-2.5"><Skeleton className="h-3 w-6" /></td>
                    <td className="px-3 py-2.5"><Skeleton className="h-3 w-16" /></td>
                    <td className="px-3 py-2.5"><Skeleton className="h-3 w-16" /></td>
                    <td className="px-3 py-2.5"><Skeleton className="h-3 w-16" /></td>
                    <td className="px-3 py-2.5"><Skeleton className="h-3 w-8" /></td>
                    <td className="px-3 py-2.5"><Skeleton className="h-3 w-10" /></td>
                    <td className="px-3 py-2.5"><Skeleton className="h-3 w-10" /></td>
                    <td className="px-3 py-2.5"><Skeleton className="h-3 w-14" /></td>
                    <td className="px-3 py-2.5"><Skeleton className="h-3 w-14" /></td>
                    <td className="px-3 py-2.5"><Skeleton className="h-3 w-6" /></td>
                    <td className="px-3 py-2.5"><Skeleton className="h-3 w-20" /></td>
                    <td className="px-3 py-2.5"><Skeleton className="h-5 w-20 rounded-full" /></td>
                    <td className="px-3 py-2.5"><Skeleton className="h-5 w-20 rounded-full" /></td>
                    <td className="px-3 py-2.5"><Skeleton className="h-5 w-16 rounded-full" /></td>
                    <td className="px-3 py-2.5"><Skeleton className="h-5 w-16 rounded-full" /></td>
                    <td className="px-3 py-2.5"><Skeleton className="h-3 w-14" /></td>
                    <td className="px-3 py-2.5"><Skeleton className="h-3 w-16" /></td>
                    <td className="px-3 py-2.5"><Skeleton className="h-3 w-16" /></td>
                    <td className="px-3 py-2.5"><Skeleton className="h-3 w-28" /></td>
                    <td className="px-3 py-2.5"><Skeleton className="h-3 w-20" /></td>
                    <td className="px-3 py-2.5"><Skeleton className="h-3 w-16" /></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : filtered.length === 0 ? (
          <div className="py-16">
            <EmptyState
              icon={PlaneLanding}
              heading="No jobs found"
              description="Try adjusting your date range or filters."
            />
          </div>
        ) : (
          <div className="overflow-x-auto [overflow-y:clip]">
          <Table>
            <DraggableTableHeader
              columns={columnDefs}
              columnOrder={columnOrder}
              onReorder={reorder}
              rowClassName="border-border bg-muted"
              visibility={visibility}
            />
            <TableBody>
              {sortedData.map((job, idx) => (
                <TableRow
                  key={job.id}
                  className={`border-border cursor-pointer transition-colors hover:bg-primary/10 ${idx % 2 === 0 ? "bg-gray-100/25 dark:bg-gray-800/25" : "bg-gray-200/50 dark:bg-gray-700/50"}`}
                  onClick={(e) => {
                    if ((e.target as HTMLElement).closest("[data-no-show]")) return;
                    router.push(`/dashboard/traffic-jobs/${job.bookingChannel === "B2B" ? "b2b" : "online"}?edit=${job.id}`);
                  }}
                >
                  {columnOrder.filter((key) => visibility[key] !== false).map((key) => renderCell(key, job))}
                </TableRow>
              ))}
            </TableBody>
          </Table>
          </div>
        )}

        {/* Pagination */}
        {!loading && totalPages > 0 && (
          <div className="flex items-center justify-between pt-4">
            <p className="text-sm text-muted-foreground">
              {t("common.showing") || "Showing"} {filtered.length} of {total} {t("jobs.title")?.toLowerCase() || "jobs"}
            </p>
            <div className="flex items-center gap-2">
              <Button
                size="sm"
                variant="outline"
                disabled={page <= 1}
                onClick={() => setPage((p) => Math.max(1, p - 1))}
                className="border-border"
              >
                {t("common.previous") || "Previous"}
              </Button>
              <span className="text-sm text-muted-foreground">
                {page} / {totalPages}
              </span>
              <Button
                size="sm"
                variant="outline"
                disabled={page >= totalPages}
                onClick={() => setPage((p) => p + 1)}
                className="border-border"
              >
                {t("common.next") || "Next"}
              </Button>
            </div>
          </div>
        )}
      </div>

      {/* Print Signs Date Modal */}
      <Dialog open={signModalOpen} onOpenChange={setSignModalOpen}>
        <DialogContent className="sm:max-w-sm">
          <DialogHeader>
            <DialogTitle>{t("jobs.printSigns")}</DialogTitle>
          </DialogHeader>
          <div className="space-y-3 py-2">
            <div className="space-y-1.5">
              <Label className="text-muted-foreground text-sm">{t("jobs.selectDateForSigns")}</Label>
              <Input
                type="date"
                value={signDate}
                onChange={(e) => setSignDate(e.target.value)}
                className="border-border bg-card text-foreground"
              />
            </div>
          </div>
          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => setSignModalOpen(false)}
              className="border-border"
            >
              {t("common.cancel") || "Cancel"}
            </Button>
            <Button
              onClick={handlePrintSigns}
              disabled={generatingSigns || !signDate}
              className="gap-1.5"
            >
              {generatingSigns ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <Printer className="h-4 w-4" />
              )}
              {generatingSigns ? t("jobs.generatingSigns") : t("jobs.printSigns")}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Flight Delay Modal */}
      <Dialog open={flightDelayModalOpen} onOpenChange={setFlightDelayModalOpen}>
        <DialogContent className="sm:max-w-2xl">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <AlertTriangle className="h-4 w-4 text-amber-500" />
              Flight Delay History — {flightDelayModalRef}
            </DialogTitle>
          </DialogHeader>
          <div className="py-2 max-h-[60vh] overflow-y-auto">
            {flightDelayModalLoading && (
              <div className="flex items-center justify-center py-8 gap-2 text-sm text-muted-foreground">
                <Loader2 className="h-4 w-4 animate-spin" /> Loading…
              </div>
            )}
            {!flightDelayModalLoading && flightDelayEvents.length === 0 && (
              <p className="text-center text-sm text-muted-foreground py-8">No flight delays recorded for this job.</p>
            )}
            {!flightDelayModalLoading && flightDelayEvents.length > 0 && (
              <Table>
                <TableHeader>
                  <TableRow className="border-border bg-muted">
                    <TableHead className="text-xs">Old Arr. Date</TableHead>
                    <TableHead className="text-xs">Old Arr. Time</TableHead>
                    <TableHead className="text-xs text-amber-600 dark:text-amber-400">New Arr. Date</TableHead>
                    <TableHead className="text-xs text-amber-600 dark:text-amber-400">New Arr. Time</TableHead>
                    <TableHead className="text-xs">Reported By</TableHead>
                    <TableHead className="text-xs">Current Rep</TableHead>
                    <TableHead className="text-xs">Reported At</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {flightDelayEvents.map((ev, i) => (
                    <TableRow key={i} className="border-border hover:bg-muted/30">
                      <TableCell className="text-xs">{ev.oldArrivalDate ? new Date(ev.oldArrivalDate).toLocaleDateString(locale) : "—"}</TableCell>
                      <TableCell className="text-xs font-mono">{ev.oldArrivalTime ?? "—"}</TableCell>
                      <TableCell className="text-xs font-mono text-amber-600 dark:text-amber-400">{new Date(ev.newArrivalDate).toLocaleDateString(locale)}</TableCell>
                      <TableCell className="text-xs font-mono text-amber-600 dark:text-amber-400">{ev.newArrivalTime}</TableCell>
                      <TableCell className="text-sm">{ev.reportedBy}</TableCell>
                      <TableCell className="text-sm">{ev.currentRepName ? <span className="text-blue-600 dark:text-blue-400">{ev.currentRepName}</span> : "—"}</TableCell>
                      <TableCell className="text-xs text-muted-foreground">{new Date(ev.reportedAt).toLocaleString(locale, { timeZone: "Africa/Cairo" })}</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            )}
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setFlightDelayModalOpen(false)} className="border-border">
              Close
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* No-Show Evidence Modal */}
      <Dialog open={!!evidenceJob} onOpenChange={(o) => { if (!o) { setEvidenceJob(null); setEvidenceBlobUrls(new Map()); } }}>
        <DialogContent className="sm:max-w-2xl">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <Image className="h-4 w-4 text-muted-foreground" />
              No-Show Evidence — {evidenceJob?.internalRef}
            </DialogTitle>
          </DialogHeader>
          <div className="space-y-6 py-2 max-h-[70vh] overflow-y-auto">
            {evidenceLoading && (
              <div className="flex items-center justify-center py-6 gap-2 text-sm text-muted-foreground">
                <Loader2 className="h-4 w-4 animate-spin" /> Loading images…
              </div>
            )}
            {!evidenceLoading && (evidenceJob?.noShowEvidence ?? []).length === 0 && (
              <p className="text-center text-sm text-muted-foreground py-6">No evidence submitted yet.</p>
            )}
            {!evidenceLoading && (evidenceJob?.noShowEvidence ?? []).map((ev, i) => {
              const apiBase = process.env.NEXT_PUBLIC_API_URL ?? "";
              return (
              <div key={ev.id} className="rounded-lg border border-border p-4 space-y-3">
                <div className="flex items-center justify-between">
                  <p className="text-sm font-medium text-foreground">
                    Submitted by <span className="text-primary">{ev.submittedBy}</span>
                  </p>
                  <p className="text-xs text-muted-foreground">
                    {new Date(ev.createdAt).toLocaleString(locale, { timeZone: "Africa/Cairo" })}
                  </p>
                </div>
                <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
                  {(ev.imageUrls ?? []).map((url, j) => {
                    const resolvedUrl = isDriveId(url)
                      ? (evidenceBlobUrls.get(url) ?? null)
                      : (url.startsWith("http") ? url : `${apiBase}${url}`);
                    if (!resolvedUrl) return null;
                    return (
                      <a key={j} href={resolvedUrl} target="_blank" rel="noopener noreferrer"
                        className="block overflow-hidden rounded-md border border-border hover:opacity-80 transition-opacity">
                        <img src={resolvedUrl} alt={`Evidence ${i + 1}-${j + 1}`}
                          className="h-40 w-full object-cover" />
                      </a>
                    );
                  })}
                </div>
                <a
                  href={ev.gpsMapLink}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex items-center gap-1.5 text-xs text-blue-500 hover:text-blue-400"
                >
                  <MapPin className="h-3.5 w-3.5" />
                  GPS: {Number(ev.gpsLatitude).toFixed(6)}, {Number(ev.gpsLongitude).toFixed(6)}
                  <ExternalLink className="h-3 w-3" />
                </a>
              </div>
              );
            })}
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setEvidenceJob(null)} className="border-border">
              Close
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
