import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { api } from '../lib/api'
import { Empty, StatusPill } from '../components/ui'

export default function Reviews() {
  const { data, isLoading } = useQuery({ queryKey: ['reviews'], queryFn: () => api.reviews() })

  if (isLoading) return <p className="mono text-sm text-muted">Loading reviews…</p>
  const rows = data?.reviews ?? []
  if (rows.length === 0)
    return <Empty text="No reviews yet" hint="Open a pull request on a connected repository to trigger a review." />

  return (
    <div className="overflow-hidden rounded-md border border-rule bg-panel">
      <table className="w-full text-sm">
        <thead>
          <tr className="mono border-b border-rule text-left text-xs uppercase tracking-wide text-muted">
            <th className="px-4 py-2 font-medium">Pull request</th>
            <th className="px-4 py-2 font-medium">Status</th>
            <th className="px-4 py-2 font-medium text-right">Findings</th>
            <th className="px-4 py-2 font-medium text-right">Duration</th>
            <th className="px-4 py-2 font-medium text-right">When</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((r) => (
            <tr key={r.id} className="border-b border-rule last:border-0 hover:bg-ground">
              <td className="px-4 py-2">
                <Link to={`/reviews/${r.id}`} className="hover:underline">
                  <span className="mono text-xs text-muted">{r.repo}#{r.pr_number}</span>{' '}
                  {r.pr_title || 'Untitled'}
                </Link>
              </td>
              <td className="px-4 py-2"><StatusPill status={r.status} /></td>
              <td className="mono px-4 py-2 text-right">{r.findings_count}</td>
              <td className="mono px-4 py-2 text-right">
                {r.duration_ms != null ? `${(r.duration_ms / 1000).toFixed(1)}s` : '—'}
              </td>
              <td className="px-4 py-2 text-right text-xs text-muted">
                {new Date(r.created_at).toLocaleString()}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
