/**
 * Hook: useBilling
 * Returns { plan, limits, usage, allPlans, upgrade(newPlan) }.
 */
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import client from '../api/client';

export default function useBilling() {
  const queryClient = useQueryClient();

  const { data, isLoading } = useQuery({
    queryKey: ['billing', 'plan'],
    queryFn: async () => {
      const { data } = await client.get('/api/billing/plan');
      return data;
    },
    retry: false,
  });

  const upgradeMutation = useMutation({
    mutationFn: async ({ tenantId, newPlan }) => {
      const { data } = await client.post('/api/billing/upgrade', {
        tenant_id: tenantId,
        new_plan: newPlan,
      });
      return data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['billing'] });
      queryClient.invalidateQueries({ queryKey: ['features'] });
    },
  });

  return {
    plan: data?.plan || null,
    limits: data?.limits || {},
    usage: data?.usage || {},
    features: data?.features || [],
    allPlans: data?.all_plans || {},
    isLoading,
    upgrade: upgradeMutation.mutate,
    isUpgrading: upgradeMutation.isPending,
  };
}
