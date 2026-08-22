"use client";

import { useEffect, useState, useCallback, useRef, useMemo, use } from "react";
import { useRouter } from "next/navigation";
import { ArrowLeft, Loader2, Upload, ExternalLink, Plus, Trash2 } from "lucide-react";
import { toast } from "sonner";
import { PageHeader } from "@/components/page-header";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Switch } from "@/components/ui/switch";
import api from "@/lib/api";
import { useT } from "@/lib/i18n";
import { usePermission } from "@/hooks/use-permission";

interface VehicleType {
  id: string;
  name: string;
  seatCapacity: number;
}

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

const COLORS = ["White", "Black", "Silver", "Gray", "Red", "Blue", "Green", "Yellow", "Orange", "Brown", "Beige", "Gold", "Maroon", "Navy", "Burgundy"];
const CURRENCIES = ["EGP", "USD", "EUR", "GBP", "SAR"];

export default function EditVehiclePage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
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
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState("details");
  const [vehicleSubmitting, setVehicleSubmitting] = useState(false);

  // Vehicle details state
  const [plateNumber, setPlateNumber] = useState("");
  const [vehicleTypeId, setVehicleTypeId] = useState("");
  const [ownership, setOwnership] = useState("");
  const [color, setColor] = useState("");
  const [carBrand, setCarBrand] = useState("");
  const [carModel, setCarModel] = useState("");
  const [makeYear, setMakeYear] = useState("");
  const [luggageCapacity, setLuggageCapacity] = useState("");

  // Compliance state
  const [complianceLoading, setComplianceLoading] = useState(false);
  const [complianceSaving, setComplianceSaving] = useState(false);
  const [licenseExpiryDate, setLicenseExpiryDate] = useState("");
  const [licenseCopyUrl, setLicenseCopyUrl] = useState("");
  const [hasInsurance, setHasInsurance] = useState(false);
  const [insuranceExpiryDate, setInsuranceExpiryDate] = useState("");
  const [insuranceDocUrl, setInsuranceDocUrl] = useState("");
  const [annualPayment, setAnnualPayment] = useState("");
  const [annualPaymentCurrency, setAnnualPaymentCurrency] = useState("EGP");
  const [gpsSubscription, setGpsSubscription] = useState("");
  const [gpsSubscriptionCurrency, setGpsSubscriptionCurrency] = useState("EGP");
  const [tourismSupportFund, setTourismSupportFund] = useState("");
  const [tourismSupportFundCurrency, setTourismSupportFundCurrency] = useState("EGP");
  const [registrationFees, setRegistrationFees] = useState("");
  const [registrationFeesCurrency, setRegistrationFeesCurrency] = useState("EGP");
  const [temporaryPermitDate, setTemporaryPermitDate] = useState("");

  // Deposit payments (multi-line)
  interface DepositPayment {
    id: string;
    amount: number;
    currency: string;
    paidAt: string;
    createdByName: string;
  }
  const [deposits, setDeposits] = useState<DepositPayment[]>([]);
  const [newDepositAmount, setNewDepositAmount] = useState("");
  const [newDepositCurrency, setNewDepositCurrency] = useState("EGP");
  const [newDepositDate, setNewDepositDate] = useState(() => new Date().toISOString().slice(0, 16));
  const [addingDeposit, setAddingDeposit] = useState(false);

  const licenseFileRef = useRef<HTMLInputElement>(null);
  const insuranceFileRef = useRef<HTMLInputElement>(null);

  // Computed values
  const permitExpiry = useMemo(() => {
    if (!temporaryPermitDate) return null;
    const d = new Date(temporaryPermitDate);
    d.setMonth(d.getMonth() + 3);
    return d;
  }, [temporaryPermitDate]);

  const permitStatus = useMemo(() => {
    if (!permitExpiry) return null;
    const now = new Date();
    if (permitExpiry < now) return "expired";
    const oneMonthFromNow = new Date();
    oneMonthFromNow.setMonth(oneMonthFromNow.getMonth() + 1);
    if (permitExpiry < oneMonthFromNow) return "warning";
    return "valid";
  }, [permitExpiry]);

  const totalFees = useMemo(() => {
    if (ownership !== "CONTRACTED") return 0;
    const annual = parseFloat(annualPayment) || 0;
    const gps = parseFloat(gpsSubscription) || 0;
    const tourism = parseFloat(tourismSupportFund) || 0;
    const registration = parseFloat(registrationFees) || 0;
    return annual + gps + tourism + registration;
  }, [ownership, annualPayment, gpsSubscription, tourismSupportFund, registrationFees]);

  const depositTotal = useMemo(() => {
    return deposits.reduce((sum, d) => sum + Number(d.amount), 0);
  }, [deposits]);

  const balanceRemaining = useMemo(() => {
    return totalFees - depositTotal;
  }, [totalFees, depositTotal]);

  // Fetch vehicle types
  const fetchTypes = useCallback(async () => {
    try {
      const { data } = await api.get("/vehicles/types");
      setTypes(Array.isArray(data) ? data : []);
    } catch {
      toast.error(t("vehicles.failedLoadTypes"));
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Fetch vehicle data
  const fetchVehicle = useCallback(async () => {
    setLoading(true);
    try {
      const { data } = await api.get(`/vehicles/${id}`);
      const v = data.data || data;
      setPlateNumber(v.plateNumber);
      setVehicleTypeId(v.vehicleTypeId);
      setOwnership(v.ownership);
      setColor(v.color || "");
      setCarBrand(v.carBrand || "");
      setCarModel(v.carModel || "");
      setMakeYear(v.makeYear != null ? String(v.makeYear) : "");
      setLuggageCapacity(v.luggageCapacity != null ? String(v.luggageCapacity) : "");
    } catch {
      toast.error(t("vehicles.failedLoadVehicles"));
      router.push("/dashboard/vehicles");
    } finally {
      setLoading(false);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id]);

  // Load compliance data
  const loadCompliance = useCallback(async () => {
    setComplianceLoading(true);
    try {
      const { data } = await api.get(`/vehicles/${id}/compliance`);
      const c = data?.data;
      if (c) {
        setLicenseExpiryDate(c.licenseExpiryDate ? c.licenseExpiryDate.split("T")[0] : "");
        setLicenseCopyUrl(c.licenseCopyUrl || "");
        setHasInsurance(c.hasInsurance ?? false);
        setInsuranceExpiryDate(c.insuranceExpiryDate ? c.insuranceExpiryDate.split("T")[0] : "");
        setInsuranceDocUrl(c.insuranceDocUrl || "");
        setAnnualPayment(c.annualPayment != null ? String(c.annualPayment) : "");
        setAnnualPaymentCurrency(c.annualPaymentCurrency || "EGP");
        setGpsSubscription(c.gpsSubscription != null ? String(c.gpsSubscription) : "");
        setGpsSubscriptionCurrency(c.gpsSubscriptionCurrency || "EGP");
        setTourismSupportFund(c.tourismSupportFund != null ? String(c.tourismSupportFund) : "");
        setTourismSupportFundCurrency(c.tourismSupportFundCurrency || "EGP");
        setRegistrationFees(c.registrationFees != null ? String(c.registrationFees) : "");
        setRegistrationFeesCurrency(c.registrationFeesCurrency || "EGP");
        setTemporaryPermitDate(c.temporaryPermitDate ? c.temporaryPermitDate.split("T")[0] : "");
        if (c.depositPayments) setDeposits(c.depositPayments);
      }
    } catch {
      // No compliance data yet
    } finally {
      setComplianceLoading(false);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id]);

  useEffect(() => {
    fetchTypes();
    fetchVehicle();
    loadCompliance();
  }, [fetchTypes, fetchVehicle, loadCompliance]);

  // Update vehicle details
  const handleUpdateVehicle = async () => {
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

    setVehicleSubmitting(true);
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
      await api.patch(`/vehicles/${id}`, payload);
      toast.success(t("vehicles.vehicleUpdated"));
      router.push("/dashboard/vehicles");
    } catch {
      toast.error(t("vehicles.failedUpdateVehicle"));
    } finally {
      setVehicleSubmitting(false);
    }
  };

  // Save compliance
  async function handleSaveCompliance() {
    setComplianceSaving(true);
    try {
      const payload: Record<string, unknown> = {};
      if (licenseExpiryDate) payload.licenseExpiryDate = licenseExpiryDate;
      payload.hasInsurance = hasInsurance;
      if (hasInsurance && insuranceExpiryDate) payload.insuranceExpiryDate = insuranceExpiryDate;
      if (gpsSubscription) {
        payload.gpsSubscription = parseFloat(gpsSubscription);
        payload.gpsSubscriptionCurrency = gpsSubscriptionCurrency;
      }
      if (tourismSupportFund) {
        payload.tourismSupportFund = parseFloat(tourismSupportFund);
        payload.tourismSupportFundCurrency = tourismSupportFundCurrency;
      }
      if (temporaryPermitDate) payload.temporaryPermitDate = temporaryPermitDate;
      if (ownership === "CONTRACTED") {
        if (annualPayment) {
          payload.annualPayment = parseFloat(annualPayment);
          payload.annualPaymentCurrency = annualPaymentCurrency;
        }
        if (registrationFees) {
          payload.registrationFees = parseFloat(registrationFees);
          payload.registrationFeesCurrency = registrationFeesCurrency;
        }
      }
      await api.patch(`/vehicles/${id}/compliance`, payload);
      toast.success(t("vehicles.complianceSaved"));
    } catch {
      toast.error(t("vehicles.failedSaveCompliance"));
    } finally {
      setComplianceSaving(false);
    }
  }

  // Upload file
  async function handleUploadFile(type: "license" | "insurance", file: File) {
    const formData = new FormData();
    formData.append("file", file);
    try {
      const { data } = await api.post(`/vehicles/${id}/compliance/${type}`, formData, {
        headers: { "Content-Type": "multipart/form-data" },
      });
      if (type === "license") setLicenseCopyUrl(data.url);
      else setInsuranceDocUrl(data.url);
      toast.success(t("vehicles.fileUploaded"));
    } catch {
      toast.error(t("vehicles.failedUpload"));
    }
  }

  // Deposit payment handlers
  async function handleAddDeposit() {
    if (!newDepositAmount || parseFloat(newDepositAmount) <= 0) {
      toast.error(t("vehicles.amount") + " must be greater than 0");
      return;
    }
    setAddingDeposit(true);
    try {
      await api.post(`/vehicles/${id}/deposits`, {
        amount: parseFloat(newDepositAmount),
        currency: newDepositCurrency,
        paidAt: new Date(newDepositDate).toISOString(),
      });
      toast.success(t("vehicles.depositAdded"));
      setNewDepositAmount("");
      setNewDepositDate(new Date().toISOString().slice(0, 16));
      // Reload deposits
      const { data } = await api.get(`/vehicles/${id}/compliance`);
      if (data?.data?.depositPayments) setDeposits(data.data.depositPayments);
    } catch {
      toast.error(t("vehicles.failedAddDeposit"));
    } finally {
      setAddingDeposit(false);
    }
  }

  async function handleRemoveDeposit(depositId: string) {
    try {
      await api.delete(`/vehicles/${id}/deposits/${depositId}`);
      toast.success(t("vehicles.depositRemoved"));
      setDeposits((prev) => prev.filter((d) => d.id !== depositId));
    } catch {
      toast.error(t("vehicles.failedRemoveDeposit"));
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center py-24">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
      </div>
    );
  }

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
        title={t("vehicles.editVehicle")}
        description={plateNumber}
      />

      <Card className="border-border bg-card">
        <CardContent className="pt-6">
          <Tabs value={activeTab} onValueChange={setActiveTab}>
            <TabsList className="border-border bg-card w-full">
              <TabsTrigger value="details" className="flex-1">{t("vehicles.details")}</TabsTrigger>
              <TabsTrigger value="compliance" className="flex-1">{t("vehicles.compliance")}</TabsTrigger>
            </TabsList>

            {/* Details Tab */}
            <TabsContent value="details" className="mt-4 space-y-4">
              {canPlateNumber && (
              <div className="space-y-2">
                <Label htmlFor="edit-plate-number" className="text-muted-foreground">{t("vehicles.plateNumber")}</Label>
                <Input id="edit-plate-number" placeholder="e.g. ABC-1234" value={plateNumber} onChange={(e) => setPlateNumber(e.target.value)} className="border-border bg-card text-foreground placeholder:text-muted-foreground" />
              </div>
              )}
              {canVehicleType && (
              <div className="space-y-2">
                <Label htmlFor="edit-vehicle-type" className="text-muted-foreground">{t("vehicles.type")}</Label>
                <Select value={vehicleTypeId} onValueChange={setVehicleTypeId}>
                  <SelectTrigger className="border-border bg-card text-foreground"><SelectValue placeholder={t("vehicles.selectType")} /></SelectTrigger>
                  <SelectContent className="border-border bg-popover text-foreground">
                    {types.map((type) => (<SelectItem key={type.id} value={type.id} className="focus:bg-accent focus:text-accent-foreground">{type.name} ({type.seatCapacity} {t("vehicles.seats")})</SelectItem>))}
                  </SelectContent>
                </Select>
              </div>
              )}
              {canOwnership && (
              <div className="space-y-2">
                <Label htmlFor="edit-ownership" className="text-muted-foreground">{t("vehicles.ownership")}</Label>
                <Select value={ownership} onValueChange={setOwnership}>
                  <SelectTrigger className="border-border bg-card text-foreground"><SelectValue placeholder={t("vehicles.selectOwnership")} /></SelectTrigger>
                  <SelectContent className="border-border bg-popover text-foreground">
                    <SelectItem value="OWNED" className="focus:bg-accent focus:text-accent-foreground">{t("vehicles.owned")}</SelectItem>
                    <SelectItem value="RENTED" className="focus:bg-accent focus:text-accent-foreground">{t("vehicles.rented")}</SelectItem>
                    <SelectItem value="CONTRACTED" className="focus:bg-accent focus:text-accent-foreground">{t("vehicles.contracted")}</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              )}
              {canColor && (
              <div className="space-y-2">
                <Label htmlFor="edit-color" className="text-muted-foreground">{t("vehicles.color")}</Label>
                <Select value={color} onValueChange={setColor}>
                  <SelectTrigger className="border-border bg-card text-foreground"><SelectValue placeholder={t("vehicles.selectColor")} /></SelectTrigger>
                  <SelectContent className="border-border bg-popover text-foreground">
                    {COLORS.map((c) => (<SelectItem key={c} value={c} className="focus:bg-accent focus:text-accent-foreground">{c}</SelectItem>))}
                  </SelectContent>
                </Select>
              </div>
              )}
              <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                {canBrand && (
                <div className="space-y-2">
                  <Label htmlFor="edit-car-brand" className="text-muted-foreground">{t("vehicles.carBrand")}</Label>
                  <Input id="edit-car-brand" placeholder="e.g. Toyota" value={carBrand} onChange={(e) => setCarBrand(e.target.value)} className="border-border bg-card text-foreground placeholder:text-muted-foreground" />
                </div>
                )}
                {canModel && (
                <div className="space-y-2">
                  <Label htmlFor="edit-car-model" className="text-muted-foreground">{t("vehicles.carModel")}</Label>
                  <Input id="edit-car-model" placeholder="e.g. Hiace" value={carModel} onChange={(e) => setCarModel(e.target.value)} className="border-border bg-card text-foreground placeholder:text-muted-foreground" />
                </div>
                )}
                {canMakeYear && (
                <div className="space-y-2">
                  <Label htmlFor="edit-make-year" className="text-muted-foreground">{t("vehicles.makeYear")}</Label>
                  <Input id="edit-make-year" type="number" min={1900} max={2100} placeholder="e.g. 2023" value={makeYear} onChange={(e) => setMakeYear(e.target.value)} className="border-border bg-card text-foreground placeholder:text-muted-foreground" />
                </div>
                )}
                {canLuggageCapacity && (
                <div className="space-y-2">
                  <Label htmlFor="edit-luggage-capacity" className="text-muted-foreground">{t("vehicles.luggageCapacity")}</Label>
                  <Input id="edit-luggage-capacity" type="number" min={0} placeholder="e.g. 4" value={luggageCapacity} onChange={(e) => setLuggageCapacity(e.target.value)} className="border-border bg-card text-foreground placeholder:text-muted-foreground" />
                </div>
                )}
              </div>

              <div className="flex justify-end gap-3 pt-4 border-t border-border">
                <Button variant="ghost" onClick={() => router.push("/dashboard/vehicles")} className="text-muted-foreground hover:text-foreground">{t("common.cancel")}</Button>
                <Button onClick={handleUpdateVehicle} disabled={vehicleSubmitting} className="gap-1.5 bg-primary text-primary-foreground hover:bg-primary/90">
                  {vehicleSubmitting && <Loader2 className="h-4 w-4 animate-spin" />}
                  {t("common.saveChanges")}
                </Button>
              </div>
            </TabsContent>

            {/* Compliance Tab */}
            <TabsContent value="compliance" className="mt-4 space-y-5">
              {complianceLoading ? (
                <div className="flex items-center justify-center py-12">
                  <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
                </div>
              ) : (
                <>
                  {/* License Section */}
                  <div className="space-y-3">
                    <div className="space-y-2">
                      <Label className="text-muted-foreground">{t("vehicles.licenseExpiryDate")}</Label>
                      <Input type="date" value={licenseExpiryDate} onChange={(e) => setLicenseExpiryDate(e.target.value)} className="border-border bg-card text-foreground" />
                    </div>
                    <div className="space-y-2">
                      <Label className="text-muted-foreground">{t("vehicles.uploadLicense")}</Label>
                      <div className="flex items-center gap-2">
                        <input ref={licenseFileRef} type="file" className="hidden" accept=".pdf,.jpg,.jpeg,.png" onChange={(e) => { const f = e.target.files?.[0]; if (f) handleUploadFile("license", f); if (licenseFileRef.current) licenseFileRef.current.value = ""; }} />
                        <Button variant="outline" size="sm" className="gap-1.5" onClick={() => licenseFileRef.current?.click()}>
                          <Upload className="h-4 w-4" /> {t("common.upload")}
                        </Button>
                        {licenseCopyUrl && (
                          <a href={licenseCopyUrl} target="_blank" rel="noopener noreferrer" className="text-xs text-primary flex items-center gap-1">
                            <ExternalLink className="h-3 w-3" /> {t("vehicles.viewFile")}
                          </a>
                        )}
                      </div>
                    </div>
                  </div>

                  {/* Insurance Section */}
                  <div className="space-y-3 border-t border-border pt-4">
                    <div className="flex items-center justify-between">
                      <Label className="text-muted-foreground">{t("vehicles.hasInsurance")}</Label>
                      <Switch checked={hasInsurance} onCheckedChange={setHasInsurance} />
                    </div>
                    {hasInsurance && (
                      <>
                        <div className="space-y-2">
                          <Label className="text-muted-foreground">{t("vehicles.insuranceExpiryDate")}</Label>
                          <Input type="date" value={insuranceExpiryDate} onChange={(e) => setInsuranceExpiryDate(e.target.value)} className="border-border bg-card text-foreground" />
                        </div>
                        <div className="space-y-2">
                          <Label className="text-muted-foreground">{t("vehicles.uploadInsurance")}</Label>
                          <div className="flex items-center gap-2">
                            <input ref={insuranceFileRef} type="file" className="hidden" accept=".pdf,.jpg,.jpeg,.png" onChange={(e) => { const f = e.target.files?.[0]; if (f) handleUploadFile("insurance", f); if (insuranceFileRef.current) insuranceFileRef.current.value = ""; }} />
                            <Button variant="outline" size="sm" className="gap-1.5" onClick={() => insuranceFileRef.current?.click()}>
                              <Upload className="h-4 w-4" /> {t("common.upload")}
                            </Button>
                            {insuranceDocUrl && (
                              <a href={insuranceDocUrl} target="_blank" rel="noopener noreferrer" className="text-xs text-primary flex items-center gap-1">
                                <ExternalLink className="h-3 w-3" /> {t("vehicles.viewFile")}
                              </a>
                            )}
                          </div>
                        </div>
                      </>
                    )}
                  </div>

                  {/* Contract / Financial Section */}
                  {(ownership === "CONTRACTED" || ownership === "OWNED") && (
                    <div className="space-y-3 border-t border-border pt-4">
                      <p className="text-sm font-medium text-foreground">{t("vehicles.contractedFields")}</p>

                      {ownership === "CONTRACTED" && (
                        <div className="space-y-2">
                          <Label className="text-muted-foreground">{t("vehicles.annualPayment")}</Label>
                          <div className="flex gap-2">
                            <Input type="number" min={0} value={annualPayment} onChange={(e) => setAnnualPayment(e.target.value)} className="border-border bg-card text-foreground flex-1" placeholder="0.00" />
                            <Select value={annualPaymentCurrency} onValueChange={setAnnualPaymentCurrency}>
                              <SelectTrigger className="border-border bg-card text-foreground w-24"><SelectValue /></SelectTrigger>
                              <SelectContent className="border-border bg-popover text-foreground">
                                {CURRENCIES.map((c) => (<SelectItem key={c} value={c}>{c}</SelectItem>))}
                              </SelectContent>
                            </Select>
                          </div>
                        </div>
                      )}

                      <div className="space-y-2">
                        <Label className="text-muted-foreground">{t("vehicles.gpsSubscription")}</Label>
                        <div className="flex gap-2">
                          <Input type="number" min={0} value={gpsSubscription} onChange={(e) => setGpsSubscription(e.target.value)} className="border-border bg-card text-foreground flex-1" placeholder="0.00" />
                          <Select value={gpsSubscriptionCurrency} onValueChange={setGpsSubscriptionCurrency}>
                            <SelectTrigger className="border-border bg-card text-foreground w-24"><SelectValue /></SelectTrigger>
                            <SelectContent className="border-border bg-popover text-foreground">
                              {CURRENCIES.map((c) => (<SelectItem key={c} value={c}>{c}</SelectItem>))}
                            </SelectContent>
                          </Select>
                        </div>
                      </div>

                      <div className="space-y-2">
                        <Label className="text-muted-foreground">{t("vehicles.tourismSupportFund")}</Label>
                        <div className="flex gap-2">
                          <Input type="number" min={0} value={tourismSupportFund} onChange={(e) => setTourismSupportFund(e.target.value)} className="border-border bg-card text-foreground flex-1" placeholder="0.00" />
                          <Select value={tourismSupportFundCurrency} onValueChange={setTourismSupportFundCurrency}>
                            <SelectTrigger className="border-border bg-card text-foreground w-24"><SelectValue /></SelectTrigger>
                            <SelectContent className="border-border bg-popover text-foreground">
                              {CURRENCIES.map((c) => (<SelectItem key={c} value={c}>{c}</SelectItem>))}
                            </SelectContent>
                          </Select>
                        </div>
                      </div>

                      {ownership === "CONTRACTED" && (
                        <div className="space-y-2">
                          <Label className="text-muted-foreground">{t("vehicles.registrationFees")}</Label>
                          <div className="flex gap-2">
                            <Input type="number" min={0} value={registrationFees} onChange={(e) => setRegistrationFees(e.target.value)} className="border-border bg-card text-foreground flex-1" placeholder="0.00" />
                            <Select value={registrationFeesCurrency} onValueChange={setRegistrationFeesCurrency}>
                              <SelectTrigger className="border-border bg-card text-foreground w-24"><SelectValue /></SelectTrigger>
                              <SelectContent className="border-border bg-popover text-foreground">
                                {CURRENCIES.map((c) => (<SelectItem key={c} value={c}>{c}</SelectItem>))}
                              </SelectContent>
                            </Select>
                          </div>
                        </div>
                      )}

                      {/* Temporary Permit */}
                      <div className="space-y-2">
                        <Label className="text-muted-foreground">{t("vehicles.temporaryPermit")}</Label>
                        <Input type="date" value={temporaryPermitDate} onChange={(e) => setTemporaryPermitDate(e.target.value)} className="border-border bg-card text-foreground" />
                        {permitExpiry && (
                          <div className="flex items-center gap-2 text-xs">
                            <span className="text-muted-foreground">{t("vehicles.permitExpiry")}: {permitExpiry.toLocaleDateString()}</span>
                            {permitStatus === "expired" && (
                              <Badge className="bg-red-500/20 text-red-600 dark:text-red-400 text-xs">{t("vehicles.permitExpired")}</Badge>
                            )}
                            {permitStatus === "warning" && (
                              <Badge className="bg-amber-500/20 text-amber-600 dark:text-amber-400 text-xs">{t("vehicles.permitExpiringSoon")}</Badge>
                            )}
                            {permitStatus === "valid" && (
                              <Badge className="bg-emerald-500/20 text-emerald-600 dark:text-emerald-400 text-xs">{t("vehicles.permitValid")}</Badge>
                            )}
                          </div>
                        )}
                      </div>

                      {/* Total Fees (CONTRACTED only) */}
                      {ownership === "CONTRACTED" && (
                        <div className="space-y-2">
                          <Label className="text-muted-foreground">{t("vehicles.totalFees")}</Label>
                          <div className="rounded-md border border-border bg-muted/30 px-3 py-2 text-sm font-semibold text-foreground">
                            {totalFees.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })} {annualPaymentCurrency}
                          </div>
                        </div>
                      )}

                      {/* Deposit Payments Grid (CONTRACTED only) */}
                      {ownership === "CONTRACTED" && (
                        <div className="space-y-3 border-t border-border pt-4">
                          <p className="text-sm font-medium text-foreground">{t("vehicles.depositPayments")}</p>

                          <div className="overflow-x-auto [overflow-y:clip]">
                            <table className="w-full text-sm">
                              <thead>
                                <tr className="border-b border-border text-xs text-muted-foreground">
                                  <th className="pb-2 text-left font-medium">{t("vehicles.amount")}</th>
                                  <th className="pb-2 text-left font-medium">{t("vehicles.currency")}</th>
                                  <th className="pb-2 text-left font-medium">{t("vehicles.dateTime")}</th>
                                  <th className="pb-2 text-left font-medium">{t("vehicles.createdBy")}</th>
                                  <th className="pb-2 w-10"></th>
                                </tr>
                              </thead>
                              <tbody>
                                {deposits.map((dep) => (
                                  <tr key={dep.id} className="border-b border-border/50">
                                    <td className="py-2 font-mono">{Number(dep.amount).toLocaleString(undefined, { minimumFractionDigits: 2 })}</td>
                                    <td className="py-2">{dep.currency}</td>
                                    <td className="py-2 text-muted-foreground">{new Date(dep.paidAt).toLocaleString()}</td>
                                    <td className="py-2 text-muted-foreground">{dep.createdByName}</td>
                                    <td className="py-2">
                                      <Button variant="ghost" size="sm" className="h-6 w-6 p-0 text-red-500 hover:text-red-700" onClick={() => handleRemoveDeposit(dep.id)}>
                                        <Trash2 className="h-3.5 w-3.5" />
                                      </Button>
                                    </td>
                                  </tr>
                                ))}
                                {deposits.length === 0 && (
                                  <tr>
                                    <td colSpan={5} className="py-4 text-center text-muted-foreground text-xs">{t("vehicles.noDeposits")}</td>
                                  </tr>
                                )}
                              </tbody>
                            </table>
                          </div>

                          {/* Add new deposit row */}
                          <div className="flex items-end gap-2">
                            <div className="flex-1">
                              <Input type="number" min={0} value={newDepositAmount} onChange={(e) => setNewDepositAmount(e.target.value)} placeholder="0.00" className="border-border bg-card text-foreground" />
                            </div>
                            <Select value={newDepositCurrency} onValueChange={setNewDepositCurrency}>
                              <SelectTrigger className="border-border bg-card text-foreground w-24"><SelectValue /></SelectTrigger>
                              <SelectContent className="border-border bg-popover text-foreground">
                                {CURRENCIES.map((c) => (<SelectItem key={c} value={c}>{c}</SelectItem>))}
                              </SelectContent>
                            </Select>
                            <Input type="datetime-local" value={newDepositDate} onChange={(e) => setNewDepositDate(e.target.value)} className="border-border bg-card text-foreground w-52" />
                            <Button size="sm" onClick={handleAddDeposit} disabled={addingDeposit} className="gap-1 bg-primary text-primary-foreground hover:bg-primary/90">
                              {addingDeposit ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Plus className="h-3.5 w-3.5" />}
                              {t("common.add")}
                            </Button>
                          </div>

                          {/* Balance Remaining */}
                          <div className="space-y-2">
                            <Label className="text-muted-foreground">{t("vehicles.balanceRemaining")}</Label>
                            <div className={`rounded-md border border-border px-3 py-2 text-sm font-semibold ${balanceRemaining < 0 ? "text-red-500" : "text-foreground"} bg-muted/30`}>
                              {balanceRemaining.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })} {annualPaymentCurrency}
                            </div>
                          </div>
                        </div>
                      )}
                    </div>
                  )}

                  <div className="flex justify-end gap-3 pt-4 border-t border-border">
                    <Button variant="ghost" onClick={() => router.push("/dashboard/vehicles")} className="text-muted-foreground hover:text-foreground">{t("common.cancel")}</Button>
                    <Button onClick={handleSaveCompliance} disabled={complianceSaving} className="gap-1.5 bg-primary text-primary-foreground hover:bg-primary/90">
                      {complianceSaving && <Loader2 className="h-4 w-4 animate-spin" />}
                      {t("common.saveChanges")}
                    </Button>
                  </div>
                </>
              )}
            </TabsContent>
          </Tabs>
        </CardContent>
      </Card>
    </div>
  );
}
