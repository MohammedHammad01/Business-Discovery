import type { Analysis, CanonicalInput, Health, Project, SourceRead } from '../types/discovery'

const BASE = import.meta.env.VITE_API_BASE_URL ?? ''

export class ApiError extends Error {
  status: number
  constructor(message: string, status: number) {
    super(message)
    this.name = 'ApiError'
    this.status = status
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response
  try {
    response = await fetch(`${BASE}${path}`, init)
  } catch {
    throw new ApiError('Cannot reach the backend. Is uvicorn running on port 8000?', 0)
  }

  if (!response.ok) {
    let detail = `Request failed with status ${response.status}.`
    try {
      const body = await response.json()
      if (typeof body?.detail === 'string') detail = body.detail
      else if (Array.isArray(body?.detail)) detail = body.detail.map((d: { msg: string }) => d.msg).join('; ')
    } catch {
      /* keep the default message */
    }
    throw new ApiError(detail, response.status)
  }

  if (response.status === 204) return undefined as T
  return (await response.json()) as T
}

export const api = {
  health: () => request<Health>('/api/health'),

  listProjects: () => request<Project[]>('/api/projects'),

  createProject: (payload: { name: string; client_name?: string; description?: string }) =>
    request<Project>('/api/projects', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    }),

  getProject: (projectId: string) => request<Project>(`/api/projects/${projectId}`),

  resetProject: (projectId: string) =>
    request<Project>(`/api/projects/${projectId}/reset`, { method: 'POST' }),

  listSources: (projectId: string) => request<SourceRead[]>(`/api/projects/${projectId}/sources`),

  uploadFile: (projectId: string, file: File) => {
    const form = new FormData()
    form.append('file', file)
    return request<SourceRead>(`/api/projects/${projectId}/sources`, { method: 'POST', body: form })
  },

  addUrl: (projectId: string, url: string) =>
    request<SourceRead>(`/api/projects/${projectId}/sources/url`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ url }),
    }),

  deleteSource: (projectId: string, sourceId: string) =>
    request<void>(`/api/projects/${projectId}/sources/${sourceId}`, { method: 'DELETE' }),

  canonicalInput: (projectId: string) =>
    request<CanonicalInput>(`/api/projects/${projectId}/canonical-input`),

  analyze: (projectId: string) =>
    request<Analysis>(`/api/projects/${projectId}/analyze`, { method: 'POST' }),

  discovery: (projectId: string) => request<Analysis>(`/api/projects/${projectId}/discovery`),
}
