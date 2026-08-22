"use client";

import { useState, useEffect, useMemo } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import Image from "next/image";
import {
  LayoutDashboard,
  CalendarClock,
  Briefcase,
  MapPin,
  Car,
  Users,
  UserCheck,
  Building2,
  Truck,
  DollarSign,
  BarChart3,
  Settings2,
  ChevronRight,
  ChevronsLeft,
  ChevronsRight,
  Palette,
  Building,
  ShieldCheck,
  MessageCircle,
  Mail,
  Lock,
  ClipboardList,
  Globe,
  Tag,
  SlidersHorizontal,
  Receipt,
  HardDrive,
  PackagePlus,
  Newspaper,
  Search,
  FileText,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { Separator } from "@/components/ui/separator";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { useT } from "@/lib/i18n";
import { usePermissionsStore } from "@/stores/permissions-store";
import { useCompanyStore } from "@/stores/company-store";
import { useAuthStore } from "@/stores/auth-store";

export interface NavLink {
  type: "link";
  nameKey: string;
  href: string;
  icon: React.ElementType;
  permissionKey?: string;
  featureFlag?: string;
  allowedEmails?: string[];
}

export interface NavSeparator {
  type: "separator";
}

export interface NavSectionLabel {
  type: "section-label";
  labelKey: string;
}

export interface NavGroup {
  type: "group";
  nameKey: string;
  icon: React.ElementType;
  children: NavLink[];
}

export type NavItem = NavLink | NavSeparator | NavSectionLabel | NavGroup;

// The B2C website + content CMS is a standalone system now (transferra.ae),
// connected only via the partner pricing/jobs API. Its management UI —
// including public prices and the extras catalog — is owned by the B2C admin,
// so it's removed here; iTourTT keeps only ops. (The pricing/extras DATA and
// the /extras/selectable lookup remain for job costing + manual entry.)
export const navigation: NavItem[] = [
  { type: "section-label", labelKey: "sidebar.section.operations" },
  { type: "link", nameKey: "sidebar.dashboard", href: "/dashboard", icon: LayoutDashboard, permissionKey: "dashboard" },
  { type: "link", nameKey: "sidebar.dispatch", href: "/dashboard/dispatch", icon: CalendarClock, permissionKey: "dispatch" },
  { type: "link", nameKey: "sidebar.carDispatch", href: "/dashboard/car-dispatch", icon: Car, permissionKey: "dispatch", featureFlag: "NEXT_PUBLIC_ENABLE_CAR_DISPATCH" },
  { type: "link", nameKey: "sidebar.trafficJobs", href: "/dashboard/traffic-jobs", icon: Briefcase, permissionKey: "traffic-jobs" },
  { type: "section-label", labelKey: "sidebar.section.finance" },
  { type: "link", nameKey: "sidebar.finance", href: "/dashboard/finance", icon: DollarSign, permissionKey: "finance" },
  { type: "link", nameKey: "sidebar.b2cInvoices", href: "/dashboard/finance/b2c-invoices", icon: FileText, permissionKey: "finance.b2cInvoices" },
  { type: "link", nameKey: "sidebar.reports", href: "/dashboard/reports", icon: BarChart3, permissionKey: "reports" },
  { type: "link", nameKey: "sidebar.jobLocks", href: "/dashboard/job-locks", icon: Lock, permissionKey: "job-locks" },
  { type: "link", nameKey: "sidebar.activityLog", href: "/dashboard/activity-log", icon: ClipboardList, permissionKey: "activity-logs" },
  { type: "section-label", labelKey: "sidebar.section.system" },
  {
    type: "group",
    nameKey: "sidebar.systemParams",
    icon: Settings2,
    children: [
      { type: "link", nameKey: "sidebar.locations", href: "/dashboard/locations", icon: MapPin, permissionKey: "locations" },
      { type: "link", nameKey: "sidebar.vehicles", href: "/dashboard/vehicles", icon: Car, permissionKey: "vehicles" },
      { type: "link", nameKey: "sidebar.drivers", href: "/dashboard/drivers", icon: Users, permissionKey: "drivers" },
      { type: "link", nameKey: "sidebar.driverTariffs", href: "/dashboard/driver-tariffs", icon: Receipt, permissionKey: "driver-tariffs" },
      { type: "link", nameKey: "sidebar.reps", href: "/dashboard/reps", icon: UserCheck, permissionKey: "reps" },
      { type: "link", nameKey: "sidebar.agents", href: "/dashboard/agents", icon: Building2, permissionKey: "agents" },
      { type: "link", nameKey: "sidebar.customers", href: "/dashboard/customers", icon: Users, permissionKey: "customers" },
      { type: "link", nameKey: "sidebar.suppliers", href: "/dashboard/suppliers", icon: Truck, permissionKey: "suppliers" },
      { type: "link", nameKey: "sidebar.styling", href: "/dashboard/styling", icon: Palette },
      { type: "link", nameKey: "sidebar.company", href: "/dashboard/company", icon: Building, permissionKey: "company" },
      { type: "link", nameKey: "sidebar.whatsapp", href: "/dashboard/whatsapp", icon: MessageCircle, permissionKey: "whatsapp" },
      { type: "link", nameKey: "sidebar.emailSettings", href: "/dashboard/email-settings", icon: Mail, permissionKey: "company" },
      { type: "link", nameKey: "sidebar.googleDrive", href: "/dashboard/google-drive", icon: HardDrive, permissionKey: "company" },
      { type: "link", nameKey: "sidebar.users", href: "/dashboard/users", icon: ShieldCheck, permissionKey: "users" },
      { type: "link", nameKey: "sidebar.jobControl", href: "/dashboard/job-control", icon: SlidersHorizontal, permissionKey: "job-control" },
    ],
  },
];

const STORAGE_KEY = "sidebar-collapsed";

export function Sidebar() {
  const pathname = usePathname();
  const t = useT();
  const [collapsed, setCollapsed] = useState(false);
  const { has: hasPerm, isLoaded: permsLoaded } = usePermissionsStore();
  const { logoUrl, faviconUrl } = useCompanyStore();
  const { user } = useAuthStore();

  // Feature flags — must use static keys for Next.js inlining
  const featureFlags: Record<string, boolean> = {
    NEXT_PUBLIC_ENABLE_CAR_DISPATCH: process.env.NEXT_PUBLIC_ENABLE_CAR_DISPATCH === "true",
  };

  // Filter navigation based on permissions, feature flags, and email allowlist
  const canAccess = (item: NavLink): boolean => {
    if (item.featureFlag && !featureFlags[item.featureFlag]) return false;
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

  useEffect(() => {
    const stored = localStorage.getItem(STORAGE_KEY);
    if (stored === "true") setCollapsed(true);
  }, []);

  const toggleCollapsed = () => {
    setCollapsed((prev) => {
      const next = !prev;
      localStorage.setItem(STORAGE_KEY, String(next));
      return next;
    });
  };

  const toggleGroup = (key: string) => {
    if (collapsed) {
      setCollapsed(false);
      localStorage.setItem(STORAGE_KEY, "false");
      setGroupOpen((prev) => ({ ...prev, [key]: true }));
      return;
    }
    setGroupOpen((prev) => ({ ...prev, [key]: !prev[key] }));
  };

  return (
    <TooltipProvider delayDuration={0}>
      <aside
        className={cn(
          "bg-sidebar flex h-full flex-col border-r border-sidebar-border transition-all duration-200",
          collapsed ? "w-[60px]" : "w-60"
        )}
      >
        {/* Brand */}
        <div className={cn("flex h-14 items-center", collapsed ? "justify-center px-0" : "px-4")}>
          {collapsed ? (
            faviconUrl ? (
              <img
                src={faviconUrl}
                alt="iTourTT"
                width={32}
                height={32}
                className="h-8 w-8 shrink-0 rounded object-contain"
              />
            ) : (
              <Image
                src="/favicon.svg"
                alt="iTourTT"
                width={32}
                height={32}
                className="shrink-0"
              />
            )
          ) : logoUrl ? (
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
        <nav className={cn("flex-1 space-y-0.5 overflow-y-auto overflow-x-hidden", collapsed ? "p-1.5" : "p-2")}>
          {filteredNavigation.map((item, i) => {
            if (item.type === "separator") {
              return <Separator key={i} className="my-2 bg-sidebar-border" />;
            }

            if (item.type === "section-label") {
              // In collapsed mode, show a thin divider instead of the label
              if (collapsed) {
                return <Separator key={i} className="my-2 bg-sidebar-border" />;
              }
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
              const isOpen = !!groupOpen[item.nameKey] && !collapsed;
              const Icon = item.icon;
              const hasActiveChild = item.children.some((c) =>
                pathname.startsWith(c.href)
              );
              const label = t(item.nameKey);

              return (
                <div key={item.nameKey}>
                  <Tooltip>
                    <TooltipTrigger asChild>
                      <button
                        onClick={() => toggleGroup(item.nameKey)}
                        className={cn(
                          "flex w-full items-center rounded-lg text-sm font-medium transition-colors",
                          collapsed
                            ? "justify-center px-0 py-2"
                            : "gap-2.5 px-3 py-2",
                          hasActiveChild
                            ? "border-l-2 border-sidebar-primary bg-sidebar-accent text-sidebar-foreground"
                            : "border-l-2 border-transparent text-sidebar-foreground/60 hover:bg-sidebar-accent/60 hover:text-sidebar-foreground"
                        )}
                      >
                        <Icon className="h-4 w-4 shrink-0" />
                        {!collapsed && (
                          <>
                            <span className="flex-1 text-left whitespace-nowrap overflow-hidden">{label}</span>
                            <ChevronRight
                              className={cn(
                                "h-3.5 w-3.5 text-sidebar-foreground/40 transition-transform duration-150",
                                isOpen && "rotate-90"
                              )}
                            />
                          </>
                        )}
                      </button>
                    </TooltipTrigger>
                    {collapsed && (
                      <TooltipContent side="right" sideOffset={8}>
                        {label}
                      </TooltipContent>
                    )}
                  </Tooltip>

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
                              "flex items-center gap-2.5 rounded-lg px-3 py-1.5 text-sm font-medium transition-colors whitespace-nowrap overflow-hidden",
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
            const label = t(item.nameKey);
            return (
              <Tooltip key={item.href}>
                <TooltipTrigger asChild>
                  <Link
                    href={item.href}
                    className={cn(
                      "flex items-center rounded-lg text-sm font-medium transition-colors",
                      collapsed
                        ? "justify-center px-0 py-2"
                        : "gap-2.5 px-3 py-2",
                      isActive
                        ? "border-l-2 border-sidebar-primary bg-sidebar-accent text-sidebar-foreground"
                        : "border-l-2 border-transparent text-sidebar-foreground/60 hover:bg-sidebar-accent/60 hover:text-sidebar-foreground"
                    )}
                  >
                    <Icon className="h-4 w-4 shrink-0" />
                    {!collapsed && (
                      <span className="whitespace-nowrap overflow-hidden">{label}</span>
                    )}
                  </Link>
                </TooltipTrigger>
                {collapsed && (
                  <TooltipContent side="right" sideOffset={8}>
                    {label}
                  </TooltipContent>
                )}
              </Tooltip>
            );
          })}
        </nav>

        {/* Collapse toggle */}
        <Separator className="bg-sidebar-border" />
        <div className={cn("flex items-center", collapsed ? "justify-center p-2" : "justify-end px-3 py-2")}>
          <Tooltip>
            <TooltipTrigger asChild>
              <button
                onClick={toggleCollapsed}
                className="flex h-8 w-8 items-center justify-center rounded-lg border border-sidebar-border bg-sidebar-accent text-sidebar-foreground/60 transition-colors hover:bg-sidebar-accent/80 hover:text-sidebar-foreground"
              >
                {collapsed ? (
                  <ChevronsRight className="h-4 w-4" />
                ) : (
                  <ChevronsLeft className="h-4 w-4" />
                )}
              </button>
            </TooltipTrigger>
            <TooltipContent side="right" sideOffset={8}>
              {collapsed ? t("sidebar.expand") : t("sidebar.collapse")}
            </TooltipContent>
          </Tooltip>
        </div>
      </aside>
    </TooltipProvider>
  );
}
