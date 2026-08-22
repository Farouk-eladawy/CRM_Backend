"use client";

import { useEffect, useState, useCallback, use } from "react";
import { useRouter } from "next/navigation";
import { ArrowLeft, Loader2 } from "lucide-react";
import { PageHeader } from "@/components/page-header";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  PriceListGrid,
  PriceGridItem,
  PriceGridVehicleType,
} from "@/components/price-list-grid";
import api from "@/lib/api";
import { toast } from "sonner";
import { useT } from "@/lib/i18n";

interface Agent {
  id: string;
  legalName: string;
  tradeName: string | null;
  taxId: string | null;
  address: string | null;
  city: string | null;
  country: string | null;
  phone: string | null;
  email: string | null;
  currency: string;
  isActive: boolean;
  creditTerms?: { creditLimit: number; creditDays: number } | null;
  invoiceCycle?: { cycleType: string; dayOfWeek: number | null; dayOfMonth: number | null } | null;
}

interface VehicleType {
  id: string;
  name: string;
  seatCapacity: number;
}

export default function AgentDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const resolvedParams = use(params);
  const router = useRouter();
  const t = useT();
  const [agent, setAgent] = useState<Agent | null>(null);
  const [loading, setLoading] = useState(true);

  // Price list
  const [priceItems, setPriceItems] = useState<PriceGridItem[]>([]);
  const [priceLoading, setPriceLoading] = useState(false);
  const [vehicleTypes, setVehicleTypes] = useState<VehicleType[]>([]);

  // ─── Fetch ──────────────────────────────────

  const fetchAgent = useCallback(async () => {
    try {
      const res = await api.get(`/agents/${resolvedParams.id}`);
      const data = res.data?.data || res.data;
      setAgent(data);
    } catch {
      toast.error("Failed to load agent");
      router.push("/dashboard/agents");
    }
  }, [resolvedParams.id, router]);

  const fetchVehicleTypes = useCallback(async () => {
    try {
      const res = await api.get<VehicleType[]>("/vehicles/types");
      const types = Array.isArray(res.data) ? res.data : [];
      types.sort((a, b) => a.seatCapacity - b.seatCapacity);
      setVehicleTypes(types);
    } catch {
      // silent
    }
  }, []);

  const fetchPriceList = useCallback(async () => {
    setPriceLoading(true);
    try {
      const res = await api.get(`/agents/${resolvedParams.id}/price-list`);
      const data = res.data?.data || [];
      setPriceItems(data);
    } catch {
      toast.error("Failed to load price list");
    } finally {
      setPriceLoading(false);
    }
  }, [resolvedParams.id]);

  useEffect(() => {
    async function loadAll() {
      setLoading(true);
      try {
        await Promise.all([fetchAgent(), fetchVehicleTypes(), fetchPriceList()]);
      } finally {
        setLoading(false);
      }
    }
    loadAll();
  }, [fetchAgent, fetchVehicleTypes, fetchPriceList]);

  // ─── Price list handlers ────────────────────

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
    await api.post(`/agents/${resolvedParams.id}/price-list`, { items });
  }

  async function handleDeletePriceRoute(itemIds: string[]) {
    await Promise.all(
      itemIds.map((id) =>
        api.delete(`/agents/${resolvedParams.id}/price-list/${id}`)
      )
    );
  }

  // ─── Render ─────────────────────────────────

  if (loading) {
    return (
      <div className="flex items-center justify-center py-20">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
      </div>
    );
  }

  if (!agent) return null;

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-4">
        <Button
          variant="ghost"
          size="icon"
          onClick={() => router.push("/dashboard/agents")}
          className="text-muted-foreground hover:text-foreground"
        >
          <ArrowLeft className="h-5 w-5" />
        </Button>
        <PageHeader
          title={agent.tradeName || agent.legalName}
          description={agent.tradeName ? agent.legalName : undefined}
        />
      </div>

      <Tabs defaultValue="info" className="space-y-4">
        <TabsList className="bg-muted">
          <TabsTrigger value="info">{t("agents.tabOverview")}</TabsTrigger>
          <TabsTrigger value="prices">{t("agents.tabPriceList")}</TabsTrigger>
        </TabsList>

        {/* ── Overview Tab ── */}
        <TabsContent value="info" className="space-y-4">
          <Card className="border-border bg-card">
            <CardHeader>
              <CardTitle className="text-foreground">
                {t("agents.agentInfo")}
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-2 gap-4 text-sm md:grid-cols-3">
                <div>
                  <span className="text-muted-foreground">
                    {t("agents.legalName")}
                  </span>
                  <p className="font-medium text-foreground">
                    {agent.legalName}
                  </p>
                </div>
                {agent.tradeName && (
                  <div>
                    <span className="text-muted-foreground">
                      {t("agents.tradeName")}
                    </span>
                    <p className="font-medium text-foreground">
                      {agent.tradeName}
                    </p>
                  </div>
                )}
                {agent.taxId && (
                  <div>
                    <span className="text-muted-foreground">
                      {t("agents.taxId")}
                    </span>
                    <p className="font-medium text-foreground">
                      {agent.taxId}
                    </p>
                  </div>
                )}
                {agent.phone && (
                  <div>
                    <span className="text-muted-foreground">
                      {t("agents.phone")}
                    </span>
                    <p className="font-medium text-foreground">{agent.phone}</p>
                  </div>
                )}
                {agent.email && (
                  <div>
                    <span className="text-muted-foreground">
                      {t("common.email")}
                    </span>
                    <p className="font-medium text-foreground">{agent.email}</p>
                  </div>
                )}
                {agent.city && (
                  <div>
                    <span className="text-muted-foreground">
                      {t("locations.city")}
                    </span>
                    <p className="font-medium text-foreground">{agent.city}</p>
                  </div>
                )}
                {agent.country && (
                  <div>
                    <span className="text-muted-foreground">
                      {t("locations.country")}
                    </span>
                    <p className="font-medium text-foreground">
                      {agent.country}
                    </p>
                  </div>
                )}
                <div>
                  <span className="text-muted-foreground">Currency</span>
                  <p className="font-medium text-foreground">
                    {agent.currency}
                  </p>
                </div>
                {agent.address && (
                  <div className="col-span-2">
                    <span className="text-muted-foreground">
                      {t("agents.address")}
                    </span>
                    <p className="font-medium text-foreground">
                      {agent.address}
                    </p>
                  </div>
                )}
                <div>
                  <span className="text-muted-foreground">
                    {t("common.status")}
                  </span>
                  <p className="font-medium">
                    {agent.isActive ? (
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
              </div>
            </CardContent>
          </Card>

          {/* Credit Terms */}
          {agent.creditTerms && (
            <Card className="border-border bg-card">
              <CardHeader>
                <CardTitle className="text-foreground">
                  {t("finance.creditStatus")}
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="grid grid-cols-2 gap-4 text-sm md:grid-cols-3">
                  <div>
                    <span className="text-muted-foreground">
                      {t("agents.creditLimit")}
                    </span>
                    <p className="font-medium text-foreground">
                      {Number(agent.creditTerms.creditLimit).toLocaleString()}{" "}
                      {agent.currency}
                    </p>
                  </div>
                  <div>
                    <span className="text-muted-foreground">
                      {t("agents.creditDays")}
                    </span>
                    <p className="font-medium text-foreground">
                      {agent.creditTerms.creditDays} days
                    </p>
                  </div>
                </div>
              </CardContent>
            </Card>
          )}
        </TabsContent>

        {/* ── Price List Tab ── */}
        <TabsContent value="prices" className="space-y-4">
          {priceLoading ? (
            <div className="flex items-center justify-center py-12">
              <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
            </div>
          ) : (
            <PriceListGrid
              items={priceItems}
              vehicleTypes={vehicleTypes as PriceGridVehicleType[]}
              priceFieldName="price"
              onSave={handleSavePriceList}
              onDeleteRoute={handleDeletePriceRoute}
              onRefresh={fetchPriceList}
            />
          )}
        </TabsContent>
      </Tabs>
    </div>
  );
}
