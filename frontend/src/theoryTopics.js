// Nav/topic metadata for the Theory section, kept separate from
// theoryContent.jsx so that file can export components only (plain
// data + JSX components mixed in one file breaks React Fast Refresh).
import {
  ControlFlowTopic,
  CursorsTopic,
  ExceptionHandlingTopic,
  PuttingItTogetherTopic,
  StoredProceduresTopic,
  VariablesTopic,
} from './theoryContent'

export const THEORY_TOPICS = [
  { id: 'stored-procedures', title: 'Stored Procedures & Functions', Content: StoredProceduresTopic },
  { id: 'variables', title: 'Variables', Content: VariablesTopic },
  { id: 'control-flow', title: 'Control Flow', Content: ControlFlowTopic },
  { id: 'cursors', title: 'Cursors', Content: CursorsTopic },
  { id: 'exception-handling', title: 'Exception Handling', Content: ExceptionHandlingTopic },
  { id: 'putting-it-together', title: 'Putting It Together', Content: PuttingItTogetherTopic },
]
