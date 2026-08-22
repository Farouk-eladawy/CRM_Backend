"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { ShieldAlert, MapPin, Smartphone } from "lucide-react";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import api from "@/lib/api";
import { useAuthStore } from "@/stores/auth-store";

interface ConflictMeta {
  kind?: string;
  subjectName?: string;
  subjectRole?: string;
  ipAddress?: string | null;
  deviceName?: string | null;
}
interface Notification {
  id: string;
  title: string;
  message: string;
  createdAt: string;
  isRead?: boolean;
  metadata?: ConflictMeta | null;
}

/**
 * Center-screen alert for Admin / Dispatch Manager / Online Manager: fires when a
 * rep/driver login is blocked because a session is already active on another
 * device. Only those roles ever receive the REP_LOGIN_CONFLICT notification, so
 * simply surfacing unread ones is sufficient. The rep/driver is not notified.
 */
export function SessionConflictModal() {
  const { isAuthenticated } = useAuthStore();
  const [current, setCurrent] = useState<Notification | null>(null);
  const seen = useRef<Set<string>>(new Set());

  const poll = useCallback(async () => {
    try {
      const { data } = await api.get<{
        data: { notifications: Notification[]; unreadCount: number };
      }>("/notifications");
      const conflicts = (data?.data?.notifications ?? []).filter(
        (n) => n.metadata?.kind === "REP_LOGIN_CONFLICT" && !n.isRead && !seen.current.has(n.id),
      );
      if (conflicts.length && !current) setCurrent(conflicts[0]);
    } catch {
      /* ignore polling errors */
    }
  }, [current]);

  useEffect(() => {
    if (!isAuthenticated) return;
    poll();
    const id = setInterval(poll, 15000);
    return () => clearInterval(id);
  }, [isAuthenticated, poll]);

  const dismiss = async () => {
    if (!current) return;
    seen.current.add(current.id);
    const id = current.id;
    setCurrent(null);
    try {
      await api.patch(`/notifications/${id}/read`);
    } catch {
      /* best-effort */
    }
  };

  if (!current) return null;
  const m = current.metadata ?? {};

  return (
    <Dialog open onOpenChange={(o) => { if (!o) void dismiss(); }}>
      <DialogContent className="max-w-md">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2 text-amber-500">
            <ShieldAlert className="h-5 w-5" /> Blocked login attempt
          </DialogTitle>
        </DialogHeader>
        <div className="space-y-3 py-1">
          <p className="text-sm text-foreground">
            A new login was blocked for{" "}
            <span className="font-semibold">{m.subjectName ?? "a user"}</span>
            {m.subjectRole ? ` (${m.subjectRole})` : ""} — a session is already active on another
            device.
          </p>
          <div className="space-y-1.5 rounded-lg border border-border bg-muted/40 p-3 text-sm">
            <div className="flex items-center gap-2 text-muted-foreground">
              <Smartphone className="h-4 w-4 shrink-0" />
              <span className="text-foreground">{m.deviceName || "Unknown device"}</span>
            </div>
            <div className="flex items-center gap-2 text-muted-foreground">
              <MapPin className="h-4 w-4 shrink-0" />
              <span className="text-foreground">{m.ipAddress || "Unknown IP"}</span>
            </div>
          </div>
          <p className="text-xs text-muted-foreground">
            The user was not notified. Review their active devices under Users → Sessions and force
            a logout if needed.
          </p>
        </div>
        <DialogFooter>
          <Button onClick={dismiss}>Dismiss</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
