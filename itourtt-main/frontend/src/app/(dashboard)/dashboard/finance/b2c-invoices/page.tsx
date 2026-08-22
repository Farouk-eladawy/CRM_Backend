"use client";

import { useState, useEffect, useCallback } from "react";
import { Loader2, Search, Download, FileText } from "lucide-react";
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
import { useT } from "@/lib/i18n";
import { usePermissionsStore } from "@/stores/permissions-store";
import { StatusBadge } from "@/components/ui/status-badge";
import { formatDate } from "@/lib/utils";

interface B2CInvoice {
  id: string;
  invoiceNumber: string;
  issuedAt: string;
  currency: string;
  subtotal: number;
  taxAmount: number;
  total: number;
  status: string;
  guestBooking: {
    bookingRef: string;
    guestName: string;
    guestEmail: string;
    jobDate: string;
    serviceType: string;
  } | null;
}

export default function B2CInvoicesPage() {
  const t = useT();
  const isLoaded = usePermissionsStore((s) => s.isLoaded);
  const hasPerm = usePermissionsStore((s) => s.has("finance.b2cInvoices"));

  const [invoices, setInvoices] = useState<B2CInvoice[]>([]);
  const [loading, setLoading] = useState(true);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("all");
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");
  const [downloading, setDownloading] = useState<string | null>(null);
  const limit = 20;

  const fetchInvoices = useCallback(async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams();
      params.set("page", String(page));
      params.set("limit", String(limit));
      if (search) params.set("search", search);
      if (statusFilter !== "all") params.set("status", statusFilter);
      if (dateFrom) params.set("dateFrom", dateFrom);
      if (dateTo) params.set("dateTo", dateTo);

      const res = await api.get(`/finance/b2c-invoices?${params.toString()}`);
      const body = res.data;
      setInvoices(body.data || []);
      setTotal(body.meta?.total || 0);
    } catch {
      toast.error("Failed to load B2C invoices");
    } finally {
      setLoading(false);
    }
  }, [page, search, statusFilter, dateFrom, dateTo]);

  useEffect(() => {
    if (isLoaded && hasPerm) fetchInvoices();
  }, [fetchInvoices, isLoaded, hasPerm]);

  const downloadPdf = async (inv: B2CInvoice) => {
    setDownloading(inv.id);
    try {
      const { data } = await api.get(`/finance/b2c-invoices/${inv.id}/pdf`, {
        responseType: "blob",
      });
      const url = URL.createObjectURL(data);
      const a = document.createElement("a");
      a.href = url;
      a.download = `${inv.invoiceNumber}.pdf`;
      a.click();
      URL.revokeObjectURL(url);
    } catch {
      toast.error("Failed to download invoice PDF");
    } finally {
      setDownloading(null);
    }
  };

  const totalPages = Math.ceil(total / limit);

  if (isLoaded && !hasPerm) {
    return (
      <div className="flex flex-col items-center justify-center py-24 text-center text-muted-foreground">
        <FileText className="mb-3 h-8 w-8" />
        <p>You do not have access to B2C invoices.</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <PageHeader
        title={t("sidebar.b2cInvoices") || "B2C Invoices"}
        description="Guest invoices generated for paid B2C direct bookings"
      />

      {/* Filters */}
      <div className="flex flex-wrap items-end gap-3">
        <div className="relative flex-1 min-w-[200px] max-w-sm">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
          <Input
            placeholder="Search by invoice #, ref, name, email..."
            value={search}
            onChange={(e) => {
              setSearch(e.target.value);
              setPage(1);
            }}
            className="pl-9"
          />
        </div>
        <div className="flex flex-col gap-1">
          <span className="text-xs text-muted-foreground">From</span>
          <Input
            type="date"
            value={dateFrom}
            onChange={(e) => {
              setDateFrom(e.target.value);
              setPage(1);
            }}
            className="w-[160px]"
          />
        </div>
        <div className="flex flex-col gap-1">
          <span className="text-xs text-muted-foreground">To</span>
          <Input
            type="date"
            value={dateTo}
            onChange={(e) => {
              setDateTo(e.target.value);
              setPage(1);
            }}
            className="w-[160px]"
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
            <SelectValue placeholder="Status" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All Statuses</SelectItem>
            <SelectItem value="ISSUED">Issued</SelectItem>
            <SelectItem value="PAID">Paid</SelectItem>
            <SelectItem value="REFUNDED">Refunded</SelectItem>
            <SelectItem value="CANCELLED">Cancelled</SelectItem>
          </SelectContent>
        </Select>
      </div>

      {/* Table */}
      <div className="rounded-lg border">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Invoice #</TableHead>
              <TableHead>Date</TableHead>
              <TableHead>Guest</TableHead>
              <TableHead>Booking Ref</TableHead>
              <TableHead>Service</TableHead>
              <TableHead className="text-right">Amount</TableHead>
              <TableHead>Status</TableHead>
              <TableHead className="w-[100px]">Actions</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {loading ? (
              <TableRow>
                <TableCell colSpan={8} className="text-center py-8">
                  <Loader2 className="mx-auto h-5 w-5 animate-spin text-muted-foreground" />
                </TableCell>
              </TableRow>
            ) : invoices.length === 0 ? (
              <TableRow>
                <TableCell colSpan={8} className="text-center py-8 text-muted-foreground">
                  No B2C invoices found
                </TableCell>
              </TableRow>
            ) : (
              invoices.map((inv) => (
                <TableRow key={inv.id}>
                  <TableCell className="font-mono text-xs">{inv.invoiceNumber}</TableCell>
                  <TableCell className="text-sm">{formatDate(inv.issuedAt)}</TableCell>
                  <TableCell>
                    <div className="text-sm font-medium">{inv.guestBooking?.guestName}</div>
                    <div className="text-xs text-muted-foreground">{inv.guestBooking?.guestEmail}</div>
                  </TableCell>
                  <TableCell className="font-mono text-xs">{inv.guestBooking?.bookingRef}</TableCell>
                  <TableCell>
                    {inv.guestBooking?.serviceType && (
                      <Badge variant="outline" className="text-xs">{inv.guestBooking.serviceType}</Badge>
                    )}
                  </TableCell>
                  <TableCell className="text-right font-mono text-sm">
                    {inv.currency} {Number(inv.total).toFixed(2)}
                  </TableCell>
                  <TableCell><StatusBadge status={inv.status} /></TableCell>
                  <TableCell>
                    <Button
                      variant="ghost"
                      size="icon"
                      className="h-7 w-7"
                      title="Download PDF"
                      disabled={downloading === inv.id}
                      onClick={() => downloadPdf(inv)}
                    >
                      {downloading === inv.id ? (
                        <Loader2 className="h-3.5 w-3.5 animate-spin" />
                      ) : (
                        <Download className="h-3.5 w-3.5" />
                      )}
                    </Button>
                  </TableCell>
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
    </div>
  );
}
