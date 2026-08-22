"use client";

import { useEffect, useState, useCallback, useMemo, useRef } from "react";
import { useRouter } from "next/navigation";
import { Building2, Plus, Loader2, FileDown, FileUp, FileSpreadsheet, AlertTriangle, Trash2 } from "lucide-react";
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
import { Checkbox } from "@/components/ui/checkbox";
import api from "@/lib/api";
import { toast } from "sonner";
import { useT } from "@/lib/i18n";
import { usePermission } from "@/hooks/use-permission";
import { useSortable } from "@/hooks/use-sortable";
import { SortableHeader } from "@/components/sortable-header";
import { TableFilterBar } from "@/components/table-filter-bar";
import { localDateStr } from "@/lib/utils";
import { useColumnPreferences } from "@/hooks/useColumnPreferences";
import { ColumnVisibilityControl } from "@/components/ui/column-visibility-control";
import { type ColumnDef } from "@/components/ui/draggable-table-header";

const AGENTS_COL_DEFS: ColumnDef[] = [
  { key: "legalName", label: "Legal Name" },
  { key: "tradeName", label: "Trade Name" },
  { key: "taxId", label: "Tax ID" },
  { key: "city", label: "City" },
  { key: "country", label: "Country" },
  { key: "phone", label: "Phone" },
  { key: "currency", label: "Currency" },
  { key: "status", label: "Status" },
  { key: "actions", label: "Actions" },
];

interface Agent {
  id: string;
  legalName: string;
  tradeName: string;
  taxId: string;
  address: string;
  city: string;
  country: string;
  phone: string;
  email: string;
  disputeEmail: string;
  currency: string;
  refPattern: string | null;
  refExample: string | null;
  isActive: boolean;
  creditTerms?: { creditLimit: number; creditDays: number } | null;
}

interface AgentsResponse {
  data: Agent[];
  total: number;
  page: number;
  limit: number;
}

const CURRENCIES = ["EGP", "USD", "EUR", "GBP", "SAR"] as const;

const INITIAL_FORM = {
  legalName: "",
  tradeName: "",
  taxId: "",
  address: "",
  city: "",
  country: "",
  phone: "",
  email: "",
  disputeEmail: "",
  currency: "EGP",
  refPattern: "",
  refExample: "",
};

export default function AgentsPage() {
  const t = useT();
  const router = useRouter();

  // Permission checks
  const canAdd = usePermission("agents.addButton");
  const canEdit = usePermission("agents.table.editButton");
  const canDelete = usePermission("agents.table.deleteButton");
  const canToggleStatus = usePermission("agents.table.toggleStatus");
  const canLegalName = usePermission("agents.form.legalName");
  const canTradeName = usePermission("agents.form.tradeName");
  const canTaxId = usePermission("agents.form.taxId");
  const canContactInfo = usePermission("agents.form.contactInfo");
  const canCurrency = usePermission("agents.form.currency");
  const canRefPattern = usePermission("agents.form.refPattern");
  const canCreditLimit = usePermission("agents.form.creditLimit");
  const canCreditDays = usePermission("agents.form.creditDays");
  const [agents, setAgents] = useState<Agent[]>([]);
  const [loading, setLoading] = useState(true);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editDialogOpen, setEditDialogOpen] = useState(false);
  const [editingAgent, setEditingAgent] = useState<Agent | null>(null);
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
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [deleteTarget, setDeleteTarget] = useState<{ id: string; name: string } | null>(null);
  const [deleting, setDeleting] = useState(false);

  const filtered = useMemo(() => {
    if (!search.trim()) return agents;
    const q = search.toLowerCase();
    return agents.filter(
      (a) =>
        a.legalName.toLowerCase().includes(q) ||
        (a.tradeName && a.tradeName.toLowerCase().includes(q)) ||
        (a.city && a.city.toLowerCase().includes(q))
    );
  }, [agents, search]);

  const { sortedData, sortKey, sortDir, onSort } = useSortable<Agent>(filtered);
  const { visibility: agentColVis, saveVisibility: saveAgentColVis } = useColumnPreferences("agents", AGENTS_COL_DEFS.map((c) => c.key));
  const isVis = (key: string) => agentColVis[key] !== false;

  const [legalName, setLegalName] = useState(INITIAL_FORM.legalName);
  const [tradeName, setTradeName] = useState(INITIAL_FORM.tradeName);
  const [taxId, setTaxId] = useState(INITIAL_FORM.taxId);
  const [address, setAddress] = useState(INITIAL_FORM.address);
  const [city, setCity] = useState(INITIAL_FORM.city);
  const [country, setCountry] = useState(INITIAL_FORM.country);
  const [phone, setPhone] = useState(INITIAL_FORM.phone);
  const [email, setEmail] = useState(INITIAL_FORM.email);
  const [disputeEmail, setDisputeEmail] = useState(INITIAL_FORM.disputeEmail);
  const [currency, setCurrency] = useState(INITIAL_FORM.currency);
  const [refPattern, setRefPattern] = useState(INITIAL_FORM.refPattern);
  const [refExample, setRefExample] = useState(INITIAL_FORM.refExample);
  const [creditLimit, setCreditLimit] = useState<number>(0);
  const [creditDays, setCreditDays] = useState<number>(0);

  const fetchAgents = useCallback(async () => {
    try {
      setLoading(true);
      const res = await api.get<AgentsResponse>("/agents");
      setAgents(res.data.data);
    } catch {
      toast.error(t("agents.failedLoad"));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchAgents();
  }, [fetchAgents]);

  async function handleToggleStatus(id: string) {
    try {
      await api.patch(`/agents/${id}/status`);
      setAgents((prev) =>
        prev.map((a) => (a.id === id ? { ...a, isActive: !a.isActive } : a))
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
      setSelectedIds(new Set(sortedData.map((a) => a.id)));
    }
  }

  function openDeleteDialog(agent: Agent) {
    setDeleteTarget({ id: agent.id, name: agent.legalName });
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
        await api.delete(`/agents/${deleteTarget.id}`);
        toast.success(t("agents.deleted"));
      } else {
        await api.delete("/agents/bulk", { data: { ids: Array.from(selectedIds) } });
        toast.success(`${selectedIds.size} agents deleted`);
        setSelectedIds(new Set());
      }
      setDeleteDialogOpen(false);
      setDeleteTarget(null);
      fetchAgents();
    } catch {
      toast.error(t("agents.failedDelete"));
    } finally {
      setDeleting(false);
    }
  }

  function resetForm() {
    setLegalName(INITIAL_FORM.legalName);
    setTradeName(INITIAL_FORM.tradeName);
    setTaxId(INITIAL_FORM.taxId);
    setAddress(INITIAL_FORM.address);
    setCity(INITIAL_FORM.city);
    setCountry(INITIAL_FORM.country);
    setPhone(INITIAL_FORM.phone);
    setEmail(INITIAL_FORM.email);
    setDisputeEmail(INITIAL_FORM.disputeEmail);
    setCurrency(INITIAL_FORM.currency);
    setRefPattern(INITIAL_FORM.refPattern);
    setRefExample(INITIAL_FORM.refExample);
    setCreditLimit(0);
    setCreditDays(0);
  }

  function openDialog() {
    resetForm();
    setDialogOpen(true);
  }

  function openEditDialog(agent: Agent) {
    setEditingAgent(agent);
    setLegalName(agent.legalName);
    setTradeName(agent.tradeName || "");
    setTaxId(agent.taxId || "");
    setAddress(agent.address || "");
    setCity(agent.city || "");
    setCountry(agent.country || "");
    setPhone(agent.phone || "");
    setEmail(agent.email || "");
    setDisputeEmail(agent.disputeEmail || "");
    setCurrency(agent.currency || "EGP");
    setRefPattern(agent.refPattern || "");
    setRefExample(agent.refExample || "");
    setCreditLimit(agent.creditTerms ? Number(agent.creditTerms.creditLimit) : 0);
    setCreditDays(agent.creditTerms ? agent.creditTerms.creditDays : 0);
    setEditDialogOpen(true);
  }

  async function handleUpdate() {
    if (!editingAgent) return;
    if (!legalName.trim()) {
      toast.error(t("agents.legalNameRequired"));
      return;
    }

    try {
      setSubmitting(true);
      await Promise.all([
        api.put(`/agents/${editingAgent.id}`, {
          legalName: legalName.trim(),
          tradeName: tradeName.trim(),
          taxId: taxId.trim(),
          address: address.trim(),
          city: city.trim(),
          country: country.trim(),
          phone: phone.trim(),
          email: email.trim(),
          ...(disputeEmail.trim() ? { disputeEmail: disputeEmail.trim() } : { disputeEmail: null }),
          currency,
          ...(refPattern.trim() ? { refPattern: refPattern.trim() } : { refPattern: null }),
          ...(refExample.trim() ? { refExample: refExample.trim() } : { refExample: null }),
        }),
        api.put(`/agents/${editingAgent.id}/credit`, {
          creditLimit,
          creditDays,
        }),
      ]);
      toast.success(t("agents.updated"));
      setEditDialogOpen(false);
      setEditingAgent(null);
      resetForm();
      fetchAgents();
    } catch {
      toast.error(t("agents.failedUpdate"));
    } finally {
      setSubmitting(false);
    }
  }

  async function handleSubmit() {
    if (!legalName.trim()) {
      toast.error(t("agents.legalNameRequired"));
      return;
    }

    try {
      setSubmitting(true);
      await api.post("/agents", {
        legalName: legalName.trim(),
        tradeName: tradeName.trim(),
        taxId: taxId.trim(),
        address: address.trim(),
        city: city.trim(),
        country: country.trim(),
        phone: phone.trim(),
        email: email.trim(),
        ...(disputeEmail.trim() && { disputeEmail: disputeEmail.trim() }),
        currency,
        ...(refPattern.trim() && { refPattern: refPattern.trim() }),
        ...(refExample.trim() && { refExample: refExample.trim() }),
      });
      toast.success(t("agents.created"));
      setDialogOpen(false);
      resetForm();
      fetchAgents();
    } catch {
      toast.error(t("agents.failedCreate"));
    } finally {
      setSubmitting(false);
    }
  }

  async function handleExport() {
    setExporting(true);
    try {
      const res = await api.get("/agents/export/excel", {
        responseType: "blob",
      });
      const url = window.URL.createObjectURL(new Blob([res.data]));
      const link = document.createElement("a");
      link.href = url;
      const date = localDateStr(new Date());
      link.setAttribute("download", `agents_${date}.xlsx`);
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
      toast.success(t("agents.exportSuccess"));
    } catch {
      toast.error(t("agents.failedExport"));
    } finally {
      setExporting(false);
    }
  }

  async function handleDownloadTemplate() {
    try {
      const res = await api.get("/agents/import/template", {
        responseType: "blob",
      });
      const url = window.URL.createObjectURL(new Blob([res.data]));
      const link = document.createElement("a");
      link.href = url;
      link.setAttribute("download", "agents_import_template.xlsx");
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
    } catch {
      toast.error(t("agents.failedTemplate"));
    }
  }

  async function handleImportFile(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;

    setImporting(true);
    try {
      const formData = new FormData();
      formData.append("file", file);
      const res = await api.post("/agents/import/excel", formData, {
        headers: { "Content-Type": "multipart/form-data" },
      });
      const result = res.data.data;
      setImportResult({
        open: true,
        imported: result.imported,
        errors: result.errors,
      });
      if (result.imported > 0) {
        fetchAgents();
      }
    } catch (err: unknown) {
      const message =
        (err as { response?: { data?: { message?: string } } })?.response?.data
          ?.message || t("agents.failedImport");
      toast.error(message);
    } finally {
      setImporting(false);
      if (importFileRef.current) {
        importFileRef.current.value = "";
      }
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <PageHeader
          title={t("agents.title")}
          description={t("agents.description")}
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
          {canAdd && (
            <Button size="sm" className="gap-1.5" onClick={openDialog}>
              <Plus className="h-4 w-4" />
              {t("agents.addAgent")}
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
      ) : agents.length === 0 ? (
        <div className="flex flex-col items-center justify-center gap-4 py-20">
          <EmptyState
            icon={Building2}
            heading="No agents yet"
            description="Add your first agent to start booking jobs."
          />
          {canAdd && (
            <Button
              size="sm"
              className="gap-1.5 bg-primary text-primary-foreground hover:bg-primary/90"
              onClick={openDialog}
            >
              <Plus className="h-4 w-4" />
              {t("agents.addAgent")}
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
              {canDelete && (
                <Button
                  variant="destructive"
                  size="sm"
                  className="gap-1.5"
                  onClick={openBulkDeleteDialog}
                >
                  <Trash2 className="h-3.5 w-3.5" />
                  Delete Selected
                </Button>
              )}
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
          <div className="flex justify-end mb-2">
            <ColumnVisibilityControl columns={AGENTS_COL_DEFS} visibility={agentColVis} onSave={saveAgentColVis} />
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
                  {isVis("legalName") && <SortableHeader label={t("agents.legalName")} sortKey="legalName" currentKey={sortKey} currentDir={sortDir} onSort={onSort} />}
                  {isVis("tradeName") && <SortableHeader label={t("agents.tradeName")} sortKey="tradeName" currentKey={sortKey} currentDir={sortDir} onSort={onSort} />}
                  {isVis("taxId") && <TableHead className="text-muted-foreground text-xs">{t("agents.taxId")}</TableHead>}
                  {isVis("city") && <SortableHeader label={t("locations.city")} sortKey="city" currentKey={sortKey} currentDir={sortDir} onSort={onSort} />}
                  {isVis("country") && <SortableHeader label={t("locations.country")} sortKey="country" currentKey={sortKey} currentDir={sortDir} onSort={onSort} />}
                  {isVis("phone") && <SortableHeader label={t("agents.phone")} sortKey="phone" currentKey={sortKey} currentDir={sortDir} onSort={onSort} />}
                  {isVis("currency") && <TableHead className="text-muted-foreground text-xs">Currency</TableHead>}
                  {isVis("status") && <TableHead className="text-muted-foreground text-xs">{t("common.status")}</TableHead>}
                  {isVis("actions") && <TableHead className="text-muted-foreground text-xs">{t("common.actions")}</TableHead>}
                </TableRow>
              </TableHeader>
              <TableBody>
                {sortedData.map((agent, idx) => (
                <TableRow
                  key={agent.id}
                  className={`border-border cursor-pointer ${idx % 2 === 0 ? "bg-gray-100/25 dark:bg-gray-800/25" : "bg-gray-200/50 dark:bg-gray-700/50"}`}
                  onClick={() => router.push(`/dashboard/agents/${agent.id}`)}
                >
                  <TableCell onClick={(e) => e.stopPropagation()}>
                    <Checkbox
                      checked={selectedIds.has(agent.id)}
                      onCheckedChange={() => toggleSelect(agent.id)}
                    />
                  </TableCell>
                  {isVis("legalName") && <TableCell className="font-medium text-foreground">{agent.legalName}</TableCell>}
                  {isVis("tradeName") && <TableCell className="text-muted-foreground">{agent.tradeName || "-"}</TableCell>}
                  {isVis("taxId") && <TableCell className="text-muted-foreground">{agent.taxId || "-"}</TableCell>}
                  {isVis("city") && <TableCell className="text-muted-foreground">{agent.city || "-"}</TableCell>}
                  {isVis("country") && <TableCell className="text-muted-foreground">{agent.country || "-"}</TableCell>}
                  {isVis("phone") && <TableCell className="text-muted-foreground">{agent.phone || "-"}</TableCell>}
                  {isVis("currency") && <TableCell className="text-muted-foreground">{agent.currency}</TableCell>}
                  {isVis("status") && (
                    <TableCell>
                      {canToggleStatus ? (
                        <button onClick={(e) => { e.stopPropagation(); handleToggleStatus(agent.id); }} className="cursor-pointer">
                          {agent.isActive ? (
                            <Badge className="bg-emerald-500/20 text-emerald-600 dark:text-emerald-400 border-emerald-500/30 hover:bg-emerald-500/30 transition-colors">
                              {t("common.active")}
                            </Badge>
                          ) : (
                            <Badge className="bg-red-500/20 text-red-600 dark:text-red-400 border-red-500/30 hover:bg-red-500/30 transition-colors">
                              {t("common.inactive")}
                            </Badge>
                          )}
                        </button>
                      ) : (
                        agent.isActive ? (
                          <Badge className="bg-emerald-500/20 text-emerald-600 dark:text-emerald-400 border-emerald-500/30">
                            {t("common.active")}
                          </Badge>
                        ) : (
                          <Badge className="bg-red-500/20 text-red-600 dark:text-red-400 border-red-500/30">
                            {t("common.inactive")}
                          </Badge>
                        )
                      )}
                    </TableCell>
                  )}
                  {isVis("actions") && (
                    <TableCell>
                      <div className="flex items-center gap-1">
                        {canEdit && (
                          <Button
                            variant="ghost"
                            size="sm"
                            className="text-muted-foreground hover:text-foreground"
                            onClick={(e) => { e.stopPropagation(); openEditDialog(agent); }}
                          >
                            {t("common.edit")}
                          </Button>
                        )}
                        {canDelete && (
                          <Button
                            variant="ghost"
                            size="sm"
                            className="text-red-500/70 hover:text-red-500 hover:bg-red-500/10"
                            onClick={(e) => { e.stopPropagation(); openDeleteDialog(agent); }}
                          >
                            <Trash2 className="h-3.5 w-3.5" />
                          </Button>
                        )}
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

      {/* Add Agent Dialog */}
      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogContent className="max-h-[85vh] overflow-y-auto border-border bg-popover text-foreground sm:max-w-lg">
          <DialogHeader>
            <DialogTitle className="text-foreground">{t("agents.addAgent")}</DialogTitle>
          </DialogHeader>

          <div className="grid grid-cols-1 gap-4 py-2 sm:grid-cols-2">
            {canLegalName && (
              <div className="space-y-2">
                <Label htmlFor="legalName" className="text-muted-foreground">
                  {t("agents.legalName")} *
                </Label>
                <Input
                  id="legalName"
                  value={legalName}
                  onChange={(e) => setLegalName(e.target.value)}
                  placeholder="Full legal name"
                  className="border-border bg-card text-foreground placeholder:text-muted-foreground"
                />
              </div>
            )}

            {canTradeName && (
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

            {canTaxId && (
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

            {canContactInfo && (
              <>
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

                <div className="space-y-2">
                  <Label htmlFor="email" className="text-muted-foreground">
                    {t("common.email")}
                  </Label>
                  <Input
                    id="email"
                    type="email"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    placeholder="agent@example.com"
                    className="border-border bg-card text-foreground placeholder:text-muted-foreground"
                  />
                </div>

                <div className="space-y-2">
                  <Label htmlFor="disputeEmail" className="text-muted-foreground">
                    {t("agents.disputeEmail")}
                  </Label>
                  <Input
                    id="disputeEmail"
                    type="email"
                    value={disputeEmail}
                    onChange={(e) => setDisputeEmail(e.target.value)}
                    placeholder="disputes@example.com"
                    className="border-border bg-card text-foreground placeholder:text-muted-foreground"
                  />
                </div>

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
              </>
            )}

            {canCurrency && (
              <div className="space-y-2">
                <Label htmlFor="currency" className="text-muted-foreground">
                  Currency
                </Label>
                <Select value={currency} onValueChange={setCurrency}>
                  <SelectTrigger className="w-full border-border bg-card text-foreground">
                    <SelectValue placeholder="Select currency" />
                  </SelectTrigger>
                  <SelectContent className="border-border bg-popover">
                    {CURRENCIES.map((cur) => (
                      <SelectItem
                        key={cur}
                        value={cur}
                        className="text-foreground focus:bg-accent focus:text-accent-foreground"
                      >
                        {cur}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            )}

            {canRefPattern && (
              <>
                <div className="space-y-2">
                  <Label htmlFor="refPattern" className="text-muted-foreground">
                    {t("agents.refPattern")}
                  </Label>
                  <Input
                    id="refPattern"
                    value={refPattern}
                    onChange={(e) => setRefPattern(e.target.value)}
                    placeholder="e.g. ^INT-\d+$"
                    className="border-border bg-card text-foreground placeholder:text-muted-foreground font-mono text-sm"
                  />
                </div>

                <div className="space-y-2">
                  <Label htmlFor="refExample" className="text-muted-foreground">
                    {t("agents.refExample")}
                  </Label>
                  <Input
                    id="refExample"
                    value={refExample}
                    onChange={(e) => setRefExample(e.target.value)}
                    placeholder="e.g. INT-3550321"
                    className="border-border bg-card text-foreground placeholder:text-muted-foreground"
                  />
                </div>
              </>
            )}
          </div>

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
              {t("common.create")} {t("agents.title")}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Edit Agent Dialog */}
      <Dialog
        open={editDialogOpen}
        onOpenChange={(open) => {
          setEditDialogOpen(open);
          if (!open) setEditingAgent(null);
        }}
      >
        <DialogContent className="max-h-[85vh] overflow-y-auto border-border bg-popover text-foreground sm:max-w-lg">
          <DialogHeader>
            <DialogTitle className="text-foreground">{t("agents.editAgent")}</DialogTitle>
          </DialogHeader>

          <div className="grid grid-cols-1 gap-4 py-2 sm:grid-cols-2">
            {canLegalName && (
              <div className="space-y-2">
                <Label htmlFor="edit-legalName" className="text-muted-foreground">
                  {t("agents.legalName")} *
                </Label>
                <Input
                  id="edit-legalName"
                  value={legalName}
                  onChange={(e) => setLegalName(e.target.value)}
                  placeholder="Full legal name"
                  className="border-border bg-card text-foreground placeholder:text-muted-foreground"
                />
              </div>
            )}

            {canTradeName && (
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

            {canTaxId && (
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

            {canContactInfo && (
              <>
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

                <div className="space-y-2">
                  <Label htmlFor="edit-email" className="text-muted-foreground">
                    {t("common.email")}
                  </Label>
                  <Input
                    id="edit-email"
                    type="email"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    placeholder="agent@example.com"
                    className="border-border bg-card text-foreground placeholder:text-muted-foreground"
                  />
                </div>

                <div className="space-y-2">
                  <Label htmlFor="edit-disputeEmail" className="text-muted-foreground">
                    {t("agents.disputeEmail")}
                  </Label>
                  <Input
                    id="edit-disputeEmail"
                    type="email"
                    value={disputeEmail}
                    onChange={(e) => setDisputeEmail(e.target.value)}
                    placeholder="disputes@example.com"
                    className="border-border bg-card text-foreground placeholder:text-muted-foreground"
                  />
                </div>

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
              </>
            )}

            {canCurrency && (
              <div className="space-y-2">
                <Label htmlFor="edit-currency" className="text-muted-foreground">
                  Currency
                </Label>
                <Select value={currency} onValueChange={setCurrency}>
                  <SelectTrigger className="w-full border-border bg-card text-foreground">
                    <SelectValue placeholder="Select currency" />
                  </SelectTrigger>
                  <SelectContent className="border-border bg-popover">
                    {CURRENCIES.map((cur) => (
                      <SelectItem
                        key={cur}
                        value={cur}
                        className="text-foreground focus:bg-accent focus:text-accent-foreground"
                      >
                        {cur}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            )}

            {canRefPattern && (
              <>
                <div className="space-y-2">
                  <Label htmlFor="edit-refPattern" className="text-muted-foreground">
                    {t("agents.refPattern")}
                  </Label>
                  <Input
                    id="edit-refPattern"
                    value={refPattern}
                    onChange={(e) => setRefPattern(e.target.value)}
                    placeholder="e.g. ^INT-\d+$"
                    className="border-border bg-card text-foreground placeholder:text-muted-foreground font-mono text-sm"
                  />
                </div>

                <div className="space-y-2">
                  <Label htmlFor="edit-refExample" className="text-muted-foreground">
                    {t("agents.refExample")}
                  </Label>
                  <Input
                    id="edit-refExample"
                    value={refExample}
                    onChange={(e) => setRefExample(e.target.value)}
                    placeholder="e.g. INT-3550321"
                    className="border-border bg-card text-foreground placeholder:text-muted-foreground"
                  />
                </div>
              </>
            )}

            {(canCreditLimit || canCreditDays) && (
              <div className="col-span-2 border-t border-border pt-3 mt-1">
                <p className="text-sm font-medium text-foreground mb-3">{t("finance.creditStatus")}</p>
                <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                  {canCreditLimit && (
                    <div className="space-y-2">
                      <Label htmlFor="edit-creditLimit" className="text-muted-foreground">
                        {t("agents.creditLimit")}
                      </Label>
                      <Input
                        id="edit-creditLimit"
                        type="number"
                        min={0}
                        value={creditLimit}
                        onChange={(e) => setCreditLimit(Number(e.target.value) || 0)}
                        placeholder="0"
                        className="border-border bg-card text-foreground placeholder:text-muted-foreground"
                      />
                    </div>
                  )}
                  {canCreditDays && (
                    <div className="space-y-2">
                      <Label htmlFor="edit-creditDays" className="text-muted-foreground">
                        {t("agents.creditDays")}
                      </Label>
                      <Input
                        id="edit-creditDays"
                        type="number"
                        min={0}
                        value={creditDays}
                        onChange={(e) => setCreditDays(Number(e.target.value) || 0)}
                        placeholder="0"
                        className="border-border bg-card text-foreground placeholder:text-muted-foreground"
                      />
                    </div>
                  )}
                </div>
              </div>
            )}
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
              {deleteTarget ? "Delete Agent" : "Delete Selected Agents"}
            </DialogTitle>
          </DialogHeader>
          <div className="py-4">
            {deleteTarget ? (
              <p className="text-sm text-muted-foreground">
                Are you sure you want to delete <span className="font-medium text-foreground">{deleteTarget.name}</span>? This action cannot be undone.
              </p>
            ) : (
              <p className="text-sm text-muted-foreground">
                Are you sure you want to delete <span className="font-medium text-foreground">{selectedIds.size} agents</span>? This action cannot be undone.
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
        <DialogContent className="border-border bg-popover text-foreground max-w-lg">
          <DialogHeader>
            <DialogTitle>{t("agents.importResults")}</DialogTitle>
          </DialogHeader>
          <div className="space-y-4 py-2">
            <div className="flex items-center gap-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-full bg-emerald-500/15">
                <FileSpreadsheet className="h-5 w-5 text-emerald-500" />
              </div>
              <div>
                <p className="text-sm font-medium text-foreground">
                  {importResult.imported} {t("agents.imported")}
                </p>
                {importResult.errors.length > 0 && (
                  <p className="text-xs text-muted-foreground">
                    {importResult.errors.length} {t("agents.errors")}
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
