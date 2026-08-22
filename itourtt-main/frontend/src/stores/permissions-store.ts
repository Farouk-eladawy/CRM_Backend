'use client';

import { create } from 'zustand';
import api from '@/lib/api';
import { getAncestorKeys } from '@/lib/permission-registry';

interface PermissionsState {
  permissions: Set<string>;
  isLoaded: boolean;
  isLoading: boolean;
  loadPermissions: () => Promise<void>;
  has: (key: string) => boolean;
  hasAny: (...keys: string[]) => boolean;
  hasAll: (...keys: string[]) => boolean;
  clear: () => void;
}

export const usePermissionsStore = create<PermissionsState>((set, get) => ({
  permissions: new Set<string>(),
  isLoaded: false,
  isLoading: false,

  loadPermissions: async () => {
    if (get().isLoading) return;
    set({ isLoading: true });
    try {
      const { data } = await api.get<{ permissionKeys: string[] }>(
        '/permissions/mine',
      );
      set({
        permissions: new Set(data.permissionKeys),
        isLoaded: true,
        isLoading: false,
      });
    } catch {
      set({ isLoading: false });
    }
  },

  has: (key: string): boolean => {
    const { permissions } = get();
    if (permissions.size === 0) return false;

    // Check the key itself
    if (!permissions.has(key)) return false;

    // Check all ancestors exist too (hierarchical rule)
    const ancestors = getAncestorKeys(key);
    return ancestors.every((a) => permissions.has(a));
  },

  hasAny: (...keys: string[]): boolean => {
    const { has } = get();
    return keys.some((k) => has(k));
  },

  hasAll: (...keys: string[]): boolean => {
    const { has } = get();
    return keys.every((k) => has(k));
  },

  clear: () => {
    set({ permissions: new Set(), isLoaded: false });
  },
}));
