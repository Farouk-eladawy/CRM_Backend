import React from 'react';
import { getStatusColors, t, type JobStatus, type PortalJobStatus } from '@itour/shared';
import { Badge } from './Badge';

interface StatusBadgeProps {
  status: JobStatus | PortalJobStatus;
}

export function StatusBadge({ status }: StatusBadgeProps) {
  const colors = getStatusColors();
  const color = colors[status as keyof typeof colors] || colors.PENDING;

  return (
    <Badge
      label={t(`status.${status}`)}
      backgroundColor={color.bg}
      textColor={color.text}
      borderColor={color.border}
    />
  );
}
