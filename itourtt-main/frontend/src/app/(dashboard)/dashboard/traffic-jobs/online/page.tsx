"use client";

import { useEffect, useState, useCallback, useRef } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { toast } from "sonner";
import {
  Briefcase,
  Loader2,
  Search,
  Filter,
  ArrowLeft,
  Save,
  Lock,
  X,
  DollarSign,
} from "lucide-react";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { Checkbox } from "@/components/ui/checkbox";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { LocationCombobox } from "@/components/location-combobox";
import { SearchableCombobox } from "@/components/searchable-combobox";
import { JobExtrasEditor, type JobExtra } from "@/components/job-extras-editor";
import api from "@/lib/api";
import { usePermission } from "@/hooks/use-permission";
import { useT, useLocaleId } from "@/lib/i18n";
import { cn, formatDate , localDateStr } from "@/lib/utils";
import { useSortable } from "@/hooks/use-sortable";
import { StatusBadge } from "@/components/ui/status-badge";
import { useColumnPreferences } from "@/hooks/useColumnPreferences";
import { DraggableTableHeader, type ColumnDef } from "@/components/ui/draggable-table-header";
import { ColumnVisibilityControl } from "@/components/ui/column-visibility-control";
import { ChevronUp, ChevronDown } from "lucide-react";
import { SERVICE_TYPE_DROPDOWN_OPTIONS, useServiceTypeLabel } from "@/lib/service-types";

/* ─────────── types ─────────── */

interface Agent {
  id: string;
  legalName: string;
  currency?: string | null;
  refPattern?: string | null;
  refExample?: string | null;
}

interface VehicleType {
  id: string;
  name: string;
  seatCapacity: number;
}

interface TrafficJob {
  id: string;
  internalRef: string;
  agentRef: string | null;
  bookingChannel: "ONLINE" | "B2B" | "B2C";
  serviceType: string;
  jobDate: string;
  status: string;
  bookingStatus: string;
  adultCount: number;
  childCount: number;
  paxCount: number;
  clientName: string | null;
  clientMobile: string | null;
  pickUpTime: string | null;
  notes: string | null;
  collectionRequired: boolean;
  collectionAmount: number | null;
  collectionCurrency: string;
  collectionCollected: boolean;
  transferPrice: number | null;
  transferPriceCurrency: string;
  requestedVehicleTypeId: string | null;
  requestedVehicleType?: { id: string; name: string } | null;
  jobExtras: JobExtra[];
  printSign: boolean;
  createdAt: string;
  editUnlockedAt: string | null;
  agentId: string | null;
  originAirportId: string | null;
  originZoneId: string | null;
  originHotelId: string | null;
  destinationAirportId: string | null;
  destinationZoneId: string | null;
  destinationHotelId: string | null;
  agent?: { id: string; legalName: string; tradeName?: string } | null;
  originAirport?: { id: string; name: string; code: string } | null;
  originZone?: { id: string; name: string } | null;
  originHotel?: { id: string; name: string } | null;
  destinationAirport?: { id: string; name: string; code: string } | null;
  destinationZone?: { id: string; name: string } | null;
  destinationHotel?: { id: string; name: string } | null;
  fromZone?: { name: string } | null;
  toZone?: { name: string } | null;
  jobServiceTypeId?: string | null;
  flight?: { flightNo: string; carrier?: string; terminal?: string; arrivalTime?: string; departureTime?: string } | null;
  assignment?: {
    vehicle?: { plateNumber: string };
    driver?: { name: string };
    rep?: { name: string };
  } | null;
}


function isJobLocked(jobDate: string, editUnlockedAt?: string | null): boolean {
  if (editUnlockedAt) return false; // explicitly unlocked
  const serviceDate = new Date(jobDate);
  const oneWeekLater = new Date(serviceDate.getTime() + 7 * 24 * 60 * 60 * 1000);
  return new Date() > oneWeekLater;
}

/* ─────────── form state ─────────── */

interface FormState {
  bookingStatus: string;
  agentId: string;
  agentRef: string;
  serviceType: string;
  jobServiceTypeId: string;
  jobDate: string;
  adultCount: string;
  childCount: string;
  originAirportId: string;
  originZoneId: string;
  originHotelId: string;
  destinationAirportId: string;
  destinationZoneId: string;
  destinationHotelId: string;
  originSelectedId: string;
  destinationSelectedId: string;
  clientName: string;
  clientMobile: string;
  extras: JobExtra[];
  pickUpTime: string;
  notes: string;
  collectionRequired: boolean;
  collectionAmount: string;
  collectionCurrency: string;
  transferPrice: string;
  transferPriceCurrency: string;
  requestedVehicleTypeId: string;
  flightNo: string;
  terminal: string;
  arrivalTime: string;
  departureTime: string;
}

const defaultForm: FormState = {
  bookingStatus: "NEW",
  agentId: "",
  agentRef: "",
  serviceType: "ARR",
  jobServiceTypeId: "",
  jobDate: localDateStr(new Date()),
  adultCount: "1",
  childCount: "0",
  originAirportId: "",
  originZoneId: "",
  originHotelId: "",
  destinationAirportId: "",
  destinationZoneId: "",
  destinationHotelId: "",
  originSelectedId: "",
  destinationSelectedId: "",
  clientName: "",
  clientMobile: "",
  extras: [],
  pickUpTime: "",
  notes: "",
  collectionRequired: false,
  collectionAmount: "",
  collectionCurrency: "EGP",
  transferPrice: "",
  transferPriceCurrency: "EGP",
  requestedVehicleTypeId: "",
  flightNo: "",
  terminal: "",
  arrivalTime: "",
  departureTime: "",
};

/* ─────────── component ─────────── */

export default function OnlineJobPage() {
  const t = useT();
  const locale = useLocaleId();
  const router = useRouter();
  const canEditVehicleType = usePermission("traffic-jobs.online.form.requestedVehicleType");
  const canCreate = usePermission("traffic-jobs.online.createJob");
  const canProvider = usePermission("traffic-jobs.online.form.provider");
  const canAgentRef = usePermission("traffic-jobs.online.form.agentRef");
  const canServiceType = usePermission("traffic-jobs.online.form.serviceType");
  const canDateTime = usePermission("traffic-jobs.online.form.dateTime");
  const canClientInfo = usePermission("traffic-jobs.online.form.clientInfo");
  const canPaxCount = usePermission("traffic-jobs.online.form.paxCount");
  const canRoute = usePermission("traffic-jobs.online.form.route");
  const canFlightInfo = usePermission("traffic-jobs.online.form.flightInfo");
  const canExtras = usePermission("traffic-jobs.online.form.extras");
  const canNotes = usePermission("traffic-jobs.online.form.notes");
  const canStatusFilter = usePermission("traffic-jobs.online.table.statusFilter");
  const searchParams = useSearchParams();
  const editParam = searchParams.get("edit");
  const formRef = useRef<HTMLDivElement>(null);
  const autoEditLoadedRef = useRef(false);

  const [agents, setAgents] = useState<Agent[]>([]);
  const [vehicleTypes, setVehicleTypes] = useState<VehicleType[]>([]);
  const [jobServiceTypes, setJobServiceTypes] = useState<{ id: string; name: string }[]>([]);
  const [jobs, setJobs] = useState<TrafficJob[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [filterStatus, setFilterStatus] = useState<string>("ALL");
  const [filterBookingStatus, setFilterBookingStatus] = useState<string>("ALL");
  const [search, setSearch] = useState("");
  const [debouncedSearch, setDebouncedSearch] = useState("");
  const [form, setForm] = useState<FormState>({ ...defaultForm });
  const [editingJobId, setEditingJobId] = useState<string | null>(null);
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [total, setTotal] = useState(0);
  const limit = 20;

  const serviceTypeLabel = useServiceTypeLabel();

  const updateForm = useCallback((updates: Partial<FormState>) => {
    setForm((prev) => ({ ...prev, ...updates }));
  }, []);

  /* ── Fetch agents + vehicle types ── */
  useEffect(() => {
    async function fetchAgents() {
      try {
        const { data } = await api.get("/agents");
        setAgents(Array.isArray(data) ? data : data.data || []);
      } catch {
        /* non-critical */
      }
    }
    async function fetchVehicleTypes() {
      try {
        const { data } = await api.get("/vehicles/types");
        setVehicleTypes(Array.isArray(data) ? data : data.data || []);
      } catch {
        /* non-critical */
      }
    }
    async function fetchJobServiceTypes() {
      try {
        const { data } = await api.get("/job-service-types");
        setJobServiceTypes(Array.isArray(data) ? data : data.data || []);
      } catch { /* non-critical */ }
    }
    fetchAgents();
    fetchVehicleTypes();
    fetchJobServiceTypes();
  }, []);

  /* ── Debounce search ── */
  useEffect(() => {
    const timer = setTimeout(() => {
      setDebouncedSearch(search);
      setPage(1);
    }, 400);
    return () => clearTimeout(timer);
  }, [search]);

  /* ── Fetch ONLINE jobs ── */
  const fetchJobs = useCallback(async () => {
    try {
      setLoading(true);
      const params: Record<string, string> = {
        bookingChannel: "ONLINE,B2C",
        page: String(page),
        limit: String(limit),
      };
      if (filterStatus !== "ALL") params.status = filterStatus;
      if (debouncedSearch.trim()) params.search = debouncedSearch.trim();
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
  }, [filterStatus, page, debouncedSearch]);

  useEffect(() => {
    fetchJobs();
  }, [fetchJobs]);

  /* ── Auto-open edit form when ?edit=<id> is in the URL ── */
  useEffect(() => {
    if (!editParam || autoEditLoadedRef.current) return;
    autoEditLoadedRef.current = true;
    api.get(`/traffic-jobs/${editParam}`)
      .then(({ data }) => {
        handleSelectJob(data);
        setTimeout(() => formRef.current?.scrollIntoView({ behavior: "smooth", block: "start" }), 100);
      })
      .catch(() => toast.error("Job not found"));
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [editParam]);

  /* ── Select job for editing ── */
  const handleSelectJob = (job: TrafficJob) => {
    if (isJobLocked(job.jobDate, job.editUnlockedAt)) return;

    setEditingJobId(job.id);

    // A job must carry exactly one origin and one destination FK. Legacy B2C jobs
    // may have both a zone and a hotel set; collapse to the most specific node
    // (airport → hotel → zone) so the form never re-submits a conflicting pair.
    const originAirportId = job.originAirportId || job.originAirport?.id || "";
    const originHotelId = originAirportId ? "" : (job.originHotelId || job.originHotel?.id || "");
    const originZoneId = originAirportId || originHotelId ? "" : (job.originZoneId || job.originZone?.id || "");
    const destinationAirportId = job.destinationAirportId || job.destinationAirport?.id || "";
    const destinationHotelId = destinationAirportId ? "" : (job.destinationHotelId || job.destinationHotel?.id || "");
    const destinationZoneId = destinationAirportId || destinationHotelId ? "" : (job.destinationZoneId || job.destinationZone?.id || "");

    const originSelectedId = originAirportId || originHotelId || originZoneId || "";
    const destinationSelectedId = destinationAirportId || destinationHotelId || destinationZoneId || "";

    const pickUpTime = job.pickUpTime ? new Date(job.pickUpTime).toLocaleTimeString("en-GB", { timeZone: "Africa/Cairo", hour: "2-digit", minute: "2-digit", hour12: false }) : "";
    const arrivalTime = job.flight?.arrivalTime ? new Date(job.flight.arrivalTime).toLocaleTimeString("en-GB", { timeZone: "Africa/Cairo", hour: "2-digit", minute: "2-digit", hour12: false }) : "";
    const departureTime = job.flight?.departureTime ? new Date(job.flight.departureTime).toLocaleTimeString("en-GB", { timeZone: "Africa/Cairo", hour: "2-digit", minute: "2-digit", hour12: false }) : "";

    setForm({
      bookingStatus: "UPDATED",
      agentId: job.agentId || (job.agent as any)?.id || "",
      agentRef: job.agentRef || "",
      serviceType: job.serviceType,
      jobDate: job.jobDate?.split("T")[0] || "",
      adultCount: String(job.adultCount),
      childCount: String(job.childCount),
      originAirportId,
      originZoneId,
      originHotelId,
      destinationAirportId,
      destinationZoneId,
      destinationHotelId,
      originSelectedId,
      destinationSelectedId,
      clientName: job.clientName || "",
      clientMobile: job.clientMobile || "",
      extras: (job.jobExtras || []).map((e) => ({
        id: e.id,
        extraId: e.extraId ?? null,
        name: e.name,
        qty: Number(e.qty),
        unitAmount: Number(e.unitAmount),
        currency: e.currency,
        source: e.source,
      })),
      pickUpTime,
      notes: job.notes || "",
      collectionRequired: job.collectionRequired || false,
      collectionAmount: job.collectionAmount ? String(job.collectionAmount) : "",
      collectionCurrency: job.collectionCurrency || "EGP",
      transferPrice: job.transferPrice ? String(job.transferPrice) : "",
      transferPriceCurrency: job.transferPriceCurrency || "EGP",
      requestedVehicleTypeId: job.requestedVehicleTypeId || job.requestedVehicleType?.id || "",
      jobServiceTypeId: job.jobServiceTypeId || (job as any).jobServiceType?.id || "",
      flightNo: job.flight?.flightNo || "",
      terminal: job.flight?.terminal || "",
      arrivalTime,
      departureTime,
    });
  };

  const handleCancelEdit = () => {
    setEditingJobId(null);
    setForm({ ...defaultForm });
  };

  /* ── Create or Update job ── */
  const handleSave = async () => {
    if (!form.agentId) {
      toast.error(t("jobs.agentRequired"));
      return;
    }
    if (!form.agentRef.trim()) {
      toast.error(t("jobs.agentRefRequired"));
      return;
    }
    if (agentRefInvalid) {
      toast.error(`${t("jobs.agentRefInvalid")} ${selectedAgent?.refExample ? `(${selectedAgent.refExample})` : ""}`);
      return;
    }
    if (!form.clientName.trim()) {
      toast.error(t("jobs.clientNameRequired"));
      return;
    }
    if (!form.clientMobile.trim()) {
      toast.error(t("jobs.clientMobileRequired"));
      return;
    }

    const hasOrigin = form.originAirportId || form.originZoneId || form.originHotelId;
    const hasDest = form.destinationAirportId || form.destinationZoneId || form.destinationHotelId;
    if (!hasOrigin || !hasDest) {
      toast.error(t("jobs.originDestRequired"));
      return;
    }

    setSaving(true);
    try {
      const payload: Record<string, unknown> = {
        bookingChannel: "ONLINE",
        agentId: form.agentId,
        agentRef: form.agentRef.trim(),
        serviceType: form.serviceType,
        jobDate: form.jobDate,
        adultCount: parseInt(form.adultCount) || 1,
        childCount: parseInt(form.childCount) || 0,
        bookingStatus: form.bookingStatus,
      };

      if (form.originAirportId) payload.originAirportId = form.originAirportId;
      if (form.originZoneId) payload.originZoneId = form.originZoneId;
      if (form.originHotelId) payload.originHotelId = form.originHotelId;
      if (form.destinationAirportId) payload.destinationAirportId = form.destinationAirportId;
      if (form.destinationZoneId) payload.destinationZoneId = form.destinationZoneId;
      if (form.destinationHotelId) payload.destinationHotelId = form.destinationHotelId;

      payload.clientName = form.clientName.trim();
      payload.clientMobile = form.clientMobile.trim();
      payload.extras = form.extras
        .filter((e) => e.name && e.qty > 0)
        .map((e) => ({
          extraId: e.extraId ?? undefined,
          name: e.name,
          qty: e.qty,
          unitAmount: e.unitAmount,
          currency: e.currency,
          source: e.source,
        }));
      payload.printSign = form.serviceType === "ARR";

      payload.collectionRequired = form.collectionRequired;
      if (form.collectionRequired) {
        const collectionAmt = parseFloat(form.collectionAmount);
        if (!collectionAmt || collectionAmt <= 0) {
          toast.error(t("jobs.collectionAmountRequired") || "Collection amount is required");
          setSaving(false);
          return;
        }
        payload.collectionAmount = collectionAmt;
        payload.collectionCurrency = form.collectionCurrency;
      }

      const transferAmt = parseFloat(form.transferPrice);
      if (transferAmt > 0) {
        payload.transferPrice = transferAmt;
        payload.transferPriceCurrency = form.transferPriceCurrency;
      }
      if (form.requestedVehicleTypeId) {
        payload.requestedVehicleTypeId = form.requestedVehicleTypeId;
      }
      if (form.jobServiceTypeId) payload.jobServiceTypeId = form.jobServiceTypeId;

      if (form.pickUpTime) payload.pickUpTime = `${form.jobDate}T${form.pickUpTime}`;
      if (form.notes.trim()) payload.notes = form.notes.trim();

      const showFlight = form.serviceType === "ARR" || form.serviceType === "DEP";
      const relevantFlightTime = form.serviceType === "ARR" ? form.arrivalTime : form.departureTime;
      if (showFlight && (form.flightNo || form.terminal || relevantFlightTime)) {
        payload.flight = {
          flightNo: form.flightNo || "TBD",
          ...(form.terminal && { terminal: form.terminal }),
          // Only persist the flight time that matches the service type so a stale
          // arrival/departure value can never leak onto the wrong job type.
          ...(form.serviceType === "ARR" && form.arrivalTime && { arrivalTime: `${form.jobDate}T${form.arrivalTime}` }),
          ...(form.serviceType === "DEP" && form.departureTime && { departureTime: `${form.jobDate}T${form.departureTime}` }),
        };
      }

      if (editingJobId) {
        const { bookingChannel, ...updatePayload } = payload;
        await api.patch(`/traffic-jobs/${editingJobId}`, updatePayload);
        // When booking is cancelled, also cancel the operational job status
        if (form.bookingStatus === "CANCELLED") {
          try {
            await api.patch(`/traffic-jobs/${editingJobId}/status`, { status: "CANCELLED" });
          } catch {
            // Job may already be in a terminal state — booking status still saved
          }
        }
        toast.success(t("jobs.updated") || "Job updated successfully");
      } else {
        const { bookingStatus, ...createPayload } = payload;
        await api.post("/traffic-jobs", createPayload);
        toast.success(t("jobs.created"));
      }

      setEditingJobId(null);
      setForm({ ...defaultForm });
      fetchJobs();
    } catch (err: unknown) {
      const msg =
        err && typeof err === "object" && "response" in err
          ? (err as { response?: { data?: { message?: string } } }).response?.data?.message || t("jobs.failedCreate")
          : t("jobs.failedCreate");
      toast.error(msg);
    } finally {
      setSaving(false);
    }
  };

  const filtered = jobs.filter((j) => {
    if (filterBookingStatus !== "ALL" && j.bookingStatus !== filterBookingStatus) return false;
    return true;
  });

  const { sortedData, sortKey, sortDir, onSort } = useSortable(filtered);
  const showFlightFields = form.serviceType === "ARR" || form.serviceType === "DEP";

  // ── Draggable column order ──
  const ONLINE_DEFAULT_COLS = [
    "internalRef", "agentRef", "serviceType", "jobDate", "pickUpTime", "arrivalTime",
    "agent", "clientName", "route", "pax",
    "extras", "collectionAmt", "collectionCur", "transferPrice", "transferCur",
    "vehicleType", "notes", "bookingStatus", "status", "assignment",
  ];
  const { columns: onlineColumnOrder, reorder: onlineReorder, visibility: onlineVisibility, saveVisibility: onlineSaveVisibility } = useColumnPreferences("traffic_jobs_online", ONLINE_DEFAULT_COLS);

  const sortBtn = (label: string, key: string) => (
    <button onClick={() => onSort(key)} className="flex items-center gap-0.5 text-xs font-medium text-muted-foreground hover:text-foreground">
      {label}
      {sortKey === key && (sortDir === "asc" ? <ChevronUp className="h-3 w-3" /> : <ChevronDown className="h-3 w-3" />)}
    </button>
  );
  const th = (label: string) => <span className="text-xs font-medium text-muted-foreground">{label}</span>;

  const onlineColumnDefs: ColumnDef[] = [
    { key: "internalRef",    label: sortBtn(t("dispatch.ref"), "internalRef") },
    { key: "agentRef",       label: sortBtn(t("jobs.agentRef"), "agentRef") },
    { key: "serviceType",    label: sortBtn(t("jobs.type"), "serviceType") },
    { key: "jobDate",        label: sortBtn(t("common.date"), "jobDate") },
    { key: "pickUpTime",     label: sortBtn(t("jobs.pickUpTime"), "pickUpTime") },
    { key: "arrivalTime",    label: th(t("jobs.arrivalTime")) },
    { key: "agent",          label: sortBtn(t("jobs.transferProvider"), "agent.legalName") },
    { key: "clientName",     label: sortBtn(t("jobs.clientName"), "clientName") },
    { key: "route",          label: th(t("dispatch.route")) },
    { key: "pax",            label: sortBtn(t("dispatch.pax"), "paxCount") },
    { key: "extras",         label: th(t("jobs.extras") || "Extras") },
    { key: "collectionAmt",  label: th("Coll. Amt"), className: "w-[70px]" },
    { key: "collectionCur",  label: th("Coll. Cur"), className: "w-[60px]" },
    { key: "transferPrice",  label: th("Tr. Price"), className: "w-[70px]" },
    { key: "transferCur",    label: th("Tr. Cur"), className: "w-[60px]" },
    { key: "vehicleType",    label: th("Veh. Type") },
    { key: "notes",          label: th(t("jobs.notes") || "Notes") },
    { key: "bookingStatus",  label: th(t("jobs.bookingStatus") || "Booking") },
    { key: "status",         label: sortBtn(t("common.status"), "status") },
    { key: "assignment",     label: th(t("jobs.assignment")) },
  ];

  const renderOnlineCell = (key: string, job: TrafficJob, locked: boolean): React.ReactNode => {
    switch (key) {
      case "internalRef":
        return (
          <TableCell key={key} className="text-foreground font-mono text-xs">
            <div className="flex items-center gap-1.5">
              {locked && <Lock className="h-3.5 w-3.5 text-muted-foreground/60 shrink-0" />}
              {job.internalRef}
            </div>
          </TableCell>
        );
      case "agentRef":
        return <TableCell key={key} className="text-muted-foreground text-xs">{job.agentRef || "\u2014"}</TableCell>;
      case "serviceType":
        return (
          <TableCell key={key}>
            <Badge variant="outline" className="border-border text-muted-foreground text-xs">
              {serviceTypeLabel(job.serviceType)}
            </Badge>
          </TableCell>
        );
      case "jobDate":
        return <TableCell key={key} className="text-muted-foreground text-xs">{formatDate(job.jobDate)}</TableCell>;
      case "pickUpTime":
        return (
          <TableCell key={key} className="text-muted-foreground text-xs whitespace-nowrap">
            {job.pickUpTime ? new Date(job.pickUpTime).toLocaleTimeString(locale, { timeZone: "Africa/Cairo", hour: "2-digit", minute: "2-digit", hour12: false }) : "\u2014"}
          </TableCell>
        );
      case "arrivalTime":
        return (
          <TableCell key={key} className="text-muted-foreground text-xs whitespace-nowrap">
            {job.flight?.arrivalTime ? new Date(job.flight.arrivalTime).toLocaleTimeString(locale, { timeZone: "Africa/Cairo", hour: "2-digit", minute: "2-digit", hour12: false }) : "\u2014"}
          </TableCell>
        );
      case "agent":
        return <TableCell key={key} className="text-muted-foreground text-xs">{job.agent?.legalName || "\u2014"}</TableCell>;
      case "clientName":
        return <TableCell key={key} className="text-muted-foreground text-xs">{job.clientName || "\u2014"}</TableCell>;
      case "route":
        return (
          <TableCell key={key} className="text-muted-foreground text-xs">
            {job.originAirport?.code || job.fromZone?.name || job.originZone?.name || job.originHotel?.name || "\u2014"} &rarr; {job.destinationAirport?.code || job.toZone?.name || job.destinationZone?.name || job.destinationHotel?.name || "\u2014"}
          </TableCell>
        );
      case "pax":
        return (
          <TableCell key={key} className="text-muted-foreground text-xs">
            {job.paxCount}
            <span className="ml-1 text-muted-foreground/60">({job.adultCount}A{job.childCount > 0 && `+${job.childCount}C`})</span>
          </TableCell>
        );
      case "extras": {
        const extras = (job.jobExtras || [])
          .filter((e) => e.qty > 0)
          .map((e) => `${e.name} \u00d7${e.qty}`);
        return <TableCell key={key} className="text-muted-foreground text-xs">{extras.length > 0 ? extras.join(", ") : "\u2014"}</TableCell>;
      }
      case "collectionAmt":
        return (
          <TableCell key={key} className="text-muted-foreground text-xs text-center">
            {job.collectionRequired && job.collectionAmount ? <span className="text-amber-500">{job.collectionAmount}</span> : "\u2014"}
          </TableCell>
        );
      case "collectionCur":
        return (
          <TableCell key={key} className="text-muted-foreground text-xs text-center">
            {job.collectionRequired ? <span className="text-amber-500">{job.collectionCurrency}</span> : "\u2014"}
          </TableCell>
        );
      case "transferPrice":
        return (
          <TableCell key={key} className="text-muted-foreground text-xs text-center">
            {job.transferPrice ? <span className="text-sky-500">{job.transferPrice}</span> : "\u2014"}
          </TableCell>
        );
      case "transferCur":
        return (
          <TableCell key={key} className="text-muted-foreground text-xs text-center">
            {job.transferPrice ? <span className="text-sky-500">{job.transferPriceCurrency}</span> : "\u2014"}
          </TableCell>
        );
      case "vehicleType":
        return <TableCell key={key} className="text-muted-foreground text-xs whitespace-nowrap">{job.requestedVehicleType?.name || "\u2014"}</TableCell>;
      case "notes":
        return (
          <TableCell key={key} className="text-muted-foreground text-xs max-w-[150px] truncate" title={job.notes || ""}>
            {job.notes || "\u2014"}
          </TableCell>
        );
      case "bookingStatus":
        return <TableCell key={key}><StatusBadge status={job.bookingStatus || "NEW"} /></TableCell>;
      case "status":
        return <TableCell key={key}><StatusBadge status={job.status} /></TableCell>;
      case "assignment":
        return (
          <TableCell key={key} className="text-xs text-muted-foreground">
            {job.assignment ? (
              <span>
                {job.assignment.vehicle?.plateNumber || "\u2014"}
                {job.assignment.driver && ` / ${job.assignment.driver.name}`}
              </span>
            ) : t("dispatch.unassigned")}
          </TableCell>
        );
      default:
        return <TableCell key={key} />;
    }
  };
  const selectedAgent = agents.find((a) => a.id === form.agentId);
  const agentRefInvalid = !!(form.agentRef && selectedAgent?.refPattern && (() => { try { return !new RegExp(selectedAgent.refPattern).test(form.agentRef); } catch { return false; } })());

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center gap-3">
        <Button
          variant="ghost"
          size="icon"
          onClick={() => router.push("/dashboard/traffic-jobs")}
          className="text-muted-foreground hover:text-foreground"
        >
          <ArrowLeft className="h-5 w-5" />
        </Button>
        <div>
          <h1 className="text-2xl font-semibold text-foreground">
            {editingJobId ? (t("jobs.editJob") || "Edit Job") : t("jobs.newOnlineJob")}
          </h1>
          <p className="text-sm text-muted-foreground">{t("jobs.onlineDescription")}</p>
        </div>
      </div>

      {/* ─── Inline Form ─── */}
      <Card ref={formRef} className={cn("border-border bg-card flex flex-col", editingJobId && "ring-2 ring-primary/50")}>
        <div className="overflow-y-auto p-4 space-y-4">
          {/* ── Booking Info ── */}
          <div className="flex items-center gap-2 pt-1">
            <span className="text-xs font-medium text-muted-foreground uppercase tracking-wide whitespace-nowrap">Booking Info</span>
            <hr className="flex-1 border-border" />
          </div>

          {/* Line 1: Booking Status + Transfer Provider + Agent Ref + Service Type + Service Date + Pickup Time */}
          <div className="grid grid-cols-6 gap-3">
            <div className="min-w-0 space-y-1.5">
              <Label className="text-muted-foreground text-xs">{t("jobs.bookingStatus") || "Booking Status"}</Label>
              <Select value={form.bookingStatus} onValueChange={(v) => updateForm({ bookingStatus: v })}>
                <SelectTrigger className="w-full border-border bg-card text-foreground h-9 min-w-0">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent className="border-border bg-popover text-foreground">
                  {!editingJobId && <SelectItem value="NEW">{t("jobs.bookingNew") || "New"}</SelectItem>}
                  <SelectItem value="UPDATED">{t("jobs.bookingUpdated") || "Updated"}</SelectItem>
                  <SelectItem value="CANCELLED">{t("jobs.bookingCancelled") || "Cancelled"}</SelectItem>
                </SelectContent>
              </Select>
            </div>
            {canProvider && (
            <div className="min-w-0 space-y-1.5">
              <Label className="text-muted-foreground text-xs">{t("jobs.transferProvider")} *</Label>
              <Select value={form.agentId} onValueChange={(v) => { const ag = agents.find((a) => a.id === v); updateForm({ agentId: v, agentRef: "", transferPriceCurrency: ag?.currency || "EGP" }); }}>
                <SelectTrigger className="w-full border-border bg-card text-foreground h-9 min-w-0">
                  <SelectValue placeholder={t("jobs.selectAgent")} className="truncate" />
                </SelectTrigger>
                <SelectContent className="border-border bg-popover text-foreground">
                  {agents.map((a) => (
                    <SelectItem key={a.id} value={a.id}>{a.legalName}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            )}
            {canAgentRef && (
            <div className="min-w-0 space-y-1.5">
              <Label className="text-muted-foreground text-xs">{t("jobs.agentRef")} *</Label>
              <Input
                value={form.agentRef}
                onChange={(e) => updateForm({ agentRef: e.target.value })}
                placeholder={selectedAgent?.refExample || t("jobs.agentRefPlaceholder")}
                className={cn(
                  "border-border bg-card text-foreground placeholder:text-muted-foreground h-9",
                  agentRefInvalid && "border-red-500 focus-visible:ring-red-500"
                )}
              />
              {agentRefInvalid && (
                <p className="text-[10px] text-red-500">
                  {t("jobs.agentRefInvalid")} {selectedAgent?.refExample && `(${selectedAgent.refExample})`}
                </p>
              )}
            </div>
            )}
            <div className="min-w-0 space-y-1.5">
              <Label className="text-muted-foreground text-xs">Route / Service Type</Label>
              <SearchableCombobox
                items={jobServiceTypes.map((s) => ({ value: s.id, label: s.name }))}
                value={form.jobServiceTypeId}
                onChange={(v) => updateForm({ jobServiceTypeId: v })}
                placeholder="Select route…"
                searchPlaceholder="Search routes…"
                emptyText="No routes found."
                triggerClassName="border-border bg-card text-foreground h-9"
              />
            </div>
            {canServiceType && (
            <div className="min-w-0 space-y-1.5">
              <Label className="text-muted-foreground text-xs">{t("jobs.serviceType")}</Label>
              <Select
                value={form.serviceType}
                onValueChange={(v) =>
                  // Clear the flight time that no longer applies so a stale arrival/
                  // departure value can't carry over when switching service type.
                  updateForm(
                    v === "ARR"
                      ? { serviceType: v, departureTime: "" }
                      : v === "DEP"
                        ? { serviceType: v, arrivalTime: "" }
                        : { serviceType: v, arrivalTime: "", departureTime: "" },
                  )
                }
              >
                <SelectTrigger className="w-full border-border bg-card text-foreground h-9 min-w-0">
                  <SelectValue className="truncate" />
                </SelectTrigger>
                <SelectContent className="border-border bg-popover text-foreground">
                  {SERVICE_TYPE_DROPDOWN_OPTIONS.map(({ value: key, label }) => (
                    <SelectItem key={key} value={key}>{label}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            )}
            {canDateTime && (
            <>
            <div className="min-w-0 space-y-1.5">
              <Label className="text-muted-foreground text-xs">{t("jobs.serviceDate")}</Label>
              <Input
                type="date"
                value={form.jobDate}
                onChange={(e) => updateForm({ jobDate: e.target.value })}
                min="2020-01-01"
                className="border-border bg-card text-foreground h-9"
              />
            </div>
            {form.serviceType !== "ARR" && (
              <div className="min-w-0 space-y-1.5">
                <Label className="text-muted-foreground text-xs">{t("jobs.pickUpTime")}</Label>
                <Input
                  value={form.pickUpTime}
                  onChange={(e) => {
                    let v = e.target.value.replace(/[^0-9:]/g, "");
                    if (v.length === 2 && !v.includes(":") && form.pickUpTime.length < v.length) v += ":";
                    if (v.length > 5) v = v.slice(0, 5);
                    updateForm({ pickUpTime: v });
                  }}
                  placeholder="HH:MM"
                  maxLength={5}
                  className="border-border bg-card text-foreground placeholder:text-muted-foreground h-9 font-mono"
                />
              </div>
            )}
            </>
            )}
          </div>

          {/* ── Client Info ── */}
          <div className="flex items-center gap-2 pt-1">
            <span className="text-xs font-medium text-muted-foreground uppercase tracking-wide whitespace-nowrap">Client Info</span>
            <hr className="flex-1 border-border" />
          </div>

          {/* Line 2: Client Lead Name + Client Mobile + Adults + Children */}
          <div className="grid grid-cols-4 gap-3">
            {canClientInfo && (
            <>
            <div className="space-y-1.5">
              <Label className="text-muted-foreground text-xs">{t("jobs.clientName")} *</Label>
              <Input
                value={form.clientName}
                onChange={(e) => updateForm({ clientName: e.target.value })}
                placeholder={t("jobs.passengerName")}
                className="border-border bg-card text-foreground placeholder:text-muted-foreground h-9"
              />
            </div>
            <div className="space-y-1.5">
              <Label className="text-muted-foreground text-xs">{t("jobs.clientMobile")} *</Label>
              <Input
                value={form.clientMobile}
                onChange={(e) => updateForm({ clientMobile: e.target.value })}
                placeholder={t("jobs.clientMobilePlaceholder")}
                className="border-border bg-card text-foreground placeholder:text-muted-foreground h-9"
              />
            </div>
            </>
            )}
            {canPaxCount && (
            <>
            <div className="space-y-1.5">
              <Label className="text-muted-foreground text-xs">{t("jobs.adults")}</Label>
              <Input
                type="number"
                min="1"
                value={form.adultCount}
                onChange={(e) => updateForm({ adultCount: e.target.value })}
                className="border-border bg-card text-foreground h-9"
              />
            </div>
            <div className="space-y-1.5">
              <Label className="text-muted-foreground text-xs">{t("jobs.children")}</Label>
              <Input
                type="number"
                min="0"
                value={form.childCount}
                onChange={(e) => updateForm({ childCount: e.target.value })}
                className="border-border bg-card text-foreground h-9"
              />
            </div>
            </>
            )}
          </div>

          {/* ── Route & Flight ── */}
          <div className="flex items-center gap-2 pt-1">
            <span className="text-xs font-medium text-muted-foreground uppercase tracking-wide whitespace-nowrap">Route &amp; Flight</span>
            <hr className="flex-1 border-border" />
          </div>

          {/* Line 3: Origin + Destination + Flight Info */}
          <div className="grid grid-cols-[15.3fr_15.3fr_3.1fr_3.1fr_3.2fr] gap-3">
            {canRoute && (
            <>
            <div className="min-w-0 space-y-1.5">
              <Label className="text-muted-foreground text-xs">{t("jobs.origin")}</Label>
              <LocationCombobox
                value={form.originSelectedId}
                onChange={(id, type) => {
                  const clear = { originAirportId: "", originZoneId: "", originHotelId: "", originSelectedId: id };
                  if (type === "AIRPORT") updateForm({ ...clear, originAirportId: id });
                  else if (type === "ZONE") updateForm({ ...clear, originZoneId: id });
                  else if (type === "HOTEL") updateForm({ ...clear, originHotelId: id });
                }}
                placeholder={t("jobs.searchOrigin")}
              />
            </div>
            <div className="min-w-0 space-y-1.5">
              <Label className="text-muted-foreground text-xs">{t("jobs.destination")}</Label>
              <LocationCombobox
                value={form.destinationSelectedId}
                onChange={(id, type) => {
                  const clear = { destinationAirportId: "", destinationZoneId: "", destinationHotelId: "", destinationSelectedId: id };
                  if (type === "AIRPORT") updateForm({ ...clear, destinationAirportId: id });
                  else if (type === "ZONE") updateForm({ ...clear, destinationZoneId: id });
                  else if (type === "HOTEL") updateForm({ ...clear, destinationHotelId: id });
                }}
                placeholder={t("jobs.searchDestination")}
              />
            </div>
            </>
            )}
            {canFlightInfo && showFlightFields && (
              <>
                <div className="min-w-0 space-y-1.5">
                  <Label className="text-muted-foreground text-xs">{t("jobs.flightNo")}</Label>
                  <Input
                    value={form.flightNo}
                    onChange={(e) => updateForm({ flightNo: e.target.value })}
                    placeholder="e.g. MS800"
                    className="border-border bg-card text-foreground placeholder:text-muted-foreground h-9"
                  />
                </div>
                <div className="min-w-0 space-y-1.5">
                  <Label className="text-muted-foreground text-xs">{t("jobs.terminal")}</Label>
                  <Input
                    value={form.terminal}
                    onChange={(e) => updateForm({ terminal: e.target.value })}
                    placeholder="e.g. T2"
                    className="border-border bg-card text-foreground placeholder:text-muted-foreground h-9"
                  />
                </div>
                {form.serviceType === "ARR" && (
                  <div className="min-w-0 space-y-1.5">
                    <Label className="text-muted-foreground text-xs">{t("jobs.arrivalTime")}</Label>
                    <Input
                      value={form.arrivalTime}
                      onChange={(e) => {
                        let v = e.target.value.replace(/[^0-9:]/g, "");
                        if (v.length === 2 && !v.includes(":") && form.arrivalTime.length < v.length) v += ":";
                        if (v.length > 5) v = v.slice(0, 5);
                        updateForm({ arrivalTime: v });
                      }}
                      placeholder="HH:MM"
                      maxLength={5}
                      className="border-border bg-card text-foreground placeholder:text-muted-foreground h-9 font-mono"
                    />
                  </div>
                )}
                {form.serviceType === "DEP" && (
                  <div className="min-w-0 space-y-1.5">
                    <Label className="text-muted-foreground text-xs">{t("jobs.departureTime")}</Label>
                    <Input
                      value={form.departureTime}
                      onChange={(e) => {
                        let v = e.target.value.replace(/[^0-9:]/g, "");
                        if (v.length === 2 && !v.includes(":") && form.departureTime.length < v.length) v += ":";
                        if (v.length > 5) v = v.slice(0, 5);
                        updateForm({ departureTime: v });
                      }}
                      placeholder="HH:MM"
                      maxLength={5}
                      className="border-border bg-card text-foreground placeholder:text-muted-foreground h-9 font-mono"
                    />
                  </div>
                )}
              </>
            )}
          </div>

          {/* ── Extras & Pricing ── */}
          <div className="flex items-center gap-2 pt-1">
            <span className="text-xs font-medium text-muted-foreground uppercase tracking-wide whitespace-nowrap">Extras &amp; Pricing</span>
            <hr className="flex-1 border-border" />
          </div>

          {/* Line 4: Managed extras + Collection */}
          {canExtras && (
          <div className="space-y-3">
            <div className="grid grid-cols-[2fr_4rem_6rem_5rem_auto] gap-2 px-0.5 text-[10px] font-medium uppercase tracking-wide text-muted-foreground">
              <span>{t("jobs.extras") || "Extras"}</span>
              <span className="text-center">{t("jobs.qty") || "Qty"}</span>
              <span className="text-right">{t("jobs.amount") || "Amount"}</span>
              <span>{t("jobs.currency") || "Cur."}</span>
              <span />
            </div>
            <JobExtrasEditor value={form.extras} onChange={(extras) => updateForm({ extras })} />
            <div className="grid grid-cols-5 gap-3">
            <div className="min-w-0 flex items-center">
              <label className="flex items-center gap-2 text-sm text-foreground">
                <Checkbox
                  checked={form.collectionRequired}
                  onCheckedChange={(v) => updateForm({ collectionRequired: v === true, ...(!v ? { collectionAmount: "", collectionCurrency: "EGP" } : { collectionCurrency: selectedAgent?.currency || "EGP" }) })}
                />
                {t("jobs.collection") || "Collection"}
                {form.collectionRequired && (
                  <>
                    <Input
                      type="number"
                      min="0"
                      step="0.01"
                      value={form.collectionAmount}
                      onChange={(e) => updateForm({ collectionAmount: e.target.value })}
                      placeholder={t("jobs.collectionAmount") || "Amount"}
                      className="border-border bg-card text-foreground h-7 w-24 text-center"
                    />
                    <Select value={form.collectionCurrency} onValueChange={(v) => updateForm({ collectionCurrency: v })}>
                      <SelectTrigger className="border-border bg-card text-foreground h-7 w-20">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        {["EGP", "USD", "EUR", "GBP", "SAR"].map((c) => (
                          <SelectItem key={c} value={c}>{c}</SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </>
                )}
              </label>
            </div>
            </div>
          </div>
          )}

          {/* Line 5: Transfer Price + Requested Vehicle Type */}
          <div className="grid grid-cols-5 gap-3">
            <div className="space-y-1.5">
              <Label className="text-muted-foreground text-xs">Transfer Price</Label>
              <div className="flex gap-1.5">
                <Input
                  type="number"
                  min="0"
                  step="0.01"
                  value={form.transferPrice}
                  onChange={(e) => updateForm({ transferPrice: e.target.value })}
                  placeholder="0.00"
                  className="border-border bg-card text-foreground placeholder:text-muted-foreground h-9 flex-1"
                />
                <Select value={form.transferPriceCurrency} onValueChange={(v) => updateForm({ transferPriceCurrency: v })}>
                  <SelectTrigger className="border-border bg-card text-foreground h-9 w-20">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {["EGP", "USD", "EUR", "GBP", "SAR"].map((c) => (
                      <SelectItem key={c} value={c}>{c}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            </div>
            {canEditVehicleType && (
            <div className="space-y-1.5">
              <Label className="text-muted-foreground text-xs">Requested Vehicle Type</Label>
              <Select value={form.requestedVehicleTypeId} onValueChange={(v) => updateForm({ requestedVehicleTypeId: v === "__none__" ? "" : v })}>
                <SelectTrigger className="w-full border-border bg-card text-foreground h-9 min-w-0">
                  <SelectValue placeholder="Select type" />
                </SelectTrigger>
                <SelectContent className="border-border bg-popover text-foreground">
                  <SelectItem value="__none__">None</SelectItem>
                  {vehicleTypes.map((vt) => (
                    <SelectItem key={vt.id} value={vt.id}>{vt.name} ({vt.seatCapacity} seats)</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            )}
          </div>

          {/* ── Notes ── */}
          <div className="flex items-center gap-2 pt-1">
            <span className="text-xs font-medium text-muted-foreground uppercase tracking-wide whitespace-nowrap">Notes</span>
            <hr className="flex-1 border-border" />
          </div>

          {/* Line 6: Notes */}
          {canNotes && (
          <div className="space-y-1.5">
            <Label className="text-muted-foreground text-xs">{t("jobs.notes")}</Label>
            <Input
              value={form.notes}
              onChange={(e) => updateForm({ notes: e.target.value })}
              placeholder={t("jobs.optionalNotes")}
              className="border-border bg-card text-foreground placeholder:text-muted-foreground h-9"
            />
          </div>
          )}
        </div>

        {/* Sticky Footer — Cancel + Save */}
        <div className="sticky bottom-0 bg-card border-t border-border py-3 px-4 flex justify-end gap-2">
          {editingJobId && (
            <Button
              variant="outline"
              onClick={handleCancelEdit}
              className="gap-1.5 border-border text-muted-foreground hover:text-foreground"
            >
              <X className="h-4 w-4" />
              {t("common.cancel") || "Cancel"}
            </Button>
          )}
          {canCreate && (
          <Button
            onClick={handleSave}
            disabled={saving}
            className="gap-1.5 bg-primary text-primary-foreground hover:bg-primary/90"
          >
            {saving ? <Loader2 className="h-4 w-4 animate-spin" /> : <Save className="h-4 w-4" />}
            {editingJobId ? (t("jobs.updateJob") || "Update Job") : t("jobs.createJob")}
          </Button>
          )}
        </div>
      </Card>

      {/* ─── Jobs Grid ─── */}
      <div className="space-y-3">
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
            {canStatusFilter && (
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
            )}
            <Select value={filterBookingStatus} onValueChange={(v) => { setFilterBookingStatus(v); setPage(1); }}>
              <SelectTrigger className="w-36 border-border bg-card text-foreground">
                <SelectValue />
              </SelectTrigger>
              <SelectContent className="border-border bg-popover text-foreground">
                <SelectItem value="ALL">{t("jobs.allBooking") || "All Booking"}</SelectItem>
                <SelectItem value="NEW">{t("jobs.bookingNew") || "New"}</SelectItem>
                <SelectItem value="UPDATED">{t("jobs.bookingUpdated") || "Updated"}</SelectItem>
                <SelectItem value="CANCELLED">{t("jobs.bookingCancelled") || "Cancelled"}</SelectItem>
              </SelectContent>
            </Select>
          </div>
          <div className="ml-auto">
            <ColumnVisibilityControl
              columns={onlineColumnDefs}
              visibility={onlineVisibility}
              onSave={onlineSaveVisibility}
            />
          </div>
        </div>

        <Card className="border-border bg-card">
          {loading ? (
            <div className="flex items-center justify-center py-12">
              <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
            </div>
          ) : filtered.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-12 text-muted-foreground">
              <Briefcase className="mb-2 h-8 w-8" />
              <p>{t("jobs.noJobs")}</p>
            </div>
          ) : (
            <Table>
              <DraggableTableHeader
                columns={onlineColumnDefs}
                columnOrder={onlineColumnOrder}
                onReorder={onlineReorder}
                rowClassName="border-border bg-muted"
                visibility={onlineVisibility}
              />
              <TableBody>
                {sortedData.map((job, idx) => {
                  const locked = isJobLocked(job.jobDate, job.editUnlockedAt);
                  const isSelected = editingJobId === job.id;
                  return (
                    <TableRow
                      key={job.id}
                      onClick={() => !locked && handleSelectJob(job)}
                      className={cn(
                        "border-border",
                        locked ? "opacity-60 cursor-not-allowed" : "cursor-pointer hover:bg-primary/10",
                        isSelected
                          ? "bg-primary/20 dark:bg-primary/20"
                          : idx % 2 === 0
                            ? "bg-gray-100/25 dark:bg-gray-800/25"
                            : "bg-gray-200/50 dark:bg-gray-700/50"
                      )}
                    >
                      {onlineColumnOrder.filter((key) => onlineVisibility[key] !== false).map((key) => renderOnlineCell(key, job, locked))}
                    </TableRow>
                  );
                })}
              </TableBody>
            </Table>
          )}
        </Card>

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
    </div>
  );
}
