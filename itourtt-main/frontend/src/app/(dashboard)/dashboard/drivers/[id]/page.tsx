"use client";

import { useEffect, useRef, useState, useCallback } from "react";
import { useParams, useRouter } from "next/navigation";
import { toast } from "sonner";
import { PageHeader } from "@/components/page-header";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { Switch } from "@/components/ui/switch";
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
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  Tabs,
  TabsContent,
  TabsList,
  TabsTrigger,
} from "@/components/ui/tabs";
import api from "@/lib/api";
import { useT } from "@/lib/i18n";
import { useServiceTypeLabel } from "@/lib/service-types";
import {
  ArrowLeft,
  Loader2,
  Car,
  DollarSign,
  User,
  Upload,
  Pencil,
  Trash2,
  Plus,
  KeyRound,
  UserPlus,
  AlertTriangle,
  CheckCircle2,
} from "lucide-react";

interface VehicleType {
  id: string;
  name: string;
}

interface Vehicle {
  id: string;
  plateNumber: string;
  vehicleType: VehicleType;
}

interface DriverVehicle {
  id: string;
  vehicleId: string;
  isPrimary: boolean;
  vehicle: Vehicle;
}

interface DriverUser {
  id: string;
  email: string;
  name: string;
  role: string;
  isActive: boolean;
}

interface Driver {
  id: string;
  name: string;
  mobileNumber: string;
  licenseNumber: string | null;
  licenseExpiryDate: string | null;
  attachmentUrl: string | null;
  isActive: boolean;
  supplierId: string | null;
  user: DriverUser | null;
  driverVehicles: DriverVehicle[];
}

interface TripFee {
  id: string;
  amount: string;
  currency: string;
  isPosted: boolean;
  createdAt: string;
  trafficJob: {
    id: string;
    internalRef: string;
    serviceType: string;
    jobDate: string;
  };
  // A fee leg is either a zone or an airport — never both, and either side may be
  // absent (ARR starts at an airport, DEP ends at one).
  fromZone?: { id: string; name: string } | null;
  toZone?: { id: string; name: string } | null;
  fromAirport?: { id: string; name: string; code: string } | null;
  toAirport?: { id: string; name: string; code: string } | null;
}

function feeLocationLabel(fee: TripFee, side: "from" | "to") {
  if (side === "from") {
    if (fee.fromAirport) return `${fee.fromAirport.code} – ${fee.fromAirport.name}`;
    return fee.fromZone?.name ?? "—";
  }
  if (fee.toAirport) return `${fee.toAirport.code} – ${fee.toAirport.name}`;
  return fee.toZone?.name ?? "—";
}

interface TripFeesResult {
  fees: TripFee[];
  totalAmount: number;
  count: number;
}

function getExpiryStatus(dateStr: string | null): "expired" | "expiring" | "ok" | null {
  if (!dateStr) return null;
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  const expiry = new Date(dateStr);
  expiry.setHours(0, 0, 0, 0);
  if (expiry < today) return "expired";
  const thirtyDays = new Date(today);
  thirtyDays.setDate(thirtyDays.getDate() + 30);
  if (expiry <= thirtyDays) return "expiring";
  return "ok";
}

export default function DriverDetailPage() {
  const serviceTypeLabel = useServiceTypeLabel();
  const t = useT();
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const fileInputRef = useRef<HTMLInputElement>(null);

  const [loading, setLoading] = useState(true);
  const [driver, setDriver] = useState<Driver | null>(null);
  const [saving, setSaving] = useState(false);

  // Edit profile
  const [editName, setEditName] = useState("");
  const [editMobile, setEditMobile] = useState("");
  const [editLicense, setEditLicense] = useState("");
  const [editExpiry, setEditExpiry] = useState("");
  const [profileDirty, setProfileDirty] = useState(false);

  // Vehicles
  const [allVehicles, setAllVehicles] = useState<Vehicle[]>([]);
  const [showAssignVehicle, setShowAssignVehicle] = useState(false);
  const [assigningVehicle, setAssigningVehicle] = useState(false);
  const [selectedVehicleId, setSelectedVehicleId] = useState("");
  const [isPrimary, setIsPrimary] = useState(false);
  const [unassigning, setUnassigning] = useState<string | null>(null);

  // Trip fees
  const [feesData, setFeesData] = useState<TripFeesResult | null>(null);
  const [feesFrom, setFeesFrom] = useState("");
  const [feesTo, setFeesTo] = useState("");
  const [feesLoading, setFeesLoading] = useState(false);

  // Account
  const [showCreateAccount, setShowCreateAccount] = useState(false);
  const [showResetPw, setShowResetPw] = useState(false);
  const [newPassword, setNewPassword] = useState("");
  const [accountBusy, setAccountBusy] = useState(false);
  const [uploading, setUploading] = useState(false);

  const loadDriver = useCallback(async () => {
    try {
      const { data } = await api.get(`/drivers/${id}`);
      const d: Driver = data.data ?? data;
      setDriver(d);
      setEditName(d.name);
      setEditMobile(d.mobileNumber);
      setEditLicense(d.licenseNumber ?? "");
      setEditExpiry(
        d.licenseExpiryDate ? d.licenseExpiryDate.split("T")[0] : ""
      );
      setProfileDirty(false);
    } catch {
      toast.error("Failed to load driver");
      router.push("/dashboard/drivers");
    } finally {
      setLoading(false);
    }
  }, [id, router]);

  const loadFees = useCallback(async () => {
    setFeesLoading(true);
    try {
      const params = new URLSearchParams();
      if (feesFrom) params.set("from", feesFrom);
      if (feesTo) params.set("to", feesTo);
      const { data } = await api.get(`/drivers/${id}/trip-fees?${params}`);
      setFeesData(data.data ?? data);
    } catch {
      toast.error("Failed to load fees");
    } finally {
      setFeesLoading(false);
    }
  }, [id, feesFrom, feesTo]);

  useEffect(() => {
    loadDriver();
  }, [loadDriver]);

  useEffect(() => {
    loadFees();
  }, [loadFees]);

  async function loadVehicles() {
    if (allVehicles.length > 0) return;
    try {
      const { data } = await api.get("/vehicles?limit=200");
      setAllVehicles(data.data ?? []);
    } catch {
      // ignore
    }
  }

  async function handleSaveProfile() {
    if (!driver) return;
    setSaving(true);
    try {
      const { data } = await api.patch(`/drivers/${id}`, {
        name: editName,
        mobileNumber: editMobile,
        licenseNumber: editLicense || null,
        licenseExpiryDate: editExpiry || null,
      });
      setDriver((prev) => ({ ...prev!, ...(data.data ?? data) }));
      setProfileDirty(false);
      toast.success(t("drivers.updated"));
    } catch {
      toast.error(t("drivers.failedUpdate"));
    } finally {
      setSaving(false);
    }
  }

  async function handleAssignVehicle() {
    if (!selectedVehicleId) return;
    setAssigningVehicle(true);
    try {
      await api.post(`/drivers/${id}/vehicles`, {
        vehicleId: selectedVehicleId,
        isPrimary,
      });
      toast.success("Vehicle assigned");
      setShowAssignVehicle(false);
      setSelectedVehicleId("");
      setIsPrimary(false);
      await loadDriver();
    } catch {
      toast.error("Failed to assign vehicle");
    } finally {
      setAssigningVehicle(false);
    }
  }

  async function handleUnassignVehicle(vehicleId: string) {
    setUnassigning(vehicleId);
    try {
      await api.delete(`/drivers/${id}/vehicles/${vehicleId}`);
      toast.success("Vehicle unassigned");
      await loadDriver();
    } catch {
      toast.error("Failed to unassign vehicle");
    } finally {
      setUnassigning(null);
    }
  }

  async function handleFileUpload(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;
    setUploading(true);
    try {
      const formData = new FormData();
      formData.append("file", file);
      const { data } = await api.post(`/drivers/${id}/attachment`, formData, {
        headers: { "Content-Type": "multipart/form-data" },
      });
      setDriver((prev) => (prev ? { ...prev, attachmentUrl: data.url } : prev));
      toast.success(t("drivers.attachmentUploaded"));
    } catch {
      toast.error(t("drivers.failedUpload"));
    } finally {
      setUploading(false);
      if (fileInputRef.current) fileInputRef.current.value = "";
    }
  }

  async function handleCreateAccount() {
    if (!newPassword || newPassword.length < 6) return;
    setAccountBusy(true);
    try {
      await api.post(`/drivers/${id}/account`, { password: newPassword });
      toast.success(t("drivers.accountCreated"));
      setShowCreateAccount(false);
      setNewPassword("");
      await loadDriver();
    } catch {
      toast.error(t("drivers.failedAccount"));
    } finally {
      setAccountBusy(false);
    }
  }

  async function handleResetPassword() {
    if (!newPassword || newPassword.length < 6) return;
    setAccountBusy(true);
    try {
      await api.patch(`/drivers/${id}/account/password`, { password: newPassword });
      toast.success(t("drivers.passwordReset"));
      setShowResetPw(false);
      setNewPassword("");
    } catch {
      toast.error(t("drivers.failedPassword"));
    } finally {
      setAccountBusy(false);
    }
  }

  if (loading || !driver) {
    return (
      <div className="flex h-64 items-center justify-center">
        <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
      </div>
    );
  }

  const expiryStatus = getExpiryStatus(driver.licenseExpiryDate);
  const assignedVehicleIds = new Set(driver.driverVehicles.map((dv) => dv.vehicleId));
  const availableVehicles = allVehicles.filter((v) => !assignedVehicleIds.has(v.id));

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-3">
        <Button
          variant="ghost"
          size="sm"
          onClick={() => router.push("/dashboard/drivers")}
          className="gap-1.5 text-muted-foreground"
        >
          <ArrowLeft className="h-4 w-4" />
          {t("drivers.backToList")}
        </Button>
      </div>

      <PageHeader
        title={driver.name}
        description={driver.mobileNumber}
      />

      <Tabs defaultValue="profile">
        <TabsList className="mb-6">
          <TabsTrigger value="profile" className="gap-2">
            <User className="h-4 w-4" />
            {t("drivers.profile")}
          </TabsTrigger>
          <TabsTrigger value="vehicles" className="gap-2">
            <Car className="h-4 w-4" />
            {t("drivers.vehicles")} ({driver.driverVehicles.length})
          </TabsTrigger>
          <TabsTrigger value="fees" className="gap-2">
            <DollarSign className="h-4 w-4" />
            {t("drivers.tripFees")}
          </TabsTrigger>
          <TabsTrigger value="account" className="gap-2">
            <User className="h-4 w-4" />
            {t("drivers.account")}
          </TabsTrigger>
        </TabsList>

        {/* ─── PROFILE ─── */}
        <TabsContent value="profile">
          <Card className="border-border bg-card p-6">
            <div className="mb-4 flex items-center justify-between">
              <h2 className="text-lg font-semibold text-foreground">
                {t("drivers.profile")}
              </h2>
              <Badge variant={driver.isActive ? "default" : "secondary"}>
                {driver.isActive ? t("common.active") : t("common.inactive")}
              </Badge>
            </div>

            <div className="grid gap-4 sm:grid-cols-2">
              <div>
                <Label className="text-foreground/70">{t("drivers.name")}</Label>
                <Input
                  value={editName}
                  onChange={(e) => { setEditName(e.target.value); setProfileDirty(true); }}
                  className="border-border bg-muted/50 text-foreground mt-1"
                />
              </div>
              <div>
                <Label className="text-foreground/70">{t("drivers.mobileNumber")}</Label>
                <Input
                  value={editMobile}
                  onChange={(e) => { setEditMobile(e.target.value); setProfileDirty(true); }}
                  className="border-border bg-muted/50 text-foreground mt-1"
                />
              </div>
              <div>
                <Label className="text-foreground/70">{t("drivers.licenseNumber")}</Label>
                <Input
                  value={editLicense}
                  onChange={(e) => { setEditLicense(e.target.value); setProfileDirty(true); }}
                  className="border-border bg-muted/50 text-foreground mt-1"
                />
              </div>
              <div>
                <Label className="text-foreground/70">{t("drivers.licenseExpiryDate")}</Label>
                <Input
                  type="date"
                  value={editExpiry}
                  onChange={(e) => { setEditExpiry(e.target.value); setProfileDirty(true); }}
                  className="border-border bg-muted/50 text-foreground mt-1"
                />
                {expiryStatus === "expired" && (
                  <p className="mt-1 flex items-center gap-1 text-xs text-destructive">
                    <AlertTriangle className="h-3.5 w-3.5" />
                    {t("drivers.expired")}
                  </p>
                )}
                {expiryStatus === "expiring" && (
                  <p className="mt-1 flex items-center gap-1 text-xs text-amber-500">
                    <AlertTriangle className="h-3.5 w-3.5" />
                    {t("drivers.expiringSoon")}
                  </p>
                )}
              </div>
            </div>

            {/* Attachment */}
            <div className="mt-4">
              <Label className="text-foreground/70">{t("drivers.attachment")}</Label>
              <div className="mt-2 flex items-center gap-3">
                {driver.attachmentUrl ? (
                  <a
                    href={`http://localhost:3001${driver.attachmentUrl}`}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-sm text-primary underline"
                  >
                    {driver.attachmentUrl.split("/").pop()}
                  </a>
                ) : (
                  <span className="text-sm text-muted-foreground">—</span>
                )}
                <input
                  ref={fileInputRef}
                  type="file"
                  className="hidden"
                  accept="image/*,.pdf,.doc,.docx"
                  onChange={handleFileUpload}
                />
                <Button
                  variant="outline"
                  size="sm"
                  disabled={uploading}
                  onClick={() => fileInputRef.current?.click()}
                  className="gap-1.5"
                >
                  {uploading ? (
                    <Loader2 className="h-4 w-4 animate-spin" />
                  ) : (
                    <Upload className="h-4 w-4" />
                  )}
                  {t("common.upload")}
                </Button>
              </div>
            </div>

            {profileDirty && (
              <div className="mt-6 flex justify-end">
                <Button onClick={handleSaveProfile} disabled={saving} className="gap-2">
                  {saving && <Loader2 className="h-4 w-4 animate-spin" />}
                  {saving ? t("common.loading") : t("common.saveChanges")}
                </Button>
              </div>
            )}
          </Card>
        </TabsContent>

        {/* ─── VEHICLES ─── */}
        <TabsContent value="vehicles">
          <Card className="border-border bg-card p-6">
            <div className="mb-4 flex items-center justify-between">
              <h2 className="text-lg font-semibold text-foreground">
                {t("drivers.vehicles")}
              </h2>
              <Button
                size="sm"
                className="gap-1.5"
                onClick={() => {
                  loadVehicles();
                  setShowAssignVehicle(true);
                }}
              >
                <Plus className="h-4 w-4" />
                {t("drivers.assignVehicle")}
              </Button>
            </div>

            {driver.driverVehicles.length === 0 ? (
              <p className="text-sm text-muted-foreground">{t("drivers.noVehicles")}</p>
            ) : (
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Plate</TableHead>
                    <TableHead>Type</TableHead>
                    <TableHead>{t("drivers.isPrimary")}</TableHead>
                    <TableHead />
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {driver.driverVehicles.map((dv) => (
                    <TableRow key={dv.id}>
                      <TableCell className="font-mono text-sm">
                        {dv.vehicle.plateNumber}
                      </TableCell>
                      <TableCell className="text-sm">
                        {dv.vehicle.vehicleType.name}
                      </TableCell>
                      <TableCell>
                        {dv.isPrimary && (
                          <Badge variant="default" className="text-xs">
                            {t("drivers.isPrimary")}
                          </Badge>
                        )}
                      </TableCell>
                      <TableCell className="text-right">
                        <Button
                          variant="ghost"
                          size="sm"
                          className="gap-1.5 text-destructive hover:text-destructive"
                          disabled={unassigning === dv.vehicleId}
                          onClick={() => handleUnassignVehicle(dv.vehicleId)}
                        >
                          {unassigning === dv.vehicleId ? (
                            <Loader2 className="h-4 w-4 animate-spin" />
                          ) : (
                            <Trash2 className="h-4 w-4" />
                          )}
                          {t("drivers.unassignVehicle")}
                        </Button>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            )}
          </Card>
        </TabsContent>

        {/* ─── TRIP FEES ─── */}
        <TabsContent value="fees">
          <Card className="border-border bg-card p-6">
            <div className="mb-4 flex flex-wrap items-end gap-3">
              <h2 className="flex-1 text-lg font-semibold text-foreground">
                {t("drivers.tripFees")}
              </h2>
              <div className="flex items-end gap-2">
                <div>
                  <Label className="text-xs text-foreground/60">{t("common.from")}</Label>
                  <Input
                    type="date"
                    value={feesFrom}
                    onChange={(e) => setFeesFrom(e.target.value)}
                    className="border-border bg-muted/50 text-foreground mt-0.5 h-8 text-sm"
                  />
                </div>
                <div>
                  <Label className="text-xs text-foreground/60">{t("common.to")}</Label>
                  <Input
                    type="date"
                    value={feesTo}
                    onChange={(e) => setFeesTo(e.target.value)}
                    className="border-border bg-muted/50 text-foreground mt-0.5 h-8 text-sm"
                  />
                </div>
              </div>
            </div>

            {feesData && (
              <div className="mb-4 flex items-center gap-6 rounded-lg border border-border bg-muted/20 px-4 py-3">
                <div>
                  <p className="text-xs text-muted-foreground">{t("drivers.tripFees")}</p>
                  <p className="text-lg font-bold text-foreground">{feesData.count}</p>
                </div>
                <div>
                  <p className="text-xs text-muted-foreground">{t("drivers.totalFees")}</p>
                  <p className="text-lg font-bold text-foreground">
                    {feesData.totalAmount.toLocaleString(undefined, { minimumFractionDigits: 2 })} EGP
                  </p>
                </div>
              </div>
            )}

            {feesLoading ? (
              <div className="flex h-24 items-center justify-center">
                <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
              </div>
            ) : !feesData || feesData.fees.length === 0 ? (
              <p className="text-sm text-muted-foreground">{t("drivers.noFees")}</p>
            ) : (
              <div className="overflow-x-auto [overflow-y:clip]">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Job Ref</TableHead>
                      <TableHead>Date</TableHead>
                      <TableHead>Type</TableHead>
                      <TableHead>{t("drivers.route")}</TableHead>
                      <TableHead>{t("drivers.amount")}</TableHead>
                      <TableHead>{t("drivers.posted")}</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {feesData.fees.map((fee) => (
                      <TableRow key={fee.id}>
                        <TableCell className="font-mono text-xs">
                          {fee.trafficJob.internalRef}
                        </TableCell>
                        <TableCell className="text-xs">
                          {new Date(fee.trafficJob.jobDate).toLocaleDateString()}
                        </TableCell>
                        <TableCell>
                          <Badge variant="outline" className="text-xs">
                            {serviceTypeLabel(fee.trafficJob.serviceType)}
                          </Badge>
                        </TableCell>
                        <TableCell className="text-xs text-muted-foreground">
                          {feeLocationLabel(fee, "from")} → {feeLocationLabel(fee, "to")}
                        </TableCell>
                        <TableCell className="font-mono text-sm">
                          {Number(fee.amount).toLocaleString(undefined, {
                            minimumFractionDigits: 2,
                          })}{" "}
                          {fee.currency}
                        </TableCell>
                        <TableCell>
                          {fee.isPosted ? (
                            <CheckCircle2 className="h-4 w-4 text-green-500" />
                          ) : (
                            <span className="text-xs text-muted-foreground">—</span>
                          )}
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </div>
            )}
          </Card>
        </TabsContent>

        {/* ─── ACCOUNT ─── */}
        <TabsContent value="account">
          <Card className="border-border bg-card p-6">
            <h2 className="mb-4 text-lg font-semibold text-foreground">
              {t("drivers.account")}
            </h2>

            {driver.user ? (
              <div className="space-y-4">
                <div className="rounded-lg border border-border bg-muted/20 p-4">
                  <div className="grid gap-3 sm:grid-cols-2">
                    <div>
                      <p className="text-xs text-muted-foreground">{t("common.email")}</p>
                      <p className="font-mono text-sm">{driver.user.email}</p>
                    </div>
                    <div>
                      <p className="text-xs text-muted-foreground">{t("common.role")}</p>
                      <Badge variant="outline" className="text-xs">
                        {driver.user.role}
                      </Badge>
                    </div>
                    <div>
                      <p className="text-xs text-muted-foreground">{t("common.status")}</p>
                      <Badge
                        variant={driver.user.isActive ? "default" : "secondary"}
                        className="text-xs"
                      >
                        {driver.user.isActive ? t("common.active") : t("common.inactive")}
                      </Badge>
                    </div>
                  </div>
                </div>
                <Button
                  variant="outline"
                  size="sm"
                  className="gap-1.5"
                  onClick={() => { setNewPassword(""); setShowResetPw(true); }}
                >
                  <KeyRound className="h-4 w-4" />
                  {t("drivers.resetPassword")}
                </Button>
              </div>
            ) : (
              <div className="space-y-3">
                <p className="text-sm text-muted-foreground">
                  {t("drivers.loginWithMobile")}
                </p>
                <Button
                  size="sm"
                  className="gap-1.5"
                  onClick={() => { setNewPassword(""); setShowCreateAccount(true); }}
                >
                  <UserPlus className="h-4 w-4" />
                  {t("drivers.createAccount")}
                </Button>
              </div>
            )}
          </Card>
        </TabsContent>
      </Tabs>

      {/* Assign Vehicle Dialog */}
      <Dialog open={showAssignVehicle} onOpenChange={setShowAssignVehicle}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{t("drivers.assignVehicle")}</DialogTitle>
          </DialogHeader>
          <div className="space-y-4 py-2">
            <div>
              <Label className="text-foreground/70">Vehicle</Label>
              <Select value={selectedVehicleId} onValueChange={setSelectedVehicleId}>
                <SelectTrigger className="border-border bg-muted/50 mt-1">
                  <SelectValue placeholder="Select vehicle..." />
                </SelectTrigger>
                <SelectContent>
                  {availableVehicles.map((v) => (
                    <SelectItem key={v.id} value={v.id}>
                      {v.plateNumber} — {v.vehicleType.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="flex items-center gap-3">
              <Switch
                checked={isPrimary}
                onCheckedChange={setIsPrimary}
                id="primary-vehicle"
              />
              <Label htmlFor="primary-vehicle" className="text-foreground/70">
                {t("drivers.isPrimary")}
              </Label>
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowAssignVehicle(false)}>
              {t("common.cancel")}
            </Button>
            <Button
              disabled={!selectedVehicleId || assigningVehicle}
              onClick={handleAssignVehicle}
            >
              {assigningVehicle && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
              {t("common.confirm")}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Create Account Dialog */}
      <Dialog open={showCreateAccount} onOpenChange={setShowCreateAccount}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>
              {t("drivers.createAccountFor")} {driver.name}
            </DialogTitle>
          </DialogHeader>
          <div className="py-2">
            <p className="mb-3 text-sm text-muted-foreground">
              {t("drivers.loginWithMobile")}
            </p>
            <Label className="text-foreground/70">{t("drivers.newPassword")}</Label>
            <Input
              type="password"
              value={newPassword}
              onChange={(e) => setNewPassword(e.target.value)}
              placeholder={t("drivers.minChars")}
              className="border-border bg-muted/50 text-foreground mt-1"
            />
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowCreateAccount(false)}>
              {t("common.cancel")}
            </Button>
            <Button
              disabled={newPassword.length < 6 || accountBusy}
              onClick={handleCreateAccount}
            >
              {accountBusy && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
              {t("drivers.createAccount")}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Reset Password Dialog */}
      <Dialog open={showResetPw} onOpenChange={setShowResetPw}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>
              {t("drivers.resetPasswordFor")} {driver.name}
            </DialogTitle>
          </DialogHeader>
          <div className="py-2">
            <Label className="text-foreground/70">{t("drivers.newPassword")}</Label>
            <Input
              type="password"
              value={newPassword}
              onChange={(e) => setNewPassword(e.target.value)}
              placeholder={t("drivers.minChars")}
              className="border-border bg-muted/50 text-foreground mt-1"
            />
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowResetPw(false)}>
              {t("common.cancel")}
            </Button>
            <Button
              disabled={newPassword.length < 6 || accountBusy}
              onClick={handleResetPassword}
            >
              {accountBusy && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
              {t("drivers.resetPassword")}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
