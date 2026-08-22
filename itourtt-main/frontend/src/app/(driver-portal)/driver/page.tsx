"use client";

import { useEffect, useState, useCallback } from "react";
import api from "@/lib/api";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
  DialogDescription,
} from "@/components/ui/dialog";
import {
  Plane,
  MapPin,
  Users,
  Car,
  Clock,
  CheckCircle2,
  XCircle,
  UserX,
  Bell,
  CalendarDays,
  Loader2,
  RefreshCw,
  Briefcase,
  User,
  PlayCircle,
  Navigation,
  ChevronLeft,
  ChevronRight,
  DollarSign,
} from "lucide-react";
import { toast } from "sonner";
import { NoShowEvidenceDialog } from "@/components/no-show-evidence-dialog";
import { CompletedEvidenceDialog } from "@/components/completed-evidence-dialog";
import { InProgressEvidenceDialog } from "@/components/in-progress-evidence-dialog";
import JobDetailModal from "@/components/job-detail-modal";
import { useT, useLocaleId } from "@/lib/i18n";
import { formatDate , localDateStr } from "@/lib/utils";
import { captureGPS } from "@/lib/gps";
import { SERVICE_TYPE_COLORS, useServiceTypeLabel } from "@/lib/service-types";

interface DriverJob {
  id: string;
  internalRef: string;
  agentRef: string | null;
  serviceType: string;
  jobDate: string;
  status: string;
  driverStatus: string;
  bookingChannel: string | null;
  clientName: string | null;
  clientMobile: string | null;
  paxCount: number;
  pickUpTime: string | null;
  notes: string | null;
  custRepName: string | null;
  custRepMobile: string | null;
  custRepMeetingPoint: string | null;
  custRepMeetingTime: string | null;
  fromZone?: { name: string };
  toZone?: { name: string };
  originAirport?: { name: string; code: string } | null;
  originZone?: { name: string } | null;
  originHotel?: { name: string } | null;
  destinationAirport?: { name: string; code: string } | null;
  destinationZone?: { name: string } | null;
  destinationHotel?: { name: string } | null;
  flight?: {
    flightNo: string;
    carrier: string;
    terminal: string | null;
    arrivalTime: string | null;
    departureTime: string | null;
  };
  agent?: { legalName: string };
  customer?: { legalName: string };
  assignment?: {
    vehicle?: { plateNumber: string; vehicleType?: { name: string } };
    rep?: { name: string; mobileNumber: string };
    externalDriverName?: string | null;
    externalDriverPhone?: string | null;
    supplier?: { tradeName?: string | null; legalName: string };
  };
  collectionRequired: boolean;
  collectionAmount: number | null;
  collectionCurrency: string;
  collectionCollected: boolean;
}

interface Notification {
  id: string;
  title: string;
  message: string;
  type: string;
  isRead: boolean;
  createdAt: string;
  trafficJob?: {
    internalRef: string;
    serviceType: string;
    jobDate: string;
  };
}


const STATUS_COLORS: Record<string, string> = {
  PENDING: "bg-yellow-500/10 text-yellow-400 border-yellow-500/20",
  ASSIGNED: "bg-blue-500/10 text-blue-400 border-blue-500/20",
  IN_PROGRESS: "bg-cyan-500/10 text-cyan-400 border-cyan-500/20",
  COMPLETED: "bg-green-500/10 text-green-400 border-green-500/20",
  CANCELLED: "bg-red-500/10 text-red-400 border-red-500/20",
  NO_SHOW: "bg-gray-500/10 text-gray-400 border-gray-500/20",
};

const TERMINAL_STATUSES = ["COMPLETED", "CANCELLED", "NO_SHOW"];

/** NO SHOW can only be reported 80 minutes after the job time (ARR + DEP) */
const NO_SHOW_DELAY_MS = 80 * 60 * 1000;

export default function DriverDashboardPage() {
  const t = useT();
  const locale = useLocaleId();
  const [jobs, setJobs] = useState<DriverJob[]>([]);
  const [notifications, setNotifications] = useState<Notification[]>([]);
  const [unreadCount, setUnreadCount] = useState(0);
  const [loading, setLoading] = useState(true);
  const [jobDetailId, setJobDetailId] = useState<string | null>(null);
  const [confirmDialog, setConfirmDialog] = useState<{
    open: boolean;
    jobId: string;
    jobRef: string;
    status: string;
  }>({ open: false, jobId: "", jobRef: "", status: "" });
  const [noShowDialog, setNoShowDialog] = useState<{
    open: boolean;
    jobId: string;
    jobRef: string;
  }>({ open: false, jobId: "", jobRef: "" });
  const [completedDialog, setCompletedDialog] = useState<{
    open: boolean;
    jobId: string;
    jobRef: string;
  }>({ open: false, jobId: "", jobRef: "" });
  const [inProgressDialog, setInProgressDialog] = useState<{
    open: boolean;
    jobId: string;
    jobRef: string;
  }>({ open: false, jobId: "", jobRef: "" });
  const [updating, setUpdating] = useState(false);
  const [collectingJobId, setCollectingJobId] = useState<string | null>(null);
  const [selectedDate, setSelectedDate] = useState(() => localDateStr(new Date()));

  const shiftDate = (days: number) => {
    const d = new Date(selectedDate);
    d.setDate(d.getDate() + days);
    setSelectedDate(localDateStr(d));
  };

  const fetchJobs = useCallback(async () => {
    try {
      const { data } = await api.get("/driver-portal/jobs", {
        params: { date: selectedDate },
      });
      setJobs(data.data?.jobs ?? []);
    } catch {
      toast.error(t("portal.failedLoadJobs"));
    }
  }, [selectedDate]);

  const fetchNotifications = useCallback(async () => {
    try {
      const { data } = await api.get("/driver-portal/notifications");
      setNotifications(data.data?.notifications ?? []);
      setUnreadCount(data.data?.unreadCount ?? 0);
    } catch {
      // ignore
    }
  }, []);

  const fetchAll = useCallback(async () => {
    setLoading(true);
    await Promise.all([fetchJobs(), fetchNotifications()]);
    setLoading(false);
  }, [fetchJobs, fetchNotifications]);

  useEffect(() => {
    fetchAll();
  }, [fetchAll]);

  const handleMarkCollected = async (jobId: string) => {
    setCollectingJobId(jobId);
    try {
      await api.patch(`/driver-portal/jobs/${jobId}/collection`, { collected: true });
      toast.success(t("portal.collectionMarked") || "Collection marked");
      fetchJobs();
    } catch {
      toast.error(t("portal.collectionError") || "Failed to mark collection");
    } finally {
      setCollectingJobId(null);
    }
  };

  const handleStatusChange = (jobId: string, jobRef: string, status: string) => {
    if (status === "NO_SHOW") {
      setNoShowDialog({ open: true, jobId, jobRef });
      return;
    }
    if (status === "COMPLETED") {
      setCompletedDialog({ open: true, jobId, jobRef });
      return;
    }
    if (status === "IN_PROGRESS") {
      setInProgressDialog({ open: true, jobId, jobRef });
      return;
    }
    setConfirmDialog({ open: true, jobId, jobRef, status });
  };

  const confirmStatusChange = async () => {
    setUpdating(true);
    try {
      toast.info(t("portal.capturingLocation"));
      // GPS is mandatory: abort the status change if a fix can't be obtained so
      // location is never missing from the audit trail.
      const gps = await captureGPS();
      await api.patch(`/driver-portal/jobs/${confirmDialog.jobId}/status`, {
        status: confirmDialog.status,
        latitude: gps.lat,
        longitude: gps.lng,
      });
      toast.success(t("portal.jobMarkedAs").replace("{ref}", confirmDialog.jobRef).replace("{status}", confirmDialog.status.replace("_", " ")));
      setConfirmDialog({ open: false, jobId: "", jobRef: "", status: "" });
      fetchJobs();
    } catch (err: unknown) {
      const message =
        (err as { response?: { data?: { message?: string } } })?.response?.data
          ?.message || (err instanceof Error ? err.message : t("portal.failedUpdateStatus"));
      toast.error(message);
    } finally {
      setUpdating(false);
    }
  };

  const markNotificationRead = async (id: string) => {
    try {
      await api.patch(`/driver-portal/notifications/${id}/read`);
      setNotifications((prev) =>
        prev.map((n) => (n.id === id ? { ...n, isRead: true } : n))
      );
      setUnreadCount((c) => Math.max(0, c - 1));
    } catch {
      // ignore
    }
  };

  const markAllRead = async () => {
    try {
      await api.patch("/driver-portal/notifications/read-all");
      setNotifications((prev) => prev.map((n) => ({ ...n, isRead: true })));
      setUnreadCount(0);
    } catch {
      // ignore
    }
  };

  const formatTime = (isoString: string | null) => {
    if (!isoString) return null;
    // Always render operational times in Africa/Cairo, never the device timezone.
    return new Date(isoString).toLocaleTimeString(locale, {
      timeZone: "Africa/Cairo",
      hour: "2-digit",
      minute: "2-digit",
      hour12: false,
    });
  };

  const activeJobs = jobs.filter((j) => !TERMINAL_STATUSES.includes(j.driverStatus));
  const completedJobs = jobs.filter((j) => TERMINAL_STATUSES.includes(j.driverStatus));

  if (loading) {
    return (
      <div className="flex items-center justify-center py-20">
        <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-foreground">{t("portal.myJobs")}</h1>
        <Button variant="outline" size="sm" onClick={fetchAll}>
          <RefreshCw className="mr-1.5 h-3.5 w-3.5" />
          {t("portal.refresh")}
        </Button>
      </div>

      {/* Date Selector */}
      <div className="flex items-center gap-2">
        <Button variant="outline" size="icon" className="h-9 w-9" onClick={() => shiftDate(-1)}>
          <ChevronLeft className="h-4 w-4" />
        </Button>
        <div className="relative">
          <CalendarDays className="pointer-events-none absolute left-2.5 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
          <input
            type="date"
            value={selectedDate}
            onChange={(e) => e.target.value && setSelectedDate(e.target.value)}
            className="h-9 rounded-md border border-border bg-card pl-9 pr-3 text-sm text-foreground"
          />
        </div>
        <Button variant="outline" size="icon" className="h-9 w-9" onClick={() => shiftDate(1)}>
          <ChevronRight className="h-4 w-4" />
        </Button>
        <Button
          variant="ghost"
          size="sm"
          className="text-xs"
          onClick={() => setSelectedDate(localDateStr(new Date()))}
        >
          {t("portal.today")}
        </Button>
      </div>

      {/* Active Jobs */}
      {activeJobs.length === 0 && completedJobs.length === 0 ? (
        <Card>
          <CardContent className="flex flex-col items-center justify-center py-12">
            <Briefcase className="mb-3 h-10 w-10 text-muted-foreground/40" />
            <p className="text-sm text-muted-foreground">
              {t("portal.noJobs")}
            </p>
          </CardContent>
        </Card>
      ) : (
        <>
          {activeJobs.length > 0 && (
            <div className="space-y-3">
              <h2 className="text-sm font-medium text-muted-foreground uppercase tracking-wider">
                {t("portal.active")} ({activeJobs.length})
              </h2>
              <div className="grid gap-3">
                {activeJobs.map((job) => (
                  <DriverJobCard
                    key={job.id}
                    job={job}
                    onStatusChange={handleStatusChange}
                    onMarkCollected={handleMarkCollected}
                    onViewDetail={setJobDetailId}
                    collectingJobId={collectingJobId}
                    formatTime={formatTime}
                  />
                ))}
              </div>
            </div>
          )}

          {completedJobs.length > 0 && (
            <div className="space-y-3">
              <h2 className="text-sm font-medium text-muted-foreground uppercase tracking-wider">
                {t("portal.completedClosed")} ({completedJobs.length})
              </h2>
              <div className="grid gap-3">
                {completedJobs.map((job) => (
                  <DriverJobCard
                    key={job.id}
                    job={job}
                    onStatusChange={handleStatusChange}
                    onMarkCollected={handleMarkCollected}
                    onViewDetail={setJobDetailId}
                    collectingJobId={collectingJobId}
                    formatTime={formatTime}
                  />
                ))}
              </div>
            </div>
          )}
        </>
      )}

      {/* Notifications */}
      <div className="space-y-3" id="notifications">
        <div className="flex items-center justify-between">
          <h2 className="text-sm font-medium text-muted-foreground uppercase tracking-wider">
            <Bell className="mr-1 inline h-4 w-4" />
            {t("portal.notifications")}
            {unreadCount > 0 && (
              <Badge variant="destructive" className="ml-2 text-xs">
                {unreadCount}
              </Badge>
            )}
          </h2>
          {unreadCount > 0 && (
            <Button variant="ghost" size="sm" onClick={markAllRead}>
              {t("portal.markAllRead")}
            </Button>
          )}
        </div>

        {notifications.length === 0 ? (
          <Card>
            <CardContent className="py-8 text-center text-sm text-muted-foreground">
              {t("portal.noNotifications")}
            </CardContent>
          </Card>
        ) : (
          <div className="space-y-2">
            {notifications.map((n) => (
              <Card
                key={n.id}
                className={`cursor-pointer transition-colors ${!n.isRead ? "border-primary/30 bg-primary/5" : ""}`}
                onClick={() => !n.isRead && markNotificationRead(n.id)}
              >
                <CardContent className="flex items-start gap-3 py-3">
                  <Bell
                    className={`mt-0.5 h-4 w-4 shrink-0 ${!n.isRead ? "text-primary" : "text-muted-foreground"}`}
                  />
                  <div className="min-w-0 flex-1">
                    <p
                      className={`text-sm ${!n.isRead ? "font-medium text-foreground" : "text-muted-foreground"}`}
                    >
                      {n.title}
                    </p>
                    <p className="text-xs text-muted-foreground">{n.message}</p>
                    <p className="mt-1 text-xs text-muted-foreground/60">
                      {new Date(n.createdAt).toLocaleString(locale)}
                    </p>
                  </div>
                  {!n.isRead && (
                    <div className="mt-1 h-2 w-2 shrink-0 rounded-full bg-primary" />
                  )}
                </CardContent>
              </Card>
            ))}
          </div>
        )}
      </div>

      {/* Status Confirmation Dialog */}
      <Dialog
        open={confirmDialog.open}
        onOpenChange={(open) => {
          if (!open) setConfirmDialog({ open: false, jobId: "", jobRef: "", status: "" });
        }}
      >
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{t("portal.confirmStatusChange")}</DialogTitle>
            <DialogDescription>
              {t("portal.confirmStatusMsg")}{" "}
              <span className="font-semibold">{confirmDialog.jobRef}</span> {t("portal.as")}{" "}
              <span className="font-semibold">
                {confirmDialog.status.replace("_", " ")}
              </span>
              {t("portal.cannotBeUndone")}
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button
              variant="outline"
              onClick={() =>
                setConfirmDialog({ open: false, jobId: "", jobRef: "", status: "" })
              }
              disabled={updating}
            >
              {t("common.cancel")}
            </Button>
            <Button
              onClick={confirmStatusChange}
              disabled={updating}
              variant={confirmDialog.status === "COMPLETED" ? "default" : "destructive"}
            >
              {updating && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
              {t("portal.confirm")}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* No Show Evidence Dialog */}
      <NoShowEvidenceDialog
        open={noShowDialog.open}
        onOpenChange={(open) => {
          if (!open) setNoShowDialog({ open: false, jobId: "", jobRef: "" });
        }}
        jobId={noShowDialog.jobId}
        jobRef={noShowDialog.jobRef}
        portalApiBase="/driver-portal"
        onSuccess={fetchJobs}
      />

      {/* Completed Evidence Dialog */}
      <CompletedEvidenceDialog
        open={completedDialog.open}
        onOpenChange={(open) => {
          if (!open) setCompletedDialog({ open: false, jobId: "", jobRef: "" });
        }}
        jobId={completedDialog.jobId}
        jobRef={completedDialog.jobRef}
        portalApiBase="/driver-portal"
        onSuccess={fetchJobs}
      />

      {/* In Progress Evidence Dialog */}
      <InProgressEvidenceDialog
        open={inProgressDialog.open}
        onOpenChange={(open) => {
          if (!open) setInProgressDialog({ open: false, jobId: "", jobRef: "" });
        }}
        jobId={inProgressDialog.jobId}
        jobRef={inProgressDialog.jobRef}
        portalApiBase="/driver-portal"
        onSuccess={fetchJobs}
      />

      <JobDetailModal
        jobId={jobDetailId}
        open={jobDetailId !== null}
        onClose={() => setJobDetailId(null)}
        apiBase="/driver-portal/jobs"
      />
    </div>
  );
}

function DriverJobCard({
  job,
  onStatusChange,
  onMarkCollected,
  onViewDetail,
  collectingJobId,
  formatTime,
}: {
  job: DriverJob;
  onStatusChange: (jobId: string, jobRef: string, status: string) => void;
  onMarkCollected: (jobId: string) => void;
  onViewDetail: (jobId: string) => void;
  collectingJobId: string | null;
  formatTime: (iso: string | null) => string | null;
}) {
  const t = useT();
  const serviceTypeLabel = useServiceTypeLabel();
  const driverStatus = job.driverStatus;
  const isTerminal = TERMINAL_STATUSES.includes(driverStatus);
  const flightTime =
    job.serviceType === "ARR"
      ? formatTime(job.flight?.arrivalTime ?? null)
      : formatTime(job.flight?.departureTime ?? null);

  // Compute job reference time for time guards
  const jobTime = (() => {
    const rawTime = job.serviceType === "ARR"
      ? job.flight?.arrivalTime
      : job.pickUpTime;
    return rawTime ? new Date(rawTime) : null;
  })();
  const now = new Date();
  const canStartProgress = !jobTime || now >= jobTime;
  const canComplete = !jobTime || now >= new Date(jobTime.getTime() + 15 * 60 * 1000);
  const progressBlockMsg = jobTime && !canStartProgress
    ? `${t("portal.availableFrom")} ${jobTime.toLocaleTimeString("en-GB", { timeZone: "Africa/Cairo", hour: "2-digit", minute: "2-digit", hour12: false })}`
    : "";
  const completeBlockMsg = jobTime && !canComplete
    ? `${t("portal.availableFrom")} ${new Date(jobTime.getTime() + 15 * 60 * 1000).toLocaleTimeString("en-GB", { timeZone: "Africa/Cairo", hour: "2-digit", minute: "2-digit", hour12: false })}`
    : "";
  // NO SHOW only becomes available 80 minutes after the job time (ARR + DEP)
  const canNoShow = !jobTime || now >= new Date(jobTime.getTime() + NO_SHOW_DELAY_MS);
  const noShowBlockMsg = jobTime && !canNoShow
    ? `${t("portal.availableFrom")} ${new Date(jobTime.getTime() + NO_SHOW_DELAY_MS).toLocaleTimeString("en-GB", { timeZone: "Africa/Cairo", hour: "2-digit", minute: "2-digit", hour12: false })}`
    : "";

  return (
    <Card className={isTerminal ? "opacity-60" : ""}>
      <CardContent className="p-4">
        {/* Top row: ref + badges */}
        <div className="flex flex-wrap items-center gap-2">
          <button
            type="button"
            onClick={() => onViewDetail(job.id)}
            className="font-mono text-sm font-semibold text-primary hover:underline"
          >
            {job.internalRef}
          </button>
          <Badge
            variant="outline"
            className={SERVICE_TYPE_COLORS[job.serviceType] || ""}
          >
            {serviceTypeLabel(job.serviceType)}
          </Badge>
          <Badge
            variant="outline"
            className={STATUS_COLORS[driverStatus] || ""}
          >
            {driverStatus.replace("_", " ")}
          </Badge>
          {job.agentRef && (
            <span className="ml-auto text-xs text-muted-foreground">
              {job.agentRef}
            </span>
          )}
        </div>

        {/* Time info: arrival time for ARR, pickup time for DEP/other */}
        <div className="mt-2 flex flex-wrap items-center gap-3 text-sm">
          {job.serviceType === "ARR" && job.flight?.arrivalTime && (
            <span className="flex items-center gap-1 font-medium text-blue-400">
              <Plane className="h-3.5 w-3.5" />
              {t("portal.arrivalTime") || "Arrival"}: {formatTime(job.flight.arrivalTime)}
            </span>
          )}
          {job.serviceType !== "ARR" && job.pickUpTime && (
            <span className="flex items-center gap-1 font-medium text-orange-400">
              <Clock className="h-3.5 w-3.5" />
              {t("portal.pickUpTime") || "Pickup"}: {formatTime(job.pickUpTime)}
            </span>
          )}
          {job.flight && (
            <span className="flex items-center gap-1 text-muted-foreground">
              <Plane className="h-3.5 w-3.5" />
              {job.flight.carrier} {job.flight.flightNo}
              {job.flight.terminal && <span className="ml-1">T{job.flight.terminal}</span>}
            </span>
          )}
        </div>

        {/* Route */}
        <div className="mt-2 flex flex-wrap items-center gap-3 text-sm text-muted-foreground">
          <span className="flex items-center gap-1">
            <MapPin className="h-3.5 w-3.5" />
            {job.originAirport?.code || job.originHotel?.name || job.originZone?.name || job.fromZone?.name || "—"} &rarr; {job.destinationAirport?.code || job.destinationHotel?.name || job.destinationZone?.name || job.toZone?.name || "—"}
          </span>
        </div>

        {/* Pax + vehicle + rep */}
        <div className="mt-2 flex flex-wrap items-center gap-3 text-sm text-muted-foreground">
          <span className="flex items-center gap-1">
            <Users className="h-3.5 w-3.5" />
            {job.paxCount} {t("portal.pax")}
          </span>
          {job.assignment?.vehicle && (
            <span className="flex items-center gap-1">
              <Car className="h-3.5 w-3.5" />
              {job.assignment.vehicle.plateNumber}
              {job.assignment.vehicle.vehicleType && (
                <span className="text-xs">
                  ({job.assignment.vehicle.vehicleType.name})
                </span>
              )}
            </span>
          )}
          {job.assignment?.rep && (
            <span className="flex items-center gap-1 text-xs">
              <User className="h-3.5 w-3.5" />
              {t("portal.repLabel")} {job.assignment.rep.name} ({job.assignment.rep.mobileNumber})
            </span>
          )}
          {job.assignment?.externalDriverName && (
            <span className="flex items-center gap-1 text-xs">
              <User className="h-3.5 w-3.5" />
              {t("portal.driverLabel")} {job.assignment.externalDriverName}
              {job.assignment.externalDriverPhone && ` (${job.assignment.externalDriverPhone})`}
              {job.assignment.supplier && (
                <span className="text-muted-foreground"> — {job.assignment.supplier.tradeName ?? job.assignment.supplier.legalName}</span>
              )}
            </span>
          )}
        </div>

        {/* Online client info */}
        {job.bookingChannel === "ONLINE" && job.clientName && (
          <div className="mt-2 flex flex-wrap gap-x-3 gap-y-1 rounded-md border border-blue-500/20 bg-blue-500/5 px-2.5 py-1.5 text-xs">
            <span className="text-blue-400 font-medium">{t("portal.onlineClient")}:</span>
            <span className="text-foreground font-semibold">{job.clientName}</span>
          </div>
        )}

        {/* Customer Rep Meeting Info */}
        {(job.custRepName || job.custRepMobile || job.custRepMeetingPoint || job.custRepMeetingTime) && (
          <div className="mt-2 flex flex-wrap gap-x-3 gap-y-1 text-xs text-muted-foreground">
            {job.custRepName && <span>{t("jobs.custRepName")}: <b className="text-foreground">{job.custRepName}</b></span>}
            {job.custRepMobile && (
              <a href={`tel:${job.custRepMobile}`} className="text-blue-400 underline">
                {job.custRepMobile}
              </a>
            )}
            {job.custRepMeetingPoint && <span>{t("jobs.custRepMeetingPoint")}: <b className="text-foreground">{job.custRepMeetingPoint}</b></span>}
            {job.custRepMeetingTime && <span>{t("jobs.custRepMeetingTime")}: <b className="text-foreground">{new Date(job.custRepMeetingTime).toLocaleTimeString([], { timeZone: "Africa/Cairo", hour: "2-digit", minute: "2-digit", hour12: false })}</b></span>}
          </div>
        )}

        {/* Notes */}
        {job.notes && (
          <p className="mt-2 text-xs text-muted-foreground/70 italic">
            {job.notes}
          </p>
        )}

        {/* Collection banner */}
        {job.collectionRequired && (
          <div className={`mt-2 flex items-center gap-2 rounded-md border px-3 py-2 text-sm ${job.collectionCollected ? "border-emerald-500/30 bg-emerald-500/10" : "border-amber-500/30 bg-amber-500/10"}`}>
            <DollarSign className={`h-4 w-4 ${job.collectionCollected ? "text-emerald-500" : "text-amber-500"}`} />
            <span className="font-medium text-foreground">
              {job.collectionAmount} {job.collectionCurrency}
            </span>
            {job.collectionCollected ? (
              <Badge variant="outline" className="ml-auto border-emerald-500/50 text-emerald-500 text-xs">
                {t("portal.collected") || "Collected"}
              </Badge>
            ) : (
              <Button
                size="sm"
                variant="outline"
                className="ml-auto gap-1.5 border-amber-500/50 text-amber-500 hover:bg-amber-500/20 hover:text-amber-400"
                onClick={() => onMarkCollected(job.id)}
                disabled={collectingJobId === job.id}
              >
                {collectingJobId === job.id ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <DollarSign className="h-3.5 w-3.5" />}
                {t("portal.markCollected") || "Mark Collected"}
              </Button>
            )}
          </div>
        )}

        {/* Action buttons */}
        {!isTerminal && (
          <div className="mt-3 flex flex-wrap gap-2 border-t border-border pt-3">
            {driverStatus === "PENDING" && (
              <Button
                size="sm"
                variant="outline"
                className="gap-1.5 text-cyan-400 hover:text-cyan-300 disabled:opacity-50"
                onClick={() => onStatusChange(job.id, job.internalRef, "IN_PROGRESS")}
                disabled={!canStartProgress}
                title={progressBlockMsg || undefined}
              >
                <PlayCircle className="h-3.5 w-3.5" />
                {t("portal.inProgress")}
                {!canStartProgress && progressBlockMsg && (
                  <span className="ml-1 text-[10px] opacity-70">({progressBlockMsg})</span>
                )}
              </Button>
            )}
            <Button
              size="sm"
              variant="default"
              className="gap-1.5"
              onClick={() => onStatusChange(job.id, job.internalRef, "COMPLETED")}
              disabled={driverStatus !== "IN_PROGRESS" || (job.collectionRequired && !job.collectionCollected) || !canComplete}
              title={
                driverStatus !== "IN_PROGRESS"
                  ? t("portal.startInProgressFirst")
                  : job.collectionRequired && !job.collectionCollected
                  ? (t("portal.collectionRequiredBeforeComplete") || "Collect payment before completing")
                  : completeBlockMsg || undefined
              }
            >
              <CheckCircle2 className="h-3.5 w-3.5" />
              {t("portal.complete")}
              {!canComplete && driverStatus === "IN_PROGRESS" && completeBlockMsg && (
                <span className="ml-1 text-[10px] opacity-70">({completeBlockMsg})</span>
              )}
            </Button>
            <Button
              size="sm"
              variant="outline"
              className="gap-1.5 text-orange-400 hover:text-orange-300"
              onClick={() => onStatusChange(job.id, job.internalRef, "NO_SHOW")}
              disabled={!canNoShow}
              title={noShowBlockMsg || undefined}
            >
              <UserX className="h-3.5 w-3.5" />
              {t("portal.noShow")}
              {!canNoShow && noShowBlockMsg && (
                <span className="ml-1 text-[10px] opacity-70">({noShowBlockMsg})</span>
              )}
            </Button>
            <Button
              size="sm"
              variant="outline"
              className="gap-1.5 text-destructive hover:text-destructive"
              onClick={() => onStatusChange(job.id, job.internalRef, "CANCELLED")}
            >
              <XCircle className="h-3.5 w-3.5" />
              {t("portal.cancelJob")}
            </Button>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
