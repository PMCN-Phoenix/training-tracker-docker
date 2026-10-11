import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { api } from './client.js'

export const qk = {
  exercise: (ex, range) => ['exercise', ex, range],
  prTests: (range) => ['prTests', range],
  calendar: () => ['calendar'],
  reflections: (filters) => ['reflections', filters],
  reflection: (id) => ['reflection', id],
  stats: () => ['stats'],
  day: (date) => ['day', date],
}

export function useCalendar() {
  return useQuery({
    queryKey: qk.calendar(),
    queryFn: async () => (await api.calendar()).data,
  })
}

export function useExercise(exercise, range = {}) {
  return useQuery({
    queryKey: qk.exercise(exercise, range),
    queryFn: async () => (await api.exercise(exercise, range)).data,
    enabled: Boolean(exercise),
  })
}

export function usePrTests(range = {}) {
  return useQuery({
    queryKey: qk.prTests(range),
    queryFn: async () => (await api.prTests(range)).data,
  })
}

export function useReflections(filters = {}) {
  return useQuery({
    queryKey: qk.reflections(filters),
    queryFn: async () => {
      const d = await api.reflections(filters)
      // 后端为 {code,data:{items,total}}，前端组件消费裸数组
      return Array.isArray(d) ? d : (d.data?.items || [])
    },
  })
}

export function useStats() {
  return useQuery({
    queryKey: qk.stats(),
    queryFn: async () => (await api.stats()).data,
  })
}

export function useDay(date) {
  return useQuery({
    queryKey: qk.day(date),
    queryFn: async () => (await api.day(date)).data,
    enabled: Boolean(date),
  })
}

export function useReflectionMutations() {
  const qc = useQueryClient()
  const invalidate = () => {
    qc.invalidateQueries({ queryKey: ['reflections'] })
    qc.invalidateQueries({ queryKey: ['stats'] })
    qc.invalidateQueries({ queryKey: ['day'] })
  }
  const create = useMutation({ mutationFn: api.createReflection, onSuccess: invalidate })
  const update = useMutation({
    mutationFn: ({ id, payload }) => api.updateReflection(id, payload),
    onSuccess: invalidate,
  })
  const remove = useMutation({ mutationFn: api.deleteReflection, onSuccess: invalidate })
  return { create, update, remove }
}
