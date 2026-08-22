"use client";

import { useState, useEffect, useCallback } from "react";
import { toast } from "sonner";
import {
  ChevronLeft,
  ChevronRight,
  Loader2,
  CheckCircle2,
  Clock,
  MapPin,
  Plane,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Textarea } from "@/components/ui/textarea";
import api from "@/lib/api";
import { useT } from "@/lib/i18n";
import { localDateStr } from "@/lib/utils";
import JobDetailModal from "@/components/job-detail-modal";

interface SupplierJob {
  id: string;
  internalRef: string;
  serviceType: string;
  jobDate: string;
  status: string;
  clientName: string | null;
  paxCount: number;
  notes: string | null;
  supplierStatus: string;
  supplierNotes: string | null;
  fromZone?: { name: string } | null;
  toZone?: { name: string } | null;
  originAirport?: { code: string } | null;
  destinationAirport?: { code: string } | null;
  originHotel?: { name: string } | null;
  destinationHotel?: { name: string } | null;
  originZone?: { name: string } | null;
  destinationZone?: { name: string } | null;
  flight?: { flightNo: string; carrier?: string; arrivalTime?: string; departureTime?: string } | null;
  assignment?: {
    vehicle?: { plateNumber: string; vehicleType?: { name: string } } | null;
    driver?: { name: string; mobileNumber: string } | null;
  } | null;
}

export default function SupplierJobsPage() {
  const t = useT();
  const [date, setDate] = useState(() => localDateStr(new Date()));
  const [jobs, setJobs] = useState<SupplierJob[]>([]);
  const [loading, setLoading] = useState(true);
  const [jobDetailId, setJobDetailId] = useState<string | null>(null);
  const [completing, setCompleting] = useState<string | null>(null);
  const [notesMap, setNotesMap] = useState<Record<string, string>>({});

  const fetchJobs = useCallback(async (d: string) => {
    setLoading(true);
    try {
      const { data } = await api.get(`/supplier-portal/jobs?date=${d}`);
      setJobs(data.data?.jobs || []);
    } catch {
      toast.error("Failed to load jobs");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchJobs(date);
  }, [date, fetchJobs]);

  const navigateDay = (dir: -1 | 1) => {
    const d = new Date(date);
    d.setDate(d.getDate() + dir);
    setDate(localDateStr(d));
  };

  const handleComplete = async (jobId: string) => {
    setCompleting(jobId);
    try {
      await api.patch(`/supplier-portal/jobs/${jobId}/complete`, {
        notes: notesMap[jobId] || undefined,
      });
      toast.success(t("supplierPortal.completedSuccess"));
      setJobs((prev) =>
        prev.map((j) =>
          j.id === jobId
            ? { ...j, supplierStatus: "COMPLETED", supplierNotes: notesMap[jobId] || null }
            : j,
        ),
      );
    } catch {
      toast.error(t("supplierPortal.completeFailed"));
    } finally {
      setCompleting(null);
    }
  };

  return (
    <div className="space-y-4">
      {/* Date navigation */}
      <div className="flex items-center justify-between">
        <Button variant="ghost" size="icon" onClick={() => navigateDay(-1)}>
          <ChevronLeft className="h-5 w-5" />
        </Button>
        <div className="text-center">
          <p className="text-lg font-semibold text-foreground">
            {new Date(date).toLocaleDateString(undefined, {
              weekday: "long",
              month: "long",
              day: "numeric",
            })}
          </p>
          <p className="text-xs text-muted-foreground">
            {jobs.length} job{jobs.length !== 1 ? "s" : ""}
          </p>
        </div>
        <Button variant="ghost" size="icon" onClick={() => navigateDay(1)}>
          <ChevronRight className="h-5 w-5" />
        </Button>
      </div>

      {loading ? (
        <div className="flex items-center justify-center py-20">
          <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
        </div>
      ) : jobs.length === 0 ? (
        <div className="py-20 text-center text-sm text-muted-foreground">
          {t("supplierPortal.noJobs")}
        </div>
      ) : (
        <div className="space-y-3">
          {jobs.map((job) => {
            const isCompleted = job.supplierStatus === "COMPLETED";
            const originLabel = job.originAirport?.code || job.originHotel?.name || job.originZone?.name || job.fromZone?.name || "—";
            const destLabel = job.destinationAirport?.code || job.destinationHotel?.name || job.destinationZone?.name || job.toZone?.name || "—";
            const route = `${originLabel} → ${destLabel}`;

            return (
              <Card key={job.id} className="overflow-hidden">
                <div className="p-4 space-y-3">
                  {/* Header */}
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <button
                        type="button"
                        onClick={() => setJobDetailId(job.id)}
                        className="text-xs font-mono text-primary hover:underline border border-border rounded px-2 py-0.5"
                      >
                        {job.internalRef}
                      </button>
                      <Badge
                        className={
                          isCompleted
                            ? "bg-green-500/10 text-green-500 border-green-500/20"
                            : "bg-amber-500/10 text-amber-500 border-amber-500/20"
                        }
                      >
                        {isCompleted
                          ? t("supplierPortal.completed")
                          : t("supplierPortal.pending")}
                      </Badge>
                    </div>
                    <Badge variant="secondary" className="text-xs">
                      {job.serviceType}
                    </Badge>
                  </div>

                  {/* Route */}
                  {route && (
                    <div className="flex items-center gap-2 text-sm">
                      <MapPin className="h-4 w-4 text-muted-foreground" />
                      <span className="text-foreground">{route}</span>
                    </div>
                  )}

                  {/* Flight info */}
                  {job.flight && (
                    <div className="flex items-center gap-2 text-sm">
                      <Plane className="h-4 w-4 text-muted-foreground" />
                      <span className="text-muted-foreground">
                        {job.flight.flightNo}
                        {job.flight.carrier && ` (${job.flight.carrier})`}
                      </span>
                    </div>
                  )}

                  {/* Vehicle & Driver */}
                  {job.assignment && (
                    <div className="text-xs text-muted-foreground space-y-0.5">
                      {job.assignment.vehicle && (
                        <p>
                          Vehicle: {job.assignment.vehicle.plateNumber}
                          {job.assignment.vehicle.vehicleType && ` - ${job.assignment.vehicle.vehicleType.name}`}
                        </p>
                      )}
                      {job.assignment.driver && (
                        <p>
                          Driver: {job.assignment.driver.name} ({job.assignment.driver.mobileNumber})
                        </p>
                      )}
                    </div>
                  )}

                  {/* Pax + Client */}
                  <div className="text-xs text-muted-foreground">
                    {job.paxCount} pax
                    {job.clientName && ` — ${job.clientName}`}
                  </div>

                  {/* Notes input + Complete button */}
                  {!isCompleted && (
                    <div className="space-y-2 pt-1">
                      <Textarea
                        placeholder={t("supplierPortal.notesPlaceholder")}
                        value={notesMap[job.id] || ""}
                        onChange={(e) =>
                          setNotesMap((prev) => ({ ...prev, [job.id]: e.target.value }))
                        }
                        className="min-h-[60px] text-sm"
                      />
                      <Button
                        onClick={() => handleComplete(job.id)}
                        disabled={completing === job.id}
                        className="w-full gap-2"
                        size="sm"
                      >
                        {completing === job.id ? (
                          <Loader2 className="h-4 w-4 animate-spin" />
                        ) : (
                          <CheckCircle2 className="h-4 w-4" />
                        )}
                        {t("supplierPortal.markComplete")}
                      </Button>
                    </div>
                  )}

                  {/* Show notes if completed */}
                  {isCompleted && job.supplierNotes && (
                    <div className="rounded-md bg-muted/50 p-2 text-xs text-muted-foreground">
                      <p className="font-medium">{t("supplierPortal.notes")}:</p>
                      <p>{job.supplierNotes}</p>
                    </div>
                  )}
                </div>
              </Card>
            );
          })}
        </div>
      )}

      <JobDetailModal
        jobId={jobDetailId}
        open={jobDetailId !== null}
        onClose={() => setJobDetailId(null)}
        apiBase="/supplier-portal/jobs"
      />
    </div>
  );
}
