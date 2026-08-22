"use client";

import { useEffect, useRef, useState } from "react";
import { toast } from "sonner";
import { PageHeader } from "@/components/page-header";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import { Textarea } from "@/components/ui/textarea";
import { Badge } from "@/components/ui/badge";
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
import api from "@/lib/api";
import { useT } from "@/lib/i18n";
import { usePermission } from "@/hooks/use-permission";
import {
  Loader2,
  Send,
  Upload,
  Paperclip,
  X,
  ChevronDown,
  ChevronUp,
  Clock,
  Zap,
  Bell,
} from "lucide-react";

const TEMPLATE_VARIABLES = [
  "clientName",
  "serviceDate",
  "pickupTime",
  "origin",
  "destination",
  "serviceType",
  "internalRef",
  "agentRef",
  "repName",
  "repNumber",
  "driverName",
  "driverNumber",
  "paxCount",
  "clientSign",
];

const SAMPLE_DATA: Record<string, string> = {
  clientName: "John Smith",
  serviceDate: "2025-03-15",
  pickupTime: "08:30 AM",
  origin: "Cairo Airport T2",
  destination: "Four Seasons Hotel",
  serviceType: "Arrival",
  internalRef: "TJ-2025-0042",
  agentRef: "AGT-7890",
  repName: "Ahmed Hassan",
  repNumber: "+201012345678",
  driverName: "Mohamed Ali",
  driverNumber: "+201098765432",
  paxCount: "3",
  clientSign: "(attached below)",
};

interface WhatsappTemplate {
  id: string;
  name: string;
  triggerType: "JOB_CREATED" | "DRIVER_ASSIGNED" | "SCHEDULED";
  isEnabled: boolean;
  templateBody: string;
  daysBefore: number | null;
  sendHour: number | null;
  sendMinute: number | null;
}

interface LogEntry {
  id: string;
  trafficJobId: string;
  recipientPhone: string;
  messageSid: string | null;
  status: "SENT" | "FAILED";
  errorMessage: string | null;
  sentAt: string;
  templateName: string | null;
  trafficJob: { internalRef: string };
}

const TRIGGER_ICONS: Record<string, React.ReactNode> = {
  JOB_CREATED: <Zap className="h-4 w-4" />,
  DRIVER_ASSIGNED: <Bell className="h-4 w-4" />,
  SCHEDULED: <Clock className="h-4 w-4" />,
};

const TRIGGER_COLORS: Record<string, string> = {
  JOB_CREATED: "bg-blue-500/10 text-blue-400 border-blue-500/20",
  DRIVER_ASSIGNED: "bg-purple-500/10 text-purple-400 border-purple-500/20",
  SCHEDULED: "bg-amber-500/10 text-amber-400 border-amber-500/20",
};

function renderPreview(body: string): string {
  let preview = body;
  for (const key of TEMPLATE_VARIABLES) {
    preview = preview.replace(
      new RegExp(`\\{\\{${key}\\}\\}`, "g"),
      SAMPLE_DATA[key] ?? key
    );
  }
  return preview;
}

interface TemplateCardProps {
  template: WhatsappTemplate;
  onSave: (id: string, patch: Partial<WhatsappTemplate>) => Promise<void>;
}

function TemplateCard({ template, onSave }: TemplateCardProps) {
  const t = useT();
  const [expanded, setExpanded] = useState(false);
  const [saving, setSaving] = useState(false);
  const [local, setLocal] = useState<WhatsappTemplate>({ ...template });

  // keep in sync if parent refetches
  useEffect(() => {
    setLocal({ ...template });
  }, [template]);

  async function handleToggleEnabled(val: boolean) {
    setLocal((p) => ({ ...p, isEnabled: val }));
    setSaving(true);
    try {
      await onSave(template.id, { isEnabled: val });
    } finally {
      setSaving(false);
    }
  }

  async function handleSave() {
    setSaving(true);
    try {
      await onSave(template.id, {
        name: local.name,
        templateBody: local.templateBody,
        daysBefore: local.daysBefore,
        sendHour: local.sendHour,
        sendMinute: local.sendMinute,
      });
      setExpanded(false);
    } finally {
      setSaving(false);
    }
  }

  const triggerKey = `whatsapp.trigger.${template.triggerType}` as Parameters<typeof t>[0];

  return (
    <Card className="border-border bg-card overflow-hidden">
      {/* Header row */}
      <div className="flex items-center gap-4 px-5 py-4">
        <div
          className={`flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-xs font-medium ${TRIGGER_COLORS[template.triggerType]}`}
        >
          {TRIGGER_ICONS[template.triggerType]}
          {t(triggerKey)}
        </div>
        <span className="flex-1 font-medium text-foreground truncate">
          {local.name}
        </span>
        <div className="flex items-center gap-3">
          {saving && <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />}
          <Switch
            checked={local.isEnabled}
            onCheckedChange={handleToggleEnabled}
            disabled={saving}
          />
          <button
            onClick={() => setExpanded((v) => !v)}
            className="rounded p-1 text-muted-foreground hover:text-foreground transition-colors"
          >
            {expanded ? (
              <ChevronUp className="h-4 w-4" />
            ) : (
              <ChevronDown className="h-4 w-4" />
            )}
          </button>
        </div>
      </div>

      {/* Expanded body */}
      {expanded && (
        <div className="border-t border-border px-5 py-4 space-y-4">
          {/* Template name */}
          <div>
            <Label className="text-foreground/70">{t("whatsapp.templateName")}</Label>
            <Input
              value={local.name}
              onChange={(e) => setLocal((p) => ({ ...p, name: e.target.value }))}
              className="border-border bg-muted/50 text-foreground mt-1"
            />
          </div>

          {/* Template body */}
          <div>
            <Label className="text-foreground/70">{t("whatsapp.templateBody")}</Label>
            <Textarea
              value={local.templateBody}
              onChange={(e) =>
                setLocal((p) => ({ ...p, templateBody: e.target.value }))
              }
              rows={4}
              className="border-border bg-muted/50 text-foreground mt-1"
            />
            <div className="mt-2 flex flex-wrap gap-1.5">
              {TEMPLATE_VARIABLES.map((v) => (
                <Badge
                  key={v}
                  variant="secondary"
                  className="cursor-pointer text-xs"
                  onClick={() =>
                    setLocal((p) => ({
                      ...p,
                      templateBody: p.templateBody + `{{${v}}}`,
                    }))
                  }
                >
                  {`{{${v}}}`}
                </Badge>
              ))}
            </div>
          </div>

          {/* Live preview */}
          <div>
            <Label className="text-foreground/70">{t("whatsapp.livePreview")}</Label>
            <div className="mt-1 rounded-lg border border-border bg-muted/30 p-3 text-sm text-foreground/80 whitespace-pre-wrap">
              {renderPreview(local.templateBody)}
            </div>
          </div>

          {/* Scheduled-only timing config */}
          {template.triggerType === "SCHEDULED" && (
            <div>
              <p className="mb-3 text-sm font-medium text-foreground/70">
                {t("whatsapp.scheduledConfig")}
              </p>
              <div className="grid gap-4 sm:grid-cols-3">
                <div>
                  <Label className="text-foreground/70">{t("whatsapp.daysBefore")}</Label>
                  <Input
                    type="number"
                    min={0}
                    max={30}
                    value={local.daysBefore ?? 1}
                    onChange={(e) =>
                      setLocal((p) => ({
                        ...p,
                        daysBefore: parseInt(e.target.value, 10) || 0,
                      }))
                    }
                    className="border-border bg-muted/50 text-foreground mt-1"
                  />
                </div>
                <div>
                  <Label className="text-foreground/70">{t("whatsapp.sendHourLabel")}</Label>
                  <Select
                    value={String(local.sendHour ?? 9)}
                    onValueChange={(v) =>
                      setLocal((p) => ({ ...p, sendHour: parseInt(v, 10) }))
                    }
                  >
                    <SelectTrigger className="border-border bg-muted/50 text-foreground mt-1">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      {Array.from({ length: 24 }, (_, i) => (
                        <SelectItem key={i} value={String(i)}>
                          {String(i).padStart(2, "0")}:xx
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
                <div>
                  <Label className="text-foreground/70">{t("whatsapp.sendMinuteLabel")}</Label>
                  <Select
                    value={String(local.sendMinute ?? 0)}
                    onValueChange={(v) =>
                      setLocal((p) => ({ ...p, sendMinute: parseInt(v, 10) }))
                    }
                  >
                    <SelectTrigger className="border-border bg-muted/50 text-foreground mt-1">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      {[0, 5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 55].map((m) => (
                        <SelectItem key={m} value={String(m)}>
                          :{String(m).padStart(2, "0")}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
              </div>
            </div>
          )}

          <div className="flex justify-end gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() => {
                setLocal({ ...template });
                setExpanded(false);
              }}
            >
              {t("common.cancel")}
            </Button>
            <Button size="sm" disabled={saving} onClick={handleSave}>
              {saving && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
              {t("common.saveChanges")}
            </Button>
          </div>
        </div>
      )}
    </Card>
  );
}

export default function WhatsAppPage() {
  const t = useT();
  const canEditSettings = usePermission("whatsapp.settings.editSettings");
  const canTestSend = usePermission("whatsapp.testSend");
  const canUploadMedia = usePermission("whatsapp.uploadMedia");
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [testSending, setTestSending] = useState(false);
  const [uploading, setUploading] = useState(false);

  // Twilio settings
  const [isEnabled, setIsEnabled] = useState(false);
  const [twilioAccountSid, setTwilioAccountSid] = useState("");
  const [twilioAuthToken, setTwilioAuthToken] = useState("");
  const [whatsappFrom, setWhatsappFrom] = useState("");
  const [mediaUrl, setMediaUrl] = useState("");

  // Templates
  const [templates, setTemplates] = useState<WhatsappTemplate[]>([]);

  // Test
  const [testPhone, setTestPhone] = useState("");

  // Logs
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [logsTotal, setLogsTotal] = useState(0);

  useEffect(() => {
    loadAll();
  }, []);

  async function loadAll() {
    try {
      const [settingsRes, templatesRes, logsRes] = await Promise.all([
        api.get("/whatsapp-notifications/settings"),
        api.get("/whatsapp-notifications/templates"),
        api.get("/whatsapp-notifications/logs?limit=20"),
      ]);
      const s = settingsRes.data;
      setIsEnabled(s.isEnabled ?? false);
      setTwilioAccountSid(s.twilioAccountSid ?? "");
      setTwilioAuthToken(s.twilioAuthToken ?? "");
      setWhatsappFrom(s.whatsappFrom ?? "");
      setMediaUrl(s.mediaUrl ?? "");
      setTemplates(templatesRes.data ?? []);
      setLogs(logsRes.data.logs ?? []);
      setLogsTotal(logsRes.data.total ?? 0);
    } catch {
      // defaults fine
    } finally {
      setLoading(false);
    }
  }

  async function handleSaveSettings() {
    setSubmitting(true);
    try {
      const { data } = await api.patch("/whatsapp-notifications/settings", {
        isEnabled,
        twilioAccountSid,
        ...(twilioAuthToken && !twilioAuthToken.startsWith("****")
          ? { twilioAuthToken }
          : {}),
        whatsappFrom,
        mediaUrl: mediaUrl || null,
      });
      setTwilioAuthToken(data.twilioAuthToken ?? "");
      setMediaUrl(data.mediaUrl ?? "");
      toast.success(t("whatsapp.settingsSaved"));
    } catch {
      toast.error(t("whatsapp.failedSave"));
    } finally {
      setSubmitting(false);
    }
  }

  async function handleSaveTemplate(
    id: string,
    patch: Partial<WhatsappTemplate>
  ) {
    try {
      const { data } = await api.patch(
        `/whatsapp-notifications/templates/${id}`,
        patch
      );
      setTemplates((prev) =>
        prev.map((tpl) => (tpl.id === id ? { ...tpl, ...data } : tpl))
      );
      toast.success(t("whatsapp.templateSaved"));
    } catch {
      toast.error(t("whatsapp.templateSaveFailed"));
      throw new Error("save failed");
    }
  }

  async function handleTestSend() {
    if (!testPhone.trim()) return;
    setTestSending(true);
    try {
      await api.post("/whatsapp-notifications/test", { phone: testPhone });
      toast.success(t("whatsapp.testSent"));
      loadAll();
    } catch {
      toast.error(t("whatsapp.testFailed"));
    } finally {
      setTestSending(false);
    }
  }

  async function handleFileUpload(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;
    setUploading(true);
    try {
      const formData = new FormData();
      formData.append("file", file);
      const { data } = await api.post(
        "/whatsapp-notifications/upload-media",
        formData,
        { headers: { "Content-Type": "multipart/form-data" } }
      );
      setMediaUrl(data.url);
      toast.success(t("whatsapp.fileUploaded"));
    } catch {
      toast.error(t("whatsapp.fileUploadFailed"));
    } finally {
      setUploading(false);
      if (fileInputRef.current) fileInputRef.current.value = "";
    }
  }

  if (loading) {
    return (
      <div className="flex h-64 items-center justify-center">
        <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <PageHeader
        title={t("whatsapp.title")}
        description={t("whatsapp.description")}
      />

      {/* Card 1 — Twilio Configuration */}
      <Card className="border-border bg-card p-6">
        <h2 className="mb-4 text-lg font-semibold text-foreground">
          {t("whatsapp.twilioConfig")}
        </h2>
        <div className="space-y-4">
          <div className="flex items-center gap-3">
            <Switch
              checked={isEnabled}
              onCheckedChange={setIsEnabled}
              id="wa-enabled"
              disabled={!canEditSettings}
            />
            <Label htmlFor="wa-enabled" className="text-foreground/70">
              {t("whatsapp.enableNotifications")}
            </Label>
          </div>

          <div className="grid gap-4 sm:grid-cols-2">
            <div>
              <Label className="text-foreground/70">{t("whatsapp.accountSid")}</Label>
              <Input
                value={twilioAccountSid}
                onChange={(e) => setTwilioAccountSid(e.target.value)}
                placeholder="ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
                className="border-border bg-muted/50 text-foreground mt-1"
              />
            </div>
            <div>
              <Label className="text-foreground/70">{t("whatsapp.authToken")}</Label>
              <Input
                type="password"
                value={twilioAuthToken}
                onChange={(e) => setTwilioAuthToken(e.target.value)}
                placeholder="••••••••"
                className="border-border bg-muted/50 text-foreground mt-1"
              />
            </div>
          </div>

          <div>
            <Label className="text-foreground/70">{t("whatsapp.fromNumber")}</Label>
            <Input
              value={whatsappFrom}
              onChange={(e) => setWhatsappFrom(e.target.value)}
              placeholder="+14155238886"
              className="border-border bg-muted/50 text-foreground mt-1 max-w-xs"
            />
          </div>
        </div>
      </Card>

      {/* Card 2 — File Attachment */}
      <Card className="border-border bg-card p-6">
        <h2 className="mb-1 text-lg font-semibold text-foreground">
          {t("whatsapp.fileAttachment")}
        </h2>
        <p className="mb-4 text-sm text-muted-foreground">
          {t("whatsapp.fileAttachmentDesc")}
        </p>
        <div className="space-y-3">
          <div className="flex items-end gap-3">
            <div className="flex-1">
              <Label className="text-foreground/70">{t("whatsapp.mediaUrl")}</Label>
              <Input
                value={mediaUrl}
                onChange={(e) => setMediaUrl(e.target.value)}
                placeholder="https://example.com/file.pdf"
                className="border-border bg-muted/50 text-foreground mt-1"
              />
            </div>
            <input
              ref={fileInputRef}
              type="file"
              className="hidden"
              accept="image/*,.pdf,.doc,.docx"
              onChange={handleFileUpload}
            />
            {canUploadMedia && (
              <Button
                variant="outline"
                size="sm"
                className="gap-1.5 shrink-0"
                disabled={uploading}
                onClick={() => fileInputRef.current?.click()}
              >
                {uploading ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <Upload className="h-4 w-4" />
                )}
                {t("whatsapp.uploadFile")}
              </Button>
            )}
          </div>
          {mediaUrl && (
            <div className="flex items-center gap-2 rounded-md border border-border bg-muted/30 px-3 py-2 text-sm">
              <Paperclip className="h-4 w-4 shrink-0 text-muted-foreground" />
              <span className="flex-1 truncate text-foreground/80">{mediaUrl}</span>
              <button
                onClick={() => setMediaUrl("")}
                className="shrink-0 rounded p-0.5 text-muted-foreground hover:text-foreground"
              >
                <X className="h-3.5 w-3.5" />
              </button>
            </div>
          )}
        </div>
      </Card>

      {/* Save settings button */}
      {canEditSettings && (
        <div className="flex justify-end">
          <Button onClick={handleSaveSettings} disabled={submitting}>
            {submitting && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
            {t("common.saveChanges")}
          </Button>
        </div>
      )}

      {/* Section — Message Templates */}
      <div>
        <h2 className="mb-1 text-lg font-semibold text-foreground">
          {t("whatsapp.templates")}
        </h2>
        <p className="mb-4 text-sm text-muted-foreground">
          {t("whatsapp.templatesDesc")}
        </p>
        <div className="space-y-3">
          {templates.map((tpl) => (
            <TemplateCard
              key={tpl.id}
              template={tpl}
              onSave={handleSaveTemplate}
            />
          ))}
        </div>
      </div>

      {/* Test Message */}
      <Card className="border-border bg-card p-6">
        <h2 className="mb-4 text-lg font-semibold text-foreground">
          {t("whatsapp.testMessage")}
        </h2>
        <div className="flex items-end gap-3">
          <div className="flex-1">
            <Label className="text-foreground/70">{t("whatsapp.recipientPhone")}</Label>
            <Input
              value={testPhone}
              onChange={(e) => setTestPhone(e.target.value)}
              placeholder="+201234567890"
              className="border-border bg-muted/50 text-foreground mt-1"
            />
          </div>
          {canTestSend && (
            <Button
              onClick={handleTestSend}
              disabled={testSending || !testPhone.trim()}
              size="sm"
              className="gap-1.5 shrink-0"
            >
              {testSending ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <Send className="h-4 w-4" />
              )}
              {t("whatsapp.sendTest")}
            </Button>
          )}
        </div>
      </Card>

      {/* Recent Logs */}
      <Card className="border-border bg-card p-6">
        <h2 className="mb-4 text-lg font-semibold text-foreground">
          {t("whatsapp.recentLogs")}{" "}
          <span className="text-sm font-normal text-muted-foreground">
            ({logsTotal})
          </span>
        </h2>
        {logs.length === 0 ? (
          <p className="text-sm text-muted-foreground">{t("whatsapp.noLogs")}</p>
        ) : (
          <div className="overflow-x-auto [overflow-y:clip]">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>{t("whatsapp.jobRef")}</TableHead>
                  <TableHead>{t("whatsapp.recipient")}</TableHead>
                  <TableHead>{t("whatsapp.templateLog")}</TableHead>
                  <TableHead>{t("common.status")}</TableHead>
                  <TableHead>{t("whatsapp.sentAt")}</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {logs.map((log) => (
                  <TableRow key={log.id}>
                    <TableCell className="font-mono text-xs">
                      {log.trafficJob?.internalRef ?? "—"}
                    </TableCell>
                    <TableCell className="text-xs">{log.recipientPhone}</TableCell>
                    <TableCell className="text-xs text-muted-foreground">
                      {log.templateName ?? "—"}
                    </TableCell>
                    <TableCell>
                      <Badge
                        variant={log.status === "SENT" ? "default" : "destructive"}
                        className="text-xs"
                      >
                        {log.status}
                      </Badge>
                    </TableCell>
                    <TableCell className="text-xs text-muted-foreground">
                      {new Date(log.sentAt).toLocaleString()}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        )}
      </Card>
    </div>
  );
}
