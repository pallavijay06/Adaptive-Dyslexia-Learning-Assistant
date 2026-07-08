import api from '../config/api';

export const adaptiveService = {
  /**
   * POST /adaptive-plan/generate
   * Initializes a personalized learning journey for the user.
   * Returns the full backend plan on success, throws on failure.
   */
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
};

