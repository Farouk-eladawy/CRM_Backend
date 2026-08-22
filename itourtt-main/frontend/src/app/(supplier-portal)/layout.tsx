"use client";

import { useEffect, useState } from "react";
import { useRouter, usePathname } from "next/navigation";
import Link from "next/link";
import { useAuthStore } from "@/stores/auth-store";
import { ThemeProvider } from "@/components/theme-provider";
import { LicenseGate } from "@/components/license-gate";
import { useT } from "@/lib/i18n";
import { Truck, Briefcase, LogOut, User } from "lucide-react";
import { cn } from "@/lib/utils";

export default function SupplierPortalLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const router = useRouter();
  const { user, isAuthenticated, hydrate } = useAuthStore();
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    hydrate();
    setMounted(true);
  }, [hydrate]);

  useEffect(() => {
    if (mounted && !isAuthenticated) {
      router.replace("/login");
    }
    if (mounted && isAuthenticated && user?.role !== "SUPPLIER") {
      router.replace("/dashboard");
    }
  }, [mounted, isAuthenticated, user, router]);

  if (!mounted || !isAuthenticated || user?.role !== "SUPPLIER") {
    return (
      <div className="flex min-h-screen items-center justify-center bg-background">
        <div className="h-6 w-6 animate-spin rounded-full border-2 border-muted-foreground/20 border-t-foreground" />
      </div>
    );
  }

  return (
    <ThemeProvider>
      <LicenseGate>
        <SupplierPortalShell user={user}>{children}</SupplierPortalShell>
      </LicenseGate>
    </ThemeProvider>
  );
}

function SupplierPortalShell({
  user,
  children,
}: {
  user: { name: string; role: string };
  children: React.ReactNode;
}) {
  const pathname = usePathname();
  const { logout } = useAuthStore();
  const t = useT();

  const tabs = [
    { href: "/supplier", label: t("supplierPortal.myJobs"), icon: Briefcase, exact: true },
    { href: "/supplier/profile", label: t("supplierPortal.profile"), icon: User },
  ];

  return (
    <div className="flex min-h-screen flex-col bg-background">
      {/* Top bar */}
      <header className="sticky top-0 z-50 border-b border-border bg-card">
        <div className="flex h-12 items-center justify-between px-4">
          <Link href="/supplier" className="flex items-center gap-2">
            <div className="flex h-7 w-7 items-center justify-center rounded-lg bg-primary/10">
              <Truck className="h-3.5 w-3.5 text-primary" />
            </div>
            <span className="text-sm font-semibold text-foreground">
              {t("supplierPortal.title")}
            </span>
          </Link>
          <span className="text-xs text-muted-foreground max-w-[120px] truncate">
            {user.name}
          </span>
        </div>
      </header>

      {/* Page content */}
      <main className="flex-1 overflow-y-auto px-4 py-4 pb-20">
        {children}
      </main>

      {/* Footer — fixed above bottom nav */}
      <div className="fixed bottom-16 left-0 right-0 z-40 border-t border-border bg-gray-500/15 px-4 py-1 text-right text-[11px] text-foreground">
        Developed by: <a href="https://wa.me/+201002805139" target="_blank" rel="noopener noreferrer" className="underline hover:text-primary">Mohamed Gouda</a> &middot; v{process.env.NEXT_PUBLIC_APP_VERSION}
      </div>

      {/* Bottom tab bar */}
      <nav className="fixed bottom-0 left-0 right-0 z-50 border-t border-border bg-card safe-bottom">
        <div className="flex h-16 items-center justify-around">
          {tabs.map((tab) => {
            const isActive = tab.exact
              ? pathname === tab.href
              : pathname.startsWith(tab.href);
            return (
              <Link
                key={tab.href}
                href={tab.href}
                className={cn(
                  "flex flex-1 flex-col items-center gap-0.5 py-2 text-[10px] font-medium transition-colors",
                  isActive
                    ? "text-primary"
                    : "text-muted-foreground active:text-foreground",
                )}
              >
                <tab.icon className={cn("h-5 w-5", isActive && "text-primary")} />
                {tab.label}
              </Link>
            );
          })}
          <button
            onClick={logout}
            className="flex flex-1 flex-col items-center gap-0.5 py-2 text-[10px] font-medium text-muted-foreground active:text-destructive"
          >
            <LogOut className="h-5 w-5" />
            {t("header.signOut")}
          </button>
        </div>
      </nav>
    </div>
  );
}
