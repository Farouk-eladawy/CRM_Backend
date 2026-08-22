"use client";

import { useEffect, useState, useCallback, useMemo, useRef } from "react";
import { useRouter } from "next/navigation";
import {
  Truck,
  Plus,
  Loader2,
  UserPlus,
  KeyRound,
  Eye,
  FileDown,
  FileUp,
  FileSpreadsheet,
  AlertTriangle,
  Trash2,
} from "lucide-react";
import { toast } from "sonner";
import { PageHeader } from "@/components/page-header";
import { EmptyState } from "@/components/ui/empty-state";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "@/components/ui/dialog";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Checkbox } from "@/components/ui/checkbox";
import api from "@/lib/api";
import { useT } from "@/lib/i18n";
import { usePermission } from "@/hooks/use-permission";
import { useSortable } from "@/hooks/use-sortable";
import { SortableHeader } from "@/components/sortable-header";
import { TableFilterBar } from "@/components/table-filter-bar";
import { localDateStr } from "@/lib/utils";
import { useColumnPreferences } from "@/hooks/useColumnPreferences";
import { ColumnVisibilityControl } from "@/components/ui/column-visibility-control";
import { type ColumnDef } from "@/components/ui/draggable-table-header";

const SUPPLIERS_COL_DEFS: ColumnDef[] = [
  { key: "type", label: "Type" },
  { key: "legalName", label: "Legal Name" },
  { key: "tradeName", label: "Trade Name" },
  { key: "taxId", label: "Tax ID" },
  { key: "city", label: "City" },
  { key: "country", label: "Country" },
  { key: "phone", label: "Phone" },
  { key: "account", label: "Account" },
  { key: "status", label: "Status" },
  { key: "actions", label: "Actions" },
];

interface Supplier {
  id: string;
  supplierType: "COMPANY" | "INDIVIDUAL";
  legalName: string;
  tradeName: string;
  taxId: string;
  address: string;
  city: string;
  country: string;
  phone: string;
  email: string;
  mobileNumber: string;
  nationalIdImage: string | null;
  userId?: string | null;
  user?: { id: string; email: string; name: string; role: string; isActive: boolean } | null;
  isActive: boolean;
}

interface SuppliersResponse {
  data: Supplier[];
  meta: {
    total: number;
    page: number;
    limit: number;
    totalPages: number;
  };
}

export default function SuppliersPage() {
  const t = useT();
  const router = useRouter();
  const canAddSupplier = usePermission("suppliers.addButton");
  const canEditSupplier = usePermission("suppliers.table.editButton");
  const canDeleteSupplier = usePermission("suppliers.table.deleteButton");
  const canToggleStatus = usePermission("suppliers.table.toggleStatus");
  const canCreateAccount = usePermission("suppliers.table.createAccount");
  const canResetPassword = usePermission("suppliers.table.resetPassword");
  const canFormLegalName = usePermission("suppliers.form.legalName");
  const canFormTradeName = usePermission("suppliers.form.tradeName");
  const canFormTaxId = usePermission("suppliers.form.taxId");
  const canFormContactInfo = usePermission("suppliers.form.contactInfo");
  const [suppliers, setSuppliers] = useState<Supplier[]>([]);
  const [loading, setLoading] = useState(true);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editDialogOpen, setEditDialogOpen] = useState(false);
  const [editingSupplier, setEditingSupplier] = useState<Supplier | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const importFileRef = useRef<HTMLInputElement>(null);
  const [importing, setImporting] = useState(false);
  const [exporting, setExporting] = useState(false);
  const [importResult, setImportResult] = useState<{
    open: boolean;
    imported: number;
    errors: string[];
  }>({ open: false, imported: 0, errors: [] });

  const [search, setSearch] = useState("");
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [total, setTotal] = useState(0);
  const PAGE_SIZE = 50;
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [deleteTarget, setDeleteTarget] = useState<{ id: string; name: string } | null>(null);
  const [deleting, setDeleting] = useState(false);

  const filtered = useMemo(() => {
    if (!search.trim()) return suppliers;
    const q = search.toLowerCase();
    return suppliers.filter(
      (s) =>
        s.legalName.toLowerCase().includes(q) ||
        (s.tradeName && s.tradeName.toLowerCase().includes(q)) ||
        (s.city && s.city.toLowerCase().includes(q))
    );
  }, [suppliers, search]);

  const { sortedData, sortKey, sortDir, onSort } = useSortable<Supplier>(filtered);
  const { visibility: supplierColVis, saveVisibility: saveSupplierColVis } = useColumnPreferences("suppliers_list", SUPPLIERS_COL_DEFS.map((c) => c.key));
  const isVis = (key: string) => supplierColVis[key] !== false;

  // Account management
  const [accountDialogOpen, setAccountDialogOpen] = useState(false);
  const [passwordDialogOpen, setPasswordDialogOpen] = useState(false);
  const [accountSupplierId, setAccountSupplierId] = useState<string | null>(null);
  const [accountSupplierName, setAccountSupplierName] = useState("");
  const [accountSupplierPhone, setAccountSupplierPhone] = useState("");
  const [accountPassword, setAccountPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");

  const [supplierTab, setSupplierTab] = useState<"COMPANY" | "INDIVIDUAL">("COMPANY");
  const [legalName, setLegalName] = useState("");
  const [tradeName, setTradeName] = useState("");
  const [taxId, setTaxId] = useState("");
  const [address, setAddress] = useState("");
  const [city, setCity] = useState("");
  const [country, setCountry] = useState("");
  const [phone, setPhone] = useState("");
  const [email, setEmail] = useState("");
  // Individual supplier fields
  const [indName, setIndName] = useState("");
  const [indMobile, setIndMobile] = useState("");
  const [indEmail, setIndEmail] = useState("");
  const [indNationalIdFile, setIndNationalIdFile] = useState<File | null>(null);
  const nationalIdRef = useRef<HTMLInputElement>(null);
  // Car types
  const [vehicleTypes, setVehicleTypes] = useState<{ id: string; name: string; seatCapacity: number }[]>([]);
  const [selectedCarTypeIds, setSelectedCarTypeIds] = useState<Set<string>>(new Set());

  const fetchSuppliers = useCallback(async (p = page) => {
    try {
      setLoading(true);
      const { data } = await api.get<SuppliersResponse>("/suppliers", {
        params: { page: p, limit: PAGE_SIZE },
      });
      setSuppliers(data.data);
      setTotalPages(data.meta.totalPages);
      setTotal(data.meta.total);
    } catch {
      toast.error(t("suppliers.failedLoad"));
    } finally {
      setLoading(false);
    }
  }, [page]);

  useEffect(() => {
    setSelectedIds(new Set());
    fetchSuppliers(page);
  }, [page]);

  // Fetch vehicle types once
  useEffect(() => {
    api.get("/vehicles/types").then((res) => {
      setVehicleTypes(res.data.data || res.data || []);
    }).catch(() => {});
  }, []);

  async function handleToggleStatus(id: string) {
    try {
      await api.patch(`/suppliers/${id}/status`);
      setSuppliers((prev) =>
        prev.map((s) => (s.id === id ? { ...s, isActive: !s.isActive } : s))
      );
      toast.success(t("common.statusUpdated"));
    } catch {
      toast.error(t("common.failedStatusUpdate"));
    }
  }

  function toggleSelect(id: string) {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }

  function toggleSelectAll() {
    if (selectedIds.size === sortedData.length) {
      setSelectedIds(new Set());
    } else {
      setSelectedIds(new Set(sortedData.map((s) => s.id)));
    }
  }

  function openDeleteDialog(supplier: Supplier) {
    setDeleteTarget({ id: supplier.id, name: supplier.legalName });
    setDeleteDialogOpen(true);
  }

  function openBulkDeleteDialog() {
    setDeleteTarget(null);
    setDeleteDialogOpen(true);
  }

  async function handleDelete() {
    setDeleting(true);
    try {
      if (deleteTarget) {
        await api.delete(`/suppliers/${deleteTarget.id}`);
        toast.success(t("suppliers.deleted"));
      } else {
        await api.delete("/suppliers/bulk", { data: { ids: Array.from(selectedIds) } });
        toast.success(`${selectedIds.size} suppliers deleted`);
        setSelectedIds(new Set());
      }
      setDeleteDialogOpen(false);
      setDeleteTarget(null);
      fetchSuppliers();
    } catch {
      toast.error("Failed to delete supplier(s)");
    } finally {
      setDeleting(false);
    }
  }

  function resetForm() {
    setSupplierTab("COMPANY");
    setLegalName("");
    setTradeName("");
    setTaxId("");
    setAddress("");
    setCity("");
    setCountry("");
    setPhone("");
    setEmail("");
    setIndName("");
    setIndMobile("");
    setIndEmail("");
    setIndNationalIdFile(null);
    if (nationalIdRef.current) nationalIdRef.current.value = "";
  }

  function openDialog() {
    resetForm();
    setDialogOpen(true);
  }

  function openEditDialog(supplier: Supplier) {
    setEditingSupplier(supplier);
    setLegalName(supplier.legalName || "");
    setTradeName(supplier.tradeName || "");
    setTaxId(supplier.taxId || "");
    setAddress(supplier.address || "");
    setCity(supplier.city || "");
    setCountry(supplier.country || "");
    setPhone(supplier.phone || "");
    setEmail(supplier.email || "");
    // Load car types for this supplier
    api.get(`/suppliers/${supplier.id}/car-types`).then((res) => {
      const types = res.data.data || res.data || [];
      setSelectedCarTypeIds(new Set(types.map((t: { id: string }) => t.id)));
    }).catch(() => setSelectedCarTypeIds(new Set()));
    setEditDialogOpen(true);
  }

  async function handleUpdate() {
    if (!editingSupplier) return;
    if (!legalName.trim()) {
      toast.error(t("suppliers.legalNameRequired"));
      return;
    }

    try {
      setSubmitting(true);
      await Promise.all([
        api.put(`/suppliers/${editingSupplier.id}`, {
          legalName: legalName.trim(),
          tradeName: tradeName.trim() || undefined,
          taxId: taxId.trim() || undefined,
          address: address.trim() || undefined,
          city: city.trim() || undefined,
          country: country.trim() || undefined,
          phone: phone.trim() || undefined,
          email: email.trim() || undefined,
        }),
        api.put(`/suppliers/${editingSupplier.id}/car-types`, {
          vehicleTypeIds: Array.from(selectedCarTypeIds),
        }),
      ]);
      toast.success(t("suppliers.updated"));
      setEditDialogOpen(false);
      setEditingSupplier(null);
      resetForm();
      fetchSuppliers();
    } catch {
      toast.error(t("suppliers.failedUpdate"));
    } finally {
      setSubmitting(false);
    }
  }

  async function handleSubmit() {
    if (supplierTab === "COMPANY") {
      if (!legalName.trim()) {
        toast.error(t("suppliers.legalNameRequired"));
        return;
      }
      try {
        setSubmitting(true);
        await api.post("/suppliers", {
          supplierType: "COMPANY",
          legalName: legalName.trim(),
          tradeName: tradeName.trim(),
          taxId: taxId.trim(),
          address: address.trim(),
          city: city.trim(),
          country: country.trim(),
          phone: phone.trim(),
          email: email.trim(),
        });
        toast.success(t("suppliers.created"));
        setDialogOpen(false);
        resetForm();
        fetchSuppliers();
      } catch {
        toast.error(t("suppliers.failedCreate"));
      } finally {
        setSubmitting(false);
      }
    } else {
      // Individual
      if (!indName.trim()) {
        toast.error("Name is required");
        return;
      }
      if (!indMobile.trim()) {
        toast.error("Mobile number is required");
        return;
      }
      try {
        setSubmitting(true);
        const res = await api.post("/suppliers", {
          supplierType: "INDIVIDUAL",
          legalName: indName.trim(),
          mobileNumber: indMobile.trim(),
          email: indEmail.trim() || undefined,
        });
        const newId = res.data?.data?.id || res.data?.id;
        // Upload national ID if provided
        if (indNationalIdFile && newId) {
          const formData = new FormData();
          formData.append("file", indNationalIdFile);
          await api.post(`/suppliers/${newId}/national-id`, formData, {
            headers: { "Content-Type": "multipart/form-data" },
          });
        }
        toast.success(t("suppliers.created"));
        setDialogOpen(false);
        resetForm();
        fetchSuppliers();
      } catch {
        toast.error(t("suppliers.failedCreate"));
      } finally {
        setSubmitting(false);
      }
    }
  }

  async function handleExport() {
    setExporting(true);
    try {
      const res = await api.get("/suppliers/export/excel", {
        responseType: "blob",
      });
      const url = window.URL.createObjectURL(new Blob([res.data]));
      const link = document.createElement("a");
      link.href = url;
      const date = localDateStr(new Date());
      link.setAttribute("download", `suppliers_${date}.xlsx`);
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
      toast.success(t("suppliers.exportSuccess"));
    } catch {
      toast.error(t("suppliers.failedExport"));
    } finally {
      setExporting(false);
    }
  }

  async function handleDownloadTemplate() {
    try {
      const res = await api.get("/suppliers/import/template", {
        responseType: "blob",
      });
      const url = window.URL.createObjectURL(new Blob([res.data]));
      const link = document.createElement("a");
      link.href = url;
      link.setAttribute("download", "suppliers_import_template.xlsx");
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
    } catch {
      toast.error(t("suppliers.failedTemplate"));
    }
  }

  async function handleImportFile(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;

    setImporting(true);
    try {
      const formData = new FormData();
      formData.append("file", file);
      const res = await api.post("/suppliers/import/excel", formData, {
        headers: { "Content-Type": "multipart/form-data" },
      });
      const result = res.data.data;
      setImportResult({
        open: true,
        imported: result.imported,
        errors: result.errors,
      });
      if (result.imported > 0) {
        fetchSuppliers();
      }
    } catch (err: unknown) {
      const message =
        (err as { response?: { data?: { message?: string } } })?.response?.data
          ?.message || t("suppliers.failedImport");
      toast.error(message);
    } finally {
      setImporting(false);
      if (importFileRef.current) {
        importFileRef.current.value = "";
      }
    }
  }

  function openAccountDialog(supplier: Supplier) {
    setAccountSupplierId(supplier.id);
    setAccountSupplierName(supplier.legalName);
    setAccountSupplierPhone(supplier.phone || "");
    setAccountPassword("");
    setAccountDialogOpen(true);
  }

  function openPasswordDialog(supplier: Supplier) {
    setAccountSupplierId(supplier.id);
    setAccountSupplierName(supplier.legalName);
    setNewPassword("");
    setPasswordDialogOpen(true);
  }

  async function handleCreateAccount() {
    if (!accountSupplierId || !accountPassword.trim()) {
      toast.error("Password is required");
      return;
    }
    if (accountPassword.length < 6) {
      toast.error("Password must be at least 6 characters");
      return;
    }
    try {
      setSubmitting(true);
      await api.post(`/suppliers/${accountSupplierId}/account`, {
        password: accountPassword,
      });
      toast.success("Supplier account created successfully");
      setAccountDialogOpen(false);
      fetchSuppliers();
    } catch {
      toast.error("Failed to create account");
    } finally {
      setSubmitting(false);
    }
  }

  async function handleResetPassword() {
    if (!accountSupplierId || !newPassword.trim()) {
      toast.error("Password is required");
      return;
    }
    if (newPassword.length < 6) {
      toast.error("Password must be at least 6 characters");
      return;
    }
    try {
      setSubmitting(true);
      await api.patch(`/suppliers/${accountSupplierId}/account/password`, {
        password: newPassword,
      });
      toast.success("Password reset successfully");
      setPasswordDialogOpen(false);
    } catch {
      toast.error("Failed to reset password");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <PageHeader
          title={t("suppliers.title")}
          description={t("suppliers.description")}
        />
        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            className="gap-1.5"
            onClick={handleDownloadTemplate}
          >
            <FileDown className="h-4 w-4" />
            {t("common.template")}
          </Button>
          <Button
            variant="outline"
            size="sm"
            className="gap-1.5"
            onClick={() => importFileRef.current?.click()}
            disabled={importing}
          >
            {importing ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <FileUp className="h-4 w-4" />
            )}
            {t("common.import")}
          </Button>
          <Button
            variant="outline"
            size="sm"
            className="gap-1.5"
            onClick={handleExport}
            disabled={exporting}
          >
            {exporting ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <FileSpreadsheet className="h-4 w-4" />
            )}
            {t("common.export")}
          </Button>
          {canAddSupplier && (
          <Button size="sm" className="gap-1.5" onClick={openDialog}>
            <Plus className="h-4 w-4" />
            {t("suppliers.addSupplier")}
          </Button>
          )}
        </div>
      </div>

      {/* Hidden file input for import */}
      <input
        ref={importFileRef}
        type="file"
        className="hidden"
        accept=".xlsx,.xls"
        onChange={handleImportFile}
      />

      {loading ? (
        <div className="flex items-center justify-center py-20">
          <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
        </div>
      ) : suppliers.length === 0 ? (
        <div className="flex flex-col items-center justify-center gap-4 py-20">
          <EmptyState
            icon={Truck}
            heading="No suppliers yet"
            description="Add your first supplier to get started."
          />
          {canAddSupplier && (
            <Button
              size="sm"
              className="gap-1.5 bg-primary text-primary-foreground hover:bg-primary/90"
              onClick={openDialog}
            >
              <Plus className="h-4 w-4" />
              {t("suppliers.addSupplier")}
            </Button>
          )}
        </div>
      ) : (
        <>
          <TableFilterBar
            search={search}
            onSearchChange={setSearch}
            placeholder={t("common.search") + "..."}
          />
          {selectedIds.size > 0 && (
            <div className="flex items-center gap-3 rounded-lg border border-red-500/20 bg-red-500/5 px-4 py-2">
              <span className="text-sm text-foreground font-medium">
                {selectedIds.size} selected
              </span>
              <Button
                variant="destructive"
                size="sm"
                className="gap-1.5"
                onClick={openBulkDeleteDialog}
              >
                <Trash2 className="h-3.5 w-3.5" />
                Delete Selected
              </Button>
              <Button
                variant="ghost"
                size="sm"
                className="text-muted-foreground"
                onClick={() => setSelectedIds(new Set())}
              >
                Clear
              </Button>
            </div>
          )}
          <div className="flex items-center justify-between text-sm text-muted-foreground">
            <span>
              {t("common.showing")} {sortedData.length} {t("common.of")} {total} {t("suppliers.title").toLowerCase()}
            </span>
            {totalPages > 1 && (
              <div className="flex items-center gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  disabled={page <= 1}
                  onClick={() => setPage((p) => Math.max(1, p - 1))}
                >
                  {t("common.previous")}
                </Button>
                <span className="text-xs">
                  {page} / {totalPages}
                </span>
                <Button
                  variant="outline"
                  size="sm"
                  disabled={page >= totalPages}
                  onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                >
                  {t("common.next")}
                </Button>
              </div>
            )}
          </div>
          <div className="flex justify-end mb-2">
            <ColumnVisibilityControl columns={SUPPLIERS_COL_DEFS} visibility={supplierColVis} onSave={saveSupplierColVis} />
          </div>
          <div className="overflow-x-auto [overflow-y:clip]">
            <Table>
              <TableHeader>
                <TableRow className="border-border bg-muted">
                  <TableHead className="w-10">
                    <Checkbox
                      checked={sortedData.length > 0 && selectedIds.size === sortedData.length}
                      onCheckedChange={toggleSelectAll}
                    />
                  </TableHead>
                  {isVis("type") && <TableHead className="text-muted-foreground text-xs">Type</TableHead>}
                  {isVis("legalName") && <SortableHeader label={t("agents.legalName")} sortKey="legalName" currentKey={sortKey} currentDir={sortDir} onSort={onSort} />}
                  {isVis("tradeName") && <SortableHeader label={t("agents.tradeName")} sortKey="tradeName" currentKey={sortKey} currentDir={sortDir} onSort={onSort} />}
                  {isVis("taxId") && <TableHead className="text-muted-foreground text-xs">{t("agents.taxId")}</TableHead>}
                  {isVis("city") && <SortableHeader label={t("locations.city")} sortKey="city" currentKey={sortKey} currentDir={sortDir} onSort={onSort} />}
                  {isVis("country") && <SortableHeader label={t("locations.country")} sortKey="country" currentKey={sortKey} currentDir={sortDir} onSort={onSort} />}
                  {isVis("phone") && <TableHead className="text-muted-foreground text-xs">{t("agents.phone")}</TableHead>}
                  {isVis("account") && <TableHead className="text-muted-foreground text-xs">Account</TableHead>}
                  {isVis("status") && <TableHead className="text-muted-foreground text-xs">{t("common.status")}</TableHead>}
                  {isVis("actions") && <TableHead className="text-right text-muted-foreground text-xs">{t("common.actions")}</TableHead>}
                </TableRow>
              </TableHeader>
              <TableBody>
                {sortedData.map((supplier, idx) => (
                <TableRow
                  key={supplier.id}
                  className={`border-border ${idx % 2 === 0 ? "bg-gray-100/25 dark:bg-gray-800/25" : "bg-gray-200/50 dark:bg-gray-700/50"}`}
                >
                  <TableCell>
                    <Checkbox
                      checked={selectedIds.has(supplier.id)}
                      onCheckedChange={() => toggleSelect(supplier.id)}
                    />
                  </TableCell>
                  {isVis("type") && <TableCell><Badge variant="outline" className="text-xs">{supplier.supplierType === "INDIVIDUAL" ? "Individual" : "Company"}</Badge></TableCell>}
                  {isVis("legalName") && <TableCell className="font-medium text-foreground">{supplier.legalName}</TableCell>}
                  {isVis("tradeName") && <TableCell className="text-muted-foreground">{supplier.tradeName || "-"}</TableCell>}
                  {isVis("taxId") && <TableCell className="text-muted-foreground">{supplier.taxId || "-"}</TableCell>}
                  {isVis("city") && <TableCell className="text-muted-foreground">{supplier.city || "-"}</TableCell>}
                  {isVis("country") && <TableCell className="text-muted-foreground">{supplier.country || "-"}</TableCell>}
                  {isVis("phone") && <TableCell className="text-muted-foreground">{supplier.phone || "-"}</TableCell>}
                  {isVis("account") && (
                    <TableCell>
                      {supplier.userId ? (
                        <div className="flex items-center gap-1">
                          <Badge variant="outline" className="text-xs">{supplier.user?.email}</Badge>
                          {canResetPassword && <Button variant="ghost" size="sm" className="h-7 gap-1 px-2 text-muted-foreground hover:text-foreground" onClick={() => openPasswordDialog(supplier)}><KeyRound className="h-3.5 w-3.5" />{t("common.reset")}</Button>}
                        </div>
                      ) : canCreateAccount ? (
                        <Button variant="ghost" size="sm" className="h-7 gap-1 px-2 text-muted-foreground hover:text-foreground" onClick={() => openAccountDialog(supplier)}><UserPlus className="h-3.5 w-3.5" />Create Account</Button>
                      ) : <span className="text-xs text-muted-foreground">—</span>}
                    </TableCell>
                  )}
                  {isVis("status") && (
                    <TableCell>
                      {canToggleStatus ? (
                        <button onClick={() => handleToggleStatus(supplier.id)} className="cursor-pointer">
                          {supplier.isActive ? <Badge className="bg-emerald-500/15 text-emerald-600 dark:text-emerald-400 border-emerald-500/20 hover:bg-emerald-500/25 transition-colors">{t("common.active")}</Badge> : <Badge className="bg-red-500/15 text-red-600 dark:text-red-400 border-red-500/20 hover:bg-red-500/25 transition-colors">{t("common.inactive")}</Badge>}
                        </button>
                      ) : (supplier.isActive ? <Badge className="bg-emerald-500/15 text-emerald-600 dark:text-emerald-400 border-emerald-500/20">{t("common.active")}</Badge> : <Badge className="bg-red-500/15 text-red-600 dark:text-red-400 border-red-500/20">{t("common.inactive")}</Badge>)}
                    </TableCell>
                  )}
                  {isVis("actions") && (
                    <TableCell className="text-right">
                      <div className="flex items-center justify-end gap-1">
                        <Button variant="ghost" size="sm" className="gap-1 text-muted-foreground hover:text-foreground" onClick={() => router.push(`/dashboard/suppliers/${supplier.id}`)}><Eye className="h-3.5 w-3.5" />{t("common.view")}</Button>
                        {canEditSupplier && <Button variant="ghost" size="sm" className="text-muted-foreground hover:text-foreground" onClick={() => openEditDialog(supplier)}>{t("common.edit")}</Button>}
                        {canDeleteSupplier && <Button variant="ghost" size="sm" className="text-red-500/70 hover:text-red-500 hover:bg-red-500/10" onClick={() => openDeleteDialog(supplier)}><Trash2 className="h-3.5 w-3.5" /></Button>}
                      </div>
                    </TableCell>
                  )}
                </TableRow>
              ))}
              </TableBody>
            </Table>
          </div>
        </>
      )}

      {/* Add Supplier Dialog (Tabbed: Company / Individual) */}
      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogContent className="border-border bg-popover text-foreground sm:max-w-lg">
          <DialogHeader>
            <DialogTitle className="text-foreground">{t("suppliers.addSupplier")}</DialogTitle>
          </DialogHeader>

          <Tabs value={supplierTab} onValueChange={(v) => setSupplierTab(v as "COMPANY" | "INDIVIDUAL")} className="w-full">
            <TabsList className="bg-muted w-full">
              <TabsTrigger value="COMPANY" className="flex-1">Company</TabsTrigger>
              <TabsTrigger value="INDIVIDUAL" className="flex-1">Individual</TabsTrigger>
            </TabsList>

            {/* Company Tab */}
            <TabsContent value="COMPANY">
              <div className="grid grid-cols-1 gap-4 py-4 sm:grid-cols-2">
                {canFormLegalName && (
                <div className="space-y-2">
                  <Label htmlFor="legalName" className="text-muted-foreground">
                    {t("agents.legalName")} *
                  </Label>
                  <Input
                    id="legalName"
                    value={legalName}
                    onChange={(e) => setLegalName(e.target.value)}
                    placeholder="Company legal name"
                    className="border-border bg-card text-foreground placeholder:text-muted-foreground"
                  />
                </div>
                )}
                {canFormTradeName && (
                <div className="space-y-2">
                  <Label htmlFor="tradeName" className="text-muted-foreground">
                    {t("agents.tradeName")}
                  </Label>
                  <Input
                    id="tradeName"
                    value={tradeName}
                    onChange={(e) => setTradeName(e.target.value)}
                    placeholder="Trade / brand name"
                    className="border-border bg-card text-foreground placeholder:text-muted-foreground"
                  />
                </div>
                )}
                {canFormTaxId && (
                <div className="space-y-2">
                  <Label htmlFor="taxId" className="text-muted-foreground">
                    {t("agents.taxId")}
                  </Label>
                  <Input
                    id="taxId"
                    value={taxId}
                    onChange={(e) => setTaxId(e.target.value)}
                    placeholder="Tax registration number"
                    className="border-border bg-card text-foreground placeholder:text-muted-foreground"
                  />
                </div>
                )}
                {canFormContactInfo && (
                <div className="space-y-2">
                  <Label htmlFor="phone" className="text-muted-foreground">
                    {t("agents.phone")}
                  </Label>
                  <Input
                    id="phone"
                    value={phone}
                    onChange={(e) => setPhone(e.target.value)}
                    placeholder="+20 xxx xxx xxxx"
                    className="border-border bg-card text-foreground placeholder:text-muted-foreground"
                  />
                </div>
                )}
                {canFormContactInfo && (
                <div className="space-y-2">
                  <Label htmlFor="email" className="text-muted-foreground">
                    {t("common.email")}
                  </Label>
                  <Input
                    id="email"
                    type="email"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    placeholder="contact@company.com"
                    className="border-border bg-card text-foreground placeholder:text-muted-foreground"
                  />
                </div>
                )}
                {canFormContactInfo && (
                <div className="space-y-2">
                  <Label htmlFor="city" className="text-muted-foreground">
                    {t("locations.city")}
                  </Label>
                  <Input
                    id="city"
                    value={city}
                    onChange={(e) => setCity(e.target.value)}
                    placeholder="City"
                    className="border-border bg-card text-foreground placeholder:text-muted-foreground"
                  />
                </div>
                )}
                {canFormContactInfo && (
                <div className="space-y-2">
                  <Label htmlFor="country" className="text-muted-foreground">
                    {t("locations.country")}
                  </Label>
                  <Input
                    id="country"
                    value={country}
                    onChange={(e) => setCountry(e.target.value)}
                    placeholder="Country"
                    className="border-border bg-card text-foreground placeholder:text-muted-foreground"
                  />
                </div>
                )}
                {canFormContactInfo && (
                <div className="col-span-2 space-y-2">
                  <Label htmlFor="address" className="text-muted-foreground">
                    {t("agents.address")}
                  </Label>
                  <Input
                    id="address"
                    value={address}
                    onChange={(e) => setAddress(e.target.value)}
                    placeholder="Full street address"
                    className="border-border bg-card text-foreground placeholder:text-muted-foreground"
                  />
                </div>
                )}
              </div>
            </TabsContent>

            {/* Individual Tab */}
            <TabsContent value="INDIVIDUAL">
              <div className="grid grid-cols-1 gap-4 py-4 sm:grid-cols-2">
                <div className="col-span-2 space-y-2">
                  <Label htmlFor="indName" className="text-muted-foreground">
                    Name *
                  </Label>
                  <Input
                    id="indName"
                    value={indName}
                    onChange={(e) => setIndName(e.target.value)}
                    placeholder="Full name"
                    className="border-border bg-card text-foreground placeholder:text-muted-foreground"
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="indMobile" className="text-muted-foreground">
                    Mobile *
                  </Label>
                  <Input
                    id="indMobile"
                    value={indMobile}
                    onChange={(e) => setIndMobile(e.target.value)}
                    placeholder="+20 100 000 0000"
                    className="border-border bg-card text-foreground placeholder:text-muted-foreground"
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="indEmail" className="text-muted-foreground">
                    {t("common.email")}
                  </Label>
                  <Input
                    id="indEmail"
                    type="email"
                    value={indEmail}
                    onChange={(e) => setIndEmail(e.target.value)}
                    placeholder="email@example.com"
                    className="border-border bg-card text-foreground placeholder:text-muted-foreground"
                  />
                </div>
                <div className="col-span-2 space-y-2">
                  <Label htmlFor="indNationalId" className="text-muted-foreground">
                    National ID (upload copy)
                  </Label>
                  <Input
                    id="indNationalId"
                    ref={nationalIdRef}
                    type="file"
                    accept="image/*,.pdf"
                    onChange={(e) => setIndNationalIdFile(e.target.files?.[0] || null)}
                    className="border-border bg-card text-foreground file:text-muted-foreground"
                  />
                </div>
              </div>
            </TabsContent>
          </Tabs>

          <DialogFooter>
            <Button
              variant="ghost"
              onClick={() => setDialogOpen(false)}
              className="text-muted-foreground hover:text-foreground"
            >
              {t("common.cancel")}
            </Button>
            <Button
              onClick={handleSubmit}
              disabled={submitting}
              className="gap-1.5 bg-primary text-primary-foreground hover:bg-primary/90"
            >
              {submitting && <Loader2 className="h-4 w-4 animate-spin" />}
              {t("common.create")} {t("suppliers.title")}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Create Account Dialog */}
      <Dialog open={accountDialogOpen} onOpenChange={setAccountDialogOpen}>
        <DialogContent className="border-border bg-popover text-popover-foreground sm:max-w-md">
          <DialogHeader>
            <DialogTitle>Create Account for {accountSupplierName}</DialogTitle>
          </DialogHeader>
          <div className="space-y-4 py-2">
            <div className="space-y-2">
              <Label className="text-muted-foreground">
                {t("suppliers.phone")}
              </Label>
              <Input
                value={accountSupplierPhone}
                disabled
                className="border-border bg-muted/30 text-foreground"
              />
              <p className="text-xs text-muted-foreground">{t("drivers.loginWithMobile")}</p>
            </div>
            <div className="space-y-2">
              <Label htmlFor="acct-password" className="text-muted-foreground">
                {t("common.password")} *
              </Label>
              <Input
                id="acct-password"
                type="password"
                placeholder="Min 6 characters"
                value={accountPassword}
                onChange={(e) => setAccountPassword(e.target.value)}
                className="border-border bg-muted/50 text-foreground placeholder:text-muted-foreground/50"
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="ghost" onClick={() => setAccountDialogOpen(false)} disabled={submitting}>
              {t("common.cancel")}
            </Button>
            <Button onClick={handleCreateAccount} disabled={submitting} className="gap-1.5">
              {submitting && <Loader2 className="h-4 w-4 animate-spin" />}
              Create Account
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Reset Password Dialog */}
      <Dialog open={passwordDialogOpen} onOpenChange={setPasswordDialogOpen}>
        <DialogContent className="border-border bg-popover text-popover-foreground sm:max-w-md">
          <DialogHeader>
            <DialogTitle>Reset Password for {accountSupplierName}</DialogTitle>
          </DialogHeader>
          <div className="space-y-4 py-2">
            <div className="space-y-2">
              <Label htmlFor="new-pw" className="text-muted-foreground">
                New Password *
              </Label>
              <Input
                id="new-pw"
                type="password"
                placeholder="Min 6 characters"
                value={newPassword}
                onChange={(e) => setNewPassword(e.target.value)}
                className="border-border bg-muted/50 text-foreground placeholder:text-muted-foreground/50"
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="ghost" onClick={() => setPasswordDialogOpen(false)} disabled={submitting}>
              {t("common.cancel")}
            </Button>
            <Button onClick={handleResetPassword} disabled={submitting} className="gap-1.5">
              {submitting && <Loader2 className="h-4 w-4 animate-spin" />}
              Reset Password
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Edit Supplier Dialog */}
      <Dialog
        open={editDialogOpen}
        onOpenChange={(open) => {
          setEditDialogOpen(open);
          if (!open) setEditingSupplier(null);
        }}
      >
        <DialogContent className="border-border bg-popover text-foreground sm:max-w-lg">
          <DialogHeader>
            <DialogTitle className="text-foreground">{t("suppliers.editSupplier")}</DialogTitle>
          </DialogHeader>

          <div className="grid grid-cols-1 gap-4 py-4 sm:grid-cols-2">
            {canFormLegalName && (
            <div className="space-y-2">
              <Label htmlFor="edit-legalName" className="text-muted-foreground">
                {t("agents.legalName")} *
              </Label>
              <Input
                id="edit-legalName"
                value={legalName}
                onChange={(e) => setLegalName(e.target.value)}
                placeholder="Company legal name"
                className="border-border bg-card text-foreground placeholder:text-muted-foreground"
              />
            </div>
            )}

            {canFormTradeName && (
            <div className="space-y-2">
              <Label htmlFor="edit-tradeName" className="text-muted-foreground">
                {t("agents.tradeName")}
              </Label>
              <Input
                id="edit-tradeName"
                value={tradeName}
                onChange={(e) => setTradeName(e.target.value)}
                placeholder="Trade / brand name"
                className="border-border bg-card text-foreground placeholder:text-muted-foreground"
              />
            </div>
            )}

            {canFormTaxId && (
            <div className="space-y-2">
              <Label htmlFor="edit-taxId" className="text-muted-foreground">
                {t("agents.taxId")}
              </Label>
              <Input
                id="edit-taxId"
                value={taxId}
                onChange={(e) => setTaxId(e.target.value)}
                placeholder="Tax registration number"
                className="border-border bg-card text-foreground placeholder:text-muted-foreground"
              />
            </div>
            )}

            {canFormContactInfo && (
            <div className="space-y-2">
              <Label htmlFor="edit-phone" className="text-muted-foreground">
                {t("agents.phone")}
              </Label>
              <Input
                id="edit-phone"
                value={phone}
                onChange={(e) => setPhone(e.target.value)}
                placeholder="+20 xxx xxx xxxx"
                className="border-border bg-card text-foreground placeholder:text-muted-foreground"
              />
            </div>
            )}

            {canFormContactInfo && (
            <div className="space-y-2">
              <Label htmlFor="edit-email" className="text-muted-foreground">
                {t("common.email")}
              </Label>
              <Input
                id="edit-email"
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="contact@company.com"
                className="border-border bg-card text-foreground placeholder:text-muted-foreground"
              />
            </div>
            )}

            {canFormContactInfo && (
            <div className="space-y-2">
              <Label htmlFor="edit-city" className="text-muted-foreground">
                {t("locations.city")}
              </Label>
              <Input
                id="edit-city"
                value={city}
                onChange={(e) => setCity(e.target.value)}
                placeholder="City"
                className="border-border bg-card text-foreground placeholder:text-muted-foreground"
              />
            </div>
            )}

            {canFormContactInfo && (
            <div className="space-y-2">
              <Label htmlFor="edit-country" className="text-muted-foreground">
                {t("locations.country")}
              </Label>
              <Input
                id="edit-country"
                value={country}
                onChange={(e) => setCountry(e.target.value)}
                placeholder="Country"
                className="border-border bg-card text-foreground placeholder:text-muted-foreground"
              />
            </div>
            )}

            {canFormContactInfo && (
            <div className="col-span-2 space-y-2">
              <Label htmlFor="edit-address" className="text-muted-foreground">
                {t("agents.address")}
              </Label>
              <Input
                id="edit-address"
                value={address}
                onChange={(e) => setAddress(e.target.value)}
                placeholder="Full street address"
                className="border-border bg-card text-foreground placeholder:text-muted-foreground"
              />
            </div>
            )}

            {/* Car Types */}
            <div className="col-span-2 space-y-2">
              <Label className="text-muted-foreground">Car Types</Label>
              <div className="grid grid-cols-2 gap-2 rounded-md border border-border p-2">
                {vehicleTypes.length === 0 ? (
                  <span className="col-span-2 text-xs text-muted-foreground">No car types available</span>
                ) : (
                  vehicleTypes.map((vt) => (
                    <label key={vt.id} className="flex items-center gap-2 cursor-pointer select-none">
                      <Checkbox
                        checked={selectedCarTypeIds.has(vt.id)}
                        onCheckedChange={() => {
                          setSelectedCarTypeIds((prev) => {
                            const next = new Set(prev);
                            if (next.has(vt.id)) next.delete(vt.id);
                            else next.add(vt.id);
                            return next;
                          });
                        }}
                        className="h-4 w-4"
                      />
                      <span className="text-sm">{vt.name} <span className="text-muted-foreground">({vt.seatCapacity} seats)</span></span>
                    </label>
                  ))
                )}
              </div>
            </div>
          </div>

          <DialogFooter>
            <Button
              variant="ghost"
              onClick={() => setEditDialogOpen(false)}
              className="text-muted-foreground hover:text-foreground"
            >
              {t("common.cancel")}
            </Button>
            <Button
              onClick={handleUpdate}
              disabled={submitting}
              className="gap-1.5 bg-primary text-primary-foreground hover:bg-primary/90"
            >
              {submitting && <Loader2 className="h-4 w-4 animate-spin" />}
              {t("common.saveChanges")}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Delete Confirmation Dialog */}
      <Dialog open={deleteDialogOpen} onOpenChange={setDeleteDialogOpen}>
        <DialogContent className="border-border bg-popover text-popover-foreground sm:max-w-md">
          <DialogHeader>
            <DialogTitle className="text-foreground">
              {deleteTarget ? "Delete Supplier" : "Delete Selected Suppliers"}
            </DialogTitle>
          </DialogHeader>
          <div className="py-4">
            {deleteTarget ? (
              <p className="text-sm text-muted-foreground">
                Are you sure you want to delete <span className="font-medium text-foreground">{deleteTarget.name}</span>? This action cannot be undone.
              </p>
            ) : (
              <p className="text-sm text-muted-foreground">
                Are you sure you want to delete <span className="font-medium text-foreground">{selectedIds.size} suppliers</span>? This action cannot be undone.
              </p>
            )}
          </div>
          <DialogFooter>
            <Button
              variant="ghost"
              onClick={() => setDeleteDialogOpen(false)}
              disabled={deleting}
              className="text-muted-foreground hover:text-foreground"
            >
              {t("common.cancel")}
            </Button>
            <Button
              variant="destructive"
              onClick={handleDelete}
              disabled={deleting}
              className="gap-1.5"
            >
              {deleting && <Loader2 className="h-4 w-4 animate-spin" />}
              {t("common.delete")}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Import Results Dialog */}
      <Dialog
        open={importResult.open}
        onOpenChange={(open) => {
          if (!open) setImportResult({ open: false, imported: 0, errors: [] });
        }}
      >
        <DialogContent className="border-border bg-popover text-popover-foreground max-w-lg">
          <DialogHeader>
            <DialogTitle>{t("suppliers.importResults")}</DialogTitle>
          </DialogHeader>
          <div className="space-y-4 py-2">
            <div className="flex items-center gap-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-full bg-emerald-500/15">
                <FileSpreadsheet className="h-5 w-5 text-emerald-500" />
              </div>
              <div>
                <p className="text-sm font-medium text-foreground">
                  {importResult.imported} {t("suppliers.imported")}
                </p>
                {importResult.errors.length > 0 && (
                  <p className="text-xs text-muted-foreground">
                    {importResult.errors.length} {t("suppliers.errors")}
                  </p>
                )}
              </div>
            </div>

            {importResult.errors.length > 0 && (
              <div className="max-h-48 overflow-y-auto rounded-lg border border-border bg-muted/30 p-3">
                <p className="mb-2 text-xs font-medium text-muted-foreground uppercase">
                  Errors
                </p>
                <ul className="space-y-1">
                  {importResult.errors.map((err, i) => (
                    <li
                      key={i}
                      className="text-xs text-destructive flex items-start gap-1.5"
                    >
                      <AlertTriangle className="mt-0.5 h-3 w-3 shrink-0" />
                      {err}
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>
          <DialogFooter>
            <Button
              onClick={() =>
                setImportResult({ open: false, imported: 0, errors: [] })
              }
            >
              {t("common.close")}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
