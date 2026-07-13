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

      const msg = response.data?.error || '';
      if (msg.toLowerCase().includes('not found') || msg.toLowerCase().includes('no account')) {
        setError('No account found. Please sign up first.');
      } else if (msg.toLowerCase().includes('invalid') || msg.toLowerCase().includes('password')) {
        setError('Incorrect email or password. Please try again.');
      } else {
        setError(msg || 'Login failed.');
      }
      return false;
    } catch (axiosError) {
      const msg = axiosError?.response?.data?.error || '';
      const status = axiosError?.response?.status;
      if (status === 401) {
        setError('Incorrect email or password. Please try again.');
      } else if (status === 404 || msg.toLowerCase().includes('not found')) {
        setError('No account found. Please sign up first.');
      } else if (msg) {
        setError(msg);
      } else {
        setError('Login failed. Please check your connection and try again.');
      }
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
        full_name: values.full_name,
        email: values.email,
        password: values.password,
        confirm_password: values.confirm_password,
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

      const msg = response.data?.error || '';
      if (msg.toLowerCase().includes('already')) {
        setError('An account with this email already exists. Please log in.');
      } else {
        setError(msg || 'Registration failed.');
      }
      return false;
    } catch (axiosError) {
      const msg = axiosError?.response?.data?.error || '';
      if (axiosError?.response?.status === 409 || msg.toLowerCase().includes('already')) {
        setError('An account with this email already exists. Please log in.');
      } else if (msg) {
        setError(msg);
      } else {
        setError('Registration failed. Please check your connection and try again.');
      }
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
