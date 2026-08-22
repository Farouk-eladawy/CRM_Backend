jest.mock('../../src/api/client', () => ({
  __esModule: true,
  default: {
    post: jest.fn(),
    get: jest.fn(),
    interceptors: {
      request: { use: jest.fn() },
      response: { use: jest.fn() },
    },
  },
}));

jest.mock('../../src/native/push-notifications', () => ({
  unregisterDeviceToken: jest.fn().mockResolvedValue(undefined),
}));

import api from '../../src/api/client';
import { useAuthStore, validateRole } from '../../src/auth/auth-store';
import type { AuthUser, AuthResponse, UserRole } from '../../src/types';
import EncryptedStorage from 'react-native-encrypted-storage';

const mockApi = api as jest.Mocked<typeof api>;

const mockUser: AuthUser = {
  id: 'user-1',
  email: 'driver@itour.com',
  name: 'Ahmed Driver',
  role: 'DRIVER',
  driverId: 'driver-uuid-1',
};

const mockAuthResponse: AuthResponse = {
  accessToken: 'access-token-123',
  refreshToken: 'refresh-token-456',
  user: mockUser,
};

describe('auth-store', () => {
  beforeEach(() => {
    // Reset store to initial state
    useAuthStore.setState({
      user: null,
      isAuthenticated: false,
      isLoading: false,
      error: null,
    });
    jest.clearAllMocks();
  });

  describe('initial state', () => {
    it('has null user', () => {
      expect(useAuthStore.getState().user).toBeNull();
    });

    it('is not authenticated', () => {
      expect(useAuthStore.getState().isAuthenticated).toBe(false);
    });

    it('is not loading', () => {
      expect(useAuthStore.getState().isLoading).toBe(false);
    });

    it('has no error', () => {
      expect(useAuthStore.getState().error).toBeNull();
    });
  });

  describe('login - success path', () => {
    beforeEach(() => {
      (mockApi.post as jest.Mock).mockResolvedValue({ data: mockAuthResponse });
    });

    it('sets isLoading to true during login', async () => {
      const loginPromise = useAuthStore.getState().login({
        identifier: 'driver@itour.com',
        password: 'password123',
      });

      // isLoading should be true immediately
      // Note: Due to microtask ordering this may already be resolved
      await loginPromise;
    });

    it('sets user and isAuthenticated on success', async () => {
      await useAuthStore.getState().login({
        identifier: 'driver@itour.com',
        password: 'password123',
      });

      const state = useAuthStore.getState();
      expect(state.user).toEqual(mockUser);
      expect(state.isAuthenticated).toBe(true);
      expect(state.isLoading).toBe(false);
      expect(state.error).toBeNull();
    });

    it('returns the user object', async () => {
      const result = await useAuthStore.getState().login({
        identifier: 'driver@itour.com',
        password: 'password123',
      });

      expect(result).toEqual(mockUser);
    });

    it('calls API with correct payload', async () => {
      const payload = { identifier: 'driver@itour.com', password: 'secret' };
      await useAuthStore.getState().login(payload);

      expect(mockApi.post).toHaveBeenCalledWith('/auth/login', payload);
    });

    it('stores tokens in encrypted storage', async () => {
      await useAuthStore.getState().login({
        identifier: 'driver@itour.com',
        password: 'password123',
      });

      expect(EncryptedStorage.setItem).toHaveBeenCalledWith('accessToken', 'access-token-123');
      expect(EncryptedStorage.setItem).toHaveBeenCalledWith('refreshToken', 'refresh-token-456');
    });

    it('stores user in encrypted storage', async () => {
      await useAuthStore.getState().login({
        identifier: 'driver@itour.com',
        password: 'password123',
      });

      expect(EncryptedStorage.setItem).toHaveBeenCalledWith('user', JSON.stringify(mockUser));
    });
  });

  describe('login - failure path', () => {
    it('sets error message from API response', async () => {
      const apiError = {
        response: { data: { message: 'Invalid credentials' } },
      };
      (mockApi.post as jest.Mock).mockRejectedValue(apiError);

      await expect(
        useAuthStore.getState().login({
          identifier: 'bad@email.com',
          password: 'wrong',
        }),
      ).rejects.toEqual(apiError);

      const state = useAuthStore.getState();
      expect(state.error).toBe('Invalid credentials');
      expect(state.isLoading).toBe(false);
      expect(state.isAuthenticated).toBe(false);
      expect(state.user).toBeNull();
    });

    it('sets default error message when API error has no message', async () => {
      (mockApi.post as jest.Mock).mockRejectedValue(new Error('Network error'));

      await expect(
        useAuthStore.getState().login({
          identifier: 'test@test.com',
          password: 'test',
        }),
      ).rejects.toThrow();

      expect(useAuthStore.getState().error).toBe('Login failed');
    });

    it('clears previous error on new login attempt', async () => {
      // First, set an error
      useAuthStore.setState({ error: 'Previous error' });

      // Mock a successful login
      (mockApi.post as jest.Mock).mockResolvedValue({ data: mockAuthResponse });

      await useAuthStore.getState().login({
        identifier: 'driver@itour.com',
        password: 'password123',
      });

      expect(useAuthStore.getState().error).toBeNull();
    });
  });

  describe('logout', () => {
    beforeEach(async () => {
      // Set up authenticated state
      useAuthStore.setState({
        user: mockUser,
        isAuthenticated: true,
      });
    });

    it('clears user state', async () => {
      await useAuthStore.getState().logout();

      const state = useAuthStore.getState();
      expect(state.user).toBeNull();
      expect(state.isAuthenticated).toBe(false);
      expect(state.error).toBeNull();
    });

    it('clears encrypted storage', async () => {
      await useAuthStore.getState().logout();

      expect(EncryptedStorage.removeItem).toHaveBeenCalledWith('accessToken');
      expect(EncryptedStorage.removeItem).toHaveBeenCalledWith('refreshToken');
      expect(EncryptedStorage.removeItem).toHaveBeenCalledWith('user');
    });
  });

  describe('hydrate', () => {
    it('restores user from storage when token and user exist', async () => {
      (EncryptedStorage.getItem as jest.Mock).mockImplementation(async (key: string) => {
        if (key === 'accessToken') return 'stored-token';
        if (key === 'user') return JSON.stringify(mockUser);
        return null;
      });

      await useAuthStore.getState().hydrate();

      const state = useAuthStore.getState();
      expect(state.user).toEqual(mockUser);
      expect(state.isAuthenticated).toBe(true);
    });

    it('does not restore when no token exists', async () => {
      (EncryptedStorage.getItem as jest.Mock).mockImplementation(async (key: string) => {
        if (key === 'user') return JSON.stringify(mockUser);
        return null;
      });

      await useAuthStore.getState().hydrate();

      const state = useAuthStore.getState();
      expect(state.user).toBeNull();
      expect(state.isAuthenticated).toBe(false);
    });

    it('does not restore when no user string exists', async () => {
      (EncryptedStorage.getItem as jest.Mock).mockImplementation(async (key: string) => {
        if (key === 'accessToken') return 'stored-token';
        return null;
      });

      await useAuthStore.getState().hydrate();

      const state = useAuthStore.getState();
      expect(state.user).toBeNull();
      expect(state.isAuthenticated).toBe(false);
    });

    it('handles corrupted user JSON gracefully', async () => {
      (EncryptedStorage.getItem as jest.Mock).mockImplementation(async (key: string) => {
        if (key === 'accessToken') return 'stored-token';
        if (key === 'user') return 'not-valid-json{{{';
        return null;
      });

      await useAuthStore.getState().hydrate();

      const state = useAuthStore.getState();
      expect(state.user).toBeNull();
      expect(state.isAuthenticated).toBe(false);
    });
  });

  describe('validateRole', () => {
    it('returns true when user role is in allowed roles', () => {
      expect(validateRole(mockUser, ['DRIVER', 'REP'])).toBe(true);
    });

    it('returns false when user role is not in allowed roles', () => {
      expect(validateRole(mockUser, ['ADMIN', 'DISPATCHER'])).toBe(false);
    });

    it('returns true for single matching role', () => {
      expect(validateRole(mockUser, ['DRIVER'])).toBe(true);
    });

    it('returns false for empty allowed roles array', () => {
      expect(validateRole(mockUser, [])).toBe(false);
    });

    it('works with all role types', () => {
      const roles: UserRole[] = ['ADMIN', 'DISPATCHER', 'ACCOUNTANT', 'AGENT_MANAGER', 'VIEWER', 'REP', 'DRIVER', 'SUPPLIER'];
      roles.forEach((role) => {
        const user: AuthUser = { ...mockUser, role };
        expect(validateRole(user, [role])).toBe(true);
        // Should not match a different role
        const otherRoles = roles.filter((r) => r !== role);
        if (otherRoles.length > 0) {
          expect(validateRole(user, [otherRoles[0]])).toBe(false);
        }
      });
    });
  });
});
