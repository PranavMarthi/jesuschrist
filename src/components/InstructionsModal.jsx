import { useEffect } from 'react'

function InstructionsModal({ phase, onClose }) {
  useEffect(() => {
    const handleKeyDown = (event) => {
      if (event.key !== 'Enter') return
      event.preventDefault()
      onClose()
    }

    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [onClose])

  return (
    <aside className={`instructions-modal ${phase === 'exiting' ? 'is-exiting' : 'is-visible'}`} aria-label="Map instructions">
      <div className="instructions-modal__header">
        <div />
        <div />

        <p className="instructions-modal__eyebrow">Quick Start</p>
        <div height="1px" />
        <h2 className="instructions-modal__title">PolyWorld</h2>

        {/* <p className="instructions-modal__subtitle">
          Your Predictions, in Real Life.
        </p> */}

        <div height="1px" />
        <div />

        <p className="instructions-modal__subtitle instructions-modal__subtitle--mono">
          Your Predictions, in Real Life.
        </p>


        <div />
        <p className="instructions-modal__subtitle instructions-modal__subtitle--mono">
          Polyworld allows you to see where prediction markets are happening in the real world. Geopolitics, sports, culture, finance, and more.
        </p>

        <div />
        <div />

        <p className="instructions-modal__hint">Tip: Try searching “Tokyo” or “Madison Square Garden”.</p>
      </div>


      <div />

      <button className="instructions-modal__close" type="button" onClick={onClose}>
        Explore <span style={{ marginLeft: '10px' }}>↵</span>
      </button>
    </aside>
  )
}

export default InstructionsModal
