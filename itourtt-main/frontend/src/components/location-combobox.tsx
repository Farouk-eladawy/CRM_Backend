"use client";

import { useState, useEffect, useCallback } from "react";
import {
  Check,
  ChevronsUpDown,
  MapPin,
  Plane,
  Building2,
  Plus,
  Loader2,
  Hotel as HotelIcon,
  Globe,
  Map,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
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
  CommandSeparator,
} from "@/components/ui/command";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "@/components/ui/dialog";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Badge } from "@/components/ui/badge";
import { toast } from "sonner";
import api from "@/lib/api";
import { useT } from "@/lib/i18n";
import {
  GooglePlacesAutocomplete,
  type PlaceResult,
} from "@/components/google-places-autocomplete";

interface LocationResult {
  id: string;
  type: "AIRPORT" | "ZONE" | "HOTEL";
  name: string;
  code?: string;
  path: string;
}

interface LocationComboboxProps {
  value: string;
  onChange: (id: string, type: string, name?: string) => void;
  types?: string[];
  placeholder?: string;
  disabled?: boolean;
}

type NewLocationType = "hotel" | "zone";

interface ZoneOption {
  id: string;
  name: string;
  cityName: string;
}

interface CityOption {
  id: string;
  name: string;
  airportName: string;
}

const typeIcons: Record<string, React.ElementType> = {
  AIRPORT: Plane,
  ZONE: MapPin,
  HOTEL: Building2,
};

const typeColors: Record<string, string> = {
  AIRPORT: "bg-blue-500/20 text-blue-600 border-blue-500/30",
  ZONE: "bg-emerald-500/20 text-emerald-600 border-emerald-500/30",
  HOTEL: "bg-amber-500/20 text-amber-600 border-amber-500/30",
};

export function LocationCombobox({
  value,
  onChange,
  types,
  placeholder = "Select location...",
  disabled = false,
}: LocationComboboxProps) {
  const t = useT();
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<LocationResult[]>([]);
  const [selected, setSelected] = useState<LocationResult | null>(null);
  const [loading, setLoading] = useState(false);

  // Add new location modal state
  const [addOpen, setAddOpen] = useState(false);
  const [addType, setAddType] = useState<NewLocationType>("hotel");
  const [addName, setAddName] = useState("");
  const [addParentId, setAddParentId] = useState("");
  const [addSubmitting, setAddSubmitting] = useState(false);
  const [zones, setZones] = useState<ZoneOption[]>([]);
  const [cities, setCities] = useState<CityOption[]>([]);
  const [loadingParents, setLoadingParents] = useState(false);
  const [addPlace, setAddPlace] = useState<PlaceResult | null>(null);

  const searchLocations = useCallback(
    async (q: string) => {
      setLoading(true);
      try {
        const params: Record<string, string> = {};
        if (q) params.q = q;
        if (types?.length) params.types = types.join(",");
        const { data } = await api.get("/locations/search", { params });
        setResults(Array.isArray(data) ? data : data.data || []);
      } catch {
        setResults([]);
      } finally {
        setLoading(false);
      }
    },
    [types]
  );

  // Load initial results when popover opens
  useEffect(() => {
    if (open) {
      searchLocations(query);
    }
  }, [open, searchLocations]); // eslint-disable-line react-hooks/exhaustive-deps

  // Debounced search
  useEffect(() => {
    if (!open) return;
    const timer = setTimeout(() => {
      searchLocations(query);
    }, 300);
    return () => clearTimeout(timer);
  }, [query, open, searchLocations]);

  // Resolve selected value by fetching from API when value changes
  useEffect(() => {
    if (!value) {
      setSelected(null);
      return;
    }
    // If already resolved, skip
    if (selected?.id === value) return;
    // Try to find in current results first
    const found = results.find((r) => r.id === value);
    if (found) {
      setSelected(found);
      return;
    }
    // Fetch by ID from the search endpoint
    api.get("/locations/search", { params: { q: "", types: types?.join(",") || "" } })
      .then(({ data }) => {
        const all: LocationResult[] = Array.isArray(data) ? data : data.data || [];
        const match = all.find((r) => r.id === value);
        if (match) setSelected(match);
      })
      .catch(() => {});
  }, [value]); // eslint-disable-line react-hooks/exhaustive-deps

  // Update selected when results change and we have a value
  useEffect(() => {
    if (value && results.length > 0) {
      const found = results.find((r) => r.id === value);
      if (found) setSelected(found);
    }
  }, [value, results]);

  // Load parent options when add modal opens
  useEffect(() => {
    if (!addOpen) return;
    setLoadingParents(true);
    const loadParents = async () => {
      try {
        const { data } = await api.get("/locations/tree");
        const tree = Array.isArray(data) ? data : data.data ?? data.countries ?? [];
        const zoneList: ZoneOption[] = [];
        const cityList: CityOption[] = [];
        for (const country of tree) {
          for (const airport of country.airports || []) {
            for (const city of airport.cities || []) {
              cityList.push({
                id: city.id,
                name: city.name,
                airportName: airport.name,
              });
              for (const zone of city.zones || []) {
                zoneList.push({
                  id: zone.id,
                  name: zone.name,
                  cityName: city.name,
                });
              }
            }
          }
        }
        setZones(zoneList);
        setCities(cityList);
      } catch {
        toast.error("Failed to load location tree");
      } finally {
        setLoadingParents(false);
      }
    };
    loadParents();
  }, [addOpen]);

  function openAddModal() {
    setOpen(false);
    setAddType("hotel");
    setAddName(query); // Pre-fill with search query
    setAddParentId("");
    setAddPlace(null);
    setAddOpen(true);
  }

  async function handleAddSubmit() {
    if (!addName.trim()) {
      toast.error(t("locations.nameRequired") || "Name is required");
      return;
    }
    if (!addParentId) {
      toast.error(
        addType === "hotel"
          ? t("locationCombobox.selectZone") || "Please select a zone"
          : t("locationCombobox.selectCity") || "Please select a city"
      );
      return;
    }

    setAddSubmitting(true);
    try {
      const endpoint =
        addType === "hotel" ? "/locations/hotels" : "/locations/zones";
      const parentKey = addType === "hotel" ? "zoneId" : "cityId";
      const payload: Record<string, any> = {
        name: addName.trim(),
        [parentKey]: addParentId,
      };
      if (addPlace) {
        payload.latitude = addPlace.lat;
        payload.longitude = addPlace.lng;
        payload.placeId = addPlace.placeId;
      }
      const { data } = await api.post(endpoint, payload);

      const created = data.data || data;
      const locType = addType === "hotel" ? "HOTEL" : "ZONE";

      toast.success(
        `${addType === "hotel" ? t("locations.hotel") : t("locations.zone")} ${t("locations.createdSuccess") || "created successfully"}`
      );

      // Select the newly created location
      const newLoc: LocationResult = {
        id: created.id,
        type: locType,
        name: created.name,
        path: "",
      };
      setSelected(newLoc);
      onChange(created.id, locType, created.name);
      setAddOpen(false);

      // Refresh search results
      searchLocations("");
    } catch (err: unknown) {
      const message =
        (err as { response?: { data?: { message?: string } } })?.response?.data
          ?.message || "Failed to create location";
      toast.error(message);
    } finally {
      setAddSubmitting(false);
    }
  }

  return (
    <>
      <Popover open={open} onOpenChange={setOpen}>
        <PopoverTrigger asChild>
          <Button
            variant="outline"
            role="combobox"
            aria-expanded={open}
            disabled={disabled}
            className={cn(
              "w-full justify-between border-border bg-card text-foreground font-normal",
              !selected && "text-muted-foreground"
            )}
          >
            {selected ? (
              <span className="flex items-center gap-2 truncate">
                <Badge
                  variant="outline"
                  className={cn(
                    "text-[10px] px-1 py-0",
                    typeColors[selected.type]
                  )}
                >
                  {selected.type}
                </Badge>
                <span className="truncate">{selected.name}</span>
              </span>
            ) : (
              placeholder
            )}
            <ChevronsUpDown className="ml-2 h-4 w-4 shrink-0 opacity-50" />
          </Button>
        </PopoverTrigger>
        <PopoverContent
          className="w-[350px] p-0 border-border bg-popover"
          align="start"
        >
          <Command shouldFilter={false}>
            <CommandInput
              placeholder={t("locationCombobox.searchPlaceholder") || "Search locations..."}
              value={query}
              onValueChange={setQuery}
            />
            <CommandList>
              <CommandEmpty>
                {loading
                  ? t("common.loading") || "Searching..."
                  : t("locationCombobox.noResults") || "No locations found."}
              </CommandEmpty>
              <CommandGroup>
                {results.map((loc) => {
                  const Icon = typeIcons[loc.type] || MapPin;
                  return (
                    <CommandItem
                      key={`${loc.type}-${loc.id}`}
                      value={`${loc.type}-${loc.id}`}
                      onSelect={() => {
                        setSelected(loc);
                        onChange(loc.id, loc.type, loc.name);
                        setOpen(false);
                      }}
                    >
                      <Check
                        className={cn(
                          "mr-2 h-4 w-4",
                          value === loc.id ? "opacity-100" : "opacity-0"
                        )}
                      />
                      <Icon className="mr-2 h-4 w-4 shrink-0 text-muted-foreground" />
                      <div className="flex flex-col min-w-0">
                        <span className="flex items-center gap-2">
                          <span className="truncate font-medium">
                            {loc.name}
                            {loc.code && (
                              <span className="ml-1 text-muted-foreground">
                                ({loc.code})
                              </span>
                            )}
                          </span>
                          <Badge
                            variant="outline"
                            className={cn(
                              "text-[10px] px-1 py-0 shrink-0",
                              typeColors[loc.type]
                            )}
                          >
                            {loc.type}
                          </Badge>
                        </span>
                        <span className="text-xs text-muted-foreground truncate">
                          {loc.path}
                        </span>
                      </div>
                    </CommandItem>
                  );
                })}
              </CommandGroup>
              <CommandSeparator />
              <CommandGroup>
                <CommandItem
                  onSelect={openAddModal}
                  className="text-primary"
                >
                  <Plus className="mr-2 h-4 w-4" />
                  <span className="font-medium">
                    {t("locationCombobox.addNew") || "Add New Location"}
                  </span>
                </CommandItem>
              </CommandGroup>
            </CommandList>
          </Command>
        </PopoverContent>
      </Popover>

      {/* Add New Location Modal */}
      <Dialog open={addOpen} onOpenChange={setAddOpen}>
        <DialogContent className="border-border bg-popover text-foreground sm:max-w-md">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <Plus className="h-5 w-5" />
              {t("locationCombobox.addNewTitle") || "Add New Location"}
            </DialogTitle>
          </DialogHeader>

          <div className="space-y-4 py-2">
            {/* Location Type */}
            <div className="space-y-2">
              <Label className="text-muted-foreground">
                {t("locationCombobox.locationType") || "Location Type"}
              </Label>
              <Select
                value={addType}
                onValueChange={(v) => {
                  setAddType(v as NewLocationType);
                  setAddParentId("");
                }}
              >
                <SelectTrigger className="border-border bg-card text-foreground">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="hotel">
                    <span className="flex items-center gap-2">
                      <HotelIcon className="h-4 w-4" />
                      {t("locations.hotel") || "Hotel"}
                    </span>
                  </SelectItem>
                  <SelectItem value="zone">
                    <span className="flex items-center gap-2">
                      <MapPin className="h-4 w-4" />
                      {t("locations.zone") || "Zone"}
                    </span>
                  </SelectItem>
                </SelectContent>
              </Select>
            </div>

            {/* Name */}
            <div className="space-y-2">
              <Label className="text-muted-foreground">
                {t("common.name") || "Name"}
              </Label>
              <Input
                placeholder={
                  addType === "hotel"
                    ? t("locationCombobox.hotelNamePlaceholder") || "e.g. Hilton Hurghada Resort"
                    : t("locationCombobox.zoneNamePlaceholder") || "e.g. Sahl Hasheesh"
                }
                value={addName}
                onChange={(e) => setAddName(e.target.value)}
                className="border-border bg-card text-foreground placeholder:text-muted-foreground"
                onKeyDown={(e) => {
                  if (e.key === "Enter") handleAddSubmit();
                }}
              />
            </div>

            {/* Parent: Zone (for hotels) or City (for zones) */}
            <div className="space-y-2">
              <Label className="text-muted-foreground">
                {addType === "hotel"
                  ? t("locations.zone") || "Zone"
                  : t("locations.city") || "City"}
              </Label>
              {loadingParents ? (
                <div className="flex items-center gap-2 py-2 text-sm text-muted-foreground">
                  <Loader2 className="h-4 w-4 animate-spin" />
                  {t("common.loading") || "Loading..."}
                </div>
              ) : (
                <Select value={addParentId} onValueChange={setAddParentId}>
                  <SelectTrigger className="border-border bg-card text-foreground">
                    <SelectValue
                      placeholder={
                        addType === "hotel"
                          ? t("locationCombobox.selectZone") || "Select zone..."
                          : t("locationCombobox.selectCity") || "Select city..."
                      }
                    />
                  </SelectTrigger>
                  <SelectContent>
                    {addType === "hotel"
                      ? zones.map((z) => (
                          <SelectItem key={z.id} value={z.id}>
                            <span className="flex items-center gap-2">
                              <MapPin className="h-3.5 w-3.5 text-muted-foreground" />
                              {z.name}
                              <span className="text-xs text-muted-foreground">
                                ({z.cityName})
                              </span>
                            </span>
                          </SelectItem>
                        ))
                      : cities.map((c) => (
                          <SelectItem key={c.id} value={c.id}>
                            <span className="flex items-center gap-2">
                              <Map className="h-3.5 w-3.5 text-muted-foreground" />
                              {c.name}
                              <span className="text-xs text-muted-foreground">
                                ({c.airportName})
                              </span>
                            </span>
                          </SelectItem>
                        ))}
                  </SelectContent>
                </Select>
              )}
            </div>

            {/* Google Places for coordinates */}
            <div className="space-y-2">
              <Label className="text-muted-foreground">
                Location on Google Maps
                <span className="ml-1 text-xs text-muted-foreground/60">(optional)</span>
              </Label>
              <GooglePlacesAutocomplete
                value={addPlace}
                onChange={(place) => {
                  setAddPlace(place);
                  if (place && !addName.trim()) {
                    setAddName(place.name);
                  }
                }}
                type={addType}
                placeholder={`Search for ${addType} on Google Maps...`}
              />
              {addPlace && (
                <p className="text-xs text-muted-foreground">
                  {addPlace.lat.toFixed(5)}, {addPlace.lng.toFixed(5)}
                </p>
              )}
            </div>
          </div>

          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => setAddOpen(false)}
              className="border-border text-muted-foreground hover:text-foreground"
            >
              {t("common.cancel") || "Cancel"}
            </Button>
            <Button
              onClick={handleAddSubmit}
              disabled={addSubmitting}
              className="gap-1.5"
            >
              {addSubmitting && <Loader2 className="h-4 w-4 animate-spin" />}
              {t("common.create") || "Create"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
}
