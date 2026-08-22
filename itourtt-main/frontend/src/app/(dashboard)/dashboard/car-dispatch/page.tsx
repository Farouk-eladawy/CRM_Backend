"use client";

import { useState, useEffect, useCallback } from "react";
import { useRouter } from "next/navigation";
import api from "@/lib/api";
import { useT } from "@/lib/i18n";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "@/components/ui/dialog";
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
import { Label } from "@/components/ui/label";
import { Checkbox } from "@/components/ui/checkbox";
import { Separator } from "@/components/ui/separator";
import {
  Plus,
  Trash2,
  Save,
  Car,
  ChevronDown,
  Check,
  X,
  Loader2,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { type JobExtra } from "@/components/job-extras-editor";
import { SERVICE_TYPE_DROPDOWN_OPTIONS } from "@/lib/service-types";

/* ────────────────────────────── Types ────────────────────────────── */

interface VehicleType {
  id: string;
  name: string;
  seatCapacity: number;
}

interface Vehicle {
  id: string;
  plateNumber: string;
  vehicleTypeId: string;
  vehicleType: VehicleType;
  ownership: string;
  supplierId?: string | null;
  isActive: boolean;
  carBrand?: string | null;
  carModel?: string | null;
}

interface Customer {
  id: string;
  legalName: string;
  tradeName?: string | null;
}

interface Driver {
  id: string;
  name: string;
  mobileNumber: string;
  isActive: boolean;
}

interface Supplier {
  id: string;
  legalName: string;
  tradeName?: string | null;
  vehicles?: Vehicle[];
}

interface LocationOption {
  id: string;
  name: string;
}

interface JobRow {
  uid: string; // local row key
  customerId: string;
  customerJobId: string; // customer's own job/booking reference
  bookingNumber: string; // auto-generated after save
  description: string; // origin → destination
  pickUpTime: string; // HH:mm
  driverId: string;
  extras: JobExtra[];
  collectionAmount: string;
  collectionCurrency: string;
  custRepName: string;
  custRepMobile: string;
  extraDriverName: string;
  extraDriverPhone: string;
  serviceType: string;
  // location IDs for API
  originAirportId: string;
  originZoneId: string;
  originHotelId: string;
  destinationAirportId: string;
  destinationZoneId: string;
  destinationHotelId: string;
  paxCount: string;
  // state
  saved: boolean;
  saving: boolean;
  savedJobId?: string;
  error?: string;
}

interface CarCard {
  vehicle: Vehicle;
  jobs: JobRow[];
  isSupplier: boolean;
}

const CURRENCIES = ["EGP", "USD", "EUR", "GBP", "SAR"];


function newJobRow(): JobRow {
  return {
    uid: crypto.randomUUID(),
    customerId: "",
    customerJobId: "",
    bookingNumber: "",
    description: "",
    pickUpTime: "",
    driverId: "",
    extras: [],
    collectionAmount: "",
    collectionCurrency: "EGP",
    custRepName: "",
    custRepMobile: "",
    extraDriverName: "",
    extraDriverPhone: "",
    serviceType: "ARR",
    originAirportId: "",
    originZoneId: "",
    originHotelId: "",
    destinationAirportId: "",
    destinationZoneId: "",
    destinationHotelId: "",
    paxCount: "1",
    saved: false,
    saving: false,
  };
}

/* ────────────────────────── Combobox ────────────────────────── */

function ComboSelect({
  options,
  value,
  onChange,
  placeholder,
  className,
}: {
  options: { value: string; label: string }[];
  value: string;
  onChange: (v: string) => void;
  placeholder?: string;
  className?: string;
}) {
  const [open, setOpen] = useState(false);
  const selected = options.find((o) => o.value === value);

  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger asChild>
        <Button
          variant="outline"
          role="combobox"
          className={cn(
            "h-8 w-full justify-between px-2 text-xs font-normal",
            !value && "text-muted-foreground",
            className
          )}
        >
          <span className="truncate">
            {selected ? selected.label : placeholder || "Select..."}
          </span>
          <ChevronDown className="ml-1 h-3 w-3 shrink-0 opacity-50" />
        </Button>
      </PopoverTrigger>
      <PopoverContent className="w-[220px] p-0" align="start">
        <Command>
          <CommandInput placeholder="Search..." className="h-8 text-xs" />
          <CommandList>
            <CommandEmpty>No results.</CommandEmpty>
            <CommandGroup>
              {options.map((o) => (
                <CommandItem
                  key={o.value}
                  value={o.label}
                  onSelect={() => {
                    onChange(o.value);
                    setOpen(false);
                  }}
                >
                  <Check
                    className={cn(
                      "mr-2 h-3 w-3",
                      value === o.value ? "opacity-100" : "opacity-0"
                    )}
                  />
                  <span className="text-xs">{o.label}</span>
                </CommandItem>
              ))}
            </CommandGroup>
          </CommandList>
        </Command>
      </PopoverContent>
    </Popover>
  );
}

/* ────────────────── Multi-Select Cars Combobox ────────────────── */

function MultiSelectCars({
  vehicles,
  selected,
  onChange,
}: {
  vehicles: Vehicle[];
  selected: Set<string>;
  onChange: (s: Set<string>) => void;
}) {
  const [open, setOpen] = useState(false);

  const allSelected = selected.size === vehicles.length && vehicles.length > 0;

  const toggle = (id: string) => {
    const next = new Set(selected);
    if (next.has(id)) next.delete(id);
    else next.add(id);
    onChange(next);
  };

  const toggleAll = () => {
    if (allSelected) onChange(new Set());
    else onChange(new Set(vehicles.map((v) => v.id)));
  };

  const selectedVehicles = vehicles.filter((v) => selected.has(v.id));

  return (
    <div className="flex items-center gap-2">
      <Popover open={open} onOpenChange={setOpen}>
        <PopoverTrigger asChild>
          <Button
            variant="outline"
            role="combobox"
            className="h-9 w-[350px] justify-between px-3 text-sm font-normal"
          >
            <span className="truncate">
              {selected.size === 0
                ? "Select cars..."
                : selected.size === vehicles.length
                  ? `All cars (${vehicles.length})`
                  : `${selected.size} car${selected.size > 1 ? "s" : ""} selected`}
            </span>
            <ChevronDown className="ml-2 h-4 w-4 shrink-0 opacity-50" />
          </Button>
        </PopoverTrigger>
        <PopoverContent className="w-[350px] p-0" align="start">
          <Command>
            <CommandInput placeholder="Search plate number..." className="h-9" />
            <CommandList>
              <CommandEmpty>No cars found.</CommandEmpty>
              <CommandGroup>
                {/* Select All */}
                <CommandItem onSelect={toggleAll} className="font-medium">
                  <div className={cn(
                    "mr-2 flex h-4 w-4 items-center justify-center rounded-sm border border-primary",
                    allSelected ? "bg-primary text-primary-foreground" : "opacity-50"
                  )}>
                    {allSelected && <Check className="h-3 w-3" />}
                  </div>
                  Select All
                  <span className="ml-auto text-xs text-muted-foreground">{vehicles.length}</span>
                </CommandItem>
                <div className="mx-1 my-1 h-px bg-border" />
                {/* Individual cars */}
                {vehicles.map((v) => {
                  const isSelected = selected.has(v.id);
                  return (
                    <CommandItem
                      key={v.id}
                      value={`${v.plateNumber} ${v.vehicleType?.name || ""}`}
                      onSelect={() => toggle(v.id)}
                    >
                      <div className={cn(
                        "mr-2 flex h-4 w-4 items-center justify-center rounded-sm border border-primary",
                        isSelected ? "bg-primary text-primary-foreground" : "opacity-50"
                      )}>
                        {isSelected && <Check className="h-3 w-3" />}
                      </div>
                      <span>{v.plateNumber}</span>
                      <span className="ml-auto text-xs text-muted-foreground">
                        {v.vehicleType?.name}
                      </span>
                    </CommandItem>
                  );
                })}
              </CommandGroup>
            </CommandList>
          </Command>
        </PopoverContent>
      </Popover>

      {/* Selected tags */}
      {selectedVehicles.length > 0 && (
        <div className="flex flex-wrap items-center gap-1">
          {selectedVehicles.map((v) => (
            <Badge
              key={v.id}
              variant="secondary"
              className="gap-1 pl-2 pr-1 text-xs cursor-pointer hover:bg-destructive/10"
              onClick={() => toggle(v.id)}
            >
              {v.plateNumber}
              <X className="h-3 w-3" />
            </Badge>
          ))}
        </div>
      )}
    </div>
  );
}

/* ─────────────────────── Main Page Component ─────────────────────── */

const CAR_DISPATCH_ENABLED = process.env.NEXT_PUBLIC_ENABLE_CAR_DISPATCH === "true";

export default function CarDispatchPage() {
  const router = useRouter();

  useEffect(() => {
    if (!CAR_DISPATCH_ENABLED) router.replace("/dashboard");
  }, [router]);

  if (!CAR_DISPATCH_ENABLED) return null;

  return <CarDispatchContent />;
}

function CarDispatchContent() {
  const t = useT();

  // Data
  const [ownedVehicles, setOwnedVehicles] = useState<Vehicle[]>([]);
  const [customers, setCustomers] = useState<Customer[]>([]);
  const [drivers, setDrivers] = useState<Driver[]>([]);
  const [suppliers, setSuppliers] = useState<Supplier[]>([]);
  const [vehicleTypes, setVehicleTypes] = useState<VehicleType[]>([]);
  const [zones, setZones] = useState<LocationOption[]>([]);

  // State
  const [cards, setCards] = useState<CarCard[]>([]);
  const [jobDate, setJobDate] = useState(() => {
    const d = new Date();
    return d.toISOString().slice(0, 10);
  });
  const [loading, setLoading] = useState(true);
  const [selectedOwnedIds, setSelectedOwnedIds] = useState<Set<string>>(new Set());
  const [addCarOpen, setAddCarOpen] = useState(false);
  const [selectedSupplierId, setSelectedSupplierId] = useState("");
  const [selectedSupplierCarTypeId, setSelectedSupplierCarTypeId] = useState("");
  const [supplierCarTypes, setSupplierCarTypes] = useState<VehicleType[]>([]);

  // ─── Fetch reference data ───
  const fetchData = useCallback(async () => {
    setLoading(true);
    try {
      const [vehRes, custRes, drvRes, supRes, typRes, zoneRes] = await Promise.all([
        api.get("/vehicles", { params: { limit: 100 } }),
        api.get("/customers", { params: { limit: 100 } }),
        api.get("/drivers", { params: { limit: 100, isActive: true } }),
        api.get("/dispatch/available-suppliers"),
        api.get("/vehicles/types"),
        api.get("/locations/zones"),
      ]);

      const allVehicles: Vehicle[] = (
        vehRes.data.data || vehRes.data
      ).filter((v: Vehicle) => v.isActive);
      const owned = allVehicles.filter((v) => !v.supplierId);
      setOwnedVehicles(owned);
      setCustomers(custRes.data.data || custRes.data);
      setDrivers(
        (drvRes.data.data || drvRes.data).filter((d: Driver) => d.isActive)
      );
      setSuppliers(supRes.data.data || supRes.data || []);
      setVehicleTypes(typRes.data.data || typRes.data || []);
      const rawZones = zoneRes.data.data || zoneRes.data || [];
      setZones(rawZones.map((z: { id: string; name: string; city?: { name: string } }) => ({
        id: z.id,
        name: z.city ? `${z.name} (${z.city.name})` : z.name,
      })));

      // Build initial cards from owned vehicles
      setCards((prev) => {
        // Keep existing supplier cards and their jobs
        const supplierCards = prev.filter((c) => c.isSupplier);
        const ownedCards = owned.map((v) => {
          const existing = prev.find(
            (c) => c.vehicle.id === v.id && !c.isSupplier
          );
          return {
            vehicle: v,
            jobs: existing?.jobs || [],
            isSupplier: false,
          };
        });
        return [...ownedCards, ...supplierCards];
      });
    } catch (err) {
      console.error("Failed to load data:", err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  // ─── Supplier car types loading ───
  useEffect(() => {
    if (!selectedSupplierId) {
      setSupplierCarTypes([]);
      return;
    }
    api
      .get(`/suppliers/${selectedSupplierId}/car-types`)
      .then((res) => {
        setSupplierCarTypes(res.data.data || res.data || []);
      })
      .catch(() => setSupplierCarTypes([]));
  }, [selectedSupplierId]);

  // ─── Load existing jobs for the selected date ───
  const loadJobsForDate = useCallback(async () => {
    try {
      const res = await api.get("/dispatch/day", { params: { date: jobDate } });
      const dayData = res.data.data || res.data;
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      const allJobs: any[] = [
        ...(dayData.arrivals || []),
        ...(dayData.departures || []),
        ...(dayData.city || []),
      ];

      // Group jobs by assigned vehicleId
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      const jobsByVehicle: Record<string, any[]> = {};
      for (const j of allJobs) {
        const vId = j.assignment?.vehicleId;
        if (!vId) continue;
        if (!jobsByVehicle[vId]) jobsByVehicle[vId] = [];
        jobsByVehicle[vId].push(j);
      }

      // Map API jobs to JobRow format
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      const toJobRow = (j: any): JobRow => ({
        uid: j.id,
        customerId: j.customerId || "",
        customerJobId: j.customerJobId || "",
        bookingNumber: j.internalRef || "",
        description: "",
        pickUpTime: j.pickUpTime ? new Date(j.pickUpTime).toTimeString().slice(0, 5) : "",
        driverId: j.assignment?.driverId || "",
        extras: ((j.jobExtras || []) as JobExtra[]).map((e) => ({
          id: e.id,
          extraId: e.extraId ?? null,
          name: e.name,
          qty: Number(e.qty),
          unitAmount: Number(e.unitAmount),
          currency: e.currency,
          source: e.source,
        })),
        collectionAmount: j.collectionAmount ? String(j.collectionAmount) : "",
        collectionCurrency: j.collectionCurrency || "EGP",
        custRepName: j.custRepName || "",
        custRepMobile: j.custRepMobile || "",
        extraDriverName: j.assignment?.externalDriverName || "",
        extraDriverPhone: j.assignment?.externalDriverPhone || "",
        serviceType: j.serviceType || "ARR",
        originAirportId: j.originAirportId || "",
        originZoneId: j.originZoneId || "",
        originHotelId: j.originHotelId || "",
        destinationAirportId: j.destinationAirportId || "",
        destinationZoneId: j.destinationZoneId || "",
        destinationHotelId: j.destinationHotelId || "",
        paxCount: String(j.paxCount || 1),
        saved: true,
        saving: false,
        savedJobId: j.id,
      });

      setCards((prev) =>
        prev.map((card) => {
          const existingJobs = jobsByVehicle[card.vehicle.id] || [];
          const existingRows = existingJobs.map(toJobRow);
          // Keep unsaved rows the user is currently editing
          const unsavedRows = card.jobs.filter((r) => !r.saved);
          return { ...card, jobs: [...existingRows, ...unsavedRows] };
        })
      );

      // Auto-select owned vehicles that have jobs on this date
      const vehicleIdsWithJobs = new Set(Object.keys(jobsByVehicle));
      if (vehicleIdsWithJobs.size > 0) {
        setSelectedOwnedIds((prev) => {
          const next = new Set(prev);
          for (const vId of vehicleIdsWithJobs) next.add(vId);
          return next;
        });
      }
    } catch {
      // Dispatch day endpoint may fail on dev environments with schema drift — silently skip
    }
  }, [jobDate]);

  useEffect(() => {
    if (!loading) {
      loadJobsForDate();
    }
  }, [jobDate, loading, loadJobsForDate]);

  // ─── Add supplier car ───
  const handleAddSupplierCar = () => {
    const carType = supplierCarTypes.find((ct) => ct.id === selectedSupplierCarTypeId);
    if (!carType) return;
    const supplier = suppliers.find((s) => s.id === selectedSupplierId);
    // Create a virtual vehicle card representing this supplier + car type
    const virtualId = `sup_${selectedSupplierId}_${selectedSupplierCarTypeId}`;
    if (cards.some((c) => c.vehicle.id === virtualId)) return;
    const virtualVehicle: Vehicle = {
      id: virtualId,
      plateNumber: supplier?.tradeName || supplier?.legalName || "Supplier",
      vehicleTypeId: carType.id,
      vehicleType: carType,
      ownership: "CONTRACTED",
      supplierId: selectedSupplierId,
      isActive: true,
      carBrand: null,
      carModel: null,
    };
    setCards((prev) => [
      ...prev,
      { vehicle: virtualVehicle, jobs: [], isSupplier: true },
    ]);
    setAddCarOpen(false);
    setSelectedSupplierId("");
    setSelectedSupplierCarTypeId("");
  };

  // ─── Remove supplier card ───
  const removeSupplierCard = (vehicleId: string) => {
    setCards((prev) => prev.filter((c) => c.vehicle.id !== vehicleId));
  };

  // ─── Job row management ───
  const addJobRow = (vehicleId: string) => {
    setCards((prev) =>
      prev.map((c) =>
        c.vehicle.id === vehicleId
          ? { ...c, jobs: [...c.jobs, newJobRow()] }
          : c
      )
    );
  };

  const updateJobField = (
    vehicleId: string,
    uid: string,
    field: keyof JobRow,
    value: string | boolean | number
  ) => {
    setCards((prev) =>
      prev.map((c) =>
        c.vehicle.id === vehicleId
          ? {
              ...c,
              jobs: c.jobs.map((j) =>
                j.uid === uid ? { ...j, [field]: value } : j
              ),
            }
          : c
      )
    );
  };

  const removeJobRow = (vehicleId: string, uid: string) => {
    setCards((prev) =>
      prev.map((c) =>
        c.vehicle.id === vehicleId
          ? { ...c, jobs: c.jobs.filter((j) => j.uid !== uid) }
          : c
      )
    );
  };

  // ─── Save job row → B2B pool ───
  const saveJobRow = async (vehicleId: string, uid: string) => {
    const card = cards.find((c) => c.vehicle.id === vehicleId);
    if (!card) return;
    const job = card.jobs.find((j) => j.uid === uid);
    if (!job || job.saved || job.saving) return;

    // Client-side validation
    const errors: string[] = [];
    if (!job.customerId) errors.push("Customer is required");
    if (!job.originZoneId && !job.originAirportId && !job.originHotelId)
      errors.push("Origin is required");
    if (!job.destinationZoneId && !job.destinationAirportId && !job.destinationHotelId)
      errors.push("Destination is required");
    if (errors.length > 0) {
      setCards((prev) =>
        prev.map((c) =>
          c.vehicle.id === vehicleId
            ? {
                ...c,
                jobs: c.jobs.map((j) =>
                  j.uid === uid ? { ...j, error: errors.join(", ") } : j
                ),
              }
            : c
        )
      );
      return;
    }

    // Mark saving
    setCards((prev) =>
      prev.map((c) =>
        c.vehicle.id === vehicleId
          ? {
              ...c,
              jobs: c.jobs.map((j) =>
                j.uid === uid ? { ...j, saving: true } : j
              ),
            }
          : c
      )
    );

    try {
      // Build payload for traffic-jobs API
      const payload: Record<string, unknown> = {
        bookingChannel: "B2B",
        serviceType: job.serviceType || "ARR",
        jobDate: jobDate,
        adultCount: parseInt(job.paxCount) || 1,
        childCount: 0,
        customerId: job.customerId || undefined,
        customerJobId: job.customerJobId?.trim() || undefined,
        custRepName: job.custRepName || undefined,
        custRepMobile: job.custRepMobile || undefined,
        extras: job.extras
          .filter((e) => e.name && e.qty > 0)
          .map((e) => ({
            extraId: e.extraId ?? undefined,
            name: e.name,
            qty: e.qty,
            unitAmount: e.unitAmount,
            currency: e.currency,
            source: e.source,
          })),
        pickUpTime: job.pickUpTime
          ? `${jobDate}T${job.pickUpTime}:00`
          : undefined,
        collectionRequired: !!job.collectionAmount,
        collectionAmount: job.collectionAmount
          ? parseFloat(job.collectionAmount)
          : undefined,
        collectionCurrency: job.collectionCurrency || "EGP",
      };

      // Origin / destination from description or IDs
      if (job.originAirportId) payload.originAirportId = job.originAirportId;
      if (job.originZoneId) payload.originZoneId = job.originZoneId;
      if (job.originHotelId) payload.originHotelId = job.originHotelId;
      if (job.destinationAirportId)
        payload.destinationAirportId = job.destinationAirportId;
      if (job.destinationZoneId)
        payload.destinationZoneId = job.destinationZoneId;
      if (job.destinationHotelId)
        payload.destinationHotelId = job.destinationHotelId;

      // For supplier cards: set requested vehicle type, no real vehicle assignment
      if (card.isSupplier) {
        payload.requestedVehicleTypeId = card.vehicle.vehicleTypeId;
      }

      // Remove undefined
      Object.keys(payload).forEach(
        (k) => payload[k] === undefined && delete payload[k]
      );

      const res = await api.post("/traffic-jobs", payload);
      const created = res.data.data || res.data;

      // Only assign real vehicle + driver for owned cars (not supplier cards)
      if (created.id && !card.isSupplier) {
        const assignPayload: Record<string, unknown> = {
          trafficJobId: created.id,
          vehicleId: vehicleId,
        };
        if (job.driverId) {
          assignPayload.driverId = job.driverId;
        }
        if (job.extraDriverName) {
          assignPayload.externalDriverName = job.extraDriverName;
          if (job.extraDriverPhone) {
            assignPayload.externalDriverPhone = job.extraDriverPhone;
          }
        }
        await api.post("/dispatch/assign", assignPayload);
      }

      // Update row as saved
      setCards((prev) =>
        prev.map((c) =>
          c.vehicle.id === vehicleId
            ? {
                ...c,
                jobs: c.jobs.map((j) =>
                  j.uid === uid
                    ? {
                        ...j,
                        saved: true,
                        saving: false,
                        savedJobId: created.id,
                        bookingNumber: created.internalRef || "",
                        error: undefined,
                      }
                    : j
                ),
              }
            : c
        )
      );
    } catch (err: unknown) {
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      const axErr = err as any;
      const apiMsg = axErr?.response?.data?.message;
      const msg = Array.isArray(apiMsg) ? apiMsg.join(", ") : apiMsg || (err instanceof Error ? err.message : "Failed to save job");
      setCards((prev) =>
        prev.map((c) =>
          c.vehicle.id === vehicleId
            ? {
                ...c,
                jobs: c.jobs.map((j) =>
                  j.uid === uid
                    ? { ...j, saving: false, error: msg }
                    : j
                ),
              }
            : c
        )
      );
    }
  };

  // ─── Save all unsaved jobs on a card ───
  const saveAllJobs = async (vehicleId: string) => {
    const card = cards.find((c) => c.vehicle.id === vehicleId);
    if (!card) return;
    for (const job of card.jobs) {
      if (!job.saved && !job.saving) {
        await saveJobRow(vehicleId, job.uid);
      }
    }
  };

  // ─── Combobox option lists ───
  const customerOptions = customers.map((c) => ({
    value: c.id,
    label: c.tradeName || c.legalName,
  }));

  const driverOptions = drivers.map((d) => ({
    value: d.id,
    label: `${d.name} (${d.mobileNumber})`,
  }));

  const supplierOptions = suppliers.map((s) => ({
    value: s.id,
    label: s.tradeName || s.legalName,
  }));


  if (loading) {
    return (
      <div className="flex h-[60vh] items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-4 p-4">
      {/* ─── Page Header ─── */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Car Dispatch</h1>
          <p className="text-sm text-muted-foreground">
            Assign jobs to vehicles — jobs are posted to B2B pool on save
          </p>
        </div>
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2">
            <Label className="text-sm font-medium">Date:</Label>
            <Input
              type="date"
              value={jobDate}
              onChange={(e) => setJobDate(e.target.value)}
              min="2020-01-01"
              className="h-9 w-[160px]"
            />
          </div>
          <Button onClick={() => setAddCarOpen(true)} className="gap-2">
            <Plus className="h-4 w-4" />
            Add Supplier Car
          </Button>
        </div>
      </div>

      <Separator />

      {/* ─── Owned Car Multi-Select ─── */}
      {ownedVehicles.length > 0 && (
        <MultiSelectCars
          vehicles={ownedVehicles}
          selected={selectedOwnedIds}
          onChange={setSelectedOwnedIds}
        />
      )}

      {/* ─── Car Cards Grid ─── */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {cards.filter((c) => c.isSupplier || selectedOwnedIds.has(c.vehicle.id)).map((card) => (
          <VehicleCard
            key={card.vehicle.id}
            card={card}
            customerOptions={customerOptions}
            driverOptions={driverOptions}
            zoneOptions={zones}
            jobDate={jobDate}
            onAddJob={() => addJobRow(card.vehicle.id)}
            onUpdateField={(uid, field, value) =>
              updateJobField(card.vehicle.id, uid, field, value)
            }
            onRemoveJob={(uid) => removeJobRow(card.vehicle.id, uid)}
            onSaveJob={(uid) => saveJobRow(card.vehicle.id, uid)}
            onSaveAll={() => saveAllJobs(card.vehicle.id)}
            onRemoveCard={
              card.isSupplier
                ? () => removeSupplierCard(card.vehicle.id)
                : undefined
            }
          />
        ))}

        {cards.length === 0 && (
          <div className="flex h-[40vh] items-center justify-center text-muted-foreground">
            No vehicles found. Add a supplier car to get started.
          </div>
        )}
      </div>

      {/* ─── Add Supplier Car Dialog ─── */}
      <Dialog open={addCarOpen} onOpenChange={setAddCarOpen}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>Add Supplier Car</DialogTitle>
          </DialogHeader>
          <div className="space-y-4 py-2">
            <div className="space-y-2">
              <Label>Supplier</Label>
              <ComboSelect
                options={supplierOptions}
                value={selectedSupplierId}
                onChange={(v) => {
                  setSelectedSupplierId(v);
                  setSelectedSupplierCarTypeId("");
                }}
                placeholder="Select supplier..."
              />
            </div>
            {selectedSupplierId && (
              <div className="space-y-2">
                <Label>Car Type</Label>
                {supplierCarTypes.length === 0 ? (
                  <p className="text-sm text-muted-foreground">
                    No car types defined for this supplier. Add car types in the supplier settings.
                  </p>
                ) : (
                  <ComboSelect
                    options={supplierCarTypes.map((ct) => ({
                      value: ct.id,
                      label: `${ct.name} (${ct.seatCapacity} seats)`,
                    }))}
                    value={selectedSupplierCarTypeId}
                    onChange={setSelectedSupplierCarTypeId}
                    placeholder="Select car type..."
                  />
                )}
              </div>
            )}
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setAddCarOpen(false)}>
              Cancel
            </Button>
            <Button
              onClick={handleAddSupplierCar}
              disabled={!selectedSupplierCarTypeId}
            >
              Add Vehicle
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}

/* ───────────────────── Vehicle Card Component ───────────────────── */

function VehicleCard({
  card,
  customerOptions,
  driverOptions,
  zoneOptions,
  jobDate,
  onAddJob,
  onUpdateField,
  onRemoveJob,
  onSaveJob,
  onSaveAll,
  onRemoveCard,
}: {
  card: CarCard;
  customerOptions: { value: string; label: string }[];
  driverOptions: { value: string; label: string }[];
  zoneOptions: LocationOption[];
  jobDate: string;
  onAddJob: () => void;
  onUpdateField: (uid: string, field: keyof JobRow, value: string | boolean | number) => void;
  onRemoveJob: (uid: string) => void;
  onSaveJob: (uid: string) => void;
  onSaveAll: () => void;
  onRemoveCard?: () => void;
}) {
  const { vehicle, jobs, isSupplier } = card;
  const unsavedCount = jobs.filter((j) => !j.saved).length;

  return (
    <Card
      className={cn(
        "overflow-hidden text-[11px] [&_*]:text-[11px]",
        isSupplier && "border-amber-300 dark:border-amber-700"
      )}
    >
      {/* ─── Card Header: Plate + Type ─── */}
      <CardHeader className="flex flex-row items-center justify-between gap-4 border-b bg-muted/40 px-4 py-3">
        <div className="flex items-center gap-3">
          <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-primary/10">
            <Car className="h-5 w-5 text-primary" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="text-lg font-bold tracking-wider">
                {vehicle.plateNumber}
              </span>
              <Badge variant="secondary" className="text-xs">
                {vehicle.vehicleType?.name || "Unknown"}
              </Badge>
              {isSupplier && (
                <Badge
                  variant="outline"
                  className="border-amber-400 text-amber-600 text-xs"
                >
                  Supplier
                </Badge>
              )}
            </div>
            {(vehicle.carBrand || vehicle.carModel) && (
              <p className="text-xs text-muted-foreground">
                {[vehicle.carBrand, vehicle.carModel]
                  .filter(Boolean)
                  .join(" ")}
              </p>
            )}
          </div>
        </div>
        <div className="flex items-center gap-2">
          {unsavedCount > 0 && (
            <Button
              size="sm"
              onClick={onSaveAll}
              className="gap-1.5"
            >
              <Save className="h-3.5 w-3.5" />
              Save All ({unsavedCount})
            </Button>
          )}
          <Button size="sm" variant="outline" onClick={onAddJob} className="gap-1.5">
            <Plus className="h-3.5 w-3.5" />
            Add Job
          </Button>
          {onRemoveCard && (
            <Button
              size="sm"
              variant="ghost"
              onClick={onRemoveCard}
              className="text-destructive hover:text-destructive"
            >
              <X className="h-4 w-4" />
            </Button>
          )}
        </div>
      </CardHeader>

      {/* ─── Jobs Table ─── */}
      <CardContent className="p-0">
        {jobs.length === 0 ? (
          <div className="flex items-center justify-center py-8 text-sm text-muted-foreground">
            No jobs yet — click &quot;Add Job&quot; to start
          </div>
        ) : (
          <div className="overflow-x-auto [overflow-y:clip]">
            <table className="w-full border-collapse text-xs">
              <thead>
                <tr className="bg-muted/50">
                  <th className="border border-border px-1 py-1 text-left font-semibold text-xs">Customer</th>
                  <th className="border border-border px-1 py-1 text-left font-semibold text-xs">Booking #</th>
                  <th className="border border-border px-1 py-1 text-left font-semibold text-xs">Cust. Job ID</th>
                  <th className="border border-border px-1 py-1 text-left font-semibold text-xs">Origin</th>
                  <th className="border border-border px-1 py-1 text-left font-semibold text-xs">Destination</th>
                  <th className="border border-border px-1 py-1 text-left font-semibold text-xs">Time</th>
                  <th className="border border-border px-1 py-1 text-left font-semibold text-xs">Driver</th>
                  <th className="border border-border px-1 py-1 text-left font-semibold text-xs">Cust. Rep</th>
                  <th className="border border-border px-1 py-1 text-left font-semibold text-xs">Extra Driver</th>
                  <th className="border border-border px-1 py-1 text-left font-semibold text-xs">Type</th>
                  <th className="border border-border px-1 py-1 text-center font-semibold text-xs">Pax</th>
                  <th className="border border-border px-1 py-1 text-center font-semibold text-xs">Act</th>
                </tr>
              </thead>
              <tbody>
                {jobs.map((job) => (
                  <JobRowComponent
                    key={job.uid}
                    job={job}
                    isSupplierCard={isSupplier}
                    customerOptions={customerOptions}
                    driverOptions={driverOptions}
                    zoneOptions={zoneOptions}
                    onUpdate={(field, value) =>
                      onUpdateField(job.uid, field, value)
                    }
                    onRemove={() => onRemoveJob(job.uid)}
                    onSave={() => onSaveJob(job.uid)}
                  />
                ))}
              </tbody>
            </table>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

/* ───────────────────── Job Row Component ───────────────────── */

function JobRowComponent({
  job,
  isSupplierCard,
  customerOptions,
  driverOptions,
  zoneOptions,
  onUpdate,
  onRemove,
  onSave,
}: {
  job: JobRow;
  isSupplierCard: boolean;
  customerOptions: { value: string; label: string }[];
  driverOptions: { value: string; label: string }[];
  zoneOptions: LocationOption[];
  onUpdate: (field: keyof JobRow, value: string | boolean | number) => void;
  onRemove: () => void;
  onSave: () => void;
}) {
  const cell = "border border-border p-0 align-top";
  const inp = "h-7 rounded-none border-0 bg-transparent px-1 text-xs shadow-none focus-visible:ring-1 focus-visible:ring-inset focus-visible:ring-primary";

  return (
    <tr
      className={cn(
        job.saved && "bg-green-50 dark:bg-green-950/20",
        job.error && "bg-red-50 dark:bg-red-950/20"
      )}
    >
      {/* Customer */}
      <td className={cell}>
        <ComboSelect
          options={customerOptions}
          value={job.customerId}
          onChange={(v) => onUpdate("customerId", v)}
          placeholder="Customer..."
          className="h-7 rounded-none border-0 shadow-none"
        />
      </td>

      {/* Booking # */}
      <td className={cn(cell, "px-1 text-center")}>
        {job.bookingNumber ? (
          <span className="text-[11px] font-mono">{job.bookingNumber}</span>
        ) : (
          <span className="text-[10px] text-muted-foreground italic">Auto</span>
        )}
      </td>

      {/* Customer Job ID */}
      <td className={cell}>
        <Input
          value={job.customerJobId}
          onChange={(e) => onUpdate("customerJobId", e.target.value)}
          placeholder="Cust. Job ID..."
          className="h-7 rounded-none border-0 shadow-none text-xs"
          disabled={job.saved}
        />
      </td>

      {/* Origin Zone */}
      <td className={cell}>
        <ComboSelect
          options={zoneOptions.map((z) => ({ value: z.id, label: z.name }))}
          value={job.originZoneId}
          onChange={(v) => onUpdate("originZoneId", v)}
          placeholder="Origin..."
          className="h-7 rounded-none border-0 shadow-none"
        />
      </td>

      {/* Destination Zone */}
      <td className={cell}>
        <ComboSelect
          options={zoneOptions.map((z) => ({ value: z.id, label: z.name }))}
          value={job.destinationZoneId}
          onChange={(v) => onUpdate("destinationZoneId", v)}
          placeholder="Dest..."
          className="h-7 rounded-none border-0 shadow-none"
        />
      </td>

      {/* Time (24hr) */}
      <td className={cell}>
        <Input
          type="text"
          value={job.pickUpTime}
          onChange={(e) => {
            let v = e.target.value.replace(/[^0-9:]/g, "");
            if (v.length === 2 && !v.includes(":")) v += ":";
            if (v.length > 5) v = v.slice(0, 5);
            onUpdate("pickUpTime", v);
          }}
          placeholder="HH:MM"
          maxLength={5}
          className={cn(inp, "font-mono")}
          disabled={job.saved}
        />
      </td>

      {/* Driver */}
      <td className={cell}>
        {isSupplierCard ? (
          <span className="px-1 text-[10px] text-muted-foreground italic">External</span>
        ) : (
          <ComboSelect
            options={driverOptions}
            value={job.driverId}
            onChange={(v) => onUpdate("driverId", v)}
            placeholder="Driver..."
            className="h-7 rounded-none border-0 shadow-none"
          />
        )}
      </td>

      {/* Customer Rep */}
      <td className={cell}>
        <Input
          value={job.custRepName}
          onChange={(e) => onUpdate("custRepName", e.target.value)}
          placeholder="Name"
          className={cn(inp, "border-b border-border rounded-none")}
          disabled={job.saved}
        />
        <Input
          value={job.custRepMobile}
          onChange={(e) => onUpdate("custRepMobile", e.target.value)}
          placeholder="Mobile"
          className={inp}
          disabled={job.saved}
        />
      </td>

      {/* Extra Driver (always shown — supplier cards use this for external driver) */}
      <td className={cell}>
        <Input
          value={job.extraDriverName}
          onChange={(e) => onUpdate("extraDriverName", e.target.value)}
          placeholder="Name"
          className={cn(inp, "border-b border-border rounded-none")}
          disabled={job.saved}
        />
        <Input
          value={job.extraDriverPhone}
          onChange={(e) => onUpdate("extraDriverPhone", e.target.value)}
          placeholder="Phone"
          className={inp}
          disabled={job.saved}
        />
      </td>

      {/* Transfer Type */}
      <td className={cell}>
        <select
          value={job.serviceType}
          onChange={(e) => onUpdate("serviceType", e.target.value)}
          disabled={job.saved}
          className="h-7 w-full border-0 bg-transparent px-1 text-xs focus:outline-none"
        >
          {SERVICE_TYPE_DROPDOWN_OPTIONS.map((st) => (
            <option key={st.value} value={st.value}>{st.label}</option>
          ))}
        </select>
      </td>

      {/* Pax */}
      <td className={cell}>
        <input
          type="number"
          min={1}
          value={job.paxCount}
          onChange={(e) => onUpdate("paxCount", e.target.value)}
          className="h-7 w-full border-0 bg-transparent px-1 text-xs text-center focus:outline-none"
          disabled={job.saved}
        />
      </td>

      {/* Actions */}
      <td className={cn(cell, "text-center")}>
        <div className="flex items-center justify-center gap-0">
          {!job.saved && (
            <button
              onClick={onSave}
              disabled={job.saving}
              className="h-7 w-7 inline-flex items-center justify-center text-primary hover:bg-primary/10"
            >
              {job.saving ? (
                <Loader2 className="h-3.5 w-3.5 animate-spin" />
              ) : (
                <Save className="h-3.5 w-3.5" />
              )}
            </button>
          )}
          {job.saved && (
            <span className="text-[10px] text-green-600 font-medium">OK</span>
          )}
          {!job.saved && (
            <button
              onClick={onRemove}
              className="h-7 w-7 inline-flex items-center justify-center text-destructive hover:bg-destructive/10"
            >
              <Trash2 className="h-3.5 w-3.5" />
            </button>
          )}
        </div>
        {job.error && (
          <p className="text-[9px] text-destructive leading-tight px-0.5 truncate" title={job.error}>
            {job.error}
          </p>
        )}
      </td>
    </tr>
  );
}
