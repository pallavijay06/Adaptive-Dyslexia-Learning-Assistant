import api from '../config/api';

export const adaptiveService = {
  /** POST /adaptive-plan/generate */
  generatePlan: async (userId, documentConcepts = [], documentId = null) => {
    const response = await api.post('/adaptive-plan/generate', {
      user_id: userId,
      document_concepts: documentConcepts,
      document_id: documentId,
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

  /** POST /adaptive-plan/revision-notes */
  generateRevisionNotes: async (options = {}) => {
    const revisionTopics = Array.isArray(options) ? options : options.revisionTopics ?? [];
    const revisionReason = Array.isArray(options) ? null : options.revisionReason ?? null;
    const userId = Array.isArray(options) ? null : options.userId ?? null;
    const documentId = Array.isArray(options) ? null : options.documentId ?? null;

    const payload = {
      revision_topics: revisionTopics,
      user_id: userId,
      document_id: documentId,
      revision_reason: revisionReason,
    };

    console.log('[adaptiveService] Sending revision-notes request', payload);
    const response = await api.post('/adaptive-plan/revision-notes', payload, { timeout: 180000 });
    console.log('[adaptiveService] Received revision-notes response', response?.data);

    if (!response.data?.success) {
      throw new Error(response.data?.error || 'Failed to generate revision notes.');
    }
    return response.data;
  },
};

