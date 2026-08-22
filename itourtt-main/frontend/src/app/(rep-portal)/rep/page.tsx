"use client";

import { useEffect, useState, useCallback } from "react";
import api from "@/lib/api";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
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
  ChevronLeft,
  ChevronRight,
  MapPinCheck,
  AlertTriangle,
  ClipboardList,
} from "lucide-react";
import JobDetailModal from "@/components/job-detail-modal";
import { toast } from "sonner";
import { NoShowEvidenceDialog } from "@/components/no-show-evidence-dialog";
import { InPlaceEvidenceDialog } from "@/components/in-place-evidence-dialog";
import { CompletedEvidenceDialog } from "@/components/completed-evidence-dialog";
import { GuestSurveyDialog } from "@/components/guest-survey-dialog";
import { useT, useLocaleId } from "@/lib/i18n";
import { formatDate , localDateStr, formatTimeCairo, dateStrCairo, cairoWallclockToISO } from "@/lib/utils";
import { captureGPS } from "@/lib/gps";
import { SERVICE_TYPE_COLORS, useServiceTypeLabel } from "@/lib/service-types";

interface RepJob {
  id: string;
  internalRef: string;
  agentRef: string | null;
  serviceType: string;
  jobDate: string;
  status: string;
  repStatus: string;
  repUnlockedAt: string | null;
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
  guestSurvey?: { id: string } | null;
  assignment?: {
    vehicle?: { plateNumber: string; vehicleType?: { name: string } };
    driver?: { name: string; mobileNumber: string };
    externalDriverName?: string | null;
    externalDriverPhone?: string | null;
    supplier?: { tradeName?: string | null; legalName: string };
  };
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
  IN_PLACE: "bg-emerald-500/10 text-emerald-400 border-emerald-500/20",
  COMPLETED: "bg-green-500/10 text-green-400 border-green-500/20",
  CANCELLED: "bg-red-500/10 text-red-400 border-red-500/20",
  NO_SHOW: "bg-gray-500/10 text-gray-400 border-gray-500/20",
};

const TERMINAL_STATUSES = ["COMPLETED", "CANCELLED", "NO_SHOW"];

/** NO SHOW can only be reported 80 minutes after the job time (ARR + DEP) */
const NO_SHOW_DELAY_MS = 80 * 60 * 1000;

export default function RepDashboardPage() {
  const t = useT();
  const locale = useLocaleId();
  const [jobs, setJobs] = useState<RepJob[]>([]);
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
  const [updating, setUpdating] = useState(false);
  const [noShowDialog, setNoShowDialog] = useState<{
    open: boolean;
    jobId: string;
    jobRef: string;
  }>({ open: false, jobId: "", jobRef: "" });
  const [inPlaceDialog, setInPlaceDialog] = useState<{
    open: boolean;
    jobId: string;
    jobRef: string;
  }>({ open: false, jobId: "", jobRef: "" });
  const [completedDialog, setCompletedDialog] = useState<{
    open: boolean;
    jobId: string;
    jobRef: string;
  }>({ open: false, jobId: "", jobRef: "" });
  const [surveyDialog, setSurveyDialog] = useState<{
    open: boolean;
    jobId: string;
    jobRef: string;
  }>({ open: false, jobId: "", jobRef: "" });
  const [flightDelayDialog, setFlightDelayDialog] = useState<{
    open: boolean;
    jobId: string;
    jobRef: string;
    oldServiceDate: string | null;
    currentArrivalTime: string | null;
  }>({ open: false, jobId: "", jobRef: "", oldServiceDate: null, currentArrivalTime: null });
  const [flightDelayDate, setFlightDelayDate] = useState("");
  const [flightDelayTime, setFlightDelayTime] = useState("");
  const [sendingDelay, setSendingDelay] = useState(false);
  const [selectedDate, setSelectedDate] = useState(() => localDateStr(new Date()));

  const shiftDate = (days: number) => {
    const d = new Date(selectedDate);
    d.setDate(d.getDate() + days);
    setSelectedDate(localDateStr(d));
  };

  const fetchJobs = useCallback(async () => {
    try {
      const { data } = await api.get("/rep-portal/jobs", {
        params: { date: selectedDate },
      });
      setJobs(data.data?.jobs ?? []);
    } catch {
      toast.error(t("portal.failedLoadJobs"));
    }
  }, [selectedDate]);

  const fetchNotifications = useCallback(async () => {
    try {
      const { data } = await api.get("/rep-portal/notifications");
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

  const handleStatusChange = (jobId: string, jobRef: string, status: string) => {
    if (status === "NO_SHOW") {
      setNoShowDialog({ open: true, jobId, jobRef });
      return;
    }
    if (status === "IN_PLACE") {
      setInPlaceDialog({ open: true, jobId, jobRef });
      return;
    }
    if (status === "COMPLETED") {
      setCompletedDialog({ open: true, jobId, jobRef });
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
      await api.patch(`/rep-portal/jobs/${confirmDialog.jobId}/status`, {
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

  const handleFlightDelay = async () => {
    if (!flightDelayDate || !flightDelayTime) return;
    setSendingDelay(true);
    try {
      // Entered date/time is a Cairo wall-clock; convert to a UTC instant
      // independent of the rep's device timezone.
      const newArrivalTime = cairoWallclockToISO(flightDelayDate, flightDelayTime);
      await api.patch(`/rep-portal/jobs/${flightDelayDialog.jobId}/flight-delay`, {
        arrivalTime: newArrivalTime,
      });
      toast.success(t("portal.flightDelayReported").replace("{ref}", flightDelayDialog.jobRef));
      setFlightDelayDialog({ open: false, jobId: "", jobRef: "", oldServiceDate: null, currentArrivalTime: null });
      setFlightDelayDate("");
      setFlightDelayTime("");
      fetchJobs();
    } catch (err: unknown) {
      const message =
        (err as { response?: { data?: { message?: string } } })?.response?.data
          ?.message || t("portal.flightDelayFailed");
      toast.error(message);
    } finally {
      setSendingDelay(false);
    }
  };

  const markNotificationRead = async (id: string) => {
    try {
      await api.patch(`/rep-portal/notifications/${id}/read`);
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
      await api.patch("/rep-portal/notifications/read-all");
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

  const activeJobs = jobs.filter((j) => !TERMINAL_STATUSES.includes(j.repStatus));
  const completedJobs = jobs.filter((j) => TERMINAL_STATUSES.includes(j.repStatus));

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
        <div className="flex items-center gap-2">
          <Button variant="outline" size="sm" onClick={fetchAll}>
            <RefreshCw className="mr-1.5 h-3.5 w-3.5" />
            {t("portal.refresh")}
          </Button>
        </div>
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
                  <JobCard
                    key={job.id}
                    job={job}
                    onStatusChange={handleStatusChange}
                    onFlightDelay={(jobId, jobRef, jobDate, arrivalTime) => {
                      setFlightDelayDate(dateStrCairo(arrivalTime ?? new Date()));
                      setFlightDelayTime(arrivalTime ? (formatTimeCairo(arrivalTime) ?? "") : "");
                      setFlightDelayDialog({ open: true, jobId, jobRef, oldServiceDate: jobDate, currentArrivalTime: arrivalTime });
                    }}
                    onSurvey={(jobId, jobRef) => setSurveyDialog({ open: true, jobId, jobRef })}
                    onViewDetail={setJobDetailId}
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
                  <JobCard
                    key={job.id}
                    job={job}
                    onStatusChange={handleStatusChange}
                    onFlightDelay={(jobId, jobRef, jobDate, arrivalTime) => {
                      setFlightDelayDate(dateStrCairo(arrivalTime ?? new Date()));
                      setFlightDelayTime(arrivalTime ? (formatTimeCairo(arrivalTime) ?? "") : "");
                      setFlightDelayDialog({ open: true, jobId, jobRef, oldServiceDate: jobDate, currentArrivalTime: arrivalTime });
                    }}
                    onSurvey={(jobId, jobRef) => setSurveyDialog({ open: true, jobId, jobRef })}
                    onViewDetail={setJobDetailId}
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
        portalApiBase="/rep-portal"
        onSuccess={fetchJobs}
      />

      {/* In Place Evidence Dialog */}
      <InPlaceEvidenceDialog
        open={inPlaceDialog.open}
        onOpenChange={(open) => {
          if (!open) setInPlaceDialog({ open: false, jobId: "", jobRef: "" });
        }}
        jobId={inPlaceDialog.jobId}
        jobRef={inPlaceDialog.jobRef}
        portalApiBase="/rep-portal"
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
        portalApiBase="/rep-portal"
        onSuccess={fetchJobs}
      />

      {/* Guest Survey Dialog */}
      <GuestSurveyDialog
        open={surveyDialog.open}
        onOpenChange={(open) => {
          if (!open) setSurveyDialog({ open: false, jobId: "", jobRef: "" });
        }}
        jobId={surveyDialog.jobId}
        jobRef={surveyDialog.jobRef}
        portalApiBase="/rep-portal"
        onSuccess={fetchJobs}
      />

      {/* Flight Delay Dialog */}
      <Dialog
        open={flightDelayDialog.open}
        onOpenChange={(open) => {
          if (!open) {
            setFlightDelayDialog({ open: false, jobId: "", jobRef: "", oldServiceDate: null, currentArrivalTime: null });
            setFlightDelayDate("");
            setFlightDelayTime("");
          }
        }}
      >
        <DialogContent>
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <AlertTriangle className="h-5 w-5 text-amber-400" />
              {t("portal.reportFlightDelay")}
            </DialogTitle>
            <DialogDescription>
              {t("portal.reportFlightDelayDesc").replace("{ref}", flightDelayDialog.jobRef)}
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
            <div className="grid grid-cols-2 gap-3 rounded-md border border-border bg-muted/40 px-3 py-2.5">
              <div className="space-y-0.5">
                <p className="text-xs text-muted-foreground">{t("portal.currentServiceDate")}</p>
                <p className="text-sm font-medium text-foreground">
                  {flightDelayDialog.oldServiceDate ?? "—"}
                </p>
              </div>
              <div className="space-y-0.5">
                <p className="text-xs text-muted-foreground">{t("portal.currentArrivalTime")}</p>
                <p className="text-sm font-medium text-foreground">
                  {flightDelayDialog.currentArrivalTime
                    ? (formatTimeCairo(flightDelayDialog.currentArrivalTime) ?? "—")
                    : "—"}
                </p>
              </div>
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-1.5">
                <label className="text-sm font-medium text-foreground">{t("portal.newArrivalDate")}</label>
                <input
                  type="date"
                  value={flightDelayDate}
                  onChange={(e) => setFlightDelayDate(e.target.value)}
                  className="w-full h-9 rounded-md border border-border bg-card px-3 text-sm text-foreground"
                />
              </div>
              <div className="space-y-1.5">
                <label className="text-sm font-medium text-foreground">{t("portal.newArrivalTime")}</label>
                <input
                  type="time"
                  value={flightDelayTime}
                  onChange={(e) => setFlightDelayTime(e.target.value)}
                  className="w-full h-9 rounded-md border border-border bg-card px-3 text-sm text-foreground"
                />
              </div>
            </div>
          </div>
          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => {
                setFlightDelayDialog({ open: false, jobId: "", jobRef: "", oldServiceDate: null, currentArrivalTime: null });
                setFlightDelayDate("");
                setFlightDelayTime("");
              }}
              disabled={sendingDelay}
            >
              {t("common.cancel")}
            </Button>
            <Button
              onClick={handleFlightDelay}
              disabled={!flightDelayDate || !flightDelayTime || sendingDelay}
              className="bg-amber-600 hover:bg-amber-700"
            >
              {sendingDelay && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
              {t("portal.reportDelay")}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <JobDetailModal
        jobId={jobDetailId}
        open={jobDetailId !== null}
        onClose={() => setJobDetailId(null)}
        apiBase="/rep-portal/jobs"
      />
    </div>
  );
}

function JobCard({
  job,
  onStatusChange,
  onFlightDelay,
  onSurvey,
  onViewDetail,
  formatTime,
}: {
  job: RepJob;
  onStatusChange: (jobId: string, jobRef: string, status: string) => void;
  onFlightDelay: (jobId: string, jobRef: string, jobDate: string, arrivalTime: string | null) => void;
  onSurvey: (jobId: string, jobRef: string) => void;
  onViewDetail: (jobId: string) => void;
  formatTime: (iso: string | null) => string | null;
}) {
  const t = useT();
  const serviceTypeLabel = useServiceTypeLabel();
  const repStatus = job.repStatus;
  const isTerminal = TERMINAL_STATUSES.includes(repStatus);
  const flightTime =
    job.serviceType === "ARR"
      ? formatTime(job.flight?.arrivalTime ?? null)
      : formatTime(job.flight?.departureTime ?? null);

  // IN PLACE is only active within 10 min before to 80 min after flight arrival
  const inPlaceWindowOpen = (() => {
    if (job.serviceType !== "ARR" || !job.flight?.arrivalTime || job.repUnlockedAt) return true;
    const now = new Date();
    const arr = new Date(job.flight.arrivalTime);
    return now >= new Date(arr.getTime() - 10 * 60 * 1000) &&
           now <= new Date(arr.getTime() + 80 * 60 * 1000);
  })();

  const inPlaceWindowMsg = (() => {
    if (!job.flight?.arrivalTime || inPlaceWindowOpen) return "";
    const arr = new Date(job.flight.arrivalTime);
    const start = new Date(arr.getTime() - 10 * 60 * 1000);
    const end = new Date(arr.getTime() + 80 * 60 * 1000);
    const fmt = (d: Date) => d.toLocaleTimeString("en-GB", { timeZone: "Africa/Cairo", hour: "2-digit", minute: "2-digit", hour12: false });
    return t("portal.availableWindow").replace("{start}", fmt(start)).replace("{end}", fmt(end));
  })();

  // NO SHOW only becomes available 80 minutes after the job time (ARR + DEP)
  const jobTime = (() => {
    const rawTime = job.serviceType === "ARR" ? job.flight?.arrivalTime : job.pickUpTime;
    return rawTime ? new Date(rawTime) : null;
  })();
  const canNoShow = !jobTime || new Date() >= new Date(jobTime.getTime() + NO_SHOW_DELAY_MS);
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
            className={STATUS_COLORS[repStatus] || ""}
          >
            {repStatus.replace("_", " ")}
          </Badge>
          {job.agentRef && (
            <span className="ml-auto text-xs text-muted-foreground">
              {job.agentRef}
            </span>
          )}
        </div>

        {/* Time info: driver arrival/pickup time + flight info */}
        <div className="mt-2 flex flex-wrap items-center gap-3 text-sm">
          {job.serviceType === "ARR" && job.flight?.arrivalTime && (
            <span className="flex items-center gap-1 font-medium text-blue-400">
              <Clock className="h-3.5 w-3.5" />
              {t("portal.driverArrival") || "Driver arrives"}: {formatTime(job.flight.arrivalTime)}
            </span>
          )}
          {job.serviceType !== "ARR" && job.pickUpTime && (
            <span className="flex items-center gap-1 font-medium text-orange-400">
              <Clock className="h-3.5 w-3.5" />
              {t("portal.driverPickup") || "Driver pickup"}: {formatTime(job.pickUpTime)}
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

        {/* Pax + vehicle + driver */}
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
          {job.assignment?.driver ? (
            <span className="text-xs">
              {t("portal.driverLabel")} {job.assignment.driver.name} ({job.assignment.driver.mobileNumber})
            </span>
          ) : job.assignment?.externalDriverName ? (
            <span className="text-xs">
              {t("portal.driverLabel")} <span className="font-medium text-amber-500">Supp.</span> {job.assignment.externalDriverName}
              {job.assignment.externalDriverPhone && ` (${job.assignment.externalDriverPhone})`}
              {job.assignment.supplier && (
                <span className="text-muted-foreground"> — {job.assignment.supplier.tradeName ?? job.assignment.supplier.legalName}</span>
              )}
            </span>
          ) : null}
        </div>

        {/* Online client info */}
        {job.bookingChannel === "ONLINE" && (job.clientName || job.clientMobile) && (
          <div className="mt-2 flex flex-wrap gap-x-3 gap-y-1 rounded-md border border-blue-500/20 bg-blue-500/5 px-2.5 py-1.5 text-xs">
            <span className="text-blue-400 font-medium">{t("portal.onlineClient")}:</span>
            {job.clientName && <span className="text-foreground font-semibold">{job.clientName}</span>}
            {job.clientMobile && (
              <a href={`tel:${job.clientMobile}`} className="text-blue-400 underline">
                {job.clientMobile}
              </a>
            )}
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

        {/* Action buttons */}
        <div className="mt-3 flex flex-wrap gap-2 border-t border-border pt-3">
          {!isTerminal && (
            <>
              {repStatus === "PENDING" && job.serviceType !== "DEP" && (
                <Button
                  size="sm"
                  variant="outline"
                  className="gap-1.5 text-emerald-400 hover:text-emerald-300 disabled:opacity-50"
                  onClick={() => onStatusChange(job.id, job.internalRef, "IN_PLACE")}
                  disabled={!inPlaceWindowOpen}
                  title={inPlaceWindowMsg || undefined}
                >
                  <MapPinCheck className="h-3.5 w-3.5" />
                  {t("portal.inPlace")}
                  {!inPlaceWindowOpen && inPlaceWindowMsg && (
                    <span className="ml-1 text-[10px] opacity-70">({inPlaceWindowMsg})</span>
                  )}
                </Button>
              )}
              <Button
                size="sm"
                variant="default"
                className="gap-1.5"
                onClick={() => onStatusChange(job.id, job.internalRef, "COMPLETED")}
                disabled={repStatus !== "IN_PLACE"}
                title={repStatus !== "IN_PLACE" ? t("portal.markInPlaceFirst") : undefined}
              >
                <CheckCircle2 className="h-3.5 w-3.5" />
                {t("portal.complete")}
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
            </>
          )}
          {job.serviceType === "ARR" && !isTerminal && (
            <Button
              size="sm"
              variant="outline"
              className="gap-1.5 text-amber-400 hover:text-amber-300"
              onClick={() => onFlightDelay(job.id, job.internalRef, job.jobDate, job.flight?.arrivalTime ?? null)}
            >
              <AlertTriangle className="h-3.5 w-3.5" />
              {t("portal.flightDelay")}
            </Button>
          )}
          {job.serviceType === "ARR" && (
            <Button
              size="sm"
              variant="outline"
              className={
                job.guestSurvey
                  ? "gap-1.5 text-emerald-400 hover:text-emerald-300"
                  : "gap-1.5 text-sky-400 hover:text-sky-300"
              }
              onClick={() => onSurvey(job.id, job.internalRef)}
              title={job.guestSurvey ? t("survey.alreadySubmitted") : undefined}
            >
              <ClipboardList className="h-3.5 w-3.5" />
              {t("portal.survey")}
              {job.guestSurvey && <CheckCircle2 className="h-3.5 w-3.5" />}
            </Button>
          )}
        </div>
      </CardContent>
    </Card>
  );
}

