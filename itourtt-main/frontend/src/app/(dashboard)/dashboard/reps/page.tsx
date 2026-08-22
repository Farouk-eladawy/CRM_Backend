"use client";

import { useEffect, useState, useCallback, useRef, useMemo } from "react";
import { useRouter } from "next/navigation";
import {
  UserCheck,
  Plus,
  Loader2,
  Pencil,
  Trash2,
  Upload,
  Download,
  KeyRound,
  UserPlus,
  FileDown,
  FileUp,
  FileSpreadsheet,
  AlertTriangle,
  ExternalLink,
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
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
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

const REPS_COL_DEFS: ColumnDef[] = [
  { key: "name", label: "Name" },
  { key: "mobile", label: "Mobile" },
  { key: "feePerFlight", label: "Fee/Flight" },
  { key: "attachment", label: "Attachment" },
  { key: "account", label: "Account" },
  { key: "status", label: "Status" },
  { key: "actions", label: "Actions" },
];

interface Rep {
  id: string;
  name: string;
  mobileNumber: string;
  feePerFlight: string | number;
  attachmentUrl: string | null;
  userId: string | null;
  user?: { id: string; email: string; name: string; role: string; isActive: boolean } | null;
  isActive: boolean;
}

interface RepsResponse {
  data: Rep[];
  total: number;
  page: number;
  limit: number;
}

export default function RepsPage() {
  const t = useT();
  const router = useRouter();
  const canAddRep = usePermission("reps.addButton");
  const canEditRep = usePermission("reps.table.editButton");
  const canDeleteRep = usePermission("reps.table.deleteButton");
  const canToggleStatus = usePermission("reps.table.toggleStatus");
  const canUploadAttachment = usePermission("reps.table.uploadAttachment");
  const canCreateAccount = usePermission("reps.table.createAccount");
  const canResetPassword = usePermission("reps.table.resetPassword");
  const canImport = usePermission("reps.import");
  const canExport = usePermission("reps.export");
  const canDownloadTemplate = usePermission("reps.downloadTemplate");
  const canFormName = usePermission("reps.form.name");
  const canFormMobile = usePermission("reps.form.mobile");
  const canFormFeePerFlight = usePermission("reps.form.feePerFlight");
  const [reps, setReps] = useState<Rep[]>([]);
  const [loading, setLoading] = useState(true);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editDialogOpen, setEditDialogOpen] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [editingRep, setEditingRep] = useState<Rep | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const importFileRef = useRef<HTMLInputElement>(null);
  const [uploadingId, setUploadingId] = useState<string | null>(null);
  const [importing, setImporting] = useState(false);
  const [exporting, setExporting] = useState(false);
  const [importResult, setImportResult] = useState<{
    open: boolean;
    imported: number;
    errors: string[];
  }>({ open: false, imported: 0, errors: [] });

  const [search, setSearch] = useState("");
  const [statusTab, setStatusTab] = useState<"active" | "inactive">("active");

  const activeCount = useMemo(() => reps.filter((r) => r.isActive).length, [reps]);
  const inactiveCount = reps.length - activeCount;

  const filtered = useMemo(() => {
    const wantActive = statusTab === "active";
    let result = reps.filter((r) => r.isActive === wantActive);
    if (search.trim()) {
      const q = search.toLowerCase();
      result = result.filter(
        (r) =>
          r.name.toLowerCase().includes(q) ||
          (r.mobileNumber && r.mobileNumber.toLowerCase().includes(q))
      );
    }
    return result;
  }, [reps, search, statusTab]);

  const { sortedData, sortKey, sortDir, onSort } = useSortable(filtered);
  const { visibility: repColVis, saveVisibility: saveRepColVis } = useColumnPreferences("reps_list", REPS_COL_DEFS.map((c) => c.key));
  const isVis = (key: string) => repColVis[key] !== false;

  // Delete
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [deletingRep, setDeletingRep] = useState<Rep | null>(null);
  const [deleting, setDeleting] = useState(false);

  // Account management
  const [accountDialogOpen, setAccountDialogOpen] = useState(false);
  const [passwordDialogOpen, setPasswordDialogOpen] = useState(false);
  const [accountRepId, setAccountRepId] = useState<string | null>(null);
  const [accountRepName, setAccountRepName] = useState("");
  const [accountRepPhone, setAccountRepPhone] = useState("");
  const [accountPassword, setAccountPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");

  // Form fields
  const [name, setName] = useState("");
  const [mobileNumber, setMobileNumber] = useState("");
  const [feePerFlight, setFeePerFlight] = useState("");

  const fetchReps = useCallback(async () => {
    try {
      setLoading(true);
      const { data } = await api.get<RepsResponse>("/reps", { params: { limit: 1000 } });
      setReps(data.data);
    } catch {
      toast.error(t("drivers.failedLoad"));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchReps();
  }, [fetchReps]);

  function resetForm() {
    setName("");
    setMobileNumber("");
    setFeePerFlight("");
  }

  function openAddDialog() {
    resetForm();
    setDialogOpen(true);
  }

  function openEditDialog(rep: Rep) {
    setEditingRep(rep);
    setName(rep.name);
    setMobileNumber(rep.mobileNumber);
    setFeePerFlight(String(Number(rep.feePerFlight) || ""));
    setEditDialogOpen(true);
  }

  async function handleToggleStatus(id: string) {
    try {
      await api.patch(`/reps/${id}/status`);
      setReps((prev) =>
        prev.map((r) => (r.id === id ? { ...r, isActive: !r.isActive } : r))
      );
      toast.success(t("common.statusUpdated"));
    } catch {
      toast.error(t("common.failedStatusUpdate"));
    }
  }

  function openDeleteDialog(rep: Rep) {
    setDeletingRep(rep);
    setDeleteDialogOpen(true);
  }

  async function handleDelete() {
    if (!deletingRep) return;
    try {
      setDeleting(true);
      await api.delete(`/reps/${deletingRep.id}`);
      toast.success(t("reps.deleted"));
      setDeleteDialogOpen(false);
      setDeletingRep(null);
      fetchReps();
    } catch {
      toast.error(t("reps.failedDelete"));
    } finally {
      setDeleting(false);
    }
  }

  async function handleCreate() {
    if (!name.trim() || !mobileNumber.trim()) {
      toast.error(t("drivers.nameRequired"));
      return;
    }

    try {
      setSubmitting(true);
      await api.post("/reps", {
        name: name.trim(),
        mobileNumber: mobileNumber.trim(),
        ...(feePerFlight !== "" && { feePerFlight: parseFloat(feePerFlight) }),
      });
      toast.success(t("drivers.created"));
      setDialogOpen(false);
      resetForm();
      fetchReps();
    } catch {
      toast.error(t("drivers.failedCreate"));
    } finally {
      setSubmitting(false);
    }
  }

  async function handleUpdate() {
    if (!editingRep) return;
    if (!name.trim() || !mobileNumber.trim()) {
      toast.error(t("drivers.nameRequired"));
      return;
    }

    try {
      setSubmitting(true);
      await api.patch(`/reps/${editingRep.id}`, {
        name: name.trim(),
        mobileNumber: mobileNumber.trim(),
        feePerFlight: feePerFlight !== "" ? parseFloat(feePerFlight) : 0,
      });
      toast.success(t("drivers.updated"));
      setEditDialogOpen(false);
      setEditingRep(null);
      resetForm();
      fetchReps();
    } catch {
      toast.error(t("drivers.failedUpdate"));
    } finally {
      setSubmitting(false);
    }
  }

  async function handleAttachmentUpload(repId: string, file: File) {
    setUploadingId(repId);
    try {
      const formData = new FormData();
      formData.append("file", file);
      const res = await api.post<{ url: string }>(
        `/reps/${repId}/attachment`,
        formData,
        { headers: { "Content-Type": "multipart/form-data" } }
      );
      setReps((prev) =>
        prev.map((r) =>
          r.id === repId ? { ...r, attachmentUrl: res.data.url } : r
        )
      );
      toast.success(t("drivers.attachmentUploaded"));
    } catch {
      toast.error(t("drivers.failedUpload"));
    } finally {
      setUploadingId(null);
    }
  }

  function triggerFileUpload(repId: string) {
    setUploadingId(repId);
    if (fileInputRef.current) {
      fileInputRef.current.dataset.repId = repId;
      fileInputRef.current.value = "";
      fileInputRef.current.click();
    }
  }

  function onFileSelected(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    const repId = e.target.dataset.repId;
    if (file && repId) {
      handleAttachmentUpload(repId, file);
    } else {
      setUploadingId(null);
    }
  }

  async function handleExport() {
    setExporting(true);
    try {
      const res = await api.get("/reps/export/excel", { responseType: "blob" });
      const url = window.URL.createObjectURL(new Blob([res.data]));
      const link = document.createElement("a");
      link.href = url;
      const date = localDateStr(new Date());
      link.setAttribute("download", `reps_${date}.xlsx`);
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
      toast.success(t("reps.exportSuccess"));
    } catch {
      toast.error(t("reps.failedExport"));
    } finally {
      setExporting(false);
    }
  }

  async function handleDownloadTemplate() {
    try {
      const res = await api.get("/reps/import/template", { responseType: "blob" });
      const url = window.URL.createObjectURL(new Blob([res.data]));
      const link = document.createElement("a");
      link.href = url;
      link.setAttribute("download", "reps_import_template.xlsx");
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
    } catch {
      toast.error(t("reps.failedTemplate"));
    }
  }

  async function handleImportFile(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;

    setImporting(true);
    try {
      const formData = new FormData();
      formData.append("file", file);
      const res = await api.post("/reps/import/excel", formData, {
        headers: { "Content-Type": "multipart/form-data" },
      });
      const result = res.data.data;
      setImportResult({
        open: true,
        imported: result.imported,
        errors: result.errors,
      });
      if (result.imported > 0) {
        fetchReps();
      }
    } catch (err: unknown) {
      const message =
        (err as { response?: { data?: { message?: string } } })?.response?.data
          ?.message || t("reps.failedImport");
      toast.error(message);
    } finally {
      setImporting(false);
      if (importFileRef.current) {
        importFileRef.current.value = "";
      }
    }
  }

  function openAccountDialog(rep: Rep) {
    setAccountRepId(rep.id);
    setAccountRepName(rep.name);
    setAccountRepPhone(rep.mobileNumber);
    setAccountPassword("");
    setAccountDialogOpen(true);
  }

  function openPasswordDialog(rep: Rep) {
    setAccountRepId(rep.id);
    setAccountRepName(rep.name);
    setNewPassword("");
    setPasswordDialogOpen(true);
  }

  async function handleCreateAccount() {
    if (!accountRepId || !accountPassword.trim()) {
      toast.error(t("drivers.passwordRequired"));
      return;
    }

    try {
      setSubmitting(true);
      await api.post(`/reps/${accountRepId}/account`, {
        password: accountPassword.trim(),
      });
      toast.success(t("drivers.accountCreated"));
      setAccountDialogOpen(false);
      fetchReps();
    } catch (err: unknown) {
      const message =
        (err as { response?: { data?: { message?: string } } })?.response?.data
          ?.message || t("drivers.failedAccount");
      toast.error(message);
    } finally {
      setSubmitting(false);
    }
  }

  async function handleResetPassword() {
    if (!accountRepId || !newPassword.trim()) {
      toast.error(t("drivers.passwordRequired"));
      return;
    }

    try {
      setSubmitting(true);
      await api.patch(`/reps/${accountRepId}/account/password`, {
        password: newPassword.trim(),
      });
      toast.success(t("drivers.passwordReset"));
      setPasswordDialogOpen(false);
    } catch (err: unknown) {
      const message =
        (err as { response?: { data?: { message?: string } } })?.response?.data
          ?.message || t("drivers.failedPassword");
      toast.error(message);
    } finally {
      setSubmitting(false);
    }
  }

  const backendUrl =
    process.env.NEXT_PUBLIC_API_URL?.replace("/api", "") ??
    "http://localhost:3001";

  const repFormFields = (
    <div className="space-y-4 py-2">
      {canFormName && (
      <div className="space-y-2">
        <Label htmlFor="rep-name" className="text-muted-foreground">
          {t("common.name")} *
        </Label>
        <Input
          id="rep-name"
          placeholder={t("drivers.fullName")}
          value={name}
          onChange={(e) => setName(e.target.value)}
          className="border-border bg-muted/50 text-foreground placeholder:text-muted-foreground/50"
        />
      </div>
      )}
      {canFormMobile && (
      <div className="space-y-2">
        <Label htmlFor="rep-mobile" className="text-muted-foreground">
          {t("drivers.mobileNumber")} *
        </Label>
        <Input
          id="rep-mobile"
          placeholder="+20 xxx xxx xxxx"
          value={mobileNumber}
          onChange={(e) => setMobileNumber(e.target.value)}
          className="border-border bg-muted/50 text-foreground placeholder:text-muted-foreground/50"
        />
      </div>
      )}
      {canFormFeePerFlight && (
      <div className="space-y-2">
        <Label htmlFor="rep-fee" className="text-muted-foreground">
          {t("reps.feePerFlight")} (EGP)
        </Label>
        <Input
          id="rep-fee"
          type="number"
          min="0"
          step="0.01"
          placeholder="0.00"
          value={feePerFlight}
          onChange={(e) => setFeePerFlight(e.target.value)}
          className="border-border bg-muted/50 text-foreground placeholder:text-muted-foreground/50"
        />
      </div>
      )}
    </div>
  );

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <PageHeader
          title={t("reps.title")}
          description={t("reps.description")}
        />
        <div className="flex items-center gap-2">
          {canDownloadTemplate && (
          <Button
            variant="outline"
            size="sm"
            className="gap-1.5"
            onClick={handleDownloadTemplate}
          >
            <FileDown className="h-4 w-4" />
            {t("common.template")}
          </Button>
          )}
          {canImport && (
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
          )}
          {canExport && (
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
          )}
          {canAddRep && (
          <Button size="sm" className="gap-1.5" onClick={openAddDialog}>
            <Plus className="h-4 w-4" />
            {t("reps.addRep")}
          </Button>
          )}
        </div>
      </div>

      {/* Hidden file inputs */}
      <input
        ref={fileInputRef}
        type="file"
        className="hidden"
        onChange={onFileSelected}
        accept=".pdf,.jpg,.jpeg,.png,.doc,.docx"
      />
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
      ) : reps.length === 0 ? (
        <div className="flex flex-col items-center justify-center gap-4 py-20">
          <EmptyState
            icon={UserCheck}
            heading="No reps yet"
            description="Add reps to assign them to completed jobs."
          />
          {canAddRep && (
            <Button size="sm" className="gap-1.5" onClick={openAddDialog}>
              <Plus className="h-4 w-4" />
              {t("reps.addRep")}
            </Button>
          )}
        </div>
      ) : (
        <>
          <Tabs value={statusTab} onValueChange={(v) => setStatusTab(v as "active" | "inactive")}>
            <TabsList className="border-border bg-muted">
              <TabsTrigger value="active">
                {t("reps.activeTab")}
                <Badge variant="secondary" className="ml-1.5">{activeCount}</Badge>
              </TabsTrigger>
              <TabsTrigger value="inactive">
                {t("reps.inactiveTab")}
                <Badge variant="secondary" className="ml-1.5">{inactiveCount}</Badge>
              </TabsTrigger>
            </TabsList>
          </Tabs>
          <TableFilterBar
            search={search}
            onSearchChange={setSearch}
            placeholder={t("common.search") + "..."}
          />
          <div className="flex justify-end mb-2">
            <ColumnVisibilityControl columns={REPS_COL_DEFS} visibility={repColVis} onSave={saveRepColVis} />
          </div>
          <div className="overflow-x-auto [overflow-y:clip]">
            <Table>
              <TableHeader>
                <TableRow className="border-border bg-muted">
                  {isVis("name") && <SortableHeader label={t("common.name")} sortKey="name" currentKey={sortKey} currentDir={sortDir} onSort={onSort} />}
                  {isVis("mobile") && <SortableHeader label={t("drivers.mobile")} sortKey="mobileNumber" currentKey={sortKey} currentDir={sortDir} onSort={onSort} />}
                  {isVis("feePerFlight") && <SortableHeader label={t("reps.feePerFlight")} sortKey="feePerFlight" currentKey={sortKey} currentDir={sortDir} onSort={onSort} />}
                  {isVis("attachment") && <TableHead className="text-muted-foreground text-xs">{t("drivers.attachment")}</TableHead>}
                  {isVis("account") && <TableHead className="text-muted-foreground text-xs">{t("reps.account")}</TableHead>}
                  {isVis("status") && <TableHead className="text-muted-foreground text-xs">{t("common.status")}</TableHead>}
                  {isVis("actions") && <TableHead className="text-right text-muted-foreground text-xs">{t("common.actions")}</TableHead>}
                </TableRow>
              </TableHeader>
              <TableBody>
                {sortedData.map((rep, idx) => (
                <TableRow
                  key={rep.id}
                  className={`border-border ${idx % 2 === 0 ? "bg-gray-100/25 dark:bg-gray-800/25" : "bg-gray-200/50 dark:bg-gray-700/50"}`}
                >
                  {isVis("name") && <TableCell className="font-medium text-foreground">{rep.name}</TableCell>}
                  {isVis("mobile") && <TableCell className="text-muted-foreground">{rep.mobileNumber}</TableCell>}
                  {isVis("feePerFlight") && <TableCell className="text-muted-foreground">{Number(rep.feePerFlight) > 0 ? `${Number(rep.feePerFlight).toFixed(2)} EGP` : "-"}</TableCell>}
                  {isVis("attachment") && (
                    <TableCell>
                      {rep.attachmentUrl ? (
                        <a href={`${backendUrl}${rep.attachmentUrl}`} target="_blank" rel="noopener noreferrer" className="inline-flex items-center gap-1 text-sm text-primary hover:underline">
                          <Download className="h-3.5 w-3.5" />{t("common.view")}
                        </a>
                      ) : canUploadAttachment ? (
                        <Button variant="ghost" size="sm" className="h-7 gap-1 px-2 text-muted-foreground hover:text-foreground" onClick={() => triggerFileUpload(rep.id)} disabled={uploadingId === rep.id}>
                          {uploadingId === rep.id ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Upload className="h-3.5 w-3.5" />}
                          {t("common.upload")}
                        </Button>
                      ) : <span className="text-xs text-muted-foreground">—</span>}
                    </TableCell>
                  )}
                  {isVis("account") && (
                    <TableCell>
                      {rep.userId ? (
                        <div className="flex items-center gap-2">
                          <Badge className="bg-blue-500/15 text-blue-600 dark:text-blue-400 border-blue-500/20">{rep.user?.email ?? "Linked"}</Badge>
                          {canResetPassword && <Button variant="ghost" size="sm" className="h-7 gap-1 px-2 text-muted-foreground hover:text-foreground" onClick={() => openPasswordDialog(rep)}><KeyRound className="h-3.5 w-3.5" />{t("common.reset")}</Button>}
                        </div>
                      ) : canCreateAccount ? (
                        <Button variant="ghost" size="sm" className="h-7 gap-1 px-2 text-muted-foreground hover:text-foreground" onClick={() => openAccountDialog(rep)}>
                          <UserPlus className="h-3.5 w-3.5" />{t("reps.createAccount")}
                        </Button>
                      ) : <span className="text-xs text-muted-foreground">—</span>}
                    </TableCell>
                  )}
                  {isVis("status") && (
                    <TableCell>
                      {canToggleStatus ? (
                        <button onClick={() => handleToggleStatus(rep.id)} className="cursor-pointer">
                          {rep.isActive ? <Badge className="bg-emerald-500/15 text-emerald-600 dark:text-emerald-400 border-emerald-500/20 hover:bg-emerald-500/25 transition-colors">{t("common.active")}</Badge> : <Badge className="bg-red-500/15 text-red-600 dark:text-red-400 border-red-500/20 hover:bg-red-500/25 transition-colors">{t("common.inactive")}</Badge>}
                        </button>
                      ) : (rep.isActive ? <Badge className="bg-emerald-500/15 text-emerald-600 dark:text-emerald-400 border-emerald-500/20">{t("common.active")}</Badge> : <Badge className="bg-red-500/15 text-red-600 dark:text-red-400 border-red-500/20">{t("common.inactive")}</Badge>)}
                    </TableCell>
                  )}
                  {isVis("actions") && (
                    <TableCell className="text-right">
                      {canEditRep && <Button variant="ghost" size="sm" className="gap-1 text-muted-foreground hover:text-foreground" onClick={() => router.push(`/dashboard/reps/${rep.id}`)}><ExternalLink className="h-3.5 w-3.5" />{t("common.view")}</Button>}
                      {canEditRep && <Button variant="ghost" size="sm" className="gap-1 text-muted-foreground hover:text-foreground" onClick={() => openEditDialog(rep)}><Pencil className="h-3.5 w-3.5" />{t("common.edit")}</Button>}
                      {canDeleteRep && <Button variant="ghost" size="sm" className="gap-1 text-muted-foreground hover:text-red-600" onClick={() => openDeleteDialog(rep)}><Trash2 className="h-3.5 w-3.5" /></Button>}
                    </TableCell>
                  )}
                </TableRow>
              ))}
              {sortedData.length === 0 && (
                <TableRow className="border-border">
                  <TableCell colSpan={REPS_COL_DEFS.length} className="py-10 text-center text-muted-foreground">
                    {t("common.noData")}
                  </TableCell>
                </TableRow>
              )}
              </TableBody>
            </Table>
          </div>
        </>
      )}

      {/* Add Rep Dialog */}
      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogContent className="border-border bg-popover text-popover-foreground sm:max-w-md">
          <DialogHeader>
            <DialogTitle>{t("reps.addRep")}</DialogTitle>
          </DialogHeader>
          {repFormFields}
          <DialogFooter>
            <Button
              variant="ghost"
              onClick={() => setDialogOpen(false)}
              disabled={submitting}
            >
              {t("common.cancel")}
            </Button>
            <Button
              onClick={handleCreate}
              disabled={submitting}
              className="gap-1.5"
            >
              {submitting && <Loader2 className="h-4 w-4 animate-spin" />}
              {t("reps.addRep")}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Edit Rep Dialog */}
      <Dialog
        open={editDialogOpen}
        onOpenChange={(open) => {
          setEditDialogOpen(open);
          if (!open) setEditingRep(null);
        }}
      >
        <DialogContent className="border-border bg-popover text-popover-foreground sm:max-w-md">
          <DialogHeader>
            <DialogTitle>{t("reps.editRep")}</DialogTitle>
          </DialogHeader>
          {repFormFields}
          <DialogFooter>
            <Button
              variant="ghost"
              onClick={() => setEditDialogOpen(false)}
              disabled={submitting}
            >
              {t("common.cancel")}
            </Button>
            <Button
              onClick={handleUpdate}
              disabled={submitting}
              className="gap-1.5"
            >
              {submitting && <Loader2 className="h-4 w-4 animate-spin" />}
              {t("common.saveChanges")}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Create Account Dialog */}
      <Dialog open={accountDialogOpen} onOpenChange={setAccountDialogOpen}>
        <DialogContent className="border-border bg-popover text-popover-foreground sm:max-w-md">
          <DialogHeader>
            <DialogTitle>{t("reps.createAccountFor")} {accountRepName}</DialogTitle>
          </DialogHeader>
          <div className="space-y-4 py-2">
            <div className="space-y-2">
              <Label className="text-muted-foreground">
                {t("reps.mobileNumber")}
              </Label>
              <Input
                value={accountRepPhone}
                disabled
                className="border-border bg-muted/30 text-foreground"
              />
              <p className="text-xs text-muted-foreground">{t("drivers.loginWithMobile")}</p>
            </div>
            <div className="space-y-2">
              <Label htmlFor="account-password" className="text-muted-foreground">
                {t("common.password")} *
              </Label>
              <Input
                id="account-password"
                type="password"
                placeholder={t("drivers.minChars")}
                value={accountPassword}
                onChange={(e) => setAccountPassword(e.target.value)}
                className="border-border bg-muted/50 text-foreground placeholder:text-muted-foreground/50"
              />
            </div>
          </div>
          <DialogFooter>
            <Button
              variant="ghost"
              onClick={() => setAccountDialogOpen(false)}
              disabled={submitting}
            >
              {t("common.cancel")}
            </Button>
            <Button
              onClick={handleCreateAccount}
              disabled={submitting}
              className="gap-1.5"
            >
              {submitting && <Loader2 className="h-4 w-4 animate-spin" />}
              {t("reps.createAccount")}
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
            <DialogTitle>{t("reps.importResults")}</DialogTitle>
          </DialogHeader>
          <div className="space-y-4 py-2">
            <div className="flex items-center gap-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-full bg-emerald-500/15">
                <FileSpreadsheet className="h-5 w-5 text-emerald-500" />
              </div>
              <div>
                <p className="text-sm font-medium text-foreground">
                  {importResult.imported} {t("reps.imported")}
                </p>
                {importResult.errors.length > 0 && (
                  <p className="text-xs text-muted-foreground">
                    {importResult.errors.length} {t("reps.errors")}
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

      {/* Delete Confirmation Dialog */}
      <Dialog open={deleteDialogOpen} onOpenChange={(open) => {
        setDeleteDialogOpen(open);
        if (!open) setDeletingRep(null);
      }}>
        <DialogContent className="border-border bg-popover text-popover-foreground sm:max-w-md">
          <DialogHeader>
            <DialogTitle>{t("reps.deleteRep")}</DialogTitle>
          </DialogHeader>
          <div className="space-y-3 py-2">
            <p className="text-sm text-muted-foreground">
              {t("reps.deleteConfirm")} <span className="font-medium text-foreground">{deletingRep?.name}</span>?
            </p>
            <p className="text-xs text-muted-foreground">
              {t("reps.deleteNote")}
            </p>
          </div>
          <DialogFooter>
            <Button
              variant="ghost"
              onClick={() => setDeleteDialogOpen(false)}
              disabled={deleting}
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

      {/* Reset Password Dialog */}
      <Dialog open={passwordDialogOpen} onOpenChange={setPasswordDialogOpen}>
        <DialogContent className="border-border bg-popover text-popover-foreground sm:max-w-md">
          <DialogHeader>
            <DialogTitle>{t("reps.resetPasswordFor")} {accountRepName}</DialogTitle>
          </DialogHeader>
          <div className="space-y-4 py-2">
            <div className="space-y-2">
              <Label htmlFor="new-password" className="text-muted-foreground">
                {t("drivers.newPassword")} *
              </Label>
              <Input
                id="new-password"
                type="password"
                placeholder={t("drivers.minChars")}
                value={newPassword}
                onChange={(e) => setNewPassword(e.target.value)}
                className="border-border bg-muted/50 text-foreground placeholder:text-muted-foreground/50"
              />
            </div>
          </div>
          <DialogFooter>
            <Button
              variant="ghost"
              onClick={() => setPasswordDialogOpen(false)}
              disabled={submitting}
            >
              {t("common.cancel")}
            </Button>
            <Button
              onClick={handleResetPassword}
              disabled={submitting}
              className="gap-1.5"
            >
              {submitting && <Loader2 className="h-4 w-4 animate-spin" />}
              {t("reps.resetPassword")}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
