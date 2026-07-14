import { useState } from 'react';
import { NavLink, useNavigate } from 'react-router-dom';
import {
  BookOpen,
  Compass,
  FolderOpen,
  LayoutDashboard,
  LogOut,
  PanelLeftClose,
  PanelLeftOpen,
  Sparkles,
  TrendingUp,
  Upload,
} from 'lucide-react';
import { useAuth } from '../contexts/AuthContext';

const navItems = [
  { to: '/dashboard', label: 'Dashboard', icon: LayoutDashboard },
  { to: '/upload', label: 'Upload', icon: Upload },
  { to: '/learning-selection', label: 'Learning', icon: Sparkles },
  // { to: '/progress', label: 'Progress', icon: TrendingUp },
  // { to: '/journey', label: 'Journey', icon: Compass },
  // { to: '/manual-learning', label: 'Manual', icon: BookOpen },
  // { to: '/workspace', label: 'Workspace', icon: FolderOpen },
];

export default function SidebarNav() {
  const { isAuthenticated, logout } = useAuth();
  const navigate = useNavigate();
  const [collapsed, setCollapsed] = useState(false);

  if (!isAuthenticated) {
    return null;
  }

  return (
    <aside className={`sidebar-nav ${collapsed ? 'collapsed' : ''}`}>
      <div className="sidebar-header">
        <div className="sidebar-brand">
          <div className="sidebar-brand-icon">
            <Sparkles size={18} />
          </div>
          {!collapsed && (
            <div className="sidebar-brand-copy">
              <span>Adaptive</span>
              <strong>Learning</strong>
            </div>
          )}
        </div>
        <button
          type="button"
          className="sidebar-collapse"
          onClick={() => setCollapsed((value) => !value)}
          aria-label={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
        >
          {collapsed ? <PanelLeftOpen size={18} /> : <PanelLeftClose size={18} />}
        </button>
      </div>

      <nav className="sidebar-links" aria-label="Primary navigation">
        {navItems.map(({ to, label, icon: Icon }) => (
          <NavLink
            key={to}
            to={to}
            className={({ isActive }) => `sidebar-link ${isActive ? 'active' : ''}`}
          >
            <span className="sidebar-link-icon">
              <Icon size={18} />
            </span>
            {!collapsed && <span className="sidebar-link-label">{label}</span>}
          </NavLink>
        ))}
      </nav>

      <div className="sidebar-footer">
        <button
          type="button"
          className="sidebar-logout"
          onClick={async () => {
            await logout();
            navigate('/auth', { replace: true });
          }}
        >
          <span className="sidebar-link-icon">
            <LogOut size={18} />
          </span>
          {!collapsed && <span className="sidebar-link-label">Logout</span>}
        </button>
      </div>
    </aside>
  );
}
