import { useState, useRef, useCallback } from 'react';
import { learningService } from '../services/learningService';

/**
 * Word Explorer — mirrors Streamlit render_word_explorer() in app.py exactly.
 *
 * Streamlit behaviour:
 *   - Text input: "Enter a word to explore" (any word, no document required)
 *   - "Explore 🔍" button → calls explain_word(word) → POST /vocabulary/explain
 *   - Displays: Meaning, Explanation, Example
 *   - Works for words NOT in the uploaded document (e.g. mitochondria, recursion)
 *
 * This component does NOT depend on documentId or the uploaded document.
 */
export default function WordExplorerPanel() {
  const [wordInput, setWordInput] = useState('');
  const [result, setResult]       = useState(null);
  const [loading, setLoading]     = useState(false);
  const [error, setError]         = useState('');

  // Session cache — mirrors Streamlit vocab_explain_cache
  const cache = useRef({});

  const handleExplore = useCallback(async () => {
    const word = wordInput.trim();
    if (!word) {
      setError('Please enter a word.');
      return;
    }

    setError('');
    const key = word.toLowerCase();

    if (cache.current[key]) {
      setResult(cache.current[key]);
      return;
    }

    setLoading(true);
    setResult(null);
    try {
      const explanation = await learningService.explainWord(word);
      cache.current[key] = explanation;
      setResult(explanation);
    } catch (err) {
      setError(err.message || 'Could not explain this word. Please try again.');
    } finally {
      setLoading(false);
    }
  }, [wordInput]);

  const handleKeyDown = (e) => {
    if (e.key === 'Enter') handleExplore();
  };

  return (
    <div className="word-explorer-panel">
      {/* ── Header ──────────────────────────────────────────────────────── */}
      <div className="word-explorer-header card">
        <div className="word-explorer-title-row">
          <span className="word-explorer-icon" aria-hidden="true">🔍</span>
          <div>
            <h2 className="word-explorer-title">Word Explorer</h2>
            <p className="word-explorer-subtitle">
              Learn the meaning of any word — even if it's not in your document!
            </p>
          </div>
        </div>

        {/* Input row — mirrors Streamlit col1/col2 layout */}
        <div className="word-explorer-input-row">
          <input
            type="text"
            className="word-explorer-input"
            value={wordInput}
            onChange={(e) => setWordInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="e.g., photosynthesis, algorithm, mitochondria"
            aria-label="Enter a word to explore"
            disabled={loading}
          />
          <button
            type="button"
            className="button button-primary"
            onClick={handleExplore}
            disabled={loading || !wordInput.trim()}
            aria-busy={loading}
          >
            {loading ? 'Looking up…' : 'Explore 🔍'}
          </button>
        </div>
      </div>

      {/* ── Error ───────────────────────────────────────────────────────── */}
      {error && (
        <p className="word-explorer-error" role="alert">{error}</p>
      )}

      {/* ── Loading ─────────────────────────────────────────────────────── */}
      {loading && (
        <div className="word-explorer-loading card" role="status" aria-live="polite">
          <span className="notes-loading-spinner" aria-hidden="true" />
          <span>Looking up &ldquo;{wordInput.trim()}&rdquo;…</span>
        </div>
      )}

      {/* ── Empty state ─────────────────────────────────────────────────── */}
      {!loading && !result && !error && (
        <div className="word-explorer-empty card">
          <span className="word-explorer-empty-icon" aria-hidden="true">📖</span>
          <p>
            Type any word above and press <strong>Explore</strong> to see its meaning,
            explanation, and an example sentence.
          </p>
        </div>
      )}

      {/* ── Result — mirrors Streamlit html_result block ─────────────────── */}
      {!loading && result && (
        <div className="word-explorer-definition card" aria-live="polite">
          <div className="word-explorer-def-word">
            {(result.word || wordInput).charAt(0).toUpperCase() +
              (result.word || wordInput).slice(1)}
          </div>

          {result.meaning && (
            <div className="word-explorer-def-row">
              <span className="word-explorer-def-label">📖 Meaning</span>
              <span className="word-explorer-def-value">{result.meaning}</span>
            </div>
          )}
          {result.explanation && (
            <div className="word-explorer-def-row">
              <span className="word-explorer-def-label">📝 Explanation</span>
              <span className="word-explorer-def-value">{result.explanation}</span>
            </div>
          )}
          {result.example && (
            <div className="word-explorer-def-row">
              <span className="word-explorer-def-label">💡 Example</span>
              <span className="word-explorer-def-value">&ldquo;{result.example}&rdquo;</span>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
