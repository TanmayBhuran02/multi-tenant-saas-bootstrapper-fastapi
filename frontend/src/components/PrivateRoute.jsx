/**
 * PrivateRoute component.
 *
 * Guards routes that require authentication.
 * Redirects to /login if no token exists.
 */
import { Navigate } from 'react-router-dom';
import useTenantStore from '../context/TenantContext';

export default function PrivateRoute({ children }) {
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

  return children;
}
