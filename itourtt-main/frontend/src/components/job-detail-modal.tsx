"use client";

import { useState, useEffect } from "react";
import api from "@/lib/api";
import { Loader2 } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { useT } from "@/lib/i18n";

interface JobDetail {
  id: string;
  internalRef: string;
  agentRef: string | null;
  bookingChannel: string;
  serviceType: string;
  jobDate: string;
  pickUpTime: string | null;
  status: string;
  bookingStatus: string;
  adultCount: number;
  childCount: number;
  paxCount: number;
  clientName: string | null;
  clientMobile: string | null;
  notes: string | null;
  priceAmount: number | null;
  priceCurrency: string | null;
  transferPrice: number | null;
  transferPriceCurrency: string | null;
  jobExtras?: { name: string; qty: number }[];
  printSign: boolean;
  collectionRequired: boolean;
  collectionAmount: number | null;
  collectionCurrency: string | null;
  agent: { legalName: string; tradeName: string | null } | null;
  customer: { legalName: string } | null;
  originAirport: { code: string; name: string } | null;
  originZone: { name: string } | null;
  originHotel: { name: string } | null;
  destinationAirport: { code: string; name: string } | null;
  destinationZone: { name: string } | null;
  destinationHotel: { name: string } | null;
  flight: {
    flightNo: string;
    carrier: string | null;
    terminal: string | null;
    arrivalTime: string | null;
    departureTime: string | null;
  } | null;
  assignment: {
    vehicle: {
      plateNumber: string;
      vehicleType: { name: string } | null;
      supplier: { legalName: string; tradeName: string | null } | null;
    } | null;
    driver: { name: string; mobileNumber: string } | null;
    rep: { name: string; mobileNumber: string } | null;
    driverStatus: string | null;
    repStatus: string | null;
  } | null;
  createdBy: { name: string } | null;
  createdAt: string;
}

const STATUS_COLORS: Record<string, string> = {
  PENDING: "bg-yellow-500/15 text-yellow-600 border-yellow-500/30",
  ASSIGNED: "bg-blue-500/15 text-blue-600 border-blue-500/30",
  IN_PROGRESS: "bg-purple-500/15 text-purple-600 border-purple-500/30",
  COMPLETED: "bg-green-500/15 text-green-600 border-green-500/30",
  CANCELLED: "bg-red-500/15 text-red-600 border-red-500/30",
  NO_SHOW: "bg-orange-500/15 text-orange-600 border-orange-500/30",
  NEW: "bg-slate-500/15 text-slate-600 border-slate-500/30",
  CONFIRMED: "bg-green-500/15 text-green-600 border-green-500/30",
};

function Row({ label, value }: { label: string; value: React.ReactNode }) {
  if (!value && value !== 0) return null;
  return (
    <div className="flex gap-2 text-sm">
      <span className="text-muted-foreground min-w-[140px] shrink-0">{label}</span>
      <span className="text-foreground font-medium break-words">{value}</span>
    </div>
  );
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="space-y-2">
      <p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground border-b border-border pb-1">
        {title}
      </p>
      <div className="space-y-1.5">{children}</div>
    </div>
  );
}

function fmt(dt: string | null | undefined) {
  if (!dt) return null;
  return new Date(dt).toLocaleTimeString([], { timeZone: "Africa/Cairo", hour: "2-digit", minute: "2-digit", hour12: false });
}

function fmtDate(dt: string | null | undefined) {
  if (!dt) return null;
  return new Date(dt).toLocaleDateString("en-GB");
}

interface Props {
  jobId: string | null;
  open: boolean;
  onClose: () => void;
  /** Override API base path. Defaults to /traffic-jobs. Portal pages pass their own base. */
  apiBase?: string;
}

export default function JobDetailModal({ jobId, open, onClose, apiBase = "/traffic-jobs" }: Props) {
  const t = useT();
  const [job, setJob] = useState<JobDetail | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!open || !jobId) return;
    setJob(null);
    setLoading(true);
    api
      .get(`${apiBase}/${jobId}`)
      .then(({ data }) => setJob(data.data ?? data))
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [open, jobId]);

  const originLabel =
    job?.originAirport?.code ||
    job?.originHotel?.name ||
    job?.originZone?.name ||
    "—";
  const destLabel =
    job?.destinationAirport?.code ||
    job?.destinationHotel?.name ||
    job?.destinationZone?.name ||
    "—";

  const extras: string[] = (job?.jobExtras || [])
    .filter((e) => e.qty > 0)
    .map((e) => `${e.name} ×${e.qty}`);
  if (job?.printSign) extras.push("Print Sign");

  return (
    <Dialog open={open} onOpenChange={(v) => !v && onClose()}>
      <DialogContent className="w-[50vw] max-w-[50vw] max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="font-mono text-base">
            {job?.internalRef ?? t("jobs.jobDetails")}
          </DialogTitle>
        </DialogHeader>

        {loading && (
          <div className="flex justify-center py-12">
            <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
          </div>
        )}

        {!loading && job && (
          <div className="space-y-5 pt-2">
            {/* ── Status badges ── */}
            <div className="flex flex-wrap gap-2">
              <Badge variant="outline" className={STATUS_COLORS[job.status] || ""}>
                {job.status}
              </Badge>
              <Badge variant="outline" className={STATUS_COLORS[job.bookingStatus] || ""}>
                {job.bookingStatus}
              </Badge>
              <Badge variant="outline" className="text-xs">
                {job.serviceType}
              </Badge>
              <Badge variant="outline" className="text-xs">
                {job.bookingChannel}
              </Badge>
            </div>

            {/* ── Two-column grid ── */}
            <div className="grid grid-cols-2 gap-5">
              {/* ── Basic info ── */}
              <Section title={t("jobs.jobDetails")}>
                <Row label={t("reports.trsfReference")} value={job.internalRef} />
                <Row label={t("reports.agentRef")} value={job.agentRef} />
                <Row label={t("agents.legalName")} value={job.agent?.tradeName ?? job.agent?.legalName} />
                <Row label={t("jobs.serviceDate")} value={fmtDate(job.jobDate)} />
                <Row label={t("jobs.pickUpTime")} value={fmt(job.pickUpTime)} />
              </Section>

              {/* ── Route ── */}
              <Section title={t("dispatch.route")}>
                <Row label={t("dispatch.origin")} value={originLabel} />
                <Row label={t("dispatch.destination")} value={destLabel} />
              </Section>

              {/* ── Flight ── */}
              {job.flight && (
                <Section title={t("jobs.flightDetails")}>
                  <Row label={t("jobs.flightNo")} value={job.flight.flightNo} />
                  <Row label={t("jobs.carrier")} value={job.flight.carrier} />
                  <Row label={t("jobs.terminal")} value={job.flight.terminal} />
                  <Row label={t("jobs.arrivalTime")} value={fmt(job.flight.arrivalTime)} />
                  <Row label={t("jobs.departureTime")} value={fmt(job.flight.departureTime)} />
                </Section>
              )}

              {/* ── Passenger ── */}
              <Section title={t("jobs.passengerDetails")}>
                <Row label={t("jobs.clientName")} value={job.clientName} />
                <Row label={t("jobs.clientMobile")} value={job.clientMobile} />
                <Row label={t("jobs.adults")} value={job.adultCount} />
                <Row label={t("jobs.children")} value={job.childCount || null} />
                <Row label={t("jobs.totalPax")} value={job.paxCount} />
                {extras.length > 0 && (
                  <Row label={t("jobs.extras")} value={extras.join(", ")} />
                )}
              </Section>

              {/* ── Assignment ── */}
              {job.assignment && (
                <Section title={t("dispatch.assignment")}>
                  <Row
                    label={t("vehicles.plateNumber")}
                    value={
                      job.assignment.vehicle
                        ? `${job.assignment.vehicle.plateNumber}${job.assignment.vehicle.vehicleType ? ` — ${job.assignment.vehicle.vehicleType.name}` : ""}`
                        : null
                    }
                  />
                  <Row
                    label={t("dispatch.supplier")}
                    value={
                      job.assignment.vehicle?.supplier?.tradeName ??
                      job.assignment.vehicle?.supplier?.legalName
                    }
                  />
                  <Row label={t("dispatch.driverName")} value={job.assignment.driver?.name} />
                  <Row label={t("common.mobile")} value={job.assignment.driver?.mobileNumber} />
                  <Row label={t("reports.repName")} value={job.assignment.rep?.name} />
                  <Row label={t("reports.driverJobStatus")} value={job.assignment.driverStatus} />
                  <Row label={t("reports.repJobStatus")} value={job.assignment.repStatus} />
                </Section>
              )}

              {/* ── Pricing ── */}
              {(job.priceAmount != null || job.transferPrice != null) && (
                <Section title={t("jobs.pricing")}>
                  {job.transferPrice != null && (
                    <Row
                      label={t("jobs.transferPrice")}
                      value={`${job.transferPrice} ${job.transferPriceCurrency ?? ""}`}
                    />
                  )}
                  {job.priceAmount != null && (
                    <Row
                      label={t("reports.applicationPrice")}
                      value={`${job.priceAmount} ${job.priceCurrency ?? ""}`}
                    />
                  )}
                  {job.collectionRequired && (
                    <Row
                      label={t("jobs.collection")}
                      value={`${job.collectionAmount ?? 0} ${job.collectionCurrency ?? ""}`}
                    />
                  )}
                </Section>
              )}

              {/* ── Meta ── */}
              <Section title={t("common.createdBy")}>
                <Row label={t("common.createdBy")} value={job.createdBy?.name} />
                <Row label={t("common.createdAt")} value={fmtDate(job.createdAt)} />
              </Section>
            </div>

            {/* ── Notes (full width) ── */}
            {job.notes && (
              <Section title={t("common.notes")}>
                <p className="text-sm text-foreground whitespace-pre-wrap">{job.notes}</p>
              </Section>
            )}
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
}
