import React, { useState, useEffect } from 'react';
import { useForm } from 'react-hook-form';
import client from '../../api/client';
import useTenantStore from '../../context/TenantContext';
import './Superadmin.css';

export default function SuperadminPage() {
  const logout = useTenantStore((s) => s.logout);
  const [metrics, setMetrics] = useState(null);
  const [tenants, setTenants] = useState([]);
  const [loading, setLoading] = useState(true);
  const [provisionLoading, setProvisionLoading] = useState(false);
  const [error, setError] = useState('');

  const { register, handleSubmit, reset, formState: { errors } } = useForm();

  const loadDashboard = async () => {
    setLoading(true);
    try {
      const [metricsRes, tenantsRes] = await Promise.all([
        client.get('/api/admin/metrics'),
        client.get('/api/admin/tenants?per_page=50')
      ]);
      setMetrics(metricsRes.data.metrics);
      setTenants(tenantsRes.data.tenants);
    } catch (err) {
      setError('Failed to load dashboard data');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadDashboard();
  }, []);

  const handleProvision = async (data) => {
    setProvisionLoading(true);
    setError('');
    try {
      await client.post('/api/tenants/provision', data);
      reset();
      loadDashboard();
    } catch (err) {
      setError(err.response?.data?.error || 'Provisioning failed');
    } finally {
      setProvisionLoading(false);
    }
  };

  const handleDelete = async (tenantId) => {
    if (!window.confirm('Are you sure you want to soft-delete this tenant?')) return;
    try {
      await client.delete(`/api/tenants/${tenantId}`);
      loadDashboard();
    } catch (err) {
      setError('Failed to delete tenant');
    }
  };

  if (loading) return <div className="superadmin-dashboard">Loading...</div>;

  return (
    <div className="superadmin-dashboard animate-slide-up">
      <div className="superadmin-header">
        <h1>Platform Admin</h1>
        <button className="logout-btn" onClick={logout}>Sign Out</button>
      </div>

      {error && <div className="login-error" style={{ marginBottom: '1rem' }}>{error}</div>}

      <div className="metrics-grid">
        <div className="metric-card">
          <span className="metric-title">Total Tenants</span>
          <span className="metric-value">{metrics?.total_tenants || 0}</span>
        </div>
        <div className="metric-card">
          <span className="metric-title">Total Users</span>
          <span className="metric-value">{metrics?.total_users || 0}</span>
        </div>
        <div className="metric-card">
          <span className="metric-title">Active Plans</span>
          <div style={{ display: 'flex', gap: '1rem', marginTop: '0.5rem' }}>
            {metrics?.by_plan && Object.entries(metrics.by_plan).map(([plan, count]) => (
              <div key={plan} style={{ display: 'flex', flexDirection: 'column' }}>
                <span style={{ fontSize: '0.75rem', textTransform: 'uppercase', color: 'var(--color-text-secondary)' }}>{plan}</span>
                <span style={{ fontSize: '1.25rem', fontWeight: 'bold' }}>{count}</span>
              </div>
            ))}
          </div>
        </div>
      </div>

      <div className="provision-section">
        <h2>Provision New Tenant</h2>
        <form onSubmit={handleSubmit(handleProvision)} className="provision-form">
          <div className="input-group">
            <label className="input-label">Display Name</label>
            <input className="input" placeholder="Acme Corp" {...register('display_name', { required: true })} />
          </div>
          <div className="input-group">
            <label className="input-label">Subdomain</label>
            <input className="input" placeholder="acme" {...register('subdomain', { required: true })} />
          </div>
          <div className="input-group">
            <label className="input-label">Owner Email</label>
            <input className="input" type="email" placeholder="owner@acme.com" {...register('owner_email', { required: true })} />
          </div>
          <div className="input-group">
            <label className="input-label">Owner Password</label>
            <input className="input" type="password" placeholder="Min 8 chars" {...register('owner_password', { required: true, minLength: 8 })} />
          </div>
          <div className="input-group">
            <label className="input-label">Plan</label>
            <select className="input" {...register('plan')}>
              <option value="free">Free</option>
              <option value="starter">Starter</option>
              <option value="pro">Pro</option>
              <option value="enterprise">Enterprise</option>
            </select>
          </div>
          <button type="submit" className="btn btn-primary" disabled={provisionLoading} style={{ height: '42px', marginBottom: '2px' }}>
            {provisionLoading ? 'Provisioning...' : 'Provision'}
          </button>
        </form>
      </div>

      <div className="tenants-section">
        <div className="tenants-header">
          <h2>All Tenants</h2>
        </div>
        <div className="table-wrapper">
          <table className="tenants-table">
            <thead>
              <tr>
                <th>Name</th>
                <th>Subdomain</th>
                <th>Plan</th>
                <th>Users</th>
                <th>Status</th>
                <th>Created At</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {tenants.map(t => (
                <tr key={t.id}>
                  <td style={{ fontWeight: 500 }}>{t.display_name}</td>
                  <td style={{ fontFamily: 'monospace' }}>{t.subdomain}</td>
                  <td style={{ textTransform: 'capitalize' }}>{t.plan}</td>
                  <td>{t.user_count}</td>
                  <td>
                    <span className={`status-badge status-${t.status}`}>
                      {t.status}
                    </span>
                  </td>
                  <td style={{ color: 'var(--color-text-secondary)', fontSize: '0.875rem' }}>
                    {new Date(t.created_at).toLocaleDateString()}
                  </td>
                  <td>
                    {t.status !== 'deleted' && (
                      <button className="delete-btn" onClick={() => handleDelete(t.id)}>
                        Delete
                      </button>
                    )}
                  </td>
                </tr>
              ))}
              {tenants.length === 0 && (
                <tr>
                  <td colSpan="7" style={{ textAlign: 'center', padding: '2rem', color: 'var(--color-text-secondary)' }}>
                    No tenants found.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
