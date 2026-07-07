/**
 * Hook: useTenant
 * Returns { tenant, user, plan } from the Zustand store.
 */
import useTenantStore from '../context/TenantContext';

export default function useTenant() {
  const tenant = useTenantStore((s) => s.tenant);
  const user = useTenantStore((s) => s.user);
  const plan = useTenantStore((s) => s.plan);
  return { tenant, user, plan };
}
