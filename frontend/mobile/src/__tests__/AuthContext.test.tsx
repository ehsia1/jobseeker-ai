/**
 * Unit tests for AuthContext and useAuth hook.
 * Tests authentication state management, login, register, and logout flows.
 */

// Must mock before imports since client.ts evaluates Platform.select at module load time
jest.mock('react-native', () => ({
  Platform: {
    OS: 'ios',
    select: jest.fn((options: Record<string, string>) => options.ios || options.default),
  },
}));

import React from 'react';
import { renderHook, act, waitFor } from '@testing-library/react-native';
import { AuthProvider, useAuth } from '../contexts/AuthContext';
import {
  mockSecureStore,
  mockFetchSuccess,
  mockFetchError,
  createMockUser,
  createMockProfile,
  createMockAuthResponse,
} from './helpers';

// Mock the API client module
jest.mock('../api/client', () => {
  const originalModule = jest.requireActual('../api/client');
  return {
    ...originalModule,
    getToken: jest.fn(),
    setToken: jest.fn(),
    removeToken: jest.fn(),
    authApi: {
      login: jest.fn(),
      register: jest.fn(),
      getCurrentUser: jest.fn(),
      logout: jest.fn(),
    },
  };
});

import { getToken, setToken, removeToken, authApi } from '../api/client';

const wrapper = ({ children }: { children: React.ReactNode }) => (
  <AuthProvider>{children}</AuthProvider>
);

describe('AuthContext', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    // Default: no token stored
    (getToken as jest.Mock).mockResolvedValue(null);
    (setToken as jest.Mock).mockResolvedValue(undefined);
    (removeToken as jest.Mock).mockResolvedValue(undefined);
  });

  // ============= Initial State Tests =============

  describe('Initial State', () => {
    it('starts with loading state', async () => {
      const { result } = renderHook(() => useAuth(), { wrapper });

      // Initially loading
      expect(result.current.isLoading).toBe(true);
      expect(result.current.isAuthenticated).toBe(false);
      expect(result.current.user).toBeNull();

      // Wait for initial auth check to complete
      await waitFor(() => {
        expect(result.current.isLoading).toBe(false);
      });
    });

    it('sets unauthenticated when no token exists', async () => {
      (getToken as jest.Mock).mockResolvedValue(null);

      const { result } = renderHook(() => useAuth(), { wrapper });

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false);
      });

      expect(result.current.isAuthenticated).toBe(false);
      expect(result.current.user).toBeNull();
    });

    it('sets authenticated when valid token exists', async () => {
      const mockUser = createMockUser({ profile: createMockProfile() });
      (getToken as jest.Mock).mockResolvedValue('valid-token');
      (authApi.getCurrentUser as jest.Mock).mockResolvedValue(mockUser);

      const { result } = renderHook(() => useAuth(), { wrapper });

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false);
      });

      expect(result.current.isAuthenticated).toBe(true);
      expect(result.current.user).toEqual(mockUser);
    });

    it('clears token and sets unauthenticated when getCurrentUser fails', async () => {
      (getToken as jest.Mock).mockResolvedValue('expired-token');
      (authApi.getCurrentUser as jest.Mock).mockRejectedValue(new Error('Unauthorized'));

      const { result } = renderHook(() => useAuth(), { wrapper });

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false);
      });

      expect(removeToken).toHaveBeenCalled();
      expect(result.current.isAuthenticated).toBe(false);
      expect(result.current.user).toBeNull();
    });
  });

  // ============= Login Tests =============

  describe('login', () => {
    it('authenticates user on successful login', async () => {
      const mockUser = createMockUser();
      const mockAuthResponse = createMockAuthResponse();

      (getToken as jest.Mock).mockResolvedValue(null);
      (authApi.login as jest.Mock).mockResolvedValue(mockAuthResponse);
      (authApi.getCurrentUser as jest.Mock).mockResolvedValue(mockUser);

      const { result } = renderHook(() => useAuth(), { wrapper });

      // Wait for initial load
      await waitFor(() => {
        expect(result.current.isLoading).toBe(false);
      });

      // Perform login
      await act(async () => {
        await result.current.login('test@example.com', 'password123');
      });

      expect(authApi.login).toHaveBeenCalledWith('test@example.com', 'password123');
      expect(authApi.getCurrentUser).toHaveBeenCalled();
      expect(result.current.isAuthenticated).toBe(true);
      expect(result.current.user).toEqual(mockUser);
    });

    it('throws error and stays unauthenticated on login failure', async () => {
      (getToken as jest.Mock).mockResolvedValue(null);
      (authApi.login as jest.Mock).mockRejectedValue(new Error('Invalid credentials'));

      const { result } = renderHook(() => useAuth(), { wrapper });

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false);
      });

      await expect(
        act(async () => {
          await result.current.login('test@example.com', 'wrong');
        })
      ).rejects.toThrow('Invalid credentials');

      expect(result.current.isAuthenticated).toBe(false);
      expect(result.current.user).toBeNull();
    });

    it('sets loading state during login', async () => {
      const mockUser = createMockUser();
      let resolveLogin: () => void;
      const loginPromise = new Promise<void>((resolve) => {
        resolveLogin = resolve;
      });

      (getToken as jest.Mock).mockResolvedValue(null);
      (authApi.login as jest.Mock).mockImplementation(() => loginPromise);
      (authApi.getCurrentUser as jest.Mock).mockResolvedValue(mockUser);

      const { result } = renderHook(() => useAuth(), { wrapper });

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false);
      });

      // Start login - should set loading
      let loginCall: Promise<void>;
      act(() => {
        loginCall = result.current.login('test@example.com', 'password');
      });

      expect(result.current.isLoading).toBe(true);

      // Resolve login
      await act(async () => {
        resolveLogin!();
        await loginCall;
      });

      expect(result.current.isLoading).toBe(false);
    });
  });

  // ============= Register Tests =============

  describe('register', () => {
    it('registers and automatically logs in user', async () => {
      const mockUser = createMockUser();
      const mockAuthResponse = createMockAuthResponse();

      (getToken as jest.Mock).mockResolvedValue(null);
      (authApi.register as jest.Mock).mockResolvedValue(mockUser);
      (authApi.login as jest.Mock).mockResolvedValue(mockAuthResponse);
      (authApi.getCurrentUser as jest.Mock).mockResolvedValue(mockUser);

      const { result } = renderHook(() => useAuth(), { wrapper });

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false);
      });

      await act(async () => {
        await result.current.register('new@example.com', 'password123', 'New User');
      });

      expect(authApi.register).toHaveBeenCalledWith('new@example.com', 'password123', 'New User');
      expect(authApi.login).toHaveBeenCalledWith('new@example.com', 'password123');
      expect(result.current.isAuthenticated).toBe(true);
      expect(result.current.user).toEqual(mockUser);
    });

    it('throws error on registration failure', async () => {
      (getToken as jest.Mock).mockResolvedValue(null);
      (authApi.register as jest.Mock).mockRejectedValue(new Error('Email already exists'));

      const { result } = renderHook(() => useAuth(), { wrapper });

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false);
      });

      await expect(
        act(async () => {
          await result.current.register('existing@example.com', 'password123');
        })
      ).rejects.toThrow('Email already exists');

      expect(result.current.isAuthenticated).toBe(false);
    });
  });

  // ============= Logout Tests =============

  describe('logout', () => {
    it('clears user state on logout', async () => {
      const mockUser = createMockUser();
      (getToken as jest.Mock).mockResolvedValue('valid-token');
      (authApi.getCurrentUser as jest.Mock).mockResolvedValue(mockUser);
      (authApi.logout as jest.Mock).mockResolvedValue(undefined);

      const { result } = renderHook(() => useAuth(), { wrapper });

      // Wait for authenticated state
      await waitFor(() => {
        expect(result.current.isAuthenticated).toBe(true);
      });

      // Perform logout
      await act(async () => {
        await result.current.logout();
      });

      expect(authApi.logout).toHaveBeenCalled();
      expect(result.current.isAuthenticated).toBe(false);
      expect(result.current.user).toBeNull();
    });
  });

  // ============= refreshUser Tests =============

  describe('refreshUser', () => {
    it('refreshes user data from server', async () => {
      const mockUser = createMockUser({ full_name: 'Original Name' });
      const updatedUser = createMockUser({ full_name: 'Updated Name' });

      (getToken as jest.Mock).mockResolvedValue('valid-token');
      (authApi.getCurrentUser as jest.Mock)
        .mockResolvedValueOnce(mockUser)
        .mockResolvedValueOnce(updatedUser);

      const { result } = renderHook(() => useAuth(), { wrapper });

      await waitFor(() => {
        expect(result.current.user?.full_name).toBe('Original Name');
      });

      // Refresh user
      await act(async () => {
        await result.current.refreshUser();
      });

      expect(result.current.user?.full_name).toBe('Updated Name');
    });
  });

  // ============= useAuth Hook Tests =============

  describe('useAuth hook', () => {
    it('throws error when used outside AuthProvider', () => {
      // Suppress console.error for this test
      const consoleSpy = jest.spyOn(console, 'error').mockImplementation(() => {});

      expect(() => {
        renderHook(() => useAuth());
      }).toThrow('useAuth must be used within an AuthProvider');

      consoleSpy.mockRestore();
    });
  });
});
