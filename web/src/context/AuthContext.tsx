import React, { createContext, useContext, useState, useEffect } from 'react';
import { User, UserRole } from '../types';
import { api } from '../services/api';

interface AuthContextType {
  user: User | null;
  token: string | null;
  login: (email: string, password?: string) => Promise<void>;
  logout: () => void;
  switchRole: (role: UserRole) => void;
  isAuthenticated: boolean;
  activeFleetId: number;
  setActiveFleetId: (id: number) => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [token, setToken] = useState<string | null>(localStorage.getItem('evc_token'));
  const [user, setUser] = useState<User | null>(() => {
    const saved = localStorage.getItem('evc_user');
    if (saved) {
      try {
        return JSON.parse(saved);
      } catch {
        return null;
      }
    }
    // Default initial user for instant seamless experience
    return {
      user_id: 1,
      tenant_id: 1,
      email: 'manager@voltfleet.com',
      role: 'fleet_manager',
    };
  });
  const [activeFleetId, setActiveFleetId] = useState<number>(1);

  useEffect(() => {
    if (token) {
      api.setToken(token);
    }
  }, [token]);

  const login = async (email: string, password: string = 'Password123!') => {
    const res = await api.login(email, password);
    setToken(res.access_token);
    setUser(res.user);
    localStorage.setItem('evc_user', JSON.stringify(res.user));
    setActiveFleetId(res.user.tenant_id);
  };

  const logout = () => {
    setToken(null);
    setUser(null);
    api.setToken(null);
    localStorage.removeItem('evc_token');
    localStorage.removeItem('evc_user');
  };

  const switchRole = (role: UserRole) => {
    if (!user) return;
    const updated: User = {
      ...user,
      role,
      email: `${role}@${user.tenant_id === 1 ? 'voltfleet.com' : user.tenant_id === 2 ? 'metrohaul.com' : 'greenhaul.com'}`,
    };
    setUser(updated);
    localStorage.setItem('evc_user', JSON.stringify(updated));
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        token,
        login,
        logout,
        switchRole,
        isAuthenticated: !!user,
        activeFleetId,
        setActiveFleetId,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};
