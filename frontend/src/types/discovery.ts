// Mirrors the backend Pydantic contracts. Keep in sync with
// backend/app/schemas/{canonical,discovery,poc,api}.py

export type Priority = 'high' | 'medium' | 'low'
export type Confidence = 'fact' | 'inference' | 'assumption'

export type SourceType =
  | 'meeting_transcript'
  | 'whatsapp_export'
  | 'document'
  | 'pdf'
  | 'docx'
  | 'text'
  | 'screenshot'
  | 'website'

export interface SourceMetadata {
  page_count: number | null
  url: string | null
  original_filename: string | null
  content_type: string | null
  char_count: number | null
  truncated: boolean
  extraction: string | null
  uploaded_at: string | null
  extra: Record<string, unknown>
}

export interface SourceRead {
  source_id: string
  type: SourceType
  name: string
  char_count: number
  preview: string
  metadata: SourceMetadata
  created_at: string
}

export interface CanonicalSource {
  source_id: string
  type: SourceType
  name: string
  content: string
  metadata: SourceMetadata
}

export interface CanonicalInput {
  project_id: string
  sources: CanonicalSource[]
}

export interface Project {
  project_id: string
  name: string
  client_name: string
  description: string
  created_at: string
  source_count: number
  has_analysis: boolean
}

export interface ProcessStep {
  step: string
  actor: string
  pain: string
  source_ids: string[]
}

export interface BusinessNeed {
  summary: string
  goals: string[]
  source_ids: string[]
}

export interface CurrentProcess {
  summary: string
  steps: ProcessStep[]
  actors: string[]
  systems: string[]
}

export interface PainPoint {
  problem: string
  impact: string
  severity: Priority
  evidence_source_ids: string[]
}

export interface Requirement {
  requirement: string
  priority: Priority
  confidence: Confidence
  source_ids: string[]
}

export interface MissingInformation {
  question: string
  reason: string
}

export interface Contradiction {
  description: string
  source_ids: string[]
}

export interface RecommendedProcess {
  summary: string
  steps: ProcessStep[]
  automation_opportunities: string[]
}

export interface SolutionScreen {
  name: string
  purpose: string
  primary_role: string
}

export interface WorkflowStage {
  stage: string
  actor: string
  action: string
  outcome: string
}

export interface Solution {
  summary: string
  features: string[]
  roles: string[]
  modules: string[]
  screens: SolutionScreen[]
  workflow: WorkflowStage[]
}

export interface PocField {
  label: string
  field_type: 'text' | 'textarea' | 'number' | 'select' | 'date'
  options: string[]
  required: boolean
}

export interface PocDefinition {
  objective: string
  screens: string[]
  demo_flow: string[]
  request_fields: PocField[]
  in_scope: string[]
  out_of_scope: string[]
}

export interface DiscoveryOutput {
  business_need: BusinessNeed
  current_process: CurrentProcess
  pain_points: PainPoint[]
  requirements: Requirement[]
  missing_information: MissingInformation[]
  contradictions: Contradiction[]
  recommended_process: RecommendedProcess
  solution: Solution
  poc: PocDefinition
  assumptions: string[]
}

export interface PocStage {
  key: string
  title: string
  actor: string
  action: string
  outcome: string
  status_label: string
}

export interface PocBlueprint {
  objective: string
  entity_label: string
  roles: string[]
  request_fields: PocField[]
  stages: PocStage[]
  demo_flow: string[]
  in_scope: string[]
  out_of_scope: string[]
}

export interface Analysis {
  analysis_id: string
  project_id: string
  created_at: string
  model: string
  mocked: boolean
  canonical_input: CanonicalInput
  discovery: DiscoveryOutput
  poc_blueprint: PocBlueprint
}

export interface Health {
  status: string
  ai_configured: boolean
  mock_enabled: boolean
  model: string
  extractors: Record<string, boolean>
}
