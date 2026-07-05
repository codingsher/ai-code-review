import { useQuery } from '@tanstack/react-query'
import { api } from '../lib/api'
import { Empty } from '../components/ui'

export default function Repositories() {
  const { data, isLoading } = useQuery({ queryKey: ['repos'], queryFn: api.repos })

  if (isLoading) return <p className="mono text-sm text-muted">Loading repositories…</p>
  const repos = data?.repositories ?? []
  if (repos.length === 0)
    return <Empty text="No repositories connected" hint="Point a GitHub webhook at /api/webhooks/github to connect one." />

  return (
    <ul className="overflow-hidden rounded-md border border-rule bg-panel">
      {repos.map((r) => (
        <li key={r.id} className="flex items-center justify-between border-b border-rule px-4 py-3 last:border-0">
          <span className="mono text-sm">{r.full_name}</span>
          <span className="text-xs text-muted">{r.review_count} reviews</span>
        </li>
      ))}
    </ul>
  )
}
