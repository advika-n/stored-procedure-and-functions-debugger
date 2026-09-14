// Rasterizes an already-rendered SVG string (the Mermaid flowchart's own
// output, already sitting in DebuggerPage.jsx's `diagramSvg` state) to a
// PNG data URL via an offscreen <canvas>. Used only when downloading a
// PDF/Document report -- a plain-text report can't embed an image at
// all, and handing the raw SVG to the backend isn't viable: Mermaid's
// markup leans on `<foreignObject>` HTML labels that no lightweight
// server-side SVG-to-raster path renders reliably (see backend/app/
// report.py's module docstring for the fuller rationale). A browser can
// rasterize its own already-rendered SVG through a canvas in a few
// lines, so that happens here instead, client-side, right before the
// report request goes out.
//
// The exported PNG always gets a white background regardless of the
// app's active Day/Night theme -- this image is headed into a document
// meant to be read/printed on a white page, not displayed inside the
// themed UI, so matching the on-screen theme would be the wrong goal.
export function rasterizeSvgToPng(svgString, { scale = 2 } = {}) {
  return new Promise((resolve) => {
    if (!svgString) {
      resolve(null)
      return
    }

    // Prefer the SVG's own width/height attributes (Mermaid always sets
    // these) for the intrinsic size; fall back to a generous default so
    // a malformed/sizeless SVG still produces *something* rather than a
    // blank 0x0 canvas.
    const widthMatch = svgString.match(/width="([\d.]+)(?:px)?"/)
    const heightMatch = svgString.match(/height="([\d.]+)(?:px)?"/)
    const width = widthMatch ? parseFloat(widthMatch[1]) : 800
    const height = heightMatch ? parseFloat(heightMatch[1]) : 600

    const blob = new Blob([svgString], { type: 'image/svg+xml;charset=utf-8' })
    const url = URL.createObjectURL(blob)
    const image = new Image()

    image.onload = () => {
      try {
        const canvas = document.createElement('canvas')
        canvas.width = Math.max(1, Math.round(width * scale))
        canvas.height = Math.max(1, Math.round(height * scale))
        const ctx = canvas.getContext('2d')
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
