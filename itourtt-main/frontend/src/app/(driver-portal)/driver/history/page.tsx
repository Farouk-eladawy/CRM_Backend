"use client";

import { useState, useCallback } from "react";
import api from "@/lib/api";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  Plane,
  MapPin,
  Users,
  Search,
  History,
  Loader2,
  CalendarDays,
} from "lucide-react";
import { toast } from "sonner";
import { useT, useLocaleId } from "@/lib/i18n";
import { formatDate , localDateStr } from "@/lib/utils";
import { SERVICE_TYPE_COLORS, useServiceTypeLabel } from "@/lib/service-types";

interface HistoryJob {
  id: string;
  internalRef: string;
  serviceType: string;
  jobDate: string;
  status: string;
  driverStatus: string;
  paxCount: number;
  feeEarned: number | null;
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
  };
}


const STATUS_COLORS: Record<string, string> = {
  COMPLETED: "bg-green-500/10 text-green-400 border-green-500/20",
  CANCELLED: "bg-red-500/10 text-red-400 border-red-500/20",
  NO_SHOW: "bg-gray-500/10 text-gray-400 border-gray-500/20",
};

export default function DriverHistoryPage() {
  const t = useT();
  const serviceTypeLabel = useServiceTypeLabel();
  const locale = useLocaleId();
  const today = localDateStr(new Date());
  const [dateFrom, setDateFrom] = useState(today);
  const [dateTo, setDateTo] = useState(today);
  const [jobs, setJobs] = useState<HistoryJob[]>([]);
  const [loading, setLoading] = useState(false);
  const [searched, setSearched] = useState(false);

  const fetchHistory = useCallback(async () => {
    if (dateFrom > dateTo) {
      toast.error(t("portal.invalidDateRange"));
      return;
    }
    setLoading(true);
    setSearched(true);
    try {
      const { data } = await api.get("/driver-portal/jobs/history", {
        params: { dateFrom, dateTo },
      });
      setJobs(data.data?.jobs ?? []);
    } catch {
      toast.error(t("portal.failedHistory"));
    } finally {
      setLoading(false);
    }
  }, [dateFrom, dateTo]);

  const formatTime = (isoString: string | null) => {
    if (!isoString) return "\u2014";
    return new Date(isoString).toLocaleTimeString(locale, {
      timeZone: "Africa/Cairo",
      hour: "2-digit",
      minute: "2-digit",
      hour12: false,
    });
  };

  const totalFees = jobs.reduce((sum, j) => sum + (j.feeEarned ?? 0), 0);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-foreground">
          <History className="mr-2 inline h-6 w-6" />
          {t("portal.tripHistory")}
        </h1>
        <p className="text-sm text-muted-foreground">
          {t("portal.tripHistoryDesc")}
        </p>
      </div>

      {/* Date range picker & search */}
      <div className="flex flex-wrap items-end gap-3">
        <div className="space-y-1">
          <Label className="text-xs text-muted-foreground">{t("common.from")}</Label>
          <div className="relative">
            <CalendarDays className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
            <Input
              type="date"
              value={dateFrom}
              onChange={(e) => setDateFrom(e.target.value)}
              className="w-44 pl-9"
            />
          </div>
        </div>
        <div className="space-y-1">
          <Label className="text-xs text-muted-foreground">{t("common.to")}</Label>
          <div className="relative">
            <CalendarDays className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
            <Input
              type="date"
              value={dateTo}
              onChange={(e) => setDateTo(e.target.value)}
              className="w-44 pl-9"
            />
          </div>
        </div>
        <Button onClick={fetchHistory} disabled={loading}>
          {loading ? (
            <Loader2 className="mr-1.5 h-4 w-4 animate-spin" />
          ) : (
            <Search className="mr-1.5 h-4 w-4" />
          )}
          {t("portal.search")}
        </Button>
      </div>

      {/* Results */}
      {!searched ? (
        <Card>
          <CardContent className="flex flex-col items-center justify-center py-12">
            <History className="mb-3 h-10 w-10 text-muted-foreground/40" />
            <p className="text-sm text-muted-foreground">
              {t("portal.selectDateRange")}
            </p>
          </CardContent>
        </Card>
      ) : loading ? (
        <div className="flex items-center justify-center py-20">
          <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
        </div>
      ) : jobs.length === 0 ? (
        <Card>
          <CardContent className="flex flex-col items-center justify-center py-12">
            <History className="mb-3 h-10 w-10 text-muted-foreground/40" />
            <p className="text-sm text-muted-foreground">
              {t("portal.noTrips")}
            </p>
          </CardContent>
        </Card>
      ) : (
        <>
          {/* Desktop table */}
          <div className="hidden md:block">
            <div className="overflow-x-auto">
                <Table>
                  <TableHeader>
                    <TableRow className="bg-muted">
                      <TableHead className="text-muted-foreground text-xs">{t("dispatch.ref")}</TableHead>
                      <TableHead className="text-muted-foreground text-xs">{t("common.date")}</TableHead>
                      <TableHead className="text-muted-foreground text-xs">{t("jobs.type")}</TableHead>
                      <TableHead className="text-muted-foreground text-xs">{t("dispatch.flight")}</TableHead>
                      <TableHead className="text-muted-foreground text-xs">{t("dispatch.route")}</TableHead>
                      <TableHead className="text-center text-muted-foreground text-xs">{t("dispatch.pax")}</TableHead>
                      <TableHead className="text-muted-foreground text-xs">{t("common.status")}</TableHead>
                      <TableHead className="text-right text-muted-foreground text-xs">{t("portal.feeEgp")}</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {jobs.map((job, idx) => (
                      <TableRow key={job.id} className={`${idx % 2 === 0 ? "bg-gray-100/25 dark:bg-gray-800/25" : "bg-gray-200/50 dark:bg-gray-700/50"}`}>
                        <TableCell className="font-mono text-xs">
                          {job.internalRef}
                        </TableCell>
                        <TableCell className="text-sm text-muted-foreground">
                          {formatDate(job.jobDate)}
                        </TableCell>
                        <TableCell>
                          <Badge
                            variant="outline"
                            className={SERVICE_TYPE_COLORS[job.serviceType] || ""}
                          >
                            {serviceTypeLabel(job.serviceType)}
                          </Badge>
                        </TableCell>
                        <TableCell className="text-sm">
                          {job.flight ? (
                            <span className="flex items-center gap-1">
                              <Plane className="h-3.5 w-3.5 text-muted-foreground" />
                              {job.flight.carrier} {job.flight.flightNo}
                              <span className="text-muted-foreground">
                                {job.serviceType === "ARR"
                                  ? formatTime(job.flight.arrivalTime)
                                  : formatTime(job.flight.departureTime)}
                              </span>
                            </span>
                          ) : (
                            "\u2014"
                          )}
                        </TableCell>
                        <TableCell className="text-sm">
                          <span className="flex items-center gap-1">
                            <MapPin className="h-3.5 w-3.5 text-muted-foreground" />
                            {job.originAirport?.code || job.fromZone?.name || job.originZone?.name || job.originHotel?.name || "\u2014"} &rarr;{" "}
                            {job.destinationAirport?.code || job.toZone?.name || job.destinationZone?.name || job.destinationHotel?.name || "\u2014"}
                          </span>
                        </TableCell>
                        <TableCell className="text-center">
                          <span className="flex items-center justify-center gap-1">
                            <Users className="h-3.5 w-3.5 text-muted-foreground" />
                            {job.paxCount}
                          </span>
                        </TableCell>
                        <TableCell>
                          <Badge
                            variant="outline"
                            className={STATUS_COLORS[job.driverStatus] || ""}
                          >
                            {job.driverStatus.replace("_", " ")}
                          </Badge>
                        </TableCell>
                        <TableCell className="text-right font-mono">
                          {job.feeEarned != null
                            ? job.feeEarned.toLocaleString(locale)
                            : "\u2014"}
                        </TableCell>
                      </TableRow>
                    ))}
                    {/* Total row */}
                    <TableRow className="border-t-2 font-semibold">
                      <TableCell colSpan={7} className="text-right">
                        {t("common.total")}
                      </TableCell>
                      <TableCell className="text-right font-mono">
                        {totalFees.toLocaleString(locale)} EGP
                      </TableCell>
                    </TableRow>
                  </TableBody>
                </Table>
            </div>
          </div>

          {/* Mobile cards */}
          <div className="space-y-3 md:hidden">
            {jobs.map((job) => (
              <Card key={job.id}>
                <CardContent className="p-4 space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="font-mono text-sm font-semibold">
                      {job.internalRef}
                    </span>
                    <div className="flex gap-1.5">
                      <Badge
                        variant="outline"
                        className={SERVICE_TYPE_COLORS[job.serviceType] || ""}
                      >
                        {serviceTypeLabel(job.serviceType)}
                      </Badge>
                      <Badge
                        variant="outline"
                        className={STATUS_COLORS[job.driverStatus] || ""}
                      >
                        {job.driverStatus.replace("_", " ")}
                      </Badge>
                    </div>
                  </div>
                  <div className="text-xs text-muted-foreground">
                    {formatDate(job.jobDate)}
                  </div>
                  {job.flight && (
                    <div className="flex items-center gap-2 text-sm text-muted-foreground">
                      <Plane className="h-3.5 w-3.5" />
                      {job.flight.carrier} {job.flight.flightNo}
                    </div>
                  )}
                  <div className="flex items-center gap-2 text-sm text-muted-foreground">
                    <MapPin className="h-3.5 w-3.5" />
                    {job.originAirport?.code || job.fromZone?.name || job.originZone?.name || job.originHotel?.name || "\u2014"} &rarr; {job.destinationAirport?.code || job.toZone?.name || job.destinationZone?.name || job.destinationHotel?.name || "\u2014"}
                  </div>
                  <div className="flex items-center justify-between text-sm">
                    <span className="flex items-center gap-1 text-muted-foreground">
                      <Users className="h-3.5 w-3.5" />
                      {job.paxCount} {t("dispatch.pax")}
                    </span>
                    {job.feeEarned != null && (
                      <span className="font-mono font-semibold text-green-400">
                        {job.feeEarned.toLocaleString(locale)} EGP
                      </span>
                    )}
                  </div>
                </CardContent>
              </Card>
            ))}

            {/* Mobile total */}
            <Card className="border-primary/30">
              <CardContent className="flex items-center justify-between p-4">
                <span className="font-semibold text-foreground">{t("portal.totalFees")}</span>
                <span className="font-mono text-lg font-bold text-green-400">
                  {totalFees.toLocaleString(locale)} EGP
                </span>
              </CardContent>
            </Card>
          </div>
        </>
      )}
    </div>
  );
}
