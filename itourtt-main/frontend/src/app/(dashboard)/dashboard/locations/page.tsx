"use client";

import { useEffect, useState, useCallback, useRef } from "react";
import {
  ChevronRight,
  MapPin,
  Plus,
  Trash2,
  Loader2,
  Building,
  Globe,
  Map,
  Hotel as HotelIcon,
  FileDown,
  FileUp,
  FileSpreadsheet,
  AlertTriangle,
  Search,
  X,
  KeyRound,
  Eye,
  EyeOff,
  Navigation,
  Pencil,
} from "lucide-react";
import { PageHeader } from "@/components/page-header";
import { Card } from "@/components/ui/card";
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
import { Badge } from "@/components/ui/badge";
import api from "@/lib/api";
import { toast } from "sonner";
import { useT } from "@/lib/i18n";
import { useAuthStore } from "@/stores/auth-store";
import { usePermission } from "@/hooks/use-permission";
import { localDateStr } from "@/lib/utils";
import {
  GooglePlacesAutocomplete,
  type PlaceResult,
} from "@/components/google-places-autocomplete";

// ─── Types ──────────────────────────────────────────────────────
interface HotelNode {
  id: string;
  name: string;
}

interface ZoneNode {
  id: string;
  name: string;
  hotels: HotelNode[];
}

interface CityNode {
  id: string;
  name: string;
  zones: ZoneNode[];
}

interface AirportNode {
  id: string;
  name: string;
  code: string;
  cities: CityNode[];
}

interface CountryNode {
  id: string;
  name: string;
  code: string;
  airports: AirportNode[];
}

type LocationLevel = "country" | "airport" | "city" | "zone" | "hotel";

interface AddDialogState {
  open: boolean;
  level: LocationLevel;
  parentId: string;
  parentLabel: string;
}

// ─── Level config ───────────────────────────────────────────────
const LEVEL_CONFIG: Record<
  LocationLevel,
  {
    label: string;
    icon: React.ElementType;
    hasCode: boolean;
    endpoint: string;
    parentKey?: string;
    childLevel?: LocationLevel;
    childLabel?: string;
  }
> = {
  country: {
    label: "locations.country",
    icon: Globe,
    hasCode: true,
    endpoint: "/locations/countries",
    childLevel: "airport",
    childLabel: "locations.airport",
  },
  airport: {
    label: "locations.airport",
    icon: Building,
    hasCode: true,
    endpoint: "/locations/airports",
    parentKey: "countryId",
    childLevel: "city",
    childLabel: "locations.city",
  },
  city: {
    label: "locations.city",
    icon: Map,
    hasCode: false,
    endpoint: "/locations/cities",
    parentKey: "airportId",
    childLevel: "zone",
    childLabel: "locations.zone",
  },
  zone: {
    label: "locations.zone",
    icon: MapPin,
    hasCode: false,
    endpoint: "/locations/zones",
    parentKey: "cityId",
    childLevel: "hotel",
    childLabel: "locations.hotel",
  },
  hotel: {
    label: "locations.hotel",
    icon: HotelIcon,
    hasCode: false,
    endpoint: "/locations/hotels",
    parentKey: "zoneId",
  },
};

// ─── Tree row component ─────────────────────────────────────────
function TreeRow({
  icon: Icon,
  name,
  code,
  depth,
  hasChildren,
  expanded,
  onToggle,
  onAddChild,
  childLabel,
  onEdit,
  onDelete,
}: {
  icon: React.ElementType;
  name: string;
  code?: string;
  depth: number;
  hasChildren: boolean;
  expanded: boolean;
  onToggle: () => void;
  onAddChild?: () => void;
  childLabel?: string;
  onEdit?: () => void;
  onDelete?: () => void;
}) {
  const paddingLeft = depth * 20;

  return (
    <div
      className="group flex items-center gap-1.5 rounded-md px-2 py-1.5 transition-colors"
      style={{ paddingLeft: `${paddingLeft + 8}px` }}
    >
      {/* Expand/collapse toggle */}
      {hasChildren ? (
        <button
          onClick={onToggle}
          className="flex h-5 w-5 shrink-0 items-center justify-center rounded transition-colors"
        >
          <ChevronRight
            className={`h-3.5 w-3.5 text-muted-foreground transition-transform duration-150 ${
              expanded ? "rotate-90" : ""
            }`}
          />
        </button>
      ) : (
        <span className="w-5 shrink-0" />
      )}

      {/* Add child button (visible on hover, before name) */}
      {onAddChild && childLabel && (
        <button
          onClick={(e) => {
            e.stopPropagation();
            onAddChild();
          }}
          title={childLabel}
          className="flex h-5 w-5 shrink-0 items-center justify-center rounded text-muted-foreground opacity-0 transition-opacity hover:bg-primary/10 hover:text-primary group-hover:opacity-100"
        >
          <Plus className="h-3.5 w-3.5" />
        </button>
      )}

      {/* Edit button (visible on hover) */}
      {onEdit && (
        <button
          onClick={(e) => {
            e.stopPropagation();
            onEdit();
          }}
          title="Edit"
          className="flex h-5 w-5 shrink-0 items-center justify-center rounded text-muted-foreground opacity-0 transition-opacity hover:bg-primary/10 hover:text-primary group-hover:opacity-100"
        >
          <Pencil className="h-3.5 w-3.5" />
        </button>
      )}

      {/* Delete button (visible on hover, before name) */}
      {onDelete && (
        <button
          onClick={(e) => {
            e.stopPropagation();
            onDelete();
          }}
          title="Delete"
          className="flex h-5 w-5 shrink-0 items-center justify-center rounded text-muted-foreground opacity-0 transition-opacity hover:bg-destructive/10 hover:text-destructive group-hover:opacity-100"
        >
          <Trash2 className="h-3.5 w-3.5" />
        </button>
      )}

      {/* Icon */}
      <Icon className="h-4 w-4 shrink-0 text-muted-foreground" />

      {/* Name */}
      <span className="truncate text-sm text-foreground">{name}</span>

      {/* Code badge */}
      {code && (
        <Badge
          variant="secondary"
          className="ml-1 bg-secondary text-[10px] text-muted-foreground"
        >
          {code}
        </Badge>
      )}
    </div>
  );
}

// ─── Main page ──────────────────────────────────────────────────
export default function LocationsPage() {
  const t = useT();
  const { user } = useAuthStore();
  const isAdmin = user?.role === "ADMIN";

  // Permission checks
  const canAddCountry = usePermission("locations.countries.addButton");
  const canEditCountry = usePermission("locations.countries.editButton");
  const canAddAirport = usePermission("locations.airports.addButton");
  const canEditAirport = usePermission("locations.airports.editButton");
  const canDeleteAirport = usePermission("locations.airports.deleteButton");
  const canAddCity = usePermission("locations.cities.addButton");
  const canEditCity = usePermission("locations.cities.editButton");
  const canDeleteCity = usePermission("locations.cities.deleteButton");
  const canAddZone = usePermission("locations.zones.addButton");
  const canEditZone = usePermission("locations.zones.editButton");
  const canDeleteZone = usePermission("locations.zones.deleteButton");
  const canAddHotel = usePermission("locations.hotels.addButton");
  const canEditHotel = usePermission("locations.hotels.editButton");
  const canDeleteHotel = usePermission("locations.hotels.deleteButton");
  const [countries, setCountries] = useState<CountryNode[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");

  // Import/Export state
  const importFileRef = useRef<HTMLInputElement>(null);
  const [importing, setImporting] = useState(false);
  const [exporting, setExporting] = useState(false);
  const [importResult, setImportResult] = useState<{
    open: boolean;
    imported: number;
    errors: string[];
  }>({ open: false, imported: 0, errors: [] });

  // Google Maps API Key
  const [googleMapsKey, setGoogleMapsKey] = useState("");
  const [googleMapsKeyLoading, setGoogleMapsKeyLoading] = useState(true);
  const [savingKey, setSavingKey] = useState(false);
  const [showKey, setShowKey] = useState(false);

  // Expanded state keyed by "level-id"
  const [expanded, setExpanded] = useState<Record<string, boolean>>({});

  // Add dialog
  const [dialog, setDialog] = useState<AddDialogState>({
    open: false,
    level: "country",
    parentId: "",
    parentLabel: "",
  });
  const [formName, setFormName] = useState("");
  const [formCode, setFormCode] = useState("");
  const [submitting, setSubmitting] = useState(false);

  // Google Places autocomplete for add dialog
  const [formPlace, setFormPlace] = useState<PlaceResult | null>(null);

  // Batch geocode state
  const [batchGeocoding, setBatchGeocoding] = useState(false);
  const [batchResult, setBatchResult] = useState<{
    open: boolean;
    resolved: number;
    needsReview: Array<{
      type: string;
      id: string;
      name: string;
      candidates: PlaceResult[];
    }>;
  }>({ open: false, resolved: 0, needsReview: [] });

  // Edit dialog
  const [editDialog, setEditDialog] = useState<{
    open: boolean;
    level: LocationLevel;
    id: string;
    name: string;
    code: string;
  }>({ open: false, level: "country", id: "", name: "", code: "" });
  const [editName, setEditName] = useState("");
  const [editCode, setEditCode] = useState("");
  const [editPlace, setEditPlace] = useState<PlaceResult | null>(null);
  const [editSubmitting, setEditSubmitting] = useState(false);

  // Delete confirmation
  const [deleteDialog, setDeleteDialog] = useState<{
    open: boolean;
    level: LocationLevel;
    id: string;
    name: string;
  }>({ open: false, level: "country", id: "", name: "" });
  const [deleting, setDeleting] = useState(false);

  // ─── Fetch tree ─────────────────────────────────────────────
  const fetchTree = useCallback(async () => {
    try {
      const { data } = await api.get("/locations/tree");
      const tree = Array.isArray(data) ? data : data.data ?? data.countries ?? [];
      setCountries(tree);
    } catch {
      toast.error(t("locations.failedLoad"));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchTree();
  }, [fetchTree]);

  // ─── Fetch Google Maps API Key ─────────────────────────────
  useEffect(() => {
    api
      .get("/settings/system")
      .then(({ data }) => {
        const raw = data.data ?? data;
        setGoogleMapsKey(raw.googleMapsApiKey ?? "");
      })
      .catch(() => {})
      .finally(() => setGoogleMapsKeyLoading(false));
  }, []);

  async function handleSaveGoogleMapsKey() {
    setSavingKey(true);
    try {
      await api.patch("/settings/system", { googleMapsApiKey: googleMapsKey });
      toast.success("Google Maps API key saved");
    } catch {
      toast.error("Failed to save Google Maps API key");
    } finally {
      setSavingKey(false);
    }
  }

  // ─── Toggle expansion ──────────────────────────────────────
  function toggle(key: string) {
    setExpanded((prev) => ({ ...prev, [key]: !prev[key] }));
  }

  // ─── Search filter ────────────────────────────────────────
  const searchLower = search.toLowerCase().trim();

  function matchesSearch(name: string, code?: string): boolean {
    if (!searchLower) return true;
    return (
      name.toLowerCase().includes(searchLower) ||
      (code ? code.toLowerCase().includes(searchLower) : false)
    );
  }

  // Filter tree: keep a node if it or any descendant matches
  const filteredCountries = !searchLower
    ? countries
    : countries
        .map((country) => {
          const filteredAirports = country.airports
            .map((airport) => {
              const filteredCities = airport.cities
                .map((city) => {
                  const filteredZones = city.zones
                    .map((zone) => {
                      const filteredHotels = zone.hotels.filter((h) =>
                        matchesSearch(h.name)
                      );
                      if (filteredHotels.length > 0 || matchesSearch(zone.name))
                        return { ...zone, hotels: filteredHotels };
                      return null;
                    })
                    .filter(Boolean) as ZoneNode[];
                  if (filteredZones.length > 0 || matchesSearch(city.name))
                    return { ...city, zones: filteredZones };
                  return null;
                })
                .filter(Boolean) as CityNode[];
              if (
                filteredCities.length > 0 ||
                matchesSearch(airport.name, airport.code)
              )
                return { ...airport, cities: filteredCities };
              return null;
            })
            .filter(Boolean) as AirportNode[];
          if (
            filteredAirports.length > 0 ||
            matchesSearch(country.name, country.code)
          )
            return { ...country, airports: filteredAirports };
          return null;
        })
        .filter(Boolean) as CountryNode[];

  // Auto-expand all nodes when searching
  const searchExpanded: Record<string, boolean> = {};
  if (searchLower) {
    filteredCountries.forEach((country) => {
      searchExpanded[`country-${country.id}`] = true;
      country.airports.forEach((airport) => {
        searchExpanded[`airport-${airport.id}`] = true;
        airport.cities.forEach((city) => {
          searchExpanded[`city-${city.id}`] = true;
          city.zones.forEach((zone) => {
            searchExpanded[`zone-${zone.id}`] = true;
          });
        });
      });
    });
  }

  const effectiveExpanded = searchLower ? searchExpanded : expanded;

  // ─── Open add dialog ──────────────────────────────────────
  function openAdd(level: LocationLevel, parentId: string, parentLabel: string) {
    setDialog({ open: true, level, parentId, parentLabel });
    setFormName("");
    setFormCode("");
    setFormPlace(null);
  }

  // ─── Submit new location ──────────────────────────────────
  async function handleSubmit() {
    const config = LEVEL_CONFIG[dialog.level];
    if (!formName.trim()) {
      toast.error(t("locations.nameRequired"));
      return;
    }
    if (config.hasCode && !formCode.trim()) {
      toast.error(t("locations.codeRequired"));
      return;
    }

    setSubmitting(true);
    try {
      const payload: Record<string, any> = { name: formName.trim() };
      if (config.hasCode) {
        payload.code = formCode.trim().toUpperCase();
      }
      if (config.parentKey && dialog.parentId) {
        payload[config.parentKey] = dialog.parentId;
      }
      if (formPlace) {
        payload.latitude = formPlace.lat;
        payload.longitude = formPlace.lng;
        payload.placeId = formPlace.placeId;
      }

      await api.post(config.endpoint, payload);
      toast.success(`${t(config.label)} ${t("locations.createdSuccess")}`);
      setDialog((prev) => ({ ...prev, open: false }));
      await fetchTree();
    } catch (err: unknown) {
      const message =
        (err as { response?: { data?: { message?: string } } })?.response?.data
          ?.message || `${t("locations.failedCreate")} ${t(config.label).toLowerCase()}`;
      toast.error(message);
    } finally {
      setSubmitting(false);
    }
  }

  // ─── Delete handler ─────────────────────────────────────────
  function openEdit(level: LocationLevel, id: string, name: string, code?: string) {
    setEditDialog({ open: true, level, id, name, code: code || "" });
    setEditName(name);
    setEditCode(code || "");
    setEditPlace(null);
  }

  async function handleEditSubmit() {
    if (!editName.trim()) {
      toast.error(t("locations.nameRequired"));
      return;
    }
    const config = LEVEL_CONFIG[editDialog.level];
    if (config.hasCode && !editCode.trim()) {
      toast.error(t("locations.codeRequired"));
      return;
    }

    setEditSubmitting(true);
    try {
      const payload: Record<string, any> = { name: editName.trim() };
      if (config.hasCode) {
        payload.code = editCode.trim().toUpperCase();
      }
      if (editPlace) {
        payload.latitude = editPlace.lat;
        payload.longitude = editPlace.lng;
        payload.placeId = editPlace.placeId;
      }

      await api.patch(`${config.endpoint}/${editDialog.id}`, payload);
      toast.success(`${t(config.label)} updated`);
      setEditDialog((prev) => ({ ...prev, open: false }));
      await fetchTree();
    } catch (err: unknown) {
      const message =
        (err as { response?: { data?: { message?: string } } })?.response?.data
          ?.message || "Failed to update";
      toast.error(message);
    } finally {
      setEditSubmitting(false);
    }
  }

  function confirmDelete(level: LocationLevel, id: string, name: string) {
    setDeleteDialog({ open: true, level, id, name });
  }

  async function handleDelete() {
    const { level, id } = deleteDialog;
    const endpoint = `${LEVEL_CONFIG[level].endpoint}/${id}`;
    setDeleting(true);
    try {
      await api.delete(endpoint);
      toast.success(`${t(LEVEL_CONFIG[level].label)} ${t("locations.deletedSuccess")}`);
      setDeleteDialog((prev) => ({ ...prev, open: false }));
      await fetchTree();
    } catch (err: unknown) {
      const message =
        (err as { response?: { data?: { message?: string } } })?.response?.data
          ?.message || `${t("locations.failedDelete")} ${t(LEVEL_CONFIG[level].label).toLowerCase()}`;
      toast.error(message);
    } finally {
      setDeleting(false);
    }
  }

  // ─── Export ────────────────────────────────────────────────
  async function handleExport() {
    setExporting(true);
    try {
      const res = await api.get("/locations/export/excel", {
        responseType: "blob",
      });
      const url = window.URL.createObjectURL(new Blob([res.data]));
      const link = document.createElement("a");
      link.href = url;
      const date = localDateStr(new Date());
      link.setAttribute("download", `locations_${date}.xlsx`);
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
      toast.success(t("locations.exportSuccess"));
    } catch {
      toast.error(t("locations.failedExport"));
    } finally {
      setExporting(false);
    }
  }

  // ─── Download template ────────────────────────────────────
  async function handleDownloadTemplate() {
    try {
      const res = await api.get("/locations/import/template", {
        responseType: "blob",
      });
      const url = window.URL.createObjectURL(new Blob([res.data]));
      const link = document.createElement("a");
      link.href = url;
      link.setAttribute("download", "locations_import_template.xlsx");
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
    } catch {
      toast.error(t("locations.failedTemplate"));
    }
  }

  // ─── Import file ──────────────────────────────────────────
  async function handleImportFile(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;

    setImporting(true);
    try {
      const formData = new FormData();
      formData.append("file", file);
      const res = await api.post("/locations/import/excel", formData, {
        headers: { "Content-Type": "multipart/form-data" },
      });
      const result = res.data.data;
      setImportResult({
        open: true,
        imported: result.imported,
        errors: result.errors,
      });
      if (result.imported > 0) {
        fetchTree();
      }
    } catch (err: unknown) {
      const message =
        (err as { response?: { data?: { message?: string } } })?.response?.data
          ?.message || t("locations.failedImport");
      toast.error(message);
    } finally {
      setImporting(false);
      if (importFileRef.current) {
        importFileRef.current.value = "";
      }
    }
  }

  // ─── Batch Geocode ────────────────────────────────────────
  async function handleBatchGeocode() {
    setBatchGeocoding(true);
    try {
      const { data } = await api.post("/locations/batch-geocode");
      const result = data.data || data;
      setBatchResult({
        open: true,
        resolved: result.resolved,
        needsReview: result.needsReview || [],
      });
      if (result.resolved > 0) {
        fetchTree();
      }
    } catch (err: unknown) {
      const message =
        (err as { response?: { data?: { message?: string } } })?.response?.data
          ?.message || "Failed to run batch geocode";
      toast.error(message);
    } finally {
      setBatchGeocoding(false);
    }
  }

  async function handlePickCandidate(
    type: string,
    id: string,
    candidate: PlaceResult,
  ) {
    try {
      await api.patch(`/locations/${type}/${id}/coordinates`, {
        latitude: candidate.lat,
        longitude: candidate.lng,
        placeId: candidate.placeId,
      });
      toast.success("Coordinates updated");
      // Remove from review list
      setBatchResult((prev) => ({
        ...prev,
        resolved: prev.resolved + 1,
        needsReview: prev.needsReview.filter(
          (item) => !(item.type === type && item.id === id)
        ),
      }));
    } catch {
      toast.error("Failed to update coordinates");
    }
  }

  // ─── Render ───────────────────────────────────────────────
  const currentConfig = LEVEL_CONFIG[dialog.level];

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <PageHeader
          title={t("locations.title")}
          description={`${t("locations.description")}: ${t("locations.locationTree")}`}
        />
        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            className="gap-1.5"
            onClick={handleDownloadTemplate}
          >
            <FileDown className="h-4 w-4" />
            {t("common.template")}
          </Button>
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
          {isAdmin && (
            <Button
              variant="outline"
              size="sm"
              className="gap-1.5"
              onClick={handleBatchGeocode}
              disabled={batchGeocoding}
            >
              {batchGeocoding ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <Navigation className="h-4 w-4" />
              )}
              Resolve Coordinates
            </Button>
          )}
          {canAddCountry && (
            <Button size="sm" className="gap-1.5" onClick={() => openAdd("country", "", "")}>
              <Plus className="h-4 w-4" />
              {t("locations.addCountry")}
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

      {/* Google Maps API Key */}
      {isAdmin && (
        <Card className="border-border bg-card p-4">
          <div className="flex items-center gap-3">
            <KeyRound className="h-5 w-5 shrink-0 text-muted-foreground" />
            <div className="flex-1 space-y-1">
              <Label className="text-xs font-medium text-muted-foreground">
                Google Maps API Key
              </Label>
              <div className="flex items-center gap-2">
                <div className="relative flex-1">
                  <Input
                    type={showKey ? "text" : "password"}
                    placeholder={googleMapsKeyLoading ? "Loading..." : "Enter your Google Maps API key..."}
                    value={googleMapsKey}
                    onChange={(e) => setGoogleMapsKey(e.target.value)}
                    disabled={googleMapsKeyLoading}
                    className="border-border bg-background pr-9 text-foreground placeholder:text-muted-foreground/50 font-mono text-sm"
                  />
                  <button
                    type="button"
                    onClick={() => setShowKey((v) => !v)}
                    className="absolute right-2.5 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
                  >
                    {showKey ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                  </button>
                </div>
                <Button
                  size="sm"
                  onClick={handleSaveGoogleMapsKey}
                  disabled={savingKey || googleMapsKeyLoading}
                >
                  {savingKey ? <Loader2 className="h-4 w-4 animate-spin" /> : "Save"}
                </Button>
              </div>
              <p className="text-[11px] text-muted-foreground/60">
                Required for Google Places autocomplete in the booking widget. Get a key from Google Cloud Console.
              </p>
            </div>
          </div>
        </Card>
      )}

      {/* Search filter */}
      <div className="relative">
        <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
        <Input
          placeholder={t("locations.searchPlaceholder") || "Search locations..."}
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="border-border bg-card pl-9 pr-9 text-foreground placeholder:text-muted-foreground/50"
        />
        {search && (
          <button
            onClick={() => setSearch("")}
            className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
          >
            <X className="h-4 w-4" />
          </button>
        )}
      </div>

      <Card className="border-border bg-card p-0">
        {loading ? (
          <div className="flex items-center justify-center py-20">
            <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
          </div>
        ) : filteredCountries.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-20 text-muted-foreground">
            {searchLower ? (
              <>
                <Search className="mb-3 h-10 w-10" />
                <p className="text-sm">{t("locations.noSearchResults") || "No locations match your search"}</p>
                <p className="mt-1 text-xs text-muted-foreground/60">
                  {t("locations.tryDifferentSearch") || "Try a different search term"}
                </p>
              </>
            ) : (
              <>
                <Globe className="mb-3 h-10 w-10" />
                <p className="text-sm">{t("locations.noLocations")}</p>
                <p className="mt-1 text-xs text-muted-foreground/60">
                  {t("locations.addCountryToStart")}
                </p>
              </>
            )}
          </div>
        ) : (
          <div className="py-2">
            {filteredCountries.map((country) => {
              const countryKey = `country-${country.id}`;
              const countryExpanded = !!effectiveExpanded[countryKey];

              return (
                <div key={country.id}>
                  {/* Country */}
                  <TreeRow
                    icon={Globe}
                    name={country.name}
                    code={country.code}
                    depth={0}
                    hasChildren={country.airports.length > 0}
                    expanded={countryExpanded}
                    onToggle={() => toggle(countryKey)}
                    onAddChild={canAddAirport ? () =>
                      openAdd("airport", country.id, country.name)
                    : undefined}
                    childLabel={t("locations.airport")}
                    onEdit={canEditCountry ? () => openEdit("country", country.id, country.name, country.code) : undefined}
                    onDelete={isAdmin ? () =>
                      confirmDelete("country", country.id, country.name)
                    : undefined}
                  />

                  {/* Airports */}
                  {countryExpanded &&
                    country.airports.map((airport) => {
                      const airportKey = `airport-${airport.id}`;
                      const airportExpanded = !!effectiveExpanded[airportKey];

                      return (
                        <div key={airport.id}>
                          <TreeRow
                            icon={Building}
                            name={airport.name}
                            code={airport.code}
                            depth={1}
                            hasChildren={airport.cities.length > 0}
                            expanded={airportExpanded}
                            onToggle={() => toggle(airportKey)}
                            onAddChild={canAddCity ? () =>
                              openAdd("city", airport.id, airport.name)
                            : undefined}
                            childLabel={t("locations.city")}
                            onEdit={canEditAirport ? () => openEdit("airport", airport.id, airport.name, airport.code) : undefined}
                            onDelete={canDeleteAirport ? () =>
                              confirmDelete("airport", airport.id, airport.name)
                            : undefined}
                          />

                          {/* Cities */}
                          {airportExpanded &&
                            airport.cities.map((city) => {
                              const cityKey = `city-${city.id}`;
                              const cityExpanded = !!effectiveExpanded[cityKey];

                              return (
                                <div key={city.id}>
                                  <TreeRow
                                    icon={Map}
                                    name={city.name}
                                    depth={2}
                                    hasChildren={city.zones.length > 0}
                                    expanded={cityExpanded}
                                    onToggle={() => toggle(cityKey)}
                                    onAddChild={canAddZone ? () =>
                                      openAdd("zone", city.id, city.name)
                                    : undefined}
                                    childLabel={t("locations.zone")}
                                    onEdit={canEditCity ? () => openEdit("city", city.id, city.name) : undefined}
                                    onDelete={canDeleteCity ? () =>
                                      confirmDelete("city", city.id, city.name)
                                    : undefined}
                                  />

                                  {/* Zones */}
                                  {cityExpanded &&
                                    city.zones.map((zone) => {
                                      const zoneKey = `zone-${zone.id}`;
                                      const zoneExpanded = !!effectiveExpanded[zoneKey];

                                      return (
                                        <div key={zone.id}>
                                          <TreeRow
                                            icon={MapPin}
                                            name={zone.name}
                                            depth={3}
                                            hasChildren={
                                              zone.hotels.length > 0
                                            }
                                            expanded={zoneExpanded}
                                            onToggle={() => toggle(zoneKey)}
                                            onAddChild={canAddHotel ? () =>
                                              openAdd(
                                                "hotel",
                                                zone.id,
                                                zone.name
                                              )
                                            : undefined}
                                            childLabel={t("locations.hotel")}
                                            onEdit={canEditZone ? () => openEdit("zone", zone.id, zone.name) : undefined}
                                            onDelete={canDeleteZone ? () =>
                                              confirmDelete(
                                                "zone",
                                                zone.id,
                                                zone.name
                                              )
                                            : undefined}
                                          />

                                          {/* Hotels */}
                                          {zoneExpanded &&
                                            zone.hotels.map((hotel) => (
                                              <TreeRow
                                                key={hotel.id}
                                                icon={HotelIcon}
                                                name={hotel.name}
                                                depth={4}
                                                hasChildren={false}
                                                expanded={false}
                                                onToggle={() => {}}
                                                onEdit={canEditHotel ? () => openEdit("hotel", hotel.id, hotel.name) : undefined}
                                                onDelete={canDeleteHotel ? () =>
                                                  confirmDelete(
                                                    "hotel",
                                                    hotel.id,
                                                    hotel.name
                                                  )
                                                : undefined}
                                              />
                                            ))}
                                        </div>
                                      );
                                    })}
                                </div>
                              );
                            })}
                        </div>
                      );
                    })}
                </div>
              );
            })}
          </div>
        )}
      </Card>

      {/* ─── Add dialog ──────────────────────────────────────── */}
      <Dialog
        open={dialog.open}
        onOpenChange={(open) => setDialog((prev) => ({ ...prev, open }))}
      >
        <DialogContent className="border-border bg-popover text-foreground sm:max-w-md">
          <DialogHeader>
            <DialogTitle>
              {t("common.add")} {t(currentConfig.label)}
              {dialog.parentLabel && (
                <span className="ml-1 text-sm font-normal text-muted-foreground">
                  {t("locations.in")} {dialog.parentLabel}
                </span>
              )}
            </DialogTitle>
          </DialogHeader>

          <div className="space-y-4 py-2">
            {/* Name field */}
            <div className="space-y-2">
              <Label className="text-muted-foreground">{t("common.name")}</Label>
              <Input
                placeholder={`${t(currentConfig.label)} ${t("locations.namePlaceholder")}`}
                value={formName}
                onChange={(e) => setFormName(e.target.value)}
                className="border-border bg-card text-foreground placeholder:text-muted-foreground"
                onKeyDown={(e) => {
                  if (e.key === "Enter") handleSubmit();
                }}
              />
            </div>

            {/* Code field (only for country and airport) */}
            {currentConfig.hasCode && (
              <div className="space-y-2">
                <Label className="text-muted-foreground">{t("locations.code")}</Label>
                <Input
                  placeholder={
                    dialog.level === "country" ? "e.g. EG" : "e.g. CAI"
                  }
                  value={formCode}
                  onChange={(e) => setFormCode(e.target.value)}
                  maxLength={dialog.level === "country" ? 3 : 10}
                  className="border-border bg-card text-foreground uppercase placeholder:text-muted-foreground placeholder:normal-case"
                  onKeyDown={(e) => {
                    if (e.key === "Enter") handleSubmit();
                  }}
                />
              </div>
            )}

            {/* Google Places autocomplete for coordinates */}
            <div className="space-y-2">
              <Label className="text-muted-foreground">
                Location on Google Maps
                <span className="ml-1 text-xs text-muted-foreground/60">(optional)</span>
              </Label>
              <GooglePlacesAutocomplete
                value={formPlace}
                onChange={(place) => {
                  setFormPlace(place);
                  // Auto-fill name if empty
                  if (place && !formName.trim()) {
                    setFormName(place.name);
                  }
                }}
                type={dialog.level}
                placeholder={`Search for ${dialog.level} on Google Maps...`}
              />
              {formPlace && (
                <p className="text-xs text-muted-foreground">
                  <MapPin className="inline h-3 w-3 mr-1" />
                  {formPlace.lat.toFixed(5)}, {formPlace.lng.toFixed(5)}
                  <span className="ml-2 text-muted-foreground/60">
                    {formPlace.formattedAddress}
                  </span>
                </p>
              )}
            </div>
          </div>

          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => setDialog((prev) => ({ ...prev, open: false }))}
              className="border-border text-muted-foreground hover:text-foreground"
            >
              {t("common.cancel")}
            </Button>
            <Button
              onClick={handleSubmit}
              disabled={submitting}
              className="gap-1.5 bg-primary text-primary-foreground hover:bg-primary/90"
            >
              {submitting && <Loader2 className="h-4 w-4 animate-spin" />}
              {t("common.create")}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* ─── Edit dialog ─────────────────────────────────────── */}
      <Dialog
        open={editDialog.open}
        onOpenChange={(open) => setEditDialog((prev) => ({ ...prev, open }))}
      >
        <DialogContent className="border-border bg-popover text-foreground sm:max-w-md">
          <DialogHeader>
            <DialogTitle>
              Edit {t(LEVEL_CONFIG[editDialog.level].label)}
            </DialogTitle>
          </DialogHeader>

          <div className="space-y-4 py-2">
            <div className="space-y-2">
              <Label className="text-muted-foreground">{t("common.name")}</Label>
              <Input
                value={editName}
                onChange={(e) => setEditName(e.target.value)}
                className="border-border bg-card text-foreground"
                onKeyDown={(e) => { if (e.key === "Enter") handleEditSubmit(); }}
              />
            </div>

            {LEVEL_CONFIG[editDialog.level].hasCode && (
              <div className="space-y-2">
                <Label className="text-muted-foreground">{t("locations.code")}</Label>
                <Input
                  value={editCode}
                  onChange={(e) => setEditCode(e.target.value)}
                  maxLength={editDialog.level === "country" ? 3 : 10}
                  className="border-border bg-card text-foreground uppercase"
                  onKeyDown={(e) => { if (e.key === "Enter") handleEditSubmit(); }}
                />
              </div>
            )}

            <div className="space-y-2">
              <Label className="text-muted-foreground">
                Location on Google Maps
                <span className="ml-1 text-xs text-muted-foreground/60">(optional)</span>
              </Label>
              <GooglePlacesAutocomplete
                value={editPlace}
                onChange={(place) => setEditPlace(place)}
                type={editDialog.level}
                placeholder={`Search for ${editDialog.level} on Google Maps...`}
              />
              {editPlace && (
                <p className="text-xs text-muted-foreground">
                  <MapPin className="inline h-3 w-3 mr-1" />
                  {editPlace.lat.toFixed(5)}, {editPlace.lng.toFixed(5)}
                </p>
              )}
            </div>
          </div>

          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => setEditDialog((prev) => ({ ...prev, open: false }))}
              className="border-border text-muted-foreground hover:text-foreground"
            >
              {t("common.cancel")}
            </Button>
            <Button
              onClick={handleEditSubmit}
              disabled={editSubmitting}
              className="gap-1.5"
            >
              {editSubmitting && <Loader2 className="h-4 w-4 animate-spin" />}
              Save
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* ─── Delete confirmation dialog ───────────────────────── */}
      <Dialog
        open={deleteDialog.open}
        onOpenChange={(open) =>
          setDeleteDialog((prev) => ({ ...prev, open }))
        }
      >
        <DialogContent className="border-border bg-popover text-foreground sm:max-w-md">
          <DialogHeader>
            <DialogTitle>
              {t("common.delete")} {t(LEVEL_CONFIG[deleteDialog.level].label)}
            </DialogTitle>
          </DialogHeader>
          <p className="text-sm text-muted-foreground">
            {t("locations.deleteConfirmMessage")}{" "}
            <strong className="text-foreground">{deleteDialog.name}</strong>?
            {" "}{t("locations.deleteWarning")}
          </p>
          <DialogFooter>
            <Button
              variant="outline"
              onClick={() =>
                setDeleteDialog((prev) => ({ ...prev, open: false }))
              }
              className="border-border text-muted-foreground hover:text-foreground"
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

      {/* ─── Import results dialog ─────────────────────────────── */}
      <Dialog
        open={importResult.open}
        onOpenChange={(open) => {
          if (!open) setImportResult({ open: false, imported: 0, errors: [] });
        }}
      >
        <DialogContent className="border-border bg-popover text-foreground max-w-lg">
          <DialogHeader>
            <DialogTitle>{t("locations.importResults")}</DialogTitle>
          </DialogHeader>
          <div className="space-y-4 py-2">
            <div className="flex items-center gap-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-full bg-emerald-500/15">
                <FileSpreadsheet className="h-5 w-5 text-emerald-500" />
              </div>
              <div>
                <p className="text-sm font-medium text-foreground">
                  {importResult.imported} {t("locations.imported")}
                </p>
                {importResult.errors.length > 0 && (
                  <p className="text-xs text-muted-foreground">
                    {importResult.errors.length} {t("locations.errors")}
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

      {/* ─── Batch geocode results dialog ──────────────────────── */}
      <Dialog
        open={batchResult.open}
        onOpenChange={(open) => {
          if (!open) setBatchResult({ open: false, resolved: 0, needsReview: [] });
        }}
      >
        <DialogContent className="border-border bg-popover text-foreground max-w-2xl max-h-[80vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <Navigation className="h-5 w-5" />
              Batch Geocode Results
            </DialogTitle>
          </DialogHeader>
          <div className="space-y-4 py-2">
            <div className="flex items-center gap-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-full bg-emerald-500/15">
                <MapPin className="h-5 w-5 text-emerald-500" />
              </div>
              <div>
                <p className="text-sm font-medium text-foreground">
                  {batchResult.resolved} locations resolved automatically
                </p>
                {batchResult.needsReview.length > 0 && (
                  <p className="text-xs text-muted-foreground">
                    {batchResult.needsReview.length} locations need manual review
                  </p>
                )}
              </div>
            </div>

            {batchResult.needsReview.length > 0 && (
              <div className="space-y-3">
                <p className="text-xs font-medium text-muted-foreground uppercase">
                  Needs Manual Review
                </p>
                {batchResult.needsReview.map((item) => (
                  <div
                    key={`${item.type}-${item.id}`}
                    className="rounded-lg border border-border bg-muted/30 p-3"
                  >
                    <div className="flex items-center gap-2 mb-2">
                      <Badge
                        variant="secondary"
                        className="text-[10px] uppercase"
                      >
                        {item.type}
                      </Badge>
                      <span className="text-sm font-medium text-foreground">
                        {item.name}
                      </span>
                    </div>
                    <div className="space-y-1">
                      {item.candidates.map((c) => (
                        <button
                          key={c.placeId}
                          className="flex w-full items-center gap-2 rounded px-2 py-1.5 text-left text-xs transition-colors hover:bg-accent"
                          onClick={() =>
                            handlePickCandidate(item.type, item.id, c)
                          }
                        >
                          <MapPin className="h-3.5 w-3.5 shrink-0 text-muted-foreground" />
                          <span className="flex-1 truncate">
                            {c.name} — {c.formattedAddress}
                          </span>
                          <span className="shrink-0 text-muted-foreground">
                            Select
                          </span>
                        </button>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
          <DialogFooter>
            <Button
              onClick={() =>
                setBatchResult({ open: false, resolved: 0, needsReview: [] })
              }
            >
              {t("common.close")}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
