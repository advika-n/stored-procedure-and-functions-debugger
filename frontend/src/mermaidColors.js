// Mermaid's own config grammar (mermaid.initialize's themeVariables, and
// the classDef/linkStyle lines cfg.js generates) only accepts literal
// color values -- it rejects CSS functions like var(...) outright (see
// cfg.js's comment on this, confirmed by hitting that parse error
// directly). So the flowchart can't just read theme.css's custom
// properties the way every other component does; these are a hand-kept
// mirror of the same dark/light values instead. Keep this in sync with
// theme.css by hand whenever either one changes.
//
// amber/teal here are the *darkened* light-mode text/stroke shade (same
// rule theme.css's --accent-amber/teal follow); amberDim/tealDim are a
// light *fill* tint for a node's interior, analogous to --accent-*-bg.
export const MERMAID_PALETTE = {
  dark: {
    background: '#161d2e',
    primaryColor: '#1d2538',
    primaryBorderColor: '#2a3348',
    textPrimary: '#edeff4',
    lineColor: '#2a3348',
    amber: '#e8a23d',
    amberDim: '#3a2e18',
    teal: '#4fb0a5',
    tealDim: '#1c332f',
    terminalFill: '#1d2538',
    terminalBorder: '#2a3348',
    terminalText: '#8891a6',
  },
  light: {
    background: '#ffffff',
    primaryColor: '#eef0f4',
    primaryBorderColor: '#cdd3dc',
    textPrimary: '#16202e',
    lineColor: '#cdd3dc',
    amber: '#8a4a08',
    amberDim: '#fbe7c8',
    teal: '#0c645d', // kept in sync with theme.css's --accent-teal (light) -- see its comment
    tealDim: '#d7f0ec',
    terminalFill: '#eef0f4',
    terminalBorder: '#cdd3dc',
    terminalText: '#5b6472',
  },
}

export function getMermaidPalette(theme) {
  return MERMAID_PALETTE[theme] ?? MERMAID_PALETTE.dark
}
