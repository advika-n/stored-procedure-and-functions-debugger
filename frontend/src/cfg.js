// Builds a control-flow graph from the procedure AST (the shape the
// backend returns from POST /debug -- see backend/app/parser.py), and
// renders it as a Mermaid flowchart definition.
//
// This is deliberately AST-driven, not step-driven: the diagram's
// shape (which nodes exist, how they connect) comes entirely from the
// procedure's structure and is built once per Debug run. Only the
// *styling* -- which node is "current", which branch lit up as taken --
// is recomputed as the user steps through the execution trace.

// -- rendering AST expression/statement nodes back to source text ----------
// (mirrors backend/app/interpreter.py's render_expr / render_statement_header)

function renderExpr(node) {
  switch (node.type) {
    case 'NumberLiteral':
      return String(node.value)
    case 'StringLiteral':
      return `'${node.value}'`
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
// 'seq' | 'then' | 'else' | 'loop' | 'loop-exit'.
function emitBlock(statements, entryTails, nodes, edges) {
  let tails = entryTails

  for (const stmt of statements) {
    const nodeId = `n${stmt.line}`

    if (stmt.type === 'IfStatement' || stmt.type === 'WhileStatement') {
      nodes.push({ id: nodeId, label: renderStatementHeader(stmt), shape: 'diamond', line: stmt.line, kind: stmt.type })
    } else {
      nodes.push({ id: nodeId, label: renderStatementHeader(stmt), shape: 'rect', line: stmt.line, kind: stmt.type })
    }

    for (const tail of tails) {
      edges.push({ from: tail.nodeId, to: nodeId, kind: tail.kind })
    }

    if (stmt.type === 'IfStatement') {
      const thenTails = emitBlock(stmt.then_body, [{ nodeId, kind: 'then' }], nodes, edges)
      const elseTails = stmt.else_body
        ? emitBlock(stmt.else_body, [{ nodeId, kind: 'else' }], nodes, edges)
        : [{ nodeId, kind: 'else' }]
      tails = [...thenTails, ...elseTails]
    } else if (stmt.type === 'WhileStatement') {
      const bodyTails = emitBlock(stmt.body, [{ nodeId, kind: 'loop' }], nodes, edges)
      for (const tail of bodyTails) {
        edges.push({ from: tail.nodeId, to: nodeId, kind: 'loop-back' })
      }
      tails = [{ nodeId, kind: 'loop-exit' }]
    } else {
      tails = [{ nodeId, kind: 'seq' }]
    }
  }

  return tails
}

/** Build a { nodes, edges } control-flow graph from a ProcedureNode AST. */
export function buildFlowchartGraph(ast) {
  const nodes = [
    { id: START_ID, label: 'Start', shape: 'terminal' },
    { id: END_ID, label: 'End', shape: 'terminal' },
  ]
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
 * passed already, and -- for each IF/WHILE node reached so far --
 * which of its outgoing branches was actually taken most recently
 * (a node can be revisited if it's inside a loop).
 */
export function computeDiagramState(graph, steps, currentStepIndex) {
  const visitedLines = new Set()
  const takenKindByLine = new Map() // line -> 'then' | 'else' | 'loop' | 'loop-exit'

  const executed = steps.slice(0, currentStepIndex + 1)
  for (const step of executed) {
    visitedLines.add(step.line)
    if (step.branch) {
      if (step.branch.path === 'then') takenKindByLine.set(step.line, 'then')
      else if (step.branch.path === 'else') takenKindByLine.set(step.line, 'else')
      // path === 'none': condition false, no ELSE -- nothing taken to mark
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
  if (node.shape === 'terminal') return `  ${node.id}(["${label}"])`
  return `  ${node.id}["${label}"]`
}

/** Render the graph + current playback state into a Mermaid flowchart definition. */
export function renderMermaidDefinition(graph, diagramState) {
  const { currentLine, visitedLines, takenKindByLine } = diagramState
  const lines = ['flowchart TD']

  for (const node of graph.nodes) {
    lines.push(nodeMermaidText(node))
  }
  lines.push('')

  // Emit edges in a fixed order and remember each one's index, since
  // Mermaid's `linkStyle` addresses edges positionally.
  const edgeLabel = { then: 'then', else: 'else', loop: 'loop', 'loop-exit': 'exit' }
  const takenLinkStyleIndexes = []
  const notTakenLinkStyleIndexes = []

  graph.edges.forEach((edge, index) => {
    const label = edgeLabel[edge.kind]
    lines.push(label ? `  ${edge.from} -->|${label}| ${edge.to}` : `  ${edge.from} --> ${edge.to}`)

    if (edge.kind === 'then' || edge.kind === 'else' || edge.kind === 'loop' || edge.kind === 'loop-exit') {
      // This edge is one of a conditional pair leaving a node whose
      // line we may have visited -- look up which side was taken.
      const sourceNode = graph.nodes.find((n) => n.id === edge.from)
      const taken = sourceNode && takenKindByLine.get(sourceNode.line)
      if (taken) {
        if (taken === edge.kind) takenLinkStyleIndexes.push(index)
        else notTakenLinkStyleIndexes.push(index)
      }
    }
  })
  lines.push('')

  lines.push('  classDef current fill:#ffd54f,stroke:#8a6d00,stroke-width:3px,color:#000;')
  lines.push('  classDef visited fill:#e6f4ea,stroke:#1e7e34,stroke-width:1px,color:#1e7e34;')
  lines.push('  classDef terminal fill:#eee,stroke:#999,color:#333;')

  const currentNode = graph.nodes.find((n) => n.line === currentLine)
  const visitedNodeIds = graph.nodes
    .filter((n) => n.line !== undefined && n.line !== currentLine && visitedLines.has(n.line))
    .map((n) => n.id)

  if (visitedNodeIds.length > 0) lines.push(`  class ${visitedNodeIds.join(',')} visited;`)
  if (currentNode) lines.push(`  class ${currentNode.id} current;`)

  for (const index of takenLinkStyleIndexes) {
    lines.push(`  linkStyle ${index} stroke:#2ea043,stroke-width:3px;`)
  }
  for (const index of notTakenLinkStyleIndexes) {
    lines.push(`  linkStyle ${index} stroke:#bbb,stroke-width:1px,stroke-dasharray:4 3;`)
  }

  return lines.join('\n')
}
