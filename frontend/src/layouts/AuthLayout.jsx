import { Outlet } from 'react-router-dom';

export default function AuthLayout() {
  return (
    <main>
      <div className="card" style={{ maxWidth: '480px', margin: '4rem auto' }}>
        <Outlet />
      </div>
    </main>
  );
}
