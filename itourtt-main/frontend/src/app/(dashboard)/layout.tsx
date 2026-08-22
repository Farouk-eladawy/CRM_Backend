"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useAuthStore } from "@/stores/auth-store";
import { useCompanyStore } from "@/stores/company-store";
import { Sidebar } from "@/components/sidebar";
import { Header } from "@/components/header";
import { ThemeProvider, useTheme } from "@/components/theme-provider";
import { LicenseGate } from "@/components/license-gate";
import { SessionConflictModal } from "@/components/session-conflict-modal";

function DashboardFrame({ children }: { children: React.ReactNode }) {
  const { settings } = useTheme();
  const style: React.CSSProperties = settings.innerBgImageUrl
    ? {
        backgroundImage: `url('${settings.innerBgImageUrl}')`,
        backgroundSize: "cover",
        backgroundPosition: "center",
        backgroundAttachment: "fixed",
      }
    : {};
  return (
    <div className="flex h-screen overflow-hidden bg-background" style={style}>
      {children}
    </div>
  );
}

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const router = useRouter();
  const { isAuthenticated, hydrate } = useAuthStore();
  const { loadCompanySettings } = useCompanyStore();
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    hydrate();
    setMounted(true);
  }, [hydrate]);

  useEffect(() => {
    if (mounted && isAuthenticated) {
      loadCompanySettings();
    }
  }, [mounted, isAuthenticated, loadCompanySettings]);

  useEffect(() => {
    if (mounted && !isAuthenticated) {
      router.replace("/login");
    }
  }, [mounted, isAuthenticated, router]);

  if (!mounted || !isAuthenticated) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-background">
        <div className="h-6 w-6 animate-spin rounded-full border-2 border-muted-foreground/20 border-t-foreground" />
      </div>
    );
  }

  return (
    <ThemeProvider>
      <LicenseGate>
        <DashboardFrame>
          <div className="hidden lg:flex">
            <Sidebar />
          </div>
          <div className="flex flex-1 flex-col overflow-hidden">
            <Header />
            <SessionConflictModal />
            <main className="flex-1 overflow-y-auto p-3 pb-10 md:p-6 md:pb-10">{children}</main>
            <footer className="flex h-14 shrink-0 flex-wrap items-center justify-end gap-3 border-t border-border bg-slate-100/95 dark:bg-card/95 px-5 text-xs text-muted-foreground backdrop-blur-sm">
              <span>iTour Transport &amp; Traffic</span>
              <span className="text-border">|</span>
              <span>
                Developed by{" "}
                <a href="https://wa.me/+201002805139" target="_blank" rel="noopener noreferrer" className="text-primary hover:underline">
                  Mohamed Gouda
                </a>
              </span>
              <span className="text-border">|</span>
              <span>v{process.env.NEXT_PUBLIC_APP_VERSION}</span>
            </footer>
          </div>
        </DashboardFrame>
      </LicenseGate>
    </ThemeProvider>
  );
}
