import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { supplierApi } from '../services/api';

export function useSuppliers(keyword = '') {
  return useQuery({ queryKey: ['suppliers', keyword], queryFn: () => supplierApi.list(keyword) });
}
export function useCreateSupplier() {
  const qc = useQueryClient();
  return useMutation({ mutationFn: supplierApi.create, onSuccess: () => qc.invalidateQueries({ queryKey: ['suppliers'] }) });
}
export function useUpdateSupplier() {
  const qc = useQueryClient();
  return useMutation({ mutationFn: ({ id, data }: { id: number; data: any }) => supplierApi.update(id, data), onSuccess: () => qc.invalidateQueries({ queryKey: ['suppliers'] }) });
}
export function useDeleteSupplier() {
  const qc = useQueryClient();
  return useMutation({ mutationFn: supplierApi.delete, onSuccess: () => qc.invalidateQueries({ queryKey: ['suppliers'] }) });
}
