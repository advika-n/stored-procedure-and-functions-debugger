import { useEffect, useRef } from 'react'

// Course-grading requirement: student photo, name, register number, and
// guide, surfaced from a nav trigger as a modal rather than a route (see
// Layout.jsx). All four fields below are placeholders -- swap the photo
// slot for a real <img> and the two bracketed strings for the real
// values once you have them; nothing else about this component needs
// to change to do that.
function DevelopedByModal({ onClose }) {
  const panelRef = useRef(null)

  // Escape to dismiss, from anywhere -- matches the close button and
  // click-outside below as the three required dismiss paths.
  useEffect(() => {
    function handleKeyDown(event) {
      if (event.key === 'Escape') onClose()
    }
    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [onClose])

  // Focus the dialog on open (so Escape/Tab work immediately without a
  // click first) and stop the page behind it from scrolling while open.
  useEffect(() => {
    panelRef.current?.focus()
    const previousOverflow = document.body.style.overflow
    document.body.style.overflow = 'hidden'
    return () => {
      document.body.style.overflow = previousOverflow
    }
  }, [])

  function handleOverlayMouseDown(event) {
    // Only the backdrop itself, not a click that started inside the
    // panel and dragged/released outside it (e.g. selecting text).
    if (event.target === event.currentTarget) onClose()
  }

  return (
    <div className="modal-overlay" onMouseDown={handleOverlayMouseDown}>
      <div
        ref={panelRef}
        className="panel developed-by-modal"
        role="dialog"
        aria-modal="true"
        aria-labelledby="developed-by-name"
        tabIndex={-1}
      >
        <span className="panel-tab">DEVELOPED BY</span>
        <button className="modal-close" onClick={onClose} aria-label="Close">
          ✕
        </button>

        <div className="developed-by-content">
          {/* PLACEHOLDER -- replace with <img src="/path/to/photo.jpg" alt="[NAME]" /> */}
          <div className="developed-by-photo" aria-hidden="true">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
              <circle cx="12" cy="8" r="4" />
              <path d="M4 20c0-4.4 3.6-8 8-8s8 3.6 8 8" />
            </svg>
          </div>

          <h2 id="developed-by-name" className="developed-by-name">
            [NAME]
          </h2>
          <p className="developed-by-reg">Register Number: [REGISTER NUMBER]</p>
          <p className="developed-by-guide">Guided By: Dr. Swaminathan A, Assistant Professor</p>
        </div>
      </div>
    </div>
  )
}

export default DevelopedByModal
