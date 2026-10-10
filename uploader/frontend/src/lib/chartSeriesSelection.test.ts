import { describe, expect, it } from 'vitest'
import { BENCHMARK_KEYS } from '../data/performance'
import {
  combinationIsValid,
  toggleSetMember,
  visibleProgramModeKeys,
} from './chartSeriesSelection'

describe('toggleSetMember', () => {
  it('adds and removes TCP independently', () => {
    let hidden = new Set<'TCP'>()
    hidden = toggleSetMember(hidden, 'TCP')
    expect(hidden.has('TCP')).toBe(true)
    hidden = toggleSetMember(hidden, 'TCP')
    expect(hidden.has('TCP')).toBe(false)
  })

  it('toggles SPX, NDX, and BTC independently', () => {
    let enabled = new Set<'SPX' | 'NDX' | 'BTC'>(['SPX', 'NDX'])
    enabled = toggleSetMember(enabled, 'BTC')
    expect([...enabled].sort()).toEqual(['BTC', 'NDX', 'SPX'])
    enabled = toggleSetMember(enabled, 'SPX')
    expect(enabled.has('SPX')).toBe(false)
    expect(enabled.has('NDX')).toBe(true)
    expect(enabled.has('BTC')).toBe(true)
    enabled = toggleSetMember(enabled, 'NDX')
    expect([...enabled]).toEqual(['BTC'])
  })
})

describe('visibleProgramModeKeys', () => {
  it('supports TCP only', () => {
    expect(visibleProgramModeKeys('TCP', false, new Set())).toEqual(['TCP'])
  })

  it('supports TCP + each benchmark independently', () => {
    expect(visibleProgramModeKeys('TCP', false, new Set(['BTC']))).toEqual(['TCP', 'BTC'])
    expect(visibleProgramModeKeys('TCP', false, new Set(['SPX']))).toEqual(['TCP', 'SPX'])
    expect(visibleProgramModeKeys('TCP', false, new Set(['NDX']))).toEqual(['TCP', 'NDX'])
  })

  it('supports the full TCP + SPX + NDX + BTC combination', () => {
    expect(visibleProgramModeKeys('TCP', false, new Set([...BENCHMARK_KEYS]))).toEqual([
      'TCP',
      'SPX',
      'NDX',
      'BTC',
    ])
  })

  it('can hide TCP while leaving benchmarks visible', () => {
    expect(visibleProgramModeKeys('TCP', true, new Set(['SPX', 'BTC']))).toEqual(['SPX', 'BTC'])
  })
})

describe('combinationIsValid', () => {
  const combos: Array<[boolean, Array<'SPX' | 'NDX' | 'BTC'>]> = [
    [false, []],
    [false, ['BTC']],
    [false, ['SPX']],
    [false, ['NDX']],
    [false, ['SPX', 'NDX', 'BTC']],
    [true, ['SPX']],
  ]
  it('accepts arbitrary program/benchmark combinations', () => {
    for (const [hidden, benches] of combos) {
      expect(combinationIsValid('TCP', hidden, benches)).toBe(true)
    }
  })
})
