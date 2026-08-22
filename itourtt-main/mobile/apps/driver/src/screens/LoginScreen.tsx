import React, { useState } from 'react';
import {
  View,
  Text,
  StyleSheet,
  KeyboardAvoidingView,
  Platform,
  Alert,
} from 'react-native';
import { useAuthStore, validateRole, getColors, typography, spacing, useT } from '@itour/shared';
import { Button, Input } from '@itour/ui';

export function LoginScreen() {
  const colors = getColors();
  const t = useT();
  const { login, isLoading, error } = useAuthStore();
  const [identifier, setIdentifier] = useState('');
  const [password, setPassword] = useState('');

  const handleLogin = async () => {
    if (!identifier.trim() || !password.trim()) return;

    try {
      const user = await login({ identifier: identifier.trim(), password });
      if (!validateRole(user, ['DRIVER'])) {
        Alert.alert(t('common.error'), t('auth.invalidRole'));
        useAuthStore.getState().logout();
      }
    } catch {
      // Error is handled by the store
    }
  };

  return (
    <KeyboardAvoidingView
      style={[styles.container, { backgroundColor: colors.background }]}
      behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
    >
      <View style={styles.content}>
        <View style={styles.header}>
          <Text style={[typography.h1, { color: colors.foreground }]}>iTour</Text>
          <Text style={[typography.h4, { color: colors.mutedForeground, marginTop: spacing[1] }]}>
            Driver App
          </Text>
        </View>

        <View style={styles.form}>
          <Input
            label={t('auth.identifier')}
            value={identifier}
            onChangeText={setIdentifier}
            placeholder="email@example.com"
            autoCapitalize="none"
            keyboardType="email-address"
            returnKeyType="next"
          />

          <Input
            label={t('auth.password')}
            value={password}
            onChangeText={setPassword}
            placeholder="********"
            secureTextEntry
            returnKeyType="done"
            onSubmitEditing={handleLogin}
          />

          {error && (
            <Text style={[typography.caption, { color: colors.destructive, marginBottom: spacing[3] }]}>
              {error}
            </Text>
          )}

          <Button
            title={t('auth.login')}
            onPress={handleLogin}
            loading={isLoading}
            disabled={!identifier.trim() || !password.trim()}
            size="lg"
          />
        </View>
      </View>
    </KeyboardAvoidingView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
  },
  content: {
    flex: 1,
    justifyContent: 'center',
    paddingHorizontal: spacing[6],
  },
  header: {
    alignItems: 'center',
    marginBottom: spacing[10],
  },
  form: {
    width: '100%',
  },
});
