"use client";

import { useEffect, useState } from "react";
import QRCode from "qrcode";
import { toast } from "sonner";
import { ShieldCheck, ShieldOff, Copy, KeyRound } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import api from "@/lib/api";

function errMessage(err: unknown, fallback = "Something went wrong") {
  return (
    (err as { response?: { data?: { message?: string } } })?.response?.data?.message || fallback
  );
}

export function TwoFactorSettings() {
  const [enabled, setEnabled] = useState<boolean | null>(null);
  const [phase, setPhase] = useState<"idle" | "setup" | "recovery">("idle");
  const [secret, setSecret] = useState("");
  const [qr, setQr] = useState("");
  const [code, setCode] = useState("");
  const [recovery, setRecovery] = useState<string[]>([]);
  const [busy, setBusy] = useState(false);

  const load = async () => {
    try {
      const { data } = await api.get<{ twoFactorEnabled?: boolean }>("/users/me");
      setEnabled(!!data.twoFactorEnabled);
    } catch {
      setEnabled(false);
    }
  };
  useEffect(() => {
    load();
  }, []);

  const startSetup = async () => {
    setBusy(true);
    try {
      const { data } = await api.post<{ secret: string; otpauthUri: string }>("/auth/2fa/setup");
      setSecret(data.secret);
      setQr(await QRCode.toDataURL(data.otpauthUri, { margin: 1, width: 200 }));
      setPhase("setup");
    } catch (err) {
      toast.error(errMessage(err));
    } finally {
      setBusy(false);
    }
  };

  const enable = async () => {
    setBusy(true);
    try {
      const { data } = await api.post<{ recoveryCodes: string[] }>("/auth/2fa/enable", { code });
      setRecovery(data.recoveryCodes);
      setPhase("recovery");
      setCode("");
      toast.success("Two-factor authentication enabled");
      load();
    } catch (err) {
      toast.error(errMessage(err, "Invalid code"));
    } finally {
      setBusy(false);
    }
  };

  const disable = async () => {
    const c = window.prompt("Enter a current authenticator or recovery code to disable 2FA");
    if (!c) return;
    try {
      await api.post("/auth/2fa/disable", { code: c });
      toast.success("Two-factor authentication disabled");
      setPhase("idle");
      setSecret("");
      setQr("");
      load();
    } catch (err) {
      toast.error(errMessage(err, "Invalid code"));
    }
  };

  return (
    <Card className="border-border bg-card">
      <CardHeader className="pb-3">
        <CardTitle className="flex items-center justify-between text-lg">
          <span className="flex items-center gap-2">
            <ShieldCheck className="h-5 w-5" />
            Two-factor authentication
          </span>
          {enabled === null ? null : enabled ? (
            <Badge className="border-transparent bg-emerald-500/15 text-emerald-400">Enabled</Badge>
          ) : (
            <Badge className="border-transparent bg-amber-500/15 text-amber-400">Disabled</Badge>
          )}
        </CardTitle>
      </CardHeader>
      <CardContent>
        {/* Recovery phase must win over the enabled view so freshly-issued codes stay visible. */}
        {enabled && phase !== "recovery" ? (
          <div className="space-y-3">
            <p className="text-sm text-muted-foreground">
              Your account is protected with an authenticator app.
            </p>
            <Button variant="destructive" size="sm" className="gap-2" onClick={disable}>
              <ShieldOff className="h-4 w-4" /> Disable 2FA
            </Button>
          </div>
        ) : phase === "idle" ? (
          <div className="space-y-3">
            <p className="text-sm text-muted-foreground">
              Add a second step at sign-in using an authenticator app (Google Authenticator, Authy,
              1Password).
            </p>
            <Button size="sm" className="gap-2" disabled={busy} onClick={startSetup}>
              <KeyRound className="h-4 w-4" /> Set up 2FA
            </Button>
          </div>
        ) : phase === "setup" ? (
          <div className="space-y-4">
            <p className="text-sm text-muted-foreground">
              1. Scan this QR code with your authenticator app (or enter the key manually).
            </p>
            <div className="flex flex-col items-start gap-4 sm:flex-row sm:items-center">
              {/* eslint-disable-next-line @next/next/no-img-element */}
              {qr && <img src={qr} alt="2FA QR code" className="rounded-lg bg-white p-2" />}
              <div className="space-y-1">
                <div className="text-xs text-muted-foreground">Manual key</div>
                <button
                  type="button"
                  onClick={() => {
                    navigator.clipboard.writeText(secret);
                    toast.success("Key copied");
                  }}
                  className="inline-flex items-center gap-1.5 rounded-lg border border-border px-2.5 py-1.5 font-mono text-xs text-foreground hover:bg-muted"
                >
                  {secret} <Copy className="h-3 w-3" />
                </button>
              </div>
            </div>
            <div className="space-y-2">
              <Label className="text-sm text-muted-foreground">
                2. Enter the 6-digit code from your app
              </Label>
              <Input
                inputMode="numeric"
                maxLength={6}
                value={code}
                onChange={(e) => setCode(e.target.value.replace(/\D/g, ""))}
                className="max-w-40 text-center tracking-[0.3em]"
                placeholder="000000"
              />
            </div>
            <div className="flex gap-2">
              <Button size="sm" onClick={enable} disabled={busy || code.length !== 6}>
                Verify &amp; enable
              </Button>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => {
                  setPhase("idle");
                  setCode("");
                }}
              >
                Cancel
              </Button>
            </div>
          </div>
        ) : (
          <div className="space-y-3">
            <p className="text-sm text-foreground">
              Save these recovery codes somewhere safe. Each can be used once if you lose your
              device.
            </p>
            <div className="grid grid-cols-2 gap-2 rounded-lg border border-border bg-muted/40 p-3 font-mono text-sm">
              {recovery.map((c) => (
                <div key={c} className="text-foreground">
                  {c}
                </div>
              ))}
            </div>
            <div className="flex gap-2">
              <Button
                variant="outline"
                size="sm"
                className="gap-2"
                onClick={() => {
                  navigator.clipboard.writeText(recovery.join("\n"));
                  toast.success("Codes copied");
                }}
              >
                <Copy className="h-4 w-4" /> Copy codes
              </Button>
              <Button size="sm" onClick={() => setPhase("idle")}>
                Done
              </Button>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
