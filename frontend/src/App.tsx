import { useCallback, useEffect, useState } from 'react'
import { AnalysisPage } from './pages/AnalysisPage'
import { PocPage } from './pages/PocPage'
import { SolutionPage } from './pages/SolutionPage'
import { WorkspacePage } from './pages/WorkspacePage'
import { api, ApiError } from './services/api'
import type { Analysis, Health, Project, SourceRead } from './types/discovery'
import { Banner, Spinner } from './components/primitives'

type Tab = 'workspace' | 'analysis' | 'solution' | 'poc'

const TABS: { key: Tab; label: string }[] = [
  { key: 'workspace', label: '1. Inputs' },
  { key: 'analysis', label: '2. Discovery' },
  { key: 'solution', label: '3. Solution' },
  { key: 'poc', label: '4. POC' },
]

const STORAGE_KEY = 'abd.project_id'

export default function App() {
  const [health, setHealth] = useState<Health | null>(null)
  const [project, setProject] = useState<Project | null>(null)
  const [sources, setSources] = useState<SourceRead[]>([])
  const [analysis, setAnalysis] = useState<Analysis | null>(null)
  const [tab, setTab] = useState<Tab>('workspace')
  const [error, setError] = useState<string | null>(null)
  const [booting, setBooting] = useState(true)
  const [analyzing, setAnalyzing] = useState(false)

  const loadProject = useCallback(async (projectId: string) => {
    const loaded = await api.getProject(projectId)
    setProject(loaded)
    setSources(await api.listSources(projectId))
    if (loaded.has_analysis) {
      setAnalysis(await api.discovery(projectId))
    } else {
      setAnalysis(null)
    }
  }, [])

  useEffect(() => {
    ;(async () => {
      try {
        setHealth(await api.health())
        const saved = localStorage.getItem(STORAGE_KEY)
        if (saved) {
          try {
            await loadProject(saved)
          } catch {
            localStorage.removeItem(STORAGE_KEY)
          }
        }
      } catch (err) {
        setError(err instanceof Error ? err.message : String(err))
      } finally {
        setBooting(false)
      }
    })()
  }, [loadProject])

  const handleError = (err: unknown) => {
    setError(err instanceof ApiError || err instanceof Error ? err.message : String(err))
  }

  const createProject = async (payload: { name: string; client_name: string; description: string }) => {
    setError(null)
    try {
      const created = await api.createProject(payload)
      localStorage.setItem(STORAGE_KEY, created.project_id)
      setProject(created)
      setSources([])
      setAnalysis(null)
    } catch (err) {
      handleError(err)
    }
  }

  const refreshSources = async () => {
    if (!project) return
    setSources(await api.listSources(project.project_id))
  }

  const analyze = async () => {
    if (!project) return
    setError(null)
    setAnalyzing(true)
    try {
      const result = await api.analyze(project.project_id)
      setAnalysis(result)
      setTab('analysis')
    } catch (err) {
      handleError(err)
    } finally {
      setAnalyzing(false)
    }
  }

  const resetProject = async () => {
    if (!project) return
    try {
      setProject(await api.resetProject(project.project_id))
      setSources([])
      setAnalysis(null)
      setTab('workspace')
    } catch (err) {
      handleError(err)
    }
  }

  const switchProject = () => {
    localStorage.removeItem(STORAGE_KEY)
    setProject(null)
    setSources([])
    setAnalysis(null)
    setTab('workspace')
  }

  const sourceNames = Object.fromEntries(sources.map((s) => [s.source_id, s.name]))

  return (
    <div className="app">
      <header className="app__head">
        <div>
          <h1>AI Business Discovery → POC</h1>
          <p className="app__tagline">
            Every input is normalized into one canonical JSON contract, then a single Business
            Discovery Agent turns it into structured output the UI renders deterministically.
          </p>
        </div>
        <div className="app__status">
          {health && (
            <span className={`pill ${health.ai_configured ? 'pill--ok' : 'pill--warn'}`}>
              {health.ai_configured ? `AI: ${health.model}` : 'AI: mock mode (no API key)'}
            </span>
          )}
          {project && (
            <button className="btn btn--ghost" onClick={switchProject}>
              New project
            </button>
          )}
        </div>
      </header>

      {error && (
        <Banner tone="error">
          {error}
          <button className="banner__close" onClick={() => setError(null)} aria-label="Dismiss">
            ×
          </button>
        </Banner>
      )}

      {booting ? (
        <Spinner label="Connecting to the backend…" />
      ) : (
        <>
          <nav className="tabs">
            {TABS.map((entry) => {
              const locked = entry.key !== 'workspace' && !analysis
              return (
                <button
                  key={entry.key}
                  className={`tabs__item ${tab === entry.key ? 'is-active' : ''}`}
                  disabled={locked}
                  title={locked ? 'Run the analysis first' : undefined}
                  onClick={() => setTab(entry.key)}
                >
                  {entry.label}
                </button>
              )
            })}
          </nav>

          <main className="app__body">
            {tab === 'workspace' && (
              <WorkspacePage
                health={health}
                project={project}
                sources={sources}
                analyzing={analyzing}
                hasAnalysis={Boolean(analysis)}
                onCreateProject={createProject}
                onSourcesChanged={refreshSources}
                onAnalyze={analyze}
                onReset={resetProject}
                onError={handleError}
              />
            )}
            {tab === 'analysis' && analysis && (
              <AnalysisPage analysis={analysis} sourceNames={sourceNames} />
            )}
            {tab === 'solution' && analysis && <SolutionPage solution={analysis.discovery.solution} />}
            {tab === 'poc' && analysis && <PocPage blueprint={analysis.poc_blueprint} />}
          </main>
        </>
      )}
    </div>
  )
}
