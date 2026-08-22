"use client";

import { useState, Suspense } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import Link from "next/link";
import { Loader2, KeyRound, ArrowLeft, CheckCircle, Eye, EyeOff } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import api from "@/lib/api";

function ResetPasswordForm() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const token = searchParams.get("token") ?? "";
  const email = searchParams.get("email") ?? "";

  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [done, setDone] = useState(false);
  const [error, setError] = useState("");

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError("");

    if (password.length < 8) {
      setError("Password must be at least 8 characters");
      return;
    }
    if (password !== confirmPassword) {
      setError("Passwords do not match");
      return;
    }
    if (!token || !email) {
      setError("Invalid reset link. Please request a new one.");
      return;
    }

    setLoading(true);
    try {
      await api.post("/auth/reset-password", { email, token, newPassword: password });
      setDone(true);
      setTimeout(() => router.push("/login"), 3000);
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { message?: string } } })?.response?.data?.message;
      setError(msg || "Reset failed. The link may have expired.");
    } finally {
      setLoading(false);
    }
  }

  if (!token || !email) {
    return (
      <div className="text-center space-y-4">
        <p className="text-red-400 text-sm">Invalid reset link. Please request a new one.</p>
        <Link href="/forgot-password">
          <Button variant="outline" className="border-white/20 text-white hover:bg-white/10">
            Request New Link
          </Button>
        </Link>
      </div>
    );
  }

  return (
    <>
      {done ? (
        <div className="text-center space-y-4">
          <CheckCircle className="h-12 w-12 text-emerald-400 mx-auto" />
          <h1 className="text-xl font-semibold text-white">Password Reset!</h1>
          <p className="text-sm text-white/60">Redirecting you to login…</p>
        </div>
      ) : (
        <>
          <div className="mb-6">
            <KeyRound className="h-10 w-10 text-blue-400 mb-3" />
            <h1 className="text-xl font-semibold text-white">Set New Password</h1>
            <p className="text-sm text-white/50 mt-1">
              Choose a strong password for <span className="text-white/70">{email}</span>
            </p>
          </div>

          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="space-y-1.5">
              <Label className="text-white/70 text-xs">New Password</Label>
              <div className="relative">
                <Input
                  type={showPassword ? "text" : "password"}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="At least 8 characters"
                  className="bg-white/10 border-white/20 text-white placeholder:text-white/30 focus:border-blue-400 pr-10"
                  disabled={loading}
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-white/40 hover:text-white/70"
                >
                  {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                </button>
              </div>
            </div>

            <div className="space-y-1.5">
              <Label className="text-white/70 text-xs">Confirm Password</Label>
              <Input
                type="password"
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                placeholder="Repeat password"
                className="bg-white/10 border-white/20 text-white placeholder:text-white/30 focus:border-blue-400"
                disabled={loading}
              />
            </div>

            {error && <p className="text-xs text-red-400">{error}</p>}

            <Button type="submit" disabled={loading} className="w-full bg-blue-600 hover:bg-blue-500 text-white">
              {loading ? <Loader2 className="h-4 w-4 animate-spin mr-2" /> : null}
              Reset Password
            </Button>

            <Link href="/login">
              <Button type="button" variant="ghost" className="w-full text-white/50 hover:text-white hover:bg-white/5 text-sm">
                <ArrowLeft className="h-4 w-4 mr-2" />
                Back to Login
              </Button>
            </Link>
          </form>
        </>
      )}
    </>
  );
}

export default function ResetPasswordPage() {
  return (
    <div className="min-h-screen bg-black flex items-center justify-center p-4">
      <div className="w-full max-w-sm">
        <div className="bg-white/5 backdrop-blur-md border border-white/10 rounded-2xl p-8 shadow-2xl">
          <Suspense fallback={<div className="text-white/50 text-sm text-center">Loading…</div>}>
            <ResetPasswordForm />
          </Suspense>
        </div>
      </div>
    </div>
  );
}
