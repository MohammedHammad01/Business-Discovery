import { useRef, useState } from 'react'
import { Badge, Banner, Card, EmptyState, Spinner, sourceLabel } from '../components/primitives'
import { api } from '../services/api'
import type { Health, Project, SourceRead } from '../types/discovery'

interface Props {
  health: Health | null
  project: Project | null
  sources: SourceRead[]
  analyzing: boolean
  hasAnalysis: boolean
  onCreateProject: (payload: { name: string; client_name: string; description: string }) => Promise<void>
  onSourcesChanged: () => Promise<void>
  onAnalyze: () => Promise<void>
  onReset: () => Promise<void>
  onError: (err: unknown) => void
}

export function WorkspacePage(props: Props) {
  const { health, project, sources, analyzing, hasAnalysis } = props
  const [name, setName] = useState('Client discovery demo')
  const [clientName, setClientName] = useState('')
  const [description, setDescription] = useState('')
  const [url, setUrl] = useState('')
  const [busy, setBusy] = useState<string | null>(null)
  const fileInput = useRef<HTMLInputElement>(null)

  if (!project) {
    return (
      <Card title="Create a project" subtitle="One project holds the client's inputs and its analysis.">
        <form
          className="form"
          onSubmit={(event) => {
            event.preventDefault()
            void props.onCreateProject({ name, client_name: clientName, description })
          }}
        >
          <label>
            Project name
            <input value={name} onChange={(e) => setName(e.target.value)} required maxLength={200} />
          </label>
          <label>
            Client name (optional)
            <input value={clientName} onChange={(e) => setClientName(e.target.value)} maxLength={200} />
          </label>
          <label>
            Description (optional)
            <textarea value={description} onChange={(e) => setDescription(e.target.value)} rows={3} />
          </label>
          <button className="btn btn--primary" type="submit">
            Create project
          </button>
        </form>
      </Card>
    )
  }

  const uploadFiles = async (files: FileList | null) => {
    if (!files?.length) return
    for (const file of Array.from(files)) {
      setBusy(`Extracting ${file.name}…`)
      try {
        await api.uploadFile(project.project_id, file)
      } catch (err) {
        props.onError(err)
      }
    }
    setBusy(null)
    if (fileInput.current) fileInput.current.value = ''
    await props.onSourcesChanged()
  }

  const addUrl = async () => {
    if (!url.trim()) return
    setBusy(`Fetching ${url}…`)
    try {
      await api.addUrl(project.project_id, url.trim())
      setUrl('')
    } catch (err) {
      props.onError(err)
    } finally {
      setBusy(null)
      await props.onSourcesChanged()
    }
  }

  const removeSource = async (sourceId: string) => {
    try {
      await api.deleteSource(project.project_id, sourceId)
    } catch (err) {
      props.onError(err)
    }
    await props.onSourcesChanged()
  }

  const missingExtractors = Object.entries(health?.extractors ?? {})
    .filter(([, available]) => !available)
    .map(([key]) => key)

  return (
    <div className="grid grid--two">
      <Card
        title={project.name}
        subtitle={project.client_name ? `Client: ${project.client_name}` : 'Add the client inputs you have.'}
        actions={
          <button className="btn btn--ghost" onClick={() => void props.onReset()}>
            Clear inputs
          </button>
        }
      >
        <div className="uploader">
          <input
            ref={fileInput}
            type="file"
            multiple
            accept=".txt,.md,.log,.csv,.vtt,.srt,.pdf,.docx,.png,.jpg,.jpeg,.webp,.gif,.bmp"
            onChange={(e) => void uploadFiles(e.target.files)}
          />
          <p className="hint">
            Transcripts, WhatsApp exports, PDF/DOCX documents and screenshots. Each file is extracted
            deterministically and stored as one canonical source.
          </p>

          <div className="row">
            <input
              placeholder="https://client-site.example/product"
              value={url}
              onChange={(e) => setUrl(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter') void addUrl()
              }}
            />
            <button className="btn" onClick={() => void addUrl()} disabled={!url.trim()}>
              Add website
            </button>
          </div>

          {busy && <Spinner label={busy} />}
          {missingExtractors.length > 0 && (
            <Banner tone="warn">
              Unavailable extractors in this environment: {missingExtractors.join(', ')}. Other input
              types still work.
            </Banner>
          )}
        </div>
      </Card>

      <Card title={`Sources (${sources.length})`} subtitle="These become the canonical input for the agent.">
        {sources.length === 0 ? (
          <EmptyState message="No sources yet. Upload a transcript, chat export, document or screenshot." />
        ) : (
          <ul className="sources">
            {sources.map((source) => (
              <li key={source.source_id} className="sources__item">
                <div className="sources__head">
                  <code>{source.source_id}</code>
                  <Badge tone="type">{sourceLabel(source.type)}</Badge>
                  <strong title={source.name}>{source.name}</strong>
                  <button
                    className="btn btn--icon"
                    aria-label={`Remove ${source.name}`}
                    onClick={() => void removeSource(source.source_id)}
                  >
                    ×
                  </button>
                </div>
                <p className="sources__preview">{source.preview}</p>
                <p className="sources__meta">
                  {source.char_count.toLocaleString()} chars
                  {source.metadata.extraction ? ` · ${source.metadata.extraction}` : ''}
                  {source.metadata.page_count ? ` · ${source.metadata.page_count} pages` : ''}
                  {source.metadata.truncated ? ' · truncated' : ''}
                </p>
              </li>
            ))}
          </ul>
        )}

        <div className="analyze">
          <button
            className="btn btn--primary btn--lg"
            disabled={sources.length === 0 || analyzing}
            onClick={() => void props.onAnalyze()}
          >
            {analyzing ? 'Analyzing…' : hasAnalysis ? 'Re-run analysis' : 'Analyze business'}
          </button>
          {analyzing && <Spinner label="One AI call over the canonical input…" />}
          {health && !health.ai_configured && (
            <p className="hint">
              No GEMINI_API_KEY is set, so the deterministic mock agent will answer. The flow,
              contracts and UI are identical.
            </p>
          )}
        </div>
      </Card>
    </div>
  )
}
