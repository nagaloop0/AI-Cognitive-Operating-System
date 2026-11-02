import { describe, expect, it } from 'vitest'
import { DEMO_NO_AI_MESSAGE, DEMO_READ_ONLY_MESSAGE, demoFileFor, demoWriteResponse } from '@/api'

const SAMPLES = [{ question: 'What did I work on yesterday?', answer: { answer: 'You worked on shop-api.' } }]

function post(body: unknown): RequestInit {
  return { method: 'POST', body: JSON.stringify(body) }
}

describe('demo mode', () => {
  it('maps dashboard GET requests to demo JSON files', () => {
    expect(demoFileFor('/api/stats/dashboard?limit=15')).toBe('stats-dashboard.json')
    expect(demoFileFor('/api/assistant/messages?limit=10')).toBe('assistant-messages.json')
    expect(demoFileFor('/api/summary/daily?day=2026-10-30&refresh=false')).toBe('summary-2026-10-30.json')
  })

  it('has no file for requests outside the demo', () => {
    expect(demoFileFor('/api/settings')).toBeNull()
    expect(demoFileFor('/api/summary/daily')).toBeNull()
  })

  it.each([
    '/api/control/clear-history',
    '/api/control/toggle',
    '/api/patterns/retrain',
    '/api/settings',
    '/api/categories',
    '/api/assistant/messages/1/read',
  ])('refuses the write %s', async (path) => {
    const response = demoWriteResponse(path, post({}), SAMPLES)

    expect(response.status).toBe(403)
    expect(await response.json()).toEqual({ detail: DEMO_READ_ONLY_MESSAGE })
  })

  it('answers an example question with its stored sample, ignoring case and spaces', async () => {
    const response = demoWriteResponse('/api/ask', post({ question: '  what did I work on YESTERDAY? ' }), SAMPLES)

    expect(response.status).toBe(200)
    expect(await response.json()).toEqual({ answer: 'You worked on shop-api.' })
  })

  it('explains that other questions need the local AI', async () => {
    const response = demoWriteResponse('/api/ask', post({ question: 'Did I go to the gym?' }), SAMPLES)

    expect(response.status).toBe(503)
    expect(await response.json()).toEqual({ detail: DEMO_NO_AI_MESSAGE })
  })
})
