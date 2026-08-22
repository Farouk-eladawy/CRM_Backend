"use client";

import { useState, useEffect } from "react";
import { Loader2, Building2, Car, Mail, Phone, MapPin } from "lucide-react";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import api from "@/lib/api";
import { useT } from "@/lib/i18n";

interface SupplierProfile {
  id: string;
  legalName: string;
  tradeName: string | null;
  taxId: string | null;
  address: string | null;
  city: string | null;
  country: string | null;
  phone: string | null;
  email: string | null;
  vehicles: {
    id: string;
    plateNumber: string;
    ownership: string;
    vehicleType?: { name: string; seatCapacity: number };
  }[];
}

export default function SupplierProfilePage() {
  const t = useT();
  const [profile, setProfile] = useState<SupplierProfile | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function load() {
      try {
        const { data } = await api.get("/supplier-portal/profile");
        setProfile(data.data);
      } catch {
        // ignore
      } finally {
        setLoading(false);
      }
    }
    load();
  }, []);

  if (loading) {
    return (
      <div className="flex items-center justify-center py-20">
        <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
      </div>
    );
  }

  if (!profile) {
    return (
      <div className="py-20 text-center text-sm text-muted-foreground">
        Could not load profile.
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Company Info */}
      <Card className="p-4 space-y-3">
        <div className="flex items-center gap-2">
          <Building2 className="h-5 w-5 text-primary" />
          <h2 className="font-semibold text-foreground">
            {t("supplierPortal.companyInfo")}
          </h2>
        </div>
        <div className="space-y-2 text-sm">
          <p className="font-medium text-foreground">{profile.legalName}</p>
          {profile.tradeName && (
            <p className="text-muted-foreground">{profile.tradeName}</p>
          )}
          {profile.email && (
            <div className="flex items-center gap-2 text-muted-foreground">
              <Mail className="h-3.5 w-3.5" />
              <span>{profile.email}</span>
            </div>
          )}
          {profile.phone && (
            <div className="flex items-center gap-2 text-muted-foreground">
              <Phone className="h-3.5 w-3.5" />
              <span>{profile.phone}</span>
            </div>
          )}
          {(profile.city || profile.country) && (
            <div className="flex items-center gap-2 text-muted-foreground">
              <MapPin className="h-3.5 w-3.5" />
              <span>{[profile.city, profile.country].filter(Boolean).join(", ")}</span>
            </div>
          )}
          {profile.taxId && (
            <p className="text-xs text-muted-foreground">
              Tax ID: {profile.taxId}
            </p>
          )}
        </div>
      </Card>

      {/* Linked Vehicles */}
      <Card className="p-4 space-y-3">
        <div className="flex items-center gap-2">
          <Car className="h-5 w-5 text-primary" />
          <h2 className="font-semibold text-foreground">
            {t("supplierPortal.vehicles")}
          </h2>
          <Badge variant="secondary" className="ml-auto text-xs">
            {profile.vehicles.length}
          </Badge>
        </div>
        {profile.vehicles.length === 0 ? (
          <p className="text-sm text-muted-foreground">No vehicles linked.</p>
        ) : (
          <div className="space-y-2">
            {profile.vehicles.map((v) => (
              <div
                key={v.id}
                className="flex items-center justify-between rounded-md border border-border p-3"
              >
                <div>
                  <p className="text-sm font-medium text-foreground">
                    {v.plateNumber}
                  </p>
                  {v.vehicleType && (
                    <p className="text-xs text-muted-foreground">
                      {v.vehicleType.name} ({v.vehicleType.seatCapacity} seats)
                    </p>
                  )}
                </div>
                <Badge variant="outline" className="text-xs">
                  {v.ownership}
                </Badge>
              </div>
            ))}
          </div>
        )}
      </Card>
    </div>
  );
}
