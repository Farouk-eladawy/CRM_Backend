'use client';

import { useEffect, useState } from 'react';
import api from '@/lib/api';

interface LicenseStatus {
  valid: boolean;
  expiresAt: string | null;
  daysRemaining: number | null;
  message: string;
}

const MAX_RETRIES = 5;
const RETRY_DELAY = 2000;

export function useLicense() {
  const [status, setStatus] = useState<LicenseStatus | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    let attempt = 0;

    async function check() {
      while (attempt < MAX_RETRIES && !cancelled) {
        try {
          // api interceptor handles 401 → refresh token automatically
          const { data } = await api.get('/settings/license-status');
          if (!cancelled) {
            setStatus(data);
            setLoading(false);
          }
          return;
        } catch {
          // Network error, 5xx, or auth failure after refresh — retry
          attempt++;
          if (attempt < MAX_RETRIES) {
            await new Promise((r) => setTimeout(r, RETRY_DELAY));
          }
        }
      }
      // All retries exhausted
      if (!cancelled) {
        setStatus({ valid: false, expiresAt: null, daysRemaining: null, message: 'Unable to verify license' });
        setLoading(false);
      }
    }

    check();
    return () => { cancelled = true; };
  }, []);

  return { status, loading };
}
