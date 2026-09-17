import { useEffect, useRef } from 'react'
import developerPhoto from './assets/developer-photo.jpeg'
import guidePhoto from './assets/guide-photo.jpg'

// Course-grading requirement: student photo, name, register number, and
// guide, surfaced from a nav trigger as a modal rather than a route (see
// Layout.jsx). Student and guide get identical treatment -- one
// .developed-by-member row each (photo + role/name/detail stack).
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
          <div className="developed-by-member">
            <div className="developed-by-photo">
              <img src={developerPhoto} alt="N. Advika" />
            </div>
            <div className="developed-by-info">
              <p className="developed-by-role">Developed By:</p>
              <h2 id="developed-by-name" className="developed-by-name">
                N. Advika
              </h2>
              <p className="developed-by-reg">Register Number: 25BCE5669</p>
            </div>
          </div>

          <div className="developed-by-member">
            <div className="developed-by-photo">
              <img src={guidePhoto} alt="Dr. Swaminathan A" />
            </div>
            <div className="developed-by-info">
              <p className="developed-by-role">Guided By:</p>
              <h2 className="developed-by-name">Dr. Swaminathan A</h2>
              <p className="developed-by-reg">Assistant Professor</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

export default DevelopedByModal
