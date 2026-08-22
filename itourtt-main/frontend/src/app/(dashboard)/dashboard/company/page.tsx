"use client";

import { useEffect, useState, useRef } from "react";
import { Building2, ImageIcon, FileImage, Loader2, ShieldCheck, ShieldX, ShieldAlert, Key, RefreshCw } from "lucide-react";
import { toast } from "sonner";
import { PageHeader } from "@/components/page-header";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import api from "@/lib/api";
import { useT } from "@/lib/i18n";
import { RichTextEditor } from "@/components/rich-text-editor";
import { Badge } from "@/components/ui/badge";
import { usePermission } from "@/hooks/use-permission";

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "";

interface CompanySettingsData {
  companyName: string;
  logoUrl: string | null;
  faviconUrl: string | null;
  reportHeaderHtml: string | null;
  reportFooterHtml: string | null;
  licenseKey: string | null;
  systemNotificationEmail: string | null;
}

type LicenseVerdict =
  | "active" | "grace" | "expired" | "revoked" | "invalid"
  | "domain_mismatch" | "install_blocked" | "ip_mismatch" | "grace_expired";

interface LicenseStatus {
  valid: boolean;
  expiresAt: string | null;
  daysRemaining: number | null;
  message: string;
  status?: LicenseVerdict;      // raw verdict from the Ed25519 verifier
  checkedOnline?: boolean;      // confirmed against the license server this call?
  lastCheckedAt?: string | null; // ISO of last successful online check
}

// tone + short label per verdict — drives the status card colour and badge (#1 grace=amber, #2 distinct modes)
type Tone = "ok" | "warn" | "bad";
const VERDICT_META: Record<LicenseVerdict, { tone: Tone; label: string }> = {
  active:          { tone: "ok",   label: "Active" },
  grace:           { tone: "warn", label: "Renew soon" },
  expired:         { tone: "bad",  label: "Expired" },
  revoked:         { tone: "bad",  label: "Revoked" },
  invalid:         { tone: "bad",  label: "Invalid" },
  domain_mismatch: { tone: "bad",  label: "Wrong host" },
  install_blocked: { tone: "bad",  label: "Install limit" },
  ip_mismatch:     { tone: "bad",  label: "Wrong server" },
  grace_expired:   { tone: "bad",  label: "Unverified" },
};
const TONE_STYLE: Record<Tone, { wrap: string; text: string; badge: string }> = {
  ok:   { wrap: "border-emerald-500/30 bg-emerald-500/10", text: "text-emerald-600", badge: "border-emerald-500/50 text-emerald-600" },
  warn: { wrap: "border-amber-500/30 bg-amber-500/10",     text: "text-amber-600",   badge: "border-amber-500/50 text-amber-600" },
  bad:  { wrap: "border-destructive/30 bg-destructive/10", text: "text-destructive", badge: "border-destructive/50 text-destructive" },
};

export default function CompanyPage() {
  const t = useT();
  const canEditSettings = usePermission("company.editSettings");
  const canUploadLogo = usePermission("company.uploadLogo");
  const canUploadFavicon = usePermission("company.uploadFavicon");
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [uploadingLogo, setUploadingLogo] = useState(false);
  const [uploadingFavicon, setUploadingFavicon] = useState(false);

  const [companyName, setCompanyName] = useState("iTour TT");
  const [logoUrl, setLogoUrl] = useState<string | null>(null);
  const [faviconUrl, setFaviconUrl] = useState<string | null>(null);
  const [reportHeaderHtml, setReportHeaderHtml] = useState("");
  const [reportFooterHtml, setReportFooterHtml] = useState("");
  const [systemNotificationEmail, setSystemNotificationEmail] = useState("");
  const [licenseKey, setLicenseKey] = useState("");
  const [licenseStatus, setLicenseStatus] = useState<LicenseStatus | null>(null);
  const [activatingLicense, setActivatingLicense] = useState(false);
  const [recheckingLicense, setRecheckingLicense] = useState(false);

  const logoInput = useRef<HTMLInputElement>(null);
  const faviconInput = useRef<HTMLInputElement>(null);

  useEffect(() => {
    Promise.all([
      api.get("/settings/company"),
      api.get("/settings/license-status"),
    ])
      .then(([companyRes, licenseRes]) => {
        const data: CompanySettingsData = companyRes.data;
        setCompanyName(data.companyName ?? "iTour TT");
        setLogoUrl(data.logoUrl ?? null);
        setFaviconUrl(data.faviconUrl ?? null);
        setReportHeaderHtml(data.reportHeaderHtml ?? "");
        setReportFooterHtml(data.reportFooterHtml ?? "");
        setSystemNotificationEmail(data.systemNotificationEmail ?? "");
        setLicenseKey(data.licenseKey ?? "");
        setLicenseStatus(licenseRes.data);
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  async function handleUploadLogo(file: File) {
    setUploadingLogo(true);
    try {
      const formData = new FormData();
      formData.append("file", file);
      const { data } = await api.post("/settings/company/logo", formData, {
        headers: { "Content-Type": "multipart/form-data" },
      });
      setLogoUrl(data.url);
      toast.success(t("company.logoUploaded"));
    } catch {
      toast.error(t("company.failedLogo"));
    } finally {
      setUploadingLogo(false);
    }
  }

  async function handleUploadFavicon(file: File) {
    setUploadingFavicon(true);
    try {
      const formData = new FormData();
      formData.append("file", file);
      const { data } = await api.post("/settings/company/favicon", formData, {
        headers: { "Content-Type": "multipart/form-data" },
      });
      setFaviconUrl(data.url);
      toast.success(t("company.faviconUploaded"));
    } catch {
      toast.error(t("company.failedFavicon"));
    } finally {
      setUploadingFavicon(false);
    }
  }

  async function handleSave() {
    setSubmitting(true);
    try {
      await api.patch("/settings/company", {
        companyName,
        reportHeaderHtml: reportHeaderHtml || null,
        reportFooterHtml: reportFooterHtml || null,
        systemNotificationEmail: systemNotificationEmail.trim() || null,
      });
      toast.success(t("company.settingsSaved"));
    } catch {
      toast.error(t("company.failedSave"));
    } finally {
      setSubmitting(false);
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center py-20">
        <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <PageHeader
        title={t("company.title")}
        description={t("company.description")}
      />

      {/* Company Identity */}
      <Card className="border-border bg-card p-6">
        <h3 className="mb-4 text-base font-medium text-foreground">
          {t("company.identity")}
        </h3>

        <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
          {/* Company Name */}
          <div className="space-y-2">
            <Label className="text-foreground/70">{t("company.companyName")}</Label>
            <Input
              value={companyName}
              onChange={(e) => setCompanyName(e.target.value)}
              className="border-border bg-muted/50 text-foreground placeholder:text-muted-foreground/50"
              placeholder="Company name"
              disabled={!canEditSettings}
            />
          </div>

          {/* Logo */}
          <div className="space-y-2">
            <Label className="text-foreground/70">{t("company.companyLogo")}</Label>
            <div className="flex items-center gap-4">
              <div className="flex h-[120px] w-[120px] shrink-0 items-center justify-center rounded-lg border border-dashed border-border bg-muted/30">
                {logoUrl ? (
                  <img
                    src={`${API_BASE}${logoUrl}`}
                    alt="Logo"
                    className="h-full w-full rounded-lg object-contain p-2"
                  />
                ) : (
                  <Building2 className="h-10 w-10 text-muted-foreground/40" />
                )}
              </div>
              <div>
                <input
                  ref={logoInput}
                  type="file"
                  accept="image/*"
                  className="hidden"
                  onChange={(e) => {
                    const file = e.target.files?.[0];
                    if (file) handleUploadLogo(file);
                  }}
                />
                {canUploadLogo && (
                  <Button
                    variant="outline"
                    size="sm"
                    disabled={uploadingLogo}
                    onClick={() => logoInput.current?.click()}
                    className="gap-1.5"
                  >
                    {uploadingLogo ? (
                      <Loader2 className="h-4 w-4 animate-spin" />
                    ) : (
                      <ImageIcon className="h-4 w-4" />
                    )}
                    {t("company.uploadLogo")}
                  </Button>
                )}
                <p className="mt-1 text-xs text-muted-foreground/60">{t("company.logoHint")}</p>
              </div>
            </div>
          </div>

          {/* Favicon */}
          <div className="space-y-2">
            <Label className="text-foreground/70">{t("company.favicon")}</Label>
            <div className="flex items-center gap-4">
              <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-lg border border-dashed border-border bg-muted/30">
                {faviconUrl ? (
                  <img
                    src={`${API_BASE}${faviconUrl}`}
                    alt="Favicon"
                    className="h-full w-full rounded-lg object-contain p-1"
                  />
                ) : (
                  <FileImage className="h-5 w-5 text-muted-foreground/40" />
                )}
              </div>
              <div>
                <input
                  ref={faviconInput}
                  type="file"
                  accept="image/*"
                  className="hidden"
                  onChange={(e) => {
                    const file = e.target.files?.[0];
                    if (file) handleUploadFavicon(file);
                  }}
                />
                {canUploadFavicon && (
                  <Button
                    variant="outline"
                    size="sm"
                    disabled={uploadingFavicon}
                    onClick={() => faviconInput.current?.click()}
                    className="gap-1.5"
                  >
                    {uploadingFavicon ? (
                      <Loader2 className="h-4 w-4 animate-spin" />
                    ) : (
                      <FileImage className="h-4 w-4" />
                    )}
                    {t("company.uploadFavicon")}
                  </Button>
                )}
                <p className="mt-1 text-xs text-muted-foreground/60">
                  {t("company.faviconHint")}
                </p>
              </div>
            </div>
          </div>
        </div>
      </Card>

      {/* System Email Notifications */}
      <Card className="border-border bg-card p-6">
        <h3 className="mb-1 text-base font-medium text-foreground">
          {t("company.systemNotifications") || "System Email Notifications"}
        </h3>
        <p className="mb-4 text-sm text-muted-foreground">
          {t("company.systemNotificationsDesc") ||
            "A single mailbox that receives all automated system notifications (e.g. job updates). Leave blank to disable these emails. Individual admin users are no longer emailed."}
        </p>
        <div className="max-w-md space-y-2">
          <Label className="text-foreground/70">
            {t("company.systemNotificationEmail") || "Notification Email"}
          </Label>
          <Input
            type="email"
            value={systemNotificationEmail}
            onChange={(e) => setSystemNotificationEmail(e.target.value)}
            className="border-border bg-muted/50 text-foreground placeholder:text-muted-foreground/50"
            placeholder="info@fulvago.com"
            disabled={!canEditSettings}
          />
        </div>
      </Card>

      {/* Report Header */}
      <Card className="border-border bg-card p-6">
        <h3 className="mb-1 text-base font-medium text-foreground">
          {t("company.reportHeader")}
        </h3>
        <p className="mb-4 text-sm text-muted-foreground">
          {t("company.reportHeaderDesc")}
        </p>
        <RichTextEditor
          content={reportHeaderHtml}
          onChange={setReportHeaderHtml}
          logoUrl={logoUrl}
        />
      </Card>

      {/* Report Footer */}
      <Card className="border-border bg-card p-6">
        <h3 className="mb-1 text-base font-medium text-foreground">
          {t("company.reportFooter")}
        </h3>
        <p className="mb-4 text-sm text-muted-foreground">
          {t("company.reportFooterDesc")}
        </p>
        <RichTextEditor
          content={reportFooterHtml}
          onChange={setReportFooterHtml}
          logoUrl={logoUrl}
        />
      </Card>

      {/* Software License */}
      <Card className="border-border bg-card p-6">
        <h3 className="mb-1 text-base font-medium text-foreground flex items-center gap-2">
          <Key className="h-4 w-4" />
          {t("company.softwareLicense") || "Software License"}
        </h3>
        <p className="mb-4 text-sm text-muted-foreground">
          {t("company.softwareLicenseDesc") || "Enter your license key to activate the software."}
        </p>

        {/* License Status */}
        {licenseStatus && (() => {
          const verdict = (licenseStatus.status ?? (licenseStatus.valid ? "active" : "invalid")) as LicenseVerdict;
          const meta = VERDICT_META[verdict] ?? { tone: (licenseStatus.valid ? "ok" : "bad") as Tone, label: licenseStatus.valid ? "Active" : "Inactive" };
          const ts = TONE_STYLE[meta.tone];
          const Icon = meta.tone === "ok" ? ShieldCheck : meta.tone === "warn" ? ShieldAlert : ShieldX;
          const recheck = async () => {
            setRecheckingLicense(true);
            try {
              const { data } = await api.post("/settings/license-recheck");
              setLicenseStatus(data);
              toast[data.valid ? "success" : "error"](data.message || "License re-checked");
            } catch {
              toast.error(t("company.licenseRecheckFailed") || "Failed to re-check license");
            } finally {
              setRecheckingLicense(false);
            }
          };
          return (
            <div className={`mb-4 rounded-lg border px-4 py-3 ${ts.wrap}`}>
              <div className="flex items-center gap-2">
                <Icon className={`h-5 w-5 shrink-0 ${ts.text}`} />
                <div className="flex-1 min-w-0">
                  <p className={`text-sm font-medium ${ts.text}`}>{licenseStatus.message}</p>
                  {licenseStatus.expiresAt && (
                    <p className="text-xs text-muted-foreground">
                      Expires: {licenseStatus.expiresAt}
                      {licenseStatus.daysRemaining !== null && ` (${licenseStatus.daysRemaining} days remaining)`}
                    </p>
                  )}
                </div>
                <Badge variant="outline" className={ts.badge}>{meta.label}</Badge>
              </div>
              {/* Online-check signal + manual re-check (#3) */}
              <div className="mt-2 flex items-center justify-between gap-2 border-t border-border/40 pt-2">
                <p className="text-[11px] text-muted-foreground">
                  {licenseStatus.checkedOnline
                    ? "Verified online with license server"
                    : licenseStatus.lastCheckedAt
                      ? `Offline (cached) · last online check: ${new Date(licenseStatus.lastCheckedAt).toLocaleString()}`
                      : "Not yet verified online"}
                </p>
                <button
                  onClick={recheck}
                  disabled={recheckingLicense}
                  className="inline-flex shrink-0 items-center gap-1 rounded-md border border-border px-2 py-1 text-[11px] text-muted-foreground hover:bg-white/10 hover:text-foreground transition-colors disabled:opacity-50"
                >
                  <RefreshCw className={`h-3 w-3 ${recheckingLicense ? "animate-spin" : ""}`} />
                  {t("company.recheckNow") || "Re-check now"}
                </button>
              </div>
            </div>
          );
        })()}

        {/* License Key Input — second half masked */}
        <div className="space-y-2">
          <Label className="text-foreground/70">{t("company.licenseKey") || "License Key"}</Label>
          <div className="flex gap-2">
            <div className="flex-1 flex rounded-md border border-border bg-muted/50 overflow-hidden">
              <input
                type="text"
                readOnly
                value={licenseKey ? licenseKey.slice(0, Math.ceil(licenseKey.length / 2)) : ""}
                className="flex-1 bg-transparent px-3 py-2 text-sm text-foreground outline-none font-mono"
                placeholder={t("company.licenseKeyPlaceholder") || "Enter license key..."}
                tabIndex={-1}
              />
              <input
                type="password"
                readOnly
                value={licenseKey ? licenseKey.slice(Math.ceil(licenseKey.length / 2)) : ""}
                className="flex-1 bg-transparent px-0 py-2 text-sm text-foreground outline-none font-mono border-none"
                tabIndex={-1}
              />
            </div>
          </div>
          {/* Hidden actual input for pasting */}
          <div className="flex gap-2">
            <Input
              value={licenseKey}
              onChange={(e) => setLicenseKey(e.target.value)}
              placeholder={t("company.pasteFullKey") || "Paste full license key here to activate..."}
              className="border-border bg-muted/50 text-foreground placeholder:text-muted-foreground/50 font-mono text-xs"
              type="password"
            />
            <Button
              variant="outline"
              disabled={activatingLicense || !licenseKey.trim()}
              onClick={async () => {
                setActivatingLicense(true);
                try {
                  const { data } = await api.post("/settings/activate-license", { key: licenseKey.trim() });
                  setLicenseStatus(data);
                  if (data.valid) {
                    toast.success(t("company.licenseActivated") || "License activated successfully");
                    // Hard reload so the LicenseGate re-fetches with the valid key
                    setTimeout(() => { window.location.href = "/dashboard"; }, 1200);
                  } else {
                    toast.error(data.message || "Invalid license key");
                  }
                } catch {
                  toast.error(t("company.licenseFailed") || "Failed to activate license");
                } finally {
                  setActivatingLicense(false);
                }
              }}
              className="gap-1.5 shrink-0"
            >
              {activatingLicense && <Loader2 className="h-4 w-4 animate-spin" />}
              {t("company.activate") || "Activate"}
            </Button>
          </div>
        </div>
      </Card>

      {/* Save */}
      {canEditSettings && (
        <div className="flex justify-end">
          <Button
            onClick={handleSave}
            disabled={submitting}
            className="gap-1.5"
          >
            {submitting && <Loader2 className="h-4 w-4 animate-spin" />}
            {t("common.saveChanges")}
          </Button>
        </div>
      )}
    </div>
  );
}
