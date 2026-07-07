/**
 * Hook: useFeatureFlag
 * Returns boolean: whether the given flag is enabled for the current tenant.
 */
import useTenantStore from '../context/TenantContext';

export default function useFeatureFlag(flagName) {
  const featureFlags = useTenantStore((s) => s.featureFlags);
  const flag = featureFlags.find((f) => f.flag_name === flagName);
  return flag?.enabled ?? false;
}
