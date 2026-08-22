module.exports = {
  preset: 'react-native',
  displayName: 'shared',
  rootDir: '.',
  testMatch: ['<rootDir>/**/__tests__/**/*.test.{ts,tsx}'],
  moduleFileExtensions: ['ts', 'tsx', 'js', 'jsx'],
  transformIgnorePatterns: [
    'node_modules/(?!(react-native|@react-native|react-native-encrypted-storage|@react-native-community)/)',
  ],
  setupFiles: ['<rootDir>/__tests__/setup.ts'],
  moduleNameMapper: {
    'react-native-encrypted-storage': '<rootDir>/__tests__/__mocks__/react-native-encrypted-storage.ts',
  },
};
