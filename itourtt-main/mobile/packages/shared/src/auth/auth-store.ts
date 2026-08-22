import { create } from 'zustand';
import api from '../api/client';
import { secureStorage } from './secure-storage';
import type { AuthUser, AuthResponse, LoginPayload, UserRole } from '../types';

interface AuthState {
  user: AuthUser | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  error: string | null;
  login: (payload: LoginPayload) => Promise<AuthUser>;
  logout: () => Promise<void>;
  hydrate: () => Promise<void>;
}

export const useAuthStore = create<AuthState>((set) => ({
  user: null,
  isAuthenticated: false,
  isLoading: false,
  error: null,

  login: async (payload: LoginPayload) => {
    set({ isLoading: true, error: null });
    try {
      const { data } = await api.post<AuthResponse>('/auth/login', payload);
      await secureStorage.setTokens(data.accessToken, data.refreshToken);
      await secureStorage.setUser(JSON.stringify(data.user));
      set({ user: data.user, isAuthenticated: true, isLoading: false });
      return data.user;
    } catch (err: unknown) {
      const message =
        (err as { response?: { data?: { message?: string } } })?.response?.data?.message ||
        'Login failed';
      set({ error: message, isLoading: false });
      throw err;
    }
  },

  logout: async () => {
    // Unregister device token before clearing auth
    try {
      const { unregisterDeviceToken } = await import('../native/push-notifications');
      await unregisterDeviceToken();
    } catch {
      // Ignore - push module may not be available
    }
    await secureStorage.clearAll();
    set({ user: null, isAuthenticated: false, error: null });
  },

  hydrate: async () => {
    const token = await secureStorage.getAccessToken();
    const userStr = await secureStorage.getUser();
    if (token && userStr) {
      try {
        const user = JSON.parse(userStr) as AuthUser;
        set({ user, isAuthenticated: true });
      } catch {
        set({ user: null, isAuthenticated: false });
      }
    }
  },
}));

/** Validate that the logged-in user has one of the allowed roles */
export function validateRole(user: AuthUser, allowedRoles: UserRole[]): boolean {
  return allowedRoles.includes(user.role);
}
