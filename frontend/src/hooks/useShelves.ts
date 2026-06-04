import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { shelfApi } from '../services/api';

export function useShelves() {
  return useQuery({ queryKey: ['shelves'], queryFn: () => shelfApi.list() });
}
export function useCreateShelf() {
  const qc = useQueryClient();
  return useMutation({ mutationFn: shelfApi.create, onSuccess: () => qc.invalidateQueries({ queryKey: ['shelves'] }) });
}
export function useUpdateShelf() {
  const qc = useQueryClient();
  return useMutation({ mutationFn: ({ id, data }: { id: number; data: any }) => shelfApi.update(id, data), onSuccess: () => qc.invalidateQueries({ queryKey: ['shelves'] }) });
}
export function useDeleteShelf() {
  const qc = useQueryClient();
  return useMutation({ mutationFn: shelfApi.delete, onSuccess: () => qc.invalidateQueries({ queryKey: ['shelves'] }) });
}
