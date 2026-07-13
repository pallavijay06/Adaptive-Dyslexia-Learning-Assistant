import { useEffect, useMemo, useState } from 'react';
import {
  BookOpenCheck,
  BrainCircuit,
  Calculator,
  ImagePlus,
  Sparkles,
  StepForward,
  Wand2,
} from 'lucide-react';
import { learningService } from '../services/learningService';
import { stemService } from '../services/stemService';

function formatTextBlock(text) {
  if (!text) return null;
  return text
    .split(/\n+/)
    .map((line) => line.trim())
    .filter(Boolean)
    .slice(0, 4);
}

export default function StemSupportPanel({ documentId }) {
  const [documentText, setDocumentText] = useState('');
  const [analysis, setAnalysis] = useState(null);
  const [formulaCards, setFormulaCards] = useState([]);
  const [conceptCards, setConceptCards] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const [formulaInput, setFormulaInput] = useState('');
  const [formulaExplanation, setFormulaExplanation] = useState(null);
  const [formulaLoading, setFormulaLoading] = useState(false);
  const [formulaError, setFormulaError] = useState('');

  const [solverInput, setSolverInput] = useState('');
  const [solverResult, setSolverResult] = useState(null);
  const [solverLoading, setSolverLoading] = useState(false);
  const [solverError, setSolverError] = useState('');

  const [diagramFile, setDiagramFile] = useState(null);
  const [diagramPreview, setDiagramPreview] = useState('');
  const [diagramExplanation, setDiagramExplanation] = useState(null);
  const [diagramLoading, setDiagramLoading] = useState(false);
  const [diagramError, setDiagramError] = useState('');

  useEffect(() => {
    let ignore = false;

    async function loadStemSupport() {
      if (!documentId) {
        setLoading(false);
        return;
      }

      try {
        setLoading(true);
        setError('');
        const text = await learningService.fetchDocumentText(documentId);
        if (ignore) return;
        setDocumentText(text);

        const [analysisResult, formulaResult, conceptResult] = await Promise.all([
          stemService.analyzeDocumentText(text),
          stemService.extractFormulas(text),
          stemService.getConceptBreakdown(text),
        ]);

        if (ignore) return;
        setAnalysis(analysisResult);
        setFormulaCards(formulaResult?.explanations || []);
        setConceptCards(conceptResult?.formulas || []);
      } catch (err) {
        if (!ignore) {
          setError(err.message || 'Unable to load STEM support right now.');
        }
      } finally {
        if (!ignore) {
          setLoading(false);
        }
      }
    }

    loadStemSupport();
    return () => {
      ignore = true;
    };
  }, [documentId]);

  const summaryItems = useMemo(() => {
    if (!analysis) return [];
    return [
      { label: 'Formulas', value: analysis.formula_count ?? 0, icon: Calculator },
      { label: 'Symbols', value: analysis.symbol_count ?? 0, icon: Sparkles },
      { label: 'Diagrams', value: analysis.has_diagrams ? 'Detected' : 'None', icon: ImagePlus },
    ];
  }, [analysis]);

  async function handleFormulaExplain(event) {
    event.preventDefault();
    const trimmed = formulaInput.trim();
    if (!trimmed) {
      setFormulaError('Enter a formula to explain.');
      return;
    }

    try {
      setFormulaLoading(true);
      setFormulaError('');
      const result = await stemService.explainFormula(trimmed);
      setFormulaExplanation(result);
      setFormulaCards((current) => [result, ...current.filter((item) => item.formula !== result.formula)]);
    } catch (err) {
      setFormulaError(err.message || 'Formula explanation failed.');
    } finally {
      setFormulaLoading(false);
    }
  }

  async function handleSolverSubmit(event) {
    event.preventDefault();
    const trimmed = solverInput.trim();
    if (!trimmed) {
      setSolverError('Enter a problem or formula to solve.');
      return;
    }

    try {
      setSolverLoading(true);
      setSolverError('');
      const result = await stemService.solveProblem(trimmed);
      setSolverResult(result);
    } catch (err) {
      setSolverError(err.message || 'Step solver failed.');
    } finally {
      setSolverLoading(false);
    }
  }

  async function handleDiagramUpload(event) {
    const file = event.target.files?.[0];
    if (!file) return;

    const previewUrl = URL.createObjectURL(file);
    setDiagramFile(file);
    setDiagramPreview(previewUrl);
    setDiagramLoading(true);
    setDiagramError('');
    setDiagramExplanation(null);

    try {
      const result = await stemService.explainDiagram(file);
      setDiagramExplanation(result);
    } catch (err) {
      setDiagramError(err.message || 'Diagram explanation failed.');
    } finally {
      setDiagramLoading(false);
    }
  }

  return (
    <div className="stem-panel">
      <section className="stem-hero card">
        <div className="stem-hero-copy">
          <div className="stem-eyebrow">
            <BrainCircuit size={18} />
            <span>STEM support</span>
          </div>
          <h2>Clear explanations, visual support, and guided problem solving.</h2>
          <p>
            This view keeps the existing STEM tools intact while presenting them with calmer spacing,
            brighter icons, and smoother transitions.
          </p>
        </div>
        <div className="stem-hero-stats">
          {summaryItems.map((item) => {
            const Icon = item.icon;
            return (
              <div key={item.label} className="stem-stat-card">
                <div className="stem-stat-icon">
                  <Icon size={18} />
                </div>
                <div>
                  <p className="stem-stat-value">{item.value}</p>
                  <span className="stem-stat-label">{item.label}</span>
                </div>
              </div>
            );
          })}
        </div>
      </section>

      {error && <p className="notes-error" role="alert">{error}</p>}

      {loading ? (
        <div className="notes-loading card" role="status" aria-live="polite">
          <span className="notes-loading-spinner" aria-hidden="true" />
          <span>Preparing your STEM support view…</span>
        </div>
      ) : (
        <>
          <section className="stem-grid">
            <article className="stem-card card">
              <div className="stem-card-header">
                <div>
                  <p className="stem-card-kicker">Formula cards</p>
                  <h3>Understand formulas with simple language</h3>
                </div>
                <div className="stem-card-icon">
                  <Calculator size={20} />
                </div>
              </div>

              <form className="stem-form" onSubmit={handleFormulaExplain}>
                <label className="stem-field-label" htmlFor="formula-input">
                  Explore one formula
                </label>
                <div className="stem-form-row">
                  <input
                    id="formula-input"
                    className="stem-input"
                    value={formulaInput}
                    onChange={(event) => setFormulaInput(event.target.value)}
                    placeholder="Example: F = ma"
                  />
                  <button type="submit" className="button button-primary" disabled={formulaLoading}>
                    {formulaLoading ? 'Checking…' : 'Explain'}
                  </button>
                </div>
                {formulaError && <p className="stem-inline-error">{formulaError}</p>}
              </form>

              <div className="stem-card-body">
                {formulaExplanation && (
                  <div className="stem-highlight-card">
                    <p className="stem-highlight-title">{formulaExplanation.formula || formulaInput}</p>
                    <p className="stem-highlight-text">{formulaExplanation.meaning}</p>
                    <p className="stem-highlight-caption">{formulaExplanation.example}</p>
                  </div>
                )}

                {formulaCards.length > 0 ? (
                  <div className="stem-card-list">
                    {formulaCards.map((item, index) => (
                      <div key={`${item.formula || 'formula'}-${index}`} className="stem-list-card">
                        <div className="stem-list-card-top">
                          <strong>{item.formula || 'Formula'}</strong>
                          <span className="stem-pill">Ready</span>
                        </div>
                        <p>{item.meaning || 'Meaning will appear here.'}</p>
                        {item.terms && Object.keys(item.terms).length > 0 && (
                          <div className="stem-tag-row">
                            {Object.entries(item.terms).slice(0, 4).map(([key, value]) => (
                              <span key={key} className="stem-tag">{key}: {value}</span>
                            ))}
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="stem-empty-state">
                    <Wand2 size={18} />
                    <span>Formulas found in your document will appear here.</span>
                  </div>
                )}
              </div>
            </article>

            <article className="stem-card card">
              <div className="stem-card-header">
                <div>
                  <p className="stem-card-kicker">Diagram viewer</p>
                  <h3>Upload a diagram and get a guided explanation</h3>
                </div>
                <div className="stem-card-icon">
                  <ImagePlus size={20} />
                </div>
              </div>

              <label className="stem-upload-box" htmlFor="diagram-upload">
                <input id="diagram-upload" type="file" accept="image/png,image/jpeg" onChange={handleDiagramUpload} />
                <span className="stem-upload-title">Choose a PNG or JPG diagram</span>
                <span className="stem-upload-subtitle">The explanation will stay in the same workspace.</span>
              </label>

              {diagramLoading && <p className="stem-inline-loading">Reading the diagram…</p>}
              {diagramError && <p className="stem-inline-error">{diagramError}</p>}

              <div className="stem-card-body">
                {diagramPreview && (
                  <div className="stem-image-preview">
                    <img src={diagramPreview} alt="Uploaded diagram preview" />
                  </div>
                )}

                {diagramExplanation && (
                  <div className="stem-highlight-card">
                    <p className="stem-highlight-title">What this diagram shows</p>
                    <div className="stem-explanation-lines">
                      {formatTextBlock(diagramExplanation.meaning || diagramExplanation.example || '')?.map((line) => (
                        <p key={line}>{line}</p>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            </article>
          </section>

          <section className="stem-grid">
            <article className="stem-card card">
              <div className="stem-card-header">
                <div>
                  <p className="stem-card-kicker">Concept explanations</p>
                  <h3>Break difficult ideas into smaller pieces</h3>
                </div>
                <div className="stem-card-icon">
                  <BookOpenCheck size={20} />
                </div>
              </div>

              <div className="stem-card-body">
                {conceptCards.length > 0 ? (
                  <div className="stem-card-list">
                    {conceptCards.map((item, index) => (
                      <div key={`${item.formula || item.meaning || 'concept'}-${index}`} className="stem-list-card">
                        <div className="stem-list-card-top">
                          <strong>{item.formula || 'Concept'}</strong>
                          <span className="stem-pill">Explained</span>
                        </div>
                        <p>{item.meaning || 'Explanation coming soon.'}</p>
                        {item.example && <p className="stem-caption">{item.example}</p>}
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="stem-empty-state">
                    <Sparkles size={18} />
                    <span>Concept breakdowns will appear after your document is reviewed.</span>
                  </div>
                )}
              </div>
            </article>

            <article className="stem-card card">
              <div className="stem-card-header">
                <div>
                  <p className="stem-card-kicker">Step solver</p>
                  <h3>Follow a guided path to the answer</h3>
                </div>
                <div className="stem-card-icon">
                  <StepForward size={20} />
                </div>
              </div>

              <form className="stem-form" onSubmit={handleSolverSubmit}>
                <label className="stem-field-label" htmlFor="solver-input">
                  Enter a problem or formula
                </label>
                <textarea
                  id="solver-input"
                  className="stem-textarea"
                  value={solverInput}
                  onChange={(event) => setSolverInput(event.target.value)}
                  rows={4}
                  placeholder="Example: Find v when a = 2 and t = 4 in v = at"
                />
                <button type="submit" className="button button-primary" disabled={solverLoading}>
                  {solverLoading ? 'Solving…' : 'Solve step by step'}
                </button>
                {solverError && <p className="stem-inline-error">{solverError}</p>}
              </form>

              <div className="stem-card-body">
                {solverResult && (
                  <div className="stem-highlight-card">
                    <p className="stem-highlight-title">Step-by-step guidance</p>
                    <div className="stem-explanation-lines">
                      {formatTextBlock(solverResult.meaning || solverResult.example || '')?.map((line) => (
                        <p key={line}>{line}</p>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            </article>
          </section>
        </>
      )}
    </div>
  );
}
