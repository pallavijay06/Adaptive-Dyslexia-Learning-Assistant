import { Outlet } from 'react-router-dom';
import AuthNav from '../components/AuthNav';

export default function AppLayout() {
  return (
    <main>
      <header style={{ marginBottom: '1.5rem' }}>
        <h1>Adaptive Learning Assistant</h1>
        <p>Application shell placeholder for the React migration.</p>
      </header>
      <AuthNav />
      <Outlet />
    </main>
  );
}
