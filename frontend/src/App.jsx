import React, { useState, useMemo, useEffect } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { ThemeProvider } from '@mui/material/styles';
import CssBaseline from '@mui/material/CssBaseline';
import { createAppTheme } from './theme';
import { AuthProvider, useAuth } from './context/AuthContext';
import Layout from './components/Layout';
import RoleDashboard from './components/RoleDashboard';
import Login from './components/Login';
import ForgotPassword from './components/ForgotPassword';
import ResetPassword from './components/ResetPassword';
import CasesList from './components/CasesList';
import DocumentsList from './components/DocumentsList';
import UsersList from './components/UsersList';
import Settings from './components/Settings';
import Audit from './pages/Audit';
import BillingDashboard from './components/BillingDashboard';
import PrivateRoute from './components/PrivateRoute';
import { useTranslation } from 'react-i18next';

function AppContent() {
  const { i18n } = useTranslation();
  const [mode, setMode] = useState(() => {
    const savedMode = localStorage.getItem('themeMode');
    return savedMode || 'light';
  });

  const direction = i18n.language === 'ar' ? 'rtl' : 'ltr';
  const theme = useMemo(() => createAppTheme(mode, direction), [mode, direction]);

  useEffect(() => {
    document.documentElement.dir = direction;
    document.documentElement.lang = i18n.language;
  }, [direction, i18n.language]);

  const toggleTheme = () => {
    setMode((prevMode) => {
      const newMode = prevMode === 'light' ? 'dark' : 'light';
      localStorage.setItem('themeMode', newMode);
      return newMode;
    });
  };

  const { isAuthenticated } = useAuth();

  return (
    <ThemeProvider theme={theme}>
      <CssBaseline />
      <Routes>
        <Route
          path="/login"
          element={
            isAuthenticated ? <Navigate to="/" /> : <Login />
          }
        />
        <Route
          path="/forgot-password"
          element={
            isAuthenticated ? <Navigate to="/" /> : <ForgotPassword />
          }
        />
        <Route
          path="/reset-password"
          element={
            isAuthenticated ? <Navigate to="/" /> : <ResetPassword />
          }
        />
        <Route
          path="/"
          element={
            <PrivateRoute>
              <Layout onToggleTheme={toggleTheme} mode={mode}>
                <RoleDashboard />
              </Layout>
            </PrivateRoute>
          }
        />
        <Route
          path="/casos"
          element={
            <PrivateRoute>
              <Layout onToggleTheme={toggleTheme} mode={mode}>
                <CasesList />
              </Layout>
            </PrivateRoute>
          }
        />
        <Route
          path="/documentos"
          element={
            <PrivateRoute>
              <Layout onToggleTheme={toggleTheme} mode={mode}>
                <DocumentsList />
              </Layout>
            </PrivateRoute>
          }
        />
        <Route
          path="/usuarios"
          element={
            <PrivateRoute requiredRoles={['admin', 'clerk']}>
              <Layout onToggleTheme={toggleTheme} mode={mode}>
                <UsersList />
              </Layout>
            </PrivateRoute>
          }
        />
        <Route
          path="/configuracion"
          element={
            <PrivateRoute>
              <Layout onToggleTheme={toggleTheme} mode={mode}>
                <Settings />
              </Layout>
            </PrivateRoute>
          }
        />
        <Route
          path="/auditoria"
          element={
            <PrivateRoute requiredRoles={['admin', 'clerk']}>
              <Layout onToggleTheme={toggleTheme} mode={mode}>
                <Audit />
              </Layout>
            </PrivateRoute>
          }
        />
        <Route
          path="/facturation"
          element={
            <PrivateRoute requiredRoles={['admin']}>
              <Layout onToggleTheme={toggleTheme} mode={mode}>
                <BillingDashboard />
              </Layout>
            </PrivateRoute>
          }
        />
        <Route path="*" element={<Navigate to="/" />} />
      </Routes>
    </ThemeProvider>
  );
}

function App() {
  return (
    <Router>
      <AuthProvider>
        <AppContent />
      </AuthProvider>
    </Router>
  );
}

export default App;
