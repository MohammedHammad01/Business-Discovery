import { useState } from 'react'
import { Badge, Bullets, Card, EmptyState, PriorityBadge, SourceRefs } from '../components/primitives'
import type { Analysis } from '../types/discovery'

export function AnalysisPage({
  analysis,
  sourceNames,
}: {
  analysis: Analysis
  sourceNames: Record<string, string>
}) {
  const { discovery } = analysis
  const [showCanonical, setShowCanonical] = useState(false)

  return (
    <div className="grid">
      <div className="meta-strip">
        <span>
          Model: <strong>{analysis.model}</strong>
          {analysis.mocked && ' (offline mock)'}
        </span>
        <span>Sources analyzed: {analysis.canonical_input.sources.length}</span>
        <span>{new Date(analysis.created_at).toLocaleString()}</span>
        <button className="btn btn--ghost btn--sm" onClick={() => setShowCanonical((v) => !v)}>
          {showCanonical ? 'Hide' : 'Show'} canonical input JSON
        </button>
      </div>

      {showCanonical && (
        <Card title="Canonical input" subtitle="The one contract the AI layer consumes, whatever the file format was.">
          <pre className="json">{JSON.stringify(analysis.canonical_input, null, 2)}</pre>
        </Card>
      )}

      <Card title="Business need" subtitle={discovery.business_need.summary}>
        <Bullets items={discovery.business_need.goals} empty="No goals were identified." />
        <SourceRefs ids={discovery.business_need.source_ids} names={sourceNames} />
      </Card>

      <div className="grid grid--two">
        <Card title="Current process" subtitle={discovery.current_process.summary}>
          {discovery.current_process.steps.length === 0 ? (
            <EmptyState message="The current process could not be reconstructed from these sources." />
          ) : (
            <ol className="steps">
              {discovery.current_process.steps.map((step, index) => (
                <li key={`${step.step}-${index}`}>
                  <div className="steps__head">
                    <strong>{step.step}</strong>
                    {step.actor && <Badge tone="type">{step.actor}</Badge>}
                  </div>
                  {step.pain && <p className="steps__pain">⚠ {step.pain}</p>}
                  <SourceRefs ids={step.source_ids} names={sourceNames} />
                </li>
              ))}
            </ol>
          )}
          <div className="chips">
            {discovery.current_process.actors.map((actor) => (
              <Badge key={actor} tone="role">
                {actor}
              </Badge>
            ))}
            {discovery.current_process.systems.map((system) => (
              <Badge key={system} tone="system">
                {system}
              </Badge>
            ))}
          </div>
        </Card>

        <Card title={`Pain points (${discovery.pain_points.length})`}>
          {discovery.pain_points.length === 0 ? (
            <EmptyState message="No pain points were identified." />
          ) : (
            <ul className="list">
              {discovery.pain_points.map((pain, index) => (
                <li key={`${pain.problem}-${index}`}>
                  <div className="list__head">
                    <strong>{pain.problem}</strong>
                    <PriorityBadge value={pain.severity} />
                  </div>
                  <p>{pain.impact}</p>
                  <SourceRefs ids={pain.evidence_source_ids} names={sourceNames} />
                </li>
              ))}
            </ul>
          )}
        </Card>
      </div>

      <Card title={`Requirements (${discovery.requirements.length})`} subtitle="Facts, inferences and assumptions are labelled separately.">
        {discovery.requirements.length === 0 ? (
          <EmptyState message="No requirements were extracted." />
        ) : (
          <table className="table">
            <thead>
              <tr>
                <th>Requirement</th>
                <th>Priority</th>
                <th>Basis</th>
                <th>Evidence</th>
              </tr>
            </thead>
            <tbody>
              {discovery.requirements.map((req, index) => (
                <tr key={`${req.requirement}-${index}`}>
                  <td>{req.requirement}</td>
                  <td>
                    <PriorityBadge value={req.priority} />
                  </td>
                  <td>
                    <Badge tone={req.confidence}>{req.confidence}</Badge>
                  </td>
                  <td>
                    <SourceRefs ids={req.source_ids} names={sourceNames} />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </Card>

      <div className="grid grid--two">
        <Card title="Missing information" subtitle="What must be clarified with the client.">
          {discovery.missing_information.length === 0 ? (
            <EmptyState message="Nothing outstanding was flagged." />
          ) : (
            <ul className="list">
              {discovery.missing_information.map((item, index) => (
                <li key={`${item.question}-${index}`}>
                  <strong>{item.question}</strong>
                  <p>{item.reason}</p>
                </li>
              ))}
            </ul>
          )}
        </Card>

        <Card title="Assumptions & contradictions" subtitle="Kept apart from client facts on purpose.">
          <h4>Assumptions</h4>
          <Bullets items={discovery.assumptions} empty="No assumptions were needed." />
          <h4>Contradictions between sources</h4>
          {discovery.contradictions.length === 0 ? (
            <EmptyState message="No contradictions were found." />
          ) : (
            <ul className="list">
              {discovery.contradictions.map((item, index) => (
                <li key={`${item.description}-${index}`}>
                  <p>{item.description}</p>
                  <SourceRefs ids={item.source_ids} names={sourceNames} />
                </li>
              ))}
            </ul>
          )}
        </Card>
      </div>

      <Card title="Recommended process" subtitle={discovery.recommended_process.summary}>
        <ol className="steps steps--positive">
          {discovery.recommended_process.steps.map((step, index) => (
            <li key={`${step.step}-${index}`}>
              <div className="steps__head">
                <strong>{step.step}</strong>
                {step.actor && <Badge tone="type">{step.actor}</Badge>}
              </div>
            </li>
          ))}
        </ol>
        <h4>Automation opportunities</h4>
        <Bullets
          items={discovery.recommended_process.automation_opportunities}
          empty="No automation opportunities were identified."
        />
      </Card>
    </div>
  )
}
