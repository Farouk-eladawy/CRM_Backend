"use client";

import { useEffect, useState, useCallback } from "react";
import { useRouter } from "next/navigation";
import { ArrowLeft, Loader2 } from "lucide-react";
import { toast } from "sonner";
import { PageHeader } from "@/components/page-header";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent } from "@/components/ui/card";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import api from "@/lib/api";
import { useT } from "@/lib/i18n";
import { usePermission } from "@/hooks/use-permission";

interface VehicleType {
  id: string;
  name: string;
  seatCapacity: number;
}

const COLORS = ["White", "Black", "Silver", "Gray", "Red", "Blue", "Green", "Yellow", "Orange", "Brown", "Beige", "Gold", "Maroon", "Navy", "Burgundy"];

export default function AddVehiclePage() {
  const t = useT();
  const router = useRouter();
  const canPlateNumber = usePermission("vehicles.form.plateNumber");
  const canVehicleType = usePermission("vehicles.form.vehicleType");
  const canColor = usePermission("vehicles.form.color");
  const canBrand = usePermission("vehicles.form.brand");
  const canModel = usePermission("vehicles.form.model");
  const canMakeYear = usePermission("vehicles.form.makeYear");
  const canLuggageCapacity = usePermission("vehicles.form.luggageCapacity");
  const canOwnership = usePermission("vehicles.form.ownership");

  const [types, setTypes] = useState<VehicleType[]>([]);
  const [submitting, setSubmitting] = useState(false);

  // Form state
  const [plateNumber, setPlateNumber] = useState("");
  const [vehicleTypeId, setVehicleTypeId] = useState("");
  const [ownership, setOwnership] = useState("");
  const [color, setColor] = useState("");
  const [carBrand, setCarBrand] = useState("");
  const [carModel, setCarModel] = useState("");
  const [makeYear, setMakeYear] = useState("");
  const [luggageCapacity, setLuggageCapacity] = useState("");

  const fetchTypes = useCallback(async () => {
    try {
      const { data } = await api.get("/vehicles/types");
      setTypes(Array.isArray(data) ? data : []);
    } catch {
      toast.error(t("vehicles.failedLoadTypes"));
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    fetchTypes();
  }, [fetchTypes]);

  const handleCreate = async () => {
    if (!plateNumber.trim()) {
      toast.error(t("vehicles.plateRequired"));
      return;
    }
    if (!vehicleTypeId) {
      toast.error(t("vehicles.typeRequired"));
      return;
    }
    if (!ownership) {
      toast.error(t("vehicles.ownershipRequired"));
      return;
    }

    setSubmitting(true);
    try {
      const payload: Record<string, unknown> = {
        plateNumber: plateNumber.trim(),
        vehicleTypeId,
        ownership,
      };
      if (color) payload.color = color;
      if (carBrand.trim()) payload.carBrand = carBrand.trim();
      if (carModel.trim()) payload.carModel = carModel.trim();
      if (makeYear) payload.makeYear = parseInt(makeYear, 10);
      if (luggageCapacity) payload.luggageCapacity = parseInt(luggageCapacity, 10);
      await api.post("/vehicles", payload);
      toast.success(t("vehicles.vehicleCreated"));
      router.push("/dashboard/vehicles");
    } catch {
      toast.error(t("vehicles.failedCreateVehicle"));
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-4">
        <Button
          variant="ghost"
          size="sm"
          onClick={() => router.push("/dashboard/vehicles")}
          className="gap-1.5 text-muted-foreground hover:text-foreground"
        >
          <ArrowLeft className="h-4 w-4" />
          {t("common.back")}
        </Button>
      </div>

      <PageHeader
        title={t("vehicles.addVehicle")}
        description={t("vehicles.vehiclesDescription")}
      />

      <Card className="border-border bg-card">
        <CardContent className="pt-6 space-y-4">
          {canPlateNumber && (
          <div className="space-y-2">
            <Label htmlFor="plate-number" className="text-muted-foreground">
              {t("vehicles.plateNumber")}
            </Label>
            <Input
              id="plate-number"
              placeholder="e.g. ABC-1234"
              value={plateNumber}
              onChange={(e) => setPlateNumber(e.target.value)}
              className="border-border bg-card text-foreground placeholder:text-muted-foreground"
            />
          </div>
          )}

          {canVehicleType && (
          <div className="space-y-2">
            <Label htmlFor="vehicle-type" className="text-muted-foreground">
              {t("vehicles.type")}
            </Label>
            <Select value={vehicleTypeId} onValueChange={setVehicleTypeId}>
              <SelectTrigger className="border-border bg-card text-foreground">
                <SelectValue placeholder={t("vehicles.selectType")} />
              </SelectTrigger>
              <SelectContent className="border-border bg-popover text-foreground">
                {types.map((type) => (
                  <SelectItem
                    key={type.id}
                    value={type.id}
                    className="focus:bg-accent focus:text-accent-foreground"
                  >
                    {type.name} ({type.seatCapacity} {t("vehicles.seats")})
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          )}

          {canOwnership && (
          <div className="space-y-2">
            <Label htmlFor="ownership" className="text-muted-foreground">
              {t("vehicles.ownership")}
            </Label>
            <Select value={ownership} onValueChange={setOwnership}>
              <SelectTrigger className="border-border bg-card text-foreground">
                <SelectValue placeholder={t("vehicles.selectOwnership")} />
              </SelectTrigger>
              <SelectContent className="border-border bg-popover text-foreground">
                <SelectItem value="OWNED" className="focus:bg-accent focus:text-accent-foreground">
                  {t("vehicles.owned")}
                </SelectItem>
                <SelectItem value="RENTED" className="focus:bg-accent focus:text-accent-foreground">
                  {t("vehicles.rented")}
                </SelectItem>
                <SelectItem value="CONTRACTED" className="focus:bg-accent focus:text-accent-foreground">
                  {t("vehicles.contracted")}
                </SelectItem>
              </SelectContent>
            </Select>
          </div>
          )}

          {canColor && (
          <div className="space-y-2">
            <Label htmlFor="color" className="text-muted-foreground">
              {t("vehicles.color")}
            </Label>
            <Select value={color} onValueChange={setColor}>
              <SelectTrigger className="border-border bg-card text-foreground">
                <SelectValue placeholder={t("vehicles.selectColor")} />
              </SelectTrigger>
              <SelectContent className="border-border bg-popover text-foreground">
                {COLORS.map((c) => (
                  <SelectItem
                    key={c}
                    value={c}
                    className="focus:bg-accent focus:text-accent-foreground"
                  >
                    {c}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          )}

          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            {canBrand && (
            <div className="space-y-2">
              <Label htmlFor="car-brand" className="text-muted-foreground">
                {t("vehicles.carBrand")}
              </Label>
              <Input
                id="car-brand"
                placeholder="e.g. Toyota"
                value={carBrand}
                onChange={(e) => setCarBrand(e.target.value)}
                className="border-border bg-card text-foreground placeholder:text-muted-foreground"
              />
            </div>
            )}
            {canModel && (
            <div className="space-y-2">
              <Label htmlFor="car-model" className="text-muted-foreground">
                {t("vehicles.carModel")}
              </Label>
              <Input
                id="car-model"
                placeholder="e.g. Hiace"
                value={carModel}
                onChange={(e) => setCarModel(e.target.value)}
                className="border-border bg-card text-foreground placeholder:text-muted-foreground"
              />
            </div>
            )}
            {canMakeYear && (
            <div className="space-y-2">
              <Label htmlFor="make-year" className="text-muted-foreground">
                {t("vehicles.makeYear")}
              </Label>
              <Input
                id="make-year"
                type="number"
                min={1900}
                max={2100}
                placeholder="e.g. 2023"
                value={makeYear}
                onChange={(e) => setMakeYear(e.target.value)}
                className="border-border bg-card text-foreground placeholder:text-muted-foreground"
              />
            </div>
            )}
            {canLuggageCapacity && (
            <div className="space-y-2">
              <Label htmlFor="luggage-capacity" className="text-muted-foreground">
                {t("vehicles.luggageCapacity")}
              </Label>
              <Input
                id="luggage-capacity"
                type="number"
                min={0}
                placeholder="e.g. 4"
                value={luggageCapacity}
                onChange={(e) => setLuggageCapacity(e.target.value)}
                className="border-border bg-card text-foreground placeholder:text-muted-foreground"
              />
            </div>
            )}
          </div>

          <div className="flex justify-end gap-3 pt-4 border-t border-border">
            <Button
              variant="ghost"
              onClick={() => router.push("/dashboard/vehicles")}
              className="text-muted-foreground hover:text-foreground"
            >
              {t("common.cancel")}
            </Button>
            <Button
              onClick={handleCreate}
              disabled={submitting}
              className="gap-1.5 bg-primary text-primary-foreground hover:bg-primary/90"
            >
              {submitting && <Loader2 className="h-4 w-4 animate-spin" />}
              {t("common.create")}
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
