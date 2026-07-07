/**
 * Onboarding Wizard — 3-step tenant provisioning flow.
 *
 * Step 1: Organization name + subdomain
 * Step 2: Plan selection
 * Step 3: Team invites + owner password
 */
import { useState } from 'react';
import { useForm } from 'react-hook-form';
import { useNavigate } from 'react-router-dom';
import client from '../../api/client';
import './Onboarding.css';

const PLANS = [
  {
    id: 'free',
    name: 'Free',
    price: '$0',
    period: '/month',
    features: ['Basic Dashboard', 'Up to 3 Users', 'Community Support', '1 Project'],
    color: 'var(--plan-free)',
  },
  {
    id: 'starter',
    name: 'Starter',
    price: '$29',
    period: '/month',
    features: ['Everything in Free', 'CSV Export', 'API Access', 'Email Support', 'Up to 10 Users', '5 Projects'],
    color: 'var(--plan-starter)',
    popular: false,
  },
  {
    id: 'pro',
    name: 'Pro',
    price: '$99',
    period: '/month',
    features: ['Everything in Starter', 'Advanced Analytics', 'Webhooks', 'SSO Integration', 'Priority Support', 'Up to 50 Users'],
    color: 'var(--plan-pro)',
    popular: true,
  },
  {
    id: 'enterprise',
    name: 'Enterprise',
    price: '$299',
    period: '/month',
    features: ['Everything in Pro', 'Audit Logs', 'Custom Domain', 'Dedicated Support', 'Unlimited Users', 'SLA Guarantee'],
    color: 'var(--plan-enterprise)',
  },
];

export default function OnboardingWizard() {
  const navigate = useNavigate();
  const [step, setStep] = useState(1);
  const [selectedPlan, setSelectedPlan] = useState('free');
  const [error, setError] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);

  const {
    register,
    handleSubmit,
    watch,
    formState: { errors },
    trigger,
    getValues,
  } = useForm({
    defaultValues: {
      displayName: '',
      subdomain: '',
      ownerEmail: '',
      ownerPassword: '',
      confirmPassword: '',
    },
  });

  const subdomain = watch('subdomain');

  const nextStep = async () => {
    let fieldsToValidate = [];
    if (step === 1) fieldsToValidate = ['displayName', 'subdomain'];
    if (step === 3) fieldsToValidate = ['ownerEmail', 'ownerPassword', 'confirmPassword'];

    const isValid = await trigger(fieldsToValidate);
    if (isValid) setStep((s) => Math.min(s + 1, 3));
  };

  const prevStep = () => setStep((s) => Math.max(s - 1, 1));

  const onSubmit = async (formData) => {
    setError('');
    setIsSubmitting(true);

    try {
      await client.post('/api/tenants/provision', {
        display_name: formData.displayName,
        subdomain: formData.subdomain,
        plan: selectedPlan,
        owner_email: formData.ownerEmail,
        owner_password: formData.ownerPassword,
      });

      // Login after provisioning
      const loginRes = await client.post('/api/auth/login', {
        email: formData.ownerEmail,
        password: formData.ownerPassword,
      });

      localStorage.setItem('access_token', loginRes.data.access_token);
      localStorage.setItem('user', JSON.stringify(loginRes.data.user));
      if (loginRes.data.user.tenant_id) {
        localStorage.setItem('tenant_id', loginRes.data.user.tenant_id);
      }

      navigate('/dashboard');
    } catch (err) {
      setError(err.response?.data?.error || 'Failed to create organization. Please try again.');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="onboarding-page">
      <div className="onboarding-bg-glow" />

      <div className="onboarding-container">
        {/* Progress bar */}
        <div className="onboarding-progress">
          {[1, 2, 3].map((s) => (
            <div key={s} className="onboarding-progress-step">
              <div className={`progress-dot ${step >= s ? 'active' : ''} ${step > s ? 'completed' : ''}`}>
                {step > s ? '✓' : s}
              </div>
              <span className={`progress-label ${step >= s ? 'active' : ''}`}>
                {s === 1 ? 'Organization' : s === 2 ? 'Plan' : 'Account'}
              </span>
              {s < 3 && <div className={`progress-line ${step > s ? 'active' : ''}`} />}
            </div>
          ))}
        </div>

        {/* Error */}
        {error && (
          <div className="onboarding-error animate-slide-up">
            <span>⚠️</span> {error}
          </div>
        )}

        <form onSubmit={handleSubmit(onSubmit)}>
          {/* ── Step 1: Organization ────────────────────── */}
          {step === 1 && (
            <div className="onboarding-step animate-slide-up">
              <div className="step-header">
                <h2>Create your organization</h2>
                <p>Tell us about your company to get started.</p>
              </div>

              <div className="step-body">
                <div className="input-group">
                  <label className="input-label" htmlFor="displayName">Organization Name</label>
                  <input
                    id="displayName"
                    className={`input ${errors.displayName ? 'input-error' : ''}`}
                    placeholder="Acme Inc."
                    {...register('displayName', { required: 'Organization name is required' })}
                  />
                  {errors.displayName && <span className="error-text">{errors.displayName.message}</span>}
                </div>

                <div className="input-group">
                  <label className="input-label" htmlFor="subdomain">Subdomain</label>
                  <div className="subdomain-input-wrap">
                    <input
                      id="subdomain"
                      className={`input subdomain-input ${errors.subdomain ? 'input-error' : ''}`}
                      placeholder="acme"
                      {...register('subdomain', {
                        required: 'Subdomain is required',
                        pattern: {
                          value: /^[a-z0-9][a-z0-9-]{1,48}[a-z0-9]$/,
                          message: 'Lowercase letters, numbers, and hyphens only (3-50 chars)',
                        },
                      })}
                    />
                    <span className="subdomain-suffix">.saas.app</span>
                  </div>
                  {errors.subdomain && <span className="error-text">{errors.subdomain.message}</span>}
                  {subdomain && !errors.subdomain && (
                    <span className="subdomain-preview">
                      Your app will be at <strong>{subdomain}.saas.app</strong>
                    </span>
                  )}
                </div>
              </div>

              <div className="step-actions">
                <div />
                <button type="button" className="btn btn-primary btn-lg" onClick={nextStep}>
                  Continue →
                </button>
              </div>
            </div>
          )}

          {/* ── Step 2: Plan Selection ──────────────────── */}
          {step === 2 && (
            <div className="onboarding-step animate-slide-up">
              <div className="step-header">
                <h2>Choose your plan</h2>
                <p>Start free and upgrade as you grow. All plans include a 14-day trial.</p>
              </div>

              <div className="plan-grid">
                {PLANS.map((plan) => (
                  <div
                    key={plan.id}
                    className={`plan-card glass-card ${selectedPlan === plan.id ? 'selected' : ''} ${plan.popular ? 'popular' : ''}`}
                    onClick={() => setSelectedPlan(plan.id)}
                  >
                    {plan.popular && <div className="plan-popular-tag">Most Popular</div>}
                    <div className="plan-card-header">
                      <h3 className="plan-card-name" style={{ color: plan.color }}>{plan.name}</h3>
                      <div className="plan-card-price">
                        <span className="plan-price-amount">{plan.price}</span>
                        <span className="plan-price-period">{plan.period}</span>
                      </div>
                    </div>
                    <ul className="plan-card-features">
                      {plan.features.map((feat, i) => (
                        <li key={i}>
                          <span className="plan-check" style={{ color: plan.color }}>✓</span>
                          {feat}
                        </li>
                      ))}
                    </ul>
                    <div className={`plan-card-radio ${selectedPlan === plan.id ? 'checked' : ''}`}>
                      {selectedPlan === plan.id && <div className="plan-card-radio-dot" />}
                    </div>
                  </div>
                ))}
              </div>

              <div className="step-actions">
                <button type="button" className="btn btn-ghost" onClick={prevStep}>
                  ← Back
                </button>
                <button type="button" className="btn btn-primary btn-lg" onClick={nextStep}>
                  Continue →
                </button>
              </div>
            </div>
          )}

          {/* ── Step 3: Account Setup ──────────────────── */}
          {step === 3 && (
            <div className="onboarding-step animate-slide-up">
              <div className="step-header">
                <h2>Set up your account</h2>
                <p>Create the owner account for your organization.</p>
              </div>

              <div className="step-body">
                <div className="input-group">
                  <label className="input-label" htmlFor="ownerEmail">Email</label>
                  <input
                    id="ownerEmail"
                    type="email"
                    className={`input ${errors.ownerEmail ? 'input-error' : ''}`}
                    placeholder="you@company.com"
                    {...register('ownerEmail', {
                      required: 'Email is required',
                      pattern: {
                        value: /^[^\s@]+@[^\s@]+\.[^\s@]+$/,
                        message: 'Invalid email address',
                      },
                    })}
                  />
                  {errors.ownerEmail && <span className="error-text">{errors.ownerEmail.message}</span>}
                </div>

                <div className="input-group">
                  <label className="input-label" htmlFor="ownerPassword">Password</label>
                  <input
                    id="ownerPassword"
                    type="password"
                    className={`input ${errors.ownerPassword ? 'input-error' : ''}`}
                    placeholder="Min. 8 characters"
                    {...register('ownerPassword', {
                      required: 'Password is required',
                      minLength: { value: 8, message: 'At least 8 characters' },
                    })}
                  />
                  {errors.ownerPassword && <span className="error-text">{errors.ownerPassword.message}</span>}
                </div>

                <div className="input-group">
                  <label className="input-label" htmlFor="confirmPassword">Confirm Password</label>
                  <input
                    id="confirmPassword"
                    type="password"
                    className={`input ${errors.confirmPassword ? 'input-error' : ''}`}
                    placeholder="Re-enter password"
                    {...register('confirmPassword', {
                      required: 'Please confirm your password',
                      validate: (val) => val === getValues('ownerPassword') || 'Passwords do not match',
                    })}
                  />
                  {errors.confirmPassword && <span className="error-text">{errors.confirmPassword.message}</span>}
                </div>

                {/* Summary */}
                <div className="onboarding-summary glass-card">
                  <h4>Summary</h4>
                  <div className="summary-row">
                    <span>Organization</span>
                    <strong>{getValues('displayName') || '—'}</strong>
                  </div>
                  <div className="summary-row">
                    <span>Subdomain</span>
                    <strong>{getValues('subdomain') || '—'}.saas.app</strong>
                  </div>
                  <div className="summary-row">
                    <span>Plan</span>
                    <strong className={`badge badge-${selectedPlan}`}>{selectedPlan}</strong>
                  </div>
                </div>
              </div>

              <div className="step-actions">
                <button type="button" className="btn btn-ghost" onClick={prevStep}>
                  ← Back
                </button>
                <button
                  type="submit"
                  className="btn btn-primary btn-lg"
                  disabled={isSubmitting}
                >
                  {isSubmitting ? (
                    <>
                      <span className="loading-spinner-sm" />
                      Creating...
                    </>
                  ) : (
                    'Create Organization 🚀'
                  )}
                </button>
              </div>
            </div>
          )}
        </form>
      </div>
    </div>
  );
}
