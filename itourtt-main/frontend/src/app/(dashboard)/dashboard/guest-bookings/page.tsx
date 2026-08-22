"use client";

import { useState, useEffect, useCallback } from "react";
import {
  Loader2,
  Search,
  ArrowRightLeft,
  XCircle,
  Eye,
  CreditCard,
  Calendar,
  User,
  Plane,
  MapPin,
  Car,
} from "lucide-react";
import { toast } from "sonner";
import api from "@/lib/api";
import { PageHeader } from "@/components/page-header";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { useT } from "@/lib/i18n";
import { usePermission } from "@/hooks/use-permission";
import { StatusBadge } from "@/components/ui/status-badge";
import { useColumnPreferences } from "@/hooks/useColumnPreferences";
import { ColumnVisibilityControl } from "@/components/ui/column-visibility-control";
import { type ColumnDef } from "@/components/ui/draggable-table-header";
import { useServiceTypeLabel } from "@/lib/service-types";

const GUEST_BOOKINGS_COL_DEFS: ColumnDef[] = [
  { key: "ref", label: "Ref" },
  { key: "guest", label: "Guest" },
  { key: "service", label: "Service" },
  { key: "date", label: "Date" },
  { key: "route", label: "Route" },
  { key: "total", label: "Total" },
  { key: "payment", label: "Payment" },
  { key: "status", label: "Status" },
  { key: "actions", label: "Actions" },
];

interface GuestBooking {
  id: string;
  bookingRef: string;
  guestName: string;
  guestEmail: string;
  guestPhone: string;
  guestCountry?: string;
  serviceType: string;
  jobDate: string;
  pickupTime?: string;
  paxCount: number;
  subtotal: number;
  taxAmount: number;
  total: number;
  currency: string;
  paymentMethod: string;
  paymentStatus: string;
  paymentGateway?: string;
  bookingStatus: string;
  trafficJobId?: string;
  notes?: string;
  flightNo?: string;
  carrier?: string;
  extras?: any;
  fromZone?: { id: string; name: string; city?: { name: string } };
  toZone?: { id: string; name: string; city?: { name: string } };
  hotel?: { id: string; name: string };
  originAirport?: { id: string; name: string; code: string };
  destinationAirport?: { id: string; name: string; code: string };
  vehicleType?: { id: string; name: string; seatCapacity: number };
  createdAt: string;
}


export default function GuestBookingsPage() {
  const serviceTypeLabel = useServiceTypeLabel();
  const t = useT();
  const canConvert = usePermission("guest-bookings.convert");
  const canCancel = usePermission("guest-bookings.cancel");
  const { visibility: gbColVis, saveVisibility: saveGbColVis } = useColumnPreferences("guest_bookings", GUEST_BOOKINGS_COL_DEFS.map((c) => c.key));
  const isVis = (key: string) => gbColVis[key] !== false;
  const visColCount = GUEST_BOOKINGS_COL_DEFS.filter((c) => gbColVis[c.key] !== false).length;
  const [bookings, setBookings] = useState<GuestBooking[]>([]);
  const [loading, setLoading] = useState(true);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("all");
  const [paymentFilter, setPaymentFilter] = useState("all");
  const [selectedBooking, setSelectedBooking] = useState<GuestBooking | null>(null);
  const [converting, setConverting] = useState<string | null>(null);
  const limit = 20;

  const fetchBookings = useCallback(async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams();
      params.set("page", String(page));
      params.set("limit", String(limit));
      if (search) params.set("search", search);
      if (statusFilter !== "all") params.set("bookingStatus", statusFilter);
      if (paymentFilter !== "all") params.set("paymentStatus", paymentFilter);

      const res = await api.get(`/guest-bookings?${params.toString()}`);
      const body = res.data;
      setBookings(body.data || []);
      setTotal(body.meta?.total || 0);
    } catch {
      toast.error("Failed to load guest bookings");
    } finally {
      setLoading(false);
    }
  }, [page, search, statusFilter, paymentFilter]);

  useEffect(() => {
    fetchBookings();
  }, [fetchBookings]);

  const handleConvert = async (id: string) => {
    setConverting(id);
    try {
      await api.post(`/guest-bookings/${id}/convert`);
      toast.success("Booking converted to traffic job");
      await fetchBookings();
      setSelectedBooking(null);
    } catch (err: any) {
      toast.error(err?.response?.data?.message || "Failed to convert booking");
    } finally {
      setConverting(null);
    }
  };

  const handleCancel = async (id: string) => {
    try {
      await api.patch(`/guest-bookings/${id}/cancel`);
      toast.success("Booking cancelled");
      await fetchBookings();
      setSelectedBooking(null);
    } catch (err: any) {
      toast.error(err?.response?.data?.message || "Failed to cancel booking");
    }
  };

  const totalPages = Math.ceil(total / limit);

  return (
    <div className="space-y-6">
      <PageHeader
        title={t("guestBookings.title") || "Guest Bookings"}
        description={
          t("guestBookings.description") ||
          "Manage B2C direct guest bookings and convert them to traffic jobs"
        }
      />

      {/* Filters */}
      <div className="flex flex-wrap items-center gap-3">
        <div className="relative flex-1 min-w-[200px] max-w-sm">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
          <Input
            placeholder="Search by ref, name, email..."
            value={search}
            onChange={(e) => {
              setSearch(e.target.value);
              setPage(1);
            }}
            className="pl-9"
          />
        </div>
        <Select
          value={statusFilter}
          onValueChange={(v) => {
            setStatusFilter(v);
            setPage(1);
          }}
        >
          <SelectTrigger className="w-[160px]">
            <SelectValue placeholder="Booking Status" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All Statuses</SelectItem>
            <SelectItem value="CONFIRMED">Confirmed</SelectItem>
            <SelectItem value="CANCELLED">Cancelled</SelectItem>
            <SelectItem value="CONVERTED">Converted</SelectItem>
          </SelectContent>
        </Select>
        <Select
          value={paymentFilter}
          onValueChange={(v) => {
            setPaymentFilter(v);
            setPage(1);
          }}
        >
          <SelectTrigger className="w-[160px]">
            <SelectValue placeholder="Payment Status" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All Payments</SelectItem>
            <SelectItem value="PENDING">Pending</SelectItem>
            <SelectItem value="PAID">Paid</SelectItem>
            <SelectItem value="REFUNDED">Refunded</SelectItem>
            <SelectItem value="FAILED">Failed</SelectItem>
          </SelectContent>
        </Select>
      </div>

      {/* Table */}
      <div className="flex justify-end mb-2">
        <ColumnVisibilityControl columns={GUEST_BOOKINGS_COL_DEFS} visibility={gbColVis} onSave={saveGbColVis} />
      </div>
      <div className="rounded-lg border">
        <Table>
          <TableHeader>
            <TableRow>
              {isVis("ref") && <TableHead>Ref</TableHead>}
              {isVis("guest") && <TableHead>Guest</TableHead>}
              {isVis("service") && <TableHead>Service</TableHead>}
              {isVis("date") && <TableHead>Date</TableHead>}
              {isVis("route") && <TableHead>Route</TableHead>}
              {isVis("total") && <TableHead className="text-right">Total</TableHead>}
              {isVis("payment") && <TableHead>Payment</TableHead>}
              {isVis("status") && <TableHead>Status</TableHead>}
              {isVis("actions") && <TableHead className="w-[100px]">Actions</TableHead>}
            </TableRow>
          </TableHeader>
          <TableBody>
            {loading ? (
              <TableRow>
                <TableCell colSpan={visColCount} className="text-center py-8">
                  <Loader2 className="mx-auto h-5 w-5 animate-spin text-muted-foreground" />
                </TableCell>
              </TableRow>
            ) : bookings.length === 0 ? (
              <TableRow>
                <TableCell colSpan={visColCount} className="text-center py-8 text-muted-foreground">
                  No guest bookings found
                </TableCell>
              </TableRow>
            ) : (
              bookings.map((b) => (
                <TableRow key={b.id}>
                  {isVis("ref") && <TableCell className="font-mono text-xs">{b.bookingRef}</TableCell>}
                  {isVis("guest") && <TableCell><div className="text-sm font-medium">{b.guestName}</div><div className="text-xs text-muted-foreground">{b.guestEmail}</div></TableCell>}
                  {isVis("service") && <TableCell><Badge variant="outline" className="text-xs">{serviceTypeLabel(b.serviceType)}</Badge></TableCell>}
                  {isVis("date") && <TableCell className="text-sm">{new Date(b.jobDate).toLocaleDateString()}</TableCell>}
                  {isVis("route") && <TableCell className="text-sm">{b.fromZone?.name} → {b.toZone?.name}</TableCell>}
                  {isVis("total") && <TableCell className="text-right font-mono text-sm">{b.currency} {Number(b.total).toFixed(2)}</TableCell>}
                  {isVis("payment") && <TableCell><StatusBadge status={b.paymentStatus} /></TableCell>}
                  {isVis("status") && <TableCell><StatusBadge status={b.bookingStatus} /></TableCell>}
                  {isVis("actions") && (
                    <TableCell>
                      <div className="flex items-center gap-1">
                        <Button variant="ghost" size="icon" className="h-7 w-7" onClick={() => setSelectedBooking(b)}><Eye className="h-3.5 w-3.5" /></Button>
                        {canConvert && b.bookingStatus === "CONFIRMED" && (
                          <Button variant="ghost" size="icon" className="h-7 w-7 text-blue-600" disabled={converting === b.id} onClick={() => handleConvert(b.id)} title="Convert to Traffic Job">
                            {converting === b.id ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <ArrowRightLeft className="h-3.5 w-3.5" />}
                          </Button>
                        )}
                      </div>
                    </TableCell>
                  )}
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </div>

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="flex items-center justify-between text-sm text-muted-foreground">
          <span>
            Showing {(page - 1) * limit + 1}–{Math.min(page * limit, total)} of {total}
          </span>
          <div className="flex gap-1">
            <Button
              variant="outline"
              size="sm"
              disabled={page <= 1}
              onClick={() => setPage((p) => p - 1)}
            >
              Previous
            </Button>
            <Button
              variant="outline"
              size="sm"
              disabled={page >= totalPages}
              onClick={() => setPage((p) => p + 1)}
            >
              Next
            </Button>
          </div>
        </div>
      )}

      {/* Detail Dialog */}
      <Dialog
        open={!!selectedBooking}
        onOpenChange={(open) => !open && setSelectedBooking(null)}
      >
        <DialogContent className="max-w-2xl max-h-[85vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              Booking {selectedBooking?.bookingRef}
              {selectedBooking && (
                <StatusBadge status={selectedBooking.bookingStatus} />
              )}
            </DialogTitle>
          </DialogHeader>
          {selectedBooking && (
            <div className="space-y-4">
              {/* Guest Info */}
              <div className="rounded-lg border p-4">
                <h4 className="mb-2 flex items-center gap-2 text-sm font-medium">
                  <User className="h-4 w-4" /> Guest Information
                </h4>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 text-sm">
                  <div>
                    <span className="text-muted-foreground">Name:</span>{" "}
                    {selectedBooking.guestName}
                  </div>
                  <div>
                    <span className="text-muted-foreground">Email:</span>{" "}
                    {selectedBooking.guestEmail}
                  </div>
                  <div>
                    <span className="text-muted-foreground">Phone:</span>{" "}
                    {selectedBooking.guestPhone}
                  </div>
                  {selectedBooking.guestCountry && (
                    <div>
                      <span className="text-muted-foreground">Country:</span>{" "}
                      {selectedBooking.guestCountry}
                    </div>
                  )}
                </div>
              </div>

              {/* Trip Info */}
              <div className="rounded-lg border p-4">
                <h4 className="mb-2 flex items-center gap-2 text-sm font-medium">
                  <MapPin className="h-4 w-4" /> Trip Details
                </h4>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 text-sm">
                  <div>
                    <span className="text-muted-foreground">Service:</span>{" "}
                    {serviceTypeLabel(selectedBooking.serviceType)}
                  </div>
                  <div>
                    <span className="text-muted-foreground">Date:</span>{" "}
                    {new Date(selectedBooking.jobDate).toLocaleDateString()}
                  </div>
                  <div>
                    <span className="text-muted-foreground">From:</span>{" "}
                    {selectedBooking.fromZone?.name}
                    {selectedBooking.fromZone?.city &&
                      ` (${selectedBooking.fromZone.city.name})`}
                  </div>
                  <div>
                    <span className="text-muted-foreground">To:</span>{" "}
                    {selectedBooking.toZone?.name}
                    {selectedBooking.toZone?.city &&
                      ` (${selectedBooking.toZone.city.name})`}
                  </div>
                  {selectedBooking.hotel && (
                    <div>
                      <span className="text-muted-foreground">Hotel:</span>{" "}
                      {selectedBooking.hotel.name}
                    </div>
                  )}
                  <div>
                    <span className="text-muted-foreground">Passengers:</span>{" "}
                    {selectedBooking.paxCount}
                  </div>
                  <div>
                    <span className="text-muted-foreground">Vehicle:</span>{" "}
                    {selectedBooking.vehicleType?.name}
                  </div>
                </div>
              </div>

              {/* Flight Info */}
              {selectedBooking.flightNo && (
                <div className="rounded-lg border p-4">
                  <h4 className="mb-2 flex items-center gap-2 text-sm font-medium">
                    <Plane className="h-4 w-4" /> Flight Details
                  </h4>
                  <div className="grid grid-cols-1 sm:grid-cols-3 gap-2 text-sm">
                    <div>
                      <span className="text-muted-foreground">Flight:</span>{" "}
                      {selectedBooking.flightNo}
                    </div>
                    {selectedBooking.carrier && (
                      <div>
                        <span className="text-muted-foreground">Carrier:</span>{" "}
                        {selectedBooking.carrier}
                      </div>
                    )}
                  </div>
                </div>
              )}

              {/* Payment Info */}
              <div className="rounded-lg border p-4">
                <h4 className="mb-2 flex items-center gap-2 text-sm font-medium">
                  <CreditCard className="h-4 w-4" /> Payment
                </h4>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 text-sm">
                  <div>
                    <span className="text-muted-foreground">Method:</span>{" "}
                    {selectedBooking.paymentMethod === "PAY_ON_ARRIVAL"
                      ? "Pay on Arrival"
                      : "Online"}
                  </div>
                  <div>
                    <span className="text-muted-foreground">Status:</span>{" "}
                    <StatusBadge status={selectedBooking.paymentStatus} />
                  </div>
                  {selectedBooking.paymentGateway && (
                    <div>
                      <span className="text-muted-foreground">Gateway:</span>{" "}
                      {selectedBooking.paymentGateway}
                    </div>
                  )}
                  <div>
                    <span className="text-muted-foreground">Total:</span>{" "}
                    <span className="font-mono font-medium">
                      {selectedBooking.currency}{" "}
                      {Number(selectedBooking.total).toFixed(2)}
                    </span>
                  </div>
                </div>
              </div>

              {/* Actions */}
              <div className="flex items-center gap-2 pt-2">
                {selectedBooking.bookingStatus === "CONFIRMED" && (
                  <>
                    {canConvert && (
                      <Button
                        onClick={() => handleConvert(selectedBooking.id)}
                        disabled={
                          converting === selectedBooking.id ||
                          (selectedBooking.paymentMethod === "ONLINE" &&
                            selectedBooking.paymentStatus !== "PAID")
                        }
                      >
                        {converting === selectedBooking.id ? (
                          <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                        ) : (
                          <ArrowRightLeft className="mr-2 h-4 w-4" />
                        )}
                        Convert to Traffic Job
                      </Button>
                    )}
                    {canCancel && (
                      <Button
                        variant="destructive"
                        onClick={() => handleCancel(selectedBooking.id)}
                      >
                        <XCircle className="mr-2 h-4 w-4" />
                        Cancel Booking
                      </Button>
                    )}
                  </>
                )}
                {selectedBooking.bookingStatus === "CONVERTED" &&
                  selectedBooking.trafficJobId && (
                    <Button
                      variant="outline"
                      onClick={() =>
                        window.open(
                          `/dashboard/traffic-jobs/online?highlight=${selectedBooking.trafficJobId}`,
                          "_blank"
                        )
                      }
                    >
                      View Traffic Job
                    </Button>
                  )}
              </div>
            </div>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
}
