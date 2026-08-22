import React from 'react';
import { serviceTypeColors, t, type ServiceType } from '@itour/shared';
import { Badge } from './Badge';

interface ServiceTypeBadgeProps {
  serviceType: ServiceType;
}

export function ServiceTypeBadge({ serviceType }: ServiceTypeBadgeProps) {
  const color = serviceTypeColors[serviceType] || { bg: '#F4F4F5', text: '#71717A' };

  return (
    <Badge
      label={t(`serviceType.${serviceType}`)}
      backgroundColor={color.bg}
      textColor={color.text}
    />
  );
}
