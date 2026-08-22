'use client';

import { useEffect, useState } from 'react';
import { usePathname } from 'next/navigation';
import { ShieldX, AlertTriangle, X } from 'lucide-react';
import { useLicense } from '@/hooks/use-license';

const ALLOWED_PATHS = ['/dashboard/company'];

function getWarningLevel(days: number): 90 | 60 | 30 | null {
  if (days <= 30) return 30;
  if (days <= 60) return 60;
  if (days <= 90) return 90;
  return null;
}

const LEVEL_STYLE = {
  30: {
    border: 'border-red-500/40',
    bg: 'bg-red-950/60',
    icon: 'text-red-400',
    badge: 'bg-red-500/20 text-red-300',
    title: 'text-red-300',
    btn: 'bg-red-600 hover:bg-red-700 text-white',
  },
  60: {
    border: 'border-orange-500/40',
    bg: 'bg-orange-950/60',
    icon: 'text-orange-400',
    badge: 'bg-orange-500/20 text-orange-300',
    title: 'text-orange-300',
    btn: 'bg-orange-600 hover:bg-orange-700 text-white',
  },
  90: {
    border: 'border-yellow-500/40',
    bg: 'bg-yellow-950/60',
    icon: 'text-yellow-400',
    badge: 'bg-yellow-500/20 text-yellow-300',
    title: 'text-yellow-300',
    btn: 'bg-yellow-600 hover:bg-yellow-700 text-white',
  },
} as const;

export function LicenseGate({ children }: { children: React.ReactNode }) {
  const { status, loading } = useLicense();
  const pathname = usePathname();
  const [warningDismissed, setWarningDismissed] = useState(false);

  const warningLevel = status?.valid && status.daysRemaining !== null
    ? getWarningLevel(status.daysRemaining)
    : null;

  // Restore per-level dismissal from sessionStorage
  useEffect(() => {
    if (!warningLevel) return;
    const key = `license_warn_dismissed_${warningLevel}`;
    if (sessionStorage.getItem(key) === '1') {
      setWarningDismissed(true);
    } else {
      setWarningDismissed(false);
    }
  }, [warningLevel]);

  // Dismiss via Escape key
  useEffect(() => {
    if (!warningLevel || warningDismissed) return;
    const handler = (e: KeyboardEvent) => {
      if (e.key === 'Escape') dismiss();
    };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  });

  function dismiss() {
    if (!warningLevel) return;
    sessionStorage.setItem(`license_warn_dismissed_${warningLevel}`, '1');
    setWarningDismissed(true);
  }

  // Fail-soft: an invalid / unconfigured license WARNS but never hard-blocks the app,
  // so a config gap or transient check failure can't take production down. Dismissible per session.
  const invalid = !!(status && !status.valid);
  const [invalidDismissed, setInvalidDismissed] = useState(false);
  useEffect(() => {
    if (!invalid) { setInvalidDismissed(false); return; }
    setInvalidDismissed(sessionStorage.getItem('license_invalid_dismissed') === '1');
  }, [invalid]);
  function dismissInvalid() {
    sessionStorage.setItem('license_invalid_dismissed', '1');
    setInvalidDismissed(true);
  }

  // Always allow the Company settings page so admin can enter the license key
  if (ALLOWED_PATHS.includes(pathname)) {
    return <>{children}</>;
  }

  if (loading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-background">
        <div className="h-6 w-6 animate-spin rounded-full border-2 border-muted-foreground/20 border-t-foreground" />
      </div>
    );
  }

  const showWarning = warningLevel !== null && !warningDismissed && !ALLOWED_PATHS.includes(pathname);
  const showInvalid = invalid && !invalidDismissed && !ALLOWED_PATHS.includes(pathname);

  return (
    <>
      {children}
      {showInvalid && (
        <div className="fixed bottom-4 right-4 z-[9998] w-full max-w-sm rounded-xl border border-destructive/40 bg-card p-4 shadow-2xl">
          <div className="flex items-start gap-3">
            <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-destructive/10">
              <ShieldX className="h-5 w-5 text-destructive" />
            </div>
            <div className="min-w-0 flex-1">
              <div className="flex items-center justify-between gap-2">
                <h2 className="text-sm font-bold text-foreground">License not active</h2>
                <button
                  onClick={dismissInvalid}
                  className="rounded-lg p-1 text-muted-foreground hover:bg-white/10 hover:text-foreground transition-colors"
                  aria-label="Dismiss"
                >
                  <X className="h-4 w-4" />
                </button>
              </div>
              <p className="mt-1 text-xs text-muted-foreground">
                {status?.message || 'Your software license is not configured or could not be verified.'} The
                app stays usable — please reactivate to clear this notice.
              </p>
              <div className="mt-3 flex items-center gap-2">
                <a
                  href="/dashboard/company"
                  className="rounded-lg bg-primary px-3 py-1.5 text-xs font-medium text-primary-foreground hover:bg-primary/90 transition-colors"
                >
                  Activate License
                </a>
                <a
                  href="https://wa.me/+201002805139"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-xs text-muted-foreground underline hover:text-foreground transition-colors"
                >
                  Contact Mohamed Gouda
                </a>
              </div>
            </div>
          </div>
        </div>
      )}
      {showWarning && (() => {
        const level = warningLevel!;
        const days = status!.daysRemaining!;
        const s = LEVEL_STYLE[level];
        const months = level === 90 ? '3 months' : level === 60 ? '2 months' : '1 month';
        return (
          <div className="fixed inset-0 z-[9999] flex items-center justify-center bg-black/60 backdrop-blur-sm p-4">
            <div className={`relative w-full max-w-md rounded-2xl border ${s.border} ${s.bg} backdrop-blur-md p-6 shadow-2xl`}>
              <button
                onClick={dismiss}
                className="absolute right-4 top-4 rounded-lg p-1 text-muted-foreground hover:bg-white/10 hover:text-foreground transition-colors"
                aria-label="Dismiss"
              >
                <X className="h-4 w-4" />
              </button>

              <div className={`mb-4 flex h-12 w-12 items-center justify-center rounded-full bg-white/10`}>
                <AlertTriangle className={`h-6 w-6 ${s.icon}`} />
              </div>

              <span className={`inline-block rounded-full px-2.5 py-0.5 text-xs font-semibold ${s.badge} mb-3`}>
                License Expiry Warning
              </span>

              <h2 className={`text-lg font-bold ${s.title} mb-1`}>
                License expires in {days} day{days !== 1 ? 's' : ''}
              </h2>
              <p className="text-sm text-muted-foreground mb-5">
                Your iTourTT license will expire within {months}. Please renew before it expires to avoid service interruption.
              </p>

              <div className="flex items-center gap-3">
                <a
                  href="https://wa.me/+201002805139"
                  target="_blank"
                  rel="noopener noreferrer"
                  className={`flex-1 rounded-lg px-4 py-2 text-center text-sm font-medium transition-colors ${s.btn}`}
                >
                  Contact to Renew
                </a>
                <button
                  onClick={dismiss}
                  className="flex-1 rounded-lg border border-border px-4 py-2 text-sm text-muted-foreground hover:bg-white/10 hover:text-foreground transition-colors"
                >
                  Dismiss
                </button>
              </div>

              <p className="mt-3 text-center text-[11px] text-muted-foreground">
                Press <kbd className="rounded border border-border bg-white/10 px-1 py-0.5 font-mono text-[10px]">Esc</kbd> to dismiss · Reappears each session
              </p>
            </div>
          </div>
        );
      })()}
    </>
  );
}
