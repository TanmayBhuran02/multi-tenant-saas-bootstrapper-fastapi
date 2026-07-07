/**
 * Zustand store for tenant context.
 *
 * Manages: tenant, user, plan, feature flags, loading state.
 * Persists token + tenant_id in localStorage.
 */
import { create } from 'zustand';
import client from '../api/client';

const useTenantStore = create((set, get) => ({
  // ── State ─────────────────────────────────────────
  tenant: null,
  user: null,
  plan: null,
  featureFlags: [],
  isLoading: true,
  isAuthenticated: false,

  // ── Actions ───────────────────────────────────────

  /**
   * Set tenant data and persist tenant_id.
   */
  setTenant: (tenant) => {
    if (tenant?.id) {
      localStorage.setItem('tenant_id', tenant.id);
    }
    set({ tenant, plan: tenant?.plan || null });
  },

  /**
   * Set user after login.
   */
  setUser: (user) => {
    localStorage.setItem('user', JSON.stringify(user));
    set({ user, isAuthenticated: true });
  },

  /**
   * Login: authenticate and load tenant data.
   */
  login: async (email, password, tenantId) => {
    const payload = { email, password };
    if (tenantId) payload.tenant_id = tenantId;

    const { data } = await client.post('/api/auth/login', payload);
    localStorage.setItem('access_token', data.access_token);

    const user = data.user;
    localStorage.setItem('user', JSON.stringify(user));

    if (user.tenant_id) {
      localStorage.setItem('tenant_id', user.tenant_id);
    }

    set({
      user,
      isAuthenticated: true,
      plan: user.plan || null,
    });

    // Load tenant data
    await get().hydrate();
    return data;
  },

  /**
   * Logout: clear all state and localStorage.
   */
  logout: () => {
    localStorage.removeItem('access_token');
    localStorage.removeItem('tenant_id');
    localStorage.removeItem('user');
    set({
      tenant: null,
      user: null,
      plan: null,
      featureFlags: [],
      isAuthenticated: false,
    });
  },

  /**
   * Refresh feature flags from the API.
   */
  refreshFlags: async () => {
    try {
      const { data } = await client.get('/api/features/');
      set({ featureFlags: data.flags || [] });
    } catch (err) {
      console.warn('Failed to refresh flags:', err);
    }
  },

  /**
   * Hydrate store from API on app load (if token exists).
   */
  hydrate: async () => {
    const token = localStorage.getItem('access_token');
    if (!token) {
      set({ isLoading: false, isAuthenticated: false });
      return;
    }

    try {
      // Load user profile
      const { data: profileData } = await client.get('/api/auth/me');
      const user = profileData.user;

      // Load tenant config if we have a tenant_id
      let tenant = null;
      const tenantId = user.tenant_id || localStorage.getItem('tenant_id');
      if (tenantId) {
        try {
          const { data: configData } = await client.get(`/api/tenants/${tenantId}/config`);
          tenant = { id: tenantId, configs: configData.configs || [] };
        } catch {
          // Config might not be accessible, continue
        }
      }

      // Load feature flags
      let featureFlags = [];
      try {
        const { data: flagsData } = await client.get('/api/features/');
        featureFlags = flagsData.flags || [];
      } catch {
        // Flags might not be accessible, continue
      }

      // Load billing info
      let plan = null;
      try {
        const { data: billingData } = await client.get('/api/billing/plan');
        plan = billingData.plan;
        if (tenant) {
          tenant.plan = plan;
          tenant.limits = billingData.limits;
          tenant.usage = billingData.usage;
          tenant.features = billingData.features;
        }
      } catch {
        // Billing might not be accessible, continue
      }

      set({
        user,
        tenant,
        plan,
        featureFlags,
        isAuthenticated: true,
        isLoading: false,
      });
    } catch (err) {
      // Token is invalid
      localStorage.removeItem('access_token');
      set({
        isLoading: false,
        isAuthenticated: false,
        user: null,
        tenant: null,
      });
    }
  },
}));

export default useTenantStore;
