'use client';

import { usePermissionsStore } from '@/stores/permissions-store';

/**
 * Check if the current user has a specific permission.
 */
export function usePermission(key: string): boolean {
  return usePermissionsStore((s) => s.has(key));
}

/**
 * Check multiple permissions at once.
 * Returns a record of key → boolean.
 */
export function usePermissions(
  ...keys: string[]
): Record<string, boolean> {
  return usePermissionsStore((s) => {
    const result: Record<string, boolean> = {};
    for (const k of keys) result[k] = s.has(k);
    return result;
  });
}
