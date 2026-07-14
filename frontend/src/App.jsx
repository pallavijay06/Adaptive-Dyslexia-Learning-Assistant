import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom';
import { AuthProvider, useAuth } from './contexts/AuthContext';
import { AccessibilityProvider } from './contexts/AccessibilityContext';
import { DocumentProvider } from './contexts/DocumentContext';
import { JourneyProvider } from './contexts/JourneyContext';
import { ThemeProvider } from './contexts/ThemeContext';
import RootLayout from './layouts/RootLayout';
import AuthLayout from './layouts/AuthLayout';
import AppLayout from './layouts/AppLayout';
import WorkspaceLayout from './layouts/WorkspaceLayout';
import ProtectedRoute from './components/ProtectedRoute';
import AuthPage from './pages/AuthPage';
import DashboardPage from './pages/DashboardPage';
import AuthRoute from './routes/AuthRoute';
import DashboardRoute from './routes/DashboardRoute';
import UploadRoute from './routes/UploadRoute';
import LearningSelectionRoute from './routes/LearningSelectionRoute';
import JourneyRoute from './routes/JourneyRoute';
import ManualLearningRoute from './routes/ManualLearningRoute';
import ProgressRoute from './routes/ProgressRoute';
import WorkspacePage from './pages/WorkspacePage';

function AppRoutes() {
  const { initialising } = useAuth();

  if (initialising) {
    return <div className="card" style={{ maxWidth: '480px', margin: '4rem auto' }}>Loading session...</div>;
  }

  return (
    <Routes>
      <Route element={<RootLayout />}>
        <Route element={<AuthLayout />}>
          <Route path="/auth" element={<AuthPage />} />
          <Route index element={<Navigate to="/auth" replace />} />
        </Route>

        <Route element={<AppLayout />}>
          <Route
            path="/dashboard"
            element={
              <ProtectedRoute>
                <DashboardPage />
              </ProtectedRoute>
            }
          />
          <Route path="/upload" element={<ProtectedRoute><UploadRoute /></ProtectedRoute>} />
          <Route path="/learning-selection" element={<ProtectedRoute><LearningSelectionRoute /></ProtectedRoute>} />
          <Route path="/progress" element={<ProtectedRoute><ProgressRoute /></ProtectedRoute>} />
        </Route>

        <Route element={<WorkspaceLayout />}>
          <Route path="/journey" element={<ProtectedRoute><JourneyRoute /></ProtectedRoute>} />
          <Route path="/manual-learning" element={<ProtectedRoute><ManualLearningRoute /></ProtectedRoute>} />
          <Route path="/workspace" element={<ProtectedRoute><WorkspacePage /></ProtectedRoute>} />
        </Route>
      </Route>
    </Routes>
  );
}

function App() {
  return (
    <BrowserRouter>
      <ThemeProvider>
        <AccessibilityProvider>
          <AuthProvider>
            <DocumentProvider>
              <JourneyProvider>
                <AppRoutes />
              </JourneyProvider>
            </DocumentProvider>
          </AuthProvider>
        </AccessibilityProvider>
      </ThemeProvider>
    </BrowserRouter>
  );
}

export default App;
