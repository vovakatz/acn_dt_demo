import React, { createContext, useContext, useState, ReactNode } from 'react';
import { authService } from './api';
import { LoginCredentials } from '../types/auth';

interface AuthContextType {
  isAuthenticated: boolean;
  login: (credentials: LoginCredentials) => Promise<void>;
  logout: () => void;
  error: string | null;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  const [isAuthenticated, setIsAuthenticated] = useState<boolean>(authService.isAuthenticated());
  const [error, setError] = useState<string | null>(null);

  const login = async (credentials: LoginCredentials) => {
    try {
      setError(null);
      await authService.login(credentials);
      setIsAuthenticated(true);
    } catch (err) {
      setError('Login failed. Please check your credentials.');
      throw err;
    }
  };

  const logout = () => {
    authService.logout();
    setIsAuthenticated(false);
  };

  const value = {
    isAuthenticated,
    login,
    logout,
    error
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};

export const useAuth = (): AuthContextType => {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};