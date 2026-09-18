import React, { createContext, useContext, useState, useEffect } from 'react';
import type { User } from '../types';
import { apiClient } from '../api/client';

interface AuthContextType {
  user: User | null;
  token: string | null;
  loading: boolean;
  login: (token: string, user: User) => void;
  logout: () => Promise<void>;
  updateUser: (user: User) => void;
  isStudent: boolean;
  isFaculty: boolean;
  isMentor: boolean;
  isAdmin: boolean;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<User | null>(() => {
    const saved = localStorage.getItem('fx_user');
    return saved ? JSON.parse(saved) : null;
  });
  const [token, setToken] = useState<string | null>(() => {
    return localStorage.getItem('fx_token');
  });
  const [loading, setLoading] = useState<boolean>(true);

  useEffect(() => {
    const verifyUser = async () => {
      if (token) {
        try {
          const res = await apiClient.get<User>('/auth/me/');
          setUser(res.data);
          localStorage.setItem('fx_user', JSON.stringify(res.data));
        } catch {
          logout();
        }
      }
      setLoading(false);
    };
    verifyUser();
  }, [token]);

  const login = (newToken: string, newUser: User) => {
    setToken(newToken);
    setUser(newUser);
    localStorage.setItem('fx_token', newToken);
    localStorage.setItem('fx_user', JSON.stringify(newUser));
  };

  const logout = async () => {
    try {
      if (token) {
        await apiClient.post('/auth/logout/');
      }
    } catch {
      // Ignore logout errors
    } finally {
      setToken(null);
      setUser(null);
      localStorage.removeItem('fx_token');
      localStorage.removeItem('fx_user');
    }
  };

  const updateUser = (updated: User) => {
    setUser(updated);
    localStorage.setItem('fx_user', JSON.stringify(updated));
  };

  const isStudent = user?.role === 'STUDENT';
  const isFaculty = user?.role === 'FACULTY' || user?.role === 'MENTOR';
  const isMentor = isFaculty;
  const isAdmin = user?.role === 'ADMIN';

  return (
    <AuthContext.Provider
      value={{
        user,
        token,
        loading,
        login,
        logout,
        updateUser,
        isStudent,
        isFaculty,
        isMentor,
        isAdmin,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = (): AuthContextType => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};
