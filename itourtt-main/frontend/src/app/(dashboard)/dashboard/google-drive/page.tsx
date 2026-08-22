"use client";

import { useEffect, useState, useCallback } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import { toast } from "sonner";
import { Loader2, CheckCircle2, XCircle, Info, RefreshCw, Unlink } from "lucide-react";
import { PageHeader } from "@/components/page-header";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import { Badge } from "@/components/ui/badge";
import api from "@/lib/api";
import { useT } from "@/lib/i18n";

interface GoogleDriveData {
  enabled: boolean;
  oauthClientId: string | null;
  oauthClientSecret: string | null;
  oauthRefreshToken: string | null;
  rootFolderId: string | null;
  isConnected: boolean;
}

interface MigrationResult {
  total: number;
  migrated: number;
  skipped: number;
  errors: number;
  details: string[];
}

export default function GoogleDrivePage() {
  const t = useT();
  const searchParams = useSearchParams();
  const router = useRouter();

  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [testing, setTesting] = useState(false);
  const [migrating, setMigrating] = useState(false);
  const [exchanging, setExchanging] = useState(false);

  const [enabled, setEnabled] = useState(false);
  const [clientId, setClientId] = useState("");
  const [clientSecret, setClientSecret] = useState("");
  const [rootFolderId, setRootFolderId] = useState("");
  const [isConnected, setIsConnected] = useState(false);

  const [testResult, setTestResult] = useState<{ ok: boolean; message: string } | null>(null);
  const [migrationResult, setMigrationResult] = useState<MigrationResult | null>(null);

  const load = useCallback((resetSecret = true) => {
    return api
      .get<GoogleDriveData>("/settings/google-drive")
      .then(({ data }) => {
        setEnabled(data.enabled ?? false);
        setClientId(data.oauthClientId ?? "");
        if (resetSecret) setClientSecret(data.oauthClientSecret ?? "");
        setRootFolderId(data.rootFolderId ?? "");
        setIsConnected(data.isConnected ?? false);
      })
      .catch(() => toast.error(t("googleDrive.saveError")));
  }, []);

  // ── Load settings on mount ──
  useEffect(() => {
    load().finally(() => setLoading(false));
  }, [load]);

  // ── Handle OAuth redirect-back (code in URL) ──
  useEffect(() => {
    const code = searchParams.get("code");
    if (!code) return;

    // Clear the code from the URL immediately so reload doesn't re-trigger
    router.replace("/dashboard/google-drive");

    setExchanging(true);
    const redirectUri = window.location.origin + "/dashboard/google-drive";

    api
      .post("/settings/google-drive/exchange-code", { code, redirectUri })
      .then(() => {
        toast.success(t("googleDrive.connectSuccess"));
        setIsConnected(true);
        setTestResult(null);
        return load();
      })
      .catch((err) => {
        const msg = err?.response?.data?.message || t("googleDrive.connectError");
        toast.error(msg);
      })
      .finally(() => setExchanging(false));
  }, [searchParams]);

  const handleSave = async () => {
    setSubmitting(true);
    try {
      await api.patch("/settings/google-drive", {
        enabled,
        oauthClientId: clientId || undefined,
        oauthClientSecret: clientSecret !== "••••••••" ? (clientSecret || undefined) : undefined,
        rootFolderId: rootFolderId || undefined,
      });
      toast.success(t("googleDrive.saved"));
      setTestResult(null);
      // Don't reset the secret field — keep what the user typed so they can see it wasn't reverted.
      // Only reload other fields (enabled, clientId, rootFolderId, isConnected).
      await load(false);
    } catch {
      toast.error(t("googleDrive.saveError"));
    } finally {
      setSubmitting(false);
    }
  };

  const handleConnect = async () => {
    if (!clientId || !clientSecret) {
      toast.error(t("googleDrive.saveCrendentialsFirst"));
      return;
    }
    // If user has typed a new secret (not the masked placeholder), save it first.
    // If the field shows '••••••••', the secret is already in the DB — skip the extra save.
    if (clientSecret !== "••••••••") {
      await handleSave();
    }

    const redirectUri = window.location.origin + "/dashboard/google-drive";
    try {
      const { data } = await api.post<{ url: string }>("/settings/google-drive/auth-url", { redirectUri });
      window.location.href = data.url;
    } catch (err: any) {
      const msg = err?.response?.data?.message || t("googleDrive.connectError");
      toast.error(msg);
    }
  };

  const handleDisconnect = async () => {
    try {
      await api.post("/settings/google-drive/disconnect");
      setIsConnected(false);
      toast.success(t("googleDrive.disconnectSuccess"));
      setTestResult(null);
    } catch {
      toast.error(t("googleDrive.connectError"));
    }
  };

  const handleTest = async () => {
    setTesting(true);
    setTestResult(null);
    try {
      const { data } = await api.post<{ ok: boolean; message: string }>("/settings/google-drive/test");
      setTestResult(data);
      if (data.ok) toast.success(t("googleDrive.testSuccess"));
      else toast.error(data.message || t("googleDrive.testFailed"));
    } catch {
      toast.error(t("googleDrive.testError"));
    } finally {
      setTesting(false);
    }
  };

  const handleMigrate = async () => {
    setMigrating(true);
    setMigrationResult(null);
    try {
      const { data } = await api.post<MigrationResult>("/settings/google-drive/migrate");
      setMigrationResult(data);
      if (data.errors === 0) toast.success(t("googleDrive.migrationComplete"));
      else toast.warning(`${t("googleDrive.migrationComplete")} — ${data.errors} ${t("googleDrive.errors")}`);
    } catch {
      toast.error(t("googleDrive.migrationError"));
    } finally {
      setMigrating(false);
    }
  };

  if (loading || exchanging) {
    return (
      <div className="flex flex-col items-center justify-center h-64 gap-3">
        <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
        {exchanging && <p className="text-sm text-muted-foreground">{t("googleDrive.exchanging")}</p>}
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <PageHeader
        title={t("googleDrive.title")}
        description={t("googleDrive.description")}
      />

      {/* ── Setup Instructions ── */}
      <Card className="p-5">
        <div className="flex items-center gap-2 mb-4">
          <Info className="h-4 w-4 text-blue-500 shrink-0" />
          <h3 className="font-semibold text-sm">{t("googleDrive.instructions")}</h3>
        </div>
        <ol className="space-y-2 text-sm text-muted-foreground">
          {[
            t("googleDrive.step1"),
            t("googleDrive.step2"),
            t("googleDrive.step3"),
            t("googleDrive.step4"),
            t("googleDrive.step5"),
            t("googleDrive.step6"),
            t("googleDrive.step7"),
          ].map((step, i) => (
            <li key={i} className="flex items-start gap-2">
              <span className="flex-shrink-0 w-5 h-5 rounded-full bg-muted flex items-center justify-center text-xs font-medium">
                {i + 1}
              </span>
              <span>{step}</span>
            </li>
          ))}
        </ol>
      </Card>

      {/* ── Credentials ── */}
      <Card className="p-5 space-y-5">
        <h3 className="font-semibold text-sm">{t("googleDrive.credentials")}</h3>

        {/* Enable toggle */}
        <div className="flex items-center justify-between">
          <div>
            <Label className="text-sm font-medium">{t("googleDrive.enabled")}</Label>
            <p className="text-xs text-muted-foreground mt-0.5 max-w-md">
              {t("googleDrive.enabledDesc")}
            </p>
          </div>
          <Switch checked={enabled} onCheckedChange={setEnabled} />
        </div>

        <hr className="border-border" />

        {/* Client ID */}
        <div className="space-y-1.5">
          <Label className="text-sm">{t("googleDrive.clientId")}</Label>
          <Input
            value={clientId}
            onChange={(e) => setClientId(e.target.value)}
            placeholder={t("googleDrive.clientIdPlaceholder")}
          />
        </div>

        {/* Client Secret */}
        <div className="space-y-1.5">
          <Label className="text-sm">{t("googleDrive.clientSecret")}</Label>
          <Input
            type="password"
            value={clientSecret}
            onChange={(e) => setClientSecret(e.target.value)}
            placeholder={t("googleDrive.clientSecretPlaceholder")}
          />
        </div>

        {/* Root Folder ID */}
        <div className="space-y-1.5">
          <Label className="text-sm">{t("googleDrive.rootFolderId")}</Label>
          <Input
            value={rootFolderId}
            onChange={(e) => setRootFolderId(e.target.value)}
            placeholder={t("googleDrive.rootFolderIdPlaceholder")}
          />
          <p className="text-xs text-muted-foreground">{t("googleDrive.rootFolderIdDesc")}</p>
        </div>

        <Button onClick={handleSave} disabled={submitting} size="sm">
          {submitting && <Loader2 className="h-4 w-4 animate-spin mr-2" />}
          {t("googleDrive.save")}
        </Button>
      </Card>

      {/* ── Google Account Connection ── */}
      <Card className="p-5 space-y-4">
        <div className="flex items-center justify-between">
          <h3 className="font-semibold text-sm">{t("googleDrive.connection")}</h3>
          <Badge variant={isConnected ? "default" : "secondary"} className="gap-1.5">
            {isConnected
              ? <><CheckCircle2 className="h-3 w-3" />{t("googleDrive.connected")}</>
              : <><XCircle className="h-3 w-3" />{t("googleDrive.notConnected")}</>
            }
          </Badge>
        </div>

        <div className="flex gap-2">
          {!isConnected ? (
            <Button onClick={handleConnect} size="sm" disabled={submitting}>
              {t("googleDrive.connect")}
            </Button>
          ) : (
            <>
              <Button onClick={handleTest} variant="outline" size="sm" disabled={testing}>
                {testing
                  ? <Loader2 className="h-4 w-4 animate-spin mr-2" />
                  : <RefreshCw className="h-4 w-4 mr-2" />
                }
                {t("googleDrive.testConnection")}
              </Button>
              <Button onClick={handleDisconnect} variant="ghost" size="sm" className="text-destructive hover:text-destructive">
                <Unlink className="h-4 w-4 mr-2" />
                {t("googleDrive.disconnect")}
              </Button>
            </>
          )}
        </div>

        {testResult && (
          <div className={`flex items-start gap-2 rounded-md border px-3 py-2 text-sm ${
            testResult.ok
              ? "border-green-300 bg-green-50 text-green-800 dark:bg-green-950/30 dark:border-green-700 dark:text-green-300"
              : "border-red-300 bg-red-50 text-red-800 dark:bg-red-950/30 dark:border-red-700 dark:text-red-300"
          }`}>
            {testResult.ok
              ? <CheckCircle2 className="h-4 w-4 mt-0.5 shrink-0" />
              : <XCircle className="h-4 w-4 mt-0.5 shrink-0" />
            }
            <span>{testResult.message}</span>
          </div>
        )}
      </Card>

      {/* ── Migration ── */}
      {isConnected && (
        <Card className="p-5 space-y-4">
          <div>
            <h3 className="font-semibold text-sm">{t("googleDrive.migration")}</h3>
            <p className="text-xs text-muted-foreground mt-1">{t("googleDrive.migrationDesc")}</p>
          </div>

          <Button onClick={handleMigrate} variant="outline" size="sm" disabled={migrating}>
            {migrating
              ? <><Loader2 className="h-4 w-4 animate-spin mr-2" />{t("googleDrive.migrating")}</>
              : t("googleDrive.runMigration")
            }
          </Button>

          {migrationResult && (
            <div className="space-y-2">
              <div className="grid grid-cols-4 gap-2 text-center text-sm">
                {[
                  { label: t("googleDrive.total"),    value: migrationResult.total },
                  { label: t("googleDrive.migrated"), value: migrationResult.migrated },
                  { label: t("googleDrive.skipped"),  value: migrationResult.skipped },
                  { label: t("googleDrive.errors"),   value: migrationResult.errors },
                ].map(({ label, value }) => (
                  <div key={label} className="rounded-md border p-2">
                    <div className="text-lg font-semibold">{value}</div>
                    <div className="text-xs text-muted-foreground">{label}</div>
                  </div>
                ))}
              </div>
              {migrationResult.details.length > 0 && (
                <details className="text-xs">
                  <summary className="cursor-pointer text-muted-foreground">Details ({migrationResult.details.length})</summary>
                  <pre className="mt-2 max-h-48 overflow-auto rounded bg-muted p-2 text-xs">
                    {migrationResult.details.join("\n")}
                  </pre>
                </details>
              )}
            </div>
          )}
        </Card>
      )}
    </div>
  );
}
