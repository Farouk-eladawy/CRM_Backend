module.exports = {
  preset: 'react-native',
  displayName: 'guest',
  rootDir: '.',
  testMatch: ['<rootDir>/src/**/__tests__/**/*.test.{ts,tsx}'],
  moduleFileExtensions: ['ts', 'tsx', 'js', 'jsx'],
  transformIgnorePatterns: [
    'node_modules/(?!(react-native|@react-native|@react-native-community|@itour)/)',
  ],
  moduleNameMapper: {
    '@itour/shared': '<rootDir>/../../packages/shared/src',
    '@itour/ui': '<rootDir>/../../packages/ui/src',
  },
};
