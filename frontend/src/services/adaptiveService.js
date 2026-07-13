import api from '../config/api';

export const adaptiveService = {
  /** POST /adaptive-plan/generate */
  generatePlan: async (userId, documentConcepts = []) => {
    const response = await api.post('/adaptive-plan/generate', {
      user_id: userId,
      document_concepts: documentConcepts,
    });
    if (!response.data?.success) {
      throw new Error(response.data?.error || 'Failed to generate adaptive plan.');
    }
    return response.data;
  },

  /** GET /adaptive-plan/current/:userId */
  getCurrentRecommendation: async (userId) => {
    const response = await api.get(`/adaptive-plan/current/${userId}`);
    if (!response.data?.success) {
      throw new Error(response.data?.error || 'Failed to fetch current recommendation.');
    }
    return response.data;
  },

  /** GET /adaptive-plan/learning-path/:userId */
  getLearningPath: async (userId) => {
    const response = await api.get(`/adaptive-plan/learning-path/${userId}`);
    if (!response.data?.success) {
      throw new Error(response.data?.error || 'Failed to fetch learning path.');
    }
    return response.data;
  },

  /** POST /adaptive-plan/next-step */
  nextStep: async (userId) => {
    const response = await api.post('/adaptive-plan/next-step', { user_id: userId });
    if (!response.data?.success) {
      throw new Error(response.data?.error || 'Failed to advance step.');
    }
    return response.data;
  },

  /** POST /adaptive-plan/complete-step */
  completeStep: async (userId, step) => {
    const response = await api.post('/adaptive-plan/complete-step', { user_id: userId, step });
    if (!response.data?.success) {
      throw new Error(response.data?.error || 'Failed to complete step.');
    }
    return response.data;
  },
};

