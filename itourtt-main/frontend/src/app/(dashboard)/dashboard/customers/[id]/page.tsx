"use client";

import { useEffect, useState, useCallback, use } from "react";
import { useRouter } from "next/navigation";
import {
  ArrowLeft,
  Loader2,
} from "lucide-react";
import { PageHeader } from "@/components/page-header";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { PriceListGrid, PriceGridItem, PriceGridVehicleType } from "@/components/price-list-grid";
import { ImportTemplateManager } from "@/components/import-template-manager";
import api from "@/lib/api";
import { toast } from "sonner";
import { useLocaleId } from "@/lib/i18n";

interface Customer {
  id: string;
  legalName: string;
  tradeName: string | null;
  taxId: string | null;
  address: string | null;
  city: string | null;
  country: string | null;
  phone: string | null;
  email: string | null;
  contactPerson: string | null;
  currency: string;
  creditLimit: number | null;
  creditDays: number | null;
  isActive: boolean;
}

interface VehicleType {
  id: string;
  name: string;
  seatCapacity: number;
}

export default function CustomerDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const resolvedParams = use(params);
  const router = useRouter();
  const locale = useLocaleId();
  const [customer, setCustomer] = useState<Customer | null>(null);
  const [vehicleTypes, setVehicleTypes] = useState<VehicleType[]>([]);
  const [loading, setLoading] = useState(true);
  const [priceItems, setPriceItems] = useState<PriceGridItem[]>([]);

  const fetchCustomer = useCallback(async () => {
    try {
      const res = await api.get<{ data: Customer }>(
        `/customers/${resolvedParams.id}`
      );
      setCustomer(res.data.data);
    } catch {
      toast.error("Failed to load customer");
      router.push("/dashboard/customers");
    }
  }, [resolvedParams.id, router]);

  const fetchVehicleTypes = useCallback(async () => {
    try {
      const res = await api.get<VehicleType[]>("/vehicles/types");
      const types = Array.isArray(res.data) ? res.data : [];
      types.sort((a, b) => a.seatCapacity - b.seatCapacity);
      setVehicleTypes(types);
    } catch {
      toast.error("Failed to load vehicle types");
    }
  }, []);

  const fetchPriceList = useCallback(async () => {
    try {
      const res = await api.get<{ data: PriceGridItem[] }>(
        `/customers/${resolvedParams.id}/price-list`
      );
      setPriceItems(res.data.data || []);
    } catch {
      toast.error("Failed to load price list");
    }
  }, [resolvedParams.id]);

  useEffect(() => {
    async function loadData() {
      setLoading(true);
      await Promise.all([fetchCustomer(), fetchVehicleTypes(), fetchPriceList()]);
      setLoading(false);
    }
    loadData();
  }, [fetchCustomer, fetchVehicleTypes, fetchPriceList]);

  async function handleSavePriceList(
    items: {
      serviceType: string;
      fromZoneId: string;
      toZoneId: string;
      vehicleTypeId: string;
      price: number;
      driverTip: number;
    }[]
  ) {
    // Map price → transferPrice for the customer API
    const mapped = items.map((item) => ({
      serviceType: item.serviceType,
      fromZoneId: item.fromZoneId,
      toZoneId: item.toZoneId,
      vehicleTypeId: item.vehicleTypeId,
      transferPrice: item.price,
      driverTip: item.driverTip,
    }));
    await api.post(`/customers/${resolvedParams.id}/price-list`, { items: mapped });
  }

  async function handleDeletePriceRoute(itemIds: string[]) {
    await Promise.all(
      itemIds.map((id) =>
        api.delete(`/customers/${resolvedParams.id}/price-list/${id}`)
      )
    );
  }

  async function handleDownloadTemplate() {
    try {
      const response = await api.get("/customers/price-list/template", {
        responseType: "blob",
      });
      const blob = new Blob([response.data], {
        type: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
      });
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = "price-list-template.xlsx";
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(url);
      toast.success("Template downloaded");
    } catch {
      toast.error("Failed to download template");
    }
  }

  async function handleImport(file: File) {
    const formData = new FormData();
    formData.append("file", file);

    const res = await api.post<{ data: { imported: number; errors: string[] }; message: string }>(
      `/customers/${resolvedParams.id}/price-list/import`,
      formData,
      { headers: { "Content-Type": "multipart/form-data" } }
    );

    const { imported, errors } = res.data.data;
    if (errors.length > 0) {
      toast.warning(`Imported ${imported} items with ${errors.length} errors`);
      errors.slice(0, 5).forEach((err) => toast.error(err));
    } else {
      toast.success(`Successfully imported ${imported} price items`);
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center py-20">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
      </div>
    );
  }

  if (!customer) {
    return null;
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-4">
        <Button
          variant="ghost"
          size="icon"
          onClick={() => router.push("/dashboard/customers")}
          className="text-muted-foreground hover:text-foreground"
        >
          <ArrowLeft className="h-5 w-5" />
        </Button>
        <PageHeader
          title={customer.tradeName || customer.legalName}
          description={customer.tradeName ? customer.legalName : undefined}
        />
      </div>

      <Tabs defaultValue="info" className="space-y-4">
        <TabsList className="bg-muted">
          <TabsTrigger value="info">Overview</TabsTrigger>
          <TabsTrigger value="prices">Price List</TabsTrigger>
          <TabsTrigger value="templates">Import Templates</TabsTrigger>
        </TabsList>

        <TabsContent value="info" className="space-y-4">
          <Card className="border-border bg-card">
            <CardHeader>
              <CardTitle className="text-foreground">
                Customer Information
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-2 gap-4 text-sm md:grid-cols-3">
                <div>
                  <span className="text-muted-foreground">Legal Name</span>
                  <p className="font-medium text-foreground">
                    {customer.legalName}
                  </p>
                </div>
                {customer.tradeName && (
                  <div>
                    <span className="text-muted-foreground">Trade Name</span>
                    <p className="font-medium text-foreground">
                      {customer.tradeName}
                    </p>
                  </div>
                )}
                {customer.taxId && (
                  <div>
                    <span className="text-muted-foreground">Tax ID</span>
                    <p className="font-medium text-foreground">
                      {customer.taxId}
                    </p>
                  </div>
                )}
                {customer.contactPerson && (
                  <div>
                    <span className="text-muted-foreground">Contact Person</span>
                    <p className="font-medium text-foreground">
                      {customer.contactPerson}
                    </p>
                  </div>
                )}
                {customer.phone && (
                  <div>
                    <span className="text-muted-foreground">Phone</span>
                    <p className="font-medium text-foreground">
                      {customer.phone}
                    </p>
                  </div>
                )}
                {customer.email && (
                  <div>
                    <span className="text-muted-foreground">Email</span>
                    <p className="font-medium text-foreground">
                      {customer.email}
                    </p>
                  </div>
                )}
                <div>
                  <span className="text-muted-foreground">Currency</span>
                  <p className="font-medium text-foreground">
                    {customer.currency}
                  </p>
                </div>
                {customer.creditLimit != null && (
                  <div>
                    <span className="text-muted-foreground">Credit Limit</span>
                    <p className="font-medium text-foreground">
                      {customer.creditLimit.toLocaleString(locale)} {customer.currency}
                    </p>
                  </div>
                )}
                {customer.creditDays != null && (
                  <div>
                    <span className="text-muted-foreground">Credit Days</span>
                    <p className="font-medium text-foreground">
                      {customer.creditDays} days
                    </p>
                  </div>
                )}
                <div>
                  <span className="text-muted-foreground">Status</span>
                  <p className="font-medium">
                    {customer.isActive ? (
                      <Badge className="bg-emerald-500/20 text-emerald-600 border-emerald-500/30">
                        Active
                      </Badge>
                    ) : (
                      <Badge className="bg-red-500/20 text-red-600 border-red-500/30">
                        Inactive
                      </Badge>
                    )}
                  </p>
                </div>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="prices" className="space-y-4">
          <PriceListGrid
            items={priceItems}
            vehicleTypes={vehicleTypes as PriceGridVehicleType[]}
            priceFieldName="transferPrice"
            onSave={handleSavePriceList}
            onDeleteRoute={handleDeletePriceRoute}
            onDownloadTemplate={handleDownloadTemplate}
            onImport={handleImport}
            onRefresh={fetchPriceList}
          />
        </TabsContent>

        <TabsContent value="templates" className="space-y-4">
          <ImportTemplateManager customerId={resolvedParams.id} />
        </TabsContent>
      </Tabs>
    </div>
  );
}
