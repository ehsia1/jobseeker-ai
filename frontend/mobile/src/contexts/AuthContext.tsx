import React, { createContext, useContext, useEffect, useState, useCallback } from 'react';
import { authApi, getToken, removeToken } from '../api/client';
import type { User, UserProfile } from '../../shared/src/types';

interface AuthState {
  user: (User & { profile?: UserProfile }) | null;
  isLoading: boolean;
  isAuthenticated: boolean;
}

interface AuthContextType extends AuthState {
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string, fullName?: string) => Promise<void>;
  logout: () => Promise<void>;
  refreshUser: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [state, setState] = useState<AuthState>({
    user: null,
    isLoading: true,
    isAuthenticated: false,
  });

  const refreshUser = useCallback(async () => {
    console.log('[Auth] refreshUser called');
    try {
      const token = await getToken();
      if (!token) {
        console.log('[Auth] No token found, setting unauthenticated');
        setState({ user: null, isLoading: false, isAuthenticated: false });
        return;
      }

      console.log('[Auth] Token found, fetching current user');
      const user = await authApi.getCurrentUser();
      console.log('[Auth] Got user, setting authenticated');
      setState({ user, isLoading: false, isAuthenticated: true });
    } catch (error) {
      console.log('[Auth] Error in refreshUser:', error);
      await removeToken();
      setState({ user: null, isLoading: false, isAuthenticated: false });
    }
  }, []);

  useEffect(() => {
    refreshUser();
  }, [refreshUser]);

  const login = useCallback(async (email: string, password: string) => {
    console.log('[Auth] login called for:', email);
    setState((prev) => ({ ...prev, isLoading: true }));
    try {
      await authApi.login(email, password);
      console.log('[Auth] login API success, fetching user');
      const user = await authApi.getCurrentUser();
      console.log('[Auth] getCurrentUser success, setting authenticated');
      setState({ user, isLoading: false, isAuthenticated: true });
    } catch (error) {
      console.log('[Auth] login error:', error);
      setState((prev) => ({ ...prev, isLoading: false }));
      throw error;
    }
  }, []);

  const register = useCallback(async (email: string, password: string, fullName?: string) => {
    console.log('[Auth] register called for:', email);
    setState((prev) => ({ ...prev, isLoading: true }));
    try {
      await authApi.register(email, password, fullName);
      console.log('[Auth] register API success, now logging in');
      // After registration, log in automatically
      await authApi.login(email, password);
      console.log('[Auth] login after register success, fetching user');
      const user = await authApi.getCurrentUser();
      console.log('[Auth] getCurrentUser success, setting authenticated');
      setState({ user, isLoading: false, isAuthenticated: true });
    } catch (error) {
      console.log('[Auth] register error:', error);
      setState((prev) => ({ ...prev, isLoading: false }));
      throw error;
    }
  }, []);

  const logout = useCallback(async () => {
    await authApi.logout();
    setState({ user: null, isLoading: false, isAuthenticated: false });
  }, []);

  return (
    <AuthContext.Provider
      value={{
        ...state,
        login,
        register,
        logout,
        refreshUser,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}
