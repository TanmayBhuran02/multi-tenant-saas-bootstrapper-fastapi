/**
 * SuperadminRoute component.
 *
 * Guards routes that require superadmin access.
 * Decodes JWT to check is_superadmin claim.
 */
import { Navigate } from 'react-router-dom';
import useTenantStore from '../context/TenantContext';

function decodeToken(token) {
  try {
    const payload = token.split('.')[1];
    return JSON.parse(atob(payload));
  } catch {
    return null;
  }
}

export default function SuperadminRoute({ children }) {
  const isAuthenticated = useTenantStore((s) => s.isAuthenticated);
  const isLoading = useTenantStore((s) => s.isLoading);

  if (isLoading) {
    return (
      <div className="route-loading">
        <div className="loading-spinner" />
        <p>Loading...</p>
      </div>
    );
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }

  const token = localStorage.getItem('access_token');
  const decoded = decodeToken(token);

  if (!decoded?.is_superadmin) {
    return <Navigate to="/dashboard" replace />;
  }

  return children;
}
