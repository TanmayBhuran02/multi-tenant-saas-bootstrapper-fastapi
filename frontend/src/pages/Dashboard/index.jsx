import React, { useState, useEffect } from 'react';
import { useForm } from 'react-hook-form';
import client from '../../api/client';
import useTenantStore from '../../context/TenantContext';
import './Dashboard.css';

export default function DashboardPage() {
  const { user, tenant, logout } = useTenantStore();
  const [team, setTeam] = useState([]);
  const [loadingTeam, setLoadingTeam] = useState(false);
  const [inviteLoading, setInviteLoading] = useState(false);
  const [error, setError] = useState('');
  
  const { register, handleSubmit, reset, formState: { errors } } = useForm();

  const loadTeam = async () => {
    if (!tenant?.id) return;
    setLoadingTeam(true);
    try {
      const { data } = await client.get(`/api/tenants/${tenant.id}/users`);
      setTeam(data.users || []);
    } catch (err) {
      console.error('Failed to load team', err);
    } finally {
      setLoadingTeam(false);
    }
  };

  useEffect(() => {
    loadTeam();
  }, [tenant?.id]);

  const handleInvite = async (data) => {
    setInviteLoading(true);
    setError('');
    try {
      await client.post('/api/auth/register', {
        email: data.email,
        password: data.password,
        role: 'member'
      });
      reset();
      loadTeam();
    } catch (err) {
      setError(err.response?.data?.error || 'Failed to add member');
    } finally {
      setInviteLoading(false);
    }
  };

  const isOwnerOrAdmin = user?.role === 'owner' || user?.role === 'admin';

  return (
    <div className="user-dashboard animate-slide-up">
      <div className="dashboard-header">
        <h1>Dashboard</h1>
        <div style={{ display: 'flex', gap: '1rem', alignItems: 'center' }}>
          <span className="tenant-badge">{tenant?.display_name || 'Personal'}</span>
          <button className="logout-btn" onClick={logout}>Sign Out</button>
        </div>
      </div>

      <div className="welcome-card">
        <h2>Welcome back, {user?.email}!</h2>
        <p>
          You are successfully logged into your SaaS application. This is your personal dashboard 
          where you can access all your tenant-specific features, billing information, and settings.
        </p>
      </div>

      <div className="dashboard-grid">
        <div className="dashboard-card">
          <h3>👤 My Profile</h3>
          <div className="profile-details">
            <div className="profile-row">
              <span className="profile-label">Email:</span>
              <span className="profile-value">{user?.email}</span>
            </div>
            <div className="profile-row">
              <span className="profile-label">Role:</span>
              <span className="profile-value" style={{ textTransform: 'capitalize' }}>{user?.role || 'User'}</span>
            </div>
            <div className="profile-row">
              <span className="profile-label">Account Created:</span>
              <span className="profile-value">
                {new Date(user?.created_at).toLocaleDateString()}
              </span>
            </div>
          </div>
        </div>

        <div className="dashboard-card">
          <h3>🏢 Organization Details</h3>
          <div className="profile-details">
            <div className="profile-row">
              <span className="profile-label">Tenant Name:</span>
              <span className="profile-value">{tenant?.display_name || 'N/A'}</span>
            </div>
            <div className="profile-row">
              <span className="profile-label">Subdomain:</span>
              <span className="profile-value">{tenant?.subdomain || 'N/A'}</span>
            </div>
            <div className="profile-row">
              <span className="profile-label">Current Plan:</span>
              <span className="profile-value" style={{ textTransform: 'capitalize', color: 'var(--color-primary)' }}>
                {tenant?.plan || 'Free'}
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* Team Management Section */}
      <div className="dashboard-card" style={{ marginTop: '1.5rem' }}>
        <h3 style={{ marginBottom: '1.5rem' }}>👥 Team Management</h3>
        
        {isOwnerOrAdmin && (
          <div className="invite-section">
            <h4 style={{ fontSize: '1rem', marginBottom: '1rem' }}>Add New Member</h4>
            {error && <div className="login-error" style={{ marginBottom: '1rem' }}>{error}</div>}
            <form onSubmit={handleSubmit(handleInvite)} className="invite-form">
              <input 
                className="input" 
                type="email" 
                placeholder="colleague@company.com" 
                {...register('email', { required: true })} 
              />
              <input 
                className="input" 
                type="password" 
                placeholder="Temporary Password (min 8 chars)" 
                {...register('password', { required: true, minLength: 8 })} 
              />
              <button type="submit" className="btn btn-primary" disabled={inviteLoading}>
                {inviteLoading ? 'Adding...' : 'Add Member'}
              </button>
            </form>
          </div>
        )}

        <div className="team-list">
          {loadingTeam ? (
            <p style={{ padding: '1rem', color: 'var(--color-text-secondary)' }}>Loading team...</p>
          ) : (
            <table className="team-table">
              <thead>
                <tr>
                  <th>Email</th>
                  <th>Role</th>
                  <th>Joined</th>
                </tr>
              </thead>
              <tbody>
                {team.map(member => (
                  <tr key={member.id}>
                    <td>{member.email}</td>
                    <td style={{ textTransform: 'capitalize' }}>{member.role}</td>
                    <td style={{ color: 'var(--color-text-secondary)' }}>
                      {new Date(member.created_at).toLocaleDateString()}
                    </td>
                  </tr>
                ))}
                {team.length === 0 && (
                  <tr>
                    <td colSpan="3" style={{ textAlign: 'center', color: 'var(--color-text-secondary)' }}>No team members found.</td>
                  </tr>
                )}
              </tbody>
            </table>
          )}
        </div>
      </div>
    </div>
  );
}
