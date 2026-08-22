'use client';

import { create } from 'zustand';
import api from '@/lib/api';
import type { AuthUser, AuthResponse, LoginPayload } from '@/types';
import { usePermissionsStore } from './permissions-store';

interface AuthState {
  user: AuthUser | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  error: string | null;
  isAccountLocked: boolean;
  twoFactorChallenge: string | null;
  login: (payload: LoginPayload) => Promise<void>;
  verifyTwoFactor: (code: string) => Promise<void>;
  cancelTwoFactor: () => void;
  logout: () => Promise<void>;
  hydrate: () => void;
}

type LoginResult =
  | AuthResponse
  | { twoFactorRequired: true; challengeToken: string };

export const useAuthStore = create<AuthState>((set) => ({
  user: null,
  isAuthenticated: false,
  isLoading: false,
  error: null,
  isAccountLocked: false,
  twoFactorChallenge: null,

  login: async (payload: LoginPayload) => {
    set({ isLoading: true, error: null, isAccountLocked: false, twoFactorChallenge: null });
    try {
      const { data } = await api.post<LoginResult>('/auth/login', payload);
      // 2FA step-up: the server withheld a session and returned a challenge.
      if ('twoFactorRequired' in data && data.twoFactorRequired) {
        set({ twoFactorChallenge: data.challengeToken, isLoading: false });
        return;
      }
      const session = data as AuthResponse;
      localStorage.setItem('accessToken', session.accessToken);
      localStorage.setItem('refreshToken', session.refreshToken);
      localStorage.setItem('user', JSON.stringify(session.user));
      set({ user: session.user, isAuthenticated: true, isLoading: false });
      // Load granular permissions after successful login
      usePermissionsStore.getState().loadPermissions();
    } catch (err: unknown) {
      const status = (err as { response?: { status?: number } })?.response?.status;
      const message =
        (err as { response?: { data?: { message?: string } } })?.response?.data?.message ||
        'Login failed';

      if (status === 423) {
        // Account locked due to concurrent login
        set({ error: message, isLoading: false, isAccountLocked: true });
      } else {
        set({ error: message, isLoading: false, isAccountLocked: false });
      }
      throw err;
    }
  },

  // Login step 2: exchange the stored challenge + a TOTP/recovery code for a session.
  verifyTwoFactor: async (code: string) => {
    const challengeToken = useAuthStore.getState().twoFactorChallenge;
    if (!challengeToken) throw new Error('No 2FA challenge in progress');
    set({ isLoading: true, error: null });
    try {
      const { data } = await api.post<AuthResponse>('/auth/2fa/verify', { challengeToken, code });
      localStorage.setItem('accessToken', data.accessToken);
      localStorage.setItem('refreshToken', data.refreshToken);
      localStorage.setItem('user', JSON.stringify(data.user));
      set({ user: data.user, isAuthenticated: true, isLoading: false, twoFactorChallenge: null });
      usePermissionsStore.getState().loadPermissions();
    } catch (err: unknown) {
      const message =
        (err as { response?: { data?: { message?: string } } })?.response?.data?.message ||
        'Verification failed';
      set({ error: message, isLoading: false });
      throw err;
    }
  },

  cancelTwoFactor: () => set({ twoFactorChallenge: null, error: null }),

  logout: async () => {
    // Notify the server to clear the session (allows clean re-login)
    try {
      await api.post('/auth/logout');
    } catch {
      // Ignore — clear locally regardless
    }
    localStorage.removeItem('accessToken');
    localStorage.removeItem('refreshToken');
    localStorage.removeItem('user');
    usePermissionsStore.getState().clear();
    set({ user: null, isAuthenticated: false, error: null, isAccountLocked: false });
    window.location.href = '/login';
  },

  hydrate: () => {
    if (typeof window === 'undefined') return;
    const token = localStorage.getItem('accessToken');
    const userStr = localStorage.getItem('user');
    if (token && userStr) {
      try {
        const user = JSON.parse(userStr) as AuthUser;
        set({ user, isAuthenticated: true });
        // Load granular permissions on hydrate
        usePermissionsStore.getState().loadPermissions();
      } catch {
        set({ user: null, isAuthenticated: false });
      }
    }
  },
}));
