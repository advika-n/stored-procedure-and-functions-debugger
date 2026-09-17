// Nav/topic metadata for the Learn page's "Deep Dive" panel (formerly the
// standalone Theory tab's nav -- see LearnPage.jsx), kept separate from
// theoryContent.jsx so that file can export components only (plain
// data + JSX components mixed in one file breaks React Fast Refresh).
// StoredProceduresTopic is intentionally not listed here -- its content
// duplicated Learn's own Concept Explanation section.
import {
  ControlFlowTopic,
  CursorsTopic,
  ExceptionHandlingTopic,
  PuttingItTogetherTopic,
  VariablesTopic,
} from './theoryContent'

export const THEORY_TOPICS = [
  { id: 'variables', title: 'Variables', Content: VariablesTopic },
  { id: 'control-flow', title: 'Control Flow', Content: ControlFlowTopic },
  { id: 'cursors', title: 'Cursors', Content: CursorsTopic },
  { id: 'exception-handling', title: 'Exception Handling', Content: ExceptionHandlingTopic },
  { id: 'putting-it-together', title: 'Putting It Together', Content: PuttingItTogetherTopic },
]
