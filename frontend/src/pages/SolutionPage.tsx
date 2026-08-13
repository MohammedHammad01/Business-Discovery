import { Badge, Bullets, Card, EmptyState } from '../components/primitives'
import type { Solution } from '../types/discovery'

/** Deterministic components, one per part of the solution JSON. */

function RoleList({ roles }: { roles: string[] }) {
  if (!roles.length) return <EmptyState message="No roles were proposed." />
  return (
    <div className="chips">
      {roles.map((role) => (
        <Badge key={role} tone="role">
          {role}
        </Badge>
      ))}
    </div>
  )
}

function FeatureList({ features }: { features: string[] }) {
  if (!features.length) return <EmptyState message="No features were proposed." />
  return (
    <ul className="features">
      {features.map((feature) => (
        <li key={feature}>{feature}</li>
      ))}
    </ul>
  )
}

function Workflow({ stages }: { stages: Solution['workflow'] }) {
  if (!stages.length) return <EmptyState message="No workflow was proposed." />
  return (
    <ol className="workflow">
      {stages.map((stage, index) => (
        <li key={`${stage.stage}-${index}`}>
          <span className="workflow__index">{index + 1}</span>
          <div>
            <div className="workflow__head">
              <strong>{stage.stage}</strong>
              {stage.actor && <Badge tone="role">{stage.actor}</Badge>}
            </div>
            {stage.action && <p>{stage.action}</p>}
            {stage.outcome && <p className="workflow__outcome">→ {stage.outcome}</p>}
          </div>
        </li>
      ))}
    </ol>
  )
}

export function SolutionPage({ solution }: { solution: Solution }) {
  return (
    <div className="grid">
      <Card title="Proposed solution" subtitle={solution.summary}>
        <h4>Roles</h4>
        <RoleList roles={solution.roles} />
        <h4>Modules</h4>
        <Bullets items={solution.modules} empty="No modules were proposed." />
      </Card>

      <div className="grid grid--two">
        <Card title="Features">
          <FeatureList features={solution.features} />
        </Card>
        <Card title="Screens">
          {solution.screens.length === 0 ? (
            <EmptyState message="No screens were proposed." />
          ) : (
            <ul className="list">
              {solution.screens.map((screen, index) => (
                <li key={`${screen.name}-${index}`}>
                  <div className="list__head">
                    <strong>{screen.name}</strong>
                    {screen.primary_role && <Badge tone="role">{screen.primary_role}</Badge>}
                  </div>
                  <p>{screen.purpose}</p>
                </li>
              ))}
            </ul>
          )}
        </Card>
      </div>

      <Card title="Workflow" subtitle="The end-to-end path the application supports.">
        <Workflow stages={solution.workflow} />
      </Card>
    </div>
  )
}
