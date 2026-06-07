import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { wastageApi } from '../services/api';

export function useWastage() {
  return useQuery({ queryKey: ['wastage'], queryFn: wastageApi.list });
}

export function useWastageDetail(id: number | null) {
  return useQuery({
    queryKey: ['wastage', id],
    queryFn: () => wastageApi.get(id!),
    enabled: !!id,
  });
}

export function useCreateWastage() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: wastageApi.create,
    onSuccess: () => qc.invalidateQueries({ queryKey: ['wastage'] }),
  });
}

export function useCancelWastage() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: wastageApi.cancel,
    onSuccess: () => qc.invalidateQueries({ queryKey: ['wastage'] }),
  });
}
