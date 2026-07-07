import { createContext, useContext, useMemo, useState } from 'react';

const JourneyContext = createContext(null);

export function JourneyProvider({ children }) {
  const [journey, setJourney] = useState(null);
  const [currentStep, setCurrentStep] = useState(null);

  const value = useMemo(() => ({ journey, setJourney, currentStep, setCurrentStep }), [journey, currentStep]);

  return <JourneyContext.Provider value={value}>{children}</JourneyContext.Provider>;
}

export function useJourney() {
  return useContext(JourneyContext);
}
