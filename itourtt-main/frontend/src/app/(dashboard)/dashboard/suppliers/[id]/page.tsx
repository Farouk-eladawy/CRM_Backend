"use client";

import { useEffect, useState, useCallback, use } from "react";
import { useRouter } from "next/navigation";
import { ArrowLeft, Loader2 } from "lucide-react";
import { PageHeader } from "@/components/page-header";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import api from "@/lib/api";
import { toast } from "sonner";
import { useT } from "@/lib/i18n";

interface Supplier {
  id: string;
  supplierType: "COMPANY" | "INDIVIDUAL";
  legalName: string;
  tradeName: string;
  taxId: string;
  address: string;
  city: string;
  country: string;
  phone: string;
  email: string;
  mobileNumber: string;
  nationalIdImage: string | null;
  userId?: string | null;
  user?: { id: string; email: string; name: string; role: string; isActive: boolean } | null;
  isActive: boolean;
}

export default function SupplierDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const resolvedParams = use(params);
  const router = useRouter();
  const t = useT();
  const [supplier, setSupplier] = useState<Supplier | null>(null);
  const [loading, setLoading] = useState(true);

  const fetchSupplier = useCallback(async () => {
    try {
      setLoading(true);
      const res = await api.get(`/suppliers/${resolvedParams.id}`);
      const data = res.data?.data || res.data;
      setSupplier(data);
    } catch {
      toast.error("Failed to load supplier");
      router.push("/dashboard/suppliers");
    } finally {
      setLoading(false);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [resolvedParams.id, router]);

  useEffect(() => {
    fetchSupplier();
  }, [fetchSupplier]);

  if (loading) {
    return (
      <div className="flex items-center justify-center py-20">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
      </div>
    );
  }

  if (!supplier) return null;

  const isIndividual = supplier.supplierType === "INDIVIDUAL";

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-4">
        <Button
          variant="ghost"
          size="icon"
          onClick={() => router.push("/dashboard/suppliers")}
          className="text-muted-foreground hover:text-foreground"
        >
          <ArrowLeft className="h-5 w-5" />
        </Button>
        <PageHeader
          title={supplier.tradeName || supplier.legalName}
          description={supplier.tradeName ? supplier.legalName : undefined}
        />
        <Badge variant="outline" className="ml-2 text-xs">
          {isIndividual ? "Individual" : "Company"}
        </Badge>
      </div>

      <Card className="border-border bg-card">
        <CardHeader>
          <CardTitle className="text-foreground">
            {t("suppliers.supplierInfo")}
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 gap-4 text-sm md:grid-cols-3">
            <div>
              <span className="text-muted-foreground">{isIndividual ? "Name" : t("agents.legalName")}</span>
              <p className="font-medium text-foreground">{supplier.legalName}</p>
            </div>
            {!isIndividual && supplier.tradeName && (
              <div>
                <span className="text-muted-foreground">{t("agents.tradeName")}</span>
                <p className="font-medium text-foreground">{supplier.tradeName}</p>
              </div>
            )}
            {!isIndividual && supplier.taxId && (
              <div>
                <span className="text-muted-foreground">{t("agents.taxId")}</span>
                <p className="font-medium text-foreground">{supplier.taxId}</p>
              </div>
            )}
            {supplier.phone && (
              <div>
                <span className="text-muted-foreground">{t("agents.phone")}</span>
                <p className="font-medium text-foreground">{supplier.phone}</p>
              </div>
            )}
            {isIndividual && supplier.mobileNumber && (
              <div>
                <span className="text-muted-foreground">Mobile</span>
                <p className="font-medium text-foreground">{supplier.mobileNumber}</p>
              </div>
            )}
            {supplier.email && (
              <div>
                <span className="text-muted-foreground">{t("common.email")}</span>
                <p className="font-medium text-foreground">{supplier.email}</p>
              </div>
            )}
            {!isIndividual && supplier.city && (
              <div>
                <span className="text-muted-foreground">{t("locations.city")}</span>
                <p className="font-medium text-foreground">{supplier.city}</p>
              </div>
            )}
            {!isIndividual && supplier.country && (
              <div>
                <span className="text-muted-foreground">{t("locations.country")}</span>
                <p className="font-medium text-foreground">{supplier.country}</p>
              </div>
            )}
            {!isIndividual && supplier.address && (
              <div className="col-span-2">
                <span className="text-muted-foreground">{t("agents.address")}</span>
                <p className="font-medium text-foreground">{supplier.address}</p>
              </div>
            )}
            <div>
              <span className="text-muted-foreground">{t("common.status")}</span>
              <p className="font-medium">
                {supplier.isActive ? (
                  <Badge className="bg-emerald-500/20 text-emerald-600 border-emerald-500/30">
                    {t("common.active")}
                  </Badge>
                ) : (
                  <Badge className="bg-red-500/20 text-red-600 border-red-500/30">
                    {t("common.inactive")}
                  </Badge>
                )}
              </p>
            </div>
            {supplier.user && (
              <div>
                <span className="text-muted-foreground">Account</span>
                <p className="font-medium text-foreground">{supplier.user.email}</p>
              </div>
            )}
            {isIndividual && supplier.nationalIdImage && (
              <div className="col-span-2">
                <span className="text-muted-foreground">National ID</span>
                <p className="mt-1">
                  <a
                    href={`${process.env.NEXT_PUBLIC_API_URL ?? ""}/${supplier.nationalIdImage}`}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-primary hover:underline text-sm"
                  >
                    View uploaded document
                  </a>
                </p>
              </div>
            )}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
