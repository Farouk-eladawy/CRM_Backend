import { create } from 'zustand';
import { Appearance, ColorSchemeName } from 'react-native';

type ThemeMode = 'light' | 'dark' | 'system';

interface ThemeState {
  mode: ThemeMode;
  resolvedMode: 'light' | 'dark';
  setMode: (mode: ThemeMode) => Promise<void>;
  hydrate: () => Promise<void>;
}

function resolveMode(mode: ThemeMode): 'light' | 'dark' {
  if (mode === 'system') {
    return Appearance.getColorScheme() === 'dark' ? 'dark' : 'light';
  }
  return mode;
}

export const useThemeStore = create<ThemeState>((set, get) => ({
  mode: 'system',
  resolvedMode: resolveMode('system'),

  setMode: async (mode: ThemeMode) => {
    set({ mode, resolvedMode: resolveMode(mode) });
    try {
      // Store preference - reuse the encrypted storage pattern
      const EncryptedStorage = require('react-native-encrypted-storage').default;
      await EncryptedStorage.setItem('theme_mode', mode);
    } catch {}
  },

  hydrate: async () => {
    try {
      const EncryptedStorage = require('react-native-encrypted-storage').default;
      const stored = await EncryptedStorage.getItem('theme_mode');
      if (stored && (stored === 'light' || stored === 'dark' || stored === 'system')) {
        set({ mode: stored as ThemeMode, resolvedMode: resolveMode(stored as ThemeMode) });
      }
    } catch {}

    // Listen for system theme changes
    const subscription = Appearance.addChangeListener(({ colorScheme }) => {
      const state = get();
      if (state.mode === 'system') {
        set({ resolvedMode: colorScheme === 'dark' ? 'dark' : 'light' });
      }
    });
  },
}));
