"use client";

import { useState, useMemo, useEffect } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import Image from "next/image";
import { ChevronRight } from "lucide-react";
import { cn } from "@/lib/utils";
import { Separator } from "@/components/ui/separator";
import {
  Sheet,
  SheetContent,
  SheetTitle,
} from "@/components/ui/sheet";
import { useT } from "@/lib/i18n";
import { usePermissionsStore } from "@/stores/permissions-store";
import { useCompanyStore } from "@/stores/company-store";
import { useAuthStore } from "@/stores/auth-store";
import {
  navigation,
  type NavItem,
  type NavLink,
} from "@/components/sidebar";

interface MobileSidebarProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export function MobileSidebar({ open, onOpenChange }: MobileSidebarProps) {
  const pathname = usePathname();
  const t = useT();
  const { has: hasPerm, isLoaded: permsLoaded } = usePermissionsStore();
  const { logoUrl } = useCompanyStore();
  const { user } = useAuthStore();

  // Close drawer on navigation
  useEffect(() => {
    onOpenChange(false);
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [pathname]);

  const canAccess = (item: NavLink): boolean => {
    if (item.allowedEmails) {
      if (!user || !item.allowedEmails.includes(user.email)) return false;
    }
    if (!permsLoaded || !item.permissionKey) return true;
    return hasPerm(item.permissionKey);
  };

  const filteredNavigation = useMemo(() => {
    if (!permsLoaded) return navigation;
    return navigation
      .map((item) => {
        if (item.type === "group") {
          const visibleChildren = item.children.filter(canAccess);
          if (visibleChildren.length === 0) return null;
          return { ...item, children: visibleChildren };
        }
        if (item.type === "link" && !canAccess(item)) return null;
        return item;
      })
      .filter(Boolean) as NavItem[];
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [permsLoaded, hasPerm]);

  const [groupOpen, setGroupOpen] = useState<Record<string, boolean>>(() => {
    const initial: Record<string, boolean> = {};
    for (const item of navigation) {
      if (item.type === "group") {
        const childActive = item.children.some((c) =>
          pathname.startsWith(c.href)
        );
        if (childActive) initial[item.nameKey] = true;
      }
    }
    return initial;
  });

  const toggleGroup = (key: string) => {
    setGroupOpen((prev) => ({ ...prev, [key]: !prev[key] }));
  };

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent
        side="left"
        className="w-72 p-0 bg-sidebar text-sidebar-foreground"
        showCloseButton={false}
      >
        <SheetTitle className="sr-only">Navigation</SheetTitle>

        {/* Brand */}
        <div className="flex h-14 items-center px-4">
          {logoUrl ? (
            <img
              src={logoUrl}
              alt={t("sidebar.brand")}
              className="h-11 w-full object-contain"
            />
          ) : (
            <Image
              src="/itourtt-logo.svg"
              alt={t("sidebar.brand")}
              width={200}
              height={44}
              className="h-11 w-full object-contain"
              priority
            />
          )}
        </div>
        <Separator className="bg-sidebar-border" />

        {/* Navigation */}
        <nav className="flex-1 space-y-0.5 overflow-y-auto p-2">
          {filteredNavigation.map((item, i) => {
            if (item.type === "separator") {
              return <Separator key={i} className="my-2 bg-sidebar-border" />;
            }

            if (item.type === "section-label") {
              return (
                <p
                  key={i}
                  className="text-[10px] uppercase tracking-widest text-sidebar-foreground/40 px-2 pt-4 pb-1 select-none"
                >
                  {t(item.labelKey)}
                </p>
              );
            }

            if (item.type === "group") {
              const isOpen = !!groupOpen[item.nameKey];
              const Icon = item.icon;
              const hasActiveChild = item.children.some((c) =>
                pathname.startsWith(c.href)
              );
              const label = t(item.nameKey);

              return (
                <div key={item.nameKey}>
                  <button
                    onClick={() => toggleGroup(item.nameKey)}
                    className={cn(
                      "flex w-full items-center gap-2.5 rounded-lg px-3 py-2 text-sm font-medium transition-colors",
                      hasActiveChild
                        ? "border-l-2 border-sidebar-primary bg-sidebar-accent text-sidebar-foreground"
                        : "border-l-2 border-transparent text-sidebar-foreground/60 hover:bg-sidebar-accent/60 hover:text-sidebar-foreground"
                    )}
                  >
                    <Icon className="h-4 w-4 shrink-0" />
                    <span className="flex-1 text-left">{label}</span>
                    <ChevronRight
                      className={cn(
                        "h-3.5 w-3.5 text-sidebar-foreground/40 transition-transform duration-150",
                        isOpen && "rotate-90"
                      )}
                    />
                  </button>

                  {isOpen && (
                    <div className="ml-3 mt-0.5 space-y-0.5 border-l border-sidebar-border pl-2">
                      {item.children.map((child) => {
                        const ChildIcon = child.icon;
                        const isActive = pathname.startsWith(child.href);
                        return (
                          <Link
                            key={child.href}
                            href={child.href}
                            className={cn(
                              "flex items-center gap-2.5 rounded-lg px-3 py-1.5 text-sm font-medium transition-colors",
                              isActive
                                ? "border-l-2 border-sidebar-primary bg-sidebar-accent text-sidebar-foreground"
                                : "border-l-2 border-transparent text-sidebar-foreground/50 hover:bg-sidebar-accent/60 hover:text-sidebar-foreground"
                            )}
                          >
                            <ChildIcon className="h-3.5 w-3.5 shrink-0" />
                            {t(child.nameKey)}
                          </Link>
                        );
                      })}
                    </div>
                  )}
                </div>
              );
            }

            // Regular link
            const isActive =
              item.href === "/dashboard"
                ? pathname === "/dashboard"
                : pathname.startsWith(item.href);
            const Icon = item.icon;
            return (
              <Link
                key={item.href}
                href={item.href}
                className={cn(
                  "flex items-center gap-2.5 rounded-lg px-3 py-2 text-sm font-medium transition-colors",
                  isActive
                    ? "border-l-2 border-sidebar-primary bg-sidebar-accent text-sidebar-foreground"
                    : "border-l-2 border-transparent text-sidebar-foreground/60 hover:bg-sidebar-accent/60 hover:text-sidebar-foreground"
                )}
              >
                <Icon className="h-4 w-4 shrink-0" />
                {t(item.nameKey)}
              </Link>
            );
          })}
        </nav>
      </SheetContent>
    </Sheet>
  );
}
