import { useEffect, useState } from 'react';
import { BrainCircuit, Calculator, FlaskConical, ImagePlus, StepForward } from 'lucide-react';
import { stemService } from '../services/stemService';

// ── Formula Assistant tab ────────────────────────────────────────────────────
// Mirrors: _render_formula_tab(formulas) in backend/stem/stem_page.py

function FormulaTab({ formulas }) {
  const [explanations, setExplanations] = useState({});
  const [loading, setLoading] = useState({});
  const [errors, setErrors] = useState({});
  const [manualFormula, setManualFormula] = useState('');
  const [manualLoading, setManualLoading] = useState(false);
  const [manualError, setManualError] = useState('');
  const [manualResult, setManualResult] = useState(null);

  async function loadExplanation(formula) {
    if (explanations[formula] || loading[formula]) return;
    setLoading((prev) => ({ ...prev, [formula]: true }));
    setErrors((prev) => ({ ...prev, [formula]: '' }));
    try {
      const result = await stemService.explainFormula(formula);
      setExplanations((prev) => ({ ...prev, [formula]: result }));
    } catch (err) {
      setErrors((prev) => ({ ...prev, [formula]: err.message || 'Explanation failed.' }));
    } finally {
      setLoading((prev) => ({ ...prev, [formula]: false }));
    }
  }

  async function handleManualExplain(event) {
    event.preventDefault();
    const trimmed = manualFormula.trim();
    if (!trimmed) {
      setManualError('Enter a formula to explain.');
      return;
    }
    setManualLoading(true);
    setManualError('');
    setManualResult(null);
    try {
      const result = await stemService.explainFormula(trimmed);
      setManualResult(result);
    } catch (err) {
      setManualError(err.message || 'Formula explanation failed.');
    } finally {
      setManualLoading(false);
    }
  }

  if (!formulas || formulas.length === 0) {
    return <p className="stem-empty-state">No formulas detected in the document.</p>;
  }

  return (
    <div className="stem-tab-content">
      <form className="stem-form" onSubmit={handleManualExplain}>
        <label className="stem-field-label" htmlFor="manual-formula-input">
          Explore one formula
        </label>
        <div className="stem-form-row">
          <input
            id="manual-formula-input"
            className="stem-input"
            value={manualFormula}
            onChange={(e) => setManualFormula(e.target.value)}
            placeholder="Example: F = ma"
          />
          <button type="submit" className="button button-primary" disabled={manualLoading}>
            {manualLoading ? 'Checking…' : 'Explain'}
          </button>
        </div>
        {manualError && <p className="stem-inline-error">{manualError}</p>}
      </form>

      {manualResult && (
        <div className="stem-highlight-card">
          <p className="stem-highlight-title">{manualResult.formula || manualFormula}</p>
          <p className="stem-highlight-text">{manualResult.meaning}</p>
          <p className="stem-highlight-caption">{manualResult.example}</p>
          {manualResult.terms && Object.keys(manualResult.terms).length > 0 && (
            <div className="stem-tag-row">
              {Object.entries(manualResult.terms).map(([key, value]) => (
                <span key={key} className="stem-tag">{key}: {value}</span>
              ))}
            </div>
          )}
        </div>
      )}

      <div className="stem-card-list">
        {formulas.map((formula) => {
          const exp = explanations[formula];
          const isLoading = loading[formula];
          const err = errors[formula];
          return (
            <div key={formula} className="stem-list-card">
              <div className="stem-list-card-top">
                <strong>{formula}</strong>
                <button
                  type="button"
                  className="button button-secondary"
                  onClick={() => loadExplanation(formula)}
                  disabled={isLoading || !!exp}
                >
                  {isLoading ? 'Loading…' : exp ? 'Explained' : 'Explain'}
                </button>
              </div>
              {err && <p className="stem-inline-error">{err}</p>}
              {exp && (
                <>
                  <p>{exp.meaning}</p>
                  <p className="stem-caption">{exp.example}</p>
                  {exp.terms && Object.keys(exp.terms).length > 0 && (
                    <div className="stem-tag-row">
                      {Object.entries(exp.terms).map(([key, value]) => (
                        <span key={key} className="stem-tag">{key}: {value}</span>
                      ))}
                    </div>
                  )}
                </>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}

// ── Symbol Explanation tab ───────────────────────────────────────────────────
// Mirrors: _render_symbol_tab(symbols) in backend/stem/stem_page.py

function SymbolTab({ symbols }) {
  const [explanations, setExplanations] = useState({});
  const [loading, setLoading] = useState({});
  const [errors, setErrors] = useState({});

  async function loadExplanation(symbol) {
    if (explanations[symbol] || loading[symbol]) return;
    setLoading((prev) => ({ ...prev, [symbol]: true }));
    setErrors((prev) => ({ ...prev, [symbol]: '' }));
    try {
      const result = await stemService.explainSymbol(symbol);
      setExplanations((prev) => ({ ...prev, [symbol]: result }));
    } catch (err) {
      setErrors((prev) => ({ ...prev, [symbol]: err.message || 'Explanation failed.' }));
    } finally {
      setLoading((prev) => ({ ...prev, [symbol]: false }));
    }
  }

  if (!symbols || symbols.length === 0) {
    return <p className="stem-empty-state">No STEM symbols detected in the document.</p>;
  }

  return (
    <div className="stem-tab-content">
      <div className="stem-card-list">
        {symbols.map((symbol) => {
          const exp = explanations[symbol];
          const isLoading = loading[symbol];
          const err = errors[symbol];
          return (
            <div key={symbol} className="stem-list-card">
              <div className="stem-list-card-top">
                <strong>{symbol}</strong>
                <button
                  type="button"
                  className="button button-secondary"
                  onClick={() => loadExplanation(symbol)}
                  disabled={isLoading || !!exp}
                >
                  {isLoading ? 'Loading…' : exp ? 'Explained' : 'Explain'}
                </button>
              </div>
              {err && <p className="stem-inline-error">{err}</p>}
              {exp && (
                <>
                  <p>{exp.meaning}</p>
                  <p>{exp.simple_explanation}</p>
                  <p className="stem-caption">{exp.example}</p>
                </>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}

// ── Diagram Explanation tab ──────────────────────────────────────────────────
// Mirrors: _render_diagram_tab(diagram_images) in backend/stem/stem_page.py
// Streamlit extracts diagrams automatically from the uploaded PDF.
// React calls POST /document/<id>/diagrams which does the same extraction
// server-side — no second upload is ever required.

function DiagramTab({ documentId }) {
  const [diagrams, setDiagrams] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    let ignore = false;
    async function load() {
      if (!documentId) return;
      setLoading(true);
      setError('');
      try {
        const result = await stemService.getDocumentDiagrams(documentId);
        if (!ignore) setDiagrams(result);
      } catch (err) {
        if (!ignore) setError(err.message || 'Diagram explanation failed.');
      } finally {
        if (!ignore) setLoading(false);
      }
    }
    load();
    return () => { ignore = true; };
  }, [documentId]);

  if (loading) return <p className="stem-inline-loading">Extracting and explaining diagrams from your document…</p>;
  if (error) return <p className="stem-inline-error">{error}</p>;
  if (!diagrams || diagrams.length === 0) {
    return <p className="stem-empty-state">No diagrams were found in this document.</p>;
  }

  return (
    <div className="stem-tab-content">
      {diagrams.map(({ index, filename, image_url, explanation }) => (
        <div key={index} className="stem-highlight-card">
          <p className="stem-highlight-title">{explanation.diagram_type || `Diagram ${index}`}</p>
          <p className="stem-caption">{filename}</p>
          {image_url && (
            <img
              src={image_url}
              alt={explanation.diagram_type || `Diagram ${index}`}
              className="stem-diagram-image"
            />
          )}
          {explanation.purpose && <p>{explanation.purpose}</p>}
          {explanation.how_it_works?.length > 0 && (
            <ul className="stem-steps-list">
              {explanation.how_it_works.map((step, i) => (
                <li key={i}>{step}</li>
              ))}
            </ul>
          )}
          {explanation.component_roles?.length > 0 && (
            <div className="stem-tag-row">
              {explanation.component_roles.map((cr, i) => (
                <span key={i} className="stem-tag">{cr.component}: {cr.role}</span>
              ))}
            </div>
          )}
          {explanation.key_concept && <p><strong>Key concept:</strong> {explanation.key_concept}</p>}
          {explanation.simplified_explanation && <p>{explanation.simplified_explanation}</p>}
          {explanation.key_takeaway && <p className="stem-caption">{explanation.key_takeaway}</p>}
        </div>
      ))}
    </div>
  );
}

// ── Step Solver tab ──────────────────────────────────────────────────────────
// Mirrors: _render_step_solver_tab(document_text) in backend/stem/stem_page.py

function StepSolverTab() {
  const [input, setInput] = useState('');
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  async function handleSolve(event) {
    event.preventDefault();
    const trimmed = input.trim();
    if (!trimmed) {
      setError('Enter a STEM problem before solving.');
      return;
    }
    setLoading(true);
    setError('');
    setResult(null);
    try {
      const solution = await stemService.solveProblem(trimmed);
      setResult(solution);
    } catch (err) {
      setError(err.message || 'Step solver failed.');
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="stem-tab-content">
      <form className="stem-form" onSubmit={handleSolve}>
        <label className="stem-field-label" htmlFor="solver-input">
          Enter your STEM problem
        </label>
        <textarea
          id="solver-input"
          className="stem-textarea"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          rows={5}
          placeholder={'10 + 5 * 2\n\nOR\n\nx + 5 = 12\n\nOR\n\nF = ma\nm = 5\na = 2'}
        />
        <button type="submit" className="button button-primary" disabled={loading}>
          {loading ? 'Solving…' : 'Solve Problem'}
        </button>
        {error && <p className="stem-inline-error">{error}</p>}
      </form>

      {result && (
        <div className="stem-highlight-card">
          <p className="stem-highlight-title">{result.formula || 'Solution'}</p>
          {result.meaning && <p>{result.meaning}</p>}
          {result.example && <p className="stem-caption">{result.example}</p>}
          {result.terms && Object.keys(result.terms).length > 0 && (
            <div className="stem-tag-row">
              {Object.entries(result.terms).map(([key, value]) => (
                <span key={key} className="stem-tag">{key}: {value}</span>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

// ── Main panel ───────────────────────────────────────────────────────────────

const TABS = [
  { id: 'formula',  label: 'Formula Assistant',   icon: Calculator },
  { id: 'symbol',   label: 'Symbol Explanation',  icon: FlaskConical },
  { id: 'diagram',  label: 'Diagram Explanation', icon: ImagePlus },
  { id: 'solver',   label: 'Step Solver',         icon: StepForward },
];

export default function StemSupportPanel({ documentId }) {
  const [stemData, setStemData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [activeTab, setActiveTab] = useState('formula');

  useEffect(() => {
    let ignore = false;

    async function load() {
      if (!documentId) {
        setLoading(false);
        return;
      }
      setLoading(true);
      setError('');
      try {
        const data = await stemService.analyzeDocument(documentId);
        if (!ignore) setStemData(data);
      } catch (err) {
        if (!ignore) setError(err.message || 'Unable to load STEM support.');
      } finally {
        if (!ignore) setLoading(false);
      }
    }

    load();
    return () => { ignore = true; };
  }, [documentId]);

  return (
    <div className="stem-panel">
      <section className="stem-hero card">
        <div className="stem-hero-copy">
          <div className="stem-eyebrow">
            <BrainCircuit size={18} />
            <span>STEM support</span>
          </div>
          <h2>Clear explanations, visual support, and guided problem solving.</h2>
        </div>
        {stemData && (
          <div className="stem-hero-stats">
            <div className="stem-stat-card">
              <div className="stem-stat-icon"><Calculator size={18} /></div>
              <div>
                <p className="stem-stat-value">{stemData.formula_count ?? 0}</p>
                <span className="stem-stat-label">Formulas</span>
              </div>
            </div>
            <div className="stem-stat-card">
              <div className="stem-stat-icon"><FlaskConical size={18} /></div>
              <div>
                <p className="stem-stat-value">{stemData.symbol_count ?? 0}</p>
                <span className="stem-stat-label">Symbols</span>
              </div>
            </div>
            <div className="stem-stat-card">
              <div className="stem-stat-icon"><ImagePlus size={18} /></div>
              <div>
                <p className="stem-stat-value">{stemData.has_diagrams ? 'Detected' : 'None'}</p>
                <span className="stem-stat-label">Diagrams</span>
              </div>
            </div>
          </div>
        )}
      </section>

      {error && <p className="notes-error" role="alert">{error}</p>}

      {loading ? (
        <div className="notes-loading card" role="status" aria-live="polite">
          <span className="notes-loading-spinner" aria-hidden="true" />
          <span>Preparing your STEM support view…</span>
        </div>
      ) : (
        <>
          <nav className="stem-tab-nav" role="tablist" aria-label="STEM tools">
            {TABS.map(({ id, label, icon: Icon }) => (
              <button
                key={id}
                type="button"
                role="tab"
                aria-selected={activeTab === id}
                className={`stem-tab-btn${activeTab === id ? ' stem-tab-btn--active' : ''}`}
                onClick={() => setActiveTab(id)}
              >
                <Icon size={16} aria-hidden="true" />
                {label}
              </button>
            ))}
          </nav>

          <div className="stem-tab-panel card">
            {activeTab === 'formula' && (
              <FormulaTab formulas={stemData?.formulas ?? []} />
            )}
            {activeTab === 'symbol' && (
              <SymbolTab symbols={stemData?.symbols ?? []} />
            )}
            {activeTab === 'diagram' && <DiagramTab documentId={documentId} />}
            {activeTab === 'solver' && <StepSolverTab />}
          </div>
        </>
      )}
    </div>
  );
}
