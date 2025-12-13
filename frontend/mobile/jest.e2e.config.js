/**
 * Jest configuration for E2E tests.
 * These tests run against the live backend server.
 */
module.exports = {
  preset: 'jest-expo',
  transformIgnorePatterns: [
    'node_modules/(?!((jest-)?react-native|@react-native(-community)?)|expo(nent)?|@expo(nent)?/.*|@expo-google-fonts/.*|react-navigation|@react-navigation/.*|@unimodules/.*|unimodules|sentry-expo|native-base|react-native-svg|@tanstack/.*)',
  ],
  setupFilesAfterEnv: ['<rootDir>/jest.e2e.setup.js'],
  moduleNameMapper: {
    '^@/(.*)$': '<rootDir>/$1',
  },
  testMatch: [
    '**/__e2e__/**/*.test.[jt]s?(x)',
    '**/__e2e__/**/*-test.[jt]s?(x)',
  ],
  testPathIgnorePatterns: [
    '/node_modules/',
  ],
  testEnvironment: 'node',
  moduleFileExtensions: ['ts', 'tsx', 'js', 'jsx', 'json', 'node'],
  testTimeout: 30000,
};
