/**
 * Login Page
 *
 * Supports both tenant-user and superadmin login.
 * Uses react-hook-form for validation.
 */
import { useState } from 'react';
import { useForm } from 'react-hook-form';
import { useNavigate, Link } from 'react-router-dom';
import useTenantStore from '../../context/TenantContext';
import './Login.css';

export default function LoginPage() {
  const navigate = useNavigate();
  const login = useTenantStore((s) => s.login);
  const [error, setError] = useState('');
  const [isLoading, setIsLoading] = useState(false);

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm();

  const onSubmit = async (formData) => {
    setError('');
    setIsLoading(true);

    try {
      const result = await login(formData.email, formData.password, formData.tenantId || undefined);
      const user = result.user;

      if (user.is_superadmin) {
        navigate('/superadmin');
      } else {
        navigate('/dashboard');
      }
    } catch (err) {
      setError(err.response?.data?.error || 'Login failed. Please check your credentials.');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="login-page">
      <div className="login-bg-glow" />

      <div className="login-container animate-scale-in">
        {/* Logo / Brand */}
        <div className="login-header">
          <div className="login-logo">
            <svg width="40" height="40" viewBox="0 0 40 40" fill="none">
              <rect width="40" height="40" rx="10" fill="url(#logo-gradient)" />
              <path d="M12 20L18 14L24 20L18 26Z" fill="white" fillOpacity="0.9" />
              <path d="M18 14L24 20L30 14L24 8Z" fill="white" fillOpacity="0.6" />
              <defs>
                <linearGradient id="logo-gradient" x1="0" y1="0" x2="40" y2="40">
                  <stop stopColor="#7c5cff" />
                  <stop offset="1" stopColor="#00d4aa" />
                </linearGradient>
              </defs>
            </svg>
          </div>
          <h1 className="login-title">Welcome back</h1>
          <p className="login-subtitle">Sign in to your SaaS dashboard</p>
        </div>

        {/* Error message */}
        {error && (
          <div className="login-error animate-slide-up">
            <span className="login-error-icon">⚠️</span>
            {error}
          </div>
        )}

        {/* Login form */}
        <form onSubmit={handleSubmit(onSubmit)} className="login-form">
          <div className="input-group">
            <label className="input-label" htmlFor="email">Email</label>
            <input
              id="email"
              type="email"
              className={`input ${errors.email ? 'input-error' : ''}`}
              placeholder="you@company.com"
              autoComplete="email"
              {...register('email', {
                required: 'Email is required',
                pattern: {
                  value: /^[^\s@]+@[^\s@]+\.[^\s@]+$/,
                  message: 'Invalid email address',
                },
              })}
            />
            {errors.email && <span className="error-text">{errors.email.message}</span>}
          </div>

          <div className="input-group">
            <label className="input-label" htmlFor="password">Password</label>
            <input
              id="password"
              type="password"
              className={`input ${errors.password ? 'input-error' : ''}`}
              placeholder="••••••••"
              autoComplete="current-password"
              {...register('password', {
                required: 'Password is required',
                minLength: {
                  value: 6,
                  message: 'Password must be at least 6 characters',
                },
              })}
            />
            {errors.password && <span className="error-text">{errors.password.message}</span>}
          </div>

          <div className="input-group">
            <label className="input-label" htmlFor="tenantId">
              Tenant ID <span className="optional-tag">optional</span>
            </label>
            <input
              id="tenantId"
              type="text"
              className="input"
              placeholder="For local dev without subdomain"
              {...register('tenantId')}
            />
          </div>

          <button
            type="submit"
            className="btn btn-primary btn-lg login-submit"
            disabled={isLoading}
          >
            {isLoading ? (
              <>
                <span className="loading-spinner-sm" />
                Signing in...
              </>
            ) : (
              'Sign In'
            )}
          </button>
        </form>

        <div className="login-footer">
          <p>
            Don't have an account?{' '}
            <Link to="/onboarding">Create your organization</Link>
          </p>
        </div>
      </div>
    </div>
  );
}
