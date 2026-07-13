import api from '../config/api';

export const stemService = {
  analyzeDocumentText: async (text) => {
    const res = await api.post('/stem/document/analyze', { text }, { timeout: 120000 });
    if (!res.data?.success) {
      throw new Error(res.data?.error || 'STEM analysis failed.');
    }
    return res.data;
  },

  extractFormulas: async (text) => {
    const res = await api.post('/stem/formula/extract', { text }, { timeout: 120000 });
    if (!res.data?.success) {
      throw new Error(res.data?.error || 'Formula extraction failed.');
    }
    return res.data;
  },

  explainFormula: async (formula) => {
    const res = await api.post('/stem/formula/explain', { formula }, { timeout: 120000 });
    if (!res.data?.success) {
      throw new Error(res.data?.error || 'Formula explanation failed.');
    }
    return res.data.explanation;
  },

  getConceptBreakdown: async (text) => {
    const res = await api.post('/stem/concept-breakdown', { text }, { timeout: 120000 });
    if (!res.data?.success) {
      throw new Error(res.data?.error || 'Concept breakdown failed.');
    }
    return res.data;
  },

  solveProblem: async (problem) => {
    const res = await api.post('/stem/step-solver', { problem }, { timeout: 120000 });
    if (!res.data?.success) {
      throw new Error(res.data?.error || 'Step solver failed.');
    }
    return res.data.solution;
  },

  explainDiagram: async (file) => {
    const formData = new FormData();
    formData.append('file', file);
    const res = await api.post('/stem/diagram/explain', formData, {
      timeout: 180000,
      headers: { 'Content-Type': 'multipart/form-data' },
    });
    if (!res.data?.success) {
      throw new Error(res.data?.error || 'Diagram explanation failed.');
    }
    return res.data.explanation;
  },
};
