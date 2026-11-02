import { flushPromises, mount } from '@vue/test-utils'
import { afterEach, describe, expect, it, vi } from 'vitest'
import PatternWidget from '../PatternWidget.vue'
import type { HabitPatternItem, PredictionItem } from '@/types'

const PATTERNS: HabitPatternItem[] = [
  {
    id: 1,
    trigger_sequence: 'Google Chrome',
    predicted_action: 'Code',
    occurrence_count: 3,
    confidence: 0.75,
    last_triggered: null,
  },
]

const PREDICTIONS: PredictionItem[] = [
  { id: 7, timestamp: '2026-10-29T09:00:00Z', trigger_sequence: 'Google Chrome', suggested_action: 'Code', status: 'accepted' },
]

afterEach(() => {
  vi.unstubAllGlobals()
})

describe('PatternWidget', () => {
  it('shows both empty states when nothing has been learned yet', () => {
    const wrapper = mount(PatternWidget)

    expect(wrapper.text()).toContain('No repetitive workflows detected yet.')
    expect(wrapper.text()).toContain('No notifications triggered yet.')
  })

  it('shows a learned habit with its confidence and count', () => {
    const wrapper = mount(PatternWidget, { props: { patterns: PATTERNS } })

    expect(wrapper.find('.src-chip').text()).toBe('Google Chrome')
    expect(wrapper.find('.dst-chip').text()).toBe('Code')
    expect(wrapper.find('.conf-badge').text()).toBe('75% confidence')
    expect(wrapper.find('.conf-badge').classes()).toContain('conf-high')
    expect(wrapper.find('.count-label').text()).toBe('3x observed')
  })

  it('shows a prediction with its feedback status', () => {
    const wrapper = mount(PatternWidget, { props: { recentPredictions: PREDICTIONS } })

    expect(wrapper.find('.pred-text').text()).toBe('Suggested Code after Google Chrome')
    expect(wrapper.find('.status-pill').classes()).toContain('status-accepted')
  })

  it('retrains through the API and tells the dashboard to reload', async () => {
    const fetchMock = vi.fn().mockResolvedValue({ ok: true, json: async () => ({ message: 'ok' }) })
    vi.stubGlobal('fetch', fetchMock)
    const wrapper = mount(PatternWidget)

    await wrapper.find('.retrain-btn').trigger('click')
    await flushPromises()

    expect(fetchMock).toHaveBeenCalledWith('/api/patterns/retrain', { method: 'POST' })
    expect(wrapper.emitted('retrain')).toHaveLength(1)
  })

  it('does not tell the dashboard to reload when retraining fails', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: false, status: 500 }))
    const wrapper = mount(PatternWidget)

    await wrapper.find('.retrain-btn').trigger('click')
    await flushPromises()

    expect(wrapper.emitted('retrain')).toBeUndefined()
  })
})
