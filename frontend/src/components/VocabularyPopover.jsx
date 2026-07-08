import { useEffect, useRef } from 'react';

/**
 * Inline vocabulary popup — mirrors Streamlit reading_view.py click behaviour.
 *
 * Streamlit showed ONLY "Meaning:" when a highlighted word was clicked
 * (_get_definition → BUILT_IN_DICTIONARY or explain_word().meaning only).
 * explanation and example are NOT shown here; they belong to Word Explorer.
 */
export default function VocabularyPopover({ anchorRect, explanation, loading, error, onClose }) {
  const ref = useRef(null);

  useEffect(() => {
    function handlePointerDown(e) {
      if (ref.current && !ref.current.contains(e.target)) onClose();
    }
    document.addEventListener('pointerdown', handlePointerDown);
    return () => document.removeEventListener('pointerdown', handlePointerDown);
  }, [onClose]);

  useEffect(() => {
    function handleKey(e) {
      if (e.key === 'Escape') onClose();
    }
    document.addEventListener('keydown', handleKey);
    return () => document.removeEventListener('keydown', handleKey);
  }, [onClose]);

  const style = {};
  if (anchorRect) {
    const top = anchorRect.bottom + window.scrollY + 6;
    const left = Math.min(
      anchorRect.left + window.scrollX,
      window.innerWidth - 320 - 12,
    );
    style.top = top;
    style.left = Math.max(8, left);
  }

  return (
    <div
      ref={ref}
      className="vocab-popover"
      style={style}
      role="dialog"
      aria-modal="true"
      aria-label="Word meaning"
    >
      <button
        type="button"
        className="vocab-popover-close"
        onClick={onClose}
        aria-label="Close"
      >
        ✕
      </button>

      {loading && (
        <div className="vocab-popover-loading" role="status">
          <span className="notes-loading-spinner" aria-hidden="true" />
          Looking up…
        </div>
      )}

      {error && !loading && (
        <p className="vocab-popover-error" role="alert">{error}</p>
      )}

      {explanation && !loading && (
        <>
          <div className="vocab-popover-word">{explanation.word}</div>
          {explanation.meaning && (
            <div className="vocab-popover-row">
              <span className="vocab-popover-label">📖 Meaning</span>
              <span>{explanation.meaning}</span>
            </div>
          )}
        </>
      )}
    </div>
  );
}
