'use client';

import React from 'react';
import { usePermission } from '@/hooks/use-permission';
import { usePermissionsStore } from '@/stores/permissions-store';

interface PermissionGateProps {
  /** The permission key to check, e.g. "agents.addButton" */
  permission: string;
  /** 'disable' = grey out (default), 'hide' = remove from DOM */
  mode?: 'disable' | 'hide';
  children: React.ReactNode;
  /** Optional fallback when hidden */
  fallback?: React.ReactNode;
}

export function PermissionGate({
  permission,
  mode = 'disable',
  children,
  fallback,
}: PermissionGateProps) {
  const allowed = usePermission(permission);
  const isLoaded = usePermissionsStore((s) => s.isLoaded);

  // While permissions haven't loaded yet, show children normally
  if (!isLoaded) return <>{children}</>;

  if (allowed) return <>{children}</>;

  if (mode === 'hide') return <>{fallback ?? null}</>;

  // 'disable' mode: render children but greyed out and non-interactive
  return (
    <div
      className="pointer-events-none opacity-40 select-none"
      aria-disabled="true"
      title="You do not have permission for this action"
    >
      {children}
    </div>
  );
}
