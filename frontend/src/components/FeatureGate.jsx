/**
 * FeatureGate component.
 *
 * Conditionally renders children based on feature flag status.
 * Shows fallback (or upgrade prompt) if flag is disabled.
 */
import useFeatureFlag from '../hooks/useFeatureFlag';
import './FeatureGate.css';

export default function FeatureGate({ flagName, children, fallback }) {
  const isEnabled = useFeatureFlag(flagName);

  if (isEnabled) {
    return children;
  }

  if (fallback) {
    return fallback;
  }

  // Default: upgrade prompt
  return (
    <div className="feature-gate-locked">
      <div className="feature-gate-icon">🔒</div>
      <h3 className="feature-gate-title">Feature Locked</h3>
      <p className="feature-gate-text">
        <strong>{flagName.replace(/_/g, ' ')}</strong> is not available on your
        current plan. Upgrade to unlock this feature.
      </p>
      <button className="btn btn-primary btn-sm" onClick={() => window.location.href = '/dashboard'}>
        View Plans
      </button>
    </div>
  );
}
