import { createContext, useContext, useEffect, useMemo, useState } from 'react';
import api from '../config/api';

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const restoreSession = async () => {
    try {
      const response = await api.get('/auth/session');
      if (response.data?.authenticated) {
        setUser(response.data.user ?? null);
        setIsAuthenticated(true);
      } else {
        setUser(null);
        setIsAuthenticated(false);
      }
    } catch {
      setUser(null);
      setIsAuthenticated(false);
    } finally {
      setLoading(false);
    }
  };

  const login = async ({ email, password }) => {
    setLoading(true);
    setError('');
    try {
      const response = await api.post('/auth/login', { email, password });
      if (response.data?.success) {
        setUser(response.data.user ?? null);
        setIsAuthenticated(true);
        return true;
      }

      setError(response.data?.error || 'Login failed.');
      return false;
    } catch (axiosError) {
      setError(axiosError?.response?.data?.error || 'Login failed.');
      return false;
    } finally {
      setLoading(false);
    }
  };

  const signup = async (values) => {
    setLoading(true);
    setError('');
    try {
      const response = await api.post('/auth/register', {
        full_name,
        email,
        password,
        confirm_password,
        age: values.age,
        grade: values.grade,
        institution: values.institution,
        field_of_study: values.field_of_study,
      });
      if (response.data?.success) {
        setUser(response.data.user ?? null);
        setIsAuthenticated(true);
        return true;
      }

      setError(response.data?.error || 'Signup failed.');
      return false;
    } catch (axiosError) {
      setError(axiosError?.response?.data?.error || 'Signup failed.');
      return false;
    } finally {
      setLoading(false);
    }
  };

  const logout = async () => {
    setLoading(true);
    try {
      await api.post('/auth/logout');
    } catch {
      // Intentionally ignore logout errors and clear local UI state.
    } finally {
      setUser(null);
      setIsAuthenticated(false);
      setLoading(false);
    }
  };

  const clearError = () => setError('');

  useEffect(() => {
    restoreSession();
  }, []);

  const value = useMemo(() => ({
    user,
    setUser,
    isAuthenticated,
    setIsAuthenticated,
    loading,
    setLoading,
    error,
    setError,
    clearError,
    login,
    signup,
    logout,
    restoreSession,
  }), [user, isAuthenticated, loading, error]);

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  return useContext(AuthContext);
}
