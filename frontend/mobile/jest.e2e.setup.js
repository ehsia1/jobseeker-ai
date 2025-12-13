/**
 * Jest setup for E2E tests.
 * Minimal setup - does NOT mock fetch since we need real HTTP requests.
 */

// Mock expo-secure-store for token management
jest.mock('expo-secure-store', () => {
  const store = {};
  return {
    getItemAsync: jest.fn((key) => Promise.resolve(store[key] || null)),
    setItemAsync: jest.fn((key, value) => {
      store[key] = value;
      return Promise.resolve();
    }),
    deleteItemAsync: jest.fn((key) => {
      delete store[key];
      return Promise.resolve();
    }),
  };
});

// Mock react-native Platform for client.ts module load
jest.mock('react-native', () => ({
  Platform: {
    OS: 'ios',
    select: jest.fn((options) => options.ios || options.default),
  },
}));

// Set E2E environment variable
process.env.E2E_TEST = 'true';

// Increase timeout for network requests
jest.setTimeout(30000);
