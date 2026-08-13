import { useMemo, useState } from 'react'
import { Badge, Card, EmptyState } from '../components/primitives'
import type { PocBlueprint, PocField } from '../types/discovery'

/**
 * The interactive POC. Every element here is a fixed component driven by the
 * validated blueprint JSON -- the AI never generates frontend code.
 */

interface AuditEntry {
  at: string
  actor: string
  event: string
  note: string
}

const DECISION_WORDS = ['decid', 'approv', 'review', 'sign', 'authoris', 'authoriz']

function isDecisionStage(statusLabel: string, action: string): boolean {
  const text = `${statusLabel} ${action}`.toLowerCase()
  return DECISION_WORDS.some((word) => text.includes(word))
}

function FieldInput({
  field,
  value,
  onChange,
}: {
  field: PocField
  value: string
  onChange: (value: string) => void
}) {
  const common = {
    value,
    required: field.required,
    onChange: (e: { target: { value: string } }) => onChange(e.target.value),
  }
  if (field.field_type === 'textarea') return <textarea rows={3} {...common} />
  if (field.field_type === 'select') {
    return (
      <select {...common}>
        <option value="">Select…</option>
        {field.options.map((option) => (
          <option key={option} value={option}>
            {option}
          </option>
        ))}
      </select>
    )
  }
  const type = field.field_type === 'number' ? 'number' : field.field_type === 'date' ? 'date' : 'text'
  return <input type={type} {...common} />
}

export function PocPage({ blueprint }: { blueprint: PocBlueprint }) {
  const [values, setValues] = useState<Record<string, string>>({})
  const [stageIndex, setStageIndex] = useState(0)
  const [status, setStatus] = useState<string>('Draft')
  const [audit, setAudit] = useState<AuditEntry[]>([])
  const [closed, setClosed] = useState<'approved' | 'rejected' | null>(null)
  const [formError, setFormError] = useState<string | null>(null)

  const stages = blueprint.stages
  const requester = blueprint.roles[0] ?? 'Requester'
  const currentStage = stages[stageIndex]
  const title = values[blueprint.request_fields[0]?.label ?? ''] || `${blueprint.entity_label} #1042`

  const missingRequired = useMemo(
    () => blueprint.request_fields.filter((f) => f.required && !values[f.label]?.trim()).map((f) => f.label),
    [blueprint.request_fields, values],
  )

  if (stages.length === 0) {
    return <EmptyState message="The analysis did not produce a workflow, so there is no POC flow to run." />
  }

  const log = (actor: string, event: string, note: string) =>
    setAudit((entries) => [
      ...entries,
      { at: new Date().toLocaleTimeString(), actor, event, note },
    ])

  const submit = () => {
    if (missingRequired.length) {
      setFormError(`Please complete: ${missingRequired.join(', ')}.`)
      return
    }
    setFormError(null)
    setStatus(stages[0].status_label)
    log(requester, `${blueprint.entity_label} submitted`, title)
    setStageIndex(1)
  }

  const advance = (decision?: 'approved' | 'rejected') => {
    const stage = stages[stageIndex]
    if (decision === 'rejected') {
      setStatus('Rejected')
      setClosed('rejected')
      log(stage.actor, 'Rejected', stage.outcome || 'Returned to the requester.')
      return
    }
    setStatus(stage.status_label)
    log(stage.actor, stage.title, stage.outcome || stage.action)
    if (decision === 'approved') setClosed('approved')
    if (stageIndex < stages.length - 1) setStageIndex(stageIndex + 1)
    else setClosed((current) => current ?? 'approved')
  }

  const restart = () => {
    setValues({})
    setStageIndex(0)
    setStatus('Draft')
    setAudit([])
    setClosed(null)
    setFormError(null)
  }

  const submitted = stageIndex > 0

  return (
    <div className="grid">
      <Card
        title="Interactive POC"
        subtitle={blueprint.objective}
        actions={
          <button className="btn btn--ghost" onClick={restart}>
            Restart demo
          </button>
        }
      >
        <ol className="tracker">
          {stages.map((stage, index) => {
            const state =
              closed === 'rejected' && index >= stageIndex
                ? 'rejected'
                : index < stageIndex || closed === 'approved'
                  ? 'done'
                  : index === stageIndex && submitted
                    ? 'active'
                    : 'todo'
            return (
              <li key={stage.key} className={`tracker__item is-${state}`}>
                <span className="tracker__dot" />
                <div>
                  <strong>{stage.title}</strong>
                  <span className="tracker__actor">{stage.actor}</span>
                </div>
              </li>
            )
          })}
        </ol>
        <p className="poc__status">
          Current status: <Badge tone={closed === 'rejected' ? 'high' : 'ok'}>{status}</Badge>
        </p>
      </Card>

      <div className="grid grid--two">
        <Card title={`New ${blueprint.entity_label}`} subtitle={`Acting as ${requester}`}>
          <form
            className="form"
            onSubmit={(event) => {
              event.preventDefault()
              submit()
            }}
          >
            {blueprint.request_fields.map((field) => (
              <label key={field.label}>
                {field.label}
                {field.required && <span className="req">*</span>}
                <FieldInput
                  field={field}
                  value={values[field.label] ?? ''}
                  onChange={(value) => setValues((prev) => ({ ...prev, [field.label]: value }))}
                />
              </label>
            ))}
            {formError && <p className="form__error">{formError}</p>}
            <button className="btn btn--primary" type="submit" disabled={submitted}>
              {submitted ? `${blueprint.entity_label} submitted` : `Submit ${blueprint.entity_label.toLowerCase()}`}
            </button>
          </form>
        </Card>

        <Card title="Next action" subtitle={submitted ? `Waiting on ${currentStage?.actor}` : 'Submit the form to start.'}>
          {!submitted && <EmptyState message="Nothing to do yet — the flow starts with a submission." />}

          {submitted && closed && (
            <div className="poc__done">
              <p>
                The {blueprint.entity_label.toLowerCase()} is <strong>{status.toLowerCase()}</strong>. The
                requester can see the outcome and the audit trail below.
              </p>
              <button className="btn" onClick={restart}>
                Run it again
              </button>
            </div>
          )}

          {submitted && !closed && currentStage && (
            <div className="poc__action">
              <p className="poc__actor">
                <Badge tone="role">{currentStage.actor}</Badge> {currentStage.action || currentStage.title}
              </p>
              {currentStage.outcome && <p className="hint">Outcome: {currentStage.outcome}</p>}
              {isDecisionStage(currentStage.status_label, currentStage.action) ? (
                <div className="row">
                  <button className="btn btn--primary" onClick={() => advance('approved')}>
                    Approve
                  </button>
                  <button className="btn btn--danger" onClick={() => advance('rejected')}>
                    Reject
                  </button>
                </div>
              ) : (
                <button className="btn btn--primary" onClick={() => advance()}>
                  {`Continue as ${currentStage.actor}`}
                </button>
              )}
            </div>
          )}
        </Card>
      </div>

      <div className="grid grid--two">
        <Card title="Audit trail" subtitle="Produced as a side effect of the workflow.">
          {audit.length === 0 ? (
            <EmptyState message="No events yet." />
          ) : (
            <ul className="timeline">
              {audit.map((entry, index) => (
                <li key={index}>
                  <span className="timeline__time">{entry.at}</span>
                  <div>
                    <strong>{entry.event}</strong>
                    <span className="timeline__actor"> · {entry.actor}</span>
                    {entry.note && <p>{entry.note}</p>}
                  </div>
                </li>
              ))}
            </ul>
          )}
        </Card>

        <Card title="POC scope" subtitle="What this demo deliberately does and does not cover.">
          <h4>In scope</h4>
          <ul className="bullets">
            {blueprint.in_scope.map((item) => (
              <li key={item}>{item}</li>
            ))}
          </ul>
          <h4>Out of scope</h4>
          <ul className="bullets bullets--muted">
            {blueprint.out_of_scope.map((item) => (
              <li key={item}>{item}</li>
            ))}
          </ul>
        </Card>
      </div>
    </div>
  )
}
