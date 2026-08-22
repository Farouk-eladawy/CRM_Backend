"use client";

import { useEffect, useState, useRef, useCallback } from "react";
import { Upload, Trash2, Loader2, FileText, FileSpreadsheet, Image } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "@/components/ui/dialog";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import api from "@/lib/api";
import { toast } from "sonner";
import { useT } from "@/lib/i18n";
import { usePermission } from "@/hooks/use-permission";
import { SELECTABLE_SERVICE_TYPES, serviceTypeDropdownLabel, useServiceTypeLabel } from "@/lib/service-types";

interface ImportTemplate {
  id: string;
  serviceType: string;
  fileType: string;
  fileName: string;
  notes: string | null;
  createdAt: string;
}

const SERVICE_TYPES = SELECTABLE_SERVICE_TYPES;

const FILE_TYPE_ICON: Record<string, React.ReactNode> = {
  PDF: <FileText className="h-4 w-4 text-red-500" />,
  XLSX: <FileSpreadsheet className="h-4 w-4 text-green-600" />,
  IMAGE: <Image className="h-4 w-4 text-blue-500" />,
};

interface ImportTemplateManagerProps {
  customerId: string;
}

export function ImportTemplateManager({ customerId }: ImportTemplateManagerProps) {
  const serviceTypeLabel = useServiceTypeLabel();
  const t = useT();
  const canUpload = usePermission("customers.detail.importTemplates.upload");
  const canDeleteTemplate = usePermission("customers.detail.importTemplates.delete");
  const [templates, setTemplates] = useState<ImportTemplate[]>([]);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [selectedServiceType, setSelectedServiceType] = useState("");
  const [notes, setNotes] = useState("");
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);

  const fetchTemplates = useCallback(async () => {
    try {
      const res = await api.get(`/customers/${customerId}/import-templates`);
      setTemplates(res.data.data || []);
    } catch {
      toast.error("Failed to load import templates");
    } finally {
      setLoading(false);
    }
  }, [customerId]);

  useEffect(() => {
    fetchTemplates();
  }, [fetchTemplates]);

  async function handleUpload() {
    if (!selectedFile || !selectedServiceType) return;

    setUploading(true);
    try {
      const formData = new FormData();
      formData.append("file", selectedFile);
      formData.append("serviceType", selectedServiceType);
      if (notes.trim()) formData.append("notes", notes.trim());

      await api.post(`/customers/${customerId}/import-templates`, formData, {
        headers: { "Content-Type": "multipart/form-data" },
      });

      toast.success(t("importTemplates.uploadSuccess") || "Template uploaded successfully");
      setDialogOpen(false);
      setSelectedFile(null);
      setSelectedServiceType("");
      setNotes("");
      fetchTemplates();
    } catch {
      toast.error("Failed to upload template");
    } finally {
      setUploading(false);
    }
  }

  async function handleDelete(templateId: string) {
    if (!confirm(t("importTemplates.confirmDelete") || "Are you sure you want to delete this template?")) return;

    try {
      await api.delete(`/customers/${customerId}/import-templates/${templateId}`);
      toast.success(t("importTemplates.deleteSuccess") || "Template deleted");
      fetchTemplates();
    } catch {
      toast.error("Failed to delete template");
    }
  }

  // Service types already used by this customer
  const usedServiceTypes = templates.map((t) => t.serviceType);

  return (
    <Card className="border-border bg-card">
      <CardHeader className="flex flex-row items-center justify-between">
        <CardTitle className="text-foreground">
          {t("importTemplates.title") || "Import Templates"}
        </CardTitle>
        {canUpload && (
          <Button
            variant="outline"
            size="sm"
            className="gap-1.5 border-border"
            onClick={() => setDialogOpen(true)}
          >
            <Upload className="h-4 w-4" />
            {t("importTemplates.upload") || "Upload Template"}
          </Button>
        )}
      </CardHeader>
      <CardContent>
        {loading ? (
          <div className="flex items-center justify-center py-12">
            <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
          </div>
        ) : templates.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-12 text-muted-foreground">
            <FileText className="h-10 w-10 mb-2 opacity-40" />
            <p className="text-sm">
              {t("importTemplates.noTemplates") ||
                "No import templates configured. Upload a sample file for each service type to improve AI extraction accuracy."}
            </p>
          </div>
        ) : (
          <div className="rounded-md border border-border overflow-hidden">
            <Table>
              <TableHeader>
                <TableRow className="bg-muted">
                  <TableHead className="text-gray-200">{t("importTemplates.serviceType") || "Service Type"}</TableHead>
                  <TableHead className="text-gray-200">{t("importTemplates.fileType") || "File Type"}</TableHead>
                  <TableHead className="text-gray-200">{t("importTemplates.fileName") || "File Name"}</TableHead>
                  <TableHead className="text-gray-200">{t("importTemplates.uploaded") || "Uploaded"}</TableHead>
                  <TableHead className="text-gray-200 w-20"></TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {templates.map((tmpl) => (
                  <TableRow key={tmpl.id} className="border-border">
                    <TableCell>
                      <Badge variant="outline" className="text-xs">
                        {serviceTypeLabel(tmpl.serviceType)}
                      </Badge>
                    </TableCell>
                    <TableCell>
                      <span className="flex items-center gap-1.5">
                        {FILE_TYPE_ICON[tmpl.fileType] || null}
                        {tmpl.fileType}
                      </span>
                    </TableCell>
                    <TableCell className="max-w-[200px] truncate text-sm text-muted-foreground">
                      {tmpl.fileName}
                    </TableCell>
                    <TableCell className="text-sm text-muted-foreground">
                      {new Date(tmpl.createdAt).toLocaleDateString()}
                    </TableCell>
                    <TableCell>
                      {canDeleteTemplate && (
                        <Button
                          variant="ghost"
                          size="icon"
                          className="h-8 w-8 text-red-500 hover:text-red-600 hover:bg-red-500/10"
                          onClick={() => handleDelete(tmpl.id)}
                        >
                          <Trash2 className="h-4 w-4" />
                        </Button>
                      )}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        )}
      </CardContent>

      {/* Upload Dialog */}
      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogContent className="sm:max-w-md border-border bg-card text-foreground">
          <DialogHeader>
            <DialogTitle>{t("importTemplates.upload") || "Upload Template"}</DialogTitle>
          </DialogHeader>
          <div className="space-y-4 py-2">
            <div className="space-y-2">
              <Label>{t("importTemplates.serviceType") || "Service Type"}</Label>
              <Select value={selectedServiceType} onValueChange={setSelectedServiceType}>
                <SelectTrigger className="border-border bg-card text-foreground">
                  <SelectValue placeholder="Select service type" />
                </SelectTrigger>
                <SelectContent className="border-border bg-popover text-foreground">
                  {SERVICE_TYPES.map((st) => (
                    <SelectItem key={st} value={st}>
                      {serviceTypeDropdownLabel(st)}
                      {usedServiceTypes.includes(st) && " (will replace existing)"}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-2">
              <Label>File</Label>
              <Input
                ref={fileInputRef}
                type="file"
                accept=".pdf,.xlsx,.xls,.png,.jpg,.jpeg"
                onChange={(e) => setSelectedFile(e.target.files?.[0] || null)}
                className="border-border bg-card text-foreground"
              />
              <p className="text-xs text-muted-foreground">
                Accepted: PDF, Excel (.xlsx, .xls), Images (.png, .jpg). Max 10MB.
              </p>
            </div>

            <div className="space-y-2">
              <Label>Notes (optional)</Label>
              <Input
                value={notes}
                onChange={(e) => setNotes(e.target.value)}
                placeholder="E.g., Columns: Date, Guest, Hotel, Flight"
                className="border-border bg-card text-foreground placeholder:text-muted-foreground"
              />
            </div>
          </div>
          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => setDialogOpen(false)}
              className="border-border"
            >
              Cancel
            </Button>
            <Button
              onClick={handleUpload}
              disabled={!selectedFile || !selectedServiceType || uploading}
              className="gap-1.5"
            >
              {uploading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Upload className="h-4 w-4" />}
              Upload
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </Card>
  );
}
