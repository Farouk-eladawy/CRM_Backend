"use client";

import { useEffect, useState, useCallback, useRef, useMemo } from "react";
import { useRouter } from "next/navigation";
import { Car, Plus, Loader2, Trash2, FileDown, FileUp, FileSpreadsheet, AlertTriangle, ImagePlus, X } from "lucide-react";
import { Skeleton } from "@/components/ui/skeleton";
import { toast } from "sonner";
import { PageHeader } from "@/components/page-header";
import { EmptyState } from "@/components/ui/empty-state";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Switch } from "@/components/ui/switch";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Label } from "@/components/ui/label";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "@/components/ui/dialog";
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
import { useSortable } from "@/hooks/use-sortable";
import { SortableHeader } from "@/components/sortable-header";
import { TableFilterBar } from "@/components/table-filter-bar";
import { localDateStr } from "@/lib/utils";
import { useColumnPreferences } from "@/hooks/useColumnPreferences";
import { ColumnVisibilityControl } from "@/components/ui/column-visibility-control";
import { type ColumnDef } from "@/components/ui/draggable-table-header";

const VEHICLES_COL_DEFS: ColumnDef[] = [
  { key: "plateNumber", label: "Plate Number" },
  { key: "type", label: "Type" },
  { key: "color", label: "Color" },
  { key: "carBrand", label: "Brand" },
  { key: "carModel", label: "Model" },
  { key: "makeYear", label: "Year" },
  { key: "luggageCapacity", label: "Luggage" },
  { key: "ownership", label: "Ownership" },
  { key: "status", label: "Status" },
  { key: "actions", label: "Actions" },
];

// ─── Types ───────────────────────────────────────────────────────
interface VehicleType {
  id: string;
  name: string;
  seatCapacity: number;
  imageUrl?: string | null;
  description?: string | null;
  wifi?: boolean;
  airConditioning?: boolean;
  transmission?: "MANUAL" | "AUTOMATIC" | null;
  luggageCapacity?: number | null;
  gpsTracked?: boolean;
}

// Resolve an uploaded "/uploads/..." path to an absolute URL for display.
const resolveUploadUrl = (url: string) =>
  url.startsWith("http") ? url : `${process.env.NEXT_PUBLIC_API_URL ?? ""}${url}`;

interface Vehicle {
  id: string;
  plateNumber: string;
  vehicleTypeId: string;
  vehicleType?: VehicleType;
  ownership: "OWNED" | "RENTED" | "CONTRACTED";
  color: string | null;
  carBrand: string | null;
  carModel: string | null;
  makeYear: number | null;
  luggageCapacity: number | null;
  isActive: boolean;
}

interface VehiclesResponse {
  data: Vehicle[];
  total: number;
  page: number;
  limit: number;
}

// ─── Main Page ───────────────────────────────────────────────────
export default function VehiclesPage() {
  const t = useT();
  const router = useRouter();
  const canAddType = usePermission("vehicles.types.addButton");
  const canEditType = usePermission("vehicles.types.editButton");
  const canAddVehicle = usePermission("vehicles.addButton");
  const canEditVehicle = usePermission("vehicles.table.editButton");
  const canDeleteVehicle = usePermission("vehicles.table.deleteButton");
  const canToggleStatus = usePermission("vehicles.table.toggleStatus");
  const canImport = usePermission("vehicles.import");
  const canExport = usePermission("vehicles.export");
  const canDownloadTemplate = usePermission("vehicles.downloadTemplate");
  const [activeTab, setActiveTab] = useState("types");

  // Vehicle Types state
  const [types, setTypes] = useState<VehicleType[]>([]);
  const [typesLoading, setTypesLoading] = useState(true);
  const [typeDialogOpen, setTypeDialogOpen] = useState(false);
  const [editTypeDialogOpen, setEditTypeDialogOpen] = useState(false);
  const [editingType, setEditingType] = useState<VehicleType | null>(null);
  const [typeSubmitting, setTypeSubmitting] = useState(false);
  const [typeName, setTypeName] = useState("");
  const [typeSeatCapacity, setTypeSeatCapacity] = useState("");
  const [typeImageUrl, setTypeImageUrl] = useState("");
  const [typeDescription, setTypeDescription] = useState("");
  const [typeImageUploading, setTypeImageUploading] = useState(false);
  const typeImageInputRef = useRef<HTMLInputElement>(null);
  // Amenities
  const [typeWifi, setTypeWifi] = useState(false);
  const [typeAirConditioning, setTypeAirConditioning] = useState(false);
  const [typeGpsTracked, setTypeGpsTracked] = useState(false);
  const [typeLuggageCapacity, setTypeLuggageCapacity] = useState("");
  const [typeTransmission, setTypeTransmission] = useState<"" | "MANUAL" | "AUTOMATIC">("");

  // Vehicles state
  const [vehicles, setVehicles] = useState<Vehicle[]>([]);
  const [vehiclesLoading, setVehiclesLoading] = useState(true);

  // Delete state
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [deletingVehicle, setDeletingVehicle] = useState<Vehicle | null>(null);
  const [deleting, setDeleting] = useState(false);

  // Import/Export state
  const importFileRef = useRef<HTMLInputElement>(null);
  const [importing, setImporting] = useState(false);
  const [exporting, setExporting] = useState(false);
  const [importResult, setImportResult] = useState<{
    open: boolean;
    imported: number;
    errors: string[];
  }>({ open: false, imported: 0, errors: [] });

  // Search & sorting for types
  const [typeSearch, setTypeSearch] = useState("");
  const filteredTypes = useMemo(() => {
    if (!typeSearch.trim()) return types;
    const q = typeSearch.toLowerCase();
    return types.filter((t) => t.name.toLowerCase().includes(q));
  }, [types, typeSearch]);
  const { sortedData: sortedTypes, sortKey: typeSortKey, sortDir: typeSortDir, onSort: onTypeSort } = useSortable<VehicleType>(filteredTypes);

  // Search & sorting for vehicles
  const [vehicleSearch, setVehicleSearch] = useState("");
  const filteredVehicles = useMemo(() => {
    if (!vehicleSearch.trim()) return vehicles;
    const q = vehicleSearch.toLowerCase();
    return vehicles.filter(
      (v) =>
        v.plateNumber.toLowerCase().includes(q) ||
        (v.vehicleType?.name && v.vehicleType.name.toLowerCase().includes(q))
    );
  }, [vehicles, vehicleSearch]);
  const { sortedData: sortedVehicles, sortKey: vehicleSortKey, sortDir: vehicleSortDir, onSort: onVehicleSort } = useSortable<Vehicle>(filteredVehicles);
  const { visibility: vehicleColVis, saveVisibility: saveVehicleColVis } = useColumnPreferences("vehicles_list", VEHICLES_COL_DEFS.map((c) => c.key));
  const isVehicleVis = (key: string) => vehicleColVis[key] !== false;

  // ─── Fetch Vehicle Types ────────────────────────────────────────
  const fetchTypes = useCallback(async () => {
    setTypesLoading(true);
    try {
      const { data } = await api.get("/vehicles/types");
      setTypes(Array.isArray(data) ? data : []);
    } catch {
      toast.error(t("vehicles.failedLoadTypes"));
    } finally {
      setTypesLoading(false);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // ─── Fetch Vehicles ────────────────────────────────────────────
  const fetchVehicles = useCallback(async () => {
    setVehiclesLoading(true);
    try {
      const { data } = await api.get<VehiclesResponse>("/vehicles");
      setVehicles(Array.isArray(data.data) ? data.data : []);
    } catch {
      toast.error(t("vehicles.failedLoadVehicles"));
    } finally {
      setVehiclesLoading(false);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    fetchTypes();
    fetchVehicles();
  }, [fetchTypes, fetchVehicles]);

  // ─── Create Vehicle Type ────────────────────────────────────────
  const handleCreateType = async () => {
    if (!typeName.trim()) {
      toast.error(t("vehicles.nameRequired"));
      return;
    }
    const capacity = parseInt(typeSeatCapacity, 10);
    if (!capacity || capacity <= 0) {
      toast.error(t("vehicles.seatCapacityPositive"));
      return;
    }

    setTypeSubmitting(true);
    try {
      await api.post("/vehicles/types", {
        name: typeName.trim(),
        seatCapacity: capacity,
        imageUrl: typeImageUrl || null,
        description: typeDescription.trim() || null,
        ...typeAmenityPayload(),
      });
      toast.success(t("vehicles.typeCreated"));
      setTypeDialogOpen(false);
      resetTypeForm();
      fetchTypes();
    } catch {
      toast.error(t("vehicles.failedCreateType"));
    } finally {
      setTypeSubmitting(false);
    }
  };

  // ─── Edit Vehicle Type ─────────────────────────────────────────
  function openEditTypeDialog(type: VehicleType) {
    setEditingType(type);
    setTypeName(type.name);
    setTypeSeatCapacity(String(type.seatCapacity));
    setTypeImageUrl(type.imageUrl || "");
    setTypeDescription(type.description || "");
    setTypeWifi(!!type.wifi);
    setTypeAirConditioning(!!type.airConditioning);
    setTypeGpsTracked(!!type.gpsTracked);
    setTypeLuggageCapacity(
      type.luggageCapacity != null ? String(type.luggageCapacity) : "",
    );
    setTypeTransmission(type.transmission ?? "");
    setEditTypeDialogOpen(true);
  }

  // Build the amenity portion of the create/update payload.
  const typeAmenityPayload = () => ({
    wifi: typeWifi,
    airConditioning: typeAirConditioning,
    gpsTracked: typeGpsTracked,
    luggageCapacity: typeLuggageCapacity.trim()
      ? parseInt(typeLuggageCapacity, 10)
      : null,
    transmission: typeTransmission || null,
  });

  // ─── Upload Vehicle Type Image ─────────────────────────────────
  const handleTypeImageUpload = async (
    e: React.ChangeEvent<HTMLInputElement>,
  ) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setTypeImageUploading(true);
    try {
      const formData = new FormData();
      formData.append("file", file);
      const { data } = await api.post("/vehicles/types/image", formData, {
        headers: { "Content-Type": "multipart/form-data" },
      });
      const url = data?.data?.url ?? data?.url;
      if (url) setTypeImageUrl(url);
      toast.success(t("vehicles.imageUploaded"));
    } catch {
      toast.error(t("vehicles.failedUploadImage"));
    } finally {
      setTypeImageUploading(false);
      if (typeImageInputRef.current) typeImageInputRef.current.value = "";
    }
  };

  const handleUpdateType = async () => {
    if (!editingType) return;
    if (!typeName.trim()) {
      toast.error(t("vehicles.nameRequired"));
      return;
    }
    const capacity = parseInt(typeSeatCapacity, 10);
    if (!capacity || capacity <= 0) {
      toast.error(t("vehicles.seatCapacityPositive"));
      return;
    }

    setTypeSubmitting(true);
    try {
      await api.patch(`/vehicles/types/${editingType.id}`, {
        name: typeName.trim(),
        seatCapacity: capacity,
        imageUrl: typeImageUrl || null,
        description: typeDescription.trim() || null,
        ...typeAmenityPayload(),
      });
      toast.success(t("vehicles.typeUpdated"));
      setEditTypeDialogOpen(false);
      setEditingType(null);
      resetTypeForm();
      fetchTypes();
    } catch {
      toast.error(t("vehicles.failedUpdateType"));
    } finally {
      setTypeSubmitting(false);
    }
  };

  // ─── Form Resets ────────────────────────────────────────────────
  const resetTypeForm = () => {
    setTypeName("");
    setTypeSeatCapacity("");
    setTypeImageUrl("");
    setTypeDescription("");
    setTypeWifi(false);
    setTypeAirConditioning(false);
    setTypeGpsTracked(false);
    setTypeLuggageCapacity("");
    setTypeTransmission("");
  };

  // ─── Shared image + description fields for type dialogs ─────────
  // Defined as a function (not a component) so the dialog state isn't
  // remounted on each keystroke, which would drop textarea focus.
  const vehicleTypeMediaFields = () => (
    <>
      <div className="space-y-2">
        <Label className="text-muted-foreground">
          {t("vehicles.typeImage")}
        </Label>
        <p className="text-xs text-muted-foreground">
          {t("vehicles.typeImageHint")}
        </p>
        <div className="flex items-center gap-3">
          <div className="relative h-20 w-28 shrink-0 overflow-hidden rounded-md border border-border bg-card">
            {typeImageUrl ? (
              <>
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img
                  src={resolveUploadUrl(typeImageUrl)}
                  alt=""
                  className="h-full w-full object-cover"
                />
                <button
                  type="button"
                  onClick={() => setTypeImageUrl("")}
                  className="absolute right-1 top-1 rounded-full bg-black/60 p-0.5 text-white hover:bg-black/80"
                  aria-label={t("common.remove")}
                >
                  <X className="h-3.5 w-3.5" />
                </button>
              </>
            ) : (
              <div className="flex h-full w-full items-center justify-center text-muted-foreground">
                <ImagePlus className="h-6 w-6" />
              </div>
            )}
          </div>
          <div>
            <input
              ref={typeImageInputRef}
              type="file"
              accept="image/*"
              className="hidden"
              onChange={handleTypeImageUpload}
            />
            <Button
              type="button"
              variant="outline"
              size="sm"
              disabled={typeImageUploading}
              onClick={() => typeImageInputRef.current?.click()}
              className="gap-1.5"
            >
              {typeImageUploading ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <ImagePlus className="h-4 w-4" />
              )}
              {typeImageUrl ? t("vehicles.changeImage") : t("vehicles.uploadImage")}
            </Button>
          </div>
        </div>
      </div>
      <div className="space-y-2">
        <Label htmlFor="type-description" className="text-muted-foreground">
          {t("vehicles.typeDescription")}
        </Label>
        <Textarea
          id="type-description"
          rows={3}
          maxLength={300}
          placeholder={t("vehicles.typeDescriptionPlaceholder")}
          value={typeDescription}
          onChange={(e) => setTypeDescription(e.target.value)}
          className="border-border bg-card text-foreground placeholder:text-muted-foreground"
        />
      </div>

      {/* ── Amenities (shown on B2C vehicle cards) ── */}
      <div className="space-y-3 rounded-md border border-border p-3">
        <p className="text-xs font-medium text-muted-foreground">
          {t("vehicles.amenities")}
        </p>
        <div className="grid grid-cols-2 gap-3">
          <div className="space-y-1.5">
            <Label className="text-muted-foreground">
              {t("vehicles.transmission")}
            </Label>
            <Select
              value={typeTransmission || "NONE"}
              onValueChange={(v) =>
                setTypeTransmission(v === "NONE" ? "" : (v as "MANUAL" | "AUTOMATIC"))
              }
            >
              <SelectTrigger className="border-border bg-card text-foreground">
                <SelectValue placeholder={t("vehicles.notSpecified")} />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="NONE">{t("vehicles.notSpecified")}</SelectItem>
                <SelectItem value="AUTOMATIC">{t("vehicles.automatic")}</SelectItem>
                <SelectItem value="MANUAL">{t("vehicles.manual")}</SelectItem>
              </SelectContent>
            </Select>
          </div>
          <div className="space-y-1.5">
            <Label className="text-muted-foreground">
              {t("vehicles.luggageCapacity")}
            </Label>
            <Input
              type="number"
              min={0}
              placeholder="e.g. 3"
              value={typeLuggageCapacity}
              onChange={(e) => setTypeLuggageCapacity(e.target.value)}
              className="border-border bg-card text-foreground placeholder:text-muted-foreground"
            />
          </div>
        </div>
        <div className="space-y-2 pt-1">
          <div className="flex items-center justify-between">
            <Label className="text-muted-foreground">{t("vehicles.wifi")}</Label>
            <Switch checked={typeWifi} onCheckedChange={setTypeWifi} />
          </div>
          <div className="flex items-center justify-between">
            <Label className="text-muted-foreground">{t("vehicles.airConditioning")}</Label>
            <Switch checked={typeAirConditioning} onCheckedChange={setTypeAirConditioning} />
          </div>
          <div className="flex items-center justify-between">
            <Label className="text-muted-foreground">{t("vehicles.gpsTracked")}</Label>
            <Switch checked={typeGpsTracked} onCheckedChange={setTypeGpsTracked} />
          </div>
        </div>
      </div>
    </>
  );

  // ─── Resolve type name for vehicles table ──────────────────────
  const getTypeName = (vehicle: Vehicle) => {
    if (vehicle.vehicleType?.name) return vehicle.vehicleType.name;
    const found = types.find((tp) => tp.id === vehicle.vehicleTypeId);
    return found?.name ?? "Unknown";
  };

  // ─── Toggle Vehicle Status ───────────────────────────────────
  async function handleToggleStatus(id: string) {
    try {
      await api.patch(`/vehicles/${id}/status`);
      setVehicles((prev) =>
        prev.map((v) => (v.id === id ? { ...v, isActive: !v.isActive } : v))
      );
      toast.success(t("common.statusUpdated"));
    } catch {
      toast.error(t("common.failedStatusUpdate"));
    }
  }

  // ─── Delete Vehicle ──────────────────────────────────────────
  function openDeleteDialog(vehicle: Vehicle) {
    setDeletingVehicle(vehicle);
    setDeleteDialogOpen(true);
  }

  async function handleDelete() {
    if (!deletingVehicle) return;
    try {
      setDeleting(true);
      await api.delete(`/vehicles/${deletingVehicle.id}`);
      toast.success(t("vehicles.deleted"));
      setDeleteDialogOpen(false);
      setDeletingVehicle(null);
      fetchVehicles();
    } catch {
      toast.error(t("vehicles.failedDelete"));
    } finally {
      setDeleting(false);
    }
  }

  // ─── Export / Import ──────────────────────────────────────────
  async function handleExport() {
    setExporting(true);
    try {
      const res = await api.get("/vehicles/export/excel", {
        responseType: "blob",
      });
      const url = window.URL.createObjectURL(new Blob([res.data]));
      const link = document.createElement("a");
      link.href = url;
      const date = localDateStr(new Date());
      link.setAttribute("download", `vehicles_${date}.xlsx`);
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
      toast.success(t("vehicles.exportSuccess"));
    } catch {
      toast.error(t("vehicles.failedExport"));
    } finally {
      setExporting(false);
    }
  }

  async function handleDownloadTemplate() {
    try {
      const res = await api.get("/vehicles/import/template", {
        responseType: "blob",
      });
      const url = window.URL.createObjectURL(new Blob([res.data]));
      const link = document.createElement("a");
      link.href = url;
      link.setAttribute("download", "vehicles_import_template.xlsx");
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
    } catch {
      toast.error(t("vehicles.failedTemplate"));
    }
  }

  async function handleImportFile(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;

    setImporting(true);
    try {
      const formData = new FormData();
      formData.append("file", file);
      const res = await api.post("/vehicles/import/excel", formData, {
        headers: { "Content-Type": "multipart/form-data" },
      });
      const result = res.data.data;
      setImportResult({
        open: true,
        imported: result.imported,
        errors: result.errors,
      });
      if (result.imported > 0) {
        fetchVehicles();
      }
    } catch (err: unknown) {
      const message =
        (err as { response?: { data?: { message?: string } } })?.response?.data
          ?.message || t("vehicles.failedImport");
      toast.error(message);
    } finally {
      setImporting(false);
      if (importFileRef.current) {
        importFileRef.current.value = "";
      }
    }
  }

  // ─── Render ─────────────────────────────────────────────────────
  return (
    <div className="space-y-6">
      <PageHeader
        title={t("vehicles.title")}
        description={t("vehicles.description")}
      />

      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList className="border-border bg-card">
          <TabsTrigger value="types">{t("vehicles.vehicleTypes")}</TabsTrigger>
          <TabsTrigger value="vehicles">{t("vehicles.title")}</TabsTrigger>
        </TabsList>

        {/* ── Vehicle Types Tab ─────────────────────────────────── */}
        <TabsContent value="types" className="mt-4 space-y-4">
          <div className="flex items-center justify-between">
            <p className="text-sm text-muted-foreground">
              {t("vehicles.typesDescription")}
            </p>
            {canAddType && (
            <Button
              size="sm"
              className="gap-1.5 bg-primary text-primary-foreground hover:bg-primary/90"
              onClick={() => setTypeDialogOpen(true)}
            >
              <Plus className="h-4 w-4" />
              {t("vehicles.addType")}
            </Button>
            )}
          </div>

          {typesLoading ? (
            <div className="overflow-x-auto [overflow-y:clip]">
              <table className="w-full text-sm">
                <tbody>
                  {Array.from({ length: 8 }).map((_, i) => (
                    <tr key={i} className={`border-b border-border ${i % 2 === 0 ? "bg-gray-100/25 dark:bg-gray-800/25" : "bg-gray-200/50 dark:bg-gray-700/50"}`}>
                      <td className="px-3 py-3"><Skeleton className="h-4 w-32" /></td>
                      <td className="px-3 py-3"><Skeleton className="h-4 w-16" /></td>
                      <td className="px-3 py-3 text-right"><Skeleton className="h-7 w-14 ml-auto" /></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : types.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-12 text-muted-foreground">
              <Car className="mb-2 h-8 w-8" />
              <p className="text-sm">{t("vehicles.noTypes")}</p>
            </div>
          ) : (
            <>
              <TableFilterBar
                search={typeSearch}
                onSearchChange={setTypeSearch}
                placeholder={t("common.search") + "..."}
              />
              <div className="overflow-x-auto [overflow-y:clip]">
                <Table>
                  <TableHeader>
                    <TableRow className="border-border bg-muted">
                      <SortableHeader label={t("common.name")} sortKey="name" currentKey={typeSortKey} currentDir={typeSortDir} onSort={onTypeSort} />
                      <SortableHeader label={t("vehicles.seatCapacity")} sortKey="seatCapacity" currentKey={typeSortKey} currentDir={typeSortDir} onSort={onTypeSort} />
                      <TableHead className="text-right text-muted-foreground text-xs">
                        {t("common.actions")}
                      </TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {sortedTypes.map((type, idx) => (
                    <TableRow
                      key={type.id}
                      className={`border-border ${idx % 2 === 0 ? "bg-gray-100/25 dark:bg-gray-800/25" : "bg-gray-200/50 dark:bg-gray-700/50"}`}
                    >
                      <TableCell className="font-medium text-foreground">
                        {type.name}
                      </TableCell>
                      <TableCell className="text-muted-foreground">
                        {type.seatCapacity} {t("vehicles.seats")}
                      </TableCell>
                      <TableCell className="text-right">
                        {canEditType && (
                        <Button
                          variant="ghost"
                          size="sm"
                          className="text-muted-foreground hover:text-foreground"
                          onClick={() => openEditTypeDialog(type)}
                        >
                          {t("common.edit")}
                        </Button>
                        )}
                      </TableCell>
                    </TableRow>
                  ))}
                  </TableBody>
                </Table>
              </div>
            </>
          )}
        </TabsContent>

        {/* ── Vehicles Tab ──────────────────────────────────────── */}
        <TabsContent value="vehicles" className="mt-4 space-y-4">
          <div className="flex items-center justify-between">
            <p className="text-sm text-muted-foreground">
              {t("vehicles.vehiclesDescription")}
            </p>
            <div className="flex items-center gap-2">
              {canDownloadTemplate && (
              <Button
                variant="outline"
                size="sm"
                className="gap-1.5"
                onClick={handleDownloadTemplate}
              >
                <FileDown className="h-4 w-4" />
                {t("common.template")}
              </Button>
              )}
              {canImport && (
              <Button
                variant="outline"
                size="sm"
                className="gap-1.5"
                onClick={() => importFileRef.current?.click()}
                disabled={importing}
              >
                {importing ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <FileUp className="h-4 w-4" />
                )}
                {t("common.import")}
              </Button>
              )}
              {canExport && (
              <Button
                variant="outline"
                size="sm"
                className="gap-1.5"
                onClick={handleExport}
                disabled={exporting}
              >
                {exporting ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <FileSpreadsheet className="h-4 w-4" />
                )}
                {t("common.export")}
              </Button>
              )}
              {canAddVehicle && (
              <Button
                size="sm"
                className="gap-1.5 bg-primary text-primary-foreground hover:bg-primary/90"
                onClick={() => router.push("/dashboard/vehicles/new")}
              >
                <Plus className="h-4 w-4" />
                {t("vehicles.addVehicle")}
              </Button>
              )}
            </div>
          </div>

          {/* Hidden file input for import */}
          <input
            ref={importFileRef}
            type="file"
            className="hidden"
            accept=".xlsx,.xls"
            onChange={handleImportFile}
          />

          {vehiclesLoading ? (
            <div className="overflow-x-auto [overflow-y:clip]">
              <table className="w-full text-sm">
                <tbody>
                  {Array.from({ length: 9 }).map((_, i) => (
                    <tr key={i} className={`border-b border-border ${i % 2 === 0 ? "bg-gray-100/25 dark:bg-gray-800/25" : "bg-gray-200/50 dark:bg-gray-700/50"}`}>
                      <td className="px-3 py-3"><Skeleton className="h-4 w-24" /></td>
                      <td className="px-3 py-3"><Skeleton className="h-4 w-20" /></td>
                      <td className="px-3 py-3"><Skeleton className="h-4 w-12" /></td>
                      <td className="px-3 py-3"><Skeleton className="h-4 w-16" /></td>
                      <td className="px-3 py-3"><Skeleton className="h-4 w-16" /></td>
                      <td className="px-3 py-3"><Skeleton className="h-4 w-10" /></td>
                      <td className="px-3 py-3"><Skeleton className="h-4 w-8" /></td>
                      <td className="px-3 py-3"><Skeleton className="h-5 w-20 rounded-full" /></td>
                      <td className="px-3 py-3"><Skeleton className="h-5 w-14 rounded-full" /></td>
                      <td className="px-3 py-3 text-right"><Skeleton className="h-7 w-24 ml-auto" /></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : vehicles.length === 0 ? (
            <div className="py-16">
              <EmptyState
                icon={Car}
                heading="No vehicles yet"
                description="Add vehicles to assign them to jobs."
              />
            </div>
          ) : (
            <>
              <TableFilterBar
                search={vehicleSearch}
                onSearchChange={setVehicleSearch}
                placeholder={t("common.search") + "..."}
              />
              <div className="flex justify-end mb-2">
                <ColumnVisibilityControl columns={VEHICLES_COL_DEFS} visibility={vehicleColVis} onSave={saveVehicleColVis} />
              </div>
              <div className="overflow-x-auto [overflow-y:clip]">
                <Table>
                  <TableHeader>
                    <TableRow className="border-border bg-muted">
                      {isVehicleVis("plateNumber") && <SortableHeader label={t("vehicles.plateNumber")} sortKey="plateNumber" currentKey={vehicleSortKey} currentDir={vehicleSortDir} onSort={onVehicleSort} />}
                      {isVehicleVis("type") && <SortableHeader label={t("vehicles.type")} sortKey="vehicleType.name" currentKey={vehicleSortKey} currentDir={vehicleSortDir} onSort={onVehicleSort} />}
                      {isVehicleVis("color") && <TableHead className="text-muted-foreground text-xs">{t("vehicles.color")}</TableHead>}
                      {isVehicleVis("carBrand") && <TableHead className="text-muted-foreground text-xs">{t("vehicles.carBrand")}</TableHead>}
                      {isVehicleVis("carModel") && <TableHead className="text-muted-foreground text-xs">{t("vehicles.carModel")}</TableHead>}
                      {isVehicleVis("makeYear") && <TableHead className="text-muted-foreground text-xs">{t("vehicles.makeYear")}</TableHead>}
                      {isVehicleVis("luggageCapacity") && <TableHead className="text-muted-foreground text-xs">{t("vehicles.luggageCapacity")}</TableHead>}
                      {isVehicleVis("ownership") && <TableHead className="text-muted-foreground text-xs">{t("vehicles.ownership")}</TableHead>}
                      {isVehicleVis("status") && <TableHead className="text-muted-foreground text-xs">{t("common.status")}</TableHead>}
                      {isVehicleVis("actions") && <TableHead className="text-right text-muted-foreground text-xs">{t("common.actions")}</TableHead>}
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {sortedVehicles.map((vehicle, idx) => (
                    <TableRow
                      key={vehicle.id}
                      className={`border-border ${idx % 2 === 0 ? "bg-gray-100/25 dark:bg-gray-800/25" : "bg-gray-200/50 dark:bg-gray-700/50"}`}
                    >
                      {isVehicleVis("plateNumber") && <TableCell className="font-medium text-foreground">{vehicle.plateNumber}</TableCell>}
                      {isVehicleVis("type") && <TableCell className="text-muted-foreground">{getTypeName(vehicle)}</TableCell>}
                      {isVehicleVis("color") && <TableCell className="text-muted-foreground">{vehicle.color || "—"}</TableCell>}
                      {isVehicleVis("carBrand") && <TableCell className="text-muted-foreground">{vehicle.carBrand || "—"}</TableCell>}
                      {isVehicleVis("carModel") && <TableCell className="text-muted-foreground">{vehicle.carModel || "—"}</TableCell>}
                      {isVehicleVis("makeYear") && <TableCell className="text-muted-foreground">{vehicle.makeYear ?? "—"}</TableCell>}
                      {isVehicleVis("luggageCapacity") && <TableCell className="text-muted-foreground">{vehicle.luggageCapacity != null ? vehicle.luggageCapacity : "—"}</TableCell>}
                      {isVehicleVis("ownership") && <TableCell><Badge variant="secondary" className="bg-secondary text-muted-foreground">{vehicle.ownership}</Badge></TableCell>}
                      {isVehicleVis("status") && (
                        <TableCell>
                          {canToggleStatus ? (
                            <button onClick={() => handleToggleStatus(vehicle.id)} className="cursor-pointer">
                              {vehicle.isActive ? <Badge className="bg-emerald-500/20 text-emerald-600 dark:text-emerald-400 hover:bg-emerald-500/30 transition-colors">{t("common.active")}</Badge> : <Badge className="bg-red-500/20 text-red-600 dark:text-red-400 hover:bg-red-500/30 transition-colors">{t("common.inactive")}</Badge>}
                            </button>
                          ) : (
                            vehicle.isActive ? <Badge className="bg-emerald-500/20 text-emerald-600 dark:text-emerald-400">{t("common.active")}</Badge> : <Badge className="bg-red-500/20 text-red-600 dark:text-red-400">{t("common.inactive")}</Badge>
                          )}
                        </TableCell>
                      )}
                      {isVehicleVis("actions") && (
                        <TableCell className="text-right">
                          {canEditVehicle && <Button variant="ghost" size="sm" className="text-muted-foreground hover:text-foreground" onClick={() => router.push(`/dashboard/vehicles/${vehicle.id}/edit`)}>{t("common.edit")}</Button>}
                          {canDeleteVehicle && <Button variant="ghost" size="sm" className="gap-1 text-muted-foreground hover:text-red-600" onClick={() => openDeleteDialog(vehicle)}><Trash2 className="h-3.5 w-3.5" /></Button>}
                        </TableCell>
                      )}
                    </TableRow>
                  ))}
                  </TableBody>
                </Table>
              </div>
            </>
          )}
        </TabsContent>
      </Tabs>

      {/* ── Add Vehicle Type Dialog ────────────────────────────── */}
      <Dialog
        open={typeDialogOpen}
        onOpenChange={(open) => {
          setTypeDialogOpen(open);
          if (!open) resetTypeForm();
        }}
      >
        <DialogContent className="border-border bg-popover text-foreground">
          <DialogHeader>
            <DialogTitle>{t("vehicles.addVehicleType")}</DialogTitle>
          </DialogHeader>
          <div className="space-y-4 py-2">
            <div className="space-y-2">
              <Label htmlFor="type-name" className="text-muted-foreground">
                {t("common.name")}
              </Label>
              <Input
                id="type-name"
                placeholder="e.g. Sedan, Minibus, Coaster"
                value={typeName}
                onChange={(e) => setTypeName(e.target.value)}
                className="border-border bg-card text-foreground placeholder:text-muted-foreground"
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="type-capacity" className="text-muted-foreground">
                {t("vehicles.seatCapacity")}
              </Label>
              <Input
                id="type-capacity"
                type="number"
                min={1}
                placeholder="e.g. 4"
                value={typeSeatCapacity}
                onChange={(e) => setTypeSeatCapacity(e.target.value)}
                className="border-border bg-card text-foreground placeholder:text-muted-foreground"
              />
            </div>
            {vehicleTypeMediaFields()}
          </div>
          <DialogFooter>
            <Button
              variant="ghost"
              onClick={() => setTypeDialogOpen(false)}
              className="text-muted-foreground hover:text-foreground"
            >
              {t("common.cancel")}
            </Button>
            <Button
              onClick={handleCreateType}
              disabled={typeSubmitting}
              className="gap-1.5 bg-primary text-primary-foreground hover:bg-primary/90"
            >
              {typeSubmitting && (
                <Loader2 className="h-4 w-4 animate-spin" />
              )}
              {t("common.create")}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* ── Import Results Dialog ─────────────────────────────── */}
      <Dialog
        open={importResult.open}
        onOpenChange={(open) => {
          if (!open) setImportResult({ open: false, imported: 0, errors: [] });
        }}
      >
        <DialogContent className="border-border bg-popover text-foreground max-w-lg">
          <DialogHeader>
            <DialogTitle>{t("vehicles.importResults")}</DialogTitle>
          </DialogHeader>
          <div className="space-y-4 py-2">
            <div className="flex items-center gap-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-full bg-emerald-500/15">
                <FileSpreadsheet className="h-5 w-5 text-emerald-500" />
              </div>
              <div>
                <p className="text-sm font-medium text-foreground">
                  {importResult.imported} {t("vehicles.imported")}
                </p>
                {importResult.errors.length > 0 && (
                  <p className="text-xs text-muted-foreground">
                    {importResult.errors.length} {t("vehicles.errors")}
                  </p>
                )}
              </div>
            </div>

            {importResult.errors.length > 0 && (
              <div className="max-h-48 overflow-y-auto rounded-lg border border-border bg-muted/30 p-3">
                <p className="mb-2 text-xs font-medium text-muted-foreground uppercase">
                  Errors
                </p>
                <ul className="space-y-1">
                  {importResult.errors.map((err, i) => (
                    <li
                      key={i}
                      className="text-xs text-destructive flex items-start gap-1.5"
                    >
                      <AlertTriangle className="mt-0.5 h-3 w-3 shrink-0" />
                      {err}
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>
          <DialogFooter>
            <Button
              onClick={() =>
                setImportResult({ open: false, imported: 0, errors: [] })
              }
            >
              {t("common.close")}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* ── Delete Vehicle Confirmation Dialog ─────────────────── */}
      <Dialog open={deleteDialogOpen} onOpenChange={(open) => {
        setDeleteDialogOpen(open);
        if (!open) setDeletingVehicle(null);
      }}>
        <DialogContent className="border-border bg-popover text-popover-foreground sm:max-w-md">
          <DialogHeader>
            <DialogTitle>{t("vehicles.deleteVehicle")}</DialogTitle>
          </DialogHeader>
          <div className="space-y-3 py-2">
            <p className="text-sm text-muted-foreground">
              {t("vehicles.deleteConfirm")} <span className="font-medium text-foreground">{deletingVehicle?.plateNumber}</span>?
            </p>
            <p className="text-xs text-muted-foreground">
              {t("vehicles.deleteNote")}
            </p>
          </div>
          <DialogFooter>
            <Button
              variant="ghost"
              onClick={() => setDeleteDialogOpen(false)}
              disabled={deleting}
            >
              {t("common.cancel")}
            </Button>
            <Button
              variant="destructive"
              onClick={handleDelete}
              disabled={deleting}
              className="gap-1.5"
            >
              {deleting && <Loader2 className="h-4 w-4 animate-spin" />}
              {t("common.delete")}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* ── Edit Vehicle Type Dialog ─────────────────────────── */}
      <Dialog
        open={editTypeDialogOpen}
        onOpenChange={(open) => {
          setEditTypeDialogOpen(open);
          if (!open) {
            setEditingType(null);
            resetTypeForm();
          }
        }}
      >
        <DialogContent className="border-border bg-popover text-foreground">
          <DialogHeader>
            <DialogTitle>{t("vehicles.editType")}</DialogTitle>
          </DialogHeader>
          <div className="space-y-4 py-2">
            <div className="space-y-2">
              <Label htmlFor="edit-type-name" className="text-muted-foreground">
                {t("common.name")}
              </Label>
              <Input
                id="edit-type-name"
                placeholder="e.g. Sedan, Minibus, Coaster"
                value={typeName}
                onChange={(e) => setTypeName(e.target.value)}
                className="border-border bg-card text-foreground placeholder:text-muted-foreground"
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="edit-type-capacity" className="text-muted-foreground">
                {t("vehicles.seatCapacity")}
              </Label>
              <Input
                id="edit-type-capacity"
                type="number"
                min={1}
                placeholder="e.g. 4"
                value={typeSeatCapacity}
                onChange={(e) => setTypeSeatCapacity(e.target.value)}
                className="border-border bg-card text-foreground placeholder:text-muted-foreground"
              />
            </div>
            {vehicleTypeMediaFields()}
          </div>
          <DialogFooter>
            <Button
              variant="ghost"
              onClick={() => setEditTypeDialogOpen(false)}
              className="text-muted-foreground hover:text-foreground"
            >
              {t("common.cancel")}
            </Button>
            <Button
              onClick={handleUpdateType}
              disabled={typeSubmitting}
              className="gap-1.5 bg-primary text-primary-foreground hover:bg-primary/90"
            >
              {typeSubmitting && (
                <Loader2 className="h-4 w-4 animate-spin" />
              )}
              {t("common.saveChanges")}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

    </div>
  );
}
