import { useEffect, useMemo, useState } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import AuthForm from '../components/AuthForm';

export default function AuthPage() {
  const [mode, setMode] = useState('login');
  const { login, signup, isAuthenticated, loading, error, clearError } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();

  useEffect(() => {
    if (isAuthenticated) {
      const from = location.state?.from?.pathname || '/dashboard';
      navigate(from, { replace: true });
    }
  }, [isAuthenticated, location.state, navigate]);

  useEffect(() => {
    clearError();
  }, [mode, clearError]);

  const title = useMemo(() => (mode === 'signup' ? 'Create your account' : 'Welcome back'), [mode]);

  const handleSubmit = async (values) => {
    if (mode === 'signup') {
      await signup(values);
      return;
    }

    await login(values);
  };

  return (
    <section>
      <h2 className="auth-title">{title}</h2>
      <p className="auth-caption">Use your account to continue learning with a calm, accessible experience.</p>
      <div className="auth-pill-group" role="tablist" aria-label="Authentication mode">
        <button
          type="button"
          className={`auth-pill-button ${mode === 'login' ? 'active' : ''}`}
          onClick={() => setMode('login')}
          aria-pressed={mode === 'login'}
        >
          Log in
        </button>
        <button
          type="button"
          className={`auth-pill-button ${mode === 'signup' ? 'active' : ''}`}
          onClick={() => setMode('signup')}
          aria-pressed={mode === 'signup'}
        >
          Sign up
        </button>
      </div>
      <AuthForm mode={mode} onSubmit={handleSubmit} loading={loading} error={error} />
    </section>
  );
}
