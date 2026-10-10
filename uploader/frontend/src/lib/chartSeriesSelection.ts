import { BENCHMARK_KEYS, type BenchmarkKey, type ProductKey, type SeriesKey } from '../data/performance'

export function toggleSetMember<T>(prev: Set<T>, key: T): Set<T> {
  const next = new Set(prev)
  if (next.has(key)) next.delete(key)
  else next.add(key)
  return next
}

export function visibleProgramModeKeys(
  program: ProductKey,
  programHidden: boolean,
  enabledBenchmarks: Set<BenchmarkKey>,
): SeriesKey[] {
  const keys: SeriesKey[] = []
  if (!programHidden) keys.push(program)
  for (const key of BENCHMARK_KEYS) {
    if (enabledBenchmarks.has(key)) keys.push(key)
  }
  return keys
}

export function combinationIsValid(
  program: ProductKey,
  programHidden: boolean,
  enabledBenchmarks: ReadonlyArray<BenchmarkKey>,
): boolean {
  const enabled = new Set(enabledBenchmarks)
  const keys = visibleProgramModeKeys(program, programHidden, enabled)
  return keys.every((key) => key === program || (BENCHMARK_KEYS as string[]).includes(key))
}
