import React, { createContext, useContext, useState, useEffect } from 'react';
import { User } from '../types';
import { apiService } from '../services/api';

interface AuthContextType {
  user: User | null;
  login: (apiKey: string, role: 'ADMIN' | 'TRADER') => Promise<boolean>;
  logout: () => void;
  isAuthenticated: boolean;
  isLoading: boolean;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};

interface AuthProviderProps {
  children: React.ReactNode;
}

export const AuthProvider: React.FC<AuthProviderProps> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    // Check for stored auth data on component mount
    const storedApiKey = localStorage.getItem('apiKey');
    const storedRole = localStorage.getItem('role') as 'ADMIN' | 'TRADER';
    
    if (storedApiKey && storedRole) {
      const userData: User = {
        id: storedRole.toLowerCase() + '_user',
        role: storedRole,
        apiKey: storedApiKey,
      };
      
      setUser(userData);
      apiService.setApiKey(storedApiKey);
    }
    
    setIsLoading(false);
  }, []);

  const login = async (apiKey: string, role: 'ADMIN' | 'TRADER'): Promise<boolean> => {
    setIsLoading(true);
    
    try {
      // Set the API key and test the connection
      apiService.setApiKey(apiKey);
      await apiService.healthCheck();
      
      const userData: User = {
        id: role.toLowerCase() + '_user',
        role,
        apiKey,
      };
      
      setUser(userData);
      
      // Store auth data in localStorage
      localStorage.setItem('apiKey', apiKey);
      localStorage.setItem('role', role);
      
      setIsLoading(false);
      return true;
    } catch (error) {
      console.error('Login failed:', error);
      setIsLoading(false);
      return false;
    }
  };

  const logout = () => {
    setUser(null);
    apiService.setApiKey('');
    localStorage.removeItem('apiKey');
    localStorage.removeItem('role');
  };

  const value: AuthContextType = {
    user,
    login,
    logout,
    isAuthenticated: !!user,
    isLoading,
  };

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
};
