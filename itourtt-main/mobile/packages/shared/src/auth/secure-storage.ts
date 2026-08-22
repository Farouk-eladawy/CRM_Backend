import EncryptedStorage from 'react-native-encrypted-storage';

const KEYS = {
  ACCESS_TOKEN: 'accessToken',
  REFRESH_TOKEN: 'refreshToken',
  USER: 'user',
} as const;

export const secureStorage = {
  async getAccessToken(): Promise<string | null> {
    return EncryptedStorage.getItem(KEYS.ACCESS_TOKEN);
  },

  async setAccessToken(token: string): Promise<void> {
    await EncryptedStorage.setItem(KEYS.ACCESS_TOKEN, token);
  },

  async getRefreshToken(): Promise<string | null> {
    return EncryptedStorage.getItem(KEYS.REFRESH_TOKEN);
  },

  async setRefreshToken(token: string): Promise<void> {
    await EncryptedStorage.setItem(KEYS.REFRESH_TOKEN, token);
  },

  async getUser(): Promise<string | null> {
    return EncryptedStorage.getItem(KEYS.USER);
  },

  async setUser(user: string): Promise<void> {
    await EncryptedStorage.setItem(KEYS.USER, user);
  },

  async setTokens(accessToken: string, refreshToken: string): Promise<void> {
    await Promise.all([
      EncryptedStorage.setItem(KEYS.ACCESS_TOKEN, accessToken),
      EncryptedStorage.setItem(KEYS.REFRESH_TOKEN, refreshToken),
    ]);
  },

  async clearAll(): Promise<void> {
    await Promise.all([
      EncryptedStorage.removeItem(KEYS.ACCESS_TOKEN),
      EncryptedStorage.removeItem(KEYS.REFRESH_TOKEN),
      EncryptedStorage.removeItem(KEYS.USER),
    ]);
  },
};
