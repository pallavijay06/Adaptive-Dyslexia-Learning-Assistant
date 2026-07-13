import { useState } from 'react';
import { Eye, EyeOff, Lock, Mail, User } from 'lucide-react';

export default function AuthForm({ mode, onSubmit, loading, error }) {
  const [form, setForm] = useState({
    email: '',
    password: '',
    confirm_password: '',
    full_name: '',
    age: '',
    grade: '',
    institution: '',
    field_of_study: '',
  });
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);

  const handleChange = (event) => {
    const { name, value } = event.target;
    setForm((current) => ({ ...current, [name]: value }));
  };

  const handleSubmit = (event) => {
    event.preventDefault();
    onSubmit(form);
  };

  return (
    <form onSubmit={handleSubmit} style={{ display: 'grid', gap: '0.95rem' }}>
      {mode === 'signup' && (
        <label className="auth-field">
          <span>Full name</span>
          <div className="auth-input-wrapper">
            <User size={18} className="auth-icon" />
            <input className="auth-input" name="full_name" value={form.full_name} onChange={handleChange} required placeholder="Alex Morgan" />
          </div>
        </label>
      )}

      <label className="auth-field">
        <span>Email</span>
        <div className="auth-input-wrapper">
          <Mail size={18} className="auth-icon" />
          <input className="auth-input" type="email" name="email" value={form.email} onChange={handleChange} required placeholder="you@example.com" />
        </div>
      </label>

      <label className="auth-field">
        <span>Password</span>
        <div className="auth-input-wrapper">
          <Lock size={18} className="auth-icon" />
          <input className="auth-input" type={showPassword ? 'text' : 'password'} name="password" value={form.password} onChange={handleChange} required placeholder="Enter your password" />
          <button
            type="button"
            aria-label={showPassword ? 'Hide password' : 'Show password'}
            onClick={() => setShowPassword((value) => !value)}
            style={{ position: 'absolute', right: '0.8rem', top: '50%', transform: 'translateY(-50%)', background: 'transparent', border: 'none', color: '#64748b', cursor: 'pointer' }}
          >
            {showPassword ? <EyeOff size={18} /> : <Eye size={18} />}
          </button>
        </div>
        {mode === 'signup' && (
          <span style={{ fontSize: '0.78rem', color: '#64748b', marginTop: '0.25rem' }}>
            Min 8 characters · uppercase &amp; lowercase · a digit · a symbol (e.g. !@#$)
          </span>
        )}
      </label>

      {mode === 'signup' && (
        <>
          <label className="auth-field">
            <span>Confirm password</span>
            <div className="auth-input-wrapper">
              <Lock size={18} className="auth-icon" />
              <input className="auth-input" type={showConfirmPassword ? 'text' : 'password'} name="confirm_password" value={form.confirm_password} onChange={handleChange} required placeholder="Re-enter your password" />
              <button
                type="button"
                aria-label={showConfirmPassword ? 'Hide confirm password' : 'Show confirm password'}
                onClick={() => setShowConfirmPassword((value) => !value)}
                style={{ position: 'absolute', right: '0.8rem', top: '50%', transform: 'translateY(-50%)', background: 'transparent', border: 'none', color: '#64748b', cursor: 'pointer' }}
              >
                {showConfirmPassword ? <EyeOff size={18} /> : <Eye size={18} />}
              </button>
            </div>
          </label>

          <label className="auth-field">
            <span>Age</span>
            <input className="auth-input" style={{ paddingLeft: '0.95rem' }} type="number" name="age" value={form.age} onChange={handleChange} />
          </label>

          <label className="auth-field">
            <span>Grade or year</span>
            <input className="auth-input" style={{ paddingLeft: '0.95rem' }} name="grade" value={form.grade} onChange={handleChange} required />
          </label>

          <label className="auth-field">
            <span>Institution</span>
            <input className="auth-input" style={{ paddingLeft: '0.95rem' }} name="institution" value={form.institution} onChange={handleChange} required />
          </label>

          <label className="auth-field">
            <span>Field of study</span>
            <input className="auth-input" style={{ paddingLeft: '0.95rem' }} name="field_of_study" value={form.field_of_study} onChange={handleChange} required />
          </label>
        </>
      )}

      {error ? <p className="auth-alert" role="alert">{error}</p> : null}

      <button className="auth-button" type="submit" disabled={loading}>
        {loading ? 'Please wait…' : mode === 'signup' ? 'Create account' : 'Log in'}
      </button>
    </form>
  );
}
