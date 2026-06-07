import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { returnApi } from '../services/api';

export function useReturns() {
  return useQuery({ queryKey: ['returns'], queryFn: returnApi.list });
}

export function useReturnDetail(id: number | null) {
  return useQuery({
    queryKey: ['returns', id],
    queryFn: () => returnApi.get(id!),
    enabled: !!id,
  });
}

export function useCreateReturn() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: returnApi.create,
    onSuccess: () => qc.invalidateQueries({ queryKey: ['returns'] }),
  });
}

export function useCancelReturn() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: returnApi.cancel,
    onSuccess: () => qc.invalidateQueries({ queryKey: ['returns'] }),
  });
}
