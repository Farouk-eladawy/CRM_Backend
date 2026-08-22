"use client";

import { useEffect, useState, useCallback, useRef, useMemo } from "react";
import { toast } from "sonner";
import {
  CalendarClock,
  ChevronLeft,
  ChevronRight,
  Loader2,
  Plane,
  PlaneTakeoff,
  Bus,
  Car,
  Truck,
  Users,
  UserCheck,
  Download,
  Lock,
  LockOpen,
  DollarSign,
  Search,
  X,
  ChevronDown,
  Check,
  Eye,
} from "lucide-react";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { Badge } from "@/components/ui/badge";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Command,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
} from "@/components/ui/command";
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "@/components/ui/dialog";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Input } from "@/components/ui/input";
import api from "@/lib/api";
import { useT, useLocaleId } from "@/lib/i18n";
import { formatDate, cn } from "@/lib/utils";
import { useAuthStore } from "@/stores/auth-store";
import { usePermission } from "@/hooks/use-permission";
import { SERVICE_TYPE_COLORS_SOLID, useServiceTypeLabel } from "@/lib/service-types";

// ────────────────────────────────────────────
// Types
// ────────────────────────────────────────────

interface Job {
  id: string;
  internalRef: string;
  agentRef: string | null;
  bookingChannel: "ONLINE" | "B2B" | "B2C";
  serviceType: string;
  jobDate: string;
  status: string;
  adultCount: number;
  childCount: number;
  paxCount: number;
  clientName: string | null;
  clientMobile: string | null;
  custRepName: string | null;
  custRepMobile: string | null;
  custRepMeetingPoint: string | null;
  custRepMeetingTime: string | null;
  pickUpTime: string | null;
  dispatchUnlockedAt: string | null;
  agent?: { legalName: string; phone?: string | null } | null;
  customer?: { legalName: string; phone?: string | null } | null;
  originAirport?: { name: string; code: string } | null;
  originZone?: { name: string } | null;
  originHotel?: { name: string } | null;
  destinationAirport?: { name: string; code: string } | null;
  destinationZone?: { name: string } | null;
  destinationHotel?: { name: string } | null;
  fromZone?: { name: string } | null;
  toZone?: { name: string } | null;
  flight?: {
    flightNo: string;
    carrier: string;
    terminal?: string | null;
    arrivalTime?: string;
    departureTime?: string;
  } | null;
  assignment?: {
    id: string;
    vehicleId: string | null;
    driverId: string | null;
    repId: string | null;
    supplierId?: string | null;
    supplierCarTypeId?: string | null;
    externalDriverName?: string | null;
    externalDriverPhone?: string | null;
    remarks?: string | null;
    vehicle?: {
      plateNumber: string;
      supplierId?: string | null;
      vehicleType?: { name: string; seatCapacity: number };
    };
    supplierCarType?: {
      vehicleType?: { name: string; seatCapacity: number };
    } | null;
    driver?: { name: string; mobileNumber?: string };
    rep?: { name: string };
  } | null;
  collectionRequired: boolean;
  collectionAmount: number | null;
  collectionCurrency: string | null;
  jobExtras?: { name: string; qty: number }[];
  requestedVehicleTypeId: string | null;
  requestedVehicleType?: { id: string; name: string } | null;
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
  supplier?: { id: string; legalName: string; tradeName?: string | null } | null;
  isBusy?: boolean;
  isCarType?: boolean;
}

interface PersonResource {
  id: string;
  name: string;
  mobileNumber?: string;
  supplierId?: string | null;
}

type EditField = "source" | "vehicle" | "driver" | "rep" | "remarks";

interface ActiveCell {
  jobId: string;
  field: EditField;
}

// ────────────────────────────────────────────
// Helpers
// ────────────────────────────────────────────

const statusRowClass: Record<string, string> = {
  PENDING: "border-l-4 border-l-red-500",
  ASSIGNED: "border-l-4 border-l-emerald-500",
  IN_PROGRESS: "border-l-4 border-l-blue-500",
  COMPLETED: "border-l-4 border-l-zinc-500",
  CANCELLED: "border-l-4 border-l-red-900 bg-red-950/30",
};

function fmtDate(d: Date) {
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, "0");
  const day = String(d.getDate()).padStart(2, "0");
  return `${y}-${m}-${day}`;
}

function fmtTime(iso: string | undefined, locale = "en-US") {
  if (!iso) return "";
  const d = new Date(iso);
  // Operational times are Africa/Cairo regardless of the viewer's device timezone.
  return d.toLocaleTimeString(locale, { timeZone: "Africa/Cairo", hour: "2-digit", minute: "2-digit", hour12: false });
}

// ────────────────────────────────────────────
// Searchable Select Components
// ────────────────────────────────────────────

interface SelectOption {
  id: string;
  label: string;
  sublabel?: string;
  isBusy?: boolean;
}

/** Compact searchable dropdown for inline table cells */
function InlineSearchSelect({
  currentId,
  options,
  onSelect,
  onClose,
  placeholder,
}: {
  currentId: string;
  options: SelectOption[];
  onSelect: (id: string) => void;
  onClose: () => void;
  placeholder: string;
}) {
  const selected = options.find((o) => o.id === currentId);

  return (
    <Popover open={true} onOpenChange={(open) => { if (!open) onClose(); }}>
      <PopoverTrigger asChild>
        <button className="h-7 w-full rounded-sm border border-border bg-secondary px-2 text-xs text-left flex items-center justify-between focus:outline-none">
          <span className={cn("truncate", !selected && "text-muted-foreground")}>
            {selected ? selected.label : placeholder}
          </span>
          <ChevronDown className="ml-1 h-3 w-3 shrink-0 opacity-50" />
        </button>
      </PopoverTrigger>
      <PopoverContent className="w-64 p-0 z-50" align="start" sideOffset={2}>
        <Command>
          <CommandInput placeholder="Search..." className="h-8 text-xs" />
          <CommandList className="max-h-52">
            <CommandEmpty className="text-xs py-2 text-center text-muted-foreground">No results</CommandEmpty>
            <CommandGroup>
              {options.map((o) => (
                <CommandItem
                  key={o.id}
                  value={o.label}
                  onSelect={() => { onSelect(o.id); onClose(); }}
                  className="text-xs"
                >
                  <Check className={cn("mr-2 h-3 w-3 shrink-0", currentId === o.id ? "opacity-100" : "opacity-0")} />
                  <span className={cn(o.isBusy && "text-orange-500 dark:text-orange-400")}>{o.label}</span>
                  {o.sublabel && (
                    <span className="ml-auto text-muted-foreground shrink-0">{o.sublabel}</span>
                  )}
                  {o.isBusy && (
                    <span className="ml-1 shrink-0 text-[10px] font-medium text-orange-500 dark:text-orange-400">●</span>
                  )}
                </CommandItem>
              ))}
            </CommandGroup>
          </CommandList>
        </Command>
      </PopoverContent>
    </Popover>
  );
}

/** Full-width searchable combobox for dialog forms */
function DialogSearchSelect({
  value,
  options,
  onSelect,
  placeholder,
  emptyMessage,
}: {
  value: string;
  options: SelectOption[];
  onSelect: (id: string) => void;
  placeholder: string;
  emptyMessage?: string;
}) {
  const [open, setOpen] = useState(false);
  const selected = options.find((o) => o.id === value);

  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger asChild>
        <Button
          variant="outline"
          role="combobox"
          aria-expanded={open}
          className="w-full justify-between border-border bg-card text-foreground font-normal"
        >
          <span className={cn("truncate", !selected && "text-muted-foreground")}>
            {selected ? selected.label : placeholder}
          </span>
          <ChevronDown className="ml-2 h-4 w-4 shrink-0 opacity-50" />
        </Button>
      </PopoverTrigger>
      <PopoverContent className="w-full p-0" align="start">
        <Command>
          <CommandInput placeholder="Search..." />
          <CommandList className="max-h-52">
            <CommandEmpty>{emptyMessage || "No results"}</CommandEmpty>
            <CommandGroup>
              {options.map((o) => (
                <CommandItem
                  key={o.id}
                  value={o.label}
                  onSelect={() => { onSelect(o.id); setOpen(false); }}
                >
                  <Check className={cn("mr-2 h-4 w-4 shrink-0", value === o.id ? "opacity-100" : "opacity-0")} />
                  <span className={cn(o.isBusy && "text-orange-500 dark:text-orange-400")}>{o.label}</span>
                  {o.sublabel && (
                    <span className="ml-auto text-xs text-muted-foreground shrink-0">{o.sublabel}</span>
                  )}
                  {o.isBusy && (
                    <Badge variant="outline" className="ml-2 shrink-0 border-orange-500/40 text-orange-500 text-[10px] px-1">busy</Badge>
                  )}
                </CommandItem>
              ))}
            </CommandGroup>
          </CommandList>
        </Command>
      </PopoverContent>
    </Popover>
  );
}

// ────────────────────────────────────────────
// Editable Cell
// ────────────────────────────────────────────

function EditableSourceCell({
  job,
  vehicles,
  suppliers,
  selectedSource,
  isEditing,
  onStartEdit,
  onSelect,
  onCancel,
  cellRef,
  locked,
}: {
  job: Job;
  vehicles: VehicleResource[];
  suppliers: SupplierResource[];
  selectedSource: string;
  isEditing: boolean;
  onStartEdit: () => void;
  onSelect: (source: string) => void;
  onCancel: () => void;
  cellRef: (el: HTMLTableCellElement | null) => void;
  locked?: boolean;
}) {
  const t = useT();
  const ownedCount = vehicles.filter((v) => !v.supplierId).length;

  const sourceOptions: SelectOption[] = [
    { id: "owned", label: t("dispatch.ownedVehicles"), sublabel: String(ownedCount) },
    ...suppliers.map((s) => ({
      id: s.id,
      label: s.tradeName || s.legalName,
      sublabel: String(s.vehicleCount),
    })),
  ];

  // Derive display label for the current source
  const sourceLabel = selectedSource === "owned"
    ? t("dispatch.ownedVehicles")
    : selectedSource
      ? (suppliers.find((s) => s.id === selectedSource)?.tradeName ||
         suppliers.find((s) => s.id === selectedSource)?.legalName || "—")
      : "";

  if (locked) {
    return (
      <TableCell ref={cellRef} className="text-sm text-muted-foreground">
        {sourceLabel || "—"}
      </TableCell>
    );
  }

  if (isEditing) {
    return (
      <TableCell ref={cellRef} className="p-1">
        <InlineSearchSelect
          currentId={selectedSource}
          options={sourceOptions}
          onSelect={onSelect}
          onClose={onCancel}
          placeholder={t("dispatch.selectSource")}
        />
      </TableCell>
    );
  }

  return (
    <TableCell
      ref={cellRef}
      tabIndex={0}
      className="cursor-pointer text-sm focus:outline-none focus:ring-1 focus:ring-ring focus:ring-inset"
      onClick={onStartEdit}
      onKeyDown={(e) => {
        if (e.key === "Enter" || e.key === " ") {
          e.preventDefault();
          onStartEdit();
        }
      }}
    >
      {sourceLabel ? (
        <span className="text-muted-foreground text-xs">{sourceLabel}</span>
      ) : (
        <span className="text-orange-600 dark:text-orange-400 text-xs">{t("dispatch.selectSource")}</span>
      )}
    </TableCell>
  );
}

function EditableVehicleCell({
  job,
  vehicles,
  selectedSource,
  isEditing,
  onStartEdit,
  onSelect,
  onCancel,
  cellRef,
  locked,
}: {
  job: Job;
  vehicles: VehicleResource[];
  selectedSource: string;
  isEditing: boolean;
  onStartEdit: () => void;
  onSelect: (vehicleId: string) => void;
  onCancel: () => void;
  cellRef: (el: HTMLTableCellElement | null) => void;
  locked?: boolean;
}) {
  const t = useT();
  const current = job.assignment?.vehicle;
  const currentCarType = job.assignment?.supplierCarType;
  const vehicleLabel = current?.plateNumber ?? currentCarType?.vehicleType?.name ?? null;

  // Filter vehicles based on the source column selection
  const filteredVehicles = selectedSource === "owned"
    ? vehicles.filter((v) => !v.supplierId)
    : selectedSource
      ? vehicles.filter((v) => v.supplierId === selectedSource)
      : vehicles;

  if (locked) {
    return (
      <TableCell ref={cellRef} className="text-sm">
        {vehicleLabel ? (
          <Badge variant="outline" className="border-zinc-500/30 text-zinc-600 dark:text-zinc-400">
            {vehicleLabel}
          </Badge>
        ) : (
          <span className="text-muted-foreground/60 text-xs">—</span>
        )}
      </TableCell>
    );
  }

  if (isEditing) {
    const vehicleOptions: SelectOption[] = filteredVehicles.map((v) => ({
      id: v.id,
      label: v.isCarType ? v.plateNumber : `${v.plateNumber} — ${v.vehicleType?.name ?? ""}`,
      sublabel: v.vehicleType?.seatCapacity ? `${v.vehicleType.seatCapacity} seats` : undefined,
      isBusy: v.isBusy,
    }));
    const currentId = job.assignment?.supplierCarTypeId || job.assignment?.vehicleId || "";
    return (
      <TableCell ref={cellRef} className="p-1">
        <InlineSearchSelect
          currentId={currentId}
          options={vehicleOptions}
          onSelect={onSelect}
          onClose={onCancel}
          placeholder={t("dispatch.select")}
        />
      </TableCell>
    );
  }

  return (
    <TableCell
      ref={cellRef}
      tabIndex={0}
      className="cursor-pointer text-sm focus:outline-none focus:ring-1 focus:ring-ring focus:ring-inset"
      onClick={onStartEdit}
      onKeyDown={(e) => {
        if (e.key === "Enter" || e.key === " ") {
          e.preventDefault();
          onStartEdit();
        }
      }}
    >
      {vehicleLabel ? (
        <Badge
          variant="outline"
          className="border-emerald-500/30 text-emerald-600 dark:text-emerald-400"
        >
          {vehicleLabel}
        </Badge>
      ) : (
        <span className="text-muted-foreground text-xs">{t("dispatch.clickToAssign")}</span>
      )}
    </TableCell>
  );
}

function EditablePersonCell({
  job,
  field,
  resources,
  selectedSource,
  isEditing,
  onStartEdit,
  onSelect,
  onExternalDriver,
  onCancel,
  cellRef,
  locked,
  allowWithoutAssignment,
}: {
  job: Job;
  field: "driver" | "rep";
  resources: PersonResource[];
  selectedSource?: string;
  isEditing: boolean;
  onStartEdit: () => void;
  onSelect: (id: string) => void;
  onExternalDriver?: (name: string, phone: string) => void;
  onCancel: () => void;
  cellRef: (el: HTMLTableCellElement | null) => void;
  locked?: boolean;
  allowWithoutAssignment?: boolean;
}) {
  const t = useT();
  const currentId =
    field === "driver" ? job.assignment?.driverId : job.assignment?.repId;
  const currentName =
    field === "driver"
      ? (job.assignment?.driver?.name || job.assignment?.externalDriverName)
      : job.assignment?.rep?.name;
  const canEdit = !locked && (!!job.assignment || !!allowWithoutAssignment);
  const isSupplierDriver = field === "driver" && selectedSource && selectedSource !== "owned";

  // Filter drivers by source (owned vs supplier), reps show all
  const filteredResources = field === "driver" && selectedSource
    ? selectedSource === "owned"
      ? resources.filter((r) => !r.supplierId)
      : resources.filter((r) => r.supplierId === selectedSource)
    : resources;

  // Supplier driver: show text inputs for name + phone
  if (isSupplierDriver && isEditing && canEdit) {
    return (
      <ExternalDriverInput
        job={job}
        onSave={(name, phone) => {
          onExternalDriver?.(name, phone);
        }}
        onCancel={onCancel}
        cellRef={cellRef}
      />
    );
  }

  if (isEditing && canEdit) {
    const personOptions: SelectOption[] = [
      { id: "__none__", label: t("dispatch.none") },
      ...filteredResources.map((r) => ({
        id: r.id,
        label: r.name,
        sublabel: r.mobileNumber,
      })),
    ];
    return (
      <TableCell ref={cellRef} className="p-1">
        <InlineSearchSelect
          currentId={currentId || ""}
          options={personOptions}
          onSelect={onSelect}
          onClose={onCancel}
          placeholder={t("dispatch.select")}
        />
      </TableCell>
    );
  }

  return (
    <TableCell
      ref={cellRef}
      tabIndex={canEdit ? 0 : -1}
      className={`text-sm text-muted-foreground ${canEdit ? "cursor-pointer focus:outline-none focus:ring-1 focus:ring-ring focus:ring-inset" : ""}`}
      onClick={canEdit ? onStartEdit : undefined}
      onKeyDown={
        canEdit
          ? (e) => {
              if (e.key === "Enter" || e.key === " ") {
                e.preventDefault();
                onStartEdit();
              }
            }
          : undefined
      }
    >
      {currentName ? (
        <div>
          <span>{currentName}</span>
          {field === "driver" && (job.assignment?.driver?.mobileNumber || job.assignment?.externalDriverPhone) && (
            <div className="text-[10px] text-muted-foreground/70 font-mono">
              {job.assignment?.driver?.mobileNumber || job.assignment?.externalDriverPhone}
            </div>
          )}
        </div>
      ) : (
        <span
          className={
            field === "driver" ? "text-yellow-600 dark:text-yellow-400 text-xs" : "text-muted-foreground/60 text-xs"
          }
        >
          —
        </span>
      )}
    </TableCell>
  );
}

// ────────────────────────────────────────────
// External Driver Input (for supplier drivers)
// ────────────────────────────────────────────

function ExternalDriverInput({
  job,
  onSave,
  onCancel,
  cellRef,
}: {
  job: Job;
  onSave: (name: string, phone: string) => void;
  onCancel: () => void;
  cellRef: (el: HTMLTableCellElement | null) => void;
}) {
  const t = useT();
  const [name, setName] = useState(job.assignment?.externalDriverName || "");
  const [phone, setPhone] = useState(job.assignment?.externalDriverPhone || "");
  const nameRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    nameRef.current?.focus();
  }, []);

  const handleSave = () => {
    onSave(name.trim(), phone.trim());
  };

  return (
    <TableCell ref={cellRef} className="p-1">
      <div className="flex flex-col gap-0.5">
        <input
          ref={nameRef}
          type="text"
          value={name}
          onChange={(e) => setName(e.target.value)}
          placeholder={t("dispatch.externalDriverName")}
          className="h-6 w-full rounded border border-border bg-secondary px-1.5 text-xs text-foreground placeholder:text-muted-foreground/50 focus:outline-none focus:ring-1 focus:ring-ring"
          onKeyDown={(e) => {
            if (e.key === "Enter") handleSave();
            if (e.key === "Escape") onCancel();
          }}
        />
        <input
          type="text"
          value={phone}
          onChange={(e) => setPhone(e.target.value)}
          placeholder={t("dispatch.externalDriverPhone")}
          className="h-6 w-full rounded border border-border bg-secondary px-1.5 text-xs text-foreground placeholder:text-muted-foreground/50 focus:outline-none focus:ring-1 focus:ring-ring"
          onKeyDown={(e) => {
            if (e.key === "Enter") handleSave();
            if (e.key === "Escape") onCancel();
          }}
          onBlur={handleSave}
        />
      </div>
    </TableCell>
  );
}

// ────────────────────────────────────────────
// Editable Remarks Cell
// ────────────────────────────────────────────

function EditableRemarksCell({
  job,
  isEditing,
  onStartEdit,
  onSave,
  onCancel,
  cellRef,
  locked,
}: {
  job: Job;
  isEditing: boolean;
  onStartEdit: () => void;
  onSave: (value: string) => void;
  onCancel: () => void;
  cellRef: (el: HTMLTableCellElement | null) => void;
  locked?: boolean;
}) {
  const t = useT();
  const [value, setValue] = useState(job.assignment?.remarks || "");
  const inputRef = useRef<HTMLInputElement>(null);
  const canEdit = !locked && !!job.assignment;

  useEffect(() => {
    if (isEditing) {
      setValue(job.assignment?.remarks || "");
      setTimeout(() => inputRef.current?.focus(), 0);
    }
  }, [isEditing, job.assignment?.remarks]);

  if (isEditing && canEdit) {
    return (
      <TableCell ref={cellRef} className="p-1">
        <input
          ref={inputRef}
          type="text"
          value={value}
          onChange={(e) => setValue(e.target.value)}
          placeholder={t("dispatch.remarks")}
          className="h-7 w-full rounded border border-border bg-secondary px-1.5 text-xs text-foreground placeholder:text-muted-foreground/50 focus:outline-none focus:ring-1 focus:ring-ring"
          onKeyDown={(e) => {
            if (e.key === "Enter") {
              onSave(value.trim());
            }
            if (e.key === "Escape") onCancel();
          }}
          onBlur={() => onSave(value.trim())}
        />
      </TableCell>
    );
  }

  return (
    <TableCell
      ref={cellRef}
      tabIndex={canEdit ? 0 : -1}
      className={`text-sm text-muted-foreground ${canEdit ? "cursor-pointer focus:outline-none focus:ring-1 focus:ring-ring focus:ring-inset" : ""}`}
      onClick={canEdit ? onStartEdit : undefined}
      onKeyDown={
        canEdit
          ? (e) => {
              if (e.key === "Enter" || e.key === " ") {
                e.preventDefault();
                onStartEdit();
              }
            }
          : undefined
      }
    >
      {job.assignment?.remarks ? (
        <span className="text-xs">{job.assignment.remarks}</span>
      ) : (
        <span className="text-muted-foreground/60 text-xs">—</span>
      )}
    </TableCell>
  );
}

// ────────────────────────────────────────────
// SummaryFooter
// ────────────────────────────────────────────

function SummaryFooter({
  arrivals,
  departures,
  cityTransfers,
}: {
  arrivals: Job[];
  departures: Job[];
  cityTransfers: Job[];
}) {
  const t = useT();
  const all = [...arrivals, ...departures, ...cityTransfers];
  const total = all.length;
  const assigned = all.filter((j) => j.assignment).length;
  const pending = all.filter((j) => j.status === "PENDING").length;
  const completed = all.filter((j) => j.status === "COMPLETED").length;
  const totalPax = all.reduce((s, j) => s + j.paxCount, 0);

  return (
    <div className="sticky bottom-0 z-10 border-t border-border bg-popover/95 backdrop-blur px-4 py-3">
      <div className="flex items-center justify-between text-sm">
        <div className="flex gap-6 text-muted-foreground">
          <span>
            {t("dispatch.total")}{" "}
            <span className="font-medium text-foreground">{total}</span>
          </span>
          <span>
            {t("dispatch.arr")}{" "}
            <span className="font-medium text-foreground">{arrivals.length}</span>
          </span>
          <span>
            {t("dispatch.dep")}{" "}
            <span className="font-medium text-foreground">
              {departures.length}
            </span>
          </span>
          <span>
            {t("dispatch.otherLabel")}{" "}
            <span className="font-medium text-foreground">
              {cityTransfers.length}
            </span>
          </span>
          <span className="border-l border-border pl-6">
            {t("dispatch.paxLabel")}{" "}
            <span className="font-medium text-foreground">{totalPax}</span>
          </span>
        </div>
        <div className="flex gap-6 text-muted-foreground">
          <span>
            {t("dispatch.assignedLabel")}{" "}
            <span className="font-medium text-emerald-600 dark:text-emerald-400">
              {assigned}/{total}
            </span>
          </span>
          <span>
            {t("dispatch.pendingLabel")}{" "}
            <span className="font-medium text-amber-600 dark:text-amber-400">{pending}</span>
          </span>
          <span>
            {t("dispatch.completedLabel")}{" "}
            <span className="font-medium text-blue-600 dark:text-blue-400">{completed}</span>
          </span>
          <span className="border-l border-border pl-6">
            {t("dispatch.rate")}{" "}
            <span className="font-medium text-foreground">
              {total > 0 ? Math.round((assigned / total) * 100) : 0}%
            </span>
          </span>
        </div>
      </div>
    </div>
  );
}

// ────────────────────────────────────────────
// ────────────────────────────────────────────
// Shared Extras & Collection cells
// ────────────────────────────────────────────

function ExtrasCell({ job }: { job: Job }) {
  const parts = (job.jobExtras || [])
    .filter((e) => e.qty > 0)
    .map((e) => `${e.name}×${e.qty}`)
    .join(", ");
  return (
    <TableCell className="text-xs text-muted-foreground whitespace-nowrap">
      {parts || "—"}
    </TableCell>
  );
}

function CollectionCells({ job }: { job: Job }) {
  return (
    <>
      <TableCell className="text-xs text-center whitespace-nowrap">
        {job.collectionRequired && job.collectionAmount
          ? <span className="text-amber-500 font-medium">{job.collectionAmount}</span>
          : "—"}
      </TableCell>
      <TableCell className="text-xs text-center">
        {job.collectionRequired
          ? <span className="text-amber-500">{job.collectionCurrency}</span>
          : "—"}
      </TableCell>
    </>
  );
}

// ────────────────────────────────────────────
// JobDetailModal – read-only full job view
// ────────────────────────────────────────────

function DetailRow({ label, value, phone }: { label: string; value?: string | number | null; phone?: boolean }) {
  if (value === null || value === undefined || value === "") return null;
  const str = String(value);
  return (
    <div className="flex gap-2 text-sm">
      <span className="w-40 shrink-0 text-muted-foreground">{label}</span>
      {phone ? (
        <a href={`tel:${str}`} className="text-blue-500 underline break-words">{str}</a>
      ) : (
        <span className="text-foreground break-words">{str}</span>
      )}
    </div>
  );
}

function DetailSection({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="space-y-1.5">
      <p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground/60 border-b border-border pb-1">
        {title}
      </p>
      {children}
    </div>
  );
}

function JobDetailModal({ job, open, onClose, locale }: { job: Job | null; open: boolean; onClose: () => void; locale: string }) {
  const serviceTypeLabel = useServiceTypeLabel();
  if (!job) return null;

  const origin =
    job.originAirport ? `${job.originAirport.name} (${job.originAirport.code})`
    : job.originHotel?.name || job.originZone?.name || job.fromZone?.name || "—";

  const destination =
    job.destinationAirport ? `${job.destinationAirport.name} (${job.destinationAirport.code})`
    : job.destinationHotel?.name || job.destinationZone?.name || job.toZone?.name || "—";

  const isOwned = !job.assignment?.supplierId;
  const vehicleTypeName =
    job.assignment?.vehicle?.vehicleType?.name ||
    job.assignment?.supplierCarType?.vehicleType?.name || null;
  const seatCapacity =
    job.assignment?.vehicle?.vehicleType?.seatCapacity ||
    job.assignment?.supplierCarType?.vehicleType?.seatCapacity || null;
  const driverName = isOwned
    ? job.assignment?.driver?.name
    : job.assignment?.externalDriverName;
  const driverMobile = isOwned
    ? job.assignment?.driver?.mobileNumber
    : job.assignment?.externalDriverPhone;

  const extras: string[] = (job.jobExtras || [])
    .filter((e) => e.qty > 0)
    .map((e) => `${e.name} ×${e.qty}`);

  return (
    <Dialog open={open} onOpenChange={(v) => { if (!v) onClose(); }}>
      <DialogContent className="max-h-[90vh] overflow-y-auto" style={{ width: "85vw", maxWidth: "85vw" }}>
        <DialogHeader>
          <DialogTitle className="font-mono text-base">{job.internalRef}</DialogTitle>
        </DialogHeader>

        <div className="pt-2" style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "50px" }}>
          {/* Left column */}
          <div className="space-y-5">
            <DetailSection title="Identification">
              <DetailRow label="Internal Ref" value={job.internalRef} />
              <DetailRow label="Agent Ref" value={job.agentRef} />
            </DetailSection>

            <DetailSection title="Booking">
              <DetailRow label="Booking Channel" value={job.bookingChannel === "B2C" ? "B2C Website" : job.bookingChannel} />
              {job.bookingChannel === "ONLINE" || job.bookingChannel === "B2C" ? (
                <>
                  <DetailRow label="Agent" value={job.agent?.legalName} />
                  <DetailRow label="Agent Phone" value={job.agent?.phone} phone />
                </>
              ) : (
                <>
                  <DetailRow label="Customer" value={job.customer?.legalName} />
                  <DetailRow label="Customer Phone" value={job.customer?.phone} phone />
                </>
              )}
            </DetailSection>

            <DetailSection title="Service & Status">
              <DetailRow label="Service Type" value={serviceTypeLabel(job.serviceType)} />
              <DetailRow label="Job Date" value={job.jobDate ? new Date(job.jobDate).toLocaleDateString() : null} />
              <DetailRow label="Status" value={job.status} />
            </DetailSection>

            <DetailSection title="Passengers">
              <DetailRow label="Client Name" value={job.clientName} />
              <DetailRow label="Client Number" value={job.clientMobile} phone />
              <DetailRow label="Adults" value={job.adultCount} />
              <DetailRow label="Children" value={job.childCount} />
              <DetailRow label="Total Pax" value={job.paxCount} />
            </DetailSection>

            <DetailSection title="Route">
              <DetailRow label="Origin" value={origin} />
              <DetailRow label="Destination" value={destination} />
            </DetailSection>

            {job.flight && (
              <DetailSection title="Flight">
                <DetailRow label="Flight Number" value={job.flight.flightNo} />
                <DetailRow label="Carrier" value={job.flight.carrier} />
                <DetailRow label="Terminal" value={job.flight.terminal} />
                {job.serviceType === "DEP"
                  ? job.flight.departureTime && (
                      <DetailRow
                        label="Departure Flight Time"
                        value={fmtTime(job.flight.departureTime, locale)}
                      />
                    )
                  : job.flight.arrivalTime && (
                      <DetailRow
                        label="Arrival Flight Time"
                        value={fmtTime(job.flight.arrivalTime, locale)}
                      />
                    )}
              </DetailSection>
            )}

            <DetailSection title="Timing">
              <DetailRow label="Pick Up Time" value={job.pickUpTime ? fmtTime(job.pickUpTime, locale) : null} />
            </DetailSection>
          </div>

          {/* Right column */}
          <div className="space-y-5">
            {(job.custRepName || job.custRepMobile || job.custRepMeetingPoint || job.custRepMeetingTime) && (
              <DetailSection title="Customer Rep Contact">
                <DetailRow label="Rep Name" value={job.custRepName} />
                <DetailRow label="Rep Mobile" value={job.custRepMobile} phone />
                <DetailRow label="Meeting Point" value={job.custRepMeetingPoint} />
                <DetailRow label="Meeting Time" value={job.custRepMeetingTime} />
              </DetailSection>
            )}

            {job.assignment && (
              <DetailSection title="Assignment">
                <DetailRow label="Vehicle Source" value={isOwned ? "Owned" : "Supplier"} />
                <DetailRow label="Vehicle Plate" value={job.assignment.vehicle?.plateNumber} />
                <DetailRow label="Vehicle Type" value={vehicleTypeName} />
                <DetailRow label="Seat Capacity" value={seatCapacity} />
                <DetailRow label="Driver Name" value={driverName} />
                <DetailRow label="Driver Mobile" value={driverMobile} phone />
                <DetailRow label="Rep" value={job.assignment.rep?.name} />
                <DetailRow label="Remarks" value={job.assignment.remarks} />
              </DetailSection>
            )}

            {job.requestedVehicleType && (
              <DetailSection title="Requested Vehicle">
                <DetailRow label="Vehicle Type" value={job.requestedVehicleType.name} />
              </DetailSection>
            )}

            {extras.length > 0 && (
              <DetailSection title="Extras">
                {extras.map((e) => (
                  <DetailRow key={e} label="" value={e} />
                ))}
              </DetailSection>
            )}

            {job.collectionRequired && (
              <DetailSection title="Collection">
                <DetailRow label="Amount" value={job.collectionAmount} />
                <DetailRow label="Currency" value={job.collectionCurrency} />
              </DetailSection>
            )}
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}

// JobGrid with inline editing
// ────────────────────────────────────────────

function JobGrid({
  jobs,
  title,
  icon: Icon,
  activeCell,
  vehicles,
  suppliers,
  drivers,
  reps,
  jobSources,
  setJobSource,
  onStartEdit,
  onCancelEdit,
  onInlineAssign,
  onDialogAssign,
  locked,
  showLockColumn,
  canUnlock,
  onToggleLock,
  showPickUpTime,
  canAssignVehicle = true,
  canAssignRep = true,
  savedRowId,
}: {
  jobs: Job[];
  title: string;
  icon: React.ElementType;
  activeCell: ActiveCell | null;
  vehicles: VehicleResource[];
  suppliers: SupplierResource[];
  drivers: PersonResource[];
  reps: PersonResource[];
  jobSources: Record<string, string>;
  setJobSource: (jobId: string, source: string) => void;
  onStartEdit: (jobId: string, field: EditField) => void;
  onCancelEdit: () => void;
  onInlineAssign: (
    job: Job,
    field: EditField,
    value: string
  ) => void;
  onDialogAssign: (job: Job) => void;
  locked?: boolean;
  showLockColumn?: boolean;
  canUnlock?: boolean;
  onToggleLock?: (jobId: string, unlock: boolean) => void;
  showPickUpTime?: boolean;
  canAssignVehicle?: boolean;
  canAssignRep?: boolean;
  savedRowId?: string | null;
}) {
  const [detailJob, setDetailJob] = useState<Job | null>(null);
  const t = useT();
  const locale = useLocaleId();
  const cellRefs = useRef<Map<string, HTMLTableCellElement>>(new Map());

  const setCellRef = useCallback(
    (jobId: string, field: EditField) =>
      (el: HTMLTableCellElement | null) => {
        const key = `${jobId}-${field}`;
        if (el) cellRefs.current.set(key, el);
        else cellRefs.current.delete(key);
      },
    []
  );

  // Keyboard navigation between cells
  const handleCellKeyDown = useCallback(
    (e: React.KeyboardEvent, jobId: string, field: EditField) => {
      const fields: EditField[] = ["source", "vehicle", "driver", "rep", "remarks"];
      const fieldIdx = fields.indexOf(field);
      const jobIdx = jobs.findIndex((j) => j.id === jobId);

      if (e.key === "Tab") {
        e.preventDefault();
        let nextFieldIdx = e.shiftKey ? fieldIdx - 1 : fieldIdx + 1;
        let nextJobIdx = jobIdx;

        if (nextFieldIdx >= fields.length) {
          nextFieldIdx = 0;
          nextJobIdx++;
        } else if (nextFieldIdx < 0) {
          nextFieldIdx = fields.length - 1;
          nextJobIdx--;
        }

        if (nextJobIdx >= 0 && nextJobIdx < jobs.length) {
          const nextKey = `${jobs[nextJobIdx].id}-${fields[nextFieldIdx]}`;
          cellRefs.current.get(nextKey)?.focus();
        }
      } else if (e.key === "ArrowDown" && jobIdx < jobs.length - 1) {
        e.preventDefault();
        const nextKey = `${jobs[jobIdx + 1].id}-${field}`;
        cellRefs.current.get(nextKey)?.focus();
      } else if (e.key === "ArrowUp" && jobIdx > 0) {
        e.preventDefault();
        const nextKey = `${jobs[jobIdx - 1].id}-${field}`;
        cellRefs.current.get(nextKey)?.focus();
      }
    },
    [jobs]
  );

  if (jobs.length === 0) {
    return (
      <Card className="border-border bg-card p-6">
        <div className="flex flex-col items-center justify-center py-8 text-muted-foreground/60">
          <Icon className="mb-2 h-8 w-8" />
          <p className="text-sm">{t(`dispatch.no${title}Jobs`)}</p>
        </div>
      </Card>
    );
  }

  return (
    <>
    <JobDetailModal job={detailJob} open={!!detailJob} onClose={() => setDetailJob(null)} locale={locale} />
    <div className="overflow-x-auto [overflow-y:clip]">
      <Table>
        <TableHeader>
          <TableRow className="border-border bg-muted">
            <TableHead className="text-muted-foreground text-xs w-8" />
            {showLockColumn && <TableHead className="text-muted-foreground text-xs w-8" />}
            <TableHead className="text-muted-foreground text-xs w-28">{t("dispatch.ref")}</TableHead>
            <TableHead className="text-muted-foreground text-xs">{t("dispatch.agent")}</TableHead>
            <TableHead className="text-muted-foreground text-xs">{t("dispatch.route")}</TableHead>
            <TableHead className="text-muted-foreground text-xs w-14">{t("dispatch.pax")}</TableHead>
            <TableHead className="text-muted-foreground text-xs w-24">Req. Type</TableHead>
            <TableHead className="text-muted-foreground text-xs w-24">{t("jobs.flightNumber")}</TableHead>
            <TableHead className="text-muted-foreground text-xs w-20">Flight Time</TableHead>
            {showPickUpTime && <TableHead className="text-muted-foreground text-xs w-20">{t("jobs.pickUpTime")}</TableHead>}
            <TableHead className="text-muted-foreground text-xs w-20">Terminal</TableHead>
            <TableHead className="text-muted-foreground text-xs w-36">{t("dispatch.carSource")}</TableHead>
            <TableHead className="text-muted-foreground text-xs w-36">{t("dispatch.vehicle")}</TableHead>
            <TableHead className="text-muted-foreground text-xs w-32">{t("dispatch.driver")}</TableHead>
            <TableHead className="text-muted-foreground text-xs w-32">{t("dispatch.rep")}</TableHead>
            <TableHead className="text-muted-foreground text-xs w-32">{t("dispatch.remarks")}</TableHead>
            <TableHead className="text-muted-foreground text-xs w-28">{t("jobs.extras")}</TableHead>
            <TableHead className="text-muted-foreground text-xs w-20">Coll. Amt</TableHead>
            <TableHead className="text-muted-foreground text-xs w-16">Coll. Cur</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {jobs.map((job, idx) => {
            const isJobLocked = locked && !job.dispatchUnlockedAt;
            const isEditable =
              !isJobLocked && (job.status === "PENDING" || job.status === "ASSIGNED");
            const stripe = idx % 2 === 0 ? "bg-gray-100/25 dark:bg-gray-800/25" : "bg-gray-200/50 dark:bg-gray-700/50";
            const jobSource = jobSources[job.id] || "";

            return (
              <TableRow
                key={job.id}
                className={`border-border transition-colors duration-300 ${statusRowClass[job.status] || stripe} ${job.status === "CANCELLED" ? "[&_td]:line-through [&_td]:text-red-900 dark:[&_td]:text-red-800" : ""} ${savedRowId === job.id ? "bg-green-500/10" : ""}`}
              >
                <TableCell className="w-8 px-1">
                  <button
                    type="button"
                    onClick={() => setDetailJob(job)}
                    className="flex h-6 w-6 items-center justify-center rounded hover:bg-muted/50 transition-colors"
                    title="View job details"
                  >
                    <Eye className="h-3.5 w-3.5 text-muted-foreground/60 hover:text-foreground transition-colors" />
                  </button>
                </TableCell>
                {showLockColumn && (
                  <TableCell className="w-8 px-1">
                    {canUnlock && onToggleLock ? (
                      <button
                        type="button"
                        onClick={() => onToggleLock(job.id, !job.dispatchUnlockedAt)}
                        className="flex h-6 w-6 items-center justify-center rounded hover:bg-muted/50 transition-colors"
                        title={job.dispatchUnlockedAt ? t("dispatch.lockJob") : t("dispatch.unlockJob")}
                      >
                        {job.dispatchUnlockedAt ? (
                          <LockOpen className="h-3.5 w-3.5 text-emerald-500" />
                        ) : (
                          <Lock className="h-3.5 w-3.5 text-amber-500" />
                        )}
                      </button>
                    ) : (
                      job.dispatchUnlockedAt ? (
                        <LockOpen className="h-3.5 w-3.5 text-emerald-500/60 mx-auto" />
                      ) : (
                        <Lock className="h-3.5 w-3.5 text-amber-500/60 mx-auto" />
                      )
                    )}
                  </TableCell>
                )}
                <TableCell
                  className="text-foreground font-mono text-xs cursor-pointer"
                  onClick={() => isEditable && onDialogAssign(job)}
                  title={t("dispatch.fullAssignTitle")}
                >
                  {job.internalRef}
                </TableCell>
                <TableCell className="text-muted-foreground text-sm">
                  {job.bookingChannel === "ONLINE" || job.bookingChannel === "B2C"
                    ? job.agent?.legalName || "—"
                    : job.customer?.legalName || "—"}
                </TableCell>
                <TableCell className="text-muted-foreground text-xs">
                  {job.originAirport?.code || job.originHotel?.name || job.originZone?.name || job.fromZone?.name || "\u2014"} → {job.destinationAirport?.code || job.destinationHotel?.name || job.destinationZone?.name || job.toZone?.name || "\u2014"}
                </TableCell>
                <TableCell className="text-muted-foreground text-center">
                  <span className="flex items-center justify-center gap-0.5">
                    {job.paxCount}
                    {job.collectionRequired && (
                      <span title={`${job.collectionAmount} ${job.collectionCurrency}`}>
                        <DollarSign className="h-3 w-3 text-amber-500" />
                      </span>
                    )}
                  </span>
                </TableCell>
                <TableCell className="text-xs">
                  {job.requestedVehicleType ? (
                    <Badge
                      variant="outline"
                      className={
                        job.assignment?.vehicle?.vehicleType &&
                        job.requestedVehicleTypeId &&
                        job.assignment.vehicle.vehicleType.name !== job.requestedVehicleType.name
                          ? "border-amber-500/50 bg-amber-500/10 text-amber-600 dark:text-amber-400"
                          : "border-border text-muted-foreground"
                      }
                    >
                      {job.requestedVehicleType.name}
                    </Badge>
                  ) : (
                    <span className="text-muted-foreground/60">—</span>
                  )}
                </TableCell>
                <TableCell className="text-muted-foreground text-xs font-mono">
                  {job.flight?.flightNo || "—"}
                </TableCell>
                <TableCell className="text-muted-foreground text-xs font-mono">
                  {job.flight
                    ? fmtTime(
                        job.serviceType === "DEP"
                          ? job.flight.departureTime
                          : job.flight.arrivalTime,
                        locale,
                      ) || "—"
                    : "—"}
                </TableCell>
                {showPickUpTime && (
                  <TableCell className="text-muted-foreground text-xs font-mono">
                    {fmtTime(job.pickUpTime ?? undefined, locale) || "—"}
                  </TableCell>
                )}
                <TableCell className="text-muted-foreground text-xs font-mono">
                  {job.flight?.terminal || "—"}
                </TableCell>

                {isEditable ? (
                  <>
                    {canAssignVehicle ? (
                      <EditableSourceCell
                        job={job}
                        vehicles={vehicles}
                        suppliers={suppliers}
                        selectedSource={jobSource}
                        isEditing={
                          activeCell?.jobId === job.id &&
                          activeCell?.field === "source"
                        }
                        onStartEdit={() => onStartEdit(job.id, "source")}
                        onSelect={(val) => {
                          setJobSource(job.id, val);
                          onCancelEdit();
                        }}
                        onCancel={onCancelEdit}
                        cellRef={setCellRef(job.id, "source")}
                        locked={isJobLocked}
                      />
                    ) : (
                      <TableCell className="text-sm text-muted-foreground">—</TableCell>
                    )}
                    {canAssignVehicle ? (
                      <EditableVehicleCell
                        job={job}
                        vehicles={vehicles}
                        selectedSource={jobSource}
                        isEditing={
                          activeCell?.jobId === job.id &&
                          activeCell?.field === "vehicle"
                        }
                        onStartEdit={() => onStartEdit(job.id, "vehicle")}
                        onSelect={(val) =>
                          onInlineAssign(job, "vehicle", val)
                        }
                        onCancel={onCancelEdit}
                        cellRef={setCellRef(job.id, "vehicle")}
                        locked={isJobLocked}
                      />
                    ) : (
                      <TableCell className="text-sm">
                        {job.assignment?.vehicle ? (
                          <Badge variant="outline" className="border-zinc-500/30 text-zinc-600 dark:text-zinc-400">
                            {job.assignment.vehicle.plateNumber}
                          </Badge>
                        ) : (
                          <span className="text-muted-foreground/60 text-xs">—</span>
                        )}
                      </TableCell>
                    )}
                    {canAssignVehicle ? (
                      <EditablePersonCell
                        job={job}
                        field="driver"
                        resources={drivers}
                        selectedSource={jobSource}
                        isEditing={
                          activeCell?.jobId === job.id &&
                          activeCell?.field === "driver"
                        }
                        onStartEdit={() => onStartEdit(job.id, "driver")}
                        onSelect={(val) =>
                          onInlineAssign(job, "driver", val)
                        }
                        onExternalDriver={(name, phone) =>
                          onInlineAssign(job, "driver", `__external__:${name}:${phone}`)
                        }
                        onCancel={onCancelEdit}
                        cellRef={setCellRef(job.id, "driver")}
                        locked={isJobLocked}
                      />
                    ) : (
                      <TableCell className="text-sm text-muted-foreground">
                        {job.assignment?.driver?.name || job.assignment?.externalDriverName || "—"}
                      </TableCell>
                    )}
                    {canAssignRep ? (
                      <EditablePersonCell
                        job={job}
                        field="rep"
                        resources={reps}
                        isEditing={
                          activeCell?.jobId === job.id &&
                          activeCell?.field === "rep"
                        }
                        onStartEdit={() => onStartEdit(job.id, "rep")}
                        onSelect={(val) =>
                          onInlineAssign(job, "rep", val)
                        }
                        onCancel={onCancelEdit}
                        cellRef={setCellRef(job.id, "rep")}
                        locked={isJobLocked}
                        allowWithoutAssignment={!canAssignVehicle}
                      />
                    ) : (
                      <TableCell className="text-sm text-muted-foreground">
                        {job.assignment?.rep?.name || "—"}
                      </TableCell>
                    )}
                    <EditableRemarksCell
                      job={job}
                      isEditing={
                        activeCell?.jobId === job.id &&
                        activeCell?.field === "remarks"
                      }
                      onStartEdit={() => onStartEdit(job.id, "remarks")}
                      onSave={(val) =>
                        onInlineAssign(job, "remarks", val)
                      }
                      onCancel={onCancelEdit}
                      cellRef={setCellRef(job.id, "remarks")}
                      locked={isJobLocked}
                    />
                    <ExtrasCell job={job} />
                    <CollectionCells job={job} />
                  </>
                ) : (
                  <>
                    <TableCell className="text-sm text-muted-foreground">
                      {(() => {
                        const v = job.assignment?.vehicleId
                          ? vehicles.find((veh) => veh.id === job.assignment?.vehicleId)
                          : null;
                        if (!v) return "—";
                        if (!v.supplierId) return t("dispatch.ownedVehicles");
                        const s = suppliers.find((sup) => sup.id === v.supplierId);
                        return s?.tradeName || s?.legalName || "—";
                      })()}
                    </TableCell>
                    <TableCell className="text-sm">
                      {job.assignment?.vehicle ? (
                        <Badge
                          variant="outline"
                          className={
                            job.requestedVehicleTypeId &&
                            job.assignment.vehicle.vehicleType &&
                            job.requestedVehicleType &&
                            job.assignment.vehicle.vehicleType.name !== job.requestedVehicleType.name
                              ? "border-amber-500/50 bg-amber-500/10 text-amber-600 dark:text-amber-400"
                              : "border-zinc-500/30 text-zinc-600 dark:text-zinc-400"
                          }
                        >
                          {job.assignment.vehicle.plateNumber}
                        </Badge>
                      ) : (
                        <span className="text-muted-foreground/60 text-xs">—</span>
                      )}
                    </TableCell>
                    <TableCell className="text-sm text-muted-foreground">
                      {(job.assignment?.driver?.name || job.assignment?.externalDriverName) ? (
                        <div>
                          <span>{job.assignment?.driver?.name || job.assignment?.externalDriverName}</span>
                          {(job.assignment?.driver?.mobileNumber || job.assignment?.externalDriverPhone) && (
                            <div className="text-[10px] text-muted-foreground/70 font-mono">
                              {job.assignment?.driver?.mobileNumber || job.assignment?.externalDriverPhone}
                            </div>
                          )}
                        </div>
                      ) : "—"}
                    </TableCell>
                    <TableCell className="text-sm text-muted-foreground">
                      {job.assignment?.rep?.name || "—"}
                    </TableCell>
                    <TableCell className="text-sm text-muted-foreground">
                      {job.assignment?.remarks ? (
                        <span className="text-xs">{job.assignment.remarks}</span>
                      ) : "—"}
                    </TableCell>
                    <ExtrasCell job={job} />
                    <CollectionCells job={job} />
                  </>
                )}
              </TableRow>
            );
          })}
        </TableBody>
      </Table>
    </div>
    </>
  );
}

// ────────────────────────────────────────────
// VehicleFleetOverview
// ────────────────────────────────────────────

// CONFLICT_WINDOW_MS removed — conflict detection disabled per user request

function getJobTime(job: Job): Date | null {
  const iso =
    job.serviceType === "ARR"
      ? (job.flight?.arrivalTime ?? job.pickUpTime)
      : (job.pickUpTime ?? job.flight?.departureTime ?? job.flight?.arrivalTime);
  if (!iso) return null;
  return new Date(iso);
}

function VehicleFleetOverview({ jobs, locale }: { jobs: Job[]; locale: string }) {
  const serviceTypeLabel = useServiceTypeLabel();
  const t = useT();
  const [collapsed, setCollapsed] = useState(false);

  // Group assigned jobs by vehicleId
  const vehicleMap = new Map<
    string,
    { plate: string; typeName: string; jobs: Job[] }
  >();

  for (const job of jobs) {
    if (!job.assignment?.vehicleId || !job.assignment.vehicle) continue;
    const vid = job.assignment.vehicleId;
    if (!vehicleMap.has(vid)) {
      vehicleMap.set(vid, {
        plate: job.assignment.vehicle.plateNumber,
        typeName: job.assignment.vehicle.vehicleType?.name ?? "—",
        jobs: [],
      });
    }
    vehicleMap.get(vid)!.jobs.push(job);
  }

  // Sort each vehicle's jobs by time
  const entries = Array.from(vehicleMap.entries()).map(([vid, data]) => {
    const sorted = [...data.jobs].sort((a, b) => {
      const ta = getJobTime(a)?.getTime() ?? 0;
      const tb = getJobTime(b)?.getTime() ?? 0;
      return ta - tb;
    });
    return { vid, ...data, jobs: sorted };
  });

  entries.sort((a, b) => a.plate.localeCompare(b.plate));

  if (entries.length === 0) return null;

  const serviceColors = SERVICE_TYPE_COLORS_SOLID;

  return (
    <div className="space-y-2">
      {/* Section header */}
      <div className="flex items-center justify-between">
        <button
          type="button"
          onClick={() => setCollapsed((c) => !c)}
          className="flex items-center gap-2 text-sm font-medium text-muted-foreground hover:text-foreground transition-colors"
        >
          <Car className="h-4 w-4" />
          {t("dispatch.fleetOverview")}
          <span className="rounded-full bg-muted px-2 py-0.5 text-xs font-normal">
            {entries.length} {t("dispatch.vehicles")}
          </span>
          <span className="text-muted-foreground/50 text-xs">
            {collapsed ? "▸" : "▾"}
          </span>
        </button>
      </div>

      {!collapsed && (
        <div className="flex gap-3 overflow-x-auto pb-2 pt-0.5">
          {entries.map(({ vid, plate, typeName, jobs: vjobs }) => (
            <div
              key={vid}
              className="flex-shrink-0 w-52 rounded-lg border border-border bg-card p-3 space-y-2"
            >
              {/* Card header */}
              <div className="flex items-start justify-between gap-1">
                <div>
                  <div className="font-mono font-semibold text-sm text-foreground leading-tight">
                    {plate}
                  </div>
                  <div className="text-[11px] text-muted-foreground">{typeName}</div>
                </div>
                <div className="flex flex-col items-end gap-1">
                  <span className="rounded-full bg-muted px-1.5 py-0.5 text-[10px] font-medium text-muted-foreground">
                    {vjobs.length} {vjobs.length === 1 ? t("dispatch.tripSingle") : t("dispatch.tripPlural")}
                  </span>
                </div>
              </div>

              {/* Trip list */}
              <div className="space-y-1 border-t border-border pt-2">
                {vjobs.map((job) => {
                  const jobTime = getJobTime(job);
                  const jobDriver =
                    job.assignment?.driver?.name ?? job.assignment?.externalDriverName ?? null;
                  return (
                    <div
                      key={job.id}
                      className="rounded px-2 py-1 text-[11px] space-y-0.5 bg-muted/40"
                    >
                      <div className="flex items-center justify-between gap-1">
                        <span
                          className={`rounded border px-1 py-0.5 text-[10px] font-semibold ${
                            serviceColors[job.serviceType] ?? "bg-zinc-500/20 text-zinc-400 border-zinc-500/30"
                          }`}
                        >
                          {serviceTypeLabel(job.serviceType)}
                        </span>
                        <span className="font-mono text-[10px] text-muted-foreground">
                          {jobTime ? fmtTime(jobTime.toISOString(), locale) : "—"}
                        </span>
                      </div>
                      <div className="flex items-center justify-between">
                        <span className="text-foreground/80 truncate font-mono">{job.internalRef}</span>
                        <span className="text-muted-foreground ml-1 flex-shrink-0">{job.paxCount}p</span>
                      </div>
                      {jobDriver && (
                        <div className="flex items-center gap-1 text-[10px] text-muted-foreground pt-0.5">
                          <Users className="h-2.5 w-2.5 flex-shrink-0" />
                          <span className="truncate">{jobDriver}</span>
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

// ────────────────────────────────────────────
// RepOverview
// ────────────────────────────────────────────

function RepOverview({ jobs, locale }: { jobs: Job[]; locale: string }) {
  const serviceTypeLabel = useServiceTypeLabel();
  const t = useT();
  const [collapsed, setCollapsed] = useState(false);

  // Group jobs that have a rep assigned
  const repMap = new Map<string, { name: string; jobs: Job[] }>();

  for (const job of jobs) {
    if (!job.assignment?.repId || !job.assignment.rep) continue;
    const rid = job.assignment.repId;
    if (!repMap.has(rid)) {
      repMap.set(rid, { name: job.assignment.rep.name, jobs: [] });
    }
    repMap.get(rid)!.jobs.push(job);
  }

  const entries = Array.from(repMap.entries()).map(([rid, data]) => {
    const sorted = [...data.jobs].sort((a, b) => {
      const ta = getJobTime(a)?.getTime() ?? 0;
      const tb = getJobTime(b)?.getTime() ?? 0;
      return ta - tb;
    });
    return { rid, ...data, jobs: sorted };
  });

  entries.sort((a, b) => a.name.localeCompare(b.name));

  if (entries.length === 0) return null;

  const serviceColors = SERVICE_TYPE_COLORS_SOLID;

  return (
    <div className="space-y-2">
      {/* Section header */}
      <div className="flex items-center justify-between">
        <button
          type="button"
          onClick={() => setCollapsed((c) => !c)}
          className="flex items-center gap-2 text-sm font-medium text-muted-foreground hover:text-foreground transition-colors"
        >
          <UserCheck className="h-4 w-4" />
          {t("dispatch.repOverview")}
          <span className="rounded-full bg-muted px-2 py-0.5 text-xs font-normal">
            {entries.length} {t("dispatch.repsLabel")}
          </span>
          <span className="text-muted-foreground/50 text-xs">
            {collapsed ? "▸" : "▾"}
          </span>
        </button>
      </div>

      {!collapsed && (
        <div className="flex gap-3 overflow-x-auto pb-2 pt-0.5">
          {entries.map(({ rid, name, jobs: rjobs }) => (
            <div
              key={rid}
              className="flex-shrink-0 w-52 rounded-lg border border-border bg-card p-3 space-y-2"
            >
              {/* Card header */}
              <div className="flex items-start justify-between gap-1">
                <div className="min-w-0">
                  <div className="font-semibold text-sm text-foreground leading-tight truncate">
                    {name}
                  </div>
                  <div className="text-[11px] text-muted-foreground">{t("dispatch.rep")}</div>
                </div>
                <div className="flex flex-col items-end gap-1 flex-shrink-0">
                  <span className="rounded-full bg-muted px-1.5 py-0.5 text-[10px] font-medium text-muted-foreground">
                    {rjobs.length} {rjobs.length === 1 ? t("dispatch.tripSingle") : t("dispatch.tripPlural")}
                  </span>
                </div>
              </div>

              {/* Trip list */}
              <div className="space-y-1 border-t border-border pt-2">
                {rjobs.map((job) => {
                  const jobTime = getJobTime(job);
                  return (
                    <div
                      key={job.id}
                      className="rounded px-2 py-1 text-[11px] space-y-0.5 bg-muted/40"
                    >
                      <div className="flex items-center justify-between gap-1">
                        <span
                          className={`rounded border px-1 py-0.5 text-[10px] font-semibold ${
                            serviceColors[job.serviceType] ?? "bg-zinc-500/20 text-zinc-400 border-zinc-500/30"
                          }`}
                        >
                          {serviceTypeLabel(job.serviceType)}
                        </span>
                        <span className="font-mono text-[10px] text-muted-foreground">
                          {jobTime ? fmtTime(jobTime.toISOString(), locale) : "—"}
                        </span>
                      </div>
                      <div className="flex items-center justify-between">
                        <span className="text-foreground/80 truncate font-mono">{job.internalRef}</span>
                        <span className="text-muted-foreground ml-1 flex-shrink-0">{job.paxCount}p</span>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

// ────────────────────────────────────────────
// Main Component
// ────────────────────────────────────────────

const FORTY_EIGHT_HOURS_MS = 48 * 60 * 60 * 1000;

export default function DispatchPage() {
  const serviceTypeLabel = useServiceTypeLabel();
  const t = useT();
  const locale = useLocaleId();
  const { user } = useAuthStore();
  const [date, setDate] = useState(new Date());
  const [arrivals, setArrivals] = useState<Job[]>([]);
  const [departures, setDepartures] = useState<Job[]>([]);
  const [cityTransfers, setCityTransfers] = useState<Job[]>([]);
  const [loading, setLoading] = useState(true);
  const [exporting, setExporting] = useState(false);

  // Available resources for the day (pre-fetched)
  const [suppliers, setSuppliers] = useState<SupplierResource[]>([]);
  const [vehicles, setVehicles] = useState<VehicleResource[]>([]);
  const [drivers, setDrivers] = useState<PersonResource[]>([]);
  const [reps, setReps] = useState<PersonResource[]>([]);

  // Inline editing state
  const [activeCell, setActiveCell] = useState<ActiveCell | null>(null);

  // Row success flash state
  const [savedRowId, setSavedRowId] = useState<string | null>(null);
  const showSavedFlash = (jobId: string) => {
    setSavedRowId(jobId);
    setTimeout(() => setSavedRowId(null), 1000);
  };

  // Per-job car source selection (lifted to parent so it persists across tab switches)
  const [jobSources, setJobSources] = useState<Record<string, string>>({});

  // Optimistic rollback state
  const prevState = useRef<{
    arrivals: Job[];
    departures: Job[];
    cityTransfers: Job[];
  } | null>(null);

  // Dialog fallback
  const [dialogJob, setDialogJob] = useState<Job | null>(null);
  const [dialogSupplier, setDialogSupplier] = useState("");
  const [dialogVehicle, setDialogVehicle] = useState("");
  const [dialogDriver, setDialogDriver] = useState("");
  const [dialogRep, setDialogRep] = useState("");
  const [dialogExternalDriverName, setDialogExternalDriverName] = useState("");
  const [dialogExternalDriverPhone, setDialogExternalDriverPhone] = useState("");
  const [dialogRemarks, setDialogRemarks] = useState("");
  const [dialogSaving, setDialogSaving] = useState(false);

  // Search filter
  const [searchQuery, setSearchQuery] = useState("");

  // Agent / Customer filter
  const [filterAgentCustomer, setFilterAgentCustomer] = useState<string>("ALL");

  // Vehicle Type filter
  const [filterVehicleType, setFilterVehicleType] = useState<string>("ALL");

  const allJobs = useMemo(() => [...arrivals, ...departures, ...cityTransfers], [arrivals, departures, cityTransfers]);

  const agentCustomerOptions = useMemo(() => {
    const map = new Map<string, string>();
    for (const job of allJobs) {
      if ((job.bookingChannel === "ONLINE" || job.bookingChannel === "B2C") && job.agent?.legalName) {
        map.set(`agent:${job.agent.legalName}`, job.agent.legalName);
      } else if (job.bookingChannel === "B2B" && job.customer?.legalName) {
        map.set(`customer:${job.customer.legalName}`, job.customer.legalName);
      }
    }
    return Array.from(map.entries())
      .map(([key, label]) => ({ key, label }))
      .sort((a, b) => a.label.localeCompare(b.label));
  }, [allJobs]);

  const vehicleTypeOptions = useMemo(() => {
    const map = new Map<string, string>();
    for (const job of allJobs) {
      if (job.requestedVehicleType?.id && job.requestedVehicleType?.name) {
        map.set(job.requestedVehicleType.id, job.requestedVehicleType.name);
      }
    }
    return Array.from(map.entries())
      .map(([id, name]) => ({ id, name }))
      .sort((a, b) => a.name.localeCompare(b.name));
  }, [allJobs]);

  const filterJobs = useCallback((jobs: Job[], query: string, agentCustomerKey: string, vehicleTypeId: string) => {
    return jobs.filter((job) => {
      // Agent/Customer filter
      if (agentCustomerKey !== "ALL") {
        const jobKey = job.bookingChannel === "ONLINE" || job.bookingChannel === "B2C"
          ? `agent:${job.agent?.legalName || ""}`
          : `customer:${job.customer?.legalName || ""}`;
        if (jobKey !== agentCustomerKey) return false;
      }
      // Vehicle Type filter
      if (vehicleTypeId !== "ALL") {
        if (job.requestedVehicleType?.id !== vehicleTypeId) return false;
      }
      // Text search filter
      if (query.trim()) {
        const q = query.toLowerCase();
        const ref = job.internalRef?.toLowerCase() || "";
        const agentRef = job.agentRef?.toLowerCase() || "";
        const driverName = job.assignment?.driver?.name?.toLowerCase() || "";
        const externalDriver = job.assignment?.externalDriverName?.toLowerCase() || "";
        const repName = job.assignment?.rep?.name?.toLowerCase() || "";
        if (
          !ref.includes(q) &&
          !agentRef.includes(q) &&
          !driverName.includes(q) &&
          !externalDriver.includes(q) &&
          !repName.includes(q)
        ) return false;
      }
      return true;
    });
  }, []);

  const filteredArrivals = useMemo(() => filterJobs(arrivals, searchQuery, filterAgentCustomer, filterVehicleType), [arrivals, searchQuery, filterAgentCustomer, filterVehicleType, filterJobs]);
  const filteredDepartures = useMemo(() => filterJobs(departures, searchQuery, filterAgentCustomer, filterVehicleType), [departures, searchQuery, filterAgentCustomer, filterVehicleType, filterJobs]);
  const filteredCityTransfers = useMemo(() => filterJobs(cityTransfers, searchQuery, filterAgentCustomer, filterVehicleType), [cityTransfers, searchQuery, filterAgentCustomer, filterVehicleType, filterJobs]);

  // Derive initial car sources from existing vehicle assignments
  useEffect(() => {
    const initial: Record<string, string> = {};
    for (const job of allJobs) {
      if (job.assignment?.vehicleId) {
        // Regular vehicle assignment — resolve supplier from vehicle
        const v = vehicles.find((veh) => veh.id === job.assignment?.vehicleId);
        if (v) {
          initial[job.id] = v.supplierId || "owned";
        } else if (job.assignment.vehicle) {
          // Vehicle is already assigned (not in available list) — use assignment data
          initial[job.id] = job.assignment.vehicle.supplierId || "owned";
        }
      } else if (job.assignment?.supplierCarTypeId && job.assignment.supplierId) {
        // Supplier car type assignment (no vehicleId) — restore supplier source directly
        initial[job.id] = job.assignment.supplierId;
      }
    }
    setJobSources((prev) => ({ ...initial, ...prev }));
  }, [allJobs, vehicles]);

  const setJobSource = useCallback((jobId: string, source: string) => {
    setJobSources((prev) => ({ ...prev, [jobId]: source }));
  }, []);

  // Filtered vehicles for dialog based on owned/supplier selection
  const dialogFilteredVehicles = dialogSupplier === "owned"
    ? vehicles.filter((v) => !v.supplierId)
    : dialogSupplier
      ? vehicles.filter((v) => v.supplierId === dialogSupplier)
      : [];

  // ── Fetch day data + available resources ──

  const fetchDay = useCallback(async () => {
    setLoading(true);
    const dateStr = fmtDate(date);
    try {
      const [dayRes, sRes, vRes, dRes, rRes] = await Promise.allSettled([
        api.get(`/dispatch/day?date=${dateStr}`),
        api.get(`/dispatch/available-suppliers`),
        api.get(`/dispatch/available-vehicles?date=${dateStr}`),
        api.get(`/dispatch/available-drivers?date=${dateStr}`),
        api.get(`/dispatch/available-reps?date=${dateStr}`),
      ]);

      if (dayRes.status === "fulfilled") {
        const d = dayRes.value.data?.data || dayRes.value.data;
        const byArrivalTime = (a: Job, b: Job) => {
          const ta = a.flight?.arrivalTime ? new Date(a.flight.arrivalTime).getTime() : Infinity;
          const tb = b.flight?.arrivalTime ? new Date(b.flight.arrivalTime).getTime() : Infinity;
          return ta - tb;
        };
        const byPickUpTime = (a: Job, b: Job) => {
          const ta = a.pickUpTime ? new Date(a.pickUpTime).getTime() : Infinity;
          const tb = b.pickUpTime ? new Date(b.pickUpTime).getTime() : Infinity;
          return ta - tb;
        };
        setArrivals((d.arrivals || []).slice().sort(byArrivalTime));
        setDepartures((d.departures || []).slice().sort(byPickUpTime));
        setCityTransfers((d.cityJobs || d.cityTransfers || []).slice().sort(byPickUpTime));
      }
      if (sRes.status === "fulfilled") {
        const s = sRes.value.data?.data || sRes.value.data;
        setSuppliers(Array.isArray(s) ? s : []);
      }
      if (vRes.status === "fulfilled") {
        const v = vRes.value.data?.data || vRes.value.data;
        setVehicles(Array.isArray(v) ? v : []);
      }
      if (dRes.status === "fulfilled") {
        const d = dRes.value.data?.data || dRes.value.data;
        setDrivers(Array.isArray(d) ? d : []);
      }
      if (rRes.status === "fulfilled") {
        const r = rRes.value.data?.data || rRes.value.data;
        setReps(Array.isArray(r) ? r : []);
      }
    } catch {
      toast.error(t("dispatch.failedLoad"));
    } finally {
      setLoading(false);
    }
  }, [date]);

  useEffect(() => {
    fetchDay();
  }, [fetchDay]);

  // ── Date navigation ──

  const prevDay = () => {
    const d = new Date(date);
    d.setDate(d.getDate() - 1);
    setDate(d);
  };
  const nextDay = () => {
    const d = new Date(date);
    d.setDate(d.getDate() + 1);
    setDate(d);
  };
  const goToday = () => setDate(new Date());

  const exportExcel = async () => {
    setExporting(true);
    try {
      const dateStr = fmtDate(date);
      const res = await api.get(`/export/odoo/dispatch?date=${dateStr}`, {
        responseType: "blob",
      });
      const url = window.URL.createObjectURL(new Blob([res.data]));
      const link = document.createElement("a");
      link.href = url;
      link.setAttribute("download", `dispatch_${dateStr}.xlsx`);
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
    } catch {
      toast.error(t("dispatch.exportFailed"));
    } finally {
      setExporting(false);
    }
  };

  // ── Optimistic helpers ──

  const saveSnapshot = () => {
    prevState.current = {
      arrivals: arrivals.map((j) => ({ ...j, assignment: j.assignment ? { ...j.assignment } : undefined })),
      departures: departures.map((j) => ({ ...j, assignment: j.assignment ? { ...j.assignment } : undefined })),
      cityTransfers: cityTransfers.map((j) => ({ ...j, assignment: j.assignment ? { ...j.assignment } : undefined })),
    };
  };

  const rollback = () => {
    if (prevState.current) {
      setArrivals(prevState.current.arrivals);
      setDepartures(prevState.current.departures);
      setCityTransfers(prevState.current.cityTransfers);
      prevState.current = null;
    }
  };

  const updateJobInList = (
    setter: React.Dispatch<React.SetStateAction<Job[]>>,
    jobId: string,
    updater: (job: Job) => Job
  ) => {
    setter((prev) => prev.map((j) => (j.id === jobId ? updater(j) : j)));
  };

  const findJobList = (
    jobId: string
  ): [Job[], React.Dispatch<React.SetStateAction<Job[]>>] | null => {
    if (arrivals.find((j) => j.id === jobId)) return [arrivals, setArrivals];
    if (departures.find((j) => j.id === jobId))
      return [departures, setDepartures];
    if (cityTransfers.find((j) => j.id === jobId))
      return [cityTransfers, setCityTransfers];
    return null;
  };

  // ── Inline assignment handler ──

  const handleInlineAssign = async (
    job: Job,
    field: EditField,
    value: string
  ) => {
    setActiveCell(null);

    // Handle "none" selection for optional fields
    const actualValue = value === "__none__" ? null : value;

    // For rep field on unassigned jobs (rep-only assign): POST with repId only
    if (!job.assignment && field === "rep" && actualValue) {
      saveSnapshot();
      const repRes = reps.find((r) => r.id === actualValue);
      const found = findJobList(job.id);
      if (found) {
        updateJobInList(found[1], job.id, (j) => ({
          ...j,
          status: "ASSIGNED",
          assignment: {
            id: "__pending__",
            vehicleId: null,
            driverId: null,
            repId: actualValue,
            vehicle: undefined,
            driver: undefined,
            rep: repRes ? { name: repRes.name } : undefined,
          },
        }));
      }
      try {
        await api.post("/dispatch/assign", {
          trafficJobId: job.id,
          repId: actualValue,
        });
        toast.success(t("dispatch.repUpdated"));
        showSavedFlash(job.id);
        fetchDay();
      } catch (err: unknown) {
        rollback();
        const msg =
          (err as { response?: { data?: { message?: string } } })?.response?.data?.message ||
          t("dispatch.assignmentFailed");
        toast.error(msg);
      }
      return;
    }

    // For vehicle field on unassigned jobs: full assign (POST)
    if (!job.assignment && field === "vehicle" && actualValue) {
      saveSnapshot();

      const vehicleRes = vehicles.find((v) => v.id === actualValue);
      const isCarType = vehicleRes?.isCarType === true;

      // Optimistic: create placeholder assignment
      const found = findJobList(job.id);
      if (found) {
        updateJobInList(found[1], job.id, (j) => ({
          ...j,
          status: "ASSIGNED",
          assignment: {
            id: "__pending__",
            vehicleId: isCarType ? null : actualValue,
            supplierCarTypeId: isCarType ? actualValue : null,
            supplierId: isCarType ? (vehicleRes?.supplierId ?? null) : null,
            driverId: null,
            repId: null,
            vehicle: !isCarType && vehicleRes
              ? { plateNumber: vehicleRes.plateNumber, vehicleType: vehicleRes.vehicleType }
              : undefined,
            supplierCarType: isCarType && vehicleRes
              ? { vehicleType: vehicleRes.vehicleType }
              : undefined,
            driver: undefined,
            rep: undefined,
          },
        }));
      }

      const assignPayload = isCarType
        ? { trafficJobId: job.id, supplierCarTypeId: actualValue, supplierId: vehicleRes?.supplierId }
        : { trafficJobId: job.id, vehicleId: actualValue };

      try {
        await api.post("/dispatch/assign", assignPayload);
        toast.success(t("dispatch.vehicleAssigned"));
        showSavedFlash(job.id);
        fetchDay(); // refresh to get full assignment data
      } catch (err: unknown) {
        const resp = (err as { response?: { status?: number; data?: { message?: string } } })?.response;
        if (resp?.status === 409 && resp?.data?.message?.includes("Vehicle type mismatch")) {
          // Ask user to confirm mismatch
          if (window.confirm(resp.data.message + "\n\nAssign anyway?")) {
            try {
              await api.post("/dispatch/assign", {
                trafficJobId: job.id,
                vehicleId: actualValue,
                allowTypeMismatch: true,
              });
              toast.success(t("dispatch.vehicleAssigned"));
              fetchDay();
              return;
            } catch (retryErr: unknown) {
              rollback();
              const retryMsg =
                (retryErr as { response?: { data?: { message?: string } } })?.response
                  ?.data?.message || t("dispatch.assignmentFailed");
              toast.error(retryMsg);
              return;
            }
          } else {
            rollback();
            return;
          }
        }
        rollback();
        const msg = resp?.data?.message || t("dispatch.assignmentFailed");
        toast.error(msg);
      }
      return;
    }

    // For reassigning an existing assignment (PATCH)
    if (job.assignment && job.assignment.id !== "__pending__") {
      saveSnapshot();

      // Check if this is an external driver (supplier driver entered manually)
      const isExternalDriver = field === "driver" && typeof value === "string" && value.startsWith("__external__:");

      // Build optimistic update
      const found = findJobList(job.id);
      if (found) {
        updateJobInList(found[1], job.id, (j) => {
          if (!j.assignment) return j;
          const updated = { ...j, assignment: { ...j.assignment } };
          if (field === "vehicle" && actualValue) {
            const v = vehicles.find((x) => x.id === actualValue);
            if (v?.isCarType) {
              updated.assignment.vehicleId = null;
              updated.assignment.vehicle = undefined;
              updated.assignment.supplierCarTypeId = actualValue;
              updated.assignment.supplierId = v.supplierId ?? null;
              updated.assignment.supplierCarType = { vehicleType: v.vehicleType };
            } else {
              updated.assignment.vehicleId = actualValue;
              updated.assignment.supplierCarTypeId = null;
              updated.assignment.supplierId = null;
              updated.assignment.vehicle = v
                ? { plateNumber: v.plateNumber, vehicleType: v.vehicleType }
                : updated.assignment.vehicle;
            }
          } else if (field === "driver" && isExternalDriver) {
            const parts = value.split(":");
            updated.assignment.driverId = null;
            updated.assignment.driver = undefined;
            updated.assignment.externalDriverName = parts[1] || null;
            updated.assignment.externalDriverPhone = parts[2] || null;
          } else if (field === "driver") {
            updated.assignment.driverId = actualValue;
            const driverRes = drivers.find((d) => d.id === actualValue);
            updated.assignment.driver = actualValue
              ? { name: driverRes?.name || "", mobileNumber: driverRes?.mobileNumber }
              : undefined;
            updated.assignment.externalDriverName = null;
            updated.assignment.externalDriverPhone = null;
          } else if (field === "rep") {
            updated.assignment.repId = actualValue;
            updated.assignment.rep = actualValue
              ? { name: reps.find((r) => r.id === actualValue)?.name || "" }
              : undefined;
          } else if (field === "remarks") {
            updated.assignment.remarks = actualValue;
          }
          return updated;
        });
      }

      const payload: Record<string, string | boolean | null> = {};
      if (field === "vehicle" && actualValue) {
        const selectedVehicle = vehicles.find((v) => v.id === actualValue);
        if (selectedVehicle?.isCarType) {
          payload.supplierCarTypeId = actualValue;
          payload.supplierId = selectedVehicle.supplierId ?? null;
        } else {
          payload.vehicleId = actualValue;
        }
      }
      if (field === "driver" && isExternalDriver) {
        const parts = value.split(":");
        payload.driverId = null;
        payload.externalDriverName = parts[1] || null;
        payload.externalDriverPhone = parts[2] || null;
      } else if (field === "driver") {
        payload.driverId = actualValue;
      }
      if (field === "rep") payload.repId = actualValue;
      if (field === "remarks") payload.remarks = actualValue;

      try {
        await api.patch(
          `/dispatch/assignments/${job.assignment.id}`,
          payload
        );
        toast.success(t(`dispatch.${field === "remarks" ? "remarks" : field}Updated`));
        showSavedFlash(job.id);
      } catch (err: unknown) {
        const resp = (err as { response?: { status?: number; data?: { message?: string } } })?.response;
        if (resp?.status === 409 && resp?.data?.message?.includes("Vehicle type mismatch")) {
          if (window.confirm(resp.data.message + "\n\nAssign anyway?")) {
            try {
              await api.patch(
                `/dispatch/assignments/${job.assignment!.id}`,
                { ...payload, allowTypeMismatch: true }
              );
              toast.success(t(`dispatch.${field === "remarks" ? "remarks" : field}Updated`));
              showSavedFlash(job.id);
              fetchDay();
              return;
            } catch (retryErr: unknown) {
              rollback();
              const retryMsg =
                (retryErr as { response?: { data?: { message?: string } } })?.response
                  ?.data?.message || t("dispatch.updateFailed");
              toast.error(retryMsg);
              return;
            }
          } else {
            rollback();
            return;
          }
        }
        rollback();
        const msg = resp?.data?.message || t("dispatch.updateFailed");
        toast.error(msg);
      }
    }
  };

  // ── Dialog-based assignment (fallback) ──

  const openDialog = (job: Job) => {
    if (dispatcherLocked && !job.dispatchUnlockedAt) return;
    setDialogJob(job);
    // Pre-select source: owned vs supplier based on current vehicle
    const currentVehicle = job.assignment?.vehicleId
      ? vehicles.find((v) => v.id === job.assignment?.vehicleId)
      : null;
    setDialogSupplier(currentVehicle ? (currentVehicle.supplierId || "owned") : "");
    setDialogVehicle(job.assignment?.vehicleId || "");
    setDialogDriver(job.assignment?.driverId || "");
    setDialogRep(job.assignment?.repId || "");
    setDialogExternalDriverName(job.assignment?.externalDriverName || "");
    setDialogExternalDriverPhone(job.assignment?.externalDriverPhone || "");
    setDialogRemarks(job.assignment?.remarks || "");
  };

  const dialogIsSupplier = dialogSupplier && dialogSupplier !== "owned";

  const handleDialogSave = async () => {
    if (!dialogJob) return;
    if (canAssignVehicle && !dialogVehicle) {
      toast.error(t("dispatch.vehicleRequired"));
      return;
    }
    if (!canAssignVehicle && !dialogRep) {
      toast.error(t("dispatch.repRequired"));
      return;
    }
    setDialogSaving(true);
    try {
      if (dialogJob.assignment) {
        // Reassign
        const payload: Record<string, string | null> = {};
        if (dialogVehicle !== dialogJob.assignment.vehicleId)
          payload.vehicleId = dialogVehicle;
        if (dialogIsSupplier) {
          // External driver (text fields)
          if (dialogExternalDriverName !== (dialogJob.assignment.externalDriverName || ""))
            payload.externalDriverName = dialogExternalDriverName || null;
          if (dialogExternalDriverPhone !== (dialogJob.assignment.externalDriverPhone || ""))
            payload.externalDriverPhone = dialogExternalDriverPhone || null;
          payload.driverId = null;
        } else {
          if (dialogDriver !== (dialogJob.assignment.driverId || ""))
            payload.driverId = dialogDriver || null;
          payload.externalDriverName = null;
          payload.externalDriverPhone = null;
        }
        if (dialogRep !== (dialogJob.assignment.repId || ""))
          payload.repId = dialogRep || null;
        if (dialogRemarks !== (dialogJob.assignment.remarks || ""))
          payload.remarks = dialogRemarks || null;

        if (Object.keys(payload).length > 0) {
          await api.patch(
            `/dispatch/assignments/${dialogJob.assignment.id}`,
            payload
          );
        }
      } else {
        // New assign
        const payload: Record<string, string | null> = {
          trafficJobId: dialogJob.id,
        };
        if (dialogVehicle) payload.vehicleId = dialogVehicle;
        if (dialogIsSupplier) {
          if (dialogExternalDriverName) payload.externalDriverName = dialogExternalDriverName;
          if (dialogExternalDriverPhone) payload.externalDriverPhone = dialogExternalDriverPhone;
        } else {
          if (dialogDriver) payload.driverId = dialogDriver;
        }
        if (dialogRep) payload.repId = dialogRep;
        if (dialogRemarks) payload.remarks = dialogRemarks;
        await api.post("/dispatch/assign", payload);
      }
      toast.success(t("dispatch.assignmentSaved"));
      setDialogJob(null);
      fetchDay();
    } catch (err: unknown) {
      const resp = (err as { response?: { status?: number; data?: { message?: string } } })?.response;
      if (resp?.status === 409 && resp?.data?.message?.includes("Vehicle type mismatch")) {
        if (window.confirm(resp.data.message + "\n\nAssign anyway?")) {
          try {
            if (dialogJob!.assignment) {
              const retryPayload: Record<string, unknown> = { allowTypeMismatch: true };
              if (dialogVehicle !== dialogJob!.assignment.vehicleId)
                retryPayload.vehicleId = dialogVehicle;
              await api.patch(
                `/dispatch/assignments/${dialogJob!.assignment.id}`,
                retryPayload
              );
            } else {
              const retryPayload: Record<string, unknown> = {
                trafficJobId: dialogJob!.id,
                vehicleId: dialogVehicle,
                allowTypeMismatch: true,
              };
              if (dialogIsSupplier) {
                if (dialogExternalDriverName) retryPayload.externalDriverName = dialogExternalDriverName;
                if (dialogExternalDriverPhone) retryPayload.externalDriverPhone = dialogExternalDriverPhone;
              } else {
                if (dialogDriver) retryPayload.driverId = dialogDriver;
              }
              if (dialogRep) retryPayload.repId = dialogRep;
              if (dialogRemarks) retryPayload.remarks = dialogRemarks;
              await api.post("/dispatch/assign", retryPayload);
            }
            toast.success(t("dispatch.assignmentSaved"));
            setDialogJob(null);
            fetchDay();
          } catch (retryErr: unknown) {
            const retryMsg =
              (retryErr as { response?: { data?: { message?: string } } })?.response?.data
                ?.message || t("dispatch.assignmentFailed");
            toast.error(retryMsg);
          }
        }
      } else {
        const msg = resp?.data?.message || t("dispatch.assignmentFailed");
        toast.error(msg);
      }
    } finally {
      setDialogSaving(false);
    }
  };

  // ── Stats ──

  const totalJobs =
    arrivals.length + departures.length + cityTransfers.length;
  const assignedCount = [...arrivals, ...departures, ...cityTransfers].filter(
    (j) => j.assignment
  ).length;

  // ── Dispatcher 48-hour lock ──

  const isDispatcher = user?.role === "DISPATCHER" || user?.roleSlug === "dispatcher";
  const isPast48h = new Date() > new Date(date.getTime() + FORTY_EIGHT_HOURS_MS);
  const dispatcherLocked = isDispatcher && isPast48h;
  const canUnlock = usePermission("dispatch.assignment.unlock48h");
  const canAssignVehicle = usePermission("dispatch.assignment.assignVehicle");
  const canAssignRep = usePermission("dispatch.assignment.assignRep");
  const canExport = usePermission("dispatch.exportButton");

  const handleToggleLock = async (jobId: string, shouldUnlock: boolean) => {
    try {
      if (shouldUnlock) {
        await api.post(`/dispatch/jobs/${jobId}/unlock`);
        toast.success(t("dispatch.jobUnlocked"));
      } else {
        await api.post(`/dispatch/jobs/${jobId}/lock`);
        toast.success(t("dispatch.jobLocked"));
      }
      fetchDay();
    } catch (err: unknown) {
      const msg =
        (err as { response?: { data?: { message?: string } } })?.response?.data
          ?.message || t("dispatch.lockToggleFailed");
      toast.error(msg);
    }
  };

  // ── Grid props ──

  const showLockColumn = isPast48h;

  const gridProps = {
    activeCell,
    vehicles,
    suppliers,
    drivers,
    reps,
    jobSources,
    setJobSource,
    onStartEdit: (jobId: string, field: EditField) =>
      setActiveCell({ jobId, field }),
    onCancelEdit: () => setActiveCell(null),
    onInlineAssign: handleInlineAssign,
    onDialogAssign: openDialog,
    locked: dispatcherLocked,
    showLockColumn,
    canUnlock: canUnlock && isPast48h,
    onToggleLock: handleToggleLock,
    canAssignVehicle,
    canAssignRep,
    savedRowId,
  };

  return (
    <div className="flex flex-col h-full animate-in fade-in duration-300">
      <div className="flex-1 space-y-4 overflow-auto pb-2">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <CalendarClock className="h-6 w-6 text-muted-foreground" />
            <h1 className="text-2xl font-semibold text-foreground">
              {t("dispatch.title")}
            </h1>
          </div>
          <div className="flex items-center gap-4 text-sm text-muted-foreground">
            <span>
              {assignedCount}/{totalJobs} {t("dispatch.assigned")}
            </span>
            <Badge
              variant="outline"
              className={
                assignedCount === totalJobs && totalJobs > 0
                  ? "border-emerald-500/30 text-emerald-600 dark:text-emerald-400"
                  : "border-amber-500/30 text-amber-600 dark:text-amber-400"
              }
            >
              {totalJobs > 0
                ? Math.round((assignedCount / totalJobs) * 100)
                : 0}
              %
            </Badge>
          </div>
        </div>

        {/* Date toolbar */}
        <div className="flex items-center gap-2">
          <Button
            variant="ghost"
            size="icon"
            onClick={prevDay}
            className="h-8 w-8 text-muted-foreground"
          >
            <ChevronLeft className="h-4 w-4" />
          </Button>
          <Button
            variant="ghost"
            size="sm"
            onClick={goToday}
            className="text-muted-foreground"
          >
            {t("dispatch.today")}
          </Button>
          <span className="min-w-[140px] text-center text-lg font-medium text-foreground">
            {formatDate(date)}
          </span>
          <Button
            variant="ghost"
            size="icon"
            onClick={nextDay}
            className="h-8 w-8 text-muted-foreground"
          >
            <ChevronRight className="h-4 w-4" />
          </Button>
          <div className="ml-auto flex items-center gap-2">
            {canExport && (
              <Button
                variant="outline"
                size="sm"
                onClick={exportExcel}
                disabled={exporting || loading}
                className="gap-1.5 text-muted-foreground"
              >
                {exporting ? <Loader2 className="h-4 w-4 animate-spin" /> : <Download className="h-4 w-4" />}
                {t("dispatch.exportExcel")}
              </Button>
            )}
          </div>
        </div>

        {/* Legend + keyboard hints */}
        <div className="flex items-center justify-between">
          <div className="flex gap-4 text-xs text-muted-foreground">
            <span className="flex items-center gap-1">
              <span className="h-2 w-2 rounded-full bg-red-500" /> {t("dispatch.unassigned")}
            </span>
            <span className="flex items-center gap-1">
              <span className="h-2 w-2 rounded-full bg-emerald-500" /> {t("dispatch.assigned")}
            </span>
            <span className="flex items-center gap-1">
              <span className="h-2 w-2 rounded-full bg-blue-500" /> {t("dispatch.inProgress")}
            </span>
          </div>
          <div className="text-xs text-muted-foreground/60">
            {t("dispatch.clickCells")} &middot; {t("dispatch.clickRefDialog")}
          </div>
        </div>

        {/* Fleet Overview */}
        {!loading && canAssignVehicle && (
          <VehicleFleetOverview
            jobs={[...arrivals, ...departures, ...cityTransfers]}
            locale={locale}
          />
        )}

        {/* Rep Overview */}
        {!loading && canAssignRep && (
          <RepOverview
            jobs={[...arrivals, ...departures, ...cityTransfers]}
            locale={locale}
          />
        )}

        {dispatcherLocked && (
          <div className="flex items-center gap-2 rounded-lg border border-amber-500/30 bg-amber-500/10 px-4 py-2 text-sm text-amber-600 dark:text-amber-400">
            {t("dispatch.lockedBanner")}
          </div>
        )}

        {/* Search filter */}
        {!loading && (
          <div className="relative max-w-sm">
            <Search className="absolute left-2.5 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground/60" />
            <Input
              placeholder={t("dispatch.searchPlaceholder")}
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="h-8 pl-8 pr-8 border-border bg-muted/30 text-foreground placeholder:text-muted-foreground/50 text-sm"
            />
            {searchQuery && (
              <button
                onClick={() => setSearchQuery("")}
                className="absolute right-2 top-1/2 -translate-y-1/2 text-muted-foreground/60 hover:text-foreground"
              >
                <X className="h-3.5 w-3.5" />
              </button>
            )}
          </div>
        )}

        {loading ? (
          <div className="space-y-4">
            {/* ARR skeleton */}
            <div>
              <div className="mb-2 flex items-center gap-2">
                <Skeleton className="h-4 w-4" />
                <Skeleton className="h-4 w-28" />
              </div>
              <div className="overflow-x-auto rounded-md border border-border">
                <table className="w-full text-sm">
                  <tbody>
                    {Array.from({ length: 5 }).map((_, i) => (
                      <tr key={i} className={`border-b border-border ${i % 2 === 0 ? "bg-gray-100/25 dark:bg-gray-800/25" : "bg-gray-200/50 dark:bg-gray-700/50"}`}>
                        <td className="px-2 py-2.5"><Skeleton className="h-3 w-20" /></td>
                        <td className="px-2 py-2.5"><Skeleton className="h-3 w-10" /></td>
                        <td className="px-2 py-2.5"><Skeleton className="h-3 w-24" /></td>
                        <td className="px-2 py-2.5"><Skeleton className="h-3 w-28" /></td>
                        <td className="px-2 py-2.5"><Skeleton className="h-3 w-24" /></td>
                        <td className="px-2 py-2.5"><Skeleton className="h-3 w-8" /></td>
                        <td className="px-2 py-2.5"><Skeleton className="h-5 w-14 rounded-full" /></td>
                        <td className="px-2 py-2.5"><Skeleton className="h-3 w-12" /></td>
                        <td className="px-2 py-2.5"><Skeleton className="h-3 w-10" /></td>
                        <td className="px-2 py-2.5"><Skeleton className="h-6 w-20 rounded-sm" /></td>
                        <td className="px-2 py-2.5"><Skeleton className="h-6 w-20 rounded-sm" /></td>
                        <td className="px-2 py-2.5"><Skeleton className="h-6 w-20 rounded-sm" /></td>
                        <td className="px-2 py-2.5"><Skeleton className="h-6 w-28 rounded-sm" /></td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
            {/* DEP skeleton */}
            <div>
              <div className="mb-2 flex items-center gap-2">
                <Skeleton className="h-4 w-4" />
                <Skeleton className="h-4 w-28" />
              </div>
              <div className="overflow-x-auto rounded-md border border-border">
                <table className="w-full text-sm">
                  <tbody>
                    {Array.from({ length: 4 }).map((_, i) => (
                      <tr key={i} className={`border-b border-border ${i % 2 === 0 ? "bg-gray-100/25 dark:bg-gray-800/25" : "bg-gray-200/50 dark:bg-gray-700/50"}`}>
                        <td className="px-2 py-2.5"><Skeleton className="h-3 w-20" /></td>
                        <td className="px-2 py-2.5"><Skeleton className="h-3 w-10" /></td>
                        <td className="px-2 py-2.5"><Skeleton className="h-3 w-24" /></td>
                        <td className="px-2 py-2.5"><Skeleton className="h-3 w-28" /></td>
                        <td className="px-2 py-2.5"><Skeleton className="h-3 w-24" /></td>
                        <td className="px-2 py-2.5"><Skeleton className="h-3 w-8" /></td>
                        <td className="px-2 py-2.5"><Skeleton className="h-5 w-14 rounded-full" /></td>
                        <td className="px-2 py-2.5"><Skeleton className="h-3 w-12" /></td>
                        <td className="px-2 py-2.5"><Skeleton className="h-3 w-10" /></td>
                        <td className="px-2 py-2.5"><Skeleton className="h-6 w-20 rounded-sm" /></td>
                        <td className="px-2 py-2.5"><Skeleton className="h-6 w-20 rounded-sm" /></td>
                        <td className="px-2 py-2.5"><Skeleton className="h-6 w-20 rounded-sm" /></td>
                        <td className="px-2 py-2.5"><Skeleton className="h-6 w-28 rounded-sm" /></td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        ) : (
          <Tabs defaultValue="split" className="space-y-4">
            <div className="flex items-center gap-3">
              <TabsList className="bg-card border border-border">
                <TabsTrigger
                  value="split"
                  className="data-[state=active]:bg-accent text-muted-foreground data-[state=active]:text-accent-foreground"
                >
                  {t("dispatch.splitView")}
                </TabsTrigger>
                <TabsTrigger
                  value="arrivals"
                  className="data-[state=active]:bg-accent text-muted-foreground data-[state=active]:text-accent-foreground"
                >
                  {t("dispatch.arrivals")}
                  <Badge variant="secondary" className="ml-1.5 px-1.5 py-0 text-[10px] leading-4 min-w-[18px] text-center">
                    {filteredArrivals.length}
                  </Badge>
                </TabsTrigger>
                <TabsTrigger
                  value="departures"
                  className="data-[state=active]:bg-accent text-muted-foreground data-[state=active]:text-accent-foreground"
                >
                  {t("dispatch.departures")}
                  <Badge variant="secondary" className="ml-1.5 px-1.5 py-0 text-[10px] leading-4 min-w-[18px] text-center">
                    {filteredDepartures.length}
                  </Badge>
                </TabsTrigger>
                <TabsTrigger
                  value="city"
                  className="data-[state=active]:bg-accent text-muted-foreground data-[state=active]:text-accent-foreground"
                >
                  {t("dispatch.other")}
                  <Badge variant="secondary" className="ml-1.5 px-1.5 py-0 text-[10px] leading-4 min-w-[18px] text-center">
                    {filteredCityTransfers.length}
                  </Badge>
                </TabsTrigger>
              </TabsList>

              {/* Agent / Customer filter */}
              <Select value={filterAgentCustomer} onValueChange={setFilterAgentCustomer}>
                <SelectTrigger className="w-52 h-9 border-border bg-card text-foreground text-sm">
                  <SelectValue placeholder={t("dispatch.filterByAgentCustomer") || "Agent / Customer"} />
                </SelectTrigger>
                <SelectContent className="border-border bg-popover text-foreground max-h-60">
                  <SelectItem value="ALL">{t("dispatch.allAgentsCustomers") || "All Agents / Customers"}</SelectItem>
                  {agentCustomerOptions.map((opt) => (
                    <SelectItem key={opt.key} value={opt.key}>
                      {opt.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>

              {vehicleTypeOptions.length > 0 && (
                <Select value={filterVehicleType} onValueChange={setFilterVehicleType}>
                  <SelectTrigger className="w-44 h-9 border-border bg-card text-foreground text-sm">
                    <SelectValue placeholder={t("dispatch.filterByVehicleType")} />
                  </SelectTrigger>
                  <SelectContent className="border-border bg-popover text-foreground max-h-60">
                    <SelectItem value="ALL">{t("dispatch.allVehicleTypes")}</SelectItem>
                    {vehicleTypeOptions.map((opt) => (
                      <SelectItem key={opt.id} value={opt.id}>
                        {opt.name}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              )}
            </div>

            <TabsContent value="split">
              <div className="grid grid-cols-1 gap-4 xl:grid-cols-2">
                <div>
                  <h3 className="mb-2 flex items-center gap-2 text-sm font-medium text-muted-foreground">
                    <Plane className="h-4 w-4" /> {t("dispatch.arrivals")} ({filteredArrivals.length})
                  </h3>
                  <JobGrid
                    jobs={filteredArrivals}
                    title="Arrival"
                    icon={Plane}
                    {...gridProps}
                  />
                </div>
                <div>
                  <h3 className="mb-2 flex items-center gap-2 text-sm font-medium text-muted-foreground">
                    <PlaneTakeoff className="h-4 w-4" /> {t("dispatch.departures")} (
                    {filteredDepartures.length})
                  </h3>
                  <JobGrid
                    jobs={filteredDepartures}
                    title="Departure"
                    icon={PlaneTakeoff}
                    showPickUpTime
                    {...gridProps}
                  />
                </div>
              </div>
              {filteredCityTransfers.length > 0 && (
                <div className="mt-4">
                  <h3 className="mb-2 flex items-center gap-2 text-sm font-medium text-muted-foreground">
                    <Bus className="h-4 w-4" /> {t("dispatch.other")} (
                    {filteredCityTransfers.length})
                  </h3>
                  <JobGrid
                    jobs={filteredCityTransfers}
                    title="Other"
                    icon={Bus}
                    showPickUpTime
                    {...gridProps}
                  />
                </div>
              )}
            </TabsContent>

            <TabsContent value="arrivals">
              <JobGrid
                jobs={filteredArrivals}
                title="Arrival"
                icon={Plane}
                {...gridProps}
              />
            </TabsContent>

            <TabsContent value="departures">
              <JobGrid
                jobs={filteredDepartures}
                title="Departure"
                icon={PlaneTakeoff}
                showPickUpTime
                {...gridProps}
              />
            </TabsContent>

            <TabsContent value="city">
              <JobGrid
                jobs={filteredCityTransfers}
                title="Other"
                icon={Bus}
                showPickUpTime
                {...gridProps}
              />
            </TabsContent>
          </Tabs>
        )}
      </div>

      {/* Summary Footer */}
      {!loading && (
        <SummaryFooter
          arrivals={arrivals}
          departures={departures}
          cityTransfers={cityTransfers}
        />
      )}

      {/* Full Assignment Dialog (fallback) */}
      <Dialog
        open={!!dialogJob}
        onOpenChange={(open) => !open && setDialogJob(null)}
      >
        <DialogContent className="border-border bg-popover text-foreground">
          <DialogHeader>
            <DialogTitle>
              {t("dispatch.assignJob")} — {dialogJob?.internalRef}
            </DialogTitle>
          </DialogHeader>
          <div className="space-y-4 py-2">
            <div className="flex gap-4 text-sm text-muted-foreground">
              <span>
                {t("dispatch.type")} <b className="text-foreground">{serviceTypeLabel(dialogJob?.serviceType)}</b>
              </span>
              <span>
                {t("dispatch.paxLabel")} <b className="text-foreground">{dialogJob?.paxCount}</b>
              </span>
              <span>
                {t("dispatch.routeLabel")}{" "}
                <b className="text-foreground">
                  {dialogJob?.originAirport?.code || dialogJob?.originHotel?.name || dialogJob?.originZone?.name || dialogJob?.fromZone?.name || "\u2014"} → {dialogJob?.destinationAirport?.code || dialogJob?.destinationHotel?.name || dialogJob?.destinationZone?.name || dialogJob?.toZone?.name || "\u2014"}
                </b>
              </span>
            </div>

            {/* Customer Rep Meeting Info */}
            {(dialogJob?.custRepName || dialogJob?.custRepMobile || dialogJob?.custRepMeetingPoint || dialogJob?.custRepMeetingTime) && (
              <div className="flex flex-wrap gap-x-4 gap-y-1 text-sm text-muted-foreground">
                {dialogJob.custRepName && (
                  <span>{t("jobs.custRepName")}: <b className="text-foreground">{dialogJob.custRepName}</b></span>
                )}
                {dialogJob.custRepMobile && (
                  <span>{t("jobs.custRepMobile")}: <b className="text-foreground">{dialogJob.custRepMobile}</b></span>
                )}
                {dialogJob.custRepMeetingPoint && (
                  <span>{t("jobs.custRepMeetingPoint")}: <b className="text-foreground">{dialogJob.custRepMeetingPoint}</b></span>
                )}
                {dialogJob.custRepMeetingTime && (
                  <span>{t("jobs.custRepMeetingTime")}: <b className="text-foreground">{new Date(dialogJob.custRepMeetingTime).toLocaleTimeString([], { timeZone: "Africa/Cairo", hour: "2-digit", minute: "2-digit", hour12: false })}</b></span>
                )}
              </div>
            )}

            {canAssignVehicle && (
              <>
                <div className="space-y-1.5">
                  <div className="flex items-center gap-2 text-sm text-muted-foreground">
                    <Truck className="h-4 w-4" /> {t("dispatch.vehicleSource")}
                  </div>
                  <DialogSearchSelect
                    value={dialogSupplier}
                    options={[
                      {
                        id: "owned",
                        label: t("dispatch.ownedVehicles"),
                        sublabel: String(vehicles.filter((v) => !v.supplierId).length),
                      },
                      ...suppliers.map((s) => ({
                        id: s.id,
                        label: s.tradeName || s.legalName,
                        sublabel: String(s.vehicleCount),
                      })),
                    ]}
                    onSelect={(val) => {
                      setDialogSupplier(val);
                      setDialogVehicle("");
                      setDialogDriver("");
                    }}
                    placeholder={t("dispatch.selectSource")}
                  />
                </div>

                <div className="space-y-1.5">
                  <div className="flex items-center gap-2 text-sm text-muted-foreground">
                    <Car className="h-4 w-4" /> {t("dispatch.vehicle")} *
                  </div>
                  <DialogSearchSelect
                    value={dialogVehicle}
                    options={dialogFilteredVehicles.map((v) => ({
                      id: v.id,
                      label: `${v.plateNumber} — ${v.vehicleType?.name ?? ""}`,
                      sublabel: v.vehicleType?.seatCapacity ? `${v.vehicleType.seatCapacity} ${t("dispatch.seats")}` : undefined,
                      isBusy: v.isBusy,
                    }))}
                    onSelect={setDialogVehicle}
                    placeholder={t("dispatch.selectVehicle")}
                    emptyMessage={t("dispatch.noVehiclesAvailable")}
                  />
                </div>

                <div className="space-y-1.5">
                  <div className="flex items-center gap-2 text-sm text-muted-foreground">
                    <Users className="h-4 w-4" /> {t("dispatch.driver")}
                  </div>
                  {dialogIsSupplier ? (
                    <div className="space-y-2">
                      <Input
                        placeholder={t("dispatch.externalDriverName")}
                        value={dialogExternalDriverName}
                        onChange={(e) => setDialogExternalDriverName(e.target.value)}
                        className="border-border bg-card text-foreground"
                      />
                      <Input
                        placeholder={t("dispatch.externalDriverPhone")}
                        value={dialogExternalDriverPhone}
                        onChange={(e) => setDialogExternalDriverPhone(e.target.value)}
                        className="border-border bg-card text-foreground"
                      />
                    </div>
                  ) : (
                    <DialogSearchSelect
                      value={dialogDriver}
                      options={(() => {
                        const filtered = dialogSupplier === "owned"
                          ? drivers.filter((d) => !d.supplierId)
                          : dialogSupplier
                            ? drivers.filter((d) => d.supplierId === dialogSupplier)
                            : drivers;
                        return filtered.map((d) => ({ id: d.id, label: d.name, sublabel: d.mobileNumber }));
                      })()}
                      onSelect={setDialogDriver}
                      placeholder={t("dispatch.selectDriver")}
                      emptyMessage={t("dispatch.noDriversAvailable")}
                    />
                  )}
                </div>
              </>
            )}

            {canAssignRep && (
            <div className="space-y-1.5">
              <div className="flex items-center gap-2 text-sm text-muted-foreground">
                <UserCheck className="h-4 w-4" /> {t("dispatch.rep")}{!canAssignVehicle && " *"}
              </div>
              <DialogSearchSelect
                value={dialogRep}
                options={reps.map((r) => ({ id: r.id, label: r.name, sublabel: r.mobileNumber }))}
                onSelect={setDialogRep}
                placeholder={t("dispatch.selectRep")}
              />
            </div>
            )}

            <div className="space-y-1.5">
              <div className="flex items-center gap-2 text-sm text-muted-foreground">
                {t("dispatch.remarks")}
              </div>
              <Input
                placeholder={t("dispatch.remarks")}
                value={dialogRemarks}
                onChange={(e) => setDialogRemarks(e.target.value)}
                className="border-border bg-card text-foreground"
              />
            </div>
          </div>
          <DialogFooter>
            <Button
              variant="ghost"
              onClick={() => setDialogJob(null)}
              className="text-muted-foreground hover:text-foreground"
            >
              {t("common.cancel")}
            </Button>
            <Button
              onClick={handleDialogSave}
              disabled={dialogSaving}
              className="bg-primary text-primary-foreground hover:bg-primary/90"
            >
              {dialogSaving && (
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              )}
              {t("dispatch.saveAssignment")}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
