import api from '../client';
import type { AuthResponse } from '../../types';

export const authApi = {
  login(identifier: string, password: string) {
    return api.post<AuthResponse>('/auth/login', { identifier, password });
  },

  refresh(refreshToken: string) {
    return api.post<AuthResponse>('/auth/refresh', { refreshToken });
  },

  registerDeviceToken(token: string, platform: 'ios' | 'android') {
    return api.post('/auth/device-token', { token, platform });
  },

  unregisterDeviceToken(token: string) {
    return api.delete('/auth/device-token', { data: { token } });
  },
};
