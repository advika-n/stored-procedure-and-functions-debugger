// Rasterizes the already-rendered flowchart -- the live DOM element
// holding Mermaid's SVG output, already sitting on screen in
// SqlConsolePage.jsx's `.diagram-svg` container -- to a PNG data URL.
// Used only when downloading a PDF/Document report -- a plain-text
// report can't embed an image at all, and handing the raw SVG to the
// backend isn't viable: Mermaid's markup leans on `<foreignObject>`
// HTML labels that no lightweight server-side SVG-to-raster path
// renders reliably (see backend/app/report.py's module docstring for
// the fuller rationale).
//
// Three real bugs, found live in order, each hiding the next (see
// PROMPT_LOG.md for the full investigation):
//   1. A sizing bug (fixed below, see width/height derivation): the
//      original width/height detection regex-scanned the ENTIRE svgString
//      for the first width="..."/height="..." match, not just the root
//      <svg> tag's own sizing. Mermaid's root tag sets width as a
//      *percentage* (`width="100%"`, no height attribute at all) with the
//      real pixel size only in its `viewBox`, so that scan skipped the
//      root tag entirely and landed on the first width="0"/height="0" it
//      found deeper in the markup (an internal marker/defs element) --
//      silently rasterizing a 1x1 image every time, indistinguishable
//      from "no diagram" once embedded in a PDF/DOCX page.
//   2. Once #1 was fixed and the canvas was actually the right size,
//      `canvas.toDataURL()` started throwing `SecurityError: Tainted
//      canvases may not be exported` -- confirmed live, on EVERY sample,
//      regardless of the image source being a same-origin blob URL. Any
//      SVG containing a `<foreignObject>` (which is exactly how Mermaid
//      renders node/edge labels -- rich HTML text, not plain SVG <text>)
//      permanently taints a <canvas> once drawn via <img> + drawImage;
//      this is a hard browser restriction on rasterizing <foreignObject>
//      HTML content through an <img> element, not fixable by tweaking the
//      SVG markup. Mermaid's own `flowchart.htmlLabels: false` config
//      (which should avoid <foreignObject> entirely) was tried too and
//      confirmed NOT to actually suppress it in this Mermaid version -- a
//      known upstream limitation, not a config mistake here.
//   3. html2canvas (which walks the live DOM instead of decoding an
//      <img>, sidestepping #2 entirely) was tried next and does run
//      without error, but renders the whole diagram as a blank white
//      image -- confirmed live by sampling the resulting canvas's own
//      pixel data (100% pure white, not even node borders/edges painted)
//      -- a known html2canvas gap in nested-SVG support, not something
//      this app's markup is doing wrong.
// Fixed for real by converting each <foreignObject> label to a plain SVG
// <text> element (see foreignObjectsToSvgText below) BEFORE rasterizing
// through the same <img> + <canvas> approach #1 already fixed the sizing
// for -- a <foreignObject>-free SVG carries none of #2's restriction, so
// this is the one combination that's actually been confirmed, live, to
// produce a real, visible embedded diagram image.
const SVG_NS = 'http://www.w3.org/2000/svg'

// Mermaid inlines a per-label text color directly as `style="color: ... "`
// on some spans (not all -- unstyled ones fall back to the diagram's own
// root default, see `defaultFill` below); reading it back is just a plain
// DOM style-property read on a still-attached-nowhere clone, no
// getComputedStyle/layout needed, so this works on a detached SVG too.
function colorFromInlineStyle(el) {
  const styled = el.querySelector('[style*="color"]')
  if (!styled) return null
  const color = styled.style.color
  return color || null
}

// Replaces every <foreignObject> label (Mermaid's HTML-based node/edge
// text) in `svgRoot` with an equivalent plain SVG <text>, in place. Each
// foreignObject's own width/height (its label's bounding box, in its
// *parent* <g>'s already-translated local coordinate space -- see the
// `<g transform="translate(x, y)">` wrapper Mermaid emits around every
// label) becomes the <text>'s centering box, so the existing ancestor
// transform still positions it correctly with no coordinate math of this
// function's own. Multi-line labels (Mermaid wraps long statement text at
// `max-width: 200px`) get one <tspan> per source <p>, stacked with a
// fixed line height -- an approximation of Mermaid's own font-metric-based
// layout, not a pixel-perfect match, but legible and correctly centered,
// which is what a report figure needs.
function foreignObjectsToSvgText(svgRoot, defaultFill) {
  const foreignObjects = Array.from(svgRoot.querySelectorAll('foreignObject'))
  // { element, maxWidth } per label, handed to shrinkTextNodesToFit below --
  // Mermaid sized each shape to fit its OWN (HTML-based) rendering of this
  // exact text exactly, so the plain SVG <text> substitute built here can
  // come out slightly wider at the same nominal font-size (HTML and SVG
  // text layout use different metrics) and overflow the shape it's
  // centered in; this list is what lets that get corrected afterward.
  const textNodes = []
  for (const fo of foreignObjects) {
    const width = parseFloat(fo.getAttribute('width')) || 0
    const height = parseFloat(fo.getAttribute('height')) || 0
    const paragraphs = Array.from(fo.querySelectorAll('p'))
    const lines = (paragraphs.length ? paragraphs.map((p) => p.textContent) : [fo.textContent])
      .map((line) => line.trim())
      .filter(Boolean)

    if (lines.length === 0) {
      // An empty label placeholder (Mermaid emits one for every edge even
      // when it carries no text) -- nothing to draw, and leaving an empty
      // 0x0 foreignObject behind is harmless, but removing it keeps the
      // converted markup free of foreignObject entirely, which is the
      // whole point of this pass.
      fo.remove()
      continue
    }

    // A node label (e.g. "DECLARE ...", inside a `.node` group) always
    // sits on top of that node's own colored shape fill, so the on-screen
    // diagram's own near-white default text color (`defaultFill`, correct
    // for the app's dark theme) stays legible once transplanted onto this
    // export's white page too -- the node shape's own fill/stroke colors
    // come through unmodified (this pass only touches <foreignObject>, not
    // <rect>/<path>). An edge/condition label ("then"/"else"/"TRUE"/
    // "FALSE", inside a `.edgeLabel` group) has no shape behind it at all
    // -- it sits directly on whatever background is behind the whole
    // diagram, which on screen is the app's own dark canvas but in this
    // export is a plain white page, so that same near-white default would
    // render as invisible/near-invisible text (confirmed live -- see
    // PROMPT_LOG.md). Only labels with no inline color of their own AND no
    // enclosing node shape get the dark, page-safe fallback instead.
    const isEdgeLabel = !!fo.closest('.edgeLabel')
    const fallbackFill = isEdgeLabel ? '#1a1a1a' : defaultFill
    const fill = colorFromInlineStyle(fo) || fallbackFill
    const text = svgRoot.ownerDocument.createElementNS(SVG_NS, 'text')
    text.setAttribute('x', String(width / 2))
    text.setAttribute('text-anchor', 'middle')
    text.setAttribute('font-family', "'IBM Plex Mono', monospace")
    text.setAttribute('font-size', '15')
    // fill as a bare presentation ATTRIBUTE loses to the diagram's own
    // embedded <style> block -- confirmed live: `#flowchart-1{fill:
    // #edeff4}` (the root selector mermaidColors.js's theme sets) beat a
    // `fill="..."` attribute on this exact element every time, no matter
    // what color this pass chose, because an SVG presentation attribute is
    // the WEAKEST possible CSS origin (below even a plain, non-!important
    // stylesheet rule). An inline `style="fill:..."` outranks that
    // embedded stylesheet rule the same way any inline style always beats
    // an external one, so this pass's own fill choice -- including the
    // edge-label dark-fallback fix directly above -- actually sticks.
    if (fill) text.style.fill = fill

    const lineHeight = 17
    const startY = height / 2 - ((lines.length - 1) * lineHeight) / 2 + 5
    lines.forEach((line, i) => {
      const tspan = svgRoot.ownerDocument.createElementNS(SVG_NS, 'tspan')
      tspan.setAttribute('x', String(width / 2))
      tspan.setAttribute('y', String(startY + i * lineHeight))
      tspan.textContent = line
      text.appendChild(tspan)
    })

    fo.replaceWith(text)
    textNodes.push({ element: text, maxWidth: width })
  }
  return textNodes
}

// SVG text-length measurement only works on an element that's actually
// attached and laid out in the document -- a detached clone reports 0 for
// `getComputedTextLength()`. Temporarily attaches `svgRoot` off-screen
// (never visible, never affects layout of anything else), shrinks any
// label whose measured width exceeds the box Mermaid originally sized for
// it, then detaches `svgRoot` again so the caller's clone ends up back in
// its original (still-detached) state, just with corrected font sizes.
function shrinkTextNodesToFit(svgRoot, textNodes) {
  if (textNodes.length === 0) return
  const host = document.createElementNS(SVG_NS, 'svg')
  host.setAttribute('style', 'position:fixed; left:-99999px; top:-99999px; visibility:hidden;')
  host.appendChild(svgRoot)
  document.body.appendChild(host)
  try {
    for (const { element, maxWidth } of textNodes) {
      if (!maxWidth) continue
      const widest = Math.max(
        0,
        ...Array.from(element.querySelectorAll('tspan'), (tspan) => tspan.getComputedTextLength()),
      )
      const available = maxWidth * 0.94 // a little breathing room on both sides
      if (widest > available) {
        const currentSize = parseFloat(element.getAttribute('font-size'))
        element.setAttribute('font-size', String(Math.max(8, currentSize * (available / widest))))
      }
    }
  } finally {
    host.removeChild(svgRoot)
    document.body.removeChild(host)
  }
}

// The diagram's own default text color, for any label whose span carries
// no per-label inline color of its own -- pulled straight from the live
// (still-attached, so getComputedStyle actually resolves) root <svg>'s
// own computed `color`/`fill`, which mermaidColors.js's palette already
// sets as `themeVariables.primaryTextColor` when the diagram was first
// rendered on screen. Read from the ORIGINAL element, not the detached
// clone this module goes on to build -- a detached node has no
// stylesheet cascade applied, so its own computed style is meaningless.
function defaultTextFill(originalSvgElement) {
  const computed = getComputedStyle(originalSvgElement)
  return computed.fill && computed.fill !== 'none' ? computed.fill : computed.color || '#000000'
}

function svgDimensions(svgElement) {
  const viewBox = svgElement.viewBox?.baseVal
  if (viewBox && viewBox.width && viewBox.height) {
    return { width: viewBox.width, height: viewBox.height }
  }
  const rect = svgElement.getBoundingClientRect()
  return { width: rect.width || 800, height: rect.height || 600 }
}

function rasterizeSvgString(svgString, width, height, scale) {
  return new Promise((resolve) => {
    const blob = new Blob([svgString], { type: 'image/svg+xml;charset=utf-8' })
    const url = URL.createObjectURL(blob)
    const image = new Image()

    image.onload = () => {
      try {
        const canvas = document.createElement('canvas')
        canvas.width = Math.max(1, Math.round(width * scale))
        canvas.height = Math.max(1, Math.round(height * scale))
        const ctx = canvas.getContext('2d')
        // The exported PNG always gets a white background regardless of
        // the app's active Day/Night theme -- this image is headed into a
        // document meant to be read/printed on a white page, not
        // displayed inside the themed UI, so matching the on-screen theme
        // would be the wrong goal.
        ctx.fillStyle = '#ffffff'
        ctx.fillRect(0, 0, canvas.width, canvas.height)
        ctx.drawImage(image, 0, 0, canvas.width, canvas.height)
        resolve(canvas.toDataURL('image/png'))
      } catch {
        // Best-effort: a rasterization failure just means the report
        // ships without a diagram image, not a failed download overall.
        resolve(null)
      } finally {
        URL.revokeObjectURL(url)
      }
    }
    image.onerror = () => {
      URL.revokeObjectURL(url)
      resolve(null)
    }
    image.src = url
  })
}

// `element` is the live `.diagram-svg` container (holding Mermaid's <svg>
// as its one child) already rendered on screen.
export async function rasterizeDiagramElementToPng(element, { scale = 2 } = {}) {
  if (!element) return null
  const svgElement = element.tagName === 'svg' ? element : element.querySelector('svg')
  if (!svgElement) return null

  try {
    const fill = defaultTextFill(svgElement)
    const { width, height } = svgDimensions(svgElement)

    const clone = svgElement.cloneNode(true)
    const textNodes = foreignObjectsToSvgText(clone, fill)
    shrinkTextNodesToFit(clone, textNodes)
    // Explicit pixel width/height on the clone -- the original only ever
    // carries a percentage width (see this file's own history above), and
    // an <img> needs a real intrinsic size to rasterize at, not "100%" of
    // an offscreen blob URL with no layout context of its own.
    clone.setAttribute('width', String(width))
    clone.setAttribute('height', String(height))

    const svgString = new XMLSerializer().serializeToString(clone)
    return await rasterizeSvgString(svgString, width, height, scale)
  } catch {
    return null
  }
}
