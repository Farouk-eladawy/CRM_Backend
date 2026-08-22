'use client';

import { create } from 'zustand';
import api from '@/lib/api';

interface CompanyState {
  logoUrl: string | null;
  faviconUrl: string | null;
  companyName: string;
  isLoaded: boolean;
  isLoading: boolean;
  loadCompanySettings: () => Promise<void>;
}

/**
 * Converts a stored logo/favicon URL or path to a usable URL.
 * Stored values may be a relative path (/uploads/x.jpg) or an absolute URL
 * (http://localhost:3001/uploads/x.jpg from old saves). In production nginx
 * serves /uploads/ at the root domain, so we use the path directly.
 * In development we need the full localhost backend URL.
 */
function toUploadUrl(urlOrPath: string | null): string | null {
  if (!urlOrPath) return null;
  let p = urlOrPath;
  if (p.startsWith('http://') || p.startsWith('https://')) {
    try { p = new URL(p).pathname; } catch { return null; }
  }
  if (!p) return null;
  if (process.env.NODE_ENV === 'development') {
    return `http://localhost:3001${p}`;
  }
  return p; // nginx proxies /uploads/ directly to backend in production
}

export const useCompanyStore = create<CompanyState>((set, get) => ({
  logoUrl: null,
  faviconUrl: null,
  companyName: 'iTour TT',
  isLoaded: false,
  isLoading: false,

  loadCompanySettings: async () => {
    if (get().isLoading || get().isLoaded) return;
    set({ isLoading: true });
    try {
      const { data } = await api.get('/settings/company');
      set({
        logoUrl: toUploadUrl(data.logoUrl),
        faviconUrl: toUploadUrl(data.faviconUrl),
        companyName: data.companyName || 'iTour TT',
        isLoaded: true,
        isLoading: false,
      });
    } catch {
      set({ isLoading: false, isLoaded: true });
    }
  },
}));
