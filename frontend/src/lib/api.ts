const token = () => localStorage.getItem('access_token')

async function req<T>(path: string): Promise<T> {
  const res = await fetch(path, {
    headers: token() ? { Authorization: `Bearer ${token()}` } : {},
  })
  if (res.status === 401) throw new Error('unauthorized')
  if (!res.ok) throw new Error(`${res.status}`)
  return res.json()
}

export type ReviewRow = {
  id: string; job_id: string; status: string; findings_count: number
  duration_ms: number | null; repo: string; pr_number: number
  pr_title: string; created_at: string
}
export type Finding = {
  source: string; title: string; severity: string; category: string
  confidence: number | null; file: string; line: number; detail: Record<string, unknown>
}
export type ReviewDetail = {
  id: string; job_id: string; status: string; head_sha: string
  duration_ms: number | null; findings: Finding[]
}
export type Repo = { id: string; full_name: string; active: boolean; review_count: number }
export type Metrics = {
  total_reviews: number; success: number; failed: number
  success_rate: number | null; avg_duration_ms: number | null
  findings_by_severity: Record<string, number>
  findings_by_category: Record<string, number>
  reviews_per_repository: Record<string, number>
}

export const api = {
  metrics: () => req<Metrics>('/api/metrics/summary'),
  reviews: (offset = 0) => req<{ reviews: ReviewRow[] }>(`/api/reviews?offset=${offset}`),
  review: (id: string) => req<ReviewDetail>(`/api/reviews/${id}`),
  repos: () => req<{ repositories: Repo[] }>('/api/repositories'),
  loginUrl: () => req<{ authorize_url: string }>('/api/auth/github/login'),
}
