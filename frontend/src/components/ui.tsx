import type { ReactNode } from 'react'
import { NavLink } from 'react-router-dom'

// Signature: diff-gutter severity glyphs
export const SEV: Record<string, { glyph: string; cls: string; label: string }> = {
  critical: { glyph: '!!', cls: 'text-crit', label: 'critical' },
  high: { glyph: '!', cls: 'text-bad', label: 'high' },
  medium: { glyph: '~', cls: 'text-warn', label: 'medium' },
  low: { glyph: '·', cls: 'text-info', label: 'low' },
  info: { glyph: '·', cls: 'text-muted', label: 'info' },
}

export function SevGlyph({ severity }: { severity: string }) {
  const s = SEV[severity] ?? SEV.info
  return (
    <span
      className={`mono inline-block w-6 text-center font-bold ${s.cls}`}
      title={s.label}
      aria-label={s.label}
    >
      {s.glyph}
    </span>
  )
}

export function StatusPill({ status }: { status: string }) {
  const cls =
    status === 'done' ? 'text-ok border-ok/40'
    : status === 'processing' || status === 'queued' ? 'text-warn border-warn/40'
    : 'text-bad border-bad/40'
  return (
    <span className={`mono border rounded-sm px-1.5 py-0.5 text-xs ${cls}`}>{status}</span>
  )
}

const nav = [
  { to: '/', label: 'Dashboard' },
  { to: '/reviews', label: 'Reviews' },
  { to: '/repositories', label: 'Repositories' },
]

export function Layout({ children }: { children: ReactNode }) {
  return (
    <div className="min-h-screen">
      <header className="border-b border-rule bg-panel">
        <div className="mx-auto flex max-w-5xl items-baseline gap-8 px-4 py-3">
          <span className="mono text-sm font-bold tracking-tight">
            review<span className="text-ok">/</span>bot
          </span>
          <nav className="flex gap-5 text-sm">
            {nav.map((n) => (
              <NavLink
                key={n.to}
                to={n.to}
                end={n.to === '/'}
                className={({ isActive }) =>
                  `pb-0.5 focus-visible:outline focus-visible:outline-2 focus-visible:outline-ink ${
                    isActive ? 'border-b-2 border-ink font-medium' : 'text-muted hover:text-ink'
                  }`
                }
              >
                {n.label}
              </NavLink>
            ))}
          </nav>
        </div>
      </header>
      <main className="mx-auto max-w-5xl px-4 py-8">{children}</main>
    </div>
  )
}

export function Empty({ text, hint }: { text: string; hint: string }) {
  return (
    <div className="rounded-md border border-rule bg-panel p-10 text-center">
      <p className="mono text-sm">{text}</p>
      <p className="mt-1 text-sm text-muted">{hint}</p>
    </div>
  )
}
