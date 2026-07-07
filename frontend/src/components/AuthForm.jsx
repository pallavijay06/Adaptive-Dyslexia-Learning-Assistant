import { useState } from 'react';

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

  const handleChange = (event) => {
    const { name, value } = event.target;
    setForm((current) => ({ ...current, [name]: value }));
  };

  const handleSubmit = (event) => {
    event.preventDefault();
    onSubmit(form);
  };

  return (
    <form onSubmit={handleSubmit} style={{ display: 'grid', gap: '0.9rem' }}>
      {mode === 'signup' && (
        <label>
          <span>Full name</span>
          <input name="full_name" value={form.full_name} onChange={handleChange} required />
        </label>
      )}

      <label>
        <span>Email</span>
        <input type="email" name="email" value={form.email} onChange={handleChange} required />
      </label>

      <label>
        <span>Password</span>
        <input type="password" name="password" value={form.password} onChange={handleChange} required />
      </label>

      {mode === 'signup' && (
        <>
          <label>
            <span>Confirm password</span>
            <input type="password" name="confirm_password" value={form.confirm_password} onChange={handleChange} required />
          </label>

          <label>
            <span>Age</span>
            <input type="number" name="age" value={form.age} onChange={handleChange} />
          </label>

          <label>
            <span>Grade or year</span>
            <input name="grade" value={form.grade} onChange={handleChange} required />
          </label>

          <label>
            <span>Institution</span>
            <input name="institution" value={form.institution} onChange={handleChange} required />
          </label>

          <label>
            <span>Field of study</span>
            <input name="field_of_study" value={form.field_of_study} onChange={handleChange} required />
          </label>
        </>
      )}

      {error ? <p role="alert" style={{ color: '#b42318' }}>{error}</p> : null}

      <button type="submit" disabled={loading}>
        {loading ? 'Please wait…' : mode === 'signup' ? 'Create account' : 'Log in'}
      </button>
    </form>
  );
}
