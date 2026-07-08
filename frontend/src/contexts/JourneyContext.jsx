import { createContext, useContext, useMemo, useState } from 'react';

const JourneyContext = createContext(null);

export function JourneyProvider({ children }) {
  // Raw backend objects only — no derived state.
  const [adaptiveLearningPlan, setAdaptiveLearningPlan] = useState(null);
  const [currentRecommendation, setCurrentRecommendation] = useState(null);
  const [learningPath, setLearningPath] = useState(null);
  const [currentStep, setCurrentStep] = useState(null);
  const [documentId, setDocumentId] = useState(null);

  const value = useMemo(() => ({
    adaptiveLearningPlan,
    setAdaptiveLearningPlan,
    currentRecommendation,
    setCurrentRecommendation,
    learningPath,
    setLearningPath,
    currentStep,
    setCurrentStep,
    documentId,
    setDocumentId,
  }), [adaptiveLearningPlan, currentRecommendation, learningPath, currentStep, documentId]);

  return <JourneyContext.Provider value={value}>{children}</JourneyContext.Provider>;
}

export function useJourney() {
  return useContext(JourneyContext);
}
