import { flushPromises, mount } from '@vue/test-utils'
import { afterEach, describe, expect, it, vi } from 'vitest'
import SummaryCard from '../SummaryCard.vue'
import type { DailySummary } from '@/types'

function summary(overrides: Partial<DailySummary> = {}): DailySummary {
  return {
    day: '2026-10-29',
    headline: 'Styling the dashboard',
    focus_areas: ['style.css', 'ai-project.md'],
    insight: 'Your focus blocks were short today.',
    suggestion: 'Block one hour for deep work tomorrow.',
    time_split: [
      { app_name: 'Code', minutes: 90 },
      { app_name: 'Google Chrome', minutes: 30 },
    ],
    active_minutes: 120,
    category_minutes: { work: 90, fun: 30 },
    source: 'llm',
    model: 'llama3.2:3b',
    attempts: 1,
    is_partial: false,
    generated_at: '2026-10-30T08:00:00Z',
    notice: null,
    ...overrides,
  }
}

// fetch that answers each call with the next body; `false` means an HTTP 500
function stubFetch(...bodies: Array<DailySummary | false>) {
  const fetchMock = vi.fn()
  for (const body of bodies) {
    fetchMock.mockResolvedValueOnce(
      body === false ? { ok: false, status: 500, json: async () => ({}) } : { ok: true, json: async () => body },
    )
  }
  vi.stubGlobal('fetch', fetchMock)
  return fetchMock
}

function requestedParams(fetchMock: ReturnType<typeof vi.fn>, call: number): URLSearchParams {
  const url = String(fetchMock.mock.calls[call]?.[0])
  return new URLSearchParams(url.split('?')[1])
}

function localIsoDate(offsetDays: number): string {
  const d = new Date()
  d.setDate(d.getDate() + offsetDays)
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
}

async function mountCard() {
  const wrapper = mount(SummaryCard)
  await flushPromises()
  return wrapper
}

afterEach(() => {
  vi.unstubAllGlobals()
})

describe('SummaryCard', () => {
  it("loads yesterday's summary and shows the model's text and the digest numbers", async () => {
    const fetchMock = stubFetch(summary())

    const wrapper = await mountCard()

    expect(requestedParams(fetchMock, 0).get('day')).toBe(localIsoDate(-1))
    expect(requestedParams(fetchMock, 0).get('refresh')).toBe('false')
    expect(wrapper.find('.headline').text()).toBe('Styling the dashboard')
    expect(wrapper.find('.badge-ai').text()).toBe('AI · llama3.2:3b')
    expect(wrapper.findAll('.focus-list li').map((li) => li.text())).toEqual(['style.css', 'ai-project.md'])
    expect(wrapper.findAll('.split-minutes').map((el) => el.text())).toEqual(['1 h 30 min', '30 min'])
  })

  it('marks a fallback summary and shows why the AI was not used', async () => {
    stubFetch(summary({ source: 'fallback', model: null, notice: 'AI not available: Ollama is not running' }))

    const wrapper = await mountCard()

    expect(wrapper.find('.badge-basic').text()).toBe('Basic summary')
    expect(wrapper.find('.notice').text()).toContain('AI not available')
  })

  it('shows the empty state for a day without activity', async () => {
    stubFetch(summary({ active_minutes: 0, time_split: [] }))

    const wrapper = await mountCard()

    expect(wrapper.text()).toContain('No activity recorded on')
    expect(wrapper.find('.headline').exists()).toBe(false)
  })

  it('shows an error when the API fails', async () => {
    stubFetch(false)

    const wrapper = await mountCard()

    expect(wrapper.find('.state-error').text()).toContain('Could not load the summary')
  })

  it('asks for a new summary when refresh is clicked', async () => {
    const fetchMock = stubFetch(summary(), summary({ headline: 'Second version' }))
    const wrapper = await mountCard()

    await wrapper.find('.icon-btn').trigger('click')
    await flushPromises()

    expect(requestedParams(fetchMock, 1).get('refresh')).toBe('true')
    expect(wrapper.find('.headline').text()).toBe('Second version')
  })

  it('loads the day picked in the date picker', async () => {
    const fetchMock = stubFetch(summary(), summary({ day: '2026-10-22' }))
    const wrapper = await mountCard()

    await wrapper.find('input[type="date"]').setValue('2026-10-22')
    await flushPromises()

    expect(requestedParams(fetchMock, 1).get('day')).toBe('2026-10-22')
  })
})
