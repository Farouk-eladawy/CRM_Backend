module.exports = {
  preset: 'react-native',
  displayName: 'ui',
  rootDir: '.',
  testMatch: ['<rootDir>/**/__tests__/**/*.test.{ts,tsx}'],
  moduleFileExtensions: ['ts', 'tsx', 'js', 'jsx'],
  transformIgnorePatterns: [
    'node_modules/(?!(react-native|@react-native|@react-native-community)/)',
  ],
  setupFiles: ['./jest.setup.ts'],
};
