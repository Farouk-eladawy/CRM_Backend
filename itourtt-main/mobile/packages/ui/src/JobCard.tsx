import React from 'react';
import { View, Text, StyleSheet, TouchableOpacity } from 'react-native';
import {
  getColors,
  getStatusColors,
  spacing,
  borderRadius,
  typography,
  formatTime,
  getRouteLabel,
  type PortalJob,
  type JobStatus,
} from '@itour/shared';
import { ServiceTypeBadge } from './ServiceTypeBadge';
import { StatusBadge } from './StatusBadge';

interface JobCardProps {
  job: PortalJob;
  portalStatus?: string;
  onPress?: () => void;
  rightContent?: React.ReactNode;
  bottomContent?: React.ReactNode;
}

export function JobCard({ job, portalStatus, onPress, rightContent, bottomContent }: JobCardProps) {
  const colors = getColors();
  const statusColors = getStatusColors();
  const displayStatus = (portalStatus || job.status) as JobStatus;
  const statusColor = statusColors[displayStatus] || statusColors.PENDING;

  const timeDisplay = job.flight?.arrivalTime
    ? formatTime(job.flight.arrivalTime)
    : job.pickUpTime
      ? formatTime(job.pickUpTime)
      : null;

  return (
    <TouchableOpacity
      onPress={onPress}
      disabled={!onPress}
      activeOpacity={onPress ? 0.7 : 1}
      style={[
        styles.card,
        {
          backgroundColor: colors.card,
          borderColor: colors.border,
          borderLeftColor: statusColor.text,
          borderLeftWidth: 3,
        },
      ]}
    >
      <View style={styles.header}>
        <View style={styles.headerLeft}>
          <ServiceTypeBadge serviceType={job.serviceType} />
          <Text style={[typography.captionMedium, { color: colors.mutedForeground, marginLeft: spacing[2] }]}>
            {job.internalRef}
          </Text>
        </View>
        <StatusBadge status={displayStatus} />
      </View>

      <View style={styles.body}>
        <Text style={[typography.bodySmMedium, { color: colors.foreground }]} numberOfLines={1}>
          {getRouteLabel(job)}
        </Text>

        <View style={styles.meta}>
          {timeDisplay && (
            <Text style={[typography.caption, { color: colors.mutedForeground }]}>
              {timeDisplay}
            </Text>
          )}
          <Text style={[typography.caption, { color: colors.mutedForeground }]}>
            {job.paxCount} pax
          </Text>
          {job.flight?.flightNo && (
            <Text style={[typography.caption, { color: colors.mutedForeground }]}>
              {job.flight.flightNo}
            </Text>
          )}
        </View>

        {job.clientName && (
          <Text style={[typography.caption, { color: colors.mutedForeground, marginTop: spacing[1] }]}>
            {job.clientName}
          </Text>
        )}
      </View>

      {rightContent && <View style={styles.right}>{rightContent}</View>}
      {bottomContent && <View style={styles.bottom}>{bottomContent}</View>}
    </TouchableOpacity>
  );
}

const styles = StyleSheet.create({
  card: {
    borderWidth: 1,
    borderRadius: borderRadius.xl,
    padding: spacing[3],
    marginHorizontal: spacing[4],
    marginVertical: spacing[1],
  },
  header: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: spacing[2],
  },
  headerLeft: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  body: {},
  meta: {
    flexDirection: 'row',
    gap: spacing[3],
    marginTop: spacing[1],
  },
  right: {
    marginTop: spacing[2],
  },
  bottom: {
    marginTop: spacing[3],
    paddingTop: spacing[3],
    borderTopWidth: StyleSheet.hairlineWidth,
    borderTopColor: 'rgba(0,0,0,0.1)',
  },
});
