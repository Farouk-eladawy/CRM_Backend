"use client";

import { useState, useEffect, useCallback, useMemo, useRef } from "react";
import { Plus, Pencil, Trash2, Receipt, Copy, Check, ChevronsUpDown, Download, Upload, Settings2 } from "lucide-react";
import { toast } from "sonner";
import { PageHeader } from "@/components/page-header";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
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
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover";
import {
  Command,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
} from "@/components/ui/command";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import { cn } from "@/lib/utils";
import { SearchableCombobox } from "@/components/searchable-combobox";
import api from "@/lib/api";
import { usePermission } from "@/hooks/use-permission";

interface Zone {
  id: string;
  name: string;
  city?: { name: string };
}

interface Airport {
  id: string;
  name: string;
  code: string;
}

interface VehicleType {
  id: string;
  name: string;
  seatCapacity?: number;
}

interface JobServiceType {
  id: string;
  name: string;
  fromZone?: { id: string; name: string } | null;
  toZone?: { id: string; name: string } | null;
}

interface Tariff {
  id: string;
  fromZone?: Zone | null;
  toZone?: Zone | null;
  fromAirport?: Airport | null;
  toAirport?: Airport | null;
  vehicleType: VehicleType;
  jobServiceType?: JobServiceType | null;
  amount: number;
  currency: string;
  notes: string | null;
  isActive: boolean;
}

// A unified location item used across all location pickers
interface LocationItem {
  value: string;       // prefixed: "zone:id" or "airport:id"
  label: string;
  sub?: string;
  type: "zone" | "airport";
}

function locationLabel(t: Tariff, side: "from" | "to") {
  if (side === "from") {
    if (t.fromAirport) return `${t.fromAirport.code} – ${t.fromAirport.name}`;
    if (t.fromZone)    return t.fromZone.name + (t.fromZone.city ? ` (${t.fromZone.city.name})` : "");
    return "—";
  }
  if (t.toAirport) return `${t.toAirport.code} – ${t.toAirport.name}`;
  if (t.toZone)    return t.toZone.name + (t.toZone.city ? ` (${t.toZone.city.name})` : "");
  return "—";
}

const EMPTY_FORM = {
  jobServiceTypeId: "",
  fromLocationValue: "",   // "zone:<id>" | "airport:<id>"
  toLocationValue: "",
  vehicleTypeId: "",
  amount: "",
  currency: "EGP",
  notes: "",
};

// Parse a prefixed location value back to DTO fields
function parseLocation(val: string): { fromZoneId?: string; fromAirportId?: string } | { toZoneId?: string; toAirportId?: string } | null {
  if (!val) return null;
  const [type, id] = val.split(":");
  if (type === "zone")    return { fromZoneId: id };
  if (type === "airport") return { fromAirportId: id };
  return null;
}
function parseFromLocation(val: string) {
  if (!val) return {};
  const [type, id] = val.split(":");
  if (type === "zone")    return { fromZoneId: id,    fromAirportId: undefined };
  if (type === "airport") return { fromAirportId: id, fromZoneId: undefined };
  return {};
}
function parseToLocation(val: string) {
  if (!val) return {};
  const [type, id] = val.split(":");
  if (type === "zone")    return { toZoneId: id,    toAirportId: undefined };
  if (type === "airport") return { toAirportId: id, toZoneId: undefined };
  return {};
}

// ── Creatable Combobox (for Service Type) ─────────────────────────────────────

function CreatableCombobox({
  items,
  value,
  onChange,
  onCreate,
  placeholder,
  searchPlaceholder,
}: {
  items: { value: string; label: string }[];
  value: string;
  onChange: (v: string) => void;
  onCreate: (name: string) => Promise<{ id: string; name: string } | null>;
  placeholder?: string;
  searchPlaceholder?: string;
}) {
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const [creating, setCreating] = useState(false);

  const selected = items.find((i) => i.value === value);
  const filtered = items.filter((i) => i.label.toLowerCase().includes(query.toLowerCase()));
  const canCreate = query.trim() && !items.some((i) => i.label.toLowerCase() === query.toLowerCase());

  const handleCreate = async () => {
    if (!query.trim()) return;
    setCreating(true);
    const created = await onCreate(query.trim());
    setCreating(false);
    if (created) {
      onChange(created.id);
      setOpen(false);
      setQuery("");
    }
  };

  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger asChild>
        <Button variant="outline" role="combobox" aria-expanded={open} className="w-full justify-between font-normal">
          <span className="truncate text-left">
            {selected ? selected.label : <span className="text-muted-foreground">{placeholder ?? "Select…"}</span>}
          </span>
          <ChevronsUpDown className="ml-2 h-4 w-4 shrink-0 opacity-50" />
        </Button>
      </PopoverTrigger>
      <PopoverContent className="w-[--radix-popover-trigger-width] p-0" align="start">
        <Command shouldFilter={false}>
          <CommandInput
            placeholder={searchPlaceholder ?? "Search or type new…"}
            value={query}
            onValueChange={setQuery}
          />
          <CommandList>
            {filtered.length === 0 && !canCreate && (
              <CommandEmpty>No results.</CommandEmpty>
            )}
            <CommandGroup>
              {filtered.map((item) => (
                <CommandItem
                  key={item.value}
                  value={item.value}
                  onSelect={() => { onChange(item.value); setOpen(false); setQuery(""); }}
                >
                  <Check className={cn("mr-2 h-4 w-4", value === item.value ? "opacity-100" : "opacity-0")} />
                  {item.label}
                </CommandItem>
              ))}
              {canCreate && (
                <CommandItem
                  value="__create__"
                  onSelect={handleCreate}
                  disabled={creating}
                  className="text-primary font-medium"
                >
                  <Plus className="mr-2 h-4 w-4" />
                  {creating ? "Creating…" : `Create "${query.trim()}"`}
                </CommandItem>
              )}
            </CommandGroup>
          </CommandList>
        </Command>
      </PopoverContent>
    </Popover>
  );
}

// ── Service Types Manager Modal ───────────────────────────────────────────────

function ServiceTypesManager({
  open,
  onClose,
  zones,
  onChanged,
}: {
  open: boolean;
  onClose: () => void;
  zones: Zone[];
  onChanged: () => void;
}) {
  const canUpsert = usePermission("driver-tariffs.upsert");
  const canDelete = usePermission("driver-tariffs.delete");

  const [items, setItems] = useState<JobServiceType[]>([]);
  const [loading, setLoading] = useState(false);

  // Form state
  const [formOpen, setFormOpen] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [name, setName] = useState("");
  const [fromZoneId, setFromZoneId] = useState("");
  const [toZoneId, setToZoneId] = useState("");
  const [saving, setSaving] = useState(false);

  // Delete
  const [deleteId, setDeleteId] = useState<string | null>(null);
  const [deleting, setDeleting] = useState(false);

  // Import
  const importRef = useRef<HTMLInputElement>(null);
  const [importing, setImporting] = useState(false);
  const [dlTemplate, setDlTemplate] = useState(false);
  const [importResult, setImportResult] = useState<{ open: boolean; imported: number; errors: string[] }>({
    open: false, imported: 0, errors: [],
  });

  const zoneItems = useMemo(
    () => zones.map((z) => ({ value: z.id, label: z.name, sub: z.city?.name })),
    [zones]
  );

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const res = await api.get("/job-service-types");
      setItems(res.data.data || res.data || []);
    } catch {
      toast.error("Failed to load service types");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (open) load();
  }, [open, load]);

  const openAdd = () => {
    setEditingId(null); setName(""); setFromZoneId(""); setToZoneId("");
    setFormOpen(true);
  };

  const openEdit = (st: JobServiceType) => {
    setEditingId(st.id);
    setName(st.name);
    setFromZoneId(st.fromZone?.id ?? "");
    setToZoneId(st.toZone?.id ?? "");
    setFormOpen(true);
  };

  const handleSave = async () => {
    if (!name.trim()) { toast.error("Name is required"); return; }
    setSaving(true);
    try {
      if (editingId) {
        await api.patch(`/job-service-types/${editingId}`, {
          name: name.trim(),
          fromZoneId: fromZoneId || null,
          toZoneId: toZoneId || null,
        });
        toast.success("Service type updated");
      } else {
        await api.post("/job-service-types", {
          name: name.trim(),
          fromZoneId: fromZoneId || undefined,
          toZoneId: toZoneId || undefined,
        });
        toast.success("Service type created");
      }
      setFormOpen(false);
      load();
      onChanged();
    } catch (err: any) {
      toast.error(err?.response?.data?.message || "Failed to save");
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async () => {
    if (!deleteId) return;
    setDeleting(true);
    try {
      await api.delete(`/job-service-types/${deleteId}`);
      toast.success("Service type deleted");
      setDeleteId(null);
      load();
      onChanged();
    } catch {
      toast.error("Failed to delete");
    } finally {
      setDeleting(false);
    }
  };

  const handleDownloadTemplate = async () => {
    setDlTemplate(true);
    try {
      const res = await api.get("/job-service-types/import/template", { responseType: "blob" });
      const url = window.URL.createObjectURL(new Blob([res.data]));
      const a = document.createElement("a");
      a.href = url; a.setAttribute("download", "service_types_template.xlsx");
      document.body.appendChild(a); a.click(); a.remove();
      window.URL.revokeObjectURL(url);
    } catch {
      toast.error("Failed to download template");
    } finally {
      setDlTemplate(false);
    }
  };

  const handleImport = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setImporting(true);
    try {
      const formData = new FormData();
      formData.append("file", file);
      const res = await api.post("/job-service-types/import/excel", formData, {
        headers: { "Content-Type": "multipart/form-data" },
      });
      const result = res.data.data;
      setImportResult({ open: true, imported: result.imported, errors: result.errors });
      if (result.imported > 0) { load(); onChanged(); }
    } catch (err: any) {
      toast.error(err?.response?.data?.message || "Import failed");
    } finally {
      setImporting(false);
      if (importRef.current) importRef.current.value = "";
    }
  };

  return (
    <>
      <Dialog open={open} onOpenChange={(o) => !o && onClose()}>
        <DialogContent className="w-[90vw] max-w-3xl max-h-[90vh] flex flex-col">
          <DialogHeader>
            <DialogTitle>Manage Service Types</DialogTitle>
          </DialogHeader>

          {/* Toolbar */}
          <div className="flex items-center justify-between gap-2 py-1">
            <span className="text-sm text-muted-foreground">
              {items.length} service type{items.length !== 1 ? "s" : ""}
            </span>
            <div className="flex gap-2">
              <Button variant="outline" size="sm" onClick={handleDownloadTemplate} disabled={dlTemplate}>
                <Download className="h-4 w-4 mr-1.5" />
                {dlTemplate ? "Downloading…" : "Template"}
              </Button>
              {canUpsert && (
                <>
                  <Button variant="outline" size="sm" onClick={() => importRef.current?.click()} disabled={importing}>
                    <Upload className="h-4 w-4 mr-1.5" />
                    {importing ? "Importing…" : "Import"}
                  </Button>
                  <input ref={importRef} type="file" accept=".xlsx,.xls" className="hidden" onChange={handleImport} />
                  <Button size="sm" onClick={openAdd}>
                    <Plus className="h-4 w-4 mr-1.5" /> Add
                  </Button>
                </>
              )}
            </div>
          </div>

          {/* Table */}
          <div className="flex-1 overflow-y-auto rounded border">
            {loading ? (
              <div className="flex items-center justify-center h-32 text-sm text-muted-foreground">Loading…</div>
            ) : items.length === 0 ? (
              <div className="flex flex-col items-center justify-center h-32 gap-2 text-sm text-muted-foreground">
                <p>No service types yet.</p>
                {canUpsert && (
                  <Button variant="outline" size="sm" onClick={openAdd}>
                    <Plus className="h-4 w-4 mr-1" /> Add first service type
                  </Button>
                )}
              </div>
            ) : (
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Name</TableHead>
                    <TableHead>From Zone</TableHead>
                    <TableHead>To Zone</TableHead>
                    {(canUpsert || canDelete) && <TableHead className="text-right w-24">Actions</TableHead>}
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {items.map((st) => (
                    <TableRow key={st.id}>
                      <TableCell className="font-medium">{st.name}</TableCell>
                      <TableCell className="text-sm text-muted-foreground">{st.fromZone?.name ?? "—"}</TableCell>
                      <TableCell className="text-sm text-muted-foreground">{st.toZone?.name ?? "—"}</TableCell>
                      {(canUpsert || canDelete) && (
                        <TableCell className="text-right">
                          <div className="flex justify-end gap-1">
                            {canUpsert && (
                              <Button variant="ghost" size="icon" onClick={() => openEdit(st)}>
                                <Pencil className="h-4 w-4" />
                              </Button>
                            )}
                            {canDelete && (
                              <Button variant="ghost" size="icon" onClick={() => setDeleteId(st.id)}>
                                <Trash2 className="h-4 w-4 text-destructive" />
                              </Button>
                            )}
                          </div>
                        </TableCell>
                      )}
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            )}
          </div>

          <DialogFooter>
            <Button variant="outline" onClick={onClose}>Close</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Add / Edit form */}
      <Dialog open={formOpen} onOpenChange={(o) => !o && setFormOpen(false)}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle>{editingId ? "Edit Service Type" : "Add Service Type"}</DialogTitle>
          </DialogHeader>
          <div className="space-y-4 py-2">
            <div className="space-y-1.5">
              <Label>Name <span className="text-destructive">*</span></Label>
              <Input
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="e.g. ARR-HRG"
                autoFocus
              />
            </div>
            <div className="space-y-1.5">
              <Label>From Zone <span className="text-muted-foreground text-xs">(optional)</span></Label>
              <SearchableCombobox
                items={zoneItems}
                value={fromZoneId}
                onChange={setFromZoneId}
                placeholder="Select zone…"
                searchPlaceholder="Search zones…"
              />
            </div>
            <div className="space-y-1.5">
              <Label>To Zone <span className="text-muted-foreground text-xs">(optional)</span></Label>
              <SearchableCombobox
                items={zoneItems}
                value={toZoneId}
                onChange={setToZoneId}
                placeholder="Select zone…"
                searchPlaceholder="Search zones…"
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setFormOpen(false)}>Cancel</Button>
            <Button onClick={handleSave} disabled={saving}>
              {saving ? "Saving…" : "Save"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Delete confirmation */}
      <AlertDialog open={!!deleteId} onOpenChange={(o) => !o && setDeleteId(null)}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete Service Type</AlertDialogTitle>
            <AlertDialogDescription>
              This will permanently delete the service type. Tariffs linked to it will lose the reference.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction
              onClick={handleDelete}
              disabled={deleting}
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
            >
              {deleting ? "Deleting…" : "Delete"}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

      {/* Import result */}
      <AlertDialog open={importResult.open} onOpenChange={(o) => !o && setImportResult((r) => ({ ...r, open: false }))}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Import Complete</AlertDialogTitle>
            <AlertDialogDescription asChild>
              <div className="space-y-3 text-sm">
                <p><span className="font-medium text-green-600">{importResult.imported}</span> service type{importResult.imported !== 1 ? "s" : ""} imported.</p>
                {importResult.errors.length > 0 && (
                  <div>
                    <p className="font-medium text-destructive mb-1">{importResult.errors.length} error{importResult.errors.length !== 1 ? "s" : ""}:</p>
                    <ul className="max-h-40 overflow-y-auto text-xs text-muted-foreground list-disc pl-4 space-y-0.5">
                      {importResult.errors.map((e, i) => <li key={i}>{e}</li>)}
                    </ul>
                  </div>
                )}
              </div>
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogAction onClick={() => setImportResult((r) => ({ ...r, open: false }))}>OK</AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </>
  );
}

// ── Page ─────────────────────────────────────────────────────────────────────

export default function DriverTariffsPage() {
  const canUpsert = usePermission("driver-tariffs.upsert");
  const canDelete = usePermission("driver-tariffs.delete");

  const [tariffs, setTariffs] = useState<Tariff[]>([]);
  const [zones, setZones] = useState<Zone[]>([]);
  const [airports, setAirports] = useState<Airport[]>([]);
  const [vehicleTypes, setVehicleTypes] = useState<VehicleType[]>([]);
  const [jobServiceTypes, setJobServiceTypes] = useState<JobServiceType[]>([]);
  const [loading, setLoading] = useState(true);

  const [dialogOpen, setDialogOpen] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [form, setForm] = useState({ ...EMPTY_FORM });
  const [saving, setSaving] = useState(false);

  const [deleteId, setDeleteId] = useState<string | null>(null);
  const [deleting, setDeleting] = useState(false);

  // Service types manager
  const [stManagerOpen, setStManagerOpen] = useState(false);

  // Import state
  const importFileRef = useRef<HTMLInputElement>(null);
  const [importing, setImporting] = useState(false);
  const [downloadingTemplate, setDownloadingTemplate] = useState(false);
  const [importResult, setImportResult] = useState<{
    open: boolean; imported: number; errors: string[];
  }>({ open: false, imported: 0, errors: [] });

  const fetchData = useCallback(async () => {
    setLoading(true);
    try {
      const [tariffsRes, zonesRes, airportsRes, vtRes, jstRes] = await Promise.all([
        api.get("/driver-tariffs"),
        api.get("/locations/zones"),
        api.get("/locations/airports"),
        api.get("/vehicles/types"),
        api.get("/job-service-types"),
      ]);
      setTariffs(
        (tariffsRes.data.data || tariffsRes.data || []).map((t: any) => ({
          ...t,
          amount: Number(t.amount),
        }))
      );
      setZones(zonesRes.data.data || zonesRes.data || []);
      setAirports(airportsRes.data.data || airportsRes.data || []);
      setVehicleTypes(vtRes.data.data || vtRes.data || []);
      setJobServiceTypes(jstRes.data.data || jstRes.data || []);
    } catch {
      toast.error("Failed to load data");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { fetchData(); }, [fetchData]);

  const locationItems = useMemo((): LocationItem[] => [
    ...airports.map((a) => ({
      value: `airport:${a.id}`,
      label: `${a.code} – ${a.name}`,
      sub: "Airport",
      type: "airport" as const,
    })),
    ...zones.map((z) => ({
      value: `zone:${z.id}`,
      label: z.name,
      sub: z.city?.name,
      type: "zone" as const,
    })),
  ], [airports, zones]);

  const vehicleTypeItems = useMemo(() =>
    vehicleTypes.map((vt) => ({
      value: vt.id,
      label: vt.name,
      sub: vt.seatCapacity ? `${vt.seatCapacity} seats` : undefined,
    })),
    [vehicleTypes]
  );

  const serviceTypeItems = useMemo(() =>
    jobServiceTypes.map((s) => ({ value: s.id, label: s.name })),
    [jobServiceTypes]
  );

  // When a service type is selected, auto-fill zones if it has mappings
  const handleServiceTypeChange = (id: string) => {
    const st = jobServiceTypes.find((s) => s.id === id);
    setForm((f) => ({
      ...f,
      jobServiceTypeId: id,
      ...(st?.fromZone ? { fromLocationValue: `zone:${st.fromZone.id}` } : {}),
      ...(st?.toZone   ? { toLocationValue:   `zone:${st.toZone.id}`   } : {}),
    }));
  };

  const handleCreateServiceType = async (name: string) => {
    try {
      const res = await api.post("/job-service-types", { name });
      const newSt: JobServiceType = res.data.data || res.data;
      setJobServiceTypes((prev) => [...prev, newSt]);
      toast.success(`Service type "${name}" created`);
      return newSt;
    } catch (err: any) {
      toast.error(err?.response?.data?.message || "Failed to create service type");
      return null;
    }
  };

  const openAdd = () => {
    setEditingId(null);
    setForm({ ...EMPTY_FORM });
    setDialogOpen(true);
  };

  const tariffToFormValues = (t: Tariff) => ({
    jobServiceTypeId: t.jobServiceType?.id ?? "",
    fromLocationValue: t.fromAirport ? `airport:${t.fromAirport.id}` : t.fromZone ? `zone:${t.fromZone.id}` : "",
    toLocationValue:   t.toAirport   ? `airport:${t.toAirport.id}`   : t.toZone   ? `zone:${t.toZone.id}`   : "",
    vehicleTypeId: t.vehicleType.id,
    amount: String(t.amount),
    currency: t.currency,
    notes: t.notes ?? "",
  });

  const openEdit = (t: Tariff) => {
    setEditingId(t.id);
    setForm(tariffToFormValues(t));
    setDialogOpen(true);
  };

  const openCopy = (t: Tariff) => {
    setEditingId(null);
    setForm(tariffToFormValues(t));
    setDialogOpen(true);
  };

  const handleSave = async () => {
    if (!form.fromLocationValue || !form.toLocationValue || !form.vehicleTypeId || !form.amount) {
      toast.error("From location, to location, vehicle type, and amount are required");
      return;
    }
    const amt = parseFloat(form.amount);
    if (isNaN(amt) || amt < 0) {
      toast.error("Amount must be a valid non-negative number");
      return;
    }
    setSaving(true);
    try {
      await api.post("/driver-tariffs", {
        ...parseFromLocation(form.fromLocationValue),
        ...parseToLocation(form.toLocationValue),
        vehicleTypeId: form.vehicleTypeId,
        amount: amt,
        currency: form.currency,
        notes: form.notes || undefined,
        jobServiceTypeId: form.jobServiceTypeId || undefined,
      });
      toast.success(editingId ? "Tariff updated" : "Tariff added");
      setDialogOpen(false);
      fetchData();
    } catch (err: any) {
      toast.error(err?.response?.data?.message || "Failed to save tariff");
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async () => {
    if (!deleteId) return;
    setDeleting(true);
    try {
      await api.delete(`/driver-tariffs/${deleteId}`);
      toast.success("Tariff deleted");
      setDeleteId(null);
      fetchData();
    } catch {
      toast.error("Failed to delete tariff");
    } finally {
      setDeleting(false);
    }
  };

  const handleDownloadTemplate = async () => {
    setDownloadingTemplate(true);
    try {
      const res = await api.get("/driver-tariffs/import/template", { responseType: "blob" });
      const url = window.URL.createObjectURL(new Blob([res.data]));
      const link = document.createElement("a");
      link.href = url;
      link.setAttribute("download", "driver_tariffs_template.xlsx");
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
    } catch {
      toast.error("Failed to download template");
    } finally {
      setDownloadingTemplate(false);
    }
  };

  const handleImportFile = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setImporting(true);
    try {
      const formData = new FormData();
      formData.append("file", file);
      const res = await api.post("/driver-tariffs/import/excel", formData, {
        headers: { "Content-Type": "multipart/form-data" },
      });
      const result = res.data.data;
      setImportResult({ open: true, imported: result.imported, errors: result.errors });
      if (result.imported > 0) fetchData();
    } catch (err: unknown) {
      const message =
        (err as { response?: { data?: { message?: string } } })?.response?.data?.message ||
        "Failed to import file";
      toast.error(message);
    } finally {
      setImporting(false);
      if (importFileRef.current) importFileRef.current.value = "";
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-start justify-between">
        <PageHeader
          title="Driver Tariffs"
          description="Rate card for driver trip fees by route and vehicle type. Used to auto-calculate driver fees when a job is completed."
        />
        <div className="flex items-center gap-2 mt-1 shrink-0">
          <Button
            variant="outline"
            size="sm"
            onClick={() => setStManagerOpen(true)}
          >
            <Settings2 className="h-4 w-4 mr-1.5" />
            Service Types
          </Button>
          <Button
            variant="outline"
            size="sm"
            onClick={handleDownloadTemplate}
            disabled={downloadingTemplate}
          >
            <Download className="h-4 w-4 mr-1.5" />
            {downloadingTemplate ? "Downloading…" : "Template"}
          </Button>
          {canUpsert && (
            <>
              <Button
                variant="outline"
                size="sm"
                onClick={() => importFileRef.current?.click()}
                disabled={importing}
              >
                <Upload className="h-4 w-4 mr-1.5" />
                {importing ? "Importing…" : "Import"}
              </Button>
              <input
                ref={importFileRef}
                type="file"
                accept=".xlsx,.xls"
                className="hidden"
                onChange={handleImportFile}
              />
              <Button size="sm" onClick={openAdd}>
                <Plus className="h-4 w-4 mr-1.5" /> Add Tariff
              </Button>
            </>
          )}
        </div>
      </div>

      {loading ? (
        <div className="flex items-center justify-center h-40 text-muted-foreground text-sm">Loading tariffs…</div>
      ) : tariffs.length === 0 ? (
        <div className="flex flex-col items-center justify-center h-40 gap-2 text-muted-foreground text-sm border rounded-lg">
          <Receipt className="h-8 w-8 opacity-30" />
          <p>No tariffs configured yet.</p>
          {canUpsert && (
            <Button variant="outline" size="sm" onClick={openAdd}>
              <Plus className="h-4 w-4 mr-1" /> Add your first tariff
            </Button>
          )}
        </div>
      ) : (
        <div className="rounded-lg border">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Service Type</TableHead>
                <TableHead>From</TableHead>
                <TableHead>To</TableHead>
                <TableHead>Vehicle Type</TableHead>
                <TableHead className="text-right">Amount</TableHead>
                <TableHead>Currency</TableHead>
                <TableHead>Notes</TableHead>
                {(canUpsert || canDelete) && (
                  <TableHead className="text-right">Actions</TableHead>
                )}
              </TableRow>
            </TableHeader>
            <TableBody>
              {tariffs.map((t) => (
                <TableRow key={t.id} className={!t.isActive ? "opacity-50" : undefined}>
                  <TableCell className="font-medium text-primary">
                    {t.jobServiceType?.name ?? <span className="text-muted-foreground">—</span>}
                  </TableCell>
                  <TableCell className="text-sm">
                    {t.fromAirport
                      ? <span className="font-mono text-primary">{t.fromAirport.code}</span>
                      : t.fromZone?.name ?? "—"}
                    {t.fromZone?.city && <span className="text-muted-foreground text-xs ml-1">({t.fromZone.city.name})</span>}
                  </TableCell>
                  <TableCell className="text-sm">
                    {t.toAirport
                      ? <span className="font-mono text-primary">{t.toAirport.code}</span>
                      : t.toZone?.name ?? "—"}
                    {t.toZone?.city && <span className="text-muted-foreground text-xs ml-1">({t.toZone.city.name})</span>}
                  </TableCell>
                  <TableCell>
                    {t.vehicleType.name}
                    {t.vehicleType.seatCapacity && <span className="text-muted-foreground text-xs ml-1">({t.vehicleType.seatCapacity} seats)</span>}
                  </TableCell>
                  <TableCell className="text-right font-mono">
                    {t.amount.toLocaleString("en-EG", { minimumFractionDigits: 2 })}
                  </TableCell>
                  <TableCell>{t.currency}</TableCell>
                  <TableCell className="text-muted-foreground text-sm">{t.notes || "—"}</TableCell>
                  {(canUpsert || canDelete) && (
                    <TableCell className="text-right">
                      <div className="flex justify-end gap-1">
                        {canUpsert && (
                          <>
                            <Button variant="ghost" size="icon" title="Copy" onClick={() => openCopy(t)}>
                              <Copy className="h-4 w-4" />
                            </Button>
                            <Button variant="ghost" size="icon" title="Edit" onClick={() => openEdit(t)}>
                              <Pencil className="h-4 w-4" />
                            </Button>
                          </>
                        )}
                        {canDelete && (
                          <Button variant="ghost" size="icon" title="Delete" onClick={() => setDeleteId(t.id)}>
                            <Trash2 className="h-4 w-4 text-destructive" />
                          </Button>
                        )}
                      </div>
                    </TableCell>
                  )}
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      )}

      {/* Add / Edit / Copy Dialog */}
      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogContent className="w-[80vw] max-w-[80vw]">
          <DialogHeader>
            <DialogTitle>
              {editingId ? "Edit Driver Tariff" : "Add Driver Tariff"}
            </DialogTitle>
          </DialogHeader>

          <div className="space-y-5 py-2">
            {/* 1. Service Type — tab order 1, creatable */}
            <div className="space-y-1.5">
              <Label>Service Type</Label>
              <CreatableCombobox
                items={serviceTypeItems}
                value={form.jobServiceTypeId}
                onChange={handleServiceTypeChange}
                onCreate={handleCreateServiceType}
                placeholder="Select or create service type…"
                searchPlaceholder="Search or type to create…"
              />
            </div>

            {/* 2. Locations (zones + airports) */}
            <div className="grid grid-cols-2 gap-6">
              <div className="space-y-1.5">
                <Label>From <span className="text-destructive">*</span></Label>
                <SearchableCombobox
                  items={locationItems}
                  value={form.fromLocationValue}
                  onChange={(v) => setForm((f) => ({ ...f, fromLocationValue: v }))}
                  placeholder="Zone or airport…"
                  searchPlaceholder="Search zones / airports…"
                />
              </div>
              <div className="space-y-1.5">
                <Label>To <span className="text-destructive">*</span></Label>
                <SearchableCombobox
                  items={locationItems}
                  value={form.toLocationValue}
                  onChange={(v) => setForm((f) => ({ ...f, toLocationValue: v }))}
                  placeholder="Zone or airport…"
                  searchPlaceholder="Search zones / airports…"
                />
              </div>
            </div>

            {/* 3. Vehicle Type */}
            <div className="space-y-1.5">
              <Label>Vehicle Type <span className="text-destructive">*</span></Label>
              <SearchableCombobox
                items={vehicleTypeItems}
                value={form.vehicleTypeId}
                onChange={(v) => setForm((f) => ({ ...f, vehicleTypeId: v }))}
                placeholder="Select vehicle type…"
                searchPlaceholder="Search vehicle types…"
              />
            </div>

            {/* 4. Amount + Currency */}
            <div className="grid grid-cols-3 gap-6">
              <div className="col-span-2 space-y-1.5">
                <Label>Amount <span className="text-destructive">*</span></Label>
                <Input
                  type="number"
                  min="0"
                  step="0.01"
                  value={form.amount}
                  onChange={(e) => setForm((f) => ({ ...f, amount: e.target.value }))}
                  placeholder="0.00"
                />
              </div>
              <div className="space-y-1.5">
                <Label>Currency</Label>
                <Select value={form.currency} onValueChange={(v) => setForm((f) => ({ ...f, currency: v }))}>
                  <SelectTrigger><SelectValue /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="EGP">EGP</SelectItem>
                    <SelectItem value="USD">USD</SelectItem>
                    <SelectItem value="EUR">EUR</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>

            {/* 5. Notes */}
            <div className="space-y-1.5">
              <Label>Notes</Label>
              <Input
                value={form.notes}
                onChange={(e) => setForm((f) => ({ ...f, notes: e.target.value }))}
                placeholder="Optional notes"
              />
            </div>
          </div>

          <DialogFooter>
            <Button variant="outline" onClick={() => setDialogOpen(false)}>Cancel</Button>
            <Button onClick={handleSave} disabled={saving}>
              {saving ? "Saving…" : "Save"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Service Types Manager */}
      <ServiceTypesManager
        open={stManagerOpen}
        onClose={() => setStManagerOpen(false)}
        zones={zones}
        onChanged={fetchData}
      />

      {/* Import Result */}
      <AlertDialog open={importResult.open} onOpenChange={(o) => !o && setImportResult((r) => ({ ...r, open: false }))}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Import Complete</AlertDialogTitle>
            <AlertDialogDescription asChild>
              <div className="space-y-3 text-sm">
                <p>
                  <span className="font-medium text-green-600">{importResult.imported}</span> tariff{importResult.imported !== 1 ? "s" : ""} imported successfully.
                </p>
                {importResult.errors.length > 0 && (
                  <div>
                    <p className="font-medium text-destructive mb-1">{importResult.errors.length} error{importResult.errors.length !== 1 ? "s" : ""}:</p>
                    <ul className="max-h-48 overflow-y-auto space-y-0.5 text-xs text-muted-foreground list-disc pl-4">
                      {importResult.errors.map((e, i) => <li key={i}>{e}</li>)}
                    </ul>
                  </div>
                )}
              </div>
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogAction onClick={() => setImportResult((r) => ({ ...r, open: false }))}>
              OK
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

      {/* Delete Confirmation */}
      <AlertDialog open={!!deleteId} onOpenChange={(o: boolean) => !o && setDeleteId(null)}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete Tariff</AlertDialogTitle>
            <AlertDialogDescription>
              This tariff will be removed. Existing driver trip fees already recorded will not be affected.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction
              onClick={handleDelete}
              disabled={deleting}
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
            >
              {deleting ? "Deleting…" : "Delete"}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}
