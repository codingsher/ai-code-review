import { useQuery } from '@tanstack/react-query'
import {
  Bar, BarChart, Cell, ResponsiveContainer, Tooltip, XAxis, YAxis,
} from 'recharts'
import { api } from '../lib/api'
import { Empty, SEV } from '../components/ui'

const SEV_COLOR: Record<string, string> = {
  critical: '#8E1F14', high: '#C0392B', medium: '#B07D2B', low: '#56707F', info: '#6E7781',
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-md border border-rule bg-panel p-4">
      <div className="mono text-2xl font-bold">{value}</div>
      <div className="mt-1 text-xs text-muted">{label}</div>
    </div>
  )
}

export default function Dashboard() {
  const { data, isLoading, error } = useQuery({ queryKey: ['metrics'], queryFn: api.metrics })

  if (isLoading) return <p className="mono text-sm text-muted">Loading metrics…</p>
  if (error || !data) return <Empty text="Metrics unavailable" hint="Start the API and run a review to populate this page." />

  const sevData = Object.entries(data.findings_by_severity).map(([k, v]) => ({ name: k, count: v }))
  const catData = Object.entries(data.findings_by_category).map(([k, v]) => ({ name: k, count: v }))
  const repoData = Object.entries(data.reviews_per_repository).map(([k, v]) => ({ name: k.split('/')[1] ?? k, count: v }))

  return (
    <div className="space-y-8">
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        <Stat label="Total reviews" value={String(data.total_reviews)} />
        <Stat label="Success rate" value={data.success_rate != null ? `${Math.round(data.success_rate * 100)}%` : '—'} />
        <Stat label="Avg duration" value={data.avg_duration_ms != null ? `${(data.avg_duration_ms / 1000).toFixed(1)}s` : '—'} />
        <Stat label="Failed" value={String(data.failed)} />
      </div>

      {sevData.length === 0 ? (
        <Empty text="No findings yet" hint="Open a pull request on a connected repository to trigger a review." />
      ) : (
        <div className="grid gap-6 md:grid-cols-2">
          <section className="rounded-md border border-rule bg-panel p-4">
            <h2 className="mono mb-3 text-xs font-semibold uppercase tracking-wide text-muted">
              Findings by severity
            </h2>
            <ResponsiveContainer width="100%" height={200}>
              <BarChart data={sevData}>
                <XAxis dataKey="name" tick={{ fontSize: 11, fontFamily: 'JetBrains Mono' }} />
                <YAxis allowDecimals={false} tick={{ fontSize: 11 }} width={28} />
                <Tooltip cursor={{ fill: '#F0EFEA' }} />
                <Bar dataKey="count" radius={[2, 2, 0, 0]}>
                  {sevData.map((d) => (
                    <Cell key={d.name} fill={SEV_COLOR[d.name] ?? '#6E7781'} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
            <div className="mono mt-2 flex flex-wrap gap-3 text-xs text-muted">
              {Object.entries(SEV).map(([k, s]) => (
                <span key={k}>
                  <span className={`font-bold ${s.cls}`}>{s.glyph}</span> {k}
                </span>
              ))}
            </div>
          </section>
          <section className="rounded-md border border-rule bg-panel p-4">
            <h2 className="mono mb-3 text-xs font-semibold uppercase tracking-wide text-muted">
              Findings by category
            </h2>
            <ResponsiveContainer width="100%" height={200}>
              <BarChart data={catData}>
                <XAxis dataKey="name" tick={{ fontSize: 11, fontFamily: 'JetBrains Mono' }} />
                <YAxis allowDecimals={false} tick={{ fontSize: 11 }} width={28} />
                <Tooltip cursor={{ fill: '#F0EFEA' }} />
                <Bar dataKey="count" fill="#2F7D4F" radius={[2, 2, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </section>
          {repoData.length > 0 && (
            <section className="rounded-md border border-rule bg-panel p-4 md:col-span-2">
              <h2 className="mono mb-3 text-xs font-semibold uppercase tracking-wide text-muted">
                Reviews per repository
              </h2>
              <ResponsiveContainer width="100%" height={180}>
                <BarChart data={repoData} layout="vertical">
                  <XAxis type="number" allowDecimals={false} tick={{ fontSize: 11 }} />
                  <YAxis type="category" dataKey="name" tick={{ fontSize: 11, fontFamily: 'JetBrains Mono' }} width={120} />
                  <Tooltip cursor={{ fill: '#F0EFEA' }} />
                  <Bar dataKey="count" fill="#1F2428" radius={[0, 2, 2, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </section>
          )}
        </div>
      )}
    </div>
  )
}
