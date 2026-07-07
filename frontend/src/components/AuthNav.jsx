import { useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';

export default function AuthNav() {
  const { isAuthenticated, logout } = useAuth();
  const navigate = useNavigate();

  if (!isAuthenticated) {
    return null;
  }

  return (
    <div style={{ display: 'flex', justifyContent: 'flex-end', marginBottom: '1rem' }}>
      <button
        type="button"
        onClick={async () => {
          await logout();
          navigate('/auth', { replace: true });
        }}
      >
        Logout
      </button>
    </div>
  );
}
