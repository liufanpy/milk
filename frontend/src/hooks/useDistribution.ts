import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { distributionApi } from '../services/api';

export function useDistributions(params?: any) {
  return useQuery({ queryKey: ['distributions', params], queryFn: () => distributionApi.list(params) });
}
export function useCreateDistribution() {
  const qc = useQueryClient();
  return useMutation({ mutationFn: distributionApi.create, onSuccess: () => qc.invalidateQueries({ queryKey: ['distributions'] }) });
}
export function useSettleDistribution() {
  const qc = useQueryClient();
  return useMutation({ mutationFn: ({ id, amount }: { id: number; amount: number }) => distributionApi.settle(id, amount), onSuccess: () => qc.invalidateQueries({ queryKey: ['distributions'] }) });
}
export function useExchangeDistribution() {
  const qc = useQueryClient();
  return useMutation({ mutationFn: ({ id, data }: { id: number; data: any }) => distributionApi.exchange(id, data), onSuccess: () => qc.invalidateQueries({ queryKey: ['distributions'] }) });
}
