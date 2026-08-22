import React from 'react';
import { View } from 'react-native';
import { SkeletonJobCard } from './SkeletonJobCard';

interface SkeletonListProps {
  count?: number;
}

export function SkeletonList({ count = 5 }: SkeletonListProps) {
  return (
    <View>
      {Array.from({ length: count }).map((_, i) => (
        <SkeletonJobCard key={i} />
      ))}
    </View>
  );
}
