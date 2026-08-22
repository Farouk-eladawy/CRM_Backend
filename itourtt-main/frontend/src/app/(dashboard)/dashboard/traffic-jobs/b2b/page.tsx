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
  Upload,
} from "lucide-react";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
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
import { B2BJobImportModal } from "@/components/b2b-job-import-modal";
import api from "@/lib/api";
import { useT, useLocaleId } from "@/lib/i18n";
import { cn, formatDate , localDateStr } from "@/lib/utils";
import { usePermission } from "@/hooks/use-permission";
import { StatusBadge } from "@/components/ui/status-badge";
import { useColumnPreferences } from "@/hooks/useColumnPreferences";
import { DraggableTableHeader, type ColumnDef } from "@/components/ui/draggable-table-header";
import { ColumnVisibilityControl } from "@/components/ui/column-visibility-control";
import { SERVICE_TYPE_DROPDOWN_OPTIONS, useServiceTypeLabel } from "@/lib/service-types";

interface VehicleTypeResource {
  id: string;
  name: string;
  seatCapacity: number;
}

interface SupplierResource {
  id: string;
  legalName: string;
  tradeName: string | null;
  vehicleCount: number;
}

interface VehicleResource {
  id: string;
  plateNumber: string;
  vehicleType?: { name: string; seatCapacity: number };
  supplierId?: string | null;
}

interface PersonResource {
  id: string;
  name: string;
  mobileNumber?: string;
  supplierId?: string | null;
}

/* ─────────── types ─────────── */

interface Customer {
  id: string;
  legalName: string;
  tradeName: string | null;
}

interface TrafficJob {
  id: string;
  internalRef: string;
  agentRef: string | null;
  customerJobId: string | null;
  bookingChannel: "ONLINE" | "B2B" | "B2C";
  serviceType: string;
  jobDate: string;
  status: string;
  bookingStatus: string;
  adultCount: number;
  childCount: number;
  paxCount: number;
  clientName: string | null;
  pickUpTime: string | null;
  notes: string | null;
  jobExtras?: { name: string; qty: number }[];
  createdAt: string;
  editUnlockedAt: string | null;
  customerId: string | null;
  originAirportId: string | null;
  originZoneId: string | null;
  originHotelId: string | null;
  destinationAirportId: string | null;
  destinationZoneId: string | null;
  destinationHotelId: string | null;
  custRepName: string | null;
  custRepMobile: string | null;
  custRepMeetingPoint: string | null;
  custRepMeetingTime: string | null;
  priceAmount: number | null;
  priceCurrency: string | null;
  customer?: { legalName: string } | null;
  originAirport?: { name: string; code: string } | null;
  originZone?: { name: string } | null;
  originHotel?: { name: string } | null;
  destinationAirport?: { name: string; code: string } | null;
  destinationZone?: { name: string } | null;
  destinationHotel?: { name: string } | null;
  fromZone?: { name: string } | null;
  toZone?: { name: string } | null;
  flight?: { flightNo: string; terminal?: string; arrivalTime?: string; departureTime?: string } | null;
  assignment?: {
    id: string;
    vehicleId: string | null;
    driverId: string | null;
    repId?: string | null;
    externalDriverName?: string | null;
    externalDriverPhone?: string | null;
    vehicle?: { plateNumber: string; supplierId?: string | null; vehicleType?: { name: string; seatCapacity: number } };
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
  customerId: string;
  customerJobId: string;
  serviceType: string;
  jobServiceTypeId: string;
  jobDate: string;
  paxCount: string;
  originAirportId: string;
  originZoneId: string;
  originHotelId: string;
  destinationAirportId: string;
  destinationZoneId: string;
  destinationHotelId: string;
  originSelectedId: string;
  destinationSelectedId: string;
  pickUpTime: string;
  notes: string;
  custRepName: string;
  custRepMobile: string;
  custRepMeetingPoint: string;
  custRepMeetingTime: string;
  priceAmount: string;
  priceCurrency: string;
  flightNo: string;
  terminal: string;
  arrivalTime: string;
  departureTime: string;
  assignSource: string;
  assignVehicleId: string;
  assignDriverId: string;
  assignRepId: string;
  externalVehicleType: string;
  externalDriverName: string;
  externalDriverMobile: string;
}

const defaultForm: FormState = {
  bookingStatus: "NEW",
  customerId: "",
  customerJobId: "",
  serviceType: "ARR",
  jobServiceTypeId: "",
  jobDate: localDateStr(new Date()),
  paxCount: "1",
  originAirportId: "",
  originZoneId: "",
  originHotelId: "",
  destinationAirportId: "",
  destinationZoneId: "",
  destinationHotelId: "",
  originSelectedId: "",
  destinationSelectedId: "",
  pickUpTime: "",
  notes: "",
  custRepName: "",
  custRepMobile: "",
  custRepMeetingPoint: "",
  custRepMeetingTime: "",
  priceAmount: "",
  priceCurrency: "EGP",
  flightNo: "",
  terminal: "",
  arrivalTime: "",
  departureTime: "",
  assignSource: "owned",
  assignVehicleId: "",
  assignDriverId: "",
  assignRepId: "",
  externalVehicleType: "",
  externalDriverName: "",
  externalDriverMobile: "",
};

/* ─────────── component ─────────── */

export default function B2BJobPage() {
  const t = useT();
  const locale = useLocaleId();
  const router = useRouter();
  const searchParams = useSearchParams();
  const editParam = searchParams.get("edit");
  const formRef = useRef<HTMLDivElement>(null);
  const autoEditLoadedRef = useRef(false);

  const canAssignVehicle = usePermission("dispatch.assignment.assignVehicle");
  const canAssignDriver = usePermission("dispatch.assignment.assignDriver");
  const canAssignRep = usePermission("dispatch.assignment.assignRep");
  const canAssign = canAssignVehicle || canAssignDriver || canAssignRep;

  const canCreateB2B = usePermission("traffic-jobs.b2b.createJob");
  const canCustomer = usePermission("traffic-jobs.b2b.form.customer");
  const canB2BServiceType = usePermission("traffic-jobs.b2b.form.serviceType");
  const canB2BDateTime = usePermission("traffic-jobs.b2b.form.dateTime");
  const canB2BPaxCount = usePermission("traffic-jobs.b2b.form.paxCount");
  const canB2BRoute = usePermission("traffic-jobs.b2b.form.route");
  const canB2BFlightInfo = usePermission("traffic-jobs.b2b.form.flightInfo");
  const canB2BMeetingInfo = usePermission("traffic-jobs.b2b.form.meetingInfo");
  const canB2BNotes = usePermission("traffic-jobs.b2b.form.notes");
  const canB2BStatusFilter = usePermission("traffic-jobs.b2b.table.statusFilter");
  const canB2BImport = usePermission("traffic-jobs.b2b.importJobs");

  const [customers, setCustomers] = useState<Customer[]>([]);
  const [jobs, setJobs] = useState<TrafficJob[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [filterStatus, setFilterStatus] = useState<string>("ALL");
  const [filterBookingStatus, setFilterBookingStatus] = useState<string>("ALL");
  const [search, setSearch] = useState("");
  const [form, setForm] = useState<FormState>({ ...defaultForm });
  const [suppliers, setSuppliers] = useState<SupplierResource[]>([]);
  const [jobServiceTypes, setJobServiceTypes] = useState<{ id: string; name: string }[]>([]);
  const [vehicles, setVehicles] = useState<VehicleResource[]>([]);
  const [drivers, setDrivers] = useState<PersonResource[]>([]);
  const [reps, setReps] = useState<PersonResource[]>([]);
  const [vehicleTypes, setVehicleTypes] = useState<VehicleTypeResource[]>([]);
  const [jobSources, setJobSources] = useState<Record<string, string>>({});
  const [editingJobId, setEditingJobId] = useState<string | null>(null);
  const [importModalOpen, setImportModalOpen] = useState(false);

  const serviceTypeLabel = useServiceTypeLabel();

  const updateForm = useCallback((updates: Partial<FormState>) => {
    setForm((prev) => ({ ...prev, ...updates }));
  }, []);

  /* ── Fetch customers + assignment resources ── */
  useEffect(() => {
    async function fetchResources() {
      try {
        const [custRes, supRes, vehRes, drvRes, repRes, vtRes] = await Promise.allSettled([
          api.get("/customers"),
          canAssign ? api.get("/dispatch/available-suppliers") : Promise.resolve({ data: [] }),
          canAssignVehicle ? api.get("/dispatch/available-vehicles", { params: { date: form.jobDate } }) : Promise.resolve({ data: [] }),
          canAssignDriver ? api.get("/dispatch/available-drivers", { params: { date: form.jobDate } }) : Promise.resolve({ data: [] }),
          canAssignRep ? api.get("/dispatch/available-reps", { params: { date: form.jobDate } }) : Promise.resolve({ data: [] }),
          api.get("/vehicles/types"),
        ]);
        if (custRes.status === "fulfilled") {
          const d = custRes.value.data;
          setCustomers(Array.isArray(d) ? d : d.data || []);
        }
        if (supRes.status === "fulfilled") { const d = supRes.value.data; setSuppliers(Array.isArray(d) ? d : d.data || []); }
        if (vehRes.status === "fulfilled") { const d = vehRes.value.data; setVehicles(Array.isArray(d) ? d : d.data || []); }
        if (drvRes.status === "fulfilled") { const d = drvRes.value.data; setDrivers(Array.isArray(d) ? d : d.data || []); }
        if (repRes.status === "fulfilled") { const d = repRes.value.data; setReps(Array.isArray(d) ? d : d.data || []); }
        if (vtRes.status === "fulfilled") { const d = vtRes.value.data; setVehicleTypes(Array.isArray(d) ? d : d.data || []); }
      } catch {
        /* non-critical */
      }
      try {
        const { data } = await api.get("/job-service-types");
        setJobServiceTypes(Array.isArray(data) ? data : data.data || []);
      } catch { /* non-critical */ }
    }
    fetchResources();
  }, [canAssign, canAssignVehicle, canAssignDriver, canAssignRep]);

  /* ── Fetch B2B jobs ── */
  const fetchJobs = useCallback(async () => {
    try {
      const params: Record<string, string> = { bookingChannel: "B2B" };
      if (filterStatus !== "ALL") params.status = filterStatus;
      const { data } = await api.get("/traffic-jobs", { params });
      setJobs(Array.isArray(data) ? data : data.data || []);
    } catch {
      toast.error(t("jobs.failedLoad"));
    } finally {
      setLoading(false);
    }
  }, [filterStatus]);

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

    const originSelectedId = job.originAirportId || job.originZoneId || job.originHotelId || "";
    const destinationSelectedId = job.destinationAirportId || job.destinationZoneId || job.destinationHotelId || "";

    const pickUpTime = job.pickUpTime ? new Date(job.pickUpTime).toLocaleTimeString("en-GB", { timeZone: "Africa/Cairo", hour: "2-digit", minute: "2-digit", hour12: false }) : "";
    const arrivalTime = job.flight?.arrivalTime ? new Date(job.flight.arrivalTime).toLocaleTimeString("en-GB", { timeZone: "Africa/Cairo", hour: "2-digit", minute: "2-digit", hour12: false }) : "";
    const departureTime = job.flight?.departureTime ? new Date(job.flight.departureTime).toLocaleTimeString("en-GB", { timeZone: "Africa/Cairo", hour: "2-digit", minute: "2-digit", hour12: false }) : "";
    const custRepMeetingTime = job.custRepMeetingTime ? new Date(job.custRepMeetingTime).toLocaleTimeString("en-GB", { timeZone: "Africa/Cairo", hour: "2-digit", minute: "2-digit", hour12: false }) : "";

    setForm({
      bookingStatus: "UPDATED",
      customerId: job.customerId || "",
      customerJobId: job.customerJobId || "",
      serviceType: job.serviceType,
      jobDate: job.jobDate?.split("T")[0] || "",
      paxCount: String(job.paxCount),
      originAirportId: job.originAirportId || "",
      originZoneId: job.originZoneId || "",
      originHotelId: job.originHotelId || "",
      destinationAirportId: job.destinationAirportId || "",
      destinationZoneId: job.destinationZoneId || "",
      destinationHotelId: job.destinationHotelId || "",
      originSelectedId,
      destinationSelectedId,
      pickUpTime,
      notes: job.notes || "",
      custRepName: job.custRepName || "",
      custRepMobile: job.custRepMobile || "",
      custRepMeetingPoint: job.custRepMeetingPoint || "",
      custRepMeetingTime,
      priceAmount: job.priceAmount != null ? String(job.priceAmount) : "",
      priceCurrency: job.priceCurrency || "EGP",
      jobServiceTypeId: (job as any).jobServiceType?.id || "",
      flightNo: job.flight?.flightNo || "",
      terminal: job.flight?.terminal || "",
      arrivalTime,
      departureTime,
      assignSource: job.assignment?.vehicle?.supplierId || (job.assignment?.externalDriverName ? "__supplier__" : "owned"),
      assignVehicleId: job.assignment?.vehicleId || "",
      assignDriverId: job.assignment?.driverId || "",
      assignRepId: job.assignment?.rep ? reps.find((r) => r.name === job.assignment?.rep?.name)?.id || "" : "",
      externalVehicleType: "",
      externalDriverName: job.assignment?.externalDriverName || "",
      externalDriverMobile: job.assignment?.externalDriverPhone || "",
    });
  };

  const handleCancelEdit = () => {
    setEditingJobId(null);
    setForm({ ...defaultForm });
  };

  /* ── Create or Update job ── */
  const handleSave = async () => {
    if (!form.customerId) {
      toast.error(t("jobs.customerRequired"));
      return;
    }

    if (!form.jobDate) {
      toast.error(t("jobs.dateRequired") || "Service date is required");
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
        bookingChannel: "B2B",
        customerId: form.customerId,
        serviceType: form.serviceType,
        jobDate: form.jobDate,
        adultCount: parseInt(form.paxCount) || 1,
        childCount: 0,
        bookingStatus: form.bookingStatus,
      };

      if (form.customerJobId.trim()) payload.customerJobId = form.customerJobId.trim();
      if (form.jobServiceTypeId) payload.jobServiceTypeId = form.jobServiceTypeId;
      if (form.priceAmount) {
        payload.priceAmount = parseFloat(form.priceAmount);
        payload.priceCurrency = form.priceCurrency || "EGP";
      }

      if (form.originAirportId) payload.originAirportId = form.originAirportId;
      if (form.originZoneId) payload.originZoneId = form.originZoneId;
      if (form.originHotelId) payload.originHotelId = form.originHotelId;
      if (form.destinationAirportId) payload.destinationAirportId = form.destinationAirportId;
      if (form.destinationZoneId) payload.destinationZoneId = form.destinationZoneId;
      if (form.destinationHotelId) payload.destinationHotelId = form.destinationHotelId;

      if (form.pickUpTime) payload.pickUpTime = `${form.jobDate}T${form.pickUpTime}`;
      if (form.notes.trim()) payload.notes = form.notes.trim();
      if (form.custRepName.trim()) payload.custRepName = form.custRepName.trim();
      if (form.custRepMobile.trim()) payload.custRepMobile = form.custRepMobile.trim();
      if (form.custRepMeetingPoint.trim()) payload.custRepMeetingPoint = form.custRepMeetingPoint.trim();
      if (form.custRepMeetingTime) payload.custRepMeetingTime = `${form.jobDate}T${form.custRepMeetingTime}`;

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

      // Build assignment payload based on source type
      const buildAssignPayload = (): Record<string, string | boolean> | null => {
        const ap: Record<string, string | boolean> = {};
        const supplierMode = form.assignSource !== "owned";

        if (supplierMode) {
          // Supplier: external driver name/phone, no vehicleId/driverId
          if (form.externalDriverName.trim()) ap.externalDriverName = form.externalDriverName.trim();
          if (form.externalDriverMobile.trim()) ap.externalDriverPhone = form.externalDriverMobile.trim();
        } else {
          // Owned: select from company vehicles/drivers
          if (form.assignVehicleId) ap.vehicleId = form.assignVehicleId;
          if (form.assignDriverId) ap.driverId = form.assignDriverId;
        }

        // Rep — skip if "N/A"
        if (form.assignRepId && form.assignRepId !== "__NA__") ap.repId = form.assignRepId;

        return Object.keys(ap).length > 0 ? ap : null;
      };

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
        // Update assignment if changed
        const assignPayload = buildAssignPayload();
        if (assignPayload) {
          const job = jobs.find((j) => j.id === editingJobId);
          try {
            if (job?.assignment) {
              await api.patch(`/dispatch/assignments/${job.assignment.id}`, assignPayload);
            } else {
              await api.post("/dispatch/assign", { trafficJobId: editingJobId, ...assignPayload });
            }
          } catch {
            // Assignment update failed but job was saved — non-blocking
          }
        }
        toast.success(t("jobs.updated") || "Job updated successfully");
      } else {
        const { bookingStatus, ...createPayload } = payload;
        const { data: newJob } = await api.post("/traffic-jobs", createPayload);
        // Assign vehicle/driver/rep if selected
        const assignPayload = buildAssignPayload();
        if (assignPayload && newJob?.id) {
          try {
            await api.post("/dispatch/assign", { trafficJobId: newJob.id, ...assignPayload });
          } catch {
            // Assignment failed but job was created — non-blocking
          }
        }
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

  /* ── Assignment handlers ── */
  const handleAssignVehicle = async (job: TrafficJob, vehicleId: string) => {
    try {
      if (job.assignment) {
        await api.patch(`/dispatch/assignments/${job.assignment.id}`, { vehicleId });
      } else {
        await api.post("/dispatch/assign", { trafficJobId: job.id, vehicleId });
      }
      toast.success(t("dispatch.vehicleAssigned") || "Vehicle assigned");
      fetchJobs();
    } catch (err: unknown) {
      const resp = (err as { response?: { status?: number; data?: { message?: string } } })?.response;
      if (resp?.status === 409 && resp?.data?.message?.includes("Vehicle type mismatch")) {
        if (window.confirm(resp.data.message + "\n\nAssign anyway?")) {
          try {
            if (job.assignment) {
              await api.patch(`/dispatch/assignments/${job.assignment.id}`, { vehicleId, allowTypeMismatch: true });
            } else {
              await api.post("/dispatch/assign", { trafficJobId: job.id, vehicleId, allowTypeMismatch: true });
            }
            toast.success(t("dispatch.vehicleAssigned") || "Vehicle assigned");
            fetchJobs();
          } catch {
            toast.error(t("dispatch.assignmentFailed") || "Assignment failed");
          }
          return;
        }
      }
      toast.error(resp?.data?.message || t("dispatch.assignmentFailed") || "Assignment failed");
    }
  };

  const handleAssignDriver = async (job: TrafficJob, driverId: string) => {
    try {
      if (job.assignment) {
        await api.patch(`/dispatch/assignments/${job.assignment.id}`, { driverId });
      } else {
        await api.post("/dispatch/assign", { trafficJobId: job.id, driverId });
      }
      toast.success(t("dispatch.driverAssigned") || "Driver assigned");
      fetchJobs();
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { message?: string } } })?.response?.data?.message || t("dispatch.assignmentFailed") || "Assignment failed";
      toast.error(msg);
    }
  };

  const handleAssignRep = async (job: TrafficJob, repId: string) => {
    try {
      if (job.assignment) {
        await api.patch(`/dispatch/assignments/${job.assignment.id}`, { repId });
      } else {
        await api.post("/dispatch/assign", { trafficJobId: job.id, repId });
      }
      toast.success(t("dispatch.repUpdated") || "Rep assigned");
      fetchJobs();
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { message?: string } } })?.response?.data?.message || t("dispatch.assignmentFailed") || "Assignment failed";
      toast.error(msg);
    }
  };

  // Derive source per job from assignment vehicle
  const getJobSource = (job: TrafficJob): string => {
    if (jobSources[job.id]) return jobSources[job.id];
    if (job.assignment?.vehicle?.supplierId) return job.assignment.vehicle.supplierId;
    return "owned";
  };

  // Filter vehicles by selected source
  const getFilteredVehicles = (source: string): VehicleResource[] => {
    if (source === "owned") return vehicles.filter((v) => !v.supplierId);
    return vehicles.filter((v) => v.supplierId === source);
  };

  // Filter drivers by source (owned drivers only for owned source)
  const getFilteredDrivers = (): PersonResource[] => {
    return drivers.filter((d) => !d.supplierId);
  };

  const isSupplierSource = form.assignSource !== "owned";

  const handleUnassign = async (job: TrafficJob) => {
    if (!job.assignment || !window.confirm("Remove assignment?")) return;
    try {
      await api.delete(`/dispatch/assignments/${job.assignment.id}`);
      toast.success("Assignment removed");
      fetchJobs();
    } catch {
      toast.error("Failed to remove assignment");
    }
  };

  const filtered = jobs.filter((j) => {
    if (filterBookingStatus !== "ALL" && j.bookingStatus !== filterBookingStatus) return false;
    if (!search) return true;
    const q = search.toLowerCase();
    return (
      j.internalRef?.toLowerCase().includes(q) ||
      j.customerJobId?.toLowerCase().includes(q) ||
      j.customer?.legalName?.toLowerCase().includes(q) ||
      j.clientName?.toLowerCase().includes(q)
    );
  });

  const showFlightFields = form.serviceType === "ARR" || form.serviceType === "DEP";

  // ── Draggable column order ──
  const B2B_DEFAULT_COLS = [
    "ref", "customerJobId", "serviceType", "jobDate", "customer",
    "route", "pax", "extras", "notes", "price", "bookingStatus", "status", "assignment",
  ];
  const { columns: b2bColumnOrder, reorder: b2bReorder, visibility: b2bVisibility, saveVisibility: b2bSaveVisibility } = useColumnPreferences("traffic_jobs_b2b", B2B_DEFAULT_COLS);
  const th = (label: string) => <span className="text-xs font-medium text-muted-foreground">{label}</span>;

  const b2bColumnDefs: ColumnDef[] = [
    { key: "ref",           label: th(t("dispatch.ref")) },
    { key: "customerJobId", label: th(t("jobs.customerJobId") || "Cust. Job ID") },
    { key: "serviceType",   label: th(t("jobs.type")) },
    { key: "jobDate",       label: th(t("common.date")) },
    { key: "customer",      label: th(t("jobs.customer")) },
    { key: "route",         label: th(t("dispatch.route")) },
    { key: "pax",           label: th(t("dispatch.pax")) },
    { key: "extras",        label: th(t("jobs.extras") || "Extras") },
    { key: "notes",         label: th(t("jobs.notes") || "Notes") },
    { key: "price",         label: th(t("jobs.price") || "Price") },
    { key: "bookingStatus", label: th(t("jobs.bookingStatus") || "Booking") },
    { key: "status",        label: th(t("common.status")) },
    { key: "assignment",    label: th(t("jobs.assignment")) },
  ];

  const renderB2BCell = (key: string, job: TrafficJob, locked: boolean): React.ReactNode => {
    switch (key) {
      case "ref":
        return (
          <TableCell key={key} className="text-foreground font-mono text-xs">
            <div className="flex items-center gap-1.5">
              {locked && <Lock className="h-3.5 w-3.5 text-muted-foreground/60 shrink-0" />}
              {job.internalRef}
            </div>
          </TableCell>
        );
      case "customerJobId":
        return <TableCell key={key} className="text-muted-foreground text-xs">{job.customerJobId || "\u2014"}</TableCell>;
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
      case "customer":
        return <TableCell key={key} className="text-muted-foreground text-xs">{job.customer?.legalName || "\u2014"}</TableCell>;
      case "route":
        return (
          <TableCell key={key} className="text-muted-foreground text-xs">
            {job.originAirport?.code || job.fromZone?.name || job.originZone?.name || job.originHotel?.name || "\u2014"} &rarr; {job.destinationAirport?.code || job.toZone?.name || job.destinationZone?.name || job.destinationHotel?.name || "\u2014"}
          </TableCell>
        );
      case "pax":
        return <TableCell key={key} className="text-muted-foreground text-xs">{job.paxCount}</TableCell>;
      case "extras": {
        const extras = (job.jobExtras || [])
          .filter((e) => e.qty > 0)
          .map((e) => `${e.name} \u00d7${e.qty}`);
        return <TableCell key={key} className="text-muted-foreground text-xs">{extras.length > 0 ? extras.join(", ") : "\u2014"}</TableCell>;
      }
      case "notes":
        return (
          <TableCell key={key} className="text-muted-foreground text-xs max-w-[150px] truncate" title={job.notes || ""}>
            {job.notes || "\u2014"}
          </TableCell>
        );
      case "price":
        return (
          <TableCell key={key} className="text-muted-foreground text-xs">
            {job.priceAmount != null ? (
              <span>{Number(job.priceAmount).toLocaleString()} <span className="text-muted-foreground/60">{job.priceCurrency || "EGP"}</span></span>
            ) : "\u2014"}
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
                {job.assignment.vehicle?.plateNumber || job.assignment.externalDriverName || "\u2014"}
                {job.assignment.driver ? ` / ${job.assignment.driver.name}` : job.assignment.externalDriverName ? ` / ${job.assignment.externalDriverPhone || ""}` : ""}
                {job.assignment.rep && ` / ${job.assignment.rep.name}`}
              </span>
            ) : t("dispatch.unassigned")}
          </TableCell>
        );
      default:
        return <TableCell key={key} />;
    }
  };

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
            {editingJobId ? (t("jobs.editJob") || "Edit Job") : t("jobs.newB2BJob")}
          </h1>
          <p className="text-sm text-muted-foreground">{t("jobs.b2bDescription")}</p>
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

          {/* Row 1: Booking Status + Customer + Service Type + Date + Pickup + Adults */}
          <div className="grid grid-cols-7 gap-3">
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
            {canCustomer && (
            <div className="min-w-0 space-y-1.5">
              <Label className="text-muted-foreground text-xs">{t("jobs.customer")} *</Label>
              <Select value={form.customerId} onValueChange={(v) => updateForm({ customerId: v })}>
                <SelectTrigger className="w-full border-border bg-card text-foreground h-9 min-w-0">
                  <SelectValue placeholder={t("jobs.selectCustomer")} className="truncate" />
                </SelectTrigger>
                <SelectContent className="border-border bg-popover text-foreground">
                  {customers.map((c) => (
                    <SelectItem key={c.id} value={c.id}>
                      {c.legalName}
                      {c.tradeName && <span className="ml-1 text-muted-foreground">({c.tradeName})</span>}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            )}
            <div className="min-w-0 space-y-1.5">
              <Label className="text-muted-foreground text-xs">{t("jobs.customerJobId") || "Customer Job ID"}</Label>
              <Input
                value={form.customerJobId}
                onChange={(e) => updateForm({ customerJobId: e.target.value })}
                placeholder={t("jobs.customerJobIdPlaceholder") || "Customer ref..."}
                className="border-border bg-card text-foreground placeholder:text-muted-foreground h-9"
              />
            </div>
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
            {canB2BServiceType && (
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
            {canB2BDateTime && (
            <>
            <div className="min-w-0 space-y-1.5">
              <Label className="text-muted-foreground text-xs">{t("jobs.serviceDate")} *</Label>
              <Input
                type="date"
                value={form.jobDate}
                onChange={(e) => updateForm({ jobDate: e.target.value })}
                min="2020-01-01"
                className={cn("border-border bg-card text-foreground h-9", !form.jobDate && "border-red-500")}
                required
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
            {canB2BPaxCount && (
            <div className="min-w-0 space-y-1.5">
              <Label className="text-muted-foreground text-xs">{t("dispatch.pax") || "Pax"}</Label>
              <Input
                type="number"
                min="1"
                value={form.paxCount}
                onChange={(e) => updateForm({ paxCount: e.target.value })}
                className="border-border bg-card text-foreground h-9"
              />
            </div>
            )}
          </div>

          {/* ── Route & Flight ── */}
          <div className="flex items-center gap-2 pt-1">
            <span className="text-xs font-medium text-muted-foreground uppercase tracking-wide whitespace-nowrap">Route &amp; Flight</span>
            <hr className="flex-1 border-border" />
          </div>

          {/* Row 2: Origin + Destination + Flight Info + Arrival/Departure Time */}
          <div className={`grid gap-3 ${showFlightFields ? "grid-cols-5" : "grid-cols-2"}`}>
            {canB2BRoute && (
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
            {canB2BFlightInfo && showFlightFields && (
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
                <div className="min-w-0 space-y-1.5">
                  <Label className="text-muted-foreground text-xs">
                    {form.serviceType === "ARR" ? t("jobs.arrivalTime") : t("jobs.departureTime")}
                  </Label>
                  <Input
                    value={form.serviceType === "ARR" ? form.arrivalTime : form.departureTime}
                    onChange={(e) => {
                      let v = e.target.value.replace(/[^0-9:]/g, "");
                      const current = form.serviceType === "ARR" ? form.arrivalTime : form.departureTime;
                      if (v.length === 2 && !v.includes(":") && current.length < v.length) v += ":";
                      if (v.length > 5) v = v.slice(0, 5);
                      updateForm(form.serviceType === "ARR" ? { arrivalTime: v } : { departureTime: v });
                    }}
                    placeholder="HH:MM"
                    maxLength={5}
                    className="border-border bg-card text-foreground placeholder:text-muted-foreground h-9 font-mono"
                  />
                </div>
              </>
            )}
          </div>

          {/* ── Pricing & Meeting ── */}
          <div className="flex items-center gap-2 pt-1">
            <span className="text-xs font-medium text-muted-foreground uppercase tracking-wide whitespace-nowrap">Pricing &amp; Meeting</span>
            <hr className="flex-1 border-border" />
          </div>

          {/* Row 4: Price + Customer Rep Meeting Fields */}
          <div className="grid grid-cols-6 gap-3">
            <div className="min-w-0 space-y-1.5">
              <Label className="text-muted-foreground text-xs">{t("jobs.price") || "Price"}</Label>
              <div className="flex gap-1">
                <Input
                  type="number"
                  min="0"
                  step="0.01"
                  value={form.priceAmount}
                  onChange={(e) => updateForm({ priceAmount: e.target.value })}
                  placeholder="0.00"
                  className="border-border bg-card text-foreground placeholder:text-muted-foreground h-9 flex-1"
                />
                <Select value={form.priceCurrency} onValueChange={(v) => updateForm({ priceCurrency: v })}>
                  <SelectTrigger className="w-[70px] border-border bg-card text-foreground h-9">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent className="border-border bg-popover text-foreground">
                    <SelectItem value="EGP">EGP</SelectItem>
                    <SelectItem value="USD">USD</SelectItem>
                    <SelectItem value="EUR">EUR</SelectItem>
                    <SelectItem value="GBP">GBP</SelectItem>
                    <SelectItem value="SAR">SAR</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>
            {canB2BMeetingInfo && (
            <>
            <div className="min-w-0 space-y-1.5">
              <Label className="text-muted-foreground text-xs">{t("jobs.custRepName")}</Label>
              <Input
                value={form.custRepName}
                onChange={(e) => updateForm({ custRepName: e.target.value })}
                className="border-border bg-card text-foreground placeholder:text-muted-foreground h-9"
              />
            </div>
            <div className="min-w-0 space-y-1.5">
              <Label className="text-muted-foreground text-xs">{t("jobs.custRepMobile")}</Label>
              <Input
                type="tel"
                value={form.custRepMobile}
                onChange={(e) => updateForm({ custRepMobile: e.target.value })}
                placeholder="+20 xxx xxx xxxx"
                className="border-border bg-card text-foreground placeholder:text-muted-foreground h-9"
              />
            </div>
            <div className="min-w-0 space-y-1.5">
              <Label className="text-muted-foreground text-xs">{t("jobs.custRepMeetingPoint")}</Label>
              <Input
                value={form.custRepMeetingPoint}
                onChange={(e) => updateForm({ custRepMeetingPoint: e.target.value })}
                className="border-border bg-card text-foreground placeholder:text-muted-foreground h-9"
              />
            </div>
            <div className="min-w-0 space-y-1.5">
              <Label className="text-muted-foreground text-xs">{t("jobs.custRepMeetingTime")}</Label>
              <Input
                value={form.custRepMeetingTime}
                onChange={(e) => {
                  let v = e.target.value.replace(/[^0-9:]/g, "");
                  if (v.length === 2 && !v.includes(":") && form.custRepMeetingTime.length < v.length) v += ":";
                  if (v.length > 5) v = v.slice(0, 5);
                  updateForm({ custRepMeetingTime: v });
                }}
                placeholder="HH:MM"
                maxLength={5}
                className="border-border bg-card text-foreground placeholder:text-muted-foreground h-9 font-mono"
              />
            </div>
            </>
            )}
          </div>

          {/* ── Assignment ── */}
          {canAssign && (
          <div className="flex items-center gap-2 pt-1">
            <span className="text-xs font-medium text-muted-foreground uppercase tracking-wide whitespace-nowrap">Assignment</span>
            <hr className="flex-1 border-border" />
          </div>
          )}

          {/* Row 5: Assignment — Source, Vehicle, Driver, Rep */}
          {canAssign && (
            <div className={`grid gap-3 ${isSupplierSource ? "grid-cols-5" : "grid-cols-4"}`}>
              {canAssignVehicle && (
                <div className="min-w-0 space-y-1.5">
                  <Label className="text-muted-foreground text-xs">{t("dispatch.source") || "Car Source"}</Label>
                  <Select value={form.assignSource} onValueChange={(v) => updateForm({ assignSource: v, assignVehicleId: "", assignDriverId: "", externalVehicleType: "", externalDriverName: "", externalDriverMobile: "" })}>
                    <SelectTrigger className="w-full border-border bg-card text-foreground h-9 min-w-0">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent className="border-border bg-popover text-foreground">
                      <SelectItem value="owned">Owned ({vehicles.filter((v) => !v.supplierId).length})</SelectItem>
                      {suppliers.map((s) => (
                        <SelectItem key={s.id} value={s.id}>
                          {s.tradeName || s.legalName} ({s.vehicleCount})
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
              )}

              {/* ── Owned: Vehicle select ── */}
              {canAssignVehicle && !isSupplierSource && (
                <div className="min-w-0 space-y-1.5">
                  <Label className="text-muted-foreground text-xs">{t("dispatch.vehicle") || "Vehicle"}</Label>
                  <Select value={form.assignVehicleId} onValueChange={(v) => updateForm({ assignVehicleId: v })}>
                    <SelectTrigger className="w-full border-border bg-card text-foreground h-9 min-w-0">
                      <SelectValue placeholder="Select vehicle..." />
                    </SelectTrigger>
                    <SelectContent className="border-border bg-popover text-foreground">
                      {getFilteredVehicles("owned").map((v) => (
                        <SelectItem key={v.id} value={v.id}>
                          {v.plateNumber} {v.vehicleType?.name ? `(${v.vehicleType.name})` : ""}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
              )}

              {/* ── Supplier: Car type select ── */}
              {canAssignVehicle && isSupplierSource && (
                <div className="min-w-0 space-y-1.5">
                  <Label className="text-muted-foreground text-xs">{t("dispatch.carType") || "Car Type"}</Label>
                  <Select value={form.externalVehicleType} onValueChange={(v) => updateForm({ externalVehicleType: v })}>
                    <SelectTrigger className="w-full border-border bg-card text-foreground h-9 min-w-0">
                      <SelectValue placeholder={t("dispatch.carType") || "Car Type"} />
                    </SelectTrigger>
                    <SelectContent className="border-border bg-popover text-foreground">
                      {vehicleTypes.map((vt) => (
                        <SelectItem key={vt.id} value={vt.name}>
                          {vt.name}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
              )}

              {/* ── Owned: Driver select ── */}
              {canAssignDriver && !isSupplierSource && (
                <div className="min-w-0 space-y-1.5">
                  <Label className="text-muted-foreground text-xs">{t("dispatch.driver") || "Driver"}</Label>
                  <Select value={form.assignDriverId} onValueChange={(v) => updateForm({ assignDriverId: v })}>
                    <SelectTrigger className="w-full border-border bg-card text-foreground h-9 min-w-0">
                      <SelectValue placeholder="Select driver..." />
                    </SelectTrigger>
                    <SelectContent className="border-border bg-popover text-foreground">
                      {getFilteredDrivers().map((d) => (
                        <SelectItem key={d.id} value={d.id}>
                          {d.name}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
              )}

              {/* ── Supplier: Driver name + mobile text fields ── */}
              {canAssignDriver && isSupplierSource && (
                <>
                  <div className="min-w-0 space-y-1.5">
                    <Label className="text-muted-foreground text-xs">{t("dispatch.driverName") || "Driver Name"}</Label>
                    <Input
                      value={form.externalDriverName}
                      onChange={(e) => updateForm({ externalDriverName: e.target.value })}
                      placeholder="Driver name..."
                      className="border-border bg-card text-foreground placeholder:text-muted-foreground h-9"
                    />
                  </div>
                  <div className="min-w-0 space-y-1.5">
                    <Label className="text-muted-foreground text-xs">{t("dispatch.driverMobile") || "Driver Mobile"}</Label>
                    <Input
                      type="tel"
                      value={form.externalDriverMobile}
                      onChange={(e) => updateForm({ externalDriverMobile: e.target.value })}
                      placeholder="+20 xxx xxx xxxx"
                      className="border-border bg-card text-foreground placeholder:text-muted-foreground h-9"
                    />
                  </div>
                </>
              )}

              {/* ── Rep (both modes): with N/A option ── */}
              {canAssignRep && (
                <div className="min-w-0 space-y-1.5">
                  <Label className="text-muted-foreground text-xs">{t("dispatch.rep") || "Rep"}</Label>
                  <Select value={form.assignRepId} onValueChange={(v) => updateForm({ assignRepId: v })}>
                    <SelectTrigger className="w-full border-border bg-card text-foreground h-9 min-w-0">
                      <SelectValue placeholder="Select rep..." />
                    </SelectTrigger>
                    <SelectContent className="border-border bg-popover text-foreground">
                      <SelectItem value="__NA__">N/A</SelectItem>
                      {reps.map((r) => (
                        <SelectItem key={r.id} value={r.id}>
                          {r.name}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
              )}
            </div>
          )}

          {/* ── Notes ── */}
          <div className="flex items-center gap-2 pt-1">
            <span className="text-xs font-medium text-muted-foreground uppercase tracking-wide whitespace-nowrap">Notes</span>
            <hr className="flex-1 border-border" />
          </div>

          {/* Row 6: Notes */}
          {canB2BNotes && (
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
          {canCreateB2B && (
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
            {canB2BStatusFilter && (
            <Select value={filterStatus} onValueChange={setFilterStatus}>
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
            <Select value={filterBookingStatus} onValueChange={setFilterBookingStatus}>
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
          {canB2BImport && (
          <Button
            variant="outline"
            className="gap-1.5 border-border ml-auto"
            onClick={() => setImportModalOpen(true)}
          >
            <Upload className="h-4 w-4" />
            {t("jobImport.title") || "Import Jobs"}
          </Button>
          )}
          <ColumnVisibilityControl
            columns={b2bColumnDefs}
            visibility={b2bVisibility}
            onSave={b2bSaveVisibility}
          />
        </div>

        <div>
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
            <div className="overflow-x-auto [overflow-y:clip]">
            <Table>
              <DraggableTableHeader
                columns={b2bColumnDefs}
                columnOrder={b2bColumnOrder}
                onReorder={b2bReorder}
                rowClassName="border-border bg-muted"
                visibility={b2bVisibility}
              />
              <TableBody>
                {filtered.map((job, idx) => {
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
                      {b2bColumnOrder.filter((key) => b2bVisibility[key] !== false).map((key) => renderB2BCell(key, job, locked))}
                    </TableRow>
                  );
                })}
              </TableBody>
            </Table>
            </div>
          )}
        </div>
      </div>

      <B2BJobImportModal
        open={importModalOpen}
        onOpenChange={setImportModalOpen}
        customers={customers}
        onImportComplete={fetchJobs}
      />
    </div>
  );
}
