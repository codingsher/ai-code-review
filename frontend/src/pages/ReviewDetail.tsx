import { useQuery } from '@tanstack/react-query'
import { useParams } from 'react-router-dom'
import { api } from '../lib/api'
import { Empty, SevGlyph, StatusPill } from '../components/ui'

const ORDER = ['critical', 'high', 'medium', 'low', 'info']

export default function ReviewDetail() {
  const { id } = useParams<{ id: string }>()
  const { data, isLoading } = useQuery({
    queryKey: ['review', id],
    queryFn: () => api.review(id!),
    enabled: !!id,
  })

  if (isLoading) return <p className="mono text-sm text-muted">Loading review…</p>
  if (!data) return <Empty text="Review not found" hint="It may have been deleted." />

  const findings = [...data.findings].sort(
    (a, b) => ORDER.indexOf(a.severity) - ORDER.indexOf(b.severity),
  )

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center gap-3">
        <h1 className="mono text-lg font-bold">Review {data.job_id.slice(0, 8)}</h1>
        <StatusPill status={data.status} />
        <span className="mono text-xs text-muted">@ {data.head_sha.slice(0, 7)}</span>
        {data.duration_ms != null && (
          <span className="mono text-xs text-muted">{(data.duration_ms / 1000).toFixed(1)}s</span>
        )}
      </div>

      {findings.length === 0 ? (
        <Empty text="No findings" hint="This change passed all analyzers." />
      ) : (
        <div className="overflow-hidden rounded-md border border-rule bg-panel">
          {findings.map((f, i) => (
            <details key={i} className="group border-b border-rule last:border-0">
              <summary className="flex cursor-pointer items-baseline gap-2 px-4 py-2.5 hover:bg-ground">
                <SevGlyph severity={f.severity} />
                <span className="flex-1 text-sm">{f.title}</span>
                <span className="mono shrink-0 text-xs text-muted">
                  {f.file}:{f.line}
                </span>
                <span className="mono shrink-0 rounded-sm border border-rule px-1 text-xs text-muted">
                  {f.source}
                </span>
              </summary>
              <div className="space-y-2 border-t border-rule bg-ground px-4 py-3 text-sm">
                <p className="mono text-xs text-muted">
                  {f.category}
                  {f.confidence != null && ` · confidence ${Math.round(f.confidence * 100)}%`}
                </p>
                {typeof f.detail.explanation === 'string' && <p>{f.detail.explanation}</p>}
                {typeof f.detail.suggested_fix === 'string' && (
                  <p><span className="font-medium">Fix:</span> {f.detail.suggested_fix}</p>
                )}
                {typeof f.detail.code_example === 'string' && f.detail.code_example && (
                  <pre className="overflow-x-auto rounded-sm border border-rule bg-panel p-3 text-xs">
                    {f.detail.code_example}
                  </pre>
                )}
              </div>
            </details>
          ))}
        </div>
      )}
    </div>
  )
}
