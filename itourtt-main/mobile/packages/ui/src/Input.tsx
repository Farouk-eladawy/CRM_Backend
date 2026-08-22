import React, { forwardRef } from 'react';
import {
  TextInput,
  View,
  Text,
  StyleSheet,
  type TextInputProps,
  type ViewStyle,
} from 'react-native';
import { getColors, borderRadius, spacing, typography } from '@itour/shared';

interface InputProps extends TextInputProps {
  label?: string;
  error?: string;
  containerStyle?: ViewStyle;
}

export const Input = forwardRef<TextInput, InputProps>(
  ({ label, error, containerStyle, style, ...props }, ref) => {
    const colors = getColors();

    return (
      <View style={[styles.container, containerStyle]}>
        {label && (
          <Text style={[typography.label, { color: colors.foreground, marginBottom: spacing[1] }]}>
            {label}
          </Text>
        )}
        <TextInput
          ref={ref}
          style={[
            styles.input,
            typography.body,
            {
              backgroundColor: colors.background,
              borderColor: error ? colors.destructive : colors.input,
              color: colors.foreground,
            },
            style,
          ]}
          placeholderTextColor={colors.mutedForeground}
          {...props}
        />
        {error && (
          <Text style={[typography.caption, { color: colors.destructive, marginTop: spacing[0.5] }]}>
            {error}
          </Text>
        )}
      </View>
    );
  },
);

Input.displayName = 'Input';

const styles = StyleSheet.create({
  container: {
    marginBottom: spacing[4],
  },
  input: {
    height: 44,
    borderWidth: 1,
    borderRadius: borderRadius.lg,
    paddingHorizontal: spacing[3],
  },
});
