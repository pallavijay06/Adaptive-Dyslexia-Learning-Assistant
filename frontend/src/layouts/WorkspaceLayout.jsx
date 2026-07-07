import { Outlet } from 'react-router-dom';

export default function WorkspaceLayout() {
  return (
    <main>
      <header style={{ marginBottom: '1.5rem' }}>
        <h1>Learning Workspace</h1>
        <p>Workspace shell placeholder for upcoming learning experiences.</p>
      </header>
      <Outlet />
    </main>
  );
}
