import api from '../config/api';

export const learningService = {
  /**
   * POST /document/<id>/simplify
   * Response: { success: true, simplified: string }
   */
  simplifyDocument: async (documentId) => {
    const res = await api.post(`/document/${documentId}/simplify`, {}, { timeout: 120000 });
    if (!res.data?.success) {
      throw new Error(res.data?.error || 'Simplification failed.');
    }
    return res.data.simplified;
  },

  /**
   * POST /document/<id>/simplify  (alias used by VisualLearningPanel)
   */
  fetchDocumentText: async (documentId) => {
    const res = await api.post(`/document/${documentId}/simplify`, {}, { timeout: 120000 });
    if (!res.data?.success) {
      throw new Error(res.data?.error || 'Could not fetch document text.');
    }
    return res.data.simplified;
  },

  /**
   * POST /visualize
   * Request:  { text: string, visual_type?: "flowchart"|"mind_map"|null, user_id?: number }
   * Response: { visual: { flowchart_url?, mindmap_url?, title, description, topic }, success: true }
   */
  generateVisual: async (text, visualType = null, userId = null) => {
    const payload = { text };
    if (visualType) payload.visual_type = visualType;
    if (userId != null) payload.user_id = userId;
    const res = await api.post('/visualize', payload, { timeout: 120000 });
    if (!res.data?.success) {
      throw new Error(res.data?.error || 'Visual generation failed.');
    }
    return res.data.visual;
  },

  /**
   * POST /document/<id>/vocabulary
   * Request:  { word_count?: number }
   * Response: { success: true, vocabulary: Array<{ word: string, meaning: string }> }
   */
  fetchVocabulary: async (documentId, wordCount = 10) => {
    const res = await api.post(
      `/document/${documentId}/vocabulary`,
      { word_count: wordCount },
      { timeout: 60000 },
    );
    if (!res.data?.success) {
      throw new Error(res.data?.error || 'Vocabulary extraction failed.');
    }
    return res.data.vocabulary;
  },

  /**
   * POST /vocabulary/explain
   * Request:  { word: string }
   * Response: { success: true, explanation: { word, meaning, explanation, example } }
   */
  explainWord: async (word) => {
    const res = await api.post('/vocabulary/explain', { word }, { timeout: 30000 });
    if (!res.data?.success) {
      throw new Error(res.data?.error || 'Word explanation failed.');
    }
    return res.data.explanation;
  },

  /**
   * POST /document/<id>/audio
   * Response: { success: true, audio_url: string, sentences: string[] }
   */
  generateAudio: async (documentId) => {
    const res = await api.post(`/document/${documentId}/audio`, {}, { timeout: 120000 });
    if (!res.data?.success) {
      throw new Error(res.data?.error || 'Audio generation failed.');
    }
    return res.data;
  },

  /**
   * POST /audio  (learning_routes)
   * Generates audio from arbitrary text — used for Simplified Notes audio.
   * Request:  { text: string }
   * Response: { success: true, audio_url: string }
   */
  generateAudioFromText: async (text) => {
    const res = await api.post('/audio', { text }, { timeout: 120000 });
    if (!res.data?.success) {
      throw new Error(res.data?.error || 'Audio generation failed.');
    }
    return res.data;
  },
};
