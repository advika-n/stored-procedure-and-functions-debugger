// Builds a control-flow graph from the procedure AST (the shape the
// backend returns from POST /debug -- see backend/app/parser.py), and
// renders it as a Mermaid flowchart definition.
//
// This is deliberately AST-driven, not step-driven: the diagram's
// shape (which nodes exist, how they connect) comes entirely from the
// procedure's structure and is built once per Debug run. Only the
// *styling* -- which node is "current", which branch lit up as taken,
// and (see renderMermaidDefinition's `theme` param) which color
// palette Day/Night Mode is currently using -- is recomputed as the
// user steps through the execution trace or flips the theme toggle.

import { getMermaidPalette } from './mermaidColors'

// -- rendering AST expression/statement nodes back to source text ----------
// (mirrors backend/app/interpreter.py's render_expr / render_statement_header)

function renderExpr(node) {
  switch (node.type) {
    case 'NumberLiteral':
      return String(node.value)
    case 'StringLiteral':
      return `'${node.value}'`
    case 'NullLiteral':
      return 'NULL'
    case 'Identifier':
      return node.name
    case 'UnaryExpr':
      return `${node.operator}${renderExpr(node.operand)}`
    case 'BinaryExpr':
      return `${renderExpr(node.left)} ${node.operator} ${renderExpr(node.right)}`
    case 'CursorFoundExpr':
      return `${node.cursor}%FOUND`
    case 'CursorNotFoundExpr':
      return `${node.cursor}%NOTFOUND`
    case 'FunctionCallExpr':
      // Function calls inside procedures (a later phase than the rest
      // of this mirror) -- without this case a statement using one
      // (e.g. `SET y = Square(x);`) would render as `SET y = ?;` in the
      // flowchart node label, same as backend/app/interpreter.py's own
      // render_expr needed the matching case for the same reason.
      return `${node.name}(${node.args.map(renderExpr).join(', ')})`
    default:
      return '?'
  }
}

function renderStatementHeader(node) {
  switch (node.type) {
    case 'DeclareStatement': {
      let text = `DECLARE ${node.name} ${node.var_type}`
      if (node.default !== null) text += ` DEFAULT ${renderExpr(node.default)}`
      return text + ';'
    }
    case 'SetStatement':
      return `SET ${node.target} = ${renderExpr(node.value)};`
    case 'IfStatement':
      return `IF ${renderExpr(node.condition)} THEN`
    case 'WhileStatement':
      return `WHILE ${renderExpr(node.condition)} DO`
    case 'CaseStatement':
      // Mirrors backend/app/interpreter.py's render_statement_header
      // exactly: the operand's text for simple CASE, or bare "CASE" for
      // searched CASE (no single condition to show -- each WHEN gets
      // its own labeled edge instead, built in emitBlock below).
      return node.operand !== null ? `CASE ${renderExpr(node.operand)}` : 'CASE'
    case 'CursorDeclNode':
      return `DECLARE ${node.name} CURSOR FOR ${node.query};`
    case 'OpenCursorNode':
      return `OPEN ${node.name};`
    case 'FetchCursorNode':
      return `FETCH ${node.name} INTO ${node.targets.join(', ')};`
    case 'CloseCursorNode':
      return `CLOSE ${node.name};`
    case 'HandlerDeclNode':
      // renderStatementHeader(action) already ends in ';'.
      return `DECLARE CONTINUE HANDLER FOR ${node.condition} ${renderStatementHeader(node.action)}`
    case 'ReturnNode':
      return `RETURN ${renderExpr(node.value)};`
    case 'LoopStatement':
      // Mirrors backend/app/interpreter.py's render_statement_header:
      // just the header line, no body (the body is walked separately by
      // emitBlock below, same as WhileStatement/IfStatement/CaseStatement).
      return node.label ? `${node.label}: LOOP` : 'LOOP'
    case 'LeaveStatement':
      return node.label ? `LEAVE ${node.label};` : 'LEAVE;'
    case 'SqlStatement':
      // `sql` already IS the full statement text (see
      // backend/app/parser.py's "SQL passthrough statements" section) --
      // nothing to reconstruct, just close it with ';' like every other
      // case here does.
      return `${node.sql};`
    default:
      return node.type
  }
}

// Mermaid node labels are double-quoted; escape the characters that
// would otherwise break out of the quotes or get HTML-interpreted.
function escapeLabel(text) {
  return text
    .replace(/&/g, '&amp;')
    .replace(/"/g, '&quot;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
}

const START_ID = 'startNode'
const END_ID = 'endNode' // `end` is a reserved Mermaid keyword, so avoid it

// -- graph construction ------------------------------------------------

// Walks a list of statements, threading dangling "tails" (edges waiting
// for a destination) through it. Each tail is { nodeId, kind } where
// `kind` becomes the edge's kind once it's finally connected --
// 'seq' | 'then' | 'else' | 'loop' | 'loop-exit' | 'loop-back' | 'leave'
// | 'when-<N>' (CASE's own N-way branches -- see
// isConditionalEdgeKind/edgeLabelFor below for where the open-ended
// 'when-<N>' set is actually handled).
//
// `loopStack` (innermost last) is only for LEAVE resolution -- see the
// LoopStatement/LeaveStatement cases below. It's threaded unchanged
// through every recursive emitBlock call except LoopStatement's own
// (which pushes a fresh context for its body), exactly like WHILE/IF/
// CASE were already threading `nodes`/`edges` unchanged before this.
function emitBlock(statements, entryTails, nodes, edges, loopStack = []) {
  let tails = entryTails

  for (const stmt of statements) {
    const nodeId = `n${stmt.line}`

    if (stmt.type === 'IfStatement' || stmt.type === 'WhileStatement' || stmt.type === 'CaseStatement') {
      nodes.push({ id: nodeId, label: renderStatementHeader(stmt), shape: 'diamond', line: stmt.line, kind: stmt.type })
    } else if (stmt.type === 'ReturnNode') {
      // Stadium shape (same bracket syntax as the Start/End terminals),
      // styled separately -- see the returnNode/returnCurrent classDefs
      // in renderMermaidDefinition -- to read as "execution ends here".
      nodes.push({ id: nodeId, label: renderStatementHeader(stmt), shape: 'stadium', line: stmt.line, kind: stmt.type })
    } else {
      // SqlStatement (CREATE TABLE/INSERT/UPDATE/DELETE/SELECT) falls
      // through to this plain rect-node case too -- it never branches or
      // loops, so it needs no special shape/edge handling below, same as
      // SetStatement/DeclareStatement/CallStatement already didn't.
      nodes.push({ id: nodeId, label: renderStatementHeader(stmt), shape: 'rect', line: stmt.line, kind: stmt.type })
    }

    for (const tail of tails) {
      edges.push({ from: tail.nodeId, to: nodeId, kind: tail.kind })
    }

    if (stmt.type === 'IfStatement') {
      const thenTails = emitBlock(stmt.then_body, [{ nodeId, kind: 'then' }], nodes, edges, loopStack)
      const elseTails = stmt.else_body
        ? emitBlock(stmt.else_body, [{ nodeId, kind: 'else' }], nodes, edges, loopStack)
        : [{ nodeId, kind: 'else' }]
      tails = [...thenTails, ...elseTails]
    } else if (stmt.type === 'CaseStatement') {
      // One outgoing edge per WHEN clause (kind 'when-<index>', an
      // open-ended set unlike IF's fixed 'then'/'else' pair -- see
      // isConditionalEdgeKind/edgeLabelFor below), plus one more for
      // ELSE -- synthesized as a dangling tail exactly like IfStatement
      // does above when there's no else_body, representing "no WHEN
      // matched, fell through" (backend/app/interpreter.py's `path:
      // 'none'` case -- see computeDiagramState below for why that
      // fallthrough edge is never highlighted as "taken", mirroring
      // IF's own already-established behavior).
      const whenTails = stmt.when_clauses.flatMap((clause, index) =>
        emitBlock(clause.body, [{ nodeId, kind: `when-${index}` }], nodes, edges, loopStack),
      )
      const elseTails = stmt.else_body
        ? emitBlock(stmt.else_body, [{ nodeId, kind: 'else' }], nodes, edges, loopStack)
        : [{ nodeId, kind: 'else' }]
      tails = [...whenTails, ...elseTails]
    } else if (stmt.type === 'WhileStatement') {
      const bodyTails = emitBlock(stmt.body, [{ nodeId, kind: 'loop' }], nodes, edges, loopStack)
      for (const tail of bodyTails) {
        edges.push({ from: tail.nodeId, to: nodeId, kind: 'loop-back' })
      }
      tails = [{ nodeId, kind: 'loop-exit' }]
    } else if (stmt.type === 'LoopStatement') {
      // Unlike WHILE, LOOP has no condition of its own -- there is no
      // 'loop-exit' edge leaving this node directly. The ONLY way out is
      // a LEAVE somewhere in the body (possibly several IF/WHILE/CASE/
      // LOOP levels deep) naming this loop -- each one contributes its
      // OWN edge into whatever follows this LoopStatement, collected via
      // `loopContext.exits` below (pushed to by the LeaveStatement case,
      // reached through the `loopStack` this LOOP's own body is walked
      // with). If nothing ever LEAVEs this exact loop, `exits` stays
      // empty and this statement contributes no tail at all -- correctly
      // meaning "nothing after this LOOP is reachable", symmetric with
      // ReturnNode's own "tails = []" below.
      const loopContext = { label: stmt.label, exits: [] }
      const bodyTails = emitBlock(stmt.body, [{ nodeId, kind: 'loop' }], nodes, edges, [...loopStack, loopContext])
      for (const tail of bodyTails) {
        edges.push({ from: tail.nodeId, to: nodeId, kind: 'loop-back' })
      }
      tails = loopContext.exits
    } else if (stmt.type === 'LeaveStatement') {
      // Resolve against `loopStack` (innermost first) exactly like
      // app.interpreter's own `_loop_stack` resolution: an unlabeled
      // LEAVE targets the innermost enclosing loop; a labeled one
      // searches outward for a matching label. A LEAVE with no
      // resolvable target (shouldn't happen for a backend-validated AST,
      // since app.interpreter would have already raised) contributes no
      // exit edge anywhere rather than crashing the diagram.
      const target = stmt.label
        ? [...loopStack].reverse().find((ctx) => ctx.label === stmt.label)
        : loopStack[loopStack.length - 1]
      if (target) target.exits.push({ nodeId, kind: 'leave' })
      // Nothing after a LEAVE in the same block is reachable -- same
      // "execution unconditionally exits here" reasoning as ReturnNode.
      tails = []
    } else if (stmt.type === 'ReturnNode') {
      // Execution halts here -- no continuation edge to whatever
      // statement would textually follow (even inside an IF/WHILE/CASE
      // block). If this was one branch of an IF/CASE, the other
      // branches' own tails (already computed independently) are
      // unaffected.
      tails = []
    } else {
      tails = [{ nodeId, kind: 'seq' }]
    }
  }

  return tails
}

// The wrapped forms (FunctionNode/ProcedureNode) carry a name/params/line
// for their own CREATE ... line -- same field shape the backend's
// render_definition_header reads for the synthetic "entry" DebugStep
// (see interpreter.py), so `line` here lines up with that step's `line`
// and the existing current/visited-by-line matching below just works,
// no special-casing needed. The bare legacy Procedure form (no CREATE
// wrapper) has none of that, so it keeps the old generic, unlined
// "Start" marker -- it was never highlightable either.
function buildEntryNode(ast) {
  if (ast.type === 'FunctionNode' || ast.type === 'ProcedureNode') {
    const params = (ast.params ?? []).map((p) => p.name).join(', ')
    return { id: START_ID, label: `${ast.name}(${params})`, shape: 'stadium', line: ast.line }
  }
  return { id: START_ID, label: 'Start', shape: 'terminal' }
}

/** Build a { nodes, edges } control-flow graph from a ProcedureNode AST. */
export function buildFlowchartGraph(ast) {
  const nodes = [buildEntryNode(ast), { id: END_ID, label: 'End', shape: 'terminal' }]
  const edges = []

  const finalTails = emitBlock(ast.body, [{ nodeId: START_ID, kind: 'seq' }], nodes, edges)
  for (const tail of finalTails) {
    edges.push({ from: tail.nodeId, to: END_ID, kind: tail.kind })
  }

  return { nodes, edges }
}

// -- deriving "where are we" from the step trace ------------------------

/**
 * Given the graph, the full step trace, and how far the user has
 * stepped, work out: which node is "current", which nodes have been
 * passed already, and -- for each IF/WHILE/CASE node reached so far --
 * which of its outgoing branches was actually taken most recently
 * (a node can be revisited if it's inside a loop).
 */
export function computeDiagramState(graph, steps, currentStepIndex) {
  const visitedLines = new Set()
  const takenKindByLine = new Map() // line -> 'then' | 'else' | 'loop' | 'loop-exit' | 'when-<N>'

  const executed = steps.slice(0, currentStepIndex + 1)
  for (const step of executed) {
    visitedLines.add(step.line)
    if (step.branch) {
      // Generic over IfStatement's fixed 'then'/'else' pair AND
      // CaseStatement's open-ended 'when-<N>'/'else' set -- `path` IS
      // the edge kind that was taken, whatever it says, in both cases.
      // 'none' (nothing matched, no ELSE) is the one value that never
      // marks an edge taken -- mirrors IfStatement's own pre-existing
      // "condition false, no ELSE -- nothing taken to mark" behavior,
      // now shared by CASE's identical fallthrough case.
      if (step.branch.path !== 'none') takenKindByLine.set(step.line, step.branch.path)
    } else if (step.loop) {
      takenKindByLine.set(step.line, step.loop.result ? 'loop' : 'loop-exit')
    }
  }

  const currentLine = steps[currentStepIndex]?.line ?? null

  return { currentLine, visitedLines, takenKindByLine }
}

// -- rendering the Mermaid definition ------------------------------------

function nodeMermaidText(node) {
  const label = escapeLabel(node.label)
  if (node.shape === 'diamond') return `  ${node.id}{"${label}"}`
  // 'terminal' (Start/End) and 'stadium' (entry signature, RETURN) use
  // the same rounded-stadium bracket syntax -- they're only styled
  // differently, via the classDefs below.
  if (node.shape === 'terminal' || node.shape === 'stadium') return `  ${node.id}(["${label}"])`
  return `  ${node.id}["${label}"]`
}

/** Render the graph + current playback state into a Mermaid flowchart
 * definition. `theme` ("dark" | "light", default "dark") picks which of
 * mermaidColors.js's two palettes the classDef/linkStyle colors below
 * come from -- see that file for why they can't just be var(...). */

// 'then'/'loop'/'loop-exit'/'leave' are exactly IF/WHILE/LOOP's fixed
// edge kinds; CASE's own kinds are open-ended ('when-0', 'when-1', ...
// -- one per WHEN clause, however many a given CASE happens to have),
// so they can't live in a fixed lookup table the way the others do.
// 'leave' is deliberately NOT a "which of several options was taken"
// pair the way then/else or loop/loop-exit are (a LEAVE node has only
// ONE outgoing edge, nothing to disambiguate from) -- it's labeled
// purely for diagram readability (a LEAVE's edge can jump quite far,
// out of however many nested loops it escapes), and correctly never
// picks up taken/not-taken linkStyle coloring below, since a
// LeaveStatement's own DebugStep carries no `branch`/`loop` field for
// `computeDiagramState` to key off (see isConditionalEdgeKind's own
// generic "no data for this line -> no styling" fallthrough).
const _STATIC_EDGE_LABELS = { then: 'then', else: 'else', loop: 'loop', 'loop-exit': 'exit', leave: 'leave' }
const _WHEN_EDGE_KIND_RE = /^when-(\d+)$/

function edgeLabelFor(kind) {
  if (_STATIC_EDGE_LABELS[kind]) return _STATIC_EDGE_LABELS[kind]
  const match = _WHEN_EDGE_KIND_RE.exec(kind)
  return match ? `when ${Number(match[1]) + 1}` : null
}

function isConditionalEdgeKind(kind) {
  return kind in _STATIC_EDGE_LABELS || _WHEN_EDGE_KIND_RE.test(kind)
}

export function renderMermaidDefinition(graph, diagramState, theme = 'dark') {
  const { currentLine, visitedLines, takenKindByLine } = diagramState
  const palette = getMermaidPalette(theme)
  const lines = ['flowchart TD']

  for (const node of graph.nodes) {
    lines.push(nodeMermaidText(node))
  }
  lines.push('')

  // Emit edges in a fixed order and remember each one's index, since
  // Mermaid's `linkStyle` addresses edges positionally.
  const takenLinkStyleIndexes = []
  const notTakenLinkStyleIndexes = []

  graph.edges.forEach((edge, index) => {
    const label = edgeLabelFor(edge.kind)
    lines.push(label ? `  ${edge.from} -->|${label}| ${edge.to}` : `  ${edge.from} --> ${edge.to}`)

    if (isConditionalEdgeKind(edge.kind)) {
      // This edge is one of a conditional group (2+ for IF/WHILE, N+1
      // for CASE) leaving a node whose line we may have visited -- look
      // up which one was taken.
      const sourceNode = graph.nodes.find((n) => n.id === edge.from)
      const taken = sourceNode && takenKindByLine.get(sourceNode.line)
      if (taken) {
        if (taken === edge.kind) takenLinkStyleIndexes.push(index)
        else notTakenLinkStyleIndexes.push(index)
      }
    }
  })
  lines.push('')

  // Literal hex only -- Mermaid's own `classDef`/`linkStyle` mini
  // grammar parses these as plain color tokens and rejects CSS
  // functions like var(...) or rgba(...) (confirmed: it throws a
  // parse error the moment it hits the '(' ). These values come from
  // mermaidColors.js's per-theme palette -- amber = current node, teal
  // = visited/taken, the same two semantic accents used everywhere
  // else in the app, no flowchart-only palette.
  lines.push(`  classDef current fill:${palette.amberDim},stroke:${palette.amber},stroke-width:3px,color:${palette.textPrimary};`)
  lines.push(`  classDef visited fill:${palette.tealDim},stroke:${palette.teal},stroke-width:1px,color:${palette.textPrimary};`)
  lines.push(`  classDef terminal fill:${palette.terminalFill},stroke:${palette.terminalBorder},color:${palette.terminalText};`)
  // Entry (amber "start") and RETURN (teal "end") are permanent bookend
  // colors, not just current/visited overlays -- a RETURN can only ever
  // be the *last* step of a trace (execution halts there), so it would
  // never actually pick up the generic 'visited' class, and it must
  // never render 'current' amber (wrong accent for "success/end"). Each
  // gets a dim resting shade plus a brighter "-current" shade so
  // reaching either one is still visibly distinct from merely having it
  // on screen -- same current-step highlighting guarantee every other
  // node gets, just recolored to fit the bookend semantics.
  lines.push(`  classDef entryNode fill:${palette.amberDim},stroke:${palette.amber},stroke-width:1px,color:${palette.textPrimary};`)
  lines.push(`  classDef returnNode fill:${palette.tealDim},stroke:${palette.teal},stroke-width:1px,color:${palette.textPrimary};`)
  lines.push(`  classDef returnCurrent fill:${palette.tealDim},stroke:${palette.teal},stroke-width:3px,color:${palette.textPrimary};`)

  const currentNode = graph.nodes.find((n) => n.line === currentLine)

  // One class per node, grouped so each classDef only needs one `class`
  // statement. Precedence: RETURN and the entry node keep their own
  // bookend color (dim/bright by current-ness); every other node keeps
  // the original current/visited/untouched scheme unchanged.
  const classGroups = new Map()
  const addToClass = (className, nodeId) => {
    if (!classGroups.has(className)) classGroups.set(className, [])
    classGroups.get(className).push(nodeId)
  }

  for (const node of graph.nodes) {
    const isCurrent = currentNode?.id === node.id
    if (node.kind === 'ReturnNode') {
      addToClass(isCurrent ? 'returnCurrent' : 'returnNode', node.id)
    } else if (node.id === START_ID && node.shape === 'stadium') {
      addToClass(isCurrent ? 'current' : 'entryNode', node.id)
    } else if (isCurrent) {
      addToClass('current', node.id)
    } else if (node.line !== undefined && visitedLines.has(node.line)) {
      addToClass('visited', node.id)
    }
  }

  for (const [className, ids] of classGroups) {
    lines.push(`  class ${ids.join(',')} ${className};`)
  }

  for (const index of takenLinkStyleIndexes) {
    lines.push(`  linkStyle ${index} stroke:${palette.teal},stroke-width:3px;`)
  }
  for (const index of notTakenLinkStyleIndexes) {
    lines.push(`  linkStyle ${index} stroke:${palette.lineColor},stroke-width:1px,stroke-dasharray:4 3;`)
  }

  return lines.join('\n')
}
