import { Outlet } from 'react-router-dom';
import SidebarNav from '../components/SidebarNav';
import ThemeToggle from '../components/ThemeToggle';

export default function AppLayout() {
  return (
    <div className="app-shell">
      <SidebarNav />
      <main className="app-main">
        <header className="app-header">
          <div>
            <h1>LexiTutor AI</h1>
          </div>
          <ThemeToggle />
        </header>
        <Outlet />
      </main>
    </div>
  );
}
