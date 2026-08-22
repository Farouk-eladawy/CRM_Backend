"use client";

import { useState, useCallback, useRef, useEffect, Fragment } from "react";
import {
  Plus,
  Save,
  Trash2,
  ChevronRight,
  Download,
  Upload,
  Loader2,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
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
import { LocationCombobox } from "@/components/location-combobox";
import { usePermission } from "@/hooks/use-permission";
import { toast } from "sonner";
import { SERVICE_TYPE_DROPDOWN_OPTIONS, useServiceTypeLabel } from "@/lib/service-types";

// ─── Types ─────────────────────────────────────

export interface PriceGridVehicleType {
  id: string;
  name: string;
  seatCapacity: number;
}

export interface PriceGridItem {
  id?: string;
  serviceType: string;
  fromZoneId: string;
  toZoneId: string;
  vehicleTypeId: string;
  transferPrice?: number;
  price?: number; // alias for supplier compatibility
  driverTip: number;
  fromZone?: { id: string; name: string };
  toZone?: { id: string; name: string };
  vehicleType?: PriceGridVehicleType;
}

interface RouteRow {
  key: string;
  serviceType: string;
  fromZoneId: string;
  toZoneId: string;
  fromZoneName: string;
  toZoneName: string;
  prices: Record<
    string,
    { price: number; driverTip: number; id?: string; dirty?: boolean }
  >;
  isNew?: boolean;
}

export interface PriceListGridProps {
  items: PriceGridItem[];
  vehicleTypes: PriceGridVehicleType[];
  priceFieldName?: "transferPrice" | "price";
  onSave: (
    items: {
      serviceType: string;
      fromZoneId: string;
      toZoneId: string;
      vehicleTypeId: string;
      price: number;
      driverTip: number;
    }[]
  ) => Promise<void>;
  onDeleteRoute: (itemIds: string[]) => Promise<void>;
  onDownloadTemplate?: () => void;
  onImport?: (file: File) => Promise<void>;
  onRefresh: () => Promise<void>;
}

// ─── Constants ─────────────────────────────────



// ─── Component ─────────────────────────────────

export function PriceListGrid({
  items,
  vehicleTypes,
  priceFieldName = "transferPrice",
  onSave,
  onDeleteRoute,
  onDownloadTemplate,
  onImport,
  onRefresh,
}: PriceListGridProps) {
  const getServiceTypeLabel = useServiceTypeLabel();

  // Permission checks
  const canAddRoute = usePermission("customers.detail.priceList.addRoute");
  const canEditPrice = usePermission("customers.detail.priceList.editPrice");
  const canDeleteRoute = usePermission("customers.detail.priceList.deleteRoute");
  const canImport = usePermission("customers.detail.priceList.import");
  const canDownloadTemplate = usePermission("customers.detail.priceList.downloadTemplate");
  const canSaveAll = usePermission("customers.detail.priceList.saveAll");

  const [routes, setRoutes] = useState<RouteRow[]>([]);
  const [saving, setSaving] = useState(false);
  const [importing, setImporting] = useState(false);
  const [deletingRoute, setDeletingRoute] = useState<string | null>(null);
  const [newServiceType, setNewServiceType] = useState("ARR");
  const [newFromZone, setNewFromZone] = useState("");
  const [newToZone, setNewToZone] = useState("");
  const [newFromZoneName, setNewFromZoneName] = useState("");
  const [newToZoneName, setNewToZoneName] = useState("");
  const [hasDirty, setHasDirty] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Build route rows from items
  const buildRoutes = useCallback(
    (priceItems: PriceGridItem[]): RouteRow[] => {
      const routeMap = new Map<string, RouteRow>();

      priceItems.forEach((item) => {
        const routeKey = `${item.serviceType}-${item.fromZoneId}-${item.toZoneId}`;
        if (!routeMap.has(routeKey)) {
          routeMap.set(routeKey, {
            key: routeKey,
            serviceType: item.serviceType,
            fromZoneId: item.fromZoneId,
            toZoneId: item.toZoneId,
            fromZoneName: item.fromZone?.name || "",
            toZoneName: item.toZone?.name || "",
            prices: {},
          });
        }
        const route = routeMap.get(routeKey)!;
        const priceValue =
          priceFieldName === "price"
            ? Number(item.price) || 0
            : Number(item.transferPrice) || 0;
        route.prices[item.vehicleTypeId] = {
          price: priceValue,
          driverTip: Number(item.driverTip) || 0,
          id: item.id,
        };
      });

      return Array.from(routeMap.values());
    },
    [priceFieldName]
  );

  // Sync routes when items change
  useEffect(() => {
    setRoutes(buildRoutes(items));
    setHasDirty(false);
  }, [items, buildRoutes]);

  // ─── Handlers ──────────────────────────────

  function handlePriceChange(
    routeKey: string,
    vehicleTypeId: string,
    field: "price" | "driverTip",
    value: string
  ) {
    setRoutes((prev) =>
      prev.map((route) => {
        if (route.key !== routeKey) return route;
        const currentPrices = route.prices[vehicleTypeId] || {
          price: 0,
          driverTip: 0,
        };
        return {
          ...route,
          prices: {
            ...route.prices,
            [vehicleTypeId]: {
              ...currentPrices,
              [field]: parseFloat(value) || 0,
              dirty: true,
            },
          },
        };
      })
    );
    setHasDirty(true);
  }

  function addRoute() {
    if (!newFromZone || !newToZone) {
      toast.error("Please select both From and To zones");
      return;
    }
    const routeKey = `${newServiceType}-${newFromZone}-${newToZone}`;
    if (routes.some((r) => r.key === routeKey)) {
      toast.error("This service type + route combination already exists");
      return;
    }
    setRoutes((prev) => [
      ...prev,
      {
        key: routeKey,
        serviceType: newServiceType,
        fromZoneId: newFromZone,
        toZoneId: newToZone,
        fromZoneName: newFromZoneName,
        toZoneName: newToZoneName,
        prices: {},
        isNew: true,
      },
    ]);
    setNewFromZone("");
    setNewToZone("");
    setNewFromZoneName("");
    setNewToZoneName("");
    setHasDirty(true);
  }

  async function removeRoute(routeKey: string) {
    const route = routes.find((r) => r.key === routeKey);
    if (!route) return;

    const itemIds = Object.values(route.prices)
      .map((p) => p.id)
      .filter((id): id is string => !!id);

    if (itemIds.length === 0) {
      // Just remove unsaved route from state
      setRoutes((prev) => prev.filter((r) => r.key !== routeKey));
      return;
    }

    setDeletingRoute(routeKey);
    try {
      await onDeleteRoute(itemIds);
      toast.success("Route prices deleted");
      await onRefresh();
    } catch {
      toast.error("Failed to delete route prices");
    } finally {
      setDeletingRoute(null);
    }
  }

  async function savePriceList() {
    try {
      setSaving(true);
      const saveItems: {
        serviceType: string;
        fromZoneId: string;
        toZoneId: string;
        vehicleTypeId: string;
        price: number;
        driverTip: number;
      }[] = [];

      routes.forEach((route) => {
        vehicleTypes.forEach((vt) => {
          const priceData = route.prices[vt.id];
          if (priceData && (priceData.price > 0 || priceData.driverTip > 0)) {
            saveItems.push({
              serviceType: route.serviceType,
              fromZoneId: route.fromZoneId,
              toZoneId: route.toZoneId,
              vehicleTypeId: vt.id,
              price: priceData.price,
              driverTip: priceData.driverTip,
            });
          }
        });
      });

      await onSave(saveItems);
      toast.success("Price list saved successfully");
      await onRefresh();
      setHasDirty(false);
    } catch {
      toast.error("Failed to save price list");
    } finally {
      setSaving(false);
    }
  }

  async function handleImport(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file || !onImport) return;

    setImporting(true);
    try {
      await onImport(file);
      await onRefresh();
    } catch {
      toast.error("Failed to import price list");
    } finally {
      setImporting(false);
      e.target.value = "";
    }
  }

  // ─── Keyboard navigation ──────────────────

  function handleCellKeyDown(
    e: React.KeyboardEvent<HTMLInputElement>,
    routeIdx: number,
    vtIdx: number,
    subField: "price" | "tip"
  ) {
    if (e.key === "Tab") {
      // Let natural tab behavior work
      return;
    }
    if (e.key === "Enter") {
      e.preventDefault();
      // Move to next row, same column
      const nextRow = document.querySelector(
        `[data-cell="${routeIdx + 1}-${vtIdx}-${subField}"]`
      ) as HTMLInputElement;
      nextRow?.focus();
    }
    if (e.key === "Escape") {
      e.preventDefault();
      (e.target as HTMLInputElement).blur();
    }
  }

  // ─── Render ────────────────────────────────

  return (
    <div className="space-y-4">
      {/* Toolbar */}
      <div className="flex items-center justify-between">
        <h3 className="text-foreground text-lg font-semibold">Price List</h3>
        <div className="flex items-center gap-2">
          {onDownloadTemplate && canDownloadTemplate && (
            <Button
              variant="outline"
              onClick={onDownloadTemplate}
              className="gap-1.5 border-border"
            >
              <Download className="h-4 w-4" />
              Template
            </Button>
          )}
          {onImport && canImport && (
            <label>
              <Button
                variant="outline"
                className="gap-1.5 border-border cursor-pointer"
                disabled={importing}
                asChild
              >
                <span>
                  {importing ? (
                    <Loader2 className="h-4 w-4 animate-spin" />
                  ) : (
                    <Upload className="h-4 w-4" />
                  )}
                  Import
                </span>
              </Button>
              <input
                ref={fileInputRef}
                type="file"
                accept=".xlsx,.xls"
                onChange={handleImport}
                className="hidden"
                disabled={importing}
              />
            </label>
          )}
          {canSaveAll && (
            <Button
              onClick={savePriceList}
              disabled={saving || !hasDirty}
              className="gap-1.5 bg-primary text-primary-foreground hover:bg-primary/90"
            >
              {saving ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <Save className="h-4 w-4" />
              )}
              Save All
            </Button>
          )}
        </div>
      </div>

      {/* Add Route */}
      {canAddRoute && <div className="flex items-end gap-4 rounded-lg border border-border bg-muted/50 p-4">
        <div className="w-52 space-y-2">
          <span className="text-sm text-muted-foreground">Service Type</span>
          <Select value={newServiceType} onValueChange={setNewServiceType}>
            <SelectTrigger className="border-border bg-card text-foreground">
              <SelectValue placeholder="Select type..." />
            </SelectTrigger>
            <SelectContent>
              {SERVICE_TYPE_DROPDOWN_OPTIONS.map((opt) => (
                <SelectItem key={opt.value} value={opt.value}>
                  {opt.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
        <div className="flex-1 space-y-2">
          <span className="text-sm text-muted-foreground">From</span>
          <LocationCombobox
            value={newFromZone}
            onChange={(id, _type, name) => {
              setNewFromZone(id);
              setNewFromZoneName(name || "");
            }}
            types={["ZONE"]}
            placeholder="Select origin zone..."
          />
        </div>
        <ChevronRight className="mb-2 h-5 w-5 text-muted-foreground" />
        <div className="flex-1 space-y-2">
          <span className="text-sm text-muted-foreground">To</span>
          <LocationCombobox
            value={newToZone}
            onChange={(id, _type, name) => {
              setNewToZone(id);
              setNewToZoneName(name || "");
            }}
            types={["ZONE"]}
            placeholder="Select destination zone..."
          />
        </div>
        <Button
          onClick={addRoute}
          variant="outline"
          className="gap-1.5 border-border"
        >
          <Plus className="h-4 w-4" />
          Add Route
        </Button>
      </div>}

      {/* Grid */}
      {routes.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-12 text-center">
          <p className="text-sm text-muted-foreground">
            No price items yet. Add a route above to get started.
          </p>
        </div>
      ) : (
        <div className="overflow-x-auto">
          <Table>
            <TableHeader>
              <TableRow className="border-border bg-muted">
                <TableHead className="text-muted-foreground text-xs min-w-[280px]">
                  Route
                </TableHead>
                {vehicleTypes.map((vt) => (
                  <TableHead
                    key={vt.id}
                    colSpan={2}
                    className="text-center text-muted-foreground text-xs border-l border-border"
                  >
                    {vt.name}
                    <span className="ml-1 text-xs">
                      ({vt.seatCapacity} Pax)
                    </span>
                  </TableHead>
                ))}
                <TableHead className="text-muted-foreground text-xs w-[50px]" />
              </TableRow>
              <TableRow className="border-border bg-muted">
                <TableHead />
                {vehicleTypes.map((vt) => (
                  <Fragment key={vt.id}>
                    <TableHead className="text-xs text-muted-foreground text-center border-l border-border">
                      Price
                    </TableHead>
                    <TableHead className="text-xs text-muted-foreground text-center">
                      Tip
                    </TableHead>
                  </Fragment>
                ))}
                <TableHead />
              </TableRow>
            </TableHeader>
            <TableBody>
              {routes.map((route, routeIdx) => (
                <TableRow
                  key={route.key}
                  className={`border-border ${routeIdx % 2 === 0 ? "bg-gray-100/25 dark:bg-gray-800/25" : "bg-gray-200/50 dark:bg-gray-700/50"}`}
                >
                  <TableCell className="font-medium text-foreground">
                    <div className="flex items-center gap-2">
                      <Badge
                        variant="outline"
                        className="text-xs shrink-0"
                      >
                        {getServiceTypeLabel(route.serviceType)}
                      </Badge>
                      <span>
                        {route.fromZoneName || route.fromZoneId}
                      </span>
                      <ChevronRight className="h-4 w-4 text-muted-foreground" />
                      <span>
                        {route.toZoneName || route.toZoneId}
                      </span>
                      {route.isNew && (
                        <Badge
                          variant="outline"
                          className="text-xs bg-blue-500/20 text-blue-600 border-blue-500/30"
                        >
                          New
                        </Badge>
                      )}
                    </div>
                  </TableCell>
                  {vehicleTypes.map((vt, vtIdx) => {
                    const priceData = route.prices[vt.id] || {
                      price: 0,
                      driverTip: 0,
                    };
                    return (
                      <Fragment key={`${route.key}-${vt.id}`}>
                        <TableCell className="border-l border-border p-1">
                          <input
                            type="number"
                            min="0"
                            step="0.01"
                            value={priceData.price || ""}
                            onChange={(e) =>
                              canEditPrice
                                ? handlePriceChange(
                                    route.key,
                                    vt.id,
                                    "price",
                                    e.target.value
                                  )
                                : undefined
                            }
                            onKeyDown={(e) =>
                              canEditPrice
                                ? handleCellKeyDown(e, routeIdx, vtIdx, "price")
                                : undefined
                            }
                            readOnly={!canEditPrice}
                            data-cell={`${routeIdx}-${vtIdx}-price`}
                            placeholder="0"
                            className={`h-8 w-20 text-center text-sm rounded-md border bg-card text-foreground focus:outline-none focus:ring-1 focus:ring-ring px-2 ${
                              priceData.dirty
                                ? "border-blue-500/50 bg-blue-500/5"
                                : "border-border"
                            } ${!canEditPrice ? "opacity-60 cursor-not-allowed" : ""}`}
                          />
                        </TableCell>
                        <TableCell className="p-1">
                          <input
                            type="number"
                            min="0"
                            step="0.01"
                            value={priceData.driverTip || ""}
                            onChange={(e) =>
                              canEditPrice
                                ? handlePriceChange(
                                    route.key,
                                    vt.id,
                                    "driverTip",
                                    e.target.value
                                  )
                                : undefined
                            }
                            onKeyDown={(e) =>
                              canEditPrice
                                ? handleCellKeyDown(e, routeIdx, vtIdx, "tip")
                                : undefined
                            }
                            readOnly={!canEditPrice}
                            data-cell={`${routeIdx}-${vtIdx}-tip`}
                            placeholder="0"
                            className={`h-8 w-20 text-center text-sm rounded-md border bg-card text-foreground focus:outline-none focus:ring-1 focus:ring-ring px-2 ${
                              priceData.dirty
                                ? "border-blue-500/50 bg-blue-500/5"
                                : "border-border"
                            } ${!canEditPrice ? "opacity-60 cursor-not-allowed" : ""}`}
                          />
                        </TableCell>
                      </Fragment>
                    );
                  })}
                  <TableCell className="p-1">
                    {canDeleteRoute && (
                      <Button
                        variant="ghost"
                        size="icon"
                        onClick={() => removeRoute(route.key)}
                        disabled={deletingRoute === route.key}
                        className="h-8 w-8 text-destructive hover:text-destructive hover:bg-destructive/10"
                      >
                        {deletingRoute === route.key ? (
                          <Loader2 className="h-4 w-4 animate-spin" />
                        ) : (
                          <Trash2 className="h-4 w-4" />
                        )}
                      </Button>
                    )}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      )}
    </div>
  );
}
