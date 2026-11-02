// One front door for every API call.
// Normal build: a plain fetch to the local FastAPI server (through the Vite proxy).
// Demo build (`vite build --mode demo`, for GitHub Pages): no server exists, so GET requests read
// pre-generated JSON files made from fake data, and every write is refused.

export const IS_DEMO = import.meta.env.VITE_DEMO === 'true'

export const DEMO_READ_ONLY_MESSAGE = 'This is a read-only demo with fake data. Changes are disabled.'
export const DEMO_NO_AI_MESSAGE =
  'The online demo has no AI model. Try one of the example questions, or run the project locally with Ollama.'

const DEMO_DATA_URL = `${import.meta.env.BASE_URL}demo-data/`

export interface DemoAnswer {
  question: string
  answer: unknown
}

/** Which demo JSON file answers a GET request, e.g. "/api/summary/daily?day=2026-10-30" -> "summary-2026-10-30.json". */
export function demoFileFor(path: string): string | null {
  const [route, query = ''] = path.split('?')
  const params = new URLSearchParams(query)
  if (route === '/api/stats/dashboard') return 'stats-dashboard.json'
  if (route === '/api/assistant/messages') return 'assistant-messages.json'
  if (route === '/api/summary/daily' && params.get('day')) return `summary-${params.get('day')}.json`
  return null
}

function jsonResponse(status: number, body: unknown): Response {
  return new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json' } })
}

/** Answer for a POST in the demo: a stored sample for the example questions, a refusal for everything else. */
export function demoWriteResponse(path: string, init: RequestInit | undefined, askSamples: DemoAnswer[]): Response {
  if (path === '/api/ask') {
    const question = String(JSON.parse(String(init?.body ?? '{}')).question ?? '').trim().toLowerCase()
    const sample = askSamples.find((s) => s.question.trim().toLowerCase() === question)
    return sample ? jsonResponse(200, sample.answer) : jsonResponse(503, { detail: DEMO_NO_AI_MESSAGE })
  }
  return jsonResponse(403, { detail: DEMO_READ_ONLY_MESSAGE })
}

let askSamples: Promise<DemoAnswer[]> | null = null

function loadAskSamples(): Promise<DemoAnswer[]> {
  askSamples ??= fetch(`${DEMO_DATA_URL}ask-samples.json`).then((res) => (res.ok ? res.json() : []))
  return askSamples
}

export async function apiFetch(path: string, init?: RequestInit): Promise<Response> {
  if (!IS_DEMO) return fetch(path, init)

  const method = (init?.method ?? 'GET').toUpperCase()
  if (method !== 'GET') return demoWriteResponse(path, init, await loadAskSamples())

  const file = demoFileFor(path)
  if (!file) return jsonResponse(404, { detail: 'Not part of the demo' })
  return fetch(`${DEMO_DATA_URL}${file}`)
}

export interface DemoManifest {
  days: string[]
  latest_day: string
  note: string
}

export async function loadDemoManifest(): Promise<DemoManifest | null> {
  if (!IS_DEMO) return null
  const res = await fetch(`${DEMO_DATA_URL}manifest.json`)
  return res.ok ? ((await res.json()) as DemoManifest) : null
}
