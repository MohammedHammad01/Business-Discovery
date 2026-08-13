import type { ReactNode } from 'react'
import type { Priority, SourceType } from '../types/discovery'

export function Card({
  title,
  subtitle,
  children,
  actions,
}: {
  title: string
  subtitle?: string
  children: ReactNode
  actions?: ReactNode
}) {
  return (
    <section className="card">
      <header className="card__head">
        <div>
          <h2>{title}</h2>
          {subtitle && <p className="card__subtitle">{subtitle}</p>}
        </div>
        {actions}
      </header>
      <div className="card__body">{children}</div>
    </section>
  )
}

export function Badge({ tone = 'neutral', children }: { tone?: string; children: ReactNode }) {
  return <span className={`badge badge--${tone}`}>{children}</span>
}

export function PriorityBadge({ value }: { value: Priority }) {
  return <Badge tone={value}>{value}</Badge>
}

const SOURCE_LABELS: Record<SourceType, string> = {
  meeting_transcript: 'Transcript',
  whatsapp_export: 'WhatsApp',
  document: 'Document',
  pdf: 'PDF',
  docx: 'DOCX',
  text: 'Text',
  screenshot: 'Screenshot',
  website: 'Website',
}

export function sourceLabel(type: SourceType): string {
  return SOURCE_LABELS[type] ?? type
}

/** Traceability: turns source ids into the human file names they came from. */
export function SourceRefs({
  ids,
  names,
}: {
  ids: string[]
  names: Record<string, string>
}) {
  if (!ids?.length) return <span className="refs refs--none">No source cited</span>
  return (
    <span className="refs">
      Evidence:{' '}
      {ids.map((id) => (
        <span key={id} className="refs__chip" title={id}>
          {names[id] ?? id}
        </span>
      ))}
    </span>
  )
}

export function EmptyState({ message }: { message: string }) {
  return <p className="empty">{message}</p>
}

export function Banner({ tone, children }: { tone: 'error' | 'info' | 'warn'; children: ReactNode }) {
  return <div className={`banner banner--${tone}`}>{children}</div>
}

export function Spinner({ label }: { label: string }) {
  return (
    <div className="spinner" role="status" aria-live="polite">
      <span className="spinner__dot" />
      {label}
    </div>
  )
}

export function Bullets({ items, empty }: { items: string[]; empty: string }) {
  if (!items?.length) return <EmptyState message={empty} />
  return (
    <ul className="bullets">
      {items.map((item, index) => (
        <li key={`${item}-${index}`}>{item}</li>
      ))}
    </ul>
  )
}
