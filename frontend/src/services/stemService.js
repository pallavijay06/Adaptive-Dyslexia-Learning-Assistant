import api from '../config/api';

export const stemService = {
  // Load STEM analysis for a stored document by its database id.
  // Mirrors: process_stem_support(document_text) called in render_stem_mode()
  analyzeDocument: async (documentId) => {
    const res = await api.post(`/document/${documentId}/stem`, {}, { timeout: 120000 });
    if (!res.data?.success) {
      throw new Error(res.data?.error || 'STEM analysis failed.');
    }
    return res.data;
  },

  // Explain a single formula.
  // Mirrors: explain_formula(formula) in _render_formula_tab()
  explainFormula: async (formula) => {
    const res = await api.post('/stem/formula/explain', { formula }, { timeout: 120000 });
    if (!res.data?.success) {
      throw new Error(res.data?.error || 'Formula explanation failed.');
    }
    return res.data.explanation;
  },

  // Explain a single symbol.
  // Mirrors: explain_symbol(symbol) in _render_symbol_tab()
  explainSymbol: async (symbol) => {
    const res = await api.post('/stem/symbol/explain', { symbol }, { timeout: 120000 });
    if (!res.data?.success) {
      throw new Error(res.data?.error || 'Symbol explanation failed.');
    }
    return res.data.explanation;
  },

  // Explain diagrams automatically extracted from the uploaded document.
  // Mirrors: _render_diagram_tab(diagram_images) in backend/stem/stem_page.py
  // The backend extracts images from the PDF and explains each one —
  // no second upload is required from the user.
  getDocumentDiagrams: async (documentId) => {
    const res = await api.post(`/document/${documentId}/diagrams`, {}, { timeout: 300000 });
    if (!res.data?.success) {
      throw new Error(res.data?.error || 'Diagram explanation failed.');
    }
    return res.data.diagrams;
  },

  // Solve a STEM problem step-by-step.
  // Mirrors: solve_problem(problem_input) in _render_step_solver_tab()
  solveProblem: async (problem) => {
    const res = await api.post('/stem/step-solver', { problem }, { timeout: 120000 });
    if (!res.data?.success) {
      throw new Error(res.data?.error || 'Step solver failed.');
    }
    return res.data.solution;
  },
};
