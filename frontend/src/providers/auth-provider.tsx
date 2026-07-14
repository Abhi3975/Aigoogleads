'use client';

import { useRouter } from 'next/navigation';
import { createContext, useCallback, useContext, useEffect, useState, type ReactNode } from 'react';
import { api } from '@/lib/api';
import { clearTokens, getAccessToken, setTokens } from '@/lib/tokens';
import type { AuthResponse, TokenPair, User } from '@/lib/types';

interface AuthContextValue {
  user: User | null;
  loading: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string, fullName: string) => Promise<void>;
  logout: () => Promise<void>;
  refreshUser: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const router = useRouter();

  const refreshUser = useCallback(async () => {
    if (!getAccessToken()) {
      setUser(null);
      setLoading(false);
      return;
    }
    try {
      const me = await api.get<User>('/auth/me');
      setUser(me);
    } catch {
      setUser(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void refreshUser();
  }, [refreshUser]);

  const login = useCallback(async (email: string, password: string) => {
    const tokens = await api.post<TokenPair>('/auth/login', { email, password }, { auth: false });
    setTokens(tokens.access_token, tokens.refresh_token);
    const me = await api.get<User>('/auth/me');
    setUser(me);
  }, []);

  const register = useCallback(async (email: string, password: string, fullName: string) => {
    const res = await api.post<AuthResponse>(
      '/auth/register',
      { email, password, full_name: fullName },
      { auth: false },
    );
    setTokens(res.tokens.access_token, res.tokens.refresh_token);
    setUser(res.user);
  }, []);

  const logout = useCallback(async () => {
    try {
      await api.post('/auth/logout', {});
    } catch {
      /* ignore */
    }
    clearTokens();
    setUser(null);
    router.push('/login');
  }, [router]);

  return (
    <AuthContext.Provider value={{ user, loading, login, register, logout, refreshUser }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used within AuthProvider');
  return ctx;
}
