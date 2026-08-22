"use client";

import { useCallback, useEffect, useState } from "react";
import { toast } from "sonner";
import { Smartphone, MapPin, LogOut, Loader2, Eraser } from "lucide-react";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import api from "@/lib/api";

interface UserSession {
  id: string;
  sessionId: string;
  deviceName: string | null;
  ipAddress: string | null;
  startedAt: string;
  lastSeenAt: string;
  endedAt: string | null;
  active: boolean;
}

function when(iso: string) {
  const d = new Date(iso);
  return Number.isNaN(d.getTime()) ? "—" : d.toLocaleString();
}

/** Admin view of a user's login devices, with force-logout. */
export function UserSessionsDialog({
  userId,
  userName,
  open,
  onOpenChange,
}: {
  userId: string | null;
  userName?: string;
  open: boolean;
  onOpenChange: (v: boolean) => void;
}) {
  const [sessions, setSessions] = useState<UserSession[] | null>(null);
  const [busy, setBusy] = useState<string | null>(null);

  const load = useCallback(async () => {
    if (!userId) return;
    setSessions(null);
    try {
      const { data } = await api.get<UserSession[]>(`/users/${userId}/sessions`);
      setSessions(data);
    } catch (e: unknown) {
      setSessions([]);
      toast.error((e as { response?: { data?: { message?: string } } })?.response?.data?.message || "Could not load sessions");
    }
  }, [userId]);

  useEffect(() => {
    if (open) load();
  }, [open, load]);

  const forceLogout = async (s: UserSession) => {
    if (!userId) return;
    setBusy(`logout:${s.sessionId}`);
    try {
      await api.post(`/users/${userId}/sessions/${s.sessionId}/logout`);
      toast.success("Device signed out");
      load();
    } catch (e: unknown) {
      toast.error((e as { response?: { data?: { message?: string } } })?.response?.data?.message || "Force-logout failed");
    } finally {
      setBusy(null);
    }
  };

  /** Sign the device out and delete the record, so it can't lock the user out. */
  const clearSession = async (s: UserSession) => {
    if (!userId) return;
    setBusy(`clear:${s.sessionId}`);
    try {
      await api.delete(`/users/${userId}/sessions/${s.sessionId}`);
      toast.success("Session cleared — the user can sign in again");
      load();
    } catch (e: unknown) {
      toast.error((e as { response?: { data?: { message?: string } } })?.response?.data?.message || "Could not clear session");
    } finally {
      setBusy(null);
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-lg">
        <DialogHeader>
          <DialogTitle>Active sessions{userName ? ` — ${userName}` : ""}</DialogTitle>
        </DialogHeader>
        {sessions === null ? (
          <div className="flex justify-center py-10">
            <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
          </div>
        ) : sessions.length === 0 ? (
          <p className="py-8 text-center text-sm text-muted-foreground">No sessions recorded.</p>
        ) : (
          <div className="max-h-[60vh] space-y-2 overflow-y-auto">
            {sessions.map((s) => (
              <div
                key={s.id}
                className="flex items-start justify-between gap-3 rounded-lg border border-border bg-card p-3"
              >
                <div className="min-w-0 space-y-1">
                  <div className="flex items-center gap-2 text-sm font-medium text-foreground">
                    <Smartphone className="h-4 w-4 shrink-0 text-muted-foreground" />
                    {s.deviceName || "Unknown device"}
                    {s.active ? (
                      <Badge className="border-transparent bg-emerald-500/15 text-emerald-500">Active</Badge>
                    ) : (
                      <Badge variant="outline" className="text-muted-foreground">Ended</Badge>
                    )}
                  </div>
                  <div className="flex items-center gap-2 text-xs text-muted-foreground">
                    <MapPin className="h-3.5 w-3.5 shrink-0" /> {s.ipAddress || "Unknown IP"}
                  </div>
                  <div className="text-xs text-muted-foreground">
                    Started {when(s.startedAt)} · last seen {when(s.lastSeenAt)}
                  </div>
                </div>
                <div className="flex shrink-0 flex-col items-stretch gap-1.5">
                  {s.active && (
                    <Button
                      variant="destructive"
                      size="sm"
                      className="gap-1.5"
                      disabled={busy?.endsWith(s.sessionId)}
                      onClick={() => forceLogout(s)}
                    >
                      {busy === `logout:${s.sessionId}` ? (
                        <Loader2 className="h-3.5 w-3.5 animate-spin" />
                      ) : (
                        <LogOut className="h-3.5 w-3.5" />
                      )}
                      Force logout
                    </Button>
                  )}
                  <Button
                    variant="outline"
                    size="sm"
                    className="gap-1.5"
                    title="Sign this device out and delete the session record so the user can log in again"
                    disabled={busy?.endsWith(s.sessionId)}
                    onClick={() => clearSession(s)}
                  >
                    {busy === `clear:${s.sessionId}` ? (
                      <Loader2 className="h-3.5 w-3.5 animate-spin" />
                    ) : (
                      <Eraser className="h-3.5 w-3.5" />
                    )}
                    Clear
                  </Button>
                </div>
              </div>
            ))}
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
}
