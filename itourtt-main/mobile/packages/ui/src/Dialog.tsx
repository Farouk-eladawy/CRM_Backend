import React from 'react';
import { View, Text, Modal, StyleSheet, TouchableOpacity, Pressable } from 'react-native';
import { getColors, spacing, borderRadius, typography } from '@itour/shared';

interface DialogProps {
  visible: boolean;
  title: string;
  message?: string;
  onClose: () => void;
  children?: React.ReactNode;
  actions?: React.ReactNode;
}

export function Dialog({ visible, title, message, onClose, children, actions }: DialogProps) {
  const colors = getColors();

  return (
    <Modal visible={visible} transparent animationType="fade" onRequestClose={onClose}>
      <Pressable style={styles.overlay} onPress={onClose}>
        <Pressable
          style={[styles.content, { backgroundColor: colors.card }]}
          onPress={(e) => e.stopPropagation()}
        >
          <Text style={[typography.h4, { color: colors.foreground }]}>{title}</Text>
          {message && (
            <Text
              style={[typography.bodySm, { color: colors.mutedForeground, marginTop: spacing[2] }]}
            >
              {message}
            </Text>
          )}
          {children && <View style={styles.body}>{children}</View>}
          {actions && <View style={styles.actions}>{actions}</View>}
        </Pressable>
      </Pressable>
    </Modal>
  );
}

const styles = StyleSheet.create({
  overlay: {
    flex: 1,
    backgroundColor: 'rgba(0,0,0,0.5)',
    justifyContent: 'center',
    alignItems: 'center',
    padding: spacing[6],
  },
  content: {
    width: '100%',
    borderRadius: borderRadius['2xl'],
    padding: spacing[6],
  },
  body: {
    marginTop: spacing[4],
  },
  actions: {
    flexDirection: 'row',
    justifyContent: 'flex-end',
    gap: spacing[3],
    marginTop: spacing[6],
  },
});
