import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { customerApi } from '../services/api';

export function useCustomers(keyword = '') {
  return useQuery({ queryKey: ['customers', keyword], queryFn: () => customerApi.list(keyword) });
}
export function useCreateCustomer() {
  const qc = useQueryClient();
  return useMutation({ mutationFn: customerApi.create, onSuccess: () => qc.invalidateQueries({ queryKey: ['customers'] }) });
}
export function useUpdateCustomer() {
  const qc = useQueryClient();
  return useMutation({ mutationFn: ({ id, data }: { id: number; data: any }) => customerApi.update(id, data), onSuccess: () => qc.invalidateQueries({ queryKey: ['customers'] }) });
}
export function useDeleteCustomer() {
  const qc = useQueryClient();
  return useMutation({ mutationFn: customerApi.delete, onSuccess: () => qc.invalidateQueries({ queryKey: ['customers'] }) });
}
export function useCustomerPrices(customerId: number | null) {
  return useQuery({ queryKey: ['customer-prices', customerId], queryFn: () => customerApi.getPrices(customerId!), enabled: !!customerId });
}
export function useAddCustomerPrice() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ customerId, productId, price }: { customerId: number; productId: number; price: number }) => customerApi.addPrice(customerId, productId, price),
    onSuccess: (_data, variables) => qc.invalidateQueries({ queryKey: ['customer-prices', variables.customerId] }),
  });
}
export function useDeleteCustomerPrice() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ customerId, priceId }: { customerId: number; priceId: number }) => customerApi.deletePrice(customerId, priceId),
    onSuccess: (_data, variables) => qc.invalidateQueries({ queryKey: ['customer-prices', variables.customerId] }),
  });
}
