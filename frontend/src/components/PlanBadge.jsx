/**
 * PlanBadge component.
 *
 * Renders a colored badge based on the plan name.
 * free=gray, starter=blue, pro=purple, enterprise=gold.
 */
export default function PlanBadge({ plan }) {
  const planClass = `badge badge-${plan || 'free'}`;
  return <span className={planClass}>{plan || 'free'}</span>;
}
