import { Outlet } from 'react-router-dom';
import '../styles/auth.css';

export default function AuthLayout() {
  return (
    <main className="auth-shell">
      <div className="auth-card">
        <Outlet />
      </div>
    </main>
  );
}
