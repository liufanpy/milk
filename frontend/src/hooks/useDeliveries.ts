import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { deliveryApi } from '../services/api';

export function useDeliveries(params?: any) {
  return useQuery({ queryKey: ['deliveries', params], queryFn: () => deliveryApi.list(params) });
}
export function useCreateDelivery() {
  const qc = useQueryClient();
  return useMutation({ mutationFn: deliveryApi.create, onSuccess: () => qc.invalidateQueries({ queryKey: ['deliveries'] }) });
}
export function useSettleDelivery() {
  const qc = useQueryClient();
  return useMutation({ mutationFn: ({ id, amount }: { id: number; amount: number }) => deliveryApi.settle(id, amount), onSuccess: () => qc.invalidateQueries({ queryKey: ['deliveries'] }) });
}
export function useExchangeDelivery() {
  const qc = useQueryClient();
  return useMutation({ mutationFn: ({ id, data }: { id: number; data: any }) => deliveryApi.exchange(id, data), onSuccess: () => qc.invalidateQueries({ queryKey: ['deliveries'] }) });
}
