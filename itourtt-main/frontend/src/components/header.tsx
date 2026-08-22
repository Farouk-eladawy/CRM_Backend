"use client";

import { useState, useEffect, useCallback, useRef } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { LogOut, User, Settings, HelpCircle, Menu, Bell, Check, CheckCheck, ChevronRight, AlertTriangle } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from "@/components/ui/dialog";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Badge } from "@/components/ui/badge";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { useAuthStore } from "@/stores/auth-store";
import { useT } from "@/lib/i18n";
import { MobileSidebar } from "@/components/mobile-sidebar";
import api from "@/lib/api";
import { cn } from "@/lib/utils";

// Static map: path segment → human-readable label
const SEGMENT_LABEL_MAP: Record<string, string> = {
  dashboard: "Dashboard",
  dispatch: "Dispatch",
  "car-dispatch": "Car Dispatch",
  "traffic-jobs": "Traffic Jobs",
  b2b: "B2B",
  online: "Online",
  finance: "Finance",
  reports: "Reports",
  locations: "Locations",
  vehicles: "Vehicles",
  drivers: "Drivers",
  "driver-tariffs": "Driver Tariffs",
  reps: "Reps",
  agents: "Agents",
  customers: "Customers",
  suppliers: "Suppliers",
  styling: "Styling",
  company: "Company",
  whatsapp: "WhatsApp",
  "email-settings": "Email / SMTP",
  "google-drive": "Google Drive",
  users: "Users",
  "job-control": "Job Control",
  "job-locks": "Job Locks",
  "activity-log": "Activity Log",
  website: "Website CMS",
  "public-prices": "Public Prices",
  "guest-bookings": "Guest Bookings",
  profile: "Profile & Settings",
  help: "Help & Support",
};

function Breadcrumb() {
  const pathname = usePathname();

  // Split into segments, filter empty strings
  const segments = pathname.split("/").filter(Boolean);

  // Build cumulative hrefs
  const crumbs = segments.map((seg, i) => ({
    label: SEGMENT_LABEL_MAP[seg] ?? seg.replace(/-/g, " ").replace(/\b\w/g, (c) => c.toUpperCase()),
    href: "/" + segments.slice(0, i + 1).join("/"),
    isLast: i === segments.length - 1,
  }));

  if (crumbs.length === 0) return null;

  return (
    <nav className="hidden lg:flex items-center gap-1 text-sm">
      {crumbs.map((crumb, i) => (
        <span key={crumb.href} className="flex items-center gap-1">
          {i > 0 && <ChevronRight className="h-3.5 w-3.5 text-muted-foreground/50 shrink-0" />}
          {crumb.isLast ? (
            <span className="text-foreground font-medium">{crumb.label}</span>
          ) : (
            <Link
              href={crumb.href}
              className="text-muted-foreground hover:text-foreground transition-colors"
            >
              {crumb.label}
            </Link>
          )}
        </span>
      ))}
    </nav>
  );
}

interface Notification {
  id: string;
  title: string;
  message: string;
  type: string;
  isRead: boolean;
  trafficJobId: string | null;
  createdAt: string;
  metadata?: Record<string, unknown> | null;
  trafficJob?: { internalRef: string; bookingStatus: string; status: string } | null;
}

export function Header() {
  const { user, logout, isAuthenticated } = useAuthStore();
  const t = useT();
  const [mobileNavOpen, setMobileNavOpen] = useState(false);
  const [notifications, setNotifications] = useState<Notification[]>([]);
  const [unreadCount, setUnreadCount] = useState(0);
  const [notifOpen, setNotifOpen] = useState(false);
  const [flightDelayQueue, setFlightDelayQueue] = useState<Notification[]>([]);
  const [acceptingDelay, setAcceptingDelay] = useState(false);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const shownDelayIds = useRef<Set<string>>(new Set());

  const fetchNotifications = useCallback(async () => {
    if (!isAuthenticated) return;
    try {
      const { data } = await api.get<{ data: { notifications: Notification[]; unreadCount: number } }>("/notifications");
      const all = data.data.notifications;
      setNotifications(all);
      setUnreadCount(data.data.unreadCount);

      // Surface unread FLIGHT_DELAY notifications as blocking modals
      const pendingDelays = all.filter(
        (n) => n.type === "FLIGHT_DELAY" && !n.isRead && !shownDelayIds.current.has(n.id)
      );
      if (pendingDelays.length > 0) {
        pendingDelays.forEach((n) => shownDelayIds.current.add(n.id));
        setFlightDelayQueue((prev) => {
          const existingIds = new Set(prev.map((n) => n.id));
          return [...prev, ...pendingDelays.filter((n) => !existingIds.has(n.id))];
        });
      }
    } catch {
      // Silently fail — user might not have permission
    }
  }, [isAuthenticated]);

  useEffect(() => {
    fetchNotifications();
    intervalRef.current = setInterval(fetchNotifications, 10000);
    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current);
    };
  }, [fetchNotifications]);

  const markAsRead = async (id: string) => {
    try {
      await api.patch(`/notifications/${id}/read`);
      setNotifications((prev) => prev.map((n) => (n.id === id ? { ...n, isRead: true } : n)));
      setUnreadCount((prev) => Math.max(0, prev - 1));
    } catch { /* ignore */ }
  };

  const markAllAsRead = async () => {
    try {
      await api.patch("/notifications/read-all");
      setNotifications((prev) => prev.map((n) => ({ ...n, isRead: true })));
      setUnreadCount(0);
    } catch { /* ignore */ }
  };

  const acceptFlightDelay = async (notif: Notification) => {
    setAcceptingDelay(true);
    try {
      await api.patch(`/notifications/${notif.id}/read`);
      setNotifications((prev) => prev.map((n) => (n.id === notif.id ? { ...n, isRead: true } : n)));
      setUnreadCount((prev) => Math.max(0, prev - 1));
    } catch { /* ignore */ } finally {
      setAcceptingDelay(false);
      setFlightDelayQueue((prev) => prev.filter((n) => n.id !== notif.id));
    }
  };

  const formatTime = (dateStr: string) => {
    const d = new Date(dateStr);
    const now = new Date();
    const diffMs = now.getTime() - d.getTime();
    const diffMins = Math.floor(diffMs / 60000);
    if (diffMins < 1) return t("notifications.justNow") || "Just now";
    if (diffMins < 60) return `${diffMins}m`;
    const diffHours = Math.floor(diffMins / 60);
    if (diffHours < 24) return `${diffHours}h`;
    const diffDays = Math.floor(diffHours / 24);
    return `${diffDays}d`;
  };

  return (
    <header className="flex h-14 items-center justify-between border-b border-border bg-slate-100 dark:bg-sidebar px-3 md:px-6">
      <div className="flex items-center gap-3">
        <button
          className="flex h-9 w-9 items-center justify-center rounded-lg text-muted-foreground transition-colors hover:bg-accent hover:text-foreground lg:hidden"
          onClick={() => setMobileNavOpen(true)}
        >
          <Menu className="h-5 w-5" />
        </button>
        <Breadcrumb />
      </div>
      <div className="flex items-center gap-2 sm:gap-3">
        {user && (
          <Badge variant="outline" className="hidden border-border text-muted-foreground sm:inline-flex">
            {t(`role.${user.role}`)}
          </Badge>
        )}

        {/* Notification Bell */}
        <DropdownMenu open={notifOpen} onOpenChange={setNotifOpen}>
          <DropdownMenuTrigger asChild>
            <button className="relative flex h-8 w-8 items-center justify-center rounded-lg text-muted-foreground transition-colors hover:bg-accent hover:text-foreground">
              <Bell className="h-4 w-4" />
              {unreadCount > 0 && (
                <span className="absolute -right-0.5 -top-0.5 flex h-4 min-w-4 items-center justify-center rounded-full bg-red-500 px-1 text-[10px] font-bold text-white">
                  {unreadCount > 99 ? "99+" : unreadCount}
                </span>
              )}
            </button>
          </DropdownMenuTrigger>
          <DropdownMenuContent
            align="end"
            className="w-80 max-h-96 overflow-y-auto border-border bg-popover text-popover-foreground p-0"
          >
            <div className="flex items-center justify-between px-3 py-2 border-b border-border">
              <span className="text-sm font-semibold">{t("notifications.title") || "Notifications"}</span>
              {unreadCount > 0 && (
                <button
                  onClick={(e) => { e.stopPropagation(); markAllAsRead(); }}
                  className="flex items-center gap-1 text-xs text-primary hover:underline"
                >
                  <CheckCheck className="h-3 w-3" />
                  {t("notifications.markAllRead") || "Mark all read"}
                </button>
              )}
            </div>
            {notifications.length === 0 ? (
              <div className="px-3 py-6 text-center text-sm text-muted-foreground">
                {t("notifications.noNotifications") || "No notifications"}
              </div>
            ) : (
              notifications.map((n) => (
                <div
                  key={n.id}
                  className={cn(
                    "flex items-start gap-2 px-3 py-2 cursor-pointer hover:bg-accent/50 border-b border-border last:border-b-0",
                    !n.isRead && "bg-primary/5"
                  )}
                  onClick={() => {
                    if (!n.isRead) markAsRead(n.id);
                    setNotifOpen(false);
                    if (n.type === "FLIGHT_DELAY") {
                      setFlightDelayQueue((prev) => {
                        if (prev.some((q) => q.id === n.id)) return prev;
                        return [...prev, n];
                      });
                    }
                  }}
                >
                  <div className="flex-1 min-w-0">
                    <p className={cn("text-xs truncate", !n.isRead ? "font-semibold text-foreground" : "text-muted-foreground")}>
                      {n.title}
                    </p>
                    <p className="text-xs text-muted-foreground truncate mt-0.5">{n.message}</p>
                  </div>
                  <div className="flex flex-col items-end gap-1 shrink-0">
                    <span className="text-[10px] text-muted-foreground">{formatTime(n.createdAt)}</span>
                    {!n.isRead && <span className="h-2 w-2 rounded-full bg-primary" />}
                  </div>
                </div>
              ))
            )}
          </DropdownMenuContent>
        </DropdownMenu>

        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button
              variant="ghost"
              size="sm"
              className="gap-2 text-muted-foreground hover:bg-accent hover:text-foreground"
            >
              {user?.name ? (
                <span className="flex h-7 w-7 items-center justify-center rounded-full bg-primary/15 text-primary text-xs font-semibold select-none">
                  {user.name.charAt(0).toUpperCase()}
                </span>
              ) : (
                <User className="h-4 w-4" />
              )}
              <span className="hidden text-sm text-foreground/80 sm:inline">{user?.name || "User"}</span>
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent
            align="end"
            className="w-48 border-border bg-popover text-popover-foreground"
          >
            <div className="px-2 py-1.5 text-xs text-muted-foreground">
              {user?.email}
            </div>
            <DropdownMenuSeparator className="bg-border" />
            <DropdownMenuItem asChild className="cursor-pointer focus:bg-accent">
              <Link href="/dashboard/profile">
                <Settings className="mr-2 h-4 w-4" />
                {t("header.profileSettings")}
              </Link>
            </DropdownMenuItem>
            <DropdownMenuSeparator className="bg-border" />
            <DropdownMenuItem
              onClick={logout}
              className="cursor-pointer text-red-400 focus:bg-accent focus:text-red-400"
            >
              <LogOut className="mr-2 h-4 w-4" />
              {t("header.signOut")}
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>

        <TooltipProvider delayDuration={0}>
          <Tooltip>
            <TooltipTrigger asChild>
              <Link
                href="/dashboard/help"
                className="flex h-8 w-8 items-center justify-center rounded-lg text-muted-foreground transition-colors hover:bg-accent hover:text-foreground"
              >
                <HelpCircle className="h-4 w-4" />
              </Link>
            </TooltipTrigger>
            <TooltipContent>{t("header.help")}</TooltipContent>
          </Tooltip>
        </TooltipProvider>
      </div>

      <MobileSidebar open={mobileNavOpen} onOpenChange={setMobileNavOpen} />

      {/* Flight Delay Blocking Modal — one at a time, queue-based */}
      {flightDelayQueue.length > 0 && (() => {
        const notif = flightDelayQueue[0];
        const meta = notif.metadata as { repName?: string; oldArrivalTime?: string | null; newArrivalTime?: string } | null;
        const fmt = (iso: string) => new Date(iso).toLocaleString("en-GB", {
          timeZone: "Africa/Cairo",
          day: "2-digit",
          month: "2-digit",
          year: "numeric",
          hour: "2-digit",
          minute: "2-digit",
          hour12: false,
        });
        const oldArrivalDisplay = meta?.oldArrivalTime ? fmt(meta.oldArrivalTime) : null;
        const newArrivalDisplay = meta?.newArrivalTime ? fmt(meta.newArrivalTime) : null;
        return (
          <Dialog open modal>
            <DialogContent
              className="max-w-md [&>button:first-of-type]:hidden"
              onInteractOutside={(e) => e.preventDefault()}
              onEscapeKeyDown={(e) => e.preventDefault()}
              onPointerDownOutside={(e) => e.preventDefault()}
            >
              <DialogHeader>
                <DialogTitle className="flex items-center gap-2 text-amber-600">
                  <AlertTriangle className="h-5 w-5" />
                  Flight Delay Alert
                </DialogTitle>
                <DialogDescription asChild>
                  <div className="space-y-3 pt-2 text-sm text-foreground">
                    <p className="font-medium">{notif.title}</p>
                    {meta?.repName && (
                      <p className="text-muted-foreground">
                        Reported by: <span className="font-medium text-foreground">{meta.repName}</span>
                      </p>
                    )}
                    {(oldArrivalDisplay || newArrivalDisplay) && (
                      <div className="grid grid-cols-2 gap-3">
                        {oldArrivalDisplay && (
                          <div className="rounded-md border border-border bg-muted/50 px-3 py-2">
                            <p className="text-xs text-muted-foreground mb-0.5">Original Arrival Time</p>
                            <p className="text-sm font-semibold text-foreground line-through decoration-red-500">{oldArrivalDisplay}</p>
                          </div>
                        )}
                        {newArrivalDisplay && (
                          <div className={`rounded-md border border-amber-200 bg-amber-50 px-3 py-2 dark:border-amber-800 dark:bg-amber-950 ${!oldArrivalDisplay ? "col-span-2" : ""}`}>
                            <p className="text-xs text-muted-foreground mb-0.5">New Arrival Time</p>
                            <p className="text-sm font-bold text-amber-700 dark:text-amber-400">{newArrivalDisplay}</p>
                          </div>
                        )}
                      </div>
                    )}
                    <p className="text-muted-foreground text-xs">
                      The flight time has been automatically updated in the system. Please review the dispatch and online jobs pages.
                    </p>
                    {flightDelayQueue.length > 1 && (
                      <p className="text-xs text-muted-foreground">
                        {flightDelayQueue.length - 1} more alert{flightDelayQueue.length - 1 > 1 ? "s" : ""} pending.
                      </p>
                    )}
                  </div>
                </DialogDescription>
              </DialogHeader>
              <div className="flex justify-end pt-2">
                <Button
                  onClick={() => acceptFlightDelay(notif)}
                  disabled={acceptingDelay}
                  className="bg-amber-600 hover:bg-amber-700 text-white"
                >
                  {acceptingDelay ? "Accepting…" : "Accept & Acknowledge"}
                </Button>
              </div>
            </DialogContent>
          </Dialog>
        );
      })()}
    </header>
  );
}
