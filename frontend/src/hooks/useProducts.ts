import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { productApi } from '../services/api';

export function useProducts(keyword = '') {
  return useQuery({ queryKey: ['products', keyword], queryFn: () => productApi.list(keyword) });
}
export function useCreateProduct() {
  const qc = useQueryClient();
  return useMutation({ mutationFn: productApi.create, onSuccess: () => qc.invalidateQueries({ queryKey: ['products'] }) });
}
export function useUpdateProduct() {
  const qc = useQueryClient();
  return useMutation({ mutationFn: ({ id, data }: { id: number; data: any }) => productApi.update(id, data), onSuccess: () => qc.invalidateQueries({ queryKey: ['products'] }) });
}
export function useDeleteProduct() {
  const qc = useQueryClient();
  return useMutation({ mutationFn: productApi.delete, onSuccess: () => qc.invalidateQueries({ queryKey: ['products'] }) });
}
