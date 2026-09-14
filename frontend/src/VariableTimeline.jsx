// Variable Timeline -- one sparkline per variable, plotting its value
// across the FULL step-trace of the current debug run (not just the
// current step's frame, the way the main Debugger page's Variables
// table does). Purely a frontend view over data `/debug` already
// returns (the `DebugStep` shape documented in backend/app/interpreter.py
// and CLAUDE.md §4) -- no backend/schema changes, no new endpoint.
//
// Deliberately self-contained: this component takes only `steps`,
// `currentStepIndex`, and an `onStepSelect` callback. It computes its
// own variable ordering/grouping internally rather than trusting a
// caller-supplied one, and renders its own placeholder/empty states, so
// it can be dropped into any wrapper (a sidebar panel today, something
// else in a future layout) with zero changes to this file -- only the
// thin JSX around it (panel chrome, heading, placement in the page)
// needs to move.
//
// -- Why a variable can need MORE THAN ONE sparkline segment ------------
// A variable name is only unique *within one call frame*. The same name
// can legitimately belong to several different invocations over the
// life of one trace -- self-recursion (`Fact` calling itself declares a
// fresh `sub`/`result` at every depth), mutual recursion, or simply two
// separate sequential `CALL Foo(); CALL Foo();` statements. Naively
// joining every step where a given name appears into one continuous
// line would silently stitch together values that have nothing to do
// with each other (verified against this app's own `RecursiveFactorial`
// sample: `result` appears in literally every single step of that
// trace, once inside `ComputeFactorial` and once per `Fact` recursion
// level -- 6 unrelated variables sharing one name).
//
// The `DebugStep.call` field (procedureName/depth/stack) has no unique
// per-invocation id to key off directly -- flagged here per this
// phase's own instruction, rather than silently working around it by
// enlarging the schema. It turns out none is actually needed: the
// interpreter can only ever be at one depth at a time, and a CALL always
// increases depth by exactly 1 relative to the step before it (see
// `_exec_call` in interpreter.py) -- so a fresh call frame is
// unambiguously identified by "depth just increased since the previous
// step," and returning to a shallower depth always resumes an existing
// ancestor frame, never fabricates a new one. `assignFrameInstances`
// below replays the trace once to assign each step a stable synthetic
// instance id on exactly that rule. It's a pure function of `call.depth`
// and step order, needs no new field, and correctly reunites a paused
// frame's own before/after-its-nested-call steps into one segment while
// never merging two genuinely separate invocations that happen to share
// a name, depth, and procedure.

import { useMemo, useState } from 'react'

const VIEW_W = 260
const VIEW_H = 28
const PAD_Y = 4

function assignFrameInstances(steps) {
  const instanceIdByStepIndex = new Array(steps.length)
  const activeStack = [0] // activeStack[depth] = instance id currently occupying that depth
  let nextId = 1
  let prevDepth = 0

  steps.forEach((step, i) => {
    const depth = step.call?.depth ?? 0
    if (depth > prevDepth) {
      // One or more new CALL frames entered since the last step -- each
      // depth level from here down is a brand-new invocation.
      for (let d = prevDepth + 1; d <= depth; d += 1) activeStack[d] = nextId++
      activeStack.length = depth + 1
    } else if (depth < prevDepth) {
      // Returned from one or more CALLs -- resume the existing ancestor
      // frame already sitting at this depth, never a new id.
      activeStack.length = depth + 1
    }
    instanceIdByStepIndex[i] = activeStack[depth]
    prevDepth = depth
  })

  return instanceIdByStepIndex
}

// One row per distinct variable NAME (first-appearance order across the
// whole trace), each holding one or more `instances` -- one per frame
// that ever declared a variable of that name -- so recursion/repeated
// CALLs render as clearly separate segments rather than one misleading
// merged line.
function buildVariableRows(steps) {
  const instanceIds = assignFrameInstances(steps)
  const rows = new Map()

  steps.forEach((step, stepIndex) => {
    const instanceId = instanceIds[stepIndex]
    const vars = step.variables ?? {}
    for (const [name, entry] of Object.entries(vars)) {
      if (!rows.has(name)) rows.set(name, { name, instancesById: new Map() })
      const row = rows.get(name)
      if (!row.instancesById.has(instanceId)) {
        row.instancesById.set(instanceId, {
          instanceId,
          scopeLabel: step.call ? step.call.procedureName : 'top level',
          points: [],
        })
      }
      row.instancesById.get(instanceId).points.push({
        stepIndex,
        value: entry.value,
        type: entry.type,
        changed: entry.changed,
      })
    }
  })

  return Array.from(rows.values()).map((row) => ({
    name: row.name,
    instances: Array.from(row.instancesById.values()),
  }))
}

function numericValue(point) {
  if (point.type === 'boolean') return point.value ? 1 : 0
  if (point.type === 'number') return point.value
  return null // 'string' and 'null' entries carry no plottable y-value
}

// Splits one instance's points into drawable polyline segments, breaking
// wherever the value is momentarily unknown (a 'null' snapshot, e.g. a
// DECLAREd-but-not-yet-SET variable) or where this instance's own steps
// aren't adjacent in the full trace (it was paused during a nested
// CALL it made) -- a straight line across either gap would imply a
// value that was never actually observed.
function toSegments(points) {
  const segments = []
  let current = []
  let lastStepIndex = null

  for (const point of points) {
    const y = numericValue(point)
    if (y === null) {
      if (current.length) segments.push(current)
      current = []
      lastStepIndex = null
      continue
    }
    if (lastStepIndex !== null && point.stepIndex - lastStepIndex > 1) {
      if (current.length) segments.push(current)
      current = []
    }
    current.push({ stepIndex: point.stepIndex, y, changed: point.changed })
    lastStepIndex = point.stepIndex
  }
  if (current.length) segments.push(current)
  return segments
}

// A row plots as a numeric line unless some point along the way is a
// string -- a null (not-yet-set) value doesn't disqualify it, it's just
// a gap (see toSegments above).
function classifyRow(row) {
  for (const instance of row.instances) {
    for (const point of instance.points) {
      if (point.type === 'string') return 'other'
    }
  }
  return 'numeric'
}

function yDomainForRow(row) {
  let min = Infinity
  let max = -Infinity
  for (const instance of row.instances) {
    for (const segment of toSegments(instance.points)) {
      for (const point of segment) {
        if (point.y < min) min = point.y
        if (point.y > max) max = point.y
      }
    }
  }
  if (!Number.isFinite(min)) return [0, 1]
  if (min === max) return [min - 1, max + 1] // a flat line still gets visible headroom
  return [min, max]
}

function mapX(stepIndex, stepCount) {
  return (stepIndex / Math.max(1, stepCount - 1)) * VIEW_W
}

function mapY(y, [min, max]) {
  const t = (y - min) / (max - min)
  return PAD_Y + (1 - t) * (VIEW_H - 2 * PAD_Y)
}

function indexFromPointerEvent(event, stepCount) {
  const rect = event.currentTarget.getBoundingClientRect()
  const fraction = rect.width > 0 ? (event.clientX - rect.left) / rect.width : 0
  const clamped = Math.min(1, Math.max(0, fraction))
  return Math.round(clamped * (stepCount - 1))
}

function SparklineRow({ row, steps, currentStepIndex, hoverIndex, onHover, onLeave, onSelect }) {
  const kind = useMemo(() => classifyRow(row), [row])
  const domain = useMemo(() => (kind === 'numeric' ? yDomainForRow(row) : null), [row, kind])
  const stepCount = steps.length

  const currentEntry = steps[currentStepIndex]?.variables?.[row.name]
  const currentDisplay =
    currentEntry === undefined
      ? null
      : currentEntry.value === null
        ? '—'
        : currentEntry.type === 'string'
          ? `"${currentEntry.value}"`
          : String(currentEntry.value)

  const changedTicks = []
  for (const instance of row.instances) {
    for (const point of instance.points) {
      if (point.changed) changedTicks.push(point.stepIndex)
    }
  }

  return (
    <div className="var-timeline-row">
      <div className="var-timeline-label">
        <span className="var-timeline-name">{row.name}</span>
        {row.instances.length > 1 && (
          <span
            className="var-timeline-instance-count"
            title="Number of separate invocations/frames this variable appeared in during this run"
          >
            ×{row.instances.length}
          </span>
        )}
      </div>
      <svg
        className="var-timeline-chart"
        viewBox={`0 0 ${VIEW_W} ${VIEW_H}`}
        preserveAspectRatio="none"
        onMouseMove={(event) => onHover(indexFromPointerEvent(event, stepCount))}
        onMouseLeave={onLeave}
        onClick={(event) => onSelect(indexFromPointerEvent(event, stepCount))}
        role="img"
        aria-label={`Value of ${row.name} across all ${stepCount} steps of this run`}
      >
        {kind === 'numeric' &&
          row.instances.map((instance) =>
            toSegments(instance.points).map((segment, segIndex) => (
              <g key={`${instance.instanceId}-${segIndex}`}>
                <polyline
                  className="var-timeline-line"
                  points={segment.map((p) => `${mapX(p.stepIndex, stepCount)},${mapY(p.y, domain)}`).join(' ')}
                />
                {segment
                  .filter((p) => p.changed)
                  .map((p) => (
                    <circle
                      key={p.stepIndex}
                      className="var-timeline-changed-dot"
                      cx={mapX(p.stepIndex, stepCount)}
                      cy={mapY(p.y, domain)}
                      r={2}
                    />
                  ))}
              </g>
            )),
          )}

        {kind === 'other' &&
          changedTicks.map((stepIndex) => (
            <line
              key={stepIndex}
              className="var-timeline-tick"
              x1={mapX(stepIndex, stepCount)}
              x2={mapX(stepIndex, stepCount)}
              y1={PAD_Y}
              y2={VIEW_H - PAD_Y}
            />
          ))}

        {hoverIndex !== null && hoverIndex !== currentStepIndex && (
          <line
            className="var-timeline-hover-guide"
            x1={mapX(hoverIndex, stepCount)}
            x2={mapX(hoverIndex, stepCount)}
            y1={0}
            y2={VIEW_H}
          />
        )}

        <line
          className="var-timeline-current-guide"
          x1={mapX(currentStepIndex, stepCount)}
          x2={mapX(currentStepIndex, stepCount)}
          y1={0}
          y2={VIEW_H}
        />
        {kind === 'numeric' && currentEntry && numericValue(currentEntry) !== null && (
          <circle
            className="var-timeline-current-dot"
            cx={mapX(currentStepIndex, stepCount)}
            cy={mapY(numericValue(currentEntry), domain)}
            r={3}
          />
        )}
      </svg>
      <div className="var-timeline-current-value">
        {currentDisplay === null ? <em className="var-empty">—</em> : currentDisplay}
      </div>
    </div>
  )
}

/**
 * Self-contained "Variable Timeline" view: a sparkline per variable
 * across the full step-trace of the current run, in sync with
 * `currentStepIndex`. Renders its own empty state, so it's safe to drop
 * anywhere a `steps` array is available -- no dependency on where its
 * caller places it.
 *
 * Props:
 *   steps            - the full DebugStep[] array from the last /debug
 *                       response (or a replayed History entry) -- same
 *                       shape the rest of the Debugger page already uses.
 *   currentStepIndex - which step is "current" right now, for the
 *                      highlighted marker on every sparkline.
 *   onStepSelect     - called with a step index when the user clicks a
 *                      sparkline to jump there -- wire this to the same
 *                      setter that drives Previous/Next/the scrubber/
 *                      step log.
 */
export default function VariableTimeline({ steps, currentStepIndex, onStepSelect }) {
  const hasSteps = Array.isArray(steps) && steps.length > 0
  const rows = useMemo(() => (hasSteps ? buildVariableRows(steps) : []), [hasSteps, steps])
  const [hoverIndex, setHoverIndex] = useState(null)

  if (!hasSteps) {
    return <p className="placeholder">Run Debug to see variable timelines here.</p>
  }
  if (rows.length === 0) {
    return <p className="placeholder">This run never declared any variables.</p>
  }

  return (
    <div className="var-timeline" onMouseLeave={() => setHoverIndex(null)}>
      <div className="var-timeline-scale-hint">
        <span>Step 1</span>
        <span>Step {steps.length}</span>
      </div>
      {rows.map((row) => (
        <SparklineRow
          key={row.name}
          row={row}
          steps={steps}
          currentStepIndex={currentStepIndex}
          hoverIndex={hoverIndex}
          onHover={setHoverIndex}
          onLeave={() => setHoverIndex(null)}
          onSelect={onStepSelect}
        />
      ))}
      {hoverIndex !== null && (
        <p className="var-timeline-hover-caption">
          Step {hoverIndex + 1} of {steps.length} -- line {steps[hoverIndex].line}:{' '}
          <code>{steps[hoverIndex].statementText}</code> (click a sparkline to jump here)
        </p>
      )}
    </div>
  )
}
