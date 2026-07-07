import React, { useEffect } from 'react';
import { Routes, Route, Navigate, useLocation } from 'react-router-dom';
import useTenantStore from './context/TenantContext';

// Components
import PrivateRoute from './components/PrivateRoute';
import SuperadminRoute from './components/SuperadminRoute';

// Pages
import Login from './pages/Login';
import Onboarding from './pages/Onboarding';
import Dashboard from './pages/Dashboard';
import Superadmin from './pages/Superadmin';

function App() {
  const { hydrate, isLoading } = useTenantStore();
  const location = useLocation();

  useEffect(() => {
    // Hydrate store on app load (checks for existing token)
    hydrate();
  }, [hydrate]);

  if (isLoading) {
    return <div className="app-loading">Loading...</div>;
  }

  return (
    <div className="app-container">
      <Routes>
        <Route path="/" element={<Navigate to="/login" replace />} />
        <Route path="/login" element={<Login />} />
        <Route path="/onboarding" element={<Onboarding />} />
        
        <Route 
          path="/dashboard/*" 
          element={
            <PrivateRoute>
              <Dashboard />
            </PrivateRoute>
          } 
        />
        
        <Route 
          path="/superadmin/*" 
          element={
            <SuperadminRoute>
              <Superadmin />
            </SuperadminRoute>
          } 
        />
      </Routes>
    </div>
  );
}

export default App;
