"use client";

import { useEffect, useState } from "react";
import { toast } from "sonner";
import { Mail, Loader2, Send, AlertTriangle } from "lucide-react";
import { PageHeader } from "@/components/page-header";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import { Textarea } from "@/components/ui/textarea";
import api from "@/lib/api";
import { useT } from "@/lib/i18n";

interface EmailSettingsData {
  smtpHost: string;
  smtpPort: number;
  smtpSecure: boolean;
  smtpUser: string;
  smtpPass: string;
  fromAddress: string;
  notifyDispatchEmail: string;
  notifyTrafficEmail: string;
  disputeTo: string;
  disputeCc1: string;
  disputeCc2: string;
  disputeCc3: string;
  disputeSubject: string;
  disputeBody: string;
}

export default function EmailSettingsPage() {
  const t = useT();
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [testing, setTesting] = useState(false);

  const [smtpHost, setSmtpHost] = useState("");
  const [smtpPort, setSmtpPort] = useState("587");
  const [smtpSecure, setSmtpSecure] = useState(false);
  const [smtpUser, setSmtpUser] = useState("");
  const [smtpPass, setSmtpPass] = useState("");
  const [fromAddress, setFromAddress] = useState("");
  const [notifyDispatchEmail, setNotifyDispatchEmail] = useState("");
  const [notifyTrafficEmail, setNotifyTrafficEmail] = useState("");

  const [disputeTo, setDisputeTo] = useState("");
  const [disputeCc1, setDisputeCc1] = useState("");
  const [disputeCc2, setDisputeCc2] = useState("");
  const [disputeCc3, setDisputeCc3] = useState("");
  const [disputeSubject, setDisputeSubject] = useState("");
  const [disputeBody, setDisputeBody] = useState("");

  const [testEmail, setTestEmail] = useState("");

  useEffect(() => {
    api
      .get("/settings/email")
      .then(({ data }: { data: EmailSettingsData }) => {
        setSmtpHost(data.smtpHost ?? "");
        setSmtpPort(String(data.smtpPort ?? 587));
        setSmtpSecure(data.smtpSecure ?? false);
        setSmtpUser(data.smtpUser ?? "");
        setSmtpPass(data.smtpPass ?? "");
        setFromAddress(data.fromAddress ?? "");
        setNotifyDispatchEmail(data.notifyDispatchEmail ?? "");
        setNotifyTrafficEmail(data.notifyTrafficEmail ?? "");
        setDisputeTo(data.disputeTo ?? "");
        setDisputeCc1(data.disputeCc1 ?? "");
        setDisputeCc2(data.disputeCc2 ?? "");
        setDisputeCc3(data.disputeCc3 ?? "");
        setDisputeSubject(data.disputeSubject ?? "");
        setDisputeBody(data.disputeBody ?? "");
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  async function handleSave() {
    setSubmitting(true);
    try {
      await api.patch("/settings/email", {
        smtpHost: smtpHost || undefined,
        smtpPort: parseInt(smtpPort, 10) || 587,
        smtpSecure,
        smtpUser: smtpUser || undefined,
        ...(smtpPass && !smtpPass.startsWith("••") ? { smtpPass } : {}),
        fromAddress: fromAddress || undefined,
        notifyDispatchEmail: notifyDispatchEmail || undefined,
        notifyTrafficEmail: notifyTrafficEmail || undefined,
        disputeTo: disputeTo || undefined,
        disputeCc1: disputeCc1 || undefined,
        disputeCc2: disputeCc2 || undefined,
        disputeCc3: disputeCc3 || undefined,
        disputeSubject: disputeSubject || undefined,
        disputeBody: disputeBody || undefined,
      });
      toast.success(t("emailSettings.settingsSaved"));
    } catch {
      toast.error(t("emailSettings.failedSave"));
    } finally {
      setSubmitting(false);
    }
  }

  async function handleTestEmail() {
    if (!testEmail.trim()) return;
    setTesting(true);
    try {
      await api.post("/settings/email/test", { email: testEmail });
      toast.success(t("emailSettings.testSent"));
    } catch (err: unknown) {
      const message =
        (err as { response?: { data?: { message?: string } } })?.response?.data?.message ||
        t("emailSettings.testFailed");
      toast.error(message);
    } finally {
      setTesting(false);
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
        title={t("emailSettings.title")}
        description={t("emailSettings.description")}
      />

      {/* SMTP Configuration */}
      <Card className="border-border bg-card p-6">
        <h2 className="mb-4 text-lg font-semibold text-foreground">
          {t("emailSettings.smtpConfig")}
        </h2>
        <div className="space-y-4">
          <div className="grid gap-4 sm:grid-cols-2">
            <div className="space-y-2">
              <Label className="text-foreground/70">
                {t("emailSettings.smtpHost")}
              </Label>
              <Input
                value={smtpHost}
                onChange={(e) => setSmtpHost(e.target.value)}
                placeholder="smtp.gmail.com"
                className="border-border bg-muted/50 text-foreground"
              />
            </div>
            <div className="space-y-2">
              <Label className="text-foreground/70">
                {t("emailSettings.smtpPort")}
              </Label>
              <Input
                type="number"
                value={smtpPort}
                onChange={(e) => setSmtpPort(e.target.value)}
                placeholder="587"
                className="border-border bg-muted/50 text-foreground"
              />
            </div>
          </div>

          <div className="grid gap-4 sm:grid-cols-2">
            <div className="space-y-2">
              <Label className="text-foreground/70">
                {t("emailSettings.smtpUser")}
              </Label>
              <Input
                value={smtpUser}
                onChange={(e) => setSmtpUser(e.target.value)}
                placeholder="user@gmail.com"
                className="border-border bg-muted/50 text-foreground"
              />
            </div>
            <div className="space-y-2">
              <Label className="text-foreground/70">
                {t("emailSettings.smtpPass")}
              </Label>
              <Input
                type="password"
                value={smtpPass}
                onChange={(e) => setSmtpPass(e.target.value)}
                placeholder="••••••••"
                className="border-border bg-muted/50 text-foreground"
              />
            </div>
          </div>

          <div className="grid gap-4 sm:grid-cols-2">
            <div className="space-y-2">
              <Label className="text-foreground/70">
                {t("emailSettings.fromAddress")}
              </Label>
              <Input
                type="email"
                value={fromAddress}
                onChange={(e) => setFromAddress(e.target.value)}
                placeholder="noreply@yourcompany.com"
                className="border-border bg-muted/50 text-foreground"
              />
            </div>
            <div className="flex items-center gap-3 pt-6">
              <Switch
                checked={smtpSecure}
                onCheckedChange={setSmtpSecure}
                id="smtp-secure"
              />
              <Label htmlFor="smtp-secure" className="text-foreground/70">
                {t("emailSettings.smtpSecure")}
              </Label>
            </div>
          </div>
        </div>
      </Card>

      {/* Notification Emails */}
      <Card className="border-border bg-card p-6">
        <h2 className="mb-4 text-lg font-semibold text-foreground">
          {t("emailSettings.notificationEmails")}
        </h2>
        <p className="mb-4 text-sm text-muted-foreground">
          {t("emailSettings.notificationEmailsDesc")}
        </p>
        <div className="grid gap-4 sm:grid-cols-2">
          <div className="space-y-2">
            <Label className="text-foreground/70">
              {t("emailSettings.dispatchEmail")}
            </Label>
            <Input
              type="email"
              value={notifyDispatchEmail}
              onChange={(e) => setNotifyDispatchEmail(e.target.value)}
              placeholder="dispatch@yourcompany.com"
              className="border-border bg-muted/50 text-foreground"
            />
          </div>
          <div className="space-y-2">
            <Label className="text-foreground/70">
              {t("emailSettings.trafficEmail")}
            </Label>
            <Input
              type="email"
              value={notifyTrafficEmail}
              onChange={(e) => setNotifyTrafficEmail(e.target.value)}
              placeholder="traffic@yourcompany.com"
              className="border-border bg-muted/50 text-foreground"
            />
          </div>
        </div>
      </Card>

      {/* Dispute Notification */}
      <Card className="border-border bg-card p-6">
        <div className="mb-4 flex items-center gap-2">
          <AlertTriangle className="h-5 w-5 text-amber-500" />
          <h2 className="text-lg font-semibold text-foreground">
            {t("emailSettings.disputeNotification")}
          </h2>
        </div>
        <p className="mb-4 text-sm text-muted-foreground">
          {t("emailSettings.disputeNotificationDesc")}
        </p>

        {/* TO override */}
        <div className="mb-4 space-y-2">
          <Label className="text-foreground/70">
            {t("emailSettings.disputeTo")}
          </Label>
          <Input
            type="email"
            value={disputeTo}
            onChange={(e) => setDisputeTo(e.target.value)}
            placeholder={t("emailSettings.disputeToPlaceholder")}
            className="border-border bg-muted/50 text-foreground"
          />
        </div>

        {/* CC fields */}
        <div className="mb-4 grid gap-4 sm:grid-cols-3">
          {[
            { label: t("emailSettings.disputeCc1"), value: disputeCc1, set: setDisputeCc1 },
            { label: t("emailSettings.disputeCc2"), value: disputeCc2, set: setDisputeCc2 },
            { label: t("emailSettings.disputeCc3"), value: disputeCc3, set: setDisputeCc3 },
          ].map(({ label, value, set }) => (
            <div key={label} className="space-y-2">
              <Label className="text-foreground/70">{label}</Label>
              <Input
                type="email"
                value={value}
                onChange={(e) => set(e.target.value)}
                placeholder="cc@example.com"
                className="border-border bg-muted/50 text-foreground"
              />
            </div>
          ))}
        </div>

        {/* Subject template */}
        <div className="mb-4 space-y-2">
          <Label className="text-foreground/70">
            {t("emailSettings.disputeSubject")}
          </Label>
          <Input
            value={disputeSubject}
            onChange={(e) => setDisputeSubject(e.target.value)}
            placeholder={t("emailSettings.disputeSubjectPlaceholder")}
            className="border-border bg-muted/50 text-foreground"
          />
          <p className="text-xs text-muted-foreground">
            {t("emailSettings.disputeTokensLabel")}{" "}
            {["{AgentRef}", "{JobStatus}", "{InternalRef}", "{AgentName}", "{JobDate}", "{ServiceType}"].map((tok) => (
              <code
                key={tok}
                className="mr-1 cursor-pointer rounded bg-muted px-1 py-0.5 text-xs hover:bg-muted/70"
                onClick={() => setDisputeSubject((s) => s + tok)}
              >
                {tok}
              </code>
            ))}
          </p>
        </div>

        {/* Body template */}
        <div className="space-y-2">
          <Label className="text-foreground/70">
            {t("emailSettings.disputeBody")}
          </Label>
          <Textarea
            value={disputeBody}
            onChange={(e) => setDisputeBody(e.target.value)}
            placeholder={t("emailSettings.disputeBodyPlaceholder")}
            rows={6}
            className="border-border bg-muted/50 font-mono text-sm text-foreground"
          />
          <p className="text-xs text-muted-foreground">
            {t("emailSettings.disputeTokensLabel")}{" "}
            {[
              "{AgentRef}", "{AgentName}", "{JobStatus}", "{InternalRef}",
              "{JobDate}", "{ServiceType}", "{Route}", "{DriverName}",
              "{RepName}", "{ClientName}", "{PaxCount}",
            ].map((tok) => (
              <code
                key={tok}
                className="mr-1 cursor-pointer rounded bg-muted px-1 py-0.5 text-xs hover:bg-muted/70"
                onClick={() => setDisputeBody((s) => s + tok)}
              >
                {tok}
              </code>
            ))}
          </p>
        </div>
      </Card>

      {/* Test Email */}
      <Card className="border-border bg-card p-6">
        <h2 className="mb-4 text-lg font-semibold text-foreground">
          {t("emailSettings.testEmail")}
        </h2>
        <p className="mb-3 text-sm text-muted-foreground">
          {t("emailSettings.testEmailDesc")}
        </p>
        <div className="flex items-end gap-3">
          <div className="flex-1">
            <Label className="text-foreground/70">
              {t("emailSettings.recipientEmail")}
            </Label>
            <Input
              type="email"
              value={testEmail}
              onChange={(e) => setTestEmail(e.target.value)}
              placeholder="test@example.com"
              className="border-border bg-muted/50 text-foreground"
            />
          </div>
          <Button
            onClick={handleTestEmail}
            disabled={testing || !testEmail.trim()}
            size="sm"
            className="gap-1.5"
          >
            {testing ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <Send className="h-4 w-4" />
            )}
            {t("emailSettings.sendTest")}
          </Button>
        </div>
      </Card>

      {/* Save */}
      <div className="flex justify-end">
        <Button onClick={handleSave} disabled={submitting}>
          {submitting && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
          {t("common.saveChanges")}
        </Button>
      </div>
    </div>
  );
}
