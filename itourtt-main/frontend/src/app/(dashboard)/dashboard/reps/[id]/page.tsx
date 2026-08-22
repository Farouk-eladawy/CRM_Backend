"use client";

import { useEffect, useState, useCallback } from "react";
import { useParams, useRouter } from "next/navigation";
import { toast } from "sonner";
import { PageHeader } from "@/components/page-header";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
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
import {
  ArrowLeft,
  Loader2,
  MapPin,
  DollarSign,
  User,
  Upload,
  Trash2,
  Plus,
  KeyRound,
  UserPlus,
  CheckCircle2,
} from "lucide-react";

interface Zone {
  id: string;
  name: string;
  city?: { name: string; airport?: { name: string } };
}

interface RepZone {
  id: string;
  zoneId: string;
  zone: Zone;
}

interface RepUser {
  id: string;
  email: string;
  name: string;
  role: string;
  isActive: boolean;
}

interface Rep {
  id: string;
  name: string;
  mobileNumber: string;
  feePerFlight: string | number;
  attachmentUrl: string | null;
  isActive: boolean;
  user: RepUser | null;
  repZones: RepZone[];
}

interface RepFee {
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
}

interface FeesResult {
  fees: RepFee[];
  totalAmount: number;
  count: number;
}

export default function RepDetailPage() {
  const t = useT();
  const { id } = useParams<{ id: string }>();
  const router = useRouter();

  const [loading, setLoading] = useState(true);
  const [rep, setRep] = useState<Rep | null>(null);
  const [saving, setSaving] = useState(false);
  const [uploading, setUploading] = useState(false);

  // Edit profile
  const [editName, setEditName] = useState("");
  const [editMobile, setEditMobile] = useState("");
  const [editFeePerFlight, setEditFeePerFlight] = useState("");
  const [profileDirty, setProfileDirty] = useState(false);

  // Zones
  const [allZones, setAllZones] = useState<Zone[]>([]);
  const [showAssignZone, setShowAssignZone] = useState(false);
  const [assigningZone, setAssigningZone] = useState(false);
  const [selectedZoneId, setSelectedZoneId] = useState("");
  const [unassigning, setUnassigning] = useState<string | null>(null);

  // Fees
  const [feesData, setFeesData] = useState<FeesResult | null>(null);
  const [feesFrom, setFeesFrom] = useState("");
  const [feesTo, setFeesTo] = useState("");
  const [feesLoading, setFeesLoading] = useState(false);

  // Account
  const [showCreateAccount, setShowCreateAccount] = useState(false);
  const [showResetPw, setShowResetPw] = useState(false);
  const [newPassword, setNewPassword] = useState("");
  const [accountBusy, setAccountBusy] = useState(false);

  const loadRep = useCallback(async () => {
    try {
      const { data } = await api.get(`/reps/${id}`);
      const r: Rep = data.data ?? data;
      setRep(r);
      setEditName(r.name);
      setEditMobile(r.mobileNumber);
      setEditFeePerFlight(String(r.feePerFlight ?? 0));
      setProfileDirty(false);
    } catch {
      toast.error("Failed to load rep");
      router.push("/dashboard/reps");
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
      const { data } = await api.get(`/reps/${id}/fees?${params}`);
      setFeesData(data.data ?? data);
    } catch {
      toast.error("Failed to load fees");
    } finally {
      setFeesLoading(false);
    }
  }, [id, feesFrom, feesTo]);

  useEffect(() => {
    loadRep();
  }, [loadRep]);

  useEffect(() => {
    loadFees();
  }, [loadFees]);

  async function loadZones() {
    if (allZones.length > 0) return;
    try {
      const { data } = await api.get("/locations/zones");
      setAllZones(Array.isArray(data) ? data : (data.data ?? []));
    } catch {
      // ignore
    }
  }

  async function handleSaveProfile() {
    if (!rep) return;
    setSaving(true);
    try {
      const { data } = await api.patch(`/reps/${id}`, {
        name: editName,
        mobileNumber: editMobile,
        feePerFlight: parseFloat(editFeePerFlight) || 0,
      });
      setRep((prev) => ({ ...prev!, ...(data.data ?? data) }));
      setProfileDirty(false);
      toast.success("Rep updated successfully");
    } catch {
      toast.error("Failed to update rep");
    } finally {
      setSaving(false);
    }
  }

  async function handleAssignZone() {
    if (!selectedZoneId) return;
    setAssigningZone(true);
    try {
      await api.post(`/reps/${id}/zones`, { zoneId: selectedZoneId });
      toast.success("Zone assigned");
      setShowAssignZone(false);
      setSelectedZoneId("");
      await loadRep();
    } catch {
      toast.error("Failed to assign zone");
    } finally {
      setAssigningZone(false);
    }
  }

  async function handleUnassignZone(zoneId: string) {
    setUnassigning(zoneId);
    try {
      await api.delete(`/reps/${id}/zones/${zoneId}`);
      toast.success("Zone unassigned");
      await loadRep();
    } catch {
      toast.error("Failed to unassign zone");
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
      const { data } = await api.post(`/reps/${id}/attachment`, formData, {
        headers: { "Content-Type": "multipart/form-data" },
      });
      setRep((prev) => (prev ? { ...prev, attachmentUrl: data.url } : prev));
      toast.success("Attachment uploaded");
    } catch {
      toast.error("Failed to upload attachment");
    } finally {
      setUploading(false);
    }
  }

  async function handleCreateAccount() {
    if (!newPassword || newPassword.length < 6) return;
    setAccountBusy(true);
    try {
      await api.post(`/reps/${id}/account`, { password: newPassword });
      toast.success("Account created successfully");
      setShowCreateAccount(false);
      setNewPassword("");
      await loadRep();
    } catch {
      toast.error("Failed to create account");
    } finally {
      setAccountBusy(false);
    }
  }

  async function handleResetPassword() {
    if (!newPassword || newPassword.length < 6) return;
    setAccountBusy(true);
    try {
      await api.patch(`/reps/${id}/account/password`, { password: newPassword });
      toast.success("Password reset successfully");
      setShowResetPw(false);
      setNewPassword("");
    } catch {
      toast.error("Failed to reset password");
    } finally {
      setAccountBusy(false);
    }
  }

  if (loading || !rep) {
    return (
      <div className="flex h-64 items-center justify-center">
        <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
      </div>
    );
  }

  const assignedZoneIds = new Set(rep.repZones.map((rz) => rz.zoneId));
  const availableZones = allZones.filter((z) => !assignedZoneIds.has(z.id));

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-3">
        <Button
          variant="ghost"
          size="sm"
          onClick={() => router.push("/dashboard/reps")}
          className="gap-1.5 text-muted-foreground"
        >
          <ArrowLeft className="h-4 w-4" />
          {t("reps.backToList")}
        </Button>
      </div>

      <PageHeader title={rep.name} description={rep.mobileNumber} />

      <Tabs defaultValue="profile">
        <TabsList className="mb-6">
          <TabsTrigger value="profile" className="gap-2">
            <User className="h-4 w-4" />
            {t("reps.profile")}
          </TabsTrigger>
          <TabsTrigger value="zones" className="gap-2">
            <MapPin className="h-4 w-4" />
            {t("reps.zones")} ({rep.repZones.length})
          </TabsTrigger>
          <TabsTrigger value="fees" className="gap-2">
            <DollarSign className="h-4 w-4" />
            {t("reps.fees")}
          </TabsTrigger>
          <TabsTrigger value="account" className="gap-2">
            <User className="h-4 w-4" />
            {t("reps.account")}
          </TabsTrigger>
        </TabsList>

        {/* ─── PROFILE ─── */}
        <TabsContent value="profile">
          <Card className="border-border bg-card p-6">
            <div className="mb-4 flex items-center justify-between">
              <h2 className="text-lg font-semibold text-foreground">
                {t("reps.profile")}
              </h2>
              <Badge variant={rep.isActive ? "default" : "secondary"}>
                {rep.isActive ? t("common.active") : t("common.inactive")}
              </Badge>
            </div>

            <div className="grid gap-4 sm:grid-cols-2">
              <div>
                <Label className="text-foreground/70">{t("reps.name")}</Label>
                <Input
                  value={editName}
                  onChange={(e) => { setEditName(e.target.value); setProfileDirty(true); }}
                  className="border-border bg-muted/50 text-foreground mt-1"
                />
              </div>
              <div>
                <Label className="text-foreground/70">{t("reps.mobile")}</Label>
                <Input
                  value={editMobile}
                  onChange={(e) => { setEditMobile(e.target.value); setProfileDirty(true); }}
                  className="border-border bg-muted/50 text-foreground mt-1"
                />
              </div>
              <div>
                <Label className="text-foreground/70">{t("reps.feePerFlight")}</Label>
                <Input
                  type="number"
                  min={0}
                  step="0.01"
                  value={editFeePerFlight}
                  onChange={(e) => { setEditFeePerFlight(e.target.value); setProfileDirty(true); }}
                  className="border-border bg-muted/50 text-foreground mt-1"
                />
              </div>
            </div>

            {/* Attachment */}
            <div className="mt-4">
              <Label className="text-foreground/70">{t("drivers.attachment")}</Label>
              <div className="mt-2 flex items-center gap-3">
                {rep.attachmentUrl ? (
                  <a
                    href={`http://localhost:3001${rep.attachmentUrl}`}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-sm text-primary underline"
                  >
                    {rep.attachmentUrl.split("/").pop()}
                  </a>
                ) : (
                  <span className="text-sm text-muted-foreground">—</span>
                )}
                <input
                  type="file"
                  className="hidden"
                  id="rep-attachment"
                  accept="image/*,.pdf,.doc,.docx"
                  onChange={handleFileUpload}
                />
                <Button
                  variant="outline"
                  size="sm"
                  disabled={uploading}
                  onClick={() => document.getElementById("rep-attachment")?.click()}
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

        {/* ─── ZONES ─── */}
        <TabsContent value="zones">
          <Card className="border-border bg-card p-6">
            <div className="mb-4 flex items-center justify-between">
              <h2 className="text-lg font-semibold text-foreground">
                {t("reps.zones")}
              </h2>
              <Button
                size="sm"
                className="gap-1.5"
                onClick={() => {
                  loadZones();
                  setShowAssignZone(true);
                }}
              >
                <Plus className="h-4 w-4" />
                {t("reps.assignZone")}
              </Button>
            </div>

            {rep.repZones.length === 0 ? (
              <p className="text-sm text-muted-foreground">{t("reps.noZones")}</p>
            ) : (
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Zone</TableHead>
                    <TableHead>City</TableHead>
                    <TableHead>Airport</TableHead>
                    <TableHead />
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {rep.repZones.map((rz) => (
                    <TableRow key={rz.id}>
                      <TableCell className="font-medium text-sm">
                        {rz.zone.name}
                      </TableCell>
                      <TableCell className="text-sm text-muted-foreground">
                        {rz.zone.city?.name ?? "—"}
                      </TableCell>
                      <TableCell className="text-sm text-muted-foreground">
                        {rz.zone.city?.airport?.name ?? "—"}
                      </TableCell>
                      <TableCell className="text-right">
                        <Button
                          variant="ghost"
                          size="sm"
                          className="gap-1.5 text-destructive hover:text-destructive"
                          disabled={unassigning === rz.zoneId}
                          onClick={() => handleUnassignZone(rz.zoneId)}
                        >
                          {unassigning === rz.zoneId ? (
                            <Loader2 className="h-4 w-4 animate-spin" />
                          ) : (
                            <Trash2 className="h-4 w-4" />
                          )}
                          {t("reps.unassignZone")}
                        </Button>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            )}
          </Card>
        </TabsContent>

        {/* ─── FEES ─── */}
        <TabsContent value="fees">
          <Card className="border-border bg-card p-6">
            <div className="mb-4 flex flex-wrap items-end gap-3">
              <h2 className="flex-1 text-lg font-semibold text-foreground">
                {t("reps.fees")}
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
                  <p className="text-xs text-muted-foreground">{t("reps.fees")}</p>
                  <p className="text-lg font-bold text-foreground">{feesData.count}</p>
                </div>
                <div>
                  <p className="text-xs text-muted-foreground">{t("reps.totalFees")}</p>
                  <p className="text-lg font-bold text-foreground">
                    {feesData.totalAmount.toLocaleString(undefined, { minimumFractionDigits: 2 })} EGP
                  </p>
                </div>
                <div>
                  <p className="text-xs text-muted-foreground">{t("reps.feePerFlight")}</p>
                  <p className="text-sm font-medium text-foreground">
                    {Number(rep.feePerFlight).toLocaleString(undefined, { minimumFractionDigits: 2 })} EGP
                  </p>
                </div>
              </div>
            )}

            {feesLoading ? (
              <div className="flex h-24 items-center justify-center">
                <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
              </div>
            ) : !feesData || feesData.fees.length === 0 ? (
              <p className="text-sm text-muted-foreground">{t("reps.noFees")}</p>
            ) : (
              <div className="overflow-x-auto [overflow-y:clip]">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Job Ref</TableHead>
                      <TableHead>Date</TableHead>
                      <TableHead>Type</TableHead>
                      <TableHead>{t("reps.amount")}</TableHead>
                      <TableHead>{t("reps.posted")}</TableHead>
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
                            {fee.trafficJob.serviceType}
                          </Badge>
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
              {t("reps.account")}
            </h2>

            {rep.user ? (
              <div className="space-y-4">
                <div className="rounded-lg border border-border bg-muted/20 p-4">
                  <div className="grid gap-3 sm:grid-cols-2">
                    <div>
                      <p className="text-xs text-muted-foreground">{t("common.email")}</p>
                      <p className="font-mono text-sm">{rep.user.email}</p>
                    </div>
                    <div>
                      <p className="text-xs text-muted-foreground">{t("common.role")}</p>
                      <Badge variant="outline" className="text-xs">
                        {rep.user.role}
                      </Badge>
                    </div>
                    <div>
                      <p className="text-xs text-muted-foreground">{t("common.status")}</p>
                      <Badge
                        variant={rep.user.isActive ? "default" : "secondary"}
                        className="text-xs"
                      >
                        {rep.user.isActive ? t("common.active") : t("common.inactive")}
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
                  {t("reps.resetPassword")}
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
                  {t("reps.createAccount")}
                </Button>
              </div>
            )}
          </Card>
        </TabsContent>
      </Tabs>

      {/* Assign Zone Dialog */}
      <Dialog open={showAssignZone} onOpenChange={setShowAssignZone}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{t("reps.assignZone")}</DialogTitle>
          </DialogHeader>
          <div className="py-2">
            <Label className="text-foreground/70">Zone</Label>
            <Select value={selectedZoneId} onValueChange={setSelectedZoneId}>
              <SelectTrigger className="border-border bg-muted/50 mt-1">
                <SelectValue placeholder="Select zone..." />
              </SelectTrigger>
              <SelectContent>
                {availableZones.map((z) => (
                  <SelectItem key={z.id} value={z.id}>
                    {z.name}
                    {z.city ? ` — ${z.city.name}` : ""}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowAssignZone(false)}>
              {t("common.cancel")}
            </Button>
            <Button
              disabled={!selectedZoneId || assigningZone}
              onClick={handleAssignZone}
            >
              {assigningZone && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
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
              {t("reps.createAccountFor")} {rep.name}
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
              {t("reps.createAccount")}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Reset Password Dialog */}
      <Dialog open={showResetPw} onOpenChange={setShowResetPw}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>
              {t("reps.resetPasswordFor")} {rep.name}
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
              {t("reps.resetPassword")}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
