/**
 * Jest setup file for JobSeeker AI mobile app tests.
 * Configures mocks for native modules and global test utilities.
 */

// Mock expo-secure-store
jest.mock('expo-secure-store', () => ({
  getItemAsync: jest.fn(),
  setItemAsync: jest.fn(),
  deleteItemAsync: jest.fn(),
}));

// Note: react-native Platform is mocked in individual test files that need it
// because mocking it globally causes circular dependency issues with jest-expo

// Silence console logs during tests (optional - comment out if debugging)
global.console = {
  ...console,
  log: jest.fn(),
  debug: jest.fn(),
  info: jest.fn(),
  // Keep warn and error for debugging
  warn: console.warn,
  error: console.error,
};

// Mock fetch globally
global.fetch = jest.fn();

// Reset mocks before each test
beforeEach(() => {
  jest.clearAllMocks();
  global.fetch.mockReset();
});
