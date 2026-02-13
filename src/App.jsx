import { useCallback, useEffect, useState } from 'react'
import MapboxExample from './components/MapboxExample'
import InstructionsModal from './components/InstructionsModal'
import './App.css'

function App() {
  const [onboardingPhase, setOnboardingPhase] = useState('visible')

  useEffect(() => {
    if (onboardingPhase !== 'exiting') return

    const timer = setTimeout(() => {
      setOnboardingPhase('done')
    }, 650)

    return () => clearTimeout(timer)
  }, [onboardingPhase])

  const handleExplore = () => {
    if (onboardingPhase !== 'visible') return
    setOnboardingPhase('exiting')
  }

  const handleReturnToInstructions = useCallback(() => {
    setOnboardingPhase('visible')
  }, [])

  const handleDismissOnboardingFromMap = useCallback(() => {
    setOnboardingPhase('done')
  }, [])

  return (
    <div style={{ width: '100vw', height: '100vh' }}>
      <MapboxExample
        onboardingPhase={onboardingPhase}
        onReturnToInstructions={handleReturnToInstructions}
        onDismissOnboarding={handleDismissOnboardingFromMap}
      />
      {onboardingPhase !== 'done' ? <InstructionsModal phase={onboardingPhase} onClose={handleExplore} /> : null}
    </div>
  )
}

export default App
