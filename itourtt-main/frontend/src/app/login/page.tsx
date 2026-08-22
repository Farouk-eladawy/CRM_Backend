"use client";

import { useState, useEffect, Suspense } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import Link from "next/link";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod/v4";
import Image from "next/image";
import { Loader2, ShieldAlert, ShieldCheck } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useAuthStore } from "@/stores/auth-store";
import { useT } from "@/lib/i18n";

const loginSchema = z.object({
  identifier: z.string().min(1, "Email or mobile number is required"),
  password: z.string().min(6, "Password must be at least 6 characters"),
});

type LoginForm = z.infer<typeof loginSchema>;

function LoginForm() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { login, verifyTwoFactor, cancelTwoFactor, twoFactorChallenge, isLoading, error, isAccountLocked, isAuthenticated, hydrate } = useAuthStore();
  const [mounted, setMounted] = useState(false);
  const [code, setCode] = useState("");
  const [loginBgUrl, setLoginBgUrl] = useState<string | null>(null);
  const [loginLogoUrl, setLoginLogoUrl] = useState<string | null>(null);
  const t = useT();

  const isDisplaced = searchParams.get("reason") === "displaced";

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<LoginForm>({
    resolver: zodResolver(loginSchema),
    defaultValues: { identifier: "", password: "" },
  });

  useEffect(() => {
    hydrate();
    setMounted(true);
    fetch("/api/auth/login-config")
      .then((r) => r.json())
      .then((d) => {
        if (d.loginBgImageUrl) setLoginBgUrl(d.loginBgImageUrl);
        if (d.loginLogoUrl) setLoginLogoUrl(d.loginLogoUrl);
      })
      .catch(() => {});
  }, [hydrate]);

  useEffect(() => {
    if (mounted && isAuthenticated) {
      const user = useAuthStore.getState().user;
      router.replace(user?.role === 'REP' ? '/rep' : user?.role === 'DRIVER' ? '/driver' : user?.role === 'SUPPLIER' ? '/supplier' : '/dashboard');
    }
  }, [mounted, isAuthenticated, router]);

  const routeForRole = (role?: string) =>
    role === 'REP' ? '/rep' : role === 'DRIVER' ? '/driver' : role === 'SUPPLIER' ? '/supplier' : '/dashboard';

  const onSubmit = async (data: LoginForm) => {
    try {
      await login(data);
      // If the account has 2FA, login withheld the session — show the code step.
      if (useAuthStore.getState().twoFactorChallenge) {
        setCode("");
        return;
      }
      router.replace(routeForRole(useAuthStore.getState().user?.role));
    } catch {
      // error is already set in the store
    }
  };

  const onVerify = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await verifyTwoFactor(code.trim());
      router.replace(routeForRole(useAuthStore.getState().user?.role));
    } catch {
      // error is already set in the store
    }
  };

  if (!mounted) return null;

  return (
    <div className="relative flex min-h-screen items-center justify-center overflow-hidden bg-black">
      {/* Background image */}
      <div
        className="absolute inset-0 z-0"
        style={{
          backgroundImage: loginBgUrl ? `url('${loginBgUrl}')` : "url('/login-bg.webp')",
          backgroundSize: "cover",
          backgroundRepeat: "no-repeat",
          backgroundPosition: "center",
        }}
      />

      {/* Login card – glass effect */}
      <div className="relative z-10 w-full max-w-sm px-4">
        <div className="rounded-2xl border border-white/10 bg-white/[0.06] p-8 shadow-2xl backdrop-blur-xl">
          {/* Logo / Brand */}
          <div className="mb-6 flex flex-col items-center gap-3">
            <Image
              src={loginLogoUrl ?? "/favicon.svg"}
              alt="iTourTT"
              width={56}
              height={56}
            />
            <h1 className="text-xl font-semibold text-white">{t("sidebar.brand")}</h1>
            <p className="text-sm text-white/50">{t("login.system")}</p>
          </div>

          {/* Session displaced warning */}
          {isDisplaced && !isAccountLocked && (
            <div className="mb-4 rounded-lg border border-amber-500/30 bg-amber-500/10 p-3 flex gap-2 items-start">
              <ShieldAlert className="h-4 w-4 text-amber-400 mt-0.5 shrink-0" />
              <p className="text-xs text-amber-300 leading-relaxed">
                Someone logged in with your credentials on another device. Please log in again. If this was not you, contact your administrator immediately.
              </p>
            </div>
          )}

          {/* Account locked warning */}
          {isAccountLocked && (
            <div className="mb-4 rounded-lg border border-red-500/40 bg-red-500/10 p-3 flex gap-2 items-start">
              <ShieldAlert className="h-4 w-4 text-red-400 mt-0.5 shrink-0" />
              <p className="text-xs text-red-300 leading-relaxed">
                Your account has been locked due to a concurrent login attempt. Please contact your system administrator to restore access.
              </p>
            </div>
          )}

          {/* Form */}
          {!twoFactorChallenge ? (
          <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
            <div className="space-y-1.5">
              <Label htmlFor="identifier" className="text-sm text-white/70">
                {t("login.identifier")}
              </Label>
              <Input
                id="identifier"
                type="text"
                placeholder={t("login.identifierPlaceholder")}
                autoComplete="username"
                className="border-white/10 bg-white/[0.06] text-white placeholder:text-white/30 focus-visible:ring-white/20"
                {...register("identifier")}
              />
              {errors.identifier && (
                <p className="text-xs text-red-400">{errors.identifier.message}</p>
              )}
            </div>

            <div className="space-y-1.5">
              <Label htmlFor="password" className="text-sm text-white/70">
                {t("login.password")}
              </Label>
              <Input
                id="password"
                type="password"
                placeholder="Enter password"
                autoComplete="current-password"
                className="border-white/10 bg-white/[0.06] text-white placeholder:text-white/30 focus-visible:ring-white/20"
                {...register("password")}
              />
              {errors.password && (
                <p className="text-xs text-red-400">
                  {errors.password.message}
                </p>
              )}
            </div>

            {error && !isAccountLocked && (
              <p className="text-center text-sm text-red-400">{error}</p>
            )}

            <Button
              type="submit"
              disabled={isLoading}
              className="w-full bg-white text-black hover:bg-white/90"
            >
              {isLoading ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  {t("login.signingIn")}
                </>
              ) : (
                t("login.signIn")
              )}
            </Button>

            <div className="text-center">
              <Link href="/forgot-password" className="text-xs text-white/40 hover:text-white/70 transition-colors">
                {t("login.forgotPassword") || "Forgot password?"}
              </Link>
            </div>
          </form>
          ) : (
          <form onSubmit={onVerify} className="space-y-4">
            <div className="flex items-center gap-2 text-white/80">
              <ShieldCheck className="h-4 w-4 shrink-0 text-white/70" />
              <span className="text-sm font-medium">Two-factor verification</span>
            </div>
            <p className="text-xs text-white/50">
              Enter the 6-digit code from your authenticator app, or a recovery code.
            </p>
            <Input
              autoFocus
              inputMode="numeric"
              autoComplete="one-time-code"
              placeholder="000000"
              value={code}
              onChange={(e) => setCode(e.target.value.replace(/[^0-9a-f-]/gi, ""))}
              className="border-white/10 bg-white/[0.06] text-center text-lg tracking-[0.3em] text-white placeholder:text-white/30 focus-visible:ring-white/20"
            />
            {error && (
              <p className="text-center text-sm text-red-400">{error}</p>
            )}
            <Button
              type="submit"
              disabled={isLoading || code.trim().length < 6}
              className="w-full bg-white text-black hover:bg-white/90"
            >
              {isLoading ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Verifying…
                </>
              ) : (
                "Verify"
              )}
            </Button>
            <button
              type="button"
              onClick={() => { cancelTwoFactor(); setCode(""); }}
              className="w-full text-center text-xs text-white/40 transition-colors hover:text-white/70"
            >
              Back to login
            </button>
          </form>
          )}
        </div>

        <p className="mt-4 text-center text-xs text-white/30">
          iTour Transport &amp; Traffic v{process.env.NEXT_PUBLIC_APP_VERSION}
        </p>
      </div>
    </div>
  );
}

export default function LoginPage() {
  return (
    <Suspense fallback={null}>
      <LoginForm />
    </Suspense>
  );
}
