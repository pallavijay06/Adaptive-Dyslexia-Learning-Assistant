import { Outlet } from 'react-router-dom';

export default function WorkspaceLayout() {
  return (
    <main className="workspace-layout">
      <Outlet />
    </main>
  );
}
